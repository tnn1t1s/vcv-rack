#include <rack.hpp>
#include "AgentModule.hpp"

using namespace rack;
extern Plugin* pluginInstance;

/**
 * ADSR -- standard attack/decay/sustain/release envelope generator.
 *
 * ENV output is 0-10V.
 *
 * Rack IDs (stable, never reorder):
 *   Params:  ATTACK_PARAM=0, DECAY_PARAM=1, SUSTAIN_PARAM=2, RELEASE_PARAM=3
 *   Inputs:  GATE_INPUT=0
 *   Outputs: ENV_OUTPUT=0
 */
struct ADSR : AgentModule {

    enum ParamId  { ATTACK_PARAM, DECAY_PARAM, SUSTAIN_PARAM, RELEASE_PARAM, NUM_PARAMS };
    enum InputId  { GATE_INPUT,   NUM_INPUTS  };
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
        configInput (GATE_INPUT,  "Gate");
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

        float attack  = params[ATTACK_PARAM].getValue();
        float decay   = params[DECAY_PARAM].getValue();
        float sustain = params[SUSTAIN_PARAM].getValue();
        float release = params[RELEASE_PARAM].getValue();
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
        return R"({
  "module_id": "agentrack.adsr.v1",
  "ensemble_role": "none",
  "ports": [
    {"name": "GATE", "direction": "input",  "signal_class": "gate",     "semantic_role": "trigger",  "required": true},
    {"name": "ENV",  "direction": "output", "signal_class": "cv_unipolar", "semantic_role": "envelope_out"}
  ],
  "params": [
    {"name": "ATTACK",  "rack_id": 0, "unit": "seconds",    "scale": "linear", "min": 0.001, "max": 2.0,  "default": 0.1},
    {"name": "DECAY",   "rack_id": 1, "unit": "seconds",    "scale": "linear", "min": 0.001, "max": 2.0,  "default": 0.1},
    {"name": "SUSTAIN", "rack_id": 2, "unit": "normalized", "scale": "linear", "min": 0.0,   "max": 1.0,  "default": 0.5},
    {"name": "RELEASE", "rack_id": 3, "unit": "seconds",    "scale": "linear", "min": 0.001, "max": 4.0,  "default": 0.25}
  ],
  "guarantees": [
    "ENV output is 0-10V",
    "rising GATE edge triggers ATTACK",
    "falling GATE edge triggers RELEASE",
    "SUSTAIN level is held while GATE is high after DECAY completes"
  ]
})";
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

        // Knob labels
        const char* labels[] = { "A", "D", "S", "R" };
        float ypos[]         = { 28.f, 46.f, 64.f, 82.f };
        nvgFontSize(args.vg, 6.f);
        nvgFillColor(args.vg, nvgRGB(0, 0, 0));
        for (int i = 0; i < 4; i++) {
            nvgText(args.vg, box.size.x / 2.f,
                    mm2px(ypos[i]) - 10.f, labels[i], NULL);
        }

        // Port labels
        nvgFillColor(args.vg, nvgRGB(0, 0, 0));
        nvgText(args.vg, box.size.x / 2.f, mm2px(100.f) - 10.f, "GATE", NULL);
        nvgText(args.vg, box.size.x / 2.f, mm2px(115.f) - 10.f, "ENV",  NULL);
    }
};


// ---------------------------------------------------------------------------
// Widget -- 6HP
// ---------------------------------------------------------------------------

struct ADSRWidget : rack::ModuleWidget {

    ADSRWidget(ADSR* module) {
        setModule(module);

        // 6HP = 30.48mm
        auto* panel = new ADSRPanel;
        panel->box.size = mm2px(Vec(30.48f, 128.5f));
        addChild(panel);
        box.size = panel->box.size;

        addChild(createWidget<ThemedScrew>(Vec(1 * RACK_GRID_WIDTH, 0)));
        addChild(createWidget<ThemedScrew>(Vec(4 * RACK_GRID_WIDTH, 0)));
        addChild(createWidget<ThemedScrew>(Vec(1 * RACK_GRID_WIDTH, RACK_GRID_HEIGHT - RACK_GRID_WIDTH)));
        addChild(createWidget<ThemedScrew>(Vec(4 * RACK_GRID_WIDTH, RACK_GRID_HEIGHT - RACK_GRID_WIDTH)));

        float cx = 15.24f;  // center x of 6HP

        addParam(createParamCentered<rack::RoundSmallBlackKnob>(mm2px(rack::Vec(cx, 28.f)),  module, ADSR::ATTACK_PARAM));
        addParam(createParamCentered<rack::RoundSmallBlackKnob>(mm2px(rack::Vec(cx, 46.f)),  module, ADSR::DECAY_PARAM));
        addParam(createParamCentered<rack::RoundSmallBlackKnob>(mm2px(rack::Vec(cx, 64.f)),  module, ADSR::SUSTAIN_PARAM));
        addParam(createParamCentered<rack::RoundSmallBlackKnob>(mm2px(rack::Vec(cx, 82.f)),  module, ADSR::RELEASE_PARAM));

        addInput (createInputCentered<rack::PJ301MPort>(mm2px(rack::Vec(cx, 100.f)), module, ADSR::GATE_INPUT));
        addOutput(createOutputCentered<rack::PJ301MPort>(mm2px(rack::Vec(cx, 115.f)), module, ADSR::ENV_OUTPUT));
    }
};


rack::Model* modelADSR = createModel<ADSR, ADSRWidget>("ADSR");
