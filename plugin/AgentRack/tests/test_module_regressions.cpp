/**
 * Thin module-level regression harness for deterministic AgentRack modules.
 *
 * This sits above shared-component tests. It should only cover stable,
 * important module behaviors and invariants.
 */

#include "ModuleHarness.hpp"
#include <array>
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
#include "../src/Kck.cpp"
#include "../src/Snr.cpp"
#include "../src/Tr909Ctrl.cpp"
#include "../src/Toms.cpp"
#include "../src/Chh.cpp"
#include "../src/Ohh.cpp"
#include "../src/RimClap.cpp"
#include "../src/CrashRide.cpp"

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

    ModuleHarness::connectInput(module, Attenuate::IN_0, 4.f);
    module.params[Attenuate::SCALE_0].setValue(0.5f);

    ModuleHarness::connectInput(module, Attenuate::IN_1, -3.f);
    module.params[Attenuate::SCALE_1].setValue(0.25f);

    ModuleHarness::connectInput(module, Attenuate::IN_2, 7.f);
    module.params[Attenuate::SCALE_2].setValue(0.f);

    ModuleHarness::connectOutput(module, Attenuate::OUT_0);
    ModuleHarness::connectOutput(module, Attenuate::OUT_1);
    ModuleHarness::connectOutput(module, Attenuate::OUT_2);

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

static std::array<float, 4096> render_snr_hit(float tone, float snappy) {
    Snr module;
    module.params[Snr::TONE_PARAM].setValue(tone);
    module.params[Snr::SNAPPY_PARAM].setValue(snappy);
    module.params[Snr::TUNE_PARAM].setValue(0.50f);
    module.params[Snr::LEVEL_PARAM].setValue(1.f);

    std::array<float, 4096> out {};
    auto args = ModuleHarness::makeArgs();

    ModuleHarness::connectInput(module, Snr::TRIG_INPUT, 0.f);
    module.process(args);
    ModuleHarness::connectInput(module, Snr::TRIG_INPUT, 10.f);
    module.process(args);
    ModuleHarness::connectInput(module, Snr::TRIG_INPUT, 0.f);

    for (size_t i = 0; i < out.size(); i++) {
        module.process(args);
        out[i] = AgentRack::Signal::Audio::fromRackVolts(
            module.outputs[Snr::OUT_OUTPUT].getVoltage());
    }
    return out;
}

static std::array<float, 4096> render_chh_hit(float tune, float decay) {
    Chh module;
    module.params[Chh::TUNE_PARAM].setValue(tune);
    module.params[Chh::DECAY_PARAM].setValue(decay);
    module.params[Chh::BPF_PARAM].setValue(0.58f);
    module.params[Chh::HPF_PARAM].setValue(0.52f);
    module.params[Chh::Q_PARAM].setValue(0.30f);
    module.params[Chh::DRIVE_PARAM].setValue(0.f);
    module.params[Chh::LEVEL_PARAM].setValue(1.f);

    std::array<float, 4096> out {};
    auto args = ModuleHarness::makeArgs();

    ModuleHarness::connectInput(module, Chh::TRIG_INPUT, 0.f);
    module.process(args);
    ModuleHarness::connectInput(module, Chh::TRIG_INPUT, 10.f);
    module.process(args);
    ModuleHarness::connectInput(module, Chh::TRIG_INPUT, 0.f);

    for (size_t i = 0; i < out.size(); i++) {
        module.process(args);
        out[i] = AgentRack::Signal::Audio::fromRackVolts(
            module.outputs[Chh::OUT_OUTPUT].getVoltage());
    }
    return out;
}

static std::array<float, 4096> render_rimclap_clap_hit() {
    RimClap module;
    module.params[RimClap::CLAP_LEVEL_PARAM].setValue(1.f);
    module.params[RimClap::RIM_LEVEL_PARAM].setValue(0.f);

    std::array<float, 4096> out {};
    auto args = ModuleHarness::makeArgs();

    ModuleHarness::connectInput(module, RimClap::CLAP_TRIG_INPUT, 0.f);
    module.process(args);
    ModuleHarness::connectInput(module, RimClap::CLAP_TRIG_INPUT, 10.f);
    module.process(args);
    ModuleHarness::connectInput(module, RimClap::CLAP_TRIG_INPUT, 0.f);

    for (size_t i = 0; i < out.size(); i++) {
        module.process(args);
        out[i] = AgentRack::Signal::Audio::fromRackVolts(
            module.outputs[RimClap::CLAP_OUT_OUTPUT].getVoltage());
    }
    return out;
}

