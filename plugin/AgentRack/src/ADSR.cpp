#include <rack.hpp>
#include "AgentModule.hpp"
#include "PanelLayout.hpp"
#include "agentrack/signal/CV.hpp"

using namespace rack;
extern Plugin* pluginInstance;

/**
 * ADSR -- standard attack/decay/sustain/release envelope generator.
 *
 * ENV output is 0-10V.
 *
 * Rack IDs (stable, never reorder):
 *   Params:  ATTACK_PARAM=0, DECAY_PARAM=1, SUSTAIN_PARAM=2, RELEASE_PARAM=3,
 *            ATTACK_CV_PARAM=4, DECAY_CV_PARAM=5, SUSTAIN_CV_PARAM=6, RELEASE_CV_PARAM=7
 *   Inputs:  GATE_INPUT=0, ATTACK_INPUT=1, DECAY_INPUT=2, SUSTAIN_INPUT=3, RELEASE_INPUT=4
 *   Outputs: ENV_OUTPUT=0
 */
struct ADSR : AgentModule {

    enum ParamId  {
        ATTACK_PARAM, DECAY_PARAM, SUSTAIN_PARAM, RELEASE_PARAM,
        ATTACK_CV_PARAM, DECAY_CV_PARAM, SUSTAIN_CV_PARAM, RELEASE_CV_PARAM,
        NUM_PARAMS
    };
    enum InputId  { GATE_INPUT, ATTACK_INPUT, DECAY_INPUT, SUSTAIN_INPUT, RELEASE_INPUT, NUM_INPUTS  };
    enum OutputId { ENV_OUTPUT,   NUM_OUTPUTS };

    float env    = 0.f;
    bool  lastGate = false;
    enum Stage { IDLE, ATTACK, DECAY, SUSTAIN_STAGE, RELEASE } stage = IDLE;

    ADSR() {
        config(NUM_PARAMS, NUM_INPUTS, NUM_OUTPUTS);
        configParam(ATTACK_PARAM,  0.001f, 2.0f, 0.1f,  "Attack",  " s");
        configParam(DECAY_PARAM,   0.001f, 2.0f, 0.1f,  "Decay",   " s");
        configParam(SUSTAIN_PARAM, 0.0f,   1.0f, 0.5f,  "Sustain", "%", 0.f, 100.f);
        configParam(RELEASE_PARAM, 0.001f, 4.0f, 0.25f, "Release", " s");
        configParam(ATTACK_CV_PARAM,  -1.f, 1.f, 0.f, "Attack CV depth",  "x");
        configParam(DECAY_CV_PARAM,   -1.f, 1.f, 0.f, "Decay CV depth",   "x");
        configParam(SUSTAIN_CV_PARAM, -1.f, 1.f, 0.f, "Sustain CV depth", "x");
        configParam(RELEASE_CV_PARAM, -1.f, 1.f, 0.f, "Release CV depth", "x");
        configInput (GATE_INPUT,  "Gate");
        configInput (ATTACK_INPUT,  "Attack CV");
        configInput (DECAY_INPUT,   "Decay CV");
        configInput (SUSTAIN_INPUT, "Sustain CV");
        configInput (RELEASE_INPUT, "Release CV");
        configOutput(ENV_OUTPUT,  "Envelope");
    }

    void process(const ProcessArgs& args) override {
        bool gate = inputs[GATE_INPUT].getVoltage() > 1.f;

        // Gate edge detection.
        // Rising edge always (re)starts ATTACK.
        // Falling edge only triggers RELEASE from SUSTAIN -- during ATTACK and
        // DECAY the gate going low is ignored so short trigger pulses still
        // complete the full A/D cycle before releasing.
        if (gate && !lastGate)  stage = ATTACK;
        if (!gate && lastGate && stage == SUSTAIN_STAGE)  stage = RELEASE;
        lastGate = gate;

        AgentRack::Signal::CV::Parameter attackParam{
            "attack", params[ATTACK_PARAM].getValue(), 0.001f, 2.0f
        };
        AgentRack::Signal::CV::Parameter decayParam{
            "decay", params[DECAY_PARAM].getValue(), 0.001f, 2.0f
        };
        AgentRack::Signal::CV::Parameter sustainParam{
            "sustain", params[SUSTAIN_PARAM].getValue(), 0.0f, 1.0f
        };
        AgentRack::Signal::CV::Parameter releaseParam{
            "release", params[RELEASE_PARAM].getValue(), 0.001f, 4.0f
        };

        float attack  = attackParam.modulate(params[ATTACK_CV_PARAM].getValue(),
                                             inputs[ATTACK_INPUT].getVoltage());
        float decay   = decayParam.modulate(params[DECAY_CV_PARAM].getValue(),
                                            inputs[DECAY_INPUT].getVoltage());
        float sustain = sustainParam.modulate(params[SUSTAIN_CV_PARAM].getValue(),
                                              inputs[SUSTAIN_INPUT].getVoltage());
        float release = releaseParam.modulate(params[RELEASE_CV_PARAM].getValue(),
                                              inputs[RELEASE_INPUT].getVoltage());
        float dt      = args.sampleTime;

        switch (stage) {
            case IDLE:
                env = 0.f;
                break;
            case ATTACK:
                env += dt / attack;
                if (env >= 1.f) { env = 1.f; stage = DECAY; }
                break;
            case DECAY:
                env -= dt / decay;
                if (env <= sustain) {
                    env = sustain;
                    // If gate already low (short trigger), skip straight to release
                    stage = gate ? SUSTAIN_STAGE : RELEASE;
                }
                break;
            case SUSTAIN_STAGE:
                env = sustain;
                if (!gate) stage = RELEASE;
                break;
            case RELEASE:
                env -= dt / release;
                if (env <= 0.f) { env = 0.f; stage = IDLE; }
                break;
        }

        outputs[ENV_OUTPUT].setVoltage(env * 10.f);
    }

