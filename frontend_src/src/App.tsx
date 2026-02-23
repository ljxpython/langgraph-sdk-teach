import { type CSSProperties, useState } from 'react'

import { AssistantManagePage } from './pages/AssistantManagePage'
import { ObserverPage } from './pages/ObserverPage'

export default function App() {
  const [page, setPage] = useState<'observer' | 'assistants'>('observer')
  const [collapsed, setCollapsed] = useState(false)

  const sidebarWidth = collapsed ? 44 : 220

  const navButtonStyle = (active: boolean): CSSProperties => ({
    textAlign: 'left',
    borderRadius: 8,
    border: active ? '1px solid #60a5fa' : '1px solid rgba(148,163,184,0.35)',
    background: active ? 'rgba(96,165,250,0.2)' : 'rgba(15,23,42,0.2)',
    color: '#e2e8f0',
    padding: '8px 10px',
    cursor: 'pointer',
    width: '100%',
    overflow: 'hidden',
    whiteSpace: 'nowrap',
    textOverflow: 'ellipsis',
  })

  return (
    <div style={{ minHeight: '100vh', display: 'grid', gridTemplateColumns: `${sidebarWidth}px 1fr`, background: '#eef2f7' }}>
      <aside
        style={{
          borderRight: '1px solid #d1d5db',
          background: 'linear-gradient(180deg, #0f172a 0%, #1e293b 100%)',
          color: '#e2e8f0',
          padding: collapsed ? 6 : 14,
          display: 'grid',
          alignContent: 'start',
          gap: 12,
          transition: 'all 180ms ease',
        }}
      >
        {collapsed ? (
          <button
            type="button"
            onClick={() => setCollapsed((prev) => !prev)}
            style={{
              borderRadius: 8,
              border: '1px solid rgba(148,163,184,0.4)',
              background: 'rgba(15,23,42,0.2)',
              color: '#e2e8f0',
              padding: '6px 0',
              cursor: 'pointer',
              width: '100%',
            }}
            title="展开侧栏"
          >
            »
          </button>
        ) : (
          <>
            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', gap: 8 }}>
              <div style={{ padding: '6px 8px', borderRadius: 8, background: 'rgba(255,255,255,0.08)', width: '100%' }}>
                <div style={{ fontWeight: 700 }}>AI Platform</div>
                <div style={{ fontSize: 12, opacity: 0.85 }}>Learning Workspace</div>
              </div>
              <button
                type="button"
                onClick={() => setCollapsed((prev) => !prev)}
                style={{
                  borderRadius: 8,
                  border: '1px solid rgba(148,163,184,0.4)',
                  background: 'rgba(15,23,42,0.2)',
                  color: '#e2e8f0',
                  padding: '6px 8px',
                  cursor: 'pointer',
                  flexShrink: 0,
                }}
                title="折叠侧栏"
              >
                «
              </button>
            </div>

            <button
              type="button"
              onClick={() => setPage('observer')}
              style={navButtonStyle(page === 'observer')}
              title="通用对话工作台"
            >
              通用对话工作台
            </button>

            <button
              type="button"
              onClick={() => setPage('assistants')}
              style={{
                ...navButtonStyle(page === 'assistants'),
                border: page === 'assistants' ? '1px solid #34d399' : '1px solid rgba(148,163,184,0.35)',
                background: page === 'assistants' ? 'rgba(52,211,153,0.18)' : 'rgba(15,23,42,0.2)',
              }}
              title="Assistant 管理"
            >
              Assistant 管理
            </button>
          </>
        )}
      </aside>

      <section style={{ minWidth: 0 }}>{page === 'observer' ? <ObserverPage /> : <AssistantManagePage />}</section>
    </div>
  )
}
