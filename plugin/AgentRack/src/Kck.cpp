#include <rack.hpp>
#include "AgentModule.hpp"
#include "PanelLayout.hpp"
#include "NineOhNinePanel.hpp"
#include "agentrack/signal/Audio.hpp"
#include <cmath>
#include <cstdint>

using namespace rack;
extern Plugin* pluginInstance;

/**
 * Kck -- TR-909 inspired kick drum.
 *
 * Direct port of a known-passable JUCE 909 kick generator with all internal
 * model parameters exposed via `KckFit::Config`. Mirrors the `TomFit::Config`
 * pattern used by Toms.cpp so the voice_lab fitting workflow can sweep any
 * constant via `--param fit_<name>=<value>`.
 *
 * Per-sample algorithm (since trigger):
 *   basePitch  = basePitchOffset + tune * basePitchSpan
 *   ampDecay   = ampDecayMin - decay * ampDecaySpan         (1/tau)
 *   fastSweep  = (pitchSweepFastBase + attack * pitchSweepFastAttack)
 *                * exp(-(pitchSweepFastRateBase + attack * pitchSweepFastRateAttack)
 *                      * pitchDecayScale * t)
 *                * pitchAmpScale
 *   slowSweep  = pitchSweepSlowBase
 *                * exp(-(pitchSweepSlowRateBase + (1-decay) * pitchSweepSlowRateDecay) * t)
 *   freq       = basePitch + fastSweep + slowSweep
 *   body       = sin(phase) * bodyFundGain
 *              + sin(phase * bodyHarmRatio + bodyHarmPhase) * bodyHarmGain
 *   subDecay   = subDecayBase + (1-decay) * subDecayInverse
 *   sub        = sin(phaseSub) * subGain * exp(-subDecay * t)
 *   ampEnv     = exp(-ampDecay * t)
 *   clickRate  = clickRateBase + attack * clickRateAttack
 *   clickEnv   = exp(-clickRate * t)
 *   clickNoise = noise() * clickEnv * (clickNoiseBase + attack * clickNoiseAttack)
 *   clickChirp = sin(2pi * (clickChirpStartHz - t * clickChirpRate) * t) * clickEnv
 *                * (clickChirpBase + attack * clickChirpAttack)
 *   out        = (body + sub) * ampEnv + clickNoise + clickChirp
 *   out        = HP(out, hpCoef)
 *   drive      = driveBase + decay * driveDecay + attack * driveAttack
 *                + driveExtra * driveExtraSpan
 *   out        = tanh(out * drive)
 *   final      = clamp(out, -1, 1) * outputGain * level
 *
 * 'attack' is our CLICK knob (0..1).
 * 'pitchAmpScale' = pitch_norm * 2 lets PITCH knob scale fast-sweep magnitude.
 * 'pitchDecayScale' = 0.5 + pitch_decay_norm scales the fast-sweep decay rate.
 * 'driveExtra' is the DRIVE knob, adds saturation on top of the JUCE default.
 *
 * Rack IDs (stable, never reorder):
 *   Params:  TUNE=0, DECAY=1, PITCH=2, PITCH_DECAY=3, CLICK=4, DRIVE=5, LEVEL=6
 *   Inputs:  TRIG=0, TUNE_CV=1, DECAY_CV=2, PITCH_CV=3, PITCH_DECAY_CV=4,
 *            CLICK_CV=5, DRIVE_CV=6, LEVEL_CV=7, ACCENT=8
 *   Outputs: OUT=0
 */

namespace KckFit {

struct Config {
    // Pitch range (calibrated against TR-909 BD ref tune050-attack050-decay050 = 49.8 Hz).
    // basePitch midpoint 45 Hz; FFT measurement adds ~5 Hz from slow-sweep residual.
    float basePitchOffset           = 20.f;
    float basePitchSpan             = 50.f;

    // Body envelope (1/tau range), calibrated against TR-909 BD: -20 dB at 170 ms
    // (tau ~ 73 ms, ampDecay ~ 13.5) at decay=0.5. JUCE original 2.25/1.75 was 10x too slow.
    float ampDecayMin               = 20.f;    // decay=0 -> tau ~ 50 ms (snappy)
    float ampDecaySpan              = 13.f;    // decay=1 -> tau ~ 143 ms (long)

    // Fast pitch sweep. DAFx-14 paper §8.1 reports the real 909 attack
    // frequency shift lasts ~6 ms ("less than a single period at the higher
    // frequency"). JUCE's rate of 38 (tau ~26 ms) was 4x too slow, smearing
    // pitch energy into the 60-100 Hz band during the body window.
    float pitchSweepFastBase        = 112.f;    // Hz
    float pitchSweepFastAttack      = 65.f;
    float pitchSweepFastRateBase    = 150.f;    // 1/tau ~ 6.7 ms (was 38)
    float pitchSweepFastRateAttack  = 22.f;

    // Slow pitch sigh. DAFx-14 describes the 909's R161-leakage sigh as
    // "subtle". JUCE's 20 Hz / tau ~154 ms smeared the fundamental from ~58
    // down to ~46 Hz across the body window, putting a wandering 2H peak in
    // the 90-118 Hz region (audible as messy noise around 100 Hz).
    float pitchSweepSlowBase        = 8.f;      // (was 20)
    float pitchSweepSlowRateBase    = 15.f;     // 1/tau ~ 67 ms (was 6.5 / tau 154 ms)
    float pitchSweepSlowRateDecay   = 3.6f;     // additional rate at decay=0

