"""Health-form (CD-51) extraction + validation models.

The vision model extracts to HealthFormExtraction. Deterministic code in
core/rules/validation.py turns that into a ValidationResult. The model never
decides accept/reject — it only reports what is visibly on the form.
"""
from __future__ import annotations

from datetime import date, datetime
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
    # DELIBERATE EXTENSION beyond the spec's literal field list: whether the
    # "has the child received all age-appropriate screenings currently
    # recommended by the AAP" box is checked YES. Not the same thing as
    # immunizations_section_completed (that's the vaccine-date table). Added
    # because the provided attestation-NO fixture is otherwise byte-for-byte
    # identical to the valid one (same signatures, same date, same
    # credential) — without this field the validator has no way to
    # distinguish them, even though catching "attestation checked NO" is
    # explicitly named as a required fixture case.
    screenings_up_to_date: bool | None
    notes: str | None                     # anything ambiguous/illegible


class ValidationIssue(BaseModel):
    field: str
    problem: str                          # human-readable, parent-friendly
    fix: str                              # e.g. "Ask Dr. Patel's office to fax a signed copy"


class ValidationResult(BaseModel):
    status: Literal["accepted", "rejected", "needs_review"]
    issues: list[ValidationIssue]
    next_due_date: date | None            # computed if accepted


class BatchScanItem(BaseModel):
    """One file's outcome within a bulk /api/validate-form request."""
    filename: str
    child_name: str | None                # resolved roster name, or the raw
                                           # extracted (unmatched) name, if any
    result: ValidationResult


class FlaggedForm(BaseModel):
    """A rejected/needs_review scan, persisted so it surfaces on the
    Dashboard instead of disappearing once the upload card is dismissed —
    the operator's job is to watch the dashboard, not babysit each scan."""
    id: str
    child_id: str | None                  # None if the name didn't match anyone
    child_name: str | None
    parent_name: str | None               # None if unmatched — no one to notify yet
    status: Literal["rejected", "needs_review"]
    issues: list[ValidationIssue]
    scanned_at: datetime
    notified_at: datetime | None = None
