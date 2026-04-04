import { useEffect, useState } from 'react'

const TYPE_STYLES = {
  success: { bg: '#F0FDF4', border: '#BBF7D0', color: '#166534', icon: '\u2705' },
  error:   { bg: '#FEF2F2', border: '#FECACA', color: '#DC2626', icon: '\u274C' },
  info:    { bg: '#EFF6FF', border: '#BFDBFE', color: '#1D4ED8', icon: '\u2139\uFE0F' },
  warning: { bg: '#FFFBEB', border: '#FDE68A', color: '#92400E', icon: '\u26A0\uFE0F' },
}

function ToastItem({ toast, onDismiss }) {
  const [visible, setVisible] = useState(false)
  const [exiting, setExiting] = useState(false)
  const style = TYPE_STYLES[toast.type] || TYPE_STYLES.info

  useEffect(() => {
    requestAnimationFrame(() => setVisible(true))
    const exitTimer = setTimeout(() => setExiting(true), 4500)
    return () => clearTimeout(exitTimer)
  }, [])

  return (
    <div
      onClick={() => onDismiss(toast.id)}
      style={{
        display: 'flex',
        alignItems: 'center',
        gap: 10,
        padding: '12px 16px',
        borderRadius: 10,
        background: style.bg,
        border: `1px solid ${style.border}`,
        color: style.color,
        fontSize: 13,
        fontWeight: 500,
        boxShadow: '0 4px 16px rgba(0,0,0,0.1)',
        cursor: 'pointer',
        maxWidth: 380,
        minWidth: 260,
        transform: visible && !exiting ? 'translateX(0)' : 'translateX(120%)',
        opacity: visible && !exiting ? 1 : 0,
        transition: 'all 0.3s ease',
        lineHeight: 1.4,
      }}
    >
      <span style={{ fontSize: 16, flexShrink: 0 }}>{style.icon}</span>
      <span style={{ flex: 1 }}>{toast.message}</span>
      <button
        onClick={(e) => { e.stopPropagation(); onDismiss(toast.id) }}
        style={{
          background: 'none', border: 'none', cursor: 'pointer',
          color: style.color, opacity: 0.5, fontSize: 14, padding: 0,
          flexShrink: 0,
        }}
      >
        \u2715
      </button>
    </div>
  )
}

export default function ToastContainer({ toasts, onDismiss }) {
  if (!toasts || toasts.length === 0) return null

  return (
    <div style={{
      position: 'fixed',
      bottom: 24,
      right: 24,
      zIndex: 9999,
      display: 'flex',
      flexDirection: 'column-reverse',
      gap: 8,
      pointerEvents: 'none',
    }}>
      <div style={{ display: 'flex', flexDirection: 'column', gap: 8, pointerEvents: 'auto' }}>
        {toasts.slice(-5).map(toast => (
          <ToastItem key={toast.id} toast={toast} onDismiss={onDismiss} />
        ))}
      </div>
    </div>
  )
}
