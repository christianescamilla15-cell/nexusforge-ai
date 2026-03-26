const TYPE_COLORS = {
  classifier: { bg: 'rgba(99,102,241,0.12)', color: '#818CF8', glow: 'rgba(99,102,241,0.2)' },
  extractor: { bg: 'rgba(16,185,129,0.12)', color: '#10B981', glow: 'rgba(16,185,129,0.2)' },
  summarizer: { bg: 'rgba(245,158,11,0.12)', color: '#F59E0B', glow: 'rgba(245,158,11,0.2)' },
  generator: { bg: 'rgba(139,92,246,0.12)', color: '#A78BFA', glow: 'rgba(139,92,246,0.2)' },
  router: { bg: 'rgba(236,72,153,0.12)', color: '#EC4899', glow: 'rgba(236,72,153,0.2)' },
  loader: { bg: 'rgba(96,165,250,0.12)', color: '#60A5FA', glow: 'rgba(96,165,250,0.2)' },
  storage: { bg: 'rgba(52,211,153,0.12)', color: '#34D399', glow: 'rgba(52,211,153,0.2)' },
  validator: { bg: 'rgba(251,146,60,0.12)', color: '#FB923C', glow: 'rgba(251,146,60,0.2)' },
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
}

export default function AgentCard({ agent, selected, onClick }) {
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
        background: '#161E2E',
        border: `1px solid ${selected ? 'rgba(99,102,241,0.4)' : 'rgba(255,255,255,0.06)'}`,
        borderRadius: 12, padding: 20, cursor: 'pointer',
        transition: 'all 0.2s ease',
        boxShadow: selected ? `0 0 20px ${tc.glow}` : 'none',
      }}
      onMouseEnter={(e) => {
        if (!selected) e.currentTarget.style.boxShadow = `0 0 16px ${tc.glow}`
        e.currentTarget.style.borderColor = 'rgba(99,102,241,0.3)'
      }}
      onMouseLeave={(e) => {
        if (!selected) e.currentTarget.style.boxShadow = 'none'
        e.currentTarget.style.borderColor = selected ? 'rgba(99,102,241,0.4)' : 'rgba(255,255,255,0.06)'
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
        <span style={{ fontSize: 15, fontWeight: 600, color: '#E5E7EB' }}>{agent.name}</span>
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
                background: 'rgba(255,255,255,0.05)', color: '#9CA3AF',
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
}
