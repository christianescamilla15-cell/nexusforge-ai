import { useState, useEffect, useRef, useCallback } from 'react'
import { t } from '../i18n/translations'

// --- Tour Steps (simplified: 3 steps, no auto-actions) ---
const TOUR_STEPS = [
  {
    id: 'welcome',
    page: 'dashboard',
    target: '.nxf-main-content main',
    title: { es: '!Bienvenido a NexusForge!', en: 'Welcome to NexusForge!' },
    desc: {
      es: 'Este es tu dashboard principal. Aqui veras el resumen de tus automatizaciones, ejecuciones y agentes.',
      en: 'This is your main dashboard. Here you\'ll see a summary of your automations, executions and agents.',
    },
  },
  {
    id: 'wizard',
    page: null,
    target: '[data-nav="wizard"]',
    title: { es: 'Crea automatizaciones con AI Wizard', en: 'Create automations with AI Wizard' },
    desc: {
      es: 'Describe lo que quieres automatizar en lenguaje natural y la IA diseñara el flujo optimo para ti.',
      en: 'Describe what you want to automate in plain language and the AI will design the optimal workflow for you.',
    },
  },
  {
    id: 'automations',
    page: null,
    target: '[data-nav="automations"]',
    title: { es: 'O usa plantillas listas para usar', en: 'Or use ready-made templates' },
    desc: {
      es: 'Elige entre plantillas predefinidas como Ticket Triage, Analisis de Documentos o Auto-Respuesta de Email. Un clic para desplegar.',
      en: 'Choose from pre-built templates like Ticket Triage, Document Analysis or Email Auto-Responder. One click to deploy.',
    },
  },
]

// --- Spotlight Overlay ---
function TourSpotlight({ targetRect, padding = 12 }) {
  if (!targetRect) return null
  const { top, left, width, height } = targetRect
  return (
    <div style={{
      position: 'fixed', inset: 0, zIndex: 9998, pointerEvents: 'none',
    }}>
      <div style={{
        position: 'absolute', inset: 0,
        background: 'rgba(0,0,0,0.45)',
        clipPath: `polygon(
          0% 0%, 100% 0%, 100% 100%, 0% 100%,
          0% ${top - padding}px,
          ${left - padding}px ${top - padding}px,
          ${left - padding}px ${top + height + padding}px,
          ${left + width + padding}px ${top + height + padding}px,
          ${left + width + padding}px ${top - padding}px,
          0% ${top - padding}px
        )`,
      }} />
      <div style={{
        position: 'absolute',
        top: top - padding, left: left - padding,
        width: width + padding * 2, height: height + padding * 2,
        border: '2px solid rgba(99,102,241,0.6)',
        borderRadius: 12,
        animation: 'tourPulse 2s ease-in-out infinite',
        pointerEvents: 'none',
      }} />
    </div>
  )
}

