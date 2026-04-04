import { useEffect, useState } from 'react'
import { useLocation } from 'react-router-dom'

/**
 * Slim loading bar at the very top of the viewport during route transitions.
 * Triggers on every location change, animates for 400ms.
 */
export default function TopLoadingBar() {
  const location = useLocation()
  const [loading, setLoading] = useState(false)
  const [progress, setProgress] = useState(0)

  useEffect(() => {
    setLoading(true)
    setProgress(30)
    const t1 = setTimeout(() => setProgress(70), 100)
    const t2 = setTimeout(() => setProgress(100), 250)
    const t3 = setTimeout(() => { setLoading(false); setProgress(0) }, 400)
    return () => { clearTimeout(t1); clearTimeout(t2); clearTimeout(t3) }
  }, [location.pathname])

  if (!loading && progress === 0) return null

  return (
    <div style={{
      position: 'fixed', top: 0, left: 0, right: 0, height: 3, zIndex: 9999,
      pointerEvents: 'none',
    }}>
      <div style={{
        height: '100%',
        background: 'linear-gradient(90deg, #6366F1, #8B5CF6, #A78BFA)',
        width: `${progress}%`,
        transition: loading ? 'width 0.3s ease' : 'width 0.15s ease, opacity 0.3s',
        opacity: progress === 100 ? 0 : 1,
        borderRadius: '0 2px 2px 0',
        boxShadow: '0 0 8px rgba(99,102,241,0.4)',
      }} />
    </div>
  )
}
