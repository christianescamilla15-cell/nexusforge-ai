import { StrictMode } from 'react'
import { createRoot } from 'react-dom/client'
import './styles/globals.css'
import App from './App.jsx'

createRoot(document.getElementById('root')).render(
  <StrictMode>
    <App />
  </StrictMode>,
)

// Web Vitals reporting (logs to console in dev, could send to analytics)
if (typeof window !== 'undefined' && window.performance) {
  const logVital = (name, value) => {
    if (import.meta.env.DEV) console.log(`[Vital] ${name}: ${Math.round(value)}ms`)
  }
  // First Contentful Paint
  const observer = new PerformanceObserver((list) => {
    list.getEntries().forEach(entry => logVital(entry.name, entry.startTime))
  })
  try { observer.observe({ type: 'paint', buffered: true }) } catch {}
}
