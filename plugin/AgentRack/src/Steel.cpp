// Steel.cpp — AI-driven wavetable stacker for AgentRack
//
// Architecture:
//   - 16 single-cycle wavetables (generated at init, 2048 samples each)
//   - Sidechain input → 512-pt vDSP FFT every ~100ms → 8-band history (20 snapshots)
//   - Every INFER_RATE seconds: build text prompt → send to Gemma (background thread)
//   - Result: JSON array of 16 mixing weights, smoothed with 1-pole filter
//   - Audio output: weighted sum of wavetables at V/OCT pitch
//
// Rack IDs (stable, never reorder):
//   Params:  PITCH=0  RATE=1
//   Inputs:  VOCT=0   SIDECHAIN=1
//   Outputs: OUT_L=0  OUT_R=1
//   Lights:  MODEL_LIGHT_R=0  MODEL_LIGHT_G=1  MODEL_LIGHT_B=2  INFER_LIGHT=3

#include <rack.hpp>
#include <Accelerate/Accelerate.h>
#include <atomic>
#include <mutex>
#include <cmath>
#include <cstring>
#include <cstdio>
#include "osdialog.h"
#include "AgentModule.hpp"
#include "PanelLayout.hpp"
#include "agentrack/signal/CV.hpp"
#include "ai/AIModule.hpp"

using namespace rack;
extern Plugin* pluginInstance;

// ─── Wavetables ──────────────────────────────────────────────────────────────

static constexpr int   WT_LEN  = 2048;
static constexpr float WT_TWOPI = 6.28318530718f;

// 16 wavetables, generated once
static float g_wt[16][WT_LEN];
static bool  g_wtReady = false;

static void normalizeWT(float* buf) {
    float peak = 0.f;
    for (int i = 0; i < WT_LEN; i++) peak = fmaxf(peak, fabsf(buf[i]));
    if (peak > 0.f) { float g = 1.f/peak; for (int i = 0; i < WT_LEN; i++) buf[i] *= g; }
}