static std::array<float, 4096> render_rimclap_rim_hit() {
    RimClap module;
    module.params[RimClap::CLAP_LEVEL_PARAM].setValue(0.f);
    module.params[RimClap::RIM_LEVEL_PARAM].setValue(1.f);

    std::array<float, 4096> out {};
    auto args = ModuleHarness::makeArgs();

    ModuleHarness::connectInput(module, RimClap::RIM_TRIG_INPUT, 0.f);
    module.process(args);
    ModuleHarness::connectInput(module, RimClap::RIM_TRIG_INPUT, 10.f);
    module.process(args);
    ModuleHarness::connectInput(module, RimClap::RIM_TRIG_INPUT, 0.f);

    for (size_t i = 0; i < out.size(); i++) {
        module.process(args);
        out[i] = AgentRack::Signal::Audio::fromRackVolts(
            module.outputs[RimClap::RIM_OUT_OUTPUT].getVoltage());
    }
    return out;
}

static std::array<float, 4096> render_kck_hit() {
    Kck module;
    module.params[Kck::TUNE_PARAM].setValue(0.35f);
    module.params[Kck::DECAY_PARAM].setValue(0.55f);
    module.params[Kck::PITCH_PARAM].setValue(0.40f);
    module.params[Kck::PITCH_DECAY_PARAM].setValue(0.30f);
    module.params[Kck::CLICK_PARAM].setValue(0.35f);
    module.params[Kck::DRIVE_PARAM].setValue(0.20f);
    module.params[Kck::LEVEL_PARAM].setValue(1.f);

    std::array<float, 4096> out {};
    auto args = ModuleHarness::makeArgs();
    ModuleHarness::connectInput(module, Kck::TRIG_INPUT, 0.f);
    module.process(args);
    ModuleHarness::connectInput(module, Kck::TRIG_INPUT, 10.f);
    module.process(args);
    ModuleHarness::connectInput(module, Kck::TRIG_INPUT, 0.f);

    for (size_t i = 0; i < out.size(); i++) {
        module.process(args);
        out[i] = AgentRack::Signal::Audio::fromRackVolts(
            module.outputs[Kck::OUT_OUTPUT].getVoltage());
    }
    return out;
}

// Render a kick hit with controlled local-accent voltage at TRIG and after.
// gateAtTrig: voltage on LOCAL_ACC_INPUT at the rising-edge frame
//             (>1V latches accent for the hit).
// gateAfter:  voltage to drive on LOCAL_ACC_INPUT for the rest of the hit
//             (no effect once latched, used to verify sample-at-trig).
static std::array<float, 4096> render_kck_with_accent(float gateAtTrig, float gateAfter) {
    Kck module;
    module.params[Kck::TUNE_PARAM].setValue(0.35f);
    module.params[Kck::DECAY_PARAM].setValue(0.55f);
    module.params[Kck::PITCH_PARAM].setValue(0.40f);
    module.params[Kck::PITCH_DECAY_PARAM].setValue(0.30f);
    module.params[Kck::CLICK_PARAM].setValue(0.35f);
    module.params[Kck::DRIVE_PARAM].setValue(0.20f);
    module.params[Kck::LEVEL_PARAM].setValue(1.f);

    std::array<float, 4096> out {};
    auto args = ModuleHarness::makeArgs();
    ModuleHarness::connectInput(module, Kck::LOCAL_ACC_INPUT, gateAtTrig);
    ModuleHarness::connectInput(module, Kck::TRIG_INPUT, 0.f);
    module.process(args);
    ModuleHarness::connectInput(module, Kck::TRIG_INPUT, 10.f);
    module.process(args);                // <-- accent latched here
    ModuleHarness::connectInput(module, Kck::TRIG_INPUT, 0.f);
    ModuleHarness::connectInput(module, Kck::LOCAL_ACC_INPUT, gateAfter);

    for (size_t i = 0; i < out.size(); i++) {
        module.process(args);
        out[i] = AgentRack::Signal::Audio::fromRackVolts(
            module.outputs[Kck::OUT_OUTPUT].getVoltage());
    }
    return out;
}

template <typename TTom>
static std::array<float, 4096> render_tom_hit(float tune, float decay) {
    TTom module;
    module.params[TTom::TUNE_PARAM].setValue(tune);
    module.params[TTom::DECAY_PARAM].setValue(decay);
    module.params[TTom::LEVEL_PARAM].setValue(1.f);

    std::array<float, 4096> out {};
    auto args = ModuleHarness::makeArgs();
    ModuleHarness::connectInput(module, TTom::TRIG_INPUT, 0.f);
    module.process(args);
    ModuleHarness::connectInput(module, TTom::TRIG_INPUT, 10.f);
    module.process(args);
    ModuleHarness::connectInput(module, TTom::TRIG_INPUT, 0.f);

    for (size_t i = 0; i < out.size(); i++) {
        module.process(args);
        out[i] = AgentRack::Signal::Audio::fromRackVolts(
            module.outputs[TTom::OUT_OUTPUT].getVoltage());
    }
    return out;
}

