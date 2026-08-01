"""
Agent 3 - Test Strategist
--------------------------
The third agent in the QA workflow pipeline.

Human job it replaces: QA Lead / Test Architect
deciding what types of testing are needed,
what to automate, what to do manually,
and what the entry and exit criteria are.

What it does:
- Takes Agent 1 and Agent 2 outputs as input
- Decides which test types are needed and why
- Prioritises based on risk scores
- Recommends manual vs automated for each area
- Defines entry and exit criteria
- Estimates test case count

Why this matters:
Without a strategy you either over-test (waste time)
or under-test (miss bugs). The strategy makes sure
testing effort matches actual risk.

Edge cases handled:
- All risks are low: recommends lightweight strategy
- Security risks present: mandates security testing
- Performance risks present: adds load testing
- Simple UI change: deprioritises backend testing
"""

import os
import json
import time
from dotenv import load_dotenv
from anthropic import Anthropic

load_dotenv()


SYSTEM_PROMPT = """You are a Senior Test Architect with 15 years of experience
designing test strategies for software features of all sizes and risk levels.

Your role is to take a requirement and its risk assessment and produce
a practical, actionable test strategy. You are realistic about time and effort.
You do not recommend testing everything - you recommend testing the right things.

Your strategies are grounded in real QA practice:
- High risk areas get more test coverage
- Security risks always get dedicated security testing
- Repetitive scenarios get automation recommendations
- One-off or exploratory work stays manual

Always respond in valid JSON format matching the exact schema provided."""


def create_test_strategy(
    requirement: str,
    requirements_analysis: dict,
    risk_assessment: dict,
    workflow_state=None,
    circuit_breaker=None
) -> dict:
    """
    Creates a test strategy based on requirement and risk assessment.

    Args:
        requirement: Original requirement text
        requirements_analysis: Output from Agent 1
        risk_assessment: Output from Agent 2
        workflow_state: Current workflow state
        circuit_breaker: Safety controls instance

    Returns:
        Dictionary with test strategy
    """

    agent_name = "Test Strategist"
    agent_start_time = time.time()

    if circuit_breaker:
        circuit_breaker.check_all(agent_name, agent_start_time)

    client = Anthropic(api_key=os.getenv("ANTHROPIC_API_KEY"))

    # Build context from previous agents
    top_risks = risk_assessment.get("top_risks", [])
    overall_risk = risk_assessment.get("overall_risk_level", "Medium")
    security_present = risk_assessment.get("security_risks_present", False)
    performance_present = risk_assessment.get("performance_risks_present", False)
    critical_risks = risk_assessment.get("critical_risks", [])

    prompt = f"""Create a test strategy for the following software feature.

REQUIREMENT SUMMARY:
{requirements_analysis.get("summary", requirement)}

KEY TEST AREAS:
{requirements_analysis.get("key_test_areas", [])}

RISK ASSESSMENT SUMMARY:
Overall risk level: {overall_risk}
Top risks: {top_risks}
Critical risks: {critical_risks}
Security risks present: {security_present}
Performance risks present: {performance_present}

Respond with ONLY a valid JSON object matching this exact schema:

{{
  "strategy_summary": "2-3 sentence plain English summary of the testing approach",
  "test_types": [
    {{
      "type": "Functional Testing",
      "reason": "Why this type of testing is needed",
      "priority": "High",
      "approach": "Manual or Automated or Both"
    }}
  ],
  "priorities": [
    {{
      "area": "Name of the area to prioritise",
      "reason": "Why this area needs priority attention",
      "risk_score": 20
    }}
  ],
  "manual_tests": [
    "Description of what should be tested manually and why"
  ],
  "automated_tests": [
    "Description of what should be automated and why"
  ],
  "entry_criteria": [
    "Condition that must be true before testing can start"
  ],
  "exit_criteria": [
    "Condition that defines when testing is complete"
  ],
  "out_of_scope": [
    "Testing areas explicitly not included and why"
  ],
  "estimated_test_cases": 25,
  "estimated_hours": 8,
  "security_testing_required": false,
  "performance_testing_required": false,
  "regression_testing_required": true,
  "recommendations": [
    "Specific recommendations for the QA team"
  ]
}}

Rules:
- If security_risks_present is true, security_testing_required MUST be true
- If performance_risks_present is true, performance_testing_required MUST be true
- test_types priority must be: High, Medium, or Low
- estimated_test_cases must be a realistic integer based on the complexity
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

            # Enforce security testing if risks present
            if security_present:
                result["security_testing_required"] = True

            # Enforce performance testing if risks present
            if performance_present:
                result["performance_testing_required"] = True

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
        f"Test Strategist failed after {max_retries} attempts. "
        f"Last error: {last_error}"
    )
