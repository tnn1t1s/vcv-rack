#pragma once

#include <cmath>

namespace AgentRack {
namespace Signal {
namespace Crinkle {

// Triangle-wave fold: signal bounces hard off the +/-1 ceiling, producing
// the strong harmonic signature associated with Buchla-style folding.
inline float trifold(float x) {
    x = x * 0.5f + 0.5f;
    x = x - std::floor(x);
    if (x > 0.5f) {
        x = 1.f - x;
    }
    return (x - 0.25f) * 4.f;
}

inline float wavefold(float input, float timbre, float symmetry) {
    float amplitude = 1.f + timbre * 5.f;
    float folded = input * amplitude + symmetry * 0.8f;
    return trifold(folded);
}

class Voice {
public:
    float processSample(float frequencyHz, float timbre, float symmetry, float sampleTime) {
        float dt = sampleTime * 0.25f;
        float output = 0.f;
        for (int i = 0; i < 4; ++i) {
            phase_ += frequencyHz * dt;
            if (phase_ >= 1.f) {
                phase_ -= 1.f;
            }

            float triangle = 2.f * std::fabs(2.f * phase_ - 1.f) - 1.f;
            output += wavefold(triangle, timbre, symmetry);
        }
        return output * 0.25f;
    }

    void reset() {
        phase_ = 0.f;
    }

private:
    float phase_ = 0.f;
};

} // namespace Crinkle
} // namespace Signal
} // namespace AgentRack
