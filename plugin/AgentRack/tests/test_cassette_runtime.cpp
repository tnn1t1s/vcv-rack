#include <cstdio>
#include "../src/agentrack/infrastructure/CassetteRuntime.hpp"

using CassetteRuntime = AgentRack::Infrastructure::CassetteRuntime;

struct FakeEngine {
    float speedRamp = 1.f;
    int resetCalls = 0;

    void reset() {
        resetCalls++;
    }
};

LoopPack& getInternalPack() {
    static LoopPack pack;
    return pack;
}

bool loadPackFromDisk(const std::string&, LoopPack&) {
    return false;
}

static int g_failures = 0;

static void expect(bool cond, const char* msg) {
    if (!cond) {
        std::fprintf(stderr, "FAIL: %s\n", msg);
        g_failures++;
    }
}

int main() {
    CassetteRuntime runtime;
    FakeEngine engine;

    expect(runtime.activePack() == &getInternalPack(), "starts on internal pack");
    expect(runtime.currentLoop() == 0, "starts on loop 0");
    expect(runtime.isPlaying(), "starts playing");
    expect(!runtime.isSwapping(), "starts not swapping");
    expect(runtime.engineShouldPlay(), "engine should play initially");

    runtime.requestLoop(3);
    expect(runtime.isSwapping(), "requestLoop starts swapping");
    expect(!runtime.engineShouldPlay(), "engine should stop during swap");

    engine.speedRamp = 0.5f;
    runtime.completeSwapIfReady(engine);
    expect(runtime.isSwapping(), "swap waits for ramp down");
    expect(runtime.currentLoop() == 0, "loop unchanged before ramp down");

    engine.speedRamp = 0.0f;
    runtime.completeSwapIfReady(engine);
    expect(!runtime.isSwapping(), "swap completes after ramp down");
    expect(runtime.currentLoop() == 3, "loop advances after swap");

    runtime.togglePlaying();
    expect(!runtime.isPlaying(), "toggle stops playback");
    expect(!runtime.engineShouldPlay(), "stopped runtime does not play");
    runtime.togglePlaying();
    expect(runtime.isPlaying(), "toggle restarts playback");

    LoopPack* pack = new LoopPack();
    pack->name = "TEST";
    pack->indexPath = "/tmp/test/index.json";
    runtime.postLoadedPack(pack);
    runtime.consumePendingPack(engine);
    expect(runtime.activePack()->name == "TEST", "pending pack becomes active");
    expect(runtime.currentLoop() == 0, "new pack resets loop");
    expect(!runtime.isSwapping(), "new pack clears swap state");
    expect(engine.resetCalls > 0, "pack consumption resets engine");

    runtime.requestLoop(4);
    engine.speedRamp = 0.0f;
    runtime.completeSwapIfReady(engine);
    expect(runtime.currentLoop() == 4, "active pack loop can advance");

    runtime.resetToInternal(engine);
    expect(runtime.activePack() == &getInternalPack(), "reset returns to internal pack");
    expect(runtime.currentLoop() == 0, "reset returns to loop 0");
    expect(!runtime.isSwapping(), "reset clears swap state");

    if (g_failures == 0) {
        std::printf("PASS test_cassette_runtime\n");
        return 0;
    }
    return 1;
}
