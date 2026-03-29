import { useEffect, useRef } from 'react'

export default function Modal({ open, onClose, title, children, width = 560 }) {
  const overlayRef = useRef(null)

  useEffect(() => {
    if (!open) return
    const handleKey = (e) => { if (e.key === 'Escape') onClose() }
    document.addEventListener('keydown', handleKey)
    document.body.style.overflow = 'hidden'
    return () => {
      document.removeEventListener('keydown', handleKey)
      document.body.style.overflow = ''
    }
  }, [open, onClose])

  if (!open) return null

  return (
    <div
      ref={overlayRef}
      onClick={(e) => { if (e.target === overlayRef.current) onClose() }}
      aria-label="Modal overlay"
      role="dialog"
      aria-modal="true"
      style={{
        position: 'fixed', inset: 0, zIndex: 1000,
        display: 'flex', alignItems: 'center', justifyContent: 'center',
        background: '#F3F4F6', backdropFilter: 'blur(4px)',
        animation: 'fadeIn 0.15s ease-out',
      }}
    >
      <div style={{
        background: '#FFFFFF', borderRadius: 12, width: '90%', maxWidth: width,
        maxHeight: '85vh', overflow: 'auto',
        border: '1px solid #E5E7EB',
        boxShadow: '0 24px 48px rgba(0,0,0,0.12)',
      }}>
        <div style={{
          display: 'flex', alignItems: 'center', justifyContent: 'space-between',
          padding: '20px 24px', borderBottom: '1px solid #E5E7EB',
        }}>
          <h2 style={{ fontSize: 18, fontWeight: 600, color: '#111827' }}>{title}</h2>
          <button
            onClick={onClose}
            aria-label="Cerrar modal"
            style={{
              background: 'none', border: 'none', color: '#9CA3AF',
              fontSize: 20, padding: 4, lineHeight: 1, cursor: 'pointer',
            }}
          >
            <svg width="20" height="20" viewBox="0 0 20 20" fill="none">
              <path d="M5 5l10 10M15 5L5 15" stroke="currentColor" strokeWidth="2" strokeLinecap="round"/>
            </svg>
          </button>
        </div>
        <div style={{ padding: 24 }}>
          {children}
        </div>
      </div>
    </div>
  )
}
