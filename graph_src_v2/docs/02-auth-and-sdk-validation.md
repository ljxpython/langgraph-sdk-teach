# v2 Auth 与 SDK 验证指南

## 1. 认证模式

### 1.1 Demo 模式（默认）

- `langgraph.json`：`auth.path = ./graph_src_v2/auth.py:custom_auth`
- 可用测试 token：
  - `owner-token`
  - `viewer-token`
  - `admin-token`

### 1.2 OAuth 模式（Supabase）

- 将 `langgraph.json` 的 `auth.path` 改为 `./graph_src_v2/auth.py:oauth_auth`
- `.env` 需配置：`SUPABASE_URL`、`SUPABASE_SERVICE_KEY`

## 2. 推荐验证顺序（SDK）

1. owner 可创建 thread。
2. viewer 不能创建 thread（403）。
3. owner 创建的 thread，viewer 不能读取（403/404）。
4. owner 可在自己 thread 上执行 run。

## 3. 启动服务

在项目根目录执行（必须指定 v2 config）：

```bash
uv run langgraph dev --config graph_src_v2/langgraph.json --port 8123 --no-browser
```

## 4. 自动化测试

测试目录：`tests/graph_v2`

运行：

```bash
pytest tests/graph_v2 -q
```
