# 08. 本地到生产迁移手册

## 目标

把 `example/ui_demo` 从“本地直连 LangGraph”迁移到“生产可控、安全可审计”的部署模式。

## 路线选择

## 路线 A：快速代理（API passthrough）

适合：先上线、尽快把密钥移出浏览器。

关键文件：

- `example/ui_demo/src/app/api/[..._path]/route.ts`
- `example/ui_demo/.env.example`
- `example/ui_demo/src/providers/Stream.tsx`

环境变量：

```bash
NEXT_PUBLIC_ASSISTANT_ID="agent"
LANGGRAPH_API_URL="https://your-deployment"
NEXT_PUBLIC_API_URL="https://your-site/api"
LANGSMITH_API_KEY="lsv2_..."
```

验收：

1. 前端请求命中 `/api/*`（而非直接命中 LangGraph 域名）。
2. 浏览器端不再保存服务端密钥。
3. thread/runs/stream 接口可正常调用。

## 路线 B：自定义鉴权（长期推荐）

适合：多租户、细粒度授权、合规场景。

核心思路：

1. 在 LangGraph 部署侧实现 custom auth（认证 + 授权 handler）。
2. 前端拿到你自己的用户 token（短期、可刷新）。
3. 在 `useTypedStream` 中通过 `defaultHeaders` 注入 token。
4. 用资源级授权保证“用户只看到自己的 threads/runs”。

## 最小迁移步骤（建议顺序）

1. **先切网络路径**
   - 把 `NEXT_PUBLIC_API_URL` 指向站点 `/api`。
2. **再切鉴权来源**
   - 移除 localStorage 长期密钥依赖，改服务端签发短 token。
3. **最后做授权隔离**
   - 在 LangGraph auth 层写 owner-based 过滤。

## 你需要改的 6 个位置

1. `src/providers/Stream.tsx`
   - `useTypedStream` 增加 `defaultHeaders`（Bearer token）。
2. `src/lib/api-key.tsx`
   - 逐步下线 localStorage 密钥方案。
3. `src/app/api/[..._path]/route.ts`
   - 统一代理注入、错误归一化、审计头。
4. `src/providers/Thread.tsx`
   - 线程检索加权限语义（至少按 owner 隔离）。
5. `src/components/thread/agent-inbox/hooks/use-interrupted-actions.tsx`
   - 对关键决策操作增加幂等与审计。
6. `src/hooks/use-file-upload.tsx`
   - 增加文件大小与类型安全策略。

## 风险与回滚

1. 风险：token 注入失败导致全部请求 401。
   - 回滚：临时切回 passthrough + server key（仅短期）。
2. 风险：授权规则过严导致“看不到历史线程”。
   - 回滚：先放宽 read 过滤，保留 write 保护。
3. 风险：上传限制过严影响体验。
   - 回滚：灰度开启限制并记录命中日志。

## 迁移完成定义（DoD）

- [ ] 浏览器端没有长期敏感密钥
- [ ] 认证失败返回明确 401，授权失败明确 403
- [ ] 线程隔离可验证（A 用户看不到 B 用户数据）
- [ ] 中断决策（approve/edit/reject）可审计
- [ ] 错误与重试策略可观测（日志/trace 可追踪）
