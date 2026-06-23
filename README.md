# Case Agent (MVP Skeleton)

Case Agent 是一个面向问题处理与案例沉淀的应用层助手，构建在 **hello-agent** 能力之上。

> 本仓库当前实现聚焦应用层编排：会话流、案例草稿、相似案例推荐入口、图片元数据管理、`case-assistant` 输入映射与结构化 memory payload。  
> hello-agent 底层能力（推理引擎、底层检索、工具运行时等）在后续集成中接入，不在本 MVP 中重复实现。

## MVP 目标

1. 接收自然语言问题描述（Agent 风格 CLI）
2. 在流程早期给出相似历史案例推荐
3. 支持图片作为一等输入（先以元数据形式接入）
4. 生成可直接喂给 `case-assistant` 的结构化案例草稿输入
5. 生成结构化案例 memory payload，便于后续检索/推荐

## 典型用户流程

1. `/new` 新建会话
2. `/message ...` 或直接输入自然语言问题
3. `/image 文件名|摘要` 注册图片元数据
4. `/similar` 查看相似案例推荐
5. `/draft` 查看持续更新的草稿
6. 补齐必要字段后 `/finalize` 预览 `case-assistant` payload + memory payload

## 目录结构

- `src/case_agent/models.py`：应用层领域模型
- `src/case_agent/workflow.py`：会话工作流与状态
- `src/case_agent/similar_cases.py`：相似案例推荐接口与 mock 实现
- `src/case_agent/images.py`：图片元数据处理
- `src/case_agent/case_skill.py`：映射到 `case-assistant` 输入结构
- `src/case_agent/memory.py`：结构化案例 memory payload 生成
- `src/case_agent/cli.py`：CLI MVP 入口
- `docs/`：概要、特性、里程碑、CLI 交互说明
- `tests/`：最小单元测试

## 运行

```bash
cd <project-root>
PYTHONPATH=src python -m case_agent.cli
```

## 当前已实现 vs 后续集成

### 已实现（MVP skeleton）
- 应用层基础模型与会话状态机
- mock 相似案例推荐
- 图片元数据注册与草稿绑定
- `case-assistant` payload 映射
- 结构化 memory payload 生成
- CLI 命令式交互骨架

### 后续（与 hello-agent/runtime 深度集成）
- 真实 LLM 对话编排与追问策略
- memory-rag 实库检索与排序
- 图片 OCR/视觉理解与自动章节绑定
- Client/Server 远程协议与流式事件
- 与现有 `case-assistant` skill 的在线执行串联
