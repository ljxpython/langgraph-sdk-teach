# 05. 官方参考索引

下面这些是学习 `example/ui_demo` 时最值得反复看的官方材料。

## 1) 项目源码与说明

1. Agent Chat UI 仓库
   - https://github.com/langchain-ai/agent-chat-ui
2. 项目 README（包含生产化说明）
   - https://github.com/langchain-ai/agent-chat-ui/blob/main/README.md

## 2) React useStream 官方资料

1. Frontend Streaming（官方，含 `useStream` 参数与返回值）
   - https://docs.langchain.com/oss/javascript/langchain/streaming/frontend
2. Agent Chat UI（官方能力说明）
   - https://docs.langchain.com/oss/javascript/langgraph/ui
3. JS API Reference（LangGraph.js）
   - https://langchain-ai.github.io/langgraphjs/reference/index.html

## 3) Generative UI（react-ui）

1. Generative UI in React（`uiMessageReducer` / `LoadExternalComponent`）
   - https://docs.langchain.com/langgraph-platform/generative-ui-react

## 4) 生产代理与鉴权

1. Next.js API passthrough 包（NPM）
   - https://www.npmjs.com/package/langgraph-nextjs-api-passthrough
2. 对应 GitHub（README 含注意事项）
   - https://github.com/bracesproul/langgraph-nextjs-api-passthrough
3. Auth & Access Control（平台文档）
   - https://docs.langchain.com/langgraph-platform/auth
4. Custom Authentication（文档）
   - https://docs.langchain.com/langsmith/custom-auth
5. LangGraph 平台 Custom Auth 入门
   - https://docs.langchain.com/langgraph-platform/custom-auth
6. LangGraph Python 自定义鉴权入门
   - https://langchain-ai.github.io/langgraph/tutorials/auth/getting_started/
7. LangGraphJS TypeScript 自定义鉴权
   - https://langchain-ai.github.io/langgraphjs/how-tos/auth/custom_auth/

## 5) 重要结论（外部资料交叉验证）

1. `useStream` 官方明确支持：branching、interrupt、optimistic update、custom events。
2. Generative UI 官方推荐模式就是本项目用的：`onCustomEvent + uiMessageReducer + LoadExternalComponent`。
3. `langgraph-nextjs-api-passthrough` 仓库 README 已明确：更推荐迁移到 LangGraph custom auth。

## 6) 阅读策略（建议）

1. 先看本地代码：`Stream.tsx`、`Thread.tsx`、`thread/index.tsx`
2. 再对照 `useStream` 官方文档，确认每个 options 的语义
3. 最后看生产化章节（passthrough/custom auth），决定你自己的上线路径
