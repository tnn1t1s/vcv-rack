#include "../src/agentrack/signal/AttenuateCore.hpp"
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

using namespace AgentRack::Signal::Attenuate;

static void test_patched_input_acts_as_attenuator() {
    printf("\n[patched row law]\n");
    CHECK_NEAR(rowOutput(true, 4.f, 0.5f, MODE_UNIPOLAR_10), 2.f, 1e-6f,
               "patched row scales input voltage");
    CHECK_NEAR(rowOutput(true, -3.f, 0.25f, MODE_VOCT_2OCT), -0.75f, 1e-6f,
               "patched row ignores macro mode");
}

static void test_unpatched_row_uses_selected_macro_range() {
    printf("\n[unpatched macro law]\n");
    CHECK_NEAR(rowOutput(false, 99.f, 0.25f, MODE_UNIPOLAR_10), 2.5f, 1e-6f,
               "unpatched unipolar row emits 0..10V");
    CHECK_NEAR(rowOutput(false, 99.f, 0.25f, MODE_BIPOLAR_5), -2.5f, 1e-6f,
               "unpatched bipolar row emits +/-5V");
    CHECK_NEAR(rowOutput(false, 99.f, 1.0f, MODE_VOCT_1OCT), 1.f, 1e-6f,
               "unpatched 1-oct row emits +/-1V range");
    CHECK_NEAR(rowOutput(false, 99.f, 1.0f, MODE_VOCT_2OCT), 2.f, 1e-6f,
               "unpatched 2-oct row emits +/-2V range");
}

static void test_mode_parsing_is_stable() {
    printf("\n[mode parsing]\n");
    CHECK(modeFromKey("unipolar_10") == MODE_UNIPOLAR_10,
          "unipolar key parses");
    CHECK(modeFromKey("voct_2oct") == MODE_VOCT_2OCT,
          "voct_2oct key parses");
    CHECK(modeFromKey("unknown") == MODE_UNIPOLAR_10,
          "unknown key falls back to unipolar");
    CHECK(normalizeMode(-1) == MODE_UNIPOLAR_10,
          "negative mode normalizes");
    CHECK(normalizeMode(99) == MODE_UNIPOLAR_10,
          "out-of-range mode normalizes");
}

int main() {
    printf("=== AgentRack Attenuate core test suite ===\n");

    test_patched_input_acts_as_attenuator();
    test_unpatched_row_uses_selected_macro_range();
    test_mode_parsing_is_stable();

    printf("\n=== Results: %d passed, %d failed ===\n", passed, failed);
    return failed > 0 ? 1 : 0;
}
