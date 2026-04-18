"""
End-to-end test for MIDI-based runtime param control.

What this tests:
  1. Build a minimal proven patch with Core/MidiMap configured for our virtual port
  2. Launch Rack headlessly
  3. Send a MIDI CC to change a param
  4. Read back via autosave and confirm the value changed

Run with:
  uv run python -m tests.test_runtime_midi
"""

import math
import time

from vcvpatch.builder import PatchBuilder
from vcvpatch.metadata import param_id
from vcvpatch.runtime import RackSession, MidiMapBuilder


def build_test_patch(path: str) -> tuple[int, int]:
    """
    Build a minimal patch: VCO -> AudioInterface2, with MidiMap controlling VCO FREQ.

    Returns (vco_module_id, freq_param_id).
    """
    pb = PatchBuilder()
    vco   = pb.module("Fundamental", "VCO", position=[0, 0], Frequency=0.0)
    audio = pb.module("Core", "AudioInterface2", position=[12, 0])
    pb.chain(vco.o.Sawtooth, audio.i.Left_input)
    pb.chain(vco.o.Sawtooth, audio.i.Right_input)
    assert pb.proven, f"Patch not proven: {pb.report()}"

    vco_id = vco._module.id
    freq_param_id = param_id("Fundamental", "VCO", "Frequency")

    mmb = MidiMapBuilder()
    mmb.map(cc=1, module_id=vco_id, param_id=freq_param_id)

    # Inject MidiMap into the patch
    pb._patch.add("Core", "MidiMap", extra_data=mmb.build())
    pb.save(path)

    print(f"Patch saved: {path}")
    print(f"  VCO module id:  {vco_id}")
    print(f"  FREQ param id:  {freq_param_id}")
    print(f"  MidiMap config: {mmb.build()['midi']}")

    return vco_id, freq_param_id


def run():
    patch_path = "/tmp/test_runtime_midi.vcv"

    vco_id, freq_param_id = build_test_patch(patch_path)

    from vcvpatch.runtime import MidiMapSpec

    specs = [MidiMapSpec(
        cc=1,
        module_id=vco_id,
        param_id=freq_param_id,
        min_val=-2.0,
        max_val=2.0,
    )]

    print("\nLaunching Rack headlessly...")
    with RackSession(patch_path, specs) as sess:
        sess.launch(timeout=20.0)
        print(f"Rack ready (pid {sess._proc.pid})")

        # Read initial value
        initial = sess.read_param(vco_id, freq_param_id)
        print(f"\nInitial FREQ param: {initial}  ({20 * 2**initial:.1f} Hz)" if initial is not None else "\nInitial FREQ: not found in autosave")

        # Set to 1.0 (= 40 Hz: 20 * 2^1 = 40 Hz)
        target = 1.0
        print(f"\nSending CC1 -> FREQ = {target}  ({20 * 2**target:.1f} Hz)")
        sess.set_param(vco_id, freq_param_id, target, min_val=-2.0, max_val=2.0)

        # Wait for autosave to reflect the change (Rack saves every ~15s by default,
        # but param changes from MIDI may appear sooner via live state)
        print("Waiting 16s for autosave to update...")
        time.sleep(16)

        after = sess.read_param(vco_id, freq_param_id)
        print(f"FREQ param after CC: {after}" + (f"  ({20 * 2**after:.1f} Hz)" if after is not None else ""))

        if after is not None and abs(after - target) < 0.1:
            print("\nPASS: param changed via MIDI CC")
        else:
            print(f"\nFAIL: expected ~{target}, got {after}")
            print("  (If MIDI device didn't connect, check MidiMap driver/deviceName in patch)")


if __name__ == "__main__":
    run()
