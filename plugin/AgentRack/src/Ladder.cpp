#include <rack.hpp>
#include "AgentModule.hpp"
#include "PanelLayout.hpp"
#include "agentrack/signal/Audio.hpp"
#include "agentrack/signal/CV.hpp"
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
 *   Params:  FREQ_PARAM=0, RES_PARAM=1, SPREAD_PARAM=2, SHAPE_PARAM=3,
 *            CUTOFF_MOD_PARAM=4
 *   Inputs:  IN_INPUT=0, CUTOFF_MOD_INPUT=1, RES_MOD_INPUT=2,
 *            SPREAD_MOD_INPUT=3, SHAPE_MOD_INPUT=4
 *   Outputs: OUT_OUTPUT=0
 */


// ---------------------------------------------------------------------------
// Module
// ---------------------------------------------------------------------------

struct Ladder : AgentModule {

    enum ParamId  { FREQ_PARAM, RES_PARAM, SPREAD_PARAM, SHAPE_PARAM, CUTOFF_MOD_PARAM, NUM_PARAMS };
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
        configParam(CUTOFF_MOD_PARAM, -1.f, 1.f, 0.2f, "Cutoff modulation depth", "%", 0.f, 100.f);
        configInput(IN_INPUT,          "Audio");
        configInput(CUTOFF_MOD_INPUT,  "Cutoff mod");
        configInput(RES_MOD_INPUT,     "Resonance mod");
        configInput(SPREAD_MOD_INPUT,  "Spread mod");
        configInput(SHAPE_MOD_INPUT,   "Shape mod");
        configOutput(OUT_OUTPUT,       "Out");
    }

    void process(const ProcessArgs& args) override {
        // --- Cutoff: stored in log2(Hz). The mod jack is intentionally gentler
        // than raw 1V/oct by default, but can be dialed up to full tracking.
        AgentRack::Signal::CV::VoctParameter cutoffParam{
            "cutoff", params[FREQ_PARAM].getValue(),
            std::log2(20.f), std::log2(20000.f)
        };
        float cutoffModDepth = params[CUTOFF_MOD_PARAM].getValue();
        float freq_log = cutoffParam.modulate(cutoffModDepth, inputs[CUTOFF_MOD_INPUT].getVoltage());
        float fc = std::pow(2.f, freq_log);

        // freq_p: normalized 0..1 position in log Hz range (used for mode A k-scaling)
        static constexpr float LOG_MIN = 4.321928f;  // log2(20)
        static constexpr float LOG_MAX = 14.28771f;  // log2(20000)
        float freq_p = (freq_log - LOG_MIN) / (LOG_MAX - LOG_MIN);
        freq_p = clamp(freq_p, 0.f, 1.f);

        AgentRack::Signal::CV::Parameter resParam{
            "resonance", params[RES_PARAM].getValue(), 0.1f, 1.2f
        };
        AgentRack::Signal::CV::Parameter spreadParam{
            "spread", params[SPREAD_PARAM].getValue(), 0.f, 1.f
        };
        AgentRack::Signal::CV::Parameter shapeParam{
            "shape", params[SHAPE_PARAM].getValue(), 0.f, 1.f
        };

        float res    = resParam.modulate(1.f, inputs[RES_MOD_INPUT].getVoltage());
        float spread = spreadParam.modulate(1.f, inputs[SPREAD_MOD_INPUT].getVoltage());
        float shape  = shapeParam.modulate(1.f, inputs[SHAPE_MOD_INPUT].getVoltage());

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
            float vin = AgentRack::Signal::Audio::fromRackVolts(
                inputs[IN_INPUT].getPolyVoltage(c));

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

            outputs[OUT_OUTPUT].setVoltage(
                AgentRack::Signal::Audio::toRackVolts(out), c);
        }
    }

};


// ---------------------------------------------------------------------------
// Panel
// ---------------------------------------------------------------------------

