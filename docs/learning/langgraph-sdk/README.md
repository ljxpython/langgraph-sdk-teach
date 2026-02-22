# LangGraph SDK 学习导航

先看：`00-learning-path.md`（唯一主线）
再看：`14-verification-matrix.md`（每个知识点怎么验收）

## 为什么放在这里

- `docs/learning/`：专门放学习型文档，不和项目设计文档混在一起。
- `docs/learning/langgraph-sdk/`：聚焦 LangGraph API/SDK 主线。
- 服务集成主线已拆到：`docs/learning/langgraph-service-core/`。
- 前端实践主线已拆到：`docs/learning/langgraph-frontend-core/`。
- 代码练习建议放在 `sdk_src/examples/`，文档和代码分离，便于迭代。

## 统一阅读序号（主线）

> 你只按这份编号走；每完成一项再进入下一项。

00. `00-learning-path.md`（总主线与进度）
01. `01-step-01-api-map.md`（对象模型）
02. `02-step-02-sdk-minimal.md`（最小可运行调用）
03. `03-runs-api-playbook.md`（Run 官方四篇重学）
04. `04-threads-api-playbook.md`（Threads T1~T4）
05. `05-step-03-stream-events.md`（Streaming 事件基础）
06. `06-runtime-dynamic-config-playbook.md`（动态配置）
07. `07-local-mcp-playbook.md`（本地 MCP）
08. `08-langgraph-runtime-context-runnables-playbook.md`（Runtime Context / runnables）
09. `09-service-observer-playbook.md`（服务集成与可观测）
10. `10-step-04-fastapi-proxy.md`（服务代理补充）
11. `11-step-05-frontend-observer.md`（前端观察补充）
12. `12-step-06-review-checklist.md`（阶段复盘）
13. `13-assistants-api-playbook.md`（Assistants 详解）
14. `14-verification-matrix.md`（验收矩阵）
15. `15-study-plan.md`（学习计划）
16. `16-deepagent-todo-skills-files-playbook.md`（DeepAgent：ToDo/Skills/文件工具）
17. `17-streaming-frontend-backend-standard.md`（Streaming 前后端规范）
18. `18-streaming-stage-s2-subgraphs-join-custom.md`（Streaming S2 进阶语义）
19. `19-streaming-stage-s3-hitl-time-travel.md`（Streaming S3：HITL 与 Time Travel）
20. `20-deepagent-canonical-example.md`（DeepAgent 规范案例）
21. `21-execution-checklist-template.md`（执行清单模板）

## 当前进度

- 你已完成：`05-step-03-stream-events.md`（Streaming 基础）
- 你下一步：`21-execution-checklist-template.md`

## 参考资料（按需）

- `15-study-plan.md`
- `01-step-01-api-map.md`
- `02-step-02-sdk-minimal.md`
- `05-step-03-stream-events.md`
- `10-step-04-fastapi-proxy.md`
- `11-step-05-frontend-observer.md`
- `../langgraph-frontend-core/README.md`
- `12-step-06-review-checklist.md`
- `13-assistants-api-playbook.md`
- `14-verification-matrix.md`
- `16-deepagent-todo-skills-files-playbook.md`
- `17-streaming-frontend-backend-standard.md`
- `18-streaming-stage-s2-subgraphs-join-custom.md`
- `19-streaming-stage-s3-hitl-time-travel.md`
- `20-deepagent-canonical-example.md`
- `21-execution-checklist-template.md`
- `04-threads-api-playbook.md`
- `03-runs-api-playbook.md`
- `06-runtime-dynamic-config-playbook.md`
- `07-local-mcp-playbook.md`
- `08-langgraph-runtime-context-runnables-playbook.md`
- `09-service-observer-playbook.md`
- `../langgraph-service-core/README.md`

## 学习原则

- 主线只学 LangGraph API/SDK。
- FastAPI 和前端仅作为观察工具。
- 每步都要求「可运行证据」。

## 学习脚本结构（已拆分）

- 统一入口：`sdk_src/examples/langgraph_sdk_learn.py`
- 公共函数：`sdk_src/examples/langgraph_sdk_learn_common.py`
- Assistants：`sdk_src/examples/langgraph_sdk_learn_assistants.py`
- Threads：`sdk_src/examples/langgraph_sdk_learn_threads.py`
- Runs：`sdk_src/examples/langgraph_sdk_learn_runs.py`
