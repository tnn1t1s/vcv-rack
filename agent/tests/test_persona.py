"""
Tests for agent/persona.py -- the build_persona_prompt function.

We test:
  - Basic identity/seniority extraction produces a system prompt string
  - work.description appears under ## Your Work
  - module_knowledge (arbitrary nested keys) is included
  - task appears under ## Your Task
  - values section appears
  - project_context string is included
  - The function returns a non-empty string for a minimal config
"""

import pytest
from pathlib import Path
import sys
import tempfile
import yaml

# Allow importing agent.persona without an installed package
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from agent.persona import build_persona_prompt


# ---------------------------------------------------------------------------
# Fixture helpers
# ---------------------------------------------------------------------------

def _write_yaml(tmp_path: Path, data: dict) -> Path:
    """Write a YAML config and return the path."""
    p = tmp_path / "config.yaml"
    p.write_text(yaml.dump(data))
    return p


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------

def test_returns_string_for_minimal_config(tmp_path):
    """A config with only a title produces a non-empty string."""
    cfg = _write_yaml(tmp_path, {"persona": {"identity": {"title": "Test Agent"}}})
    result = build_persona_prompt(cfg)
    assert isinstance(result, str)
    assert len(result) > 0


def test_identity_title_in_prompt(tmp_path):
    """The identity.title appears in the prompt."""
    cfg = _write_yaml(tmp_path, {"persona": {"identity": {"title": "Patch Wizard"}}})
    result = build_persona_prompt(cfg)
    assert "Patch Wizard" in result


def test_seniority_in_prompt(tmp_path):
    """The identity.seniority appears in the prompt."""
    cfg = _write_yaml(tmp_path, {
        "persona": {
            "identity": {
                "title": "Engineer",
                "seniority": "deeply experienced in signal flow",
            }
        }
    })
    result = build_persona_prompt(cfg)
    assert "deeply experienced in signal flow" in result


def test_work_description_in_prompt(tmp_path):
    """work.description appears under ## Your Work."""
    cfg = _write_yaml(tmp_path, {
        "persona": {
            "identity": {"title": "X"},
            "work": {"description": "Builds VCV patches from musical ideas."},
        }
    })
    result = build_persona_prompt(cfg)
    assert "## Your Work" in result
    assert "Builds VCV patches from musical ideas." in result


def test_task_in_prompt(tmp_path):
    """The task string appears under ## Your Task."""
    cfg = _write_yaml(tmp_path, {
        "persona": {
            "identity": {"title": "X"},
            "task": "Connect the oscillator to the filter.",
        }
    })
    result = build_persona_prompt(cfg)
    assert "## Your Task" in result
    assert "Connect the oscillator to the filter." in result


def test_nested_section_values_appear(tmp_path):
    """Arbitrary nested sections have their leaf string values included."""
    cfg = _write_yaml(tmp_path, {
        "persona": {
            "identity": {"title": "X"},
            "module_knowledge": {
                "Rings": "A resonator module.",
                "Clouds": "A granular processor.",
            },
        }
    })
    result = build_persona_prompt(cfg)
    assert "A resonator module." in result
    assert "A granular processor." in result


def test_values_optimizes_for_in_prompt(tmp_path):
    """The values.optimizes_for string appears in the prompt."""
    cfg = _write_yaml(tmp_path, {
        "persona": {
            "identity": {"title": "X"},
            "values": {
                "optimizes_for": "Provable patches",
                "avoids": "Magic numbers",
            },
        }
    })
    result = build_persona_prompt(cfg)
    assert "Provable patches" in result
    assert "Magic numbers" in result


def test_project_context_in_prompt(tmp_path):
    """project_context string appears in the prompt."""
    cfg = _write_yaml(tmp_path, {
        "persona": {
            "identity": {"title": "X"},
            "project_context": "This is an agentic system for building VCV patches.",
        }
    })
    result = build_persona_prompt(cfg)
    assert "This is an agentic system for building VCV patches." in result


def test_model_section_ignored(tmp_path):
    """The 'model' top-level key is not part of the persona prompt."""
    cfg = _write_yaml(tmp_path, {
        "persona": {"identity": {"title": "X"}},
        "model": {"provider": "openrouter", "name": "claude-sonnet"},
    })
    result = build_persona_prompt(cfg)
    # Model info should not leak into the prompt
    assert "openrouter" not in result