static std::array<float, 4096> render_ohh_hit(float tune, float decay) {
    Ohh module;
    module.params[Ohh::TUNE_PARAM].setValue(tune);
    module.params[Ohh::DECAY_PARAM].setValue(decay);
    module.params[Ohh::BPF_PARAM].setValue(0.55f);
    module.params[Ohh::HPF_PARAM].setValue(0.40f);
    module.params[Ohh::Q_PARAM].setValue(0.25f);
    module.params[Ohh::DRIVE_PARAM].setValue(0.f);
    module.params[Ohh::LEVEL_PARAM].setValue(1.f);

    std::array<float, 4096> out {};
    auto args = ModuleHarness::makeArgs();
    ModuleHarness::connectInput(module, Ohh::TRIG_INPUT, 0.f);
    module.process(args);
    ModuleHarness::connectInput(module, Ohh::TRIG_INPUT, 10.f);
    module.process(args);
    ModuleHarness::connectInput(module, Ohh::TRIG_INPUT, 0.f);

    for (size_t i = 0; i < out.size(); i++) {
        module.process(args);
        out[i] = AgentRack::Signal::Audio::fromRackVolts(
            module.outputs[Ohh::OUT_OUTPUT].getVoltage());
    }
    return out;
}

static float sum_abs_diff(const std::array<float, 4096>& signal, int start, int count) {
    float total = 0.f;
    for (int i = start + 1; i < start + count; i++) {
        total += std::fabs(signal[i] - signal[i - 1]);
    }
    return total;
}

static float sum_abs(const std::array<float, 4096>& signal, int start, int count) {
    float total = 0.f;
    for (int i = start; i < start + count; i++) {
        total += std::fabs(signal[i]);
    }
    return total;
}

static int decay_frames(const std::array<float, 4096>& signal, float threshold) {
    int peakIndex = 0;
    float peakValue = 0.f;
    for (int i = 0; i < 4096; i++) {
        float v = std::fabs(signal[i]);
        if (v > peakValue) {
            peakValue = v;
            peakIndex = i;
        }
    }
    for (int i = peakIndex; i < 4096; i++) {
        if (std::fabs(signal[i]) <= threshold) {
            return i - peakIndex;
        }
    }
    return 4095 - peakIndex;
}

static int zero_crossings(const std::array<float, 4096>& signal, int start, int count) {
    int total = 0;
    for (int i = start + 1; i < start + count; i++) {
        bool signA = signal[i - 1] >= 0.f;
        bool signB = signal[i] >= 0.f;
        if (signA != signB) total++;
    }
    return total;
}

static float sum_abs_8192(const std::array<float, 8192>& signal, int start, int count) {
    float total = 0.f;
    for (int i = start; i < start + count; i++) {
        total += std::fabs(signal[i]);
    }
    return total;
}

static int zero_crossings_8192(const std::array<float, 8192>& signal, int start, int count) {
    int total = 0;
    for (int i = start + 1; i < start + count; i++) {
        bool signA = signal[i - 1] >= 0.f;
        bool signB = signal[i] >= 0.f;
        if (signA != signB) total++;
    }
    return total;
}

static void test_snr_noise_controls_shape_the_hit() {
    printf("\n[Snr 909 voicing regression]\n");
    rack::random::local().seed(1234, 5678);
    auto lowSnap = render_snr_hit(0.45f, 0.10f);
    rack::random::local().seed(1234, 5678);
    auto highSnap = render_snr_hit(0.45f, 1.f);
    rack::random::local().seed(1234, 5678);
    auto shortTone = render_snr_hit(0.f, 0.55f);
    rack::random::local().seed(1234, 5678);
    auto longTone = render_snr_hit(1.f, 0.55f);

    float maxAbs = 0.f;
    for (float sample : highSnap) {
        maxAbs = std::max(maxAbs, std::fabs(sample));
    }

    float lowSnapEdge = sum_abs_diff(lowSnap, 64, 768);
    float highSnapEdge = sum_abs_diff(highSnap, 64, 768);
    int shortDecay = decay_frames(shortTone, 0.01f);
    int longDecay = decay_frames(longTone, 0.01f);

    CHECK(maxAbs < 2.6f, "snare output remains in a sane bounded range");
    CHECK(highSnapEdge > lowSnapEdge * 1.20f,
          "higher snappy increases noisy high-frequency edge");
    CHECK(longDecay > shortDecay + 8,
          "higher tone extends the snare-noise tail");
}

