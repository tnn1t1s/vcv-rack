#pragma once

#include <rack.hpp>
#include <algorithm>
#include <cmath>
#include <cstring>
#include <vector>

namespace AgentRack {
namespace TR909 {

/**
 * Shared helpers for the 909 family.
 *
 * The sample-based voices in this plugin embed clean PCM captures directly in
 * C++ headers. Each module treats that payload as its "ROM" source, then
 * re-applies the 909-style shaping stage in code: sample-rate tuning, analog
 * envelope control, and light filtering / drive.
 *
 * This keeps each module self-contained:
 *   - no external docs are required to understand the architecture
 *   - no runtime file loading is required for the cymbal family
 *   - the voice comments stay next to the DSP that implements them
 */

static constexpr float kCvScale = 0.1f;

inline float normWithCV(rack::Module& self, int paramId, int inputId) {
    float norm = self.params[paramId].getValue()
               + self.inputs[inputId].getVoltage() * kCvScale;
    return rack::math::clamp(norm, 0.f, 1.f);
}

inline std::vector<float> decodeEmbeddedF32(const unsigned char* bytes, size_t byteCount) {
    size_t frames = byteCount / sizeof(float);
    std::vector<float> out(frames);
    std::memcpy(out.data(), bytes, frames * sizeof(float));
    return out;
}

inline float sampleAt(const std::vector<float>& data, float pos) {
    if (data.empty() || pos < 0.f || pos >= float(data.size() - 1))
        return 0.f;
    int i0 = int(pos);
    int i1 = std::min(i0 + 1, int(data.size() - 1));
    float frac = pos - float(i0);
    return data[i0] + (data[i1] - data[i0]) * frac;
}

inline float playbackStep(float sourceSampleRate, float hostSampleRate, float playbackRate) {
    return (sourceSampleRate / hostSampleRate) * playbackRate;
}

inline float clampFilterHz(float hz, float sampleRate) {
    return std::min(hz, sampleRate * 0.45f);
}

inline float drive(float x, float driveNorm) {
    if (driveNorm <= 1e-5f)
        return x;
    float g = 1.f + driveNorm * 4.5f;
    return std::tanh(x * g) / std::sqrt(g);
}

struct RomTailAssetConfig {
    float sourceSampleRate = 44100.f;
    float loopStartNorm = 0.06f;
    float loopEndNorm = 0.40f;
    float hpCoef = 0.985f;
    int rmsWindow = 384;
    float targetRms = 0.10f;
    float rmsFloor = 0.01f;
    float maxGain = 6.f;
    int edgeFadeSamples = 192;

    RomTailAssetConfig() {}
    RomTailAssetConfig(float sourceSampleRate,
                       float loopStartNorm,
                       float loopEndNorm,
                       float hpCoef,
                       int rmsWindow,
                       float targetRms,
                       float rmsFloor,
                       float maxGain,
                       int edgeFadeSamples)
        : sourceSampleRate(sourceSampleRate),
          loopStartNorm(loopStartNorm),
          loopEndNorm(loopEndNorm),
          hpCoef(hpCoef),
          rmsWindow(rmsWindow),
          targetRms(targetRms),
          rmsFloor(rmsFloor),
          maxGain(maxGain),
          edgeFadeSamples(edgeFadeSamples) {}
};

struct RomTailAsset {
    float sourceSampleRate = 44100.f;
    std::vector<float> source;
    std::vector<float> textureLoop;
};

inline std::vector<float> buildTextureLoop(const std::vector<float>& source,
                                           const RomTailAssetConfig& cfg) {
    if (source.size() < 16) {
        return source;
    }

    size_t start = size_t(cfg.loopStartNorm * float(source.size()));
    size_t end   = size_t(cfg.loopEndNorm   * float(source.size()));
    start = std::min(start, source.size() - 2);
    end = std::max(end, start + 8);
    end = std::min(end, source.size());

    std::vector<float> loop(source.begin() + start, source.begin() + end);
    if (loop.size() < 8) {
        return loop;
    }

    // Remove most of the baked amplitude slope so decay control can rebuild
    // the energy contour instead of inheriting the raw PCM tail.
    std::vector<float> hp(loop.size(), 0.f);
    float prevIn = 0.f;
    float prevOut = 0.f;
    for (size_t i = 0; i < loop.size(); i++) {
        float x = loop[i];
        float y = x - prevIn + cfg.hpCoef * prevOut;
        hp[i] = y;
        prevIn = x;
        prevOut = y;
    }

    const int win = std::max(8, cfg.rmsWindow);
    double sumSq = 0.0;
    for (int i = 0; i < win && i < (int)hp.size(); i++) {
        sumSq += double(hp[(size_t)i]) * double(hp[(size_t)i]);
    }

    std::vector<float> out(hp.size(), 0.f);
    for (size_t i = 0; i < hp.size(); i++) {
        size_t addIndex = i + size_t(win / 2);
        size_t removeIndex = (i > size_t(win / 2)) ? (i - size_t(win / 2) - 1) : size_t(-1);
        if (addIndex < hp.size() && addIndex >= (size_t)win) {
            sumSq += double(hp[addIndex]) * double(hp[addIndex]);
        }
        if (removeIndex < hp.size()) {
            sumSq -= double(hp[removeIndex]) * double(hp[removeIndex]);
        }

        float rms = std::sqrt(float(std::max(sumSq, 0.0) / double(win)));
        float gain = cfg.targetRms / std::max(rms, cfg.rmsFloor);
        gain = std::min(gain, cfg.maxGain);
        out[i] = hp[i] * gain;
    }

    const int fade = std::min<int>(cfg.edgeFadeSamples, (int)out.size() / 4);
    for (int i = 0; i < fade; i++) {
        float t = float(i) / float(std::max(1, fade - 1));
        out[(size_t)i] *= t;
        out[out.size() - 1 - (size_t)i] *= t;
    }

    // Crossfade the loop boundary to avoid obvious clicks when the texture
    // branch wraps under a long decay.
    for (int i = 0; i < fade; i++) {
        float t = float(i) / float(std::max(1, fade - 1));
        size_t tailIndex = out.size() - fade + (size_t)i;
        float a = out[tailIndex];
        float b = out[(size_t)i];
        out[tailIndex] = a * (1.f - t) + b * t;
    }

    return out;
}

inline RomTailAsset makeRomTailAsset(const std::vector<float>& source,
                                     const RomTailAssetConfig& cfg) {
    RomTailAsset asset;
    asset.sourceSampleRate = cfg.sourceSampleRate;
    asset.source = source;
    asset.textureLoop = buildTextureLoop(source, cfg);
    return asset;
}

struct RomTailVoiceConfig {
    float sourceGain = 1.f;
    float tailGain = 0.65f;
    float tailGainDecayScale = 0.f;
    float tailAttackSec = 0.012f;
    float tailPlaybackRate = 1.f;

