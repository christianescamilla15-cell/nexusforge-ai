export default function EmptyState({ icon, title, description, actionLabel, onAction, secondaryLabel, onSecondary }) {
  const isDark = document.documentElement.getAttribute('data-theme') === 'dark'

  return (
    <div style={{
      display: 'flex', flexDirection: 'column', alignItems: 'center',
      justifyContent: 'center', padding: '48px 24px', textAlign: 'center',
    }}>
      {icon && (
        <div style={{
          marginBottom: 20, fontSize: 56,
          width: 88, height: 88, borderRadius: 20,
          background: isDark ? 'rgba(99,102,241,0.1)' : 'rgba(99,102,241,0.06)',
          display: 'flex', alignItems: 'center', justifyContent: 'center',
        }}>
          {icon}
        </div>
      )}
      <h3 style={{ fontSize: 18, fontWeight: 700, color: isDark ? '#E5E7EB' : '#111827', marginBottom: 8 }}>
        {title}
      </h3>
      {description && (
        <p style={{ fontSize: 14, color: '#9CA3AF', maxWidth: 360, marginBottom: 24, lineHeight: 1.5 }}>
          {description}
        </p>
      )}
      <div style={{ display: 'flex', gap: 10, flexWrap: 'wrap', justifyContent: 'center' }}>
        {actionLabel && onAction && (
          <button
            onClick={onAction}
            style={{
              padding: '10px 24px', borderRadius: 8, border: 'none',
              background: 'linear-gradient(135deg, #6366F1, #8B5CF6)',
              color: '#fff', fontSize: 14, fontWeight: 600, cursor: 'pointer',
              boxShadow: '0 2px 8px rgba(99,102,241,0.3)',
            }}
          >
            {actionLabel}
          </button>
        )}
        {secondaryLabel && onSecondary && (
          <button
            onClick={onSecondary}
            style={{
              padding: '10px 24px', borderRadius: 8,
              border: '1px solid #E5E7EB', background: isDark ? '#1E1F33' : '#fff',
              color: isDark ? '#D1D5DB' : '#6B7280', fontSize: 14, fontWeight: 600, cursor: 'pointer',
            }}
          >
            {secondaryLabel}
          </button>
        )}
      </div>
    </div>
  )
}
