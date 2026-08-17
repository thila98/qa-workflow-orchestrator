"""
Tests for individual agents.
These tests call the real Claude API — they cost money.
Run with: pytest tests/test_agents.py -v
Skip with: pytest tests/ -v --ignore=tests/test_agents.py
"""

import pytest
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from dotenv import load_dotenv
load_dotenv()

# Skip all tests if no API key present
pytestmark = pytest.mark.skipif(
    not os.getenv("ANTHROPIC_API_KEY"),
    reason="ANTHROPIC_API_KEY not set"
)

SIMPLE_REQUIREMENT = (
    "User login with email and password. "
    "After 3 failed attempts the account locks for 15 minutes. "
    "Password reset via email link that expires after 24 hours."
)


class TestRequirementsAnalyst:

    def test_returns_valid_structure(self):
        from agents.requirements_analyst import analyse_requirements
        result = analyse_requirements(requirement=SIMPLE_REQUIREMENT)

        assert isinstance(result, dict)
        assert "summary" in result
        assert "gaps" in result
        assert "quality_score" in result
        assert "is_testable" in result
        assert "key_test_areas" in result

    def test_quality_score_in_range(self):
        from agents.requirements_analyst import analyse_requirements
        result = analyse_requirements(requirement=SIMPLE_REQUIREMENT)

        assert isinstance(result["quality_score"], int)
        assert 1 <= result["quality_score"] <= 10

    def test_gaps_is_list(self):
        from agents.requirements_analyst import analyse_requirements
        result = analyse_requirements(requirement=SIMPLE_REQUIREMENT)
        assert isinstance(result["gaps"], list)

    def test_summary_is_non_empty_string(self):
        from agents.requirements_analyst import analyse_requirements
        result = analyse_requirements(requirement=SIMPLE_REQUIREMENT)
        assert isinstance(result["summary"], str)
        assert len(result["summary"]) > 10

    def test_correction_notes_accepted(self):
        from agents.requirements_analyst import analyse_requirements
        result = analyse_requirements(
            requirement=SIMPLE_REQUIREMENT,
            correction_notes="Please add more clarification questions.",
            correction_attempt=True
        )
        assert isinstance(result, dict)
        assert "quality_score" in result


class TestRiskAssessor:

    def get_mock_req_analysis(self):
        return {
            "summary": "Login feature with lockout after 3 failed attempts.",
            "gaps": ["Lockout notification method not specified"],
            "quality_score": 6,
            "key_test_areas": ["Login", "Lockout", "Password reset"],
            "is_testable": True,
            "needs_clarification": False,
            "ambiguities": [],
            "assumptions": [],
            "clarification_questions": [],
            "acceptance_criteria_present": False,
            "quality_reasoning": "Core flow clear but edge cases missing."
        }

    def test_returns_valid_structure(self):
        from agents.risk_assessor import assess_risks
        result = assess_risks(
            requirement=SIMPLE_REQUIREMENT,
            requirements_analysis=self.get_mock_req_analysis()
        )

        assert isinstance(result, dict)
        assert "risk_areas" in result
        assert "overall_risk_level" in result
        assert "security_risks_present" in result
        assert "risk_summary" in result

    def test_overall_risk_level_valid(self):
        from agents.risk_assessor import assess_risks
        result = assess_risks(
            requirement=SIMPLE_REQUIREMENT,
            requirements_analysis=self.get_mock_req_analysis()
        )
        assert result["overall_risk_level"] in ["Low", "Medium", "High", "Critical"]

    def test_risk_areas_not_empty(self):
        from agents.risk_assessor import assess_risks
        result = assess_risks(
            requirement=SIMPLE_REQUIREMENT,
            requirements_analysis=self.get_mock_req_analysis()
        )
        assert len(result["risk_areas"]) > 0

    def test_risk_score_equals_likelihood_times_impact(self):
        from agents.risk_assessor import assess_risks
        result = assess_risks(
            requirement=SIMPLE_REQUIREMENT,
            requirements_analysis=self.get_mock_req_analysis()
        )
        for risk in result["risk_areas"]:
            expected = risk["likelihood"] * risk["impact"]
            assert risk["score"] == expected, (
                f"Risk '{risk['name']}': score {risk['score']} "
                f"!= likelihood {risk['likelihood']} x impact {risk['impact']}"
            )

    def test_security_risk_flag_accurate(self):
        from agents.risk_assessor import assess_risks
        result = assess_risks(
            requirement=SIMPLE_REQUIREMENT,
            requirements_analysis=self.get_mock_req_analysis()
        )
        # Login feature should have security risks
        assert isinstance(result["security_risks_present"], bool)


