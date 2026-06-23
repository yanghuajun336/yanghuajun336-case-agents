# Overview

Case Agent 是基于 hello-agent 的案例应用层编排器：
- 负责把用户多轮输入（文本+图片）组织成案例草稿
- 负责提前给出相似历史案例建议
- 负责把草稿映射为 `case-assistant` skill 所需结构
- 负责生成可写入 memory-rag 的结构化 payload

本阶段强调“应用层与基座分层”，避免重复实现 hello-agent 已有底层能力。
