"""
Agent 5 - Coverage Analyser
-----------------------------
Optional agent - only runs if user provides an existing test suite CSV.

Human job it replaces: QA Lead manually comparing new test cases
against the existing test suite to find gaps and duplicates.
This is tedious work that typically takes 30-60 minutes manually.

What it does:
- Compares new test cases from Agent 4 against existing test suite
- Identifies genuine gaps - scenarios not covered anywhere
- Identifies potential duplicates - overlap with existing tests
- Flags outdated existing tests that may need updating
- Produces a coverage gap report with clear recommendations

Why this matters:
Without this comparison, teams often write duplicate test cases
wasting effort, or miss gaps because they assume existing tests
cover something they actually do not.

Edge cases handled:
- No CSV provided: skips gracefully, outputs a note
- Empty or malformed CSV: flags error and skips gracefully
- 100% coverage already: outputs no gaps found honestly
- CSV with different column names: maps intelligently
- Zero overlap with existing tests: flags as new test territory
"""

import os
import json
import time
from dotenv import load_dotenv
from anthropic import Anthropic
from tools.csv_reader import read_test_suite, format_for_agent

load_dotenv()


SYSTEM_PROMPT = """You are a Senior QA Lead with 15 years of experience reviewing
test suites for gaps, duplicates, and coverage quality.

Your role is to compare a newly generated set of test cases against
an existing test suite and identify:
1. Gaps - scenarios in the new tests not covered by existing tests
2. Duplicates - new tests that overlap significantly with existing tests
3. Update candidates - existing tests that may need updating based on new requirements
4. Coverage assessment - honest estimate of overall coverage after combining both sets

You are honest and precise. You do not fabricate gaps or duplicates.
If coverage is already good, you say so.
If there are real gaps, you identify them specifically.

Always respond in valid JSON format matching the exact schema provided."""


def analyse_coverage(
    requirement: str,
    test_cases_output: dict,
    existing_suite_path: str,
    workflow_state=None,
    circuit_breaker=None
) -> dict:
    """
    Compares new test cases against existing test suite for gaps and duplicates.

    Args:
        requirement: Original requirement text
        test_cases_output: Output from Agent 4 (Test Case Writer)
        existing_suite_path: Path to the existing test suite CSV file
        workflow_state: Current workflow state
        circuit_breaker: Safety controls instance

    Returns:
        Dictionary with coverage analysis results,
        or a skip result if no CSV was provided
    """

    agent_name = "Coverage Analyser"
    agent_start_time = time.time()

    # If no existing suite provided, skip gracefully
    if not existing_suite_path:
        return {
            "skipped": True,
            "reason": "No existing test suite provided.",
            "gaps": [],
            "duplicates": [],
            "coverage_estimate": "Unknown - no baseline for comparison",
            "recommendations": [
                "Upload an existing test suite CSV on the next run "
                "to get a coverage gap analysis."
            ],
            "update_candidates": [],
            "coverage_summary": "Coverage analysis was skipped as no existing test suite was provided."
        }

    if circuit_breaker:
        circuit_breaker.check_all(agent_name, agent_start_time)

    # Read the existing test suite
    test_suite = read_test_suite(existing_suite_path)

    if not test_suite or test_suite.total_count == 0:
        return {
            "skipped": True,
            "reason": "Could not read existing test suite or file is empty.",
            "gaps": [],
            "duplicates": [],
            "coverage_estimate": "Unknown",
            "recommendations": ["Check that the CSV file is valid and contains test cases."],
            "update_candidates": [],
            "coverage_summary": "Coverage analysis was skipped due to file reading issues."
        }

    # Format existing suite for the agent
    existing_suite_text = format_for_agent(test_suite, max_cases=50)

    # Format new test cases for comparison
    new_test_cases = test_cases_output.get("test_cases", [])
    new_cases_text = "\n".join([
        f"  {tc.get('tc_id')}: [{tc.get('category')}] {tc.get('title')}"
        for tc in new_test_cases[:50]
    ])

    client = Anthropic(api_key=os.getenv("ANTHROPIC_API_KEY"))

    prompt = f"""Compare the newly generated test cases against the existing test suite.

REQUIREMENT BEING TESTED:
{requirement}

NEWLY GENERATED TEST CASES ({len(new_test_cases)} total):
{new_cases_text}

EXISTING TEST SUITE:
{existing_suite_text}

Analyse the overlap and gaps between these two sets.

Respond with ONLY a valid JSON object matching this exact schema:

{{
  "gaps": [
    {{
      "scenario": "Description of the testing scenario not covered by existing tests",
      "category": "Functional",
      "risk_level": "High",
      "recommendation": "Suggested action to fill this gap"
    }}
  ],
  "duplicates": [
    {{
      "new_test": "TC_ID of the new test case",
      "existing_test": "Title or ID of the similar existing test",
      "overlap_description": "What they both test",
      "recommendation": "Keep new, merge, or skip"
    }}
  ],
  "update_candidates": [
    {{
      "existing_test": "Title or ID of existing test that needs updating",
      "reason": "Why it needs to be updated based on the new requirement"
    }}
  ],
  "coverage_estimate": "75% - existing suite covers most scenarios",
  "new_tests_adding_value": 18,
  "new_tests_duplicating": 3,
  "coverage_summary": "2-3 sentence summary of the overall coverage picture",
  "recommendations": [
    "Specific actionable recommendations for the QA team"
  ]
}}

Rules:
- Only identify genuine gaps - do not fabricate scenarios not related to the requirement
- Only identify genuine duplicates - partial similarity is not a duplicate
- coverage_estimate should be a realistic percentage with brief explanation
- new_tests_adding_value and new_tests_duplicating must be integers
- Do not add any text before or after the JSON
- Do not wrap in markdown code blocks"""

    max_retries = int(os.getenv("MAX_RETRIES", "3"))
    last_error = None

    for attempt in range(max_retries):
        try:
            response = client.messages.create(
                model="claude-sonnet-4-6",
                max_tokens=3000,
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
            result["skipped"] = False
            result["existing_suite_count"] = test_suite.total_count

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
        f"Coverage Analyser failed after {max_retries} attempts. "
        f"Last error: {last_error}"
    )