static void generateWavetables() {
    if (g_wtReady) return;
    g_wtReady = true;

    // 0 — pure sine
    for (int i = 0; i < WT_LEN; i++)
        g_wt[0][i] = sinf(WT_TWOPI * i / WT_LEN);

    // 1 — triangle
    for (int i = 0; i < WT_LEN; i++) {
        float t = (float)i / WT_LEN;
        g_wt[1][i] = (t < 0.25f) ? 4.f*t
                   : (t < 0.75f) ? 2.f - 4.f*t
                                 : 4.f*t - 4.f;
    }

    // 2 — bandlimited sawtooth (40 harmonics)
    for (int i = 0; i < WT_LEN; i++) {
        float s = 0.f;
        for (int h = 1; h <= 40; h++)
            s += ((h & 1) ? 1.f : -1.f) * sinf(WT_TWOPI * h * i / WT_LEN) / (float)h;
        g_wt[2][i] = s;
    }

    // 3 — bandlimited square (odd harmonics up to 39)
    for (int i = 0; i < WT_LEN; i++) {
        float s = 0.f;
        for (int h = 1; h <= 39; h += 2)
            s += sinf(WT_TWOPI * h * i / WT_LEN) / (float)h;
        g_wt[3][i] = s;
    }

    // 4 — pulse 25% duty
    for (int i = 0; i < WT_LEN; i++) {
        float s = 0.f;
        float d = 0.25f;
        for (int h = 1; h <= 40; h++)
            s += 2.f * sinf(3.14159265f * h * d) / (3.14159265f * h)
                     * cosf(WT_TWOPI * h * i / WT_LEN);
        g_wt[4][i] = s;
    }

    // 5 — pulse 10% duty
    for (int i = 0; i < WT_LEN; i++) {
        float s = 0.f;
        float d = 0.10f;
        for (int h = 1; h <= 40; h++)
            s += 2.f * sinf(3.14159265f * h * d) / (3.14159265f * h)
                     * cosf(WT_TWOPI * h * i / WT_LEN);
        g_wt[5][i] = s;
    }

    // 6 — super saw: three detuned saws mixed (±5 cents)
    {
        float detune[3] = { 1.f, 1.002909f, 0.997096f };  // 0, +5, -5 cents
        for (int i = 0; i < WT_LEN; i++) g_wt[6][i] = 0.f;
        for (int d = 0; d < 3; d++) {
            for (int i = 0; i < WT_LEN; i++) {
                float s = 0.f;
                for (int h = 1; h <= 30; h++)
                    s += ((h & 1) ? 1.f : -1.f)
                         * sinf(WT_TWOPI * h * detune[d] * i / WT_LEN) / (float)h;
                g_wt[6][i] += s / 3.f;
            }
        }
    }

    // 7 — odd harmonics 1+3+5+7+9 equal amplitude
    for (int i = 0; i < WT_LEN; i++) {
        float s = 0.f;
        for (int h : {1,3,5,7,9})
            s += sinf(WT_TWOPI * h * i / WT_LEN);
        g_wt[7][i] = s;
    }

    // 8 — even harmonics 1+2+4+8+16
    for (int i = 0; i < WT_LEN; i++) {
        float s = 0.f;
        for (int h : {1,2,4,8,16})
            s += sinf(WT_TWOPI * h * i / WT_LEN);
        g_wt[8][i] = s;
    }

    // 9 — bright: harmonics 1..20, amp=1/sqrt(n)
    for (int i = 0; i < WT_LEN; i++) {
        float s = 0.f;
        for (int h = 1; h <= 20; h++)
            s += sinf(WT_TWOPI * h * i / WT_LEN) / sqrtf((float)h);
        g_wt[9][i] = s;
    }

    // 10 — warm: harmonics 1..6, amp=1/n²
    for (int i = 0; i < WT_LEN; i++) {
        float s = 0.f;
        for (int h = 1; h <= 6; h++)
            s += sinf(WT_TWOPI * h * i / WT_LEN) / (float)(h*h);
        g_wt[10][i] = s;
    }

    // 11 — FM simple: carrier f=1, mod f=2, index=2
    for (int i = 0; i < WT_LEN; i++) {
        float t = (float)i / WT_LEN;
        g_wt[11][i] = sinf(WT_TWOPI * t + 2.f * sinf(WT_TWOPI * 2.f * t));
    }

    // 12 — FM complex: carrier f=1, mod f=3, index=5
    for (int i = 0; i < WT_LEN; i++) {
        float t = (float)i / WT_LEN;
        g_wt[12][i] = sinf(WT_TWOPI * t + 5.f * sinf(WT_TWOPI * 3.f * t));
    }

    // 13 — formant (vowel "ah"): fundamental + two formant peaks
    for (int i = 0; i < WT_LEN; i++) {
        float s = 0.f;
        for (int h = 1; h <= 30; h++) {
            float env = expf(-0.5f * powf((h - 8.f) / 2.f, 2.f))   // F1 ~800Hz region
                      + expf(-0.5f * powf((h - 16.f) / 3.f, 2.f))  // F2 ~1600Hz region
                      + 0.3f / (float)h;                             // fundamental presence
            s += sinf(WT_TWOPI * h * i / WT_LEN) * env / (float)h;
        }
        g_wt[13][i] = s;
    }

    // 14 — sub: sine at half frequency (sub octave)
    for (int i = 0; i < WT_LEN; i++)
        g_wt[14][i] = sinf(WT_TWOPI * 0.5f * i / WT_LEN);

    // 15 — noise band: many close harmonics (pseudo-noise)
    for (int i = 0; i < WT_LEN; i++) {
        float s = 0.f;
        float phase_offset = 0.f;
        for (int h = 1; h <= 32; h++) {
            phase_offset += (float)h * 0.7531f;  // deterministic pseudo-random phase
            s += sinf(WT_TWOPI * h * i / WT_LEN + phase_offset) / (float)h;
        }
        g_wt[15][i] = s;
    }

    // Normalize all tables to peak ±1
    for (int w = 0; w < 16; w++) normalizeWT(g_wt[w]);
}

