from agent.tools.module_surface import inspect_module_surface


def test_describe_module_surface_returns_exact_vcf_api():
    result = inspect_module_surface("Fundamental", "VCF")
    assert result["status"] == "success"
    assert result["kind"] == "audio_processor"

    params = {entry["api_name"]: entry for entry in result["params"]}
    inputs = {entry["api_name"]: entry for entry in result["inputs"]}
    outputs = {entry["api_name"]: entry for entry in result["outputs"]}

    assert "Cutoff_frequency" in params
    assert "Audio" in inputs
    assert "LPF" in outputs
    assert "HPF" in outputs
    assert outputs["LPF"]["signal_type"] == "audio"
    assert outputs["HPF"]["signal_type"] == "audio"
    assert result["routes"] == [[3, 0], [3, 1]]


def test_describe_module_surface_exposes_required_inputs_and_attenuators():
    result = inspect_module_surface("Fundamental", "VCF")
    assert result["status"] == "success"
    assert result["required_inputs"] == []
    assert {
        "input_id": 0,
        "input_api_name": "Frequency",
        "param_id": 3,
    } in result["attenuators"]


def test_describe_module_surface_reports_unknown_module():
    result = inspect_module_surface("Nope", "Missing")
    assert result["status"] == "error"
    assert "not found" in result["message"].lower()



def test_describe_module_surface_reports_befaco_slew_limiter_as_cv_controller():
    result = inspect_module_surface("Befaco", "SlewLimiter")
    assert result["status"] == "success"
    assert result["kind"] == "controller"

    params = {entry["api_name"]: entry for entry in result["params"]}
    inputs = {entry["api_name"]: entry for entry in result["inputs"]}
    outputs = {entry["api_name"]: entry for entry in result["outputs"]}

    assert "Shape" in params
    assert "Rise_time" in params
    assert "Fall_time" in params
    assert "In" in inputs
    assert "Out" in outputs
    assert outputs["Out"]["signal_type"] == "cv"