static void test_chh_sample_voice_controls_shape_the_hit() {
    printf("\n[Chh sampled hat regression]\n");
    auto shortHat = render_chh_hit(0.50f, 0.f);
    auto longHat = render_chh_hit(0.50f, 1.f);
    auto lowHat = render_chh_hit(0.f, 0.35f);
    auto highHat = render_chh_hit(1.f, 0.35f);

    float maxAbs = 0.f;
    for (float sample : highHat) {
        maxAbs = std::max(maxAbs, std::fabs(sample));
    }

    float shortTail = sum_abs(shortHat, 1200, 800);
    float longTail = sum_abs(longHat, 1200, 800);
    int lowCross = zero_crossings(lowHat, 64, 320);
    int highCross = zero_crossings(highHat, 64, 320);

    CHECK(maxAbs < 2.0f, "hat output remains bounded");
    CHECK(longTail > shortTail * 1.8f, "higher decay extends the sampled hat tail");
    CHECK(highCross > lowCross, "higher tune raises early-cycle hat brightness/pitch");
}

static void test_crashride_voices_produce_audio() {
    printf("\n[CrashRide voice regression]\n");
    CrashRide module;
    auto args = ModuleHarness::makeArgs();

    // Crash trigger
    ModuleHarness::connectInput(module, CrashRide::CRASH_TRIG_INPUT, 0.f);
    module.process(args);
    ModuleHarness::connectInput(module, CrashRide::CRASH_TRIG_INPUT, 10.f);
    module.process(args);
    ModuleHarness::connectInput(module, CrashRide::CRASH_TRIG_INPUT, 0.f);

    // Ride trigger (separate)
    ModuleHarness::connectInput(module, CrashRide::RIDE_TRIG_INPUT, 10.f);
    module.process(args);
    ModuleHarness::connectInput(module, CrashRide::RIDE_TRIG_INPUT, 0.f);

    float crashPeak = 0.f, crashEnergy = 0.f;
    float ridePeak  = 0.f, rideEnergy  = 0.f;
    for (int i = 0; i < 4096; i++) {
        module.process(args);
        float c = AgentRack::Signal::Audio::fromRackVolts(module.outputs[CrashRide::CRASH_OUT_OUTPUT].getVoltage());
        float r = AgentRack::Signal::Audio::fromRackVolts(module.outputs[CrashRide::RIDE_OUT_OUTPUT].getVoltage());
        crashPeak   = std::max(crashPeak, std::fabs(c));
        ridePeak    = std::max(ridePeak,  std::fabs(r));
        crashEnergy += std::fabs(c);
        rideEnergy  += std::fabs(r);
    }

    CHECK(crashPeak < 2.0f && ridePeak < 2.0f, "CrashRide outputs remain bounded");
    CHECK(crashEnergy > 1.f, "Crash trigger produces audio on its output");
    CHECK(rideEnergy  > 1.f, "Ride trigger produces audio on its output");
}

static void test_rimclap_voices_produce_audio() {
    printf("\n[RimClap voice regression]\n");
    auto clap = render_rimclap_clap_hit();
    auto rim  = render_rimclap_rim_hit();

    float clapPeak = 0.f, clapEnergy = 0.f;
    for (float s : clap) { clapPeak = std::max(clapPeak, std::fabs(s)); clapEnergy += std::fabs(s); }
    float rimPeak = 0.f, rimEnergy = 0.f;
    for (float s : rim)  { rimPeak  = std::max(rimPeak,  std::fabs(s)); rimEnergy  += std::fabs(s); }

    CHECK(clapPeak < 2.0f && rimPeak < 2.0f, "RimClap outputs remain bounded");
    CHECK(clapEnergy > 1.f, "Clap trigger produces audio");
    CHECK(rimEnergy  > 1.f, "Rim trigger produces audio");
}

static void test_ohh_sample_voice_controls_shape_the_hit() {
    printf("\n[Ohh sampled hat regression]\n");
    auto shortHat = render_ohh_hit(0.50f, 0.f);
    auto longHat = render_ohh_hit(0.50f, 1.f);
    auto lowHat = render_ohh_hit(0.f, 0.55f);
    auto highHat = render_ohh_hit(1.f, 0.55f);

    float maxAbs = 0.f;
    for (float sample : highHat) {
        maxAbs = std::max(maxAbs, std::fabs(sample));
    }

    float shortTail = sum_abs(shortHat, 1800, 1400);
    float longTail = sum_abs(longHat, 1800, 1400);
    int lowCross = zero_crossings(lowHat, 96, 384);
    int highCross = zero_crossings(highHat, 96, 384);

    CHECK(maxAbs < 2.2f, "open hat output remains bounded");
    CHECK(longTail > shortTail * 1.4f, "higher decay extends the open-hat tail");
    CHECK(highCross > lowCross, "higher tune raises early-cycle open-hat brightness");
}

