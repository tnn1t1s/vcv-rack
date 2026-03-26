/**
 * Standalone C++ test for FFTProvider.
 *
 * Does NOT link against Rack -- tests pure DSP math.
 * Build: see tests/Makefile
 * Run:   ./test_fft
 */

#include "../src/FFTProvider.hpp"
#include <cmath>
#include <cstdio>
#include <cstring>
#include <complex>
#include <cassert>

static int passed = 0;
static int failed = 0;

#define CHECK(cond, msg) do { \
    if (cond) { printf("  PASS  %s\n", msg); passed++; } \
    else       { printf("  FAIL  %s\n", msg); failed++; } \
} while(0)

#define CHECK_NEAR(a, b, tol, msg) do { \
    float _diff = std::fabs((float)(a) - (float)(b)); \
    if (_diff <= (tol)) { printf("  PASS  %s  (diff=%.2e)\n", msg, (double)_diff); passed++; } \
    else                { printf("  FAIL  %s  (|%.6f - %.6f| = %.2e > %.2e)\n", msg, (double)(a), (double)(b), (double)_diff, (double)(tol)); failed++; } \
} while(0)


// ---------------------------------------------------------------------------
// Helpers
// ---------------------------------------------------------------------------

static void fill_sine(float* buf, int N, float freq_norm) {
    for (int i = 0; i < N; i++)
        buf[i] = std::sin(2.f * 3.14159265f * freq_norm * (float)i);
}

static float rms(const float* buf, int N) {
    float sum = 0.f;
    for (int i = 0; i < N; i++) sum += buf[i] * buf[i];
    return std::sqrt(sum / (float)N);
}

// Pointwise multiply-accumulate of packed halfcomplex spectra
static void spec_mac(const float* a, const float* b, float* acc, int N) {
    using C = std::complex<float>;
    int bins = N / 2 + 1;
    const C* ca = (const C*)a;
    const C* cb = (const C*)b;
    C* cacc = (C*)acc;
    for (int k = 0; k < bins; k++)
        cacc[k] += ca[k] * cb[k];
}


// ---------------------------------------------------------------------------
// Tests
// ---------------------------------------------------------------------------

static void test_round_trip(FFTProvider& fft) {
    printf("\n[round-trip]\n");
    int N = fft.size();

    // Random-ish signal
    float orig[N + 2], buf[N + 2];
    memset(orig, 0, sizeof(orig));
    for (int i = 0; i < N; i++)
        orig[i] = std::sin(0.1f * i) * 0.5f + std::cos(0.07f * i) * 0.3f;
    memcpy(buf, orig, sizeof(orig));

    fft.forward(buf);

    // DC and Nyquist imaginary parts must be 0
    CHECK(std::fabs(buf[1]) < 1e-5f,   "DC imaginary == 0");
    CHECK(std::fabs(buf[N+1]) < 1e-5f, "Nyquist imaginary == 0");

    fft.inverse(buf);

    float max_err = 0.f;
    for (int i = 0; i < N; i++)
        max_err = std::max(max_err, std::fabs(buf[i] - orig[i]));
    CHECK_NEAR(max_err, 0.f, 1e-4f, "forward+inverse recovers original (max error)");
}

static void test_impulse_spectrum(FFTProvider& fft) {
    printf("\n[impulse spectrum]\n");
    int N = fft.size();

    float buf[N + 2];
    memset(buf, 0, sizeof(buf));
    buf[0] = 1.f;   // Dirac delta at n=0

    fft.forward(buf);

    // Spectrum of delta[n] is all-ones (flat magnitude)
    float max_dev = 0.f;
    int bins = N / 2 + 1;
    using C = std::complex<float>;
    const C* spec = (const C*)buf;
    for (int k = 0; k < bins; k++)
        max_dev = std::max(max_dev, std::fabs(std::abs(spec[k]) - 1.f));
    CHECK_NEAR(max_dev, 0.f, 1e-4f, "Dirac delta has flat unit spectrum");
}

