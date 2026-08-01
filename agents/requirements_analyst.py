"""
Agent 1 - Requirements Analyst
--------------------------------
The first agent in the QA workflow pipeline.

Human job it replaces: Business Analyst / QA Lead
reading through requirements at sprint kickoff and
identifying gaps before test planning begins.

What it does:
- Reads the requirement text
- Identifies missing information that would block testing
- Flags ambiguous language that could mean multiple things
- Lists unstated assumptions being made
- Checks for testability
- Scores requirement quality 1-10

Why this matters:
Poor requirements are the #1 cause of missed defects.
If you start writing test cases before identifying gaps,
you end up testing the wrong things confidently.

Edge cases handled:
- Vague or generic requirements
- Requirements with contradictions
- Very long requirements (summarised first)
- Requirements missing acceptance criteria
"""

import os
import json
import time
from dotenv import load_dotenv
from anthropic import Anthropic

load_dotenv()


# The system prompt defines the agent role.
# It lives here in the system prompt - never in user input.
# This prevents prompt injection from overwriting the agent role.
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
If something is not clear, you flag it as a gap - you never guess.

Always respond in valid JSON format matching the exact schema provided."""


def analyse_requirements(
    requirement: str,
    workflow_state=None,
    circuit_breaker=None
) -> dict:
    """
    Analyses a requirement and returns structured findings.

    Args:
        requirement: The cleaned, validated requirement text
        workflow_state: Current workflow state for cost/retry tracking
        circuit_breaker: Safety controls instance

    Returns:
        Dictionary with analysis results matching the schema
    """

    agent_name = "Requirements Analyst"
    agent_start_time = time.time()

    # Check safety limits before doing any work
    if circuit_breaker:
        circuit_breaker.check_all(agent_name, agent_start_time)

    client = Anthropic(api_key=os.getenv("ANTHROPIC_API_KEY"))

    # The prompt tells the agent exactly what schema to output.
    # Strict schema = no hallucination in structure,
    # even if content varies.
    prompt = f"""Analyse the following software requirement for a QA engineer who needs to write test cases.

REQUIREMENT:
{requirement}

Respond with ONLY a valid JSON object matching this exact schema:

{{
  "summary": "2-3 sentence plain English summary of what this feature does",
  "gaps": [
    "List each piece of missing information that would block test case writing",
    "Be specific about what is missing and why it matters for testing"
  ],
  "ambiguities": [
    "List each statement that could be interpreted in multiple ways",
    "Explain what the different interpretations could be"
  ],
  "assumptions": [
    "List each thing the requirement assumes but does not explicitly state"
  ],
  "acceptance_criteria_present": true,
  "is_testable": true,
  "quality_score": 7,
  "quality_reasoning": "Brief explanation of why you gave this score",
  "needs_clarification": false,
  "clarification_questions": [
    "List any questions that must be answered before testing can begin"
  ],
  "key_test_areas": [
    "List the main functional areas that will need test coverage"
  ]
}}

Rules:
- quality_score must be an integer between 1 and 10
- gaps, ambiguities, assumptions must be lists (can be empty lists if none found)
- is_testable must be true or false
- needs_clarification must be true or false
- Do not add any text before or after the JSON
- Do not wrap the JSON in markdown code blocks"""

    # Retry loop - handles transient API failures
    max_retries = int(os.getenv("MAX_RETRIES", "3"))
    last_error = None

    for attempt in range(max_retries):
        try:
            response = client.messages.create(
                model="claude-sonnet-4-6",
                max_tokens=2000,
                temperature=0,  # Temperature 0 = most consistent outputs
                system=SYSTEM_PROMPT,
                messages=[
                    {"role": "user", "content": prompt}
                ]
            )

            # Track cost if workflow state provided
            if workflow_state and circuit_breaker:
                cost = circuit_breaker.estimate_cost(
                    input_tokens=response.usage.input_tokens,
                    output_tokens=response.usage.output_tokens
                )
                circuit_breaker.record_cost(cost)

            # Parse and return the JSON response
            raw_output = response.content[0].text.strip()

            # Remove markdown code blocks if model added them despite instructions
            if raw_output.startswith("```"):
                raw_output = raw_output.split("```")[1]
                if raw_output.startswith("json"):
                    raw_output = raw_output[4:]
                raw_output = raw_output.strip()

            result = json.loads(raw_output)

            # Track successful completion
            if workflow_state:
                workflow_state.completed_agents.append(agent_name)

            return result

        except json.JSONDecodeError as e:
            last_error = f"Agent returned invalid JSON on attempt {attempt + 1}: {str(e)}"
            if circuit_breaker:
                circuit_breaker.record_retry(agent_name)
            if attempt < max_retries - 1:
                time.sleep(2)  # Brief pause before retry
            continue

        except Exception as e:
            last_error = f"API error on attempt {attempt + 1}: {str(e)}"
            if circuit_breaker:
                circuit_breaker.record_retry(agent_name)
            if attempt < max_retries - 1:
                time.sleep(2)
            continue

    # All retries exhausted
    if workflow_state:
        workflow_state.failed_agents.append(agent_name)

    raise RuntimeError(
        f"Requirements Analyst failed after {max_retries} attempts. "
        f"Last error: {last_error}"
    )
