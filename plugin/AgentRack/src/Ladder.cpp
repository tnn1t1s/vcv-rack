#include <rack.hpp>
#include "AgentModule.hpp"
#include <cmath>

using namespace rack;
extern Plugin* pluginInstance;

/**
 * Rungs -- TB-303-lineage diode ladder filter with stage-spread topology control.
 *
 * DSP lineage:
 *   Huovilainen A. (2004). "Improved Digital Models of the Moog VCF."
 *   Proceedings of the International Conference on Digital Audio Effects (DAFx-04),
 *   Naples, Italy, October 2004, pp. 153-160.
 *
 *   The Moog transistor ladder and the Roland TB-303 diode ladder share identical
 *   cascade topology -- four first-order lowpass sections, each implementing a
 *   differential pair (transistors) or clipper pair (diodes).  The nonlinearity
 *   in both cases is well-approximated by tanh.  Huovilainen formalised this:
 *
 *     Per stage k (0..3), bilinear-transform update:
 *       y_k[n] = y_k[n-1] + g * (tanh(x_k[n]) - tanh(y_k[n-1]))
 *       where g = tan(pi * f_c / f_s)
 *
 *     Resonance feedback (one-sample delay, stable):
 *       x_0 = v_in - 4k * y_3[n-1]    k = normalized resonance 0..1
 *
 *   The tanh on both terms captures the transistor/diode saturation: at low
 *   amplitudes the filter is linear; at high resonance and drive levels the
 *   nonlinearity introduces the characteristic acid squelch.
 *
 * AgentRack extension -- SPREAD and SHAPE:
 *   In a standard Moog/303 ladder all four poles share the same cutoff f_c.
 *   SPREAD and SHAPE independently detune each pole, opening topologies
 *   unavailable in the original circuit:
 *
 *   SPREAD (0..1): scales the per-pole offset amount.
 *     0 = all poles at f_c (zero-spread invariant: identical to Huovilainen model)
 *     1 = poles offset by up to ±0.75 octave from f_c
 *
 *   SHAPE (0..1): morphs the offset distribution pattern.
 *     0 = linear gradient  -> offsets {-1.5, -0.5, +0.5, +1.5} * spread_range
 *     1 = alternating      -> offsets {-1,   +1,   -1,   +1  } * spread_range
 *
 *   Resonance feedback always uses the base cutoff g = tan(pi * f_c / f_s),
 *   not the spread values.  At SPREAD=0 the output is identical to the
 *   unmodified Huovilainen nonlinear ladder.
 *
 * 2x oversampling to suppress tanh-generated harmonics above Nyquist.
 * Output: +-5V audio.
 *
 * Rack IDs (stable, never reorder):
 *   Params:  FREQ_PARAM=0, RES_PARAM=1, SPREAD_PARAM=2, SHAPE_PARAM=3, FM_PARAM=4
 *   Inputs:  IN_INPUT=0, VOCT_INPUT=1, FM_INPUT=2
 *   Outputs: OUT_OUTPUT=0
 */


// ---------------------------------------------------------------------------
// Module
// ---------------------------------------------------------------------------

struct Ladder : AgentModule {

    enum ParamId  { FREQ_PARAM, RES_PARAM, SPREAD_PARAM, SHAPE_PARAM, MODE_PARAM, NUM_PARAMS };
    enum InputId  { IN_INPUT, CUTOFF_MOD_INPUT, RES_MOD_INPUT, SPREAD_MOD_INPUT, SHAPE_MOD_INPUT, NUM_INPUTS };
    enum OutputId { OUT_OUTPUT, NUM_OUTPUTS };

    // Per-stage state, normalized +-1 internally
    float y[4] = {};

