const API_BASE = import.meta.env.VITE_API_URL || 'http://localhost:8000/api'

async function fetchAPI(path, options = {}) {
  const res = await fetch(`${API_BASE}${path}`, {
    headers: { 'Content-Type': 'application/json', ...options.headers },
    ...options,
  })
  if (!res.ok) {
    const error = await res.json().catch(() => ({ detail: res.statusText }))
    throw new Error(error.detail || `HTTP ${res.status}`)
  }
  return res.json()
}

export const api = {
  get: (path) => fetchAPI(path),
  post: (path, data) => fetchAPI(path, { method: 'POST', body: JSON.stringify(data) }),
  put: (path, data) => fetchAPI(path, { method: 'PUT', body: JSON.stringify(data) }),
  del: (path) => fetchAPI(path, { method: 'DELETE' }),
}
