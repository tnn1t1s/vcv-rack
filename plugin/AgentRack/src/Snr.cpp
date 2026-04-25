#include <rack.hpp>
#include "AgentModule.hpp"
#include "PanelLayout.hpp"
#include "agentrack/signal/Audio.hpp"
#include <cmath>

using namespace rack;
extern Plugin* pluginInstance;

/**
 * Snr -- TR-909 inspired snare drum.
 *
 * The original 909 snare is a balanced instrument, not a generic synth patch:
 * two trigger-reset triangle VCOs supply the body, and a quasi-random binary
 * noise source supplies the upper spectrum. The front-panel controls on the
 * original machine are Tune, Tone, Snappy, and Level, so this module now keeps
 * that same surface and fixes the rest internally.
 *
 * Internal model:
 *   body  = two phase-reset triangle oscillators with a short pitch bend and
 *           slightly different decay times
 *   noise = binary-noise generator split into low/high branches with separate
 *           envelopes; Tone sets the noise duration, Snappy sets the gain
 *   mix   = body + low-noise + high-noise + short attack click
 *
 * Rack IDs (stable for the current 909 module generation):
 *   Params:  TUNE=0, TONE=1, SNAPPY=2, LEVEL=3
 *   Inputs:  TRIG=0, TUNE_CV=1, TONE_CV=2, SNAPPY_CV=3, LEVEL_CV=4
 *   Outputs: OUT=0
 */

static constexpr float SNR_TUNE_OCT_RANGE    = 0.75f;
static constexpr float SNR_TONE_MIN_SEC      = 0.018f;
static constexpr float SNR_NOISE_HIGH_Q      = 0.78f;
static constexpr float SNR_NOISE_LOW_Q       = 0.82f;
static constexpr float SNR_CV_SCALE          = 0.1f;

static inline float snrNormWithCV(rack::Module& self, int paramId, int inputId) {
    float norm = self.params[paramId].getValue()
               + self.inputs[inputId].getVoltage() * SNR_CV_SCALE;
    return rack::math::clamp(norm, 0.f, 1.f);
}

static inline float snrTriangle(float phase) {
    return 1.f - 4.f * std::fabs(phase - 0.5f);
}

// TPT SVF used for the snare-noise branches.
struct SnrSVF {
    float ic1 = 0.f, ic2 = 0.f;
    float lpf = 0.f;
    float hpf = 0.f;
    void reset() { ic1 = ic2 = lpf = hpf = 0.f; }
    void process(float x, float fHz, float sampleRate, float Q) {
        float g = std::tan(float(M_PI) * fHz / sampleRate);
        float k = 1.f / Q;
        float a1 = 1.f / (1.f + g * (g + k));
        float a2 = g * a1;
        float a3 = g * a2;
        float v3 = x - ic2;
        float v1 = a1 * ic1 + a2 * v3;
        float v2 = ic2 + a2 * ic1 + a3 * v3;
        ic1 = 2.f * v1 - ic1;
        ic2 = 2.f * v2 - ic2;
        lpf = v2;
        hpf = x - k * v1 - v2;
    }
};

namespace SnrFit {
struct Config {
    float osc1BaseHz = 157.655031f;
    float osc2BaseHz = 332.641481f;
    float body1TauSec = 0.025189178f;
    float body2TauSec = 0.020462034f;
    float bodyLpHz = 1273.814504f;
    float toneMaxSec = 0.106f;
    float noiseHighRatio = 0.713894547f;
    float noiseClockHz = 14285.683594f;
    float noiseLpHz = 9278.987305f;
    float noiseHpHz = 3907.570801f;
    float bendMaxOct = 0.46f;
    float bendTauSec = 0.020f;
    float attackTauSec = 0.000685407f;
    float clickTauSec = 0.0015f;
    float body1Gain = 1.053525281f;
    float body2Gain = 0.196282045f;
    float bodyDrive = 1.028451443f;
    float lowNoiseGain = 0.074649002f;
    float lowNoiseToneBase = 0.75f;
    float lowNoiseToneSpan = 0.25f;
    float highNoiseBase = 0.073381014f;
    float highNoiseSnappy = 0.315936893f;
    float clickBodyGain = 0.171073779f;
    float clickNoiseGain = 0.075186349f;
    float mixDriveBase = 0.960915566f;
    float mixDriveSnappy = 0.058808930f;
    float outputGain = 0.86f;
    float osc2BendRatio = 0.751340272f;
};

static inline const Config& defaults() {
    static const Config cfg;
    return cfg;
}

static Config current = defaults();

static inline void reset() {
    current = defaults();
}
}  // namespace SnrFit


struct Snr : AgentModule {

    enum ParamId  {
        TUNE_PARAM, TONE_PARAM, SNAPPY_PARAM, LEVEL_PARAM,
        NUM_PARAMS
    };
    enum InputId  {
        TRIG_INPUT, TUNE_CV_INPUT, TONE_CV_INPUT, SNAPPY_CV_INPUT, LEVEL_CV_INPUT,
        NUM_INPUTS
    };
    enum OutputId { OUT_OUTPUT, NUM_OUTPUTS };

