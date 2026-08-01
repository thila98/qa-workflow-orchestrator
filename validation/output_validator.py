"""
Output Validator
----------------
Validates every agent output before it passes to the next agent.
This is how we prevent hallucination propagation.

The golden rule: never trust an agent output blindly.
Always verify structure, completeness, and basic sanity
before passing it downstream.

Problems this solves:
- Hallucination propagation between agents
- Silent failures where agent returns empty or malformed output
- Agents returning outputs that dont match the expected schema
- Missing required fields that downstream agents depend on
"""

from dataclasses import dataclass, field
from typing import Any


@dataclass
class OutputValidation:
    """Result of validating an agent output."""
    is_valid: bool
    confidence_score: float  # 0.0 to 1.0
    issues: list = field(default_factory=list)
    warnings: list = field(default_factory=list)
    validated_output: Any = None


def validate_requirements_analysis(output: dict) -> OutputValidation:
    """
    Validates output from Agent 1 - Requirements Analyst.

    Expected fields:
    - summary: brief summary of the requirement
    - gaps: list of missing information items
    - ambiguities: list of unclear statements
    - assumptions: list of unstated assumptions
    - quality_score: integer 1-10
    - is_testable: boolean
    - needs_clarification: boolean
    """
    issues = []
    warnings = []

    # Check output is a dictionary
    if not isinstance(output, dict):
        return OutputValidation(
            is_valid=False,
            confidence_score=0.0,
            issues=["Agent 1 output is not a valid dictionary."]
        )

    # Required fields
    required_fields = ["summary", "gaps", "ambiguities", "assumptions", "quality_score", "is_testable"]
    for field_name in required_fields:
        if field_name not in output:
            issues.append(f"Missing required field: {field_name}")

    if issues:
        return OutputValidation(is_valid=False, confidence_score=0.0, issues=issues)

    # Validate quality score range
    score = output.get("quality_score", 0)
    if not isinstance(score, (int, float)) or not (1 <= score <= 10):
        issues.append(f"quality_score must be a number between 1 and 10. Got: {score}")

    # Validate summary is not empty
    if not output.get("summary", "").strip():
        issues.append("Summary cannot be empty.")

    # Warn if no gaps found (unusual for most requirements)
    if not output.get("gaps"):
        warnings.append("No gaps identified. This is unusual - most requirements have at least one gap.")

    # Calculate confidence score based on completeness
    filled_fields = sum(1 for f in required_fields if output.get(f))
    confidence = filled_fields / len(required_fields)

    # Reduce confidence if quality score is very low
    if score and score < 4:
        confidence *= 0.7
        warnings.append(f"Low requirement quality score ({score}/10). Test cases may be incomplete.")

    return OutputValidation(
        is_valid=len(issues) == 0,
        confidence_score=round(confidence, 2),
        issues=issues,
        warnings=warnings,
        validated_output=output if len(issues) == 0 else None
    )


def validate_risk_assessment(output: dict) -> OutputValidation:
    """
    Validates output from Agent 2 - Risk Assessor.

    Expected fields:
    - risk_areas: list of risk items, each with name, likelihood, impact, score, category
    - top_risks: list of top 3-5 highest risk areas
    - overall_risk_level: Low / Medium / High / Critical
    - security_risks_present: boolean
    - performance_risks_present: boolean
    """
    issues = []
    warnings = []

    if not isinstance(output, dict):
        return OutputValidation(
            is_valid=False,
            confidence_score=0.0,
            issues=["Agent 2 output is not a valid dictionary."]
        )

    required_fields = ["risk_areas", "top_risks", "overall_risk_level"]
    for field_name in required_fields:
        if field_name not in output:
            issues.append(f"Missing required field: {field_name}")

    if issues:
        return OutputValidation(is_valid=False, confidence_score=0.0, issues=issues)

    # Validate risk areas structure
    risk_areas = output.get("risk_areas", [])
    if not isinstance(risk_areas, list):
        issues.append("risk_areas must be a list.")
    elif len(risk_areas) == 0:
        warnings.append("No risk areas identified. This may indicate a very simple feature.")
    else:
        # Validate each risk item has required sub-fields
        for i, risk in enumerate(risk_areas):
            if not isinstance(risk, dict):
                issues.append(f"Risk item {i+1} is not a valid object.")
                continue
            for sub_field in ["name", "likelihood", "impact", "score"]:
                if sub_field not in risk:
                    issues.append(f"Risk item {i+1} missing field: {sub_field}")

    # Validate overall risk level
    valid_levels = ["Low", "Medium", "High", "Critical"]
    if output.get("overall_risk_level") not in valid_levels:
        issues.append(f"overall_risk_level must be one of: {valid_levels}")

    confidence = 1.0 if len(issues) == 0 else 0.0
    if warnings:
        confidence *= 0.85

    return OutputValidation(
        is_valid=len(issues) == 0,
        confidence_score=round(confidence, 2),
        issues=issues,
        warnings=warnings,
        validated_output=output if len(issues) == 0 else None
    )


