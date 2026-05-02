#pragma once
#include <rack.hpp>
#include <algorithm>
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
    float accentAmount      = 1.f;   // 0..1, scales accent strength
    float masterVolume      = 1.f;   // 0..1, scales voice output
    bool  controllerPresent = false;
};

/**
 * AccentMix -- per-voice tuning of how Accent A (Total) and Accent B
 * (Local) gates combine into a single accent strength.
 *
 * Three independent weights are configurable, one per case:
 *   - weightTotal: strength when only Accent A fires
 *   - weightLocal: strength when only Accent B fires
 *   - weightBoth:  strength when both fire (NOT derived from the other two;
 *                  research may show "both accented" should be stronger,
 *                  weaker, or shaped differently than either alone)
 *
 * Defaults are all 1.0, which makes any accented hit (A, B, or both) full
 * strength. This is a current heuristic, NOT a verified hardware-faithful
 * default -- TR-909 service manual research is open. Tune per-voice.
 *
 * Common patterns:
 *   - weightLocal=0: voice ignores Accent B. Required for voices that
 *                    don't have a LOCAL_ACC_INPUT jack (Ohh, RimClap,
 *                    CrashRide per Roland TR-909 OM).
 *   - weightLocal > weightTotal: voice responds more strongly to its own
 *                    per-step accent than to global accent.
 *   - weightBoth > max(weightTotal, weightLocal): "both" case stacks.
 *
 * The DSP-stage weights (e.g. accentBodyAmt, accentDriveAmt) live in the
 * voice's own Fit::Config, NOT here. AccentMix produces the scalar
 * strength; the voice decides what each DSP stage does with it.
 */
struct AccentMix {
    float weightTotal = 1.f;
    float weightLocal = 1.f;
    float weightBoth  = 1.f;
};

/**
 * Compute accent strength at trigger-rising-edge time.
 *
 * Gates are sampled from cable inputs (zero latency). busAmount is from
 * Tr909Ctrl via the slow-state bus. The mix selects one of three weights
 * by case (only-A, only-B, both); when neither gate fires, returns 0.
 *
 * Voices then multiply the returned strength by their own per-DSP-stage
 * weights to scale specific stages of their synthesis.
 */
inline float resolveAccentStrength(bool totalGate, bool localGate,
                                   float busAmount,
                                   const AccentMix& mix) {
    if (totalGate && localGate) return mix.weightBoth  * busAmount;
    if (totalGate)              return mix.weightTotal * busAmount;
    if (localGate)              return mix.weightLocal * busAmount;
    return 0.f;
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
