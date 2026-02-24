# LangGraph 本地与生产开发模式手册

## 目标

- 讲清楚本地开发与生产部署的边界与取舍。
- 明确个人开发者的最小可行方案（先跑通，再可运营）。
- 避免在 Platform API 层重复实现一套 LangGraph 原生 API。

## 文档索引

1. `01-thread-identity-isolation-playbook.md`：线程创建归属、用户隔离、平台与 LangGraph 解耦/关联的最佳方案。
2. `02-platform-langgraph-global-interaction-model.md`：平台与 LangGraph 全局交互面、通信契约、幂等顺序、错误模型与治理策略。
3. `03-manageable-capabilities-via-passthrough.md`：可查询/可修改能力矩阵（threads/runs/assistants）与透传管理落地方案。
4. `04-postgres-vs-mysql-vs-sqlite.md`：数据库选型差异与在 LangGraph 场景下的落地建议。

## 一句话结论

- 本地：可以前端直连 LangGraph（调试效率优先）。
- 生产：前端不直连 LangGraph，采用 `Frontend -> Platform API/BFF -> LangGraph`。
- 聊天能力优先走 LangGraph Custom Auth 直连；passthrough 仅作为过渡方案。
- 业务能力走平台语义 API（双通道）。

## 三种模式对比

| 模式 | 调用链 | 适用阶段 | 优点 | 风险 |
|---|---|---|---|---|
| 本地直连 | Frontend -> LangGraph | 本地联调、Demo | 上手最快 | 密钥/鉴权不可控，不适合生产 |
| 平台封装（推荐） | Frontend -> Platform API -> LangGraph | 个人开发者生产阶段 | 统一鉴权、审计、成本治理 | 需要设计业务 API |
| 双通道混合（推荐增强） | Chat: Frontend -> LangGraph(Custom Auth)；Business: Frontend -> Platform API -> LangGraph | AI 只是平台一部分 | 不重复造轮子，扩展性最好 | 需要清晰路由边界 |

## 推荐架构（个人开发者，生产可用）

```text
                         ┌──────────────────────────────┐
                         │           Frontend           │
                         │ Chat 页面 + 平台业务页面      │
                         └──────────────┬───────────────┘
                                        │
                  ┌─────────────────────┴─────────────────────┐
                  │                                           │
                  ▼                                           ▼
       ┌──────────────────────────┐                ┌──────────────────────────┐
       │ LangGraph Custom Auth    │                │      Platform API         │
       │ (聊天直连受控鉴权)          │                │ (仅业务语义接口)           │
       └──────────────┬───────────┘                └──────────────┬───────────┘
                      │                                             │
                      └─────────────────────┬───────────────────────┘
                                            ▼
                                 ┌──────────────────────┐
                                 │   LangGraph Server   │
                                 └──────────────────────┘
```

## 关键设计原则

1. Platform API 不复刻 `/threads` `/runs` `/assistants`。
2. Platform API 只暴露业务动作，例如：
   - `POST /api/work-items/{id}/summarize`
   - `POST /api/okr/{id}/risk-analysis`
3. 通用聊天优先采用 LangGraph Custom Auth；passthrough 仅用于短期过渡。
4. LangGraph 原语仅在后端内部使用，不直接暴露给业务前端。

## 本地开发模式（建议）

### 模式 A：最快联调（前端直连）

```text
Frontend -> LangGraph
```

- 场景：调 Agent 行为、调 prompt、看 streaming。
- 不做：真实用户鉴权、生产密钥管理。

### 模式 B：贴近生产（推荐日常开发）

```text
Frontend -> Platform API/BFF -> LangGraph
```

- 场景：联调业务接口、权限、审计、成本统计。
- 建议：本地也保留 passthrough 路由，便于聊天页面快速回归。

## 生产模式（推荐落地顺序）

1. 先上线双通道骨架：聊天走 Custom Auth 直连，业务走 Platform API。
2. 在 Platform API 落最小治理字段：`trace_id`、`thread_id`、`run_id`、`latency`、`status`、`cost`。
3. 增加可观测：失败重试、告警、关键事件检索（done/error/__interrupt__）。
4. 逐步收敛到平台能力中心：权限、配额、审计、模型路由策略。

## 不该做的事

- 不要把 LangGraph 全部端点在 FastAPI 原封不动再抄一遍。
- 不要让前端同时依赖两套语义（平台语义 + LangGraph 原语）处理同一业务流。
- 不要在生产把 `LANGSMITH_API_KEY` 暴露到浏览器端。

## 与当前仓库的映射

- passthrough 示例：`example/ui_demo/src/app/api/[..._path]/route.ts`
- 聊天 UI 生产说明：`example/ui_demo/README.md`
- 当前 FastAPI 封装层：`fastapi_src/`
- 历史调研结论：`docs/agent-deployment-research.md`

## 个人开发 vs 团队开发（生产模式差异）

| 维度 | 个人开发（建议） | 团队开发（常见） |
|---|---|---|
| 架构复杂度 | 单体优先：`Platform API + LangGraph` | 分层拆分：BFF、AI Gateway、异步任务、观测系统 |
| 接口策略 | 先最小闭环，少量 passthrough | 稳定业务契约、版本化、兼容策略 |
| 权限模型 | 单租户或轻量 RBAC | 多租户、细粒度 RBAC、审计追踪 |
| 发布方式 | 手动/半自动发布，快速迭代 | CI/CD、灰度、回滚、值班响应 |
| 可观测性 | 基础日志 + 关键 run 指标 | 全链路 tracing、SLO/告警、容量评估 |
| 成本治理 | 看总账即可 | 按租户/项目/功能做成本分摊与预算控制 |
| 数据治理 | 最小留存与备份 | 脱敏、分级留存、合规审计 |

一句话：个人模式追求“先可用”，团队模式追求“可控、可协作、可持续扩展”。

## 最佳方案（当前建议）

- 你是个人开发者，且 AI 是平台子模块：优先采用“**双通道混合架构**”。
- 原则：
  - Chat 优先用 Custom Auth（长期更可控）
  - passthrough 仅作过渡（快速上线、后续迁移）
  - 业务用 Platform API（可控、可治理、可演进）
- 这条路线在开发效率与长期维护之间最平衡。

## 最新接入说明（agent-chat-ui）

- `agent-chat-ui` 的生产章节仍给出两种路径：Quickstart passthrough 与 Advanced custom auth。
- `langgraph-nextjs-api-passthrough` 仓库 Notice 已注明：不再是推荐方式，建议使用 LangGraph custom auth/routes。
- 因此本手册采用：**custom auth 为主，passthrough 为过渡**。
