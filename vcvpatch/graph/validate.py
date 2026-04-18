from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path

import yaml

from ..metadata import module_metadata


_REGISTRY_PATH = Path(__file__).parent / "specs" / "registry.yaml"


@dataclass
class RegistryValidationReport:
    errors: list[str] = field(default_factory=list)
    unresolved_modules: list[str] = field(default_factory=list)


def validate_registry_specs_against_metadata() -> RegistryValidationReport:
    """
    Validate metadata-backed registry specs against discovered/explicit metadata.

    Modules without local metadata are reported separately so product-truth work
    can track coverage independently from cross-reference correctness.
    """
    payload = yaml.safe_load(_REGISTRY_PATH.read_text()) or {}
    report = RegistryValidationReport()

    for raw in payload.get("modules", []):
        plugin = raw["plugin"]
        model = raw["model"]
        key = f"{plugin}/{model}"

        try:
            meta = module_metadata(plugin, model)
        except ValueError:
            report.unresolved_modules.append(key)
            continue

        params = {int(entry["id"]) for entry in meta.get("params", [])}
        inputs = {int(entry["id"]) for entry in meta.get("inputs", [])}
        outputs = {int(entry["id"]) for entry in meta.get("outputs", [])}

        for input_id, output_id in raw.get("routes", []):
            if int(input_id) not in inputs:
                report.errors.append(
                    f"{key}: route input {input_id} is not a discovered input id"
                )
            if int(output_id) not in outputs:
                report.errors.append(
                    f"{key}: route output {output_id} is not a discovered output id"
                )

        for input_id in raw.get("audio_inputs", []):
            if int(input_id) not in inputs:
                report.errors.append(
                    f"{key}: audio_inputs references missing input id {input_id}"
                )

        for output_id in raw.get("audio_outputs", []):
            if int(output_id) not in outputs:
                report.errors.append(
                    f"{key}: audio_outputs references missing output id {output_id}"
                )

        for output_id in (raw.get("outputs") or {}).keys():
            if int(output_id) not in outputs:
                report.errors.append(
                    f"{key}: outputs references missing output id {output_id}"
                )

        for input_id in (raw.get("required_inputs") or {}).keys():
            if int(input_id) not in inputs:
                report.errors.append(
                    f"{key}: required_inputs references missing input id {input_id}"
                )

        for input_id, param_id in (raw.get("attenuators") or {}).items():
            if int(input_id) not in inputs:
                report.errors.append(
                    f"{key}: attenuators references missing input id {input_id}"
                )
            if int(param_id) not in params:
                report.errors.append(
                    f"{key}: attenuators references missing param id {param_id}"
                )

    report.unresolved_modules.sort()
    return report
