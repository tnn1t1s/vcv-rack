#include <rack.hpp>
#include "AgentModule.hpp"
#include "PanelLayout.hpp"
#include <cmath>

using namespace rack;
extern Plugin* pluginInstance;

/**
 * Noise -- six spectral noise generators, output only.
 *
 * All outputs are independent, always-on, ±5V.
 *
 * Types (enum order is stable, never reorder):
 *   WHITE   (0) -- flat spectrum, uniform random
 *   PINK    (1) -- 1/f, Kellet 7-pole algorithm
 *   BROWN   (2) -- 1/f², leaky random walk (Brownian)
 *   BLUE    (3) -- f, first-difference of white
 *   VIOLET  (4) -- f², second-difference of white
 *   CRACKLE (5) -- sparse impulses (~15/sec), for IR auditioning
 *
 * Rack IDs:
 *   Params:  none
 *   Inputs:  none
 *   Outputs: WHITE=0, PINK=1, BROWN=2, BLUE=3, VIOLET=4, CRACKLE=5
 */

struct Noise : AgentModule {

    enum ParamId  { NUM_PARAMS  = 0 };
    enum InputId  { NUM_INPUTS  = 0 };
    enum OutputId {
        WHITE_OUTPUT, PINK_OUTPUT, BROWN_OUTPUT,
        BLUE_OUTPUT, VIOLET_OUTPUT, CRACKLE_OUTPUT,
        NUM_OUTPUTS
    };

    // Pink noise state -- Kellet 7-pole algorithm
    float pk0=0, pk1=0, pk2=0, pk3=0, pk4=0, pk5=0, pk6=0;

    // Brown noise state
    float brown = 0.f;

    // Blue/Violet noise state
    float prev_white = 0.f;
    float prev_blue  = 0.f;

    Noise() {
        config(NUM_PARAMS, NUM_INPUTS, NUM_OUTPUTS);
        configOutput(WHITE_OUTPUT,   "White");
        configOutput(PINK_OUTPUT,    "Pink");
        configOutput(BROWN_OUTPUT,   "Brown");
        configOutput(BLUE_OUTPUT,    "Blue");
        configOutput(VIOLET_OUTPUT,  "Violet");
        configOutput(CRACKLE_OUTPUT, "Crackle");
    }

    void process(const ProcessArgs&) override {
        float w = random::uniform() * 2.f - 1.f;  // white, ±1

        // --- Pink (Kellet 7-pole 1/f) ---
        pk0 = 0.99886f * pk0 + w * 0.0555179f;
        pk1 = 0.99332f * pk1 + w * 0.0750759f;
        pk2 = 0.96900f * pk2 + w * 0.1538520f;
        pk3 = 0.86650f * pk3 + w * 0.3104856f;
        pk4 = 0.55000f * pk4 + w * 0.5329522f;
        pk5 = -0.7616f * pk5 - w * 0.0168980f;
        float pink = (pk0 + pk1 + pk2 + pk3 + pk4 + pk5 + pk6 + w * 0.5362f) * 0.11f;
        pk6 = w * 0.115926f;

        // --- Brown (leaky random walk, 1/f²) ---
        brown = (brown + 0.02f * w) * 0.998f;
        // Steady-state RMS ≈ 0.02 / sqrt(1-0.998²) ≈ 0.316; scale × 3.f → ~±1
        float br = brown * 3.f;

        // --- Blue (first difference of white, f) ---
        float blue  = (w - prev_white) * 0.5f;  // divide by 2: diff range [-2,2]→[-1,1]
        prev_white  = w;

        // --- Violet (second difference, f²) ---
        float violet = (blue - prev_blue) * 0.5f;
        prev_blue    = blue;

        // --- Crackle (~15 sparse impulses/sec at 44100Hz) ---
        float crackle = 0.f;
        if (random::uniform() < 0.00034f)
            crackle = (random::uniform() > 0.5f) ? 1.f : -1.f;

        // Output: all signals scaled to ±5V
        outputs[WHITE_OUTPUT].setVoltage(w      * 5.f);
        outputs[PINK_OUTPUT].setVoltage(pink    * 5.f);
        outputs[BROWN_OUTPUT].setVoltage(br     * 5.f);
        outputs[BLUE_OUTPUT].setVoltage(blue    * 5.f);
        outputs[VIOLET_OUTPUT].setVoltage(violet * 5.f);
        outputs[CRACKLE_OUTPUT].setVoltage(crackle * 5.f);
    }

