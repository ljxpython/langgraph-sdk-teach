export type ToolTraceItem = {
  id: string
  ts: string
  kind: 'tool_request' | 'tool_result' | 'state_progress' | 'run_terminal' | 'user_input' | 'ai_stream'
  title: string
  summary: string
  data?: unknown
}

type ToolTracePanelProps = {
  items: ToolTraceItem[]
}

export function ToolTracePanel({ items }: ToolTracePanelProps) {
  const asMapping = (value: unknown): Record<string, unknown> | null => {
    if (!value || typeof value !== 'object' || Array.isArray(value)) {
      return null
    }
    return value as Record<string, unknown>
  }

  const extractMessagePayload = (value: unknown): Record<string, unknown> | null => {
    const direct = asMapping(value)
    if (direct) {
      return direct
    }
    if (Array.isArray(value)) {
      for (const item of value) {
        const mapping = asMapping(item)
        if (!mapping) {
          continue
        }
        if (Array.isArray(mapping.tool_calls) || typeof mapping.content === 'string' || typeof mapping.type === 'string') {
          return mapping
        }
      }
    }
    return null
  }

  const renderData = (item: ToolTraceItem) => {
    const payload = extractMessagePayload(item.data) ?? asMapping(item.data)
    if (!payload) {
      return null
    }

    if (item.kind === 'tool_request' && Array.isArray(payload.tool_calls)) {
      return (
        <div style={{ display: 'grid', gap: 6, marginTop: 6 }}>
          {payload.tool_calls.map((call, idx) => {
            const c = call && typeof call === 'object' ? (call as Record<string, unknown>) : {}
            const name = String(c.name ?? `tool-${idx + 1}`)
            const args = c.args ?? {}
            const isSubAgent = name === 'task'
            return (
              <div key={`${item.id}-call-${idx}`} style={{ border: '1px solid #e5e7eb', borderRadius: 6, padding: 6, background: '#f8fafc' }}>
                <div style={{ fontSize: 12, fontWeight: 600 }}>
                  tool: {name}
                  {isSubAgent ? <span style={{ marginLeft: 8, color: '#7c3aed' }}>子智能体委托</span> : null}
                </div>
                <pre style={{ margin: 0, whiteSpace: 'pre-wrap', fontSize: 12 }}>{JSON.stringify(args, null, 2)}</pre>
              </div>
            )
          })}
        </div>
      )
    }

    if (item.kind === 'state_progress' && item.title === 'tasks') {
      const taskName = String(payload.name ?? payload.node ?? payload.id ?? 'task')
      const status = String(payload.status ?? payload.state ?? 'running')
      const path = String(payload.path ?? payload.ns ?? '')
      return (
        <div style={{ marginTop: 6, border: '1px solid #e5e7eb', borderRadius: 6, padding: 6, background: '#f8fafc' }}>
          <div style={{ fontSize: 12, fontWeight: 600 }}>task: {taskName}</div>
          <div style={{ fontSize: 12, color: '#6b7280' }}>status: {status}</div>
          {path ? <div style={{ fontSize: 12, color: '#6b7280' }}>path: {path}</div> : null}
          <pre style={{ margin: '6px 0 0 0', whiteSpace: 'pre-wrap', fontSize: 12 }}>{JSON.stringify(payload, null, 2)}</pre>
        </div>
      )
    }

    if (item.kind === 'tool_result') {
      const content = payload.content
      return <pre style={{ marginTop: 6, whiteSpace: 'pre-wrap', fontSize: 12 }}>{typeof content === 'string' ? content : JSON.stringify(content, null, 2)}</pre>
    }

    return null
  }

  return (
    <details open>
      <summary style={{ cursor: 'pointer' }}>调用链路（Chat 内）</summary>
      <div style={{ display: 'grid', gap: 8, marginTop: 8 }}>
        {items.length === 0 ? <p style={{ margin: 0 }}>暂无链路事件</p> : null}
        {items.map((item) => (
          <div key={item.id} style={{ border: '1px solid #e5e7eb', borderRadius: 8, padding: 8, background: '#fff' }}>
            <div style={{ fontSize: 12, color: '#6b7280' }}>
              {item.ts} · {item.kind} · {item.title}
            </div>
            <div style={{ fontSize: 13 }}>{item.summary}</div>
            {renderData(item)}
          </div>
        ))}
      </div>
    </details>
  )
}