static void test_kck_trigger_produces_decaying_body() {
    printf("\n[Kck regression]\n");
    auto hit = render_kck_hit();

    float peak = 0.f;
    int peakIndex = 0;
    for (int i = 0; i < (int)hit.size(); i++) {
        float v = std::fabs(hit[i]);
        if (v > peak) { peak = v; peakIndex = i; }
    }
    float earlyEnergy = sum_abs(hit, 100, 400);

    CHECK(peak < 2.5f,         "Kck output remains bounded");
    CHECK(earlyEnergy > 1.f,   "Kck trigger produces an audible body");
    CHECK(peakIndex < 800,     "Kck peak occurs in the attack region (<18 ms)");
}

static float peak_abs(const std::array<float, 4096>& a) {
    float p = 0.f;
    for (float v : a) p = std::max(p, std::fabs(v));
    return p;
}

static void test_kck_local_accent_low_is_base_level() {
    printf("\n[Kck local accent: base level]\n");
    auto base = render_kck_with_accent(0.f, 0.f);
    float peak = peak_abs(base);
    CHECK(peak > 0.05f, "Kck fires at audible base level when ACC is low");
    CHECK(peak < 2.0f,  "Kck base output remains bounded");
}

static void test_kck_local_accent_high_boosts_amplitude() {
    printf("\n[Kck local accent: high boosts amplitude]\n");
    auto base     = render_kck_with_accent(0.f,  0.f);
    auto accented = render_kck_with_accent(10.f, 10.f);
    float peakBase     = peak_abs(base);
    float peakAccented = peak_abs(accented);
    CHECK(peakAccented > peakBase * 1.05f,
          "ACC=10V at TRIG increases output peak by >5% over base");
    CHECK(peakAccented < 2.5f, "Accented Kck output remains bounded");
}

static void test_kck_local_accent_sample_at_trig_invariance() {
    printf("\n[Kck local accent: sample-at-trig invariance]\n");
    // ACC was LOW at the trig moment; flipping it HIGH afterward must NOT
    // boost the hit. This proves the design's sample-at-trig latch.
    auto base       = render_kck_with_accent(0.f, 0.f);
    auto flippedHi  = render_kck_with_accent(0.f, 10.f);
    float peakBase     = peak_abs(base);
    float peakFlipped  = peak_abs(flippedHi);
    float ratio = peakFlipped / std::max(peakBase, 1e-6f);
    CHECK(ratio > 0.99f && ratio < 1.01f,
          "ACC toggled AFTER trig leaves output unchanged (sample-at-trig)");
}

// Render a kick hit driven by TOTAL_ACC_INPUT instead of LOCAL_ACC.
// Local jack stays at 0V; total jack is high at TRIG.
static std::array<float, 4096> render_kck_with_total_accent(float gateAtTrig) {
    Kck module;
    module.params[Kck::TUNE_PARAM].setValue(0.35f);
    module.params[Kck::DECAY_PARAM].setValue(0.55f);
    module.params[Kck::PITCH_PARAM].setValue(0.40f);
    module.params[Kck::PITCH_DECAY_PARAM].setValue(0.30f);
    module.params[Kck::CLICK_PARAM].setValue(0.35f);
    module.params[Kck::DRIVE_PARAM].setValue(0.20f);
    module.params[Kck::LEVEL_PARAM].setValue(1.f);

    std::array<float, 4096> out {};
    auto args = ModuleHarness::makeArgs();
    ModuleHarness::connectInput(module, Kck::TOTAL_ACC_INPUT, gateAtTrig);
    ModuleHarness::connectInput(module, Kck::TRIG_INPUT, 0.f);
    module.process(args);
    ModuleHarness::connectInput(module, Kck::TRIG_INPUT, 10.f);
    module.process(args);
    ModuleHarness::connectInput(module, Kck::TRIG_INPUT, 0.f);

    for (size_t i = 0; i < out.size(); i++) {
        module.process(args);
        out[i] = AgentRack::Signal::Audio::fromRackVolts(
            module.outputs[Kck::OUT_OUTPUT].getVoltage());
    }
    return out;
}

static void test_kck_total_accent_boosts_amplitude() {
    printf("\n[Kck total accent: high boosts amplitude]\n");
    auto base     = render_kck_with_total_accent(0.f);
    auto accented = render_kck_with_total_accent(10.f);
    float peakBase     = peak_abs(base);
    float peakAccented = peak_abs(accented);
    CHECK(peakAccented > peakBase * 1.05f,
          "TOTAL_ACC=10V at TRIG increases output peak (proves Accent A path)");
    CHECK(peakAccented < 2.5f, "Total-accented Kck output remains bounded");
}

