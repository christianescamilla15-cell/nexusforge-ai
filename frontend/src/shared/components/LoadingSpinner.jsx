export default function LoadingSpinner({ size = 32, color = '#6366F1' }) {
  return (
    <div
      aria-label="Cargando"
      role="status"
      style={{
        display: 'flex', alignItems: 'center', justifyContent: 'center',
        padding: 24,
      }}
    >
      <div style={{
        width: size, height: size,
        border: `3px solid rgba(255,255,255,0.06)`,
        borderTopColor: color,
        borderRadius: '50%',
        animation: 'spin 0.7s linear infinite',
      }} />
    </div>
  )
}
