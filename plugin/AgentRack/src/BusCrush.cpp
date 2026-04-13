#include <rack.hpp>
#include "AgentModule.hpp"
#include "PanelLayout.hpp"
#include "dsp/resampler.hpp"
#include <cmath>
#include <cstring>

using namespace rack;
extern Plugin* pluginInstance;

// ── HAS_CONTROLS ─────────────────────────────────────────────────────────────
// When defined: 16HP panel with per-channel amp knob + pan knob.
//   Row layout: [amp_knob | audio_in | pan_cv | pan_knob] × 8, then stereo out.
// When undefined: compact 12HP with two jack columns only (original layout).
#define HAS_CONTROLS

/**
 * BusCrush -- 8-channel summing bus with Mackie-style overload.
 *
 * Models the distortion character of a small-format analog mixer bus under
 * overload: many channels hitting a shared summing node, asymmetric rail
 * clipping, and envelope-dependent headroom reduction under sustained load.
 *
 * Rack IDs (stable, never reorder):
 *   Params:  AMP_0..7 = 0-7, PAN_CTRL_0..7 = 8-15  (HAS_CONTROLS only)
 *   Inputs:  IN_0..7 = 0-7, PAN_CV_0..7 = 8-15
 *   Outputs: OUT_L=0, OUT_R=1
 */

struct BusCrush : AgentModule {

    enum InputId {
        IN_0, IN_1, IN_2, IN_3, IN_4, IN_5, IN_6, IN_7,
        PAN_CV_0, PAN_CV_1, PAN_CV_2, PAN_CV_3,
        PAN_CV_4, PAN_CV_5, PAN_CV_6, PAN_CV_7,
        NUM_INPUTS
    };
    enum OutputId { OUT_L, OUT_R, NUM_OUTPUTS };

#ifdef HAS_CONTROLS
    enum ParamId {
        AMP_0, AMP_1, AMP_2, AMP_3, AMP_4, AMP_5, AMP_6, AMP_7,
        PAN_CTRL_0, PAN_CTRL_1, PAN_CTRL_2, PAN_CTRL_3,
        PAN_CTRL_4, PAN_CTRL_5, PAN_CTRL_6, PAN_CTRL_7,
        NUM_PARAMS
    };
#else
    enum ParamId { NUM_PARAMS = 0 };
#endif

    // ── DSP constants ─────────────────────────────────────────────────────────
    static constexpr float DC_R       = 0.995f;
    static constexpr float CH_K       = 1.0f;
    static constexpr float BUS_DRIVE  = 1.5f;
    static constexpr float ENV_DECAY  = 0.993f;
    static constexpr float CONGESTION = 0.15f;

    float dc_x_prev[8] = {};
    float dc_y_prev[8] = {};
    float hp_x_prev[8] = {};
    float hp_y_prev[8] = {};

    dsp::Upsampler<8, 8> up_L, up_R;
    dsp::Decimator<8, 8> dn_L, dn_R;

    float env_L = 0.f;
    float env_R = 0.f;

    dsp::TBiquadFilter<float> lpf_L, lpf_R;

    float shelf_x_prev_L = 0.f, shelf_y_prev_L = 0.f;
    float shelf_x_prev_R = 0.f, shelf_y_prev_R = 0.f;
    float last_sr    = 0.f;
    float shelf_alpha = 0.f;

    BusCrush() {
        config(NUM_PARAMS, NUM_INPUTS, NUM_OUTPUTS);

#ifdef HAS_CONTROLS
        for (int i = 0; i < 8; i++) {
            configParam(AMP_0     + i, 0.f, 2.f, 1.f,
                        string::f("Ch %d amp", i + 1), "x");
            configParam(PAN_CTRL_0 + i, -1.f, 1.f, 0.f,
                        string::f("Ch %d pan", i + 1), "", 0.f, 1.f);
        }
#endif
        for (int i = 0; i < 8; i++) {
            configInput(IN_0    + i, string::f("Ch %d in", i + 1));
            configInput(PAN_CV_0 + i, string::f("Ch %d pan CV (±5V)", i + 1));
        }
        configOutput(OUT_L, "Stereo left");
        configOutput(OUT_R, "Stereo right");
    }

    void onSampleRateChange(const SampleRateChangeEvent&) override {
        last_sr = 0.f;
    }

    static float asym_softclip(float x) {
        static constexpr float A = 1.2f;
        static constexpr float B = 0.85f;
        return x >= 0.f ? std::tanh(A * x) / A
                        : std::tanh(B * x) / B;
    }

