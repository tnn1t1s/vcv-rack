#pragma once
// TapeEngine.hpp — shared tape loop playback engine for Cassette and CAPSTAN.
//
// Handles: playhead advance, sample-rate correction, wow/flutter, 1-pole LP
// tone filter, soft-clip saturation, hiss, crackle, smooth play/stop ramp.
//
// Usage:
//   TapeEngine engine;
//   float s = engine.tick(buf, len, loopSR, speed, reverse,
//                         wowAmt, flutAmt, satDrive, hissAmt,
//                         toneAlpha, crackleOn, playing, sampleTime, sampleRate);
//   float angle = engine.reelAngle;  // for panel animation

#include <rack.hpp>
#include <cmath>

struct TapeEngine {
    float playhead  = 0.f;
    float reelAngle = 0.f;  // radians, for panel animation
    float wowPhase  = 0.f;
    float flutPhase = 0.f;
    float lpState   = 0.f;  // tone filter state — L channel (also used by mono tick)
    float lpStateR  = 0.f;  // tone filter state — R channel (tickStereo only)
    float crackle   = 0.f;
    float speedRamp = 1.f;  // 0=stopped, 1=full speed; smoothed on play/stop

    static constexpr float TWOPI    = 6.28318530718f;
    static constexpr float REEL_RPS = 0.5f;  // reel rotations/sec at 1x speed

    // Linear interpolation read from loop buffer with wraparound.
    static float readInterp(const float* buf, int loopLen, float pos) {
        while (pos >= (float)loopLen) pos -= (float)loopLen;
        while (pos <  0.f)           pos += (float)loopLen;
        int   i0   = (int)pos;
        int   i1   = (i0 + 1) % loopLen;
        float frac = pos - (float)i0;
        return buf[i0] * (1.f - frac) + buf[i1] * frac;
    }

    // Process one sample.
    //
    // loopBuf    — pointer to loop sample data (generated at loopSR)
    // loopLen    — number of samples in the loop
    // loopSR     — sample rate the loop was generated at (e.g. 44100)
    // speed      — 2^param speed multiplier (1.0 = normal)
    // reverse    — play backwards
    // wowAmt     — wow depth fraction (e.g. 0.005 = light, 0.018 = heavy)
    // flutAmt    — flutter depth fraction
    // satDrive   — 0-1 saturation amount
    // hissAmt    — noise floor (e.g. 0.006), 0 = off
    // toneAlpha  — 1-pole LP coefficient: 1-exp(-2π·fc·dt)
    // crackleOn  — add rare transient pops
    // playing    — false ramps speedRamp toward 0 (~200ms); true ramps toward 1 (~50ms)
    // sampleTime — 1/sampleRate
    // sampleRate — current engine sample rate
    //
    // Returns the processed, speed-ramped sample.
    float tick(
        const float* loopBuf, int loopLen, int loopSR,
        float speed, bool reverse,
        float wowAmt, float flutAmt,
        float satDrive, float hissAmt,
        float toneAlpha, bool crackleOn,
        bool  playing,
        float sampleTime, float sampleRate)
    {
        // Smooth play/stop ramp — fast start (~50ms τ), slow stop (~200ms τ)
        // Real tape: motor spins up quickly, inertia slows it down on stop.
        float tau  = playing ? 0.05f : 0.20f;
        float rate = 1.f - expf(-sampleTime / tau);
        speedRamp += ((playing ? 1.f : 0.f) - speedRamp) * rate;

        // Wow (~1.5 Hz) and flutter (~9 Hz) speed modulation
        wowPhase  += 1.5f * sampleTime;
        flutPhase += 9.0f * sampleTime;
        if (wowPhase  >= 1.f) wowPhase  -= 1.f;
        if (flutPhase >= 1.f) flutPhase -= 1.f;
        float speedMod = 1.f
            + wowAmt  * sinf(TWOPI * wowPhase)
            + flutAmt * sinf(TWOPI * flutPhase);

        // Advance playhead — scaled by speedRamp (pitch drops as tape slows)
        float advance = speed * speedMod * speedRamp * ((float)loopSR / sampleRate);
        playhead += reverse ? -advance : advance;
        while (playhead >= (float)loopLen) playhead -= (float)loopLen;
        while (playhead <  0.f)           playhead += (float)loopLen;

        // Reel animation
        reelAngle += TWOPI * REEL_RPS * speed * speedRamp * sampleTime;
        if (reelAngle >= TWOPI) reelAngle -= TWOPI;

        // Read sample
        float s = readInterp(loopBuf, loopLen, playhead);

        // 1-pole LP tone filter (tape head bandwidth)
        lpState += toneAlpha * (s - lpState);
        s = lpState;

        // Soft-clip saturation (gain-compensated — use for tape age, not overdrive)
        if (satDrive > 0.f) {
            float d = 1.f + satDrive * 4.f;
            s = tanhf(s * d) / d;
        }

        // Hiss
        if (hissAmt > 0.f)
            s += (rack::random::uniform() * 2.f - 1.f) * hissAmt;

        // Crackle (rare transient pops — OLD tape)
        if (crackleOn) {
            if (rack::random::uniform() < 0.0002f)
                crackle = (rack::random::uniform() - 0.5f) * 2.f;
            crackle *= 0.91f;
            s += crackle * 0.04f;
        }

        // Scale by speedRamp: amplitude fades with pitch as tape stops/starts
        return s * speedRamp;
    }