    std::string getManifest() const override {
        return R"({
  "module_id": "agentrack.noise.v1",
  "ensemble_role": "source",
  "ports": [
    {"name": "WHITE",   "direction": "output", "signal_class": "audio", "semantic_role": "audio_out"},
    {"name": "PINK",    "direction": "output", "signal_class": "audio", "semantic_role": "audio_out"},
    {"name": "BROWN",   "direction": "output", "signal_class": "audio", "semantic_role": "audio_out"},
    {"name": "BLUE",    "direction": "output", "signal_class": "audio", "semantic_role": "audio_out"},
    {"name": "VIOLET",  "direction": "output", "signal_class": "audio", "semantic_role": "audio_out"},
    {"name": "CRACKLE", "direction": "output", "signal_class": "audio", "semantic_role": "audio_out"}
  ],
  "params": [],
  "guarantees": [
    "all outputs always active, ±5V",
    "WHITE: flat spectrum",
    "PINK: 1/f equal-power per octave",
    "BROWN: 1/f² Brownian motion, low-passed",
    "BLUE: first-difference of white, boosted highs",
    "VIOLET: second-difference of white, very bright",
    "CRACKLE: sparse impulses (~15/sec) for IR auditioning"
  ]
})";
    }
};


// ---------------------------------------------------------------------------
// Panel -- 4HP, dark with colour-coded labels
// ---------------------------------------------------------------------------

struct NoisePanel : rack::widget::Widget {
    void draw(const DrawArgs& args) override {
        // Background
        nvgBeginPath(args.vg);
        nvgRect(args.vg, 0, 0, box.size.x, box.size.y);
        nvgFillColor(args.vg, nvgRGB(10, 10, 25));
        nvgFill(args.vg);

        // Title bar
        nvgBeginPath(args.vg);
        nvgRect(args.vg, 0, 0, box.size.x, 20.f);
        nvgFillColor(args.vg, nvgRGBA(0, 0, 0, 200));
        nvgFill(args.vg);

        nvgFontSize(args.vg, 7.f);
        nvgTextAlign(args.vg, NVG_ALIGN_CENTER | NVG_ALIGN_MIDDLE);
        nvgFillColor(args.vg, nvgRGB(255, 255, 255));
        nvgText(args.vg, box.size.x / 2.f, 10.f, "NOI", NULL);

        // Labels right-aligned, vertically centred with port (port at RIGHT_8HP=33.64mm)
        // Row Y positions from AgentLayout::ROW_Y -- shared with Attenuate for alignment
        static const NVGcolor COLS[AgentLayout::ROWS] = {
            nvgRGB(255, 255, 255),  // WHITE
            nvgRGB(255, 130, 180),  // PINK
            nvgRGB(200, 140,  60),  // BROWN
            nvgRGB( 80, 160, 255),  // BLUE
            nvgRGB(180,  80, 255),  // VIOLET
            nvgRGB(255, 160,  40),  // CRACKLE
        };
        static const char* const LABELS[AgentLayout::ROWS] = {
            "WHITE", "PINK", "BROWN", "BLUE", "VIOLET", "CRACKLE"
        };

        nvgFontSize(args.vg, 6.5f);
        nvgTextAlign(args.vg, NVG_ALIGN_RIGHT | NVG_ALIGN_MIDDLE);
        for (int i = 0; i < AgentLayout::ROWS; i++) {
            nvgFillColor(args.vg, COLS[i]);
            nvgText(args.vg, mm2px(AgentLayout::RIGHT_8HP - 6.f),
                    mm2px(AgentLayout::ROW_Y[i]), LABELS[i], NULL);
        }
    }
};


// ---------------------------------------------------------------------------
// Widget -- 8HP  (matches suite standard: Attenuate, Saphire, Crinkle)
// ---------------------------------------------------------------------------

struct NoiseWidget : rack::ModuleWidget {

    NoiseWidget(Noise* module) {
        setModule(module);

        auto* panel = new NoisePanel;
        panel->box.size = AgentLayout::panelSize_8HP();
        addChild(panel);
        box.size = panel->box.size;

        AgentLayout::addScrews_8HP(this);

        // Ports on right side (x=28mm); labels drawn by panel on left
        float px = AgentLayout::RIGHT_8HP;
        // Row Y from shared template -- identical to Attenuate's row grid
        const float* ys = AgentLayout::ROW_Y;
        int ids[] = {
            Noise::WHITE_OUTPUT, Noise::PINK_OUTPUT, Noise::BROWN_OUTPUT,
            Noise::BLUE_OUTPUT,  Noise::VIOLET_OUTPUT, Noise::CRACKLE_OUTPUT
        };
        for (int i = 0; i < 6; i++)
            addOutput(createOutputCentered<rack::PJ301MPort>(mm2px(rack::Vec(px, ys[i])), module, ids[i]));
    }
};


rack::Model* modelNoise = createModel<Noise, NoiseWidget>("Noise");