    Ladder() {
        config(NUM_PARAMS, NUM_INPUTS, NUM_OUTPUTS);
        configParam(FREQ_PARAM,   0.f, 1.f, 0.5f, "Cutoff");
        configParam(RES_PARAM,    0.f, 1.f, 0.f,  "Resonance", "%", 0.f, 100.f);
        configParam(SPREAD_PARAM, 0.f, 1.f, 0.f,  "Spread",    "%", 0.f, 100.f);
        configParam(SHAPE_PARAM,  0.f, 1.f, 0.f,  "Shape",     "%", 0.f, 100.f);
        configSwitch(MODE_PARAM, 0.f, 2.f, 2.f, "Resonance mode",
                     {"A: freq-compensated", "B: noise-kick", "C: standard"});
        configInput(IN_INPUT,          "Audio");
        configInput(CUTOFF_MOD_INPUT,  "Cutoff mod");
        configInput(RES_MOD_INPUT,     "Resonance mod");
        configInput(SPREAD_MOD_INPUT,  "Spread mod");
        configInput(SHAPE_MOD_INPUT,   "Shape mod");
        configOutput(OUT_OUTPUT,       "Out");
    }

    void process(const ProcessArgs& args) override {
        // --- Parameters with CV mod (cv/10 maps +-5V to +-0.5 on 0..1 range) ---
        float freq_p = params[FREQ_PARAM].getValue()
                     + inputs[CUTOFF_MOD_INPUT].getVoltage() / 10.f;
        freq_p = clamp(freq_p, 0.f, 1.f);

        float res    = clamp(params[RES_PARAM].getValue()
                     + inputs[RES_MOD_INPUT].getVoltage() / 10.f,    0.f, 1.f);
        float spread = clamp(params[SPREAD_PARAM].getValue()
                     + inputs[SPREAD_MOD_INPUT].getVoltage() / 10.f, 0.f, 1.f);
        float shape  = clamp(params[SHAPE_PARAM].getValue()
                     + inputs[SHAPE_MOD_INPUT].getVoltage() / 10.f,  0.f, 1.f);

        // --- Cutoff frequency: 0..1 -> 20 Hz..20 kHz (log) ---
        float fc = 20.f * std::pow(1000.f, freq_p);

        // 2x oversampling -- use doubled sample rate for coefficient computation
        float sr_over = args.sampleRate * 2.f;
        fc = clamp(fc, 20.f, sr_over * 0.45f);

        spread = spread * spread;  // log-ish: fine at low end, dramatic at top

        // --- Per-pole offset distributions ---
        // Linear gradient: poles spaced evenly below and above fc
        // Alternating:     odd poles below, even poles above
        static const float lin_off[4] = {-1.5f, -0.5f,  0.5f, 1.5f};
        static const float alt_off[4] = {-1.0f,  1.0f, -1.0f, 1.0f};

        float g[4];
        for (int i = 0; i < 4; i++) {
            float off  = (1.f - shape) * lin_off[i] + shape * alt_off[i];
            // SPREAD=1 -> +-0.75 octave per unit offset
            float fc_i = fc * std::pow(2.f, spread * off * 1.28f); // +-1.92 oct at max spread
            fc_i = clamp(fc_i, 20.f, sr_over * 0.45f);
            g[i] = std::tan(float(M_PI) * fc_i / sr_over);
        }

        // --- Resonance mode ---
        // A=0: freq-compensated k (self-oscillates evenly across cutoff range)
        // B=1: noise-kick (small perturbation to start oscillation at any cutoff)
        // C=2: standard Huovilainen (default, as before)
        int mode = (int)params[MODE_PARAM].getValue();

        float k;
        if (mode == 0) {
            // A: raise k at low cutoffs so oscillation builds fast regardless of fc
            k = res * (4.1f + 2.5f * (1.f - freq_p));
        } else {
            k = res * 4.1f;  // B and C share the same k
        }

        // Input: +-5V -> +-1 (Huovilainen model works in normalized amplitude)
        float vin = inputs[IN_INPUT].getVoltage() / 5.f;

        // --- 2x oversampled Huovilainen nonlinear update ---
        float out = 0.f;
        for (int os = 0; os < 2; os++) {
            // B: tiny noise perturbation kicks oscillation without waiting for signal
            float noise = (mode == 1) ? (random::uniform() - 0.5f) * 0.001f : 0.f;
            float x0 = vin + noise - k * y[3];

            // 4-stage cascade: each stage y_k += g_k * (tanh(x_k) - tanh(y_k))
            y[0] += g[0] * (std::tanh(x0)   - std::tanh(y[0]));
            y[1] += g[1] * (std::tanh(y[0]) - std::tanh(y[1]));
            y[2] += g[2] * (std::tanh(y[1]) - std::tanh(y[2]));
            y[3] += g[3] * (std::tanh(y[2]) - std::tanh(y[3]));
            out  += y[3];
        }
        out /= 2.f;  // decimate

        outputs[OUT_OUTPUT].setVoltage(out * 5.f);
    }