    // Body harmonic content. The spectrum-faithful pass set bodyHarmGain=0.05
    // (matching ref 2H at -27 dB), but the artistic ear preferred the JUCE
    // value 0.19 for added body character. The 3H term remains as the analog
    // bite contribution.
    float bodyFundGain              = 0.88f;
    float bodyHarmRatio             = 2.02f;    // slightly detuned 2x for shimmer
    float bodyHarmPhase             = 0.10f;
    float bodyHarmGain              = 0.19f;    // ear-tuned: JUCE value
    float bodyThirdHarmGain         = 0.06f;

    // Sub-osc retained: spectrum-faithful pass disabled it (no sub-osc in real
    // circuit), but the artistic ear preferred the additional weight. Remains
    // a tunable knob in KckDbg if a circuit-faithful render is wanted.
    float subRatio                  = 0.50f;
    float subGain                   = 0.36f;    // ear-tuned: JUCE value
    float subDecayBase              = 0.85f;
    float subDecayInverse           = 0.45f;

    // Click. The 1700 Hz tonal chirp added a persistent "rimshot ping" on top
    // of the kick body even at half magnitude; the real 909 click is a brief
    // filtered noise burst, not a tonal transient. Chirp disabled by default
    // (still tweakable via dbg knobs / fit_*); noise reduced for cleaner attack.
    float clickRateBase             = 140.f;
    float clickRateAttack           = 170.f;
    float clickNoiseBase            = 0.03f;    // (was 0.05)
    float clickNoiseAttack          = 0.10f;    // (was 0.18)
    float clickChirpStartHz         = 1700.f;
    float clickChirpRate            = 400.f;
    float clickChirpBase            = 0.f;      // (was 0.02) chirp off by default
    float clickChirpAttack          = 0.f;      // (was 0.10)

    // HP cutoff: spectrum-faithful pass raised this to 0.005 (~35 Hz) to clean
    // sub mud, but the artistic ear preferred the JUCE value 0.0012 (~8 Hz)
    // which keeps more deep bass through.
    float hpCoef                    = 0.0012f;  // ear-tuned: JUCE value
    // Drive: spectrum-faithful pass set this to 1.0 to avoid intermod 2H, but
    // the artistic ear preferred the JUCE saturator at 1.55 for bite.
    float driveBase                 = 1.55f;    // ear-tuned: JUCE value
    float driveDecay                = 0.42f;
    float driveAttack               = 0.35f;
    float driveExtraSpan            = 1.0f;     // DRIVE knob 0..1 -> 0..1 added to drive amount

    // Output
    float outputGain                = 1.0f;
};

inline Config makeKick() { return Config{}; }

}  // namespace KckFit

namespace {

static constexpr float TWO_PI   = 6.28318530717958647692f;
static constexpr float CV_SCALE = 0.1f;

static inline float kckNormWithCV(rack::Module& self, int paramId, int inputId) {
    float norm = self.params[paramId].getValue()
               + self.inputs[inputId].getVoltage() * CV_SCALE;
    return rack::math::clamp(norm, 0.f, 1.f);
}

struct KckVoice {
    dsp::SchmittTrigger trigger;
    float phase    = 0.f;
    float phaseSub = 0.f;
    float t        = 0.f;
    float hpState  = 0.f;
    bool  active   = false;
    uint32_t rngState = 1u;

    void fire() {
        phase = phaseSub = 0.f;
        t = 0.f;
        hpState = 0.f;
        active = true;
        rngState = 1978u;  // mirrors JUCE's `juce::Random rng(1978)`
    }

    inline float nextNoise() {
        // Numerical Recipes LCG; map upper bits to [-1, 1).
        rngState = rngState * 1664525u + 1013904223u;
        return ((rngState >> 8) & 0xFFFFFFu) * (2.f / 16777216.f) - 1.f;
    }

