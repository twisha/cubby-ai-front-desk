"""Health-form (CD-51) extraction + validation models.

The vision model extracts to HealthFormExtraction. Deterministic code in
core/rules/validation.py turns that into a ValidationResult. The model never
decides accept/reject — it only reports what is visibly on the form.
"""
from __future__ import annotations

from datetime import date
from typing import Literal

from pydantic import BaseModel


class HealthFormExtraction(BaseModel):
    """LLM structured output for /api/validate-form (Sonnet vision)."""
    child_name: str | None
    date_of_exam: date | None
    examiner_name: str | None
    # 3270.131(c): report signed by physician/PA/CRNP with professional title.
    examiner_credential: Literal["MD", "DO", "PA-C", "CRNP"] | None
    # The EXAMINER's signature specifically — forms also carry a parent
    # signature; the extractor must not conflate them.
    examiner_signature_present: bool
    parent_signature_present: bool
    immunizations_section_completed: bool
    notes: str | None                     # anything ambiguous/illegible


class ValidationIssue(BaseModel):
    field: str
    problem: str                          # human-readable, parent-friendly
    fix: str                              # e.g. "Ask Dr. Patel's office to fax a signed copy"


class ValidationResult(BaseModel):
    status: Literal["accepted", "rejected", "needs_review"]
    issues: list[ValidationIssue]
    next_due_date: date | None            # computed if accepted
