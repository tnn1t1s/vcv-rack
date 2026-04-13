#include <rack.hpp>
#include "AgentModule.hpp"
#include "PanelLayout.hpp"

using namespace rack;
extern Plugin* pluginInstance;

/**
 * ClockDiv -- Clock divider with /2, /4, /8, /16, /32 outputs.
 *
 * Replacement for Autodafe/ClockDivider (not available on macOS ARM64).
 * Each output is a 50% duty-cycle square wave at the divided frequency,
 * toggling on each rising edge of the clock input.
 *
 * Rack IDs (stable, never reorder):
 *   Inputs:  CLOCK_INPUT=0, RESET_INPUT=1
 *   Outputs: DIV2_OUTPUT=0, DIV4_OUTPUT=1, DIV8_OUTPUT=2,
 *            DIV16_OUTPUT=3, DIV32_OUTPUT=4
 */
struct ClockDiv : AgentModule {

    enum InputId  { CLOCK_INPUT, RESET_INPUT, NUM_INPUTS };
    enum OutputId { DIV2_OUTPUT, DIV4_OUTPUT, DIV8_OUTPUT,
                    DIV16_OUTPUT, DIV32_OUTPUT, NUM_OUTPUTS };

    dsp::SchmittTrigger clockTrig;
    dsp::SchmittTrigger resetTrig;
    int counter = 0;

    ClockDiv() {
        config(0, NUM_INPUTS, NUM_OUTPUTS);
        configInput(CLOCK_INPUT, "Clock");
        configInput(RESET_INPUT, "Reset");
        configOutput(DIV2_OUTPUT,  "/2");
        configOutput(DIV4_OUTPUT,  "/4");
        configOutput(DIV8_OUTPUT,  "/8");
        configOutput(DIV16_OUTPUT, "/16");
        configOutput(DIV32_OUTPUT, "/32");
    }

    void process(const ProcessArgs& args) override {
        if (resetTrig.process(inputs[RESET_INPUT].getVoltage()))
            counter = 0;

        if (clockTrig.process(inputs[CLOCK_INPUT].getVoltage())) {
            counter++;
            outputs[DIV2_OUTPUT ].setVoltage((counter % 2  == 0) ? 10.f : 0.f);
            outputs[DIV4_OUTPUT ].setVoltage((counter % 4  == 0) ? 10.f : 0.f);
            outputs[DIV8_OUTPUT ].setVoltage((counter % 8  == 0) ? 10.f : 0.f);
            outputs[DIV16_OUTPUT].setVoltage((counter % 16 == 0) ? 10.f : 0.f);
            outputs[DIV32_OUTPUT].setVoltage((counter % 32 == 0) ? 10.f : 0.f);
        }
    }

};


// ---------------------------------------------------------------------------
// Panel -- 8HP standard template (matches Noise, Attenuate suite)
// ---------------------------------------------------------------------------

struct ClockDivPanel : rack::widget::Widget {
    void draw(const DrawArgs& args) override {
        AgentLayout::drawStandardPanel(
            args.vg, box.size,
            /*imgHandle=*/0,
            nvgRGB(22, 22, 30),   // dark navy fallback
            "CLK/",               // title
            nvgRGB(255, 200, 0)   // amber title
        );

        // Left column: input labels
        static const char* inLabels[] = { "CLK", "RST" };
        nvgFontSize(args.vg, 6.5f);
        nvgTextAlign(args.vg, NVG_ALIGN_LEFT | NVG_ALIGN_MIDDLE);
        nvgFillColor(args.vg, nvgRGB(140, 210, 140));
        for (int i = 0; i < 2; i++)
            nvgText(args.vg,
                    mm2px(AgentLayout::LEFT_8HP + 1.f),
                    mm2px(AgentLayout::ROW_Y[i]),
                    inLabels[i], nullptr);

        // Right column: output labels
        static const char* outLabels[] = { "/2", "/4", "/8", "/16", "/32" };
        nvgTextAlign(args.vg, NVG_ALIGN_RIGHT | NVG_ALIGN_MIDDLE);
        nvgFillColor(args.vg, nvgRGB(200, 200, 200));
        for (int i = 0; i < 5; i++)
            nvgText(args.vg,
                    mm2px(AgentLayout::RIGHT_8HP - 1.f),
                    mm2px(AgentLayout::ROW_Y[i]),
                    outLabels[i], nullptr);
    }
};


// ---------------------------------------------------------------------------
// Widget -- 8HP standard (matches suite)
// ---------------------------------------------------------------------------

struct ClockDivWidget : rack::ModuleWidget {
    ClockDivWidget(ClockDiv* module) {
        setModule(module);

        auto* panel = new ClockDivPanel;
        panel->box.size = AgentLayout::panelSize_8HP();
        addChild(panel);
        box.size = panel->box.size;

        AgentLayout::addScrews_8HP(this);

        float lx = AgentLayout::LEFT_8HP;
        float rx = AgentLayout::RIGHT_8HP;
        const float* ys = AgentLayout::ROW_Y;

        // Inputs (left column, rows 0-1)
        addInput(createInputCentered<rack::PJ301MPort>(mm2px(rack::Vec(lx, ys[0])), module, ClockDiv::CLOCK_INPUT));
        addInput(createInputCentered<rack::PJ301MPort>(mm2px(rack::Vec(lx, ys[1])), module, ClockDiv::RESET_INPUT));

        // Outputs (right column, rows 0-4)
        addOutput(createOutputCentered<rack::PJ301MPort>(mm2px(rack::Vec(rx, ys[0])), module, ClockDiv::DIV2_OUTPUT));
        addOutput(createOutputCentered<rack::PJ301MPort>(mm2px(rack::Vec(rx, ys[1])), module, ClockDiv::DIV4_OUTPUT));
        addOutput(createOutputCentered<rack::PJ301MPort>(mm2px(rack::Vec(rx, ys[2])), module, ClockDiv::DIV8_OUTPUT));
        addOutput(createOutputCentered<rack::PJ301MPort>(mm2px(rack::Vec(rx, ys[3])), module, ClockDiv::DIV16_OUTPUT));
        addOutput(createOutputCentered<rack::PJ301MPort>(mm2px(rack::Vec(rx, ys[4])), module, ClockDiv::DIV32_OUTPUT));
    }
};

rack::Model* modelClockDiv = createModel<ClockDiv, ClockDivWidget>("ClockDiv");
