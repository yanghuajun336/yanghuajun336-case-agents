"""Map app-level case draft data into case-assistant skill payload."""

from __future__ import annotations

from .models import CaseDraft


def draft_to_case_assistant_payload(draft: CaseDraft) -> dict:
    """Build payload expected by existing case-assistant skill."""
    return {
        "title": draft.title,
        "author": draft.author,
        "os": draft.os,
        "product_line": draft.product_line,
        "background": draft.background,
        "root_cause": draft.root_cause,
        "solution": draft.solution,
        "summary": draft.summary,
        "references": draft.references,
        "images": [
            {
                "image_id": image.image_id,
                "file_name": image.file_name,
                "summary": image.summary,
                "linked_sections": image.linked_sections,
            }
            for image in draft.images
        ],
        "related_cases": [
            {
                "case_id": item.case_id,
                "title": item.title,
                "score": item.score,
                "summary": item.summary,
            }
            for item in draft.related_cases
        ],
    }