    std::string getManifest() const override {
        return R"({
  "module_id": "agentrack.ladder.v1",
  "ensemble_role": "none",
  "ports": [
    {"name": "IN",         "direction": "input",  "signal_class": "audio", "semantic_role": "audio_in",   "required": false},
    {"name": "CUTOFF_MOD", "direction": "input",  "signal_class": "cv",    "semantic_role": "cutoff_mod", "required": false},
    {"name": "RES_MOD",    "direction": "input",  "signal_class": "cv",    "semantic_role": "res_mod",    "required": false},
    {"name": "SPREAD_MOD", "direction": "input",  "signal_class": "cv",    "semantic_role": "spread_mod", "required": false},
    {"name": "SHAPE_MOD",  "direction": "input",  "signal_class": "cv",    "semantic_role": "shape_mod",  "required": false},
    {"name": "OUT",        "direction": "output", "signal_class": "audio", "semantic_role": "filter_out"}
  ],
  "params": [
    {"name": "FREQ",   "rack_id": 0, "unit": "normalized", "scale": "log_20_20000", "min": 0.0, "max": 1.0, "default": 0.5},
    {"name": "RES",    "rack_id": 1, "unit": "normalized", "scale": "linear",       "min": 0.0, "max": 1.0, "default": 0.0},
    {"name": "SPREAD", "rack_id": 2, "unit": "normalized", "scale": "linear",       "min": 0.0, "max": 1.0, "default": 0.0},
    {"name": "SHAPE",  "rack_id": 3, "unit": "normalized", "scale": "linear",       "min": 0.0, "max": 1.0, "default": 0.0}
  ],
  "guarantees": [
    "4-pole Huovilainen nonlinear ladder filter, 24 dB/oct at SPREAD=0",
    "SPREAD=0 SHAPE=0 output is identical to the unmodified Huovilainen nonlinear model",
    "self-oscillation at RES >= 1.0",
    "VOCT tracks 1V/octave standard for cutoff modulation",
    "output is audio-rate, +-5V",
    "2x oversampled to suppress tanh-generated aliasing"
  ]
})";
    }
};


// ---------------------------------------------------------------------------
// Panel
// ---------------------------------------------------------------------------

struct LadderPanel : rack::widget::Widget {
    void draw(const DrawArgs& args) override {
        int imgHandle = 0;
        try {
            auto img = APP->window->loadImage(
                asset::plugin(pluginInstance, "res/Ladder-bg.jpg"));
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
            // Acid green fallback -- Roland TB-303 panel homage
            nvgBeginPath(args.vg);
            nvgRect(args.vg, 0, 0, box.size.x, box.size.y);
            nvgFillColor(args.vg, nvgRGB(40, 90, 50));
            nvgFill(args.vg);
        }

        // Dark top bar + title
        nvgBeginPath(args.vg);
        nvgRect(args.vg, 0, 0, box.size.x, 20.f);
        nvgFillColor(args.vg, nvgRGBA(0, 0, 0, 180));
        nvgFill(args.vg);

        nvgFontSize(args.vg, 7.f);
        nvgTextAlign(args.vg, NVG_ALIGN_CENTER | NVG_ALIGN_MIDDLE);
        nvgFillColor(args.vg, nvgRGB(255, 255, 255));
        nvgText(args.vg, box.size.x / 2.f, 10.f, "LDR", NULL);
    }
};


