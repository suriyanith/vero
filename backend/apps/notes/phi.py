"""PHI tripwire: reject notes that look like they contain real identifiers.

This is a guardrail against accidental pastes of real patient data, NOT a
de-identification tool — the docs must say so plainly. It scans for likely
identifiers and rejects the whole note if anything matches.
"""

import re

# Each pattern is deliberately narrow: clinical text is full of numbers
# (BP 128/76, doses, lab values) that must not trip it.
PHI_PATTERNS: dict[str, re.Pattern[str]] = {
    "ssn": re.compile(r"\b\d{3}-\d{2}-\d{4}\b"),
    "phone": re.compile(r"(?:\(\d{3}\)\s?|\b\d{3}[-.])\d{3}[-.]\d{4}\b"),
    "email": re.compile(r"\b[\w.+-]+@[\w-]+\.[\w.-]+\b"),
    "mrn": re.compile(r"(?i)\b(?:MRN|medical record (?:number|#)|chart (?:number|#))\s*[:#]?\s*\w"),
    "dob": re.compile(r"(?i)\b(?:DOB|date of birth)\s*[:#]?\s*\d"),
}


def find_phi(text: str) -> list[str]:
    """Return the identifier kinds found, empty when the note looks clean."""
    return [kind for kind, pattern in PHI_PATTERNS.items() if pattern.search(text)]
