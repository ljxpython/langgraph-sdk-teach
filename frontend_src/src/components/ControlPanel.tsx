type AssistantItem = {
  assistant_id: string
  graph_id: string | null
  name: string | null
}

type ControlPanelProps = {
  collapsed: boolean
  on_toggle_collapsed: () => void
  graph_id: string
  graph_id_options: string[]
  on_graph_id_change: (value: string) => void
  assistant_id: string
  assistant_options: AssistantItem[]
  on_assistant_id_change: (value: string) => void
  on_refresh_assistants: () => Promise<void>
  system_prompt: string
  on_system_prompt_change: (value: string) => void
  use_langgraph_sampling_defaults: boolean
  on_use_langgraph_sampling_defaults_change: (value: boolean) => void
  temperature: number
  on_temperature_change: (value: number) => void
  top_p: number
  on_top_p_change: (value: number) => void
  max_tokens: number
  on_max_tokens_change: (value: number) => void
  model_provider: string
  model_provider_options: string[]
  on_model_provider_change: (value: string) => void
  enable_local_tools: boolean
  on_enable_local_tools_change: (value: boolean) => void
  enable_local_mcp: boolean
  on_enable_local_mcp_change: (value: boolean) => void
  mcp_servers: string
  mcp_server_options: string[]
  on_mcp_servers_change: (value: string) => void
  custom_tools: string
  on_custom_tools_change: (value: string) => void
}

