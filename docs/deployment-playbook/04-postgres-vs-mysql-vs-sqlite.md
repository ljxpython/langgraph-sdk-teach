# 04. PostgreSQL vs MySQL vs SQLite（平台与 LangGraph 场景）

## 结论先行

- 生产优先：`PostgreSQL`
- 开发环境：建议也用 PostgreSQL（Docker 一键起）
- SQLite：仅用于单测或超轻量本地 Demo

## 当前定稿方案（你现在这条路线）

1. **数据库统一 PostgreSQL**（开发/测试/生产全部一致）
2. **全环境通过 Docker 运行 PostgreSQL**（版本固定，避免环境漂移）
3. **ORM 使用 SQLAlchemy 2.0**（可选 SQLModel 做模型层封装）
4. **迁移使用 Alembic**（所有表结构变更必须走 migration）
5. **驱动使用 psycopg**（与 SQLAlchemy 2.0 配套）

一句话：用“`PostgreSQL + Docker + SQLAlchemy 2.0 + Alembic + psycopg`”作为统一底座。

## 使用差异（面向你当前场景）

| 维度 | PostgreSQL | MySQL | SQLite |
|---|---|---|---|
| 并发与事务 | 强一致能力完整，复杂事务表现稳定 | 并发不错，但细节与 PG 不同 | 文件锁模型，写并发弱 |
| JSON 能力 | `JSONB` 与索引生态成熟 | JSON 可用，生态可行 | JSON 支持有限，查询与索引弱 |
| 复杂查询 | CTE、窗口函数、表达式索引体验好 | 可做但语义/细节与 PG 有差异 | 能力有限 |
| 运维复杂度 | 中等，生态成熟 | 中等，生态成熟 | 低（单文件） |
| 本地一致性 | 与生产保持一致最容易 | 若生产 MySQL 则一致 | 与生产差异最大 |
| LangGraph 适配心智 | 官方文档与示例普遍以 PG 为中心 | 可做但更多自定义/第三方路径 | 多用于开发示例，不建议生产 |

## 和 LangGraph 的关系（关键）

1. LangSmith Deployment 文档里，内建 store/checkpointer 是 Postgres-backed。
2. 支持自定义 `store` 与 `checkpointer`，你可以替换为自定义实现。
3. 这意味着：
   - 你想省心：走 PostgreSQL
   - 你坚持 MySQL：可行，但要承担更多适配与验证成本

参考：

- `https://docs.langchain.com/langsmith/custom-store`
- `https://docs.langchain.com/langsmith/custom-checkpointer`

## 实操建议（个人开发者）

1. 平台数据库统一 PostgreSQL（开发/测试/生产）。
2. 每次 schema 变更只通过 Alembic migration，不直接手改线上库。
3. Repository 层以 SQLAlchemy 2.0 为主，复杂热点 SQL 再按需手写。
4. 所有环境使用同一主版本 PostgreSQL 镜像，降低“本地和线上不一致”风险。

## 最小决策模板

- 若你追求“最少坑 + 最快上线”：`PostgreSQL 全环境统一`
- 若你已有成熟 MySQL 运维：`平台可 MySQL + LangGraph 侧保持官方推荐路径`
- 若你只是本地原型：`SQLite 可用，但尽快迁移 PG`
