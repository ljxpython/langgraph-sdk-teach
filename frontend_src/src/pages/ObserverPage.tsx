import { useRef, useState, type FormEvent } from 'react'

import { ChatPanel } from '../components/ChatPanel'
import { DebugPanel } from '../components/DebugPanel'
import { StatePanel } from '../components/StatePanel'
import { TimelinePanel } from '../components/TimelinePanel'
import { createOrGetThread, getRunLogs, getState, type RunLogItem, resumeChat } from '../lib/api'
import { openStream } from '../lib/sseClient'
import type { UiStage } from '../types/events'

type ChatItem = {
  role: 'user' | 'ai'
  text: string
}

type TimelineItem = {
  ts: string
  category: string
  event: string
  summary: string
}

function nowLabel(): string {
  return new Date().toLocaleTimeString()
}

function parseJson(raw: string): unknown {
  try {
    return JSON.parse(raw)
  } catch {
    return raw
  }
}

function summarize(data: unknown): string {
  if (typeof data === 'string') {
    return data.slice(0, 180)
  }
  if (data && typeof data === 'object') {
    return JSON.stringify(data).slice(0, 180)
  }
  return String(data)
}

function categoryOf(eventName: string, data: unknown): { category: string; stage: UiStage } {
  const mapping = data && typeof data === 'object' ? (data as Record<string, unknown>) : {}
  if (eventName === 'error') return { category: 'run_terminal', stage: 'run_error' }
  if (eventName === 'done') return { category: 'run_terminal', stage: 'run_done' }
  if (eventName.startsWith('messages')) return { category: 'ai_stream', stage: 'model_streaming' }
  if (Array.isArray(mapping.tool_calls) && mapping.tool_calls.length > 0) return { category: 'tool_request', stage: 'tool_calling' }
  if (mapping.type === 'tool' || typeof mapping.tool_call_id === 'string') return { category: 'tool_result', stage: 'tool_completed' }
  if (['updates', 'tasks', 'checkpoints', 'debug', 'values', 'metadata'].includes(eventName)) {
    return { category: 'state_progress', stage: 'model_streaming' }
  }
  return { category: 'unknown', stage: 'model_streaming' }
}

