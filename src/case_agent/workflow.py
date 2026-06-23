"""High-level workflow state handling for Case Agent sessions."""

from __future__ import annotations

import uuid
from datetime import datetime, timezone

from .images import create_image_attachment
from .models import CaseSession, WorkflowStatus
from .similar_cases import MockSimilarCaseRecommender, SimilarCaseRecommender


class CaseWorkflow:
    """Session workflow skeleton for future hello-agent runtime integration."""

    REQUIRED_FIELDS = ["title", "author", "os", "product_line", "background", "root_cause", "solution", "summary"]

    def __init__(self, recommender: SimilarCaseRecommender | None = None) -> None:
        self.recommender = recommender or MockSimilarCaseRecommender()
        self.session: CaseSession | None = None

    def start_new_session(self) -> CaseSession:
        session_id = f"session-{uuid.uuid4().hex[:8]}"
        self.session = CaseSession(session_id=session_id, status=WorkflowStatus.INTAKE)
        return self.session

    def ingest_user_message(self, text: str) -> CaseSession:
        session = self._ensure_session()
        cleaned = text.strip()
        if not cleaned:
            return session

        session.messages.append(cleaned)
        if not session.draft.background:
            session.draft.background = cleaned
        if not session.draft.summary:
            session.draft.summary = cleaned[:120]

        session.status = WorkflowStatus.SIMILAR_CASE_RECOMMENDING
        self.refresh_similar_cases()
        session.status = WorkflowStatus.ANALYZING
        self._sync_ready_state()
        self._touch()
        return session

    def register_image_attachment(
        self,
        file_name: str,
        summary: str,
        mime_type: str = "image/png",
        linked_sections: list[str] | None = None,
    ) -> CaseSession:
        session = self._ensure_session()
        image = create_image_attachment(
            file_name=file_name,
            summary=summary,
            mime_type=mime_type,
            linked_sections=linked_sections,
        )
        session.images.append(image)
        session.draft.images = list(session.images)
        self.refresh_similar_cases()
        self._sync_ready_state()
        self._touch()
        return session

    def update_case_draft(self, **fields: str | list[str]) -> CaseSession:
        session = self._ensure_session()
        for field_name, field_value in fields.items():
            if hasattr(session.draft, field_name):
                setattr(session.draft, field_name, field_value)
        self._sync_ready_state()
        self._touch()
        return session

    def refresh_similar_cases(self) -> list:
        session = self._ensure_session()
        problem_text = "\n".join(session.messages)
        image_summaries = [image.summary for image in session.images if image.summary]
        session.similar_cases = self.recommender.recommend(problem_text=problem_text, image_summaries=image_summaries)
        session.draft.related_cases = list(session.similar_cases)
        self._touch()
        return session.similar_cases

    def is_ready_for_finalization(self) -> bool:
        session = self._ensure_session()
        return all(bool(getattr(session.draft, field).strip()) for field in self.REQUIRED_FIELDS)

    def finalize_session(self) -> CaseSession:
        session = self._ensure_session()
        if not self.is_ready_for_finalization():
            session.status = WorkflowStatus.DRAFT_INCOMPLETE
            raise ValueError("Case draft is incomplete and cannot be finalized.")
        session.status = WorkflowStatus.FINALIZED
        self._touch()
        return session

    def _sync_ready_state(self) -> None:
        session = self._ensure_session()
        session.status = (
            WorkflowStatus.READY_TO_FINALIZE if self.is_ready_for_finalization() else WorkflowStatus.DRAFT_INCOMPLETE
        )

    def _ensure_session(self) -> CaseSession:
        if self.session is None:
            return self.start_new_session()
        return self.session

    def _touch(self) -> None:
        session = self._ensure_session()
        session.updated_at = datetime.now(timezone.utc).isoformat()
