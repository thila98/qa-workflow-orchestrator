"""
Agent 6 - Report Writer
------------------------
The final agent in the QA workflow pipeline.
Only runs AFTER the mandatory human review gate.

Human job it replaces: QA Lead writing the final QA plan
document that gets shared with developers, product managers,
and stakeholders before a sprint begins.

What it does:
- Takes all approved agent outputs plus human reviewer notes
- Incorporates any corrections the human reviewer made
- Writes a professional executive summary
- Produces a go/no-go testing recommendation with reasoning
- Generates a complete stakeholder-ready QA strategy document
- Outputs structured data for the dashboard and HTML report

Why this matters:
Writing the final QA plan document typically takes 1-2 hours.
It requires synthesising information from multiple sources into
a coherent narrative that both technical and non-technical
stakeholders can understand. This agent does it in seconds,
incorporating all the human reviewer feedback.

Edge cases handled:
- Human reviewer made major changes: prioritises human input
- Human reviewer added notes: incorporates them prominently
- All agents had low confidence: includes prominent warning
- Critical risks detected: adds strong go/no-go warnings
"""

import os
import json
import time
from dotenv import load_dotenv
from anthropic import Anthropic

load_dotenv()


SYSTEM_PROMPT = """You are a Senior QA Lead with 15 years of experience writing
QA strategy documents and release readiness reports for software teams.

Your reports are:
- Clear and professional - readable by both technical and non-technical stakeholders
- Honest - you do not hide risks or sugarcoat problems
- Actionable - every section leads to a clear next step
- Concise - you say what needs to be said without padding

You synthesise information from multiple sources into a coherent narrative.
When a human reviewer has added notes or corrections, you incorporate them
and treat them as the authoritative source.

Always respond in valid JSON format matching the exact schema provided."""


