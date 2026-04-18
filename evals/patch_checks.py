"""Shared structural checks for built VCV patches."""

from __future__ import annotations

from typing import Any


def models(patch_dict: dict[str, Any]) -> dict[str, dict[str, Any]]:
    """Return {model_slug: module_dict} for every module in the patch."""
    return {m["model"]: m for m in patch_dict["modules"]}


def cables(patch_dict: dict[str, Any]) -> list[dict[str, Any]]:
    return patch_dict.get("cables", [])


def ports_into(patch_dict: dict[str, Any], model: str) -> set[int]:
    """Return the set of inputId values for cables arriving at the named model."""
    mods = models(patch_dict)
    if model not in mods:
        return set()
    target_id = mods[model]["id"]
    return {c["inputId"] for c in cables(patch_dict) if c["inputModuleId"] == target_id}


def src_models_into(patch_dict: dict[str, Any], dst_model: str) -> set[str]:
    """Return the set of source model slugs for cables landing on dst_model."""
    mods = models(patch_dict)
    if dst_model not in mods:
        return set()
    target_id = mods[dst_model]["id"]
    id_to_model = {m["id"]: m["model"] for m in patch_dict["modules"]}
    return {
        id_to_model[c["outputModuleId"]]
        for c in cables(patch_dict)
        if c["inputModuleId"] == target_id and c["outputModuleId"] in id_to_model
    }


def assert_cm_chord_seq_patch(patch_dict: dict[str, Any]) -> None:
    """Validate the canonical Cm chord sequencer patch structure."""
    required_models = [
        "Clocked-Clkd",
        "SEQ3",
        "ChordCV",
        "VCO",
        "Bogaudio-Mix4",
        "VCA",
        "ADSR",
        "Chronoblob2",
        "AudioInterface2",
    ]

    present = {m["model"] for m in patch_dict["modules"]}
    for model in required_models:
        assert model in present, f"Missing module: {model}"

    vcos = [m for m in patch_dict["modules"] if m["model"] == "VCO"]
    assert len(vcos) == 3, f"Expected 3 VCOs, got {len(vcos)}"

    mix4_audio_inputs = {2, 5, 8, 11}
    mix4_ports = ports_into(patch_dict, "Bogaudio-Mix4")
    assert len(mix4_ports & mix4_audio_inputs) >= 3, (
        "Expected at least 3 VCOs on Mix4 audio inputs, "
        f"but cables arrived at ports {mix4_ports}"
    )

    assert "Clocked-Clkd" in src_models_into(patch_dict, "SEQ3")
    assert "SEQ3" in src_models_into(patch_dict, "ChordCV")
    assert "ChordCV" in src_models_into(patch_dict, "VCO")
    assert "SEQ3" in src_models_into(patch_dict, "ADSR")
    assert "Bogaudio-Mix4" in src_models_into(patch_dict, "VCA")
    assert "ADSR" in src_models_into(patch_dict, "VCA")
    assert "VCA" in src_models_into(patch_dict, "Chronoblob2")
    assert "Chronoblob2" in src_models_into(patch_dict, "AudioInterface2")

    assert "modules" in patch_dict
    assert "cables" in patch_dict
    assert len(patch_dict["modules"]) >= 9
    assert len(patch_dict["cables"]) >= 8


def assert_simple_square_vcf_patch(patch_dict: dict[str, Any]) -> None:
    """Validate a minimal square-oscillator into VCF into audio-out patch."""
    required_models = ["VCO", "VCF", "AudioInterface2"]
    present = {m["model"] for m in patch_dict["modules"]}
    for model in required_models:
        assert model in present, f"Missing module: {model}"

    assert "VCO" in src_models_into(patch_dict, "VCF")
    assert "VCF" in src_models_into(patch_dict, "AudioInterface2")
    assert len(patch_dict["modules"]) >= 3
    assert len(patch_dict["cables"]) >= 3


def assert_simple_crinkle_ladder_patch(patch_dict: dict[str, Any]) -> None:
    """Validate a minimal AgentRack Crinkle -> Ladder -> Audio patch."""
    required_models = ["Crinkle", "Ladder", "AudioInterface2"]
    present = {m["model"] for m in patch_dict["modules"]}
    for model in required_models:
        assert model in present, f"Missing module: {model}"

    assert "Crinkle" in src_models_into(patch_dict, "Ladder")
    assert "Ladder" in src_models_into(patch_dict, "AudioInterface2")
    assert len(patch_dict["modules"]) >= 3
    assert len(patch_dict["cables"]) >= 3
