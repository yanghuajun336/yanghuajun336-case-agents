# CLI Interaction Expectations

## 核心命令

- `/new`：创建新会话
- `/message <text>`：输入问题文本
- `/image <name>|<summary>`：添加图片元数据
- `/similar`：查看相似案例
- `/draft`：查看当前草稿
- `/finalize`：当草稿完整时输出 skill/memory 预览
- `/help`：命令帮助
- `/exit`：退出

## 交互预期

- 自然语言输入与命令输入共存
- 每次消息后尽早刷新相似案例建议
- 草稿字段可持续补全，未完整时阻止 finalize
- finalize 只做结构化预览，不在 MVP 内执行远端 skill