    dsp::SchmittTrigger trigger;

    float phase1   = 0.f;
    float phase2   = 0.f;
    float bodyEnv1 = 0.f;
    float bodyEnv2 = 0.f;
    float noiseLowEnv = 0.f;
    float noiseHighEnv = 0.f;
    float bendEnv  = 0.f;
    float attackEnv = 1.f;
    float clickEnv = 0.f;
    float bodyLP = 0.f;

    float noisePhase = 0.f;
    uint32_t noiseShift = 0x1u;
    float noiseValue = 1.f;
    float prevBody = 0.f;
    float prevNoise = 0.f;

    SnrSVF lpNoise;
    SnrSVF hpNoise;

    Snr() {
        config(NUM_PARAMS, NUM_INPUTS, NUM_OUTPUTS);
        configParam(TUNE_PARAM,   0.f, 1.f, 0.50f, "Tune",   "%", 0.f, 100.f);
        configParam(TONE_PARAM,   0.f, 1.f, 1.00f, "Tone",   "%", 0.f, 100.f);
        configParam(SNAPPY_PARAM, 0.f, 1.f, 1.00f, "Snappy", "%", 0.f, 100.f);
        configParam(LEVEL_PARAM,  0.f, 1.f, 0.82f, "Level",  "%", 0.f, 100.f);
        configInput (TRIG_INPUT,      "Trigger");
        configInput (TUNE_CV_INPUT,   "Tune CV");
        configInput (TONE_CV_INPUT,   "Tone CV");
        configInput (SNAPPY_CV_INPUT, "Snappy CV");
        configInput (LEVEL_CV_INPUT,  "Level CV");
        configOutput(OUT_OUTPUT,      "Audio");
    }

    void process(const ProcessArgs& args) override {
        if (trigger.process(inputs[TRIG_INPUT].getVoltage(), 0.1f, 2.f)) {
            bodyEnv1 = 1.f;
            bodyEnv2 = 1.f;
            noiseLowEnv = 1.f;
            noiseHighEnv = 1.f;
            bendEnv  = 1.f;
            attackEnv = 0.f;
            clickEnv = 1.f;
            phase1   = 0.f;
            phase2   = 0.f;
            bodyLP = 0.f;
            noisePhase = 0.f;
            prevBody = 0.f;
            prevNoise = noiseValue;
            lpNoise.reset();
            hpNoise.reset();
        }

        float tune_norm    = snrNormWithCV(*this, TUNE_PARAM,   TUNE_CV_INPUT);
        float tone_norm    = snrNormWithCV(*this, TONE_PARAM,   TONE_CV_INPUT);
        float snap_norm    = snrNormWithCV(*this, SNAPPY_PARAM, SNAPPY_CV_INPUT);
        float level_norm   = snrNormWithCV(*this, LEVEL_PARAM,  LEVEL_CV_INPUT);
        const SnrFit::Config& fit = SnrFit::current;

        float tune_oct = (tune_norm - 0.5f) * 2.f * SNR_TUNE_OCT_RANGE;
        float scale    = std::pow(2.f, tune_oct);
        float bendOct  = bendEnv * fit.bendMaxOct;
        float f1       = fit.osc1BaseHz * scale * std::pow(2.f, bendOct);
        float f2       = fit.osc2BaseHz * scale * std::pow(2.f, bendOct * fit.osc2BendRatio);
        float toneTau  = SNR_TONE_MIN_SEC + tone_norm * (fit.toneMaxSec - SNR_TONE_MIN_SEC);
        float noiseHighTau = toneTau * fit.noiseHighRatio;

        // --- body: two phase-reset triangles with different decays ------
        phase1 += f1 * args.sampleTime;
        phase2 += f2 * args.sampleTime;
        phase1 -= std::floor(phase1);
        phase2 -= std::floor(phase2);

        float tri1 = snrTriangle(phase1);
        float tri2 = snrTriangle(phase2);
        float bodyRaw = tri1 * bodyEnv1 * fit.body1Gain + tri2 * bodyEnv2 * fit.body2Gain;
        float bodyLpAlpha = 1.f - std::exp(-2.f * float(M_PI) * fit.bodyLpHz * args.sampleTime);
        bodyLP += (bodyRaw - bodyLP) * bodyLpAlpha;
        float body = std::tanh(bodyLP * fit.bodyDrive);

        // --- noise: fixed binary source, split into low/high branches ----
        noisePhase += fit.noiseClockHz * args.sampleTime;
        while (noisePhase >= 1.f) {
            noisePhase -= 1.f;
            uint32_t newBit = ((noiseShift >> 0) ^ (noiseShift >> 2)
                             ^ (noiseShift >> 3) ^ (noiseShift >> 5)) & 1u;
            noiseShift = (noiseShift >> 1) | (newBit << 15);
            noiseValue = (noiseShift & 1u) ? 1.f : -1.f;
        }
        lpNoise.process(noiseValue, fit.noiseLpHz, args.sampleRate, SNR_NOISE_LOW_Q);
        hpNoise.process(noiseValue, fit.noiseHpHz, args.sampleRate, SNR_NOISE_HIGH_Q);
        float lowNoiseGain = fit.lowNoiseGain
                           * (fit.lowNoiseToneBase + tone_norm * fit.lowNoiseToneSpan);
        float lowNoise = lpNoise.lpf * noiseLowEnv * lowNoiseGain;
        float highNoise = hpNoise.hpf * noiseHighEnv * (fit.highNoiseBase + snap_norm * fit.highNoiseSnappy);
        float click = ((body - prevBody) * fit.clickBodyGain + (noiseValue - prevNoise) * fit.clickNoiseGain) * clickEnv;
        prevBody = body;
        prevNoise = noiseValue;

        // --- envelope decays --------------------------------------------
        bodyEnv1 *= std::exp(-args.sampleTime / fit.body1TauSec);
        bodyEnv2 *= std::exp(-args.sampleTime / fit.body2TauSec);
        noiseLowEnv *= std::exp(-args.sampleTime / toneTau);
        noiseHighEnv *= std::exp(-args.sampleTime / noiseHighTau);
        bendEnv *= std::exp(-args.sampleTime / fit.bendTauSec);
        attackEnv += (1.f - attackEnv) * (1.f - std::exp(-args.sampleTime / fit.attackTauSec));
        clickEnv *= std::exp(-args.sampleTime / fit.clickTauSec);

        float mix = body + lowNoise + highNoise + click;
        mix = std::tanh(mix * (fit.mixDriveBase + fit.mixDriveSnappy * snap_norm));
        mix *= attackEnv;

        float out = mix * level_norm * fit.outputGain;
        outputs[OUT_OUTPUT].setVoltage(AgentRack::Signal::Audio::toRackVolts(out));
    }
};


