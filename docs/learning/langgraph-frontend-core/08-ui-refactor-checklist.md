# 08. 前端改造清单（逐文件）

## 实施顺序

1. 先改页面骨架与布局
2. 再改面板组件与参数交互
3. 最后补日志可观测与回归验证

## 文件改造清单

### 1) `frontend_src/src/pages/ObserverPage.tsx`

- [ ] 改为三栏布局
- [ ] 新增会话数据结构与选中态
- [ ] 统一接线：stream/state/resume/run-logs
- [ ] 顶栏增加环境与状态信息

### 2) `frontend_src/src/components/SessionPanel.tsx`（新增）

- [ ] 会话列表渲染
- [ ] 新建会话按钮
- [ ] 当前会话高亮

### 3) `frontend_src/src/components/ControlPanel.tsx`（新增）

- [ ] assistant 输入
- [ ] system prompt 输入
- [ ] temperature 输入

### 4) `frontend_src/src/components/ChatPanel.tsx`

- [ ] 区分 user/ai 卡片
- [ ] 流式草稿区域
- [ ] 终态阶段显示

### 5) `frontend_src/src/components/TimelinePanel.tsx`

- [ ] 事件分类徽章
- [ ] 事件摘要与时间戳
- [ ] 空态提示

### 6) `frontend_src/src/components/StatePanel.tsx`

- [ ] state 回读
- [ ] interrupt 展示
- [ ] approve resume 按钮

### 7) `frontend_src/src/components/DebugPanel.tsx`

- [ ] run_logs 列表
- [ ] 错误高亮
- [ ] 关键 id 展示

### 8) `frontend_src/src/lib/api.ts`

- [ ] 增加 `resume`、`state`、`run-logs` 调用类型

### 9) `frontend_src/src/lib/sseClient.ts`

- [ ] 监听官方事件名
- [ ] onOpen/onError 生命周期

## 完成后验证

- [ ] `npm run build` 成功
- [ ] 本地联调成功（LangGraph + FastAPI + Frontend）
- [ ] 关键流程可演示：stream -> interrupt -> resume -> done