struct LadderPanel : rack::widget::Widget {
    void draw(const DrawArgs& args) override {
        AgentLayout::drawAssetPanel(
            args.vg, box.size, pluginInstance,
            "res/Ladder-bg.jpg",
            nvgRGB(40, 90, 50),
            "LDR", nvgRGB(255, 255, 255));
    }
};


// ---------------------------------------------------------------------------
// Widget -- 6HP
// ---------------------------------------------------------------------------

struct LadderWidget : rack::ModuleWidget {

    LadderWidget(Ladder* module) {
        setModule(module);

        auto* panel = new LadderPanel;
        panel->box.size = AgentLayout::panelSize_6HP();
        addChild(panel);
        box.size = panel->box.size;

        AgentLayout::addScrews_6HP(this);

        // Knobs: FREQ (large, top), RES (medium), SPREAD+SHAPE (small pair)
        addParam(createParamCentered<rack::RoundBigBlackKnob>(
            mm2px(rack::Vec(AgentLayout::CENTER_6HP, AgentLayout::COMPACT_ROWS_6HP[0])), module, Ladder::FREQ_PARAM));
        addParam(createParamCentered<rack::RoundBlackKnob>(
            mm2px(rack::Vec(AgentLayout::CENTER_6HP, AgentLayout::COMPACT_ROWS_6HP[1])), module, Ladder::RES_PARAM));
        addParam(createParamCentered<rack::RoundSmallBlackKnob>(
            mm2px(rack::Vec(AgentLayout::LEFT_COLUMN_6HP, AgentLayout::COMPACT_ROWS_6HP[2])), module, Ladder::SPREAD_PARAM));
        addParam(createParamCentered<rack::RoundSmallBlackKnob>(
            mm2px(rack::Vec(AgentLayout::RIGHT_COLUMN_6HP, AgentLayout::COMPACT_ROWS_6HP[2])), module, Ladder::SHAPE_PARAM));
        addParam(createParamCentered<rack::Trimpot>(
            mm2px(rack::Vec(AgentLayout::CENTER_6HP, AgentLayout::COMPACT_ROWS_6HP[4])), module, Ladder::CUTOFF_MOD_PARAM));

        // Row 1: IN (left) + OUT (right)
        addInput(createInputCentered<rack::PJ301MPort>(
            mm2px(rack::Vec(AgentLayout::LEFT_COLUMN_6HP, AgentLayout::COMPACT_ROWS_6HP[3])), module, Ladder::IN_INPUT));
        addOutput(createOutputCentered<rack::PJ301MPort>(
            mm2px(rack::Vec(AgentLayout::RIGHT_COLUMN_6HP, AgentLayout::COMPACT_ROWS_6HP[3])), module, Ladder::OUT_OUTPUT));

        // Row 2: cutoff mod (left) + res mod (right)
        addInput(createInputCentered<rack::PJ301MPort>(
            mm2px(rack::Vec(AgentLayout::LEFT_COLUMN_6HP, AgentLayout::COMPACT_ROWS_6HP[4])), module, Ladder::CUTOFF_MOD_INPUT));
        addInput(createInputCentered<rack::PJ301MPort>(
            mm2px(rack::Vec(AgentLayout::RIGHT_COLUMN_6HP, AgentLayout::COMPACT_ROWS_6HP[4])), module, Ladder::RES_MOD_INPUT));

        // Row 3: spread mod (left) + shape mod (right)
        addInput(createInputCentered<rack::PJ301MPort>(
            mm2px(rack::Vec(AgentLayout::LEFT_COLUMN_6HP, AgentLayout::COMPACT_ROWS_6HP[5])), module, Ladder::SPREAD_MOD_INPUT));
        addInput(createInputCentered<rack::PJ301MPort>(
            mm2px(rack::Vec(AgentLayout::RIGHT_COLUMN_6HP, AgentLayout::COMPACT_ROWS_6HP[5])), module, Ladder::SHAPE_MOD_INPUT));
    }
};


rack::Model* modelLadder = createModel<Ladder, LadderWidget>("Ladder");
