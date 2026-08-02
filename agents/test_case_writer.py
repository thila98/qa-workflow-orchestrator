"""
Agent 4 - Test Case Writer
---------------------------
The fourth agent in the QA workflow pipeline.

Human job it replaces: QA Engineer spending hours
writing test cases manually for a new feature.

ADAPTIVE CHUNKED GENERATION:
Instead of fixed batch sizes, this agent adapts to
requirement complexity. Complex requirements get more
batches with fewer cases each to prevent JSON truncation.

Complexity is measured using:
- Requirement character count
- Number of gaps from Agent 1
- Number of key test areas from Agent 1
- Overall risk level from Agent 2

Complexity levels:
- Simple  (<300 chars, few gaps):  3 batches x 8 cases = 24 cases
- Medium  (300-600 chars):         3 batches x 6 cases = 18 cases
- Complex (600-1000 chars):        4 batches x 5 cases = 20 cases
- Very complex (1000+ chars):      5 batches x 4 cases = 20 cases
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

Always respond in valid JSON format matching the exact schema provided.
Every field in every test case must be filled. Never leave fields empty."""


def calculate_complexity(requirement, requirements_analysis, risk_assessment):
    """
    Calculates requirement complexity to determine batch size.
    Returns a complexity level: simple, medium, complex, or very_complex.
    """
    char_count = len(requirement)
    gaps = len(requirements_analysis.get("gaps", []))
    test_areas = len(requirements_analysis.get("key_test_areas", []))
    risk_level = risk_assessment.get("overall_risk_level", "Medium")

    # Score each factor
    score = 0

    if char_count > 1000:
        score += 3
    elif char_count > 600:
        score += 2
    elif char_count > 300:
        score += 1

    if gaps > 4:
        score += 2
    elif gaps > 2:
        score += 1

    if test_areas > 5:
        score += 2
    elif test_areas > 3:
        score += 1

    if risk_level in ["Critical", "High"]:
        score += 1

    if score <= 1:
        return "simple"
    elif score <= 3:
        return "medium"
    elif score <= 5:
        return "complex"
    else:
        return "very_complex"


def get_batch_config(complexity, security_required, performance_required):
    """
    Returns batch configuration based on complexity level.
    Each config has: list of batches, each with categories and case count.
    """

    if complexity == "simple":
        batches = [
            {"categories": ["Functional", "Negative"], "count": 8},
            {"categories": ["Boundary", "Security"], "count": 7},
            {"categories": ["Integration", "UI-UX"], "count": 6},
        ]
    elif complexity == "medium":
        batches = [
            {"categories": ["Functional", "Negative"], "count": 6},
            {"categories": ["Boundary", "Security"], "count": 6},
            {"categories": ["Integration", "UI-UX"], "count": 5},
        ]
    elif complexity == "complex":
        batches = [
            {"categories": ["Functional"], "count": 5},
            {"categories": ["Negative", "Boundary"], "count": 5},
            {"categories": ["Security"], "count": 5},
            {"categories": ["Integration", "UI-UX"], "count": 5},
        ]
    else:  # very_complex
        batches = [
            {"categories": ["Functional"], "count": 4},
            {"categories": ["Negative"], "count": 4},
            {"categories": ["Boundary", "Security"], "count": 4},
            {"categories": ["Integration"], "count": 4},
            {"categories": ["UI-UX"], "count": 3},
        ]

    # Add performance batch if needed
    if performance_required:
        batches.append({"categories": ["Performance"], "count": 3})

    return batches


