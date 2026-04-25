#include <rack.hpp>
#include "AgentModule.hpp"
#include "PanelLayout.hpp"
#include "agentrack/signal/AttenuateCore.hpp"

using namespace rack;
extern Plugin* pluginInstance;
namespace AttenuateSignal = AgentRack::Signal::Attenuate;

/**
 * Attenuate -- 8-channel labeled macro/attenuator with per-row output modes.
 *
 * Each row is either:
 *   - a CV attenuator (IN patched): OUT = IN * scale
 *   - a macro knob   (IN unpatched): OUT = f(scale) where f depends on the
 *                                    row's output mode.
 *
 * Output modes (unpatched case):
 *   UNIPOLAR_10  : OUT = scale * 10V           (default, volume-like)
 *   BIPOLAR_5    : OUT = (scale - 0.5) * 10V   (general +/-5V CV)
 *   VOCT_1OCT    : OUT = (scale - 0.5) * 2V    (+/-1V = +/-1 octave V/Oct)
 *   VOCT_2OCT    : OUT = (scale - 0.5) * 4V    (+/-2V = +/-2 octaves)
 *
 * Rack IDs (stable, never reorder):
 *   Params:  SCALE_0=0 .. SCALE_7=7
 *   Inputs:  IN_0=0    .. IN_7=7
 *   Outputs: OUT_0=0   .. OUT_7=7
 *
 * Labels (std::string per row) and modes (enum per row) serialize with the
 * patch. Both can be set from the right-click menu or written into the
 * module's data JSON at patch-build time. Agents discover the affordance
 * via discovered/AgentRack/Attenuate/<version>.json -> row_config.
 */

struct Attenuate : AgentModule {

    enum ParamId  {
        SCALE_0, SCALE_1, SCALE_2, SCALE_3, SCALE_4, SCALE_5, SCALE_6, SCALE_7,
        NUM_PARAMS
    };
    enum InputId  {
        IN_0, IN_1, IN_2, IN_3, IN_4, IN_5, IN_6, IN_7,
        NUM_INPUTS
    };
    enum OutputId {
        OUT_0, OUT_1, OUT_2, OUT_3, OUT_4, OUT_5, OUT_6, OUT_7,
        NUM_OUTPUTS
    };

    std::string labels[AttenuateSignal::kRows];
    int modes[AttenuateSignal::kRows] = {
        AttenuateSignal::MODE_UNIPOLAR_10, AttenuateSignal::MODE_UNIPOLAR_10,
        AttenuateSignal::MODE_UNIPOLAR_10, AttenuateSignal::MODE_UNIPOLAR_10,
        AttenuateSignal::MODE_UNIPOLAR_10, AttenuateSignal::MODE_UNIPOLAR_10,
        AttenuateSignal::MODE_UNIPOLAR_10, AttenuateSignal::MODE_UNIPOLAR_10,
    };

    Attenuate() {
        config(NUM_PARAMS, NUM_INPUTS, NUM_OUTPUTS);
        for (int i = 0; i < AttenuateSignal::kRows; i++) {
            configParam (SCALE_0 + i, 0.f, 1.f, 1.f, string::f("Scale %d", i + 1), "%", 0.f, 100.f);
            configInput (IN_0    + i, string::f("In %d",  i + 1));
            configOutput(OUT_0   + i, string::f("Out %d", i + 1));
        }
    }

    void process(const ProcessArgs&) override {
        for (int i = 0; i < AttenuateSignal::kRows; i++) {
            float scale = params[SCALE_0 + i].getValue();
            float input = inputs[IN_0 + i].getVoltage();
            bool connected = inputs[IN_0 + i].isConnected();
            outputs[OUT_0 + i].setVoltage(AttenuateSignal::rowOutput(connected, input, scale, modes[i]));
        }
    }

    json_t* dataToJson() override {
        json_t* root = json_object();
        json_t* labelsArr = json_array();
        json_t* modesArr  = json_array();
        for (int i = 0; i < AttenuateSignal::kRows; i++) {
            json_array_append_new(labelsArr, json_string(labels[i].c_str()));
            json_array_append_new(modesArr,
                                  json_string(AttenuateSignal::MODE_KEYS[AttenuateSignal::normalizeMode(modes[i])]));
        }
        json_object_set_new(root, "labels", labelsArr);
        json_object_set_new(root, "modes",  modesArr);
        return root;
    }

    void dataFromJson(json_t* root) override {
        json_t* labelsArr = json_object_get(root, "labels");
        if (labelsArr && json_is_array(labelsArr)) {
            for (int i = 0; i < AttenuateSignal::kRows && i < (int)json_array_size(labelsArr); i++) {
                json_t* s = json_array_get(labelsArr, i);
                if (s && json_is_string(s)) labels[i] = json_string_value(s);
            }
        }
        json_t* modesArr = json_object_get(root, "modes");
        if (modesArr && json_is_array(modesArr)) {
            for (int i = 0; i < AttenuateSignal::kRows && i < (int)json_array_size(modesArr); i++) {
                json_t* s = json_array_get(modesArr, i);
                if (s && json_is_string(s))
                    modes[i] = AttenuateSignal::normalizeMode(
                        AttenuateSignal::modeFromKey(json_string_value(s)));
            }
        }
    }
};


// ---------------------------------------------------------------------------
// Panel -- 8HP, labels + range tags
// ---------------------------------------------------------------------------

struct AttenuatePanel : rack::widget::Widget {
    Attenuate* module = nullptr;

