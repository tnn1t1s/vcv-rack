#include <rack.hpp>
#include "AgentModule.hpp"
#include "agentrack/infrastructure/PartitionedConvolution.hpp"
#include "agentrack/signal/Audio.hpp"
#include "ir_names.hpp"
#include <cmath>
#include <cstdio>
#include <cstring>
#include <complex>
#include <vector>
#include <memory>
#include <thread>
#include <atomic>

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

static constexpr int BLOCK     = PartitionedConvolution::kBlockSize;
static constexpr int MAX_IR    = 132300;         // 3s at 44100 Hz
static constexpr int MAX_PRE   = 4410;           // 100ms at 44100 Hz


// ---------------------------------------------------------------------------
// Module
// ---------------------------------------------------------------------------

struct Saphire : AgentModule {

    enum ParamId  { MIX_PARAM, TIME_PARAM, BEND_PARAM, TONE_PARAM, PRE_PARAM, IR_PARAM, NUM_PARAMS };
    enum InputId  { IN_L_INPUT, IN_R_INPUT, NUM_INPUTS  };
    enum OutputId { OUT_L_OUTPUT, OUT_R_OUTPUT, NUM_OUTPUTS };

    // Raw IR -- written only from bg thread (or constructor), read only from bg thread.
    // loaded_ir_idx tracks which file is in raw_L/R (-1 = none).
    float raw_L[MAX_IR] = {};
    float raw_R[MAX_IR] = {};
    int   raw_len       = 0;
    int   loaded_ir_idx = -1;  // bg thread only

    // Current IR index for display (atomic so draw thread can read safely)
    std::atomic<int> cur_ir_idx{38};

    // Double-buffered convolution engines.
    // conv[live]   -- always processing input, always producing output.
    // conv[1-live] -- either producing output (safe_old=true) or being rebuilt (safe_old=false).
    PartitionedConvolution conv[2];
    int  live = 0;                        // audio thread only

    // Background rebuild coordination
    std::atomic<int>  pending{-1};        // set to target index when rebuild completes
    std::atomic<bool> building{false};    // true while thread is running
    std::atomic<bool> safe_old{false};    // true = conv[1-live] is safe for audio thread to push
    std::thread       builder;

    // Crossfade position (audio thread only).
    // -1 = not crossfading; 0..BLOCK-1 = fading from old engine to new.
    int xf_pos = -1;

    // Pre-delay buffers
    float pre_L[MAX_PRE] = {};
    float pre_R[MAX_PRE] = {};
    int   pre_pos = 0;

    // TONE filter state
    float tone_L = 0.f, tone_R = 0.f;

    // Change detection (audio thread only)
    float last_time = -1.f, last_bend = -999.f;
    int   last_ir   = -1;

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

