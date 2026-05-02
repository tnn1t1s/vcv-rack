#include <rack.hpp>
#include "AgentModule.hpp"
#include "PanelLayout.hpp"
#include "Tr909Bus.hpp"

using namespace rack;
extern Plugin* pluginInstance;

/**
 * Tr909Ctrl -- TR-909 global state controller.
 *
 * Sits next to the 909 voice kit and broadcasts slow-changing global
 * controls via the expander bus.
 *
 * Currently exposes:
 *   - ACCENT A  -- multiplier on the A-only accent case.
 *   - ACCENT B  -- multiplier on the B-only accent case (local accent).
 *                  This is a calibration / tuning tool: a single global
 *                  Accent B multiplier is NOT a canonical TR-909
 *                  control (Accent B is per-voice on hardware), but it
 *                  is enormously useful while iterating on per-voice
 *                  AccentMix and per-DSP-stage weights.
 *   - MASTER    -- output volume scaling for all adjacent voices.
 *
 * The bus also carries `accentBothAmount` (multiplier on the both-gates
 * case); not exposed as a knob yet -- defaults to 1.0. If research shows
 * the both-case wants its own global trim, add a 4th knob here.
 *
 * Each knob has a CV input. Tr909Ctrl is NOT in the trigger path;
 * per-step gates (Total Accent, Local Accent, voice triggers) travel
 * from the sequencer directly to each voice's cable inputs.
 */

struct Tr909Ctrl : Tr909Module {
    enum ParamId  {
        ACCENT_A_PARAM, ACCENT_B_PARAM, MASTER_VOL_PARAM,
        NUM_PARAMS
    };
    enum InputId  {
        ACCENT_A_CV_INPUT, ACCENT_B_CV_INPUT, MASTER_VOL_CV_INPUT,
        NUM_INPUTS
    };
    enum OutputId { NUM_OUTPUTS };

    Tr909Ctrl() {
        config(NUM_PARAMS, NUM_INPUTS, NUM_OUTPUTS);
        configParam(ACCENT_A_PARAM,    0.f, 1.f, 1.f, "Accent A amount", "%", 0.f, 100.f);
        configParam(ACCENT_B_PARAM,    0.f, 1.f, 1.f, "Accent B amount", "%", 0.f, 100.f);
        configParam(MASTER_VOL_PARAM,  0.f, 1.f, 1.f, "Master volume",   "%", 0.f, 100.f);
        configInput(ACCENT_A_CV_INPUT,    "Accent A amount CV");
        configInput(ACCENT_B_CV_INPUT,    "Accent B amount CV");
        configInput(MASTER_VOL_CV_INPUT,  "Master volume CV");
    }

    static inline float knobPlusCV(rack::Module& self, int paramId, int cvInputId) {
        float v = self.params[paramId].getValue()
                + self.inputs[cvInputId].getNormalVoltage(0.f) * 0.1f;
        return rack::math::clamp(v, 0.f, 1.f);
    }

    void process(const ProcessArgs& args) override {
        currentBus.accentAAmount     = knobPlusCV(*this, ACCENT_A_PARAM,    ACCENT_A_CV_INPUT);
        currentBus.accentBAmount     = knobPlusCV(*this, ACCENT_B_PARAM,    ACCENT_B_CV_INPUT);
        currentBus.masterVolume      = knobPlusCV(*this, MASTER_VOL_PARAM,  MASTER_VOL_CV_INPUT);
        currentBus.controllerPresent = true;
    }
};


// ---------------------------------------------------------------------------
// Panel -- 6 HP, solid black
// ---------------------------------------------------------------------------

struct Tr909CtrlPanel : rack::widget::Widget {
    void draw(const DrawArgs& args) override {
        nvgBeginPath(args.vg);
        nvgRect(args.vg, 0.f, 0.f, box.size.x, box.size.y);
        nvgFillColor(args.vg, nvgRGB(8, 8, 10));
        nvgFill(args.vg);

        const float cx = box.size.x * 0.5f;

        nvgFontSize(args.vg, 9.f);
        nvgFillColor(args.vg, nvgRGBA(230, 230, 240, 230));
        nvgTextAlign(args.vg, NVG_ALIGN_CENTER | NVG_ALIGN_MIDDLE);
        nvgText(args.vg, cx, mm2px(8.f), "909", nullptr);

        nvgFontSize(args.vg, 6.f);
        nvgFillColor(args.vg, nvgRGBA(220, 70, 60, 220));
        nvgText(args.vg, cx, mm2px(15.f), "CTRL", nullptr);

        // ACC A
        nvgFontSize(args.vg, 5.0f);
        nvgFillColor(args.vg, nvgRGBA(200, 200, 215, 200));
        nvgText(args.vg, cx, mm2px(25.f), "ACC A", nullptr);

        // ACC B
        nvgText(args.vg, cx, mm2px(58.f), "ACC B", nullptr);

        // MASTER
        nvgText(args.vg, cx, mm2px(91.f), "MASTER", nullptr);

        // CV labels under jacks
        nvgFontSize(args.vg, 3.5f);
        nvgFillColor(args.vg, nvgRGBA(160, 160, 175, 150));
        nvgText(args.vg, cx, mm2px(53.f),  "CV", nullptr);
        nvgText(args.vg, cx, mm2px(86.f),  "CV", nullptr);
        nvgText(args.vg, cx, mm2px(119.f), "CV", nullptr);
    }
};

struct Tr909CtrlWidget : rack::ModuleWidget {
    Tr909CtrlWidget(Tr909Ctrl* module) {
        setModule(module);

        auto* panel = new Tr909CtrlPanel;
        panel->box.size = AgentLayout::panelSize_6HP();
        addChild(panel);
        box.size = panel->box.size;

        addChild(createWidget<rack::ScrewSilver>(Vec(0, 0)));
        addChild(createWidget<rack::ScrewSilver>(Vec(box.size.x - 15, 0)));
        addChild(createWidget<rack::ScrewSilver>(Vec(0, RACK_GRID_HEIGHT - 15)));
        addChild(createWidget<rack::ScrewSilver>(Vec(box.size.x - 15, RACK_GRID_HEIGHT - 15)));

        constexpr float cx_mm = 15.24f;  // 6HP / 2

        // ACC A row
        addParam(createParamCentered<rack::RoundBlackKnob>(
            mm2px(Vec(cx_mm, 35.f)), module, Tr909Ctrl::ACCENT_A_PARAM));
        addInput(createInputCentered<rack::PJ301MPort>(
            mm2px(Vec(cx_mm, 47.f)), module, Tr909Ctrl::ACCENT_A_CV_INPUT));

        // ACC B row
        addParam(createParamCentered<rack::RoundBlackKnob>(
            mm2px(Vec(cx_mm, 68.f)), module, Tr909Ctrl::ACCENT_B_PARAM));
        addInput(createInputCentered<rack::PJ301MPort>(
            mm2px(Vec(cx_mm, 80.f)), module, Tr909Ctrl::ACCENT_B_CV_INPUT));

        // MASTER row
        addParam(createParamCentered<rack::RoundBlackKnob>(
            mm2px(Vec(cx_mm, 101.f)), module, Tr909Ctrl::MASTER_VOL_PARAM));
        addInput(createInputCentered<rack::PJ301MPort>(
            mm2px(Vec(cx_mm, 113.f)), module, Tr909Ctrl::MASTER_VOL_CV_INPUT));
    }
};

rack::Model* modelTr909Ctrl = createModel<Tr909Ctrl, Tr909CtrlWidget>("Tr909Ctrl");
