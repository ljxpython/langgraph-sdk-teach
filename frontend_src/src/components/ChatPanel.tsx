import { AssistantMessage } from './chat/AssistantMessage'
import { HumanMessage } from './chat/HumanMessage'
import { useState } from 'react'

export type InterruptDecisionType = 'approve' | 'edit' | 'reject'

export type InterruptActionRequest = {
  name: string
  args: Record<string, unknown>
  allowedDecisions: InterruptDecisionType[]
}

export type ChatItem = {
  id: string
  role: 'user' | 'ai' | 'tool' | 'interrupt'
  text: string
  name?: string
  interruptAnchorCount?: number
  interruptPayload?: unknown
  interruptActive?: boolean
  interruptActionRequests?: InterruptActionRequest[]
}

type ChatPanelProps = {
  messages: ChatItem[]
  streamDraft: string
  stage: string
  onInterruptDecision: (decision: InterruptDecisionType, options?: { message?: string; editedArgsJson?: string }) => Promise<void>
}

function stageLabel(stage: string): string {
  if (stage === 'human_review_required') return '待人工审核'
  if (stage === 'model_streaming') return '模型流式输出中'
  if (stage === 'tool_calling') return '工具调用中'
  if (stage === 'tool_completed') return '工具调用完成'
  if (stage === 'run_done') return '运行完成'
  if (stage === 'run_error') return '运行失败'
  if (stage === 'run_started') return '已启动'
  return stage
}

function dedupeDecisions(requests: InterruptActionRequest[]): InterruptDecisionType[] {
  const values = new Set<InterruptDecisionType>()
  for (const request of requests) {
    for (const decision of request.allowedDecisions) {
      values.add(decision)
    }
  }
  if (values.size === 0) {
    return ['approve']
  }
  return ['approve', 'edit', 'reject'].filter((item) => values.has(item as InterruptDecisionType)) as InterruptDecisionType[]
}

export function ChatPanel({ messages, streamDraft, stage, onInterruptDecision }: ChatPanelProps) {
  const [rejectMessage, setRejectMessage] = useState('')
  const [editArgsJson, setEditArgsJson] = useState('')
  const hasPendingInterrupt = messages.some((item) => item.role === 'interrupt' && item.interruptActive)
  const effectiveStage = hasPendingInterrupt ? 'human_review_required' : stage

  return (
    <section style={{ background: '#fff', border: '1px solid #e5e7eb', borderRadius: 12, padding: 16 }}>
      <h2 style={{ marginTop: 0 }}>Chat Panel</h2>
      <p style={{ marginTop: 0 }}>当前阶段：{stageLabel(effectiveStage)} ({effectiveStage})</p>
      <div style={{ display: 'grid', gap: 8 }}>
        {messages.map((item, idx) => {
          if (item.role === 'user') {
            return <HumanMessage key={item.id} text={item.text} idx={idx} />
          }
          if (item.role === 'interrupt') {
            const requests = item.interruptActionRequests ?? []
            const decisions = dedupeDecisions(requests)
            return (
              <div key={item.id} style={{ border: '1px solid #f59e0b', background: '#fffbeb', borderRadius: 12, padding: 12 }}>
                <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 6 }}>
                  <div style={{ fontWeight: 700 }}>人工审核请求</div>
                  <span style={{ fontSize: 12, color: '#92400e' }}>{item.interruptActive ? '待处理' : '已处理'}</span>
                </div>
                <div style={{ marginBottom: 8, fontSize: 13 }}>{item.text}</div>
                {requests.length > 0 ? (
                  <div style={{ display: 'grid', gap: 6, marginBottom: 8 }}>
                    {requests.map((request, requestIdx) => (
                      <div key={`${item.id}-request-${requestIdx}`} style={{ border: '1px solid #fde68a', borderRadius: 8, padding: 8, background: '#fffdf5' }}>
                        <div style={{ fontSize: 12, fontWeight: 600 }}>动作: {request.name}</div>
                        <div style={{ fontSize: 12, color: '#6b7280' }}>允许操作: {request.allowedDecisions.join(' / ')}</div>
                        <pre style={{ margin: '6px 0 0 0', whiteSpace: 'pre-wrap', fontSize: 12 }}>{JSON.stringify(request.args, null, 2)}</pre>
                      </div>
                    ))}
                  </div>
                ) : null}
                {item.interruptPayload ? (
                  <details>
                    <summary style={{ cursor: 'pointer', fontSize: 12, color: '#6b7280' }}>查看完整中断数据</summary>
                    <pre style={{ margin: '8px 0 0 0', whiteSpace: 'pre-wrap', fontSize: 12 }}>{JSON.stringify(item.interruptPayload, null, 2)}</pre>
                  </details>
                ) : null}
                {item.interruptActive ? (
                  <div style={{ display: 'grid', gap: 8, marginTop: 8 }}>
                    {decisions.includes('edit') ? (
                      <textarea
                        value={editArgsJson}
                        onChange={(evt) => setEditArgsJson(evt.target.value)}
                        placeholder='编辑参数(JSON)，留空将沿用原参数'
                        style={{ minHeight: 80 }}
                      />
                    ) : null}
                    {decisions.includes('reject') ? (
                      <input
                        value={rejectMessage}
                        onChange={(evt) => setRejectMessage(evt.target.value)}
                        placeholder='拒绝说明（可选）'
                      />
                    ) : null}
                    <div style={{ display: 'flex', justifyContent: 'flex-end', gap: 8, flexWrap: 'wrap' }}>
                      {decisions.includes('reject') ? (
                        <button
                          type="button"
                          onClick={() => void onInterruptDecision('reject', { message: rejectMessage })}
                          style={{ background: '#fee2e2', border: '1px solid #fca5a5' }}
                        >
                          拒绝
                        </button>
                      ) : null}
                      {decisions.includes('edit') ? (
                        <button
                          type="button"
                          onClick={() => void onInterruptDecision('edit', { editedArgsJson: editArgsJson })}
                          style={{ background: '#e0f2fe', border: '1px solid #7dd3fc' }}
                        >
                          编辑后继续
                        </button>
                      ) : null}
                      {decisions.includes('approve') ? (
                        <button
                          type="button"
                          onClick={() => void onInterruptDecision('approve')}
                          style={{ background: '#dcfce7', border: '1px solid #86efac' }}
                        >
                          批准并继续
                        </button>
                      ) : null}
                    </div>
                  </div>
                ) : (
                  <div style={{ marginTop: 8, fontSize: 12, color: '#6b7280' }}>该中断已处理</div>
                )}
              </div>
            )
          }
          if (item.role === 'tool') {
            const title = item.name?.trim() ? `Tool(${item.name})` : 'Tool'
            const text = item.text.trim() ? `${title}\n\n${item.text}` : title
            return <AssistantMessage key={item.id} text={text} idx={idx} />
          }
          return <AssistantMessage key={item.id} text={item.text} idx={idx} />
        })}
        {streamDraft ? <AssistantMessage text={streamDraft} idx={messages.length} stream /> : null}
      </div>
    </section>
  )
}