// Render a kick hit with Tr909Ctrl wired as the left expander, exposing
// configurable accentAmount and masterVolume on the bus. Trigger fires at
// frame 1; kick processes after Tr909Ctrl in each frame so resolveBus()
// sees the controller's current state.
static std::array<float, 4096> render_kck_with_ctrl(float accentAmtKnob,
                                                    float masterVolKnob,
                                                    float totalAccGate) {
    Tr909Ctrl ctrl;
    ctrl.params[Tr909Ctrl::ACCENT_AMT_PARAM].setValue(accentAmtKnob);
    ctrl.params[Tr909Ctrl::MASTER_VOL_PARAM].setValue(masterVolKnob);

    Kck kck;
    kck.params[Kck::TUNE_PARAM].setValue(0.35f);
    kck.params[Kck::DECAY_PARAM].setValue(0.55f);
    kck.params[Kck::PITCH_PARAM].setValue(0.40f);
    kck.params[Kck::PITCH_DECAY_PARAM].setValue(0.30f);
    kck.params[Kck::CLICK_PARAM].setValue(0.35f);
    kck.params[Kck::DRIVE_PARAM].setValue(0.20f);
    kck.params[Kck::LEVEL_PARAM].setValue(1.f);

    // Wire ctrl as kck's left expander.
    kck.leftExpander.module  = &ctrl;
    ctrl.rightExpander.module = &kck;

    std::array<float, 4096> out {};
    auto args = ModuleHarness::makeArgs();
    ModuleHarness::connectInput(kck, Kck::TOTAL_ACC_INPUT, totalAccGate);
    ModuleHarness::connectInput(kck, Kck::TRIG_INPUT, 0.f);
    ctrl.process(args);  // ctrl writes to its currentBus first
    kck.process(args);   // kck reads neighbor->currentBus
    ModuleHarness::connectInput(kck, Kck::TRIG_INPUT, 10.f);
    ctrl.process(args);
    kck.process(args);   // <-- TRIG rising edge here, accent latched
    ModuleHarness::connectInput(kck, Kck::TRIG_INPUT, 0.f);

    for (size_t i = 0; i < out.size(); i++) {
        ctrl.process(args);
        kck.process(args);
        out[i] = AgentRack::Signal::Audio::fromRackVolts(
            kck.outputs[Kck::OUT_OUTPUT].getVoltage());
    }
    return out;
}

static void test_tr909ctrl_accent_amount_scales_accent() {
    printf("\n[Tr909Ctrl bus: accentAmount scales accent]\n");
    // TOTAL_ACC gate high in both runs; only the controller knob differs.
    // accentAmount=0 should produce the same audio as no-accent (gate
    // is high but amount=0 zeroes the latched strength).
    auto amt0  = render_kck_with_ctrl(0.f, 1.f, 10.f);
    auto amt1  = render_kck_with_ctrl(1.f, 1.f, 10.f);
    auto noAcc = render_kck_with_total_accent(0.f);  // baseline, no ctrl
    float peakAmt0  = peak_abs(amt0);
    float peakAmt1  = peak_abs(amt1);
    float peakNoAcc = peak_abs(noAcc);
    CHECK(peakAmt1 > peakAmt0 * 1.05f,
          "ctrl ACCENT_AMT=1.0 louder than ACCENT_AMT=0.0 (bus reaches voice)");
    // amt=0 with TOTAL_ACC high should be near-equal to no accent at all.
    float ratio = peakAmt0 / std::max(peakNoAcc, 1e-6f);
    CHECK(ratio > 0.95f && ratio < 1.05f,
          "ACCENT_AMT=0 collapses to base level even with TOTAL_ACC high");
}

static void test_tr909ctrl_master_volume_scales_output() {
    printf("\n[Tr909Ctrl bus: masterVolume scales output]\n");
    auto vol100 = render_kck_with_ctrl(1.f, 1.0f, 0.f);
    auto vol050 = render_kck_with_ctrl(1.f, 0.5f, 0.f);
    auto vol000 = render_kck_with_ctrl(1.f, 0.0f, 0.f);
    float p100 = peak_abs(vol100);
    float p050 = peak_abs(vol050);
    float p000 = peak_abs(vol000);
    CHECK(p050 > 0.4f * p100 && p050 < 0.6f * p100,
          "MASTER_VOL=0.5 yields ~half peak vs MASTER_VOL=1.0");
    CHECK(p000 < p100 * 0.05f,
          "MASTER_VOL=0.0 silences the voice");
}

