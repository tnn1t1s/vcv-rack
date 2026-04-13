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

    enum ParamId  { FREQ_PARAM, RES_PARAM, SPREAD_PARAM, SHAPE_PARAM, NUM_PARAMS };
    enum InputId  { IN_INPUT, CUTOFF_MOD_INPUT, RES_MOD_INPUT, SPREAD_MOD_INPUT, SHAPE_MOD_INPUT, NUM_INPUTS };
    enum OutputId { OUT_OUTPUT, NUM_OUTPUTS };

    // Per-stage state, normalized +-1 internally -- one set per poly channel
    static constexpr int MAX_POLY = 16;
    float y[MAX_POLY][4] = {};

    Ladder() {
        config(NUM_PARAMS, NUM_INPUTS, NUM_OUTPUTS);
        // Stored in log2(Hz); displayBase=2 converts back to Hz for the tooltip.
        // CV input tracks V/oct naturally: 1V shifts stored value by 1 = 1 octave.
        configParam(FREQ_PARAM,   std::log2(20.f), std::log2(20000.f),
                                  std::log2(440.f), "Cutoff", " Hz", 2.f);
        // Stored 0.1..1.2; displayMultiplier=100 shows 10%..120%.
        configParam(RES_PARAM,    0.1f, 1.2f, 0.1f, "Resonance", "%", 0.f, 100.f);
        configParam(SPREAD_PARAM, 0.f,  1.f,  0.f,  "Spread",    "%", 0.f, 100.f);
        configParam(SHAPE_PARAM,  0.f,  1.f,  0.f,  "Shape",     "%", 0.f, 100.f);
        configInput(IN_INPUT,          "Audio");
        configInput(CUTOFF_MOD_INPUT,  "Cutoff mod");
        configInput(RES_MOD_INPUT,     "Resonance mod");
        configInput(SPREAD_MOD_INPUT,  "Spread mod");
        configInput(SHAPE_MOD_INPUT,   "Shape mod");
        configOutput(OUT_OUTPUT,       "Out");
    }

    void process(const ProcessArgs& args) override {
        // --- Cutoff: stored in log2(Hz), CV input is V/oct (1V = 1 octave) ---
        float freq_log = params[FREQ_PARAM].getValue()
                       + inputs[CUTOFF_MOD_INPUT].getVoltage();
        float fc = std::pow(2.f, freq_log);

        // freq_p: normalized 0..1 position in log Hz range (used for mode A k-scaling)
        static constexpr float LOG_MIN = 4.321928f;  // log2(20)
        static constexpr float LOG_MAX = 14.28771f;  // log2(20000)
        float freq_p = (freq_log - LOG_MIN) / (LOG_MAX - LOG_MIN);
        freq_p = clamp(freq_p, 0.f, 1.f);

        float res    = clamp(params[RES_PARAM].getValue()
                     + inputs[RES_MOD_INPUT].getVoltage() / 10.f,    0.1f, 1.2f);
        float spread = clamp(params[SPREAD_PARAM].getValue()
                     + inputs[SPREAD_MOD_INPUT].getVoltage() / 10.f, 0.f,  1.f);
        float shape  = clamp(params[SHAPE_PARAM].getValue()
                     + inputs[SHAPE_MOD_INPUT].getVoltage() / 10.f,  0.f,  1.f);

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

        // Standard Huovilainen k: res=1.0 → k=4.1 (self-oscillation threshold)
        float k = res * 4.1f;

        // Polyphonic: process each channel independently
        int channels = std::max(1, inputs[IN_INPUT].getChannels());
        outputs[OUT_OUTPUT].setChannels(channels);

        for (int c = 0; c < channels; c++) {
            float vin = inputs[IN_INPUT].getPolyVoltage(c) / 5.f;

            // --- 2x oversampled Huovilainen nonlinear update ---
            float out = 0.f;
            for (int os = 0; os < 2; os++) {
                float x0 = vin - k * y[c][3];

                // 4-stage cascade: each stage y_k += g_k * (tanh(x_k) - tanh(y_k))
                y[c][0] += g[0] * (std::tanh(x0)      - std::tanh(y[c][0]));
                y[c][1] += g[1] * (std::tanh(y[c][0]) - std::tanh(y[c][1]));
                y[c][2] += g[2] * (std::tanh(y[c][1]) - std::tanh(y[c][2]));
                y[c][3] += g[3] * (std::tanh(y[c][2]) - std::tanh(y[c][3]));
                out  += y[c][3];
            }
            out /= 2.f;  // decimate

            outputs[OUT_OUTPUT].setVoltage(out * 5.f, c);
        }
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

        // Row 1: IN (left) + OUT (right)
        addInput(createInputCentered<rack::PJ301MPort>(
            mm2px(rack::Vec(L, 67.f)), module, Ladder::IN_INPUT));
        addOutput(createOutputCentered<rack::PJ301MPort>(
            mm2px(rack::Vec(R, 67.f)), module, Ladder::OUT_OUTPUT));

        // Row 2: cutoff mod (left) + res mod (right)
        addInput(createInputCentered<rack::PJ301MPort>(
            mm2px(rack::Vec(L, 85.f)), module, Ladder::CUTOFF_MOD_INPUT));
        addInput(createInputCentered<rack::PJ301MPort>(
            mm2px(rack::Vec(R, 85.f)), module, Ladder::RES_MOD_INPUT));

        // Row 3: spread mod (left) + shape mod (right)
        addInput(createInputCentered<rack::PJ301MPort>(
            mm2px(rack::Vec(L, 103.f)), module, Ladder::SPREAD_MOD_INPUT));
        addInput(createInputCentered<rack::PJ301MPort>(
            mm2px(rack::Vec(R, 103.f)), module, Ladder::SHAPE_MOD_INPUT));
    }
};


rack::Model* modelLadder = createModel<Ladder, LadderWidget>("Ladder");
