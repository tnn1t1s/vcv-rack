#include <rack.hpp>
#include "AgentModule.hpp"
#include "PanelLayout.hpp"
#include "TR909VoiceCommon.hpp"
#include "agentrack/signal/Audio.hpp"
#include "embedded/Ride909Data.hpp"
#include <cmath>

using namespace rack;
extern Plugin* pluginInstance;

/**
 * Ride -- TR-909 style ride cymbal.
 *
 * The ride is handled here as a digital cymbal-family voice built from a
 * single embedded PCM hit and then reshaped in the analog domain:
 *
 *   embedded PCM source -> playback-rate tuning -> LPF(tone/Q) -> HPF -> VCA
 *   -> soft drive -> output level
 *
 * This is a pragmatic first pass: it uses a pristine capture from an original
 * 909 at the neutral tune position and keeps the important part editable in
 * the module itself rather than in external notes.
 *
 * Rack IDs (stable):
 *   Params:  TUNE=0, DECAY=1, TONE=2, HPF=3, Q=4, DRIVE=5, LEVEL=6
 *   Inputs:  TRIG=0, TUNE_CV=1, DECAY_CV=2, TONE_CV=3, HPF_CV=4,
 *            Q_CV=5, DRIVE_CV=6, LEVEL_CV=7
 *   Outputs: OUT=0
 */

namespace {
static constexpr float RIDE_SAMPLE_RATE   = 44100.f;
static constexpr float RIDE_TUNE_OCTAVES  = 0.7f;
static constexpr float RIDE_DECAY_MIN_SEC = 0.12f;
static constexpr float RIDE_DECAY_MAX_SEC = 4.80f;
static constexpr float RIDE_TONE_MIN_HZ   = 1800.f;
static constexpr float RIDE_TONE_MAX_HZ   = 16000.f;
static constexpr float RIDE_HPF_MIN_HZ    = 120.f;
static constexpr float RIDE_HPF_MAX_HZ    = 4200.f;
static constexpr float RIDE_Q_MIN         = 0.60f;
static constexpr float RIDE_Q_MAX         = 2.20f;

static const std::vector<float>& rideSource() {
    static const std::vector<float> sample =
        AgentRack::TR909::decodeEmbeddedF32(ride909_f32, ride909_f32_len);
    return sample;
}

static const AgentRack::TR909::RomTailAsset& rideAsset() {
    static const AgentRack::TR909::RomTailAsset asset =
        AgentRack::TR909::makeRomTailAsset(
            rideSource(),
            {
                RIDE_SAMPLE_RATE,
                0.10f, 0.42f,
                0.990f,
                640,
                0.080f,
                0.008f,
                5.0f,
                256
            });
    return asset;
}

static const AgentRack::TR909::RomTailVoiceConfig RIDE_ROM_CFG = {
    1.00f, 0.26f, 0.f, 0.020f, 0.96f
};
}

struct Ride : AgentModule {
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
    AgentRack::TR909::RomTailVoice voice;
    AgentRack::TR909::TptSVF lp;
    AgentRack::TR909::TptSVF hp;

