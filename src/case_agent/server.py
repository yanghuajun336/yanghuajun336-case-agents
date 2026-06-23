"""Stub HTTP server for Case Agent.

Uses only Python standard-library modules (``http.server``, ``json``) so
no extra dependencies are required for the MVP.

Run directly:
    PYTHONPATH=src python -m case_agent.server           # default port 8765
    PYTHONPATH=src python -m case_agent.server --port 9000

The server exposes a simple JSON-over-HTTP REST API.  Each request body must
be valid JSON; each response is JSON.  Routes mirror the protocol message
types defined in ``protocol.py``.

Route summary
-------------
POST /sessions/new                  → NewSessionResponse
POST /sessions/{id}/message         → SessionStateResponse
POST /sessions/{id}/image           → SessionStateResponse
POST /sessions/{id}/draft           → SessionStateResponse
GET  /sessions/{id}/draft           → DraftResponse
GET  /sessions/{id}/similar         → SimilarCasesResponse
POST /sessions/{id}/finalize        → FinalizeResponse

Future integration notes
------------------------
* Replace ``CaseWorkflow`` internals with hello-agent runtime calls.
* Swap HTTP for WebSocket or gRPC to support streaming events.
* Add authentication middleware before exposing to remote clients.
"""

from __future__ import annotations

import argparse
import json
import re
from http.server import BaseHTTPRequestHandler, HTTPServer
from typing import Any

from .case_skill import draft_to_case_assistant_payload
from .memory import build_case_memory_payload
from .protocol import (
    DraftResponse,
    ErrorResponse,
    FinalizeResponse,
    NewSessionResponse,
    SessionStateResponse,
    SimilarCasesResponse,
)
from .workflow import CaseWorkflow

# Path patterns
_RE_SESSION = re.compile(r"^/sessions/(?P<sid>[^/]+)$")
_RE_SESSION_ACTION = re.compile(r"^/sessions/(?P<sid>[^/]+)/(?P<action>[a-z]+)$")


class _SessionStore:
    """In-process session store; replace with persistent store for production."""

    def __init__(self) -> None:
        self._workflows: dict[str, CaseWorkflow] = {}

    def create(self) -> CaseWorkflow:
        workflow = CaseWorkflow()
        workflow.start_new_session()
        sid = workflow.session.session_id  # type: ignore[union-attr]
        self._workflows[sid] = workflow
        return workflow

    def get(self, session_id: str) -> CaseWorkflow | None:
        return self._workflows.get(session_id)


_store = _SessionStore()


def _session_state(workflow: CaseWorkflow) -> SessionStateResponse:
    """Build a SessionStateResponse snapshot from a workflow."""
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


