export default function LoadingSpinner({ size = 32, color = '#2563EB' }) {
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
        border: '3px solid #F3F4F6',
        borderTopColor: color,
        borderRadius: '50%',
        animation: 'spin 0.7s linear infinite',
      }} />
    </div>
  )
}
