#include <rack.hpp>
#include "AgentModule.hpp"
#include "PanelLayout.hpp"
#include <cmath>
#include <cstring>

using namespace rack;
extern Plugin* pluginInstance;

/**
 * Sonic -- BBE-inspired constrained spectral-phase maximizer.
 *
 * Splits audio into 3 fixed bands, applies frequency-dependent delay
 * (phase alignment) and spectral tilt weighting to produce perceived
 * clarity and punch.  Fully deterministic; no modes, no adaptive logic.
 *
 * Processing chain (per sample):
 *   1. 3-band split: 2nd-order Butterworth crossovers at 150 Hz and 2 kHz
 *   2. Phase alignment: delay LOW by 2ms*AMOUNT*(1+LOW_CONTOUR),
 *                       delay MID by 1ms*AMOUNT, HIGH is reference (0 delay)
 *   3. Spectral tilt: frequency-dependent gain controlled by COLOR/AMOUNT
 *   4. High-band soft saturation: tanh with drive=(1+2*PROCESS), normalized
 *   5. Recombine + trim: OUT *= 1/(1+0.5*AMOUNT)
 *
 * Rack IDs (stable, never reorder):
 *   Params:  AMOUNT_PARAM=0, COLOR_PARAM=1, LOW_CONTOUR_PARAM=2, PROCESS_PARAM=3
 *   Inputs:  IN_INPUT=0, CV_AMOUNT_INPUT=1, CV_COLOR_INPUT=2
 *   Outputs: OUT_OUTPUT=0
 */

static constexpr int SNX_DELAY_BUF = 512;  // covers 2ms*(1+1) at up to 96kHz


// ---------------------------------------------------------------------------
// Biquad -- 2nd-order IIR, direct form II transposed
// ---------------------------------------------------------------------------

struct SnxBiquad {
    float b0=1, b1=0, b2=0, a1=0, a2=0;
    float z1=0, z2=0;

    float process(float x) {
        float y = b0 * x + z1;
        z1 = b1 * x - a1 * y + z2;
        z2 = b2 * x - a2 * y;
        // Flush denormals
        if (std::fabs(z1) < 1e-37f) z1 = 0.f;
        if (std::fabs(z2) < 1e-37f) z2 = 0.f;
        return y;
    }

    void setLPF(float fc, float sr) {
        float w0    = 2.f * float(M_PI) * fc / sr;
        float c     = std::cos(w0);
        float alpha = std::sin(w0) * 0.7071068f;  // Q = 1/sqrt(2) Butterworth
        float ia0   = 1.f / (1.f + alpha);
        b0 = (1.f - c) * 0.5f * ia0;
        b1 = (1.f - c) * ia0;
        b2 = b0;
        a1 = -2.f * c * ia0;
        a2 = (1.f - alpha) * ia0;
    }

    void setHPF(float fc, float sr) {
        float w0    = 2.f * float(M_PI) * fc / sr;
        float c     = std::cos(w0);
        float alpha = std::sin(w0) * 0.7071068f;
        float ia0   = 1.f / (1.f + alpha);
        b0 =  (1.f + c) * 0.5f * ia0;
        b1 = -(1.f + c) * ia0;
        b2 = b0;
        a1 = -2.f * c * ia0;
        a2 = (1.f - alpha) * ia0;
    }
};


// ---------------------------------------------------------------------------
// DelayLine -- circular buffer, integer-sample delay (sample-accurate)
// ---------------------------------------------------------------------------

struct SnxDelay {
    float buf[SNX_DELAY_BUF] = {};
    int   pos = 0;

    // Write x; return sample delayed by delay_samp samples (0 = current sample)
    float tick(float x, int delay_samp) {
        buf[pos] = x;
        int read = (pos - delay_samp + SNX_DELAY_BUF) % SNX_DELAY_BUF;
        pos = (pos + 1) % SNX_DELAY_BUF;
        return buf[read];
    }
};


// ---------------------------------------------------------------------------
// Module
// ---------------------------------------------------------------------------

struct Sonic : AgentModule {

    enum ParamId  { AMOUNT_PARAM, COLOR_PARAM, LOW_CONTOUR_PARAM, PROCESS_PARAM, NUM_PARAMS };
    enum InputId  { IN_INPUT, CV_AMOUNT_INPUT, CV_COLOR_INPUT, NUM_INPUTS };
    enum OutputId { OUT_OUTPUT, NUM_OUTPUTS };

