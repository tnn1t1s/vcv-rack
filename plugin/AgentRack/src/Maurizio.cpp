#include <rack.hpp>
#include "AgentModule.hpp"
#include "agentrack/signal/Audio.hpp"
#include "agentrack/signal/CV.hpp"
#include <cmath>

using namespace rack;
extern Plugin* pluginInstance;

/**
 * Maurizio -- Basic Channel / Maurizio-style dub delay.
 *
 * A clock-syncable stereo delay with dotted/triplet ratio, high-pass filtered
 * feedback, and subtle tape saturation. Designed for the deep, washy chord
 * delays that define dub techno.
 *
 * Clock sync:
 *   Feed a clock pulse into CLK input. The delay measures the interval
 *   between rising edges and multiplies by the RATIO setting:
 *     Straight  = 1.0   (quarter note echo)
 *     Dotted    = 1.5   (dotted eighth = 3/16 of a whole note)
 *     Triplet   = 0.667 (triplet quarter)
 *   Without clock, TIME knob sets delay 50ms-2000ms directly.
 *
 * Feedback path:
 *   Each echo passes through a one-pole high-pass (HP knob, 80-800 Hz)
 *   and a one-pole low-pass (TONE knob, 1-12 kHz) plus soft tanh saturation.
 *   This scoops the mud and darkens successive repeats, exactly like tape.
 *
 * Rack IDs (stable, never reorder):
 *   Params:  TIME_PARAM=0, FEEDBACK_PARAM=1, TONE_PARAM=2, HP_PARAM=3,
 *            MIX_PARAM=4, RATIO_PARAM=5
 *   Inputs:  IN_L_INPUT=0, IN_R_INPUT=1, CLK_INPUT=2, FB_MOD_INPUT=3
 *   Outputs: OUT_L_OUTPUT=0, OUT_R_OUTPUT=1
 */


// ---------------------------------------------------------------------------
// Module
// ---------------------------------------------------------------------------

static constexpr int MAX_DELAY_SAMPLES = 48000 * 4;  // 4 seconds at 48kHz

struct Maurizio : AgentModule {

    enum ParamId  { TIME_PARAM, FEEDBACK_PARAM, TONE_PARAM, HP_PARAM,
                    MIX_PARAM, RATIO_PARAM, NUM_PARAMS };
    enum InputId  { IN_L_INPUT, IN_R_INPUT, CLK_INPUT, FB_MOD_INPUT, NUM_INPUTS };
    enum OutputId { OUT_L_OUTPUT, OUT_R_OUTPUT, NUM_OUTPUTS };

    // Delay buffer (stereo)
    float bufL[MAX_DELAY_SAMPLES] = {};
    float bufR[MAX_DELAY_SAMPLES] = {};
    int writePos = 0;

    // Clock sync state
    dsp::SchmittTrigger clockTrigger;
    float clockInterval = 0.f;    // seconds between last two clock edges
    float timeSinceClock = 0.f;
    bool clockSynced = false;

    // Filter state (feedback path)
    float hpStateL = 0.f, hpStateR = 0.f;   // high-pass
    float lpStateL = 0.f, lpStateR = 0.f;   // low-pass

    Maurizio() {
        config(NUM_PARAMS, NUM_INPUTS, NUM_OUTPUTS);
        // TIME: log-scaled 50ms to 2000ms
        configParam(TIME_PARAM,     0.f, 1.f, 0.5f, "Time", " ms", 0.f, 1.f);
        configParam(FEEDBACK_PARAM, 0.f, 0.95f, 0.65f, "Feedback", "%", 0.f, 100.f);
        // TONE: low-pass cutoff on feedback, log2(Hz)
        configParam(TONE_PARAM,     0.f, 1.f, 0.6f, "Tone", "%", 0.f, 100.f);
        // HP: high-pass cutoff on feedback
        configParam(HP_PARAM,       0.f, 1.f, 0.3f, "HP", "%", 0.f, 100.f);
        configParam(MIX_PARAM,      0.f, 1.f, 0.4f, "Mix", "%", 0.f, 100.f);
        // RATIO: 0=triplet(0.667), 0.5=straight(1.0), 1.0=dotted(1.5)
        configParam(RATIO_PARAM,    0.f, 2.f, 1.f, "Ratio");
        paramQuantities[RATIO_PARAM]->snapEnabled = true;

        configInput(IN_L_INPUT,  "Left");
        configInput(IN_R_INPUT,  "Right");
        configInput(CLK_INPUT,   "Clock");
        configInput(FB_MOD_INPUT, "Feedback CV");
        configOutput(OUT_L_OUTPUT, "Left");
        configOutput(OUT_R_OUTPUT, "Right");
    }

