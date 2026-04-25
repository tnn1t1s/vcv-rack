#include <rack.hpp>
#include "AgentModule.hpp"
#include "PanelLayout.hpp"
#include "NineOhNinePanel.hpp"
#include "agentrack/signal/Audio.hpp"
#include <cmath>

using namespace rack;
extern Plugin* pluginInstance;

/**
 * Kck -- TR-909 inspired struck-resonator kick drum.
 *
 * The 909 kick is not a VCO+envelope patch.  It is a pulse that strikes a
 * high-Q bridged-T resonator; the body of the sound is the resonator ringing
 * down at its tuned frequency.  This module models that structure directly:
 *
 *   Body  : exponentially-decaying sine at f(t).  f(t) glides from
 *           f_tune * 2^(pitch_amt) down to f_tune over PITCH_DECAY.
 *           BodyAmp decays with tau = DECAY.
 *   Click : independent damped sine at 1.8 kHz with ~3 ms decay.  Sits in
 *           as the "attack transient" the way a bandpassed impulse does on
 *           the real 909 (no noise is involved).
 *   Drive : tanh saturator on the summed mix with makeup gain.
 *   Level : final gain.
 *
 * Every knob has a matching CV input at the same row.  TUNE CV is 1V/oct
 * (exponential); all other CVs are additive at 0.1 of knob range per volt.
 *
 * Rack IDs (stable, never reorder):
 *   Params:  TUNE=0, DECAY=1, PITCH=2, PITCH_DECAY=3, CLICK=4, DRIVE=5, LEVEL=6
 *   Inputs:  TRIG=0, TUNE_CV=1, DECAY_CV=2, PITCH_CV=3, PITCH_DECAY_CV=4,
 *            CLICK_CV=5, DRIVE_CV=6, LEVEL_CV=7
 *   Outputs: OUT=0
 */

static constexpr float TUNE_MIN_HZ    = 30.f;
static constexpr float TUNE_MAX_HZ    = 100.f;
static constexpr float DECAY_MIN_SEC  = 0.08f;
static constexpr float DECAY_MAX_SEC  = 1.50f;
static constexpr float PITCH_MAX_OCT  = 2.0f;
static constexpr float PDECAY_MIN_SEC = 0.005f;
static constexpr float PDECAY_MAX_SEC = 0.080f;
static constexpr float CLICK_FREQ_HZ  = 1800.f;
static constexpr float CLICK_TAU_SEC  = 0.003f;
static constexpr float CV_SCALE       = 0.1f;   // 0.1 of knob range per volt
static constexpr float TWO_PI = 6.28318530717958647692f;

// Returns params[param] + inputs[input]*CV_SCALE, clamped to [0, 1].
static inline float normWithCV(rack::Module& self,
                                int paramId, int inputId) {
    float norm = self.params[paramId].getValue()
               + self.inputs[inputId].getVoltage() * CV_SCALE;
    return rack::math::clamp(norm, 0.f, 1.f);
}


struct Kck : AgentModule {

    enum ParamId  {
        TUNE_PARAM, DECAY_PARAM, PITCH_PARAM, PITCH_DECAY_PARAM,
        CLICK_PARAM, DRIVE_PARAM, LEVEL_PARAM,
        NUM_PARAMS
    };
    enum InputId  {
        TRIG_INPUT, TUNE_CV_INPUT, DECAY_CV_INPUT, PITCH_CV_INPUT,
        PITCH_DECAY_CV_INPUT, CLICK_CV_INPUT, DRIVE_CV_INPUT, LEVEL_CV_INPUT,
        ACCENT_INPUT,
        NUM_INPUTS
    };
    enum OutputId { OUT_OUTPUT, NUM_OUTPUTS };

    dsp::SchmittTrigger trigger;

    float bodyPhase  = 0.f;
    float bodyAmp    = 0.f;
    float pitchEnv   = 0.f;
    float clickPhase = 0.f;
    float clickAmp   = 0.f;

