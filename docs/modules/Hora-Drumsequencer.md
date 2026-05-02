# Hora-Sequencers / Drumsequencer

12-track 808-style drum sequencer (closed-source plugin; not introspectable via `rack_introspect` as of 2026-05).

**Plugin:** `Hora-Sequencers`  **Model:** `Drumsequencer`
**Verified against:** working autosave at `plugin/AgentRack/scratch/drum_machine_909_full.json`.

---

## Required cold-start baseline

A patch that instantiates Hora with empty params/data **silently sits idle**: clock pulses arrive on input 2 but no gates fire. Symptoms in the resulting autosave: `runningSeq: False`, no cursor advance.

To make Hora play on patch open, the generator MUST set:

### `data` flags

| Field          | Value to set      | Meaning                                              |
|----------------|-------------------|------------------------------------------------------|
| `gate run`     | **0** (auto-run)  | 1 means "wait for external RUN gate" — counterintuitive. |
| `runningSeq`   | **True**          | Cursor is advancing.                                 |
| `Direct Clock` | 0                 | Use internal divider; OK as-is.                      |
| `auto reset`   | 0                 | OK as-is.                                            |

### `params` baseline (38 ids must be non-zero)

```python
HORA_BASELINE_PARAMS = [
    (0,    2.0),    # mode/select
    (2,  120.0),    # BPM display
    (5,   32.0),    # step length (32 steps per pattern)
    (6,    1.0),
    (7,    2.0),
    (8,    2.0),
    # ids 111..142 are per-track default multipliers; all 1.0.
    *[(i, 1.0) for i in range(111, 143)],
]
```

Cribbed verbatim from `plugin/AgentRack/scratch/drum_machine_909_full.json`. A fresh `createModule()` does NOT auto-populate these — they are values set in the GUI on first interaction.

Reference implementation: `plugin/AgentRack/scratch/build_kck_local_accent_test.py` (`HORA_BASELINE_PARAMS` constant + `hora_data()` function).

---

## Gate programming

Gates are stored in `data["gates<track>P<pattern>"]` arrays of 32 booleans.

- Track index: 1..12.
- Pattern index: 1..12 (P1..P12).
- Step index: 0..31 within the array (step 1 = index 0).

Example: 4-on-the-floor on track 1, pattern 1:

```python
gates_t1 = [0] * 32
for i in (0, 4, 8, 12):
    gates_t1[i] = 1
data["gates1P1"] = gates_t1
```

---

## Per-step CV / velocity / probability

Three per-step parallel arrays in `data`, keyed by step and track:

| Key prefix         | Range  | Default | Meaning                                              |
|--------------------|--------|---------|------------------------------------------------------|
| `CV_out_level S_T` | 0..10  | 0       | Per-step CV value emitted on Hora's shared CV output. **Single shared lane**, NOT per-voice velocity riding on each gate output. |
| `ratchet_level S_T`| 0..N   | 0       | Per-step retrigger count.                            |
| `proba_level S_T`  | 0..1   | 1.0     | Per-step probability.                                |

Format: `<prefix> <step>_<track>` where step is 1..32 and track is 1..13. (Yes, 13 — the second slot ranges past the 12 visible tracks.)

**Important:** `CV_out_level` is a single shared CV-out lane; it is NOT per-voice velocity. This is empirically confirmed (issue #73 probe). It is well-suited to drive Total Accent (one global signal) but cannot be used as per-voice local accent.

---

## Ports

From `vcvpatch/graph/specs/registry.yaml` and probe observations:

| Output | Role                                                         |
|--------|--------------------------------------------------------------|
| 0..3   | Possibly clock-thru / accent / reset / EOC; not fully verified. |
| 4..15  | Track gate outputs. Track N → out N+3. (Track 1 = out 4, Track 2 = out 5, etc.) |

| Input | Role                          |
|-------|-------------------------------|
| 2     | CLOCK input. Required for proof. |

---

## Lesson

When adding Hora to any new patch, **crib from a known-working autosave**. Do not invent a minimal Hora dict from scratch — even if the cables look right and the gate arrays are correct, missing baseline params or wrong `gate run` semantics produce a silently-idle sequencer with no error indication. This was a multi-hour debug.