static void test_convolution_identity(FFTProvider& fft) {
    printf("\n[convolution identity -- delta IR]\n");
    int N = fft.size();
    int B = N / 2;

    // IR = delta[0]: convolving with this should return the input
    float h_buf[N + 2];
    memset(h_buf, 0, sizeof(h_buf));
    h_buf[0] = 1.f;
    fft.forward(h_buf);

    // Input block: arbitrary signal in second half (first half = overlap zeros)
    float x[N + 2];
    memset(x, 0, sizeof(x));
    for (int i = 0; i < B; i++)
        x[B + i] = std::sin(0.3f * i) + 0.5f * std::cos(0.1f * i);

    fft.forward(x);

    // acc = X * H
    float acc[N + 2];
    memset(acc, 0, sizeof(acc));
    spec_mac(x, h_buf, acc, N);

    // IFFT -> take second half (overlap-save result)
    fft.inverse(acc);

    float max_err = 0.f;
    for (int i = 0; i < B; i++) {
        float expected = std::sin(0.3f * i) + 0.5f * std::cos(0.1f * i);
        max_err = std::max(max_err, std::fabs(acc[B + i] - expected));
    }
    CHECK_NEAR(max_err, 0.f, 1e-3f, "overlap-save with delta IR returns input");
}

static void test_linearity(FFTProvider& fft) {
    printf("\n[linearity: FFT(a+b) == FFT(a) + FFT(b)]\n");
    int N = fft.size();

    float a[N + 2], b[N + 2], ab[N + 2];
    memset(a, 0, sizeof(a)); memset(b, 0, sizeof(b)); memset(ab, 0, sizeof(ab));

    fill_sine(a, N, 0.1f);
    fill_sine(b, N, 0.3f);
    for (int i = 0; i < N; i++) ab[i] = a[i] + b[i];

    fft.forward(a);
    fft.forward(b);
    fft.forward(ab);

    float max_err = 0.f;
    for (int i = 0; i < N + 2; i++)
        max_err = std::max(max_err, std::fabs(ab[i] - (a[i] + b[i])));
    CHECK_NEAR(max_err, 0.f, 1e-4f, "FFT(a+b) == FFT(a) + FFT(b)");
}

static void test_parseval(FFTProvider& fft) {
    printf("\n[Parseval's theorem: energy in time == energy in frequency]\n");
    int N = fft.size();

    float buf[N + 2];
    memset(buf, 0, sizeof(buf));
    fill_sine(buf, N, 0.13f);

    float energy_time = 0.f;
    for (int i = 0; i < N; i++) energy_time += buf[i] * buf[i];

    fft.forward(buf);

    // For real FFT: E = |X[0]|^2 + 2*sum|X[k]|^2 (k=1..N/2-1) + |X[N/2]|^2, all / N
    using C = std::complex<float>;
    const C* spec = (const C*)buf;
    int bins = N / 2 + 1;
    float energy_freq = std::norm(spec[0]) + std::norm(spec[N/2]);
    for (int k = 1; k < bins - 1; k++)
        energy_freq += 2.f * std::norm(spec[k]);
    energy_freq /= (float)N;

    CHECK_NEAR(energy_freq, energy_time, energy_time * 0.001f, "Parseval's theorem holds");
}


static void test_buffer_boundary(FFTProvider& fft) {
    printf("\n[buffer boundary -- forward must not write beyond N+1]\n");
    int N = fft.size();
    // Allocate exactly N+2 floats with a sentinel after
    std::vector<float> buf(N + 4, 0.f);
    buf[N + 2] = 1234.5f;  // sentinel
    buf[N + 3] = 6789.0f;  // sentinel
    for (int i = 0; i < N; i++) buf[i] = std::sin(0.1f * i);

    fft.forward(buf.data());

    CHECK(buf[N + 2] == 1234.5f, "forward() did not write beyond buf[N+1]");
    CHECK(buf[N + 3] == 6789.0f, "forward() did not write beyond buf[N+1] (guard 2)");
}


// ---------------------------------------------------------------------------
// main
// ---------------------------------------------------------------------------

int main() {
    printf("=== FFTProvider test suite ===\n");

    for (int fft_size : {256, 512, 1024}) {
        printf("\n--- FFT size %d ---\n", fft_size);
        auto fft = FFTProvider::create(fft_size);
        test_round_trip(*fft);
        test_impulse_spectrum(*fft);
        test_convolution_identity(*fft);
        test_linearity(*fft);
        test_parseval(*fft);
        test_buffer_boundary(*fft);
    }

    printf("\n=== Results: %d passed, %d failed ===\n", passed, failed);
    return failed > 0 ? 1 : 0;
}
