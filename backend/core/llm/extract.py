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
_SYSTEM = """You are extracting fields from a photo of a completed pediatric \
health assessment form used for Pennsylvania child care enrollment. Extract \
only what is visibly present. If a field is illegible or absent, use \
null/false and describe the ambiguity in notes. Do not infer or fill gaps. \
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
