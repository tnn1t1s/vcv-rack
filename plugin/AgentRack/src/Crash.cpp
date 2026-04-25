#include <rack.hpp>
#include "AgentModule.hpp"
#include "PanelLayout.hpp"
#include "TR909VoiceCommon.hpp"
#include "agentrack/signal/Audio.hpp"
#include "embedded/Crash909Data.hpp"
#include <cmath>

using namespace rack;
extern Plugin* pluginInstance;

/**
 * Crash -- TR-909 style crash cymbal.
 *
 * Like the ride and hats, this voice starts from an embedded clean 909 PCM hit
 * and recreates the editable part of the instrument in code:
 *
 *   embedded PCM source -> sample-rate tune -> LPF(tone/Q) -> HPF -> VCA
 *   -> soft drive -> output level
 *
 * The module is deliberately documented inline so the DSP structure remains
 * understandable without having to maintain parallel prose elsewhere.
 *
 * Rack IDs (stable):
 *   Params:  TUNE=0, DECAY=1, TONE=2, HPF=3, Q=4, DRIVE=5, LEVEL=6
 *   Inputs:  TRIG=0, TUNE_CV=1, DECAY_CV=2, TONE_CV=3, HPF_CV=4,
 *            Q_CV=5, DRIVE_CV=6, LEVEL_CV=7
 *   Outputs: OUT=0
 */

namespace {
static constexpr float CRASH_SAMPLE_RATE   = 44100.f;
static constexpr float CRASH_TUNE_OCTAVES  = 0.8f;
static constexpr float CRASH_DECAY_MIN_SEC = 0.25f;
static constexpr float CRASH_DECAY_MAX_SEC = 3.80f;
static constexpr float CRASH_TONE_MIN_HZ   = 2200.f;
static constexpr float CRASH_TONE_MAX_HZ   = 17000.f;
static constexpr float CRASH_HPF_MIN_HZ    = 140.f;
static constexpr float CRASH_HPF_MAX_HZ    = 5000.f;
static constexpr float CRASH_Q_MIN         = 0.60f;
static constexpr float CRASH_Q_MAX         = 2.50f;

static const std::vector<float>& crashSource() {
    static const std::vector<float> sample =
        AgentRack::TR909::decodeEmbeddedF32(crash909_f32, crash909_f32_len);
    return sample;
}
}

struct Crash : AgentModule {
    enum ParamId {
        TUNE_PARAM, DECAY_PARAM, TONE_PARAM, HPF_PARAM,
        Q_PARAM, DRIVE_PARAM, LEVEL_PARAM,
        NUM_PARAMS
    };
    enum InputId {
        TRIG_INPUT, TUNE_CV_INPUT, DECAY_CV_INPUT, TONE_CV_INPUT,
        HPF_CV_INPUT, Q_CV_INPUT, DRIVE_CV_INPUT, LEVEL_CV_INPUT,
        NUM_INPUTS
    };
    enum OutputId { OUT_OUTPUT, NUM_OUTPUTS };

    dsp::SchmittTrigger trigger;
    float samplePos = 0.f;
    float env = 0.f;
    AgentRack::TR909::TptSVF lp;
    AgentRack::TR909::TptSVF hp;

    Crash() {
        config(NUM_PARAMS, NUM_INPUTS, NUM_OUTPUTS);
        configParam(TUNE_PARAM,  0.f, 1.f, 0.50f, "Tune",  "%", 0.f, 100.f);
        configParam(DECAY_PARAM, 0.f, 1.f, 0.58f, "Decay", "%", 0.f, 100.f);
        configParam(TONE_PARAM,  0.f, 1.f, 0.68f, "Tone",  "%", 0.f, 100.f);
        configParam(HPF_PARAM,   0.f, 1.f, 0.12f, "HPF",   "%", 0.f, 100.f);
        configParam(Q_PARAM,     0.f, 1.f, 0.18f, "Q",     "%", 0.f, 100.f);
        configParam(DRIVE_PARAM, 0.f, 1.f, 0.10f, "Drive", "%", 0.f, 100.f);
        configParam(LEVEL_PARAM, 0.f, 1.f, 0.82f, "Level", "%", 0.f, 100.f);
        configInput(TRIG_INPUT,      "Trigger");
        configInput(TUNE_CV_INPUT,   "Tune CV");
        configInput(DECAY_CV_INPUT,  "Decay CV");
        configInput(TONE_CV_INPUT,   "Tone CV");
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
            lp.reset();
            hp.reset();
        }

        float tuneNorm  = AgentRack::TR909::normWithCV(*this, TUNE_PARAM,  TUNE_CV_INPUT);
        float decayNorm = AgentRack::TR909::normWithCV(*this, DECAY_PARAM, DECAY_CV_INPUT);
        float toneNorm  = AgentRack::TR909::normWithCV(*this, TONE_PARAM,  TONE_CV_INPUT);
        float hpfNorm   = AgentRack::TR909::normWithCV(*this, HPF_PARAM,   HPF_CV_INPUT);
        float qNorm     = AgentRack::TR909::normWithCV(*this, Q_PARAM,     Q_CV_INPUT);
        float driveNorm = AgentRack::TR909::normWithCV(*this, DRIVE_PARAM, DRIVE_CV_INPUT);
        float levelNorm = AgentRack::TR909::normWithCV(*this, LEVEL_PARAM, LEVEL_CV_INPUT);

