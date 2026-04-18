"""ADK-native eval coverage for the patch-builder agent."""

from __future__ import annotations

import asyncio
import os
from pathlib import Path

import pytest
from dotenv import load_dotenv
from google.adk.evaluation.agent_evaluator import AgentEvaluator
from google.adk.evaluation.custom_metric_evaluator import _CustomMetricEvaluator
from google.adk.evaluation.eval_case import EvalCase
from google.adk.evaluation.eval_case import Invocation
from google.adk.evaluation.eval_config import CustomMetricConfig
from google.adk.evaluation.eval_config import EvalConfig
from google.adk.evaluation.eval_metrics import BaseCriterion
from google.adk.evaluation.eval_metrics import Interval
from google.adk.evaluation.eval_metrics import MetricInfo
from google.adk.evaluation.eval_metrics import MetricValueInfo
from google.adk.evaluation.eval_set import EvalSet
from google.adk.evaluation.metric_evaluator_registry import (
    DEFAULT_METRIC_EVALUATOR_REGISTRY,
)
from google.genai import types as genai_types

load_dotenv(Path(__file__).resolve().parent.parent / "agent" / ".env")


_EVAL_CASES = [
    {
        "eval_id": "simple_square_vcf",
        "metric_name": "simple_square_vcf_patch",
        "metric_function": "evals.adk.metrics.simple_square_vcf_patch_metric",
        "description": "Patch exists and matches the minimal VCO->VCF->Audio structure.",
        "output_filename": "simple_square_vcf_adk_eval.vcv",
        "prompt_template": (
            "Create a minimal proven patch with Fundamental/VCO square output into "
            "Fundamental/VCF, then to Core/AudioInterface2 stereo out. "
            "Use explicit layout and save to {output_path}"
        ),
    },
    {
        "eval_id": "simple_crinkle_ladder",
        "metric_name": "simple_crinkle_ladder_patch",
        "metric_function": "evals.adk.metrics.simple_crinkle_ladder_patch_metric",
        "description": "Patch exists and matches the minimal Crinkle->Ladder->Audio structure.",
        "output_filename": "simple_crinkle_ladder_adk_eval.vcv",
        "prompt_template": (
            "Create a minimal proven patch with AgentRack/Crinkle into AgentRack/Ladder, "
            "then to Core/AudioInterface2 stereo out. Use explicit layout and save to {output_path}"
        ),
    },
]


def _register_repo_metric(metric_name: str, description: str) -> None:
    DEFAULT_METRIC_EVALUATOR_REGISTRY.register_evaluator(
        metric_info=MetricInfo(
            metric_name=metric_name,
            description=description,
            metric_value_info=MetricValueInfo(
                interval=Interval(min_value=0.0, max_value=1.0)
            ),
        ),
        evaluator=_CustomMetricEvaluator,
    )


@pytest.mark.eval
@pytest.mark.parametrize("case", _EVAL_CASES, ids=[case["eval_id"] for case in _EVAL_CASES])
def test_patch_builder_adk_eval_cases(tmp_path, case):
    """Run repo-native ADK evals for simple patch-builder baselines."""
    if not os.environ.get("OPENROUTER_API_KEY"):
        pytest.skip("OPENROUTER_API_KEY not set")

    output_path = tmp_path / case["output_filename"]
    prompt = case["prompt_template"].format(output_path=output_path)
    _register_repo_metric(case["metric_name"], case["description"])

    eval_set = EvalSet(
        eval_set_id=case["eval_id"],
        name=case["eval_id"],
        eval_cases=[
            EvalCase(
                eval_id=case["eval_id"],
                conversation=[
                    Invocation(
                        invocation_id=f"{case['eval_id']}_1",
                        user_content=genai_types.Content(
                            role="user",
                            parts=[genai_types.Part.from_text(text=prompt)],
                        ),
                    )
                ],
            )
        ],
    )

    eval_config = EvalConfig(
        criteria={case["metric_name"]: BaseCriterion(threshold=1.0)},
        custom_metrics={
            case["metric_name"]: CustomMetricConfig(
                code_config={"name": case["metric_function"]},
                description=case["description"],
            )
        },
    )

    asyncio.run(
        AgentEvaluator.evaluate_eval_set(
            agent_module="agent.patch_builder.agent",
            eval_set=eval_set,
            eval_config=eval_config,
            num_runs=1,
            agent_name=None,
            print_detailed_results=True,
        )
    )

    assert output_path.exists(), "ADK eval did not leave the expected patch artifact."
