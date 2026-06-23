# Case Agent Client/Server 协议说明

Case Agent 采用 **Client/Server** 分层架构。本文档说明当前已实现的协议边界，以及与 hello-agent 底层能力的集成预留点。

---

## 1. 架构分层

```
用户本地 (PC / Win11)
  └─ Case Agent Client
       ├─ CLI / TUI 入口
       ├─ 图片粘贴采集
       └─ CaseAgentTransport ─────────────→ Server
                                              │
                             Case Agent Server
                               ├─ 会话状态管理 (_SessionStore)
                               ├─ 工作流驱动 (CaseWorkflow)
                               └─ (Future) hello-agent runtime
```

---

## 2. 当前实现：HTTP JSON 协议（stub）

Server 使用 Python 标准库 `http.server`，**无外部依赖**，作为 MVP 占位。  
Client 使用 `HttpTransport` 通过 JSON over HTTP 调用。  
无 Server 时可用 `InProcessTransport` 在本地直接驱动工作流。

---

## 3. API 路由

### 创建会话

```
POST /sessions/new
Body: { "author": "...", "os": "EulerOS" }
→ { "session_id": "...", "status": "INIT" }
```

### 提交消息

```
POST /sessions/{id}/message
Body: { "text": "..." }
→ SessionStateResponse
```

### 注册图片元数据

```
POST /sessions/{id}/image
Body: { "file_name": "...", "summary": "...", "mime_type": "...", "linked_sections": [] }
→ SessionStateResponse
```

### 更新草稿字段

```
POST /sessions/{id}/draft
Body: { "fields": { "title": "...", "root_cause": "..." } }
→ SessionStateResponse
```

### 查看草稿

```
GET /sessions/{id}/draft
→ { "session_id": "...", "draft": { ... } }
```

### 查看相似案例

```
GET /sessions/{id}/similar
→ { "session_id": "...", "hits": [ { "case_id", "title", "score", "summary" } ] }
```

### 最终化案例

```
POST /sessions/{id}/finalize
→ { "session_id": "...", "case_assistant_payload": { ... }, "memory_payload": { ... } }
```

---

## 4. SessionStateResponse 字段

| 字段 | 说明 |
|------|------|
| `session_id` | 会话 ID |
| `status` | 当前工作流状态（见 WorkflowStatus）|
| `similar_cases_count` | 推荐案例数量 |
| `images_count` | 已注册图片数 |
| `draft_fields_filled` | 已填写的必填字段 |
| `draft_fields_missing` | 还缺少的必填字段 |

---

## 5. 传输实现选择

| 类 | 场景 |
|----|------|
| `InProcessTransport` | 本地模式、测试、单机运行 |
| `HttpTransport` | 远端 Server 模式 |
| `(Future) WebSocketTransport` | 流式输出、实时事件推送 |

---

## 6. Future 集成预留点

- **hello-agent runtime**：在 `CaseWorkflow.ingest_user_message()` 中将文本转发给 hello-agent，使用其推理能力决定追问策略和草稿生成逻辑。
- **memory-rag 检索**：将 `MockSimilarCaseRecommender` 替换为调用 memory-rag 的真实实现，只需实现 `SimilarCaseRecommender` 接口即可，工作流无需改动。
- **图片 OCR/视觉理解**：在 `server._handle_image()` 中集成图片理解服务，将生成的摘要和 OCR 文本写入 `RegisterImageRequest`，再流转到工作流。
- **WebSocket / SSE 事件**：使用已定义的 `CaseAgentEvent` 封装推送事件，替换当前轮询式响应。
- **会话持久化**：将 `_SessionStore` 替换为数据库后端（SQLite / Redis / PostgreSQL）。

---

## 7. 本地启动

```bash
# 启动 Server
PYTHONPATH=src python -m case_agent.server --port 8765

# 在另一个终端使用 CLI（InProcessTransport 默认，无需 server）
PYTHONPATH=src python -m case_agent.cli
```
