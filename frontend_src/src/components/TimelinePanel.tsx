type TimelineItem = {
  ts: string
  category: string
  event: string
  summary: string
}

type TimelinePanelProps = {
  items: TimelineItem[]
}

export function TimelinePanel({ items }: TimelinePanelProps) {
  return (
    <section style={{ background: '#fff', border: '1px solid #e5e7eb', borderRadius: 12, padding: 16 }}>
      <h2 style={{ marginTop: 0 }}>Timeline Panel</h2>
      <div style={{ display: 'grid', gap: 8 }}>
        {items.length === 0 ? <p style={{ margin: 0 }}>暂无事件</p> : null}
        {items.map((item, idx) => (
          <div key={`${item.ts}-${idx}`} style={{ border: '1px solid #e5e7eb', borderRadius: 8, padding: 8 }}>
            <div style={{ fontSize: 12, color: '#6b7280' }}>
              {item.ts} · {item.category} · {item.event}
            </div>
            <div>{item.summary}</div>
          </div>
        ))}
      </div>
    </section>
  )
}
