# langgraph_sdk_teach

## 项目定位

- `langgraph_sdk_teach/` 仍然定位为 LangGraph API / SDK 的学习实践仓库。
- 这里沉淀的学习文档、运行时样例、前后端观察层和平台雏形能力，已经陆续整合进 [ai-agent-test-platform](https://github.com/ljxpython/ai-agent-test-platform)。
- 当前目录下这个拆分项目不再作为主线仓库持续维护，更适合用于回看学习过程、教学资料和历史实验代码。

## 迁移说明

- 如果你的目标是企业级开发、平台化集成、权限治理或生产部署，请直接使用 `ai-agent-test-platform`。
- 如果你的目标是学习 LangGraph API、SDK、Streaming、Threads、Runs、Custom Auth 或前后端联调链路，这个仓库依然可以作为学习样例参考。

## 仓库里主要有什么

- `docs/learning/langgraph-sdk/`：LangGraph API / SDK 学习主线与阅读导航。
- `graph_src/`、`graph_src_v1/`、`graph_src_v2/`：不同阶段的图运行时实验与实现样例。
- `fastapi_src/`：FastAPI 服务层观察与透传实践。
- `platform-core/`：平台兼容接口原型。
- `platform-web/`、`frontend_src/`：前端原型与联调用界面。
- `tests/`：学习验证、接口行为验证与回归测试样例。

## 推荐阅读顺序

1. `docs/learning/langgraph-sdk/README.md`
2. `graph_src_v2/docs/README.md`
3. `fastapi_src/README.md`
4. `platform-core/README.md`

## 使用建议

- 把这个项目当学习实践仓库，不要再把它当生产主仓或长期维护的企业级方案仓库。
- 需要最新整合能力时，优先查看 `ai-agent-test-platform`。
