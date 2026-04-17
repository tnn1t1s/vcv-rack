#include <rack.hpp>
#include "AgentModule.hpp"
#include "PanelLayout.hpp"
#include "agentrack/infrastructure/SaphireImpulseResponse.hpp"
#include "agentrack/infrastructure/PartitionedConvolution.hpp"
#include "agentrack/infrastructure/SaphireRuntime.hpp"
#include "agentrack/signal/Audio.hpp"
#include "agentrack/signal/SaphireWetPath.hpp"
#include "ir_names.hpp"
#include <cmath>
#include <cstdio>

using namespace rack;
extern Plugin* pluginInstance;

/**
 * Saphire -- fixed-IR convolution reverb with operator transformations.
 *
 * IR: Lex Hall [cv313 / Echospace treatments], 44100 Hz, 3 seconds (132300 samples).
 * Loaded from res/lex-hall.f32 (raw interleaved float32, pre-resampled from 48kHz).
 *
 * Engine: uniformly partitioned overlap-save convolution.
 *   Block size B = 512 samples (11.6ms latency)
 *   FFT size    = 1024 (= 2B)
 *   Partitions  = ceil(ir_len / B), max 259 for 3s IR
 *   Cost        ~ O(P + log B) per sample vs O(N) direct -- ~250x faster
 *
 * Controls transform the linear operator H:
 *   MIX   dry/wet blend (constant-power)
 *   TIME  scales active partition count: 0 = 1 block (~12ms), 1 = all partitions
 *   BEND  nonlinear time warp of IR: beta = exp(bend * ln(3))
 *           negative: beta<1 → reads later, pulls energy forward / compresses tail
 *           zero:     beta=1 → identity
 *           positive: beta>1 → reads earlier, smears energy into tail
 *   TONE  one-pole lowpass on wet signal: 0 = ~100 Hz, 1 = ~20 kHz
 *   PRE   pre-delay: 0 = none, 1 = 100ms
 *
 * Stereo in/out. Mono input (right unpatched) folds to both channels.
 *
 * Rack IDs (stable, never reorder):
 *   Params:  MIX_PARAM=0, TIME_PARAM=1, BEND_PARAM=2, TONE_PARAM=3, PRE_PARAM=4
 *   Inputs:  IN_L_INPUT=0, IN_R_INPUT=1
 *   Outputs: OUT_L_OUTPUT=0, OUT_R_OUTPUT=1
 */


// ---------------------------------------------------------------------------
// Constants
// ---------------------------------------------------------------------------

using PartitionedConvolution = AgentRack::Infrastructure::PartitionedConvolution;
using SaphireImpulseResponse = AgentRack::Infrastructure::SaphireImpulseResponse;
using SaphireRuntime = AgentRack::Infrastructure::SaphireRuntime;
using SaphireWetPath = AgentRack::Signal::SaphireWetPath;

// ---------------------------------------------------------------------------
// Module
// ---------------------------------------------------------------------------

struct Saphire : AgentModule {

    enum ParamId  { MIX_PARAM, TIME_PARAM, BEND_PARAM, TONE_PARAM, PRE_PARAM, IR_PARAM, NUM_PARAMS };
    enum InputId  { IN_L_INPUT, IN_R_INPUT, NUM_INPUTS  };
    enum OutputId { OUT_L_OUTPUT, OUT_R_OUTPUT, NUM_OUTPUTS };

    // Flat composition: IR policy, runtime/engine handoff, and wet-path
    // post-processing each live in their own component.
    SaphireImpulseResponse impulseResponse;
    SaphireRuntime runtime;
    SaphireWetPath wetPath;

    Saphire() {
        config(NUM_PARAMS, NUM_INPUTS, NUM_OUTPUTS);
        configParam(MIX_PARAM,  0.f,  1.f,  0.5f,  "Mix");
        configParam(TIME_PARAM, 0.f,  1.f,  0.5f,  "Time");
        configParam(BEND_PARAM, -1.f, 1.f,  0.f,   "Bend");
        configParam(TONE_PARAM, 0.f,  1.f,  0.65f, "Tone");
        configParam(PRE_PARAM,  0.f,  1.f,  0.f,   "Pre-delay");
        configParam(IR_PARAM,   0.f,  (float)(IR_COUNT - 1), 38.f, "IR");
        paramQuantities[IR_PARAM]->snapEnabled = true;
        configInput (IN_L_INPUT,   "In L");
        configInput (IN_R_INPUT,   "In R");
        configOutput(OUT_L_OUTPUT, "Out L");
        configOutput(OUT_R_OUTPUT, "Out R");

        runtime.init();
        // Initial load: synchronous (no thread needed at startup)
        loadIRFromFile(38);
        doLoad(0, 0.5f, 0.f);
        runtime.setInitialState(38, 0.5f, 0.f);
    }

    ~Saphire() {
        runtime.joinBuilder();
    }

    // Load IR from res/ir/NN.f32. Called from bg thread (or constructor).
    // The .f32 files are already normalized to unit energy by convert_irs.py.
    void loadIRFromFile(int idx) {
        char name[32];
        snprintf(name, sizeof(name), "res/ir/%02d.f32", idx);
        std::string path = asset::plugin(pluginInstance, name);
        impulseResponse.loadFromPath(path, idx);
    }