    float process(const rack::Module::ProcessArgs& args,
                  const KckFit::Config& fit,
                  float tuneNorm,
                  float decayNorm,
                  float pitchNorm,
                  float pitchDecayNorm,
                  float attackNorm,
                  float driveNorm,
                  float levelNorm) {
        if (!active) return 0.f;

        const float basePitch = fit.basePitchOffset + tuneNorm * fit.basePitchSpan;
        const float ampDecay  = fit.ampDecayMin - decayNorm * fit.ampDecaySpan;

        const float pitchAmpScale   = pitchNorm * 2.f;
        const float pitchDecayScale = 0.5f + pitchDecayNorm;

        const float fastSweep =
            (fit.pitchSweepFastBase + attackNorm * fit.pitchSweepFastAttack)
            * std::exp(-(fit.pitchSweepFastRateBase
                         + attackNorm * fit.pitchSweepFastRateAttack)
                       * pitchDecayScale * t)
            * pitchAmpScale;

        const float slowSweep =
            fit.pitchSweepSlowBase
            * std::exp(-(fit.pitchSweepSlowRateBase
                         + (1.f - decayNorm) * fit.pitchSweepSlowRateDecay) * t);

        const float freq = basePitch + fastSweep + slowSweep;

        phase    += TWO_PI * freq * args.sampleTime;
        phaseSub += TWO_PI * (basePitch * fit.subRatio) * args.sampleTime;
        if (phase    > TWO_PI) phase    -= TWO_PI;
        if (phaseSub > TWO_PI) phaseSub -= TWO_PI;

        const float body =
            std::sin(phase) * fit.bodyFundGain
          + std::sin(phase * fit.bodyHarmRatio + fit.bodyHarmPhase) * fit.bodyHarmGain
          + std::sin(phase * 3.f) * fit.bodyThirdHarmGain;

        const float subDecay = fit.subDecayBase + (1.f - decayNorm) * fit.subDecayInverse;
        const float sub      = std::sin(phaseSub) * fit.subGain * std::exp(-subDecay * t);

        const float ampEnv   = std::exp(-ampDecay * t);

        const float clickRate = fit.clickRateBase + attackNorm * fit.clickRateAttack;
        const float clickEnv  = std::exp(-clickRate * t);

        const float clickNoise = nextNoise() * clickEnv
                               * (fit.clickNoiseBase + attackNorm * fit.clickNoiseAttack);

        const float chirpInstFreq = fit.clickChirpStartHz - t * fit.clickChirpRate;
        const float clickChirp = std::sin(TWO_PI * chirpInstFreq * t) * clickEnv
                               * (fit.clickChirpBase + attackNorm * fit.clickChirpAttack);

        float out = (body + sub) * ampEnv + clickNoise + clickChirp;

        // Leaky DC-blocking HP.
        hpState += fit.hpCoef * (out - hpState);
        out -= hpState;

        const float driveAmount =
            fit.driveBase
          + decayNorm  * fit.driveDecay
          + attackNorm * fit.driveAttack
          + driveNorm  * fit.driveExtraSpan;
        out = std::tanh(out * driveAmount);

        out = rack::math::clamp(out, -1.f, 1.f) * fit.outputGain * levelNorm;

        t += args.sampleTime;
        if (ampEnv < 1e-5f && t > 0.5f) active = false;

        return out;
    }
};

} // namespace


// ---------------------------------------------------------------------------
// Kck -- production module
// ---------------------------------------------------------------------------

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

    KckVoice voice;
    KckFit::Config fit;

    Kck() {
        fit = KckFit::makeKick();
        config(NUM_PARAMS, NUM_INPUTS, NUM_OUTPUTS);
        configParam(TUNE_PARAM,        0.f, 1.f, 0.50f,  "Tune",         "%", 0.f, 100.f);
        configParam(DECAY_PARAM,       0.f, 1.f, 0.50f,  "Decay",        "%", 0.f, 100.f);
        // PITCH and PITCH_DECAY defaults dialed in by ear against TR-909 BD ref:
        // amount 0.385 (=> sweep magnitude * 0.77) and decay 0.26 (=> rate * 0.76)
        // produce the most convincing "scooped, chest-pumping" attack character.
        configParam(PITCH_PARAM,       0.f, 1.f, 0.385f, "Pitch amount", "%", 0.f, 100.f);
        configParam(PITCH_DECAY_PARAM, 0.f, 1.f, 0.26f,  "Pitch decay",  "%", 0.f, 100.f);
        configParam(CLICK_PARAM,       0.f, 1.f, 0.50f, "Click",        "%", 0.f, 100.f);
        configParam(DRIVE_PARAM,       0.f, 1.f, 0.f,   "Drive",        "%", 0.f, 100.f);
        configParam(LEVEL_PARAM,       0.f, 1.f, 0.85f, "Level",        "%", 0.f, 100.f);
        configInput (TRIG_INPUT,           "Trigger");
        configInput (TUNE_CV_INPUT,        "Tune CV");
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
        if (voice.trigger.process(inputs[TRIG_INPUT].getVoltage(), 0.1f, 2.f)) {
            voice.fire();
        }

        float tuneNorm       = kckNormWithCV(*this, TUNE_PARAM,        TUNE_CV_INPUT);
        float decayNorm      = kckNormWithCV(*this, DECAY_PARAM,       DECAY_CV_INPUT);
        float pitchNorm      = kckNormWithCV(*this, PITCH_PARAM,       PITCH_CV_INPUT);
        float pitchDecayNorm = kckNormWithCV(*this, PITCH_DECAY_PARAM, PITCH_DECAY_CV_INPUT);
        float clickNorm      = kckNormWithCV(*this, CLICK_PARAM,       CLICK_CV_INPUT);
        float driveNorm      = kckNormWithCV(*this, DRIVE_PARAM,       DRIVE_CV_INPUT);
        float levelNorm      = kckNormWithCV(*this, LEVEL_PARAM,       LEVEL_CV_INPUT);

        float out = voice.process(args, fit,
                                  tuneNorm, decayNorm, pitchNorm, pitchDecayNorm,
                                  clickNorm, driveNorm, levelNorm);
        outputs[OUT_OUTPUT].setVoltage(AgentRack::Signal::Audio::toRackVolts(out));
    }
};


// ---------------------------------------------------------------------------
// Production widget -- 12HP, plain black background
// ---------------------------------------------------------------------------