def write_report(
    requirement: str,
    all_outputs: dict,
    human_reviewer_notes: str = "",
    confidence_score: float = 0.8,
    workflow_state=None,
    circuit_breaker=None
) -> dict:
    """
    Writes the final QA plan report incorporating all agent outputs
    and human reviewer feedback.

    Args:
        requirement: Original requirement text
        all_outputs: Dict containing all previous agent outputs
        human_reviewer_notes: Any notes or corrections from the human reviewer
        confidence_score: Overall workflow confidence score
        workflow_state: Current workflow state
        circuit_breaker: Safety controls instance

    Returns:
        Dictionary with the complete final report
    """

    agent_name = "Report Writer"
    agent_start_time = time.time()

    if circuit_breaker:
        circuit_breaker.check_all(agent_name, agent_start_time)

    client = Anthropic(api_key=os.getenv("ANTHROPIC_API_KEY"))

    # Extract key information from previous agents
    req_analysis = all_outputs.get("requirements_analysis", {})
    risk_assessment = all_outputs.get("risk_assessment", {})
    test_strategy = all_outputs.get("test_strategy", {})
    test_cases = all_outputs.get("test_cases", {})
    coverage = all_outputs.get("coverage_analysis", {})

    total_test_cases = test_cases.get("total_count", 0)
    overall_risk = risk_assessment.get("overall_risk_level", "Medium")
    critical_risks = risk_assessment.get("critical_risks", [])
    quality_score = req_analysis.get("quality_score", 5)

    # Build human reviewer context
    reviewer_context = ""
    if human_reviewer_notes and human_reviewer_notes.strip():
        reviewer_context = f"""
HUMAN REVIEWER NOTES AND CORRECTIONS:
{human_reviewer_notes}

IMPORTANT: The human reviewer notes above take priority over any agent outputs.
Incorporate these corrections and notes prominently in the report.
"""

    # Determine go/no-go recommendation based on risk and quality
    if critical_risks or overall_risk == "Critical":
        suggested_recommendation = "CONDITIONAL GO"
        rec_reason = (
            f"Critical risks identified: {critical_risks}. "
            f"These must be addressed before release."
        )
    elif overall_risk == "High" or quality_score < 4:
        suggested_recommendation = "CONDITIONAL GO"
        rec_reason = "High risk level or low requirement quality requires careful attention."
    else:
        suggested_recommendation = "GO"
        rec_reason = "Risk level is acceptable and requirements are testable."

    prompt = f"""Write a complete QA Plan Report based on the following information.

REQUIREMENT:
{requirement}

REQUIREMENTS ANALYSIS SUMMARY:
Quality score: {quality_score}/10
Summary: {req_analysis.get("summary", "Not available")}
Gaps identified: {len(req_analysis.get("gaps", []))}
Needs clarification: {req_analysis.get("needs_clarification", False)}

RISK ASSESSMENT:
Overall risk level: {overall_risk}
Critical risks: {critical_risks}
Security risks present: {risk_assessment.get("security_risks_present", False)}
Performance risks present: {risk_assessment.get("performance_risks_present", False)}
Risk summary: {risk_assessment.get("risk_summary", "Not available")}

TEST STRATEGY:
Strategy summary: {test_strategy.get("strategy_summary", "Not available")}
Security testing required: {test_strategy.get("security_testing_required", False)}
Performance testing required: {test_strategy.get("performance_testing_required", False)}
Estimated hours: {test_strategy.get("estimated_hours", "Not specified")}

TEST CASES:
Total generated: {total_test_cases}
Categories covered: {test_cases.get("categories_covered", [])}
Coverage summary: {test_cases.get("coverage_summary", "Not available")}

COVERAGE ANALYSIS:
{json.dumps(coverage, indent=2)[:500] if coverage and not coverage.get("skipped") else "No existing test suite comparison performed."}

AI CONFIDENCE SCORE: {confidence_score:.0%}

{reviewer_context}

SUGGESTED GO/NO-GO: {suggested_recommendation}
Reasoning: {rec_reason}

Respond with ONLY a valid JSON object matching this exact schema:

{{
  "executive_summary": "3-4 paragraph professional summary of the entire QA plan for stakeholders",
  "requirement_quality_assessment": "Assessment of the requirement quality and any concerns",
  "risk_summary": "Clear summary of risks and their implications for testing",
  "testing_approach": "Summary of the testing strategy and rationale",
  "test_suite_summary": {{
    "total_test_cases": 25,
    "by_category": {{
      "Functional": 10,
      "Negative": 6,
      "Security": 3,
      "Boundary": 3,
      "Integration": 2,
      "UI-UX": 1
    }},
    "high_priority_count": 12,
    "automation_candidates": 8
  }},
  "key_risks": [
    {{
      "risk": "Risk name",
      "level": "High",
      "mitigation": "How to address this risk in testing"
    }}
  ],
  "entry_criteria": [
    "Condition that must be true before testing starts"
  ],
  "exit_criteria": [
    "Condition that defines when testing is complete"
  ],
  "go_no_go_recommendation": "GO",
  "go_no_go_reasoning": "Clear explanation of the recommendation",
  "go_no_go_conditions": [
    "Conditions that must be met for GO recommendation"
  ],
  "action_items": [
    {{
      "action": "Specific action to take",
      "owner": "QA Engineer / QA Lead / Developer / Product Manager",
      "priority": "High"
    }}
  ],
  "reviewer_notes_incorporated": false,
  "confidence_assessment": "Assessment of how reliable this QA plan is based on AI confidence score",
  "next_steps": [
    "Clear next step for the QA team"
  ]
}}

Rules:
- executive_summary must be professional and readable by non-technical stakeholders
- go_no_go_recommendation must be: GO, CONDITIONAL GO, or NO GO
- If human reviewer notes were provided, reviewer_notes_incorporated must be true
- If confidence score is below 0.70, include a warning in confidence_assessment
- action_items owner should be realistic role names
- Do not add any text before or after the JSON
- Do not wrap in markdown code blocks"""

    max_retries = int(os.getenv("MAX_RETRIES", "3"))
    last_error = None

    for attempt in range(max_retries):
        try:
            response = client.messages.create(
                model="claude-sonnet-4-6",
                max_tokens=4000,
                temperature=0,
                system=SYSTEM_PROMPT,
                messages=[
                    {"role": "user", "content": prompt}
                ]
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

            if workflow_state:
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
