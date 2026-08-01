"""
Confidence Scorer
-----------------
Calculates an overall confidence score for the entire
workflow output based on individual agent scores and
judge agent results.

This score is shown to the human reviewer before
they approve the output. It gives them a quick signal
of how much to trust the AI output before reading it.

Score interpretation:
- 0.90 - 1.00: High confidence, review is a formality
- 0.75 - 0.89: Good confidence, spot check recommended
- 0.60 - 0.74: Medium confidence, careful review needed
- Below 0.60:  Low confidence, treat as draft only
"""

from dataclasses import dataclass
from typing import Optional


@dataclass
class WorkflowConfidence:
    """Overall confidence score for a completed workflow run."""
    overall_score: float
    grade: str
    agent_scores: dict
    judge_scores: dict
    flags: list
    recommendation: str


def calculate_workflow_confidence(
    validation_results: dict,
    judge_results: dict,
    workflow_state=None
) -> WorkflowConfidence:
    """
    Calculates overall workflow confidence from all agent
    validation and judge results.

    Args:
        validation_results: Dict of agent_name -> OutputValidation results
        judge_results: Dict of agent_name -> judge output dicts
        workflow_state: Current workflow state

    Returns:
        WorkflowConfidence with overall score and interpretation
    """

    agent_scores = {}
    judge_scores = {}
    flags = []

    # Collect validation confidence scores
    for agent_name, validation in validation_results.items():
        if hasattr(validation, "confidence_score"):
            agent_scores[agent_name] = validation.confidence_score
            if validation.issues:
                flags.append(f"{agent_name}: {len(validation.issues)} validation issues found")
            if hasattr(validation, "warnings") and validation.warnings:
                flags.append(f"{agent_name}: {len(validation.warnings)} warnings")

    # Collect judge confidence scores
    for agent_name, judgment in judge_results.items():
        if isinstance(judgment, dict):
            score = judgment.get("confidence_score", 0.5)
            judge_scores[agent_name] = score
            recommendation = judgment.get("recommendation", "PASS")

            if recommendation == "FAIL":
                flags.append(f"CRITICAL: Judge FAILED {agent_name} output")
                score = 0.0  # Failed judgment tanks the score

            elif recommendation == "PASS_WITH_WARNINGS":
                flags.append(f"WARNING: Judge flagged issues in {agent_name} output")

            hallucinations = judgment.get("hallucination_flags", [])
            if hallucinations:
                flags.append(
                    f"HALLUCINATION DETECTED in {agent_name}: "
                    f"{len(hallucinations)} potential fabrications found"
                )

    # Calculate overall score
    all_scores = list(agent_scores.values()) + list(judge_scores.values())

    if not all_scores:
        overall = 0.5
    else:
        # Weight judge scores more heavily than validation scores
        weighted_scores = []
        for name, score in agent_scores.items():
            weighted_scores.append(score * 0.4)  # Validation weight: 40%
        for name, score in judge_scores.items():
            weighted_scores.append(score * 0.6)  # Judge weight: 60%

        overall = sum(weighted_scores) / len(weighted_scores) if weighted_scores else 0.5

    # Apply penalties for failed agents
    if workflow_state and hasattr(workflow_state, "failed_agents"):
        penalty = len(workflow_state.failed_agents) * 0.15
        overall = max(0.0, overall - penalty)
        for agent in workflow_state.failed_agents:
            flags.append(f"AGENT FAILED: {agent} did not complete successfully")

    overall = round(overall, 2)

    # Determine grade and recommendation
    if overall >= 0.90:
        grade = "A"
        recommendation = "High confidence. Review is recommended but output is reliable."
    elif overall >= 0.75:
        grade = "B"
        recommendation = "Good confidence. Spot check key sections before approving."
    elif overall >= 0.60:
        grade = "C"
        recommendation = "Medium confidence. Careful review required before use."
    else:
        grade = "D"
        recommendation = "Low confidence. Treat as draft only. Significant review required."

    return WorkflowConfidence(
        overall_score=overall,
        grade=grade,
        agent_scores=agent_scores,
        judge_scores=judge_scores,
        flags=flags,
        recommendation=recommendation
    )


def format_confidence_display(confidence: WorkflowConfidence) -> str:
    """
    Formats confidence scores for display in terminal or dashboard.

    Args:
        confidence: WorkflowConfidence object

    Returns:
        Formatted string for display
    """
    lines = [
        f"WORKFLOW CONFIDENCE: {confidence.overall_score:.0%} (Grade {confidence.grade})",
        f"Recommendation: {confidence.recommendation}",
        ""
    ]

    if confidence.flags:
        lines.append("Flags:")
        for flag in confidence.flags:
            prefix = "  CRITICAL " if "CRITICAL" in flag else "  WARNING  " if "WARNING" in flag or "HALLUCINATION" in flag else "  INFO     "
            lines.append(f"{prefix}{flag}")
        lines.append("")

    lines.append("Agent scores:")
    for agent, score in confidence.agent_scores.items():
        bar = "#" * int(score * 10) + "-" * (10 - int(score * 10))
        lines.append(f"  {agent:<30} [{bar}] {score:.0%}")

    lines.append("")
    lines.append("Judge scores:")
    for agent, score in confidence.judge_scores.items():
        bar = "#" * int(score * 10) + "-" * (10 - int(score * 10))
        lines.append(f"  {agent:<30} [{bar}] {score:.0%}")

    return "\n".join(lines)
