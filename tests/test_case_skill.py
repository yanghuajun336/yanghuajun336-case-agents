import unittest

from case_agent.case_skill import draft_to_case_assistant_payload
from case_agent.models import CaseDraft, ImageAttachment, SimilarCaseHit


class TestCaseSkillMapping(unittest.TestCase):
    def test_draft_maps_to_case_assistant_payload(self):
        draft = CaseDraft(
            title="SSH 连接失败",
            author="alice",
            os="EulerOS",
            product_line="Network",
            background="用户反馈无法连接",
            root_cause="sshd 配置缺失",
            solution="补充 ListenAddress",
            summary="修复后恢复",
            references=["https://example.com/case"],
            images=[ImageAttachment(image_id="img-1", file_name="err.png", summary="报错截图")],
            related_cases=[SimilarCaseHit(case_id="case-1", title="历史案例", score=0.8, summary="相似问题")],
        )

        payload = draft_to_case_assistant_payload(draft)

        self.assertEqual(payload["title"], "SSH 连接失败")
        self.assertEqual(payload["author"], "alice")
        self.assertEqual(payload["images"][0]["file_name"], "err.png")
        self.assertEqual(payload["related_cases"][0]["case_id"], "case-1")


if __name__ == "__main__":
    unittest.main()
