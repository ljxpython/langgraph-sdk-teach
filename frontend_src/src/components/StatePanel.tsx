type StatePanelProps = {
  thread_id: string | null
  stateSnapshot: unknown
  stateSummary: string
  historyCheckpoints: Array<{ ts: string; checkpoint: string }>
  interruptPayload: unknown
  onRefreshState: () => Promise<void>
  onApproveResume: () => Promise<void>
}

export function StatePanel({
  thread_id,
  stateSnapshot,
  stateSummary,
  historyCheckpoints,
  interruptPayload,
  onRefreshState,
  onApproveResume,
}: StatePanelProps) {
  return (
    <section style={{ background: '#fff', border: '1px solid #e5e7eb', borderRadius: 12, padding: 16 }}>
      <h2 style={{ marginTop: 0 }}>State Panel</h2>
      <p style={{ marginTop: 0 }}>thread_id: {thread_id ?? 'N/A'}</p>
      <p style={{ marginTop: 0, fontSize: 12, color: '#6b7280' }}>state 摘要: {stateSummary || 'N/A'}</p>
      <div style={{ display: 'flex', gap: 8, marginBottom: 12 }}>
        <button type="button" onClick={() => void onRefreshState()}>
          刷新 State
        </button>
        <button type="button" onClick={() => void onApproveResume()}>
          Approve Resume
        </button>
      </div>
      <details open>
        <summary>Interrupt Payload</summary>
        <pre style={{ whiteSpace: 'pre-wrap' }}>{JSON.stringify(interruptPayload, null, 2)}</pre>
      </details>
      <details open>
        <summary>History Checkpoints</summary>
        <div style={{ display: 'grid', gap: 6 }}>
          {historyCheckpoints.length === 0 ? <p style={{ margin: 0 }}>暂无 checkpoint</p> : null}
          {historyCheckpoints.map((item, idx) => (
            <div key={`${item.ts}-${idx}`} style={{ border: '1px solid #e5e7eb', borderRadius: 8, padding: 8 }}>
              <div style={{ fontSize: 12, color: '#6b7280' }}>{item.ts}</div>
              <div style={{ fontSize: 12 }}>{item.checkpoint}</div>
            </div>
          ))}
        </div>
      </details>
      <details open>
        <summary>State Snapshot</summary>
        <pre style={{ whiteSpace: 'pre-wrap' }}>{JSON.stringify(stateSnapshot, null, 2)}</pre>
      </details>
    </section>
  )
}
