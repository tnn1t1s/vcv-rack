#include <rack.hpp>
#include "AgentModule.hpp"
#include "PanelLayout.hpp"
#include "agentrack/signal/Audio.hpp"
#include "agentrack/signal/CV.hpp"
#include <cmath>

using namespace rack;
extern Plugin* pluginInstance;

/**
 * Crinkle -- Buchla 259-inspired wavefolder oscillator.
 *
 * Triangle oscillator core fed through a 5-stage parallel center-clipper
 * wavefolder.  TIMBRE scales amplitude before folding (accesses different
 * regions of the transfer curve).  SYMMETRY adds DC offset before folding
 * introducing even-order harmonics and organic asymmetry.
 *
 * 4x oversampling inline to suppress folding aliasing.
 * Output: ±5V audio.
 *
 * Rack IDs (stable, never reorder):
 *   Params:  TUNE_PARAM=0, TIMBRE_PARAM=1, SYMMETRY_PARAM=2, TIMBRE_CV_PARAM=3
 *   Inputs:  VOCT_INPUT=0, TIMBRE_INPUT=1
 *   Outputs: OUT_OUTPUT=0
 */

// ---------------------------------------------------------------------------
// Wavefolder -- true triangle-bounce fold (Buchla 259 character)
// ---------------------------------------------------------------------------

// Triangle-wave fold: signal bounces hard off ±1 ceiling, creating new
// zero crossings and rich harmonics.  This is the classic Buchla approach --
// much more dramatic than soft clipping.
static inline float trifold(float x) {
    // Map any real x into -1..1 via triangle bounce
    x = x * 0.5f + 0.5f;          // shift to 0..1 range
    x = x - std::floor(x);         // wrap to 0..1
    if (x > 0.5f) x = 1.f - x;    // fold second half back
    return (x - 0.25f) * 4.f;      // rescale to -1..1
}

// Main fold function.  in should be roughly -1..1.
// timbre: 0..1   symmetry: -1..1 (DC offset adds even-order harmonics)
static float wavefold(float in, float timbre, float symmetry) {
    // TIMBRE scales amplitude 1x..6x -- at 1x output is clean triangle,
    // at higher values the wave folds multiple times producing strong harmonics
    float amp = 1.f + timbre * 5.f;
    float x   = in * amp + symmetry * 0.8f;
    return trifold(x);
}


// ---------------------------------------------------------------------------
// Module
// ---------------------------------------------------------------------------

struct Crinkle : AgentModule {

    enum ParamId  { TUNE_PARAM, TIMBRE_PARAM, SYMMETRY_PARAM, TIMBRE_CV_PARAM, NUM_PARAMS };
    enum InputId  { VOCT_INPUT, TIMBRE_INPUT, NUM_INPUTS  };
    enum OutputId { OUT_OUTPUT, NUM_OUTPUTS };

    float phase = 0.f;

    Crinkle() {
        config(NUM_PARAMS, NUM_INPUTS, NUM_OUTPUTS);
        configParam(TUNE_PARAM,      -2.f,  2.f,  0.f,  "Tune",        " oct");
        configParam(TIMBRE_PARAM,     0.f,  1.f,  0.f,  "Timbre",      "%", 0.f, 100.f);
        configParam(SYMMETRY_PARAM,  -1.f,  1.f,  0.f,  "Symmetry");
        configParam(TIMBRE_CV_PARAM, -1.f,  1.f,  1.f,  "Timbre CV",   "x");
        configInput (VOCT_INPUT,   "V/Oct");
        configInput (TIMBRE_INPUT, "Timbre CV");
        configOutput(OUT_OUTPUT,   "Out");
    }

    void process(const ProcessArgs& args) override {
        AgentRack::Signal::CV::VoctParameter pitchParam{
            "pitch", params[TUNE_PARAM].getValue(), -12.f, 12.f
        };
        float pitch = pitchParam.modulate(inputs[VOCT_INPUT].getVoltage());
        float freq  = dsp::FREQ_C4 * std::pow(2.f, pitch);

        AgentRack::Signal::CV::Parameter timbreParam{
            "timbre", params[TIMBRE_PARAM].getValue(), 0.f, 1.f
        };
        float timbre = timbreParam.modulate(params[TIMBRE_CV_PARAM].getValue(),
                                            inputs[TIMBRE_INPUT].getVoltage());

        float symmetry = params[SYMMETRY_PARAM].getValue();

        // 4x oversampling -- run oscillator + folder at 4x sample rate
        float dt = args.sampleTime / 4.f;
        float out = 0.f;
        for (int i = 0; i < 4; i++) {
            phase += freq * dt;
            if (phase >= 1.f) phase -= 1.f;

            // Triangle wave: 0..1 phase -> -1..1 triangle
            float tri = 2.f * std::fabs(2.f * phase - 1.f) - 1.f;

            out += wavefold(tri, timbre, symmetry);
        }
        out /= 4.f;

        outputs[OUT_OUTPUT].setVoltage(AgentRack::Signal::Audio::toRackVolts(out));
    }

};


