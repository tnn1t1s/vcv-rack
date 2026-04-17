#include <cstdio>
#include <cmath>
#include "../src/tape/CassetteMachineProfile.hpp"

static int g_failures = 0;

static void expect(bool cond, const char* msg) {
    if (!cond) {
        std::fprintf(stderr, "FAIL: %s\n", msg);
        g_failures++;
    }
}

static void expectNear(float a, float b, float eps, const char* msg) {
    if (std::fabs(a - b) > eps) {
        std::fprintf(stderr, "FAIL: %s (got=%g expected=%g)\n", msg, a, b);
        g_failures++;
    }
}

int main() {
    const float sampleTime = 1.f / 48000.f;

    CassetteMachineProfile clean = CassetteMachineProfile::fromSelection(0, sampleTime);
    expectNear(clean.wowAmount, 0.f, 1e-7f, "new profile has no wow");
    expectNear(clean.flutterAmount, 0.f, 1e-7f, "new profile has no flutter");
    expectNear(clean.saturationDrive, 0.f, 1e-7f, "new profile has no saturation");
    expectNear(clean.hissAmount, 0.f, 1e-7f, "new profile has no hiss");
    expect(!clean.crackleEnabled, "new profile disables crackle");

    CassetteMachineProfile worn = CassetteMachineProfile::fromSelection(1, sampleTime);
    expectNear(worn.wowAmount, 0.005f, 1e-7f, "worn profile wow");
    expectNear(worn.flutterAmount, 0.0015f, 1e-7f, "worn profile flutter");
    expectNear(worn.saturationDrive, 0.15f, 1e-7f, "worn profile saturation");
    expectNear(worn.hissAmount, 0.006f, 1e-7f, "worn profile hiss");
    expect(!worn.crackleEnabled, "worn profile disables crackle");

    CassetteMachineProfile old = CassetteMachineProfile::fromSelection(2, sampleTime);
    expectNear(old.wowAmount, 0.018f, 1e-7f, "old profile wow");
    expectNear(old.flutterAmount, 0.005f, 1e-7f, "old profile flutter");
    expectNear(old.saturationDrive, 0.45f, 1e-7f, "old profile saturation");
    expectNear(old.hissAmount, 0.022f, 1e-7f, "old profile hiss");
    expect(old.crackleEnabled, "old profile enables crackle");

    expect(clean.toneAlpha > worn.toneAlpha, "clean profile keeps the brightest tone");
    expect(worn.toneAlpha > old.toneAlpha, "worn profile is brighter than old");

    if (g_failures == 0) {
        std::printf("PASS test_cassette_machine_profile\n");
        return 0;
    }
    return 1;
}