static void test_accent_mix_resolves_three_cases_independently() {
    printf("\n[AccentMix: three cases tunable independently]\n");
    using namespace AgentRack::TR909;

    // Custom mix: A-only weak, B-only medium, both strong.
    AccentMix mix;
    mix.weightTotal = 0.25f;
    mix.weightLocal = 0.50f;
    mix.weightBoth  = 1.00f;

    float onlyA   = resolveAccentStrength(true,  false, 1.f, mix);
    float onlyB   = resolveAccentStrength(false, true,  1.f, mix);
    float both    = resolveAccentStrength(true,  true,  1.f, mix);
    float neither = resolveAccentStrength(false, false, 1.f, mix);

    CHECK(std::fabs(onlyA   - 0.25f) < 1e-6f, "A-only uses weightTotal");
    CHECK(std::fabs(onlyB   - 0.50f) < 1e-6f, "B-only uses weightLocal");
    CHECK(std::fabs(both    - 1.00f) < 1e-6f, "Both uses weightBoth (independent of A/B)");
    CHECK(std::fabs(neither - 0.00f) < 1e-6f, "Neither returns 0");

    // weightBoth can be smaller than max(A,B) -- the "both" case is
    // truly independent, NOT clamped to be at least max.
    AccentMix dipped;
    dipped.weightTotal = 0.80f;
    dipped.weightLocal = 0.80f;
    dipped.weightBoth  = 0.40f;
    float dippedBoth = resolveAccentStrength(true, true, 1.f, dipped);
    CHECK(std::fabs(dippedBoth - 0.40f) < 1e-6f,
          "weightBoth can be less than weightTotal/weightLocal");

    // busAmount scales the result of the selected case.
    AccentMix unit;  // all 1.0
    float scaled = resolveAccentStrength(true, false, 0.5f, unit);
    CHECK(std::fabs(scaled - 0.5f) < 1e-6f, "busAmount scales the resolved weight");
}

static void test_accent_mix_no_local_voice_ignores_local_gate() {
    printf("\n[AccentMix: weightLocal=0 voice ignores Accent B]\n");
    using namespace AgentRack::TR909;
    // Models Ohh / RimClap / CrashRide configuration: no Accent B response.
    AccentMix noLocal;
    noLocal.weightTotal = 1.f;
    noLocal.weightLocal = 0.f;
    noLocal.weightBoth  = 1.f;  // when both fire, behaves like total-only

    float onlyA = resolveAccentStrength(true,  false, 1.f, noLocal);
    float onlyB = resolveAccentStrength(false, true,  1.f, noLocal);
    float both  = resolveAccentStrength(true,  true,  1.f, noLocal);

    CHECK(std::fabs(onlyA - 1.0f) < 1e-6f,
          "Accent A still produces full strength");
    CHECK(std::fabs(onlyB - 0.0f) < 1e-6f,
          "Accent B alone produces zero (voice has no Accent B)");
    CHECK(std::fabs(both  - 1.0f) < 1e-6f,
          "When both fire, weightBoth governs (here equal to A alone)");
}

static void test_kck_with_custom_mix_responds_to_both_case() {
    printf("\n[Kck: custom mix routes both-case to weightBoth]\n");
    // Tune Kck's mix so weightBoth is much larger than weightTotal/Local;
    // verify a hit with both gates high produces a louder result than
    // either alone. End-to-end test through the voice DSP.
    auto runHit = [](bool tA, bool tB, AgentRack::TR909::AccentMix mix) {
        Kck module;
        module.fit.accentMix = mix;
        module.params[Kck::TUNE_PARAM].setValue(0.35f);
        module.params[Kck::DECAY_PARAM].setValue(0.55f);
        module.params[Kck::PITCH_PARAM].setValue(0.40f);
        module.params[Kck::PITCH_DECAY_PARAM].setValue(0.30f);
        module.params[Kck::CLICK_PARAM].setValue(0.35f);
        module.params[Kck::DRIVE_PARAM].setValue(0.20f);
        module.params[Kck::LEVEL_PARAM].setValue(1.f);

        std::array<float, 4096> out {};
        auto args = ModuleHarness::makeArgs();
        ModuleHarness::connectInput(module, Kck::TOTAL_ACC_INPUT, tA ? 10.f : 0.f);
        ModuleHarness::connectInput(module, Kck::LOCAL_ACC_INPUT, tB ? 10.f : 0.f);
        ModuleHarness::connectInput(module, Kck::TRIG_INPUT, 0.f);
        module.process(args);
        ModuleHarness::connectInput(module, Kck::TRIG_INPUT, 10.f);
        module.process(args);
        ModuleHarness::connectInput(module, Kck::TRIG_INPUT, 0.f);
        for (size_t i = 0; i < out.size(); i++) {
            module.process(args);
            out[i] = AgentRack::Signal::Audio::fromRackVolts(
                module.outputs[Kck::OUT_OUTPUT].getVoltage());
        }
        return out;
    };

    AgentRack::TR909::AccentMix stacked;
    stacked.weightTotal = 0.30f;
    stacked.weightLocal = 0.30f;
    stacked.weightBoth  = 1.00f;

    float pA    = peak_abs(runHit(true,  false, stacked));
    float pB    = peak_abs(runHit(false, true,  stacked));
    float pBoth = peak_abs(runHit(true,  true,  stacked));

    CHECK(pBoth > pA   * 1.05f, "both-case louder than A-only with custom mix");
    CHECK(pBoth > pB   * 1.05f, "both-case louder than B-only with custom mix");
    CHECK(pBoth < 2.5f,         "both-case output remains bounded");
}

