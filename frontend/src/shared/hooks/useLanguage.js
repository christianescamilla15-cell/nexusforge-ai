import { useState, useEffect } from 'react'

export function useLanguage() {
  const [lang, setLang] = useState(() => localStorage.getItem('nxf-lang') || 'en')

  useEffect(() => {
    localStorage.setItem('nxf-lang', lang)
    document.documentElement.lang = lang
  }, [lang])

  const toggle = () => setLang(l => l === 'en' ? 'es' : 'en')

  return { lang, setLang, toggle }
}