struct KckPanel : rack::widget::Widget {
    void draw(const DrawArgs& args) override {
        namespace P9 = AgentRack::NineOhNine;

        // Solid black background.
        nvgBeginPath(args.vg);
        nvgRect(args.vg, 0.f, 0.f, box.size.x, box.size.y);
        nvgFillColor(args.vg, nvgRGB(8, 8, 10));
        nvgFill(args.vg);

        // Title "KCK" centred near the top.
        nvgFontSize(args.vg, 9.f);
        nvgFillColor(args.vg, nvgRGBA(230, 230, 240, 230));
        nvgTextAlign(args.vg, NVG_ALIGN_CENTER | NVG_ALIGN_MIDDLE);
        nvgText(args.vg, mm2px(AgentLayout::CENTER_12HP), mm2px(8.f), "KCK", nullptr);

        // Knob labels above each pair / centred level / IO row.
        nvgFontSize(args.vg, 5.0f);
        nvgFillColor(args.vg, nvgRGBA(200, 200, 215, 200));
        nvgTextAlign(args.vg, NVG_ALIGN_CENTER | NVG_ALIGN_MIDDLE);
        const float dy = -7.f;  // label offset above knob
        nvgText(args.vg, mm2px(P9::KNOB_L_X), mm2px(P9::PAIR_Y[0][0] + dy), "TUNE",    nullptr);
        nvgText(args.vg, mm2px(P9::KNOB_R_X), mm2px(P9::PAIR_Y[0][0] + dy), "DECAY",   nullptr);
        nvgText(args.vg, mm2px(P9::KNOB_L_X), mm2px(P9::PAIR_Y[1][0] + dy), "PITCH",   nullptr);
        nvgText(args.vg, mm2px(P9::KNOB_R_X), mm2px(P9::PAIR_Y[1][0] + dy), "P DECAY", nullptr);
        nvgText(args.vg, mm2px(P9::KNOB_L_X), mm2px(P9::PAIR_Y[2][0] + dy), "CLICK",   nullptr);
        nvgText(args.vg, mm2px(P9::KNOB_R_X), mm2px(P9::PAIR_Y[2][0] + dy), "DRIVE",   nullptr);
        nvgText(args.vg, mm2px(AgentLayout::CENTER_12HP), mm2px(P9::LEVEL_KNOB_Y + dy), "LEVEL", nullptr);

        // Bottom IO row labels.
        nvgFontSize(args.vg, 4.5f);
        nvgFillColor(args.vg, nvgRGBA(180, 180, 200, 180));
        const float ioLabelY = P9::IO_JACK_Y - 6.f;
        nvgText(args.vg, mm2px(P9::IO_TRIG_X),   mm2px(ioLabelY), "TRIG",   nullptr);
        nvgText(args.vg, mm2px(P9::IO_ACCENT_X), mm2px(ioLabelY), "ACCENT", nullptr);
        nvgText(args.vg, mm2px(P9::IO_OUT_X),    mm2px(ioLabelY), "OUT",    nullptr);
    }
};

struct KckWidget : rack::ModuleWidget {
    KckWidget(Kck* module) {
        setModule(module);

        namespace P9 = AgentRack::NineOhNine;

        auto* panel = new KckPanel;
        panel->box.size = AgentLayout::panelSize_12HP();
        addChild(panel);
        box.size = panel->box.size;

        AgentLayout::addScrews_12HP(this);

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

        addParam(createParamCentered<rack::RoundBlackKnob>(
            mm2px(Vec(AgentLayout::CENTER_12HP, P9::LEVEL_KNOB_Y)),
            module, Kck::LEVEL_PARAM));
        addInput(createInputCentered<rack::PJ301MPort>(
            mm2px(Vec(AgentLayout::CENTER_12HP, P9::LEVEL_JACK_Y)),
            module, Kck::LEVEL_CV_INPUT));

        addInput(createInputCentered<rack::PJ301MPort>(
            mm2px(Vec(P9::IO_TRIG_X, P9::IO_JACK_Y)), module, Kck::TRIG_INPUT));
        addInput(createInputCentered<rack::PJ301MPort>(
            mm2px(Vec(P9::IO_ACCENT_X, P9::IO_JACK_Y)), module, Kck::ACCENT_INPUT));
        addOutput(createOutputCentered<rack::PJ301MPort>(
            mm2px(Vec(P9::IO_OUT_X, P9::IO_JACK_Y)), module, Kck::OUT_OUTPUT));
    }
};

rack::Model* modelKck = createModel<Kck, KckWidget>("Kck");


// ---------------------------------------------------------------------------
// KckDbg -- debug / fitting variant.
//
// Same engine as Kck. Exposes the 7 user-facing controls plus the most
// informative KckFit knobs for hand-fitting. Once a setting sounds right,
// copy the values back into KckFit::makeKick().
// ---------------------------------------------------------------------------

