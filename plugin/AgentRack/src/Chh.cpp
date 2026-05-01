#include <rack.hpp>
#include "AgentModule.hpp"
#include "PanelLayout.hpp"
#include "TR909VoiceCommon.hpp"
#include "agentrack/signal/Audio.hpp"
#include "embedded/Chh909Data.hpp"
#include <cmath>

using namespace rack;
extern Plugin* pluginInstance;

/**
 * Chh -- TR-909 style closed hi-hat.
 *
 * This module now uses an embedded clean closed-hat capture as the fixed PCM
 * source and keeps the control path intentionally simple:
 *
 *   embedded PCM source -> playback-rate tuning -> shortening VCA
 *   -> soft drive -> output level
 *
 * The important design choice is that the source stays static while the
 * control stage only shortens or trims the captured hat. We are not trying to
 * synthesize extra metallic tail beyond what is already in the ROM capture.
 *
 * Rack IDs (stable):
 *   Params:  TUNE=0, DECAY=1, BPF=2, HPF=3, Q=4, DRIVE=5, LEVEL=6
 *   Inputs:  TRIG=0, TUNE_CV=1, DECAY_CV=2, BPF_CV=3, HPF_CV=4,
 *            Q_CV=5, DRIVE_CV=6, LEVEL_CV=7
 *   Outputs: OUT=0
 */

namespace {
static constexpr float CHH_TUNE_OCTAVES  = 1.0f;
static constexpr float CHH_DECAY_MIN_SEC = 0.010f;
static constexpr float CHH_DECAY_MAX_SEC = 0.16f;

static const std::vector<float>& chhSource() {
    static const std::vector<float> sample =
        AgentRack::TR909::decodeEmbeddedF32(chh909_f32, chh909_f32_len);
    return sample;
}
}

struct Chh : AgentModule {
    enum ParamId {
        TUNE_PARAM, DECAY_PARAM, BPF_PARAM, HPF_PARAM,
        Q_PARAM, DRIVE_PARAM, LEVEL_PARAM,
        NUM_PARAMS
    };
    enum InputId {
        TRIG_INPUT, TUNE_CV_INPUT, DECAY_CV_INPUT, BPF_CV_INPUT,
        HPF_CV_INPUT, Q_CV_INPUT, DRIVE_CV_INPUT, LEVEL_CV_INPUT,
        NUM_INPUTS
    };
    enum OutputId { OUT_OUTPUT, NUM_OUTPUTS };

    dsp::SchmittTrigger trigger;
    float samplePos = 0.f;
    float env = 0.f;
    int dbgBitDepth = 16;

    Chh() {
        config(NUM_PARAMS, NUM_INPUTS, NUM_OUTPUTS);
        configParam(TUNE_PARAM,  0.f, 1.f, 0.50f, "Tune",  "%", 0.f, 100.f);
        configParam(DECAY_PARAM, 0.f, 1.f, 0.22f, "Decay", "%", 0.f, 100.f);
        configParam(BPF_PARAM,   0.f, 1.f, 0.58f, "BPF",   "%", 0.f, 100.f);
        configParam(HPF_PARAM,   0.f, 1.f, 0.46f, "HPF",   "%", 0.f, 100.f);
        configParam(Q_PARAM,     0.f, 1.f, 0.30f, "Q",     "%", 0.f, 100.f);
        configParam(DRIVE_PARAM, 0.f, 1.f, 0.10f, "Drive", "%", 0.f, 100.f);
        configParam(LEVEL_PARAM, 0.f, 1.f, 0.84f, "Level", "%", 0.f, 100.f);
        configInput(TRIG_INPUT,      "Trigger");
        configInput(TUNE_CV_INPUT,   "Tune CV");
        configInput(DECAY_CV_INPUT,  "Decay CV");
        configInput(BPF_CV_INPUT,    "BPF CV");
        configInput(HPF_CV_INPUT,    "HPF CV");
        configInput(Q_CV_INPUT,      "Q CV");
        configInput(DRIVE_CV_INPUT,  "Drive CV");
        configInput(LEVEL_CV_INPUT,  "Level CV");
        configOutput(OUT_OUTPUT,     "Audio");
    }

