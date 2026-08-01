"""
Input Validator
---------------
The first line of defence before any agent runs.
Validates and sanitises the user requirement input.

Problems this solves:
- Prevents empty or meaningless inputs from wasting API calls
- Catches prompt injection attempts in the requirement text
- Detects requirements that are too vague to generate useful test cases
- Ensures input length is within usable bounds
"""

import re
from dataclasses import dataclass


# Known prompt injection patterns to block
INJECTION_PATTERNS = [
    r"ignore previous instructions",
    r"ignore all instructions",
    r"forget your role",
    r"you are now",
    r"act as",
    r"disregard",
    r"override",
    r"system prompt",
    r"jailbreak",
]

# Minimum and maximum character limits
MIN_LENGTH = 20
MAX_LENGTH = 5000


@dataclass
class ValidationResult:
    """Holds the result of input validation."""
    is_valid: bool
    cleaned_input: str
    error_message: str = ""
    warnings: list = None

    def __post_init__(self):
        if self.warnings is None:
            self.warnings = []


def validate_input(requirement: str) -> ValidationResult:
    """
    Validates and sanitises user requirement input.

    Args:
        requirement: The raw requirement text from the user

    Returns:
        ValidationResult with is_valid flag and cleaned input
    """

    # Check for empty or whitespace only input
    if not requirement or not requirement.strip():
        return ValidationResult(
            is_valid=False,
            cleaned_input="",
            error_message="Requirement cannot be empty. Please describe the feature you want to test."
        )

    # Clean the input - strip leading/trailing whitespace
    cleaned = requirement.strip()

    # Check minimum length
    if len(cleaned) < MIN_LENGTH:
        return ValidationResult(
            is_valid=False,
            cleaned_input=cleaned,
            error_message=f"Requirement is too short ({len(cleaned)} characters). "
                         f"Please provide at least {MIN_LENGTH} characters describing the feature."
        )

    # Check maximum length
    if len(cleaned) > MAX_LENGTH:
        return ValidationResult(
            is_valid=False,
            cleaned_input=cleaned,
            error_message=f"Requirement is too long ({len(cleaned)} characters). "
                         f"Please keep it under {MAX_LENGTH} characters. "
                         f"Split large requirements into smaller features."
        )

    # Check for prompt injection patterns
    cleaned_lower = cleaned.lower()
    for pattern in INJECTION_PATTERNS:
        if re.search(pattern, cleaned_lower):
            return ValidationResult(
                is_valid=False,
                cleaned_input="",
                error_message="Invalid input detected. The requirement text contains instructions "
                             "that cannot be processed. Please provide a genuine feature description."
            )

    # Collect warnings for low quality inputs
    warnings = []

    # Warn if requirement looks too generic
    generic_phrases = ["test this", "test everything", "test the app", "test the system"]
    if any(phrase in cleaned_lower for phrase in generic_phrases):
        warnings.append(
            "Your requirement is quite generic. More specific requirements produce better test cases."
        )

    # Warn if no acceptance criteria detected
    acceptance_keywords = ["should", "must", "shall", "when", "if", "after", "before", "then"]
    if not any(keyword in cleaned_lower for keyword in acceptance_keywords):
        warnings.append(
            "No acceptance criteria detected. Consider adding conditions like "
            "'should', 'must', 'when', or 'after' to describe expected behaviour."
        )

    # Warn if very short (above minimum but still short)
    if len(cleaned) < 100:
        warnings.append(
            "Short requirement detected. More detail produces more comprehensive test cases."
        )

    return ValidationResult(
        is_valid=True,
        cleaned_input=cleaned,
        warnings=warnings
    )


def validate_csv_file(file_path: str) -> ValidationResult:
    """
    Validates an uploaded existing test suite CSV file.
    Used by Coverage Analyser agent (Agent 5).

    Args:
        file_path: Path to the CSV file

    Returns:
        ValidationResult indicating if file is usable
    """
    import os

    # Check file exists
    if not os.path.exists(file_path):
        return ValidationResult(
            is_valid=False,
            cleaned_input="",
            error_message=f"File not found: {file_path}"
        )

    # Check file is not empty
    if os.path.getsize(file_path) == 0:
        return ValidationResult(
            is_valid=False,
            cleaned_input="",
            error_message="The CSV file is empty."
        )

    # Check file extension
    if not file_path.lower().endswith(".csv"):
        return ValidationResult(
            is_valid=False,
            cleaned_input="",
            error_message="File must be a CSV file (.csv extension)."
        )

    # Try reading the file to check it is valid CSV
    try:
        import csv
        with open(file_path, "r", encoding="utf-8") as f:
            reader = csv.reader(f)
            rows = list(reader)

        if len(rows) < 2:
            return ValidationResult(
                is_valid=False,
                cleaned_input="",
                error_message="CSV file must have at least a header row and one test case row."
            )

        return ValidationResult(
            is_valid=True,
            cleaned_input=file_path,
            warnings=[f"Found {len(rows) - 1} existing test cases to compare against."]
        )

    except Exception as e:
        return ValidationResult(
            is_valid=False,
            cleaned_input="",
            error_message=f"Could not read CSV file: {str(e)}"
        )
