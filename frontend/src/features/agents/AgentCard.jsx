const TYPE_COLORS = {
  classifier: { bg: 'rgba(99,102,241,0.12)', color: '#818CF8', glow: 'rgba(99,102,241,0.2)' },
  extractor: { bg: 'rgba(16,185,129,0.12)', color: '#10B981', glow: 'rgba(16,185,129,0.2)' },
  summarizer: { bg: 'rgba(245,158,11,0.12)', color: '#F59E0B', glow: 'rgba(245,158,11,0.2)' },
  generator: { bg: 'rgba(139,92,246,0.12)', color: '#A78BFA', glow: 'rgba(139,92,246,0.2)' },
  router: { bg: 'rgba(236,72,153,0.12)', color: '#EC4899', glow: 'rgba(236,72,153,0.2)' },
  loader: { bg: 'rgba(96,165,250,0.12)', color: '#60A5FA', glow: 'rgba(96,165,250,0.2)' },
  storage: { bg: 'rgba(52,211,153,0.12)', color: '#34D399', glow: 'rgba(52,211,153,0.2)' },
  validator: { bg: 'rgba(251,146,60,0.12)', color: '#FB923C', glow: 'rgba(251,146,60,0.2)' },
  analyzer: { bg: 'rgba(244,114,182,0.12)', color: '#F472B6', glow: 'rgba(244,114,182,0.2)' },
  translator: { bg: 'rgba(56,189,248,0.12)', color: '#38BDF8', glow: 'rgba(56,189,248,0.2)' },
  reviewer: { bg: 'rgba(251,191,36,0.12)', color: '#FBBF24', glow: 'rgba(251,191,36,0.2)' },
  mapper: { bg: 'rgba(167,139,250,0.12)', color: '#A78BFA', glow: 'rgba(167,139,250,0.2)' },
  transformer: { bg: 'rgba(74,222,128,0.12)', color: '#4ADE80', glow: 'rgba(74,222,128,0.2)' },
  monitor: { bg: 'rgba(248,113,113,0.12)', color: '#F87171', glow: 'rgba(248,113,113,0.2)' },
  checker: { bg: 'rgba(45,212,191,0.12)', color: '#2DD4BF', glow: 'rgba(45,212,191,0.2)' },
  ranker: { bg: 'rgba(253,186,116,0.12)', color: '#FDBA74', glow: 'rgba(253,186,116,0.2)' },
  detector: { bg: 'rgba(196,181,253,0.12)', color: '#C4B5FD', glow: 'rgba(196,181,253,0.2)' },
  linker: { bg: 'rgba(134,239,172,0.12)', color: '#86EFAC', glow: 'rgba(134,239,172,0.2)' },
  collector: { bg: 'rgba(147,197,253,0.12)', color: '#93C5FD', glow: 'rgba(147,197,253,0.2)' },
  assurer: { bg: 'rgba(253,224,71,0.12)', color: '#FDE047', glow: 'rgba(253,224,71,0.2)' },
}

