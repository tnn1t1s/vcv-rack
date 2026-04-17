#include "../src/agentrack/infrastructure/SaphireRuntime.hpp"
#include "../src/FFTProvider.cpp"
#include "../src/FFTvDSP.cpp"
#include <cstdio>

using SaphireRuntime = AgentRack::Infrastructure::SaphireRuntime;

static int passed = 0;
static int failed = 0;

#define CHECK(cond, msg) do { \
    if (cond) { std::printf("  PASS  %s\n", msg); passed++; } \
    else { std::printf("  FAIL  %s\n", msg); failed++; } \
} while (0)

static void test_initial_state() {
    std::printf("\n[initial state]\n");
    SaphireRuntime runtime;
    runtime.init();
    runtime.setInitialState(12, 0.5f, 0.f);

    CHECK(runtime.currentIrIndex() == 12, "initial IR index is exposed");
    CHECK(!runtime.oldConvolutionIsSafe(), "old convolution starts unsafe");
    CHECK(!runtime.isCrossfading(), "runtime starts outside a crossfade");
    CHECK(!runtime.shouldRebuild({12, 0.5f, 0.f}), "same params do not trigger rebuild");
    CHECK(runtime.shouldRebuild({13, 0.5f, 0.f}), "IR change triggers rebuild");
    CHECK(runtime.shouldRebuild({12, 0.7f, 0.f}), "time change triggers rebuild");
    CHECK(runtime.shouldRebuild({12, 0.5f, 0.2f}), "bend change triggers rebuild");
}

static void test_request_clamps_ir_selection() {
    std::printf("\n[request normalization]\n");

    auto belowRange = SaphireRuntime::makeRequest(-5.f, 0.25f, -0.5f, 40);
    auto aboveRange = SaphireRuntime::makeRequest(99.f, 0.25f, -0.5f, 40);
    auto rounded = SaphireRuntime::makeRequest(12.6f, 0.25f, -0.5f, 40);

    CHECK(belowRange.irIndex == 0, "IR request clamps below range");
    CHECK(aboveRange.irIndex == 39, "IR request clamps above range");
    CHECK(rounded.irIndex == 13, "IR request rounds to nearest slot");
    CHECK(rounded.timeParam == 0.25f, "request keeps time parameter");
    CHECK(rounded.bendParam == -0.5f, "request keeps bend parameter");
}

static void test_rebuild_handoff_and_crossfade() {
    std::printf("\n[rebuild handoff and crossfade]\n");
    SaphireRuntime runtime;
    runtime.init();
    runtime.setInitialState(3, 0.5f, 0.f);

    int rebuiltTarget = -1;
    int rebuiltIr = -1;
    bool launched = runtime.launchRebuild({8, 0.6f, 0.25f},
        [&](int target, int irIndex) {
            rebuiltTarget = target;
            rebuiltIr = irIndex;
        });

    CHECK(launched, "first rebuild launches");
    runtime.joinBuilder();
    runtime.consumeCompletedRebuild();

    CHECK(rebuiltTarget == 1, "rebuild targets the inactive engine");
    CHECK(rebuiltIr == 8, "rebuild callback receives requested IR");
    CHECK(runtime.currentIrIndex() == 8, "completed rebuild publishes new IR index");
    CHECK(runtime.oldConvolutionIsSafe(), "old convolution becomes safe during crossfade");
    CHECK(runtime.isCrossfading(), "completed rebuild starts a crossfade");

    float wetL = 1.f;
    float wetR = -1.f;
    runtime.applyCrossfade(wetL, wetR, 0.f, 0.f);
    CHECK(wetL == 0.f && wetR == 0.f, "crossfade starts from old engine output");

    for (int i = 1; i < AgentRack::Infrastructure::PartitionedConvolution::kBlockSize; i++) {
        float l = 1.f;
        float r = 1.f;
        runtime.applyCrossfade(l, r, 0.f, 0.f);
    }
    CHECK(!runtime.isCrossfading(), "crossfade completes after one block");
    CHECK(!runtime.oldConvolutionIsSafe(), "old convolution is released after crossfade");
}

int main() {
    std::printf("=== AgentRack SaphireRuntime test suite ===\n");

    test_initial_state();
    test_request_clamps_ir_selection();
    test_rebuild_handoff_and_crossfade();

    std::printf("\n=== Results: %d passed, %d failed ===\n", passed, failed);
    return failed ? 1 : 0;
}
