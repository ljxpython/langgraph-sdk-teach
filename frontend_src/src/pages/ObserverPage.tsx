import { type FormEvent, useCallback, useEffect, useMemo, useRef, useState } from 'react'

import { ChatPanel, type ChatItem, type InterruptActionRequest, type InterruptDecisionType } from '../components/ChatPanel'
import { ControlPanel } from '../components/ControlPanel'
import { DebugPanel } from '../components/DebugPanel'
import { SessionPanel } from '../components/SessionPanel'
import { StatePanel } from '../components/StatePanel'
import { TimelinePanel } from '../components/TimelinePanel'
import { createThread, getAssistants, getHistory, getMessages, getRunLogs, getState, getThreads, resumeChat } from '../lib/api'
import type { AssistantItem, MessageItem, RunLogItem, ThreadItem } from '../lib/api'
import { openStream } from '../lib/sseClient'
import type { StreamConnection } from '../lib/sseClient'
import type { UiStage } from '../types/events'

type TimelineItem = {
  ts: string
  category: string
  event: string
  summary: string
}

type SessionItem = {
  id: string
  title: string
  user_id: string | null
  thread_id: string | null
  assistant_id: string
  graph_id: string
  system_prompt: string
  use_langgraph_sampling_defaults: boolean
  model_provider: string
  temperature: number
  top_p: number
  max_tokens: number
  enable_local_tools: boolean
  enable_local_mcp: boolean
  mcp_servers: string
  custom_tools: string
  updatedAt: string
  preview: string
}

function nowLabel(): string {
  return new Date().toLocaleTimeString()
}

const MODEL_PROVIDER_OPTIONS = ['openai', 'anthropic', 'google', 'glm4', 'deepseek']
const MCP_SERVER_OPTIONS = ['filesystem', 'github', 'browser', 'slack']
const MESSAGE_PAGE_SIZE = 30
const HISTORY_LIMIT = 20
const THREAD_PAGE_SIZE = 20

const DEFAULT_SESSION_RUNTIME = {
  assistant_id: 'agent',
  graph_id: '',
  system_prompt: '',
  use_langgraph_sampling_defaults: true,
  model_provider: 'openai',
  temperature: 0.7,
  top_p: 1,
  max_tokens: 512,
  enable_local_tools: true,
  enable_local_mcp: false,
  mcp_servers: '',
  custom_tools: '',
} as const

function parseJson(raw: string): unknown {
  try {
    return JSON.parse(raw)
  } catch {
    return raw
  }
}

function summarize(data: unknown): string {
  if (typeof data === 'string') return data.slice(0, 180)
  if (data && typeof data === 'object') return JSON.stringify(data).slice(0, 180)
  return String(data)
}

function summarizeEvent(eventName: string, data: unknown): string {
  if (!data || typeof data !== 'object') {
    return summarize(data)
  }
  const mapping = data as Record<string, unknown>

  if (eventName === 'metadata') {
    const runId = mapping.run_id
    const attempt = mapping.attempt
    return `run_id=${String(runId ?? 'N/A')} attempt=${String(attempt ?? 'N/A')}`
  }

  if (eventName === 'checkpoints') {
    const config = mapping.config && typeof mapping.config === 'object' ? (mapping.config as Record<string, unknown>) : null
    const configurable = config?.configurable && typeof config.configurable === 'object' ? (config.configurable as Record<string, unknown>) : null
    const ns = configurable?.checkpoint_ns
    const provider = configurable?.model_provider
    return `checkpoint_ns=${String(ns ?? 'N/A')} model_provider=${String(provider ?? 'N/A')}`
  }

  if (eventName === 'debug') {
    const step = mapping.step
    const debugType = mapping.type
    const ts = mapping.timestamp
    return `type=${String(debugType ?? 'N/A')} step=${String(step ?? 'N/A')} ts=${String(ts ?? 'N/A')}`
  }

  if (eventName === 'tasks') {
    const id = mapping.id ?? mapping.task_id
    const name = mapping.name ?? mapping.node
    const status = mapping.status ?? mapping.state
    return `task=${String(name ?? id ?? 'N/A')} status=${String(status ?? 'N/A')}`
  }

  if (eventName === '__interrupt__') {
    return '__interrupt__ received, human review required'
  }

  if (eventName.startsWith('messages')) {
    const payload = extractMessagePayload(data)
    if (payload) {
      if (Array.isArray(payload.tool_calls) && payload.tool_calls.length > 0) {
        const names = payload.tool_calls
          .map((item) => {
            if (item && typeof item === 'object') {
              return String((item as Record<string, unknown>).name ?? 'tool')
            }
            return 'tool'
          })
          .join(', ')
        return `tool_calls: ${names}`
      }
      const text = extractTextContent(payload).trim()
      if (text) {
        return text.slice(0, 180)
      }
    }
  }

  return summarize(data)
}

function asMapping(value: unknown): Record<string, unknown> | null {
  return value && typeof value === 'object' && !Array.isArray(value) ? (value as Record<string, unknown>) : null
}

function extractMessagePayload(data: unknown): Record<string, unknown> | null {
  const direct = asMapping(data)
  if (direct) {
    return direct
  }

  if (Array.isArray(data)) {
    for (const item of data) {
      const mapping = asMapping(item)
      if (!mapping) {
        continue
      }
      if (typeof mapping.content === 'string' || Array.isArray(mapping.tool_calls) || typeof mapping.type === 'string') {
        return mapping
      }
    }
  }

  return null
}

function extractTextContent(mapping: Record<string, unknown> | null): string {
  if (!mapping) {
    return ''
  }
  const raw = mapping.content
  if (typeof raw === 'string') {
    return raw
  }
  if (Array.isArray(raw)) {
    const texts: string[] = []
    for (const item of raw) {
      if (typeof item === 'string') {
        texts.push(item)
      } else if (item && typeof item === 'object') {
        const text = (item as Record<string, unknown>).text
        if (typeof text === 'string' && text) {
          texts.push(text)
        }
      }
    }
    return texts.join('\n')
  }
  return ''
}

