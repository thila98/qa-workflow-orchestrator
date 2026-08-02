"""
Agent 3 - Test Strategist
--------------------------
The third agent in the QA workflow pipeline.

Human job it replaces: QA Lead / Test Architect
deciding what types of testing are needed,
what to automate, what to do manually,
and what the entry and exit criteria are.

IMPORTANT DESIGN DECISION:
Agent 3 is a test strategist NOT a risk scorer.
Agent 2 has already scored all risks.
Agent 3 receives the full risk matrix and must
reference those exact scores - never invent new ones.
"""

import os
import json
import time
from dotenv import load_dotenv
from anthropic import Anthropic

load_dotenv()

SYSTEM_PROMPT = """You are a Senior Test Architect with 15 years of experience
designing test strategies for software features of all sizes and risk levels.

CRITICAL RULE: You are NOT a risk scorer. Agent 2 has already scored all risks.
When referencing risks, use only the names and scores from the risk matrix provided.
Never invent, adjust, or estimate risk scores.

Your strategies are grounded in real QA practice:
- High risk areas get more test coverage
- Security risks always get dedicated security testing
- Repetitive scenarios get automation recommendations
- One-off or exploratory work stays manual

Always respond in valid JSON format matching the exact schema provided."""


def create_test_strategy(
    requirement,
    requirements_analysis,
    risk_assessment,
    workflow_state=None,
    circuit_breaker=None,
    correction_notes=None,
    correction_attempt=False
):
    """Creates a test strategy based on requirement and risk assessment."""

    agent_name = "Test Strategist"
    agent_start_time = time.time()

    if circuit_breaker:
        circuit_breaker.check_all(agent_name, agent_start_time)

    client = Anthropic(api_key=os.getenv("ANTHROPIC_API_KEY"))

    overall_risk = risk_assessment.get("overall_risk_level", "Medium")
    security_present = risk_assessment.get("security_risks_present", False)
    performance_present = risk_assessment.get("performance_risks_present", False)
    critical_risks = risk_assessment.get("critical_risks", [])
    top_risks = risk_assessment.get("top_risks", [])

    # Format full risk matrix so Agent 3 references exact scores
    risk_matrix_text = ""
    for risk in risk_assessment.get("risk_areas", []):
        risk_matrix_text += (
            f"- {risk.get('name','')}: "
            f"Likelihood={risk.get('likelihood','')}, "
            f"Impact={risk.get('impact','')}, "
            f"Score={risk.get('score','')}, "
            f"Priority={risk.get('priority_level','')}\n"
        )

    prompt = (
        "Create a test strategy for the following software feature.\n\n"
        "YOU ARE A TEST STRATEGIST NOT A RISK SCORER.\n"
        "Agent 2 has already scored all risks. Reference those exact scores only.\n"
        "Never invent, adjust, or estimate risk scores.\n\n"
        f"REQUIREMENT SUMMARY:\n{requirements_analysis.get('summary', requirement)}\n\n"
        f"KEY TEST AREAS:\n{requirements_analysis.get('key_test_areas', [])}\n\n"
        "FULL RISK MATRIX FROM AGENT 2 (use these exact scores):\n"
        f"Overall risk level: {overall_risk}\n"
        f"{risk_matrix_text}"
        f"Top risks: {top_risks}\n"
        f"Critical risks: {critical_risks}\n"
        f"Security risks present: {security_present}\n"
        f"Performance risks present: {performance_present}\n\n"
        "Respond with ONLY a valid JSON object:\n\n"
        "{\n"
        '  "strategy_summary": "2-3 sentence summary of the testing approach",\n'
        '  "test_types": [\n'
        "    {\n"
        '      "type": "Functional Testing",\n'
        '      "reason": "Why this type is needed - max 10 words",\n'
        '      "priority": "High",\n'
        '      "approach": "Manual"\n'
        "    }\n"
        "  ],\n"
        '  "priorities": [\n'
        "    {\n"
        '      "area": "Area name",\n'
        '      "reason": "Why priority - max 10 words",\n'
        '      "risk_reference": "Copy exact score from risk matrix e.g. Score 20 High"\n'
        "    }\n"
        "  ],\n"
        '  "manual_tests": ["What to test manually - max 10 words each"],\n'
        '  "automated_tests": ["What to automate - max 10 words each"],\n'
        '  "entry_criteria": ["Condition before testing starts - max 10 words each"],\n'
        '  "exit_criteria": ["Condition that defines done - max 10 words each"],\n'
        '  "out_of_scope": ["Item not included - max 8 words each"],\n'
        '  "estimated_test_cases": 25,\n'
        '  "estimated_hours": 8,\n'
        '  "security_testing_required": false,\n'
        '  "performance_testing_required": false,\n'
        '  "regression_testing_required": true,\n'
        '  "recommendations": ["Specific recommendation - max 15 words each"]\n'
        "}\n\n"
        "Rules:\n"
        "- If security_risks_present is true, security_testing_required MUST be true\n"
        "- If performance_risks_present is true, performance_testing_required MUST be true\n"
        "- risk_reference must copy the exact score from the risk matrix above\n"
        "- STRICT LIMIT: maximum 4 test_types\n"
        "- STRICT LIMIT: maximum 3 priorities\n"
        "- STRICT LIMIT: maximum 3 items in manual_tests and automated_tests\n"
        "- STRICT LIMIT: maximum 3 entry and exit criteria\n"
        "- STRICT LIMIT: maximum 2 out_of_scope items\n"
        "- STRICT LIMIT: maximum 3 recommendations\n"
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

            # Enforce security and performance testing based on risk flags
            if security_present:
                result["security_testing_required"] = True
            if performance_present:
                result["performance_testing_required"] = True

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
        f"Test Strategist failed after {max_retries} attempts. "
        f"Last error: {last_error}"
    )
