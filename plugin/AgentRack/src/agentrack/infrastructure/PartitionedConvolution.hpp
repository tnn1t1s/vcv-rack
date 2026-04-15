#pragma once

#include "../../FFTProvider.hpp"
#include <algorithm>
#include <complex>
#include <cstring>
#include <memory>
#include <vector>

namespace AgentRack {
namespace Infrastructure {

class PartitionedConvolution {
public:
    static constexpr int kBlockSize = 512;
    static constexpr int kFFTSize = kBlockSize * 2;
    static constexpr int kSpectrumLength = kFFTSize + 2;

    PartitionedConvolution() = default;

    void init() {
        fft_ = FFTProvider::create(kFFTSize);
    }

    void load(const float* rawL, const float* rawR, int irLength) {
        int totalParts = (irLength + kBlockSize - 1) / kBlockSize;
        hL_.resize(totalParts, std::vector<float>(kSpectrumLength, 0.f));
        hR_.resize(totalParts, std::vector<float>(kSpectrumLength, 0.f));
        fdlL_.assign(totalParts, std::vector<float>(kSpectrumLength, 0.f));
        fdlR_.assign(totalParts, std::vector<float>(kSpectrumLength, 0.f));

        float tmp[kSpectrumLength];
        for (int p = 0; p < totalParts; p++) {
            int offset = p * kBlockSize;
            int len = std::min(kBlockSize, irLength - offset);

            std::memset(tmp, 0, sizeof(tmp));
            std::memcpy(tmp, rawL + offset, len * sizeof(float));
            fft_->forward(tmp);
            std::memcpy(hL_[p].data(), tmp, kSpectrumLength * sizeof(float));

            std::memset(tmp, 0, sizeof(tmp));
            std::memcpy(tmp, rawR + offset, len * sizeof(float));
            fft_->forward(tmp);
            std::memcpy(hR_[p].data(), tmp, kSpectrumLength * sizeof(float));
        }

        activeParts_ = totalParts;
        fdlPos_ = 0;
        std::memset(inBufL_, 0, sizeof(inBufL_));
        std::memset(inBufR_, 0, sizeof(inBufR_));
        std::memset(outBufL_, 0, sizeof(outBufL_));
        std::memset(outBufR_, 0, sizeof(outBufR_));
        blockPos_ = 0;
    }

    void push(float inL, float inR, float& outL, float& outR) {
        sampleInL_[blockPos_] = inL;
        sampleInR_[blockPos_] = inR;
        outL = outBufL_[blockPos_];
        outR = outBufR_[blockPos_];
        blockPos_++;
        if (blockPos_ == kBlockSize) {
            blockPos_ = 0;
            processBlock();
        }
    }

private:
    void processBlock() {
        std::memcpy(inBufL_, inBufL_ + kBlockSize, kBlockSize * sizeof(float));
        std::memcpy(inBufR_, inBufR_ + kBlockSize, kBlockSize * sizeof(float));
        std::memcpy(inBufL_ + kBlockSize, sampleInL_, kBlockSize * sizeof(float));
        std::memcpy(inBufR_ + kBlockSize, sampleInR_, kBlockSize * sizeof(float));

        float xL[kSpectrumLength];
        float xR[kSpectrumLength];
        std::memcpy(xL, inBufL_, kFFTSize * sizeof(float));
        std::memcpy(xR, inBufR_, kFFTSize * sizeof(float));
        xL[kFFTSize] = xL[kFFTSize + 1] = 0.f;
        xR[kFFTSize] = xR[kFFTSize + 1] = 0.f;
        fft_->forward(xL);
        fft_->forward(xR);

        std::memcpy(fdlL_[fdlPos_].data(), xL, kSpectrumLength * sizeof(float));
        std::memcpy(fdlR_[fdlPos_].data(), xR, kSpectrumLength * sizeof(float));

        std::memset(accL_, 0, kSpectrumLength * sizeof(float));
        std::memset(accR_, 0, kSpectrumLength * sizeof(float));

        int active = std::min(activeParts_, (int)hL_.size());
        using Complex = std::complex<float>;
        int bins = kFFTSize / 2 + 1;

        for (int k = 0; k < active; k++) {
            int src = (fdlPos_ - k + active) % active;
            const Complex* xl = (const Complex*)fdlL_[src].data();
            const Complex* xr = (const Complex*)fdlR_[src].data();
            const Complex* hl = (const Complex*)hL_[k].data();
            const Complex* hr = (const Complex*)hR_[k].data();
            Complex* al = (Complex*)accL_;
            Complex* ar = (Complex*)accR_;
            for (int b = 0; b < bins; b++) {
                al[b] += xl[b] * hl[b];
                ar[b] += xr[b] * hr[b];
            }
        }

        fdlPos_ = (fdlPos_ + 1) % (active > 0 ? active : 1);

        fft_->inverse(accL_);
        fft_->inverse(accR_);
        std::memcpy(outBufL_, accL_ + kBlockSize, kBlockSize * sizeof(float));
        std::memcpy(outBufR_, accR_ + kBlockSize, kBlockSize * sizeof(float));
    }

    std::unique_ptr<FFTProvider> fft_;

    std::vector<std::vector<float>> hL_;
    std::vector<std::vector<float>> hR_;
    std::vector<std::vector<float>> fdlL_;
    std::vector<std::vector<float>> fdlR_;
    int fdlPos_ = 0;

    float inBufL_[kFFTSize] = {};
    float inBufR_[kFFTSize] = {};
    float outBufL_[kBlockSize] = {};
    float outBufR_[kBlockSize] = {};
    float accL_[kSpectrumLength] = {};
    float accR_[kSpectrumLength] = {};
    float sampleInL_[kBlockSize] = {};
    float sampleInR_[kBlockSize] = {};
    int blockPos_ = 0;
    int activeParts_ = 0;
};

} // namespace Infrastructure
} // namespace AgentRack