static void test_kck_accent_strength_scales_amplitude() {
    printf("\n[Kck accent: strength scales monotonically]\n");
    // Drive the voice DSP directly with three latched accent values.
    // This proves the accent path applies linear strength; the call site
    // (Kck::process) computes max(local, total) from gates and feeds the
    // result to fire(), so the max() rule is trivially satisfied so long
    // as fire(strength) responds monotonically to its argument.
    KckFit::Config fit = KckFit::makeKick();
    auto args = ModuleHarness::makeArgs();

    auto runVoice = [&](float strength) {
        KckVoice v;
        v.fire(strength);
        float p = 0.f;
        for (int i = 0; i < 4096; i++) {
            float s = v.process(args, fit, 0.50f, 0.50f, 0.385f, 0.26f,
                                0.50f, 0.f, 1.f);
            p = std::max(p, std::fabs(s));
        }
        return p;
    };

    float p0   = runVoice(0.f);
    float p050 = runVoice(0.5f);
    float p1   = runVoice(1.f);
    CHECK(p050 > p0   * 1.02f, "accent=0.5 boosts peak vs accent=0");
    CHECK(p1   > p050 * 1.02f, "accent=1.0 boosts peak vs accent=0.5");
    CHECK(p1   < 2.5f,         "accent=1.0 output remains bounded");
}

static void test_toms_pitch_increases_with_voice() {
    printf("\n[Toms pitch ordering regression]\n");
    auto low  = render_tom_hit<LowTom> (0.50f, 0.50f);
    auto mid  = render_tom_hit<MidTom> (0.50f, 0.50f);
    auto high = render_tom_hit<HighTom>(0.50f, 0.50f);

    float lowPeak = 0.f, midPeak = 0.f, highPeak = 0.f;
    for (float s : low)  lowPeak  = std::max(lowPeak,  std::fabs(s));
    for (float s : mid)  midPeak  = std::max(midPeak,  std::fabs(s));
    for (float s : high) highPeak = std::max(highPeak, std::fabs(s));

    // Compare across the full body window. Each voice's steady-state pitch
    // sets the zero-crossing density.
    int lowCross  = zero_crossings(low,  256, 3000);
    int midCross  = zero_crossings(mid,  256, 3000);
    int highCross = zero_crossings(high, 256, 3000);

    CHECK(lowPeak < 1.5f && midPeak < 1.5f && highPeak < 1.5f,
          "Tom outputs remain bounded");
    CHECK(highCross > lowCross,
          "HighTom has higher steady-state pitch than LowTom");
    CHECK(midCross >= lowCross && midCross <= highCross,
          "MidTom pitch sits between Low and High");
}

static void test_toms_decay_knob_extends_tail() {
    printf("\n[Toms decay regression]\n");
    auto shortHit = render_tom_hit<LowTom>(0.50f, 0.f);
    auto longHit  = render_tom_hit<LowTom>(0.50f, 1.f);

    // Compare a late window where decay differences are amplified.
    float shortTail = sum_abs(shortHit, 3000, 1000);
    float longTail  = sum_abs(longHit,  3000, 1000);

    CHECK(longTail > shortTail * 1.3f,
          "higher decay extends the tom tail");
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
    test_kck_trigger_produces_decaying_body();
    test_kck_local_accent_low_is_base_level();
    test_kck_local_accent_high_boosts_amplitude();
    test_kck_local_accent_sample_at_trig_invariance();
    test_kck_total_accent_boosts_amplitude();
    test_tr909ctrl_accent_amount_scales_accent();
    test_tr909ctrl_master_volume_scales_output();
    test_accent_mix_resolves_three_cases_independently();
    test_accent_mix_no_local_voice_ignores_local_gate();
    test_kck_with_custom_mix_responds_to_both_case();
    test_kck_accent_strength_scales_amplitude();
    test_snr_noise_controls_shape_the_hit();
    test_toms_pitch_increases_with_voice();
    test_toms_decay_knob_extends_tail();
    test_chh_sample_voice_controls_shape_the_hit();
    test_ohh_sample_voice_controls_shape_the_hit();
    test_rimclap_voices_produce_audio();
    test_crashride_voices_produce_audio();
    test_tonnetz_trigger_selects_triangle();

    printf("\n=== Results: %d passed, %d failed ===\n", passed, failed);
    return failed > 0 ? 1 : 0;
}
