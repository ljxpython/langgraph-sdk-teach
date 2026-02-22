import type { RunLogItem } from '../lib/api'

type DebugPanelProps = {
  items: RunLogItem[]
  onRefreshLogs: () => Promise<void>
}

export function DebugPanel({ items, onRefreshLogs }: DebugPanelProps) {
  return (
    <section style={{ background: '#fff', border: '1px solid #e5e7eb', borderRadius: 12, padding: 16 }}>
      <h2 style={{ marginTop: 0 }}>Debug Panel (run_logs)</h2>
      <button type="button" onClick={() => void onRefreshLogs()}>
        刷新 Logs
      </button>
      <div style={{ display: 'grid', gap: 8, marginTop: 12 }}>
        {items.length === 0 ? <p style={{ margin: 0 }}>暂无日志</p> : null}
        {items.map((item) => (
          <div key={item.id} style={{ border: '1px solid #e5e7eb', borderRadius: 8, padding: 8 }}>
            <div style={{ fontSize: 12, color: '#6b7280' }}>
              #{item.id} · {item.created_at} · {item.endpoint}
            </div>
            <div>
              {item.event} / {item.status} / thread={item.thread_id}
            </div>
            {item.error ? <div style={{ color: '#b91c1c' }}>{item.error}</div> : null}
          </div>
        ))}
      </div>
    </section>
  )
}
