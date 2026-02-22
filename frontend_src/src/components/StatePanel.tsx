type StatePanelProps = {
  threadId: string | null
  stateSnapshot: unknown
  interruptPayload: unknown
  onRefreshState: () => Promise<void>
  onApproveResume: () => Promise<void>
}

export function StatePanel({
  threadId,
  stateSnapshot,
  interruptPayload,
  onRefreshState,
  onApproveResume,
}: StatePanelProps) {
  return (
    <section style={{ background: '#fff', border: '1px solid #e5e7eb', borderRadius: 12, padding: 16 }}>
      <h2 style={{ marginTop: 0 }}>State Panel</h2>
      <p style={{ marginTop: 0 }}>thread_id: {threadId ?? 'N/A'}</p>
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
        <summary>State Snapshot</summary>
        <pre style={{ whiteSpace: 'pre-wrap' }}>{JSON.stringify(stateSnapshot, null, 2)}</pre>
      </details>
    </section>
  )
}
