# Agent 部署接入调研方案

## 背景与目标

- 当前技术栈：LangGraph Agent 已开发完成，并采用容器化部署。
- 目标：在保证可控性与可迭代性的前提下，确定前后端接入方案。
- 范围：仅关注“功能接入路径”，不展开运维与安全细节。

## 方案清单（调研结论）

### 1) 自研 BFF + LangGraph SDK/API（最主流、最可控）

- 前端调用自研后端（BFF）。
- 后端调用 LangGraph API/SDK，并统一处理业务协议。
- 优势：控制力强、长期扩展能力好、与现有业务耦合最自然。
- 适用：个人开发到中长期产品化都适用。

### 2) AG-UI / 类似协议层（适合流式事件、多 Agent 可视化）

- 前端按协议消费事件流，后端做适配层对接 LangGraph。
- 优势：复杂交互（流式、可视化状态）起步更快。
- 代价：需要遵循协议范式，后期可能增加适配维护成本。
- 适用：交互复杂度高、需要标准化事件流的场景。

### 3) Vercel AI SDK + 自家后端（前端体验成熟，流式友好）

- 典型模式：Next.js 前端 + 自研 API 层 + Agent Runtime。
- 优势：前端开发体验好，流式能力成熟。
- 代价：需要接受其生态风格与框架约束。
- 适用：Web 产品化速度优先、前端体验优先的场景。

### 4) CopilotKit / Assistant UI（快速搭建聊天+工具调用 UI）

- 优势：上手快，可快速验证交互与功能路径。
- 代价：框架约束明显，深度定制时可能受限。
- 适用：MVP 验证、快速试错。

### 5) Dify / Flowise / FastGPT / OpenWebUI（低代码或平台化）

- 优势：搭建快、演示与验证效率高。
- 代价：深度定制和复杂业务治理能力有限。
- 适用：需求不复杂、以验证为主的阶段。

## 架构实现差异（核心对比）

### 自研 BFF 路线

```text
Frontend -> BFF(API) -> LangGraph SDK/API -> Agent Runtime
```

- 特点：边界清晰，业务逻辑集中在 BFF，最适合长期演进。

### AG-UI 路线

```text
Frontend(AG-UI Client) <-> AG-UI Event Layer <-> Adapter/BFF <-> LangGraph
```

- 特点：前端事件模型更强，但需投入协议适配成本。

## 工作复杂度对比（面向个人开发）

- 自研 BFF：前期编码量略高，但可控性最高，长期维护更稳定。
- AG-UI：前期交互快，但需要理解并适配协议模型。
- 低代码平台：前期最快，后期深度定制成本可能上升。

## 推荐结论

- 首选：`自研 BFF + LangGraph SDK/API`。
- 原因：最符合“个人开发 + 成本可控 + 长期可维护”的目标。
- 策略：先用自研 BFF 完成主流程，再按需引入 AG-UI 能力（如复杂流式事件与可视化）。

## AG-UI 口径澄清（基于官方定义）

- AG-UI（https://docs.ag-ui.com/introduction）是 Agent 与用户应用之间的事件协议层，不是完整后端替代品。
- 实际对比应为：
  - `自研 BFF + 自定义事件协议`
  - `自研 BFF + AG-UI 协议`
- 因此，AG-UI 与自研 BFF 并非完全互斥关系，通常是“协议层是否标准化”的选择。

## DIY vs AG-UI（针对当前阶段）

### 当前推荐

- 当前阶段（个人开发、成本可控、LangGraph 已跑通）建议：**先 DIY**。
- 原因：先优先收敛业务能力与工作流，不提前投入协议适配复杂度。
- 要求：DIY 接口按事件化设计（消息增量、步骤状态、工具事件），为后续 AG-UI 迁移预留适配层。

### 何时切到 AG-UI

- 出现以下信号再切换：
  - 多端（Web/App/小程序）需要统一事件协议；
  - 复杂流式事件显著增多（工具执行、中断恢复、子代理协作、状态同步）；
  - 团队协作扩大，需要跨团队统一前后端契约。

## 五类 AI 能力落地顺序（功能优先）

目标能力：

- AI 分析文档
- AI RAG 分析
- AI 生成测试脚本
- AI 生成研究报告
- AI 分析问题缺陷

建议路线：

1. 先做“一个平台 + 五个工作流”，不要一开始拆 5 个微服务。
2. 第一批优先上线：
   - AI 分析文档
   - AI 生成研究报告
   说明：两者可复用“检索-归纳-引用输出”主链路。
3. 第二批上线：
   - AI 分析问题缺陷
   - AI 生成测试脚本
   说明：缺陷分析结果可直接喂给测试脚本生成，形成闭环。
4. 第三批升级：
   - AI RAG 分析扩展为独立能力域（多数据源、多索引策略）
5. 当单体工作流平台出现瓶颈（团队、吞吐、发布节奏）时，再按能力域拆服务。

## 官方资料与备用链接

### LangGraph / LangSmith 官方

- LangChain Docs（总入口）：https://docs.langchain.com/
- LangGraph 本地与部署相关（Docs 体系内）：https://docs.langchain.com/langsmith/deployments
- Standalone Server 部署指南：https://docs.langchain.com/langsmith/deploy-standalone-server
- Control Plane 部署指南：https://docs.langchain.com/langsmith/deploy-with-control-plane
- Data Plane 架构说明：https://docs.langchain.com/langsmith/data-plane
- 平台模式对比（Cloud/Hybrid/Self-hosted）：https://docs.langchain.com/langsmith/platform-setup

### 相关生态官网

- AG-UI 官方文档：https://docs.ag-ui.com/introduction
- Vercel AI SDK：https://sdk.vercel.ai/
- CopilotKit：https://www.copilotkit.ai/
- Assistant UI：https://www.assistant-ui.com/
- Dify：https://dify.ai/
- Flowise：https://flowiseai.com/
- FastGPT：https://fastgpt.io/
- OpenWebUI：https://openwebui.com/

## 备注

- 本文为“接入路径调研稿”，用于技术路线决策与后续实施拆解。
- 若进入实施阶段，可进一步补充：接口边界定义、事件协议样例、前后端调用时序图。