    // Compute warp and load into the target convolution engine. Called from any thread.
    void doLoad(int target, float time_p, float bend_p) {
        SaphireImpulseResponse::Kernel kernel = impulseResponse.buildKernel(time_p, bend_p);
        if (kernel.first.empty()) {
            return;
        }
        runtime.convolutionAt(target).load(
            kernel.first.data(),
            kernel.second.data(),
            static_cast<int>(kernel.first.size()));
    }

    // Launch a background thread to rebuild the inactive engine.
    // If a rebuild is already running the call is a no-op -- the change
    // will be detected again next process() and retried.
    void launchRebuild(const SaphireRuntime::RebuildRequest& request) {
        runtime.launchRebuild(request,
            [this, request](int target, int requestedIrIndex) {
                if (requestedIrIndex != impulseResponse.loadedIrIndex())
                    loadIRFromFile(requestedIrIndex);
                doLoad(target, request.timeParam, request.bendParam);
            });
    }

    void process(const ProcessArgs& args) override {
        float mix_p  = params[MIX_PARAM].getValue();
        float time_p = params[TIME_PARAM].getValue();
        float bend_p = params[BEND_PARAM].getValue();
        float tone_p = params[TONE_PARAM].getValue();
        float pre_p  = params[PRE_PARAM].getValue();

        // Check for a completed rebuild -- swap engines, start crossfade
        runtime.consumeCompletedRebuild();

        SaphireRuntime::RebuildRequest request =
            SaphireRuntime::makeRequest(params[IR_PARAM].getValue(), time_p, bend_p, IR_COUNT);

        // Detect any change and launch rebuild (no-op if already building)
        if (runtime.shouldRebuild(request)) {
            launchRebuild(request);
        }

        // Inputs: sum polyphonic channels, then mono-fold if R unpatched
        float in_L = 0.f;
        int ch_L = std::max(1, inputs[IN_L_INPUT].getChannels());
        for (int c = 0; c < ch_L; c++)
            in_L += inputs[IN_L_INPUT].getPolyVoltage(c);
        in_L = AgentRack::Signal::Audio::fromRackVolts(in_L);

        float in_R;
        if (inputs[IN_R_INPUT].isConnected()) {
            in_R = 0.f;
            int ch_R = inputs[IN_R_INPUT].getChannels();
            for (int c = 0; c < ch_R; c++)
                in_R += inputs[IN_R_INPUT].getPolyVoltage(c);
            in_R = AgentRack::Signal::Audio::fromRackVolts(in_R);
        } else {
            in_R = in_L;
        }

        // Pre-delay
        SaphireWetPath::StereoFrame delayed = wetPath.applyPreDelay(in_L, in_R, pre_p);

        // Push to live engine; push to old engine only during crossfade (safe_old=true)
        float wet_L, wet_R;
        float old_L = 0.f, old_R = 0.f;
        runtime.liveConvolution().push(delayed.left, delayed.right, wet_L, wet_R);
        if (runtime.oldConvolutionIsSafe()) {
            runtime.oldConvolution().push(delayed.left, delayed.right, old_L, old_R);
        }

        // Crossfade: blend old engine's live output with new engine's live output
        runtime.applyCrossfade(wet_L, wet_R, old_L, old_R);

        // TONE: one-pole lowpass on wet signal
        SaphireWetPath::StereoFrame toned = wetPath.applyTone(wet_L, wet_R, tone_p, args.sampleRate);

        SaphireWetPath::StereoFrame mixed = wetPath.mix(in_L, in_R, toned.left, toned.right, mix_p);
        outputs[OUT_L_OUTPUT].setVoltage(AgentRack::Signal::Audio::toRackVolts(mixed.left));
        outputs[OUT_R_OUTPUT].setVoltage(AgentRack::Signal::Audio::toRackVolts(mixed.right));
    }

};


// ---------------------------------------------------------------------------
// IR Display -- shows index + name, driven by module->cur_ir_idx
// ---------------------------------------------------------------------------

struct IRDisplay : rack::TransparentWidget {
    Saphire* module = nullptr;

