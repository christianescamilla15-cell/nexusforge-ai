import { useState, useCallback, createContext, useContext } from 'react'

const ToastContext = createContext(null)

export function useToastState() {
  const [toasts, setToasts] = useState([])

  const show = useCallback((message, type = 'info') => {
    const id = Date.now() + Math.random()
    setToasts(prev => [...prev, { id, message, type }])
    setTimeout(() => setToasts(prev => prev.filter(t => t.id !== id)), 5000)
  }, [])

  const dismiss = useCallback((id) => {
    setToasts(prev => prev.filter(t => t.id !== id))
  }, [])

  return { toasts, show, dismiss }
}

export function useToast() {
  const ctx = useContext(ToastContext)
  if (!ctx) {
    // Fallback: return a no-op if not wrapped in provider
    return { toasts: [], show: () => {}, dismiss: () => {} }
  }
  return ctx
}

export { ToastContext }