export function ControlPanel({
  collapsed,
  on_toggle_collapsed,
  graph_id,
  graph_id_options,
  on_graph_id_change,
  assistant_id,
  assistant_options,
  on_assistant_id_change,
  on_refresh_assistants,
  system_prompt,
  on_system_prompt_change,
  use_langgraph_sampling_defaults,
  on_use_langgraph_sampling_defaults_change,
  temperature,
  on_temperature_change,
  top_p,
  on_top_p_change,
  max_tokens,
  on_max_tokens_change,
  model_provider,
  model_provider_options,
  on_model_provider_change,
  enable_local_tools,
  on_enable_local_tools_change,
  enable_local_mcp,
  on_enable_local_mcp_change,
  mcp_servers,
  mcp_server_options,
  on_mcp_servers_change,
  custom_tools,
  on_custom_tools_change,
}: ControlPanelProps) {
  const has_selected_assistant = assistant_options.some((item) => item.assistant_id === assistant_id)

  return (
    <section style={{ background: '#fff', border: '1px solid #e5e7eb', borderRadius: 12, padding: 12 }}>
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 10 }}>
        <h2 style={{ margin: 0 }}>{collapsed ? 'Ctl' : 'Controls'}</h2>
        <button type="button" onClick={on_toggle_collapsed} title={collapsed ? '展开 Controls' : '折叠 Controls'}>
          {collapsed ? '«' : '»'}
        </button>
      </div>
      {collapsed ? <p style={{ margin: 0, fontSize: 12, color: '#6b7280' }}>Controls 已折叠</p> : null}
      <div style={{ display: collapsed ? 'none' : 'grid', gap: 10 }}>
        <label style={{ display: 'grid', gap: 4 }}>
          <span>graph_id</span>
          <select value={graph_id} onChange={(e) => on_graph_id_change(e.target.value)}>
            <option value="">(all)</option>
            {graph_id_options.map((item) => (
              <option key={item} value={item}>
                {item}
              </option>
            ))}
          </select>
        </label>
        <label style={{ display: 'grid', gap: 4 }}>
          <span>assistant_id</span>
          <select value={assistant_id} onChange={(e) => on_assistant_id_change(e.target.value)}>
            {assistant_options.map((item) => (
              <option key={item.assistant_id} value={item.assistant_id}>
                {item.assistant_id}
                {item.graph_id ? ` · graph_id=${item.graph_id}` : ''}
                {item.name ? ` · name=${item.name}` : ''}
              </option>
            ))}
            {!has_selected_assistant ? (
              <option value={assistant_id}>{assistant_id} · (manual)</option>
            ) : null}
          </select>
        </label>
        <button type="button" onClick={() => void on_refresh_assistants()}>
          刷新 assistant/graph 列表
        </button>
        <label style={{ display: 'grid', gap: 4 }}>
          <span>assistant_id (manual)</span>
          <input value={assistant_id} onChange={(e) => on_assistant_id_change(e.target.value)} />
        </label>
        <label style={{ display: 'grid', gap: 4 }}>
          <span>system_prompt</span>
          <textarea value={system_prompt} onChange={(e) => on_system_prompt_change(e.target.value)} rows={3} />
        </label>
        <label style={{ display: 'grid', gap: 4 }}>
          <span>model_provider</span>
          <select value={model_provider} onChange={(e) => on_model_provider_change(e.target.value)}>
            {model_provider_options.map((item) => (
              <option key={item} value={item}>
                {item}
              </option>
            ))}
          </select>
        </label>
        <label style={{ display: 'grid', gap: 4 }}>
          <span>model_provider (manual)</span>
          <input value={model_provider} onChange={(e) => on_model_provider_change(e.target.value)} />
        </label>
        <label style={{ display: 'flex', gap: 8, alignItems: 'center' }}>
          <input
            type="checkbox"
            checked={use_langgraph_sampling_defaults}
            onChange={(e) => on_use_langgraph_sampling_defaults_change(e.target.checked)}
          />
          使用 LangGraph 默认采样参数
        </label>
        <label style={{ display: 'grid', gap: 4 }}>
          <span>temperature: {temperature.toFixed(2)}</span>
          <input
            type="range"
            min={0}
            max={1.5}
            step={0.1}
            value={temperature}
            disabled={use_langgraph_sampling_defaults}
            onChange={(e) => on_temperature_change(Number(e.target.value))}
          />
        </label>
        <label style={{ display: 'grid', gap: 4 }}>
          <span>top_p: {top_p.toFixed(2)}</span>
          <input
            type="range"
            min={0}
            max={1}
            step={0.05}
            value={top_p}
            disabled={use_langgraph_sampling_defaults}
            onChange={(e) => on_top_p_change(Number(e.target.value))}
          />
        </label>
        <label style={{ display: 'grid', gap: 4 }}>
          <span>max_tokens</span>
          <input
            type="number"
            min={16}
            max={4096}
            step={16}
            value={max_tokens}
            disabled={use_langgraph_sampling_defaults}
            onChange={(e) => on_max_tokens_change(Number(e.target.value) || 256)}
          />
        </label>
        <label style={{ display: 'flex', gap: 8, alignItems: 'center' }}>
          <input type="checkbox" checked={enable_local_tools} onChange={(e) => on_enable_local_tools_change(e.target.checked)} />
          启用本地 tools
        </label>
        <label style={{ display: 'flex', gap: 8, alignItems: 'center' }}>
          <input type="checkbox" checked={enable_local_mcp} onChange={(e) => on_enable_local_mcp_change(e.target.checked)} />
          启用本地 MCP
        </label>
        <label style={{ display: 'grid', gap: 4 }}>
          <span>mcp_servers</span>
          <select value={mcp_servers} onChange={(e) => on_mcp_servers_change(e.target.value)}>
            <option value="">(none)</option>
            {mcp_server_options.map((item) => (
              <option key={item} value={item}>
                {item}
              </option>
            ))}
          </select>
        </label>
        <label style={{ display: 'grid', gap: 4 }}>
          <span>mcp_servers (manual, comma-separated)</span>
          <input value={mcp_servers} onChange={(e) => on_mcp_servers_change(e.target.value)} placeholder="filesystem,github" />
        </label>
        <label style={{ display: 'grid', gap: 4 }}>
          <span>custom_tools (comma-separated)</span>
          <input value={custom_tools} onChange={(e) => on_custom_tools_change(e.target.value)} placeholder="search_web,get_weather" />
        </label>
      </div>
    </section>
  )
}
