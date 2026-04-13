#include <rack.hpp>
#include "AgentModule.hpp"
#include "PanelLayout.hpp"

using namespace rack;
extern Plugin* pluginInstance;

/**
 * Attenuate -- 6-channel CV/audio attenuator.
 *
 * Each row:  OUT = IN × SCALE
 *
 * Rack IDs (stable, never reorder):
 *   Params:  SCALE_0=0 .. SCALE_5=5
 *   Inputs:  IN_0=0    .. IN_5=5
 *   Outputs: OUT_0=0   .. OUT_5=5
 *
 * Row 0 IDs match the old single-channel Attenuate, so patches built against
 * the original module are unaffected.
 */

static constexpr int ATT_ROWS = 6;

struct Attenuate : AgentModule {

    enum ParamId  {
        SCALE_0, SCALE_1, SCALE_2, SCALE_3, SCALE_4, SCALE_5,
        NUM_PARAMS
    };
    enum InputId  {
        IN_0, IN_1, IN_2, IN_3, IN_4, IN_5,
        NUM_INPUTS
    };
    enum OutputId {
        OUT_0, OUT_1, OUT_2, OUT_3, OUT_4, OUT_5,
        NUM_OUTPUTS
    };

    Attenuate() {
        config(NUM_PARAMS, NUM_INPUTS, NUM_OUTPUTS);
        for (int i = 0; i < ATT_ROWS; i++) {
            configParam (SCALE_0 + i, 0.f, 1.f, 1.f, string::f("Scale %d", i + 1), "%", 0.f, 100.f);
            configInput (IN_0    + i, string::f("In %d",  i + 1));
            configOutput(OUT_0   + i, string::f("Out %d", i + 1));
        }
    }

    void process(const ProcessArgs&) override {
        for (int i = 0; i < ATT_ROWS; i++) {
            float scale = params[SCALE_0 + i].getValue();
            float in    = inputs[IN_0 + i].getVoltage();
            outputs[OUT_0 + i].setVoltage(in * scale);
        }
    }

};


// ---------------------------------------------------------------------------
// Panel -- 8HP, row labels on left
// ---------------------------------------------------------------------------

struct AttenuatePanel : rack::widget::Widget {
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

        // Column headers
        const float* ys = AgentLayout::ROW_Y;
        nvgFontSize(args.vg, 5.5f);
        nvgFillColor(args.vg, nvgRGBA(255, 255, 255, 160));
        nvgTextAlign(args.vg, NVG_ALIGN_CENTER | NVG_ALIGN_BOTTOM);
        for (int i = 0; i < ATT_ROWS; i++) {
            float y = mm2px(ys[i]) - mm2px(4.f);
            // Row number on far left
            char buf[4];
            snprintf(buf, sizeof(buf), "%d", i + 1);
            nvgTextAlign(args.vg, NVG_ALIGN_LEFT | NVG_ALIGN_MIDDLE);
            nvgText(args.vg, mm2px(1.5f), mm2px(ys[i]), buf, NULL);
            (void)y;
        }
    }
};


// ---------------------------------------------------------------------------
// Widget -- 8HP
// ---------------------------------------------------------------------------

struct AttenuateWidget : rack::ModuleWidget {

    AttenuateWidget(Attenuate* module) {
        setModule(module);

        auto* panel = new AttenuatePanel;
        panel->box.size = AgentLayout::panelSize_8HP();
        addChild(panel);
        box.size = panel->box.size;

        AgentLayout::addScrews_8HP(this);

        // Row layout on 8HP (40.64mm): IN=7mm, knob=20.32mm, OUT=33.64mm
        float in_x        = AgentLayout::LEFT_8HP;
        float kn_x        = AgentLayout::MID_8HP;
        float out_x       = AgentLayout::RIGHT_8HP;
        const float* ys   = AgentLayout::ROW_Y;

        for (int i = 0; i < ATT_ROWS; i++) {
            addInput(createInputCentered<rack::PJ301MPort>(
                mm2px(rack::Vec(in_x, ys[i])), module, Attenuate::IN_0 + i));
            addParam(createParamCentered<rack::RoundSmallBlackKnob>(
                mm2px(rack::Vec(kn_x, ys[i])), module, Attenuate::SCALE_0 + i));
            addOutput(createOutputCentered<rack::PJ301MPort>(
                mm2px(rack::Vec(out_x, ys[i])), module, Attenuate::OUT_0 + i));
        }
    }
};


rack::Model* modelAttenuate = createModel<Attenuate, AttenuateWidget>("Attenuate");
