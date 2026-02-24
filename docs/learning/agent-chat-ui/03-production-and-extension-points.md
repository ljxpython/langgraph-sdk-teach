# 03. 生产化与扩展点

## A. 连接模式与迁移路径

## A1. 本地学习模式（默认）

- 前端直接把 `apiUrl` 指向 LangGraph（例如 `http://localhost:2024`）
- `apiKey`（若有）由浏览器 localStorage 提供

适合学习与本地调试，链路最短。

## A2. 生产代理模式（推荐）

`src/app/api/[..._path]/route.ts` 提供 passthrough：

- 通过 `LANGGRAPH_API_URL` 指向后端部署地址
- 可选注入 `LANGSMITH_API_KEY`
- 前端只配置 `NEXT_PUBLIC_API_URL=https://your-site/api`
- 以 `runtime: "edge"` 运行，并透传 `GET/POST/PUT/PATCH/DELETE/OPTIONS`
- 若 `LANGGRAPH_API_URL` 缺失，会返回可读错误提示而不是低层网络报错

价值：避免把密钥放在浏览器，统一服务端鉴权策略。

补充：`langgraph-nextjs-api-passthrough` 仓库 README 已提示该方案更偏“快速落地”，长期建议迁移到 LangGraph 自定义鉴权与路由能力。

## A3. 自定义鉴权模式（进阶）

官方 README 已给迁移思路：

1. 先拿到你自己的鉴权 token
2. 在 `useTypedStream` 里通过 `defaultHeaders` 注入
3. `NEXT_PUBLIC_API_URL` 指向你的受保护部署

这是更长期、可控性更强的方案（权限模型、资源隔离、审计更完整）。

## B. 代码级扩展点（按优先级）

## B1. 鉴权与连接

- `src/providers/Stream.tsx`
  - 扩展 `useTypedStream({... defaultHeaders ...})`
  - 自定义连通性探测（`checkGraphStatus`）
- `src/app/api/[..._path]/route.ts`
  - 替换/扩展代理注入逻辑

## B2. 消息渲染策略

- `src/components/thread/messages/ai.tsx`
  - 自定义 tool call 展示
  - 自定义 interrupt 视图路由
  - 自定义 `LoadExternalComponent` 的 `meta`
- `src/components/thread/messages/human.tsx`
  - 编辑交互与重提交流

## B3. HITL 决策策略

- `src/components/thread/agent-inbox/hooks/use-interrupted-actions.tsx`
  - `resume`/`goto END` 的提交逻辑
- `src/components/thread/agent-inbox/components/thread-actions-view.tsx`
  - 多 action 的批量 approve/submit 策略
- `src/components/thread/agent-inbox/utils.ts`
  - 默认决策优先级、决策构建规则

## B4. 多模态输入策略

- `src/hooks/use-file-upload.tsx`
  - 文件类型、大小、去重策略
  - 拖拽/粘贴行为
- `src/lib/multimodal-utils.ts`
  - 文件到内容块编码方式

## B5. 线程检索策略

- `src/providers/Thread.tsx`
  - `threads.search()` 的过滤 metadata 与 limit
  - assistant_id 与 graph_id 的切换逻辑

## C. 你可以立刻做的 8 个改造

1. 在 `Stream.tsx` 加 token header（接你自己的 auth）。
2. 把 `checkGraphStatus` 从 `info` 扩展成更完整健康检查。
3. 给 `threads.search` 增加分页与时间排序。
4. 给 `use-file-upload` 增加文件大小上限和压缩策略。
5. 在 tool result 中增加“原始 JSON / 可视化”双视图切换。
6. 给 interrupt 决策加审计日志（decision + timestamp + user）。
7. 把 `sleep(4000)` 的 thread 刷新改为更稳的后端确认机制。
8. 在 API passthrough 层加请求追踪头与错误归一化。

## D. 调研中发现的注意点

1. `Thread` 组件里有 TODO：首 token 识别逻辑希望沉到 `useStream`。
2. `onThreadId` 使用固定延时刷新线程列表，存在时序依赖。
3. 目前 CI 只做 format/lint/spelling，不做 e2e 功能回归。
4. “永久隐藏消息”依赖双约束：
   - 后端把消息 ID 改成 `do-not-render-*`
   - 前端在消息列表过滤该前缀（`src/components/thread/index.tsx`）

这些不是 bug，但都是你后续工程化时应优先处理的位置。