    void draw(const DrawArgs& args) override {
        int imgHandle = 0;
        try {
            auto img = APP->window->loadImage(
                asset::plugin(pluginInstance, "res/Attenuate-bg.jpg"));
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
            nvgFillColor(args.vg, nvgRGB(0, 80, 80));
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
        nvgText(args.vg, box.size.x / 2.f, 10.f, "ATT", NULL);

        const float* ys = AgentLayout::ROW_Y_8;
        for (int i = 0; i < AttenuateSignal::kRows; i++) {
            // Small row index on the far left
            char buf[4];
            snprintf(buf, sizeof(buf), "%d", i + 1);
            nvgFontSize(args.vg, 5.5f);
            nvgFillColor(args.vg, nvgRGBA(255, 255, 255, 160));
            nvgTextAlign(args.vg, NVG_ALIGN_LEFT | NVG_ALIGN_MIDDLE);
            nvgText(args.vg, mm2px(1.5f), mm2px(ys[i]), buf, NULL);

            if (module) {
                // User label above the knob (yellow, 6.5pt)
                if (!module->labels[i].empty()) {
                    nvgFontSize(args.vg, 6.5f);
                    nvgFillColor(args.vg, nvgRGB(255, 220, 0));
                    nvgTextAlign(args.vg, NVG_ALIGN_CENTER | NVG_ALIGN_BOTTOM);
                    nvgText(args.vg,
                            mm2px(AgentLayout::MID_8HP),
                            mm2px(ys[i] - 4.2f),
                            module->labels[i].c_str(), NULL);
                }
                // Range tag below the knob (dim white, 4.5pt)
                int m = AttenuateSignal::normalizeMode(module->modes[i]);
                nvgFontSize(args.vg, 4.5f);
                nvgFillColor(args.vg, nvgRGBA(255, 255, 255, 140));
                nvgTextAlign(args.vg, NVG_ALIGN_CENTER | NVG_ALIGN_TOP);
                nvgText(args.vg,
                        mm2px(AgentLayout::MID_8HP),
                        mm2px(ys[i] + 4.2f),
                        AttenuateSignal::MODE_TAGS[m], NULL);
            }
        }
    }
};


// ---------------------------------------------------------------------------
// Context menu: editable label + range submenu per row
// ---------------------------------------------------------------------------

struct LabelField : rack::ui::TextField {
    Attenuate* module = nullptr;
    int index = 0;

    LabelField() { box.size.x = 140.f; }

    void onChange(const ChangeEvent& e) override {
        rack::ui::TextField::onChange(e);
        if (module) module->labels[index] = text;
    }
};


// ---------------------------------------------------------------------------
// Widget -- 8HP
// ---------------------------------------------------------------------------

struct AttenuateWidget : rack::ModuleWidget {

    AttenuateWidget(Attenuate* module) {
        setModule(module);

        auto* panel = new AttenuatePanel;
        panel->module = module;
        panel->box.size = AgentLayout::panelSize_8HP();
        addChild(panel);
        box.size = panel->box.size;

        AgentLayout::addScrews_8HP(this);

        float in_x  = AgentLayout::LEFT_8HP;
        float kn_x  = AgentLayout::MID_8HP;
        float out_x = AgentLayout::RIGHT_8HP;
        const float* ys = AgentLayout::ROW_Y_8;

        for (int i = 0; i < AttenuateSignal::kRows; i++) {
            addInput(createInputCentered<rack::PJ301MPort>(
                mm2px(rack::Vec(in_x, ys[i])), module, Attenuate::IN_0 + i));
            addParam(createParamCentered<rack::RoundSmallBlackKnob>(
                mm2px(rack::Vec(kn_x, ys[i])), module, Attenuate::SCALE_0 + i));
            addOutput(createOutputCentered<rack::PJ301MPort>(
                mm2px(rack::Vec(out_x, ys[i])), module, Attenuate::OUT_0 + i));
        }
    }

    void appendContextMenu(rack::ui::Menu* menu) override {
        auto* m = dynamic_cast<Attenuate*>(this->module);
        if (!m) return;
        menu->addChild(new rack::ui::MenuSeparator);
        menu->addChild(rack::createMenuLabel("Row labels & ranges"));
        for (int i = 0; i < AttenuateSignal::kRows; i++) {
            // Label editor
            auto* tf = new LabelField;
            tf->module = m;
            tf->index  = i;
            tf->text   = m->labels[i];
            tf->placeholder = rack::string::f("Row %d label", i + 1);
            menu->addChild(tf);

            // Range submenu
            int rowIdx = i;
            menu->addChild(rack::createSubmenuItem(
                rack::string::f("  Row %d range: %s", i + 1,
                                AttenuateSignal::MODE_TAGS[AttenuateSignal::normalizeMode(m->modes[i])]),
                "",
                [m, rowIdx](rack::ui::Menu* sub) {
                    for (int j = 0; j < AttenuateSignal::kModeCount; j++) {
                        int mode = j;
                        sub->addChild(rack::createCheckMenuItem(
                            AttenuateSignal::MODE_LABELS[j], "",
                            [m, rowIdx, mode]() { return m->modes[rowIdx] == mode; },
                            [m, rowIdx, mode]() { m->modes[rowIdx] = mode; }));
                    }
                }));
        }
    }
};


rack::Model* modelAttenuate = createModel<Attenuate, AttenuateWidget>("Attenuate");