// Interpolated wavetable read (linear interp, wraps)
static inline float readWT(int wt, float phase) {
    // phase in [0, WT_LEN)
    while (phase >= WT_LEN) phase -= WT_LEN;
    while (phase <  0.f)    phase += WT_LEN;
    int   i0   = (int)phase;
    int   i1   = (i0 + 1) % WT_LEN;
    float frac = phase - (float)i0;
    return g_wt[wt][i0] * (1.f - frac) + g_wt[wt][i1] * frac;
}

// ─── Sidechain FFT ───────────────────────────────────────────────────────────

static constexpr int FFT_SIZE     = 512;
static constexpr int FFT_LOG2     = 9;        // 2^9 = 512
static constexpr int FFT_HALF     = FFT_SIZE / 2;
static constexpr int FFT_STRIDE   = 4410;     // ~100ms at 44100 Hz
static constexpr int HISTORY_LEN  = 20;       // 20 snapshots = 2s
static constexpr int NUM_BANDS    = 8;

// Log-spaced band edges (bin indices into FFT_HALF result)
static constexpr int BAND_EDGES[NUM_BANDS + 1] = { 1, 3, 8, 18, 40, 80, 130, 185, 256 };

struct SidechainFFT {
    FFTSetup       setup      = nullptr;
    DSPSplitComplex split     = {};
    float          window_[FFT_SIZE] = {};
    float          inBuf_[FFT_SIZE]  = {};
    int            inPos_ = 0;

    void init() {
        setup = vDSP_create_fftsetup(FFT_LOG2, FFT_RADIX2);
        split.realp = new float[FFT_HALF];
        split.imagp = new float[FFT_HALF];
        vDSP_hann_window(window_, FFT_SIZE, vDSP_HANN_NORM);
    }

    void destroy() {
        if (setup) { vDSP_destroy_fftsetup(setup); setup = nullptr; }
        delete[] split.realp; split.realp = nullptr;
        delete[] split.imagp; split.imagp = nullptr;
    }

    // Push one sample; returns true when FFT_STRIDE samples have accumulated.
    bool push(float s) {
        inBuf_[inPos_ % FFT_SIZE] = s;
        return (++inPos_ >= FFT_STRIDE);
    }

    // Compute 8-band energies. Call when push() returns true.
    void compute(float bands[NUM_BANDS]) {
        // Apply Hann window to the last FFT_SIZE samples
        float windowed[FFT_SIZE];
        vDSP_vmul(inBuf_, 1, window_, 1, windowed, 1, FFT_SIZE);

        // Pack real data as split-complex for the real FFT
        vDSP_ctoz((const DSPComplex*)windowed, 2, &split, 1, FFT_HALF);
        vDSP_fft_zrip(setup, &split, 1, FFT_LOG2, FFT_FORWARD);

        // Magnitude squared per bin
        float power[FFT_HALF];
        vDSP_zvmags(&split, 1, power, 1, FFT_HALF);

        // Average power per band, then sqrt for amplitude
        float scale = 1.f / (float)(FFT_HALF);
        for (int b = 0; b < NUM_BANDS; b++) {
            float sum = 0.f;
            int   cnt = BAND_EDGES[b+1] - BAND_EDGES[b];
            for (int bin = BAND_EDGES[b]; bin < BAND_EDGES[b+1]; bin++)
                sum += power[bin];
            bands[b] = sqrtf(sum / (float)cnt * scale);
        }

        inPos_ = 0;
    }
};

// ─── Module ──────────────────────────────────────────────────────────────────

static const char* WT_NAMES[16] = {
    "sine","tri","saw","square","pulse25","pulse10",
    "supersaw","odd","even","bright","warm",
    "fm2","fm5","formant","sub","noiseband"
};

struct Steel : AIModule {