    float readBuffer(const float* buf, float delaySamples) {
        float pos = (float)writePos - delaySamples;
        if (pos < 0.f) pos += MAX_DELAY_SAMPLES;
        int i0 = (int)pos;
        int i1 = (i0 + 1) % MAX_DELAY_SAMPLES;
        float frac = pos - (float)i0;
        return buf[i0 % MAX_DELAY_SAMPLES] * (1.f - frac) + buf[i1] * frac;
    }

    void process(const ProcessArgs& args) override {
        float sr = args.sampleRate;

        // --- Clock sync ---
        timeSinceClock += args.sampleTime;
        if (clockTrigger.process(inputs[CLK_INPUT].getVoltage(), 0.1f, 2.f)) {
            if (clockSynced) {
                clockInterval = timeSinceClock;
            }
            timeSinceClock = 0.f;
            clockSynced = true;
        }
        // Timeout: if no clock for 4 seconds, revert to manual
        if (timeSinceClock > 4.f) {
            clockSynced = false;
        }

        // --- Delay time ---
        float delayTime;  // in seconds
        if (clockSynced && clockInterval > 0.001f) {
            // Clock-synced: apply ratio multiplier
            int ratioIdx = (int)params[RATIO_PARAM].getValue();
            float ratios[3] = { 0.6667f, 1.0f, 1.5f };  // triplet, straight, dotted
            delayTime = clockInterval * ratios[clamp(ratioIdx, 0, 2)];
        } else {
            // Manual: TIME knob, log-scaled 50ms to 2000ms
            float t = params[TIME_PARAM].getValue();
            delayTime = 0.050f * std::pow(40.f, t);  // 50ms at 0, 2000ms at 1
        }
        float delaySamples = clamp(delayTime * sr, 1.f, (float)(MAX_DELAY_SAMPLES - 1));

        // --- Params ---
        AgentRack::Signal::CV::Parameter feedbackParam{
            "feedback", params[FEEDBACK_PARAM].getValue(), 0.f, 0.95f
        };
        float feedback = feedbackParam.modulate(1.f, inputs[FB_MOD_INPUT].getVoltage());
        float toneParam = params[TONE_PARAM].getValue();
        float hpParam   = params[HP_PARAM].getValue();
        float mix       = params[MIX_PARAM].getValue();

        // Tone LP: 800 Hz at 0, 12000 Hz at 1
        float lpFreq = 800.f * std::pow(15.f, toneParam);
        float lpCoeff = 1.f - std::exp(-2.f * (float)M_PI * lpFreq / sr);

        // HP: 40 Hz at 0, 800 Hz at 1
        float hpFreq = 40.f * std::pow(20.f, hpParam);

        // --- Read inputs (mono-compatible: R defaults to L) ---
        float inL = AgentRack::Signal::Audio::fromRackVolts(
            inputs[IN_L_INPUT].getVoltage());
        float inR = inputs[IN_R_INPUT].isConnected()
                  ? AgentRack::Signal::Audio::fromRackVolts(
                        inputs[IN_R_INPUT].getVoltage())
                  : inL;

        // --- Read delay taps ---
        float tapL = readBuffer(bufL, delaySamples);
        float tapR = readBuffer(bufR, delaySamples);

        // --- Feedback processing: HP -> LP -> soft saturation ---
        // High-pass via subtract-LP method: lpState tracks bass, subtract to get HP
        float lpCoeffHP = 1.f - std::exp(-2.f * (float)M_PI * hpFreq / sr);
        hpStateL += lpCoeffHP * (tapL - hpStateL);
        hpStateR += lpCoeffHP * (tapR - hpStateR);
        float hpL = tapL - hpStateL;
        float hpR = tapR - hpStateR;

        // Low-pass (darken successive echoes)
        lpStateL += lpCoeff * (hpL - lpStateL);
        lpStateR += lpCoeff * (hpR - lpStateR);

        // Soft saturation (tape character)
        float fbL = std::tanh(lpStateL);
        float fbR = std::tanh(lpStateR);

        // --- Write to buffer: input + filtered feedback ---
        bufL[writePos] = inL + fbL * feedback;
        bufR[writePos] = inR + fbR * feedback;
        writePos = (writePos + 1) % MAX_DELAY_SAMPLES;

        // --- Output: dry/wet mix ---
        float wetL = tapL;
        float wetR = tapR;
        outputs[OUT_L_OUTPUT].setVoltage(AgentRack::Signal::Audio::toRackVolts(
            inL * (1.f - mix) + wetL * mix));
        outputs[OUT_R_OUTPUT].setVoltage(AgentRack::Signal::Audio::toRackVolts(
            inR * (1.f - mix) + wetR * mix));
    }

};


