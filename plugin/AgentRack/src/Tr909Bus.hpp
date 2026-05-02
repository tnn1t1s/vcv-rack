#pragma once
#include <rack.hpp>
#include <algorithm>
#include <cmath>
#include "AgentModule.hpp"

/**
 * Tr909Bus -- adjacent-module state broadcast for the AgentRack 909 suite.
 *
 * Tr909Ctrl publishes slow-changing global state (accent multiplier and
 * master volume) and adjacent voices read it via the leftExpander/
 * rightExpander module pointer. Hit-time events (triggers, total accent
 * gate, local accent gate) are NOT carried on this bus -- they travel
 * through cables to per-voice inputs so they're sampled deterministically
 * on the trigger rising edge with zero latency.
 *
 * The bus uses a "pull" / direct-read pattern: each Tr909Module exposes
 * its current state as a public member, neighbors read it directly.
 * Voices forward by copying the resolved state into their own currentBus
 * each frame, so a chain of [Tr909Ctrl][Kck][Snr][Toms]... all see the
 * controller's broadcast even though only the leftmost voice is directly
 * adjacent to the controller.
 *
 * Latency caveat: this is NOT a same-sample-deterministic bus. Reads see
 * the value the neighbor wrote on its most recent process() call. If the
 * neighbor processes AFTER us in a frame, we get its value from the
 * previous frame (1-sample staleness). Forwarding through N voices adds
 * up to N-1 samples of staleness for the far end of the chain. This is
 * acceptable for slow knob/CV state but DO NOT build synchronous
 * trigger logic on top of this bus -- use cables for any hit-time event.
 */

