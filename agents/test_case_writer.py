"""
Agent 4 - Test Case Writer
---------------------------
The fourth agent in the QA workflow pipeline.
This is the most output-heavy agent in the system.

Human job it replaces: QA Engineer spending hours
writing test cases manually for a new feature,
starting from a blank document.

What it does:
- Takes Agents 1, 2, and 3 outputs as input
- Writes detailed structured test cases
- Covers all categories: Functional, Negative, Boundary,
  Security, Integration, UI-UX, Performance
- Each test case has all required fields
- Groups test cases by risk area for easy navigation
- Flags highest priority test cases

Why this matters:
This is where QA engineers spend 25-30% of their time.
A senior engineer takes 30-45 minutes to write a solid
set of test cases for one feature. This agent does it
in under 30 seconds. The human then reviews, refines,
and adds domain-specific knowledge on top.

Edge cases handled:
- Strategy recommends security testing: generates specific
  injection, auth, and authorisation test cases
- Strategy recommends performance testing: generates
  load and concurrency test cases
- Simple features: may generate fewer than 15 test cases,
  explains why in the output
- Complex features: batches into groups of 20
"""

import os
import json
import time
from dotenv import load_dotenv
from anthropic import Anthropic

load_dotenv()


SYSTEM_PROMPT = """You are a Senior QA Engineer with 15 years of experience writing
comprehensive test cases for software features of all types and complexity levels.

Your test cases are:
- Specific and actionable - anyone can execute them without guessing
- Complete - every field is filled with meaningful content
- Well structured - steps are numbered and clear
- Properly categorised - correct test type for each scenario
- Risk-informed - higher risk areas get more test cases

You write test cases that catch real bugs. You think about:
- What happens when data is missing, invalid, or malformed
- What happens at the boundaries of acceptable values
- What happens when multiple users do the same thing at once
- What happens when the network is slow or fails
- What a malicious user might try to do
- What a confused user might accidentally do

Always respond in valid JSON format matching the exact schema provided.
Every field in every test case must be filled. Never leave fields empty."""


def write_test_cases(
    requirement: str,
    requirements_analysis: dict,
    risk_assessment: dict,
    test_strategy: dict,
    workflow_state=None,
    circuit_breaker=None
) -> dict:
    """
    Writes comprehensive test cases based on all previous agent outputs.

    Args:
        requirement: Original requirement text
        requirements_analysis: Output from Agent 1
        risk_assessment: Output from Agent 2
        test_strategy: Output from Agent 3
        workflow_state: Current workflow state
        circuit_breaker: Safety controls instance

    Returns:
        Dictionary with test cases and metadata
    """

    agent_name = "Test Case Writer"
    agent_start_time = time.time()

    if circuit_breaker:
        circuit_breaker.check_all(agent_name, agent_start_time)

    client = Anthropic(api_key=os.getenv("ANTHROPIC_API_KEY"))

    # Build targeted instructions based on strategy
    special_instructions = []

    if test_strategy.get("security_testing_required"):
        special_instructions.append(
            "IMPORTANT: Security testing is required. Include specific test cases for: "
            "SQL injection, XSS injection, unauthorised access attempts, "
            "authentication bypass, and session management."
        )

    if test_strategy.get("performance_testing_required"):
        special_instructions.append(
            "IMPORTANT: Performance testing is required. Include test cases for: "
            "response time under normal load, behaviour under concurrent users, "
            "and system behaviour when approaching limits."
        )

    if test_strategy.get("regression_testing_required"):
        special_instructions.append(
            "Include integration test cases that verify this feature does not "
            "break existing related functionality."
        )

    special_text = "\n".join(special_instructions)

    prompt = f"""Write comprehensive test cases for the following software feature.

REQUIREMENT SUMMARY:
{requirements_analysis.get("summary", requirement)}

FULL REQUIREMENT:
{requirement}

TOP RISK AREAS TO FOCUS ON:
{risk_assessment.get("top_risks", [])}

OVERALL RISK LEVEL: {risk_assessment.get("overall_risk_level", "Medium")}

TEST STRATEGY SUMMARY:
{test_strategy.get("strategy_summary", "")}

ESTIMATED TEST CASES: {test_strategy.get("estimated_test_cases", 20)}

{special_text}

Respond with ONLY a valid JSON object matching this exact schema:

{{
  "test_cases": [
    {{
      "tc_id": "TC_001",
      "category": "Functional",
      "title": "Short descriptive title of what this test verifies",
      "risk_area": "Which risk area from the risk assessment this covers",
      "precondition": "What must be true before executing this test",
      "steps": "1. First step
2. Second step
3. Third step",
      "expected_result": "Specific, measurable outcome that proves the test passed",
      "priority": "High",
      "test_type": "Manual",
      "notes": "Any additional context, data requirements, or edge case notes"
    }}
  ],
  "total_count": 25,
  "categories_covered": ["Functional", "Negative", "Boundary"],
  "coverage_summary": "Brief summary of what the test suite covers",
  "missing_coverage": "Any areas that could not be covered without more information"
}}

Rules:
- tc_id format: TC_001, TC_002, TC_003 (sequential, no gaps)
- category must be one of: Functional, Negative, Boundary, Security, Integration, UI-UX, Performance
- priority must be: High, Medium, or Low
- test_type must be: Manual, Automated, or Manual/Automated
- steps must be numbered: 1. step one 2. step two 3. step three
- expected_result must be specific - never say "works correctly" or "no errors"
- precondition must describe the exact starting state
- Generate at minimum 15 test cases, aim for the estimated count in the strategy
- Do not add any text before or after the JSON
- Do not wrap in markdown code blocks"""

    max_retries = int(os.getenv("MAX_RETRIES", "3"))
    last_error = None

    for attempt in range(max_retries):
        try:
            response = client.messages.create(
                model="claude-sonnet-4-6",
                max_tokens=8000,
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

            # Update total count to match actual generated count
            if "test_cases" in result:
                result["total_count"] = len(result["test_cases"])

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
        f"Test Case Writer failed after {max_retries} attempts. "
        f"Last error: {last_error}"
    )
