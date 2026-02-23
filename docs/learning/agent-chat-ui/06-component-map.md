# 06. 组件依赖图与职责矩阵

## 1) 顶层依赖图（从页面入口看）

```text
app/page.tsx
  └─ ThreadProvider
      └─ StreamProvider
          └─ ArtifactProvider
              └─ Thread (components/thread/index.tsx)
                  ├─ ThreadHistory
                  ├─ HumanMessage
                  ├─ AssistantMessage
                  ├─ ContentBlocksPreview -> MultimodalPreview
                  └─ Artifact
```

## 2) Thread 主编排层

- `src/components/thread/index.tsx`
  - 负责输入框、提交、停止、新建线程、历史侧栏开关。
  - 负责消息列表渲染分发（human -> `HumanMessage`，其余 -> `AssistantMessage`）。
  - 负责隐藏“仅用于工具补全”的虚拟消息（`do-not-render-` 前缀）。

## 3) 消息渲染层

### 3.1 HumanMessage

- 文件：`src/components/thread/messages/human.tsx`
- 职责：
  - 渲染用户消息文本/多模态附件。
  - 提供编辑能力并在 parent checkpoint 上重提交流。
  - 提供 branch 切换入口（`thread.setBranch`）。

### 3.2 AssistantMessage

- 文件：`src/components/thread/messages/ai.tsx`
- 职责：
  - 渲染 AI 文本（Markdown）。
  - 渲染 tool call 和 tool result。
  - 渲染 interrupt（HITL 专用或 generic）。
  - 渲染生成式 UI（`LoadExternalComponent` + `values.ui`）。
  - 提供 regenerate 和 branch 切换。

### 3.3 Shared 操作条

- 文件：`src/components/thread/messages/shared.tsx`
- 组件：`CommandBar`, `BranchSwitcher`
- 作用：抽离复制、编辑、刷新、左右分支切换等重复交互。

## 4) Interrupt（HITL）层

- schema 判定：`src/lib/agent-inbox-interrupt.ts`
- 主视图：`src/components/thread/agent-inbox/index.tsx`
- 决策状态机：`src/components/thread/agent-inbox/hooks/use-interrupted-actions.tsx`
- 多 action 编排：`src/components/thread/agent-inbox/components/thread-actions-view.tsx`
- 输入卡片：`src/components/thread/agent-inbox/components/inbox-item-input.tsx`
- 状态树：`src/components/thread/agent-inbox/components/state-view.tsx`

这组组件共同实现了：approve/edit/reject、批量提交、`resume`、`goto END`。

## 5) 多模态层

- 上传流程 Hook：`src/hooks/use-file-upload.tsx`
- 文件转换工具：`src/lib/multimodal-utils.ts`
- 预览组件：
  - `src/components/thread/ContentBlocksPreview.tsx`
  - `src/components/thread/MultimodalPreview.tsx`

## 6) Artifact（右侧扩展面板）

- 文件：`src/components/thread/artifact.tsx`
- 核心：`ArtifactProvider` + `useArtifact`
- 作用：
  - 为外部动态组件提供“可打开侧面板 + 上下文 bag”。
  - 用 Portal 挂载扩展内容，不污染主聊天流布局。

## 7) 历史线程层

- 文件：`src/components/thread/history/index.tsx`
- 作用：
  - 拉取线程列表并按首条消息摘要展示。
  - 点击后写入 query `threadId` 触发切换。
  - 桌面侧栏 + 移动端 Sheet 双形态。

## 8) UI Primitive 层（shadcn/radix 封装）

- 目录：`src/components/ui/*`
- 关键点：
  - `button.tsx` 使用 cva 管理 variant/size。
  - `sheet.tsx` 支持移动端抽屉。
  - `tooltip.tsx`、`password-input.tsx` 为高复用交互基座。

## 9) 最值得复用的 3 个设计

1. Provider 分层清晰：线程查询与运行流分离。
2. 消息渲染分发明确：`Thread` 只分发，细节下沉到 message 子组件。
3. Interrupt 走独立子系统：不会污染普通消息渲染逻辑。
