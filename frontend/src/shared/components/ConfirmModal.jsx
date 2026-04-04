import { useEffect, useRef, useState } from 'react'

/**
 * Reusable confirm dialog replacing browser confirm().
 * Usage: <ConfirmModal message="Delete?" onConfirm={...} onCancel={...} />
 */
export default function ConfirmModal({
  message,
  confirmLabel = 'Confirm',
  cancelLabel = 'Cancel',
  danger = true,
  onConfirm,
  onCancel,
}) {
  const confirmRef = useRef(null)
  const isDark = document.documentElement.getAttribute('data-theme') === 'dark'
  const bg = isDark ? '#1E1F33' : '#fff'
  const text = isDark ? '#E5E7EB' : '#111827'
  const border = isDark ? 'rgba(255,255,255,0.1)' : '#E5E7EB'

  // Auto-focus confirm button + Escape to cancel
  useEffect(() => {
    confirmRef.current?.focus()
    const handleKey = (e) => {
      if (e.key === 'Escape') onCancel()
    }
    window.addEventListener('keydown', handleKey)
    return () => window.removeEventListener('keydown', handleKey)
  }, [onCancel])

  return (
    <div
      onClick={onCancel}
      style={{
        position: 'fixed', inset: 0, background: 'rgba(0,0,0,0.4)',
        zIndex: 200, display: 'flex', alignItems: 'center', justifyContent: 'center',
        padding: 16, animation: 'fadeIn 0.15s ease-out',
      }}
    >
      <div
        onClick={e => e.stopPropagation()}
        style={{
          background: bg, borderRadius: 14, padding: 24,
          maxWidth: 400, width: '100%',
          boxShadow: '0 20px 60px rgba(0,0,0,0.3)',
          border: `1px solid ${border}`,
        }}
      >
        <p style={{ fontSize: 15, color: text, lineHeight: 1.5, marginBottom: 20, fontWeight: 500 }}>
          {message}
        </p>
        <div style={{ display: 'flex', gap: 10, justifyContent: 'flex-end' }}>
          <button
            onClick={onCancel}
            style={{
              padding: '9px 18px', borderRadius: 8, border: `1px solid ${border}`,
              background: bg, fontSize: 13, fontWeight: 600, cursor: 'pointer', color: isDark ? '#D1D5DB' : '#6B7280',
            }}
          >
            {cancelLabel}
          </button>
          <button
            ref={confirmRef}
            onClick={onConfirm}
            style={{
              padding: '9px 18px', borderRadius: 8, border: 'none',
              background: danger ? '#EF4444' : '#6366F1',
              fontSize: 13, fontWeight: 600, cursor: 'pointer', color: '#fff',
            }}
          >
            {confirmLabel}
          </button>
        </div>
      </div>
    </div>
  )
}
