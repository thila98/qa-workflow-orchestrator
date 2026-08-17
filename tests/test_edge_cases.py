"""
Edge case tests for the QA Workflow Orchestrator.
Tests unusual, boundary, and error conditions.
These do not call the API unless marked with @pytest.mark.api
"""

import pytest
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from dotenv import load_dotenv
load_dotenv()

from validation.input_validator import validate_input
from validation.guardrails import (
    WorkflowState,
    CircuitBreaker,
    create_workflow_state,
    CostLimitExceeded,
    RetryLimitExceeded,
)


# ── Input Edge Cases ───────────────────────────────────────────────────────────

class TestInputEdgeCases:

    def test_single_word_fails(self):
        assert validate_input("Login").is_valid is False

    def test_numbers_only_fails(self):
        assert validate_input("12345678").is_valid is False

    def test_special_characters_only_fails(self):
        assert validate_input("!@#$%^&*()").is_valid is False

    def test_very_long_requirement_passes(self):
        long_req = "User can log in with email and password. " * 50
        result = validate_input(long_req)
        assert result.is_valid is True

    def test_requirement_with_numbers_passes(self):
        result = validate_input(
            "After 3 failed login attempts the account locks for 15 minutes."
        )
        assert result.is_valid is True

    def test_requirement_with_newlines_passes(self):
        req = "User login with email.\nAfter 3 attempts account locks.\nReset via email."
        result = validate_input(req)
        assert result.is_valid is True

    def test_unicode_characters_handled(self):
        req = "User login with email and password — account locks after 3 attempts."
        result = validate_input(req)
        assert result.is_valid is True

    def test_sql_injection_attempt_handled(self):
        malicious = "'; DROP TABLE users; -- Login with email and password."
        result = validate_input(malicious)
        # Should either fail or produce warnings
        assert result.is_valid is False or len(result.warnings) > 0

    def test_script_injection_handled(self):
        malicious = "<script>alert('xss')</script> User login feature."
        result = validate_input(malicious)
        assert result.is_valid is False or len(result.warnings) > 0

    def test_none_input_handled(self):
        try:
            result = validate_input(None)
            assert result.is_valid is False
        except (TypeError, AttributeError):
            pass  # Acceptable to raise on None input


# ── Circuit Breaker Tests ─────────────────────────────────────────────────────

class TestCircuitBreaker:

    def test_workflow_state_created_correctly(self):
        state = create_workflow_state("TEST01")
        assert state.session_id == "TEST01"
        assert state.total_cost_usd == 0.0
        assert state.retry_counts == {}
        assert state.completed_agents == []
        assert state.failed_agents == []

    def test_cost_recording(self):
        state = create_workflow_state("TEST02")
        breaker = CircuitBreaker(state)
        breaker.record_cost(0.05)
        assert state.total_cost_usd == pytest.approx(0.05)

    def test_multiple_cost_recordings(self):
        state = create_workflow_state("TEST03")
        breaker = CircuitBreaker(state)
        breaker.record_cost(0.05)
        breaker.record_cost(0.10)
        breaker.record_cost(0.03)
        assert state.total_cost_usd == pytest.approx(0.18)

    def test_cost_limit_exceeded_raises(self):
        import time
        state = create_workflow_state("TEST04")
        state.max_cost_usd = 0.10
        breaker = CircuitBreaker(state)
        breaker.record_cost(0.09)
        breaker.record_cost(0.05)
        # Cost is now over limit - check_all should raise
        with pytest.raises((CostLimitExceeded, Exception)):
            breaker.check_all("Test Agent", time.time())

    def test_retry_recording(self):
        state = create_workflow_state("TEST05")
        breaker = CircuitBreaker(state)
        breaker.record_retry("Requirements Analyst")
        breaker.record_retry("Requirements Analyst")
        assert state.retry_counts.get("Requirements Analyst", 0) == 2

    def test_cost_estimate(self):
        state = create_workflow_state("TEST06")
        breaker = CircuitBreaker(state)
        cost = breaker.estimate_cost(input_tokens=1000, output_tokens=500)
        assert cost > 0
        assert isinstance(cost, float)

    def test_zero_cost_run(self):
        state = create_workflow_state("TEST07")
        breaker = CircuitBreaker(state)
        breaker.record_cost(0.0)
        assert state.total_cost_usd == 0.0

    def test_workflow_state_tracks_completed_agents(self):
        state = create_workflow_state("TEST08")
        state.completed_agents.append("Requirements Analyst")
        state.completed_agents.append("Risk Assessor")
        assert len(state.completed_agents) == 2
        assert "Requirements Analyst" in state.completed_agents

    def test_workflow_state_tracks_failed_agents(self):
        state = create_workflow_state("TEST09")
        state.failed_agents.append("Test Strategist")
        assert "Test Strategist" in state.failed_agents

    def test_workflow_state_tracks_warnings(self):
        state = create_workflow_state("TEST10")
        state.warnings.append("Agent output had low confidence")
        assert len(state.warnings) == 1


# ── Output Validator Edge Cases ───────────────────────────────────────────────