    static float processOversampled(float x, float* env) {
        x = asym_softclip(x);
        x = clamp(x, -0.90f, 0.95f);
        *env = std::max(std::abs(x), ENV_DECAY * (*env));
        float h = clamp(1.0f - CONGESTION * (*env), 0.01f, 1.0f);
        return x * h;
    }

    void process(const ProcessArgs& args) override {
        if (args.sampleRate != last_sr) {
            float fc = 15000.f / args.sampleRate;
            lpf_L.setParameters(dsp::TBiquadFilter<float>::LOWPASS, fc, M_SQRT1_2, 1.f);
            lpf_R.setParameters(dsp::TBiquadFilter<float>::LOWPASS, fc, M_SQRT1_2, 1.f);
            float rc_shelf = 1.f / (2.f * float(M_PI) * 2000.f);
            shelf_alpha = rc_shelf / (rc_shelf + args.sampleTime);
            last_sr = args.sampleRate;
        }

        float rc_hp   = 1.f / (2.f * float(M_PI) * 25.f);
        float alpha_hp = rc_hp / (rc_hp + args.sampleTime);

        float bus_L = 0.f, bus_R = 0.f;

        for (int i = 0; i < 8; i++) {
            float x = inputs[IN_0 + i].getVoltage();

#ifdef HAS_CONTROLS
            x *= params[AMP_0 + i].getValue();
#endif

            // DC block
            float y_dc = x - dc_x_prev[i] + DC_R * dc_y_prev[i];
            dc_x_prev[i] = x; dc_y_prev[i] = y_dc;
            if (!std::isfinite(y_dc)) { y_dc = 0.f; dc_x_prev[i] = 0.f; dc_y_prev[i] = 0.f; }

            // Pre-HP at ~25 Hz
            float y_hp = alpha_hp * (hp_y_prev[i] + y_dc - hp_x_prev[i]);
            hp_x_prev[i] = y_dc; hp_y_prev[i] = y_hp;
            if (!std::isfinite(y_hp)) { y_hp = 0.f; hp_x_prev[i] = 0.f; hp_y_prev[i] = 0.f; }

            // Channel saturation
            static const float TANH_K = std::tanh(CH_K);
            float y_sat = std::tanh(CH_K * y_hp) / TANH_K;
            if (!std::isfinite(y_sat)) y_sat = 0.f;

            // Pan: CV + optional knob offset (HAS_CONTROLS), constant-power law
            float cv  = inputs[PAN_CV_0 + i].isConnected()
                      ? inputs[PAN_CV_0 + i].getVoltage() : 0.f;
#ifdef HAS_CONTROLS
            float pan = clamp(params[PAN_CTRL_0 + i].getValue() + cv / 5.f, -1.f, 1.f);
#else
            float pan = clamp(cv / 5.f, -1.f, 1.f);
#endif
            float ang = (pan + 1.f) * 0.25f * float(M_PI);
            bus_L += y_sat * std::cos(ang);
            bus_R += y_sat * std::sin(ang);
        }

        bus_L *= BUS_DRIVE;
        bus_R *= BUS_DRIVE;

        static constexpr float SHELF_GAIN = 0.2589f;

        float hp_shelf_L = shelf_alpha * (shelf_y_prev_L + bus_L - shelf_x_prev_L);
        shelf_x_prev_L = bus_L; shelf_y_prev_L = hp_shelf_L;
        bus_L = bus_L + SHELF_GAIN * hp_shelf_L;
        if (!std::isfinite(bus_L)) { bus_L = 0.f; shelf_x_prev_L = 0.f; shelf_y_prev_L = 0.f; }

        float hp_shelf_R = shelf_alpha * (shelf_y_prev_R + bus_R - shelf_x_prev_R);
        shelf_x_prev_R = bus_R; shelf_y_prev_R = hp_shelf_R;
        bus_R = bus_R + SHELF_GAIN * hp_shelf_R;
        if (!std::isfinite(bus_R)) { bus_R = 0.f; shelf_x_prev_R = 0.f; shelf_y_prev_R = 0.f; }

        float buf_L[8], buf_R[8];
        up_L.process(bus_L, buf_L);
        up_R.process(bus_R, buf_R);
        for (int k = 0; k < 8; k++) {
            buf_L[k] = processOversampled(buf_L[k], &env_L);
            buf_R[k] = processOversampled(buf_R[k], &env_R);
        }

        float out_L = dn_L.process(buf_L);
        float out_R = dn_R.process(buf_R);
        out_L = lpf_L.process(out_L) * 0.85f;
        out_R = lpf_R.process(out_R) * 0.85f;

        if (!std::isfinite(out_L)) out_L = 0.f;
        if (!std::isfinite(out_R)) out_R = 0.f;

        outputs[OUT_L].setVoltage(out_L);
        outputs[OUT_R].setVoltage(out_R);
    }

};


