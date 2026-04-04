import { useNavigate } from 'react-router-dom'

export default function NotFoundPage({ lang = 'en' }) {
  const navigate = useNavigate()

  return (
    <div style={{
      display: 'flex', flexDirection: 'column', alignItems: 'center',
      justifyContent: 'center', padding: '80px 24px', textAlign: 'center',
    }}>
      <div style={{
        fontSize: 80, marginBottom: 16, opacity: 0.3,
        fontWeight: 900, color: '#6366F1', fontFamily: 'monospace',
      }}>404</div>
      <h1 style={{ fontSize: 24, fontWeight: 700, color: '#111827', marginBottom: 8 }}>
        {lang === 'es' ? 'Pagina no encontrada' : 'Page not found'}
      </h1>
      <p style={{ fontSize: 14, color: '#9CA3AF', maxWidth: 400, marginBottom: 24, lineHeight: 1.5 }}>
        {lang === 'es'
          ? 'La pagina que buscas no existe o fue movida. Verifica la URL o regresa al Dashboard.'
          : "The page you're looking for doesn't exist or has been moved. Check the URL or go back to Dashboard."}
      </p>
      <div style={{ display: 'flex', gap: 10 }}>
        <button onClick={() => navigate('/')} style={{
          padding: '10px 24px', borderRadius: 8, border: 'none',
          background: 'linear-gradient(135deg, #6366F1, #8B5CF6)',
          color: '#fff', fontSize: 14, fontWeight: 600, cursor: 'pointer',
        }}>
          {lang === 'es' ? 'Ir al Dashboard' : 'Go to Dashboard'}
        </button>
        <button onClick={() => navigate(-1)} style={{
          padding: '10px 24px', borderRadius: 8, border: '1px solid #E5E7EB',
          background: '#fff', color: '#6B7280', fontSize: 14, fontWeight: 600, cursor: 'pointer',
        }}>
          {lang === 'es' ? 'Regresar' : 'Go back'}
        </button>
      </div>
    </div>
  )
}
