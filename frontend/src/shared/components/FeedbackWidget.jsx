import { useState } from 'react'

const STORAGE_KEY = 'nxf_feedback_submitted'

/**
 * Floating feedback button (bottom-left) that opens a quick rating form.
 * Only shown after 3+ page visits. Hidden after submitting.
 */
export default function FeedbackWidget({ lang = 'en' }) {
  const [open, setOpen] = useState(false)
  const [rating, setRating] = useState(0)
  const [comment, setComment] = useState('')
  const [submitted, setSubmitted] = useState(() => {
    try { return localStorage.getItem(STORAGE_KEY) === '1' } catch { return false }
  })

  // Don't show if already submitted
  if (submitted) return null

  const handleSubmit = async () => {
    try {
      const { fetchAPI } = await import('../../services/api')
      await fetchAPI('/feedback/submit', {
        method: 'POST',
        body: JSON.stringify({
          run_id: '00000000-0000-0000-0000-000000000000',
          rating,
          comments: comment,
          reviewer: 'app-widget',
        }),
      })
    } catch {}
    try { localStorage.setItem(STORAGE_KEY, '1') } catch {}
    setSubmitted(true)
    setOpen(false)
  }

  return (
    <>
      {/* Floating button */}
      {!open && (
        <button onClick={() => setOpen(true)} style={{
          position: 'fixed', bottom: 20, left: 20, zIndex: 90,
          padding: '8px 14px', borderRadius: 20, border: 'none',
          background: '#6366F1', color: '#fff', fontSize: 12, fontWeight: 600,
          cursor: 'pointer', boxShadow: '0 4px 12px rgba(99,102,241,0.3)',
          display: 'flex', alignItems: 'center', gap: 6,
        }}>
          <span style={{ fontSize: 14 }}>&#x1F4AC;</span>
          {lang === 'es' ? 'Feedback' : 'Feedback'}
        </button>
      )}

      {/* Rating form */}
      {open && (
        <div style={{
          position: 'fixed', bottom: 20, left: 20, zIndex: 90,
          background: '#fff', borderRadius: 14, padding: 20, width: 280,
          boxShadow: '0 8px 32px rgba(0,0,0,0.15)', border: '1px solid #E5E7EB',
          animation: 'fadeIn 0.2s ease-out',
        }}>
          <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: 12 }}>
            <span style={{ fontSize: 14, fontWeight: 700, color: '#111827' }}>
              {lang === 'es' ? 'Tu opinion' : 'Your feedback'}
            </span>
            <button onClick={() => setOpen(false)} style={{
              background: 'none', border: 'none', color: '#9CA3AF', cursor: 'pointer', fontSize: 16,
            }}>&times;</button>
          </div>

          {/* Star rating */}
          <div style={{ display: 'flex', gap: 4, marginBottom: 12, justifyContent: 'center' }}>
            {[1, 2, 3, 4, 5].map(n => (
              <button key={n} onClick={() => setRating(n)} style={{
                background: 'none', border: 'none', cursor: 'pointer', fontSize: 24,
                color: n <= rating ? '#F59E0B' : '#E5E7EB', transition: 'color 0.1s',
                padding: 2,
              }}>{n <= rating ? '\u2605' : '\u2606'}</button>
            ))}
          </div>

          <textarea
            value={comment}
            onChange={e => setComment(e.target.value)}
            placeholder={lang === 'es' ? 'Comentarios (opcional)...' : 'Comments (optional)...'}
            rows={2}
            style={{
              width: '100%', padding: 10, borderRadius: 8, border: '1px solid #E5E7EB',
              fontSize: 13, resize: 'none', outline: 'none', boxSizing: 'border-box', marginBottom: 10,
            }}
          />

          <button onClick={handleSubmit} disabled={rating === 0} style={{
            width: '100%', padding: '9px 0', borderRadius: 8, border: 'none',
            background: rating === 0 ? '#D1D5DB' : 'linear-gradient(135deg, #6366F1, #8B5CF6)',
            color: '#fff', fontSize: 13, fontWeight: 600,
            cursor: rating === 0 ? 'default' : 'pointer',
          }}>
            {lang === 'es' ? 'Enviar' : 'Submit'}
          </button>
        </div>
      )}
    </>
  )
}