    enum ParamId {
        PITCH_PARAM,   // -4..+4 (octaves relative to C4)
        RATE_PARAM,    // 1..10 (seconds between inferences)
        NUM_PARAMS
    };
    enum InputId {
        VOCT_INPUT,
        SIDECHAIN_INPUT,
        NUM_INPUTS
    };
    enum OutputId {
        OUT_L_OUTPUT,
        OUT_R_OUTPUT,
        NUM_OUTPUTS
    };
    enum LightId {
        MODEL_LIGHT_R,
        MODEL_LIGHT_G,
        MODEL_LIGHT_B,
        INFER_LIGHT,
        NUM_LIGHTS
    };

    // Wavetable oscillator state
    float phase_   = 0.f;   // [0, WT_LEN)

    // AI weights (16 floats, smoothed)
    float targetWeights_[16] = {};
    float smoothWeights_[16] = {};
    std::mutex weightsMutex_;

    // FFT history
    SidechainFFT fft_;
    float        history_[HISTORY_LEN][NUM_BANDS] = {};
    int          historyHead_ = 0;
    bool         historyFull_ = false;
    std::mutex   historyMutex_;

    // Inference timer
    float inferTimer_   = 0.f;
    float inferFlash_   = 0.f;   // blink light duration

    // Init default weights
    void resetWeights() {
        for (int i = 0; i < 16; i++) {
            targetWeights_[i] = (i == 0) ? 1.f : 0.f;  // start on sine
            smoothWeights_[i] = targetWeights_[i];
        }
    }

    Steel() {
        generateWavetables();
        fft_.init();
        resetWeights();

        config(NUM_PARAMS, NUM_INPUTS, NUM_OUTPUTS, NUM_LIGHTS);

        configParam(PITCH_PARAM, -4.f, 4.f, 0.f, "Pitch", " oct");
        configParam(RATE_PARAM,   1.f, 10.f, 3.f, "Infer rate", " s");
        paramQuantities[RATE_PARAM]->snapEnabled = true;

        configInput(VOCT_INPUT,     "V/OCT");
        configInput(SIDECHAIN_INPUT,"Sidechain");

        configOutput(OUT_L_OUTPUT, "Left");
        configOutput(OUT_R_OUTPUT, "Right");

        startInferenceThread();
    }

    ~Steel() {
        fft_.destroy();
    }

    // ── buildPrompt ───────────────────────────────────────────────────────────
    std::string buildPrompt() override {
        std::string s;
        s.reserve(1024);

        s += "You control a 16-wavetable synthesizer. "
             "Output ONLY a flat JSON array of exactly 16 mixing weights (0.0-1.0). "
             "No explanation. No nested arrays. No markdown.\n"
             "Example output: [0.8, 0.1, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.1, 0.0]\n"
             "Waveforms: ";
        for (int i = 0; i < 16; i++) {
            char buf[32];
            snprintf(buf, sizeof(buf), "%d=%s", i, WT_NAMES[i]);
            s += buf;
            if (i < 15) s += ' ';
        }
        s += "\nSpectral history (8 bands: sub bass lmid mid hmid pres brill air), oldest first:\n";

        std::lock_guard<std::mutex> lk(historyMutex_);
        int snapshots = historyFull_ ? HISTORY_LEN : historyHead_;
        for (int j = 0; j < snapshots; j++) {
            int idx = historyFull_
                    ? (historyHead_ + j) % HISTORY_LEN
                    : j;
            char line[128];
            snprintf(line, sizeof(line),
                     "%.2f %.2f %.2f %.2f %.2f %.2f %.2f %.2f\n",
                     history_[idx][0], history_[idx][1],
                     history_[idx][2], history_[idx][3],
                     history_[idx][4], history_[idx][5],
                     history_[idx][6], history_[idx][7]);
            s += line;
        }
        s += "Weights:";

        return s;
    }

