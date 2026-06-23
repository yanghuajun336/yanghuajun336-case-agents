"""Client/Server protocol message types for Case Agent.

All messages are plain dataclasses serialisable to/from JSON.
The design intentionally avoids external runtime dependencies so
any transport layer (HTTP, WebSocket, stdio) can carry these payloads.

Future hello-agent streaming integration: replace ``CaseAgentEvent``
with an SSE or WebSocket event envelope as needed.
"""

from __future__ import annotations

from dataclasses import asdict, dataclass, field


# ---------------------------------------------------------------------------
# Request messages  (Client → Server)
# ---------------------------------------------------------------------------

@dataclass
class NewSessionRequest:
    """Start a new case session."""
    # Optional: carry caller identity or context hint.
    author: str = ""
    os: str = "EulerOS"


@dataclass
class IngestMessageRequest:
    """Submit a natural-language problem message to a session."""
    session_id: str
    text: str


@dataclass
class RegisterImageRequest:
    """Register image metadata into a session."""
    session_id: str
    file_name: str
    summary: str
    mime_type: str = "image/png"
    linked_sections: list[str] = field(default_factory=list)


@dataclass
class UpdateDraftRequest:
    """Directly patch named fields on the session's case draft."""
    session_id: str
    fields: dict[str, str | list[str]] = field(default_factory=dict)


@dataclass
class FinalizeRequest:
    """Request finalisation of the current case draft."""
    session_id: str


# ---------------------------------------------------------------------------
# Response messages  (Server → Client)
# ---------------------------------------------------------------------------

@dataclass
class ErrorResponse:
    error: str
    code: int = 400

    def as_dict(self) -> dict:
        return asdict(self)


@dataclass
class NewSessionResponse:
    session_id: str
    status: str

    def as_dict(self) -> dict:
        return asdict(self)


@dataclass
class SessionStateResponse:
    """Generic session state snapshot returned after most mutations."""
    session_id: str
    status: str
    similar_cases_count: int
    images_count: int
    draft_fields_filled: list[str]
    draft_fields_missing: list[str]

    def as_dict(self) -> dict:
        return asdict(self)


@dataclass
class DraftResponse:
    session_id: str
    draft: dict

    def as_dict(self) -> dict:
        return asdict(self)


@dataclass
class SimilarCasesResponse:
    session_id: str
    hits: list[dict]

    def as_dict(self) -> dict:
        return asdict(self)


@dataclass
class FinalizeResponse:
    session_id: str
    case_assistant_payload: dict
    memory_payload: dict

    def as_dict(self) -> dict:
        return asdict(self)


# ---------------------------------------------------------------------------
# Event envelope  (future: streaming / push)
# ---------------------------------------------------------------------------

@dataclass
class CaseAgentEvent:
    """SSE / WebSocket event envelope for future streaming integration.

    ``event_type`` is one of:
    - ``session_created``
    - ``draft_updated``
    - ``similar_cases_ready``
    - ``image_registered``
    - ``finalized``
    - ``error``
    """
    event_type: str
    session_id: str
    payload: dict = field(default_factory=dict)

    def as_dict(self) -> dict:
        return asdict(self)