    std::string getManifest() const override {
        return R"ADSR({
  "module_id": "agentrack.adsr.v1",
  "ensemble_role": "none",
  "ports": [
    {"name": "GATE",       "direction": "input",  "signal_class": "gate",        "semantic_role": "trigger",            "required": true},
    {"name": "ATTACK_CV",  "direction": "input",  "signal_class": "cv_bipolar",  "semantic_role": "attack_mod",         "required": false},
    {"name": "DECAY_CV",   "direction": "input",  "signal_class": "cv_bipolar",  "semantic_role": "decay_mod",          "required": false},
    {"name": "SUSTAIN_CV", "direction": "input",  "signal_class": "cv_bipolar",  "semantic_role": "sustain_mod",        "required": false},
    {"name": "RELEASE_CV", "direction": "input",  "signal_class": "cv_bipolar",  "semantic_role": "release_mod",        "required": false},
    {"name": "ENV",        "direction": "output", "signal_class": "cv_unipolar", "semantic_role": "envelope_out"}
  ],
  "params": [
    {"name": "ATTACK",  "rack_id": 0, "unit": "seconds",    "scale": "linear", "min": 0.001, "max": 2.0,  "default": 0.1},
    {"name": "DECAY",   "rack_id": 1, "unit": "seconds",    "scale": "linear", "min": 0.001, "max": 2.0,  "default": 0.1},
    {"name": "SUSTAIN", "rack_id": 2, "unit": "normalized", "scale": "linear", "min": 0.0,   "max": 1.0,  "default": 0.5},
    {"name": "RELEASE", "rack_id": 3, "unit": "seconds",    "scale": "linear", "min": 0.001, "max": 4.0,  "default": 0.25},
    {"name": "ATTACK_CV_DEPTH",  "rack_id": 4, "unit": "normalized", "scale": "linear", "min": -1.0, "max": 1.0, "default": 0.0},
    {"name": "DECAY_CV_DEPTH",   "rack_id": 5, "unit": "normalized", "scale": "linear", "min": -1.0, "max": 1.0, "default": 0.0},
    {"name": "SUSTAIN_CV_DEPTH", "rack_id": 6, "unit": "normalized", "scale": "linear", "min": -1.0, "max": 1.0, "default": 0.0},
    {"name": "RELEASE_CV_DEPTH", "rack_id": 7, "unit": "normalized", "scale": "linear", "min": -1.0, "max": 1.0, "default": 0.0}
  ],
  "guarantees": [
    "ENV output is 0-10V",
    "rising GATE edge triggers ATTACK",
    "falling GATE edge triggers RELEASE",
    "SUSTAIN level is held while GATE is high after DECAY completes",
    "embedded parameter modulation uses AgentRack Signal.CV bipolar-unit scaling (cv_volts / 10)",
    "CV depth params are additive in parameter space and clamped to the native parameter range"
  ]
})ADSR";
    }
};


// ---------------------------------------------------------------------------
// Panel
// ---------------------------------------------------------------------------

