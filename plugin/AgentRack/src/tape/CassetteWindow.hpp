#pragma once
#include <rack.hpp>

// ---------------------------------------------------------------------------
// 5 tape loop cassette shell colors (translucent)
// Order: pink, teal, yellow, blue, green
// ---------------------------------------------------------------------------
static const NVGcolor CASSETTE_SHELL_COLORS[5] = {
    nvgRGBA(220, 100, 150, 175),   // pink
    nvgRGBA( 60, 180, 170, 175),   // teal
    nvgRGBA(210, 190,  40, 175),   // yellow
    nvgRGBA( 60, 120, 210, 175),   // blue
    nvgRGBA( 60, 180,  80, 175),   // green
};

// Loop lengths in seconds for each cassette slot
static const float CASSETTE_LENS[5] = {0.5f, 1.f, 2.f, 3.5f, 5.f};

inline NVGcolor cassetteShellColor(int idx) {
    if (idx < 0) idx = 0;
    if (idx > 4) idx = 4;
    return CASSETTE_SHELL_COLORS[idx];
}

// ---------------------------------------------------------------------------
// drawCassetteWindow
//
// Draws a cassette tape loop inside a bounding rect (x,y,w,h).
// The characteristic X tape path: left reel feeds the RIGHT guide pin,
// right reel feeds the LEFT guide pin — the tape crosses in the center.
// reelAngle is in radians, advancing each frame.
// isReverse flips the crossing direction visually.
// ---------------------------------------------------------------------------
inline void drawCassetteWindow(NVGcontext* vg,
    float x, float y, float w, float h,
    NVGcolor shellColor, float reelAngle, bool isReverse)
{
    float cx = x + w * 0.5f;
    float cy = y + h * 0.5f;

    // --- Shell background ---
    nvgBeginPath(vg);
    nvgRoundedRect(vg, x, y, w, h, 4.f);
    nvgFillColor(vg, shellColor);
    nvgFill(vg);

    // Darker inner border
    nvgStrokeColor(vg, nvgRGBA(0, 0, 0, 80));
    nvgStrokeWidth(vg, 1.f);
    nvgStroke(vg);

    // --- Corner screws ---
    NVGcolor screwColor = nvgRGBA(200, 200, 200, 120);
    float sr = 2.5f;
    float corners[4][2] = {
        {x + 6.f, y + 6.f},
        {x + w - 6.f, y + 6.f},
        {x + 6.f, y + h - 6.f},
        {x + w - 6.f, y + h - 6.f},
    };
    for (int i = 0; i < 4; i++) {
        nvgBeginPath(vg);
        nvgCircle(vg, corners[i][0], corners[i][1], sr);
        nvgFillColor(vg, screwColor);
        nvgFill(vg);
        // Cross slot
        nvgBeginPath(vg);
        nvgMoveTo(vg, corners[i][0] - sr + 0.5f, corners[i][1]);
        nvgLineTo(vg, corners[i][0] + sr - 0.5f, corners[i][1]);
        nvgStrokeColor(vg, nvgRGBA(0, 0, 0, 100));
        nvgStrokeWidth(vg, 0.7f);
        nvgStroke(vg);
        nvgBeginPath(vg);
        nvgMoveTo(vg, corners[i][0], corners[i][1] - sr + 0.5f);
        nvgLineTo(vg, corners[i][0], corners[i][1] + sr - 0.5f);
        nvgStroke(vg);
    }

    // --- Reel centers ---
    float reelR  = w * 0.22f;   // reel outer radius
    float hubR   = reelR * 0.35f;
    float lrx    = x + w * 0.28f;   // left reel center x
    float rrx    = x + w * 0.72f;   // right reel center x
    float ry     = cy - h * 0.05f;  // reel center y (slightly above middle)

    // Guide pins (bottom center area, left and right of center gap)
    float gpY    = y + h * 0.82f;
    float lpgX   = cx - w * 0.12f;  // left guide pin
    float rpgX   = cx + w * 0.12f;  // right guide pin
    float gpR    = 2.f;

    // --- Tape path: X crossing ---
    // Left reel tangent point (bottom right of left reel)
    // Right reel tangent point (bottom left of right reel)
    float tapeW = 1.8f;

    float lTapeX = lrx + reelR * 0.6f;
    float lTapeY = ry  + reelR * 0.7f;
    float rTapeX = rrx - reelR * 0.6f;
    float rTapeY = ry  + reelR * 0.7f;

    // X crossing: left reel → right guide pin, right reel → left guide pin
    // The two tape strands cross near center
    NVGcolor tapeColor = nvgRGBA(30, 20, 10, 200);

    nvgLineCap(vg, NVG_ROUND);

    if (!isReverse) {
        // Forward: left → right guide, right → left guide
        nvgBeginPath(vg);
        nvgMoveTo(vg, lTapeX, lTapeY);
        nvgLineTo(vg, rpgX, gpY);
        nvgStrokeColor(vg, tapeColor);
        nvgStrokeWidth(vg, tapeW);
        nvgStroke(vg);

        nvgBeginPath(vg);
        nvgMoveTo(vg, rTapeX, rTapeY);
        nvgLineTo(vg, lpgX, gpY);
        nvgStrokeColor(vg, tapeColor);
        nvgStrokeWidth(vg, tapeW);
        nvgStroke(vg);
    } else {
        // Reverse: mirror the crossing
        nvgBeginPath(vg);
        nvgMoveTo(vg, lTapeX, lTapeY);
        nvgLineTo(vg, lpgX, gpY);
        nvgStrokeColor(vg, tapeColor);
        nvgStrokeWidth(vg, tapeW);
        nvgStroke(vg);

        nvgBeginPath(vg);
        nvgMoveTo(vg, rTapeX, rTapeY);
        nvgLineTo(vg, rpgX, gpY);
        nvgStrokeColor(vg, tapeColor);
        nvgStrokeWidth(vg, tapeW);
        nvgStroke(vg);
    }

    // Tape along bottom (head contact zone)
    nvgBeginPath(vg);
    nvgMoveTo(vg, lpgX, gpY);
    nvgLineTo(vg, rpgX, gpY);
    nvgStrokeColor(vg, tapeColor);
    nvgStrokeWidth(vg, tapeW);
    nvgStroke(vg);

    // --- Guide pins ---
    NVGcolor pinColor = nvgRGBA(180, 180, 180, 200);
    nvgBeginPath(vg);
    nvgCircle(vg, lpgX, gpY, gpR);
    nvgFillColor(vg, pinColor);
    nvgFill(vg);
    nvgBeginPath(vg);
    nvgCircle(vg, rpgX, gpY, gpR);
    nvgFill(vg);

    // --- Reels (spoked) ---
    NVGcolor reelRimColor  = nvgRGBA(60, 60, 60, 200);
    NVGcolor reelHubColor  = nvgRGBA(40, 40, 40, 240);
    NVGcolor spokeColor    = nvgRGBA(80, 80, 80, 180);

    for (int reel = 0; reel < 2; reel++) {
        float rx = (reel == 0) ? lrx : rrx;
        float angle = reelAngle;

        // Outer rim
        nvgBeginPath(vg);
        nvgCircle(vg, rx, ry, reelR);
        nvgFillColor(vg, nvgRGBA(50, 50, 50, 160));
        nvgFill(vg);
        nvgStrokeColor(vg, reelRimColor);
        nvgStrokeWidth(vg, 1.2f);
        nvgStroke(vg);

        // Spokes (3)
        for (int s = 0; s < 3; s++) {
            float sa = angle + s * (2.f * (float)M_PI / 3.f);
            float sx1 = rx + hubR * cosf(sa);
            float sy1 = ry + hubR * sinf(sa);
            float sx2 = rx + (reelR - 2.f) * cosf(sa);
            float sy2 = ry + (reelR - 2.f) * sinf(sa);
            nvgBeginPath(vg);
            nvgMoveTo(vg, sx1, sy1);
            nvgLineTo(vg, sx2, sy2);
            nvgStrokeColor(vg, spokeColor);
            nvgStrokeWidth(vg, 2.f);
            nvgStroke(vg);
        }

        // Hub
        nvgBeginPath(vg);
        nvgCircle(vg, rx, ry, hubR);
        nvgFillColor(vg, reelHubColor);
        nvgFill(vg);
        nvgStrokeColor(vg, nvgRGBA(100, 100, 100, 160));
        nvgStrokeWidth(vg, 0.8f);
        nvgStroke(vg);

        // Center dot
        nvgBeginPath(vg);
        nvgCircle(vg, rx, ry, 2.f);
        nvgFillColor(vg, nvgRGBA(120, 120, 120, 200));
        nvgFill(vg);
    }
}