def generate_batch(
    client,
    requirement,
    requirements_analysis,
    risk_assessment,
    test_strategy,
    categories,
    case_count,
    start_tc_id,
    special_instructions,
    circuit_breaker,
    workflow_state
):
    """
    Generates one batch of test cases for the given categories.
    Smaller batches never hit token limits.
    """

    tc_start = f"TC_{start_tc_id:03d}"

    prompt = (
        f"Write EXACTLY {case_count} test cases for this software feature.\n"
        f"Cover ONLY these categories: {', '.join(categories)}\n\n"
        f"REQUIREMENT:\n{requirement}\n\n"
        f"REQUIREMENT SUMMARY: {requirements_analysis.get('summary', '')}\n\n"
        f"TOP RISK AREAS: {risk_assessment.get('top_risks', [])}\n"
        f"OVERALL RISK LEVEL: {risk_assessment.get('overall_risk_level', 'Medium')}\n\n"
        f"{special_instructions}\n\n"
        f"Start TC IDs from {tc_start}. Generate exactly {case_count} test cases.\n\n"
        "Respond with ONLY a valid JSON array:\n\n"
        "[\n"
        "  {\n"
        f'    "tc_id": "{tc_start}",\n'
        f'    "category": "{categories[0]}",\n'
        '    "title": "Clear title under 10 words",\n'
        '    "risk_area": "Which risk area this covers",\n'
        '    "precondition": "Starting state under 15 words",\n'
        '    "steps": "1. First action 2. Second action 3. Third action",\n'
        '    "expected_result": "Specific measurable outcome under 20 words",\n'
        '    "priority": "High",\n'
        '    "test_type": "Manual",\n'
        '    "notes": "Brief context under 10 words",\n'
        '    "requirement_reference": "Which part of the requirement this test covers"\n'
        "  }\n"
        "]\n\n"
        "Rules:\n"
        f"- tc_id must start from {tc_start} and be sequential\n"
        "- category must be one of: Functional, Negative, Boundary, Security, Integration, UI-UX, Performance\n"
        "- priority must be: High, Medium, or Low\n"
        "- test_type must be: Manual, Automated, or Manual/Automated\n"
        "- expected_result must be specific - never say works correctly or no errors\n"
        "- requirement_reference must quote the specific part of the requirement this test covers\n"
        "- Return a JSON array not an object\n"
        "- Do not add any text before or after the JSON array\n"
        "- Do not wrap in markdown code blocks"
    )

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

            if circuit_breaker and workflow_state:
                cost = circuit_breaker.estimate_cost(
                    input_tokens=response.usage.input_tokens,
                    output_tokens=response.usage.output_tokens
                )
                circuit_breaker.record_cost(cost)

            raw = response.content[0].text.strip()

            if raw.startswith("```"):
                raw = raw.split("```")[1]
                if raw.startswith("json"):
                    raw = raw[4:]
                raw = raw.strip()

            batch = json.loads(raw)

            # Handle both array and object responses
            if isinstance(batch, dict):
                if "test_cases" in batch:
                    batch = batch["test_cases"]
                else:
                    # Try to find any list value in the dict
                    for v in batch.values():
                        if isinstance(v, list):
                            batch = v
                            break

            if not isinstance(batch, list):
                raise ValueError(f"Expected a list, got {type(batch)}")

            # Validate each item is a dict with required fields
            valid_batch = []
            for item in batch:
                if isinstance(item, dict) and item.get("tc_id") and item.get("title"):
                    valid_batch.append(item)

            return valid_batch

        except (json.JSONDecodeError, ValueError) as e:
            last_error = f"Batch parse error on attempt {attempt + 1}: {str(e)}"
            if circuit_breaker:
                circuit_breaker.record_retry(f"TC Writer Batch {categories[0]}")
            if attempt < max_retries - 1:
                time.sleep(2)
            continue

        except Exception as e:
            last_error = f"API error on attempt {attempt + 1}: {str(e)}"
            if circuit_breaker:
                circuit_breaker.record_retry(f"TC Writer Batch {categories[0]}")
            if attempt < max_retries - 1:
                time.sleep(2)
            continue

    print(f"WARNING: Batch {categories} failed: {last_error}")
    return []


def write_test_cases(
    requirement,
    requirements_analysis,
    risk_assessment,
    test_strategy,
    workflow_state=None,
    circuit_breaker=None,
    correction_notes=None,
    correction_attempt=False
):
    """
    Writes comprehensive test cases using adaptive chunked generation.
    Batch count and size adapt to requirement complexity.
    """

    agent_name = "Test Case Writer"
    agent_start_time = time.time()

    if circuit_breaker:
        circuit_breaker.check_all(agent_name, agent_start_time)

    client = Anthropic(api_key=os.getenv("ANTHROPIC_API_KEY"))

    # Calculate complexity and get batch config
    complexity = calculate_complexity(requirement, requirements_analysis, risk_assessment)
    security_required = test_strategy.get("security_testing_required", False)
    performance_required = test_strategy.get("performance_testing_required", False)

    batch_config = get_batch_config(complexity, security_required, performance_required)

    print(f"  Requirement complexity: {complexity}")
    print(f"  Batch plan: {len(batch_config)} batches")

    # Build special instructions
    special_parts = []
    if security_required:
        special_parts.append(
            "Security testing required: include SQL injection, XSS, "
            "unauthorised access, and authentication bypass cases."
        )
    if performance_required:
        special_parts.append(
            "Performance testing required: include response time, "
            "concurrent users, and load limit cases."
        )
    if test_strategy.get("regression_testing_required"):
        special_parts.append(
            "Include integration cases verifying existing functionality is not broken."
        )
    special_instructions = " ".join(special_parts)

    all_test_cases = []

    for i, batch in enumerate(batch_config, 1):
        categories = batch["categories"]
        count = batch["count"]
        start_id = len(all_test_cases) + 1

        print(f"  Generating Batch {i}: {', '.join(categories)} ({count} cases)...")

        batch_result = generate_batch(
            client=client,
            requirement=requirement,
            requirements_analysis=requirements_analysis,
            risk_assessment=risk_assessment,
            test_strategy=test_strategy,
            categories=categories,
            case_count=count,
            start_tc_id=start_id,
            special_instructions=special_instructions,
            circuit_breaker=circuit_breaker,
            workflow_state=workflow_state
        )
        all_test_cases.extend(batch_result)

    # Renumber all TC IDs sequentially
    for i, tc in enumerate(all_test_cases, 1):
        tc["tc_id"] = f"TC_{i:03d}"

    categories_covered = list(set(
        tc.get("category", "") for tc in all_test_cases
        if tc.get("category")
    ))

    coverage_summary = (
        f"Generated {len(all_test_cases)} test cases across "
        f"{len(categories_covered)} categories using adaptive "
        f"{len(batch_config)}-batch generation for {complexity} complexity requirement."
    )

    result = {
        "test_cases": all_test_cases,
        "total_count": len(all_test_cases),
        "categories_covered": categories_covered,
        "coverage_summary": coverage_summary,
        "missing_coverage": "Run coverage analyser with existing test suite for gap analysis.",
        "complexity_level": complexity,
        "batch_count": len(batch_config),
        "batch_details": {
            f"batch_{i}": {
                "categories": b["categories"],
                "requested": b["count"]
            }
            for i, b in enumerate(batch_config, 1)
        }
    }

    if workflow_state and not correction_attempt:
        workflow_state.completed_agents.append(agent_name)

    return result
