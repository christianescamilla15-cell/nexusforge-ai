import { useState, useEffect } from 'react'
import { t } from '../i18n/translations'

const TOUR_STEPS = [
  { page: 'dashboard', titleKey: 'dashboard', descKey: 'tourStep1' },
  { page: 'workflows', titleKey: 'workflows', descKey: 'tourStep2' },
  { page: 'executions', titleKey: 'executions', descKey: 'tourStep3' },
  { page: 'agents', titleKey: 'agents', descKey: 'tourStep4' },
  { page: 'swarms', titleKey: 'swarms', descKey: 'tourStep5' },
  { page: 'documents', titleKey: 'documents', descKey: 'tourStep6' },
  { page: 'settings', titleKey: 'chat', descKey: 'tourStep7' },
]

export default function OnboardingTour({ lang, onNavigate, onComplete }) {
  const [step, setStep] = useState(-1) // -1 = welcome screen
  const [fadeIn, setFadeIn] = useState(true)

  useEffect(() => {
    setFadeIn(false)
    const timer = setTimeout(() => setFadeIn(true), 50)
    return () => clearTimeout(timer)
  }, [step])

  // Navigate to the correct page when step changes
  useEffect(() => {
    if (step >= 0 && step < TOUR_STEPS.length) {
      onNavigate(TOUR_STEPS[step].page)
    }
  }, [step, onNavigate])

  const handleNext = () => {
    if (step < TOUR_STEPS.length - 1) {
      setStep(step + 1)
    } else {
      handleFinish()
    }
  }

  const handleFinish = () => {
    localStorage.setItem('nxf-tour-done', 'true')
    onComplete()
  }

  const totalSteps = TOUR_STEPS.length
  const isWelcome = step === -1
  const isLast = step === totalSteps - 1
  const progress = isWelcome ? 0 : ((step + 1) / totalSteps) * 100

  return (
    <div
      style={{
        position: 'fixed',
        inset: 0,
        zIndex: 9999,
        display: 'flex',
        alignItems: 'center',
        justifyContent: 'center',
        background: 'rgba(0, 0, 0, 0.75)',
        backdropFilter: 'blur(4px)',
      }}
      aria-label="Onboarding tour overlay"
      role="dialog"
      aria-modal="true"
    >
      <div
        style={{
          background: '#161E2E',
          borderRadius: 16,
          border: '1px solid rgba(99, 102, 241, 0.3)',
          padding: isWelcome ? '48px 40px' : '36px 36px 28px',
          maxWidth: isWelcome ? 520 : 480,
          width: '90%',
          textAlign: 'center',
          opacity: fadeIn ? 1 : 0,
          transform: fadeIn ? 'translateY(0) scale(1)' : 'translateY(12px) scale(0.98)',
          transition: 'opacity 0.3s ease, transform 0.3s ease',
          boxShadow: '0 25px 60px rgba(0, 0, 0, 0.5), 0 0 40px rgba(99, 102, 241, 0.1)',
        }}
      >
        {isWelcome ? (
          <>
            {/* Logo */}
            <div style={{
              width: 64, height: 64, borderRadius: 16,
              background: 'linear-gradient(135deg, #6366F1, #8B5CF6)',
              display: 'flex', alignItems: 'center', justifyContent: 'center',
              margin: '0 auto 24px', fontSize: 24, fontWeight: 700, color: '#fff',
            }}>
              NF
            </div>
            <h1 style={{ fontSize: 26, fontWeight: 700, color: '#E5E7EB', marginBottom: 12 }}>
              {t('welcome', lang)}
            </h1>
            <p style={{ fontSize: 15, color: '#9CA3AF', lineHeight: 1.6, marginBottom: 36 }}>
              {t('welcomeDesc', lang)}
            </p>
            <div style={{ display: 'flex', gap: 12, justifyContent: 'center' }}>
              <button
                onClick={handleFinish}
                aria-label={t('skip', lang)}
                style={{
                  padding: '12px 24px', borderRadius: 10, border: '1px solid rgba(255,255,255,0.1)',
                  background: 'transparent', color: '#9CA3AF', fontSize: 14,
                  fontWeight: 500, cursor: 'pointer', transition: 'all 0.2s',
                }}
                onMouseEnter={(e) => { e.currentTarget.style.borderColor = 'rgba(255,255,255,0.2)'; e.currentTarget.style.color = '#E5E7EB' }}
                onMouseLeave={(e) => { e.currentTarget.style.borderColor = 'rgba(255,255,255,0.1)'; e.currentTarget.style.color = '#9CA3AF' }}
              >
                {t('skip', lang)}
              </button>
              <button
                onClick={() => setStep(0)}
                aria-label={t('next', lang)}
                style={{
                  padding: '12px 32px', borderRadius: 10, border: 'none',
                  background: 'linear-gradient(135deg, #6366F1, #8B5CF6)',
                  color: '#fff', fontSize: 14, fontWeight: 600, cursor: 'pointer',
                  transition: 'all 0.2s', boxShadow: '0 4px 15px rgba(99, 102, 241, 0.3)',
                }}
                onMouseEnter={(e) => e.currentTarget.style.boxShadow = '0 6px 20px rgba(99, 102, 241, 0.5)'}
                onMouseLeave={(e) => e.currentTarget.style.boxShadow = '0 4px 15px rgba(99, 102, 241, 0.3)'}
              >
                {t('next', lang)}
              </button>
            </div>
          </>
        ) : (
          <>
            {/* Step counter */}
            <div style={{
              fontSize: 12, fontWeight: 600, color: '#818CF8', marginBottom: 16,
              letterSpacing: '0.05em',
            }}>
              {step + 1} / {totalSteps}
            </div>

            {/* Step icon circle */}
            <div style={{
              width: 52, height: 52, borderRadius: 14,
              background: 'rgba(99, 102, 241, 0.15)',
              border: '1px solid rgba(99, 102, 241, 0.25)',
              display: 'flex', alignItems: 'center', justifyContent: 'center',
              margin: '0 auto 20px', color: '#818CF8', fontSize: 22, fontWeight: 700,
            }}>
              {step + 1}
            </div>

            {/* Step title */}
            <h2 style={{ fontSize: 20, fontWeight: 700, color: '#E5E7EB', marginBottom: 10 }}>
              {t(TOUR_STEPS[step].titleKey, lang)}
            </h2>

            {/* Step description */}
            <p style={{ fontSize: 14, color: '#9CA3AF', lineHeight: 1.6, marginBottom: 32 }}>
              {t(TOUR_STEPS[step].descKey, lang)}
            </p>

            {/* Buttons */}
            <div style={{ display: 'flex', gap: 12, justifyContent: 'center', marginBottom: 20 }}>
              <button
                onClick={handleFinish}
                aria-label={t('skip', lang)}
                style={{
                  padding: '10px 20px', borderRadius: 8, border: '1px solid rgba(255,255,255,0.1)',
                  background: 'transparent', color: '#9CA3AF', fontSize: 13,
                  fontWeight: 500, cursor: 'pointer', transition: 'all 0.2s',
                }}
                onMouseEnter={(e) => { e.currentTarget.style.borderColor = 'rgba(255,255,255,0.2)'; e.currentTarget.style.color = '#E5E7EB' }}
                onMouseLeave={(e) => { e.currentTarget.style.borderColor = 'rgba(255,255,255,0.1)'; e.currentTarget.style.color = '#9CA3AF' }}
              >
                {t('skip', lang)}
              </button>
              <button
                onClick={handleNext}
                aria-label={isLast ? t('finish', lang) : t('next', lang)}
                style={{
                  padding: '10px 28px', borderRadius: 8, border: 'none',
                  background: 'linear-gradient(135deg, #6366F1, #8B5CF6)',
                  color: '#fff', fontSize: 13, fontWeight: 600, cursor: 'pointer',
                  transition: 'all 0.2s', boxShadow: '0 4px 15px rgba(99, 102, 241, 0.3)',
                }}
                onMouseEnter={(e) => e.currentTarget.style.boxShadow = '0 6px 20px rgba(99, 102, 241, 0.5)'}
                onMouseLeave={(e) => e.currentTarget.style.boxShadow = '0 4px 15px rgba(99, 102, 241, 0.3)'}
              >
                {isLast ? t('finish', lang) : t('next', lang)}
              </button>
            </div>

            {/* Progress bar */}
            <div style={{
              height: 4, borderRadius: 2, background: 'rgba(255,255,255,0.06)',
              overflow: 'hidden',
            }}>
              <div style={{
                height: '100%', borderRadius: 2, width: `${progress}%`,
                background: 'linear-gradient(90deg, #6366F1, #8B5CF6)',
                transition: 'width 0.4s ease',
              }} />
            </div>
          </>
        )}
      </div>
    </div>
  )
}
