/**
 * Standalone C++ test for AgentRack::Signal::Audio.
 *
 * Does NOT link against Rack -- tests the shared audio-boundary contract directly.
 * Build: see tests/Makefile
 * Run:   ./test_signal_audio
 */

#include "../src/agentrack/signal/Audio.hpp"
#include <cmath>
#include <cstdio>

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

using AgentRack::Signal::Audio::ConstantPowerMix;
using AgentRack::Signal::Audio::fromRackVolts;
using AgentRack::Signal::Audio::toRackVolts;

static void test_boundary_conversions() {
    printf("\n[fromRackVolts / toRackVolts]\n");
    CHECK_NEAR(fromRackVolts(-5.f), -1.f, 1e-6f, "-5V maps to -1");
    CHECK_NEAR(fromRackVolts(0.f),   0.f, 1e-6f, "0V maps to 0");
    CHECK_NEAR(fromRackVolts(5.f),   1.f, 1e-6f, "+5V maps to +1");
    CHECK_NEAR(toRackVolts(-1.f),   -5.f, 1e-6f, "-1 maps to -5V");
    CHECK_NEAR(toRackVolts(0.f),     0.f, 1e-6f, "0 maps to 0V");
    CHECK_NEAR(toRackVolts(1.f),     5.f, 1e-6f, "+1 maps to +5V");
}

static void test_constant_power_mix() {
    printf("\n[ConstantPowerMix]\n");
    ConstantPowerMix dry(0.f);
    ConstantPowerMix center(0.5f);
    ConstantPowerMix wet(1.f);
    ConstantPowerMix clampedLow(-1.f);
    ConstantPowerMix clampedHigh(2.f);

    CHECK_NEAR(dry.dryGain(), 1.f, 1e-6f, "mix=0 keeps full dry gain");
    CHECK_NEAR(dry.wetGain(), 0.f, 1e-6f, "mix=0 zeros wet gain");
    CHECK_NEAR(wet.dryGain(), 0.f, 1e-6f, "mix=1 zeros dry gain");
    CHECK_NEAR(wet.wetGain(), 1.f, 1e-6f, "mix=1 keeps full wet gain");
    CHECK_NEAR(center.dryGain(), std::sqrt(0.5f), 1e-6f, "mix=0.5 uses constant-power dry gain");
    CHECK_NEAR(center.wetGain(), std::sqrt(0.5f), 1e-6f, "mix=0.5 uses constant-power wet gain");
    CHECK_NEAR(clampedLow.dryGain(), 1.f, 1e-6f, "mix clamps below 0");
    CHECK_NEAR(clampedHigh.wetGain(), 1.f, 1e-6f, "mix clamps above 1");
}

int main() {
    printf("=== AgentRack Signal.Audio test suite ===\n");

    test_boundary_conversions();
    test_constant_power_mix();

    printf("\n=== Results: %d passed, %d failed ===\n", passed, failed);
    return failed > 0 ? 1 : 0;
}
