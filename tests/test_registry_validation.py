from vcvpatch.graph.validate import validate_registry_specs_against_metadata


def test_registry_specs_match_metadata_for_resolved_modules():
    report = validate_registry_specs_against_metadata()
    assert report.errors == [], "\n".join(report.errors)


def test_registry_validation_reports_unresolved_modules_explicitly():
    report = validate_registry_specs_against_metadata()
    assert report.unresolved_modules
    assert "Fundamental/Split" in report.unresolved_modules
