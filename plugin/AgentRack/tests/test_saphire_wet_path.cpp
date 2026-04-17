#include "../src/agentrack/signal/SaphireWetPath.hpp"
#include <cmath>
#include <cstdio>

using SaphireWetPath = AgentRack::Signal::SaphireWetPath;

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

static void test_predelay_delays_by_requested_samples() {
    std::printf("\n[pre-delay]\n");
    SaphireWetPath wetPath;
    float oneSampleDelay = 1.f / static_cast<float>(SaphireWetPath::kMaxPreDelaySamples - 1);

    auto first = wetPath.applyPreDelay(1.f, -1.f, oneSampleDelay);
    auto second = wetPath.applyPreDelay(0.f, 0.f, oneSampleDelay);

    CHECK_NEAR(first.left, 0.f, 1e-6f, "one-sample pre-delay starts silent on left");
    CHECK_NEAR(first.right, 0.f, 1e-6f, "one-sample pre-delay starts silent on right");
    CHECK_NEAR(second.left, 1.f, 1e-6f, "delayed left sample appears one step later");
    CHECK_NEAR(second.right, -1.f, 1e-6f, "delayed right sample appears one step later");
}

static void test_tone_smoothing_is_stateful() {
    std::printf("\n[tone smoothing]\n");
    SaphireWetPath wetPath;
    auto first = wetPath.applyTone(1.f, -1.f, 0.f, 44100.f);
    auto second = wetPath.applyTone(1.f, -1.f, 0.f, 44100.f);

    CHECK(first.left > 0.f && first.left < 1.f, "tone filter smooths toward wet left sample");
    CHECK(first.right < 0.f && first.right > -1.f, "tone filter smooths toward wet right sample");
    CHECK(second.left > first.left, "tone filter retains state on repeated left input");
    CHECK(second.right < first.right, "tone filter retains state on repeated right input");
}

static void test_mix_obeys_constant_power_endpoints() {
    std::printf("\n[constant-power mix]\n");
    SaphireWetPath wetPath;
    auto dry = wetPath.mix(0.5f, -0.5f, 1.f, 1.f, 0.f);
    auto wet = wetPath.mix(0.5f, -0.5f, 1.f, 1.f, 1.f);

    CHECK_NEAR(dry.left, 0.5f, 1e-6f, "mix=0 keeps left dry input");
    CHECK_NEAR(dry.right, -0.5f, 1e-6f, "mix=0 keeps right dry input");
    CHECK_NEAR(wet.left, 1.f, 1e-6f, "mix=1 keeps left wet input");
    CHECK_NEAR(wet.right, 1.f, 1e-6f, "mix=1 keeps right wet input");
}

int main() {
    std::printf("=== AgentRack SaphireWetPath test suite ===\n");

    test_predelay_delays_by_requested_samples();
    test_tone_smoothing_is_stateful();
    test_mix_obeys_constant_power_endpoints();

    std::printf("\n=== Results: %d passed, %d failed ===\n", passed, failed);
    return failed ? 1 : 0;
}
