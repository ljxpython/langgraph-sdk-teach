# 05. 初始化与目录落地计划

## 目标

先完成前端工程初始化与目录骨架，不写业务逻辑。

## 技术选择

- 框架：React
- 语言：TypeScript
- 构建：Vite

## 执行步骤

1. 创建 `frontend_src/` 并初始化 Vite React TS 项目。
2. 保留最小依赖，不引入 UI 库与状态库。
3. 创建目录骨架与占位文件（无业务逻辑）。
4. 配置 `.env.example`，声明 `VITE_API_BASE_URL`。
5. 验证 `npm run dev` 可启动。

## 目录骨架（初始化后）

```text
frontend_src/
├── src/
│   ├── pages/ObserverPage.tsx
│   ├── components/
│   │   ├── ChatPanel.tsx
│   │   ├── TimelinePanel.tsx
│   │   └── StatePanel.tsx
│   ├── lib/
│   │   ├── api.ts
│   │   └── sseClient.ts
│   ├── store/session.ts
│   └── types/events.ts
└── .env.example
```

## 边界

- 只做目录与初始化，不接后端、不写交互逻辑。
- 下一步再接 `/api/thread` `/api/chat/stream` `/api/state`。
