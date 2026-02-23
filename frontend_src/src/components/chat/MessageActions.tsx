import { useState } from 'react'

type MessageActionsProps = {
  content: string
  copyKey: string
}

export function MessageActions({ content, copyKey }: MessageActionsProps) {
  const [copiedKey, setCopiedKey] = useState('')

  const handleCopy = async () => {
    if (!content.trim()) {
      return
    }
    try {
      await navigator.clipboard.writeText(content)
      setCopiedKey(copyKey)
      window.setTimeout(() => {
        setCopiedKey((prev) => (prev === copyKey ? '' : prev))
      }, 1200)
    } catch {
      setCopiedKey('')
    }
  }

  const copied = copiedKey === copyKey

  return (
    <div style={{ display: 'flex', justifyContent: 'flex-end', marginTop: 8 }}>
      <button
        type="button"
        onClick={() => void handleCopy()}
        title={copied ? 'Copied' : 'Copy'}
        aria-label={copied ? 'Copied' : 'Copy message'}
        style={{
          width: 24,
          height: 24,
          borderRadius: 6,
          border: copied ? '1px solid #16a34a' : '1px solid #cbd5e1',
          background: copied ? '#ecfdf3' : '#ffffff',
          display: 'inline-flex',
          alignItems: 'center',
          justifyContent: 'center',
          cursor: 'pointer',
        }}
      >
        <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
          <title>copy</title>
          <rect x="9" y="9" width="13" height="13" rx="2" ry="2" />
          <path d="M5 15H4a2 2 0 0 1-2-2V4a2 2 0 0 1 2-2h9a2 2 0 0 1 2 2v1" />
        </svg>
      </button>
    </div>
  )
}
