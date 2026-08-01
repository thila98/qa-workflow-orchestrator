"""
QA Workflow Orchestrator - Main Entry Point
-------------------------------------------
This is the conductor of the entire multi-agent system.
It coordinates all agents, runs the Judge Agent after each one,
tracks costs and safety limits, and manages the human review gate.

Workflow sequence:
1. Validate input
2. Agent 1: Requirements Analyst -> Judge validates output
3. Agent 2: Risk Assessor -> Judge validates output
4. Agent 3: Test Strategist -> Judge validates output
5. Agent 4: Test Case Writer -> Judge validates output
6. Agent 5: Coverage Analyser (optional) -> Judge validates output
7. HUMAN REVIEW GATE - workflow pauses here
8. Agent 6: Report Writer -> Final output

Problems this solves:
- Coordinates all agents in the right order
- Ensures Judge runs after every agent
- Manages workflow state across all agents
- Handles failures gracefully with clear error messages
- Tracks cost across the entire workflow
- Enforces the mandatory human review gate
"""

import os
import json
import time
import uuid
from datetime import datetime
from dotenv import load_dotenv
from rich.console import Console
from rich.panel import Panel
from rich.progress import Progress, SpinnerColumn, TextColumn
from rich import print as rprint

from validation.input_validator import validate_input
from validation.output_validator import (
    validate_requirements_analysis,
    validate_risk_assessment,
    validate_test_strategy,
    validate_test_cases,
    validate_coverage_analysis
)
from validation.guardrails import (
    WorkflowState,
    CircuitBreaker,
    create_workflow_state,
    CostLimitExceeded,
    RetryLimitExceeded,
    AgentTimeout,
    InputValidationError
)
from agents.requirements_analyst import analyse_requirements
from agents.risk_assessor import assess_risks
from agents.test_strategist import create_test_strategy
from agents.test_case_writer import write_test_cases
from agents.judge_agent import judge_output
from tools.confidence_scorer import calculate_workflow_confidence, format_confidence_display

load_dotenv()

console = Console()


