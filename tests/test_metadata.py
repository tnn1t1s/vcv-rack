from vcvpatch.metadata import (
    input_port,
    module_metadata,
    output_port,
    param_id,
    param_name,
    param_range,
    port_name,
)


def test_module_metadata_exposes_api_names():
    meta = module_metadata("Fundamental", "VCO")
    assert meta["params"][2]["api_name"] == "Frequency"
    assert meta["inputs"][0]["api_name"] == "_1V_octave_pitch"
    assert meta["outputs"][3]["api_name"] == "Square"


def test_param_range_for_vco_frequency():
    lo, hi = param_range("Fundamental", "VCO", "Frequency")
    assert lo < 0
    assert hi > 0


def test_name_resolution_helpers():
    assert param_id("Fundamental", "VCO", "Frequency") == 2
    assert param_name("Fundamental", "VCO", 2) == "Frequency"
    assert param_name("Fundamental", "VCO", 2, api=True) == "Frequency"
    assert input_port("Fundamental", "VCO", "_1V_octave_pitch")["id"] == 0
    assert output_port("Fundamental", "VCO", "Square")["id"] == 3
    assert port_name("Fundamental", "VCO", 0, is_output=False) == "1V/octave pitch"
    assert port_name("Fundamental", "VCO", 0, is_output=False, api=True) == "_1V_octave_pitch"


def test_marbles_legacy_output_api_surface():
    meta = module_metadata("AudibleInstruments", "Marbles")
    outputs = {entry["api_name"]: entry["id"] for entry in meta["outputs"]}
    assert outputs["T2"] == 1
    assert outputs["X2"] == 5
    assert output_port("AudibleInstruments", "Marbles", "T2")["id"] == 1
    assert output_port("AudibleInstruments", "Marbles", "X2")["id"] == 5