    void draw(const DrawArgs& args) override {
        // Background
        nvgBeginPath(args.vg);
        nvgRoundedRect(args.vg, 0, 0, box.size.x, box.size.y, 2.f);
        nvgFillColor(args.vg, nvgRGBA(0, 0, 0, 200));
        nvgFill(args.vg);
        nvgStrokeColor(args.vg, nvgRGBA(255, 255, 255, 50));
        nvgStrokeWidth(args.vg, 0.5f);
        nvgStroke(args.vg);

        if (!module) {
            // Preview mode: show placeholder
            nvgFontSize(args.vg, 7.5f);
            nvgTextAlign(args.vg, NVG_ALIGN_CENTER | NVG_ALIGN_MIDDLE);
            nvgFillColor(args.vg, nvgRGB(160, 160, 160));
            nvgText(args.vg, box.size.x * 0.5f, box.size.y * 0.5f, "38 LEX HALL", NULL);
            return;
        }

        int idx = module->runtime.currentIrIndex();
        if (idx < 0 || idx >= IR_COUNT) return;

        // Index (left, amber)
        char num[8];
        snprintf(num, sizeof(num), "%02d", idx);
        nvgFontSize(args.vg, 8.5f);
        nvgTextAlign(args.vg, NVG_ALIGN_LEFT | NVG_ALIGN_MIDDLE);
        nvgFillColor(args.vg, nvgRGB(255, 210, 80));
        nvgText(args.vg, 4.f, box.size.y * 0.5f, num, NULL);

        // Name (right of index, white)
        nvgFontSize(args.vg, 7.5f);
        nvgTextAlign(args.vg, NVG_ALIGN_LEFT | NVG_ALIGN_MIDDLE);
        nvgFillColor(args.vg, nvgRGB(220, 220, 220));
        nvgText(args.vg, 20.f, box.size.y * 0.5f, IR_NAMES[idx], NULL);
    }
};


// ---------------------------------------------------------------------------
// Panel
// ---------------------------------------------------------------------------

struct SaphirePanel : rack::widget::Widget {
    void draw(const DrawArgs& args) override {
        AgentLayout::drawAssetPanel(
            args.vg, box.size, pluginInstance,
            "res/Saphire-bg.jpg",
            nvgRGB(15, 15, 25),
            "SPH", nvgRGB(255, 255, 255));
    }
};


// ---------------------------------------------------------------------------
// Widget -- 8HP
// ---------------------------------------------------------------------------

struct SaphireWidget : rack::ModuleWidget {

    SaphireWidget(Saphire* module) {
        setModule(module);

        auto* panel = new SaphirePanel;
        panel->box.size = AgentLayout::panelSize_8HP();
        addChild(panel);
        box.size = panel->box.size;

        AgentLayout::addScrews_8HP(this);

        // MIX -- large, centered
        addParam(createParamCentered<rack::RoundBigBlackKnob>(
            mm2px(rack::Vec(AgentLayout::CENTER_8HP, AgentLayout::COMPACT_ROWS_8HP[0])), module, Saphire::MIX_PARAM));
        // TIME left, BEND right -- medium
        addParam(createParamCentered<rack::RoundBlackKnob>(
            mm2px(rack::Vec(AgentLayout::LEFT_PAIR_COLUMN_8HP, AgentLayout::COMPACT_ROWS_8HP[1])), module, Saphire::TIME_PARAM));
        addParam(createParamCentered<rack::RoundBlackKnob>(
            mm2px(rack::Vec(AgentLayout::RIGHT_PAIR_COLUMN_8HP, AgentLayout::COMPACT_ROWS_8HP[1])), module, Saphire::BEND_PARAM));
        // TONE left, PRE right -- small
        addParam(createParamCentered<rack::RoundSmallBlackKnob>(
            mm2px(rack::Vec(AgentLayout::LEFT_PAIR_COLUMN_8HP, AgentLayout::COMPACT_ROWS_8HP[2])), module, Saphire::TONE_PARAM));
        addParam(createParamCentered<rack::RoundSmallBlackKnob>(
            mm2px(rack::Vec(AgentLayout::RIGHT_PAIR_COLUMN_8HP, AgentLayout::COMPACT_ROWS_8HP[2])), module, Saphire::PRE_PARAM));

        // IR display (full-width label)
        auto* disp = new IRDisplay;
        disp->module = module;
        disp->box.pos  = mm2px(rack::Vec(3.f, 63.f));
        disp->box.size = mm2px(rack::Vec(34.64f, 6.5f));
        addChild(disp);

        // IR selector -- snap knob, centered
        addParam(createParamCentered<rack::RoundBlackKnob>(
            mm2px(rack::Vec(AgentLayout::CENTER_8HP, AgentLayout::COMPACT_ROWS_8HP[3])), module, Saphire::IR_PARAM));

        // IN L/R
        addInput(createInputCentered<rack::PJ301MPort>(
            mm2px(rack::Vec(AgentLayout::LEFT_PAIR_COLUMN_8HP, AgentLayout::COMPACT_ROWS_8HP[4])), module, Saphire::IN_L_INPUT));
        addInput(createInputCentered<rack::PJ301MPort>(
            mm2px(rack::Vec(AgentLayout::RIGHT_PAIR_COLUMN_8HP, AgentLayout::COMPACT_ROWS_8HP[4])), module, Saphire::IN_R_INPUT));

        // OUT L/R
        addOutput(createOutputCentered<rack::PJ301MPort>(
            mm2px(rack::Vec(AgentLayout::LEFT_PAIR_COLUMN_8HP, AgentLayout::COMPACT_ROWS_8HP[5])), module, Saphire::OUT_L_OUTPUT));
        addOutput(createOutputCentered<rack::PJ301MPort>(
            mm2px(rack::Vec(AgentLayout::RIGHT_PAIR_COLUMN_8HP, AgentLayout::COMPACT_ROWS_8HP[5])), module, Saphire::OUT_R_OUTPUT));
    }
};


rack::Model* modelSaphire = createModel<Saphire, SaphireWidget>("Saphire");
