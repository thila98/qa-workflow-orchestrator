"""
Agent 1 - Requirements Analyst
--------------------------------
The first agent in the QA workflow pipeline.

Human job it replaces: Business Analyst / QA Lead
reading through requirements at sprint kickoff and
identifying gaps before test planning begins.
"""

import os
import json
import time
from dotenv import load_dotenv
from anthropic import Anthropic

load_dotenv()

SYSTEM_PROMPT = """You are a Senior Business Analyst and QA Lead with 15 years of experience
reviewing software requirements before testing begins.

Your role is to analyse a given requirement and identify:
1. Gaps - information missing that would block writing test cases
2. Ambiguities - statements that could be interpreted in multiple ways
3. Assumptions - things the requirement assumes but does not state
4. Testability issues - aspects that cannot be objectively verified
5. Overall quality - how well written the requirement is for testing purposes

You are thorough, precise, and focused on what matters for quality assurance.
You do not make up information. You only analyse what is provided.
Always respond in valid JSON format matching the exact schema provided."""


def analyse_requirements(
    requirement,
    workflow_state=None,
    circuit_breaker=None,
    correction_notes=None,
    correction_attempt=False
):
    """
    Analyses a requirement and returns structured findings.

    Args:
        requirement: The cleaned, validated requirement text
        workflow_state: Current workflow state for cost/retry tracking
        circuit_breaker: Safety controls instance
        correction_notes: Feedback from Judge Agent to improve output
        correction_attempt: True if this is a correction re-run

    Returns:
        Dictionary with analysis results
    """

    agent_name = "Requirements Analyst"
    agent_start_time = time.time()

    if circuit_breaker:
        circuit_breaker.check_all(agent_name, agent_start_time)

    client = Anthropic(api_key=os.getenv("ANTHROPIC_API_KEY"))

    prompt = (
        "Analyse the following software requirement for a QA engineer who needs to write test cases.\n\n"
        f"REQUIREMENT:\n{requirement}\n\n"
        "Respond with ONLY a valid JSON object matching this exact schema:\n\n"
        "{\n"
        '  "summary": "2-3 sentence plain English summary of what this feature does",\n'
        '  "gaps": ["gap 1 under 15 words", "gap 2 under 15 words"],\n'
        '  "ambiguities": ["ambiguity 1 under 15 words", "ambiguity 2 under 15 words"],\n'
        '  "assumptions": ["assumption 1 under 15 words", "assumption 2 under 15 words"],\n'
        '  "acceptance_criteria_present": true,\n'
        '  "is_testable": true,\n'
        '  "quality_score": 7,\n'
        '  "quality_reasoning": "One sentence explanation of the score",\n'
        '  "needs_clarification": false,\n'
        '  "clarification_questions": ["question 1", "question 2"],\n'
        '  "key_test_areas": ["area 1", "area 2", "area 3"]\n'
        "}\n\n"
        "Rules:\n"
        "- quality_score must be an integer between 1 and 10\n"
        "- gaps, ambiguities, assumptions must be lists (can be empty lists if none found)\n"
        "- is_testable must be true or false\n"
        "- needs_clarification must be true or false\n"
        "- STRICT LIMIT: maximum 5 items per list\n"
        "- STRICT LIMIT: maximum 15 words per list item\n"
        "- summary maximum 2 sentences\n"
        "- quality_reasoning maximum 1 sentence\n"
        "- Do not add any text before or after the JSON\n"
        "- Do not wrap the JSON in markdown code blocks"
    )

    if correction_notes:
        prompt += f"\n\nCORRECTION REQUIRED - please fix these issues in your response:\n{correction_notes}"

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

            if workflow_state and not correction_attempt:
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
        f"Requirements Analyst failed after {max_retries} attempts. "
        f"Last error: {last_error}"
    )