// ---------------------------------------------------------------------------
// Panel
// ---------------------------------------------------------------------------

struct CrinklePanel : rack::widget::Widget {
    void draw(const DrawArgs& args) override {
        AgentLayout::drawAssetPanel(
            args.vg, box.size, pluginInstance,
            "res/Crinkle-bg.jpg",
            nvgRGB(0, 140, 160),
            "CRINKLE", nvgRGB(255, 255, 255));

        // Knob labels -- small, over the image
        nvgFontSize(args.vg, 5.5f);
        nvgFillColor(args.vg, nvgRGBA(255, 255, 255, 200));
        float cx = box.size.x / 2.f;
        nvgText(args.vg, cx, mm2px(28.f) - 10.f, "TUNE",     NULL);
        nvgText(args.vg, cx, mm2px(50.f) - 10.f, "TIMBRE",   NULL);
        nvgText(args.vg, cx, mm2px(72.f) - 10.f, "SYMMETRY", NULL);

        // Port labels
        float col1 = box.size.x * 0.28f;
        float col2 = box.size.x * 0.72f;
        nvgFontSize(args.vg, 5.f);
        nvgFillColor(args.vg, nvgRGBA(255, 255, 255, 200));
        nvgText(args.vg, col1, mm2px(96.f)  - 9.f, "V/OCT", NULL);
        nvgText(args.vg, col2, mm2px(96.f)  - 9.f, "TMB",   NULL);
        nvgText(args.vg, cx,   mm2px(112.f) - 9.f, "OUT",   NULL);
    }
};


// ---------------------------------------------------------------------------
// Widget -- 8HP
// ---------------------------------------------------------------------------

struct CrinkleWidget : rack::ModuleWidget {

    CrinkleWidget(Crinkle* module) {
        setModule(module);

        // 8HP = 40.64mm
        auto* panel = new CrinklePanel;
        panel->box.size = AgentLayout::panelSize_8HP();
        addChild(panel);
        box.size = panel->box.size;

        AgentLayout::addScrews_8HP(this);

        float cx = AgentLayout::CX_8HP;
        float L  = AgentLayout::PAIR_L_8HP;
        float R  = AgentLayout::PAIR_R_8HP;
        const float* ys = AgentLayout::ROW_Y_8_COMPACT;

        // Knobs -- large for TUNE, small for TIMBRE/SYMMETRY
        addParam(createParamCentered<rack::RoundBigBlackKnob>(
            mm2px(rack::Vec(cx, ys[0])), module, Crinkle::TUNE_PARAM));
        addParam(createParamCentered<rack::RoundBlackKnob>(
            mm2px(rack::Vec(cx, ys[1])), module, Crinkle::TIMBRE_PARAM));
        addParam(createParamCentered<rack::RoundSmallBlackKnob>(
            mm2px(rack::Vec(cx, ys[2])), module, Crinkle::SYMMETRY_PARAM));

        // TIMBRE CV attenuator (small, near TIMBRE input)
        addParam(createParamCentered<rack::Trimpot>(
            mm2px(rack::Vec(R, ys[3])), module, Crinkle::TIMBRE_CV_PARAM));

        // Inputs: V/OCT left, TIMBRE right
        addInput(createInputCentered<rack::PJ301MPort>(
            mm2px(rack::Vec(L, ys[4])), module, Crinkle::VOCT_INPUT));
        addInput(createInputCentered<rack::PJ301MPort>(
            mm2px(rack::Vec(R, ys[4])), module, Crinkle::TIMBRE_INPUT));

        // Output: center
        addOutput(createOutputCentered<rack::PJ301MPort>(
            mm2px(rack::Vec(cx, ys[5])), module, Crinkle::OUT_OUTPUT));
    }
};


rack::Model* modelCrinkle = createModel<Crinkle, CrinkleWidget>("Crinkle");
