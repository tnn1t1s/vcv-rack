/**
 * Standalone C++ test for AgentRack::Infrastructure::PartitionedConvolution.
 *
 * Uses the real FFT provider but does not link against Rack.
 * Build: see tests/Makefile
 * Run:   ./test_partitioned_convolution
 */

#include "../src/agentrack/infrastructure/PartitionedConvolution.hpp"
#include "../src/FFTProvider.cpp"
#include "../src/FFTvDSP.cpp"
#include <cmath>
#include <cstdio>
#include <vector>

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

using AgentRack::Infrastructure::PartitionedConvolution;

static void test_zero_ir_is_silent() {
    printf("\n[zero IR is silent]\n");
    PartitionedConvolution conv;
    conv.init();

    float zero = 0.f;
    conv.load(&zero, &zero, 1);

    bool leftSilent = true;
    bool rightSilent = true;
    for (int i = 0; i < PartitionedConvolution::kBlockSize * 2; i++) {
        float outL = 1.f, outR = 1.f;
        conv.push((i == 0) ? 1.f : 0.f, (i == 0) ? 1.f : 0.f, outL, outR);
        leftSilent = leftSilent && std::fabs(outL) <= 1e-5f;
        rightSilent = rightSilent && std::fabs(outR) <= 1e-5f;
    }
    CHECK(leftSilent, "left output stays silent with zero IR");
    CHECK(rightSilent, "right output stays silent with zero IR");
}

static void test_delta_ir_reproduces_input_after_block_latency() {
    printf("\n[delta IR reproduces input after block latency]\n");
    PartitionedConvolution conv;
    conv.init();

    float delta = 1.f;
    conv.load(&delta, &delta, 1);

    std::vector<float> input(PartitionedConvolution::kBlockSize * 3, 0.f);
    input[0] = 0.75f;

    std::vector<float> output;
    output.reserve(input.size());

    bool stereoSymmetric = true;
    for (float sample : input) {
        float outL = 0.f, outR = 0.f;
        conv.push(sample, sample, outL, outR);
        output.push_back(outL);
        stereoSymmetric = stereoSymmetric && std::fabs(outL - outR) <= 1e-6f;
    }

    CHECK(stereoSymmetric, "stereo delta IR stays symmetric");
    CHECK_NEAR(output[0], 0.f, 1e-5f, "output starts at zero before block is processed");
    CHECK_NEAR(output[PartitionedConvolution::kBlockSize], input[0], 1e-3f,
               "delta IR reproduces impulse after one block of latency");
}

int main() {
    printf("=== AgentRack PartitionedConvolution test suite ===\n");

    test_zero_ir_is_silent();
    test_delta_ir_reproduces_input_after_block_latency();

    printf("\n=== Results: %d passed, %d failed ===\n", passed, failed);
    return failed > 0 ? 1 : 0;
}
