#include <rack.hpp>
#include "AgentModule.hpp"
#include "PanelLayout.hpp"
#include "agentrack/signal/Audio.hpp"
#include "agentrack/signal/CrinkleCore.hpp"
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

using CrinkleVoice = AgentRack::Signal::Crinkle::Voice;

// ---------------------------------------------------------------------------
// Module
// ---------------------------------------------------------------------------

struct Crinkle : AgentModule {

    enum ParamId  { TUNE_PARAM, TIMBRE_PARAM, SYMMETRY_PARAM, TIMBRE_CV_PARAM, NUM_PARAMS };
    enum InputId  { VOCT_INPUT, TIMBRE_INPUT, NUM_INPUTS  };
    enum OutputId { OUT_OUTPUT, NUM_OUTPUTS };

    static constexpr int MAX_POLY = 16;
    CrinkleVoice voices[MAX_POLY];

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
        int channels = std::max(1, std::max(inputs[VOCT_INPUT].getChannels(),
                                            inputs[TIMBRE_INPUT].getChannels()));
        channels = std::min(channels, MAX_POLY);
        outputs[OUT_OUTPUT].setChannels(channels);

        AgentRack::Signal::CV::VoctParameter pitchParam{
            "pitch", params[TUNE_PARAM].getValue(), -12.f, 12.f
        };
        AgentRack::Signal::CV::Parameter timbreParam{
            "timbre", params[TIMBRE_PARAM].getValue(), 0.f, 1.f
        };
        float symmetry = params[SYMMETRY_PARAM].getValue();

        for (int c = 0; c < channels; c++) {
            float pitch = pitchParam.modulate(inputs[VOCT_INPUT].getPolyVoltage(c));
            float freq  = dsp::FREQ_C4 * std::pow(2.f, pitch);
            float timbre = timbreParam.modulate(params[TIMBRE_CV_PARAM].getValue(),
                                                inputs[TIMBRE_INPUT].getPolyVoltage(c));
            float out = voices[c].processSample(freq, timbre, symmetry, args.sampleTime);

            outputs[OUT_OUTPUT].setVoltage(
                AgentRack::Signal::Audio::toRackVolts(out), c);
        }
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

        // Knobs -- large for TUNE, small for TIMBRE/SYMMETRY
        addParam(createParamCentered<rack::RoundBigBlackKnob>(
            mm2px(rack::Vec(AgentLayout::CENTER_8HP, AgentLayout::COMPACT_ROWS_8HP[0])), module, Crinkle::TUNE_PARAM));
        addParam(createParamCentered<rack::RoundBlackKnob>(
            mm2px(rack::Vec(AgentLayout::CENTER_8HP, AgentLayout::COMPACT_ROWS_8HP[1])), module, Crinkle::TIMBRE_PARAM));
        addParam(createParamCentered<rack::RoundSmallBlackKnob>(
            mm2px(rack::Vec(AgentLayout::CENTER_8HP, AgentLayout::COMPACT_ROWS_8HP[2])), module, Crinkle::SYMMETRY_PARAM));

        // TIMBRE CV attenuator (small, near TIMBRE input)
        addParam(createParamCentered<rack::Trimpot>(
            mm2px(rack::Vec(AgentLayout::RIGHT_PAIR_COLUMN_8HP, AgentLayout::COMPACT_ROWS_8HP[3])), module, Crinkle::TIMBRE_CV_PARAM));

        // Inputs: V/OCT left, TIMBRE right
        addInput(createInputCentered<rack::PJ301MPort>(
            mm2px(rack::Vec(AgentLayout::LEFT_PAIR_COLUMN_8HP, AgentLayout::COMPACT_ROWS_8HP[4])), module, Crinkle::VOCT_INPUT));
        addInput(createInputCentered<rack::PJ301MPort>(
            mm2px(rack::Vec(AgentLayout::RIGHT_PAIR_COLUMN_8HP, AgentLayout::COMPACT_ROWS_8HP[4])), module, Crinkle::TIMBRE_INPUT));

        // Output: center
        addOutput(createOutputCentered<rack::PJ301MPort>(
            mm2px(rack::Vec(AgentLayout::CENTER_8HP, AgentLayout::COMPACT_ROWS_8HP[5])), module, Crinkle::OUT_OUTPUT));
    }
};


rack::Model* modelCrinkle = createModel<Crinkle, CrinkleWidget>("Crinkle");
