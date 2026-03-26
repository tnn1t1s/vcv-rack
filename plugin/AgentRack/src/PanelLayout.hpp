#pragma once
#include <rack.hpp>

/**
 * PanelLayout -- shared grid constants for AgentRack module panels.
 *
 * All measurements are in millimetres unless noted.  Modules declare which
 * template they use; anything that fits the same shape shares the same pixel
 * grid, so ports across adjacent modules are always horizontally aligned.
 *
 * ┌─────────────────────────────────────────────────────────┐
 * │ Template   │ HP │  Width  │ Rows │ Use                  │
 * ├─────────────────────────────────────────────────────────┤
 * │ T_8HP_6ROW │  8 │ 40.64mm │  6   │ Noise, Attenuate     │
 * │ T_8HP_FREE │  8 │ 40.64mm │  --  │ Saphire, Crinkle     │
 * │ T_6HP_FREE │  6 │ 30.48mm │  --  │ ADSR, Ladder         │
 * └─────────────────────────────────────────────────────────┘
 *
 * Adding a new template:
 *   1. Define WIDTH_mm, and any named constants below.
 *   2. Add a drawScrews_*() overload.
 *   3. Document in the table above.
 *
 * Row grid (T_8HP_6ROW):
 *   Title bar centre:  y = 10px (draws "XXX" label in 20px bar)
 *   Row centres (mm):  26, 43, 60, 77, 94, 111
 *   Spacing:           17mm between rows
 *   Top margin:        26mm  (room for title + screw)
 *   Bottom margin:     17.5mm (128.5 - 111)
 */

namespace AgentLayout {

// ── Panel heights (all modules are standard 3U = 128.5mm) ──────────────────
static constexpr float PANEL_H = 128.5f;

// ── Standard widths ─────────────────────────────────────────────────────────
static constexpr float W_4HP  = 20.32f;
static constexpr float W_6HP  = 30.48f;
static constexpr float W_8HP  = 40.64f;

// ── Title bar ───────────────────────────────────────────────────────────────
static constexpr float TITLE_BAR_H_PX = 20.f;   // pixels (Rack native coords)
static constexpr float TITLE_Y_PX     = 10.f;   // center y of title text (px)

// ── 6-row grid (shared by Noise, Attenuate, and any future 6-row module) ────
static constexpr int   ROWS         = 6;
static constexpr float ROW_Y[ROWS]  = { 26.f, 43.f, 60.f, 77.f, 94.f, 111.f };
static constexpr float ROW_SPACING  = 17.f;   // mm between row centres

// ── Column x positions for 8HP panel ────────────────────────────────────────
static constexpr float CX_8HP    = 20.32f;   // horizontal centre
static constexpr float LEFT_8HP  =  7.f;     // left jack / label column
static constexpr float MID_8HP   = 20.32f;   // knob centre
static constexpr float RIGHT_8HP = 33.64f;   // right jack column

// ── Column x positions for 6HP panel ────────────────────────────────────────
static constexpr float CX_6HP    = 15.24f;
static constexpr float LEFT_6HP  =  6.f;
static constexpr float RIGHT_6HP = 24.5f;

// ── Screw helpers ────────────────────────────────────────────────────────────

inline void addScrews_8HP(rack::ModuleWidget* w) {
    using namespace rack;
    w->addChild(createWidget<ThemedScrew>(Vec(1 * RACK_GRID_WIDTH, 0)));
    w->addChild(createWidget<ThemedScrew>(Vec(6 * RACK_GRID_WIDTH, 0)));
    w->addChild(createWidget<ThemedScrew>(Vec(1 * RACK_GRID_WIDTH, RACK_GRID_HEIGHT - RACK_GRID_WIDTH)));
    w->addChild(createWidget<ThemedScrew>(Vec(6 * RACK_GRID_WIDTH, RACK_GRID_HEIGHT - RACK_GRID_WIDTH)));
}

inline void addScrews_6HP(rack::ModuleWidget* w) {
    using namespace rack;
    w->addChild(createWidget<ThemedScrew>(Vec(0,                  0)));
    w->addChild(createWidget<ThemedScrew>(Vec(4 * RACK_GRID_WIDTH, 0)));
    w->addChild(createWidget<ThemedScrew>(Vec(0,                  RACK_GRID_HEIGHT - RACK_GRID_WIDTH)));
    w->addChild(createWidget<ThemedScrew>(Vec(4 * RACK_GRID_WIDTH, RACK_GRID_HEIGHT - RACK_GRID_WIDTH)));
}

// ── Panel size helpers ───────────────────────────────────────────────────────
// Use RACK_GRID_WIDTH/HEIGHT directly -- mm2px(128.5) gives 379.43px which
// does NOT equal RACK_GRID_HEIGHT (380px), causing addModule to throw when
// a module is dragged in from the browser.

inline rack::math::Vec panelSize_8HP() {
    return rack::math::Vec(8.f * rack::RACK_GRID_WIDTH, rack::RACK_GRID_HEIGHT);
}
inline rack::math::Vec panelSize_6HP() {
    return rack::math::Vec(6.f * rack::RACK_GRID_WIDTH, rack::RACK_GRID_HEIGHT);
}
inline rack::math::Vec panelSize_4HP() {
    return rack::math::Vec(4.f * rack::RACK_GRID_WIDTH, rack::RACK_GRID_HEIGHT);
}

} // namespace AgentLayout
