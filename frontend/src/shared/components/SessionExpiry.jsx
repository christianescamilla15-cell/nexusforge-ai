import { useState, useEffect } from 'react'

/**
 * Shows a warning banner when the JWT is about to expire (5 min before).
 * Reads token from localStorage and decodes the exp claim.
 */
export default function SessionExpiry({ lang = 'en', onLogout }) {
  const [showWarning, setShowWarning] = useState(false)
  const [minutesLeft, setMinutesLeft] = useState(0)

  useEffect(() => {
    const check = () => {
      try {
        const token = localStorage.getItem('nf_token')
        if (!token) return
        // Decode JWT payload (base64)
        const payload = JSON.parse(atob(token.split('.')[1]))
        const exp = payload.exp * 1000 // ms
        const remaining = exp - Date.now()
        const mins = Math.floor(remaining / 60000)

        if (remaining <= 0) {
          // Expired — auto logout
          onLogout?.()
        } else if (remaining <= 300000) {
          // 5 minutes or less
          setMinutesLeft(Math.max(1, mins))
          setShowWarning(true)
        } else {
          setShowWarning(false)
        }
      } catch {}
    }

    check()
    const interval = setInterval(check, 30000) // check every 30s
    return () => clearInterval(interval)
  }, [onLogout])

  if (!showWarning) return null

  return (
    <div style={{
      position: 'fixed', top: 8, left: '50%', transform: 'translateX(-50%)',
      padding: '8px 20px', borderRadius: 8, zIndex: 350,
      background: '#FEF3C7', border: '1px solid #FCD34D', color: '#92400E',
      fontSize: 13, fontWeight: 600, boxShadow: '0 4px 12px rgba(0,0,0,0.1)',
      display: 'flex', alignItems: 'center', gap: 10,
      animation: 'fadeIn 0.2s ease-out',
    }}>
      <span>
        {lang === 'es'
          ? `Tu sesion expira en ${minutesLeft} min`
          : `Session expires in ${minutesLeft} min`}
      </span>
      <button onClick={() => {
        // Re-login silently via refresh (or show login modal)
        window.location.reload()
      }} style={{
        padding: '4px 12px', borderRadius: 6, border: 'none',
        background: '#F59E0B', color: '#fff', fontSize: 12, fontWeight: 600, cursor: 'pointer',
      }}>
        {lang === 'es' ? 'Renovar' : 'Refresh'}
      </button>
    </div>
  )
}
