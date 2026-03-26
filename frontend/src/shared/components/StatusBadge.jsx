const STATUS_STYLES = {
  pending: { bg: 'rgba(156,163,175,0.15)', color: '#9CA3AF', label: 'Pendiente' },
  running: { bg: 'rgba(99,102,241,0.15)', color: '#818CF8', label: 'Ejecutando', animation: 'pulse 1.5s infinite' },
  completed: { bg: 'rgba(16,185,129,0.15)', color: '#10B981', label: 'Completado' },
  failed: { bg: 'rgba(239,68,68,0.15)', color: '#EF4444', label: 'Fallido' },
  cancelled: { bg: 'rgba(245,158,11,0.15)', color: '#F59E0B', label: 'Cancelado' },
}

export default function StatusBadge({ status }) {
  const s = STATUS_STYLES[status] || STATUS_STYLES.pending
  return (
    <span
      aria-label={`Estado: ${s.label}`}
      style={{
        display: 'inline-flex',
        alignItems: 'center',
        gap: 6,
        padding: '3px 10px',
        borderRadius: 9999,
        fontSize: 12,
        fontWeight: 500,
        background: s.bg,
        color: s.color,
        animation: s.animation || 'none',
        whiteSpace: 'nowrap',
      }}
    >
      <span style={{
        width: 6, height: 6, borderRadius: '50%',
        background: s.color, flexShrink: 0,
      }} />
      {s.label}
    </span>
  )
}
