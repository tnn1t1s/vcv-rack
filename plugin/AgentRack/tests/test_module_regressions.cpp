/**
 * Thin module-level regression harness for deterministic AgentRack modules.
 *
 * This sits above shared-component tests. It should only cover stable,
 * important module behaviors and invariants.
 */

#include "ModuleHarness.hpp"
#include <cmath>
#include <cstdio>

rack::Plugin* pluginInstance = nullptr;

#include "../src/Attenuate.cpp"
#include "../src/ADSR.cpp"
#include "../src/ClockDiv.cpp"
#include "../src/Noise.cpp"
#include "../src/Crinkle.cpp"
#include "../src/Ladder.cpp"
#include "../src/Sonic.cpp"
#include "../src/Maurizio.cpp"
#include "../src/Tonnetz.cpp"

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

static void test_attenuate_rows_are_independent() {
    printf("\n[Attenuate row independence]\n");
    Attenuate module;

    module.inputs[Attenuate::IN_0].setVoltage(4.f);
    module.params[Attenuate::SCALE_0].setValue(0.5f);

    module.inputs[Attenuate::IN_1].setVoltage(-3.f);
    module.params[Attenuate::SCALE_1].setValue(0.25f);

    module.inputs[Attenuate::IN_2].setVoltage(7.f);
    module.params[Attenuate::SCALE_2].setValue(0.f);

    ModuleHarness::step(module, 1);

    CHECK_NEAR(module.outputs[Attenuate::OUT_0].getVoltage(), 2.f, 1e-6f,
               "row 0 output equals input times scale");
    CHECK_NEAR(module.outputs[Attenuate::OUT_1].getVoltage(), -0.75f, 1e-6f,
               "row 1 output is independent");
    CHECK_NEAR(module.outputs[Attenuate::OUT_2].getVoltage(), 0.f, 1e-6f,
               "zero scale mutes row without affecting others");
}

static void test_clockdiv_divides_and_resets() {
    printf("\n[ClockDiv divide and reset]\n");
    ClockDiv module;

    ModuleHarness::connectInput(module, ClockDiv::CLOCK_INPUT, 0.f);
    ModuleHarness::connectInput(module, ClockDiv::RESET_INPUT, 0.f);

    ModuleHarness::trigger(module, ClockDiv::CLOCK_INPUT);
    CHECK_NEAR(module.outputs[ClockDiv::DIV2_OUTPUT].getVoltage(), 0.f, 1e-6f,
               "first clock keeps /2 low");

    ModuleHarness::trigger(module, ClockDiv::CLOCK_INPUT);
    CHECK_NEAR(module.outputs[ClockDiv::DIV2_OUTPUT].getVoltage(), 10.f, 1e-6f,
               "second clock raises /2");

    ModuleHarness::trigger(module, ClockDiv::CLOCK_INPUT);
    ModuleHarness::trigger(module, ClockDiv::CLOCK_INPUT);
    CHECK_NEAR(module.outputs[ClockDiv::DIV4_OUTPUT].getVoltage(), 10.f, 1e-6f,
               "fourth clock raises /4");

    ModuleHarness::trigger(module, ClockDiv::RESET_INPUT);
    ModuleHarness::trigger(module, ClockDiv::CLOCK_INPUT);
    CHECK_NEAR(module.outputs[ClockDiv::DIV2_OUTPUT].getVoltage(), 0.f, 1e-6f,
               "reset restarts divider phase");
}

static void test_adsr_reaches_sustain_and_releases() {
    printf("\n[ADSR sustain and release]\n");
    ADSR module;

    module.params[ADSR::ATTACK_PARAM].setValue(0.01f);
    module.params[ADSR::DECAY_PARAM].setValue(0.02f);
    module.params[ADSR::SUSTAIN_PARAM].setValue(0.4f);
    module.params[ADSR::RELEASE_PARAM].setValue(0.03f);

    module.inputs[ADSR::GATE_INPUT].setVoltage(10.f);
    ModuleHarness::step(module, 40, 1000.f);

    CHECK_NEAR(module.outputs[ADSR::ENV_OUTPUT].getVoltage(), 4.f, 0.2f,
               "held gate settles near sustain level");

    module.inputs[ADSR::GATE_INPUT].setVoltage(0.f);
    ModuleHarness::step(module, 40, 1000.f);

    CHECK_NEAR(module.outputs[ADSR::ENV_OUTPUT].getVoltage(), 0.f, 0.1f,
               "release returns envelope to zero");
}

