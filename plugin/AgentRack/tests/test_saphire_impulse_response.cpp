#include "../src/agentrack/infrastructure/SaphireImpulseResponse.hpp"
#include <cmath>
#include <cstdio>
#include <vector>

using SaphireImpulseResponse = AgentRack::Infrastructure::SaphireImpulseResponse;

static int passed = 0;
static int failed = 0;

#define CHECK(cond, msg) do { \
    if (cond) { std::printf("  PASS  %s\n", msg); passed++; } \
    else { std::printf("  FAIL  %s\n", msg); failed++; } \
} while (0)

#define CHECK_NEAR(a, b, tol, msg) do { \
    float _diff = std::fabs((float)(a) - (float)(b)); \
    if (_diff <= (tol)) { std::printf("  PASS  %s  (diff=%.2e)\n", msg, (double)_diff); passed++; } \
    else { std::printf("  FAIL  %s  (|%.6f - %.6f| = %.2e > %.2e)\n", msg, (double)(a), (double)(b), (double)_diff, (double)(tol)); failed++; } \
} while (0)

static std::vector<float> buildRamp(int size, float scale) {
    std::vector<float> values(size);
    for (int i = 0; i < size; ++i) {
        values[i] = scale * static_cast<float>(i) / static_cast<float>(size - 1);
    }
    return values;
}

static void test_time_parameter_scales_kernel_length() {
    std::printf("\n[kernel length scaling]\n");
    SaphireImpulseResponse response;
    response.setRaw(buildRamp(1024, 1.f), buildRamp(1024, 0.5f));

    auto shortest = response.buildKernel(0.f, 0.f);
    auto longest = response.buildKernel(1.f, 0.f);

    CHECK((int)shortest.first.size() == SaphireImpulseResponse::kBlockSize,
          "time=0 keeps one convolution block");
    CHECK((int)longest.first.size() == 1024,
          "time=1 keeps the full IR length");
}

static void test_zero_bend_preserves_endpoints() {
    std::printf("\n[identity bend]\n");
    SaphireImpulseResponse response;
    response.setRaw(buildRamp(1024, 1.f), buildRamp(1024, 0.25f));

    auto kernel = response.buildKernel(1.f, 0.f);

    CHECK_NEAR(kernel.first.front(), 0.f, 1e-6f, "identity bend preserves left start sample");
    CHECK_NEAR(kernel.first.back(), 1.f, 1e-4f, "identity bend preserves left end sample");
    CHECK_NEAR(kernel.second.back(), 0.25f, 1e-4f, "identity bend preserves right end sample");
}

static void test_negative_and_positive_bend_move_midpoint_in_opposite_directions() {
    std::printf("\n[bend warps midpoint]\n");
    SaphireImpulseResponse response;
    response.setRaw(buildRamp(1024, 1.f), buildRamp(1024, 1.f));

    auto compressed = response.buildKernel(1.f, -1.f);
    auto identity = response.buildKernel(1.f, 0.f);
    auto smeared = response.buildKernel(1.f, 1.f);

    const int midpoint = 512;
    CHECK(compressed.first[midpoint] > identity.first[midpoint],
          "negative bend pulls more energy forward");
    CHECK(smeared.first[midpoint] < identity.first[midpoint],
          "positive bend smears energy into the tail");
}

int main() {
    std::printf("=== AgentRack SaphireImpulseResponse test suite ===\n");

    test_time_parameter_scales_kernel_length();
    test_zero_bend_preserves_endpoints();
    test_negative_and_positive_bend_move_midpoint_in_opposite_directions();

    std::printf("\n=== Results: %d passed, %d failed ===\n", passed, failed);
    return failed ? 1 : 0;
}
