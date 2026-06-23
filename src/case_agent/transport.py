"""Client transport layer for Case Agent.

Defines a protocol-level transport interface and a concrete HTTP
implementation so the CLI (and future TUI) can talk to a remote server.

Usage (HTTP client against a running server):
    transport = HttpTransport("http://127.0.0.1:8765")
    sid = transport.new_session(author="alice").session_id
    transport.ingest_message(sid, "SSH 连接失败")
    print(transport.get_draft(sid))

Future integration notes
------------------------
* Add ``WebSocketTransport`` for streaming/push events.
* Add ``InProcessTransport`` to drive ``CaseWorkflow`` locally (no network
  hop needed when client and server run in the same process).
* Add authentication headers via ``auth_token`` parameter.
"""

from __future__ import annotations

import json
import urllib.error
import urllib.parse
import urllib.request
from typing import Protocol

from .protocol import (
    DraftResponse,
    FinalizeResponse,
    NewSessionResponse,
    SessionStateResponse,
    SimilarCasesResponse,
)


# ---------------------------------------------------------------------------
# Transport protocol (interface)
# ---------------------------------------------------------------------------

class CaseAgentTransport(Protocol):
    """Pluggable transport interface for Case Agent client."""

    def new_session(self, author: str = "", os: str = "EulerOS") -> NewSessionResponse: ...
    def ingest_message(self, session_id: str, text: str) -> SessionStateResponse: ...
    def register_image(
        self,
        session_id: str,
        file_name: str,
        summary: str,
        mime_type: str = "image/png",
        linked_sections: list[str] | None = None,
    ) -> SessionStateResponse: ...
    def update_draft(self, session_id: str, fields: dict) -> SessionStateResponse: ...
    def get_draft(self, session_id: str) -> DraftResponse: ...
    def get_similar(self, session_id: str) -> SimilarCasesResponse: ...
    def finalize(self, session_id: str) -> FinalizeResponse: ...


# ---------------------------------------------------------------------------
# HTTP transport implementation
# ---------------------------------------------------------------------------

class HttpTransport:
    """HTTP JSON transport that calls the Case Agent stub server."""

    def __init__(self, base_url: str = "http://127.0.0.1:8765") -> None:
        self.base_url = base_url.rstrip("/")

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def new_session(self, author: str = "", os: str = "EulerOS") -> NewSessionResponse:
        data = self._post("/sessions/new", {"author": author, "os": os})
        return NewSessionResponse(session_id=data["session_id"], status=data["status"])

    def ingest_message(self, session_id: str, text: str) -> SessionStateResponse:
        data = self._post(f"/sessions/{session_id}/message", {"text": text})
        return self._parse_state(data)

    def register_image(
        self,
        session_id: str,
        file_name: str,
        summary: str,
        mime_type: str = "image/png",
        linked_sections: list[str] | None = None,
    ) -> SessionStateResponse:
        data = self._post(
            f"/sessions/{session_id}/image",
            {
                "file_name": file_name,
                "summary": summary,
                "mime_type": mime_type,
                "linked_sections": linked_sections or [],
            },
        )
        return self._parse_state(data)

    def update_draft(self, session_id: str, fields: dict) -> SessionStateResponse:
        data = self._post(f"/sessions/{session_id}/draft", {"fields": fields})
        return self._parse_state(data)

    def get_draft(self, session_id: str) -> DraftResponse:
        data = self._get(f"/sessions/{session_id}/draft")
        return DraftResponse(session_id=data["session_id"], draft=data["draft"])

    def get_similar(self, session_id: str) -> SimilarCasesResponse:
        data = self._get(f"/sessions/{session_id}/similar")
        return SimilarCasesResponse(session_id=data["session_id"], hits=data["hits"])

    def finalize(self, session_id: str) -> FinalizeResponse:
        data = self._post(f"/sessions/{session_id}/finalize", {})
        return FinalizeResponse(
            session_id=data["session_id"],
            case_assistant_payload=data["case_assistant_payload"],
            memory_payload=data["memory_payload"],
        )

    # ------------------------------------------------------------------
    # HTTP helpers
    # ------------------------------------------------------------------

    def _post(self, path: str, payload: dict) -> dict:
        url = self.base_url + path
        body = json.dumps(payload, ensure_ascii=False).encode()
        req = urllib.request.Request(
            url,
            data=body,
            method="POST",
            headers={"Content-Type": "application/json; charset=utf-8"},
        )
        return self._send(req)

    def _get(self, path: str) -> dict:
        url = self.base_url + path
        req = urllib.request.Request(url, method="GET")
        return self._send(req)

    def _send(self, req: urllib.request.Request) -> dict:
        try:
            with urllib.request.urlopen(req, timeout=10) as resp:
                raw = resp.read()
                return json.loads(raw)
        except urllib.error.HTTPError as exc:
            raw = exc.read()
            try:
                err = json.loads(raw)
            except json.JSONDecodeError:
                err = {"error": raw.decode(errors="replace")}
            raise CaseAgentTransportError(exc.code, err.get("error", str(exc))) from exc
        except OSError as exc:
            raise CaseAgentTransportError(0, str(exc)) from exc

    @staticmethod
    def _parse_state(data: dict) -> SessionStateResponse:
        return SessionStateResponse(
            session_id=data["session_id"],
            status=data["status"],
            similar_cases_count=data["similar_cases_count"],
            images_count=data["images_count"],
            draft_fields_filled=data["draft_fields_filled"],
            draft_fields_missing=data["draft_fields_missing"],
        )


