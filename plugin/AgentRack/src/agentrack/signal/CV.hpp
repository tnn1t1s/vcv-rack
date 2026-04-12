#pragma once

#include <algorithm>

namespace AgentRack {
namespace Signal {
namespace CV {

inline float toBipolarUnit(float volts) {
    return volts / 10.f;
}

inline float modulateParam(float base, float depth, float cvVolts,
                           float min, float max) {
    return std::max(min, std::min(max, base + depth * toBipolarUnit(cvVolts)));
}

} // namespace CV
} // namespace Signal
} // namespace AgentRack
