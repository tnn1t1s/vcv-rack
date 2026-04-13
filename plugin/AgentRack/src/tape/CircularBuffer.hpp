#pragma once
#include <vector>
#include <utility>
#include <cmath>
#include <cstring>

// 5 seconds at 192kHz max sample rate
static constexpr int CB_MAX_SAMPLES = 5 * 192001;

struct CircularBuffer {
    std::vector<float> bufL;
    std::vector<float> bufR;
    int writeHead = 0;
    int loopLen   = 44100;

    CircularBuffer() {
        bufL.resize(CB_MAX_SAMPLES, 0.f);
        bufR.resize(CB_MAX_SAMPLES, 0.f);
    }

    void setLoopLength(int samples) {
        if (samples < 2) samples = 2;
        if (samples > CB_MAX_SAMPLES) samples = CB_MAX_SAMPLES;
        loopLen = samples;
    }

    void clear() {
        memset(bufL.data(), 0, sizeof(float) * loopLen);
        memset(bufR.data(), 0, sizeof(float) * loopLen);
        writeHead = 0;
    }

    void write(float l, float r) {
        bufL[writeHead] = l;
        bufR[writeHead] = r;
        writeHead = (writeHead + 1) % loopLen;
    }

    // Catmull-Rom cubic interpolation at fractional position pos in [0, loopLen)
    std::pair<float,float> readAt(float pos) const {
        pos = fmodf(pos, (float)loopLen);
        if (pos < 0.f) pos += (float)loopLen;

        int i1 = (int)pos;
        float t = pos - (float)i1;

        int i0 = (i1 - 1 + loopLen) % loopLen;
        int i2 = (i1 + 1) % loopLen;
        int i3 = (i1 + 2) % loopLen;

        float t2 = t * t;
        float t3 = t2 * t;
        float c0 = -0.5f*t3 + t2 - 0.5f*t;
        float c1 =  1.5f*t3 - 2.5f*t2 + 1.f;
        float c2 = -1.5f*t3 + 2.0f*t2 + 0.5f*t;
        float c3 =  0.5f*t3 - 0.5f*t2;

        float l = c0*bufL[i0] + c1*bufL[i1] + c2*bufL[i2] + c3*bufL[i3];
        float r = c0*bufR[i0] + c1*bufR[i1] + c2*bufR[i2] + c3*bufR[i3];
        return std::make_pair(l, r);
    }

    // Return read position as samples behind the write head
    float offsetPos(float offsetSamples) const {
        float pos = (float)writeHead - offsetSamples;
        pos = fmodf(pos, (float)loopLen);
        if (pos < 0.f) pos += (float)loopLen;
        return pos;
    }
};