function messageId(prefix: string): string {
  return `${prefix}-${Date.now()}-${Math.random().toString(36).slice(2, 8)}`
}

function summarizeStateSnapshot(state: unknown): string {
  if (!state || typeof state !== 'object') {
    return 'empty state'
  }
  const mapping = state as Record<string, unknown>
  const values = mapping.values
  if (!values || typeof values !== 'object') {
    return 'state has no values'
  }
  const messages = (values as Record<string, unknown>).messages
  if (!Array.isArray(messages)) {
    return 'values.messages is empty'
  }
  const last = messages[messages.length - 1]
  if (last && typeof last === 'object') {
    const content = (last as Record<string, unknown>).content
    const text = typeof content === 'string' ? content : JSON.stringify(content)
    return `messages=${messages.length}, last=${text?.slice(0, 80) ?? ''}`
  }
  return `messages=${messages.length}`
}

function extractFirstDialogPreviewFromState(state: unknown): string {
  if (!state || typeof state !== 'object') {
    return ''
  }
  const values = asMapping((state as Record<string, unknown>).values)
  const messages = values?.messages
  if (!Array.isArray(messages)) {
    return ''
  }
  for (const raw of messages) {
    const mapping = asMapping(raw)
    if (!mapping) {
      continue
    }
    const role = String(mapping.role ?? mapping.type ?? '')
    if (role !== 'user' && role !== 'human') {
      continue
    }
    const text = extractTextContent(mapping).trim()
    if (text) {
      return text.slice(0, 80)
    }
  }
  for (const raw of messages) {
    const mapping = asMapping(raw)
    if (!mapping) {
      continue
    }
    const text = extractTextContent(mapping).trim()
    if (text) {
      return text.slice(0, 80)
    }
  }
  return ''
}

function normalizeHistoryCheckpoints(items: unknown[]): Array<{ ts: string; checkpoint: string }> {
  return items.map((item, idx) => {
    const mapping = item && typeof item === 'object' ? (item as Record<string, unknown>) : {}
    const checkpoint = String(mapping.checkpoint_id ?? mapping.checkpoint ?? mapping.id ?? `checkpoint-${idx + 1}`)
    const ts = String(mapping.created_at ?? mapping.ts ?? mapping.timestamp ?? `#${idx + 1}`)
    return { ts, checkpoint }
  })
}

function mapMessageToChatItems(items: MessageItem[]): ChatItem[] {
  const mapped: ChatItem[] = []
  for (const item of items) {
    if (Array.isArray(item.tool_calls) && item.tool_calls.length > 0) {
      const names = item.tool_calls.map((call) => String(call.name ?? 'tool')).join(', ')
      mapped.push({ id: messageId('history-tool-request'), role: 'tool', name: 'request', text: `调用工具: ${names}` })
      continue
    }

    if (item.type === 'tool' || item.tool_call_id) {
      const fallback = typeof item.content === 'string' ? item.content : JSON.stringify(item.content)
      mapped.push({
        id: messageId('history-tool-result'),
        role: 'tool',
        name: item.name ?? 'tool',
        text: item.text.trim() || fallback,
      })
      continue
    }

    if (item.role === 'user' && item.text.trim()) {
      mapped.push({ id: messageId('history-user'), role: 'user', text: item.text })
      continue
    }

    if (item.role === 'ai' && item.text.trim()) {
      mapped.push({ id: messageId('history-ai'), role: 'ai', text: item.text })
    }
  }
  return mapped
}

function categoryOf(eventName: string, data: unknown): { category: string; stage: UiStage } {
  const mapping = extractMessagePayload(data) ?? (data && typeof data === 'object' ? (data as Record<string, unknown>) : {})
  const interrupt = extractInterruptPayload(data)
  if (eventName === 'error') return { category: 'run_terminal', stage: 'run_error' }
  if (eventName === 'done') return { category: 'run_terminal', stage: 'run_done' }
  if (eventName === '__interrupt__' || interrupt != null) return { category: 'run_terminal', stage: 'human_review_required' }
  if (Array.isArray(mapping.tool_calls) && mapping.tool_calls.length > 0) return { category: 'tool_request', stage: 'tool_calling' }
  if (mapping.type === 'tool' || typeof mapping.tool_call_id === 'string') return { category: 'tool_result', stage: 'tool_completed' }
  if (eventName.startsWith('messages')) return { category: 'ai_stream', stage: 'model_streaming' }
  if (['updates', 'tasks', 'checkpoints', 'debug', 'values', 'metadata'].includes(eventName)) {
    return { category: 'state_progress', stage: 'model_streaming' }
  }
  return { category: 'unknown', stage: 'model_streaming' }
}

function extractInterruptPayload(data: unknown): unknown {
  const findInterrupt = (value: unknown, depth: number): unknown => {
    if (depth > 5 || value == null) {
      return null
    }
    if (Array.isArray(value)) {
      for (const item of value) {
        const nested = findInterrupt(item, depth + 1)
        if (nested != null) {
          return nested
        }
      }
      return null
    }
    if (typeof value !== 'object') {
      return null
    }

    const mapping = value as Record<string, unknown>
    const directInterrupt = mapping.__interrupt__
    if (directInterrupt != null) {
      return directInterrupt
    }

    const singleInterrupt = mapping.interrupt
    if (singleInterrupt != null && singleInterrupt !== false) {
      return singleInterrupt
    }

    const interruptList = mapping.interrupts
    if (Array.isArray(interruptList) && interruptList.length > 0) {
      return interruptList
    }

    for (const child of Object.values(mapping)) {
      const nested = findInterrupt(child, depth + 1)
      if (nested != null) {
        return nested
      }
    }
    return null
  }

  return findInterrupt(data, 0)
}

