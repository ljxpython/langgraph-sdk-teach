import ReactMarkdown from 'react-markdown'
import remarkGfm from 'remark-gfm'

import { MessageActions } from './MessageActions'

type HumanMessageProps = {
  text: string
  idx: number
}

export function HumanMessage({ text, idx }: HumanMessageProps) {
  return (
    <div
      style={{
        padding: 10,
        borderRadius: 10,
        background: '#eff6ff',
        border: '1px solid #bfdbfe',
      }}
    >
      <div style={{ marginBottom: 6 }}>
        <strong>User</strong>
      </div>
      <div style={{ lineHeight: 1.6 }}>
        <ReactMarkdown remarkPlugins={[remarkGfm]}>{text}</ReactMarkdown>
      </div>
      <MessageActions content={text} copyKey={`human-${idx}`} />
    </div>
  )
}
