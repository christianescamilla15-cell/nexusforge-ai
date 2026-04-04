import { useState, useEffect } from 'react'

/**
 * Shows a banner when the browser goes offline or backend is unreachable.
 */
export default function OfflineIndicator({ lang = 'en' }) {
  const [offline, setOffline] = useState(!navigator.onLine)

  useEffect(() => {
    const goOffline = () => setOffline(true)
    const goOnline = () => setOffline(false)
    window.addEventListener('offline', goOffline)
    window.addEventListener('online', goOnline)
    return () => {
      window.removeEventListener('offline', goOffline)
      window.removeEventListener('online', goOnline)
    }
  }, [])

  if (!offline) return null

  return (
    <div style={{
      position: 'fixed', bottom: 20, left: '50%', transform: 'translateX(-50%)',
      padding: '10px 24px', borderRadius: 10, zIndex: 400,
      background: '#1F2937', color: '#F9FAFB', fontSize: 13, fontWeight: 600,
      boxShadow: '0 4px 20px rgba(0,0,0,0.3)',
      display: 'flex', alignItems: 'center', gap: 8,
      animation: 'fadeIn 0.2s ease-out',
    }}>
      <span style={{
        width: 8, height: 8, borderRadius: '50%', background: '#EF4444',
        animation: 'pulse 1.5s infinite',
      }} />
      {lang === 'es' ? 'Sin conexion — los cambios se guardaran cuando vuelvas a conectar' : 'Offline — changes will sync when reconnected'}
    </div>
  )
}
