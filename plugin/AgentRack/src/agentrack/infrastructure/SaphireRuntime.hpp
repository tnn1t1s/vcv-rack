#pragma once

#include "PartitionedConvolution.hpp"
#include <atomic>
#include <cmath>
#include <thread>

namespace AgentRack {
namespace Infrastructure {

// Owns the live/rebuild convolution engines plus the thread-safe handoff
// between background IR rebuilds and the audio thread's crossfade.
class SaphireRuntime {
public:
    static constexpr float kParamEpsilon = 0.001f;

    struct RebuildRequest {
        int irIndex = 0;
        float timeParam = 0.f;
        float bendParam = 0.f;

        RebuildRequest() = default;
        RebuildRequest(int requestedIrIndex, float requestedTimeParam, float requestedBendParam)
        : irIndex(requestedIrIndex), timeParam(requestedTimeParam), bendParam(requestedBendParam) {}
    };

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

    static RebuildRequest makeRequest(float irParam, float timeParam, float bendParam, int irCount) {
        RebuildRequest request;
        request.irIndex = std::max(0, std::min(irCount - 1, static_cast<int>(std::round(irParam))));
        request.timeParam = timeParam;
        request.bendParam = bendParam;
        return request;
    }

    bool shouldRebuild(const RebuildRequest& request) const {
        return request.irIndex != lastIr_
            || std::fabs(request.timeParam - lastTime_) > kParamEpsilon
            || std::fabs(request.bendParam - lastBend_) > kParamEpsilon;
    }

    template <typename RebuildFn>
    bool launchRebuild(const RebuildRequest& request, RebuildFn rebuild) {
        if (building_.exchange(true)) {
            return false;
        }

        // While the inactive engine is being rewritten, the audio thread must
        // stop pushing into it. A completed rebuild restores old-engine safety
        // for the duration of the crossfade only.
        safeOld_.store(false);
        joinBuilder();

        lastIr_ = request.irIndex;
        lastTime_ = request.timeParam;
        lastBend_ = request.bendParam;
        int targetIndex = rebuildIndex();

        builder_ = std::thread([this, request, targetIndex, rebuild]() {
            rebuild(targetIndex, request.irIndex);
            currentIrIndex_.store(request.irIndex);
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
