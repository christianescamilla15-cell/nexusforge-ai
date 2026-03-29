export default function EmptyState({ icon, title, description, actionLabel, onAction }) {
  return (
    <div style={{
      display: 'flex', flexDirection: 'column', alignItems: 'center',
      justifyContent: 'center', padding: '64px 24px', textAlign: 'center',
    }}>
      {icon && (
        <div style={{ marginBottom: 16, opacity: 0.4, fontSize: 48 }}>
          {icon}
        </div>
      )}
      <h3 style={{ fontSize: 18, fontWeight: 600, color: '#111827', marginBottom: 8 }}>
        {title}
      </h3>
      {description && (
        <p style={{ fontSize: 14, color: '#9CA3AF', maxWidth: 360, marginBottom: 20 }}>
          {description}
        </p>
      )}
      {actionLabel && onAction && (
        <button
          onClick={onAction}
          aria-label={actionLabel}
          style={{
            padding: '10px 20px', borderRadius: 8, border: 'none',
            background: '#2563EB', color: '#fff', fontSize: 14, fontWeight: 500,
            transition: 'background 0.2s', cursor: 'pointer',
          }}
          onMouseEnter={(e) => e.target.style.background = '#1D4ED8'}
          onMouseLeave={(e) => e.target.style.background = '#2563EB'}
        >
          {actionLabel}
        </button>
      )}
    </div>
  )
}