    void process(const ProcessArgs& args) override {
        if (trigger.process(inputs[TRIG_INPUT].getVoltage(), 0.1f, 2.f)) {
            samplePos = 0.f;
            env = 1.f;
        }

        float tuneNorm  = AgentRack::TR909::normWithCV(*this, TUNE_PARAM,  TUNE_CV_INPUT);
        float decayNorm = AgentRack::TR909::normWithCV(*this, DECAY_PARAM, DECAY_CV_INPUT);
        float bpfNorm   = AgentRack::TR909::normWithCV(*this, BPF_PARAM,   BPF_CV_INPUT);
        float hpfNorm   = AgentRack::TR909::normWithCV(*this, HPF_PARAM,   HPF_CV_INPUT);
        float qNorm     = AgentRack::TR909::normWithCV(*this, Q_PARAM,     Q_CV_INPUT);
        float driveNorm = AgentRack::TR909::normWithCV(*this, DRIVE_PARAM, DRIVE_CV_INPUT);
        float levelNorm = AgentRack::TR909::normWithCV(*this, LEVEL_PARAM, LEVEL_CV_INPUT);
        (void) bpfNorm;
        (void) hpfNorm;
        (void) qNorm;

        float playbackRate = std::pow(2.f, (tuneNorm - 0.5f) * 2.f * CHH_TUNE_OCTAVES);
        float decayShape = std::sqrt(decayNorm);
        float decaySec = CHH_DECAY_MIN_SEC + decayShape * (CHH_DECAY_MAX_SEC - CHH_DECAY_MIN_SEC);

        const auto& sample = chhSource();
        float source = AgentRack::TR909::sampleAt(sample, samplePos);
        samplePos += AgentRack::TR909::playbackStep(AgentRack::TR909::kEmbeddedPcmSampleRate, args.sampleRate, playbackRate);

        env *= std::exp(-args.sampleTime / decaySec);
        float out = source * env * 1.04f;
        out = AgentRack::TR909::bitReduce(out, dbgBitDepth);
        out = AgentRack::TR909::drive(out, driveNorm);
        out *= levelNorm * 0.94f;
        outputs[OUT_OUTPUT].setVoltage(AgentRack::Signal::Audio::toRackVolts(out));
    }
};

struct ChhPanel : rack::widget::Widget {
    void draw(const DrawArgs& args) override {
        AgentLayout::drawAssetPanel(
            args.vg, box.size, pluginInstance,
            "res/Chh-bg.jpg",
            nvgRGB(16, 24, 28),
            "CHH", nvgRGB(200, 230, 240));

        static const char* const labels[] = {
            "TUNE", "DECAY", "BPF", "HPF", "Q", "DRIVE", "LEVEL",
        };
        nvgFontSize(args.vg, 5.5f);
        nvgFillColor(args.vg, nvgRGBA(220, 235, 240, 180));
        nvgTextAlign(args.vg, NVG_ALIGN_CENTER | NVG_ALIGN_MIDDLE);
        for (int i = 0; i < 7; i++) {
            nvgText(args.vg, mm2px(AgentLayout::CENTER_12HP),
                    mm2px(AgentLayout::ROW_Y_8[i]), labels[i], nullptr);
        }
    }
};

struct ChhWidget : rack::ModuleWidget {
    ChhWidget(Chh* module) {
        setModule(module);
        auto* panel = new ChhPanel;
        panel->box.size = AgentLayout::panelSize_12HP();
        addChild(panel);
        box.size = panel->box.size;
        AgentLayout::addScrews_12HP(this);

        const float knobX = AgentLayout::LEFT_COLUMN_12HP;
        const float jackX = AgentLayout::RIGHT_COLUMN_12HP;
        const float* ys = AgentLayout::ROW_Y_8;
        struct Row { int param; int input; };
        Row rows[7] = {
            {Chh::TUNE_PARAM,  Chh::TUNE_CV_INPUT},
            {Chh::DECAY_PARAM, Chh::DECAY_CV_INPUT},
            {Chh::BPF_PARAM,   Chh::BPF_CV_INPUT},
            {Chh::HPF_PARAM,   Chh::HPF_CV_INPUT},
            {Chh::Q_PARAM,     Chh::Q_CV_INPUT},
            {Chh::DRIVE_PARAM, Chh::DRIVE_CV_INPUT},
            {Chh::LEVEL_PARAM, Chh::LEVEL_CV_INPUT},
        };
        for (int i = 0; i < 7; i++) {
            addParam(createParamCentered<rack::RoundBlackKnob>(mm2px(Vec(knobX, ys[i])), module, rows[i].param));
            addInput(createInputCentered<rack::PJ301MPort>(mm2px(Vec(jackX, ys[i])), module, rows[i].input));
        }
        addInput(createInputCentered<rack::PJ301MPort>(mm2px(Vec(knobX, ys[7])), module, Chh::TRIG_INPUT));
        addOutput(createOutputCentered<rack::PJ301MPort>(mm2px(Vec(jackX, ys[7])), module, Chh::OUT_OUTPUT));
    }
};

rack::Model* modelChh = createModel<Chh, ChhWidget>("Chh");