static void test_adsr_short_trigger_completes_attack_decay_cycle() {
    printf("\n[ADSR short trigger completes A/D cycle]\n");
    ADSR module;

    module.params[ADSR::ATTACK_PARAM].setValue(0.01f);
    module.params[ADSR::DECAY_PARAM].setValue(0.02f);
    module.params[ADSR::SUSTAIN_PARAM].setValue(0.2f);
    module.params[ADSR::RELEASE_PARAM].setValue(0.03f);

    float peak = 0.f;

    module.inputs[ADSR::GATE_INPUT].setVoltage(10.f);
    ModuleHarness::step(module, 1, 1000.f);
    peak = std::max(peak, module.outputs[ADSR::ENV_OUTPUT].getVoltage());

    module.inputs[ADSR::GATE_INPUT].setVoltage(0.f);
    for (int i = 0; i < 80; i++) {
        ModuleHarness::step(module, 1, 1000.f);
        peak = std::max(peak, module.outputs[ADSR::ENV_OUTPUT].getVoltage());
    }

    CHECK(peak > 8.f, "short trigger still drives envelope close to full attack peak");
    CHECK_NEAR(module.outputs[ADSR::ENV_OUTPUT].getVoltage(), 0.f, 0.1f,
               "envelope eventually releases to zero after short trigger");
}

static void test_adsr_sustain_cv_modulates_target_level() {
    printf("\n[ADSR sustain CV modulation]\n");
    ADSR module;

    module.params[ADSR::ATTACK_PARAM].setValue(0.01f);
    module.params[ADSR::DECAY_PARAM].setValue(0.02f);
    module.params[ADSR::SUSTAIN_PARAM].setValue(0.2f);
    module.params[ADSR::SUSTAIN_CV_PARAM].setValue(0.5f);
    module.params[ADSR::RELEASE_PARAM].setValue(0.03f);
    module.inputs[ADSR::SUSTAIN_INPUT].setVoltage(10.f);

    module.inputs[ADSR::GATE_INPUT].setVoltage(10.f);
    ModuleHarness::step(module, 50, 1000.f);

    CHECK_NEAR(module.outputs[ADSR::ENV_OUTPUT].getVoltage(), 7.f, 0.2f,
               "sustain CV depth shifts sustain target in parameter space");
}

static void test_ladder_silence_is_stable() {
    printf("\n[Ladder silence stability]\n");
    Ladder module;

    module.params[Ladder::FREQ_PARAM].setValue(0.5f);
    module.params[Ladder::RES_PARAM].setValue(0.2f);
    module.inputs[Ladder::IN_INPUT].setVoltage(0.f);

    float maxAbsOutput = 0.f;
    for (int i = 0; i < 512; i++) {
        ModuleHarness::step(module, 1);
        maxAbsOutput = std::max(maxAbsOutput,
                                std::fabs(module.outputs[Ladder::OUT_OUTPUT].getVoltage()));
    }

    CHECK(maxAbsOutput < 1e-3f, "zero input remains near silent");
}

static void test_ladder_constant_input_stays_finite() {
    printf("\n[Ladder bounded response]\n");
    Ladder module;

    module.params[Ladder::FREQ_PARAM].setValue(0.8f);
    module.params[Ladder::RES_PARAM].setValue(0.1f);
    module.inputs[Ladder::IN_INPUT].setVoltage(5.f);

    bool finite = true;
    float maxAbsOutput = 0.f;
    for (int i = 0; i < 2048; i++) {
        ModuleHarness::step(module, 1);
        float out = module.outputs[Ladder::OUT_OUTPUT].getVoltage();
        finite = finite && std::isfinite(out);
        maxAbsOutput = std::max(maxAbsOutput, std::fabs(out));
    }

    CHECK(finite, "constant input response remains finite");
    CHECK(maxAbsOutput < 10.f, "constant input response stays bounded");
}

static void test_noise_outputs_are_finite_and_bounded() {
    printf("\n[Noise bounded random outputs]\n");
    Noise module;
    rack::random::local().seed(1234, 5678);

    bool finite = true;
    bool crackleQuantized = true;
    float maxAbs = 0.f;

    for (int i = 0; i < 2048; i++) {
        ModuleHarness::step(module, 1);
        for (int outputId = 0; outputId < Noise::NUM_OUTPUTS; outputId++) {
            float out = module.outputs[outputId].getVoltage();
            finite = finite && std::isfinite(out);
            maxAbs = std::max(maxAbs, std::fabs(out));
        }
        float crackle = module.outputs[Noise::CRACKLE_OUTPUT].getVoltage();
        crackleQuantized = crackleQuantized
                        && (crackle == -5.f || crackle == 0.f || crackle == 5.f);
    }

    CHECK(finite, "all noise outputs remain finite");
    CHECK(maxAbs < 15.f, "noise outputs stay in a sane bounded range");
    CHECK(crackleQuantized, "crackle output stays quantized to {-5, 0, +5}V");
}

static void test_crinkle_output_is_bounded_and_nonconstant() {
    printf("\n[Crinkle bounded oscillator output]\n");
    Crinkle module;

    module.params[Crinkle::TUNE_PARAM].setValue(0.f);
    module.params[Crinkle::TIMBRE_PARAM].setValue(0.3f);
    module.params[Crinkle::SYMMETRY_PARAM].setValue(0.1f);

    bool finite = true;
    float maxAbs = 0.f;
    float minOut = 1e9f;
    float maxOut = -1e9f;

    for (int i = 0; i < 2048; i++) {
        ModuleHarness::step(module, 1);
        float out = module.outputs[Crinkle::OUT_OUTPUT].getVoltage();
        finite = finite && std::isfinite(out);
        maxAbs = std::max(maxAbs, std::fabs(out));
        minOut = std::min(minOut, out);
        maxOut = std::max(maxOut, out);
    }

    CHECK(finite, "Crinkle output remains finite");
    CHECK(maxAbs <= 5.1f, "Crinkle output stays near the expected +/-5V boundary");
    CHECK((maxOut - minOut) > 1.f, "Crinkle output changes over time");
}

