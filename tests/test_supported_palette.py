from vcvpatch import supported_module, supported_modules


def test_supported_palette_contains_metadata_backed_semantic_modules():
    keys = {(module.plugin, module.model) for module in supported_modules()}
    assert ("AgentRack", "Ladder") in keys
    assert ("Fundamental", "VCO") in keys


def test_supported_palette_includes_registry_entries_once_surface_exists():
    keys = {(module.plugin, module.model) for module in supported_modules()}
    assert ("Fundamental", "Split") in keys


def test_supported_module_exposes_surface_and_semantics():
    ladder = supported_module("AgentRack", "Ladder")
    assert ladder.semantics.kind == "audio_processor"
    assert ladder.semantics.routes == ((0, 0),)
    assert ladder.inputs[0].api_name == "Audio"
    assert ladder.outputs[0].api_name == "Out"


def test_supported_palette_includes_befaco_slew_limiter():
    keys = {(module.plugin, module.model) for module in supported_modules()}
    assert ("Befaco", "SlewLimiter") in keys


def test_supported_module_exposes_befaco_slew_limiter_as_controller():
    slew = supported_module("Befaco", "SlewLimiter")
    assert slew.semantics.kind == "controller"
    assert slew.outputs[0].api_name == "Out"
    assert slew.outputs[0].signal_type == "cv"
    assert [entry.api_name for entry in slew.inputs] == ["Rise_CV", "Fall_CV", "In"]
