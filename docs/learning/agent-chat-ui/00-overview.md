# 00. 项目总览

## 这是什么

`example/ui_demo` 是一个基于 Next.js 的通用 Agent Chat 前端，面向“任何具备 `messages` 状态键的 LangGraph 服务”。

它的核心价值不是“做一个炫 UI”，而是把 LangGraph 的运行时语义（stream、thread、interrupt、branch、UI event）稳定映射为可交互前端。

## 最小核心能力

1. 配置连接（`apiUrl` / `assistantId` / `apiKey`）
2. 多线程会话（创建、切换、历史回放）
3. 流式消息渲染（含工具调用与工具结果）
4. 中断处理（HITL 决策：approve/edit/reject、resume、resolve）
5. 可选 generative UI 组件渲染（`values.ui` + 外部组件加载）

## 关键依赖

- 框架：`next@15` + `react@19`
- LangGraph：`@langchain/langgraph-sdk`、`@langchain/langgraph-sdk/react`、`@langchain/langgraph-sdk/react-ui`
- URL 状态：`nuqs`
- 交互与 UI：`framer-motion`、`sonner`、`shadcn/ui` 组件集合

## 样式与工程配置

- Tailwind + CSS 变量主题：`src/app/globals.css`
- Shadcn 配置：`components.json`
- Next 实验配置：`next.config.mjs`（`serverActions.bodySizeLimit=10mb`）
- TS 严格模式开启：`tsconfig.json`（`strict: true`）
- CI 基线：`.github/workflows/ci.yml`（format/lint/spelling）

## 核心入口

- 页面入口：`example/ui_demo/src/app/page.tsx`
- 根布局：`example/ui_demo/src/app/layout.tsx`
- Stream Provider：`example/ui_demo/src/providers/Stream.tsx`
- Thread Provider：`example/ui_demo/src/providers/Thread.tsx`
- 主聊天组件：`example/ui_demo/src/components/thread/index.tsx`

## 配置模型（非常重要）

- URL Query State：`apiUrl`、`assistantId`、`threadId`、`chatHistoryOpen`、`hideToolCalls`
- localStorage：`lg:chat:apiKey`
- 环境变量：
  - `NEXT_PUBLIC_API_URL`
  - `NEXT_PUBLIC_ASSISTANT_ID`
  - `LANGGRAPH_API_URL`（服务端代理目标）
  - `LANGSMITH_API_KEY`（服务端注入）

这套设计让该项目同时支持：

- 本地学习：前端直接连 LangGraph
- 生产部署：前端连本站 `/api`，由 Next route 代理到 LangGraph