const TYPE_ICONS = {
  classifier: 'M9 5H7a2 2 0 00-2 2v12a2 2 0 002 2h10a2 2 0 002-2V7a2 2 0 00-2-2h-2M9 5a2 2 0 002 2h2a2 2 0 002-2M9 5a2 2 0 012-2h2a2 2 0 012 2',
  extractor: 'M19.5 14.25v-2.625a3.375 3.375 0 00-3.375-3.375h-1.5A1.125 1.125 0 0113.5 7.125v-1.5a3.375 3.375 0 00-3.375-3.375H8.25m5.231 13.481L15 17.25m-4.5-15H5.625c-.621 0-1.125.504-1.125 1.125v16.5c0 .621.504 1.125 1.125 1.125h12.75c.621 0 1.125-.504 1.125-1.125V11.25a9 9 0 00-9-9zm3.75 11.625a2.625 2.625 0 11-5.25 0 2.625 2.625 0 015.25 0z',
  summarizer: 'M3.75 6.75h16.5M3.75 12h16.5m-16.5 5.25H12',
  generator: 'M9.813 15.904L9 18.75l-.813-2.846a4.5 4.5 0 00-3.09-3.09L2.25 12l2.846-.813a4.5 4.5 0 003.09-3.09L9 5.25l.813 2.846a4.5 4.5 0 003.09 3.09L15.75 12l-2.846.813a4.5 4.5 0 00-3.09 3.09zM18.259 8.715L18 9.75l-.259-1.035a3.375 3.375 0 00-2.455-2.456L14.25 6l1.036-.259a3.375 3.375 0 002.455-2.456L18 2.25l.259 1.035a3.375 3.375 0 002.455 2.456L21.75 6l-1.036.259a3.375 3.375 0 00-2.455 2.456z',
  router: 'M7.5 21L3 16.5m0 0L7.5 12M3 16.5h13.5m0-13.5L21 7.5m0 0L16.5 12M21 7.5H7.5',
  loader: 'M3 16.5v2.25A2.25 2.25 0 005.25 21h13.5A2.25 2.25 0 0021 18.75V16.5m-13.5-9L12 3m0 0l4.5 4.5M12 3v13.5',
  storage: 'M20.25 6.375c0 2.278-3.694 4.125-8.25 4.125S3.75 8.653 3.75 6.375m16.5 0c0-2.278-3.694-4.125-8.25-4.125S3.75 4.097 3.75 6.375m16.5 0v11.25c0 2.278-3.694 4.125-8.25 4.125s-8.25-1.847-8.25-4.125V6.375',
  validator: 'M9 12.75L11.25 15 15 9.75M21 12a9 9 0 11-18 0 9 9 0 0118 0z',
  analyzer: 'M3 13.125C3 12.504 3.504 12 4.125 12h2.25c.621 0 1.125.504 1.125 1.125v6.75C7.5 20.496 6.996 21 6.375 21h-2.25A1.125 1.125 0 013 19.875v-6.75zM9.75 8.625c0-.621.504-1.125 1.125-1.125h2.25c.621 0 1.125.504 1.125 1.125v11.25c0 .621-.504 1.125-1.125 1.125h-2.25a1.125 1.125 0 01-1.125-1.125V8.625zM16.5 4.125c0-.621.504-1.125 1.125-1.125h2.25C20.496 3 21 3.504 21 4.125v15.75c0 .621-.504 1.125-1.125 1.125h-2.25a1.125 1.125 0 01-1.125-1.125V4.125z',
  translator: 'M10.5 21l5.25-11.25L21 21m-9-3h7.5M3 5.621a48.474 48.474 0 016-.371m0 0c1.12 0 2.233.038 3.334.114M9 5.25V3m3.334 2.364C11.176 10.658 7.69 15.08 3 17.502m9.334-12.138c.896.061 1.785.147 2.666.257m-4.589 8.495a18.023 18.023 0 01-3.827-5.802',
  reviewer: 'M2.036 12.322a1.012 1.012 0 010-.639C3.423 7.51 7.36 4.5 12 4.5c4.638 0 8.573 3.007 9.963 7.178.07.207.07.431 0 .639C20.577 16.49 16.64 19.5 12 19.5c-4.638 0-8.573-3.007-9.963-7.178zM15 12a3 3 0 11-6 0 3 3 0 016 0z',
  mapper: 'M9 6.75V15m0-15a2.25 2.25 0 100 4.5 2.25 2.25 0 000-4.5zM3 11.25a2.25 2.25 0 100 4.5 2.25 2.25 0 000-4.5zm12 0a2.25 2.25 0 100 4.5 2.25 2.25 0 000-4.5z',
  transformer: 'M7.5 21L3 16.5m0 0L7.5 12M3 16.5h13.5m0-13.5L21 7.5m0 0L16.5 12M21 7.5H7.5',
  monitor: 'M12 9v3.75m9-.75a9 9 0 11-18 0 9 9 0 0118 0zm-9 3.75h.008v.008H12v-.008z',
  checker: 'M9 12.75L11.25 15 15 9.75m-3-7.036A11.959 11.959 0 013.598 6 11.99 11.99 0 003 9.749c0 5.592 3.824 10.29 9 11.623 5.176-1.332 9-6.03 9-11.622 0-1.31-.21-2.571-.598-3.751h-.152c-3.196 0-6.1-1.248-8.25-3.285z',
  ranker: 'M3 4.5h14.25M3 9h9.75M3 13.5h5.25m5.25-.75L17.25 9m0 0L21 12.75M17.25 9v12',
  detector: 'M21 21l-5.197-5.197m0 0A7.5 7.5 0 105.196 5.196a7.5 7.5 0 0010.607 10.607z',
  linker: 'M13.19 8.688a4.5 4.5 0 011.242 7.244l-4.5 4.5a4.5 4.5 0 01-6.364-6.364l1.757-1.757m13.35-.622l1.757-1.757a4.5 4.5 0 00-6.364-6.364l-4.5 4.5a4.5 4.5 0 001.242 7.244',
  collector: 'M20.25 7.5l-.625 10.632a2.25 2.25 0 01-2.247 2.118H6.622a2.25 2.25 0 01-2.247-2.118L3.75 7.5m8.25 3v6.75m0 0l-3-3m3 3l3-3M3.375 7.5h17.25c.621 0 1.125-.504 1.125-1.125v-1.5c0-.621-.504-1.125-1.125-1.125H3.375c-.621 0-1.125.504-1.125 1.125v1.5c0 .621.504 1.125 1.125 1.125z',
  assurer: 'M11.48 3.499a.562.562 0 011.04 0l2.125 5.111a.563.563 0 00.475.345l5.518.442c.499.04.701.663.321.988l-4.204 3.602a.563.563 0 00-.182.557l1.285 5.385a.562.562 0 01-.84.61l-4.725-2.885a.563.563 0 00-.586 0L6.982 20.54a.562.562 0 01-.84-.61l1.285-5.386a.562.562 0 00-.182-.557l-4.204-3.602a.563.563 0 01.321-.988l5.518-.442a.563.563 0 00.475-.345L11.48 3.5z',
}

