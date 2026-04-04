import { useEffect, useRef } from 'react'

/**
 * Calls `onRefresh` when the browser tab regains focus after being hidden for `staleAfterMs`.
 * Prevents over-fetching by tracking last refresh time.
 */
export function useRefreshOnFocus(onRefresh, staleAfterMs = 30000) {
  const lastRefresh = useRef(Date.now())

  useEffect(() => {
    const handler = () => {
      if (document.visibilityState === 'visible') {
        const elapsed = Date.now() - lastRefresh.current
        if (elapsed >= staleAfterMs) {
          lastRefresh.current = Date.now()
          onRefresh()
        }
      }
    }
    document.addEventListener('visibilitychange', handler)
    return () => document.removeEventListener('visibilitychange', handler)
  }, [onRefresh, staleAfterMs])
}