    // ── handleResult ─────────────────────────────────────────────────────────
    void handleResult(const std::string& response) override {
        // Find the JSON array in the response
        size_t start = response.find('[');
        size_t end   = response.rfind(']');
        if (start == std::string::npos || end == std::string::npos || end <= start)
            return;

        std::string jsonStr = response.substr(start, end - start + 1);
        json_error_t jerr;
        json_t* arr = json_loads(jsonStr.c_str(), 0, &jerr);
        if (!arr) return;
        if (!json_is_array(arr)) { json_decref(arr); return; }

        float w[16] = {};
        size_t n = json_array_size(arr);
        for (size_t i = 0; i < n && i < 16; i++) {
            json_t* v = json_array_get(arr, i);
            if (json_is_number(v))
                w[i] = rack::clamp((float)json_number_value(v), 0.f, 1.f);
        }
        json_decref(arr);

        std::lock_guard<std::mutex> lk(weightsMutex_);
        for (int i = 0; i < 16; i++) targetWeights_[i] = w[i];
    }

    // ── process ──────────────────────────────────────────────────────────────
    void process(const ProcessArgs& args) override {

        // ── Model state light ────────────────────────────────────────────────
        auto state = modelState.load();
        lights[MODEL_LIGHT_R].setBrightness(state == ModelState::ERROR   ? 1.f : 0.f);
        lights[MODEL_LIGHT_G].setBrightness(state == ModelState::READY   ? 1.f : 0.f);
        lights[MODEL_LIGHT_B].setBrightness(state == ModelState::LOADING ? 1.f : 0.f);

        // ── Sidechain FFT ────────────────────────────────────────────────────
        float sc = inputs[SIDECHAIN_INPUT].isConnected()
                 ? inputs[SIDECHAIN_INPUT].getVoltage() / 5.f
                 : 0.f;

        if (fft_.push(sc)) {
            float bands[NUM_BANDS];
            fft_.compute(bands);
            {
                std::lock_guard<std::mutex> lk(historyMutex_);
                for (int b = 0; b < NUM_BANDS; b++)
                    history_[historyHead_][b] = bands[b];
                historyHead_ = (historyHead_ + 1) % HISTORY_LEN;
                if (historyHead_ == 0) historyFull_ = true;
            }
        }

        // ── Inference timer ──────────────────────────────────────────────────
        if (state == ModelState::READY) {
            inferTimer_ += args.sampleTime;
            float rate = params[RATE_PARAM].getValue();
            if (inferTimer_ >= rate) {
                inferTimer_ = 0.f;
                submitPrompt(buildPrompt());
                inferFlash_ = 0.05f;  // 50ms blink
            }
        }

        // ── Consume result ───────────────────────────────────────────────────
        {
            std::string result;
            if (pollResult(result))
                handleResult(result);
        }

        // ── Smooth weights (τ = 1s) ──────────────────────────────────────────
        {
            float alpha = 1.f - expf(-args.sampleTime / 1.f);
            std::lock_guard<std::mutex> lk(weightsMutex_);
            for (int i = 0; i < 16; i++)
                smoothWeights_[i] += alpha * (targetWeights_[i] - smoothWeights_[i]);
        }

        // ── Infer blink ──────────────────────────────────────────────────────
        inferFlash_ = fmaxf(0.f, inferFlash_ - args.sampleTime);
        lights[INFER_LIGHT].setBrightness(inferFlash_ > 0.f ? 1.f : 0.f);

        // ── Wavetable oscillator ─────────────────────────────────────────────
        AgentRack::Signal::CV::VoctParameter pitchParam{
            "pitch", params[PITCH_PARAM].getValue(), -12.f, 12.f
        };
        float pitch = pitchParam.modulate(inputs[VOCT_INPUT].getVoltage());

        float freq     = 261.63f * powf(2.f, pitch);  // C4 * 2^pitch
        float advance  = freq * (float)WT_LEN / args.sampleRate;

        phase_ += advance;
        if (phase_ >= (float)WT_LEN) phase_ -= (float)WT_LEN;

        // Weighted mix of all 16 wavetables
        float sumL = 0.f, sumR = 0.f, sumW = 0.f;
        // R channel: phase-shifted by 1/8 cycle for stereo width
        float phaseR = phase_ + (float)WT_LEN / 8.f;
        if (phaseR >= (float)WT_LEN) phaseR -= (float)WT_LEN;

        for (int w = 0; w < 16; w++) {
            float wt = smoothWeights_[w];
            if (wt < 0.0001f) continue;
            sumL += readWT(w, phase_)  * wt;
            sumR += readWT(w, phaseR)  * wt;
            sumW += wt;
        }

        if (sumW > 0.f) { sumL /= sumW; sumR /= sumW; }

        outputs[OUT_L_OUTPUT].setVoltage(rack::clamp(sumL * 5.f, -10.f, 10.f));
        outputs[OUT_R_OUTPUT].setVoltage(rack::clamp(sumR * 5.f, -10.f, 10.f));
    }

};

