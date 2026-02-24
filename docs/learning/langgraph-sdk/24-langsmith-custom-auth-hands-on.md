# LangSmith Custom Auth 教学实战（细粒度权限版）

> 对应官方文档：
> - `https://docs.langchain.com/langsmith/set-up-custom-auth`
> - `https://docs.langchain.com/langsmith/resource-auth`

这篇的目标不是“看懂概念”，而是让你在真实开发里知道：

1. 为什么要做细粒度权限。
2. 细粒度到底细到哪里。
3. 你当前仓库已经做到什么、还差什么。
4. 下一步该怎么练，才能真正掌握。

---

## 1. 先把核心认知定住

一句话：

- `set-up-custom-auth` 解决“谁能进系统”（认证）。
- `resource-auth` 解决“进来后能看/改什么”（授权）。

如果只有认证，没有资源授权，会发生：

- 用户 A 和用户 B 都能登录；
- 但 B 可能看到 A 的 thread；
- 这在生产里是严重越权。

所以真实项目必须是两层：

1. 认证层（AuthN）
2. 资源授权层（AuthZ）

---

## 2. 你当前仓库实现到了哪一步

关键文件：

- `langgraph.json`
- `graph_src/auth.py`
- `graph_src/auth_oauth.py`
- `sdk_src/examples/langgraph_sdk_learn.py`
- `sdk_src/examples/langgraph_sdk_learn_common.py`

你已经实现：

1. `@custom_auth.authenticate`：校验 token / api-key，返回用户身份。
2. `@custom_auth.on`：全局权限兜底。
3. `@custom_auth.on.threads.*`：线程资源的细粒度处理。
4. owner 注入 + owner 过滤：线程私有化。

你还没实现：

1. 真实认证源（JWT/OAuth2/外部鉴权服务）。

补充：本仓库已新增 `graph_src/auth_oauth.py`（Supabase 生产版认证），并在 `langgraph.json` 将 `auth.path` 指向该文件；当前保持 `disable_studio_auth=false` 以保留开发便捷路径。

---

## 3. 什么叫“细粒度权限”（通俗定义）

细粒度 = 从“登录了就全能”升级为“按资源、动作、归属、组织、角色分别判断”。

建议你记这 6 个维度：

1. 资源维度：`threads` / `runs` / `assistants` / `store`
2. 动作维度：`create/read/update/delete/search/create_run`
3. 归属维度：`owner`
4. 角色维度：`viewer/user/admin`
5. 租户维度：`org_id`
6. 字段维度：哪些字段可见、哪些字段可写

你现在主要覆盖了前 4 个里的 `threads` 部分。

---

## 4. 按请求走一遍代码流程（你最该吃透）

假设你执行：

```bash
uv run python sdk_src/examples/langgraph_sdk_learn.py create-thread --bearer-token owner-token
```

路径如下：

1. CLI 解析参数（`langgraph_sdk_learn.py`）
2. `build_client_headers(...)` 构造请求头（`Authorization: Bearer owner-token`）
3. `get_client(..., headers=...)` 发请求
4. 平台读取 `langgraph.json` 的 `auth.path`
5. 进入 `graph_src/auth.py:authenticate`
6. 认证通过后，进入授权 handler（`on_access` / `on.threads.create`）
7. `on.threads.create` 注入 `metadata.owner`
8. 请求放行并创建线程

这个流程就是官方两篇教程在你仓库里的落地版本。

---

## 5. 细粒度规则怎么设计（教学模板）

下面是一个可直接照抄到你脑子里的规则模板：

### 5.1 threads 规则（你已基本实现）

- `threads.create`：需要 `threads:create`，并写入 `metadata.owner = user.identity`
- `threads.read/search/update/delete`：需要对应权限，并返回过滤器 `{"owner": user.identity}`
- admin：可返回 `{}`，表示不过滤

### 5.2 assistants 规则（阶段 B 已落地）

- viewer：禁止 create/delete
- user：可 read/search，是否允许 create 由产品决定
- admin：全动作允许

当前仓库已落地策略：

- 普通用户仅允许 `assistants:read/search`
- 仅 admin 允许 `assistants.create/update/delete`

### 5.3 runs 规则（阶段 C 已落地）

- `threads.create_run`：需要 `threads:create_run` 权限
- `threads` 资源动作统一返回 owner 过滤器，跨 owner thread 的 run 请求会被拒绝

当前仓库已落地策略：

- owner 与 viewer 都可在自己 thread 上创建 run
- 跨 owner thread 发起 run 会因 owner 过滤被拒绝
- admin 不受 owner 过滤限制