// ---------------------------------------------------------------------------
// Widget -- 6HP
// ---------------------------------------------------------------------------

struct LadderWidget : rack::ModuleWidget {

    LadderWidget(Ladder* module) {
        setModule(module);

        auto* panel = new LadderPanel;
        panel->box.size = Vec(6.f * RACK_GRID_WIDTH, RACK_GRID_HEIGHT);
        addChild(panel);
        box.size = panel->box.size;

        addChild(createWidget<ThemedScrew>(Vec(1 * RACK_GRID_WIDTH, 0)));
        addChild(createWidget<ThemedScrew>(Vec(4 * RACK_GRID_WIDTH, 0)));
        addChild(createWidget<ThemedScrew>(Vec(1 * RACK_GRID_WIDTH, RACK_GRID_HEIGHT - RACK_GRID_WIDTH)));
        addChild(createWidget<ThemedScrew>(Vec(4 * RACK_GRID_WIDTH, RACK_GRID_HEIGHT - RACK_GRID_WIDTH)));

        float cx = 15.24f;  // center x of 6HP
        float L  = cx - 7.f;
        float R  = cx + 7.f;

        // Knobs: FREQ (large, top), RES (medium), SPREAD+SHAPE (small pair)
        addParam(createParamCentered<rack::RoundBigBlackKnob>(
            mm2px(rack::Vec(cx, 22.f)), module, Ladder::FREQ_PARAM));
        addParam(createParamCentered<rack::RoundBlackKnob>(
            mm2px(rack::Vec(cx, 40.f)), module, Ladder::RES_PARAM));
        addParam(createParamCentered<rack::RoundSmallBlackKnob>(
            mm2px(rack::Vec(L, 55.f)), module, Ladder::SPREAD_PARAM));
        addParam(createParamCentered<rack::RoundSmallBlackKnob>(
            mm2px(rack::Vec(R, 55.f)), module, Ladder::SHAPE_PARAM));

        // Mode switch: A / B / C (snap knob 0-2)
        addParam(createParamCentered<rack::RoundSmallBlackKnob>(
            mm2px(rack::Vec(cx, 67.f)), module, Ladder::MODE_PARAM));

        // Row 1: IN (left) + OUT (right)
        addInput(createInputCentered<rack::PJ301MPort>(
            mm2px(rack::Vec(L, 76.f)), module, Ladder::IN_INPUT));
        addOutput(createOutputCentered<rack::PJ301MPort>(
            mm2px(rack::Vec(R, 76.f)), module, Ladder::OUT_OUTPUT));

        // Row 2: cutoff mod (left) + res mod (right)
        addInput(createInputCentered<rack::PJ301MPort>(
            mm2px(rack::Vec(L, 94.f)), module, Ladder::CUTOFF_MOD_INPUT));
        addInput(createInputCentered<rack::PJ301MPort>(
            mm2px(rack::Vec(R, 94.f)), module, Ladder::RES_MOD_INPUT));

        // Row 3: spread mod (left) + shape mod (right)
        addInput(createInputCentered<rack::PJ301MPort>(
            mm2px(rack::Vec(L, 112.f)), module, Ladder::SPREAD_MOD_INPUT));
        addInput(createInputCentered<rack::PJ301MPort>(
            mm2px(rack::Vec(R, 112.f)), module, Ladder::SHAPE_MOD_INPUT));
    }
};


rack::Model* modelLadder = createModel<Ladder, LadderWidget>("Ladder");
