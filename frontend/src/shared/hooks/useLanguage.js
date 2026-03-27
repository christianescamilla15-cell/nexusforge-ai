import { useState, useEffect } from 'react'

export function useLanguage() {
  const [lang, setLang] = useState(() => {
    try { return localStorage.getItem('nxf-lang') || 'en' } catch { return 'en' }
  })

  useEffect(() => {
    try { localStorage.setItem('nxf-lang', lang) } catch { /* storage unavailable */ }
    document.documentElement.lang = lang
  }, [lang])

  const toggle = () => setLang(l => l === 'en' ? 'es' : 'en')

  return { lang, setLang, toggle }
}