function parseInterruptActionRequests(interruptPayload: unknown): InterruptActionRequest[] {
  const entries = Array.isArray(interruptPayload) ? interruptPayload : [interruptPayload]
  const normalized: InterruptActionRequest[] = []

  for (const entry of entries) {
    const container = asMapping(entry)
    const rawValue = container?.value ?? entry
    const value = asMapping(rawValue)
    if (!value) {
      continue
    }
    const rawRequests = Array.isArray(value.action_requests) ? value.action_requests : []
    const rawConfigs = Array.isArray(value.review_configs) ? value.review_configs : []

    for (const req of rawRequests) {
      const reqMapping = asMapping(req)
      if (!reqMapping) {
        continue
      }
      const name = String(reqMapping.name ?? 'tool')
      const args = asMapping(reqMapping.args) ?? {}
      const matchedConfig = rawConfigs.find((cfg) => {
        const cfgMapping = asMapping(cfg)
        return String(cfgMapping?.action_name ?? '') === name
      })
      const cfgMapping = asMapping(matchedConfig)
      const rawAllowed = Array.isArray(cfgMapping?.allowed_decisions) ? cfgMapping?.allowed_decisions : []
      const allowedDecisions = rawAllowed
        .map((item) => String(item))
        .filter((item): item is InterruptDecisionType => item === 'approve' || item === 'edit' || item === 'reject')

      normalized.push({
        name,
        args,
        allowedDecisions: allowedDecisions.length > 0 ? allowedDecisions : ['approve'],
      })
    }
  }

  return normalized
}

function nonInterruptMessageCount(items: ChatItem[]): number {
  return items.reduce((count, item) => (item.role === 'interrupt' ? count : count + 1), 0)
}

function buildInterruptChatItem(payload: unknown, anchorCount: number): ChatItem {
  const requests = parseInterruptActionRequests(payload)
  const summary = requests.length > 0 ? `待审批动作: ${requests.map((item) => item.name).join(', ')}` : '__interrupt__ captured'
  return {
    id: messageId('interrupt'),
    role: 'interrupt',
    text: summary,
    interruptAnchorCount: anchorCount,
    interruptPayload: payload,
    interruptActive: true,
    interruptActionRequests: requests,
  }
}

function markInterruptItemsResolved(items: ChatItem[]): ChatItem[] {
  return items.map((item) => (item.role === 'interrupt' ? { ...item, interruptActive: false } : item))
}

function buildResumeCommand(
  interruptPayload: unknown,
  decision: InterruptDecisionType,
  options?: { message?: string; editedArgsJson?: string },
): { resume: { decisions: Array<Record<string, unknown>> } } {
  const requests = parseInterruptActionRequests(interruptPayload)
  const targets = requests.length > 0 ? requests : [{ name: 'tool', args: {}, allowedDecisions: ['approve', 'edit', 'reject'] as InterruptDecisionType[] }]
  const decisions: Array<Record<string, unknown>> = []

  let editedArgs: Record<string, unknown> | null = null
  if (decision === 'edit' && options?.editedArgsJson?.trim()) {
    try {
      const parsed = JSON.parse(options.editedArgsJson)
      const mapping = asMapping(parsed)
      if (!mapping) {
        throw new Error('edited args must be a JSON object')
      }
      editedArgs = mapping
    } catch (error) {
      throw new Error(error instanceof Error ? `编辑参数不是合法 JSON: ${error.message}` : '编辑参数不是合法 JSON')
    }
  }

  for (const request of targets) {
    if (!request.allowedDecisions.includes(decision)) {
      throw new Error(`当前动作 ${request.name} 不支持 ${decision}`)
    }
    if (decision === 'approve') {
      decisions.push({ type: 'approve' })
      continue
    }
    if (decision === 'reject') {
      const message = options?.message?.trim()
      decisions.push(message ? { type: 'reject', message } : { type: 'reject' })
      continue
    }
    decisions.push({
      type: 'edit',
      edited_action: {
        name: request.name,
        args: editedArgs ?? request.args,
      },
    })
  }

  return { resume: { decisions } }
}

function stageFromRecoveredContext(interrupt: unknown, logs: RunLogItem[], items: MessageItem[]): UiStage {
  if (interrupt != null) {
    return 'human_review_required'
  }
  const latest = logs[logs.length - 1]
  if (latest?.status === 'error') {
    return 'run_error'
  }
  if (latest?.status === 'done' || latest?.status === 'success') {
    return 'run_done'
  }
  if (items.length > 0) {
    return 'run_done'
  }
  return 'run_started'
}

function extractSessionPreview(items: MessageItem[]): string {
  for (const item of items) {
    if (item.role === 'user' && item.text.trim()) {
      return item.text.trim().slice(0, 80)
    }
  }
  for (const item of items) {
    if (item.text.trim()) {
      return item.text.trim().slice(0, 80)
    }
  }
  return ''
}

function toTimestamp(value: string | null | undefined): number {
  if (!value) {
    return 0
  }
  const ts = Date.parse(value)
  return Number.isNaN(ts) ? 0 : ts
}

function sortSessionsByRecent(items: SessionItem[]): SessionItem[] {
  return [...items].sort((a, b) => toTimestamp(b.updatedAt) - toTimestamp(a.updatedAt))
}

function mergeStreamText(previous: string, incoming: string): string {
  if (!incoming) {
    return previous
  }
  if (!previous) {
    return incoming
  }
  if (incoming === previous) {
    return previous
  }
  if (incoming.startsWith(previous)) {
    return incoming
  }
  if (previous.endsWith(incoming)) {
    return previous
  }
  return `${previous}${incoming}`
}

