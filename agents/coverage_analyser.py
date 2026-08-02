"""
Agent 5 - Coverage Analyser
-----------------------------
Optional agent - only runs if user provides an existing test suite CSV.

Human job it replaces: QA Lead manually comparing new test cases
against the existing test suite to find gaps and duplicates.
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

You compare newly generated test cases against an existing test suite.
You are honest and precise. You do not fabricate gaps or duplicates.
If coverage is already good, you say so.

Always respond in valid JSON format matching the exact schema provided."""


def analyse_coverage(
    requirement,
    test_cases_output,
    existing_suite_path,
    workflow_state=None,
    circuit_breaker=None,
    correction_notes=None,
    correction_attempt=False
):
    """
    Compares new test cases against existing test suite for gaps and duplicates.
    Returns a skip result if no CSV was provided.
    """

    agent_name = "Coverage Analyser"
    agent_start_time = time.time()

    if not existing_suite_path:
        return {
            "skipped": True,
            "reason": "No existing test suite provided.",
            "gaps": [],
            "duplicates": [],
            "coverage_estimate": "Unknown - no baseline for comparison",
            "recommendations": [
                "Upload an existing test suite CSV on the next run for gap analysis."
            ],
            "update_candidates": [],
            "coverage_summary": "Coverage analysis was skipped as no existing test suite was provided."
        }

    if circuit_breaker:
        circuit_breaker.check_all(agent_name, agent_start_time)

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

    existing_suite_text = format_for_agent(test_suite, max_cases=50)

    new_test_cases = test_cases_output.get("test_cases", [])
    new_cases_lines = []
    for tc in new_test_cases[:50]:
        new_cases_lines.append(
            f"  {tc.get('tc_id')}: [{tc.get('category')}] {tc.get('title')}"
        )
    new_cases_text = "\n".join(new_cases_lines)

    client = Anthropic(api_key=os.getenv("ANTHROPIC_API_KEY"))

    prompt = (
        "Compare newly generated test cases against the existing test suite.\n\n"
        f"REQUIREMENT:\n{requirement}\n\n"
        f"NEWLY GENERATED TEST CASES ({len(new_test_cases)} total):\n"
        f"{new_cases_text}\n\n"
        f"EXISTING TEST SUITE:\n{existing_suite_text}\n\n"
        "Respond with ONLY a valid JSON object:\n\n"
        "{\n"
        '  "gaps": [\n'
        "    {\n"
        '      "scenario": "Description of uncovered scenario",\n'
        '      "category": "Functional",\n'
        '      "risk_level": "High",\n'
        '      "recommendation": "Suggested action"\n'
        "    }\n"
        "  ],\n"
        '  "duplicates": [\n'
        "    {\n"
        '      "new_test": "TC_ID of new test",\n'
        '      "existing_test": "Title of similar existing test",\n'
        '      "overlap_description": "What they both test",\n'
        '      "recommendation": "Keep new, merge, or skip"\n'
        "    }\n"
        "  ],\n"
        '  "update_candidates": [\n'
        "    {\n"
        '      "existing_test": "Title of existing test needing update",\n'
        '      "reason": "Why it needs updating"\n'
        "    }\n"
        "  ],\n"
        '  "coverage_estimate": "75% - existing suite covers most scenarios",\n'
        '  "new_tests_adding_value": 18,\n'
        '  "new_tests_duplicating": 3,\n'
        '  "coverage_summary": "2-3 sentence summary of coverage picture",\n'
        '  "recommendations": ["Specific actionable recommendation"]\n'
        "}\n\n"
        "Rules:\n"
        "- Only identify genuine gaps - not scenarios unrelated to the requirement\n"
        "- Only identify genuine duplicates - partial similarity is not a duplicate\n"
        "- coverage_estimate should be a realistic percentage with brief explanation\n"
        "- new_tests_adding_value and new_tests_duplicating must be integers\n"
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
                max_tokens=3000,
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
            result["skipped"] = False
            result["existing_suite_count"] = test_suite.total_count

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
        f"Coverage Analyser failed after {max_retries} attempts. "
        f"Last error: {last_error}"
    )