    // Crossover filters -- split at 150 Hz and 2 kHz
    SnxBiquad lp1, hp1;  // LOW / (MID+HIGH) split
    SnxBiquad lp2, hp2;  // MID / HIGH split (applied to hp1 output)

    // Phase-alignment delay lines (LOW and MID; HIGH is the reference at 0 delay)
    SnxDelay del_low, del_mid;

    float last_sr = 0.f;

    Sonic() {
        config(NUM_PARAMS, NUM_INPUTS, NUM_OUTPUTS);
        configParam(AMOUNT_PARAM,      0.f, 1.f, 0.5f, "Amount",      "%", 0.f, 100.f);
        configParam(COLOR_PARAM,       0.f, 1.f, 0.5f, "Color",       "%", 0.f, 100.f);
        configParam(LOW_CONTOUR_PARAM, 0.f, 1.f, 0.5f, "Low contour", "%", 0.f, 100.f);
        configParam(PROCESS_PARAM,     0.f, 1.f, 0.5f, "Process",     "%", 0.f, 100.f);
        configInput (IN_INPUT,         "In");
        configInput (CV_AMOUNT_INPUT,  "Amount CV");
        configInput (CV_COLOR_INPUT,   "Color CV");
        configOutput(OUT_OUTPUT,       "Out");
    }

    void onSampleRateChange(const SampleRateChangeEvent&) override {
        last_sr = 0.f;  // force coefficient recompute
    }

    void process(const ProcessArgs& args) override {
        // Recompute crossover coefficients on sample rate change
        if (args.sampleRate != last_sr) {
            lp1.setLPF(150.f,  args.sampleRate);
            hp1.setHPF(150.f,  args.sampleRate);
            lp2.setLPF(2000.f, args.sampleRate);
            hp2.setHPF(2000.f, args.sampleRate);
            last_sr = args.sampleRate;
        }

        // Parameters (with CV mod)
        float amount = clamp(params[AMOUNT_PARAM].getValue()
                           + inputs[CV_AMOUNT_INPUT].getVoltage() / 10.f, 0.f, 1.f);
        float color  = clamp(params[COLOR_PARAM].getValue()
                           + inputs[CV_COLOR_INPUT].getVoltage() / 10.f,  0.f, 1.f);
        float low_c  = params[LOW_CONTOUR_PARAM].getValue();
        float proc   = params[PROCESS_PARAM].getValue();

        // Input: ±5V → ±1 (internal processing in normalized amplitude)
        float x = inputs[IN_INPUT].getVoltage() / 5.f;

        // ── Step 1: 3-band split ─────────────────────────────────────────────
        float low_sig  = lp1.process(x);
        float mid_high = hp1.process(x);
        float mid_sig  = lp2.process(mid_high);
        float high_sig = hp2.process(mid_high);

        // ── Step 2: Phase alignment (sample-accurate fixed delay) ────────────
        // LOW:  base 2.0ms * AMOUNT * (1 + LOW_CONTOUR)
        // MID:  base 1.0ms * AMOUNT
        // HIGH: 0 (reference anchor, no delay buffer needed)
        int delay_low = std::min(
            (int)(2.0f * 0.001f * amount * (1.f + low_c) * args.sampleRate + 0.5f),
            SNX_DELAY_BUF - 1);
        int delay_mid = std::min(
            (int)(1.0f * 0.001f * amount * args.sampleRate + 0.5f),
            SNX_DELAY_BUF - 1);

        low_sig = del_low.tick(low_sig, delay_low);
        mid_sig = del_mid.tick(mid_sig, delay_mid);
        // high_sig: no delay, passes through as-is

        // ── Step 3: Spectral tilt (frequency-dependent gain) ─────────────────
        float low_gain  = clamp(1.f + 0.6f * color * low_c * amount, 0.5f, 2.0f);
        float mid_gain  = clamp(1.f - 0.2f * color * amount,         0.5f, 2.0f);
        float high_gain = clamp(1.f + 0.8f * color * proc  * amount, 0.5f, 2.0f);

        low_sig  *= low_gain;
        mid_sig  *= mid_gain;
        high_sig *= high_gain;

        // ── Step 4: High-band soft saturation ────────────────────────────────
        // tanh(x * drive), normalized so unity input → unity output in linear region
        float drive = 1.f + 2.f * proc;
        float norm  = std::tanh(drive);            // tanh(1 * drive)
        high_sig    = std::tanh(high_sig * drive) / norm;

        // ── Step 5: Recombine + loudness trim ────────────────────────────────
        float out = (low_sig + mid_sig + high_sig) * (1.f / (1.f + 0.5f * amount));

        outputs[OUT_OUTPUT].setVoltage(out * 5.f);
    }

};