// ─── Panel ────────────────────────────────────────────────────────────────────

struct SteelPanel : Widget {
    Steel* module = nullptr;

    void draw(const DrawArgs& args) override {
        NVGcontext* vg = args.vg;
        float W = box.size.x;
        float H = box.size.y;

        // Background — dark steel
        nvgBeginPath(vg);
        nvgRect(vg, 0, 0, W, H);
        nvgFillColor(vg, nvgRGB(28, 30, 35));
        nvgFill(vg);

        // Title bar
        nvgBeginPath(vg);
        nvgRect(vg, 0, 0, W, 20.f);
        nvgFillColor(vg, nvgRGBA(0, 0, 0, 200));
        nvgFill(vg);
        nvgFontSize(vg, 7.f);
        nvgFontFaceId(vg, APP->window->uiFont->handle);
        nvgTextAlign(vg, NVG_ALIGN_CENTER | NVG_ALIGN_MIDDLE);
        nvgFillColor(vg, nvgRGB(200, 210, 255));
        nvgText(vg, W * 0.5f, 10.f, "STEEL", NULL);

        // Waveform display window
        float wx = mm2px(3.f), wy = mm2px(8.f);
        float ww = W - mm2px(6.f), wh = mm2px(28.f);

        nvgBeginPath(vg);
        nvgRoundedRect(vg, wx, wy, ww, wh, 3.f);
        nvgFillColor(vg, nvgRGB(10, 12, 18));
        nvgFill(vg);
        nvgStrokeColor(vg, nvgRGBA(80, 100, 180, 100));
        nvgStrokeWidth(vg, 0.8f);
        nvgStroke(vg);

        // Draw current waveform mix (128-point polyline)
        static constexpr int DRAW_PTS = 128;
        float cy = wy + wh * 0.5f;

        nvgBeginPath(vg);
        for (int i = 0; i <= DRAW_PTS; i++) {
            float phase = (float)i / DRAW_PTS * (float)WT_LEN;
            float s = 0.f, sw = 0.f;
            for (int w = 0; w < 16; w++) {
                float wt = module ? module->smoothWeights_[w] : (w == 0 ? 1.f : 0.f);
                if (wt < 0.0001f) continue;
                s  += readWT(w, phase) * wt;
                sw += wt;
            }
            if (sw > 0.f) s /= sw;

            float x = wx + (float)i / DRAW_PTS * ww;
            float y = cy - s * wh * 0.42f;
            if (i == 0) nvgMoveTo(vg, x, y);
            else        nvgLineTo(vg, x, y);
        }
        nvgStrokeColor(vg, nvgRGBA(100, 160, 255, 200));
        nvgStrokeWidth(vg, 1.2f);
        nvgStroke(vg);

        // Model status text
        auto state = module ? module->modelState.load() : AIModule::ModelState::UNLOADED;
        const char* stateStr =
            state == AIModule::ModelState::READY   ? "MODEL OK" :
            state == AIModule::ModelState::LOADING ? "LOADING..." :
            state == AIModule::ModelState::ERROR   ? "NO MODEL" :
                                                     "NO MODEL";
        nvgFontSize(vg, 4.5f);
        nvgTextAlign(vg, NVG_ALIGN_CENTER | NVG_ALIGN_MIDDLE);
        nvgFillColor(vg, state == AIModule::ModelState::READY
                        ? nvgRGB(100, 200, 100)
                        : nvgRGB(160, 100, 100));
        nvgText(vg, W * 0.5f, wy + wh + mm2px(2.5f), stateStr, NULL);

        // Control labels
        nvgFontSize(vg, 5.5f);
        nvgFillColor(vg, nvgRGBA(180, 190, 220, 200));
        nvgText(vg, mm2px(15.f), mm2px(54.f) - 9.f, "PITCH", NULL);
        nvgText(vg, mm2px(46.f), mm2px(54.f) - 9.f, "RATE",  NULL);
        nvgText(vg, mm2px(10.f), mm2px(75.f) - 9.f, "V/OCT", NULL);
        nvgText(vg, mm2px(30.f), mm2px(75.f) - 9.f, "SC",    NULL);
        nvgText(vg, mm2px(10.f), mm2px(90.f) - 9.f, "OUT L", NULL);
        nvgText(vg, mm2px(51.f), mm2px(90.f) - 9.f, "OUT R", NULL);
    }
};

