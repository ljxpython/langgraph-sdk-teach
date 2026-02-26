# graph_src_v2 新手开发与使用指南

`graph_src_v2` 是纯执行层：负责 LangGraph 图运行、运行时参数解析、工具/MCP 装配与鉴权。

## 1) 先理解这套最小心智模型

- 图入口：`assistant`、`deepagent_demo`、`deepagents_data_analysis_demo`、`personal_assistant_demo`、`customer_support_handoffs_demo`、`router_knowledge_base_demo`、`skills_sql_assistant_demo`
- 运行时配置：`runtime/options.py`（模型、工具、MCP 开关与参数）
- 模型装配：`runtime/modeling.py`
- 工具装配：`tools/registry.py`
- MCP 清单：`mcp/servers.py`
- 自定义路由：`custom_routes/app.py` + `custom_routes/tools.py`
- 鉴权：`auth/provider.py`（`custom_auth` + `oauth_auth`）

## 2) 本地启动（推荐）

在项目根目录执行：

```bash
uv run langgraph dev --config graph_src_v2/langgraph.json --port 8123 --no-browser
```

默认行为：

- `langgraph.json` 本地模式不启用 auth
- 默认不启用本地 tools（`enable_local_tools=false`）
- 默认不启用 MCP（`enable_local_mcp=false`）

### 2.1 personal_assistant_demo 是什么

- 迁移自 LangChain 官方 `subagents-personal-assistant` 示例
- 三层结构：低层日历/邮件工具 → calendar/email 子 agent → supervisor agent
- 设计原则：最小可运行、薄封装、无额外注册层

### 2.2 customer_support_handoffs_demo 是什么

- 迁移自 LangChain 官方 `handoffs-customer-support` 示例
- 核心机制：单 agent + 状态机 step 切换（`warranty_collector` → `issue_classifier` → `resolution_specialist`）
- 通过 tool 返回 `Command(update=...)` 更新工作流状态，不做过度封装

### 2.3 router_knowledge_base_demo 是什么

- 迁移自 LangChain 官方 `router-knowledge-base` 示例
- 核心机制：分类路由 -> 并行查询 github/notion/slack 专家 -> 最终综合回答
- 使用 `StateGraph + Send` 显式并行路由，保持最小实现与可读性

### 2.4 skills_sql_assistant_demo 是什么

- 迁移自 LangChain 官方 `skills-sql-assistant` 示例
- 核心机制：通过 middleware 暴露 skills 摘要，按需用 `load_skill` 加载详细 schema/业务规则
- 目标：减少上下文冗余（progressive disclosure），保持单 agent 对话体验

### 2.5 deepagents_data_analysis_demo 是什么

- 迁移自 LangChain 官方 `deepagents/data-analysis` 示例
- 核心能力：读取本地数据文件、执行分析脚本、生成可视化产物并在最终回复中回报产物路径
- 按你的要求移除了 Slack 交付流程，仅保留本地产物工作流

## 3) 最快可用验证路径

### 3.1 直接跑测试

```bash
uv run pytest graph_src_v2/tests/test_auth_core.py graph_src_v2/tests/test_custom_routes.py graph_src_v2/tests/test_model_smoke.py -q
```

### 3.2 HTTP 手工验证（不依赖外部目录）

```bash
curl -sS http://127.0.0.1:8123/internal/capabilities/tools
curl -sS http://127.0.0.1:8123/internal/capabilities/mcp-servers
curl -sS -X POST http://127.0.0.1:8123/internal/capabilities/resolve -H "Content-Type: application/json" -d '{"enable_local_tools":true,"local_tools":["word_count"]}'
```

## 4) 运行时参数怎么传（最常用）

你通常通过 `context` / `configurable` 传：

- `model_id`
- `enable_local_tools`
- `local_tools`（例如 `word_count,to_upper`）
- `enable_local_mcp`
- `mcp_servers`（例如 `local_math,local_text`）
- 可选模型参数：`temperature`、`max_tokens`、`top_p`

说明：`model_provider/model/base_url/api_key` 不需要用户传，统一由 `conf/settings.yaml` 的模型组映射。

## 5) 自定义路由（给其他服务查询能力）

已暴露在同一服务下：

- `GET /internal/capabilities/tools`
- `GET /internal/capabilities/mcp-servers`
- `POST /internal/capabilities/resolve`

用途：让外部服务先查询“可用能力”与“本次请求最终会启用哪些能力”。

## 6) deepagent 的约定（已简化）

`deepagent_demo` 现在走官方风格薄封装：

- 直接 `create_deep_agent(...)`
- `skills` 来自 `list_deepagent_skills()`
- `subagents` 来自 `list_subagents()`
- 不再使用复杂的 runtime 动态 subagent 解析链

## 7) 推荐开发流程（团队统一）

1. 改代码前先确认目录职责，不跨层引用
2. 改完先跑：
   - `uv run pytest graph_src_v2/tests/test_auth_core.py graph_src_v2/tests/test_custom_routes.py graph_src_v2/tests/test_model_smoke.py -q`
   - `uv run python -m compileall graph_src_v2`
3. 若改了运行时行为，更新本 README 与 `01-auth-and-sdk-validation.md`

## 8) 常见问题

- 为什么工具没生效？
  - 默认关闭，需显式设置 `enable_local_tools=true`。
- 为什么 MCP 没生效？
  - 默认关闭，需显式设置 `enable_local_mcp=true`，并传 `mcp_servers`。
- 为什么只传了 `model_id` 就能跑？
  - 因为模型四元组由 `settings.yaml` 统一映射。
