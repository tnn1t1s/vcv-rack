#ifdef __APPLE__
#include "FFTProvider.hpp"
#include <Accelerate/Accelerate.h>
#include <cmath>
#include <cstring>
#include <cassert>

/**
 * vDSP backend for FFTProvider.
 *
 * vDSP uses split-complex format internally (separate real/imag arrays).
 * We convert to/from the packed halfcomplex format expected by the interface
 * using scratch buffers allocated once at construction.
 */
class VDSPFFTProvider : public FFTProvider {
    int        N;
    int        log2N;
    FFTSetup   setup;
    // Scratch split-complex buffers (size N/2 each)
    float*     split_re;
    float*     split_im;

public:
    VDSPFFTProvider(int fft_size) : N(fft_size) {
        log2N   = (int)std::round(std::log2((float)N));
        setup   = vDSP_create_fftsetup(log2N, kFFTRadix2);
        split_re = new float[N / 2];
        split_im = new float[N / 2];
    }

    ~VDSPFFTProvider() override {
        vDSP_destroy_fftsetup(setup);
        delete[] split_re;
        delete[] split_im;
    }

    int size() const override { return N; }

    void forward(float* buf) override {
        // Pack real input into split-complex (interleave as pairs)
        DSPSplitComplex sc{ split_re, split_im };
        vDSP_ctoz((DSPComplex*)buf, 2, &sc, 1, N / 2);

        // Forward real FFT
        vDSP_fft_zrip(setup, &sc, 1, log2N, kFFTDirection_Forward);

        // vDSP packs DC in re[0], Nyquist in im[0].
        // Unpack to our halfcomplex format:
        //   buf[0]=Re[0], buf[1]=0, buf[2]=Re[1], buf[3]=Im[1], ..., buf[N]=Re[N/2], buf[N+1]=0
        buf[0]   = split_re[0];   // DC (real)
        buf[1]   = 0.f;
        buf[N]   = split_im[0];   // Nyquist (real, stored in im[0] by vDSP)
        buf[N+1] = 0.f;
        for (int k = 1; k < N / 2; k++) {
            buf[2*k]   = split_re[k];
            buf[2*k+1] = split_im[k];
        }

        // vDSP forward doesn't scale; scale by 2 is implicit in its convention.
        // We undo the factor-of-2 vDSP applies to real FFT:
        float scale = 0.5f;
        vDSP_vsmul(buf + 2, 1, &scale, buf + 2, 1, N - 2);
        buf[0] *= scale;
        buf[N] *= scale;
    }

    void inverse(float* buf) override {
        // Unpack halfcomplex -> vDSP split-complex
        split_re[0] = buf[0];    // DC
        split_im[0] = buf[N];    // Nyquist
        for (int k = 1; k < N / 2; k++) {
            split_re[k] = buf[2*k];
            split_im[k] = buf[2*k+1];
        }

        DSPSplitComplex sc{ split_re, split_im };
        vDSP_fft_zrip(setup, &sc, 1, log2N, kFFTDirection_Inverse);

        // Unpack split-complex -> real interleaved
        vDSP_ztoc(&sc, 1, (DSPComplex*)buf, 2, N / 2);

        // Normalise by 1/N (vDSP inverse is unnormalised)
        float scale = 1.f / (float)N;
        vDSP_vsmul(buf, 1, &scale, buf, 1, N);
    }
};

// Registration hook called by FFTProvider::create()
std::unique_ptr<FFTProvider> createVDSPProvider(int fft_size) {
    return std::unique_ptr<FFTProvider>(new VDSPFFTProvider(fft_size));
}

#endif // __APPLE__