struct KckDbg : AgentModule {
    enum ParamId {
        TUNE_PARAM, DECAY_PARAM, PITCH_PARAM, PITCH_DECAY_PARAM,
        CLICK_PARAM, DRIVE_PARAM, LEVEL_PARAM,
        // Fit knobs follow.
        BASE_PITCH_OFFSET_PARAM, BASE_PITCH_SPAN_PARAM,
        AMP_DECAY_MIN_PARAM,    AMP_DECAY_SPAN_PARAM,
        SWEEP_FAST_BASE_PARAM,  SWEEP_FAST_RATE_PARAM,
        SWEEP_SLOW_BASE_PARAM,  SWEEP_SLOW_RATE_PARAM,
        BODY_FUND_GAIN_PARAM,   BODY_HARM_RATIO_PARAM,  BODY_HARM_GAIN_PARAM,
        SUB_GAIN_PARAM,         SUB_DECAY_PARAM,
        CLICK_RATE_PARAM,       CLICK_NOISE_PARAM,
        CHIRP_START_PARAM,      CHIRP_RATE_PARAM,       CHIRP_GAIN_PARAM,
        HP_COEF_PARAM,          DRIVE_BASE_PARAM,       OUTPUT_GAIN_PARAM,
        NUM_PARAMS
    };
    // Per-knob CV inputs: one per ParamId. Layout-paired with the knobs.
    enum InputId  {
        TRIG_INPUT, ACCENT_INPUT,
        TUNE_CV, DECAY_CV, PITCH_CV, PITCH_DECAY_CV,
        CLICK_CV, DRIVE_CV, LEVEL_CV,
        BASE_PITCH_OFFSET_CV, BASE_PITCH_SPAN_CV,
        AMP_DECAY_MIN_CV, AMP_DECAY_SPAN_CV,
        SWEEP_FAST_BASE_CV, SWEEP_FAST_RATE_CV,
        SWEEP_SLOW_BASE_CV, SWEEP_SLOW_RATE_CV,
        BODY_FUND_GAIN_CV, BODY_HARM_RATIO_CV, BODY_HARM_GAIN_CV,
        SUB_GAIN_CV, SUB_DECAY_CV,
        CLICK_RATE_CV, CLICK_NOISE_CV,
        CHIRP_START_CV, CHIRP_RATE_CV, CHIRP_GAIN_CV,
        HP_COEF_CV, DRIVE_BASE_CV, OUTPUT_GAIN_CV,
        NUM_INPUTS
    };
    enum OutputId { OUT_OUTPUT, NUM_OUTPUTS };

    KckVoice voice;
    KckFit::Config fit;

    KckDbg() {
        config(NUM_PARAMS, NUM_INPUTS, NUM_OUTPUTS);
        // Playable
        configParam(TUNE_PARAM,        0.f, 1.f, 0.50f,  "Tune");
        configParam(DECAY_PARAM,       0.f, 1.f, 0.50f,  "Decay");
        configParam(PITCH_PARAM,       0.f, 1.f, 0.385f, "Pitch amount");
        configParam(PITCH_DECAY_PARAM, 0.f, 1.f, 0.26f,  "Pitch decay");
        configParam(CLICK_PARAM,       0.f, 1.f, 0.50f, "Click / attack");
        configParam(DRIVE_PARAM,       0.f, 1.f, 0.f,   "Drive (extra)");
        configParam(LEVEL_PARAM,       0.f, 1.f, 0.85f, "Level");
        // Fit
        configParam(BASE_PITCH_OFFSET_PARAM, 10.f,  80.f,    20.f,   "Base pitch offset", " Hz");
        configParam(BASE_PITCH_SPAN_PARAM,   10.f, 120.f,    50.f,   "Base pitch span",   " Hz");
        configParam(AMP_DECAY_MIN_PARAM,      1.f,  40.f,    20.f,   "Body decay min (1/tau)");
        configParam(AMP_DECAY_SPAN_PARAM,     0.f,  30.f,    13.f,   "Body decay span");
        configParam(SWEEP_FAST_BASE_PARAM,    0.f, 300.f,   112.f,   "Fast sweep amp",    " Hz");
        configParam(SWEEP_FAST_RATE_PARAM,    1.f, 300.f,   150.f,   "Fast sweep rate (1/tau)");
        configParam(SWEEP_SLOW_BASE_PARAM,    0.f, 100.f,     8.f,   "Slow sweep amp",    " Hz");
        configParam(SWEEP_SLOW_RATE_PARAM,    0.5f, 50.f,    15.f,   "Slow sweep rate (1/tau)");
        configParam(BODY_FUND_GAIN_PARAM,     0.f,   1.5f,    0.88f, "Body fundamental gain");
        configParam(BODY_HARM_RATIO_PARAM,    1.f,   3.f,     2.02f, "Body harmonic ratio");
        configParam(BODY_HARM_GAIN_PARAM,     0.f,   1.f,     0.19f, "Body harmonic gain");
        configParam(SUB_GAIN_PARAM,           0.f,   1.f,     0.36f, "Sub gain");
        configParam(SUB_DECAY_PARAM,          0.1f,  5.f,     0.85f, "Sub decay (1/tau)");
        configParam(CLICK_RATE_PARAM,        20.f, 600.f,   140.f,   "Click rate (1/tau)");
        configParam(CLICK_NOISE_PARAM,        0.f,   1.f,     0.03f, "Click noise gain");
        configParam(CHIRP_START_PARAM,      400.f,3000.f,  1700.f,   "Click chirp start", " Hz");
        configParam(CHIRP_RATE_PARAM,         0.f,1500.f,   400.f,   "Click chirp falling rate");
        configParam(CHIRP_GAIN_PARAM,         0.f,   1.f,     0.f,   "Click chirp gain");
        configParam(HP_COEF_PARAM,            0.f,   0.05f,   0.0012f,"HP coef");
        configParam(DRIVE_BASE_PARAM,         0.5f,  4.f,     1.55f, "Drive base");
        configParam(OUTPUT_GAIN_PARAM,        0.f,   2.f,     1.f,   "Output gain");

        configInput (TRIG_INPUT,   "Trigger");
        configInput (ACCENT_INPUT, "Accent");

        configInput(TUNE_CV,                   "Tune CV");
        configInput(DECAY_CV,                  "Decay CV");
        configInput(PITCH_CV,                  "Pitch amount CV");
        configInput(PITCH_DECAY_CV,            "Pitch decay CV");
        configInput(CLICK_CV,                  "Click CV");
        configInput(DRIVE_CV,                  "Drive CV");
        configInput(LEVEL_CV,                  "Level CV");
        configInput(BASE_PITCH_OFFSET_CV,      "Base pitch offset CV");
        configInput(BASE_PITCH_SPAN_CV,        "Base pitch span CV");
        configInput(AMP_DECAY_MIN_CV,          "Amp decay min CV");
        configInput(AMP_DECAY_SPAN_CV,         "Amp decay span CV");
        configInput(SWEEP_FAST_BASE_CV,        "Fast sweep amp CV");
        configInput(SWEEP_FAST_RATE_CV,        "Fast sweep rate CV");
        configInput(SWEEP_SLOW_BASE_CV,        "Slow sweep amp CV");
        configInput(SWEEP_SLOW_RATE_CV,        "Slow sweep rate CV");
        configInput(BODY_FUND_GAIN_CV,         "Body fundamental gain CV");
        configInput(BODY_HARM_RATIO_CV,        "Body harm ratio CV");
        configInput(BODY_HARM_GAIN_CV,         "Body harm gain CV");
        configInput(SUB_GAIN_CV,               "Sub gain CV");
        configInput(SUB_DECAY_CV,              "Sub decay CV");
        configInput(CLICK_RATE_CV,             "Click rate CV");
        configInput(CLICK_NOISE_CV,            "Click noise CV");
        configInput(CHIRP_START_CV,            "Chirp start Hz CV");
        configInput(CHIRP_RATE_CV,             "Chirp falling rate CV");
        configInput(CHIRP_GAIN_CV,             "Chirp gain CV");
        configInput(HP_COEF_CV,                "HP coef CV");
        configInput(DRIVE_BASE_CV,             "Drive base CV");
        configInput(OUTPUT_GAIN_CV,            "Output gain CV");

        configOutput(OUT_OUTPUT,   "Audio");
    }

