/**
 * Cross-cutting component contract checks for shared AgentRack types.
 *
 * These tests sit one level above the narrow per-type tests and assert the
 * contracts we expect future extracted components to follow.
 */

#include "../src/agentrack/signal/Audio.hpp"
#include "../src/agentrack/signal/CV.hpp"
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
using AgentRack::Signal::CV::Parameter;
using AgentRack::Signal::CV::toBipolarUnit;

static void test_audio_round_trip_contract() {
    printf("\n[audio boundary round-trip]\n");
    for (float sample : {-1.f, -0.5f, 0.f, 0.5f, 1.f}) {
        CHECK_NEAR(fromRackVolts(toRackVolts(sample)), sample, 1e-6f,
                   "audio boundary round-trip preserves normalized sample");
    }
}

static void test_constant_power_energy_contract() {
    printf("\n[constant-power energy contract]\n");
    for (float mix : {0.f, 0.25f, 0.5f, 0.75f, 1.f}) {
        ConstantPowerMix gains(mix);
        float power = gains.dryGain() * gains.dryGain()
                    + gains.wetGain() * gains.wetGain();
        CHECK_NEAR(power, 1.f, 1e-5f,
                   "dry^2 + wet^2 stays at unity power");
    }
}

static void test_cv_is_unclamped_before_parameter_application() {
    printf("\n[CV pre-clamp contract]\n");
    CHECK_NEAR(toBipolarUnit(15.f), 1.5f, 1e-6f,
               "raw CV conversion does not clamp above +10V");
    CHECK_NEAR(toBipolarUnit(-15.f), -1.5f, 1e-6f,
               "raw CV conversion does not clamp below -10V");
}

static void test_parameter_clamps_after_modulation() {
    printf("\n[parameter post-clamp contract]\n");
    Parameter parameter = {"contract", 0.2f, 0.f, 1.f};
    CHECK_NEAR(parameter.modulate(2.f, 10.f), 1.f, 1e-6f,
               "parameter clamps after applying scaled CV");
    CHECK_NEAR(parameter.modulate(2.f, -10.f), 0.f, 1e-6f,
               "parameter clamps after applying negative scaled CV");
}

int main() {
    printf("=== AgentRack shared component contract test suite ===\n");

    test_audio_round_trip_contract();
    test_constant_power_energy_contract();
    test_cv_is_unclamped_before_parameter_application();
    test_parameter_clamps_after_modulation();

    printf("\n=== Results: %d passed, %d failed ===\n", passed, failed);
    return failed > 0 ? 1 : 0;
}
