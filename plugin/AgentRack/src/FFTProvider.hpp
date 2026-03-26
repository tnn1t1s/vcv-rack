#pragma once
#include <memory>

/**
 * FFTProvider -- abstract real FFT interface.
 *
 * Spectrum format (N+2 floats, "packed halfcomplex"):
 *   [Re[0], 0, Re[1], Im[1], Re[2], Im[2], ..., Re[N/2-1], Im[N/2-1], Re[N/2], 0]
 *
 * Casting buf to std::complex<float>* gives N/2+1 bins -- use directly for
 * pointwise multiply-accumulate in the convolution engine.
 *
 * Adding a new backend: subclass FFTProvider, register in FFTProvider.cpp factory.
 */
class FFTProvider {
public:
    virtual ~FFTProvider() = default;

    virtual int size() const = 0;   // FFT size N this instance was built for

    // Forward real FFT, in-place.
    // On entry:  buf[0..N-1] = real signal,  buf[N..N+1] = 0 (scratch)
    // On exit:   buf[0..N+1] = packed halfcomplex spectrum
    virtual void forward(float* buf) = 0;

    // Inverse real FFT, in-place, normalised by 1/N.
    // On entry:  buf[0..N+1] = packed halfcomplex spectrum
    // On exit:   buf[0..N-1] = real signal,  buf[N..N+1] = garbage
    virtual void inverse(float* buf) = 0;

    // Factory: returns best available backend for the current platform.
    static std::unique_ptr<FFTProvider> create(int fft_size);
};