    // Read knob value plus CV (0.1 of param range per volt), clamped to range.
    inline float readWithCV(int paramId, int cvInputId) {
        rack::engine::ParamQuantity* q = paramQuantities[paramId];
        float range = q->maxValue - q->minValue;
        float v = params[paramId].getValue()
                + inputs[cvInputId].getVoltage() * 0.1f * range;
        return rack::math::clamp(v, q->minValue, q->maxValue);
    }

    void process(const ProcessArgs& args) override {
        // Live-copy fit knobs (with CV) into engine config every frame.
        fit.basePitchOffset          = readWithCV(BASE_PITCH_OFFSET_PARAM, BASE_PITCH_OFFSET_CV);
        fit.basePitchSpan            = readWithCV(BASE_PITCH_SPAN_PARAM,   BASE_PITCH_SPAN_CV);
        fit.ampDecayMin              = readWithCV(AMP_DECAY_MIN_PARAM,     AMP_DECAY_MIN_CV);
        fit.ampDecaySpan             = readWithCV(AMP_DECAY_SPAN_PARAM,    AMP_DECAY_SPAN_CV);
        fit.pitchSweepFastBase       = readWithCV(SWEEP_FAST_BASE_PARAM,   SWEEP_FAST_BASE_CV);
        fit.pitchSweepFastRateBase   = readWithCV(SWEEP_FAST_RATE_PARAM,   SWEEP_FAST_RATE_CV);
        fit.pitchSweepSlowBase       = readWithCV(SWEEP_SLOW_BASE_PARAM,   SWEEP_SLOW_BASE_CV);
        fit.pitchSweepSlowRateBase   = readWithCV(SWEEP_SLOW_RATE_PARAM,   SWEEP_SLOW_RATE_CV);
        fit.bodyFundGain             = readWithCV(BODY_FUND_GAIN_PARAM,    BODY_FUND_GAIN_CV);
        fit.bodyHarmRatio            = readWithCV(BODY_HARM_RATIO_PARAM,   BODY_HARM_RATIO_CV);
        fit.bodyHarmGain             = readWithCV(BODY_HARM_GAIN_PARAM,    BODY_HARM_GAIN_CV);
        fit.subGain                  = readWithCV(SUB_GAIN_PARAM,          SUB_GAIN_CV);
        fit.subDecayBase             = readWithCV(SUB_DECAY_PARAM,         SUB_DECAY_CV);
        fit.clickRateBase            = readWithCV(CLICK_RATE_PARAM,        CLICK_RATE_CV);
        fit.clickNoiseBase           = readWithCV(CLICK_NOISE_PARAM,       CLICK_NOISE_CV);
        fit.clickChirpStartHz        = readWithCV(CHIRP_START_PARAM,       CHIRP_START_CV);
        fit.clickChirpRate           = readWithCV(CHIRP_RATE_PARAM,        CHIRP_RATE_CV);
        fit.clickChirpBase           = readWithCV(CHIRP_GAIN_PARAM,        CHIRP_GAIN_CV);
        fit.hpCoef                   = readWithCV(HP_COEF_PARAM,           HP_COEF_CV);
        fit.driveBase                = readWithCV(DRIVE_BASE_PARAM,        DRIVE_BASE_CV);
        fit.outputGain               = readWithCV(OUTPUT_GAIN_PARAM,       OUTPUT_GAIN_CV);

        if (voice.trigger.process(inputs[TRIG_INPUT].getVoltage(), 0.1f, 2.f)) {
            voice.fire();
        }

        const float tuneNorm       = readWithCV(TUNE_PARAM,        TUNE_CV);
        const float decayNorm      = readWithCV(DECAY_PARAM,       DECAY_CV);
        const float pitchNorm      = readWithCV(PITCH_PARAM,       PITCH_CV);
        const float pitchDecayNorm = readWithCV(PITCH_DECAY_PARAM, PITCH_DECAY_CV);
        const float clickNorm      = readWithCV(CLICK_PARAM,       CLICK_CV);
        const float driveNorm      = readWithCV(DRIVE_PARAM,       DRIVE_CV);
        const float levelNorm      = readWithCV(LEVEL_PARAM,       LEVEL_CV);

        float out = voice.process(args, fit,
                                  tuneNorm, decayNorm, pitchNorm, pitchDecayNorm,
                                  clickNorm, driveNorm, levelNorm);
        outputs[OUT_OUTPUT].setVoltage(AgentRack::Signal::Audio::toRackVolts(out));
    }
};