// ---------------------------------------------------------------------------
// Panel -- 8HP, dark with amber accent
// ---------------------------------------------------------------------------

struct SonicPanel : rack::widget::Widget {
    void draw(const DrawArgs& args) override {
        // Background
        nvgBeginPath(args.vg);
        nvgRect(args.vg, 0, 0, box.size.x, box.size.y);
        nvgFillColor(args.vg, nvgRGB(18, 18, 30));
        nvgFill(args.vg);

        // Title bar
        nvgBeginPath(args.vg);
        nvgRect(args.vg, 0, 0, box.size.x, 20.f);
        nvgFillColor(args.vg, nvgRGBA(0, 0, 0, 200));
        nvgFill(args.vg);

        nvgFontSize(args.vg, 7.f);
        nvgTextAlign(args.vg, NVG_ALIGN_CENTER | NVG_ALIGN_MIDDLE);
        nvgFillColor(args.vg, nvgRGB(255, 200, 60));
        nvgText(args.vg, box.size.x / 2.f, 10.f, "SNX", NULL);

        // Parameter labels
        static const char* const LABELS[] = {
            "AMOUNT", "COLOR", "LOW CTR", "PROCESS"
        };
        // y positions in px matching widget knob rows
        static const float LABEL_Y[] = {
            mm2px(29.f), mm2px(46.f), mm2px(61.f), mm2px(61.f)
        };
        static const float LABEL_X[] = {
            -1.f,           // center (AMOUNT)
            -1.f,           // center (COLOR)
            mm2px(12.32f),  // left (LOW CONTOUR)
            mm2px(28.32f),  // right (PROCESS)
        };

        nvgFontSize(args.vg, 5.5f);
        nvgFillColor(args.vg, nvgRGBA(200, 200, 200, 160));
        for (int i = 0; i < 4; i++) {
            float lx = (LABEL_X[i] < 0.f) ? box.size.x / 2.f : LABEL_X[i];
            nvgTextAlign(args.vg, NVG_ALIGN_CENTER | NVG_ALIGN_TOP);
            nvgText(args.vg, lx, LABEL_Y[i], LABELS[i], NULL);
        }
    }
};


// ---------------------------------------------------------------------------
// Widget -- 8HP
// ---------------------------------------------------------------------------

struct SonicWidget : rack::ModuleWidget {

    SonicWidget(Sonic* module) {
        setModule(module);

        auto* panel = new SonicPanel;
        panel->box.size = AgentLayout::panelSize_8HP();
        addChild(panel);
        box.size = panel->box.size;

        AgentLayout::addScrews_8HP(this);

        float cx = AgentLayout::CX_8HP;
        float L  = cx - 8.f;
        float R  = cx + 8.f;

        // AMOUNT -- large knob, center
        addParam(createParamCentered<rack::RoundBigBlackKnob>(
            mm2px(rack::Vec(cx, 22.f)), module, Sonic::AMOUNT_PARAM));

        // COLOR -- medium knob, center
        addParam(createParamCentered<rack::RoundBlackKnob>(
            mm2px(rack::Vec(cx, 40.f)), module, Sonic::COLOR_PARAM));

        // LOW CONTOUR (L) + PROCESS (R) -- small knobs
        addParam(createParamCentered<rack::RoundSmallBlackKnob>(
            mm2px(rack::Vec(L, 56.f)), module, Sonic::LOW_CONTOUR_PARAM));
        addParam(createParamCentered<rack::RoundSmallBlackKnob>(
            mm2px(rack::Vec(R, 56.f)), module, Sonic::PROCESS_PARAM));

        // Audio IN (L) + OUT (R)
        addInput(createInputCentered<rack::PJ301MPort>(
            mm2px(rack::Vec(L, 76.f)), module, Sonic::IN_INPUT));
        addOutput(createOutputCentered<rack::PJ301MPort>(
            mm2px(rack::Vec(R, 76.f)), module, Sonic::OUT_OUTPUT));

        // CV: AMOUNT (L) + COLOR (R)
        addInput(createInputCentered<rack::PJ301MPort>(
            mm2px(rack::Vec(L, 94.f)), module, Sonic::CV_AMOUNT_INPUT));
        addInput(createInputCentered<rack::PJ301MPort>(
            mm2px(rack::Vec(R, 94.f)), module, Sonic::CV_COLOR_INPUT));
    }
};


rack::Model* modelSonic = createModel<Sonic, SonicWidget>("Sonic");
