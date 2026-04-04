import { useEffect } from 'react'

/**
 * Calls `onSubmit` when Ctrl+Enter or Cmd+Enter is pressed.
 * Usage: useCtrlEnter(handleSubmit, !disabled)
 */
export function useCtrlEnter(onSubmit, enabled = true) {
  useEffect(() => {
    if (!enabled) return
    const handler = (e) => {
      if ((e.ctrlKey || e.metaKey) && e.key === 'Enter') {
        e.preventDefault()
        onSubmit()
      }
    }
    window.addEventListener('keydown', handler)
    return () => window.removeEventListener('keydown', handler)
  }, [onSubmit, enabled])
}