struct KckDbgLabelCell { float xMm, yMm; const char* text; };

struct KckDbgPanel : rack::widget::Widget {
    std::vector<KckDbgLabelCell> labels;

    void draw(const DrawArgs& args) override {
        nvgBeginPath(args.vg);
        nvgRect(args.vg, 0.f, 0.f, box.size.x, box.size.y);
        nvgFillColor(args.vg, nvgRGB(20, 18, 22));
        nvgFill(args.vg);

        nvgFontSize(args.vg, 7.f);
        nvgFillColor(args.vg, nvgRGBA(220, 220, 240, 200));
        nvgTextAlign(args.vg, NVG_ALIGN_LEFT | NVG_ALIGN_MIDDLE);
        nvgText(args.vg, mm2px(4.f), mm2px(6.f), "KCK DBG", nullptr);

        nvgFontSize(args.vg, 4.5f);
        nvgFillColor(args.vg, nvgRGBA(200, 200, 220, 160));
        nvgText(args.vg, mm2px(28.f), mm2px(6.f),
                "tune/decay/pitch/p-decay/click/drive/level + 21 fit params",
                nullptr);

        nvgFontSize(args.vg, 4.4f);
        nvgFillColor(args.vg, nvgRGBA(220, 220, 240, 200));
        nvgTextAlign(args.vg, NVG_ALIGN_CENTER | NVG_ALIGN_MIDDLE);
        for (const auto& l : labels) {
            nvgText(args.vg, mm2px(l.xMm), mm2px(l.yMm), l.text, nullptr);
        }
    }
};

struct KckDbgWidget : rack::ModuleWidget {
    void addKnobAndJack(rack::engine::Module* module, int paramId, int cvInputId,
                        float xMm, float yMm,
                        const char* label, KckDbgPanel* panel) {
        // Label above the knob (row_y - 6.5), knob at row_y, jack at row_y + 10.25.
        panel->labels.push_back({ xMm, yMm - 6.5f, label });
        addParam(createParamCentered<rack::RoundSmallBlackKnob>(
            mm2px(Vec(xMm, yMm)), module, paramId));
        addInput(createInputCentered<rack::PJ301MPort>(
            mm2px(Vec(xMm, yMm + 10.25f)), module, cvInputId));
    }

