"""Minimal interactive CLI for Case Agent MVP flow."""

from __future__ import annotations

import json

from .case_skill import draft_to_case_assistant_payload
from .memory import build_case_memory_payload
from .workflow import CaseWorkflow

HELP_TEXT = """可用命令：
  /new                     新建会话
  /message <text>          输入问题描述
  /image <name>|<summary>  注册图片元数据
  /similar                 查看相似案例
  /draft                   查看当前草稿
  /finalize                预览 case-assistant payload 与 memory payload
  /help                    查看帮助
  /exit                    退出
"""


def run_cli() -> None:
    workflow = CaseWorkflow()
    session = workflow.start_new_session()
    print("Case Agent MVP CLI 已启动。输入 /help 查看命令。")
    print(f"当前会话: {session.session_id}")

    while True:
        raw = input("> ").strip()
        if not raw:
            continue
        if raw in {"/exit", "exit", "quit"}:
            print("已退出。")
            return
        if raw == "/help":
            print(HELP_TEXT)
            continue
        if raw == "/new":
            session = workflow.start_new_session()
            print(f"已创建新会话: {session.session_id}")
            continue
        if raw.startswith("/message "):
            text = raw[len("/message ") :]
            session = workflow.ingest_user_message(text)
            print(f"已记录消息。当前状态: {session.status.value}")
            print(f"推荐案例数: {len(session.similar_cases)}")
            continue
        if raw.startswith("/image "):
            payload = raw[len("/image ") :]
            if "|" not in payload:
                print("格式错误，示例: /image error.png|sshd 报错截图")
                continue
            file_name, summary = payload.split("|", 1)
            session = workflow.register_image_attachment(file_name.strip(), summary.strip())
            print(f"已注册图片。总数: {len(session.images)}")
            continue
        if raw == "/similar":
            for idx, hit in enumerate(workflow.refresh_similar_cases(), start=1):
                print(f"{idx}. [{hit.score:.2f}] {hit.title} ({hit.case_id})")
                print(f"   摘要: {hit.summary}")
            continue
        if raw == "/draft":
            print(json.dumps(workflow.session.draft.as_dict(), ensure_ascii=False, indent=2))
            continue
        if raw == "/finalize":
            try:
                workflow.finalize_session()
            except ValueError as exc:
                print(f"当前草稿未完成: {exc}")
                continue
            case_payload = draft_to_case_assistant_payload(workflow.session.draft)
            memory_payload = build_case_memory_payload(workflow.session.draft)
            print("case-assistant payload:")
            print(json.dumps(case_payload, ensure_ascii=False, indent=2))
            print("\nstructured memory payload:")
            print(json.dumps(memory_payload.as_dict(), ensure_ascii=False, indent=2))
            continue

        # 默认按自然语言消息处理
        session = workflow.ingest_user_message(raw)
        print(f"已处理自然输入。当前状态: {session.status.value}")


if __name__ == "__main__":
    run_cli()
