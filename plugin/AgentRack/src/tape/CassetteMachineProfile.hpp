#pragma once

#include <cmath>

struct CassetteMachineProfile {
    float wowAmount = 0.f;
    float flutterAmount = 0.f;
    float saturationDrive = 0.f;
    float hissAmount = 0.f;
    float toneAlpha = 0.f;
    bool crackleEnabled = false;

    static CassetteMachineProfile fromSelection(int tapeSelection, float sampleTime) {
        static constexpr float TWO_PI = 6.28318530718f;
        CassetteMachineProfile profile;

        if (tapeSelection == 1) {
            profile.wowAmount = 0.005f;
            profile.flutterAmount = 0.0015f;
            profile.saturationDrive = 0.15f;
            profile.hissAmount = 0.006f;
            profile.toneAlpha = 1.f - expf(-TWO_PI * 8000.f * sampleTime);
            return profile;
        }

        if (tapeSelection == 2) {
            profile.wowAmount = 0.018f;
            profile.flutterAmount = 0.005f;
            profile.saturationDrive = 0.45f;
            profile.hissAmount = 0.022f;
            profile.toneAlpha = 1.f - expf(-TWO_PI * 3000.f * sampleTime);
            profile.crackleEnabled = true;
            return profile;
        }

        profile.toneAlpha = 1.f - expf(-TWO_PI * 18000.f * sampleTime);
        return profile;
    }
};