    KckDbgWidget(KckDbg* module) {
        setModule(module);

        auto* panel = new KckDbgPanel;
        panel->box.size = Vec(RACK_GRID_WIDTH * 36, RACK_GRID_HEIGHT);
        addChild(panel);
        box.size = panel->box.size;

        addChild(createWidget<rack::ScrewSilver>(Vec(15, 0)));
        addChild(createWidget<rack::ScrewSilver>(Vec(box.size.x - 30, 0)));
        addChild(createWidget<rack::ScrewSilver>(Vec(15, RACK_GRID_HEIGHT - 15)));
        addChild(createWidget<rack::ScrewSilver>(Vec(box.size.x - 30, RACK_GRID_HEIGHT - 15)));

        // 7 cols x 4 rows = 28 cells exact (36 HP wide).
        // Per cell: label above knob; knob centred at row_y; CV jack 8.5 mm below knob.
        // Spacing: 26 mm horizontal, 26 mm vertical -- comfortable for hand-tuning.
        const float COLS_X[7] = { 16.f, 42.f, 68.f, 94.f, 120.f, 146.f, 172.f };
        const float ROWS_Y[4] = { 22.f, 48.f, 74.f, 100.f };

        struct Cell { int param; int cv; const char* label; };
        Cell cells[28] = {
            // Row 0 (playable controls + drive + level)
            {KckDbg::TUNE_PARAM,              KckDbg::TUNE_CV,              "TUNE"},
            {KckDbg::DECAY_PARAM,             KckDbg::DECAY_CV,             "DECAY"},
            {KckDbg::PITCH_PARAM,             KckDbg::PITCH_CV,             "PITCH AMT"},
            {KckDbg::PITCH_DECAY_PARAM,       KckDbg::PITCH_DECAY_CV,       "P DECAY"},
            {KckDbg::CLICK_PARAM,             KckDbg::CLICK_CV,             "CLICK"},
            {KckDbg::DRIVE_PARAM,             KckDbg::DRIVE_CV,             "DRIVE+"},
            {KckDbg::LEVEL_PARAM,             KckDbg::LEVEL_CV,             "LEVEL"},
            // Row 1 (pitch range + decay range + fast sweep + output gain)
            {KckDbg::BASE_PITCH_OFFSET_PARAM, KckDbg::BASE_PITCH_OFFSET_CV, "BASE OFF"},
            {KckDbg::BASE_PITCH_SPAN_PARAM,   KckDbg::BASE_PITCH_SPAN_CV,   "BASE SPAN"},
            {KckDbg::AMP_DECAY_MIN_PARAM,     KckDbg::AMP_DECAY_MIN_CV,     "DEC MIN"},
            {KckDbg::AMP_DECAY_SPAN_PARAM,    KckDbg::AMP_DECAY_SPAN_CV,    "DEC SPAN"},
            {KckDbg::SWEEP_FAST_BASE_PARAM,   KckDbg::SWEEP_FAST_BASE_CV,   "F SWEEP A"},
            {KckDbg::SWEEP_FAST_RATE_PARAM,   KckDbg::SWEEP_FAST_RATE_CV,   "F SWEEP R"},
            {KckDbg::OUTPUT_GAIN_PARAM,       KckDbg::OUTPUT_GAIN_CV,       "OUT GAIN"},
            // Row 2 (slow sweep + body harmonic stack + sub)
            {KckDbg::SWEEP_SLOW_BASE_PARAM,   KckDbg::SWEEP_SLOW_BASE_CV,   "S SWEEP A"},
            {KckDbg::SWEEP_SLOW_RATE_PARAM,   KckDbg::SWEEP_SLOW_RATE_CV,   "S SWEEP R"},
            {KckDbg::BODY_FUND_GAIN_PARAM,    KckDbg::BODY_FUND_GAIN_CV,    "FUND GAIN"},
            {KckDbg::BODY_HARM_RATIO_PARAM,   KckDbg::BODY_HARM_RATIO_CV,   "HARM RATIO"},
            {KckDbg::BODY_HARM_GAIN_PARAM,    KckDbg::BODY_HARM_GAIN_CV,    "HARM GAIN"},
            {KckDbg::SUB_GAIN_PARAM,          KckDbg::SUB_GAIN_CV,          "SUB GAIN"},
            {KckDbg::SUB_DECAY_PARAM,         KckDbg::SUB_DECAY_CV,         "SUB DEC"},
            // Row 3 (click + chirp + filter + drive base)
            {KckDbg::CLICK_RATE_PARAM,        KckDbg::CLICK_RATE_CV,        "CLK RATE"},
            {KckDbg::CLICK_NOISE_PARAM,       KckDbg::CLICK_NOISE_CV,       "CLK NOISE"},
            {KckDbg::CHIRP_START_PARAM,       KckDbg::CHIRP_START_CV,       "CHRP HZ"},
            {KckDbg::CHIRP_RATE_PARAM,        KckDbg::CHIRP_RATE_CV,        "CHRP FALL"},
            {KckDbg::CHIRP_GAIN_PARAM,        KckDbg::CHIRP_GAIN_CV,        "CHRP GAIN"},
            {KckDbg::HP_COEF_PARAM,           KckDbg::HP_COEF_CV,           "HP COEF"},
            {KckDbg::DRIVE_BASE_PARAM,        KckDbg::DRIVE_BASE_CV,        "DRV BASE"},
        };
        for (int i = 0; i < 28; i++) {
            int r = i / 7;
            int c = i % 7;
            addKnobAndJack(module, cells[i].param, cells[i].cv,
                           COLS_X[c], ROWS_Y[r], cells[i].label, panel);
        }

        // Bottom IO row: TRIG, ACCENT, OUT (centred horizontally on the 36 HP panel)
        addInput(createInputCentered<rack::PJ301MPort>(
            mm2px(Vec(72.f, 124.f)), module, KckDbg::TRIG_INPUT));
        addInput(createInputCentered<rack::PJ301MPort>(
            mm2px(Vec(91.4f, 124.f)), module, KckDbg::ACCENT_INPUT));
        addOutput(createOutputCentered<rack::PJ301MPort>(
            mm2px(Vec(110.8f, 124.f)), module, KckDbg::OUT_OUTPUT));
    }
};

rack::Model* modelKckDbg = createModel<KckDbg, KckDbgWidget>("KckDbg");