// ---------------------------------------------------------------------------
// Panel
// ---------------------------------------------------------------------------

struct SnrPanel : rack::widget::Widget {
    void draw(const DrawArgs& args) override {
        AgentLayout::drawAssetPanel(
            args.vg, box.size, pluginInstance,
            "res/Snr-bg.jpg",
            nvgRGB(30, 16, 18),
            "SNR", nvgRGB(255, 120, 100));

        static const char* const LABELS[] = {
            "TUNE", "TONE", "SNAP", "LEVEL",
        };
        const float* ys = AgentLayout::ROW_Y_8;
        nvgFontSize(args.vg, 5.5f);
        nvgFillColor(args.vg, nvgRGBA(255, 190, 180, 180));
        nvgTextAlign(args.vg, NVG_ALIGN_CENTER | NVG_ALIGN_MIDDLE);
        for (int i = 0; i < 4; i++) {
            nvgText(args.vg, mm2px(AgentLayout::CENTER_12HP), mm2px(ys[i]),
                    LABELS[i], NULL);
        }
    }
};


// ---------------------------------------------------------------------------
// Widget -- 12HP, 8-row grid
// ---------------------------------------------------------------------------

struct SnrWidget : rack::ModuleWidget {

    SnrWidget(Snr* module) {
        setModule(module);

        auto* panel = new SnrPanel;
        panel->box.size = AgentLayout::panelSize_12HP();
        addChild(panel);
        box.size = panel->box.size;

        AgentLayout::addScrews_12HP(this);

        namespace AL = AgentLayout;
        const float knobX = AL::LEFT_COLUMN_12HP;
        const float jackX = AL::RIGHT_COLUMN_12HP;
        const float* ys   = AL::ROW_Y_8;

        struct Row { int param; int input; };
        Row rows[4] = {
            {Snr::TUNE_PARAM,   Snr::TUNE_CV_INPUT},
            {Snr::TONE_PARAM,   Snr::TONE_CV_INPUT},
            {Snr::SNAPPY_PARAM, Snr::SNAPPY_CV_INPUT},
            {Snr::LEVEL_PARAM,  Snr::LEVEL_CV_INPUT},
        };
        for (int i = 0; i < 4; i++) {
            addParam(createParamCentered<rack::RoundBlackKnob>(
                mm2px(Vec(knobX, ys[i])), module, rows[i].param));
            addInput(createInputCentered<rack::PJ301MPort>(
                mm2px(Vec(jackX, ys[i])), module, rows[i].input));
        }

        addInput(createInputCentered<rack::PJ301MPort>(
            mm2px(Vec(knobX, ys[7])), module, Snr::TRIG_INPUT));
        addOutput(createOutputCentered<rack::PJ301MPort>(
            mm2px(Vec(jackX, ys[7])), module, Snr::OUT_OUTPUT));
    }
};


rack::Model* modelSnr = createModel<Snr, SnrWidget>("Snr");