    RomTailVoiceConfig() {}
    RomTailVoiceConfig(float sourceGain,
                       float tailGain,
                       float tailGainDecayScale,
                       float tailAttackSec,
                       float tailPlaybackRate)
        : sourceGain(sourceGain),
          tailGain(tailGain),
          tailGainDecayScale(tailGainDecayScale),
          tailAttackSec(tailAttackSec),
          tailPlaybackRate(tailPlaybackRate) {}
};

struct RomTailVoice {
    float sourcePos = 1e9f;
    float tailPos = 0.f;
    float env = 0.f;
    float ageSec = 0.f;

    void trigger() {
        sourcePos = 0.f;
        tailPos = 0.f;
        env = 1.f;
        ageSec = 0.f;
    }

    float process(const rack::Module::ProcessArgs& args,
                  const RomTailAsset& asset,
                  float playbackRate,
                  float decaySec,
                  float decayNorm,
                  const RomTailVoiceConfig& cfg) {
        if (asset.source.empty()) {
            return 0.f;
        }

        const float step = playbackStep(asset.sourceSampleRate, args.sampleRate, playbackRate);
        float source = sampleAt(asset.source, sourcePos);
        sourcePos += step;

        float tail = 0.f;
        if (!asset.textureLoop.empty()) {
            tail = sampleAt(asset.textureLoop, tailPos);
            tailPos += step * cfg.tailPlaybackRate;
            float limit = float(std::max<size_t>(1, asset.textureLoop.size() - 1));
            while (tailPos >= limit) tailPos -= limit;
        }

        float tailFade = 1.f - std::exp(-ageSec / std::max(1e-4f, cfg.tailAttackSec));
        float tailGain = cfg.tailGain + decayNorm * cfg.tailGainDecayScale;
        float out = source * cfg.sourceGain + tail * tailGain * env * tailFade;

        env *= std::exp(-args.sampleTime / std::max(1e-4f, decaySec));
        ageSec += args.sampleTime;
        return out;
    }
};

struct TptSVF {
    float ic1 = 0.f;
    float ic2 = 0.f;
    float lpf = 0.f;
    float bpf = 0.f;
    float hpf = 0.f;

    void reset() {
        ic1 = ic2 = lpf = bpf = hpf = 0.f;
    }

    void process(float x, float fHz, float sampleRate, float Q) {
        float g = std::tan(float(M_PI) * fHz / sampleRate);
        float k = 1.f / Q;
        float a1 = 1.f / (1.f + g * (g + k));
        float a2 = g * a1;
        float a3 = g * a2;
        float v3 = x - ic2;
        float v1 = a1 * ic1 + a2 * v3;
        float v2 = ic2 + a2 * ic1 + a3 * v3;
        ic1 = 2.f * v1 - ic1;
        ic2 = 2.f * v2 - ic2;
        bpf = v1;
        lpf = v2;
        hpf = x - k * v1 - v2;
    }
};

}  // namespace TR909
}  // namespace AgentRack
