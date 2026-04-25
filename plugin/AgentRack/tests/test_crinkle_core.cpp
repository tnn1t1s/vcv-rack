#include "../src/agentrack/signal/CrinkleCore.hpp"
#include <algorithm>
#include <cmath>
#include <cstdio>

static int passed = 0;
static int failed = 0;

#define CHECK(cond, msg) do { \
    if (cond) { printf("  PASS  %s\n", msg); passed++; } \
    else       { printf("  FAIL  %s\n", msg); failed++; } \
} while(0)

using AgentRack::Signal::Crinkle::Voice;
using AgentRack::Signal::Crinkle::trifold;
using AgentRack::Signal::Crinkle::wavefold;

static void test_fold_helpers_are_bounded() {
    printf("\n[Crinkle fold helpers]\n");
    float maxAbsTri = 0.f;
    float maxAbsFold = 0.f;
    for (int i = -200; i <= 200; ++i) {
        float x = 0.05f * static_cast<float>(i);
        maxAbsTri = std::max(maxAbsTri, std::fabs(trifold(x)));
        maxAbsFold = std::max(maxAbsFold, std::fabs(wavefold(x, 1.f, 1.f)));
    }
    CHECK(maxAbsTri <= 1.001f, "trifold stays inside +/-1");
    CHECK(maxAbsFold <= 1.001f, "wavefold stays inside +/-1");
}

static void test_voice_output_is_finite_and_dynamic() {
    printf("\n[Crinkle voice output]\n");
    Voice voice;

    bool finite = true;
    float minOut = 1e9f;
    float maxOut = -1e9f;

    for (int i = 0; i < 4096; ++i) {
        float out = voice.processSample(261.6256f, 0.3f, 0.1f, 1.f / 44100.f);
        finite = finite && std::isfinite(out);
        minOut = std::min(minOut, out);
        maxOut = std::max(maxOut, out);
    }

    CHECK(finite, "voice output remains finite");
    CHECK(std::max(std::fabs(minOut), std::fabs(maxOut)) <= 1.001f,
          "voice output stays normalized");
    CHECK((maxOut - minOut) > 0.2f, "voice output changes over time");
}

static void test_independent_voices_do_not_share_state() {
    printf("\n[Crinkle independent voices]\n");
    Voice low;
    Voice high;

    float outLow = 0.f;
    float outHigh = 0.f;
    for (int i = 0; i < 4096; ++i) {
        outLow = low.processSample(130.8128f, 0.25f, 0.05f, 1.f / 44100.f);
        outHigh = high.processSample(523.2511f, 0.25f, 0.05f, 1.f / 44100.f);
    }

    CHECK(std::fabs(outLow - outHigh) > 1e-3f,
          "separate voices diverge under different pitches");
}

int main() {
    printf("=== AgentRack Crinkle core test suite ===\n");

    test_fold_helpers_are_bounded();
    test_voice_output_is_finite_and_dynamic();
    test_independent_voices_do_not_share_state();

    printf("\n=== Results: %d passed, %d failed ===\n", passed, failed);
    return failed > 0 ? 1 : 0;
}