namespace AgentRack { namespace TR909 {

struct Bus {
    // accentAAmount / accentBAmount are 0..1 linear-space attenuators on
    // each accent rail's contribution. amtA=0 mutes A's contribution
    // wherever A fires (alone or in the both case); same for amtB.
    // ghostAmount is a 0..1 attenuator on the ghost case (no accent
    // gates fired) -- lets the user globally tune "default volume" /
    // "ghost note level" without editing per-voice config.
    float accentAAmount     = 1.f;
    float accentBAmount     = 1.f;
    float ghostAmount       = 1.f;
    float masterVolume      = 1.f;   // post-everything linear scalar
    bool  controllerPresent = false;
};

/**
 * AccentMix -- per-voice level relationship across the four 909 accent
 * cases, expressed in dB relative to a reference level.
 *
 * The four cases:
 *   - ghost:   neither gate fired. On a real 909 this is the ghost note
 *              level: a programmer leaves both accents off when they
 *              want the voice to duck below its normal hit.
 *   - local:   B only (per-voice accent track). This is the 909 "normal"
 *              hit on supported voices (BD/SD/Toms/CH per Roland OM)
 *              and is the project reference (0 dB by default).
 *   - global:  A only (Total Accent track on its own). Slight emphasis,
 *              less than full because there's no per-voice support.
 *   - both:    A and B together. The strongest hit.
 *
 * Defaults are MODEST starting points (-6 / -1 / 0 / +1.5 dB) selected
 * to be tunable by ear without clipping. They are NOT verified
 * hardware-faithful values; per-voice tuning by ear or against TR-909
 * reference samples is expected.
 *
 * AccentMix encodes ONLY the level relationship. The voice's own
 * Fit::Config still decides the CHARACTER of an accented hit
 * (drive, pitch dive, click brightness, etc.) via per-DSP-stage weights
 * gated on "is this hit accented at all?" -- different concerns,
 * intentionally separated.
 *
 * To make a voice ignore Accent B (Ohh / RimClap / Crash / Ride per
 * Roland OM): set localDb = ghostDb so B-alone collapses to ghost.
 * Or simply do not wire LOCAL_ACC_INPUT on the voice.
 */
struct AccentMix {
    float ghostDb  = -6.f;
    float globalDb = -1.f;
    float localDb  =  0.f;
    float bothDb   = +1.5f;
};

/**
 * Neutral mix: every case at 0 dB so accent rails change nothing.
 * Used as the per-voice default until that voice's level relationship
 * has been calibrated by ear; lets us plumb accent inputs everywhere
 * without changing audible behaviour for un-tuned voices.
 */
inline AccentMix neutralMix() {
    AccentMix m;
    m.ghostDb = m.globalDb = m.localDb = m.bothDb = 0.f;
    return m;
}

/** dB to linear gain (10^(db/20)). */
inline float dbToLinear(float db) {
    return std::pow(10.f, db / 20.f);
}

/**
 * Resolve the per-case output gain (linear) at trigger-rising-edge time.
 *
 * Reads the bus's three accent attenuators (accentAAmount,
 * accentBAmount, ghostAmount) and the voice's per-case dB mix.
 *
 * Single-rail and both-case scaling (linear contribution model):
 *     gain = amtA * lin(globalDb) + amtB * lin(localDb)
 *          + amtA*amtB * (lin(bothDb) - lin(globalDb) - lin(localDb))
 * (cases compute only the contributions for rails that fired).
 *
 * - amtA = 0 mutes A's contribution wherever A fires (alone or both).
 * - amtA = 1 makes A's contribution count fully.
 * - same for amtB.
 * - amtA = amtB = 0 with any rail firing -> effectively silent.
 *
 * Ghost case (neither gate fires):
 *     gain = lin(ghostDb) * bus.ghostAmount
 * The bus's ghostAmount knob is a global trim on the no-accent level.
 *
 * Verified algebraically:
 *   - amtA=1, amtB=1, both fire: gain = lin(bothDb)
 *   - amtA=0, amtB=1, both fire: gain = lin(localDb) (B-only behavior)
 *   - amtA=1, amtB=0, both fire: gain = lin(globalDb) (A-only behavior)
 *   - amtA=0, amtB=0, any fire:  gain = 0
 *   - no gates, ghostAmt=1:      gain = lin(ghostDb)
 *   - no gates, ghostAmt=0:      gain = 0
 */
inline float resolveAccentGain(bool totalGate, bool localGate,
                               const Bus& bus,
                               const AccentMix& mix) {
    if (!totalGate && !localGate) {
        return dbToLinear(mix.ghostDb) * bus.ghostAmount;
    }

    const float gA    = dbToLinear(mix.globalDb);
    const float gB    = dbToLinear(mix.localDb);
    const float gBoth = dbToLinear(mix.bothDb);
    const float amtA  = bus.accentAAmount;
    const float amtB  = bus.accentBAmount;

    float gain = 0.f;
    if (totalGate)              gain += amtA * gA;
    if (localGate)              gain += amtB * gB;
    if (totalGate && localGate) gain += amtA * amtB * (gBoth - gA - gB);
    return gain;
}

/**
 * Whether the hit should apply the voice's accent CHARACTER (per-DSP
 * weights for drive/click/pitch/etc.). Boolean: any accent gate fires =
 * accent character on; ghost = off. The voice's own Fit::Config decides
 * what that character is.
 */
inline bool isAccentedHit(bool totalGate, bool localGate) {
    return totalGate || localGate;
}


/** Result of resolving the accent state at a TRIG rising edge. */
struct AccentResolution {
    float charStrength;  // 0 or 1, drives voice DSP accent character
    float gain;          // linear multiplier for the voice output
};

/**
 * One-shot sample of the accent gates at trigger-rising-edge time.
 *
 * Reads totalInputId from `self`'s inputs (always required); reads
 * localInputId if it is >= 0 (voices without Accent B per Roland TR-909
 * OM -- Ohh, RimClap, CrashRide -- pass -1 to skip). Combines the gates
 * with bus state and the voice's mix into a {charStrength, gain} pair.
 *
 * Voice integration (with Accent B):
 *     auto acc = sampleAccentAtTrig(this, TOTAL_ACC_INPUT, bus,
 *                                   fit.accentMix, LOCAL_ACC_INPUT);
 *     voice.fire(acc.charStrength);
 *     latchedCaseGain = acc.gain;
 *
 * Voice integration (without Accent B):
 *     auto acc = sampleAccentAtTrig(this, TOTAL_ACC_INPUT, bus,
 *                                   fit.accentMix);
 *     voice.fire(acc.charStrength);
 *     latchedCaseGain = acc.gain;
 */
inline AccentResolution sampleAccentAtTrig(rack::Module* self,
                                           int totalInputId,
                                           const Bus& bus,
                                           const AccentMix& mix,
                                           int localInputId = -1) {
    const bool totalGate = (totalInputId >= 0)
        && self->inputs[totalInputId].getNormalVoltage(0.f) > 1.f;
    const bool localGate = (localInputId >= 0)
        && self->inputs[localInputId].getNormalVoltage(0.f) > 1.f;
    AccentResolution r;
    r.charStrength = isAccentedHit(totalGate, localGate) ? 1.f : 0.f;
    r.gain         = resolveAccentGain(totalGate, localGate, bus, mix);
    return r;
}

}} // namespace

/** Marker base for any 909 module that participates in the state bus. */
struct Tr909Module : AgentModule {
    AgentRack::TR909::Bus currentBus;
};

namespace AgentRack { namespace TR909 {

/**
 * Resolve the current bus state by checking adjacent Tr909Modules.
 * Returns first found controllerPresent state, defaulting to a "no
 * controller, neutral values" Bus otherwise. Voices should call this
 * once per process() and use the returned amounts when computing
 * accent/output.
 *
 * Also writes the resolved state into self->currentBus so the chain
 * extends through this voice to whichever neighbor is on the other side.
 */
inline Bus resolveBus(Tr909Module* self) {
    Bus state;

    if (auto* leftN = dynamic_cast<Tr909Module*>(self->leftExpander.module)) {
        if (leftN->currentBus.controllerPresent) {
            state = leftN->currentBus;
        }
    }
    if (!state.controllerPresent) {
        if (auto* rightN = dynamic_cast<Tr909Module*>(self->rightExpander.module)) {
            if (rightN->currentBus.controllerPresent) {
                state = rightN->currentBus;
            }
        }
    }

    self->currentBus = state;
    return state;
}

}} // namespace
