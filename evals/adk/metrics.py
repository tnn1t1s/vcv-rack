"""Custom ADK eval metrics for repo-specific patch validation."""

from __future__ import annotations

import re
from pathlib import Path

from google.adk.evaluation.eval_case import ConversationScenario
from google.adk.evaluation.eval_case import Invocation
from google.adk.evaluation.eval_metrics import EvalMetric
from google.adk.evaluation.evaluator import EvaluationResult
from google.adk.evaluation.evaluator import EvalStatus
from google.adk.evaluation.evaluator import PerInvocationResult

from evals.patch_checks import assert_cm_chord_seq_patch
from evals.patch_checks import assert_simple_crinkle_ladder_patch
from evals.patch_checks import assert_simple_square_vcf_patch
from vcvpatch.serialize import load_vcv


_OUTPUT_PATH_RE = re.compile(r"\bsave(?:d)?\s+to:?\s+(`?)(\S+)\1", re.IGNORECASE)


def _extract_output_path(invocation: Invocation) -> Path:
    text = "\n".join(
        part.text for part in invocation.user_content.parts if getattr(part, "text", None)
    )
    match = _OUTPUT_PATH_RE.search(text)
    if not match:
        raise AssertionError("Prompt does not include a 'Save to <path>' clause.")
    return Path(match.group(2))


def _output_path_from_invocations(
    actual: Invocation, expected: Invocation | None
) -> Path:
    """Prefer the expected prompt path; fall back to the actual invocation."""
    if expected is not None:
        try:
            return _extract_output_path(expected)
        except AssertionError:
            pass
    return _extract_output_path(actual)


def cm_chord_seq_patch_metric(
    eval_metric: EvalMetric,
    actual_invocations: list[Invocation],
    expected_invocations: list[Invocation] | None,
    conversation_scenario: ConversationScenario | None = None,
) -> EvaluationResult:
    """Validate that the patch-builder produced the expected Cm chord patch."""
    del eval_metric, conversation_scenario

    expected = expected_invocations[0] if expected_invocations else None
    actual = actual_invocations[0]
    score = 0.0
    status = EvalStatus.FAILED
    try:
        output_path = _output_path_from_invocations(actual, expected)
        assert output_path.exists(), f"Patch file was not written: {output_path}"
        patch_dict = load_vcv(output_path)
        assert_cm_chord_seq_patch(patch_dict)
        score = 1.0
        status = EvalStatus.PASSED
    except AssertionError:
        score = 0.0
        status = EvalStatus.FAILED

    per_invocation_results = [
        PerInvocationResult(
            actual_invocation=invocation,
            expected_invocation=expected_invocations[index]
            if expected_invocations and index < len(expected_invocations)
            else None,
            score=score,
            eval_status=status,
        )
        for index, invocation in enumerate(actual_invocations)
    ]

    overall_score = score
    overall_status = EvalStatus.PASSED if overall_score >= 1.0 else EvalStatus.FAILED
    return EvaluationResult(
        overall_score=overall_score,
        overall_eval_status=overall_status,
        per_invocation_results=per_invocation_results,
    )


def simple_square_vcf_patch_metric(
    eval_metric: EvalMetric,
    actual_invocations: list[Invocation],
    expected_invocations: list[Invocation] | None,
    conversation_scenario: ConversationScenario | None = None,
) -> EvaluationResult:
    """Validate that the patch-builder produced a minimal VCO->VCF->Audio patch."""
    del eval_metric, conversation_scenario

    expected = expected_invocations[0] if expected_invocations else None
    actual = actual_invocations[0]
    score = 0.0
    status = EvalStatus.FAILED
    try:
        output_path = _output_path_from_invocations(actual, expected)
        assert output_path.exists(), f"Patch file was not written: {output_path}"
        patch_dict = load_vcv(output_path)
        assert_simple_square_vcf_patch(patch_dict)
        score = 1.0
        status = EvalStatus.PASSED
    except AssertionError:
        score = 0.0
        status = EvalStatus.FAILED

    per_invocation_results = [
        PerInvocationResult(
            actual_invocation=invocation,
            expected_invocation=expected_invocations[index]
            if expected_invocations and index < len(expected_invocations)
            else None,
            score=score,
            eval_status=status,
        )
        for index, invocation in enumerate(actual_invocations)
    ]

    overall_score = score
    overall_status = EvalStatus.PASSED if overall_score >= 1.0 else EvalStatus.FAILED
    return EvaluationResult(
        overall_score=overall_score,
        overall_eval_status=overall_status,
        per_invocation_results=per_invocation_results,
    )


def simple_crinkle_ladder_patch_metric(
    eval_metric: EvalMetric,
    actual_invocations: list[Invocation],
    expected_invocations: list[Invocation] | None,
    conversation_scenario: ConversationScenario | None = None,
) -> EvaluationResult:
    """Validate that the patch-builder produced a minimal Crinkle->Ladder->Audio patch."""
    del eval_metric, conversation_scenario

    expected = expected_invocations[0] if expected_invocations else None
    actual = actual_invocations[0]
    score = 0.0
    status = EvalStatus.FAILED
    try:
        output_path = _output_path_from_invocations(actual, expected)
        assert output_path.exists(), f"Patch file was not written: {output_path}"
        patch_dict = load_vcv(output_path)
        assert_simple_crinkle_ladder_patch(patch_dict)
        score = 1.0
        status = EvalStatus.PASSED
    except AssertionError:
        score = 0.0
        status = EvalStatus.FAILED

    per_invocation_results = [
        PerInvocationResult(
            actual_invocation=invocation,
            expected_invocation=expected_invocations[index]
            if expected_invocations and index < len(expected_invocations)
            else None,
            score=score,
            eval_status=status,
        )
        for index, invocation in enumerate(actual_invocations)
    ]

    overall_score = score
    overall_status = EvalStatus.PASSED if overall_score >= 1.0 else EvalStatus.FAILED
    return EvaluationResult(
        overall_score=overall_score,
        overall_eval_status=overall_status,
        per_invocation_results=per_invocation_results,
    )