def run_agent_with_judge(
    agent_name: str,
    agent_func,
    agent_args: dict,
    validate_func,
    original_input: str,
    previous_outputs: dict,
    workflow_state: WorkflowState,
    circuit_breaker: CircuitBreaker
) -> dict:
    """
    Runs a single agent and immediately validates with the Judge Agent.
    This is the core pattern that prevents hallucination propagation.

    Args:
        agent_name: Display name of the agent
        agent_func: The agent function to call
        agent_args: Arguments to pass to the agent
        validate_func: The output validation function for this agent
        original_input: Original requirement text
        previous_outputs: All previous agent outputs for consistency checking
        workflow_state: Current workflow state
        circuit_breaker: Safety controls

    Returns:
        Validated agent output dict
    """

    console.print(f"
[bold cyan]Running {agent_name}...[/bold cyan]")
    start_time = time.time()

    # Run the agent
    output = agent_func(**agent_args)
    elapsed = time.time() - start_time

    console.print(f"[green]  {agent_name} completed in {elapsed:.1f}s[/green]")

    # Validate output structure
    validation = validate_func(output)

    if not validation.is_valid:
        console.print(f"[red]  Output validation FAILED:[/red]")
        for issue in validation.issues:
            console.print(f"[red]    - {issue}[/red]")
        raise ValueError(f"{agent_name} output failed validation: {validation.issues}")

    if validation.warnings:
        console.print(f"[yellow]  Warnings:[/yellow]")
        for warning in validation.warnings:
            console.print(f"[yellow]    - {warning}[/yellow]")

    console.print(f"[cyan]  Running Judge Agent validation...[/cyan]")

    # Run Judge Agent independently
    judgment = judge_output(
        agent_name=agent_name,
        original_input=original_input,
        agent_output=output,
        previous_outputs=previous_outputs
    )

    recommendation = judgment.get("recommendation", "PASS")

    if recommendation == "FAIL":
        console.print(f"[red]  Judge Agent FAILED this output[/red]")
        for flag in judgment.get("hallucination_flags", []):
            console.print(f"[red]    HALLUCINATION: {flag}[/red]")
        for issue in judgment.get("quality_issues", []):
            console.print(f"[red]    ISSUE: {issue}[/red]")
        raise ValueError(
            f"Judge Agent rejected {agent_name} output. "
            f"Reason: {judgment.get('recommendation_reason', 'Unknown')}"
        )

    elif recommendation == "PASS_WITH_WARNINGS":
        console.print(f"[yellow]  Judge Agent: PASS WITH WARNINGS[/yellow]")
        for issue in judgment.get("quality_issues", []):
            console.print(f"[yellow]    - {issue}[/yellow]")
    else:
        console.print(
            f"[green]  Judge Agent: PASS "
            f"(confidence: {judgment.get('confidence_score', 0):.0%})[/green]"
        )

    return output, validation, judgment


def run_workflow(
    requirement: str,
    existing_test_suite_path: str = None
) -> dict:
    """
    Runs the complete QA workflow orchestration.

    Args:
        requirement: The feature requirement to generate a QA plan for
        existing_test_suite_path: Optional path to existing test suite CSV

    Returns:
        Complete workflow results including all agent outputs
    """

    session_id = str(uuid.uuid4())[:8].upper()
    workflow_state = create_workflow_state(session_id)
    circuit_breaker = CircuitBreaker(workflow_state)

    console.print(Panel(
        f"[bold]QA Workflow Orchestrator[/bold]
"
        f"Session: {session_id}
"
        f"Cost limit: ${workflow_state.max_cost_usd:.2f}
"
        f"Started: {datetime.now().strftime('%H:%M:%S')}",
        title="Starting Workflow",
        border_style="cyan"
    ))

    # Storage for all outputs and validation results
    all_outputs = {}
    validation_results = {}
    judge_results = {}

    try:
        # ── Step 0: Validate Input ─────────────────────────────────────

        console.print("
[bold]Step 0: Validating input...[/bold]")
        input_validation = validate_input(requirement)

        if not input_validation.is_valid:
            raise InputValidationError(input_validation.error_message)

        if input_validation.warnings:
            for warning in input_validation.warnings:
                console.print(f"[yellow]  Warning: {warning}[/yellow]")

        cleaned_requirement = input_validation.cleaned_input
        console.print(f"[green]  Input validated ({len(cleaned_requirement)} characters)[/green]")

        # ── Step 1: Requirements Analyst ───────────────────────────────

        req_output, req_validation, req_judgment = run_agent_with_judge(
            agent_name="Requirements Analyst",
            agent_func=analyse_requirements,
            agent_args={
                "requirement": cleaned_requirement,
                "workflow_state": workflow_state,
                "circuit_breaker": circuit_breaker
            },
            validate_func=validate_requirements_analysis,
            original_input=cleaned_requirement,
            previous_outputs={},
            workflow_state=workflow_state,
            circuit_breaker=circuit_breaker
        )

        all_outputs["requirements_analysis"] = req_output
        validation_results["Requirements Analyst"] = req_validation
        judge_results["Requirements Analyst"] = req_judgment

        # If needs clarification, warn but continue
        if req_output.get("needs_clarification"):
            console.print(
                "[yellow]  NOTE: Requirements Analyst flagged that clarification "
                "is needed before full testing can begin.[/yellow]"
            )

        # ── Step 2: Risk Assessor ──────────────────────────────────────

        risk_output, risk_validation, risk_judgment = run_agent_with_judge(
            agent_name="Risk Assessor",
            agent_func=assess_risks,
            agent_args={
                "requirement": cleaned_requirement,
                "requirements_analysis": req_output,
                "workflow_state": workflow_state,
                "circuit_breaker": circuit_breaker
            },
            validate_func=validate_risk_assessment,
            original_input=cleaned_requirement,
            previous_outputs={"requirements_analysis": req_output},
            workflow_state=workflow_state,
            circuit_breaker=circuit_breaker
        )

        all_outputs["risk_assessment"] = risk_output
        validation_results["Risk Assessor"] = risk_validation
        judge_results["Risk Assessor"] = risk_judgment

        # ── Step 3: Test Strategist ────────────────────────────────────

        strategy_output, strategy_validation, strategy_judgment = run_agent_with_judge(
            agent_name="Test Strategist",
            agent_func=create_test_strategy,
            agent_args={
                "requirement": cleaned_requirement,
                "requirements_analysis": req_output,
                "risk_assessment": risk_output,
                "workflow_state": workflow_state,
                "circuit_breaker": circuit_breaker
            },
            validate_func=validate_test_strategy,
            original_input=cleaned_requirement,
            previous_outputs={
                "requirements_analysis": req_output,
                "risk_assessment": risk_output
            },
            workflow_state=workflow_state,
            circuit_breaker=circuit_breaker
        )

        all_outputs["test_strategy"] = strategy_output
        validation_results["Test Strategist"] = strategy_validation
        judge_results["Test Strategist"] = strategy_judgment

        # ── Step 4: Test Case Writer ───────────────────────────────────

        test_cases_output, tc_validation, tc_judgment = run_agent_with_judge(
            agent_name="Test Case Writer",
            agent_func=write_test_cases,
            agent_args={
                "requirement": cleaned_requirement,
                "requirements_analysis": req_output,
                "risk_assessment": risk_output,
                "test_strategy": strategy_output,
                "workflow_state": workflow_state,
                "circuit_breaker": circuit_breaker
            },
            validate_func=validate_test_cases,
            original_input=cleaned_requirement,
            previous_outputs={
                "requirements_analysis": req_output,
                "risk_assessment": risk_output,
                "test_strategy": strategy_output
            },
            workflow_state=workflow_state,
            circuit_breaker=circuit_breaker
        )

        all_outputs["test_cases"] = test_cases_output
        validation_results["Test Case Writer"] = tc_validation
        judge_results["Test Case Writer"] = tc_judgment

        console.print(
            f"
[green]  Generated {test_cases_output.get('total_count', 0)} "
            f"test cases[/green]"
        )

        # ── Step 5: Coverage Analyser (Optional) ──────────────────────

        coverage_output = None
        if existing_test_suite_path:
            console.print(f"
[bold]Step 5: Running Coverage Analyser...[/bold]")
            console.print(f"  Comparing against: {existing_test_suite_path}")

            from agents.coverage_analyser import analyse_coverage
            cov_output, cov_validation, cov_judgment = run_agent_with_judge(
                agent_name="Coverage Analyser",
                agent_func=analyse_coverage,
                agent_args={
                    "requirement": cleaned_requirement,
                    "test_cases_output": test_cases_output,
                    "existing_suite_path": existing_test_suite_path,
                    "workflow_state": workflow_state,
                    "circuit_breaker": circuit_breaker
                },
                validate_func=validate_coverage_analysis,
                original_input=cleaned_requirement,
                previous_outputs=all_outputs,
                workflow_state=workflow_state,
                circuit_breaker=circuit_breaker
            )

            coverage_output = cov_output
            all_outputs["coverage_analysis"] = cov_output
            validation_results["Coverage Analyser"] = cov_validation
            judge_results["Coverage Analyser"] = cov_judgment
        else:
            console.print(
                "
[dim]Step 5: Coverage Analyser skipped "
                "(no existing test suite provided)[/dim]"
            )

        # ── Calculate Confidence Score ─────────────────────────────────

        confidence = calculate_workflow_confidence(
            validation_results=validation_results,
            judge_results=judge_results,
            workflow_state=workflow_state
        )

        # ── Human Review Gate ──────────────────────────────────────────

        console.print("
" + "=" * 60)
        console.print(Panel(
            f"[bold yellow]HUMAN REVIEW GATE[/bold yellow]

"
            f"{format_confidence_display(confidence)}

"
            f"Total API cost so far: ${workflow_state.total_cost_usd:.4f}

"
            f"Please review the outputs above before proceeding.
"
            f"The final report will only be generated after your approval.",
            title="Review Required",
            border_style="yellow"
        ))

        # Return everything for the human review step
        return {
            "session_id": session_id,
            "status": "awaiting_review",
            "requirement": cleaned_requirement,
            "outputs": all_outputs,
            "confidence": {
                "score": confidence.overall_score,
                "grade": confidence.grade,
                "recommendation": confidence.recommendation,
                "flags": confidence.flags
            },
            "workflow_state": {
                "completed_agents": workflow_state.completed_agents,
                "failed_agents": workflow_state.failed_agents,
                "total_cost_usd": workflow_state.total_cost_usd,
                "warnings": workflow_state.warnings
            },
            "validation_results": {
                name: {
                    "is_valid": v.is_valid,
                    "confidence": v.confidence_score,
                    "issues": v.issues,
                    "warnings": v.warnings if hasattr(v, "warnings") else []
                }
                for name, v in validation_results.items()
            },
            "judge_results": judge_results
        }

    except InputValidationError as e:
        console.print(f"
[red]Input Error: {str(e)}[/red]")
        return {"status": "error", "error_type": "input_validation", "message": str(e)}

    except CostLimitExceeded as e:
        console.print(f"
[red]Cost Limit: {str(e)}[/red]")
        return {"status": "error", "error_type": "cost_limit", "message": str(e),
                "partial_outputs": all_outputs}

    except RetryLimitExceeded as e:
        console.print(f"
[red]Retry Limit: {str(e)}[/red]")
        return {"status": "error", "error_type": "retry_limit", "message": str(e),
                "partial_outputs": all_outputs}

    except AgentTimeout as e:
        console.print(f"
[red]Timeout: {str(e)}[/red]")
        return {"status": "error", "error_type": "timeout", "message": str(e),
                "partial_outputs": all_outputs}

    except Exception as e:
        console.print(f"
[red]Unexpected error: {str(e)}[/red]")
        return {"status": "error", "error_type": "unexpected", "message": str(e),
                "partial_outputs": all_outputs}