static void test_crinkle_polyphony_tracks_independent_channels() {
    printf("\n[Crinkle polyphony regression]\n");
    Crinkle module;

    module.params[Crinkle::TUNE_PARAM].setValue(0.f);
    module.params[Crinkle::TIMBRE_PARAM].setValue(0.25f);
    module.params[Crinkle::SYMMETRY_PARAM].setValue(0.05f);

    ModuleHarness::connectPolyInput(module, Crinkle::VOCT_INPUT, {-1.f, 0.f, 1.f});
    ModuleHarness::connectOutput(module, Crinkle::OUT_OUTPUT);

    for (int i = 0; i < 4096; i++) {
        ModuleHarness::step(module, 1);
    }

    CHECK(module.outputs[Crinkle::OUT_OUTPUT].getChannels() == 3,
          "Crinkle output becomes polyphonic when fed poly pitch");

    float out0 = module.outputs[Crinkle::OUT_OUTPUT].getVoltage(0);
    float out1 = module.outputs[Crinkle::OUT_OUTPUT].getVoltage(1);
    float out2 = module.outputs[Crinkle::OUT_OUTPUT].getVoltage(2);

    CHECK(std::fabs(out0 - out1) > 1e-3f,
          "Crinkle poly channels do not collapse to identical output (0 vs 1)");
    CHECK(std::fabs(out1 - out2) > 1e-3f,
          "Crinkle poly channels do not collapse to identical output (1 vs 2)");
}

static void test_sonic_zero_input_stays_silent() {
    printf("\n[Sonic silence regression]\n");
    Sonic module;
    module.params[Sonic::AMOUNT_PARAM].setValue(0.8f);
    module.params[Sonic::COLOR_PARAM].setValue(0.7f);
    module.params[Sonic::LOW_CONTOUR_PARAM].setValue(0.6f);
    module.params[Sonic::PROCESS_PARAM].setValue(0.5f);
    ModuleHarness::connectInput(module, Sonic::IN_INPUT, 0.f);

    float maxAbsOutput = 0.f;
    for (int i = 0; i < 1024; i++) {
        ModuleHarness::step(module, 1);
        maxAbsOutput = std::max(maxAbsOutput,
                                std::fabs(module.outputs[Sonic::OUT_OUTPUT].getVoltage()));
    }

    CHECK(maxAbsOutput < 1e-3f, "zero input remains silent through Sonic");
}

static void test_maurizio_dry_mix_is_identity() {
    printf("\n[Maurizio dry mix identity]\n");
    Maurizio module;
    module.params[Maurizio::MIX_PARAM].setValue(0.f);
    module.params[Maurizio::FEEDBACK_PARAM].setValue(0.f);
    ModuleHarness::connectInput(module, Maurizio::IN_L_INPUT, 2.f);
    ModuleHarness::disconnectInput(module, Maurizio::IN_R_INPUT);

    ModuleHarness::step(module, 1);

    CHECK_NEAR(module.outputs[Maurizio::OUT_L_OUTPUT].getVoltage(), 2.f, 1e-6f,
               "left output equals dry input when mix=0");
    CHECK_NEAR(module.outputs[Maurizio::OUT_R_OUTPUT].getVoltage(), 2.f, 1e-6f,
               "right output defaults to mono left input when right is disconnected");
}

static void test_tonnetz_trigger_selects_triangle() {
    printf("\n[Tonnetz trigger selection]\n");
    Tonnetz module;
    ModuleHarness::connectInput(module, Tonnetz::CV1_INPUT, 0.f);
    ModuleHarness::trigger(module, Tonnetz::TRIG_INPUT);

    CHECK(module.numSelected == 1, "one connected CV selects one triangle");
    CHECK(module.selectedTriangles[0] == 0, "0V selects triangle 0");
    CHECK(module.numVoices >= 3, "single triangle produces a chord");
}

int main() {
    printf("=== AgentRack module regression test suite ===\n");

    test_attenuate_rows_are_independent();
    test_clockdiv_divides_and_resets();
    test_adsr_reaches_sustain_and_releases();
    test_adsr_short_trigger_completes_attack_decay_cycle();
    test_adsr_sustain_cv_modulates_target_level();
    test_ladder_silence_is_stable();
    test_ladder_constant_input_stays_finite();
    test_noise_outputs_are_finite_and_bounded();
    test_crinkle_output_is_bounded_and_nonconstant();
    test_crinkle_polyphony_tracks_independent_channels();
    test_sonic_zero_input_stays_silent();
    test_maurizio_dry_mix_is_identity();
    test_tonnetz_trigger_selects_triangle();

    printf("\n=== Results: %d passed, %d failed ===\n", passed, failed);
    return failed > 0 ? 1 : 0;
}