export function ObserverPage() {
  const [userId, setUserId] = useState('u-demo')
  const [assistantId, setAssistantId] = useState('agent')
  const [message, setMessage] = useState('请给我三条学习建议')
  const [threadId, setThreadId] = useState<string | null>(null)
  const [stage, setStage] = useState<UiStage>('run_started')
  const [chatItems, setChatItems] = useState<ChatItem[]>([])
  const [streamDraft, setStreamDraft] = useState('')
  const [timeline, setTimeline] = useState<TimelineItem[]>([])
  const [stateSnapshot, setStateSnapshot] = useState<unknown>(null)
  const [interruptPayload, setInterruptPayload] = useState<unknown>(null)
  const [runLogs, setRunLogs] = useState<RunLogItem[]>([])
  const [errorText, setErrorText] = useState('')
  const sourceRef = useRef<EventSource | null>(null)

  const appendTimeline = (item: TimelineItem) => {
    setTimeline((prev) => [...prev, item])
  }

  const handleStreamEvent = (eventName: string, rawData: string) => {
    const data = parseJson(rawData)
    const cat = categoryOf(eventName, data)
    setStage(cat.stage)
    appendTimeline({
      ts: nowLabel(),
      category: cat.category,
      event: eventName,
      summary: summarize(data),
    })

    if (eventName.startsWith('messages')) {
      const mapping = data && typeof data === 'object' ? (data as Record<string, unknown>) : {}
      const content = mapping.content
      if (typeof content === 'string' && content.length > 0) {
        setStreamDraft((prev) => `${prev}${content}`)
      }
      const hasToolCalls = Array.isArray(mapping.tool_calls) && mapping.tool_calls.length > 0
      if (mapping.type === 'ai' && typeof content === 'string' && content.trim() && !hasToolCalls) {
        setChatItems((prev) => [...prev, { role: 'ai', text: content }])
      }
    }

    if (eventName === 'done') {
      setStage('run_done')
      if (streamDraft.trim()) {
        setChatItems((prev) => [...prev, { role: 'ai', text: streamDraft.trim() }])
        setStreamDraft('')
      }
      if (sourceRef.current) {
        sourceRef.current.close()
        sourceRef.current = null
      }
      void handleRefreshState()
      void handleRefreshLogs()
    }

    if (eventName === 'error') {
      setStage('run_error')
      setErrorText(summarize(data))
      if (sourceRef.current) {
        sourceRef.current.close()
        sourceRef.current = null
      }
    }
  }

  const handleStartStream = async (evt: FormEvent) => {
    evt.preventDefault()
    setErrorText('')
    setInterruptPayload(null)
    setStage('run_started')
    setStreamDraft('')

    const threadResp = await createOrGetThread(userId)
    setThreadId(threadResp.thread_id)
    setChatItems((prev) => [...prev, { role: 'user', text: message }])

    if (sourceRef.current) {
      sourceRef.current.close()
      sourceRef.current = null
    }

    const params = new URLSearchParams({
      user_id: userId,
      assistant_id: assistantId,
      message,
    })
    sourceRef.current = openStream(params, {
      onOpen: () => setStage('model_streaming'),
      onEvent: handleStreamEvent,
      onError: () => {
        setStage('run_error')
        setErrorText('SSE disconnected')
        void handleRefreshLogs()
      },
    })
  }

  const handleRefreshState = async () => {
    const state = await getState(userId)
    setThreadId(state.thread_id)
    setStateSnapshot(state.state)
  }

  const handleRefreshLogs = async () => {
    const logs = await getRunLogs(userId)
    setRunLogs(logs.items)
  }

  const handleApproveResume = async () => {
    const result = await resumeChat({
      userId,
      assistantId: 'deepagent_demo',
      command: { resume: { decisions: [{ type: 'approve' }] } },
    })
    setThreadId(result.thread_id)
    setInterruptPayload((result.result as { __interrupt__?: unknown }).__interrupt__ ?? null)
    appendTimeline({ ts: nowLabel(), category: 'run_terminal', event: 'resume', summary: 'resume called' })
    void handleRefreshState()
    void handleRefreshLogs()
  }

  return (
    <main style={{ padding: '24px', maxWidth: 1200, margin: '0 auto' }}>
      <h1 style={{ marginTop: 0 }}>LangGraph Frontend Observer</h1>
      <p>最小联调版本：thread/wait/stream/state + resume（官方 event/data 语义）。</p>
      <form onSubmit={handleStartStream} style={{ display: 'grid', gridTemplateColumns: '1fr 1fr 2fr auto', gap: 8, marginBottom: 16 }}>
        <input value={userId} onChange={(e) => setUserId(e.target.value)} placeholder="user_id" />
        <input value={assistantId} onChange={(e) => setAssistantId(e.target.value)} placeholder="assistant_id" />
        <input value={message} onChange={(e) => setMessage(e.target.value)} placeholder="message" />
        <button type="submit">Start Stream</button>
      </form>
      {errorText ? <p style={{ color: '#b91c1c' }}>Error: {errorText}</p> : null}
      <section style={{ display: 'grid', gridTemplateColumns: '1fr', gap: 16 }}>
        <ChatPanel messages={chatItems} streamDraft={streamDraft} stage={stage} />
        <TimelinePanel items={timeline} />
        <StatePanel
          threadId={threadId}
          stateSnapshot={stateSnapshot}
          interruptPayload={interruptPayload}
          onRefreshState={handleRefreshState}
          onApproveResume={handleApproveResume}
        />
        <DebugPanel items={runLogs} onRefreshLogs={handleRefreshLogs} />
      </section>
    </main>
  )
}