import { memo } from 'react'

export default memo(function AgentCard({ agent, selected, onClick }) {
  const tc = TYPE_COLORS[agent.type] || TYPE_COLORS.classifier
  const iconPath = TYPE_ICONS[agent.type] || TYPE_ICONS.classifier

  return (
    <div
      onClick={() => onClick && onClick(agent)}
      role="button"
      tabIndex={0}
      onKeyDown={(e) => e.key === 'Enter' && onClick?.(agent)}
      aria-label={`Agente ${agent.name}`}
      style={{
        background: '#FFFFFF',
        border: `1px solid ${selected ? 'rgba(37,99,235,0.4)' : '#E5E7EB'}`,
        borderRadius: 12, padding: 20, cursor: 'pointer',
        transition: 'all 0.2s ease',
        boxShadow: selected ? `0 0 20px ${tc.glow}` : 'none',
      }}
      onMouseEnter={(e) => {
        if (!selected) e.currentTarget.style.boxShadow = `0 0 16px ${tc.glow}`
        e.currentTarget.style.borderColor = 'rgba(37,99,235,0.3)'
      }}
      onMouseLeave={(e) => {
        if (!selected) e.currentTarget.style.boxShadow = 'none'
        e.currentTarget.style.borderColor = selected ? 'rgba(37,99,235,0.4)' : '#E5E7EB'
      }}
    >
      {/* Icon */}
      <div style={{
        width: 48, height: 48, borderRadius: 12, background: tc.bg,
        display: 'flex', alignItems: 'center', justifyContent: 'center', marginBottom: 14,
      }}>
        <svg width="24" height="24" viewBox="0 0 24 24" fill="none"
          stroke={tc.color} strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round">
          <path d={iconPath} />
        </svg>
      </div>

      {/* Name + type */}
      <div style={{ display: 'flex', alignItems: 'center', gap: 8, marginBottom: 8 }}>
        <span style={{ fontSize: 15, fontWeight: 600, color: '#111827' }}>{agent.name}</span>
        <span style={{
          fontSize: 11, padding: '2px 8px', borderRadius: 6,
          background: tc.bg, color: tc.color, fontWeight: 500,
        }}>{agent.type}</span>
      </div>

      {/* Description */}
      <p style={{
        fontSize: 13, color: '#9CA3AF', lineHeight: '1.5', margin: '0 0 12px',
        display: '-webkit-box', WebkitLineClamp: 2, WebkitBoxOrient: 'vertical', overflow: 'hidden',
      }}>
        {agent.description}
      </p>

      {/* Footer: status + tools */}
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
        <div style={{ display: 'flex', alignItems: 'center', gap: 6 }}>
          <span style={{
            width: 8, height: 8, borderRadius: '50%',
            background: agent.status === 'active' ? '#10B981' : '#F59E0B',
          }} />
          <span style={{ fontSize: 12, color: agent.status === 'active' ? '#10B981' : '#F59E0B' }}>
            {agent.status === 'active' ? 'Activo' : 'Pausado'}
          </span>
        </div>
        {agent.tools && (
          <div style={{ display: 'flex', gap: 4, flexWrap: 'wrap' }}>
            {agent.tools.slice(0, 3).map((tool) => (
              <span key={tool} style={{
                fontSize: 10, padding: '2px 6px', borderRadius: 4,
                background: '#F3F4F6', color: '#6B7280',
              }}>{tool}</span>
            ))}
            {agent.tools.length > 3 && (
              <span style={{ fontSize: 10, color: '#9CA3AF' }}>+{agent.tools.length - 3}</span>
            )}
          </div>
        )}
      </div>
    </div>
  )
})
