#pragma once

#include "PartitionedConvolution.hpp"
#include <atomic>
#include <cmath>
#include <thread>

namespace AgentRack {
namespace Infrastructure {

class SaphireRuntime {
public:
    static constexpr float kParamEpsilon = 0.001f;

    SaphireRuntime() = default;

    ~SaphireRuntime() {
        joinBuilder();
    }

    void init() {
        convolution_[0].init();
        convolution_[1].init();
    }

    void setInitialState(int irIndex, float timeParam, float bendParam) {
        liveIndex_ = 0;
        lastIr_ = irIndex;
        lastTime_ = timeParam;
        lastBend_ = bendParam;
        currentIrIndex_.store(irIndex);
    }

    void joinBuilder() {
        if (builder_.joinable()) {
            builder_.join();
        }
    }

    PartitionedConvolution& liveConvolution() {
        return convolution_[liveIndex_];
    }

    PartitionedConvolution& convolutionAt(int index) {
        return convolution_[index];
    }

    PartitionedConvolution& rebuildConvolution() {
        return convolution_[1 - liveIndex_];
    }

    PartitionedConvolution& oldConvolution() {
        return convolution_[1 - liveIndex_];
    }

    int rebuildIndex() const {
        return 1 - liveIndex_;
    }

    int currentIrIndex() const {
        return currentIrIndex_.load();
    }

    bool oldConvolutionIsSafe() const {
        return safeOld_.load();
    }

    bool isCrossfading() const {
        return crossfadePosition_ >= 0;
    }

    bool shouldRebuild(int irIndex, float timeParam, float bendParam) const {
        return irIndex != lastIr_
            || std::fabs(timeParam - lastTime_) > kParamEpsilon
            || std::fabs(bendParam - lastBend_) > kParamEpsilon;
    }

    template <typename RebuildFn>
    bool launchRebuild(int irIndex, float timeParam, float bendParam, RebuildFn rebuild) {
        if (building_.exchange(true)) {
            return false;
        }

        safeOld_.store(false);
        joinBuilder();

        lastIr_ = irIndex;
        lastTime_ = timeParam;
        lastBend_ = bendParam;
        int targetIndex = rebuildIndex();

        builder_ = std::thread([this, irIndex, targetIndex, rebuild]() {
            rebuild(targetIndex, irIndex);
            currentIrIndex_.store(irIndex);
            pendingIndex_.store(targetIndex);
            building_.store(false);
        });
        return true;
    }

    void consumeCompletedRebuild() {
        int pending = pendingIndex_.load();
        if (pending < 0) {
            return;
        }

        pendingIndex_.store(-1);
        liveIndex_ = pending;
        crossfadePosition_ = 0;
        safeOld_.store(true);
    }

    template <typename Sample>
    void applyCrossfade(Sample& wetLeft, Sample& wetRight, Sample oldLeft, Sample oldRight) {
        if (crossfadePosition_ < 0) {
            return;
        }

        float alpha = static_cast<float>(crossfadePosition_) /
                      static_cast<float>(PartitionedConvolution::kBlockSize);
        wetLeft = oldLeft * (1.f - alpha) + wetLeft * alpha;
        wetRight = oldRight * (1.f - alpha) + wetRight * alpha;

        if (++crossfadePosition_ >= PartitionedConvolution::kBlockSize) {
            crossfadePosition_ = -1;
            safeOld_.store(false);
        }
    }

private:
    PartitionedConvolution convolution_[2];
    int liveIndex_ = 0;

    std::atomic<int> pendingIndex_{-1};
    std::atomic<bool> building_{false};
    std::atomic<bool> safeOld_{false};
    std::atomic<int> currentIrIndex_{38};
    std::thread builder_;

    int crossfadePosition_ = -1;

    float lastTime_ = -1.f;
    float lastBend_ = -999.f;
    int lastIr_ = -1;
};

} // namespace Infrastructure
} // namespace AgentRack