# ---------------------------------------------------------------------------
# In-process transport (no network, useful for testing and local-mode CLI)
# ---------------------------------------------------------------------------

class InProcessTransport:
    """Drives CaseWorkflow directly without an HTTP server.

    Use this in local-mode CLI or tests to avoid needing a running server.
    """

    def __init__(self) -> None:
        from .case_skill import draft_to_case_assistant_payload
        from .memory import build_case_memory_payload
        from .workflow import CaseWorkflow

        self._draft_to_payload = draft_to_case_assistant_payload
        self._build_memory = build_case_memory_payload
        self._workflows: dict[str, CaseWorkflow] = {}

    def new_session(self, author: str = "", os: str = "EulerOS") -> NewSessionResponse:
        from .workflow import CaseWorkflow

        workflow = CaseWorkflow()
        workflow.start_new_session()
        assert workflow.session is not None
        if author:
            workflow.session.draft.author = author
        workflow.session.draft.os = os
        self._workflows[workflow.session.session_id] = workflow
        return NewSessionResponse(session_id=workflow.session.session_id, status=workflow.session.status.value)

    def ingest_message(self, session_id: str, text: str) -> SessionStateResponse:
        workflow = self._get_workflow(session_id)
        workflow.ingest_user_message(text)
        return self._state(workflow)

    def register_image(
        self,
        session_id: str,
        file_name: str,
        summary: str,
        mime_type: str = "image/png",
        linked_sections: list[str] | None = None,
    ) -> SessionStateResponse:
        workflow = self._get_workflow(session_id)
        workflow.register_image_attachment(file_name, summary, mime_type, linked_sections)
        return self._state(workflow)

    def update_draft(self, session_id: str, fields: dict) -> SessionStateResponse:
        workflow = self._get_workflow(session_id)
        workflow.update_case_draft(**fields)
        return self._state(workflow)

    def get_draft(self, session_id: str) -> DraftResponse:
        workflow = self._get_workflow(session_id)
        assert workflow.session is not None
        return DraftResponse(session_id=session_id, draft=workflow.session.draft.as_dict())

    def get_similar(self, session_id: str) -> SimilarCasesResponse:
        workflow = self._get_workflow(session_id)
        hits = workflow.refresh_similar_cases()
        return SimilarCasesResponse(
            session_id=session_id,
            hits=[{"case_id": h.case_id, "title": h.title, "score": h.score, "summary": h.summary} for h in hits],
        )

    def finalize(self, session_id: str) -> FinalizeResponse:
        workflow = self._get_workflow(session_id)
        workflow.finalize_session()
        assert workflow.session is not None
        draft = workflow.session.draft
        return FinalizeResponse(
            session_id=session_id,
            case_assistant_payload=self._draft_to_payload(draft),
            memory_payload=self._build_memory(draft).as_dict(),
        )

    def _get_workflow(self, session_id: str):
        workflow = self._workflows.get(session_id)
        if workflow is None:
            raise CaseAgentTransportError(404, f"Session '{session_id}' not found")
        return workflow

    def _state(self, workflow) -> SessionStateResponse:
        session = workflow.session
        assert session is not None
        draft = session.draft
        filled = [f for f in workflow.REQUIRED_FIELDS if (getattr(draft, f) or "").strip()]
        missing = [f for f in workflow.REQUIRED_FIELDS if not (getattr(draft, f) or "").strip()]
        return SessionStateResponse(
            session_id=session.session_id,
            status=session.status.value,
            similar_cases_count=len(session.similar_cases),
            images_count=len(session.images),
            draft_fields_filled=filled,
            draft_fields_missing=missing,
        )


# ---------------------------------------------------------------------------
# Error type
# ---------------------------------------------------------------------------

class CaseAgentTransportError(Exception):
    """Raised by transports when the server returns an error."""

    def __init__(self, code: int, message: str) -> None:
        super().__init__(f"[{code}] {message}")
        self.code = code
        self.message = message
