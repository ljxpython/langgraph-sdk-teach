# Supabase OAuth 实战手册（可直接复用）

> 参考官方：`https://docs.langchain.com/langsmith/add-auth-server`

这篇是你当前仓库的落地版本：从 Supabase 用户登录拿 token，到 LangGraph 自定义 auth 验证通过。

## 1. 前置条件

你需要在 `.env` 中准备：

```env
SUPABASE_URL=https://<your-project>.supabase.co
SUPABASE_ANON_KEY=<your-anon-public-key>
SUPABASE_SERVICE_KEY=<your-service-role-secret>
```

并确保：

- Supabase `Authentication -> Providers -> Email` 已开启
- 已创建测试用户（例如 2 个）
- 用户邮箱已确认（或后台创建时已设 confirmed）

## 2. 当前仓库相关文件

- `graph_src/auth_oauth.py`：Supabase 生产认证逻辑（Bearer token -> Supabase `/auth/v1/user`）
- `langgraph.json`：`auth.path` 指向 `graph_src/auth_oauth.py:oauth_auth`
- `graph_src/auth.py`：教学/demo 版本，保留用于对照学习

## 3. 快速启动

启动服务：

```bash
uv run langgraph dev --port 8123 --no-browser
```

## 4. 最小登录脚本（拿 access token）

```bash
uv run python - <<'PY'
import os
import httpx

SUPABASE_URL = os.environ["SUPABASE_URL"]
SUPABASE_ANON_KEY = os.environ["SUPABASE_ANON_KEY"]

email = "user1@example.com"
password = "123456"

resp = httpx.post(
    f"{SUPABASE_URL}/auth/v1/token?grant_type=password",
    json={"email": email, "password": password},
    headers={"apikey": SUPABASE_ANON_KEY, "Content-Type": "application/json"},
    timeout=20.0,
)
resp.raise_for_status()
print(resp.json()["access_token"])
PY
```

## 5. 用 token 调 LangGraph

把上一步 token 填进去：

```bash
uv run python sdk_src/examples/langgraph_sdk_learn.py thread-search \
  --url http://127.0.0.1:8123 \
  --bearer-token "<ACCESS_TOKEN>"
```

## 6. 角色设置脚本（app_metadata.role）

当前仓库按 `app_metadata.role` 走权限映射，常用值：

- `viewer`
- `user`
- `admin`

设置脚本：

```bash
uv run python - <<'PY'
import os
import asyncio
import httpx

SUPABASE_URL = os.environ["SUPABASE_URL"]
SUPABASE_SERVICE_KEY = os.environ["SUPABASE_SERVICE_KEY"]

TARGET_EMAIL = "user1@example.com"
TARGET_ROLE = "user"  # viewer/user/admin

HEADERS = {
    "apikey": SUPABASE_SERVICE_KEY,
    "Authorization": f"Bearer {SUPABASE_SERVICE_KEY}",
    "Content-Type": "application/json",
}

async def main():
    async with httpx.AsyncClient(timeout=20.0) as client:
        users = await client.get(f"{SUPABASE_URL}/auth/v1/admin/users", headers=HEADERS)
        users.raise_for_status()
        rows = users.json().get("users", [])
        user = next((u for u in rows if u.get("email") == TARGET_EMAIL), None)
        if not user:
            raise RuntimeError("target user not found")

        user_id = user["id"]
        app_metadata = dict(user.get("app_metadata") or {})
        app_metadata["role"] = TARGET_ROLE

        resp = await client.put(
            f"{SUPABASE_URL}/auth/v1/admin/users/{user_id}",
            headers=HEADERS,
            json={"app_metadata": app_metadata},
        )
        resp.raise_for_status()
        print("updated:", TARGET_EMAIL, "->", TARGET_ROLE)

asyncio.run(main())
PY
```

## 7. 我们实测通过的端到端验证点

- user 可创建 thread
- viewer 不可创建 thread（403）
- viewer 不可读取 user 的 thread（404）
- user 可搜索 assistants
- user 不可创建 assistants（403）
- admin 可创建/删除 assistants

## 7.1 一键验证脚本（推荐）

脚本位置：`sdk_src/examples/supabase_oauth_one_click_verify.py`

默认会验证：

- `user1@example.com` 作为 user
- `user2@example.com` 作为 viewer
- user 可创建 thread、不可创建 assistant
- viewer 不能创建 thread、不能读取 user thread

命令：

```bash
uv run python sdk_src/examples/supabase_oauth_one_click_verify.py \
  --api-url http://127.0.0.1:8123 \
  --graph-id agent
```

如果你想顺便验证 admin 能力（创建/删除 assistant）：

```bash
uv run python sdk_src/examples/supabase_oauth_one_click_verify.py \
  --api-url http://127.0.0.1:8123 \
  --graph-id agent \
  --promote-user-to-admin
```

## 8. 常见报错与处理

- 500 + `BlockingError`：说明 auth 里用了同步网络请求，需改为异步（当前已修复为 `httpx.AsyncClient`）
- 401：token 无效、过期、或 Supabase 配置错误
- 403：认证通过但权限不足
- 404（读 thread）：常是 owner 过滤生效后的“不可见”表现

## 9. 安全建议

- `SUPABASE_SERVICE_KEY` 只放服务端环境变量，不要泄露到前端
- `.env` 禁止提交到 git（本仓库已忽略）
- 若秘钥曾在聊天/日志暴露，建议立刻在 Supabase 控制台轮换
