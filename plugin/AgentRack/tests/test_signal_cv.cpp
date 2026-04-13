/**
 * Standalone C++ test for AgentRack::Signal::CV.
 *
 * Does NOT link against Rack -- tests the shared CV-domain contract directly.
 * Build: see tests/Makefile
 * Run:   ./test_signal_cv
 */

#include "../src/agentrack/signal/CV.hpp"
#include <cmath>
#include <cstdio>
#include <string>

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

using AgentRack::Signal::CV::Parameter;
using AgentRack::Signal::CV::toBipolarUnit;

static void test_to_bipolar_unit() {
    printf("\n[toBipolarUnit]\n");
    CHECK_NEAR(toBipolarUnit(-10.f), -1.f, 1e-6f, "-10V maps to -1");
    CHECK_NEAR(toBipolarUnit(0.f),    0.f, 1e-6f, "0V maps to 0");
    CHECK_NEAR(toBipolarUnit(5.f),    0.5f, 1e-6f, "+5V maps to +0.5");
    CHECK_NEAR(toBipolarUnit(10.f),   1.f, 1e-6f, "+10V maps to +1");
}

static void test_parameter_modulate_core_law() {
    printf("\n[Parameter::modulate core law]\n");
    Parameter p = {"test", 0.5f, 0.f, 1.f};
    CHECK(std::string(p.name()) == "test", "parameter preserves semantic name");
    CHECK_NEAR(p.modulate(1.f, 10.f), 1.f,   1e-6f, "positive full-scale CV adds +1 unit then clamps");
    CHECK_NEAR(p.modulate(1.f, -10.f), 0.f,  1e-6f, "negative full-scale CV subtracts 1 unit then clamps");
    CHECK_NEAR(p.modulate(0.5f, 10.f), 1.f,  1e-6f, "depth scales contribution before clamp");
    CHECK_NEAR(p.modulate(-1.f, 10.f), 0.f,  1e-6f, "negative depth inverts CV polarity");
    CHECK_NEAR(p.modulate(0.f, 10.f), 0.5f,  1e-6f, "zero depth disables modulation");
}

static void test_parameter_modulate_unclamped_interior() {
    printf("\n[Parameter::modulate interior]\n");
    Parameter p1 = {"p1", 0.25f, 0.f, 1.f};
    Parameter p2 = {"p2", 0.75f, 0.f, 1.f};
    CHECK_NEAR(p1.modulate(0.5f, 2.f), 0.35f, 1e-6f,
               "base + depth * (cv/10) applies in parameter space");
    CHECK_NEAR(p2.modulate(0.25f, -4.f), 0.65f, 1e-6f,
               "negative CV reduces the parameter before clamp");
}

int main() {
    printf("=== AgentRack Signal.CV test suite ===\n");

    test_to_bipolar_unit();
    test_parameter_modulate_core_law();
    test_parameter_modulate_unclamped_interior();

    printf("\n=== Results: %d passed, %d failed ===\n", passed, failed);
    return failed > 0 ? 1 : 0;
}
