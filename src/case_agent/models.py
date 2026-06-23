"""Domain models for the Case Agent application layer."""

from __future__ import annotations

from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from enum import Enum


def utc_now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


class WorkflowStatus(str, Enum):
    INIT = "INIT"
    INTAKE = "INTAKE"
    SIMILAR_CASE_RECOMMENDING = "SIMILAR_CASE_RECOMMENDING"
    ANALYZING = "ANALYZING"
    DRAFTING = "DRAFTING"
    DRAFT_INCOMPLETE = "DRAFT_INCOMPLETE"
    READY_TO_FINALIZE = "READY_TO_FINALIZE"
    FINALIZED = "FINALIZED"
    ARCHIVED = "ARCHIVED"


@dataclass
class ImageAttachment:
    image_id: str
    file_name: str
    summary: str = ""
    mime_type: str = "image/png"
    linked_sections: list[str] = field(default_factory=list)
    source: str = "cli"


@dataclass
class SimilarCaseHit:
    case_id: str
    title: str
    score: float
    summary: str
    root_cause: str = ""
    solution: str = ""
    tags: list[str] = field(default_factory=list)


@dataclass
class CaseDraft:
    title: str = ""
    author: str = ""
    os: str = "EulerOS"
    product_line: str = ""
    background: str = ""
    root_cause: str = ""
    solution: str = ""
    summary: str = ""
    references: list[str] = field(default_factory=list)
    images: list[ImageAttachment] = field(default_factory=list)
    related_cases: list[SimilarCaseHit] = field(default_factory=list)

    def as_dict(self) -> dict:
        return asdict(self)


@dataclass
class StructuredCaseMemoryPayload:
    case_id: str
    title: str
    summary: str
    os: str
    product_line: str
    root_cause: str
    solution: str
    references: list[str]
    image_summaries: list[dict]
    related_cases: list[dict]
    embedding_text: str
    created_at: str = field(default_factory=utc_now_iso)

    def as_dict(self) -> dict:
        return asdict(self)


@dataclass
class CaseSession:
    session_id: str
    status: WorkflowStatus = WorkflowStatus.INIT
    draft: CaseDraft = field(default_factory=CaseDraft)
    messages: list[str] = field(default_factory=list)
    images: list[ImageAttachment] = field(default_factory=list)
    similar_cases: list[SimilarCaseHit] = field(default_factory=list)
    created_at: str = field(default_factory=utc_now_iso)
    updated_at: str = field(default_factory=utc_now_iso)
