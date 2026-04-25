#pragma once

#include "../src/FFTProvider.hpp"

#include <algorithm>
#include <cerrno>
#include <cmath>
#include <complex>
#include <cstdint>
#include <cstdio>
#include <cstdlib>
#include <fstream>
#include <iomanip>
#include <map>
#include <sstream>
#include <stdexcept>
#include <string>
#include <sys/stat.h>
#include <vector>

namespace VoiceLab {

struct AudioFile {
    int sampleRate = 44100;
    std::vector<float> samples;
};

struct Analysis {
    std::string sourcePath;
    int sampleRate = 44100;
    int originalFrames = 0;
    int trimStartFrame = 0;
    int trimEndFrame = 0;
    int fftSize = 0;
    float peak = 0.f;
    float rms = 0.f;
    float durationSeconds = 0.f;
    float attackSeconds = 0.f;
    float decay20Seconds = 0.f;
    float decay40Seconds = 0.f;
    float zeroCrossingRate = 0.f;
    float spectralCentroidMeanHz = 0.f;
    std::vector<float> fftBandEdgesHz;
    std::vector<float> fftBandEnergy;
    std::vector<float> envelopeWindows;
    std::vector<float> centroidWindowsHz;
    std::vector<float> bodyPitchWindowsHz;
    std::vector<float> upperBodyModeWindowsHz;
    std::vector<std::vector<float> > bandEnergyWindows;
};

struct CompareResult {
    float total = 0.f;
    float envelope = 0.f;
    float spectrum = 0.f;
    float bandTrajectory = 0.f;
    float bodyBand = 0.f;
    float bodyPitchTrajectory = 0.f;
    float upperBodyModeTrajectory = 0.f;
    float bodyNoiseTrajectory = 0.f;
    float onsetClickTrajectory = 0.f;
    float onsetCentroidTrajectory = 0.f;
    float duration = 0.f;
    float attack = 0.f;
};

static inline int nextPow2(int x) {
    int n = 1;
    while (n < x) n <<= 1;
    return n;
}

static inline float clamp01(float x) {
    if (x < 0.f) return 0.f;
    if (x > 1.f) return 1.f;
    return x;
}

static inline float absPeak(const std::vector<float>& xs) {
    float peak = 0.f;
    for (size_t i = 0; i < xs.size(); i++) {
        peak = std::max(peak, std::fabs(xs[i]));
    }
    return peak;
}

static inline std::string jsonQuote(const std::string& s) {
    std::ostringstream os;
    os << '"';
    for (size_t i = 0; i < s.size(); i++) {
        const char c = s[i];
        switch (c) {
        case '\\': os << "\\\\"; break;
        case '"': os << "\\\""; break;
        case '\n': os << "\\n"; break;
        case '\r': os << "\\r"; break;
        case '\t': os << "\\t"; break;
        default: os << c; break;
        }
    }
    os << '"';
    return os.str();
}

template <typename T>
static inline std::string jsonArray(const std::vector<T>& xs, int precision = 6) {
    std::ostringstream os;
    os << "[";
    for (size_t i = 0; i < xs.size(); i++) {
        if (i) os << ",";
        os << std::fixed << std::setprecision(precision) << xs[i];
    }
    os << "]";
    return os.str();
}

static inline std::string jsonNestedArray(const std::vector<std::vector<float> >& rows,
                                          int precision = 6) {
    std::ostringstream os;
    os << "[";
    for (size_t i = 0; i < rows.size(); i++) {
        if (i) os << ",";
        os << jsonArray(rows[i], precision);
    }
    os << "]";
    return os.str();
}

static inline bool writeTextFile(const std::string& path, const std::string& text) {
    std::ofstream out(path.c_str(), std::ios::binary);
    if (!out) return false;
    out << text;
    return out.good();
}

static inline bool makeDirs(const std::string& path) {
    if (path.empty()) return false;
    std::string cur;
    if (path[0] == '/') cur = "/";
    for (size_t i = 0; i < path.size(); i++) {
        char c = path[i];
        cur.push_back(c);
        if (c != '/' && i + 1 != path.size()) continue;
        if (cur.size() <= 1) continue;
        if (::mkdir(cur.c_str(), 0755) != 0 && errno != EEXIST) return false;
    }
    if (::mkdir(path.c_str(), 0755) != 0 && errno != EEXIST) return false;
    return true;
}

static inline uint16_t readLe16(const unsigned char* p) {
    return uint16_t(p[0]) | (uint16_t(p[1]) << 8);
}

static inline uint32_t readLe32(const unsigned char* p) {
    return uint32_t(p[0]) | (uint32_t(p[1]) << 8) | (uint32_t(p[2]) << 16) | (uint32_t(p[3]) << 24);
}

static inline int32_t readLe24Signed(const unsigned char* p) {
    int32_t v = int32_t(uint32_t(p[0]) | (uint32_t(p[1]) << 8) | (uint32_t(p[2]) << 16));
    if (v & 0x00800000) v |= ~0x00ffffff;
    return v;
}

static inline float readF32Le(const unsigned char* p) {
    union {
        uint32_t u;
        float f;
    } cvt;
    cvt.u = readLe32(p);
    return cvt.f;
}

static inline void writeLe16(std::ofstream& out, uint16_t v) {
    char b[2];
    b[0] = char(v & 0xff);
    b[1] = char((v >> 8) & 0xff);
    out.write(b, 2);
}

static inline void writeLe32(std::ofstream& out, uint32_t v) {
    char b[4];
    b[0] = char(v & 0xff);
    b[1] = char((v >> 8) & 0xff);
    b[2] = char((v >> 16) & 0xff);
    b[3] = char((v >> 24) & 0xff);
    out.write(b, 4);
}

static inline AudioFile resampleLinearMono(const AudioFile& in, int targetSampleRate) {
    if (in.sampleRate == targetSampleRate || in.samples.empty()) return in;

    AudioFile out;
    out.sampleRate = targetSampleRate;
    const double ratio = double(targetSampleRate) / double(in.sampleRate);
    const size_t outFrames = std::max<size_t>(1, (size_t)std::llround(in.samples.size() * ratio));
    out.samples.resize(outFrames);

    for (size_t i = 0; i < outFrames; i++) {
        const double srcPos = double(i) * double(in.sampleRate) / double(targetSampleRate);
        const size_t i0 = std::min<size_t>((size_t)srcPos, in.samples.size() - 1);
        const size_t i1 = std::min<size_t>(i0 + 1, in.samples.size() - 1);
        const float frac = (float)(srcPos - double(i0));
        out.samples[i] = in.samples[i0] * (1.f - frac) + in.samples[i1] * frac;
    }
    return out;
}

static inline AudioFile readWavNormalized(const std::string& path, int targetSampleRate = 44100) {
    std::ifstream in(path.c_str(), std::ios::binary);
    if (!in) throw std::runtime_error("could not open wav: " + path);

    std::vector<unsigned char> bytes((std::istreambuf_iterator<char>(in)),
                                     std::istreambuf_iterator<char>());
    if (bytes.size() < 44) throw std::runtime_error("wav too small: " + path);
    if (std::string((const char*)&bytes[0], (const char*)&bytes[4]) != "RIFF" ||
        std::string((const char*)&bytes[8], (const char*)&bytes[12]) != "WAVE") {
        throw std::runtime_error("not a RIFF/WAVE file: " + path);
    }

    int channels = 0;
    int sampleRate = 0;
    int bitsPerSample = 0;
    int audioFormat = 0;
    int blockAlign = 0;
    size_t dataOffset = 0;
    size_t dataSize = 0;

    size_t off = 12;
    while (off + 8 <= bytes.size()) {
        std::string chunkId((const char*)&bytes[off], (const char*)&bytes[off + 4]);
        uint32_t chunkSize = readLe32(&bytes[off + 4]);
        off += 8;
        if (off + chunkSize > bytes.size()) break;

        if (chunkId == "fmt ") {
            if (chunkSize < 16) throw std::runtime_error("invalid fmt chunk: " + path);
            audioFormat = readLe16(&bytes[off + 0]);
            channels = readLe16(&bytes[off + 2]);
            sampleRate = (int)readLe32(&bytes[off + 4]);
            blockAlign = readLe16(&bytes[off + 12]);
            bitsPerSample = readLe16(&bytes[off + 14]);
        } else if (chunkId == "data") {
            dataOffset = off;
            dataSize = chunkSize;
        }
        off += chunkSize + (chunkSize & 1u);
    }

    if (!(audioFormat == 1 || audioFormat == 3)) {
        throw std::runtime_error("unsupported wav format (need PCM or float): " + path);
    }
    if (channels <= 0) throw std::runtime_error("wav has invalid channel count: " + path);
    if (!dataOffset || !dataSize) throw std::runtime_error("wav missing data chunk: " + path);
    if (blockAlign <= 0) throw std::runtime_error("wav has invalid block align: " + path);

    const int bytesPerSample = bitsPerSample / 8;
    if (bytesPerSample <= 0) throw std::runtime_error("wav has invalid bits per sample: " + path);
    if (blockAlign != channels * bytesPerSample) {
        throw std::runtime_error("wav block align does not match channel/sample layout: " + path);
    }

    AudioFile audio;
    audio.sampleRate = sampleRate;
    const size_t frameCount = dataSize / (size_t)blockAlign;
    audio.samples.resize(frameCount);

    for (size_t frame = 0; frame < frameCount; frame++) {
        const unsigned char* framePtr = &bytes[dataOffset + frame * (size_t)blockAlign];
        double mix = 0.0;
        for (int ch = 0; ch < channels; ch++) {
            const unsigned char* p = framePtr + ch * bytesPerSample;
            float s = 0.f;
            if (audioFormat == 1) {
                switch (bitsPerSample) {
                case 8:
                    s = ((int)p[0] - 128) / 128.f;
                    break;
                case 16:
                    s = (float)(int16_t)readLe16(p) / 32768.f;
                    break;
                case 24:
                    s = (float)readLe24Signed(p) / 8388608.f;
                    break;
                case 32:
                    s = (float)(int32_t)readLe32(p) / 2147483648.f;
                    break;
                default:
                    throw std::runtime_error("unsupported PCM bit depth: " + path);
                }
            } else if (audioFormat == 3) {
                if (bitsPerSample != 32) {
                    throw std::runtime_error("unsupported float bit depth: " + path);
                }
                s = readF32Le(p);
            }
            mix += s;
        }
        audio.samples[frame] = std::max(-1.f, std::min(1.f, (float)(mix / double(channels))));
    }
    return resampleLinearMono(audio, targetSampleRate);
}

static inline bool writeMonoWav16(const std::string& path, const AudioFile& audio) {
    std::ofstream out(path.c_str(), std::ios::binary);
    if (!out) return false;

    const uint32_t dataBytes = (uint32_t)(audio.samples.size() * 2);
    out.write("RIFF", 4);
    writeLe32(out, 36 + dataBytes);
    out.write("WAVE", 4);
    out.write("fmt ", 4);
    writeLe32(out, 16);
    writeLe16(out, 1);
    writeLe16(out, 1);
    writeLe32(out, (uint32_t)audio.sampleRate);
    writeLe32(out, (uint32_t)(audio.sampleRate * 2));
    writeLe16(out, 2);
    writeLe16(out, 16);
    out.write("data", 4);
    writeLe32(out, dataBytes);
    for (size_t i = 0; i < audio.samples.size(); i++) {
        float s = std::max(-1.f, std::min(1.f, audio.samples[i]));
        int v = (int)std::lround(s * 32767.f);
        if (v < -32768) v = -32768;
        if (v > 32767) v = 32767;
        writeLe16(out, (uint16_t)(int16_t)v);
    }
    return out.good();
}

static inline std::vector<float> trimmedNormalized(const AudioFile& audio,
                                                   int* trimStartFrame,
                                                   int* trimEndFrame,
                                                   float* peakOut) {
    if (audio.samples.empty()) {
        *trimStartFrame = 0;
        *trimEndFrame = 0;
        *peakOut = 0.f;
        return std::vector<float>();
    }

    const float peak = absPeak(audio.samples);
    const float threshold = std::max(1e-4f, peak * 0.02f);

    int start = 0;
    while (start < (int)audio.samples.size() && std::fabs(audio.samples[start]) < threshold) start++;

    int end = (int)audio.samples.size();
    while (end > start && std::fabs(audio.samples[end - 1]) < threshold) end--;

    if (start >= end) {
        start = 0;
        end = (int)audio.samples.size();
    }

    std::vector<float> out(audio.samples.begin() + start, audio.samples.begin() + end);
    const float trimmedPeak = std::max(1e-8f, absPeak(out));
    for (size_t i = 0; i < out.size(); i++) out[i] /= trimmedPeak;

    *trimStartFrame = start;
    *trimEndFrame = end;
    *peakOut = peak;
    return out;
}

static inline float windowRms(const std::vector<float>& xs, int start, int end) {
    if (end <= start) return 0.f;
    double sum = 0.0;
    for (int i = start; i < end; i++) sum += xs[i] * xs[i];
    return (float)std::sqrt(sum / double(end - start));
}

static inline void computeSpectrum(const std::vector<float>& segment,
                                   int sampleRate,
                                   const std::vector<float>& bandEdgesHz,
                                   int fftSize,
                                   std::vector<float>* bandEnergy,
                                   float* centroidHz,
                                   float* bodyPitchHz = nullptr,
                                   float* upperBodyModeHz = nullptr) {
    if ((int)segment.size() == 0) {
        bandEnergy->assign(bandEdgesHz.size() > 1 ? bandEdgesHz.size() - 1 : 0, 0.f);
        *centroidHz = 0.f;
        if (bodyPitchHz) *bodyPitchHz = 0.f;
        if (upperBodyModeHz) *upperBodyModeHz = 0.f;
        return;
    }

    fftSize = std::max(128, nextPow2(fftSize));
    std::vector<float> buf((size_t)fftSize + 2, 0.f);
    const int n = std::min((int)segment.size(), fftSize);
    for (int i = 0; i < n; i++) {
        const float w = 0.5f - 0.5f * std::cos(2.f * float(M_PI) * i / std::max(1, n - 1));
        buf[(size_t)i] = segment[(size_t)i] * w;
    }

    std::unique_ptr<FFTProvider> fft = FFTProvider::create(fftSize);
    fft->forward(buf.data());

    const std::complex<float>* spec = (const std::complex<float>*)buf.data();
    const int bins = fftSize / 2 + 1;
    bandEnergy->assign(bandEdgesHz.size() > 1 ? bandEdgesHz.size() - 1 : 0, 0.f);

    double centroidNum = 0.0;
    double centroidDen = 0.0;
    float bestBodyMag = -1.f;
    int bestBodyBin = -1;
    float bestUpperBodyMag = -1.f;
    int bestUpperBodyBin = -1;
    for (int k = 0; k < bins; k++) {
        const float freq = float(k) * sampleRate / float(fftSize);
        const float mag = std::abs(spec[k]);
        centroidNum += freq * mag;
        centroidDen += mag;
        if (freq >= 120.f && freq <= 400.f && mag > bestBodyMag) {
            bestBodyMag = mag;
            bestBodyBin = k;
        }
        if (freq >= 260.f && freq <= 420.f && mag > bestUpperBodyMag) {
            bestUpperBodyMag = mag;
            bestUpperBodyBin = k;
        }

        for (size_t b = 0; b + 1 < bandEdgesHz.size(); b++) {
            if (freq >= bandEdgesHz[b] && freq < bandEdgesHz[b + 1]) {
                (*bandEnergy)[b] += mag * mag;
                break;
            }
        }
    }

    float sumBands = 0.f;
    for (size_t i = 0; i < bandEnergy->size(); i++) sumBands += (*bandEnergy)[i];
    if (sumBands > 1e-12f) {
        for (size_t i = 0; i < bandEnergy->size(); i++) (*bandEnergy)[i] /= sumBands;
    }

    *centroidHz = centroidDen > 1e-12 ? (float)(centroidNum / centroidDen) : 0.f;
    auto interpolatedPeakHz = [&](int bin) -> float {
        float pitch = 0.f;
        if (bin >= 0) {
            float interpBin = (float)bin;
            if (bin > 0 && bin + 1 < bins) {
                const float ym1 = std::log(std::max(1e-12f, std::abs(spec[bin - 1])));
                const float y0  = std::log(std::max(1e-12f, std::abs(spec[bin])));
                const float yp1 = std::log(std::max(1e-12f, std::abs(spec[bin + 1])));
                const float denom = ym1 - 2.f * y0 + yp1;
                if (std::fabs(denom) > 1e-12f) {
                    const float delta = 0.5f * (ym1 - yp1) / denom;
                    if (std::fabs(delta) <= 1.f) interpBin += delta;
                }
            }
            pitch = interpBin * sampleRate / float(fftSize);
        }
        return pitch;
    };
    if (bodyPitchHz) {
        *bodyPitchHz = interpolatedPeakHz(bestBodyBin);
    }
    if (upperBodyModeHz) {
        *upperBodyModeHz = interpolatedPeakHz(bestUpperBodyBin);
    }
}

static inline Analysis analyzeAudio(const AudioFile& audio,
                                    const std::string& sourcePath = std::string(),
                                    int envelopeWindowCount = 64,
                                    int trajectoryWindowCount = 32,
                                    int fftSizeHint = 2048) {
    Analysis out;
    out.sourcePath = sourcePath;
    out.sampleRate = audio.sampleRate;
    out.originalFrames = (int)audio.samples.size();
    out.fftBandEdgesHz.push_back(0.f);
    out.fftBandEdgesHz.push_back(80.f);
    out.fftBandEdgesHz.push_back(160.f);
    out.fftBandEdgesHz.push_back(320.f);
    out.fftBandEdgesHz.push_back(640.f);
    out.fftBandEdgesHz.push_back(1280.f);
    out.fftBandEdgesHz.push_back(2560.f);
    out.fftBandEdgesHz.push_back(5120.f);
    out.fftBandEdgesHz.push_back(10000.f);
    out.fftBandEdgesHz.push_back(20000.f);

    float rawPeak = 0.f;
    std::vector<float> trimmed = trimmedNormalized(audio, &out.trimStartFrame, &out.trimEndFrame, &rawPeak);
    out.peak = rawPeak;
    out.durationSeconds = trimmed.empty() ? 0.f : float(trimmed.size()) / float(audio.sampleRate);

    if (trimmed.empty()) {
        out.trimStartFrame = 0;
        out.trimEndFrame = 0;
        out.fftSize = 0;
        return out;
    }

    out.rms = windowRms(trimmed, 0, (int)trimmed.size());

    int attackIdx = 0;
    while (attackIdx < (int)trimmed.size() && std::fabs(trimmed[(size_t)attackIdx]) < 0.9f) attackIdx++;
    out.attackSeconds = float(attackIdx) / float(audio.sampleRate);

    int peakIdx = 0;
    float peakVal = 0.f;
    for (size_t i = 0; i < trimmed.size(); i++) {
        const float v = std::fabs(trimmed[i]);
        if (v > peakVal) {
            peakVal = v;
            peakIdx = (int)i;
        }
    }
    int decay20 = (int)trimmed.size() - 1;
    int decay40 = (int)trimmed.size() - 1;
    for (int i = peakIdx; i < (int)trimmed.size(); i++) {
        const float v = std::fabs(trimmed[(size_t)i]);
        if (decay20 == (int)trimmed.size() - 1 && v <= 0.1f) decay20 = i;
        if (decay40 == (int)trimmed.size() - 1 && v <= 0.01f) {
            decay40 = i;
            break;
        }
    }
    out.decay20Seconds = float(std::max(0, decay20 - peakIdx)) / float(audio.sampleRate);
    out.decay40Seconds = float(std::max(0, decay40 - peakIdx)) / float(audio.sampleRate);

    int zc = 0;
    for (size_t i = 1; i < trimmed.size(); i++) {
        if ((trimmed[i - 1] >= 0.f && trimmed[i] < 0.f) || (trimmed[i - 1] < 0.f && trimmed[i] >= 0.f)) {
            zc++;
        }
    }
    out.zeroCrossingRate = trimmed.size() > 1 ? float(zc) / float(trimmed.size() - 1) : 0.f;

    out.fftSize = std::min(4096, std::max(512, nextPow2(std::min((int)trimmed.size(), fftSizeHint))));
    computeSpectrum(trimmed, audio.sampleRate, out.fftBandEdgesHz, out.fftSize,
                    &out.fftBandEnergy, &out.spectralCentroidMeanHz);

    out.envelopeWindows.resize((size_t)envelopeWindowCount, 0.f);
    for (int i = 0; i < envelopeWindowCount; i++) {
        int start = (int)((int64_t)i * (int64_t)trimmed.size() / envelopeWindowCount);
        int end = (int)((int64_t)(i + 1) * (int64_t)trimmed.size() / envelopeWindowCount);
        out.envelopeWindows[(size_t)i] = windowRms(trimmed, start, end);
    }
    float envPeak = absPeak(out.envelopeWindows);
    if (envPeak > 1e-8f) {
        for (size_t i = 0; i < out.envelopeWindows.size(); i++) out.envelopeWindows[i] /= envPeak;
    }

    const int frameSize = std::min(1024, std::max(128, nextPow2(std::max(32, (int)trimmed.size() / std::max(1, trajectoryWindowCount)))));
    const int hop = trajectoryWindowCount > 1 && (int)trimmed.size() > frameSize
                  ? std::max(1, ((int)trimmed.size() - frameSize) / (trajectoryWindowCount - 1))
                  : frameSize;
    out.centroidWindowsHz.reserve((size_t)trajectoryWindowCount);
    out.bodyPitchWindowsHz.reserve((size_t)trajectoryWindowCount);
    out.upperBodyModeWindowsHz.reserve((size_t)trajectoryWindowCount);
    out.bandEnergyWindows.reserve((size_t)trajectoryWindowCount);
    for (int i = 0; i < trajectoryWindowCount; i++) {
        int start = std::min(std::max(0, i * hop), std::max(0, (int)trimmed.size() - frameSize));
        int end = std::min((int)trimmed.size(), start + frameSize);
        std::vector<float> frame(trimmed.begin() + start, trimmed.begin() + end);
        std::vector<float> bands;
        float centroidHz = 0.f;
        float bodyPitchHz = 0.f;
        float upperBodyModeHz = 0.f;
        computeSpectrum(frame, audio.sampleRate, out.fftBandEdgesHz, frameSize, &bands, &centroidHz,
                        &bodyPitchHz, &upperBodyModeHz);
        out.centroidWindowsHz.push_back(centroidHz);
        out.bodyPitchWindowsHz.push_back(bodyPitchHz);
        out.upperBodyModeWindowsHz.push_back(upperBodyModeHz);
        out.bandEnergyWindows.push_back(bands);
    }

    return out;
}

static inline float meanAbsDistance(const std::vector<float>& a, const std::vector<float>& b, float norm = 1.f) {
    const size_t n = std::min(a.size(), b.size());
    if (!n) return 0.f;
    double sum = 0.0;
    const double denom = std::max(1e-8f, norm);
    for (size_t i = 0; i < n; i++) sum += std::fabs(a[i] - b[i]) / denom;
    return clamp01((float)(sum / double(n)));
}

static inline float meanAbsDistance2D(const std::vector<std::vector<float> >& a,
                                      const std::vector<std::vector<float> >& b) {
    const size_t n = std::min(a.size(), b.size());
    if (!n) return 0.f;
    double sum = 0.0;
    for (size_t i = 0; i < n; i++) sum += meanAbsDistance(a[i], b[i], 1.f);
    return clamp01((float)(sum / double(n)));
}

static inline float meanSquaredDistance(const std::vector<float>& a,
                                        const std::vector<float>& b,
                                        float norm = 1.f) {
    const size_t n = std::min(a.size(), b.size());
    if (!n) return 0.f;
    double sum = 0.0;
    const double denom = std::max(1e-8f, norm);
    for (size_t i = 0; i < n; i++) {
        const double d = (double(a[i]) - double(b[i])) / denom;
        sum += d * d;
    }
    return clamp01((float)(sum / double(n)));
}

static inline float meanSquaredDistance2D(const std::vector<std::vector<float> >& a,
                                          const std::vector<std::vector<float> >& b) {
    const size_t n = std::min(a.size(), b.size());
    if (!n) return 0.f;
    double sum = 0.0;
    for (size_t i = 0; i < n; i++) sum += meanSquaredDistance(a[i], b[i], 1.f);
    return clamp01((float)(sum / double(n)));
}

static inline float weightedMeanSquaredDistance(const std::vector<float>& a,
                                               const std::vector<float>& b,
                                               const std::vector<float>& weights,
                                               float norm = 1.f) {
    const size_t n = std::min(a.size(), std::min(b.size(), weights.size()));
    if (!n) return 0.f;
    const double denom = std::max(1e-8f, norm);
    double num = 0.0;
    double den = 0.0;
    for (size_t i = 0; i < n; i++) {
        const double w = std::max(0.f, weights[i]);
        const double d = (double(a[i]) - double(b[i])) / denom;
        num += w * d * d;
        den += w;
    }
    return clamp01((float)(num / std::max(1e-12, den)));
}

static inline std::vector<float> selectBands(const std::vector<float>& bands,
                                             const std::vector<int>& indices) {
    std::vector<float> out;
    out.reserve(indices.size());
    for (size_t i = 0; i < indices.size(); i++) {
        const int idx = indices[i];
        out.push_back(idx >= 0 && idx < (int)bands.size() ? bands[(size_t)idx] : 0.f);
    }
    return out;
}

static inline std::vector<float> bodyNoiseRatioTrajectory(const std::vector<std::vector<float> >& windows) {
    std::vector<float> out;
    out.reserve(windows.size());
    for (size_t i = 0; i < windows.size(); i++) {
        const std::vector<float>& w = windows[i];
        const float body =
            (w.size() > 2 ? w[2] : 0.f) +
            (w.size() > 3 ? w[3] : 0.f) +
            (w.size() > 4 ? w[4] : 0.f);
        const float noise =
            (w.size() > 6 ? w[6] : 0.f) +
            (w.size() > 7 ? w[7] : 0.f) +
            (w.size() > 8 ? w[8] : 0.f);
        out.push_back(body / std::max(1e-6f, body + noise));
    }
    return out;
}

static inline std::vector<float> bandSumTrajectory(const std::vector<std::vector<float> >& windows,
                                                   const std::vector<int>& indices) {
    std::vector<float> out;
    out.reserve(windows.size());
    for (size_t i = 0; i < windows.size(); i++) {
        float sum = 0.f;
        for (size_t j = 0; j < indices.size(); j++) {
            const int idx = indices[j];
            if (idx >= 0 && idx < (int)windows[i].size()) sum += windows[i][(size_t)idx];
        }
        out.push_back(sum);
    }
    return out;
}

static inline std::vector<float> prefixWeights(size_t n, size_t activeCount) {
    std::vector<float> out(n, 0.f);
    const size_t m = std::min(n, activeCount);
    for (size_t i = 0; i < m; i++) out[i] = 1.f;
    return out;
}

static inline std::vector<float> earlyWindowWeights(size_t n) {
    std::vector<float> out(n, 1.f);
    if (!n) return out;
    for (size_t i = 0; i < n; i++) {
        out[i] = 0.25f + 0.75f * std::exp(-3.f * float(i) / std::max<size_t>(1, n - 1));
    }
    return out;
}

static inline CompareResult compareAnalysis(const std::string& voice,
                                           const Analysis& ref,
                                           const Analysis& cand) {
    CompareResult out;
    const std::vector<int> bodyBands = {2, 3, 4};  // 160 Hz .. 1280 Hz
    const std::vector<float> bodyPitchWeights = earlyWindowWeights(
        std::min(ref.bodyPitchWindowsHz.size(), cand.bodyPitchWindowsHz.size()));
    const std::vector<float> upperBodyModeWeights = earlyWindowWeights(
        std::min(ref.upperBodyModeWindowsHz.size(), cand.upperBodyModeWindowsHz.size()));
    const std::vector<float> onsetWeights = prefixWeights(
        std::min(ref.centroidWindowsHz.size(), cand.centroidWindowsHz.size()), 6);
    const std::vector<int> rimClickBands = {3, 4, 5};  // 320 Hz .. 2560 Hz

    out.envelope = meanAbsDistance(ref.envelopeWindows, cand.envelopeWindows, 1.f);
    out.spectrum = meanAbsDistance(ref.fftBandEnergy, cand.fftBandEnergy, 1.f);
    out.bandTrajectory = meanSquaredDistance2D(ref.bandEnergyWindows, cand.bandEnergyWindows);
    out.bodyBand = meanSquaredDistance(selectBands(ref.fftBandEnergy, bodyBands),
                                       selectBands(cand.fftBandEnergy, bodyBands),
                                       1.f);
    out.bodyPitchTrajectory = weightedMeanSquaredDistance(
        ref.bodyPitchWindowsHz, cand.bodyPitchWindowsHz, bodyPitchWeights, 250.f);
    out.upperBodyModeTrajectory = weightedMeanSquaredDistance(
        ref.upperBodyModeWindowsHz, cand.upperBodyModeWindowsHz, upperBodyModeWeights, 250.f);
    out.bodyNoiseTrajectory = meanSquaredDistance(
        bodyNoiseRatioTrajectory(ref.bandEnergyWindows),
        bodyNoiseRatioTrajectory(cand.bandEnergyWindows),
        1.f);
    out.onsetClickTrajectory = weightedMeanSquaredDistance(
        bandSumTrajectory(ref.bandEnergyWindows, rimClickBands),
        bandSumTrajectory(cand.bandEnergyWindows, rimClickBands),
        onsetWeights,
        1.f);
    out.onsetCentroidTrajectory = weightedMeanSquaredDistance(
        ref.centroidWindowsHz,
        cand.centroidWindowsHz,
        onsetWeights,
        4000.f);

    const float durationDiff = std::fabs(ref.durationSeconds - cand.durationSeconds)
                             / std::max(0.05f, ref.durationSeconds);
    out.duration = clamp01(durationDiff * durationDiff);
    const float attackDiff = std::fabs(ref.attackSeconds - cand.attackSeconds) / 0.02f;
    out.attack = clamp01(attackDiff * attackDiff);

    if (voice == "rim") {
        out.total =
            out.spectrum * 0.18f +
            out.bandTrajectory * 0.08f +
            out.bodyBand * 0.12f +
            out.onsetClickTrajectory * 0.28f +
            out.onsetCentroidTrajectory * 0.18f +
            out.envelope * 0.08f +
            out.attack * 0.03f +
            out.duration * 0.05f;
    } else {
        out.total =
            out.envelope * 0.0079f +
            out.spectrum * 0.4216f +
            out.bandTrajectory * 0.0044f +
            out.bodyBand * 0.3942f +
            out.bodyPitchTrajectory * 0.0091f +
            out.upperBodyModeTrajectory * 0.0044f +
            out.bodyNoiseTrajectory * 0.0534f +
            out.attack * 0.0475f;
        out.total += out.duration * 0.0574f;
    }
    out.total = clamp01(out.total);
    return out;
}

static inline std::string analysisToJson(const Analysis& a) {
    std::ostringstream os;
    os << "{";
    os << "\"tool\":\"ar-analyze\",";
    os << "\"version\":1,";
    os << "\"source\":{";
    os << "\"path\":" << jsonQuote(a.sourcePath) << ",";
    os << "\"sample_rate\":" << a.sampleRate << ",";
    os << "\"frames\":" << a.originalFrames;
    os << "},";
    os << "\"trim\":{";
    os << "\"start_frame\":" << a.trimStartFrame << ",";
    os << "\"end_frame\":" << a.trimEndFrame;
    os << "},";
    os << "\"features\":{";
    os << "\"peak\":" << std::fixed << std::setprecision(6) << a.peak << ",";
    os << "\"rms\":" << a.rms << ",";
    os << "\"duration_s\":" << a.durationSeconds << ",";
    os << "\"attack_s\":" << a.attackSeconds << ",";
    os << "\"decay_t20_s\":" << a.decay20Seconds << ",";
    os << "\"decay_t40_s\":" << a.decay40Seconds << ",";
    os << "\"zero_crossing_rate\":" << a.zeroCrossingRate << ",";
    os << "\"spectral_centroid_mean_hz\":" << a.spectralCentroidMeanHz << ",";
    os << "\"fft_size\":" << a.fftSize << ",";
    os << "\"fft_band_edges_hz\":" << jsonArray(a.fftBandEdgesHz) << ",";
    os << "\"fft_band_energy\":" << jsonArray(a.fftBandEnergy) << ",";
    os << "\"envelope_windows\":" << jsonArray(a.envelopeWindows) << ",";
    os << "\"spectral_centroid_windows_hz\":" << jsonArray(a.centroidWindowsHz) << ",";
    os << "\"body_pitch_windows_hz\":" << jsonArray(a.bodyPitchWindowsHz) << ",";
    os << "\"upper_body_mode_windows_hz\":" << jsonArray(a.upperBodyModeWindowsHz) << ",";
    os << "\"fft_band_energy_windows\":" << jsonNestedArray(a.bandEnergyWindows);
    os << "}";
    os << "}";
    return os.str();
}

static inline std::string compareToJson(const std::string& voice,
                                        const std::map<std::string, float>& params,
                                        const std::string& referencePath,
                                        const CompareResult& cmp,
                                        const std::string& renderedWavPath) {
    std::ostringstream os;
    os << "{";
    os << "\"tool\":\"ar-compare\",";
    os << "\"version\":1,";
    os << "\"voice\":" << jsonQuote(voice) << ",";
    os << "\"reference\":" << jsonQuote(referencePath) << ",";
    os << "\"candidate\":{";
    os << "\"params\":{";
    bool first = true;
    for (std::map<std::string, float>::const_iterator it = params.begin(); it != params.end(); ++it) {
        if (!first) os << ",";
        first = false;
        os << jsonQuote(it->first) << ":" << std::fixed << std::setprecision(6) << it->second;
    }
    os << "}";
    os << "},";
    os << "\"score\":{";
    os << "\"total\":" << std::fixed << std::setprecision(6) << cmp.total << ",";
    os << "\"envelope\":" << cmp.envelope << ",";
    os << "\"spectrum\":" << cmp.spectrum << ",";
    os << "\"band_traj\":" << cmp.bandTrajectory << ",";
    os << "\"body_band\":" << cmp.bodyBand << ",";
    os << "\"body_pitch_traj\":" << cmp.bodyPitchTrajectory << ",";
    os << "\"upper_body_mode_traj\":" << cmp.upperBodyModeTrajectory << ",";
    os << "\"body_noise_traj\":" << cmp.bodyNoiseTrajectory << ",";
    os << "\"onset_click_traj\":" << cmp.onsetClickTrajectory << ",";
    os << "\"onset_centroid_traj\":" << cmp.onsetCentroidTrajectory << ",";
    os << "\"duration\":" << cmp.duration << ",";
    os << "\"attack\":" << cmp.attack;
    os << "},";
    os << "\"artifacts\":{";
    os << "\"rendered_wav\":" << jsonQuote(renderedWavPath);
    os << "}";
    os << "}";
    return os.str();
}

}  // namespace VoiceLab