// --- Tooltip ---
function TourTooltip({ step, stepIndex, totalSteps, targetRect, lang, onSetLang, onNext, onPrev, onSkip }) {
  let tooltipStyle = {
    position: 'fixed',
    zIndex: 9999,
    background: '#FFFFFF',
    border: '1px solid #E5E7EB',
    borderRadius: 14,
    padding: '20px 22px',
    width: 360,
    maxWidth: 'calc(100vw - 32px)',
    boxShadow: '0 12px 48px rgba(0,0,0,0.12), 0 0 0 1px rgba(99,102,241,0.08)',
    animation: 'tourTooltipIn 0.3s ease-out',
    pointerEvents: 'auto',
  }

  if (targetRect) {
    const viewportH = window.innerHeight
    const viewportW = window.innerWidth
    const spaceBelow = viewportH - (targetRect.top + targetRect.height + 20)
    const spaceAbove = targetRect.top - 20

    if (spaceBelow >= 200) {
      tooltipStyle.top = targetRect.top + targetRect.height + 16
      tooltipStyle.left = Math.max(16, Math.min(targetRect.left, viewportW - 380))
    } else if (spaceAbove >= 200) {
      tooltipStyle.bottom = viewportH - targetRect.top + 16
      tooltipStyle.left = Math.max(16, Math.min(targetRect.left, viewportW - 380))
    } else {
      tooltipStyle.top = Math.max(16, targetRect.top)
      tooltipStyle.left = targetRect.left + targetRect.width + 16
      if (tooltipStyle.left + 360 > viewportW) {
        tooltipStyle.left = Math.max(16, targetRect.left - 376)
      }
    }
  } else {
    tooltipStyle.top = '50%'
    tooltipStyle.left = '50%'
    tooltipStyle.transform = 'translate(-50%, -50%)'
    tooltipStyle.width = 420
  }

  return (
    <div data-tour-tooltip style={tooltipStyle}>
      {/* Step counter badge */}
      <div style={{
        display: 'inline-flex', alignItems: 'center', gap: 6,
        padding: '3px 10px', borderRadius: 12,
        background: 'rgba(99,102,241,0.06)', color: '#6366F1',
        fontSize: 11, fontWeight: 600, marginBottom: 10,
      }}>
        {stepIndex + 1} / {totalSteps}
      </div>

      {/* Title */}
      <h3 style={{
        fontSize: 18, fontWeight: 700, color: '#111827',
        marginBottom: 6, lineHeight: 1.3,
      }}>
        {step.title[lang] || step.title.en}
      </h3>

      {/* Description */}
      <p style={{
        fontSize: 14, color: '#4B5563', lineHeight: 1.5,
        marginBottom: 16,
      }}>
        {step.desc[lang] || step.desc.en}
      </p>

      {/* Language selector on first step */}
      {stepIndex === 0 && onSetLang && (
        <div style={{ display: 'flex', gap: 8, marginBottom: 14 }}>
          {[{ key: 'es', label: 'Español' }, { key: 'en', label: 'English' }].map(opt => (
            <button key={opt.key} onClick={() => onSetLang(opt.key)} style={{
              padding: '6px 16px', borderRadius: 100, fontSize: 13, fontWeight: 600,
              border: '1px solid', cursor: 'pointer',
              borderColor: lang === opt.key ? '#6366F1' : '#E5E7EB',
              background: lang === opt.key ? '#6366F1' : '#FFFFFF',
              color: lang === opt.key ? '#FFFFFF' : '#6B7280',
            }}>{opt.label}</button>
          ))}
        </div>
      )}

      {/* Progress dots */}
      <div style={{
        display: 'flex', gap: 4, marginBottom: 14,
      }}>
        {TOUR_STEPS.map((_, i) => (
          <div key={i} style={{
            width: i === stepIndex ? 20 : 6, height: 6, borderRadius: 3,
            background: i < stepIndex ? '#6366F1' : i === stepIndex ? '#818CF8' : '#E5E7EB',
            transition: 'all 0.3s',
          }} />
        ))}
      </div>

      {/* Buttons */}
      <div style={{ display: 'flex', gap: 8, alignItems: 'center' }}>
        {stepIndex > 0 && (
          <button
            onClick={onPrev}
            style={{
              padding: '8px 16px', borderRadius: 8,
              border: '1px solid #E5E7EB',
              background: '#FFFFFF', color: '#4B5563',
              fontSize: 13, fontWeight: 500, cursor: 'pointer',
              transition: 'all 0.15s',
            }}
          >
            {lang === 'es' ? 'Anterior' : 'Previous'}
          </button>
        )}

        <div style={{ flex: 1 }} />

        <button
          onClick={onSkip}
          style={{
            padding: '8px 16px', borderRadius: 8, border: 'none',
            background: 'transparent', color: '#9CA3AF',
            fontSize: 12, cursor: 'pointer',
            transition: 'all 0.15s',
          }}
        >
          {lang === 'es' ? 'Omitir' : 'Skip'}
        </button>

        <button
          onClick={onNext}
          style={{
            padding: '8px 20px', borderRadius: 8, border: 'none',
            background: '#6366F1',
            color: '#fff', fontSize: 13, fontWeight: 600,
            cursor: 'pointer', transition: 'all 0.15s',
          }}
        >
          {stepIndex === totalSteps - 1
            ? (lang === 'es' ? 'Comenzar' : 'Get Started')
            : (lang === 'es' ? 'Siguiente' : 'Next')}
        </button>
      </div>
    </div>
  )
}

