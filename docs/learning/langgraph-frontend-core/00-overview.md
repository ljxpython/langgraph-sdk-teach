# 00. 前端主线总览

## 目标

构建一个最小前端观察面板，能看清 LangGraph 一次 run 从输入到完成的全过程。

## 核心能力（只做这 4 个）

1. 消费 SSE 并渲染 `messages*` 文本流
2. 渲染工具调用请求与结果
3. 渲染执行时间线（updates/tasks/checkpoints/debug）
4. 命中 `__interrupt__` 时进入人工审批并恢复

## 非目标

- 复杂设计系统与动画
- 多会话产品能力
- 自定义协议与事件二次封装

## 输入与依赖

- 后端接口：`/api/thread` `/api/chat/wait` `/api/chat/stream` `/api/state`
- 事件语义：`docs/learning/langgraph-sdk/17-streaming-frontend-backend-standard.md`
