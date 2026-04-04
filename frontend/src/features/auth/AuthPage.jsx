import { useState } from 'react'
import { getApiUrl } from '../../services/api'

export default function AuthPage({ onLogin, lang = 'es' }) {
  const [mode, setMode] = useState('login') // login | register | forgot | reset
  const [email, setEmail] = useState('')
  const [password, setPassword] = useState('')
  const [name, setName] = useState('')
  const [resetCode, setResetCode] = useState('')
  const [newPassword, setNewPassword] = useState('')
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState(null)
  const [info, setInfo] = useState(null)

  const isDark = document.documentElement.getAttribute('data-theme') === 'dark'
  const bg = isDark ? '#0F1117' : '#F8FAFC'
  const card = isDark ? '#1A1D23' : '#FFFFFF'
  const border = isDark ? 'rgba(255,255,255,0.08)' : '#E2E8F0'
  const text = isDark ? '#F3F4F6' : '#111827'
  const muted = isDark ? '#9CA3AF' : '#6B7280'
  const accent = '#2563EB'

  async function handleSubmit(e) {
    e.preventDefault()
    setLoading(true)
    setError(null)

    const endpoint = mode === 'register' ? '/auth/register' : '/auth/login'
    const body = mode === 'register'
      ? { email, password, name }
      : { email, password }

    try {
      const apiUrl = getApiUrl()
      const res = await fetch(`${apiUrl}${endpoint}`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(body),
        redirect: 'follow',
      })

      const data = await res.json()

      if (!res.ok) {
        setError(data?.detail || `Error ${res.status}`)
        setLoading(false)
        return
      }

      if (data?.token) {
        localStorage.setItem('nf_token', data.token)
        localStorage.setItem('nf_user', JSON.stringify(data.user))
        if (onLogin) onLogin(data.user)
      } else {
        setError('Authentication failed — no token received')
      }
    } catch (err) {
      setError(lang === 'es'
        ? 'Servidor no disponible. Espera 30s e intenta de nuevo.'
        : 'Server unavailable. Wait 30s and try again.')
    }
    setLoading(false)
  }

  return (
    <div style={{
      minHeight: '100vh',
      background: bg,
      display: 'flex',
      alignItems: 'center',
      justifyContent: 'center',
      padding: 20,
    }}>
      <div style={{
        width: '100%',
        maxWidth: 420,
        background: card,
        border: `1px solid ${border}`,
        borderRadius: 16,
        padding: 40,
        boxShadow: isDark ? 'none' : '0 4px 24px rgba(0,0,0,0.06)',
      }}>
        {/* Logo */}
        <div style={{ textAlign: 'center', marginBottom: 32 }}>
          <div style={{
            width: 48, height: 48, borderRadius: 12,
            background: `linear-gradient(135deg, ${accent}, #7C3AED)`,
            display: 'inline-flex', alignItems: 'center', justifyContent: 'center',
            marginBottom: 16,
          }}>
            <span style={{ color: '#fff', fontSize: 24, fontWeight: 700 }}>N</span>
          </div>
          <h1 style={{ color: text, fontSize: 24, fontWeight: 700, margin: 0 }}>NexusForge AI</h1>
          <p style={{ color: muted, fontSize: 14, marginTop: 4 }}>
            {mode === 'login'
              ? (lang === 'es' ? 'Inicia sesion en tu cuenta' : 'Sign in to your account')
              : (lang === 'es' ? 'Crea tu cuenta' : 'Create your account')
            }
          </p>
        </div>

        {/* Error */}
        {error && (
          <div style={{
            background: '#FEE2E2', color: '#991B1B', padding: '10px 14px',
            borderRadius: 8, fontSize: 13, marginBottom: 16,
          }}>
            {error}
          </div>
        )}

        {/* Form */}
        <form onSubmit={handleSubmit}>
          {mode === 'register' && (
            <div style={{ marginBottom: 16 }}>
              <label style={{ display: 'block', color: muted, fontSize: 13, marginBottom: 6 }}>
                {lang === 'es' ? 'Nombre' : 'Name'}
              </label>
              <input
                type="text"
                value={name}
                onChange={e => setName(e.target.value)}
                placeholder="Christian Hernandez"
                style={{
                  width: '100%', padding: '10px 14px', borderRadius: 8,
                  border: `1px solid ${border}`, background: bg, color: text,
                  fontSize: 14, outline: 'none', boxSizing: 'border-box',
                }}
              />
            </div>
          )}

          <div style={{ marginBottom: 16 }}>
            <label style={{ display: 'block', color: muted, fontSize: 13, marginBottom: 6 }}>Email</label>
            <input
              type="email"
              value={email}
              onChange={e => setEmail(e.target.value)}
              placeholder="user@example.com"
              required
              style={{
                width: '100%', padding: '10px 14px', borderRadius: 8,
                border: `1px solid ${border}`, background: bg, color: text,
                fontSize: 14, outline: 'none', boxSizing: 'border-box',
              }}
            />
          </div>

          <div style={{ marginBottom: 24 }}>
            <label style={{ display: 'block', color: muted, fontSize: 13, marginBottom: 6 }}>
              {lang === 'es' ? 'Contrasena' : 'Password'}
            </label>
            <input
              type="password"
              value={password}
              onChange={e => setPassword(e.target.value)}
              placeholder="••••••••"
              required
              minLength={6}
              style={{
                width: '100%', padding: '10px 14px', borderRadius: 8,
                border: `1px solid ${border}`, background: bg, color: text,
                fontSize: 14, outline: 'none', boxSizing: 'border-box',
              }}
            />
          </div>

          <button
            type="submit"
            disabled={loading}
            style={{
              width: '100%', padding: '12px 0', borderRadius: 8, border: 'none',
              background: loading ? muted : accent, color: '#fff',
              fontSize: 15, fontWeight: 600, cursor: loading ? 'not-allowed' : 'pointer',
            }}
          >
            {loading
              ? '...'
              : mode === 'login'
                ? (lang === 'es' ? 'Iniciar Sesion' : 'Sign In')
                : (lang === 'es' ? 'Crear Cuenta' : 'Create Account')
            }
          </button>
          {mode === 'login' && (
            <p style={{ textAlign: 'right', marginTop: 8 }}>
              <span onClick={() => { setMode('forgot'); setError(null); setInfo(null) }}
                style={{ fontSize: 12, color: accent, cursor: 'pointer' }}>
                {lang === 'es' ? 'Olvidaste tu contraseña?' : 'Forgot password?'}
              </span>
            </p>
          )}
        </form>

        {/* Forgot password form */}
        {mode === 'forgot' && (
          <form onSubmit={async (e) => {
            e.preventDefault(); setLoading(true); setError(null); setInfo(null)
            const res = await fetch(`${getApiUrl()}/auth/forgot-password`, {
              method: 'POST', headers: { 'Content-Type': 'application/json' },
              body: JSON.stringify({ email }),
            })
            setLoading(false)
            if (res.ok) {
              setInfo(lang === 'es' ? 'Codigo enviado a tu email' : 'Code sent to your email')
              setMode('reset')
            } else {
              setError(lang === 'es' ? 'Error al enviar' : 'Failed to send')
            }
          }} style={{ marginBottom: 16 }}>
            <label style={{ fontSize: 13, fontWeight: 600, color: text, display: 'block', marginBottom: 4 }}>
              Email
            </label>
            <input type="email" value={email} onChange={e => setEmail(e.target.value)} required
              style={{ width: '100%', padding: '10px 14px', borderRadius: 8, border: `1px solid ${border}`, background: bg, color: text, fontSize: 14, outline: 'none', boxSizing: 'border-box', marginBottom: 12 }} />
            <button type="submit" disabled={loading} style={{
              width: '100%', padding: '12px 0', borderRadius: 8, border: 'none',
              background: loading ? muted : accent, color: '#fff', fontSize: 15, fontWeight: 600, cursor: loading ? 'not-allowed' : 'pointer',
            }}>{loading ? '...' : (lang === 'es' ? 'Enviar Codigo' : 'Send Code')}</button>
            <p style={{ textAlign: 'center', marginTop: 10 }}>
              <span onClick={() => { setMode('login'); setError(null); setInfo(null) }} style={{ fontSize: 12, color: accent, cursor: 'pointer' }}>
                {lang === 'es' ? 'Volver al login' : 'Back to login'}
              </span>
            </p>
          </form>
        )}

        {/* Reset password form */}
        {mode === 'reset' && (
          <form onSubmit={async (e) => {
            e.preventDefault(); setLoading(true); setError(null)
            const res = await fetch(`${getApiUrl()}/auth/reset-password`, {
              method: 'POST', headers: { 'Content-Type': 'application/json' },
              body: JSON.stringify({ email, code: resetCode, new_password: newPassword }),
            })
            setLoading(false)
            if (res.ok) {
              setInfo(lang === 'es' ? 'Contraseña cambiada! Inicia sesion.' : 'Password changed! Sign in.')
              setMode('login'); setResetCode(''); setNewPassword('')
            } else {
              const d = await res.json().catch(() => ({}))
              setError(d.detail || (lang === 'es' ? 'Codigo invalido' : 'Invalid code'))
            }
          }} style={{ marginBottom: 16 }}>
            {info && <div style={{ padding: 10, borderRadius: 8, background: '#DCFCE7', color: '#166534', fontSize: 13, marginBottom: 12 }}>{info}</div>}
            <label style={{ fontSize: 13, fontWeight: 600, color: text, display: 'block', marginBottom: 4 }}>
              {lang === 'es' ? 'Codigo de 6 digitos' : '6-digit code'}
            </label>
            <input type="text" value={resetCode} onChange={e => setResetCode(e.target.value)} required maxLength={6} placeholder="123456"
              style={{ width: '100%', padding: '10px 14px', borderRadius: 8, border: `1px solid ${border}`, background: bg, color: text, fontSize: 18, fontWeight: 700, textAlign: 'center', letterSpacing: '0.3em', outline: 'none', boxSizing: 'border-box', marginBottom: 12 }} />
            <label style={{ fontSize: 13, fontWeight: 600, color: text, display: 'block', marginBottom: 4 }}>
              {lang === 'es' ? 'Nueva contraseña' : 'New password'}
            </label>
            <input type="password" value={newPassword} onChange={e => setNewPassword(e.target.value)} required minLength={6}
              style={{ width: '100%', padding: '10px 14px', borderRadius: 8, border: `1px solid ${border}`, background: bg, color: text, fontSize: 14, outline: 'none', boxSizing: 'border-box', marginBottom: 12 }} />
            <button type="submit" disabled={loading} style={{
              width: '100%', padding: '12px 0', borderRadius: 8, border: 'none',
              background: loading ? muted : accent, color: '#fff', fontSize: 15, fontWeight: 600, cursor: loading ? 'not-allowed' : 'pointer',
            }}>{loading ? '...' : (lang === 'es' ? 'Cambiar Contraseña' : 'Reset Password')}</button>
          </form>
        )}

        {/* Divider */}
        <div style={{ display: 'flex', alignItems: 'center', gap: 12, margin: '20px 0' }}>
          <div style={{ flex: 1, height: 1, background: border }} />
          <span style={{ color: muted, fontSize: 12 }}>{lang === 'es' ? 'o' : 'or'}</span>
          <div style={{ flex: 1, height: 1, background: border }} />
        </div>

        {/* Google OAuth */}
        <button
          onClick={() => {
            setError(lang === 'es' ? 'Google OAuth proximamente. Usa email por ahora.' : 'Google OAuth coming soon. Use email for now.')
          }}
          style={{
            width: '100%', padding: '12px 0', borderRadius: 8,
            border: `1px solid ${border}`, background: 'transparent',
            color: text, fontSize: 14, fontWeight: 600, cursor: 'pointer',
            display: 'flex', alignItems: 'center', justifyContent: 'center', gap: 10,
            marginBottom: 10,
          }}
        >
          <svg width="18" height="18" viewBox="0 0 48 48">
            <path fill="#EA4335" d="M24 9.5c3.54 0 6.71 1.22 9.21 3.6l6.85-6.85C35.9 2.38 30.47 0 24 0 14.62 0 6.51 5.38 2.56 13.22l7.98 6.19C12.43 13.72 17.74 9.5 24 9.5z"/>
            <path fill="#4285F4" d="M46.98 24.55c0-1.57-.15-3.09-.38-4.55H24v9.02h12.94c-.58 2.96-2.26 5.48-4.78 7.18l7.73 6c4.51-4.18 7.09-10.36 7.09-17.65z"/>
            <path fill="#FBBC05" d="M10.53 28.59c-.48-1.45-.76-2.99-.76-4.59s.27-3.14.76-4.59l-7.98-6.19C.92 16.46 0 20.12 0 24c0 3.88.92 7.54 2.56 10.78l7.97-6.19z"/>
            <path fill="#34A853" d="M24 48c6.48 0 11.93-2.13 15.89-5.81l-7.73-6c-2.15 1.45-4.92 2.3-8.16 2.3-6.26 0-11.57-4.22-13.47-9.91l-7.98 6.19C6.51 42.62 14.62 48 24 48z"/>
          </svg>
          {lang === 'es' ? 'Continuar con Google' : 'Continue with Google'}
        </button>

        {/* Guest / Trial mode */}
        <button
          onClick={() => {
            const guestRuns = parseInt(localStorage.getItem('nf_guest_runs') || '0')
            if (guestRuns >= 10) {
              setError(lang === 'es'
                ? 'Limite de prueba alcanzado (10 ejecuciones). Registrate para continuar.'
                : 'Trial limit reached (10 runs). Register to continue.')
              return
            }
            const guestUser = {
              id: 'guest',
              name: lang === 'es' ? 'Invitado' : 'Guest',
              email: 'guest@nexusforge.ai',
              role: 'viewer',
              plan: 'trial',
              runs_today: guestRuns,
              isGuest: true,
            }
            localStorage.setItem('nf_user', JSON.stringify(guestUser))
            if (!localStorage.getItem('nf_guest_runs')) {
              localStorage.setItem('nf_guest_runs', '0')
            }
            if (onLogin) onLogin(guestUser)
          }}
          style={{
            width: '100%', padding: '12px 0', borderRadius: 8,
            border: `1px solid ${border}`,
            background: 'transparent', color: text,
            fontSize: 14, fontWeight: 600, cursor: 'pointer',
            display: 'flex', alignItems: 'center', justifyContent: 'center', gap: 8,
          }}
        >
          <span style={{ fontSize: 18 }}>🔬</span>
          {lang === 'es' ? 'Probar sin cuenta (10 ejecuciones)' : 'Try without account (10 runs)'}
        </button>
        {(() => {
          const guestRuns = parseInt(localStorage.getItem('nf_guest_runs') || '0')
          if (guestRuns > 0) {
            return (
              <p style={{ textAlign: 'center', color: guestRuns >= 8 ? '#EF4444' : muted, fontSize: 11, marginTop: 6 }}>
                {guestRuns}/10 {lang === 'es' ? 'ejecuciones usadas' : 'runs used'}
              </p>
            )
          }
          return null
        })()}

        {/* Toggle */}
        <p style={{ textAlign: 'center', color: muted, fontSize: 13, marginTop: 20 }}>
          {mode === 'login'
            ? (lang === 'es' ? 'No tienes cuenta? ' : "Don't have an account? ")
            : (lang === 'es' ? 'Ya tienes cuenta? ' : 'Already have an account? ')
          }
          <span
            onClick={() => { setMode(mode === 'login' ? 'register' : 'login'); setError(null) }}
            style={{ color: accent, cursor: 'pointer', fontWeight: 600 }}
          >
            {mode === 'login'
              ? (lang === 'es' ? 'Registrate' : 'Sign Up')
              : (lang === 'es' ? 'Inicia sesion' : 'Sign In')
            }
          </span>
        </p>

        {/* Plans preview */}
        <div style={{
          marginTop: 24, padding: 16, background: bg, borderRadius: 10,
          border: `1px solid ${border}`,
        }}>
          <p style={{ color: muted, fontSize: 12, margin: '0 0 8px', fontWeight: 600, textTransform: 'uppercase', letterSpacing: 1 }}>
            {lang === 'es' ? 'Planes disponibles' : 'Available plans'}
          </p>
          <div style={{ display: 'flex', gap: 8 }}>
            {[
              { name: 'Free', price: '$0', runs: '5/day' },
              { name: 'Pro', price: '$29', runs: '100/day' },
              { name: 'Team', price: '$99', runs: '500/day' },
            ].map(p => (
              <div key={p.name} style={{
                flex: 1, padding: '8px 6px', borderRadius: 8, textAlign: 'center',
                border: `1px solid ${border}`, fontSize: 11,
              }}>
                <div style={{ color: text, fontWeight: 700 }}>{p.name}</div>
                <div style={{ color: accent, fontWeight: 600 }}>{p.price}</div>
                <div style={{ color: muted }}>{p.runs}</div>
              </div>
            ))}
          </div>
        </div>
      </div>
    </div>
  )
}