// --- Main OnboardingTour Component ---
export default function OnboardingTour({ lang, onNavigate, onSetLang, onComplete }) {
  const [stepIndex, setStepIndex] = useState(0)
  const [targetRect, setTargetRect] = useState(null)
  const timeoutsRef = useRef([])

  const clearAllTimeouts = useCallback(() => {
    timeoutsRef.current.forEach(t => clearTimeout(t))
    timeoutsRef.current = []
  }, [])

  const addTimeout = useCallback((fn, ms) => {
    const id = setTimeout(fn, ms)
    timeoutsRef.current.push(id)
    return id
  }, [])

  useEffect(() => {
    return () => clearAllTimeouts()
  }, [clearAllTimeouts])

  const currentStep = TOUR_STEPS[stepIndex]

  const measureTarget = useCallback(() => {
    if (!currentStep?.target) {
      setTargetRect(null)
      return
    }
    const el = document.querySelector(currentStep.target)
    if (el) {
      const rect = el.getBoundingClientRect()
      setTargetRect({ top: rect.top, left: rect.left, width: rect.width, height: rect.height })
      if (rect.top < 0 || rect.bottom > window.innerHeight) {
        el.scrollIntoView({ behavior: 'smooth', block: 'center' })
        addTimeout(() => {
          const r2 = el.getBoundingClientRect()
          setTargetRect({ top: r2.top, left: r2.left, width: r2.width, height: r2.height })
        }, 400)
      }
    } else {
      setTargetRect(null)
    }
  }, [currentStep, addTimeout])

  useEffect(() => {
    if (!currentStep) return
    clearAllTimeouts()

    if (currentStep.page) {
      onNavigate(currentStep.page)
    }

    const delay = currentStep.page ? 400 : 100
    addTimeout(() => measureTarget(), delay)
  }, [stepIndex, currentStep, onNavigate, measureTarget, clearAllTimeouts, addTimeout])

  useEffect(() => {
    const handler = () => measureTarget()
    window.addEventListener('resize', handler)
    return () => window.removeEventListener('resize', handler)
  }, [measureTarget])

  const goToStep = useCallback((idx) => {
    if (idx < 0 || idx >= TOUR_STEPS.length) return
    clearAllTimeouts()
    setTargetRect(null)
    setStepIndex(idx)
  }, [clearAllTimeouts])

  const handleNext = useCallback(() => {
    if (stepIndex < TOUR_STEPS.length - 1) {
      goToStep(stepIndex + 1)
    } else {
      onNavigate('dashboard')
      window.scrollTo({ top: 0, behavior: 'smooth' })
      onComplete()
    }
  }, [stepIndex, goToStep, onNavigate, onComplete])

  const handlePrev = useCallback(() => {
    goToStep(stepIndex - 1)
  }, [stepIndex, goToStep])

  const handleSkip = useCallback(() => {
    clearAllTimeouts()
    onNavigate('dashboard')
    window.scrollTo({ top: 0, behavior: 'smooth' })
    onComplete()
  }, [clearAllTimeouts, onNavigate, onComplete])

  return (
    <>
      <style>{tourKeyframes}</style>

      {currentStep?.target && targetRect ? (
        <TourSpotlight targetRect={targetRect} />
      ) : (
        <div style={{
          position: 'fixed', inset: 0, zIndex: 9998,
          background: 'rgba(0,0,0,0.45)',
          pointerEvents: 'none',
        }} />
      )}

      <div style={{
        position: 'fixed', inset: 0, zIndex: 9998,
        pointerEvents: 'auto',
        background: 'transparent',
        cursor: 'pointer',
      }} onClick={(e) => {
        if (e.target.closest('[data-tour-tooltip]') || e.target.closest('button')) return;
        handleNext();
      }}>
        <TourTooltip
          step={currentStep}
          stepIndex={stepIndex}
          totalSteps={TOUR_STEPS.length}
          targetRect={targetRect}
          lang={lang}
          onSetLang={onSetLang}
          onNext={handleNext}
          onPrev={handlePrev}
          onSkip={handleSkip}
        />
      </div>
    </>
  )
}

// --- Keyframes ---
const tourKeyframes = `
@keyframes tourPulse {
  0%, 100% { border-color: rgba(99,102,241,0.5); box-shadow: 0 0 0 0 rgba(99,102,241,0.15); }
  50% { border-color: rgba(99,102,241,0.8); box-shadow: 0 0 20px 4px rgba(99,102,241,0.1); }
}
@keyframes tourTooltipIn {
  from { opacity: 0; transform: translateY(10px); }
  to { opacity: 1; transform: translateY(0); }
}
@keyframes tourFadeIn {
  from { opacity: 0; }
  to { opacity: 1; }
}
`
