"""Form extractor (Sonnet, vision). Turns a photo of a completed PA child-care
health form into a HealthFormExtraction. The model reports only what's
visibly present; core/rules/validation.py makes every accept/reject decision.
"""
from __future__ import annotations

import base64

from backend.config import CONFIG
from backend.core.llm.client import parse_structured
from backend.models.forms import HealthFormExtraction

# SPEC's system prompt, extended with one field (see models/forms.py's
# screenings_up_to_date docstring for why): the given prompt has no way to
# elicit the "age-appropriate screenings" YES/NO box, which is the only
# difference between the valid fixture and the attestation-NO fixture.
#
# Opens with an explicit auditor role, not just a task description: models
# default toward helpful inference, and this task needs the opposite instinct
# (a blank is a fact to report, not a gap to fill) reinforced at the identity
# level, not only as a rule further down.
_SYSTEM = """You are a compliance auditor extracting data from a legally required \
childcare health form. Your job is to record exactly what's visible on the page — \
a blank field, an illegible mark, or a missing signature is a fact to report, not \
a gap to helpfully complete.

This form is a photo of a completed pediatric health assessment form used for \
Pennsylvania child care enrollment. Extract only what is visibly present. If a \
field is illegible or absent, use null/false and describe the ambiguity in notes. \
IMPORTANT: these forms carry TWO signature areas — the examiner's \
(physician/PA/CRNP) certification signature and a parent/guardian signature. \
Report them separately and never treat a parent signature as the examiner's. \
A signature means an actual handwritten signature or clear e-signature mark, \
not a printed name. Extract the examiner's credential from the checked box \
or printed title (MD, DO, PA-C, CRNP). Also report whether the box for "has \
the child received all age-appropriate screenings currently recommended by \
the American Academy of Pediatrics" is checked YES or NO — this is a \
separate checkbox from the immunization date table. Return JSON matching the \
HealthFormExtraction schema."""


def extract_form(image_bytes: bytes, media_type: str = "image/jpeg") -> HealthFormExtraction:
    b64 = base64.standard_b64encode(image_bytes).decode("utf-8")
    content = [
        {
            "type": "image",
            "source": {"type": "base64", "media_type": media_type, "data": b64},
        },
        {"type": "text", "text": "Extract the fields from this health form."},
    ]
    return parse_structured(
        model=CONFIG.vision_model,
        system=_SYSTEM,
        content=content,
        schema=HealthFormExtraction,
        max_tokens=800,
    )