关键点：

- 在 LangGraph 资源模型里，run 创建通常表现为 `threads` 资源上的 `create_run` 动作。

### 5.4 store 规则（阶段 D 已落地）

官方推荐思路：namespace 挂用户身份。

例如约定：

- `namespace = (user_id, resource_type, resource_id)`

当前仓库已落地策略：

- 新增 `@custom_auth.on.store` 处理器
- 先按 action 做权限校验：`store:put/get/list_namespaces`
- 再校验 namespace 首段

然后校验：

- `namespace[0] == ctx.user.identity`

这样天然防跨用户读写 store。

---

## 6. 为什么 owner 过滤比“只返回 403”更重要

很多人只做“越权时报错”，但漏了“列表接口过滤”。

如果你只做 403，不做过滤，会出现：

- 用户能在 search/list 看到别人的资源 ID；
- 虽然 get 可能被拒绝，但信息已经泄漏。

所以正确做法是两步都要：

1. create 时写 owner
2. read/search 时按 owner 过滤

这就是 `resource-auth` 的核心价值。

---

## 7. 你当前实现 vs 官方教程 对照

已对齐：

- 自定义 `Auth` 对象
- `@auth.authenticate`
- 在 `langgraph.json` 注册 `auth.path`
- `@auth.on` 资源授权
- threads 的 owner 元数据 + 过滤

部分对齐：

- 你有角色和 permissions，但还是 demo token（教学级）

未对齐（生产级差距）：

- OAuth2/JWT 验签
- 外部身份提供方接入
- 多资源全面策略（assistants/runs/store）
- 审计与密钥轮换策略

---

## 8. 学习实操：按 4 个阶段走

## 阶段 A（已完成）

- 目标：认证 + threads 私有化
- 验收：viewer 无法 create，owner 可 create，search 有 owner 隔离

## 阶段 B（已完成）

- 目标：assistants 细粒度授权
- 已实现：在 `graph_src/auth.py` 增加 `@custom_auth.on.assistants`，按 action 分支控制
- 验收：普通用户 assistants.create/update/delete 返回拒绝，admin 可通过

## 阶段 C（已完成）

- 目标：补 runs 与 thread 归属联动
- 已实现：在 `threads` 动作上支持 `create_run` 权限并沿用 owner 过滤
- 验收：仅允许在符合 owner 过滤的 thread 上发起 run

## 阶段 D（已完成）

- 目标：补 store namespace 授权
- 已实现：`@custom_auth.on.store` + namespace 首段校验
- 验收：跨用户 namespace 访问被拒绝，admin 可跨用户访问

---

## 9. 当前可直接复现实验命令

启动：

```bash
uv run langgraph dev --port 8123 --no-browser
```

无凭证：

```bash
uv run python sdk_src/examples/langgraph_sdk_learn.py thread-search --url http://127.0.0.1:8123
```

viewer 越权创建：

```bash
uv run python sdk_src/examples/langgraph_sdk_learn.py create-thread --url http://127.0.0.1:8123 --bearer-token viewer-token
```

owner 创建：

```bash
uv run python sdk_src/examples/langgraph_sdk_learn.py create-thread --url http://127.0.0.1:8123 --bearer-token owner-token
```

admin 搜索：

```bash
uv run python sdk_src/examples/langgraph_sdk_learn.py thread-search --url http://127.0.0.1:8123 --bearer-token admin-token
```

测试：

```bash
uv run --with pytest pytest tests/test_custom_auth_minimal.py tests/test_sdk_client_headers.py -vv
```

阶段 B 三身份真实联调脚本：

```bash
uv run python sdk_src/examples/stage_b_auth_live_demo.py --url http://127.0.0.1:8123 --graph-id agent
```

脚本会自动演示并打印：

- owner 可 `assistants.search`
- owner / viewer 被拒绝 `assistants.create`
- admin 可 `assistants.create` 并清理删除
- owner 可 `threads.create`，viewer 被拒绝创建
- viewer 无法读取 owner 的 thread（403/404 之一）

---

## 10. 你在真实项目里应该怎么用这套方法

不是一次做满，而是按风险递进：

1. 先做最小闭环（你已做到）
2. 再做资源细粒度（assistants/runs/store）
3. 最后接入真实身份系统（OAuth/JWT）

判断标准：

- 只要系统有“多用户 + 持久化资源”，就必须做 resource-level auth。

---

## 11. 一句话记忆

`set-up-custom-auth` 是“先拦门”，`resource-auth` 是“再分房间”，细粒度就是“每个房间的每个动作都要单独授权”。
