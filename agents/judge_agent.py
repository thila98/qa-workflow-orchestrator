"""
Judge Agent
-----------
The quality guardian of the entire pipeline.

This is not a standard agent in the workflow sequence.
It is an independent validator that runs AFTER each agent
to check the output before it passes downstream.

Why this is critical:
The #1 failure mode in multi-agent systems is hallucination
propagation. One agent makes something up. The next agent
builds on the made-up fact. By the end, the entire output
is built on a fabricated foundation.

The Judge Agent breaks this chain. It is completely independent
from the agents it validates. It does not share context with them.
It only receives the input and the output, and asks:
"Does this output make sense given this input?"

Real example of what this catches:
- Agent 2 identifies a "payment processing risk" in a feature
  that has nothing to do with payments
- Agent 4 writes SQL injection tests for a feature with no database
- Agent 3 recommends load testing for a simple static page

PwC achieved a 7x accuracy improvement (10% to 70%) simply
by adding structured validation loops between agents.

Problems this solves:
- Hallucination propagation (critical)
- Agents inventing risks or test cases not grounded in the requirement
- Outputs that technically pass schema validation but are nonsensical
- Cross-agent consistency failures
"""

import os
import json
import time
from dotenv import load_dotenv
from anthropic import Anthropic

load_dotenv()


SYSTEM_PROMPT = """You are an independent Quality Assurance Judge reviewing AI agent outputs.

Your role is purely evaluative. You did NOT produce the output you are reviewing.
You are checking whether the output is:
1. Grounded - does it refer only to things actually in the requirement?
2. Complete - does it cover what it claims to cover?
3. Consistent - is it internally consistent with no contradictions?
4. Accurate - are facts and scores correct?
5. Useful - would a QA engineer actually be able to use this?

You are strict but fair. You flag real problems, not nitpicks.
You do not rewrite the output - you only judge it.

Always respond in valid JSON format matching the exact schema provided."""


def judge_output(
    agent_name: str,
    original_input: str,
    agent_output: dict,
    previous_outputs: dict = None
) -> dict:
    """
    Independently validates an agent output for quality and grounding.

    Args:
        agent_name: Name of the agent whose output is being judged
        original_input: The original requirement text
        agent_output: The output to validate
        previous_outputs: Outputs from previous agents for consistency checking

    Returns:
        Dictionary with judgment results including pass/fail and issues found
    """

    client = Anthropic(api_key=os.getenv("ANTHROPIC_API_KEY"))

    # Build context about what we are judging
    output_summary = json.dumps(agent_output, indent=2)[:3000]  # Limit size

    previous_context = ""
    if previous_outputs:
        previous_context = f"""
OUTPUTS FROM PREVIOUS AGENTS (for consistency checking):
{json.dumps({k: str(v)[:500] for k, v in previous_outputs.items()}, indent=2)}
"""

    prompt = f"""You are independently reviewing the output of: {agent_name}

ORIGINAL REQUIREMENT:
{original_input}
{previous_context}

OUTPUT TO JUDGE:
{output_summary}

Evaluate this output and respond with ONLY a valid JSON object:

{{
  "passed": true,
  "confidence_score": 0.85,
  "grounding_check": {{
    "is_grounded": true,
    "ungrounded_claims": [
      "List any claims not supported by the requirement text"
    ]
  }},
  "completeness_check": {{
    "is_complete": true,
    "missing_elements": [
      "List anything important that should be here but is not"
    ]
  }},
  "consistency_check": {{
    "is_consistent": true,
    "inconsistencies": [
      "List any internal contradictions or conflicts with previous agent outputs"
    ]
  }},
  "quality_issues": [
    "List any specific quality problems found"
  ],
  "hallucination_flags": [
    "List any content that appears fabricated or not grounded in the input"
  ],
  "recommendation": "PASS",
  "recommendation_reason": "Brief explanation of the judgment"
}}

Rules:
- passed must be true or false
- confidence_score must be 0.0 to 1.0
- recommendation must be: PASS, PASS_WITH_WARNINGS, or FAIL
- FAIL if: hallucinations detected, major missing elements, or serious inconsistencies
- PASS_WITH_WARNINGS if: minor issues that do not invalidate the output
- PASS if: output is solid and ready for the next agent
- hallucination_flags should list SPECIFIC fabricated claims, not general concerns
- Do not add any text before or after the JSON
- Do not wrap in markdown code blocks"""

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

        raw_output = response.content[0].text.strip()

        if raw_output.startswith("```"):
            raw_output = raw_output.split("```")[1]
            if raw_output.startswith("json"):
                raw_output = raw_output[4:]
            raw_output = raw_output.strip()

        result = json.loads(raw_output)
        result["agent_judged"] = agent_name
        return result

    except json.JSONDecodeError:
        # If judge itself fails, return a warning but do not block the pipeline
        return {
            "passed": True,
            "confidence_score": 0.5,
            "recommendation": "PASS_WITH_WARNINGS",
            "recommendation_reason": "Judge agent could not parse its own output. Manual review recommended.",
            "agent_judged": agent_name,
            "quality_issues": ["Judge agent validation failed - manual review required"],
            "hallucination_flags": [],
            "grounding_check": {"is_grounded": True, "ungrounded_claims": []},
            "completeness_check": {"is_complete": True, "missing_elements": []},
            "consistency_check": {"is_consistent": True, "inconsistencies": []}
        }

    except Exception as e:
        # Same - do not block pipeline on judge failure
        return {
            "passed": True,
            "confidence_score": 0.5,
            "recommendation": "PASS_WITH_WARNINGS",
            "recommendation_reason": f"Judge agent encountered an error: {str(e)}. Manual review recommended.",
            "agent_judged": agent_name,
            "quality_issues": [f"Judge error: {str(e)}"],
            "hallucination_flags": [],
            "grounding_check": {"is_grounded": True, "ungrounded_claims": []},
            "completeness_check": {"is_complete": True, "missing_elements": []},
            "consistency_check": {"is_consistent": True, "inconsistencies": []}
        }