    Kck() {
        config(NUM_PARAMS, NUM_INPUTS, NUM_OUTPUTS);
        configParam(TUNE_PARAM,         0.f, 1.f, 0.35f, "Tune",         "%", 0.f, 100.f);
        configParam(DECAY_PARAM,        0.f, 1.f, 0.55f, "Decay",        "%", 0.f, 100.f);
        configParam(PITCH_PARAM,        0.f, 1.f, 0.40f, "Pitch amount", "%", 0.f, 100.f);
        configParam(PITCH_DECAY_PARAM,  0.f, 1.f, 0.30f, "Pitch decay",  "%", 0.f, 100.f);
        configParam(CLICK_PARAM,        0.f, 1.f, 0.35f, "Click",        "%", 0.f, 100.f);
        configParam(DRIVE_PARAM,        0.f, 1.f, 0.20f, "Drive",        "%", 0.f, 100.f);
        configParam(LEVEL_PARAM,        0.f, 1.f, 0.85f, "Level",        "%", 0.f, 100.f);
        configInput (TRIG_INPUT,           "Trigger");
        configInput (TUNE_CV_INPUT,        "Tune CV (1V/oct)");
        configInput (DECAY_CV_INPUT,       "Decay CV");
        configInput (PITCH_CV_INPUT,       "Pitch amount CV");
        configInput (PITCH_DECAY_CV_INPUT, "Pitch decay CV");
        configInput (CLICK_CV_INPUT,       "Click CV");
        configInput (DRIVE_CV_INPUT,       "Drive CV");
        configInput (LEVEL_CV_INPUT,       "Level CV");
        configInput (ACCENT_INPUT,         "Accent");
        configOutput(OUT_OUTPUT,           "Audio");
    }

    void process(const ProcessArgs& args) override {
        // --- trigger -------------------------------------------------------
        if (trigger.process(inputs[TRIG_INPUT].getVoltage(), 0.1f, 2.f)) {
            bodyAmp    = 1.f;
            pitchEnv   = 1.f;
            clickAmp   = 1.f;
            bodyPhase  = 0.f;
            clickPhase = 0.f;
        }

        // --- param fetch + CV (all knob+CV sums clamped to 0..1) ----------
        float tune_norm = rack::math::clamp(params[TUNE_PARAM].getValue(), 0.f, 1.f);
        float tune_hz   = TUNE_MIN_HZ + tune_norm * (TUNE_MAX_HZ - TUNE_MIN_HZ);
        tune_hz *= std::pow(2.f, inputs[TUNE_CV_INPUT].getVoltage());  // 1V/oct

        float decay_norm  = normWithCV(*this, DECAY_PARAM,        DECAY_CV_INPUT);
        float pitch_norm  = normWithCV(*this, PITCH_PARAM,        PITCH_CV_INPUT);
        float pdecay_norm = normWithCV(*this, PITCH_DECAY_PARAM,  PITCH_DECAY_CV_INPUT);
        float click_norm  = normWithCV(*this, CLICK_PARAM,        CLICK_CV_INPUT);
        float drive_norm  = normWithCV(*this, DRIVE_PARAM,        DRIVE_CV_INPUT);
        float level_norm  = normWithCV(*this, LEVEL_PARAM,        LEVEL_CV_INPUT);

        float decay_sec  = DECAY_MIN_SEC  + decay_norm  * (DECAY_MAX_SEC  - DECAY_MIN_SEC);
        float pdecay_sec = PDECAY_MIN_SEC + pdecay_norm * (PDECAY_MAX_SEC - PDECAY_MIN_SEC);
        float pitch_amt  = pitch_norm * PITCH_MAX_OCT;

        // --- envelope decays (per-sample exponentials) --------------------
        bodyAmp   *= std::exp(-args.sampleTime / decay_sec);
        pitchEnv  *= std::exp(-args.sampleTime / pdecay_sec);
        clickAmp  *= std::exp(-args.sampleTime / CLICK_TAU_SEC);

        // --- body: damped sine with pitch-env swept frequency -------------
        float freq_now = tune_hz * std::pow(2.f, pitchEnv * pitch_amt);
        bodyPhase += TWO_PI * freq_now * args.sampleTime;
        if (bodyPhase > TWO_PI) bodyPhase -= TWO_PI;
        float body = std::sin(bodyPhase) * bodyAmp;

        // --- click: fixed-freq damped sine burst --------------------------
        clickPhase += TWO_PI * CLICK_FREQ_HZ * args.sampleTime;
        if (clickPhase > TWO_PI) clickPhase -= TWO_PI;
        float click = std::sin(clickPhase) * clickAmp;

        // --- mix + drive + level ------------------------------------------
        float mix = body + click * click_norm * 0.8f;
        if (drive_norm > 1e-4f) {
            float g = 1.f + drive_norm * 5.f;
            mix = std::tanh(mix * g) / std::sqrt(g);
        }
        float out = mix * level_norm;

        outputs[OUT_OUTPUT].setVoltage(
            AgentRack::Signal::Audio::toRackVolts(out));
    }
};


