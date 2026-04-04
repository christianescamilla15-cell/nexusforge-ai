/**
 * Simple breadcrumb navigation.
 * Usage: <Breadcrumb items={[{ label: 'Automations', onClick: () => navigate('/automations') }, { label: 'Dashboard' }]} />
 */
export default function Breadcrumb({ items = [], lang = 'en' }) {
  const isDark = document.documentElement.getAttribute('data-theme') === 'dark'

  return (
    <nav aria-label="Breadcrumb" style={{
      display: 'flex', alignItems: 'center', gap: 6,
      fontSize: 13, marginBottom: 16, flexWrap: 'wrap',
    }}>
      {items.map((item, i) => {
        const isLast = i === items.length - 1
        return (
          <span key={i} style={{ display: 'flex', alignItems: 'center', gap: 6 }}>
            {i > 0 && <span style={{ color: '#D1D5DB' }}>/</span>}
            {isLast ? (
              <span style={{ color: isDark ? '#E5E7EB' : '#111827', fontWeight: 600 }}>
                {item.label}
              </span>
            ) : (
              <button
                onClick={item.onClick}
                style={{
                  background: 'none', border: 'none', padding: 0,
                  color: '#6366F1', cursor: 'pointer', fontWeight: 500,
                  fontSize: 13,
                }}
                onMouseEnter={e => e.currentTarget.style.textDecoration = 'underline'}
                onMouseLeave={e => e.currentTarget.style.textDecoration = 'none'}
              >
                {item.label}
              </button>
            )}
          </span>
        )
      })}
    </nav>
  )
}
