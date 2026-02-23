import ReactMarkdown from 'react-markdown'
import remarkGfm from 'remark-gfm'

import { MessageActions } from './MessageActions'

type AssistantMessageProps = {
  text: string
  idx: number
  stream?: boolean
}

export function AssistantMessage({ text, idx, stream = false }: AssistantMessageProps) {
  return (
    <div
      style={{
        padding: 10,
        borderRadius: 10,
        background: stream ? '#fff7ed' : '#f8fafc',
        border: stream ? '1px solid #fed7aa' : '1px solid #e5e7eb',
      }}
    >
      <div style={{ marginBottom: 6 }}>
        <strong>{stream ? 'AI(stream)' : 'AI'}</strong>
      </div>
      <div style={{ lineHeight: 1.6 }}>
        <ReactMarkdown remarkPlugins={[remarkGfm]}>{text}</ReactMarkdown>
      </div>
      <MessageActions content={text} copyKey={`${stream ? 'stream' : 'ai'}-${idx}`} />
    </div>
  )
}