class _Handler(BaseHTTPRequestHandler):
    """HTTP request handler that routes JSON API calls."""

    # ------------------------------------------------------------------
    # Routing
    # ------------------------------------------------------------------

    def do_GET(self) -> None:  # noqa: N802
        m = _RE_SESSION_ACTION.match(self.path)
        if m:
            sid, action = m.group("sid"), m.group("action")
            if action == "draft":
                self._handle_get_draft(sid)
                return
            if action == "similar":
                self._handle_get_similar(sid)
                return
        self._send_json(404, ErrorResponse(error="Not found", code=404).as_dict())

    def do_POST(self) -> None:  # noqa: N802
        if self.path == "/sessions/new":
            self._handle_new_session()
            return
        m = _RE_SESSION_ACTION.match(self.path)
        if m:
            sid, action = m.group("sid"), m.group("action")
            if action == "message":
                self._handle_message(sid)
                return
            if action == "image":
                self._handle_image(sid)
                return
            if action == "draft":
                self._handle_update_draft(sid)
                return
            if action == "finalize":
                self._handle_finalize(sid)
                return
        self._send_json(404, ErrorResponse(error="Not found", code=404).as_dict())

    # ------------------------------------------------------------------
    # Handlers
    # ------------------------------------------------------------------

    def _handle_new_session(self) -> None:
        body = self._read_json()
        workflow = _store.create()
        session = workflow.session
        assert session is not None
        author = body.get("author", "")
        os_name = body.get("os", "EulerOS")
        if author:
            session.draft.author = author
        if os_name:
            session.draft.os = os_name
        resp = NewSessionResponse(session_id=session.session_id, status=session.status.value)
        self._send_json(200, resp.as_dict())

    def _handle_message(self, sid: str) -> None:
        workflow = self._require_session(sid)
        if workflow is None:
            return
        body = self._read_json()
        text = body.get("text", "")
        if not text:
            self._send_json(400, ErrorResponse(error="'text' is required").as_dict())
            return
        workflow.ingest_user_message(text)
        self._send_json(200, _session_state(workflow).as_dict())

    def _handle_image(self, sid: str) -> None:
        workflow = self._require_session(sid)
        if workflow is None:
            return
        body = self._read_json()
        file_name = body.get("file_name", "")
        summary = body.get("summary", "")
        if not file_name or not summary:
            self._send_json(400, ErrorResponse(error="'file_name' and 'summary' are required").as_dict())
            return
        workflow.register_image_attachment(
            file_name=file_name,
            summary=summary,
            mime_type=body.get("mime_type", "image/png"),
            linked_sections=body.get("linked_sections", []),
        )
        self._send_json(200, _session_state(workflow).as_dict())

    def _handle_update_draft(self, sid: str) -> None:
        workflow = self._require_session(sid)
        if workflow is None:
            return
        body = self._read_json()
        fields: dict[str, Any] = body.get("fields", {})
        if not fields:
            self._send_json(400, ErrorResponse(error="'fields' is required").as_dict())
            return
        workflow.update_case_draft(**fields)
        self._send_json(200, _session_state(workflow).as_dict())

    def _handle_get_draft(self, sid: str) -> None:
        workflow = self._require_session(sid)
        if workflow is None:
            return
        assert workflow.session is not None
        resp = DraftResponse(session_id=sid, draft=workflow.session.draft.as_dict())
        self._send_json(200, resp.as_dict())

    def _handle_get_similar(self, sid: str) -> None:
        workflow = self._require_session(sid)
        if workflow is None:
            return
        hits = workflow.refresh_similar_cases()
        resp = SimilarCasesResponse(
            session_id=sid,
            hits=[{"case_id": h.case_id, "title": h.title, "score": h.score, "summary": h.summary} for h in hits],
        )
        self._send_json(200, resp.as_dict())

    def _handle_finalize(self, sid: str) -> None:
        workflow = self._require_session(sid)
        if workflow is None:
            return
        try:
            workflow.finalize_session()
        except ValueError as exc:
            self._send_json(422, ErrorResponse(error=str(exc), code=422).as_dict())
            return
        assert workflow.session is not None
        draft = workflow.session.draft
        case_payload = draft_to_case_assistant_payload(draft)
        memory_payload = build_case_memory_payload(draft)
        resp = FinalizeResponse(
            session_id=sid,
            case_assistant_payload=case_payload,
            memory_payload=memory_payload.as_dict(),
        )
        self._send_json(200, resp.as_dict())

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------

    def _require_session(self, sid: str) -> CaseWorkflow | None:
        workflow = _store.get(sid)
        if workflow is None:
            self._send_json(404, ErrorResponse(error=f"Session '{sid}' not found", code=404).as_dict())
            return None
        return workflow

    def _read_json(self) -> dict:
        length = int(self.headers.get("Content-Length", 0))
        if length == 0:
            return {}
        raw = self.rfile.read(length)
        try:
            return json.loads(raw)
        except json.JSONDecodeError:
            return {}

    def _send_json(self, status: int, body: dict) -> None:
        encoded = json.dumps(body, ensure_ascii=False).encode()
        self.send_response(status)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(encoded)))
        self.end_headers()
        self.wfile.write(encoded)

    def log_message(self, fmt: str, *args: object) -> None:
        # Suppress BaseHTTPRequestHandler's per-request stderr output; the MVP
        # has no logging framework yet.  Add structured logging here in M1.
        pass


def create_server(host: str = "127.0.0.1", port: int = 8765) -> HTTPServer:
    """Create (but do not start) an HTTPServer bound to *host*:*port*."""
    return HTTPServer((host, port), _Handler)


def main() -> None:
    parser = argparse.ArgumentParser(description="Case Agent stub HTTP server")
    parser.add_argument("--host", default="127.0.0.1")
    parser.add_argument("--port", type=int, default=8765)
    args = parser.parse_args()
    server = create_server(args.host, args.port)
    print(f"Case Agent Server running on http://{args.host}:{args.port}")
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\nServer stopped.")
    finally:
        server.server_close()


if __name__ == "__main__":
    main()
