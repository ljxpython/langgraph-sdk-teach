# 03. 平台可管理能力矩阵（基于 LangGraph API 透传）

## 结论先行

你的判断是对的：平台侧要做管理，通常离不开“透传/代理 LangGraph API”这条路。

但“透传”不等于“复刻全部 API”。推荐做法是：

- 保留一层平台适配（鉴权、审计、限流、映射）
- 只开放你业务需要的管理能力子集

同时根据最新官方生态建议：

- LangGraph 接入优先走 **Custom Auth + Custom Routes**。
- `langgraph-nextjs-api-passthrough` 作为快速上线的过渡方案，不作为长期默认。

## 能力矩阵（可查询 / 可修改）

| 资源域 | 可查询能力 | 可修改能力 | 官方 API 证据 | 本仓库调用证据 |
|---|---|---|---|---|
| Threads | 创建、读取、搜索、计数、状态、历史 | 更新线程、更新线程状态、复制、删除 | `POST /threads`、`POST /threads/search`、`PATCH /threads/{thread_id}`、`POST /threads/{thread_id}/state`、`DELETE /threads/{thread_id}` | `sdk_src/examples/langgraph_sdk_learn_threads.py`、`fastapi_src/services/chat_service.py` |
| Thread Runs | 创建、列表、详情、等待完成、join、join_stream | 取消（interrupt/rollback）、resume（command） | `POST /threads/{thread_id}/runs`、`GET /threads/{thread_id}/runs`、`GET /threads/{thread_id}/runs/{run_id}`、`POST /threads/{thread_id}/runs/wait`、`GET /threads/{thread_id}/runs/{run_id}/join`、`GET /threads/{thread_id}/runs/{run_id}/stream`、`POST /threads/{thread_id}/runs/{run_id}/cancel` | `sdk_src/examples/langgraph_sdk_learn_runs.py`、`fastapi_src/api/routes.py`、`fastapi_src/services/chat_service.py` |
| Assistants | 搜索、计数、读取、读 schema/graph/versions | 创建、更新、切版本、删除 | `POST /assistants`、`POST /assistants/search`、`POST /assistants/count`、`GET /assistants/{assistant_id}`、`PATCH /assistants/{assistant_id}`、`POST /assistants/{assistant_id}/latest`、`DELETE /assistants/{assistant_id}` | `sdk_src/examples/langgraph_sdk_learn_assistants.py`、`fastapi_src/services/chat_service.py` |
| Streaming | 读取事件流（官方 event/data） | 运行时控制（mode、断连恢复、取消） | Streaming 文档 + join stream/cancel run 文档 | `fastapi_src/api/routes.py`、`docs/learning/langgraph-sdk/17-streaming-frontend-backend-standard.md` |

## 关键事实（可核验）

1. Agent Server API 官方分组明确包含 `Threads`、`Thread Runs`、`Assistants`。
   - 参考：`https://docs.langchain.com/langgraph-platform/server-api-ref`

2. 官方文档页面可直接看到线程与运行的增删改查及控制端点：
   - `create-thread`、`search-threads`、`patch-thread`、`update-thread-state`、`delete-thread`
   - `list-runs`、`get-run`、`create-run-wait-for-output`、`join-run`、`join-run-stream`、`cancel-run`

3. 本仓库已有落地代码证明这些能力可被平台封装：
   - `fastapi_src/services/chat_service.py` 已使用 `threads.create/get/search/get_state/get_history`、`runs.wait`、`assistants.search/get/create/update/delete`
   - `fastapi_src/api/routes.py` 已提供 stream/wait/resume/state/history/assistants 管理接口

## 平台侧怎么“管理”而不“重造”

推荐将管理拆成三层：

1. **透传层**（最薄）
- 负责签名、鉴权、速率限制、统一错误码

2. **索引层**（平台自有）
- 保存 `platform_session_id <-> thread_id`
- 保存 `trace_id/run_id/thread_id/user_id/tenant_id/status/cost`

3. **策略层**（平台治理）
- RBAC、配额、审计、删除策略、重试策略

这样平台“管理”的是：访问与治理，而不是复制 LangGraph 的执行内核。

## 控制强度分级（非常重要）

| 模式 | thread 创建入口 | 平台控制力 | 适用场景 |
|---|---|---|---|
| 强控制 | 平台边界创建 thread | 强（可审计、可配额、可强一致） | 正式生产 |
| 弱控制 | 客户端直连创建 thread + 平台绑定校验 | 中（可索引，弱一致） | 过渡期/混合模式 |
| 失控 | 客户端直连且不回报绑定 | 弱（基本不可治理） | 不建议 |

## 最佳落地建议（个人开发者）

1. 先用透传拿到能力闭环（不复刻全 API）。
2. 立刻加索引层（会话映射 + run 日志）。
3. 优先实现四个管理动作：
   - 会话打开/绑定
   - 消息执行（wait/stream）
   - run 取消/恢复
   - 会话状态查询
4. 再按需补 assistants 管理和线程维护（搜索、归档、删除）。

## 平台侧可复用技术栈（当前推荐）

目标：不过度设计，优先复用成熟组件。

1. `FastAPI + Supabase Auth + Casbin`
   - FastAPI：平台 API 与适配层主体
   - Supabase Auth：用户认证与会话管理
   - Casbin：RBAC/资源级授权策略

2. 数据库与迁移（优先）
   - 全环境统一：`PostgreSQL`（开发/测试/生产）
   - 运行方式：`Docker`
   - ORM：`SQLAlchemy 2.0`（可选 `SQLModel`）
   - 迁移：`Alembic`
   - 驱动：`psycopg`

3. 前端对话入口（当前建议）
   - 长期默认：LangGraph `Custom Auth`
   - 过渡可用：`langgraph-nextjs-api-passthrough`

4. 任务与缓存（后置）
   - 轻量优先：`Redis + arq`
   - 规模上来后：`Celery + Redis`

5. 可观测（后置）
   - `OpenTelemetry + Prometheus + Grafana`
   - 平台日志至少统一落：`trace_id/platform_session_id/thread_id/run_id`

6. 限流与反向代理（后置）
   - 限流：`slowapi` 或网关层限流
   - 反向代理：`Traefik` 或 `Nginx`

### 官方链接

- FastAPI：`https://fastapi.tiangolo.com/`
- Supabase Auth：`https://supabase.com/auth`
- Casbin：`https://casbin.org/`
- LangGraph Custom Auth：`https://docs.langchain.com/langgraph-platform/custom-auth`
- Passthrough 仓库 Notice：`https://github.com/bracesproul/langgraph-nextjs-api-passthrough`

## 最小可运行骨架（已落地到仓库）

路径：`example/fastapi_supabase_casbin_minimal/`

- `app.py`：FastAPI 路由与权限保护示例
- `auth.py`：通过 Supabase `/auth/v1/user` 校验 Bearer Token
- `authz.py`：PyCasbin 鉴权（Casbin 的 Python 实现）
- `model.conf` / `policy.csv`：最小 RBAC 策略
- `README.md`：安装与启动步骤

说明：Casbin 虽然起源于 Go 生态，但在 FastAPI 场景下直接使用 `PyCasbin` 即可，不需要引入 Go 服务。

## 参考链接（官方）

- Server API 总览：`https://docs.langchain.com/langgraph-platform/server-api-ref`
- Use Threads：`https://docs.langchain.com/langgraph-platform/use-threads`
- Streaming：`https://docs.langchain.com/langgraph-platform/streaming`
- Custom Auth：`https://docs.langchain.com/langgraph-platform/custom-auth`