    // Stereo tick — shares all phase/ramp state with tick(); use for stereo WAV buffers.
    // Returns {left, right} samples. Hiss and crackle are correlated (mono source).
    std::pair<float,float> tickStereo(
        const float* loopBufL, const float* loopBufR,
        int loopLen, int loopSR,
        float speed, bool reverse,
        float wowAmt, float flutAmt,
        float satDrive, float hissAmt,
        float toneAlpha, bool crackleOn,
        bool  playing,
        float sampleTime, float sampleRate)
    {
        // Smooth play/stop ramp
        float tau  = playing ? 0.05f : 0.20f;
        float rate = 1.f - expf(-sampleTime / tau);
        speedRamp += ((playing ? 1.f : 0.f) - speedRamp) * rate;

        // Wow/flutter
        wowPhase  += 1.5f * sampleTime;
        flutPhase += 9.0f * sampleTime;
        if (wowPhase  >= 1.f) wowPhase  -= 1.f;
        if (flutPhase >= 1.f) flutPhase -= 1.f;
        float speedMod = 1.f
            + wowAmt  * sinf(TWOPI * wowPhase)
            + flutAmt * sinf(TWOPI * flutPhase);

        // Advance playhead
        float advance = speed * speedMod * speedRamp * ((float)loopSR / sampleRate);
        playhead += reverse ? -advance : advance;
        while (playhead >= (float)loopLen) playhead -= (float)loopLen;
        while (playhead <  0.f)           playhead += (float)loopLen;

        // Reel animation
        reelAngle += TWOPI * REEL_RPS * speed * speedRamp * sampleTime;
        if (reelAngle >= TWOPI) reelAngle -= TWOPI;

        // Stereo read
        float sL = readInterp(loopBufL, loopLen, playhead);
        float sR = readInterp(loopBufR, loopLen, playhead);

        // 1-pole LP (independent per channel)
        lpState  += toneAlpha * (sL - lpState);
        lpStateR += toneAlpha * (sR - lpStateR);
        sL = lpState;
        sR = lpStateR;

        // Saturation (independent)
        if (satDrive > 0.f) {
            float d = 1.f + satDrive * 4.f;
            sL = tanhf(sL * d) / d;
            sR = tanhf(sR * d) / d;
        }

        // Hiss (correlated — same noise both channels)
        if (hissAmt > 0.f) {
            float h = (rack::random::uniform() * 2.f - 1.f) * hissAmt;
            sL += h;
            sR += h;
        }

        // Crackle (correlated)
        if (crackleOn) {
            if (rack::random::uniform() < 0.0002f)
                crackle = (rack::random::uniform() - 0.5f) * 2.f;
            crackle *= 0.91f;
            float c = crackle * 0.04f;
            sL += c;
            sR += c;
        }

        return std::make_pair(sL * speedRamp, sR * speedRamp);
    }

    void reset() {
        playhead  = 0.f;
        reelAngle = 0.f;
        wowPhase  = 0.f;
        flutPhase = 0.f;
        lpState   = 0.f;
        lpStateR  = 0.f;
        crackle   = 0.f;
        // speedRamp intentionally preserved — keeps play state across loop changes
    }
};
