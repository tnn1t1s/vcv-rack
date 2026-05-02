# Reflection — TR-909 Accent System Phase 1

**Date:** 2026-05-01
**Session scope:** Issue #73 phase 1 → PR #79 (merged as commit `e616501`)
**Artifact:** Tr909Ctrl global controller, AccentMix abstraction, Kck/KckDbg cable inputs for Accent A/B, 82-test regression suite, Hora research doc.

---

## Was this "vibe coding"?

Mostly **no**, but the failure modes were closer to vibe coding than I'd like.

The work *as a whole* was rigorous: the operator was a strong technical lead who refused to ship on guesses. They:
- Demanded I look at the autosave (ground truth) instead of speculating about wiring.
- Did their own architectural analysis with a second agent and proved on paper that the original expander-as-trigger-bus design was incompatible with same-sample triggers (citing `engine/Module.hpp:63` for the 1-sample latency contract).
- Used a second agent for code review, which caught real issues both passes (the `accentBothAmount=1.0` dead spot, the over-strong "matches 909 hardware" claim).
- Pushed back on heuristics like the hardcoded `max(amtA, amtB)`.
- Refused to tune the sound until the architecture was factored.

That's directed software engineering, not vibing.

But *my own* failure modes were vibe-adjacent in the worst stretches:
- I implemented the expander pattern from the SDK doc comment instead of reading actual working source. The doc was ambiguous, the bug was real, and I kept guessing iterations until the operator demanded I `WebSearch` for canonical examples.
- I made multiple changes at once (binary gate detection + accent-gain bump) when only one variable was being tested. The operator caught this and explicitly told me to slow down.
- I overclaimed "matches 909 hardware" twice — once in the bus header, then again in the voice config. Reviewer flagged the second occurrence.
- When the test rig wasn't producing accent, I jumped to fixes (binary detection, gain bumps) before diagnosing. The first useful debug move (throttled INFO logs) only happened after the operator said "stop guessing, diagnose."

The pattern is: when stuck, my reflex is to try plausible patches. The discipline that worked was the operator's: *evidence first, change one variable, read source not docs, run by me before each step*.

---

## What stood out about modern software engineering

A few things specific to this session that feel like the current state of practice:

**Multi-agent collaboration as a normal review process.** The operator ran a second agent in parallel — got architectural critiques (the same-sample-latency proof), code review (the `accentBothAmount` footgun), and the Roland TR-909 manual citation (`cdn.roland.com`). That review surface was as substantive as a careful human reviewer's. The PR review loop was: agent does work → second agent reviews → first agent revises → second agent re-reviews → human (operator) approves. The human stayed at the architectural-decision level the whole time.

**Empirical-first debugging in a live runtime.** VCV's autosave + log files made the engineering feedback loop tight. We could inspect "what does Rack think the current state is" at any moment. Most of the false starts were because I was reasoning about *what should be happening* instead of *reading the autosave*. The lesson generalizes: in any system with persisted state, treat that state as the ground truth and read it FIRST.

**Hardware-software literacy as a real constraint.** The TR-909 reference (Accent A vs Accent B, which voices have B per the service manual) drove real architectural decisions. Picking the right abstraction for the *thing being modeled*, not just generic clean code, materially improved the design.

**"Factor before tune" as a working discipline.** The operator explicitly delayed the sound-tuning research until the AccentMix abstraction was solid. This is the modern version of "make it work, make it right, make it fast" applied to perceptual code — get the configurability right *before* iterating on weights, or you'll be re-shaping config and code at the same time.

**The 1-sample latency lesson is durable.** Realizing that the canonical expander pattern fundamentally CANNOT do same-sample trigger interception, and that the right move was to split hit-time events (cables) from slow control state (bus), is the kind of insight that will inform the next 5+ voices added to this suite. Architecture wins that come from understanding the platform are worth the digging.

---

## What I would change

Three concrete things, ranked by how much pain they would have saved:

1. **Read source, not docs, when implementing platform mechanisms.** The Rack `engine/Module.hpp` comment block on Expander was ambiguous; a single `WebFetch` of the MindMeld MixMaster code at the start would have established the correct producer/consumer convention before I wrote any expander code. I did this *eventually* but only after multiple wrong implementations. **Heuristic: any time I'm about to copy-paste an SDK doc into code, find one production user of that API and read theirs first.**

2. **One variable per change when debugging.** The "binary gate + gain bump" episode was the operator's loudest correction in the session. The discipline is unglamorous: when the test rig isn't producing the expected behavior, change exactly one thing, observe, then change the next. This is hard for an LLM because we naturally pattern-match multiple plausible fixes at once. The fix is procedural — write down "what is the one thing I'm changing" before each edit.

3. **Diagnose before patching.** I reached for "let me try X" before "let me find out why X is happening" several times. The operator's "stop guessing, look at the autosave" is the right reflex. If I notice myself proposing a fix without having explained the failure, that's the signal to step back and instrument first.

---

## What went well

1. **The final architecture is clean.** Cables for hit-time events, bus for slow state, AccentMix as a per-voice tunable surface, three orthogonal global multipliers with no hidden combination rule — this design will absorb the rest of the 909 voice family without needing rework. It came out of multiple iterations and pushback, but it's solid.

2. **Test coverage genuinely captures the abstraction.** 82 regression tests, including orthogonality assertions that explicitly verify amtA does not leak into the B-only or both case. The reviewer's "the abstraction itself is untested beyond defaults" critique pushed this to a real bar.

3. **The Hora research artifact is durable.** `docs/modules/Hora-Drumsequencer.md` + the gotcha note in `vcvpatch/graph/specs/registry.yaml` + the memory entry will save the next agent the multi-hour debug we burned. The pattern of "when you get burned by a third-party module, write the lesson down before moving on" was right.

4. **Communication tightened over the session.** Early on I was over-explaining and proposing too much; by the end I was making focused changes and asking before bundling. The "ask before each step" discipline took hold.

5. **PR review actually worked.** Two passes, real issues caught both times, both resolved cleanly. The fact that the reviewer was another agent didn't make it ceremonial — it kept the work honest.

---

## One sentence

This was directed engineering with rough edges from my side; the architectural wins came from the operator demanding evidence and refusing heuristics, and the discipline I want to internalize is **"diagnose before patching, one variable per change, read the source not the docs."**
