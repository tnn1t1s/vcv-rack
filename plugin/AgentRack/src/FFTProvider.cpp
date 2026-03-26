#include "FFTProvider.hpp"
#include <cmath>
#include <cstring>
#include <memory>

// ---------------------------------------------------------------------------
// Fallback: in-place Cooley-Tukey radix-2 DIT FFT (all platforms)
// ---------------------------------------------------------------------------

static void fft_dit(float* re, float* im, int N, bool inverse) {
    // Bit-reversal permutation
    for (int i = 1, j = 0; i < N; i++) {
        int bit = N >> 1;
        for (; j & bit; bit >>= 1) j ^= bit;
        j ^= bit;
        if (i < j) { std::swap(re[i], re[j]); std::swap(im[i], im[j]); }
    }
    // Butterfly stages
    for (int len = 2; len <= N; len <<= 1) {
        float ang = 2.f * 3.14159265358979f / (float)len * (inverse ? -1.f : 1.f);
        float wr = std::cos(ang), wi = std::sin(ang);
        for (int i = 0; i < N; i += len) {
            float cr = 1.f, ci = 0.f;
            for (int j = 0; j < len / 2; j++) {
                float ur = re[i+j],         ui = im[i+j];
                float vr = re[i+j+len/2]*cr - im[i+j+len/2]*ci;
                float vi = re[i+j+len/2]*ci + im[i+j+len/2]*cr;
                re[i+j]         = ur + vr;  im[i+j]         = ui + vi;
                re[i+j+len/2]   = ur - vr;  im[i+j+len/2]   = ui - vi;
                float ncr = cr*wr - ci*wi;
                ci = cr*wi + ci*wr;  cr = ncr;
            }
        }
    }
    if (inverse) {
        for (int i = 0; i < N; i++) { re[i] /= N; im[i] /= N; }
    }
}

class FallbackFFTProvider : public FFTProvider {
    int N;
    float* re_scratch;
    float* im_scratch;

public:
    FallbackFFTProvider(int fft_size) : N(fft_size) {
        re_scratch = new float[N];
        im_scratch = new float[N];
    }
    ~FallbackFFTProvider() override {
        delete[] re_scratch;
        delete[] im_scratch;
    }
    int size() const override { return N; }

    void forward(float* buf) override {
        // Real input -> complex split
        for (int i = 0; i < N; i++) { re_scratch[i] = buf[i]; im_scratch[i] = 0.f; }
        fft_dit(re_scratch, im_scratch, N, false);
        // Pack into halfcomplex format
        buf[0] = re_scratch[0]; buf[1] = 0.f;
        buf[N] = re_scratch[N/2]; buf[N+1] = 0.f;
        for (int k = 1; k < N/2; k++) {
            buf[2*k]   = re_scratch[k];
            buf[2*k+1] = im_scratch[k];
        }
    }

    void inverse(float* buf) override {
        // Unpack halfcomplex -> complex split (use conjugate symmetry)
        re_scratch[0]   = buf[0];  im_scratch[0]   = 0.f;
        re_scratch[N/2] = buf[N];  im_scratch[N/2] = 0.f;
        for (int k = 1; k < N/2; k++) {
            re_scratch[k]     =  buf[2*k];
            im_scratch[k]     =  buf[2*k+1];
            re_scratch[N-k]   =  buf[2*k];
            im_scratch[N-k]   = -buf[2*k+1];
        }
        fft_dit(re_scratch, im_scratch, N, true);  // normalises by 1/N
        for (int i = 0; i < N; i++) buf[i] = re_scratch[i];
    }
};

// ---------------------------------------------------------------------------
// Factory
// ---------------------------------------------------------------------------

#ifdef __APPLE__
// Defined in FFTvDSP.cpp
std::unique_ptr<FFTProvider> createVDSPProvider(int fft_size);
#endif

std::unique_ptr<FFTProvider> FFTProvider::create(int fft_size) {
#ifdef __APPLE__
    return createVDSPProvider(fft_size);
#else
    return std::unique_ptr<FFTProvider>(new FallbackFFTProvider(fft_size));
#endif
}
