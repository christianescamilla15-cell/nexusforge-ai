const STATUS_STYLES = {
  pending: { bg: 'rgba(156,163,175,0.1)', color: '#9CA3AF', label: 'Pendiente' },
  running: { bg: 'rgba(37,99,235,0.08)', color: '#2563EB', label: 'Ejecutando', animation: 'pulse 1.5s infinite' },
  completed: { bg: 'rgba(5,150,105,0.08)', color: '#059669', label: 'Completado' },
  failed: { bg: 'rgba(220,38,38,0.08)', color: '#DC2626', label: 'Fallido' },
  cancelled: { bg: 'rgba(217,119,6,0.08)', color: '#D97706', label: 'Cancelado' },
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