struct ADSRPanel : rack::widget::Widget {
    void draw(const DrawArgs& args) override {
        int imgHandle = 0;
        try {
            auto img = APP->window->loadImage(
                asset::plugin(pluginInstance, "res/ADSR-bg.jpg"));
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
            nvgFillColor(args.vg, nvgRGB(220, 200, 190));
            nvgFill(args.vg);
        }

        // Dark top bar + title
        nvgBeginPath(args.vg);
        nvgRect(args.vg, 0, 0, box.size.x, 20.f);
        nvgFillColor(args.vg, nvgRGBA(0, 0, 0, 180));
        nvgFill(args.vg);

        nvgFontSize(args.vg, 7.f);
        nvgTextAlign(args.vg, NVG_ALIGN_CENTER | NVG_ALIGN_MIDDLE);
        nvgFillColor(args.vg, nvgRGB(255, 220, 0));
        nvgText(args.vg, box.size.x / 2.f, 10.f, "ADSR", NULL);

        // Stage labels
        const char* labels[] = { "A", "D", "S", "R" };
        const float* ypos    = AgentLayout::ROW_Y;
        float depthX         = 21.f;
        float ioX            = AgentLayout::RIGHT_8HP;
        nvgFontSize(args.vg, 6.f);
        nvgFillColor(args.vg, nvgRGB(0, 0, 0));
        for (int i = 0; i < 4; i++) {
            nvgTextAlign(args.vg, NVG_ALIGN_LEFT | NVG_ALIGN_MIDDLE);
            nvgText(args.vg, mm2px(2.0f), mm2px(ypos[i]) - 8.f, labels[i], NULL);
            nvgTextAlign(args.vg, NVG_ALIGN_CENTER | NVG_ALIGN_MIDDLE);
            nvgFontSize(args.vg, 4.5f);
            nvgText(args.vg, mm2px(depthX), mm2px(ypos[i]) - 8.f, "+/-", NULL);
            nvgFontSize(args.vg, 6.f);
        }

        // Port labels
        nvgFillColor(args.vg, nvgRGB(0, 0, 0));
        nvgTextAlign(args.vg, NVG_ALIGN_CENTER | NVG_ALIGN_MIDDLE);
        nvgText(args.vg, mm2px(ioX), mm2px(AgentLayout::ROW_Y[4]) - 10.f, "GATE", NULL);
        nvgText(args.vg, mm2px(ioX), mm2px(AgentLayout::ROW_Y[5]) - 10.f, "ENV",  NULL);
    }
};


// ---------------------------------------------------------------------------
// Widget -- 8HP
// ---------------------------------------------------------------------------

struct ADSRWidget : rack::ModuleWidget {

    ADSRWidget(ADSR* module) {
        setModule(module);

        auto* panel = new ADSRPanel;
        panel->box.size = AgentLayout::panelSize_8HP();
        addChild(panel);
        box.size = panel->box.size;

        AgentLayout::addScrews_8HP(this);

        const float* ys = AgentLayout::ROW_Y;
        float paramX = 11.f;
        float depthX = 21.f;
        float cvX    = AgentLayout::RIGHT_8HP;

        addParam(createParamCentered<rack::RoundSmallBlackKnob>(mm2px(rack::Vec(paramX, ys[0])), module, ADSR::ATTACK_PARAM));
        addParam(createParamCentered<rack::RoundSmallBlackKnob>(mm2px(rack::Vec(paramX, ys[1])), module, ADSR::DECAY_PARAM));
        addParam(createParamCentered<rack::RoundSmallBlackKnob>(mm2px(rack::Vec(paramX, ys[2])), module, ADSR::SUSTAIN_PARAM));
        addParam(createParamCentered<rack::RoundSmallBlackKnob>(mm2px(rack::Vec(paramX, ys[3])), module, ADSR::RELEASE_PARAM));

        addParam(createParamCentered<rack::Trimpot>(mm2px(rack::Vec(depthX, ys[0])), module, ADSR::ATTACK_CV_PARAM));
        addParam(createParamCentered<rack::Trimpot>(mm2px(rack::Vec(depthX, ys[1])), module, ADSR::DECAY_CV_PARAM));
        addParam(createParamCentered<rack::Trimpot>(mm2px(rack::Vec(depthX, ys[2])), module, ADSR::SUSTAIN_CV_PARAM));
        addParam(createParamCentered<rack::Trimpot>(mm2px(rack::Vec(depthX, ys[3])), module, ADSR::RELEASE_CV_PARAM));

        addInput(createInputCentered<rack::PJ301MPort>(mm2px(rack::Vec(cvX, ys[0])), module, ADSR::ATTACK_INPUT));
        addInput(createInputCentered<rack::PJ301MPort>(mm2px(rack::Vec(cvX, ys[1])), module, ADSR::DECAY_INPUT));
        addInput(createInputCentered<rack::PJ301MPort>(mm2px(rack::Vec(cvX, ys[2])), module, ADSR::SUSTAIN_INPUT));
        addInput(createInputCentered<rack::PJ301MPort>(mm2px(rack::Vec(cvX, ys[3])), module, ADSR::RELEASE_INPUT));
        addInput(createInputCentered<rack::PJ301MPort>(mm2px(rack::Vec(cvX, ys[4])), module, ADSR::GATE_INPUT));
        addOutput(createOutputCentered<rack::PJ301MPort>(mm2px(rack::Vec(cvX, ys[5])), module, ADSR::ENV_OUTPUT));
    }
};


rack::Model* modelADSR = createModel<ADSR, ADSRWidget>("ADSR");