// ---------------------------------------------------------------------------
// Panel
// ---------------------------------------------------------------------------

struct MaurizioPanel : rack::widget::Widget {
    void draw(const DrawArgs& args) override {
        int imgHandle = 0;
        try {
            auto img = APP->window->loadImage(
                asset::plugin(pluginInstance, "res/Maurizio-bg.jpg"));
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
            nvgFillColor(args.vg, nvgRGB(60, 50, 80));
            nvgFill(args.vg);
        }

        // Dark top bar + title
        nvgBeginPath(args.vg);
        nvgRect(args.vg, 0, 0, box.size.x, 20.f);
        nvgFillColor(args.vg, nvgRGBA(0, 0, 0, 180));
        nvgFill(args.vg);

        nvgFontSize(args.vg, 7.f);
        nvgFontFaceId(args.vg, APP->window->uiFont->handle);
        nvgTextAlign(args.vg, NVG_ALIGN_CENTER | NVG_ALIGN_MIDDLE);
        nvgFillColor(args.vg, nvgRGB(255, 255, 255));
        nvgText(args.vg, box.size.x / 2.f, 10.f, "MRZO", NULL);
    }
};


// ---------------------------------------------------------------------------
// Widget -- 6HP
// ---------------------------------------------------------------------------

struct MaurizioWidget : rack::ModuleWidget {

    MaurizioWidget(Maurizio* module) {
        setModule(module);

        auto* panel = new MaurizioPanel;
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

        // Knobs: TIME (large, top), FEEDBACK (medium), TONE+HP (small pair), MIX+RATIO (small pair)
        addParam(createParamCentered<rack::RoundBigBlackKnob>(
            mm2px(Vec(cx, 22.f)), module, Maurizio::TIME_PARAM));
        addParam(createParamCentered<rack::RoundBlackKnob>(
            mm2px(Vec(cx, 40.f)), module, Maurizio::FEEDBACK_PARAM));
        addParam(createParamCentered<rack::RoundSmallBlackKnob>(
            mm2px(Vec(L, 55.f)), module, Maurizio::TONE_PARAM));
        addParam(createParamCentered<rack::RoundSmallBlackKnob>(
            mm2px(Vec(R, 55.f)), module, Maurizio::HP_PARAM));
        addParam(createParamCentered<rack::RoundSmallBlackKnob>(
            mm2px(Vec(L, 67.f)), module, Maurizio::MIX_PARAM));
        addParam(createParamCentered<rack::CKSSThree>(
            mm2px(Vec(R, 67.f)), module, Maurizio::RATIO_PARAM));

        // Row 1: IN L + IN R
        addInput(createInputCentered<rack::PJ301MPort>(
            mm2px(Vec(L, 82.f)), module, Maurizio::IN_L_INPUT));
        addInput(createInputCentered<rack::PJ301MPort>(
            mm2px(Vec(R, 82.f)), module, Maurizio::IN_R_INPUT));

        // Row 2: CLK + FB MOD
        addInput(createInputCentered<rack::PJ301MPort>(
            mm2px(Vec(L, 97.f)), module, Maurizio::CLK_INPUT));
        addInput(createInputCentered<rack::PJ301MPort>(
            mm2px(Vec(R, 97.f)), module, Maurizio::FB_MOD_INPUT));

        // Row 3: OUT L + OUT R
        addOutput(createOutputCentered<rack::PJ301MPort>(
            mm2px(Vec(L, 112.f)), module, Maurizio::OUT_L_OUTPUT));
        addOutput(createOutputCentered<rack::PJ301MPort>(
            mm2px(Vec(R, 112.f)), module, Maurizio::OUT_R_OUTPUT));
    }
};


rack::Model* modelMaurizio = createModel<Maurizio, MaurizioWidget>("Maurizio");
