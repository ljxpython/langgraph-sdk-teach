type ChatItem = {
  role: 'user' | 'ai'
  text: string
}

type ChatPanelProps = {
  messages: ChatItem[]
  streamDraft: string
  stage: string
}

export function ChatPanel({ messages, streamDraft, stage }: ChatPanelProps) {
  return (
    <section style={{ background: '#fff', border: '1px solid #e5e7eb', borderRadius: 12, padding: 16 }}>
      <h2 style={{ marginTop: 0 }}>Chat Panel</h2>
      <p style={{ marginTop: 0 }}>当前阶段：{stage}</p>
      <div style={{ display: 'grid', gap: 8 }}>
        {messages.map((item, idx) => (
          <div
            key={`${item.role}-${idx}`}
            style={{
              padding: 10,
              borderRadius: 10,
              background: item.role === 'user' ? '#eef2ff' : '#f8fafc',
              border: '1px solid #e5e7eb',
            }}
          >
            <strong>{item.role === 'user' ? 'User' : 'AI'}:</strong> {item.text}
          </div>
        ))}
        {streamDraft ? (
          <div style={{ padding: 10, borderRadius: 10, background: '#fff7ed', border: '1px solid #fed7aa' }}>
            <strong>AI(stream):</strong> {streamDraft}
          </div>
        ) : null}
      </div>
    </section>
  )
}
