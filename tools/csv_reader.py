"""
CSV Reader Tool
---------------
Reads an existing test suite CSV file for use by
Coverage Analyser (Agent 5).

Handles common CSV format issues gracefully:
- Different column name conventions
- Missing columns
- Encoding issues
- Empty files
"""

import csv
import os
from dataclasses import dataclass
from typing import Optional


@dataclass
class TestSuiteData:
    """Holds parsed test suite data from a CSV file."""
    test_cases: list
    total_count: int
    columns_found: list
    warnings: list
    file_path: str


# Common column name variations we try to map
COLUMN_MAPPINGS = {
    "id": ["tc_id", "test_id", "id", "case_id", "no", "number"],
    "title": ["title", "name", "test_name", "summary", "description"],
    "category": ["category", "type", "test_type", "classification"],
    "priority": ["priority", "severity", "importance"],
    "status": ["status", "result", "execution_status"],
    "steps": ["steps", "test_steps", "procedure", "actions"],
    "expected_result": ["expected_result", "expected", "expected_outcome"]
}


def read_test_suite(file_path: str) -> Optional[TestSuiteData]:
    """
    Reads a test suite CSV and returns structured data.

    Args:
        file_path: Path to the CSV file

    Returns:
        TestSuiteData object or None if file cannot be read
    """
    warnings = []

    if not os.path.exists(file_path):
        return None

    try:
        # Try UTF-8 first, fall back to latin-1
        encoding = "utf-8"
        try:
            with open(file_path, "r", encoding="utf-8") as f:
                f.read()
        except UnicodeDecodeError:
            encoding = "latin-1"
            warnings.append("File encoding is not UTF-8. Using latin-1 fallback.")

        with open(file_path, "r", encoding=encoding) as f:
            reader = csv.DictReader(f)
            raw_rows = list(reader)
            original_columns = reader.fieldnames or []

        if not raw_rows:
            return TestSuiteData(
                test_cases=[],
                total_count=0,
                columns_found=list(original_columns),
                warnings=["CSV file has no data rows."],
                file_path=file_path
            )

        # Map column names to standard names
        column_map = {}
        original_lower = {col.lower().strip(): col for col in original_columns}

        for standard_name, variations in COLUMN_MAPPINGS.items():
            for variation in variations:
                if variation in original_lower:
                    column_map[standard_name] = original_lower[variation]
                    break

        if "title" not in column_map:
            warnings.append(
                "Could not identify a title/name column. "
                "Coverage analysis may be less accurate."
            )

        # Normalise rows to standard column names
        normalised_rows = []
        for row in raw_rows:
            normalised = {}
            for standard_name, original_name in column_map.items():
                normalised[standard_name] = row.get(original_name, "").strip()
            # Keep all original columns too
            normalised["_original"] = dict(row)
            normalised_rows.append(normalised)

        return TestSuiteData(
            test_cases=normalised_rows,
            total_count=len(normalised_rows),
            columns_found=list(original_columns),
            warnings=warnings,
            file_path=file_path
        )

    except Exception as e:
        return TestSuiteData(
            test_cases=[],
            total_count=0,
            columns_found=[],
            warnings=[f"Error reading file: {str(e)}"],
            file_path=file_path
        )


def format_for_agent(test_suite: TestSuiteData, max_cases: int = 50) -> str:
    """
    Formats test suite data as text for passing to an agent.
    Limits output to avoid context window overflow.

    Args:
        test_suite: Parsed test suite data
        max_cases: Maximum number of test cases to include

    Returns:
        Formatted string summary of the test suite
    """
    if not test_suite or not test_suite.test_cases:
        return "No existing test suite provided."

    lines = [
        f"EXISTING TEST SUITE: {test_suite.total_count} test cases found",
        f"File: {os.path.basename(test_suite.file_path)}",
        ""
    ]

    if test_suite.warnings:
        lines.append("Warnings:")
        for w in test_suite.warnings:
            lines.append(f"  - {w}")
        lines.append("")

    lines.append(f"Test cases (showing first {min(max_cases, test_suite.total_count)}):")

    for i, tc in enumerate(test_suite.test_cases[:max_cases]):
        title = tc.get("title") or tc.get("_original", {}).get(
            list(tc.get("_original", {}).keys())[1] if len(tc.get("_original", {}).keys()) > 1 else "", ""
        )
        category = tc.get("category", "Unknown")
        priority = tc.get("priority", "Unknown")
        lines.append(f"  {i+1}. [{category}] {title} (Priority: {priority})")

    if test_suite.total_count > max_cases:
        lines.append(f"  ... and {test_suite.total_count - max_cases} more test cases")

    return "\n".join(lines)
