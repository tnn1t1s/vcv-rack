#pragma once

#include <string>

namespace AgentRack {
namespace Signal {
namespace Attenuate {

static constexpr int kRows = 8;
static constexpr int kModeCount = 4;

enum RowMode {
    MODE_UNIPOLAR_10 = 0,
    MODE_BIPOLAR_5   = 1,
    MODE_VOCT_1OCT   = 2,
    MODE_VOCT_2OCT   = 3,
};

static const char* const MODE_KEYS[kModeCount] = {
    "unipolar_10", "bipolar_5", "voct_1oct", "voct_2oct",
};

static const char* const MODE_TAGS[kModeCount] = {
    "10V", "+-5V", "+-1V", "+-2V",
};

static const char* const MODE_LABELS[kModeCount] = {
    "0 to +10V  (unipolar)",
    "+/-5V  (bipolar)",
    "+/-1V  (V/Oct, 1 oct)",
    "+/-2V  (V/Oct, 2 oct)",
};

inline int normalizeMode(int mode) {
    if (mode < 0 || mode >= kModeCount) {
        return MODE_UNIPOLAR_10;
    }
    return mode;
}

inline int modeFromKey(const std::string& key) {
    for (int i = 0; i < kModeCount; ++i) {
        if (key == MODE_KEYS[i]) {
            return i;
        }
    }
    return MODE_UNIPOLAR_10;
}

inline float macroVolts(int mode, float scale) {
    switch (normalizeMode(mode)) {
        case MODE_UNIPOLAR_10: return scale * 10.f;
        case MODE_BIPOLAR_5:   return (scale - 0.5f) * 10.f;
        case MODE_VOCT_1OCT:   return (scale - 0.5f) *  2.f;
        case MODE_VOCT_2OCT:   return (scale - 0.5f) *  4.f;
    }
    return scale * 10.f;
}

inline float rowOutput(bool inputConnected, float inputVolts, float scale, int mode) {
    if (inputConnected) {
        return inputVolts * scale;
    }
    return macroVolts(mode, scale);
}

} // namespace Attenuate
} // namespace Signal
} // namespace AgentRack
