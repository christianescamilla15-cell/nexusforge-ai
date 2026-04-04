import { useState, useEffect } from 'react'
import { fetchAPI } from '../services/api'
import SmartDashboard from '../features/automations/dashboards/SmartDashboard'
import Breadcrumb from '../shared/components/Breadcrumb'

export default function SmartDashboardPage({ automationId, onBack, onRun, lang }) {
  const [automationName, setAutomationName] = useState('')

  useEffect(() => {
    if (!automationId) return
    fetchAPI(`/automations/${automationId}`).then(res => {
      if (!res.error && res.data?.name) {
        setAutomationName(res.data.name)
      }
    })
  }, [automationId])

  return (
    <div style={{ animation: 'fadeIn 0.3s ease-out' }}>
      <Breadcrumb
        lang={lang}
        items={[
          { label: lang === 'es' ? 'Automatizaciones' : 'Automations', onClick: onBack },
          { label: automationName || (lang === 'es' ? 'Cargando...' : 'Loading...') },
        ]}
      />

      <SmartDashboard
        automationId={automationId}
        lang={lang}
        onBack={onBack}
        onRun={onRun}
      />

      <style>{`@keyframes fadeIn { from { opacity: 0; transform: translateY(8px) } to { opacity: 1; transform: none } }`}</style>
    </div>
  )
}
