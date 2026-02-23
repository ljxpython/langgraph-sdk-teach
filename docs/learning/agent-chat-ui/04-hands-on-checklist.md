# 04. 实操清单（按这个顺序练）

## 0) 启动

```bash
cd example/ui_demo
pnpm install
pnpm dev
```

默认访问：`http://localhost:3000`

## 1) 首次连接实验

- 在设置页填：
  - Deployment URL: `http://localhost:2024`
  - Assistant / Graph ID: `agent`
- 不填 API Key（本地一般不需要）

验收：进入聊天页，且 query 中出现 `apiUrl`、`assistantId`。

## 2) 基础消息流实验

- 发送一条普通文本
- 观察 `messages` 逐步渲染
- 点击 `Cancel` 验证 `stream.stop()`

验收：

- loading 状态正确切换
- 能中途停止输出

## 3) 线程历史实验

- 连续发 2~3 条消息
- 打开左侧 Thread History
- 点击历史线程切换

验收：

- query `threadId` 改变
- 消息随线程切换回放

## 4) 分支与重跑实验

- 对 AI 消息点 Refresh（regenerate）
- 对 Human 消息点 Edit 并提交
- 用 Branch 左右切换不同分支

验收：

- 分支索引变化（`x / n`）
- 不同分支内容可切换回看

## 5) Tool Calls 可视化实验

- 让后端触发 tool call
- 观察 ToolCalls / ToolResult 卡片
- 切换 `Hide Tool Calls`

验收：

- tool 请求和结果都可见
- `hideToolCalls` query 生效

## 6) HITL 中断实验

- 触发一个需要人工决策的 action
- 在 Agent Inbox 中尝试：approve / edit / reject
- 提交 `resume` 或 `mark resolved`

验收：

- interrupt 能正确展示
- 决策提交后流程继续或结束

## 7) 多模态输入实验

- 上传图片 + PDF
- 拖拽文件到输入区
- 粘贴截图到输入框

验收：

- 预览卡片出现
- 重复文件会提示 duplicate
- 非支持类型会提示 invalid type

## 8) 生产代理实验

在 `.env` 里配置：

```bash
NEXT_PUBLIC_ASSISTANT_ID="agent"
LANGGRAPH_API_URL="https://your-langgraph-deployment"
NEXT_PUBLIC_API_URL="http://localhost:3000/api"
LANGSMITH_API_KEY="lsv2_..."
```

重启后连接，验收请求走 `/api` 代理。

## 9) 最终验收（完成标准）

- [ ] 我能解释 provider 组合顺序为什么是现在这样
- [ ] 我能说清 submit -> stream -> render 的关键调用点
- [ ] 我能独立改一个扩展点（例如 token header）
- [ ] 我能把本地直连切到生产代理模式