// ---------------------------------------------------------------------------
// Widget -- 909 family panel, 12HP
// ---------------------------------------------------------------------------

struct KckWidget : rack::ModuleWidget {
    KckWidget(Kck* module) {
        setModule(module);

        namespace P9 = AgentRack::NineOhNine;

        auto* panel = new P9::Panel;
        panel->voiceCode = "BD";
        panel->labels[0] = "TUNE";
        panel->labels[1] = "DECAY";
        panel->labels[2] = "PITCH";
        panel->labels[3] = "P DECAY";
        panel->labels[4] = "CLICK";
        panel->labels[5] = "DRIVE";
        panel->labels[6] = "LEVEL";
        panel->box.size = AgentLayout::panelSize_12HP();
        addChild(panel);
        box.size = panel->box.size;

        AgentLayout::addScrews_12HP(this);

        // Paired knob/jack layout: 6 params in 2 columns, LEVEL centered.
        struct Pair { int param; int cv; float x_mm; int row; };
        Pair pairs[6] = {
            {Kck::TUNE_PARAM,        Kck::TUNE_CV_INPUT,        P9::KNOB_L_X, 0},
            {Kck::DECAY_PARAM,       Kck::DECAY_CV_INPUT,       P9::KNOB_R_X, 0},
            {Kck::PITCH_PARAM,       Kck::PITCH_CV_INPUT,       P9::KNOB_L_X, 1},
            {Kck::PITCH_DECAY_PARAM, Kck::PITCH_DECAY_CV_INPUT, P9::KNOB_R_X, 1},
            {Kck::CLICK_PARAM,       Kck::CLICK_CV_INPUT,       P9::KNOB_L_X, 2},
            {Kck::DRIVE_PARAM,       Kck::DRIVE_CV_INPUT,       P9::KNOB_R_X, 2},
        };
        for (auto& p : pairs) {
            addParam(createParamCentered<rack::RoundBlackKnob>(
                mm2px(Vec(p.x_mm, P9::PAIR_Y[p.row][0])), module, p.param));
            addInput(createInputCentered<rack::PJ301MPort>(
                mm2px(Vec(p.x_mm, P9::PAIR_Y[p.row][1])), module, p.cv));
        }

        // LEVEL centered.
        addParam(createParamCentered<rack::RoundBlackKnob>(
            mm2px(Vec(AgentLayout::CENTER_12HP, P9::LEVEL_KNOB_Y)),
            module, Kck::LEVEL_PARAM));
        addInput(createInputCentered<rack::PJ301MPort>(
            mm2px(Vec(AgentLayout::CENTER_12HP, P9::LEVEL_JACK_Y)),
            module, Kck::LEVEL_CV_INPUT));

        // Bottom I/O strip.
        addInput(createInputCentered<rack::PJ301MPort>(
            mm2px(Vec(P9::IO_TRIG_X, P9::IO_JACK_Y)), module, Kck::TRIG_INPUT));
        addInput(createInputCentered<rack::PJ301MPort>(
            mm2px(Vec(P9::IO_ACCENT_X, P9::IO_JACK_Y)), module, Kck::ACCENT_INPUT));
        addOutput(createOutputCentered<rack::PJ301MPort>(
            mm2px(Vec(P9::IO_OUT_X, P9::IO_JACK_Y)), module, Kck::OUT_OUTPUT));
    }
};


rack::Model* modelKck = createModel<Kck, KckWidget>("Kck");
