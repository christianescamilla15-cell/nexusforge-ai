import { useState, useEffect, useRef } from 'react'

const STORAGE_KEY = 'nxf_notifications'
const MAX_NOTIFICATIONS = 20

function loadNotifications() {
  try {
    const raw = localStorage.getItem(STORAGE_KEY)
    return raw ? JSON.parse(raw) : []
  } catch { return [] }
}

function saveNotifications(list) {
  try {
    localStorage.setItem(STORAGE_KEY, JSON.stringify(list.slice(0, MAX_NOTIFICATIONS)))
  } catch { /* */ }
}

export function addNotification(message, type = 'info') {
  const list = loadNotifications()
  const item = {
    id: Date.now() + Math.random(),
    message,
    type,
    timestamp: new Date().toISOString(),
    read: false,
  }
  const updated = [item, ...list].slice(0, MAX_NOTIFICATIONS)
  saveNotifications(updated)
  // Dispatch custom event so the bell picks it up
  window.dispatchEvent(new CustomEvent('nxf-notification', { detail: item }))
  return item
}

export default function NotificationBell({ lang, isDark }) {
  const [notifications, setNotifications] = useState(loadNotifications)
  const [open, setOpen] = useState(false)
  const ref = useRef(null)

  const unread = notifications.filter(n => !n.read).length

  // Listen for new notifications
  useEffect(() => {
    const handler = () => setNotifications(loadNotifications())
    window.addEventListener('nxf-notification', handler)
    window.addEventListener('storage', handler)
    return () => {
      window.removeEventListener('nxf-notification', handler)
      window.removeEventListener('storage', handler)
    }
  }, [])

  // Close on outside click
  useEffect(() => {
    if (!open) return
    const handler = (e) => {
      if (ref.current && !ref.current.contains(e.target)) setOpen(false)
    }
    document.addEventListener('mousedown', handler)
    return () => document.removeEventListener('mousedown', handler)
  }, [open])

  const markAllRead = () => {
    const updated = notifications.map(n => ({ ...n, read: true }))
    setNotifications(updated)
    saveNotifications(updated)
  }

  const clearAll = () => {
    setNotifications([])
    saveNotifications([])
  }

  const handleToggle = () => {
    if (!open) {
      // Mark all as read when opening
      markAllRead()
    }
    setOpen(o => !o)
  }

  const formatTime = (iso) => {
    if (!iso) return ''
    const d = new Date(iso)
    const now = new Date()
    const diffMs = now - d
    const diffMin = Math.floor(diffMs / 60000)
    if (diffMin < 1) return lang === 'es' ? 'Ahora' : 'Just now'
    if (diffMin < 60) return `${diffMin}m`
    const diffH = Math.floor(diffMin / 60)
    if (diffH < 24) return `${diffH}h`
    return d.toLocaleDateString(lang === 'es' ? 'es-ES' : 'en-US', { month: 'short', day: 'numeric' })
  }

  const TYPE_ICON = {
    success: '\u2705',
    error: '\u274C',
    info: '\u2139\uFE0F',
    warning: '\u26A0\uFE0F',
  }

  return (
    <div ref={ref} style={{ position: 'relative' }}>
      <button
        onClick={handleToggle}
        aria-label={lang === 'es' ? 'Notificaciones' : 'Notifications'}
        title={lang === 'es' ? 'Notificaciones' : 'Notifications'}
        style={{
          background: 'none', border: 'none', cursor: 'pointer',
          padding: 4, position: 'relative', display: 'flex',
          alignItems: 'center', justifyContent: 'center',
          color: isDark ? '#9CA3AF' : '#6B7280',
        }}
      >
        <svg width="20" height="20" viewBox="0 0 24 24" fill="none"
          stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round">
          <path d="M14.857 17.082a23.848 23.848 0 005.454-1.31A8.967 8.967 0 0118 9.75V9A6 6 0 006 9v.75a8.967 8.967 0 01-2.312 6.022c1.733.64 3.56 1.085 5.455 1.31m5.714 0a24.255 24.255 0 01-5.714 0m5.714 0a3 3 0 11-5.714 0" />
        </svg>
        {unread > 0 && (
          <span style={{
            position: 'absolute', top: 0, right: 0,
            width: 16, height: 16, borderRadius: '50%',
            background: '#EF4444', color: '#fff',
            fontSize: 9, fontWeight: 700,
            display: 'flex', alignItems: 'center', justifyContent: 'center',
            border: `2px solid ${isDark ? '#0F1117' : '#FFFFFF'}`,
          }}>
            {unread > 9 ? '9+' : unread}
          </span>
        )}
      </button>

      {open && (
        <div style={{
          position: 'absolute', right: 0, top: 40,
          width: 340,
          background: isDark ? '#1A1D23' : '#FFFFFF',
          border: `1px solid ${isDark ? 'rgba(255,255,255,0.1)' : '#E5E7EB'}`,
          borderRadius: 12,
          boxShadow: '0 8px 32px rgba(0,0,0,0.15)',
          zIndex: 200,
          overflow: 'hidden',
        }}>
          {/* Header */}
          <div style={{
            display: 'flex', justifyContent: 'space-between', alignItems: 'center',
            padding: '12px 16px',
            borderBottom: `1px solid ${isDark ? 'rgba(255,255,255,0.06)' : '#F3F4F6'}`,
          }}>
            <span style={{ fontSize: 14, fontWeight: 700, color: isDark ? '#F3F4F6' : '#111827' }}>
              {lang === 'es' ? 'Notificaciones' : 'Notifications'}
            </span>
            {notifications.length > 0 && (
              <button
                onClick={clearAll}
                style={{
                  background: 'none', border: 'none', cursor: 'pointer',
                  fontSize: 11, color: '#9CA3AF', fontWeight: 500,
                }}
              >
                {lang === 'es' ? 'Limpiar todo' : 'Clear all'}
              </button>
            )}
          </div>

          {/* Items */}
          <div style={{ maxHeight: 320, overflowY: 'auto' }}>
            {notifications.length === 0 ? (
              <div style={{
                padding: '32px 16px', textAlign: 'center',
                color: '#9CA3AF', fontSize: 13,
              }}>
                <div style={{ fontSize: 28, marginBottom: 8, opacity: 0.4 }}>
                  <svg width="28" height="28" viewBox="0 0 24 24" fill="none"
                    stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round"
                    style={{ margin: '0 auto', display: 'block', opacity: 0.4 }}>
                    <path d="M14.857 17.082a23.848 23.848 0 005.454-1.31A8.967 8.967 0 0118 9.75V9A6 6 0 006 9v.75a8.967 8.967 0 01-2.312 6.022c1.733.64 3.56 1.085 5.455 1.31m5.714 0a24.255 24.255 0 01-5.714 0m5.714 0a3 3 0 11-5.714 0" />
                  </svg>
                </div>
                {lang === 'es' ? 'Sin notificaciones' : 'No notifications'}
              </div>
            ) : (
              notifications.slice(0, 5).map(n => (
                <div
                  key={n.id}
                  style={{
                    padding: '10px 16px',
                    borderBottom: `1px solid ${isDark ? 'rgba(255,255,255,0.04)' : '#F9FAFB'}`,
                    display: 'flex', gap: 10, alignItems: 'flex-start',
                    background: n.read ? 'transparent' : (isDark ? 'rgba(99,102,241,0.05)' : 'rgba(37,99,235,0.03)'),
                  }}
                >
                  <span style={{ fontSize: 14, flexShrink: 0, marginTop: 2 }}>
                    {TYPE_ICON[n.type] || TYPE_ICON.info}
                  </span>
                  <div style={{ flex: 1, minWidth: 0 }}>
                    <p style={{
                      fontSize: 12, color: isDark ? '#D1D5DB' : '#374151',
                      margin: 0, lineHeight: 1.4, wordBreak: 'break-word',
                    }}>
                      {n.message}
                    </p>
                    <p style={{ fontSize: 11, color: '#9CA3AF', margin: '4px 0 0' }}>
                      {formatTime(n.timestamp)}
                    </p>
                  </div>
                </div>
              ))
            )}
          </div>
        </div>
      )}
    </div>
  )
}
