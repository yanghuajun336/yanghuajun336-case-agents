"""Structured memory payload generation for finalized case drafts."""

from __future__ import annotations

import uuid

from .models import CaseDraft, StructuredCaseMemoryPayload


def build_case_memory_payload(draft: CaseDraft, case_id: str | None = None) -> StructuredCaseMemoryPayload:
    resolved_case_id = case_id or f"case-{uuid.uuid4().hex[:10]}"
    image_summaries = [
        {
            "image_id": image.image_id,
            "summary": image.summary,
            "type": image.mime_type,
            "linked_sections": image.linked_sections,
        }
        for image in draft.images
    ]
    related_cases = [
        {
            "case_id": item.case_id,
            "title": item.title,
            "score": item.score,
        }
        for item in draft.related_cases
    ]
    embedding_text = "\n".join(
        part
        for part in [
            draft.title,
            draft.summary,
            draft.background,
            draft.root_cause,
            draft.solution,
            " ".join(image.get("summary", "") for image in image_summaries),
        ]
        if part
    )
    return StructuredCaseMemoryPayload(
        case_id=resolved_case_id,
        title=draft.title,
        summary=draft.summary,
        os=draft.os,
        product_line=draft.product_line,
        root_cause=draft.root_cause,
        solution=draft.solution,
        references=list(draft.references),
        image_summaries=image_summaries,
        related_cases=related_cases,
        embedding_text=embedding_text,
    )
