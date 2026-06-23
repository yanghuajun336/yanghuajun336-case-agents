import unittest

from case_agent.workflow import CaseWorkflow


class TestCaseWorkflow(unittest.TestCase):
    def test_workflow_readiness(self):
        workflow = CaseWorkflow()
        workflow.start_new_session()

        workflow.ingest_user_message("用户反馈 ssh 无法连接")
        self.assertFalse(workflow.is_ready_for_finalization())

        workflow.update_case_draft(
            title="SSH 故障处理",
            author="bob",
            product_line="Network",
            background="用户反馈 ssh 无法连接",
            root_cause="sshd 未监听目标地址",
            solution="补充 ListenAddress 并重载",
            summary="问题已恢复",
        )
        self.assertTrue(workflow.is_ready_for_finalization())
        self.assertEqual(workflow.session.draft.os, "EulerOS")

    def test_register_image_updates_draft(self):
        workflow = CaseWorkflow()
        workflow.start_new_session()

        workflow.register_image_attachment("log.png", "错误日志截图")

        self.assertEqual(len(workflow.session.images), 1)
        self.assertEqual(len(workflow.session.draft.images), 1)

    def test_os_can_be_overridden(self):
        workflow = CaseWorkflow()
        workflow.start_new_session()
        workflow.update_case_draft(os="openEuler")
        self.assertEqual(workflow.session.draft.os, "openEuler")


if __name__ == "__main__":
    unittest.main()