// ─── Widget ───────────────────────────────────────────────────────────────────

struct SteelWidget : ModuleWidget {

    SteelWidget(Steel* module) {
        setModule(module);

        auto* panel = new SteelPanel;
        panel->module   = module;
        panel->box.size = AgentLayout::panelSize_12HP();
        addChild(panel);
        box.size = panel->box.size;

        addChild(createWidget<ThemedScrew>(Vec(1  * RACK_GRID_WIDTH, 0)));
        addChild(createWidget<ThemedScrew>(Vec(10 * RACK_GRID_WIDTH, 0)));
        addChild(createWidget<ThemedScrew>(Vec(1  * RACK_GRID_WIDTH, RACK_GRID_HEIGHT - RACK_GRID_WIDTH)));
        addChild(createWidget<ThemedScrew>(Vec(10 * RACK_GRID_WIDTH, RACK_GRID_HEIGHT - RACK_GRID_WIDTH)));

        // Params
        addParam(createParamCentered<RoundBigBlackKnob>(mm2px(Vec(15.f, 54.f)), module, Steel::PITCH_PARAM));
        addParam(createParamCentered<RoundBigBlackKnob>(mm2px(Vec(46.f, 54.f)), module, Steel::RATE_PARAM));

        // Model status light (RGB)
        addChild(createLightCentered<MediumLight<RedGreenBlueLight>>(
            mm2px(Vec(30.5f, 54.f)), module,
            Steel::MODEL_LIGHT_R));

        // Infer blink light
        addChild(createLightCentered<SmallLight<WhiteLight>>(
            mm2px(Vec(30.5f, 62.f)), module,
            Steel::INFER_LIGHT));

        // Inputs
        addInput(createInputCentered<PJ301MPort>(mm2px(Vec(10.f, 75.f)), module, Steel::VOCT_INPUT));
        addInput(createInputCentered<PJ301MPort>(mm2px(Vec(30.f, 75.f)), module, Steel::SIDECHAIN_INPUT));

        // Outputs
        addOutput(createOutputCentered<PJ301MPort>(mm2px(Vec(10.f, 90.f)), module, Steel::OUT_L_OUTPUT));
        addOutput(createOutputCentered<PJ301MPort>(mm2px(Vec(51.f, 90.f)), module, Steel::OUT_R_OUTPUT));
    }

    void appendContextMenu(Menu* menu) override {
        Steel* m = dynamic_cast<Steel*>(module);
        if (!m) return;
        menu->addChild(new MenuSeparator);
        menu->addChild(createMenuItem("Load model (.gguf)...", "", [=]() {
            osdialog_filters* f = osdialog_filters_parse("GGUF model:gguf");
            char* path = osdialog_file(OSDIALOG_OPEN, NULL, NULL, f);
            osdialog_filters_free(f);
            if (!path) return;
            m->loadModel(std::string(path));
            free(path);
        }));
        menu->addChild(createMenuItem("Reset weights (sine only)", "", [=]() {
            m->resetWeights();
        }));
    }
};

rack::Model* modelSteel = createModel<Steel, SteelWidget>("Steel");
