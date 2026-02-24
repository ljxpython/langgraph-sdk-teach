# FastAPI + Supabase Auth + Casbin 最小可运行骨架

## 目录

```text
example/fastapi_supabase_casbin_minimal/
├── app.py
├── auth.py
├── authz.py
├── config.py
├── model.conf
├── policy.csv
└── .env.example
```

## 安装

在项目根目录执行：

```bash
uv add pycasbin
```

## 配置

复制环境变量模板：

```bash
cp example/fastapi_supabase_casbin_minimal/.env.example .env
```

最少需要配置：

- `SUPABASE_URL`
- `SUPABASE_ANON_KEY`

## 启动

```bash
uv run uvicorn example.fastapi_supabase_casbin_minimal.app:app --reload --port 8020
```

## 认证与授权流程

1. 请求带 `Authorization: Bearer <supabase_access_token>`
2. `auth.py` 调用 Supabase `/auth/v1/user` 校验 token
3. `authz.py` 用 Casbin 策略判断资源访问权限
4. 通过后返回业务响应

## 验证

- `GET /health`：健康检查
- `GET /me`：读取当前用户（需要 Bearer token）
- `POST /api/threads`：受 Casbin 策略保护
- `GET /api/threads/{thread_id}`：受 Casbin 策略保护