        conv[0].init();
        conv[1].init();
        // Initial load: synchronous (no thread needed at startup)
        loadIRFromFile(38);
        doLoad(0, 0.5f, 0.f);
        last_time = 0.5f;
        last_bend = 0.f;
        last_ir   = 38;
    }

    ~Saphire() {
        // Must join before the conv[] arrays are destroyed
        if (builder.joinable()) builder.join();
    }

    // Load IR from res/ir/NN.f32 into raw_L/R. Called from bg thread (or constructor).
    // The .f32 files are already normalized to unit energy by convert_irs.py.
    void loadIRFromFile(int idx) {
        char name[32];
        snprintf(name, sizeof(name), "res/ir/%02d.f32", idx);
        std::string path = asset::plugin(pluginInstance, name);
        FILE* f = fopen(path.c_str(), "rb");
        if (!f) return;

        float buf[2];
        raw_len = 0;
        for (int i = 0; i < MAX_IR; i++) {
            if (fread(buf, sizeof(float), 2, f) < 2) break;
            raw_L[i] = buf[0];
            raw_R[i] = buf[1];
            raw_len++;
        }
        fclose(f);
        loaded_ir_idx = idx;
    }

    // Compute warp and load into conv[target]. Called from any thread.
    // Reads raw_L/raw_R (immutable after loadIR) -- safe.
    void doLoad(int target, float time_p, float bend_p) {
        int wlen = (int)(BLOCK + (raw_len - BLOCK) * time_p);
        wlen = std::max(BLOCK, std::min(raw_len, wlen));

        // BEND: power-law warp  h'[n] = raw[t^beta * (raw_len-1)]
        //   bend<0 → beta<1 → pulls energy forward
        //   bend=0 → beta=1 → identity
        //   bend>0 → beta>1 → smears energy into tail
        float beta = std::exp(bend_p * std::log(3.f));
        float N    = (float)(raw_len - 1);

        std::vector<float> wL(wlen), wR(wlen);
        for (int n = 0; n < wlen; n++) {
            float t  = (wlen > 1) ? (float)n / (float)(wlen - 1) : 0.f;
            float tw = std::pow(t, beta);
            float src = tw * N;
            int   s0  = (int)src;
            float fr  = src - (float)s0;
            int   s1  = std::min(s0 + 1, raw_len - 1);
            wL[n] = raw_L[s0] * (1.f - fr) + raw_L[s1] * fr;
            wR[n] = raw_R[s0] * (1.f - fr) + raw_R[s1] * fr;
        }

        conv[target].load(wL.data(), wR.data(), wlen);
    }

    // Launch a background thread to rebuild the inactive engine.
    // If a rebuild is already running the call is a no-op -- the change
    // will be detected again next process() and retried.
    void launchRebuild(int ir_idx, float time_p, float bend_p) {
        if (building.exchange(true)) return;   // already in progress
        safe_old.store(false);                 // stop pushing to non-live while it rebuilds
        if (builder.joinable()) builder.join();

        last_time = time_p;
        last_bend = bend_p;
        last_ir   = ir_idx;
        int target = 1 - live;

        builder = std::thread([this, ir_idx, time_p, bend_p, target]() {
            if (ir_idx != loaded_ir_idx)
                loadIRFromFile(ir_idx);
            doLoad(target, time_p, bend_p);
            cur_ir_idx.store(ir_idx);
            pending.store(target);
            building.store(false);
        });
    }

    void process(const ProcessArgs& args) override {
        float mix_p  = params[MIX_PARAM].getValue();
        float time_p = params[TIME_PARAM].getValue();
        float bend_p = params[BEND_PARAM].getValue();
        float tone_p = params[TONE_PARAM].getValue();
        float pre_p  = params[PRE_PARAM].getValue();

        // Check for a completed rebuild -- swap engines, start crossfade
        int p = pending.load();
        if (p >= 0) {
            pending.store(-1);
            live   = p;
            xf_pos = 0;
            safe_old.store(true);   // old engine (1-live) safe for audio thread to push
        }

        int ir_idx = (int)std::round(params[IR_PARAM].getValue());
        ir_idx = std::max(0, std::min(IR_COUNT - 1, ir_idx));

        // Detect any change and launch rebuild (no-op if already building)
        if (ir_idx != last_ir ||
            std::fabs(time_p - last_time) > 0.001f ||
            std::fabs(bend_p - last_bend) > 0.001f) {
            launchRebuild(ir_idx, time_p, bend_p);
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
        int pre_samp = (int)(pre_p * (MAX_PRE - 1));
        pre_L[pre_pos] = in_L;
        pre_R[pre_pos] = in_R;
        int pr = (pre_pos - pre_samp + MAX_PRE) % MAX_PRE;
        float dl_L = pre_L[pr];
        float dl_R = pre_R[pr];
        pre_pos = (pre_pos + 1) % MAX_PRE;

        // Push to live engine; push to old engine only during crossfade (safe_old=true)
        float wet_L, wet_R;
        float old_L = 0.f, old_R = 0.f;
        conv[live].push(dl_L, dl_R, wet_L, wet_R);
        if (safe_old.load()) {
            conv[1 - live].push(dl_L, dl_R, old_L, old_R);
        }

        // Crossfade: blend old engine's live output with new engine's live output
        if (xf_pos >= 0) {
            float alpha = (float)xf_pos / (float)BLOCK;
            wet_L = old_L * (1.f - alpha) + wet_L * alpha;
            wet_R = old_R * (1.f - alpha) + wet_R * alpha;
            if (++xf_pos >= BLOCK) {
                xf_pos = -1;
                safe_old.store(false);  // crossfade done, old engine no longer needed
            }
        }

        // TONE: one-pole lowpass on wet signal
        float lp_fc = 100.f * std::pow(200.f, tone_p);
        float lp_g  = 1.f - std::exp(-2.f * float(M_PI) * lp_fc / args.sampleRate);
        tone_L += lp_g * (wet_L - tone_L);
        tone_R += lp_g * (wet_R - tone_R);

        // MIX: constant-power crossfade
        AgentRack::Signal::Audio::ConstantPowerMix mix(mix_p);
        float out_L = in_L * mix.dryGain() + tone_L * mix.wetGain();
        float out_R = in_R * mix.dryGain() + tone_R * mix.wetGain();
        outputs[OUT_L_OUTPUT].setVoltage(AgentRack::Signal::Audio::toRackVolts(out_L));
        outputs[OUT_R_OUTPUT].setVoltage(AgentRack::Signal::Audio::toRackVolts(out_R));
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

        int idx = module->cur_ir_idx.load();
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
        int imgHandle = 0;
        try {
            auto img = APP->window->loadImage(
                asset::plugin(pluginInstance, "res/Saphire-bg.jpg"));
            if (img) imgHandle = img->handle;
        } catch (...) {}

        if (imgHandle > 0) {
            NVGpaint paint = nvgImagePattern(
                args.vg, 0, 0, box.size.x, box.size.y,
                0.f, imgHandle, 1.f);
            nvgBeginPath(args.vg);
            nvgRect(args.vg, 0, 0, box.size.x, box.size.y);
            nvgFillPaint(args.vg, paint);
            nvgFill(args.vg);
        } else {
            nvgBeginPath(args.vg);
            nvgRect(args.vg, 0, 0, box.size.x, box.size.y);
            nvgFillColor(args.vg, nvgRGB(15, 15, 25));
            nvgFill(args.vg);
        }

        // Dark top bar + title
        nvgBeginPath(args.vg);
        nvgRect(args.vg, 0, 0, box.size.x, 20.f);
        nvgFillColor(args.vg, nvgRGBA(0, 0, 0, 200));
        nvgFill(args.vg);

        nvgFontSize(args.vg, 7.f);
        nvgTextAlign(args.vg, NVG_ALIGN_CENTER | NVG_ALIGN_MIDDLE);
        nvgFillColor(args.vg, nvgRGB(255, 255, 255));
        nvgText(args.vg, box.size.x / 2.f, 10.f, "SPH", NULL);
    }
};