function mergeWithInterruptCards(refreshedItems: ChatItem[], currentItems: ChatItem[]): ChatItem[] {
  const interruptCards = currentItems.filter((item) => item.role === 'interrupt')
  if (interruptCards.length === 0) return refreshedItems

  const buckets = new Map<number, ChatItem[]>()
  const total = refreshedItems.length
  for (const card of interruptCards) {
    const anchorRaw = typeof card.interruptAnchorCount === 'number' ? card.interruptAnchorCount : total
    const anchor = Math.max(0, Math.min(total, anchorRaw))
    const list = buckets.get(anchor)
    if (list) list.push(card)
    else buckets.set(anchor, [card])
  }

  const merged: ChatItem[] = []
  const beforeFirst = buckets.get(0)
  if (beforeFirst) merged.push(...beforeFirst)
  for (let i = 0; i < total; i += 1) {
    merged.push(refreshedItems[i])
    const afterCurrent = buckets.get(i + 1)
    if (afterCurrent) merged.push(...afterCurrent)
  }
  return merged
}

function newSession(index: number, seed?: Partial<SessionItem>): SessionItem {
  const id = `session-${Date.now()}-${index}`
  return {
    id,
    title: seed?.title ?? `Session ${index + 1}`,
    user_id: seed?.user_id ?? null,
    thread_id: seed?.thread_id ?? null,
    assistant_id: seed?.assistant_id ?? DEFAULT_SESSION_RUNTIME.assistant_id,
    graph_id: seed?.graph_id ?? DEFAULT_SESSION_RUNTIME.graph_id,
    system_prompt: seed?.system_prompt ?? DEFAULT_SESSION_RUNTIME.system_prompt,
    use_langgraph_sampling_defaults:
      seed?.use_langgraph_sampling_defaults ?? DEFAULT_SESSION_RUNTIME.use_langgraph_sampling_defaults,
    model_provider: seed?.model_provider ?? DEFAULT_SESSION_RUNTIME.model_provider,
    temperature: seed?.temperature ?? DEFAULT_SESSION_RUNTIME.temperature,
    top_p: seed?.top_p ?? DEFAULT_SESSION_RUNTIME.top_p,
    max_tokens: seed?.max_tokens ?? DEFAULT_SESSION_RUNTIME.max_tokens,
    enable_local_tools: seed?.enable_local_tools ?? DEFAULT_SESSION_RUNTIME.enable_local_tools,
    enable_local_mcp: seed?.enable_local_mcp ?? DEFAULT_SESSION_RUNTIME.enable_local_mcp,
    mcp_servers: seed?.mcp_servers ?? DEFAULT_SESSION_RUNTIME.mcp_servers,
    custom_tools: seed?.custom_tools ?? DEFAULT_SESSION_RUNTIME.custom_tools,
    updatedAt: seed?.updatedAt ?? nowLabel(),
    preview: seed?.preview ?? '',
  }
}

function sessionFromThread(thread: ThreadItem, index: number): SessionItem {
  const metadata = thread.metadata ?? {}
  const assistantId = typeof metadata.assistant_id === 'string' && metadata.assistant_id ? metadata.assistant_id : DEFAULT_SESSION_RUNTIME.assistant_id
  const modelProvider = typeof metadata.model_provider === 'string' && metadata.model_provider ? metadata.model_provider : DEFAULT_SESSION_RUNTIME.model_provider
  return newSession(index, {
    thread_id: thread.thread_id,
    title: `Thread ${index + 1}`,
    assistant_id: assistantId,
    model_provider: modelProvider,
    updatedAt: thread.updated_at ?? nowLabel(),
    preview: typeof metadata.preview === 'string' ? metadata.preview.slice(0, 80) : '',
  })
}