def validate_test_strategy(output: dict) -> OutputValidation:
    """
    Validates output from Agent 3 - Test Strategist.

    Expected fields:
    - test_types: list of testing types required
    - priorities: list of priority areas
    - manual_tests: list of areas needing manual testing
    - automated_tests: list of areas suitable for automation
    - entry_criteria: conditions before testing starts
    - exit_criteria: conditions that define done
    - estimated_test_cases: integer estimate
    """
    issues = []
    warnings = []

    if not isinstance(output, dict):
        return OutputValidation(
            is_valid=False,
            confidence_score=0.0,
            issues=["Agent 3 output is not a valid dictionary."]
        )

    required_fields = ["test_types", "priorities", "entry_criteria", "exit_criteria"]
    for field_name in required_fields:
        if field_name not in output:
            issues.append(f"Missing required field: {field_name}")

    if issues:
        return OutputValidation(is_valid=False, confidence_score=0.0, issues=issues)

    # Must have at least one test type
    if not output.get("test_types"):
        issues.append("test_types cannot be empty. At least one testing type must be recommended.")

    # Warn if no automation candidates
    if not output.get("automated_tests"):
        warnings.append("No automation candidates identified. Consider if any tests could be automated.")

    confidence = 0.9 if len(issues) == 0 else 0.0

    return OutputValidation(
        is_valid=len(issues) == 0,
        confidence_score=round(confidence, 2),
        issues=issues,
        warnings=warnings,
        validated_output=output if len(issues) == 0 else None
    )


def validate_test_cases(output: dict) -> OutputValidation:
    """
    Validates output from Agent 4 - Test Case Writer.

    Expected fields:
    - test_cases: list of test case objects
    - total_count: integer
    - categories_covered: list of categories

    Each test case must have:
    - tc_id, category, title, precondition, steps, expected_result, priority, test_type
    """
    issues = []
    warnings = []

    VALID_CATEGORIES = {"Functional", "Negative", "Boundary", "Security", "UI-UX", "Integration", "Performance"}
    VALID_PRIORITIES = {"High", "Medium", "Low"}
    VALID_TEST_TYPES = {"Manual", "Automated", "Manual/Automated"}

    if not isinstance(output, dict):
        return OutputValidation(
            is_valid=False,
            confidence_score=0.0,
            issues=["Agent 4 output is not a valid dictionary."]
        )

    if "test_cases" not in output:
        return OutputValidation(
            is_valid=False,
            confidence_score=0.0,
            issues=["Missing required field: test_cases"]
        )

    test_cases = output["test_cases"]
    if not isinstance(test_cases, list) or len(test_cases) == 0:
        return OutputValidation(
            is_valid=False,
            confidence_score=0.0,
            issues=["test_cases must be a non-empty list."]
        )

    # Validate each test case
    seen_ids = set()
    for i, tc in enumerate(test_cases):
        if not isinstance(tc, dict):
            issues.append(f"Test case {i+1} is not a valid object.")
            continue

        # Check required fields
        for req_field in ["tc_id", "category", "title", "steps", "expected_result", "priority"]:
            if not tc.get(req_field):
                issues.append(f"Test case {i+1} missing or empty field: {req_field}")

        # Check for duplicate IDs
        tc_id = tc.get("tc_id", "")
        if tc_id in seen_ids:
            issues.append(f"Duplicate TC_ID found: {tc_id}")
        seen_ids.add(tc_id)

        # Validate category
        if tc.get("category") and tc["category"] not in VALID_CATEGORIES:
            issues.append(f"{tc_id}: Invalid category '{tc['category']}'. Must be one of {VALID_CATEGORIES}")

        # Validate priority
        if tc.get("priority") and tc["priority"] not in VALID_PRIORITIES:
            issues.append(f"{tc_id}: Invalid priority '{tc['priority']}'. Must be High, Medium, or Low.")

        # Validate expected result is specific
        expected = tc.get("expected_result", "")
        vague_phrases = ["works correctly", "works as expected", "functions properly", "no errors"]
        if any(phrase in expected.lower() for phrase in vague_phrases):
            warnings.append(f"{tc_id}: Expected result is vague. Consider making it more specific.")

    # Warn if fewer than 10 test cases
    if len(test_cases) < 10:
        warnings.append(f"Only {len(test_cases)} test cases generated. Consider if coverage is sufficient.")

    # Check category coverage
    categories_found = {tc.get("category") for tc in test_cases if isinstance(tc, dict)}
    if "Security" not in categories_found:
        warnings.append("No Security test cases generated. Consider if security testing applies.")
    if "Negative" not in categories_found:
        warnings.append("No Negative test cases generated. These are important for robustness.")

    # Calculate confidence based on issue count and test case count
    if issues:
        confidence = max(0.0, 0.5 - (len(issues) * 0.1))
    else:
        confidence = min(1.0, 0.7 + (len(test_cases) / 100))

    return OutputValidation(
        is_valid=len(issues) == 0,
        confidence_score=round(confidence, 2),
        issues=issues,
        warnings=warnings,
        validated_output=output if len(issues) == 0 else None
    )


def validate_coverage_analysis(output: dict) -> OutputValidation:
    """
    Validates output from Agent 5 - Coverage Analyser.
    This agent is optional - only runs if existing test suite CSV provided.

    Expected fields:
    - gaps: list of uncovered scenarios
    - duplicates: list of potential duplicates with existing tests
    - coverage_estimate: percentage string
    - recommendations: list of recommended actions
    """
    issues = []
    warnings = []

    if not isinstance(output, dict):
        return OutputValidation(
            is_valid=False,
            confidence_score=0.0,
            issues=["Agent 5 output is not a valid dictionary."]
        )

    required_fields = ["gaps", "duplicates", "coverage_estimate", "recommendations"]
    for field_name in required_fields:
        if field_name not in output:
            issues.append(f"Missing required field: {field_name}")

    if issues:
        return OutputValidation(is_valid=False, confidence_score=0.0, issues=issues)

    # Warn if no gaps found - unusual unless test suite is very comprehensive
    if not output.get("gaps"):
        warnings.append("No coverage gaps found. Verify that the existing test suite was analysed correctly.")

    return OutputValidation(
        is_valid=len(issues) == 0,
        confidence_score=0.9 if len(issues) == 0 else 0.0,
        issues=issues,
        warnings=warnings,
        validated_output=output if len(issues) == 0 else None
    )
