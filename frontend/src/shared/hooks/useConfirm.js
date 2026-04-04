import { useState, useCallback } from 'react'

/**
 * Hook for replacing browser confirm() with a ConfirmModal.
 * Returns [confirmState, showConfirm] where:
 * - confirmState: { message, onConfirm, onCancel } or null
 * - showConfirm(message, opts): returns a Promise<boolean>
 */
export function useConfirm() {
  const [state, setState] = useState(null)

  const showConfirm = useCallback((message, opts = {}) => {
    return new Promise((resolve) => {
      setState({
        message,
        confirmLabel: opts.confirmLabel,
        cancelLabel: opts.cancelLabel,
        danger: opts.danger !== false,
        onConfirm: () => { setState(null); resolve(true) },
        onCancel: () => { setState(null); resolve(false) },
      })
    })
  }, [])

  return [state, showConfirm]
}
