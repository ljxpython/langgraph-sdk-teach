# 05. 官方参考索引

下面给出 10 条高信号官方资料，每条都映射到 `example/ui_demo` 的对应实现位置。

## 1) 10 条官方资料（URL + 对应代码）

1. https://github.com/langchain-ai/agent-chat-ui
   - 作用：项目总入口与目录基线。
   - 对应代码：`example/ui_demo/src/app/page.tsx`

2. https://github.com/langchain-ai/agent-chat-ui/blob/main/README.md
   - 作用：生产化章节（passthrough 与 custom auth 迁移路线）。
   - 对应代码：`example/ui_demo/src/app/api/[..._path]/route.ts`

3. https://docs.langchain.com/oss/javascript/langgraph/ui
   - 作用：Agent Chat UI 官方能力总览。
   - 对应代码：`example/ui_demo/src/components/thread/index.tsx`

4. https://docs.langchain.com/oss/javascript/langchain/streaming/frontend
   - 作用：`useStream` 参数/返回值、branching、interrupt、optimistic update。
   - 对应代码：`example/ui_demo/src/providers/Stream.tsx`

5. https://docs.langchain.com/langgraph-platform/generative-ui-react
   - 作用：`onCustomEvent + uiMessageReducer + LoadExternalComponent` 官方模式。
   - 对应代码：`example/ui_demo/src/components/thread/messages/ai.tsx`

6. https://docs.langchain.com/langgraph-platform/auth
   - 作用：平台 AuthN/AuthZ 机制与资源级访问控制语义。
   - 对应代码：`docs/learning/agent-chat-ui/08-local-to-production-migration.md`

7. https://docs.langchain.com/langgraph-platform/custom-auth
   - 作用：LangGraph 平台 custom auth 的实现入口。
   - 对应代码：`example/ui_demo/src/providers/Stream.tsx`

8. https://docs.langchain.com/langsmith/custom-auth
   - 作用：部署侧自定义鉴权与用户上下文注入。
   - 对应代码：`docs/learning/agent-chat-ui/03-production-and-extension-points.md`

9. https://www.npmjs.com/package/langgraph-nextjs-api-passthrough
   - 作用：Next.js 代理包说明与 API 透传方式。
   - 对应代码：`example/ui_demo/src/app/api/[..._path]/route.ts`

10. https://github.com/bracesproul/langgraph-nextjs-api-passthrough
    - 作用：透传包源码与 README 注意事项（并指出 custom auth 的长期方向）。
    - 对应代码：`example/ui_demo/src/app/api/[..._path]/route.ts`

## 2) 交叉结论

1. `useStream` 是 `ui_demo` 的运行时核心，覆盖消息流、分支、中断、恢复。
2. Generative UI 在本项目中严格遵循官方推荐范式。
3. passthrough 适合快速上线，长期应迁移到 custom auth。

## 3) 阅读顺序建议

1. 先读 `Stream.tsx` 与 `thread/index.tsx`。
2. 再对照第 4、5 条文档确认流式与 UI 事件语义。
3. 最后读第 6~10 条完成生产化路线选择。
