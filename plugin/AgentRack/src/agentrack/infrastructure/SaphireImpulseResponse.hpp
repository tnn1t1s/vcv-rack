#pragma once

#include <algorithm>
#include <cmath>
#include <cstdio>
#include <string>
#include <utility>
#include <vector>

namespace AgentRack {
namespace Infrastructure {

// Owns the raw stereo IR and the deterministic time/bend transforms that turn
// it into a convolution kernel for a particular Saphire rebuild request.
class SaphireImpulseResponse {
public:
    static constexpr int kBlockSize = 512;
    static constexpr int kMaxIrLength = 132300;

    using Kernel = std::pair<std::vector<float>, std::vector<float>>;

    bool loadFromPath(const std::string& path, int irIndex) {
        FILE* file = std::fopen(path.c_str(), "rb");
        if (!file) {
            return false;
        }

        left_.clear();
        right_.clear();
        left_.reserve(kMaxIrLength);
        right_.reserve(kMaxIrLength);

        float frame[2];
        while (left_.size() < static_cast<size_t>(kMaxIrLength)
            && std::fread(frame, sizeof(float), 2, file) == 2) {
            left_.push_back(frame[0]);
            right_.push_back(frame[1]);
        }
        std::fclose(file);

        loadedIrIndex_ = irIndex;
        return !left_.empty();
    }

    void setRaw(const std::vector<float>& left, const std::vector<float>& right) {
        left_ = left;
        right_ = right;
        loadedIrIndex_ = -1;
    }

    int loadedIrIndex() const {
        return loadedIrIndex_;
    }

    int rawLength() const {
        return static_cast<int>(left_.size());
    }

    Kernel buildKernel(float timeParam, float bendParam) const {
        int rawSampleCount = rawLength();
        if (rawSampleCount <= 0) {
            return Kernel();
        }

        int warpedLength = static_cast<int>(kBlockSize + (rawSampleCount - kBlockSize) * timeParam);
        warpedLength = std::max(kBlockSize, std::min(rawSampleCount, warpedLength));

        float beta = std::exp(bendParam * std::log(3.f));
        float maxSourceIndex = static_cast<float>(rawSampleCount - 1);

        std::vector<float> warpedLeft(warpedLength);
        std::vector<float> warpedRight(warpedLength);
        for (int n = 0; n < warpedLength; ++n) {
            float t = (warpedLength > 1) ? static_cast<float>(n) / static_cast<float>(warpedLength - 1) : 0.f;
            float warpedPosition = std::pow(t, beta) * maxSourceIndex;
            int sourceIndex0 = static_cast<int>(warpedPosition);
            float fraction = warpedPosition - static_cast<float>(sourceIndex0);
            int sourceIndex1 = std::min(sourceIndex0 + 1, rawSampleCount - 1);

            warpedLeft[n] = left_[sourceIndex0] * (1.f - fraction) + left_[sourceIndex1] * fraction;
            warpedRight[n] = right_[sourceIndex0] * (1.f - fraction) + right_[sourceIndex1] * fraction;
        }

        return {std::move(warpedLeft), std::move(warpedRight)};
    }

private:
    std::vector<float> left_;
    std::vector<float> right_;
    int loadedIrIndex_ = -1;
};

} // namespace Infrastructure
} // namespace AgentRack
