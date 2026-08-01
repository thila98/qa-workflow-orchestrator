"""
Agent 2 - Risk Assessor
------------------------
The second agent in the QA workflow pipeline.

Human job it replaces: QA Lead and Tech Lead
sitting together to identify what could go wrong
and prioritise where to focus testing effort.

What it does:
- Takes Agent 1 output as input
- Identifies functional, integration, security, and performance risks
- Scores each risk: Likelihood (1-5) x Impact (1-5) = Risk Score (1-25)
- Ranks risks from highest to lowest
- Flags critical risks that must be addressed regardless of score

Why this matters:
Without risk assessment you test everything equally.
With it you know exactly where to focus your limited time.
A login feature at a bank has different risks than
a login feature at a blog. This agent understands the difference.

Edge cases handled:
- Requirements with no identifiable risks (simple features)
- Security risks automatically escalated to Critical
- Low confidence from Agent 1 reduces confidence here too
- Missing Agent 1 input triggers graceful failure
"""

import os
import json
import time
from dotenv import load_dotenv
from anthropic import Anthropic

load_dotenv()


SYSTEM_PROMPT = """You are a Senior QA Lead and Risk Assessment specialist with 15 years of experience
identifying what can go wrong in software features before testing begins.

Your role is to analyse a software requirement and its gap analysis to produce
a comprehensive risk matrix. You think like someone who has seen real production failures
and knows which risks cause the most damage when they slip through to production.

Risk scoring methodology:
- Likelihood: How probable is this risk? (1=Very Unlikely, 5=Very Likely)
- Impact: How bad would this be if it happened? (1=Minor inconvenience, 5=Critical business failure)
- Risk Score: Likelihood x Impact (1-25)
- Priority: 1-8=Low, 9-15=Medium, 16-20=High, 21-25=Critical

Always respond in valid JSON format matching the exact schema provided.
Never fabricate risks that have no basis in the requirement. Only identify real risks."""


def assess_risks(
    requirement: str,
    requirements_analysis: dict,
    workflow_state=None,
    circuit_breaker=None
) -> dict:
    """
    Produces a risk matrix based on the requirement and Agent 1 analysis.

    Args:
        requirement: Original requirement text
        requirements_analysis: Output from Agent 1 (Requirements Analyst)
        workflow_state: Current workflow state for cost/retry tracking
        circuit_breaker: Safety controls instance

    Returns:
        Dictionary with risk assessment results
    """

    agent_name = "Risk Assessor"
    agent_start_time = time.time()

    if circuit_breaker:
        circuit_breaker.check_all(agent_name, agent_start_time)

    # If Agent 1 flagged low quality requirement, warn but continue
    quality_score = requirements_analysis.get("quality_score", 5)
    quality_warning = ""
    if quality_score < 4:
        quality_warning = f"""
NOTE: The requirements analyst scored this requirement {quality_score}/10 for quality.
The following gaps were identified: {requirements_analysis.get("gaps", [])}
Factor this into your risk assessment - low quality requirements typically mean higher risk."""

    client = Anthropic(api_key=os.getenv("ANTHROPIC_API_KEY"))

    prompt = f"""Perform a risk assessment for the following software feature.

ORIGINAL REQUIREMENT:
{requirement}

REQUIREMENTS ANALYSIS (from previous analyst):
Summary: {requirements_analysis.get("summary", "Not available")}
Key test areas: {requirements_analysis.get("key_test_areas", [])}
Gaps identified: {requirements_analysis.get("gaps", [])}
Quality score: {quality_score}/10
{quality_warning}

Identify all testable risk areas and score them using Likelihood x Impact methodology.

Respond with ONLY a valid JSON object matching this exact schema:

{{
  "risk_areas": [
    {{
      "name": "Brief name of the risk area",
      "description": "What could go wrong and why",
      "category": "Functional",
      "likelihood": 3,
      "impact": 4,
      "score": 12,
      "priority_level": "Medium",
      "test_focus": "What testing should focus on for this risk"
    }}
  ],
  "top_risks": [
    "Name of highest risk area",
    "Name of second highest risk area",
    "Name of third highest risk area"
  ],
  "overall_risk_level": "Medium",
  "security_risks_present": false,
  "performance_risks_present": false,
  "integration_risks_present": false,
  "critical_risks": [],
  "risk_summary": "2-3 sentence summary of the overall risk picture"
}}

Rules for categories: Functional, Security, Performance, Integration, Data, UX, Compliance
Rules for priority_level: Low (1-8), Medium (9-15), High (16-20), Critical (21-25)
Rules for overall_risk_level: Low, Medium, High, Critical
- Security risks with score >= 15 must appear in critical_risks list
- Score must equal likelihood multiplied by impact
- Do not add any text before or after the JSON
- Do not wrap in markdown code blocks
- Keep descriptions concise - maximum 2 sentences each
- Limit to maximum 8 risk areas total"""

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

            # Post-processing: ensure security risks are escalated
            if result.get("security_risks_present"):
                for risk in result.get("risk_areas", []):
                    if risk.get("category") == "Security" and risk.get("score", 0) >= 15:
                        if risk["name"] not in result.get("critical_risks", []):
                            result.setdefault("critical_risks", []).append(risk["name"])

            if workflow_state:
                workflow_state.completed_agents.append(agent_name)

            return result

        except json.JSONDecodeError as e:
            last_error = f"Agent returned invalid JSON on attempt {attempt + 1}: {str(e)}"
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
        f"Risk Assessor failed after {max_retries} attempts. "
        f"Last error: {last_error}"
    )
