import { useCallback, useEffect, useMemo, useState } from 'react'

import type { AssistantItem } from '../lib/api'
import {
  createAssistant,
  deleteAssistant,
  getAssistants,
  getGraphs,
  updateAssistant,
} from '../lib/api'

type AssistantManagePageProps = {
  onBack?: () => void
}

type ToastItem = {
  id: number
  tone: 'success' | 'error'
  text: string
}

export function AssistantManagePage({ onBack }: AssistantManagePageProps) {
  const [items, setItems] = useState<AssistantItem[]>([])
  const [graphOptions, setGraphOptions] = useState<string[]>([])
  const [graphLoading, setGraphLoading] = useState(false)
  const [loading, setLoading] = useState(false)
  const [createPending, setCreatePending] = useState(false)
  const [updatePending, setUpdatePending] = useState(false)
  const [deletePending, setDeletePending] = useState(false)
  const [toasts, setToasts] = useState<ToastItem[]>([])

  const [graphId, setGraphId] = useState('agent')
  const [name, setName] = useState('')
  const [description, setDescription] = useState('')
  const [modelProvider, setModelProvider] = useState('')
  const [systemPrompt, setSystemPrompt] = useState('')
  const [enableLocalTools, setEnableLocalTools] = useState(true)
  const [enableLocalMcp, setEnableLocalMcp] = useState(false)
  const [mcpServers, setMcpServers] = useState('')
  const [recursionLimit, setRecursionLimit] = useState('')
  const [metadataOwner, setMetadataOwner] = useState('')
  const [metadataTag, setMetadataTag] = useState('')
  const [contextJson, setContextJson] = useState('')
  const [configJson, setConfigJson] = useState('')
  const [metadataJson, setMetadataJson] = useState('')

  const [editAssistantId, setEditAssistantId] = useState('')
  const [editGraphId, setEditGraphId] = useState('')
  const [editName, setEditName] = useState('')
  const [editDescription, setEditDescription] = useState('')
  const [editModelProvider, setEditModelProvider] = useState('')
  const [editSystemPrompt, setEditSystemPrompt] = useState('')
  const [editEnableLocalTools, setEditEnableLocalTools] = useState(true)
  const [editEnableLocalMcp, setEditEnableLocalMcp] = useState(false)
  const [editMcpServers, setEditMcpServers] = useState('')
  const [editRecursionLimit, setEditRecursionLimit] = useState('')
  const [editMetadataOwner, setEditMetadataOwner] = useState('')
  const [editMetadataTag, setEditMetadataTag] = useState('')
  const [editContextJson, setEditContextJson] = useState('')
  const [editConfigJson, setEditConfigJson] = useState('')
  const [editMetadataJson, setEditMetadataJson] = useState('')
  const [deleteConfirmText, setDeleteConfirmText] = useState('')
  const [deleteThreads, setDeleteThreads] = useState(false)

  const canDelete = useMemo(
    () => editAssistantId.trim().length > 0 && deleteConfirmText.trim() === editAssistantId.trim(),
    [deleteConfirmText, editAssistantId],
  )

  const pushToast = useCallback((tone: 'success' | 'error', text: string) => {
    const id = Date.now() + Math.floor(Math.random() * 100000)
    setToasts((prev) => [...prev, { id, tone, text }])
    window.setTimeout(() => {
      setToasts((prev) => prev.filter((item) => item.id !== id))
    }, 3000)
  }, [])

  const removeToast = (id: number) => {
    setToasts((prev) => prev.filter((item) => item.id !== id))
  }

  const parseJsonObject = (raw: string, fieldName: string): Record<string, unknown> | undefined => {
    if (!raw.trim()) {
      return undefined
    }
    let value: unknown
    try {
      value = JSON.parse(raw)
    } catch {
      throw new Error(`${fieldName} 不是合法 JSON`)
    }
    if (!value || typeof value !== 'object' || Array.isArray(value)) {
      throw new Error(`${fieldName} 必须是 JSON 对象`)
    }
    return value as Record<string, unknown>
  }

  const parseServerList = (raw: string): string[] => {
    return raw
      .split(',')
      .map((item) => item.trim())
      .filter((item) => item.length > 0)
  }

  const parsePositiveInt = (raw: string, fieldName: string): number | undefined => {
    if (!raw.trim()) {
      return undefined
    }
    const value = Number(raw)
    if (!Number.isInteger(value) || value <= 0) {
      throw new Error(`${fieldName} 必须是正整数`)
    }
    return value
  }

  const mergeObjects = (
    base: Record<string, unknown>,
    ext: Record<string, unknown> | undefined,
  ): Record<string, unknown> | undefined => {
    const merged = { ...base, ...(ext ?? {}) }
    return Object.keys(merged).length > 0 ? merged : undefined
  }

  const loadGraphs = useCallback(async () => {
    setGraphLoading(true)
    try {
      const resp = await getGraphs()
      setGraphOptions(resp.items)
      if (resp.items.length > 0 && !resp.items.includes(graphId)) {
        setGraphId(resp.items[0])
      }
    } catch {
      setGraphOptions([])
      pushToast('error', '加载 graph 列表失败，已回退到手动输入')
    } finally {
      setGraphLoading(false)
    }
  }, [graphId, pushToast])

  const loadAssistants = useCallback(async (withSuccessNotice: boolean = false) => {
    setLoading(true)
    try {
      const resp = await getAssistants({ limit: 200, offset: 0 })
      setItems(resp.items)
      if (withSuccessNotice) {
        pushToast('success', `刷新成功，共 ${resp.items.length} 个 assistant`)
      }
    } catch (error) {
      const msg = error instanceof Error ? error.message : String(error)
      pushToast('error', `刷新失败：${msg}`)
    } finally {
      setLoading(false)
    }
  }, [pushToast])

  useEffect(() => {
    void loadAssistants()
    void loadGraphs()
  }, [loadAssistants, loadGraphs])

  const handleCreate = async () => {
    if (!graphId.trim()) {
      pushToast('error', '创建失败：graph_id 不能为空')
      return
    }
    setCreatePending(true)
    try {
      const recursion = parsePositiveInt(recursionLimit, 'recursion_limit')
      const context = mergeObjects(
        {
          ...(modelProvider.trim() ? { model_provider: modelProvider.trim() } : {}),
          ...(systemPrompt.trim() ? { system_prompt: systemPrompt.trim() } : {}),
          enable_local_tools: enableLocalTools,
          enable_local_mcp: enableLocalMcp,
          ...(enableLocalMcp && parseServerList(mcpServers).length > 0 ? { mcp_servers: parseServerList(mcpServers) } : {}),
        },
        parseJsonObject(contextJson, 'context_json'),
      )
      const config = mergeObjects(
        {
          ...(typeof recursion === 'number' ? { recursion_limit: recursion } : {}),
        },
        parseJsonObject(configJson, 'config_json'),
      )
      const metadata = mergeObjects(
        {
          ...(metadataOwner.trim() ? { owner: metadataOwner.trim() } : {}),
          ...(metadataTag.trim() ? { tag: metadataTag.trim() } : {}),
        },
        parseJsonObject(metadataJson, 'metadata_json'),
      )
      const created = await createAssistant({
        graph_id: graphId.trim(),
        name: name.trim() || undefined,
        description: description.trim() || undefined,
        context,
        config,
        metadata,
      })
      setName('')
      setDescription('')
      setModelProvider('')
      setSystemPrompt('')
      setEnableLocalTools(true)
      setEnableLocalMcp(false)
      setMcpServers('')
      setRecursionLimit('')
      setMetadataOwner('')
      setMetadataTag('')
      setContextJson('')
      setConfigJson('')
      setMetadataJson('')
      await loadAssistants()
      pushToast('success', `创建成功：${created.item.assistant_id}`)
    } catch (error) {
      const msg = error instanceof Error ? error.message : String(error)
      pushToast('error', `创建失败：${msg}`)
    } finally {
      setCreatePending(false)
    }
  }

  const handleSelectForEdit = (item: AssistantItem) => {
    setEditAssistantId(item.assistant_id)
    setEditGraphId(item.graph_id ?? '')
    setEditName(item.name ?? '')
    setEditDescription('')
    setEditModelProvider('')
    setEditSystemPrompt('')
    setEditEnableLocalTools(true)
    setEditEnableLocalMcp(false)
    setEditMcpServers('')
    setEditRecursionLimit('')
    setEditMetadataOwner('')
    setEditMetadataTag('')
    setEditContextJson('')
    setEditConfigJson('')
    setEditMetadataJson('')
    setDeleteConfirmText('')
  }

  const handleUpdate = async () => {
    if (!editAssistantId) {
      pushToast('error', '更新失败：请先选择要更新的 assistant')
      return
    }
    setUpdatePending(true)
    try {
      const recursion = parsePositiveInt(editRecursionLimit, 'edit_recursion_limit')
      const context = mergeObjects(
        {
          ...(editModelProvider.trim() ? { model_provider: editModelProvider.trim() } : {}),
          ...(editSystemPrompt.trim() ? { system_prompt: editSystemPrompt.trim() } : {}),
          enable_local_tools: editEnableLocalTools,
          enable_local_mcp: editEnableLocalMcp,
          ...(editEnableLocalMcp && parseServerList(editMcpServers).length > 0 ? { mcp_servers: parseServerList(editMcpServers) } : {}),
        },
        parseJsonObject(editContextJson, 'edit_context_json'),
      )
      const config = mergeObjects(
        {
          ...(typeof recursion === 'number' ? { recursion_limit: recursion } : {}),
        },
        parseJsonObject(editConfigJson, 'edit_config_json'),
      )
      const metadata = mergeObjects(
        {
          ...(editMetadataOwner.trim() ? { owner: editMetadataOwner.trim() } : {}),
          ...(editMetadataTag.trim() ? { tag: editMetadataTag.trim() } : {}),
        },
        parseJsonObject(editMetadataJson, 'edit_metadata_json'),
      )
      await updateAssistant(editAssistantId, {
        graph_id: editGraphId.trim() || undefined,
        name: editName.trim() || undefined,
        description: editDescription.trim() || undefined,
        context,
        config,
        metadata,
      })
      await loadAssistants()
      pushToast('success', `更新成功：${editAssistantId}`)
    } catch (error) {
      const msg = error instanceof Error ? error.message : String(error)
      pushToast('error', `更新失败：${msg}`)
    } finally {
      setUpdatePending(false)
    }
  }

  const handleDelete = async () => {
    if (!editAssistantId) {
      pushToast('error', '删除失败：请先选择要删除的 assistant')
      return
    }
    setDeletePending(true)
    try {
      const deletingId = editAssistantId
      await deleteAssistant(editAssistantId, { delete_threads: deleteThreads })
      setEditAssistantId('')
      setEditGraphId('')
      setEditName('')
      setEditDescription('')
      setEditModelProvider('')
      setEditSystemPrompt('')
      setEditEnableLocalTools(true)
      setEditEnableLocalMcp(false)
      setEditMcpServers('')
      setEditRecursionLimit('')
      setEditMetadataOwner('')
      setEditMetadataTag('')
      setEditContextJson('')
      setEditConfigJson('')
      setEditMetadataJson('')
      setDeleteConfirmText('')
      await loadAssistants()
      pushToast('success', `删除成功：${deletingId}`)
    } catch (error) {
      const msg = error instanceof Error ? error.message : String(error)
      pushToast('error', `删除失败：${msg}`)
    } finally {
      setDeletePending(false)
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
        <strong>Assistant 管理（核心 CRUD）</strong>
        {onBack ? (
          <button type="button" onClick={onBack}>
            返回对话页
          </button>
        ) : null}
      </header>

      <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 12, alignItems: 'start' }}>
        <section style={{ background: '#fff', border: '1px solid #e5e7eb', borderRadius: 12, padding: 16, display: 'grid', gap: 10 }}>
          <h2 style={{ margin: 0 }}>创建 Assistant</h2>
          <label style={{ display: 'grid', gap: 4 }}>
            <span>graph_id *</span>
            <select value={graphId} onChange={(e) => setGraphId(e.target.value)}>
              {graphOptions.map((item) => (
                <option key={item} value={item}>
                  {item}
                </option>
              ))}
              {graphOptions.length === 0 ? <option value={graphId || 'agent'}>{graphId || 'agent'}</option> : null}
            </select>
          </label>
          <div style={{ fontSize: 12, color: '#6b7280' }}>graph 列表状态：{graphLoading ? '加载中...' : '已就绪'}</div>
          <label style={{ display: 'grid', gap: 4 }}>
            <span>graph_id (manual)</span>
            <input value={graphId} onChange={(e) => setGraphId(e.target.value)} placeholder="例如 agent" />
          </label>
          <label style={{ display: 'grid', gap: 4 }}>
            <span>name</span>
            <input value={name} onChange={(e) => setName(e.target.value)} placeholder="例如 team-helper" />
          </label>
          <label style={{ display: 'grid', gap: 4 }}>
            <span>description</span>
            <textarea value={description} onChange={(e) => setDescription(e.target.value)} rows={3} placeholder="可选描述" />
          </label>
          <label style={{ display: 'grid', gap: 4 }}>
            <span>model_provider</span>
            <input value={modelProvider} onChange={(e) => setModelProvider(e.target.value)} placeholder="例如 glm4/openai" />
          </label>
          <label style={{ display: 'grid', gap: 4 }}>
            <span>system_prompt</span>
            <textarea value={systemPrompt} onChange={(e) => setSystemPrompt(e.target.value)} rows={2} />
          </label>
          <label style={{ display: 'flex', gap: 8, alignItems: 'center' }}>
            <input type="checkbox" checked={enableLocalTools} onChange={(e) => setEnableLocalTools(e.target.checked)} />
            启用本地工具
          </label>
          <label style={{ display: 'flex', gap: 8, alignItems: 'center' }}>
            <input type="checkbox" checked={enableLocalMcp} onChange={(e) => setEnableLocalMcp(e.target.checked)} />
            启用本地 MCP
          </label>
          <label style={{ display: 'grid', gap: 4 }}>
            <span>mcp_servers（逗号分隔）</span>
            <input value={mcpServers} onChange={(e) => setMcpServers(e.target.value)} placeholder="server-a,server-b" />
          </label>
          <label style={{ display: 'grid', gap: 4 }}>
            <span>recursion_limit</span>
            <input value={recursionLimit} onChange={(e) => setRecursionLimit(e.target.value)} placeholder="例如 60" />
          </label>
          <label style={{ display: 'grid', gap: 4 }}>
            <span>metadata owner</span>
            <input value={metadataOwner} onChange={(e) => setMetadataOwner(e.target.value)} placeholder="例如 team-a" />
          </label>
          <label style={{ display: 'grid', gap: 4 }}>
            <span>metadata tag</span>
            <input value={metadataTag} onChange={(e) => setMetadataTag(e.target.value)} placeholder="例如 experiment" />
          </label>
          <label style={{ display: 'grid', gap: 4 }}>
            <span>context_json（模型/MCP/提示词等）</span>
            <textarea
              value={contextJson}
              onChange={(e) => setContextJson(e.target.value)}
              rows={3}
              placeholder='例如 {"model_provider":"glm4","system_prompt":"你是严谨助手"}'
            />
          </label>
          <label style={{ display: 'grid', gap: 4 }}>
            <span>config_json（执行配置）</span>
            <textarea value={configJson} onChange={(e) => setConfigJson(e.target.value)} rows={2} placeholder='例如 {"recursion_limit":60}' />
          </label>
          <label style={{ display: 'grid', gap: 4 }}>
            <span>metadata_json（业务标记）</span>
            <textarea value={metadataJson} onChange={(e) => setMetadataJson(e.target.value)} rows={2} placeholder='例如 {"owner":"demo"}' />
          </label>
          <button type="button" onClick={() => void handleCreate()} disabled={createPending}>
            {createPending ? '创建中...' : '创建'}
          </button>
        </section>

        <section style={{ background: '#fff', border: '1px solid #e5e7eb', borderRadius: 12, padding: 16, display: 'grid', gap: 10 }}>
          <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
            <h2 style={{ margin: 0 }}>Assistant 列表</h2>
            <button type="button" onClick={() => void loadAssistants(true)} disabled={loading || createPending || updatePending || deletePending}>
              {loading ? '刷新中...' : '刷新'}
            </button>
          </div>

          <div style={{ display: 'grid', gap: 8, maxHeight: 320, overflow: 'auto' }}>
            {items.map((item) => {
              const isActive = editAssistantId === item.assistant_id
              return (
                <button
                  key={item.assistant_id}
                  type="button"
                  onClick={() => handleSelectForEdit(item)}
                  style={{
                    textAlign: 'left',
                    border: isActive ? '1px solid #6366f1' : '1px solid #e5e7eb',
                    borderRadius: 10,
                    padding: 10,
                    background: isActive ? '#eef2ff' : '#f8fafc',
                  }}
                >
                  <div style={{ fontWeight: 600 }}>{item.assistant_id}</div>
                  <div style={{ fontSize: 12, color: '#6b7280' }}>graph_id: {item.graph_id ?? 'N/A'}</div>
                  <div style={{ fontSize: 12, color: '#6b7280' }}>name: {item.name ?? 'N/A'}</div>
                </button>
              )
            })}
            {items.length === 0 ? <p style={{ margin: 0 }}>暂无 assistant</p> : null}
          </div>

          <h3 style={{ margin: '6px 0 0 0' }}>更新 / 删除</h3>
          <label style={{ display: 'grid', gap: 4 }}>
            <span>assistant_id（选中后自动填充）</span>
            <input value={editAssistantId} onChange={(e) => setEditAssistantId(e.target.value)} />
          </label>
          <label style={{ display: 'grid', gap: 4 }}>
            <span>graph_id</span>
            <input value={editGraphId} onChange={(e) => setEditGraphId(e.target.value)} />
          </label>
          <label style={{ display: 'grid', gap: 4 }}>
            <span>name</span>
            <input value={editName} onChange={(e) => setEditName(e.target.value)} />
          </label>
          <label style={{ display: 'grid', gap: 4 }}>
            <span>description</span>
            <textarea value={editDescription} onChange={(e) => setEditDescription(e.target.value)} rows={2} />
          </label>
          <label style={{ display: 'grid', gap: 4 }}>
            <span>model_provider</span>
            <input value={editModelProvider} onChange={(e) => setEditModelProvider(e.target.value)} placeholder="例如 glm4/openai" />
          </label>
          <label style={{ display: 'grid', gap: 4 }}>
            <span>system_prompt</span>
            <textarea value={editSystemPrompt} onChange={(e) => setEditSystemPrompt(e.target.value)} rows={2} />
          </label>
          <label style={{ display: 'flex', gap: 8, alignItems: 'center' }}>
            <input type="checkbox" checked={editEnableLocalTools} onChange={(e) => setEditEnableLocalTools(e.target.checked)} />
            启用本地工具
          </label>
          <label style={{ display: 'flex', gap: 8, alignItems: 'center' }}>
            <input type="checkbox" checked={editEnableLocalMcp} onChange={(e) => setEditEnableLocalMcp(e.target.checked)} />
            启用本地 MCP
          </label>
          <label style={{ display: 'grid', gap: 4 }}>
            <span>mcp_servers（逗号分隔）</span>
            <input value={editMcpServers} onChange={(e) => setEditMcpServers(e.target.value)} placeholder="server-a,server-b" />
          </label>
          <label style={{ display: 'grid', gap: 4 }}>
            <span>recursion_limit</span>
            <input value={editRecursionLimit} onChange={(e) => setEditRecursionLimit(e.target.value)} placeholder="例如 60" />
          </label>
          <label style={{ display: 'grid', gap: 4 }}>
            <span>metadata owner</span>
            <input value={editMetadataOwner} onChange={(e) => setEditMetadataOwner(e.target.value)} placeholder="例如 team-a" />
          </label>
          <label style={{ display: 'grid', gap: 4 }}>
            <span>metadata tag</span>
            <input value={editMetadataTag} onChange={(e) => setEditMetadataTag(e.target.value)} placeholder="例如 experiment" />
          </label>
          <label style={{ display: 'grid', gap: 4 }}>
            <span>context_json（可选）</span>
            <textarea value={editContextJson} onChange={(e) => setEditContextJson(e.target.value)} rows={2} placeholder='例如 {"model_provider":"openai"}' />
          </label>
          <label style={{ display: 'grid', gap: 4 }}>
            <span>config_json（可选）</span>
            <textarea value={editConfigJson} onChange={(e) => setEditConfigJson(e.target.value)} rows={2} placeholder='例如 {"recursion_limit":40}' />
          </label>
          <label style={{ display: 'grid', gap: 4 }}>
            <span>metadata_json（可选）</span>
            <textarea value={editMetadataJson} onChange={(e) => setEditMetadataJson(e.target.value)} rows={2} placeholder='例如 {"env":"dev"}' />
          </label>
          <label style={{ display: 'flex', gap: 8, alignItems: 'center' }}>
            <input type="checkbox" checked={deleteThreads} onChange={(e) => setDeleteThreads(e.target.checked)} />
            删除时同时删除关联 threads
          </label>
          <label style={{ display: 'grid', gap: 4 }}>
            <span>删除确认（输入 assistant_id）</span>
            <input value={deleteConfirmText} onChange={(e) => setDeleteConfirmText(e.target.value)} placeholder={editAssistantId || '先选择 assistant'} />
          </label>
          <div style={{ display: 'flex', gap: 8 }}>
            <button type="button" onClick={() => void handleUpdate()} disabled={updatePending}>
              {updatePending ? '更新中...' : '更新'}
            </button>
            <button type="button" onClick={() => void handleDelete()} disabled={deletePending || !canDelete}>
              {deletePending ? '删除中...' : '删除'}
            </button>
          </div>
          {!canDelete && editAssistantId ? (
            <p style={{ margin: 0, fontSize: 12, color: '#6b7280' }}>请先输入完整 assistant_id 以确认删除</p>
          ) : null}
        </section>
      </div>

      <div style={{ position: 'fixed', top: 12, right: 12, display: 'grid', gap: 8, zIndex: 50, maxWidth: 360 }}>
        {toasts.map((item) => (
          <div
            key={item.id}
            style={{
              color: item.tone === 'success' ? '#166534' : '#b91c1c',
              background: item.tone === 'success' ? '#ecfdf3' : '#fef2f2',
              border: `1px solid ${item.tone === 'success' ? '#86efac' : '#fecaca'}`,
              borderRadius: 8,
              padding: '8px 10px',
              boxShadow: '0 6px 16px rgba(15, 23, 42, 0.12)',
              display: 'flex',
              justifyContent: 'space-between',
              alignItems: 'center',
              gap: 10,
            }}
          >
            <span>
              {item.tone === 'success' ? 'Success: ' : 'Error: '}
              {item.text}
            </span>
            <button type="button" onClick={() => removeToast(item.id)} style={{ border: 'none', background: 'transparent', cursor: 'pointer' }}>
              ×
            </button>
          </div>
        ))}
      </div>
    </main>
  )
}