        float playbackRate = std::pow(2.f, (tuneNorm - 0.5f) * 2.f * CRASH_TUNE_OCTAVES);
        float decaySec = CRASH_DECAY_MIN_SEC + decayNorm * (CRASH_DECAY_MAX_SEC - CRASH_DECAY_MIN_SEC);
        float toneHz = CRASH_TONE_MIN_HZ + toneNorm * (CRASH_TONE_MAX_HZ - CRASH_TONE_MIN_HZ);
        float hpfHz = CRASH_HPF_MIN_HZ + hpfNorm * (CRASH_HPF_MAX_HZ - CRASH_HPF_MIN_HZ);
        float q = CRASH_Q_MIN + qNorm * (CRASH_Q_MAX - CRASH_Q_MIN);

        const auto& sample = crashSource();
        float source = AgentRack::TR909::sampleAt(sample, samplePos);
        samplePos += AgentRack::TR909::playbackStep(CRASH_SAMPLE_RATE, args.sampleRate, playbackRate);

        env *= std::exp(-args.sampleTime / decaySec);
        lp.process(source,
                   AgentRack::TR909::clampFilterHz(toneHz, args.sampleRate),
                   args.sampleRate, q);
        hp.process(lp.lpf,
                   AgentRack::TR909::clampFilterHz(hpfHz, args.sampleRate),
                   args.sampleRate, 0.7071f);

        float out = hp.hpf * env * 1.08f;
        out = AgentRack::TR909::drive(out, driveNorm);
        out *= levelNorm * 0.90f;
        outputs[OUT_OUTPUT].setVoltage(AgentRack::Signal::Audio::toRackVolts(out));
    }
};

struct CrashPanel : rack::widget::Widget {
    void draw(const DrawArgs& args) override {
        AgentLayout::drawAssetPanel(
            args.vg, box.size, pluginInstance,
            "res/Crash-bg.jpg",
            nvgRGB(28, 18, 12),
            "CRH", nvgRGB(255, 205, 140));

        static const char* const labels[] = {
            "TUNE", "DECAY", "TONE", "HPF", "Q", "DRIVE", "LEVEL",
        };
        nvgFontSize(args.vg, 5.5f);
        nvgFillColor(args.vg, nvgRGBA(245, 220, 180, 185));
        nvgTextAlign(args.vg, NVG_ALIGN_CENTER | NVG_ALIGN_MIDDLE);
        for (int i = 0; i < 7; i++) {
            nvgText(args.vg, mm2px(AgentLayout::CENTER_12HP),
                    mm2px(AgentLayout::ROW_Y_8[i]), labels[i], nullptr);
        }
    }
};

struct CrashWidget : rack::ModuleWidget {
    CrashWidget(Crash* module) {
        setModule(module);
        auto* panel = new CrashPanel;
        panel->box.size = AgentLayout::panelSize_12HP();
        addChild(panel);
        box.size = panel->box.size;
        AgentLayout::addScrews_12HP(this);

        const float knobX = AgentLayout::LEFT_COLUMN_12HP;
        const float jackX = AgentLayout::RIGHT_COLUMN_12HP;
        const float* ys = AgentLayout::ROW_Y_8;
        struct Row { int param; int input; };
        Row rows[7] = {
            {Crash::TUNE_PARAM,  Crash::TUNE_CV_INPUT},
            {Crash::DECAY_PARAM, Crash::DECAY_CV_INPUT},
            {Crash::TONE_PARAM,  Crash::TONE_CV_INPUT},
            {Crash::HPF_PARAM,   Crash::HPF_CV_INPUT},
            {Crash::Q_PARAM,     Crash::Q_CV_INPUT},
            {Crash::DRIVE_PARAM, Crash::DRIVE_CV_INPUT},
            {Crash::LEVEL_PARAM, Crash::LEVEL_CV_INPUT},
        };
        for (int i = 0; i < 7; i++) {
            addParam(createParamCentered<rack::RoundBlackKnob>(mm2px(Vec(knobX, ys[i])), module, rows[i].param));
            addInput(createInputCentered<rack::PJ301MPort>(mm2px(Vec(jackX, ys[i])), module, rows[i].input));
        }
        addInput(createInputCentered<rack::PJ301MPort>(mm2px(Vec(knobX, ys[7])), module, Crash::TRIG_INPUT));
        addOutput(createOutputCentered<rack::PJ301MPort>(mm2px(Vec(jackX, ys[7])), module, Crash::OUT_OUTPUT));
    }
};

rack::Model* modelCrash = createModel<Crash, CrashWidget>("Crash");