// ── Panel ─────────────────────────────────────────────────────────────────────

struct BusCrushPanel : rack::widget::Widget {
    void draw(const DrawArgs& args) override {
        int imgHandle = 0;
        try {
            auto img = APP->window->loadImage(
                asset::plugin(pluginInstance, "res/BusCrush-bg.png"));
            if (img) imgHandle = img->handle;
        } catch (...) {}

        AgentLayout::drawStandardPanel(
            args.vg, box.size,
            imgHandle,
            nvgRGB(40, 30, 50),
            "BUS",
            nvgRGB(255, 220, 0)
        );

#ifdef HAS_CONTROLS
        // Column header labels
        NVGcontext* vg = args.vg;
        nvgFontSize(vg, 5.f);
        nvgTextAlign(vg, NVG_ALIGN_CENTER | NVG_ALIGN_MIDDLE);
        nvgFillColor(vg, nvgRGBA(200, 190, 220, 180));
        float labelY = 14.f;
        nvgText(vg, mm2px(AgentLayout::COL1_16HP), labelY, "AMP",  nullptr);
        nvgText(vg, mm2px(AgentLayout::COL2_16HP), labelY, "IN",   nullptr);
        nvgText(vg, mm2px(AgentLayout::COL3_16HP), labelY, "PAN",  nullptr);
        nvgText(vg, mm2px(AgentLayout::COL4_16HP), labelY, "PAN",  nullptr);
#endif
    }
};


// ── Widget ────────────────────────────────────────────────────────────────────

struct BusCrushWidget : rack::ModuleWidget {

    BusCrushWidget(BusCrush* module) {
        setModule(module);

        auto* panel = new BusCrushPanel;

#ifdef HAS_CONTROLS
        panel->box.size = AgentLayout::panelSize_16HP();
        addChild(panel);
        box.size = panel->box.size;
        AgentLayout::addScrews_16HP(this);

        for (int i = 0; i < 8; i++) {
            float y = mm2px(AgentLayout::ROW_Y_8[i]);
            // Amp knob
            addParam(createParamCentered<RoundSmallBlackKnob>(
                Vec(mm2px(AgentLayout::COL1_16HP), y),
                module, BusCrush::AMP_0 + i));
            // Audio in jack
            addInput(createInputCentered<PJ301MPort>(
                Vec(mm2px(AgentLayout::COL2_16HP), y),
                module, BusCrush::IN_0 + i));
            // Pan CV jack
            addInput(createInputCentered<PJ301MPort>(
                Vec(mm2px(AgentLayout::COL3_16HP), y),
                module, BusCrush::PAN_CV_0 + i));
            // Pan knob
            addParam(createParamCentered<RoundSmallBlackKnob>(
                Vec(mm2px(AgentLayout::COL4_16HP), y),
                module, BusCrush::PAN_CTRL_0 + i));
        }

        // Stereo out
        float outY = mm2px(AgentLayout::ROW_OUT_Y);
        addOutput(createOutputCentered<PJ301MPort>(
            Vec(mm2px(AgentLayout::COL2_16HP), outY),
            module, BusCrush::OUT_L));
        addOutput(createOutputCentered<PJ301MPort>(
            Vec(mm2px(AgentLayout::COL3_16HP), outY),
            module, BusCrush::OUT_R));

#else
        panel->box.size = AgentLayout::panelSize_12HP();
        addChild(panel);
        box.size = panel->box.size;
        AgentLayout::addScrews_12HP(this);

        for (int i = 0; i < 8; i++) {
            addInput(createInputCentered<PJ301MPort>(
                mm2px(Vec(AgentLayout::LEFT_12HP,  AgentLayout::ROW_Y_8[i])),
                module, BusCrush::IN_0 + i));
            addInput(createInputCentered<PJ301MPort>(
                mm2px(Vec(AgentLayout::RIGHT_12HP, AgentLayout::ROW_Y_8[i])),
                module, BusCrush::PAN_CV_0 + i));
        }

        addOutput(createOutputCentered<PJ301MPort>(
            mm2px(Vec(AgentLayout::LEFT_12HP,  AgentLayout::ROW_OUT_Y)),
            module, BusCrush::OUT_L));
        addOutput(createOutputCentered<PJ301MPort>(
            mm2px(Vec(AgentLayout::RIGHT_12HP, AgentLayout::ROW_OUT_Y)),
            module, BusCrush::OUT_R));
#endif
    }
};


rack::Model* modelBusCrush = createModel<BusCrush, BusCrushWidget>("BusCrush");
