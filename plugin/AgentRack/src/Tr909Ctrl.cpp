#include <rack.hpp>
#include "AgentModule.hpp"
#include "PanelLayout.hpp"
#include "Tr909Bus.hpp"

using namespace rack;
extern Plugin* pluginInstance;

/**
 * Tr909Ctrl -- TR-909 global state controller.
 *
 * Sits next to the 909 voice kit and broadcasts two slow-changing global
 * controls via the expander bus:
 *
 *   - ACCENT MULT  -- scales the accent strength applied by voices when
 *                     either Total Accent or Local Accent gate is high
 *                     at trigger time.
 *   - MASTER VOL   -- scales the output of all adjacent voices.
 *
 * Both have CV inputs for modulation. Tr909Ctrl is NOT in the trigger
 * path -- per-step gates (Total Accent, Local Accent, voice triggers)
 * travel from the sequencer directly to each voice's cable inputs.
 */

struct Tr909Ctrl : Tr909Module {
    enum ParamId  { ACCENT_AMT_PARAM, MASTER_VOL_PARAM, NUM_PARAMS };
    enum InputId  { ACCENT_AMT_CV_INPUT, MASTER_VOL_CV_INPUT, NUM_INPUTS };
    enum OutputId { NUM_OUTPUTS };

    Tr909Ctrl() {
        config(NUM_PARAMS, NUM_INPUTS, NUM_OUTPUTS);
        configParam(ACCENT_AMT_PARAM, 0.f, 1.f, 1.f, "Accent amount", "%", 0.f, 100.f);
        configParam(MASTER_VOL_PARAM, 0.f, 1.f, 1.f, "Master volume", "%", 0.f, 100.f);
        configInput(ACCENT_AMT_CV_INPUT, "Accent amount CV");
        configInput(MASTER_VOL_CV_INPUT, "Master volume CV");
    }

    static inline float knobPlusCV(rack::Module& self, int paramId, int cvInputId) {
        float v = self.params[paramId].getValue()
                + self.inputs[cvInputId].getNormalVoltage(0.f) * 0.1f;
        return rack::math::clamp(v, 0.f, 1.f);
    }

    void process(const ProcessArgs& args) override {
        currentBus.accentAmount      = knobPlusCV(*this, ACCENT_AMT_PARAM, ACCENT_AMT_CV_INPUT);
        currentBus.masterVolume      = knobPlusCV(*this, MASTER_VOL_PARAM, MASTER_VOL_CV_INPUT);
        currentBus.controllerPresent = true;
    }
};


// ---------------------------------------------------------------------------
// Panel -- 4 HP, solid black
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

        // ACCENT block
        nvgFontSize(args.vg, 5.0f);
        nvgFillColor(args.vg, nvgRGBA(200, 200, 215, 200));
        nvgText(args.vg, cx, mm2px(28.f), "ACCENT", nullptr);
        nvgFontSize(args.vg, 3.8f);
        nvgFillColor(args.vg, nvgRGBA(160, 160, 175, 160));
        nvgText(args.vg, cx, mm2px(58.f), "CV", nullptr);

        // MASTER VOL block
        nvgFontSize(args.vg, 5.0f);
        nvgFillColor(args.vg, nvgRGBA(200, 200, 215, 200));
        nvgText(args.vg, cx, mm2px(78.f), "VOL", nullptr);
        nvgFontSize(args.vg, 3.8f);
        nvgFillColor(args.vg, nvgRGBA(160, 160, 175, 160));
        nvgText(args.vg, cx, mm2px(108.f), "CV", nullptr);
    }
};

struct Tr909CtrlWidget : rack::ModuleWidget {
    Tr909CtrlWidget(Tr909Ctrl* module) {
        setModule(module);

        auto* panel = new Tr909CtrlPanel;
        panel->box.size = AgentLayout::panelSize_4HP();
        addChild(panel);
        box.size = panel->box.size;

        addChild(createWidget<rack::ScrewSilver>(Vec(0, 0)));
        addChild(createWidget<rack::ScrewSilver>(Vec(0, RACK_GRID_HEIGHT - 15)));

        constexpr float cx_mm = 10.16f;  // 4HP / 2

        addParam(createParamCentered<rack::RoundBlackKnob>(
            mm2px(Vec(cx_mm, 40.f)), module, Tr909Ctrl::ACCENT_AMT_PARAM));
        addInput(createInputCentered<rack::PJ301MPort>(
            mm2px(Vec(cx_mm, 64.f)), module, Tr909Ctrl::ACCENT_AMT_CV_INPUT));

        addParam(createParamCentered<rack::RoundBlackKnob>(
            mm2px(Vec(cx_mm, 90.f)), module, Tr909Ctrl::MASTER_VOL_PARAM));
        addInput(createInputCentered<rack::PJ301MPort>(
            mm2px(Vec(cx_mm, 114.f)), module, Tr909Ctrl::MASTER_VOL_CV_INPUT));
    }
};

rack::Model* modelTr909Ctrl = createModel<Tr909Ctrl, Tr909CtrlWidget>("Tr909Ctrl");
