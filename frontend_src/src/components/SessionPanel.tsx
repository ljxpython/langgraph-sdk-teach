type SessionItem = {
  id: string
  title: string
  assistant_id: string
  thread_id: string | null
  updatedAt: string
  preview: string
}

type SessionPanelProps = {
  sessions: SessionItem[]
  activeSessionId: string | null
  collapsed: boolean
  onToggleCollapsed: () => void
  onSelectSession: (sessionId: string) => void
  onCreateSession: () => void
  hasMore: boolean
  loadingMore: boolean
  onLoadMore: () => void
}

export function SessionPanel({
  sessions,
  activeSessionId,
  collapsed,
  onToggleCollapsed,
  onSelectSession,
  onCreateSession,
  hasMore,
  loadingMore,
  onLoadMore,
}: SessionPanelProps) {
  return (
    <aside style={{ background: '#fff', border: '1px solid #e5e7eb', borderRadius: 12, padding: 12, height: '100%' }}>
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 10 }}>
        <h2 style={{ margin: 0, fontSize: 16 }}>{collapsed ? 'Ses' : 'Sessions'}</h2>
        <div style={{ display: 'flex', gap: 8 }}>
          <button type="button" onClick={onToggleCollapsed} title={collapsed ? '展开会话列表' : '折叠会话列表'}>
            {collapsed ? '»' : '«'}
          </button>
          <button type="button" onClick={onCreateSession}>
            {collapsed ? '+' : '新建'}
          </button>
        </div>
      </div>
      {collapsed ? <p style={{ margin: 0, fontSize: 12, color: '#6b7280' }}>会话列表已折叠</p> : null}
      <div style={{ display: collapsed ? 'none' : 'grid', gap: 8 }}>
        {sessions.map((session) => {
          const active = session.id === activeSessionId
          return (
            <button
              key={session.id}
              type="button"
              onClick={() => onSelectSession(session.id)}
              style={{
                textAlign: 'left',
                background: active ? '#eef2ff' : '#f8fafc',
                border: active ? '1px solid #6366f1' : '1px solid #e5e7eb',
                borderRadius: 10,
                padding: 10,
              }}
            >
              <div style={{ fontWeight: 600 }}>{session.title}</div>
              <div style={{ fontSize: 12, color: '#6b7280' }}>{session.updatedAt}</div>
              <div style={{ fontSize: 12, color: '#374151', marginTop: 4 }}>
                {session.preview || '暂无会话内容'}
              </div>
              <div style={{ fontSize: 12, color: '#6b7280' }}>assistant_id: {session.assistant_id}</div>
              <div style={{ fontSize: 12, color: '#6b7280' }}>thread_id: {session.thread_id ?? 'N/A'}</div>
            </button>
          )
        })}
        <button type="button" onClick={onLoadMore} disabled={!hasMore || loadingMore}>
          {loadingMore ? '加载中...' : hasMore ? '加载更多会话' : '没有更多会话'}
        </button>
      </div>
    </aside>
  )
}
