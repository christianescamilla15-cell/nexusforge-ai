import { useState, useEffect, useCallback } from 'react'
import { api } from '../../api/client'

export function useAPI(path, deps = []) {
  const [data, setData] = useState(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState(null)
  const [fetchKey, setFetchKey] = useState(0)

  const refetch = useCallback(() => {
    setFetchKey((k) => k + 1)
  }, [])

  useEffect(() => {
    let cancelled = false
    setLoading(true)
    api.get(path)
      .then((d) => {
        if (!cancelled) { setData(d); setError(null) }
      })
      .catch((e) => {
        if (!cancelled) setError(e.message)
      })
      .finally(() => {
        if (!cancelled) setLoading(false)
      })
    return () => { cancelled = true }
  }, [path, fetchKey, ...deps])

  return { data, loading, error, refetch }
}
