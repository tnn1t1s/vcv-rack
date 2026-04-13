#pragma once

#include <algorithm>

namespace AgentRack {
namespace Signal {
namespace CV {

inline float toBipolarUnit(float volts) {
    return volts / 10.f;
}

class Parameter {
public:
    Parameter(const char* name, float base, float min, float max)
    : name_(name), base_(base), min_(min), max_(max) {
    }

    float modulate(float depth, float cvVolts) const {
        return std::max(min_, std::min(max_, base_ + depth * toBipolarUnit(cvVolts)));
    }

    const char* name() const {
        return name_;
    }

private:
    const char* name_;
    float base_;
    float min_;
    float max_;
};

class VoctParameter {
public:
    VoctParameter(const char* name, float base, float min, float max)
    : name_(name), base_(base), min_(min), max_(max) {
    }

    float modulate(float cvVolts) const {
        return std::max(min_, std::min(max_, base_ + cvVolts));
    }

    const char* name() const {
        return name_;
    }

private:
    const char* name_;
    float base_;
    float min_;
    float max_;
};

} // namespace CV
} // namespace Signal
} // namespace AgentRack
