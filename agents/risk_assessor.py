"""
Agent 2 - Risk Assessor
------------------------
The second agent in the QA workflow pipeline.

Human job it replaces: QA Lead and Tech Lead
identifying what could go wrong and prioritising
where to focus testing effort.
"""

import os
import json
import time
from dotenv import load_dotenv
from anthropic import Anthropic

load_dotenv()

SYSTEM_PROMPT = """You are a Senior QA Lead and Risk Assessment specialist with 15 years of experience
identifying what can go wrong in software features before testing begins.

Risk scoring methodology:
- Likelihood: How probable is this risk? (1=Very Unlikely, 5=Very Likely)
- Impact: How bad would this be if it happened? (1=Minor, 5=Critical business failure)
- Risk Score: Likelihood x Impact (1-25)
- Priority: 1-8=Low, 9-15=Medium, 16-20=High, 21-25=Critical

Always respond in valid JSON format. Never fabricate risks not in the requirement."""


def assess_risks(
    requirement,
    requirements_analysis,
    workflow_state=None,
    circuit_breaker=None,
    correction_notes=None,
    correction_attempt=False
):
    """Produces a risk matrix based on the requirement and Agent 1 analysis."""

    agent_name = "Risk Assessor"
    agent_start_time = time.time()

    if circuit_breaker:
        circuit_breaker.check_all(agent_name, agent_start_time)

    quality_score = requirements_analysis.get("quality_score", 5)
    quality_warning = ""
    if quality_score < 4:
        quality_warning = (
            f"NOTE: Requirement quality score is {quality_score}/10. "
            f"Gaps identified: {requirements_analysis.get('gaps', [])}. "
            "Factor this uncertainty into risk scores."
        )

    client = Anthropic(api_key=os.getenv("ANTHROPIC_API_KEY"))

    prompt = (
        "Perform a risk assessment for the following software feature.\n\n"
        f"ORIGINAL REQUIREMENT:\n{requirement}\n\n"
        f"REQUIREMENTS ANALYSIS:\n"
        f"Summary: {requirements_analysis.get('summary', 'Not available')}\n"
        f"Key test areas: {requirements_analysis.get('key_test_areas', [])}\n"
        f"Gaps identified: {requirements_analysis.get('gaps', [])}\n"
        f"Quality score: {quality_score}/10\n"
        f"{quality_warning}\n\n"
        "Identify risk areas and score them using Likelihood x Impact methodology.\n\n"
        "Respond with ONLY a valid JSON object:\n\n"
        "{\n"
        '  "risk_areas": [\n'
        "    {\n"
        '      "name": "Brief risk name",\n'
        '      "description": "What could go wrong - max 15 words",\n'
        '      "category": "Functional",\n'
        '      "likelihood": 3,\n'
        '      "impact": 4,\n'
        '      "score": 12,\n'
        '      "priority_level": "Medium",\n'
        '      "test_focus": "What to test - max 10 words"\n'
        "    }\n"
        "  ],\n"
        '  "top_risks": ["Risk 1", "Risk 2", "Risk 3"],\n'
        '  "overall_risk_level": "Medium",\n'
        '  "security_risks_present": false,\n'
        '  "performance_risks_present": false,\n'
        '  "integration_risks_present": false,\n'
        '  "critical_risks": [],\n'
        '  "risk_summary": "2 sentence summary of the risk picture"\n'
        "}\n\n"
        "Rules:\n"
        "- Categories: Functional, Security, Performance, Integration, Data, UX, Compliance\n"
        "- priority_level: Low (1-8), Medium (9-15), High (16-20), Critical (21-25)\n"
        "- overall_risk_level: Low, Medium, High, or Critical\n"
        "- score MUST equal likelihood multiplied by impact\n"
        "- Security risks with score >= 15 must appear in critical_risks\n"
        "- STRICT LIMIT: maximum 6 risk areas\n"
        "- STRICT LIMIT: description maximum 15 words\n"
        "- STRICT LIMIT: test_focus maximum 10 words\n"
        "- risk_summary maximum 2 sentences\n"
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

            # Escalate security risks automatically
            if result.get("security_risks_present"):
                for risk in result.get("risk_areas", []):
                    if risk.get("category") == "Security" and risk.get("score", 0) >= 15:
                        if risk["name"] not in result.get("critical_risks", []):
                            result.setdefault("critical_risks", []).append(risk["name"])

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
        f"Risk Assessor failed after {max_retries} attempts. "
        f"Last error: {last_error}"
    )
