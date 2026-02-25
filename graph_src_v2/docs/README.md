# graph_src_v2 使用说明（执行层）

`graph_src_v2` 只负责 LangGraph 执行，不承载平台业务 API。

## 1. 目录定位

- `graph_src_v2/langgraph.json`：v2 图注册与 auth 配置入口。
- `graph_src_v2/agents/assistant_agent/graph.py`：assistant 编译图（内部组合 `create_agent`）。
- `graph_src_v2/agents/deepagent_agent/graph.py`：deepagent 编译图（内部组合 `create_deep_agent`）。
- `graph_src_v2/runtime/context.py`：统一运行时上下文契约（含身份字段）。
- `graph_src_v2/auth.py`：本地教学 token 认证/授权。
- `graph_src_v2/auth_oauth.py`：Supabase OAuth 认证/授权。

## 2. 启动（本地）

在项目根目录运行（必须指定 v2 config）：

```bash
uv run langgraph dev --config graph_src_v2/langgraph.json --port 8123 --no-browser
```

说明：

- 当前 `langgraph.json` 默认使用 `graph_src_v2/auth.py:custom_auth`。
- 如需 OAuth，改 `auth.path` 为 `./graph_src_v2/auth_oauth.py:oauth_auth`。

## 3. SDK 快速验证

在项目根目录运行（示例使用 demo token）：

```bash
uv run python sdk_src/examples/langgraph_sdk_learn.py thread-search --url http://127.0.0.1:8123 --assistant-id assistant --bearer-token owner-token
uv run python sdk_src/examples/langgraph_sdk_learn.py create-thread --url http://127.0.0.1:8123 --assistant-id assistant --bearer-token owner-token
uv run python sdk_src/examples/langgraph_sdk_learn.py wait-run --url http://127.0.0.1:8123 --assistant-id assistant --thread-id <thread_id> --message "你好，请回复ok" --bearer-token owner-token
```

更多验证见：`graph_src_v2/docs/02-auth-and-sdk-validation.md`。

## 4. 连接 `example/ui_demo`

推荐走 Next.js `/api` passthrough，避免浏览器直连 `8123` 的跨域失败：

1. 启动 v2 服务（不要省略 `--config`）：

```bash
uv run langgraph dev --config graph_src_v2/langgraph.json --port 8123 --no-browser
```

2. 在 `example/ui_demo` 目录复制环境文件：

```bash
cp .env.example .env
```

3. 启动 UI：

```bash
npm install
npm run dev
```

4. 页面中使用：

- Deployment URL: `http://localhost:3000/api`
- Assistant / Graph ID: `assistant`
- API Key: `owner-key`（或 `viewer-key`/`admin-key`）
