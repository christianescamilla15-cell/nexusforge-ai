import { useState, useMemo } from 'react'

const TIPS = [
  { en: 'Press Ctrl+K to quickly search and navigate to any page.', es: 'Presiona Ctrl+K para buscar y navegar rapidamente.' },
  { en: 'Use Ctrl+Enter in any dashboard to run your automation instantly.', es: 'Usa Ctrl+Enter en cualquier dashboard para ejecutar al instante.' },
  { en: 'Star your most-used automations to pin them at the top.', es: 'Marca con estrella tus automatizaciones mas usadas para fijarlas arriba.' },
  { en: 'Export your workflow as JSON to back it up or share with your team.', es: 'Exporta tu workflow como JSON para respaldarlo o compartirlo.' },
  { en: 'The Intelligence Hub combines Enterprise Ops, Doc Intel, and Analyze in one place.', es: 'El Hub de Inteligencia combina Enterprise Ops, Doc Intel y Analisis en un solo lugar.' },
  { en: 'Press ? to see all keyboard shortcuts.', es: 'Presiona ? para ver todos los atajos de teclado.' },
  { en: 'Check the Status page to see real-time health of all services.', es: 'Revisa la pagina de Estado para ver la salud en tiempo real de todos los servicios.' },
  { en: 'Use the Schedule Picker to set up recurring automations.', es: 'Usa el selector de horarios para programar automatizaciones recurrentes.' },
  { en: 'You can clone any automation from its menu to create a quick copy.', es: 'Puedes clonar cualquier automatizacion desde su menu.' },
  { en: 'Export results as CSV from any dashboard for Excel analysis.', es: 'Exporta resultados como CSV desde cualquier dashboard.' },
]

export default function TipOfTheDay({ lang = 'en' }) {
  const [dismissed, setDismissed] = useState(false)

  const tip = useMemo(() => {
    const dayOfYear = Math.floor((Date.now() - new Date(new Date().getFullYear(), 0, 0)) / 86400000)
    return TIPS[dayOfYear % TIPS.length]
  }, [])

  if (dismissed) return null

  return (
    <div style={{
      padding: '10px 16px', borderRadius: 10, marginBottom: 16,
      background: 'rgba(245,158,11,0.06)', border: '1px solid rgba(245,158,11,0.15)',
      display: 'flex', justifyContent: 'space-between', alignItems: 'center', gap: 12,
      fontSize: 13,
    }}>
      <span style={{ color: '#92400E' }}>
        <strong style={{ marginRight: 6 }}>{lang === 'es' ? 'Tip:' : 'Tip:'}</strong>
        {tip[lang] || tip.en}
      </span>
      <button onClick={() => setDismissed(true)} style={{
        background: 'none', border: 'none', color: '#D1D5DB', cursor: 'pointer', fontSize: 16, flexShrink: 0,
      }}>&times;</button>
    </div>
  )
}