    Ride() {
        config(NUM_PARAMS, NUM_INPUTS, NUM_OUTPUTS);
        configParam(TUNE_PARAM,  0.f, 1.f, 0.50f, "Tune",  "%", 0.f, 100.f);
        configParam(DECAY_PARAM, 0.f, 1.f, 0.65f, "Decay", "%", 0.f, 100.f);
        configParam(TONE_PARAM,  0.f, 1.f, 0.62f, "Tone",  "%", 0.f, 100.f);
        configParam(HPF_PARAM,   0.f, 1.f, 0.10f, "HPF",   "%", 0.f, 100.f);
        configParam(Q_PARAM,     0.f, 1.f, 0.18f, "Q",     "%", 0.f, 100.f);
        configParam(DRIVE_PARAM, 0.f, 1.f, 0.10f, "Drive", "%", 0.f, 100.f);
        configParam(LEVEL_PARAM, 0.f, 1.f, 0.80f, "Level", "%", 0.f, 100.f);
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
            voice.trigger();
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

        float playbackRate = std::pow(2.f, (tuneNorm - 0.5f) * 2.f * RIDE_TUNE_OCTAVES);
        float decaySec = RIDE_DECAY_MIN_SEC + decayNorm * (RIDE_DECAY_MAX_SEC - RIDE_DECAY_MIN_SEC);
        float toneHz = RIDE_TONE_MIN_HZ + toneNorm * (RIDE_TONE_MAX_HZ - RIDE_TONE_MIN_HZ);
        float hpfHz = RIDE_HPF_MIN_HZ + hpfNorm * (RIDE_HPF_MAX_HZ - RIDE_HPF_MIN_HZ);
        float q = RIDE_Q_MIN + qNorm * (RIDE_Q_MAX - RIDE_Q_MIN);

        float source = voice.process(args, rideAsset(), playbackRate, decaySec, decayNorm, RIDE_ROM_CFG);
        lp.process(source,
                   AgentRack::TR909::clampFilterHz(toneHz, args.sampleRate),
                   args.sampleRate, q);
        hp.process(lp.lpf,
                   AgentRack::TR909::clampFilterHz(hpfHz, args.sampleRate),
                   args.sampleRate, 0.7071f);

        float out = hp.hpf * 1.05f;
        out = AgentRack::TR909::drive(out, driveNorm);
        out *= levelNorm * 0.88f;
        outputs[OUT_OUTPUT].setVoltage(AgentRack::Signal::Audio::toRackVolts(out));
    }
};

struct RidePanel : rack::widget::Widget {
    void draw(const DrawArgs& args) override {
        AgentLayout::drawAssetPanel(
            args.vg, box.size, pluginInstance,
            "res/Ride-bg.jpg",
            nvgRGB(24, 24, 16),
            "RID", nvgRGB(245, 220, 120));

        static const char* const labels[] = {
            "TUNE", "DECAY", "TONE", "HPF", "Q", "DRIVE", "LEVEL",
        };
        nvgFontSize(args.vg, 5.5f);
        nvgFillColor(args.vg, nvgRGBA(240, 225, 180, 180));
        nvgTextAlign(args.vg, NVG_ALIGN_CENTER | NVG_ALIGN_MIDDLE);
        for (int i = 0; i < 7; i++) {
            nvgText(args.vg, mm2px(AgentLayout::CENTER_12HP),
                    mm2px(AgentLayout::ROW_Y_8[i]), labels[i], nullptr);
        }
    }
};

struct RideWidget : rack::ModuleWidget {
    RideWidget(Ride* module) {
        setModule(module);
        auto* panel = new RidePanel;
        panel->box.size = AgentLayout::panelSize_12HP();
        addChild(panel);
        box.size = panel->box.size;
        AgentLayout::addScrews_12HP(this);

        const float knobX = AgentLayout::LEFT_COLUMN_12HP;
        const float jackX = AgentLayout::RIGHT_COLUMN_12HP;
        const float* ys = AgentLayout::ROW_Y_8;
        struct Row { int param; int input; };
        Row rows[7] = {
            {Ride::TUNE_PARAM,  Ride::TUNE_CV_INPUT},
            {Ride::DECAY_PARAM, Ride::DECAY_CV_INPUT},
            {Ride::TONE_PARAM,  Ride::TONE_CV_INPUT},
            {Ride::HPF_PARAM,   Ride::HPF_CV_INPUT},
            {Ride::Q_PARAM,     Ride::Q_CV_INPUT},
            {Ride::DRIVE_PARAM, Ride::DRIVE_CV_INPUT},
            {Ride::LEVEL_PARAM, Ride::LEVEL_CV_INPUT},
        };
        for (int i = 0; i < 7; i++) {
            addParam(createParamCentered<rack::RoundBlackKnob>(mm2px(Vec(knobX, ys[i])), module, rows[i].param));
            addInput(createInputCentered<rack::PJ301MPort>(mm2px(Vec(jackX, ys[i])), module, rows[i].input));
        }
        addInput(createInputCentered<rack::PJ301MPort>(mm2px(Vec(knobX, ys[7])), module, Ride::TRIG_INPUT));
        addOutput(createOutputCentered<rack::PJ301MPort>(mm2px(Vec(jackX, ys[7])), module, Ride::OUT_OUTPUT));
    }
};

rack::Model* modelRide = createModel<Ride, RideWidget>("Ride");
