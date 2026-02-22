# 00. 服务主线总览

## 目标

把 LangGraph 调用稳定落地到服务形态，且保持学习项目最小复杂度。

## 核心能力（只做这 5 个）

1. `thread` 创建/复用
2. `wait` 同步结果
3. `stream` SSE 透传
4. `state` 状态回读
5. `done/error` 终态信号

## 非目标（本阶段不做）

- 鉴权与权限系统
- 限流、配额、多租户
- 自定义事件协议
- 重前端产品化工程

## 设计原则

- 只使用官方输出：`chunk.event`、`chunk.data`、`__interrupt__`
- 只在传输层补 `done/error`
- 每项能力必须可用 curl/pytest 留证据
