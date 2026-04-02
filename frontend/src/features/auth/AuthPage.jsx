import { useState } from 'react'
import { fetchAPI } from '../../services/api'

export default function AuthPage({ onLogin, lang = 'es' }) {
  const [mode, setMode] = useState('login') // login | register
  const [email, setEmail] = useState('')
  const [password, setPassword] = useState('')
  const [name, setName] = useState('')
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState(null)

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
      const res = await fetchAPI(endpoint, {
        method: 'POST',
        body: JSON.stringify(body),
      })

      if (res.error) {
        setError(res.error)
        setLoading(false)
        return
      }

      const data = res.data
      if (data?.token) {
        localStorage.setItem('nf_token', data.token)
        localStorage.setItem('nf_user', JSON.stringify(data.user))
        if (onLogin) onLogin(data.user)
      } else {
        setError(data?.detail || 'Authentication failed')
      }
    } catch (err) {
      setError(err.message)
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
        </form>

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