// ---------------------------------------------------------------------------
// Widget -- 8HP
// ---------------------------------------------------------------------------

struct SaphireWidget : rack::ModuleWidget {

    SaphireWidget(Saphire* module) {
        setModule(module);

        auto* panel = new SaphirePanel;
        panel->box.size = Vec(8.f * RACK_GRID_WIDTH, RACK_GRID_HEIGHT);
        addChild(panel);
        box.size = panel->box.size;

        addChild(createWidget<ThemedScrew>(Vec(1 * RACK_GRID_WIDTH, 0)));
        addChild(createWidget<ThemedScrew>(Vec(6 * RACK_GRID_WIDTH, 0)));
        addChild(createWidget<ThemedScrew>(Vec(1 * RACK_GRID_WIDTH, RACK_GRID_HEIGHT - RACK_GRID_WIDTH)));
        addChild(createWidget<ThemedScrew>(Vec(6 * RACK_GRID_WIDTH, RACK_GRID_HEIGHT - RACK_GRID_WIDTH)));

        float cx = 20.32f;
        float L  = cx - 8.f;
        float R  = cx + 8.f;

        // MIX -- large, centered
        addParam(createParamCentered<rack::RoundBigBlackKnob>(
            mm2px(rack::Vec(cx, 24.f)), module, Saphire::MIX_PARAM));
        // TIME left, BEND right -- medium
        addParam(createParamCentered<rack::RoundBlackKnob>(
            mm2px(rack::Vec(L, 41.f)), module, Saphire::TIME_PARAM));
        addParam(createParamCentered<rack::RoundBlackKnob>(
            mm2px(rack::Vec(R, 41.f)), module, Saphire::BEND_PARAM));
        // TONE left, PRE right -- small
        addParam(createParamCentered<rack::RoundSmallBlackKnob>(
            mm2px(rack::Vec(L, 55.f)), module, Saphire::TONE_PARAM));
        addParam(createParamCentered<rack::RoundSmallBlackKnob>(
            mm2px(rack::Vec(R, 55.f)), module, Saphire::PRE_PARAM));

        // IR display (full-width label)
        auto* disp = new IRDisplay;
        disp->module = module;
        disp->box.pos  = mm2px(rack::Vec(3.f, 63.f));
        disp->box.size = mm2px(rack::Vec(34.64f, 6.5f));
        addChild(disp);

        // IR selector -- snap knob, centered
        addParam(createParamCentered<rack::RoundBlackKnob>(
            mm2px(rack::Vec(cx, 76.f)), module, Saphire::IR_PARAM));

        // IN L/R
        addInput(createInputCentered<rack::PJ301MPort>(
            mm2px(rack::Vec(L, 90.f)), module, Saphire::IN_L_INPUT));
        addInput(createInputCentered<rack::PJ301MPort>(
            mm2px(rack::Vec(R, 90.f)), module, Saphire::IN_R_INPUT));

        // OUT L/R
        addOutput(createOutputCentered<rack::PJ301MPort>(
            mm2px(rack::Vec(L, 107.f)), module, Saphire::OUT_L_OUTPUT));
        addOutput(createOutputCentered<rack::PJ301MPort>(
            mm2px(rack::Vec(R, 107.f)), module, Saphire::OUT_R_OUTPUT));
    }
};


rack::Model* modelSaphire = createModel<Saphire, SaphireWidget>("Saphire");
