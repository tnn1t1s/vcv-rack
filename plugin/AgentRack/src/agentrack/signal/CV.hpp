#pragma once

#include <algorithm>

namespace AgentRack {
namespace Signal {
namespace CV {

inline float toBipolarUnit(float volts) {
    return volts / 10.f;
}

struct Parameter {
    const char* name;
    float base;
    float min;
    float max;

    float modulate(float depth, float cvVolts) const {
        return std::max(min, std::min(max, base + depth * toBipolarUnit(cvVolts)));
    }
};

} // namespace CV
} // namespace Signal
} // namespace AgentRack
