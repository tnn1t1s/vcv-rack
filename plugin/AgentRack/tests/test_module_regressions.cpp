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
#include "../src/Ladder.cpp"

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

int main() {
    printf("=== AgentRack module regression test suite ===\n");

    test_attenuate_rows_are_independent();
    test_adsr_reaches_sustain_and_releases();
    test_adsr_short_trigger_completes_attack_decay_cycle();
    test_adsr_sustain_cv_modulates_target_level();
    test_ladder_silence_is_stable();
    test_ladder_constant_input_stays_finite();

    printf("\n=== Results: %d passed, %d failed ===\n", passed, failed);
    return failed > 0 ? 1 : 0;
}
