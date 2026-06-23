"""Tests for protocol message types and InProcessTransport."""

import unittest

from case_agent.protocol import (
    CaseAgentEvent,
    FinalizeResponse,
    IngestMessageRequest,
    NewSessionRequest,
    NewSessionResponse,
    RegisterImageRequest,
    SessionStateResponse,
    SimilarCasesResponse,
)
from case_agent.transport import CaseAgentTransportError, InProcessTransport


class TestProtocolMessages(unittest.TestCase):
    def test_new_session_request_defaults(self):
        req = NewSessionRequest()
        self.assertEqual(req.author, "")
        self.assertEqual(req.os, "EulerOS")

    def test_ingest_message_request_fields(self):
        req = IngestMessageRequest(session_id="s1", text="SSH 失败")
        self.assertEqual(req.session_id, "s1")
        self.assertEqual(req.text, "SSH 失败")

    def test_register_image_request_serialisation(self):
        from dataclasses import asdict

        req = RegisterImageRequest(
            session_id="s1",
            file_name="err.png",
            summary="报错截图",
            linked_sections=["symptoms"],
        )
        d = asdict(req)
        self.assertEqual(d["linked_sections"], ["symptoms"])

    def test_case_agent_event_as_dict(self):
        evt = CaseAgentEvent(
            event_type="draft_updated",
            session_id="s1",
            payload={"field": "title"},
        )
        d = evt.as_dict()
        self.assertEqual(d["event_type"], "draft_updated")
        self.assertEqual(d["payload"]["field"], "title")

    def test_session_state_response_as_dict(self):
        resp = SessionStateResponse(
            session_id="s1",
            status="DRAFT_INCOMPLETE",
            similar_cases_count=2,
            images_count=1,
            draft_fields_filled=["title"],
            draft_fields_missing=["author", "root_cause"],
        )
        d = resp.as_dict()
        self.assertIn("draft_fields_missing", d)
        self.assertEqual(d["images_count"], 1)


class TestInProcessTransport(unittest.TestCase):
    def _full_draft_fields(self) -> dict:
        return {
            "title": "SSH 故障",
            "author": "bob",
            "product_line": "Network",
            "background": "用户无法登录",
            "root_cause": "sshd 未监听目标地址",
            "solution": "补充 ListenAddress",
            "summary": "问题已修复",
        }

    def test_new_session_creates_session(self):
        transport = InProcessTransport()
        resp = transport.new_session(author="alice", os="openEuler")
        self.assertIsInstance(resp, NewSessionResponse)
        self.assertTrue(resp.session_id.startswith("session-"))
        self.assertEqual(resp.status, "INIT")

    def test_ingest_message_returns_state(self):
        transport = InProcessTransport()
        sid = transport.new_session().session_id
        state = transport.ingest_message(sid, "SSH 连接失败")
        self.assertIsInstance(state, SessionStateResponse)
        self.assertIn("title", state.draft_fields_missing)

    def test_register_image_increments_count(self):
        transport = InProcessTransport()
        sid = transport.new_session().session_id
        state = transport.register_image(sid, "err.png", "报错截图")
        self.assertEqual(state.images_count, 1)

    def test_get_draft_returns_draft(self):
        transport = InProcessTransport()
        sid = transport.new_session().session_id
        transport.ingest_message(sid, "问题描述")
        draft_resp = transport.get_draft(sid)
        self.assertIn("background", draft_resp.draft)

    def test_get_similar_returns_hits(self):
        transport = InProcessTransport()
        sid = transport.new_session().session_id
        transport.ingest_message(sid, "ssh 无法连接")
        similar = transport.get_similar(sid)
        self.assertIsInstance(similar, SimilarCasesResponse)
        self.assertGreater(len(similar.hits), 0)

    def test_finalize_success(self):
        transport = InProcessTransport()
        sid = transport.new_session().session_id
        transport.update_draft(sid, fields=self._full_draft_fields())
        result = transport.finalize(sid)
        self.assertIsInstance(result, FinalizeResponse)
        self.assertEqual(result.case_assistant_payload["title"], "SSH 故障")
        self.assertIn("embedding_text", result.memory_payload)

    def test_unknown_session_raises_error(self):
        transport = InProcessTransport()
        with self.assertRaises(CaseAgentTransportError) as ctx:
            transport.ingest_message("nonexistent-id", "hello")
        self.assertEqual(ctx.exception.code, 404)


if __name__ == "__main__":
    unittest.main()