export function ObserverPage() {
  const [sessions, setSessions] = useState<SessionItem[]>([newSession(0)])
  const [activeSessionId, setActiveSessionId] = useState<string | null>(sessions[0].id)
  const [sessionsCollapsed, setSessionsCollapsed] = useState(false)
  const [controlsCollapsed, setControlsCollapsed] = useState(false)

  const [assistant_id, setAssistantId] = useState('agent')
  const [graph_id, setGraphId] = useState('')
  const [assistant_items, setAssistantItems] = useState<AssistantItem[]>([])
  const [system_prompt, setSystemPrompt] = useState('')
  const [use_langgraph_sampling_defaults, setUseLanggraphSamplingDefaults] = useState(true)
  const [model_provider, setModelProvider] = useState('openai')
  const [temperature, setTemperature] = useState(0.7)
  const [top_p, setTopP] = useState(1)
  const [max_tokens, setMaxTokens] = useState(512)
  const [enable_local_tools, setEnableLocalTools] = useState(true)
  const [enable_local_mcp, setEnableLocalMcp] = useState(false)
  const [mcp_servers, setMcpServers] = useState('')
  const [custom_tools, setCustomTools] = useState('')
  const [message, setMessage] = useState('请给我三条学习建议')

  const [stage, setStage] = useState<UiStage>('run_started')
  const [chatItems, setChatItems] = useState<ChatItem[]>([])
  const [streamDraft, setStreamDraft] = useState('')
  const [timeline, setTimeline] = useState<TimelineItem[]>([])
  const [stateSnapshot, setStateSnapshot] = useState<unknown>(null)
  const [stateSummary, setStateSummary] = useState('')
  const [historyCheckpoints, setHistoryCheckpoints] = useState<Array<{ ts: string; checkpoint: string }>>([])
  const [interruptPayload, setInterruptPayload] = useState<unknown>(null)
  const [runLogs, setRunLogs] = useState<RunLogItem[]>([])
  const [messageOffset, setMessageOffset] = useState(0)
  const [hasMoreMessages, setHasMoreMessages] = useState(false)
  const [loadingMoreMessages, setLoadingMoreMessages] = useState(false)
  const [threadsOffset, setThreadsOffset] = useState(0)
  const [hasMoreSessions, setHasMoreSessions] = useState(false)
  const [loadingMoreSessions, setLoadingMoreSessions] = useState(false)
  const [errorText, setErrorText] = useState('')
  const sourceRef = useRef<StreamConnection | null>(null)
  const streamDraftRef = useRef('')
  const interruptCapturedRef = useRef(false)
  const activeSessionIdRef = useRef<string | null>(activeSessionId)

  useEffect(() => {
    activeSessionIdRef.current = activeSessionId
  }, [activeSessionId])

  const activeSession = sessions.find((s) => s.id === activeSessionId) ?? null
  const graph_id_options = useMemo(() => {
    const values = new Set<string>()
    for (const item of assistant_items) {
      if (item.graph_id) values.add(item.graph_id)
    }
    return [...values].sort()
  }, [assistant_items])

  const filtered_assistant_items = useMemo(() => {
    if (!graph_id) {
      return assistant_items
    }
    return assistant_items.filter((item) => item.graph_id === graph_id)
  }, [assistant_items, graph_id])

  const updateActiveSession = (patch: Partial<SessionItem>) => {
    if (!activeSessionId) return
    setSessions((prev) => prev.map((item) => (item.id === activeSessionId ? { ...item, ...patch, updatedAt: nowLabel() } : item)))
  }

  const applySessionControls = useCallback((session: SessionItem) => {
    setAssistantId(session.assistant_id)
    setGraphId(session.graph_id)
    setSystemPrompt(session.system_prompt)
    setUseLanggraphSamplingDefaults(session.use_langgraph_sampling_defaults)
    setModelProvider(session.model_provider)
    setTemperature(session.temperature)
    setTopP(session.top_p)
    setMaxTokens(session.max_tokens)
    setEnableLocalTools(session.enable_local_tools)
    setEnableLocalMcp(session.enable_local_mcp)
    setMcpServers(session.mcp_servers)
    setCustomTools(session.custom_tools)
  }, [])

  const hydrateSessionPreviews = useCallback(async (targets: SessionItem[]) => {
    const unresolved = targets.filter((item) => item.thread_id && !item.preview.trim())
    if (unresolved.length === 0) {
      return
    }
    const resolved = await Promise.all(
      unresolved.map(async (item) => {
        try {
          const stateResp = await getState({ thread_id: item.thread_id ?? undefined })
          return { id: item.id, preview: extractFirstDialogPreviewFromState(stateResp.state) }
        } catch {
          return { id: item.id, preview: '' }
        }
      }),
    )
    setSessions((prev) =>
      prev.map((item) => {
        const hit = resolved.find((entry) => entry.id === item.id)
        if (!hit || !hit.preview) {
          return item
        }
        return { ...item, preview: hit.preview }
      }),
    )
  }, [])

  const appendTimeline = (item: TimelineItem) => setTimeline((prev) => [...prev, item])

  const loadSessionContext = useCallback(async (session: SessionItem) => {
    if (!session.thread_id) {
      return
    }
    const [messagesResp, stateResp, historyResp, logsResp] = await Promise.all([
      getMessages({ thread_id: session.thread_id, limit: MESSAGE_PAGE_SIZE, offset: 0 }),
      getState({ thread_id: session.thread_id }),
      getHistory({ thread_id: session.thread_id, limit: HISTORY_LIMIT }),
      getRunLogs({ thread_id: session.thread_id }),
    ])
    if (activeSessionIdRef.current !== session.id) {
      return
    }
    setSessions((prev) =>
      prev.map((item) =>
        item.id === session.id
          ? { ...item, thread_id: messagesResp.thread_id, updatedAt: nowLabel(), preview: extractSessionPreview(messagesResp.items) }
          : item,
      ),
    )
    const recoveredInterrupt = extractInterruptPayload(stateResp.state)
    const baseItems = mapMessageToChatItems(messagesResp.items)
    setChatItems(recoveredInterrupt != null ? [...baseItems, buildInterruptChatItem(recoveredInterrupt)] : baseItems)
    setMessageOffset(messagesResp.items.length)
    setHasMoreMessages(messagesResp.items.length === MESSAGE_PAGE_SIZE)
    setStateSnapshot(stateResp.state)
    setStateSummary(summarizeStateSnapshot(stateResp.state))
    setHistoryCheckpoints(normalizeHistoryCheckpoints(historyResp.items))
    setRunLogs(logsResp.items)

    interruptCapturedRef.current = recoveredInterrupt != null
    setInterruptPayload(recoveredInterrupt)
    setStage(stageFromRecoveredContext(recoveredInterrupt, logsResp.items, messagesResp.items))
  }, [])

  const loadMoreMessagesForActiveSession = useCallback(async () => {
    if (!activeSession) {
      return
    }
    if (!activeSession.thread_id) {
      return
    }
    if (!hasMoreMessages || loadingMoreMessages) {
      return
    }
    setLoadingMoreMessages(true)
    try {
      const resp = await getMessages({ thread_id: activeSession.thread_id, limit: MESSAGE_PAGE_SIZE, offset: messageOffset })
      const older = mapMessageToChatItems(resp.items)
      setChatItems((prev) => [...older, ...prev])
      setMessageOffset((prev) => prev + resp.items.length)
      setHasMoreMessages(resp.items.length === MESSAGE_PAGE_SIZE)
    } finally {
      setLoadingMoreMessages(false)
    }
  }, [activeSession, hasMoreMessages, loadingMoreMessages, messageOffset])

  const provisionThreadForSession = useCallback(async (session: SessionItem) => {
    try {
      const threadResp = await createThread()
      setSessions((prev) =>
        prev.map((item) =>
          item.id === session.id ? { ...item, thread_id: threadResp.thread_id, updatedAt: nowLabel() } : item,
        ),
      )
      if (activeSessionId === session.id) {
        await loadSessionContext({ ...session, thread_id: threadResp.thread_id })
      }
    } catch (error) {
      const msg = error instanceof Error ? error.message : String(error)
      setErrorText(`创建线程失败: ${msg}`)
    }
  }, [activeSessionId, loadSessionContext])

  const loadAssistants = useCallback(async () => {
    const response = await getAssistants({ graph_id: graph_id || undefined, limit: 200, offset: 0 })
    setAssistantItems(response.items)
  }, [graph_id])

  useEffect(() => {
    void loadAssistants()
  }, [loadAssistants])

  useEffect(() => {
    void (async () => {
      try {
        const resp = await getThreads(THREAD_PAGE_SIZE, 0)
        if (resp.items.length === 0) {
          setThreadsOffset(0)
          setHasMoreSessions(false)
          return
        }
        const mapped = resp.items.map((item, index) => sessionFromThread(item, index))
        const sorted = sortSessionsByRecent(mapped)
        setSessions(sorted)
        setThreadsOffset(resp.items.length)
        setHasMoreSessions(resp.items.length === THREAD_PAGE_SIZE)
        setActiveSessionId(sorted[0]?.id ?? null)
        applySessionControls(sorted[0])
        void hydrateSessionPreviews(sorted)
        await loadSessionContext(sorted[0])
      } catch (error) {
        const msg = error instanceof Error ? error.message : String(error)
        setErrorText(`加载 threads 失败: ${msg}`)
      }
    })()
  }, [applySessionControls, hydrateSessionPreviews, loadSessionContext])

  const handleLoadMoreSessions = async () => {
    if (loadingMoreSessions || !hasMoreSessions) {
      return
    }
    setLoadingMoreSessions(true)
    try {
      const resp = await getThreads(THREAD_PAGE_SIZE, threadsOffset)
      const mapped = resp.items.map((item, index) => sessionFromThread(item, threadsOffset + index))
      setSessions((prev) => {
        const existingThreadIds = new Set(prev.map((item) => item.thread_id).filter((id): id is string => !!id))
        const incoming = mapped.filter((item) => !item.thread_id || !existingThreadIds.has(item.thread_id))
        return sortSessionsByRecent([...prev, ...incoming])
      })
      void hydrateSessionPreviews(mapped)
      setThreadsOffset((prev) => prev + resp.items.length)
      setHasMoreSessions(resp.items.length === THREAD_PAGE_SIZE)
    } finally {
      setLoadingMoreSessions(false)
    }
  }

  useEffect(() => {
    if (filtered_assistant_items.length === 0) {
      return
    }
    const matched = filtered_assistant_items.some((item) => item.assistant_id === assistant_id)
    if (!matched) {
      setAssistantId(filtered_assistant_items[0].assistant_id)
    }
  }, [assistant_id, filtered_assistant_items])

  useEffect(() => {
    if (!activeSessionId) {
      return
    }
    setSessions((prev) =>
      prev.map((item) =>
        item.id === activeSessionId
          ? {
              ...item,
              assistant_id,
              graph_id,
              system_prompt,
              use_langgraph_sampling_defaults,
              model_provider,
              temperature,
              top_p,
              max_tokens,
              enable_local_tools,
              enable_local_mcp,
              mcp_servers,
              custom_tools,
            }
          : item,
      ),
    )
  }, [
    activeSessionId,
    assistant_id,
    custom_tools,
    enable_local_mcp,
    enable_local_tools,
    graph_id,
    max_tokens,
    mcp_servers,
    model_provider,
    system_prompt,
    temperature,
    top_p,
    use_langgraph_sampling_defaults,
  ])

  const handleRefreshState = async () => {
    if (!activeSession?.thread_id) return
    const state = await getState({ thread_id: activeSession.thread_id })
    updateActiveSession({ thread_id: state.thread_id })
    setStateSnapshot(state.state)
    setStateSummary(summarizeStateSnapshot(state.state))
    const history = await getHistory({ thread_id: activeSession.thread_id, limit: HISTORY_LIMIT })
    setHistoryCheckpoints(normalizeHistoryCheckpoints(history.items))
  }

  const handleRefreshLogs = async () => {
    if (!activeSession?.thread_id) return
    const logs = await getRunLogs({ thread_id: activeSession.thread_id })
    setRunLogs(logs.items)
  }

  const commitStreamDraftAsMessage = () => {
    const finalDraft = streamDraftRef.current.trim()
    if (!finalDraft) {
      return ''
    }
    setChatItems((prev) => [...prev, { id: messageId('ai-final'), role: 'ai', text: finalDraft }])
    setStreamDraft('')
    streamDraftRef.current = ''
    return finalDraft
  }

  const handleStreamEvent = (eventName: string, rawData: string) => {
    const data = parseJson(rawData)
    const interrupt = extractInterruptPayload(data)
    const firstInterrupt = interrupt != null && !interruptCapturedRef.current
    const cat = categoryOf(eventName, data)
    const summary = summarizeEvent(eventName, data)

    if (eventName.startsWith('messages')) {
      const mapping = extractMessagePayload(data)
      const contentText = extractTextContent(mapping)
      if (contentText.length > 0) {
        const merged = mergeStreamText(streamDraftRef.current, contentText)
        streamDraftRef.current = merged
        setStreamDraft(merged)
      }
    }

    if (interrupt != null) {
      interruptCapturedRef.current = true
      setInterruptPayload(interrupt)
      setStage('human_review_required')
    } else if (interruptCapturedRef.current && cat.stage !== 'run_error' && cat.stage !== 'run_done') {
      setStage('human_review_required')
    } else {
      setStage(cat.stage)
    }

    if (firstInterrupt) {
      const finalDraft = streamDraftRef.current.trim()
      setChatItems((prev) => {
        const next = [...markInterruptItemsResolved(prev)]
        if (finalDraft) {
          next.push({ id: messageId('ai-final'), role: 'ai', text: finalDraft })
        }
        next.push(buildInterruptChatItem(interrupt))
        return next
      })
      if (finalDraft) {
        setStreamDraft('')
        streamDraftRef.current = ''
      }
    }
    appendTimeline({ ts: nowLabel(), category: cat.category, event: eventName, summary })

    if (eventName === 'done') {
      if (interruptCapturedRef.current) {
        commitStreamDraftAsMessage()
        setStage('human_review_required')
        sourceRef.current?.close()
        sourceRef.current = null
        void handleRefreshState()
        void handleRefreshLogs()
        return
      }
      setStage('run_done')
      commitStreamDraftAsMessage()
      sourceRef.current?.close()
      sourceRef.current = null
      void handleRefreshState()
      void handleRefreshLogs()
      if (activeSessionIdRef.current) {
        const session = sessions.find((item) => item.id === activeSessionIdRef.current)
        if (session?.thread_id) {
          void getMessages({ thread_id: session.thread_id, limit: MESSAGE_PAGE_SIZE, offset: 0 }).then((resp) => {
            setChatItems(mapMessageToChatItems(resp.items))
            setMessageOffset(resp.items.length)
            setHasMoreMessages(resp.items.length === MESSAGE_PAGE_SIZE)
            setSessions((prev) =>
              prev.map((item) =>
                item.id === session.id ? { ...item, updatedAt: nowLabel(), preview: extractSessionPreview(resp.items) } : item,
              ),
            )
          })
        }
      }
    }

    if (eventName === 'error') {
      setStage('run_error')
      setErrorText(summarize(data))
      setStreamDraft('')
      streamDraftRef.current = ''
      sourceRef.current?.close()
      sourceRef.current = null
      void handleRefreshLogs()
    }
  }

  const handleStartStream = async (evt: FormEvent) => {
    evt.preventDefault()
    if (!activeSession) return

    setErrorText('')
    setInterruptPayload(null)
    interruptCapturedRef.current = false
    setStage('run_started')
    setStreamDraft('')
    streamDraftRef.current = ''

    let currentThreadId = activeSession.thread_id
    if (!currentThreadId) {
      const threadResp = await createThread()
      currentThreadId = threadResp.thread_id
      updateActiveSession({ thread_id: currentThreadId })
    }
    setChatItems((prev) => [...prev, { id: messageId('user-input'), role: 'user', text: message }])
    if (!activeSession.preview.trim()) {
      updateActiveSession({ preview: message.trim().slice(0, 80) })
    }

    sourceRef.current?.close()

    const params = new URLSearchParams({
      user_id: activeSession.user_id ?? `thread-${currentThreadId}`,
      thread_id: currentThreadId,
      assistant_id: activeSession.assistant_id,
      message,
    })
    const contextPayload: Record<string, unknown> = {
      model_provider,
    }
    if (!use_langgraph_sampling_defaults) {
      contextPayload.temperature = temperature
      contextPayload.top_p = top_p
      contextPayload.max_tokens = max_tokens
    }
    contextPayload.enable_local_tools = enable_local_tools
    contextPayload.enable_local_mcp = enable_local_mcp
    if (system_prompt.trim()) {
      contextPayload.system_prompt = system_prompt
    }
    const normalizedMcpServers = mcp_servers
      .split(',')
      .map((item) => item.trim())
      .filter((item) => item.length > 0)
    if (enable_local_mcp && normalizedMcpServers.length > 0) {
      contextPayload.mcp_servers = normalizedMcpServers
    }
    const normalizedCustomTools = custom_tools
      .split(',')
      .map((item) => item.trim())
      .filter((item) => item.length > 0)
    if (normalizedCustomTools.length > 0 && enable_local_tools) {
      contextPayload.custom_tools = normalizedCustomTools
    }
    params.set('context_json', JSON.stringify(contextPayload))

    sourceRef.current = openStream(params, {
      onOpen: () => setStage('model_streaming'),
      onEvent: handleStreamEvent,
      onError: () => {
        setStage('run_error')
        setErrorText('SSE disconnected')
        sourceRef.current?.close()
        sourceRef.current = null
        void handleRefreshLogs()
      },
    })
  }

  const handleApproveResume = async () => {
    await handleInterruptDecision('approve')
  }

  const handleInterruptDecision = async (decision: InterruptDecisionType, options?: { message?: string; editedArgsJson?: string }) => {
    if (!activeSession?.thread_id) return
    if (interruptPayload == null) {
      setErrorText('当前没有待处理的人工审核项')
      return
    }

    let command: { resume: { decisions: Array<Record<string, unknown>> } }
    try {
      command = buildResumeCommand(interruptPayload, decision, options)
    } catch (error) {
      setErrorText(error instanceof Error ? error.message : String(error))
      return
    }

    setErrorText('')
    setStage('run_started')
    setChatItems((prev) => markInterruptItemsResolved(prev))
    const result = await resumeChat({
      thread_id: activeSession.thread_id,
      assistant_id: activeSession.assistant_id,
      command,
    })
    updateActiveSession({ thread_id: result.thread_id })
    const nextInterrupt = extractInterruptPayload(result.result)
    interruptCapturedRef.current = nextInterrupt != null
    setInterruptPayload(nextInterrupt)
    if (nextInterrupt != null) {
      setChatItems((prev) => [...markInterruptItemsResolved(prev), buildInterruptChatItem(nextInterrupt)])
    }
    setStage(nextInterrupt != null ? 'human_review_required' : 'run_done')
    appendTimeline({ ts: nowLabel(), category: 'run_terminal', event: 'resume', summary: 'resume called' })
    const refreshed = await getMessages({ thread_id: result.thread_id, limit: MESSAGE_PAGE_SIZE, offset: 0 })
    setChatItems((prev) => mergeWithInterruptCards(mapMessageToChatItems(refreshed.items), prev))
    setMessageOffset(refreshed.items.length)
    setHasMoreMessages(refreshed.items.length === MESSAGE_PAGE_SIZE)
    updateActiveSession({ preview: extractSessionPreview(refreshed.items) })
    void handleRefreshState()
    void handleRefreshLogs()
  }

  const handleCreateSession = () => {
    const nextSession = newSession(sessions.length, {
      assistant_id,
      graph_id,
      system_prompt,
      use_langgraph_sampling_defaults,
      model_provider,
      temperature,
      top_p,
      max_tokens,
      enable_local_tools,
      enable_local_mcp,
      mcp_servers,
      custom_tools,
    })
    setSessions((prev) => [nextSession, ...prev])
    setActiveSessionId(nextSession.id)
    setChatItems([])
    setTimeline([])
    setRunLogs([])
    setStateSnapshot(null)
    setStateSummary('')
    setHistoryCheckpoints([])
    setInterruptPayload(null)
    setErrorText('')
    void (async () => {
      const created = await createThread()
      setSessions((prev) =>
        prev.map((item) =>
          item.id === nextSession.id ? { ...item, thread_id: created.thread_id, updatedAt: nowLabel() } : item,
        ),
      )
    })()
  }

  const handleSelectSession = (sessionId: string) => {
    setActiveSessionId(sessionId)
    setChatItems([])
    setTimeline([])
    setRunLogs([])
    setStateSnapshot(null)
    setStateSummary('')
    setHistoryCheckpoints([])
    setInterruptPayload(null)
    setMessageOffset(0)
    setHasMoreMessages(false)
    const selected = sessions.find((item) => item.id === sessionId)
    if (selected) {
      applySessionControls(selected)
    }
    if (selected && !selected.thread_id) {
      void provisionThreadForSession(selected)
      return
    }
    if (selected) {
      void loadSessionContext(selected)
    }
  }

  return (
    <main style={{ minHeight: '100vh', padding: 16, background: '#f5f7fa' }}>
      <header
        style={{
          background: '#fff',
          border: '1px solid #e5e7eb',
          borderRadius: 12,
          padding: '10px 14px',
          display: 'flex',
          justifyContent: 'space-between',
          alignItems: 'center',
          marginBottom: 12,
        }}
      >
        <strong>LangGraph AI Platform (Learning MVP)</strong>
        <span style={{ fontSize: 12, color: '#6b7280' }}>env: dev · stage: {stage}</span>
      </header>

      <div
        style={{
          display: 'grid',
          gridTemplateColumns: `${sessionsCollapsed ? 44 : 260}px 1fr ${controlsCollapsed ? 44 : 360}px`,
          gap: 12,
          alignItems: 'start',
          transition: 'all 180ms ease',
        }}
      >
        <SessionPanel
          sessions={sessions.map((item) => ({
            id: item.id,
            title: item.title,
            assistant_id: item.assistant_id,
            thread_id: item.thread_id,
            updatedAt: item.updatedAt,
            preview: item.preview,
          }))}
          activeSessionId={activeSessionId}
          collapsed={sessionsCollapsed}
          onToggleCollapsed={() => setSessionsCollapsed((prev) => !prev)}
          onSelectSession={handleSelectSession}
          onCreateSession={handleCreateSession}
          hasMore={hasMoreSessions}
          loadingMore={loadingMoreSessions}
          onLoadMore={() => void handleLoadMoreSessions()}
        />

        <section style={{ display: 'grid', gap: 12 }}>
          <form
            onSubmit={handleStartStream}
            style={{ background: '#fff', border: '1px solid #e5e7eb', borderRadius: 12, padding: 12, display: 'grid', gap: 8 }}
          >
            <input value={message} onChange={(e) => setMessage(e.target.value)} placeholder="输入消息..." />
            <div style={{ display: 'flex', gap: 8 }}>
              <button type="submit">Start Stream</button>
              <button type="button" onClick={() => sourceRef.current?.close()}>
                Stop
              </button>
            </div>
          </form>
          {errorText ? <p style={{ color: '#b91c1c', margin: 0 }}>Error: {errorText}</p> : null}
          <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
            <span style={{ fontSize: 12, color: '#6b7280' }}>消息分页：已加载 {chatItems.length} 条</span>
            <button type="button" onClick={() => void loadMoreMessagesForActiveSession()} disabled={!hasMoreMessages || loadingMoreMessages}>
              {loadingMoreMessages ? '加载中...' : hasMoreMessages ? '加载更早消息' : '没有更多消息'}
            </button>
          </div>
          <ChatPanel
            messages={chatItems}
            streamDraft={streamDraft}
            stage={stage}
            onInterruptDecision={handleInterruptDecision}
          />
        </section>

        <section style={{ display: 'grid', gap: 12 }}>
          <ControlPanel
            collapsed={controlsCollapsed}
            on_toggle_collapsed={() => setControlsCollapsed((prev) => !prev)}
            graph_id={graph_id}
            graph_id_options={graph_id_options}
            on_graph_id_change={setGraphId}
            assistant_id={assistant_id}
            assistant_options={filtered_assistant_items}
            on_assistant_id_change={setAssistantId}
            on_refresh_assistants={loadAssistants}
            system_prompt={system_prompt}
            on_system_prompt_change={setSystemPrompt}
            use_langgraph_sampling_defaults={use_langgraph_sampling_defaults}
            on_use_langgraph_sampling_defaults_change={setUseLanggraphSamplingDefaults}
            temperature={temperature}
            on_temperature_change={setTemperature}
            top_p={top_p}
            on_top_p_change={setTopP}
            max_tokens={max_tokens}
            on_max_tokens_change={setMaxTokens}
            model_provider={model_provider}
            model_provider_options={MODEL_PROVIDER_OPTIONS}
            on_model_provider_change={setModelProvider}
            enable_local_tools={enable_local_tools}
            on_enable_local_tools_change={setEnableLocalTools}
            enable_local_mcp={enable_local_mcp}
            on_enable_local_mcp_change={setEnableLocalMcp}
            mcp_servers={mcp_servers}
            mcp_server_options={MCP_SERVER_OPTIONS}
            on_mcp_servers_change={setMcpServers}
            custom_tools={custom_tools}
            on_custom_tools_change={setCustomTools}
          />
          <TimelinePanel items={timeline} />
          <StatePanel
            thread_id={activeSession?.thread_id ?? null}
            stateSnapshot={stateSnapshot}
            stateSummary={stateSummary}
            historyCheckpoints={historyCheckpoints}
            interruptPayload={interruptPayload}
            onRefreshState={handleRefreshState}
            onApproveResume={handleApproveResume}
          />
          <DebugPanel items={runLogs} onRefreshLogs={handleRefreshLogs} />
        </section>
      </div>
    </main>
  )
}