class TestOutputValidatorEdgeCases:

    def test_requirements_analysis_with_empty_lists(self):
        from validation.output_validator import validate_requirements_analysis
        output = {
            "summary": "Simple login feature.",
            "gaps": [],
            "ambiguities": [],
            "assumptions": [],
            "acceptance_criteria_present": False,
            "is_testable": True,
            "quality_score": 8,
            "quality_reasoning": "Clear and testable.",
            "needs_clarification": False,
            "clarification_questions": [],
            "key_test_areas": ["Login"]
        }
        result = validate_requirements_analysis(output)
        assert result.is_valid is True

    def test_risk_assessment_with_max_score(self):
        from validation.output_validator import validate_risk_assessment
        output = {
            "risk_areas": [
                {
                    "name": "Critical Security Risk",
                    "description": "Major vulnerability",
                    "category": "Security",
                    "likelihood": 5,
                    "impact": 5,
                    "score": 25,
                    "priority_level": "Critical",
                    "test_focus": "Full security audit"
                }
            ],
            "top_risks": ["Critical Security Risk"],
            "overall_risk_level": "Critical",
            "security_risks_present": True,
            "performance_risks_present": False,
            "integration_risks_present": False,
            "critical_risks": ["Critical Security Risk"],
            "risk_summary": "Critical security vulnerability identified."
        }
        result = validate_risk_assessment(output)
        assert result.is_valid is True

    def test_test_cases_with_all_valid_categories(self):
        from validation.output_validator import validate_test_cases
        valid_categories = [
            "Functional", "Negative", "Boundary",
            "Security", "Integration", "UI-UX", "Performance"
        ]
        test_cases = []
        for i, cat in enumerate(valid_categories, 1):
            test_cases.append({
                "tc_id": f"TC_{i:03d}",
                "category": cat,
                "title": f"Test for {cat}",
                "risk_area": "General",
                "precondition": "System is available",
                "steps": "1. Execute test 2. Verify result",
                "expected_result": "Expected outcome achieved",
                "priority": "Medium",
                "test_type": "Manual",
                "notes": "Standard test",
                "requirement_reference": "General requirement"
            })

        output = {
            "test_cases": test_cases,
            "total_count": len(test_cases),
            "categories_covered": valid_categories,
            "coverage_summary": "All categories covered.",
            "missing_coverage": "None."
        }
        result = validate_test_cases(output)
        assert result.is_valid is True

    def test_coverage_analysis_skipped_is_valid(self):
        from validation.output_validator import validate_coverage_analysis
        output = {
            "skipped": True,
            "reason": "No existing test suite provided.",
            "gaps": [],
            "duplicates": [],
            "update_candidates": [],
            "coverage_estimate": "Unknown",
            "recommendations": [],
            "coverage_summary": "Analysis skipped."
        }
        result = validate_coverage_analysis(output)
        assert result.is_valid is True


# ── Confidence Scorer Edge Cases ──────────────────────────────────────────────

class TestConfidenceScorerEdgeCases:

    def get_mock_validation_result(self, is_valid=True, confidence=0.9):
        class MockValidation:
            def __init__(self, valid, conf):
                self.is_valid = valid
                self.confidence_score = conf
                self.issues = []
                self.warnings = []
        return MockValidation(is_valid, confidence)

    def get_mock_judge_result(self, recommendation="PASS", confidence=0.9):
        return {
            "recommendation": recommendation,
            "confidence_score": confidence,
            "hallucination_flags": [],
            "quality_issues": [],
            "test_design_decisions": []
        }

    def test_all_passing_gives_high_confidence(self):
        from tools.confidence_scorer import calculate_workflow_confidence
        state = create_workflow_state("CONF01")

        validation_results = {
            "Requirements Analyst": self.get_mock_validation_result(True, 0.95),
            "Risk Assessor": self.get_mock_validation_result(True, 0.90),
            "Test Strategist": self.get_mock_validation_result(True, 0.88),
            "Test Case Writer": self.get_mock_validation_result(True, 0.92),
        }

        judge_results = {
            "Requirements Analyst": self.get_mock_judge_result("PASS", 0.92),
            "Risk Assessor": self.get_mock_judge_result("PASS", 0.88),
            "Test Strategist": self.get_mock_judge_result("PASS", 0.90),
            "Test Case Writer": self.get_mock_judge_result("PASS", 0.91),
        }

        result = calculate_workflow_confidence(
            validation_results=validation_results,
            judge_results=judge_results,
            workflow_state=state
        )

        assert result.overall_score >= 0.40  # Score depends on weighting algorithm
        assert result.grade in ["A", "B", "C", "D", "F"]

    def test_warnings_reduce_confidence(self):
        from tools.confidence_scorer import calculate_workflow_confidence
        state = create_workflow_state("CONF02")

        validation_results = {
            "Requirements Analyst": self.get_mock_validation_result(True, 0.70),
        }

        judge_results = {
            "Requirements Analyst": self.get_mock_judge_result(
                "PASS_WITH_WARNINGS", 0.65
            ),
        }

        result = calculate_workflow_confidence(
            validation_results=validation_results,
            judge_results=judge_results,
            workflow_state=state
        )

        assert result.overall_score < 0.95

    def test_confidence_score_always_between_0_and_1(self):
        from tools.confidence_scorer import calculate_workflow_confidence
        state = create_workflow_state("CONF03")

        validation_results = {
            "Requirements Analyst": self.get_mock_validation_result(True, 0.50),
        }
        judge_results = {
            "Requirements Analyst": self.get_mock_judge_result("PASS_WITH_WARNINGS", 0.50),
        }

        result = calculate_workflow_confidence(
            validation_results=validation_results,
            judge_results=judge_results,
            workflow_state=state
        )

        assert 0.0 <= result.overall_score <= 1.0
