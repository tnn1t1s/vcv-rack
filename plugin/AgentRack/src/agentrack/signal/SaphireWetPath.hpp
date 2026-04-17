#pragma once

#include "Audio.hpp"
#include <algorithm>
#include <array>
#include <cmath>

namespace AgentRack {
namespace Signal {

// Owns the signal-path plumbing that stays outside the convolution engine:
// pre-delay, wet-path tone smoothing, and final constant-power dry/wet mix.
class SaphireWetPath {
public:
    static constexpr int kMaxPreDelaySamples = 4410;

    struct StereoFrame {
        float left = 0.f;
        float right = 0.f;

        StereoFrame() = default;
        StereoFrame(float leftValue, float rightValue)
        : left(leftValue), right(rightValue) {}
    };

    StereoFrame applyPreDelay(float inputLeft, float inputRight, float preDelayParam) {
        int preDelaySamples = static_cast<int>(preDelayParam * (kMaxPreDelaySamples - 1));
        preLeft_[prePosition_] = inputLeft;
        preRight_[prePosition_] = inputRight;

        int readPosition = (prePosition_ - preDelaySamples + kMaxPreDelaySamples) % kMaxPreDelaySamples;
        StereoFrame delayed{preLeft_[readPosition], preRight_[readPosition]};
        prePosition_ = (prePosition_ + 1) % kMaxPreDelaySamples;
        return delayed;
    }

    StereoFrame applyTone(float wetLeft, float wetRight, float toneParam, float sampleRate) {
        float lowpassCutoff = 100.f * std::pow(200.f, toneParam);
        float smoothing = 1.f - std::exp(-2.f * float(M_PI) * lowpassCutoff / sampleRate);
        toneLeft_ += smoothing * (wetLeft - toneLeft_);
        toneRight_ += smoothing * (wetRight - toneRight_);
        return {toneLeft_, toneRight_};
    }

    StereoFrame mix(float dryLeft, float dryRight, float wetLeft, float wetRight, float mixParam) const {
        Audio::ConstantPowerMix mixLaw(mixParam);
        return {
            dryLeft * mixLaw.dryGain() + wetLeft * mixLaw.wetGain(),
            dryRight * mixLaw.dryGain() + wetRight * mixLaw.wetGain(),
        };
    }

    void reset() {
        preLeft_.fill(0.f);
        preRight_.fill(0.f);
        prePosition_ = 0;
        toneLeft_ = 0.f;
        toneRight_ = 0.f;
    }

private:
    std::array<float, kMaxPreDelaySamples> preLeft_{};
    std::array<float, kMaxPreDelaySamples> preRight_{};
    int prePosition_ = 0;
    float toneLeft_ = 0.f;
    float toneRight_ = 0.f;
};

} // namespace Signal
} // namespace AgentRack
