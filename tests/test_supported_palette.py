from vcvpatch import supported_module, supported_modules


def test_supported_palette_contains_metadata_backed_semantic_modules():
    keys = {(module.plugin, module.model) for module in supported_modules()}
    assert ("AgentRack", "Ladder") in keys
    assert ("Fundamental", "VCO") in keys


def test_supported_palette_excludes_registry_entries_without_local_surface():
    keys = {(module.plugin, module.model) for module in supported_modules()}
    assert ("Fundamental", "Split") not in keys


def test_supported_module_exposes_surface_and_semantics():
    ladder = supported_module("AgentRack", "Ladder")
    assert ladder.semantics.kind == "audio_processor"
    assert ladder.semantics.routes == ((0, 0),)
    assert ladder.inputs[0].api_name == "Audio"
    assert ladder.outputs[0].api_name == "Out"
