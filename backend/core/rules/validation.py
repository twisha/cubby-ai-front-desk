"""Health-form validation — deterministic checks against a vision extraction.

Pure function; imports NO Anthropic client. The model only reports what's
visibly on the form (core/llm/extract.py); every accept/reject decision is
made here.
"""
from __future__ import annotations

from datetime import date

from backend.core.rules.scheduler import add_months, cycle_months
from backend.models.forms import HealthFormExtraction, ValidationIssue, ValidationResult
from backend.models.roster import Child


def validate(x: HealthFormExtraction, child: Child | None, today: date) -> ValidationResult:
    issues: list[ValidationIssue] = []

    if child is None:
        issues.append(ValidationIssue(
            field="child_name",
            problem=f"'{x.child_name or 'unknown'}' doesn't match any child on the roster.",
            fix="Confirm the child's name and try again, or add them to the roster first.",
        ))

    # 1. Examiner signature — NOT the parent's. The headline conflation trap:
    # a form parent-signed but examiner-unsigned MUST reject.
    if not x.examiner_signature_present:
        issues.append(ValidationIssue(
            field="examiner_signature_present",
            problem="The provider's signature block at the bottom is blank — "
                    "the parent's signature at the top doesn't count.",
            fix="Ask the provider's office to sign and return the form, or fax a signed copy.",
        ))

    # 2. Credential, Sec 3270.131(c). The Pydantic Literal already constrains
    # this to {MD, DO, PA-C, CRNP} or None; None means blank/illegible/other.
    if x.examiner_credential is None:
        issues.append(ValidationIssue(
            field="examiner_credential",
            problem="No physician/PA/CRNP credential or title is visible next to the signature.",
            fix="Ask the provider's office to note MD, DO, PA-C, or CRNP next to the signature.",
        ))

    # 3. Exam date present, not future, and still within the child's CURRENT
    # cycle window — a report whose cycle has already elapsed isn't valid as
    # a CURRENT report even if everything else on it checks out.
    if x.date_of_exam is None:
        issues.append(ValidationIssue(
            field="date_of_exam",
            problem="No exam date is visible on the form.",
            fix="Ask the provider's office to date the form.",
        ))
    elif x.date_of_exam > today:
        issues.append(ValidationIssue(
            field="date_of_exam",
            problem=f"The exam date ({x.date_of_exam.isoformat()}) is in the future.",
            fix="Double-check the date with the provider's office.",
        ))
    elif child is not None:
        months = cycle_months(child.dob, today)
        expires = add_months(x.date_of_exam, months)
        if expires < today:
            issues.append(ValidationIssue(
                field="date_of_exam",
                problem=f"This exam was signed {x.date_of_exam.isoformat()}, which is "
                        f"already outside the current {months}-month cycle.",
                fix=f"Ask the provider's office for a new exam within the last {months} months.",
            ))

    # 4. Immunization record section completed.
    if not x.immunizations_section_completed:
        issues.append(ValidationIssue(
            field="immunizations_section_completed",
            problem="The immunization record section is blank or incomplete.",
            fix="Ask the parent to attach a copy of the child's immunization record.",
        ))

    # 5. Age-appropriate screenings attestation (see models/forms.py for why
    # this field exists beyond the spec's literal schema).
    if x.screenings_up_to_date is False:
        issues.append(ValidationIssue(
            field="screenings_up_to_date",
            problem="The provider checked NO for age-appropriate screenings being up to date.",
            fix="Ask the parent to follow up on the pending screening noted on the form.",
        ))

    if child is None:
        return ValidationResult(status="needs_review", issues=issues, next_due_date=None)
    if issues:
        return ValidationResult(status="rejected", issues=issues, next_due_date=None)

    next_due = add_months(x.date_of_exam, cycle_months(child.dob, today))  # type: ignore[arg-type]
    return ValidationResult(status="accepted", issues=[], next_due_date=next_due)
