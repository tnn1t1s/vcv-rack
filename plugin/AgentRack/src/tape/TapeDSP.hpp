#pragma once
#include <rack.hpp>
#include <cmath>

// ---------------------------------------------------------------------------
// WowFlutter — filtered-noise pitch modulation
// Wow  ~1.2 Hz, Flutter ~7 Hz, both modeled as LP-filtered white noise
// ---------------------------------------------------------------------------
struct WowFlutter {
    float w0 = 0.f, w1 = 0.f;   // 2-pole LP state for wow
    float f0 = 0.f, f1 = 0.f;   // 2-pole LP state for flutter

    // Returns fractional pitch offset in semitones
    float process(float wowDepth, float flutterDepth, float sampleTime) {
        // Single-pole LP coefficients
        // fc = 1.2 Hz for wow, 7 Hz for flutter
        float kwow    = 1.f - expf(-2.f * (float)M_PI * 1.2f * sampleTime);
        float kflut   = 1.f - expf(-2.f * (float)M_PI * 7.0f * sampleTime);

        float noise0 = rack::random::normal();
        float noise1 = rack::random::normal();

        w1 = w1 + kwow * (noise0 - w1);
        w0 = w0 + kwow * (w1    - w0);

        f1 = f1 + kflut * (noise1 - f1);
        f0 = f0 + kflut * (f1    - f0);

        // Scale: wowDepth in semitones (max ~0.5), flutterDepth (max ~0.25)
        return wowDepth * w0 + flutterDepth * f0;
    }
};

// ---------------------------------------------------------------------------
// TiltSaturator — pre-emphasis → asymmetric soft clip → de-emphasis with age
// ---------------------------------------------------------------------------
struct TiltSaturator {
    float preState  = 0.f;   // 1-pole HP state for pre-emphasis
    float deState   = 0.f;   // 1-pole LP state for de-emphasis

    // HF boost at ~3.2 kHz (first-order shelving via 1-pole HP feedback)
    float preEmphasize(float x, float sampleTime) {
        float kpre  = 1.f - expf(-2.f * (float)M_PI * 3200.f * sampleTime);
        preState    = preState + kpre * (x - preState);
        return x + 0.5f * (x - preState);   // x + shelved HF content
    }

    // Asymmetric soft clip with drive
    float saturate(float x, float drive) {
        float g = 1.f + drive * 3.f;        // drive 0-1 → gain 1-4x
        float y = x * g;
        // Asymmetric: positive half slightly harder clip (tape physics)
        if (y > 0.f)
            return tanhf(y * 0.85f) / 0.85f;
        else
            return tanhf(y) ;
    }

    // LP de-emphasis; cutoff rolls from 20kHz (new) → 4kHz (old) with age
    float deEmphasize(float x, float age, float sampleTime) {
        float fc  = 20000.f * (1.f - age * 0.8f);   // age 0-1 → 20kHz-4kHz
        if (fc < 200.f) fc = 200.f;
        float kde = 1.f - expf(-2.f * (float)M_PI * fc * sampleTime);
        deState   = deState + kde * (x - deState);
        return deState;
    }
};

// ---------------------------------------------------------------------------
// TapeDropout — age-driven random amplitude dropout events
// ---------------------------------------------------------------------------
struct TapeDropout {
    float env      = 1.f;
    int   duration = 0;

    // Returns a gain multiplier 0-1; dropouts become more frequent with age
    float process(float age, float sampleTime) {
        if (duration > 0) {
            duration--;
            // Fast attack, medium release
            env += (0.f - env) * 0.05f;
        } else {
            env += (1.f - env) * 0.02f;
            // Probability per sample scales with age^2
            float prob = age * age * 0.0003f;
            if (rack::random::uniform() < prob) {
                // Duration: 1-30 ms
                duration = (int)(sampleTime > 0.f
                    ? (0.001f + rack::random::uniform() * 0.029f) / sampleTime
                    : 100);
            }
        }
        return env;
    }
};

// ---------------------------------------------------------------------------
// TapeNoise — hiss (HP-shaped white) + optional 50/60Hz hum
// ---------------------------------------------------------------------------
struct TapeNoise {
    float hissState = 0.f;   // 1-pole HP for hiss shaping
    float humPhase  = 0.f;
    float humHz     = 60.f;

    float process(float hissLevel, float humLevel, float sampleTime) {
        // Hiss: white noise HP-filtered at ~800 Hz for tape-ish character
        float noise  = rack::random::normal();
        float khiss  = 1.f - expf(-2.f * (float)M_PI * 800.f * sampleTime);
        hissState    = hissState + khiss * (noise - hissState);
        float hiss   = (noise - hissState) * hissLevel * 0.02f;

        // Hum: sine at humHz
        humPhase    += humHz * sampleTime * 2.f * (float)M_PI;
        if (humPhase > 2.f * (float)M_PI) humPhase -= 2.f * (float)M_PI;
        float hum    = sinf(humPhase) * humLevel * 0.02f;

        return hiss + hum;
    }
};
