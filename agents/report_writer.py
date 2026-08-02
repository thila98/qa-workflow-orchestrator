"""
Agent 6 - Report Writer
------------------------
The final agent in the QA workflow pipeline.
Only runs AFTER the mandatory human review gate.

Human job it replaces: QA Lead writing the final QA plan
document shared with developers, product managers,
and stakeholders before a sprint begins.
"""

import os
import json
import time
from dotenv import load_dotenv
from anthropic import Anthropic

load_dotenv()

SYSTEM_PROMPT = """You are a Senior QA Lead with 15 years of experience writing
QA strategy documents and release readiness reports for software teams.

Your reports are clear, professional, honest, and actionable.
When a human reviewer has added notes or corrections, you incorporate them
and treat them as the authoritative source.

Always respond in valid JSON format matching the exact schema provided."""


def write_report(
    requirement,
    all_outputs,
    human_reviewer_notes="",
    confidence_score=0.8,
    workflow_state=None,
    circuit_breaker=None,
    correction_notes=None,
    correction_attempt=False
):
    """
    Writes the final QA plan report incorporating all agent outputs
    and human reviewer feedback.
    """

    agent_name = "Report Writer"
    agent_start_time = time.time()

    if circuit_breaker:
        circuit_breaker.check_all(agent_name, agent_start_time)

    client = Anthropic(api_key=os.getenv("ANTHROPIC_API_KEY"))

    req_analysis = all_outputs.get("requirements_analysis", {})
    risk_assessment = all_outputs.get("risk_assessment", {})
    test_strategy = all_outputs.get("test_strategy", {})
    test_cases = all_outputs.get("test_cases", {})
    coverage = all_outputs.get("coverage_analysis", {})

    total_test_cases = test_cases.get("total_count", 0)
    overall_risk = risk_assessment.get("overall_risk_level", "Medium")
    critical_risks = risk_assessment.get("critical_risks", [])
    quality_score = req_analysis.get("quality_score", 5)

    reviewer_context = ""
    if human_reviewer_notes and human_reviewer_notes.strip():
        reviewer_context = (
            f"HUMAN REVIEWER NOTES AND CORRECTIONS:\n"
            f"{human_reviewer_notes}\n\n"
            "IMPORTANT: The human reviewer notes above take priority over agent outputs.\n"
        )

    if critical_risks or overall_risk == "Critical":
        suggested_recommendation = "CONDITIONAL GO"
        rec_reason = f"Critical risks identified: {critical_risks}. These must be addressed before release."
    elif overall_risk == "High" or quality_score < 4:
        suggested_recommendation = "CONDITIONAL GO"
        rec_reason = "High risk level or low requirement quality requires careful attention."
    else:
        suggested_recommendation = "GO"
        rec_reason = "Risk level is acceptable and requirements are testable."

    prompt = (
        "Write a complete QA Plan Report based on the following information.\n\n"
        f"REQUIREMENT:\n{requirement}\n\n"
        f"REQUIREMENTS ANALYSIS:\n"
        f"Quality score: {quality_score}/10\n"
        f"Summary: {req_analysis.get('summary', 'Not available')}\n"
        f"Gaps identified: {len(req_analysis.get('gaps', []))}\n"
        f"Needs clarification: {req_analysis.get('needs_clarification', False)}\n\n"
        f"RISK ASSESSMENT:\n"
        f"Overall risk level: {overall_risk}\n"
        f"Critical risks: {critical_risks}\n"
        f"Security risks present: {risk_assessment.get('security_risks_present', False)}\n"
        f"Risk summary: {risk_assessment.get('risk_summary', 'Not available')}\n\n"
        f"TEST STRATEGY:\n"
        f"Strategy summary: {test_strategy.get('strategy_summary', 'Not available')}\n"
        f"Security testing required: {test_strategy.get('security_testing_required', False)}\n"
        f"Estimated hours: {test_strategy.get('estimated_hours', 'Not specified')}\n\n"
        f"TEST CASES:\n"
        f"Total generated: {total_test_cases}\n"
        f"Categories covered: {test_cases.get('categories_covered', [])}\n"
        f"Coverage summary: {test_cases.get('coverage_summary', 'Not available')}\n\n"
        f"AI CONFIDENCE SCORE: {confidence_score:.0%}\n\n"
        f"{reviewer_context}"
        f"SUGGESTED GO/NO-GO: {suggested_recommendation}\n"
        f"Reasoning: {rec_reason}\n\n"
        "Respond with ONLY a valid JSON object:\n\n"
        "{\n"
        '  "executive_summary": "3-4 paragraph professional summary for stakeholders",\n'
        '  "requirement_quality_assessment": "Assessment of requirement quality",\n'
        '  "risk_summary": "Clear summary of risks and implications",\n'
        '  "testing_approach": "Summary of testing strategy and rationale",\n'
        '  "test_suite_summary": {\n'
        '    "total_test_cases": 25,\n'
        '    "by_category": {"Functional": 10, "Negative": 6, "Security": 3},\n'
        '    "high_priority_count": 12,\n'
        '    "automation_candidates": 8\n'
        "  },\n"
        '  "key_risks": [\n'
        '    {"risk": "Risk name", "level": "High", "mitigation": "How to address"}\n'
        "  ],\n"
        '  "entry_criteria": ["Condition before testing starts"],\n'
        '  "exit_criteria": ["Condition that defines done"],\n'
        '  "go_no_go_recommendation": "GO",\n'
        '  "go_no_go_reasoning": "Clear explanation of recommendation",\n'
        '  "go_no_go_conditions": ["Condition that must be met"],\n'
        '  "action_items": [\n'
        '    {"action": "Specific action", "owner": "QA Engineer", "priority": "High"}\n'
        "  ],\n"
        '  "reviewer_notes_incorporated": false,\n'
        '  "confidence_assessment": "Assessment of how reliable this QA plan is",\n'
        '  "next_steps": ["Clear next step for the QA team"]\n'
        "}\n\n"
        "Rules:\n"
        "- go_no_go_recommendation must be: GO, CONDITIONAL GO, or NO GO\n"
        "- If human reviewer notes were provided, reviewer_notes_incorporated must be true\n"
        "- If confidence score is below 0.70, include a warning in confidence_assessment\n"
        "- Do not add any text before or after the JSON\n"
        "- Do not wrap in markdown code blocks"
    )

    if correction_notes:
        prompt += f"\n\nCORRECTION REQUIRED - please fix these issues:\n{correction_notes}"

    max_retries = int(os.getenv("MAX_RETRIES", "3"))
    last_error = None

    for attempt in range(max_retries):
        try:
            response = client.messages.create(
                model="claude-sonnet-4-6",
                max_tokens=4000,
                temperature=0,
                system=SYSTEM_PROMPT,
                messages=[{"role": "user", "content": prompt}]
            )

            if workflow_state and circuit_breaker:
                cost = circuit_breaker.estimate_cost(
                    input_tokens=response.usage.input_tokens,
                    output_tokens=response.usage.output_tokens
                )
                circuit_breaker.record_cost(cost)

            raw_output = response.content[0].text.strip()

            if raw_output.startswith("```"):
                raw_output = raw_output.split("```")[1]
                if raw_output.startswith("json"):
                    raw_output = raw_output[4:]
                raw_output = raw_output.strip()

            result = json.loads(raw_output)

            if workflow_state and not correction_attempt:
                workflow_state.completed_agents.append(agent_name)

            return result

        except json.JSONDecodeError as e:
            last_error = f"Invalid JSON on attempt {attempt + 1}: {str(e)}"
            if circuit_breaker:
                circuit_breaker.record_retry(agent_name)
            if attempt < max_retries - 1:
                time.sleep(2)
            continue

        except Exception as e:
            last_error = f"API error on attempt {attempt + 1}: {str(e)}"
            if circuit_breaker:
                circuit_breaker.record_retry(agent_name)
            if attempt < max_retries - 1:
                time.sleep(2)
            continue

    if workflow_state:
        workflow_state.failed_agents.append(agent_name)

    raise RuntimeError(
        f"Report Writer failed after {max_retries} attempts. "
        f"Last error: {last_error}"
    )