class TestTestCaseWriter:

    def get_mock_inputs(self):
        req_analysis = {
            "summary": "Login feature with lockout.",
            "gaps": [],
            "quality_score": 7,
            "key_test_areas": ["Login", "Lockout"],
            "is_testable": True,
            "needs_clarification": False,
            "ambiguities": [],
            "assumptions": [],
            "clarification_questions": [],
            "acceptance_criteria_present": False,
            "quality_reasoning": "Clear requirement."
        }

        risk = {
            "risk_areas": [
                {
                    "name": "Brute Force",
                    "description": "Multiple login attempts",
                    "category": "Security",
                    "likelihood": 4,
                    "impact": 5,
                    "score": 20,
                    "priority_level": "High",
                    "test_focus": "Verify lockout after 3 attempts"
                }
            ],
            "top_risks": ["Brute Force"],
            "overall_risk_level": "High",
            "security_risks_present": True,
            "performance_risks_present": False,
            "integration_risks_present": False,
            "critical_risks": [],
            "risk_summary": "Security risk from brute force attacks."
        }

        strategy = {
            "strategy_summary": "Focus on security and boundary testing.",
            "test_types": [],
            "priorities": [],
            "manual_tests": ["Login flow"],
            "automated_tests": ["Regression suite"],
            "entry_criteria": ["Feature deployed"],
            "exit_criteria": ["All tests passed"],
            "out_of_scope": [],
            "estimated_test_cases": 15,
            "estimated_hours": 4,
            "security_testing_required": True,
            "performance_testing_required": False,
            "regression_testing_required": True,
            "recommendations": []
        }
        return req_analysis, risk, strategy

    def test_returns_valid_structure(self):
        from agents.test_case_writer import write_test_cases
        req_analysis, risk, strategy = self.get_mock_inputs()

        result = write_test_cases(
            requirement=SIMPLE_REQUIREMENT,
            requirements_analysis=req_analysis,
            risk_assessment=risk,
            test_strategy=strategy
        )

        assert isinstance(result, dict)
        assert "test_cases" in result
        assert "total_count" in result
        assert "categories_covered" in result

    def test_generates_multiple_test_cases(self):
        from agents.test_case_writer import write_test_cases
        req_analysis, risk, strategy = self.get_mock_inputs()

        result = write_test_cases(
            requirement=SIMPLE_REQUIREMENT,
            requirements_analysis=req_analysis,
            risk_assessment=risk,
            test_strategy=strategy
        )

        assert result["total_count"] >= 5

    def test_test_cases_have_required_fields(self):
        from agents.test_case_writer import write_test_cases
        req_analysis, risk, strategy = self.get_mock_inputs()

        result = write_test_cases(
            requirement=SIMPLE_REQUIREMENT,
            requirements_analysis=req_analysis,
            risk_assessment=risk,
            test_strategy=strategy
        )

        required_fields = [
            "tc_id", "category", "title", "precondition",
            "steps", "expected_result", "priority", "test_type"
        ]

        for tc in result["test_cases"]:
            for field in required_fields:
                assert field in tc, f"Missing field '{field}' in {tc.get('tc_id', 'unknown')}"

    def test_tc_ids_are_sequential(self):
        from agents.test_case_writer import write_test_cases
        req_analysis, risk, strategy = self.get_mock_inputs()

        result = write_test_cases(
            requirement=SIMPLE_REQUIREMENT,
            requirements_analysis=req_analysis,
            risk_assessment=risk,
            test_strategy=strategy
        )

        for i, tc in enumerate(result["test_cases"], 1):
            expected_id = f"TC_{i:03d}"
            assert tc["tc_id"] == expected_id, (
                f"Expected {expected_id}, got {tc['tc_id']}"
            )

    def test_covers_multiple_categories(self):
        from agents.test_case_writer import write_test_cases
        req_analysis, risk, strategy = self.get_mock_inputs()

        result = write_test_cases(
            requirement=SIMPLE_REQUIREMENT,
            requirements_analysis=req_analysis,
            risk_assessment=risk,
            test_strategy=strategy
        )

        assert len(result["categories_covered"]) >= 2


class TestJudgeAgent:

    def get_mock_req_analysis(self):
        return {
            "summary": "Login feature with lockout.",
            "gaps": [],
            "quality_score": 7,
            "key_test_areas": ["Login", "Lockout"],
            "is_testable": True,
            "needs_clarification": False,
            "ambiguities": [],
            "assumptions": [],
            "clarification_questions": [],
            "acceptance_criteria_present": False,
            "quality_reasoning": "Clear."
        }

    def test_returns_valid_structure(self):
        from agents.judge_agent import judge_output
        result = judge_output(
            agent_name="Requirements Analyst",
            original_input=SIMPLE_REQUIREMENT,
            agent_output=self.get_mock_req_analysis(),
            previous_outputs={}
        )

        assert isinstance(result, dict)
        assert "recommendation" in result
        assert "confidence_score" in result
        assert "hallucination_flags" in result

    def test_recommendation_is_valid_value(self):
        from agents.judge_agent import judge_output
        result = judge_output(
            agent_name="Requirements Analyst",
            original_input=SIMPLE_REQUIREMENT,
            agent_output=self.get_mock_req_analysis(),
            previous_outputs={}
        )
        assert result["recommendation"] in ["PASS", "PASS_WITH_WARNINGS", "FAIL"]

    def test_confidence_score_in_range(self):
        from agents.judge_agent import judge_output
        result = judge_output(
            agent_name="Requirements Analyst",
            original_input=SIMPLE_REQUIREMENT,
            agent_output=self.get_mock_req_analysis(),
            previous_outputs={}
        )
        assert 0.0 <= result["confidence_score"] <= 1.0

    def test_good_output_passes(self):
        from agents.judge_agent import judge_output
        result = judge_output(
            agent_name="Requirements Analyst",
            original_input=SIMPLE_REQUIREMENT,
            agent_output=self.get_mock_req_analysis(),
            previous_outputs={}
        )
        assert result["recommendation"] in ["PASS", "PASS_WITH_WARNINGS"]
