import { useState } from 'react'
import { fetchAPI } from '../../services/api'

const STEPS = [
  { id: 'welcome', icon: '👋' },
  { id: 'org', icon: '🏢' },
  { id: 'first_auto', icon: '⚡' },
  { id: 'done', icon: '🚀' },
]

const TEMPLATES = [
  { id: 'ticket-triage', name: { es: 'Clasificar Tickets', en: 'Ticket Triage' }, icon: '🎫', desc: { es: 'Clasifica tickets de soporte automaticamente', en: 'Auto-classify support tickets' } },
  { id: 'doc-analyzer', name: { es: 'Analizar Documentos', en: 'Analyze Documents' }, icon: '📄', desc: { es: 'Extrae datos clave de documentos', en: 'Extract key data from documents' } },
  { id: 'email-responder', name: { es: 'Responder Emails', en: 'Email Responder' }, icon: '📧', desc: { es: 'Genera respuestas inteligentes a emails', en: 'Generate smart email responses' } },
  { id: 'code-review', name: { es: 'Code Review', en: 'Code Review' }, icon: '🔍', desc: { es: 'Revisa codigo para bugs y seguridad', en: 'Review code for bugs and security' } },
]

export default function WelcomeWizard({ lang = 'es', onComplete, userName }) {
  const [step, setStep] = useState(0)
  const [orgName, setOrgName] = useState('')
  const [selectedTemplate, setSelectedTemplate] = useState(null)
  const [creating, setCreating] = useState(false)

  const t = {
    es: {
      welcomeTitle: `Bienvenido${userName ? `, ${userName}` : ''}!`,
      welcomeDesc: 'NexusForge AI te ayuda a automatizar procesos con 24 agentes inteligentes. Vamos a configurar tu espacio de trabajo.',
      orgTitle: 'Crea tu organizacion',
      orgDesc: 'Tu equipo trabaja dentro de una organizacion. Puedes invitar miembros despues.',
      orgPlaceholder: 'Nombre de tu empresa o equipo',
      templateTitle: 'Elige tu primera automatizacion',
      templateDesc: 'Selecciona una plantilla para empezar. Puedes crear mas despues.',
      doneTitle: 'Todo listo!',
      doneDesc: 'Tu espacio de trabajo esta configurado. Ahora puedes:',
      doneTips: ['Describir automatizaciones en el chat', 'Crear workflows visuales', 'Ejecutar y monitorear agentes', 'Invitar a tu equipo'],
      next: 'Siguiente',
      skip: 'Omitir',
      create: 'Crear organizacion',
      creating: 'Creando...',
      start: 'Comenzar',
      back: 'Atras',
    },
    en: {
      welcomeTitle: `Welcome${userName ? `, ${userName}` : ''}!`,
      welcomeDesc: 'NexusForge AI helps you automate processes with 24 intelligent agents. Let\'s set up your workspace.',
      orgTitle: 'Create your organization',
      orgDesc: 'Your team works within an organization. You can invite members later.',
      orgPlaceholder: 'Company or team name',
      templateTitle: 'Choose your first automation',
      templateDesc: 'Pick a template to get started. You can create more later.',
      doneTitle: 'All set!',
      doneDesc: 'Your workspace is configured. Now you can:',
      doneTips: ['Describe automations in the chat', 'Build visual workflows', 'Execute and monitor agents', 'Invite your team'],
      next: 'Next',
      skip: 'Skip',
      create: 'Create organization',
      creating: 'Creating...',
      start: 'Get Started',
      back: 'Back',
    },
  }[lang] || t.en

  const handleCreateOrg = async () => {
    if (!orgName.trim()) return
    setCreating(true)
    await fetchAPI('/organizations/', {
      method: 'POST',
      body: JSON.stringify({ name: orgName.trim() }),
    })
    setCreating(false)
    setStep(2)
  }

  const handleComplete = async () => {
    // Save consent + wizard completion
    try {
      await fetchAPI('/auth/consent', {
        method: 'POST',
        body: JSON.stringify({ accepted_terms: true, accepted_privacy: true }),
      })
    } catch { /* non-blocking */ }

    try { localStorage.setItem('nxf-wizard-done', '1') } catch {}
    if (onComplete) onComplete()
  }

  const currentStep = STEPS[step]

  return (
    <div style={{
      position: 'fixed', inset: 0, zIndex: 10000,
      background: 'rgba(0,0,0,0.5)', WebkitBackdropFilter: 'blur(8px)', backdropFilter: 'blur(8px)',
      display: 'flex', alignItems: 'center', justifyContent: 'center',
      padding: 16,
    }}>
      <div style={{
        background: '#fff', borderRadius: 20, width: '100%', maxWidth: 520,
        padding: 32, boxShadow: '0 25px 50px rgba(0,0,0,0.15)',
        animation: 'fadeIn 0.3s ease-out',
      }}>
        {/* Progress dots */}
        <div style={{ display: 'flex', justifyContent: 'center', gap: 6, marginBottom: 24 }}>
          {STEPS.map((s, i) => (
            <div key={s.id} style={{
              width: i === step ? 24 : 8, height: 8, borderRadius: 4,
              background: i < step ? '#6366F1' : i === step ? '#818CF8' : '#E5E7EB',
              transition: 'all 0.3s',
            }} />
          ))}
        </div>

        {/* Step icon */}
        <div style={{ textAlign: 'center', fontSize: 48, marginBottom: 16 }}>
          {currentStep.icon}
        </div>

        {/* Step 0: Welcome */}
        {step === 0 && (
          <div style={{ textAlign: 'center' }}>
            <h2 style={{ fontSize: 22, fontWeight: 800, color: '#111827', marginBottom: 8 }}>{t.welcomeTitle}</h2>
            <p style={{ fontSize: 15, color: '#6B7280', lineHeight: 1.6, marginBottom: 24 }}>{t.welcomeDesc}</p>
            <button onClick={() => setStep(1)} style={btnPrimary}>{t.next}</button>
          </div>
        )}

        {/* Step 1: Create Organization */}
        {step === 1 && (
          <div>
            <h2 style={{ fontSize: 20, fontWeight: 800, color: '#111827', marginBottom: 4, textAlign: 'center' }}>{t.orgTitle}</h2>
            <p style={{ fontSize: 14, color: '#6B7280', marginBottom: 20, textAlign: 'center' }}>{t.orgDesc}</p>
            <input
              value={orgName}
              onChange={e => setOrgName(e.target.value)}
              onKeyDown={e => e.key === 'Enter' && handleCreateOrg()}
              placeholder={t.orgPlaceholder}
              autoFocus
              style={{
                width: '100%', padding: '12px 16px', borderRadius: 10,
                border: '1px solid #D1D5DB', fontSize: 15, marginBottom: 16,
                boxSizing: 'border-box',
              }}
            />
            <div style={{ display: 'flex', gap: 8 }}>
              <button onClick={() => setStep(2)} style={btnSecondary}>{t.skip}</button>
              <button onClick={handleCreateOrg} disabled={!orgName.trim() || creating} style={{ ...btnPrimary, flex: 1 }}>
                {creating ? t.creating : t.create}
              </button>
            </div>
          </div>
        )}

        {/* Step 2: Choose Template */}
        {step === 2 && (
          <div>
            <h2 style={{ fontSize: 20, fontWeight: 800, color: '#111827', marginBottom: 4, textAlign: 'center' }}>{t.templateTitle}</h2>
            <p style={{ fontSize: 14, color: '#6B7280', marginBottom: 16, textAlign: 'center' }}>{t.templateDesc}</p>
            <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 10, marginBottom: 20 }}>
              {TEMPLATES.map(tmpl => (
                <button key={tmpl.id} onClick={() => setSelectedTemplate(tmpl.id)} style={{
                  padding: 14, borderRadius: 12, border: `2px solid ${selectedTemplate === tmpl.id ? '#6366F1' : '#E5E7EB'}`,
                  background: selectedTemplate === tmpl.id ? '#EEF2FF' : '#fff',
                  cursor: 'pointer', textAlign: 'left',
                }}>
                  <div style={{ fontSize: 24, marginBottom: 6 }}>{tmpl.icon}</div>
                  <div style={{ fontSize: 13, fontWeight: 700, color: '#111827' }}>{tmpl.name[lang]}</div>
                  <div style={{ fontSize: 11, color: '#6B7280', marginTop: 2 }}>{tmpl.desc[lang]}</div>
                </button>
              ))}
            </div>
            <div style={{ display: 'flex', gap: 8 }}>
              <button onClick={() => setStep(1)} style={btnSecondary}>{t.back}</button>
              <button onClick={() => setStep(3)} style={{ ...btnPrimary, flex: 1 }}>{t.next}</button>
            </div>
          </div>
        )}

        {/* Step 3: Done */}
        {step === 3 && (
          <div style={{ textAlign: 'center' }}>
            <h2 style={{ fontSize: 22, fontWeight: 800, color: '#111827', marginBottom: 8 }}>{t.doneTitle}</h2>
            <p style={{ fontSize: 14, color: '#6B7280', marginBottom: 16 }}>{t.doneDesc}</p>
            <ul style={{ textAlign: 'left', listStyle: 'none', padding: 0, marginBottom: 24 }}>
              {t.doneTips.map((tip, i) => (
                <li key={i} style={{ padding: '6px 0', fontSize: 14, color: '#374151' }}>
                  <span style={{ marginRight: 8, color: '#10B981' }}>✓</span>{tip}
                </li>
              ))}
            </ul>

            {/* Consent */}
            <div style={{ fontSize: 12, color: '#9CA3AF', marginBottom: 16, textAlign: 'left' }}>
              {lang === 'es'
                ? 'Al continuar, aceptas los Terminos de Servicio y la Politica de Privacidad de NexusForge AI.'
                : 'By continuing, you accept the Terms of Service and Privacy Policy of NexusForge AI.'}
            </div>

            <button onClick={handleComplete} style={btnPrimary}>{t.start}</button>
          </div>
        )}
      </div>
    </div>
  )
}

const btnPrimary = {
  padding: '12px 24px', borderRadius: 10, border: 'none',
  background: 'linear-gradient(135deg, #6366F1, #8B5CF6)',
  color: '#fff', fontWeight: 700, fontSize: 15, cursor: 'pointer',
  width: '100%',
}

const btnSecondary = {
  padding: '12px 24px', borderRadius: 10, border: '1px solid #E5E7EB',
  background: '#fff', color: '#6B7280', fontWeight: 500, fontSize: 14, cursor: 'pointer',
}
