import { useState, useEffect, useCallback } from 'react'
import { t } from '../i18n/translations'

const TOUR_STEPS = [
  {
    page: 'dashboard',
    titleKey: 'dashboard',
    descKey: 'tourStep1',
    // Tooltip positioned below the KPI cards area (top of main content)
    tooltipTop: 260,
    tooltipLeft: 300,
    tooltipPosition: 'bottom',
    // Spotlight: KPI area at the top of dashboard content
    spotlightTop: 100,
    spotlightLeft: 280,
    spotlightWidth: 'calc(100% - 320px)',
    spotlightHeight: 140,
  },
  {
    page: 'workflows',
    titleKey: 'workflows',
    descKey: 'tourStep2',
    tooltipTop: 320,
    tooltipLeft: 300,
    tooltipPosition: 'bottom',
    spotlightTop: 100,
    spotlightLeft: 280,
    spotlightWidth: 'calc(100% - 320px)',
    spotlightHeight: 200,
  },
  {
    page: 'executions',
    titleKey: 'executions',
    descKey: 'tourStep3',
    tooltipTop: 320,
    tooltipLeft: 300,
    tooltipPosition: 'bottom',
    spotlightTop: 100,
    spotlightLeft: 280,
    spotlightWidth: 'calc(100% - 320px)',
    spotlightHeight: 200,
  },
  {
    page: 'agents',
    titleKey: 'agents',
    descKey: 'tourStep4',
    tooltipTop: 320,
    tooltipLeft: 300,
    tooltipPosition: 'bottom',
    spotlightTop: 130,
    spotlightLeft: 280,
    spotlightWidth: 'calc(100% - 320px)',
    spotlightHeight: 260,
  },
  {
    page: 'swarms',
    titleKey: 'swarms',
    descKey: 'tourStep5',
    tooltipTop: 320,
    tooltipLeft: 300,
    tooltipPosition: 'bottom',
    spotlightTop: 100,
    spotlightLeft: 280,
    spotlightWidth: 'calc(100% - 320px)',
    spotlightHeight: 260,
  },
  {
    page: 'documents',
    titleKey: 'documents',
    descKey: 'tourStep6',
    tooltipTop: 320,
    tooltipLeft: 300,
    tooltipPosition: 'bottom',
    spotlightTop: 100,
    spotlightLeft: 280,
    spotlightWidth: 'calc(100% - 320px)',
    spotlightHeight: 200,
  },
  {
    page: null, // stay on current page
    titleKey: 'chat',
    descKey: 'tourStep7',
    // Tooltip near the bottom-right chat bubble
    tooltipTop: null, // computed: bottom-right
    tooltipLeft: null,
    tooltipPosition: 'left',
    // Spotlight: the chat bubble area bottom-right
    spotlightTop: null, // computed
    spotlightLeft: null,
    spotlightWidth: 60,
    spotlightHeight: 60,
  },
]

export default function OnboardingTour({ lang, onNavigate, onComplete }) {
  const [step, setStep] = useState(-1) // -1 = welcome screen
  const [fadeIn, setFadeIn] = useState(true)
  const [ready, setReady] = useState(false) // delay showing tooltip after navigation

  // Fade transition on step change
  useEffect(() => {
    setFadeIn(false)
    setReady(false)
    const fadeTimer = setTimeout(() => setFadeIn(true), 50)
    const readyTimer = setTimeout(() => setReady(true), 350)
    return () => { clearTimeout(fadeTimer); clearTimeout(readyTimer) }
  }, [step])

  // Navigate to the correct page when step changes
  useEffect(() => {
    if (step >= 0 && step < TOUR_STEPS.length) {
      const s = TOUR_STEPS[step]
      if (s.page) {
        onNavigate(s.page)
      }
    }
  }, [step, onNavigate])

  const handleNext = () => {
    if (step < TOUR_STEPS.length - 1) {
      setStep(step + 1)
    } else {
      handleFinish()
    }
  }

  const handlePrev = () => {
    if (step > 0) setStep(step - 1)
  }

  const handleFinish = () => {
    onComplete()
  }

  const totalSteps = TOUR_STEPS.length
  const isWelcome = step === -1
  const isLast = step === totalSteps - 1
  const progress = isWelcome ? 0 : ((step + 1) / totalSteps) * 100

  // Welcome screen
  if (isWelcome) {
    return (
      <div
        style={{
          position: 'fixed', inset: 0, zIndex: 9999,
          display: 'flex', alignItems: 'center', justifyContent: 'center',
          background: 'rgba(0, 0, 0, 0.75)', backdropFilter: 'blur(4px)',
        }}
        aria-label="Onboarding tour overlay"
        role="dialog"
        aria-modal="true"
      >
        <div
          style={{
            background: '#161E2E', borderRadius: 16,
            border: '1px solid rgba(99, 102, 241, 0.3)',
            padding: '48px 40px', maxWidth: 520, width: '90%', textAlign: 'center',
            opacity: fadeIn ? 1 : 0,
            transform: fadeIn ? 'translateY(0) scale(1)' : 'translateY(12px) scale(0.98)',
            transition: 'opacity 0.3s ease, transform 0.3s ease',
            boxShadow: '0 25px 60px rgba(0, 0, 0, 0.5), 0 0 40px rgba(99, 102, 241, 0.1)',
          }}
        >
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
        </div>
      </div>
    )
  }

  // Tour step with spotlight overlay + tooltip
  const currentStep = TOUR_STEPS[step]
  const isChatStep = step === 6

  // Compute spotlight and tooltip positions
  const spotTop = isChatStep ? 'calc(100vh - 80px)' : `${currentStep.spotlightTop}px`
  const spotLeft = isChatStep ? 'calc(100vw - 80px)' : `${currentStep.spotlightLeft}px`
  const spotW = isChatStep ? '60px' : currentStep.spotlightWidth
  const spotH = isChatStep ? '60px' : `${currentStep.spotlightHeight}px`

  // Tooltip position
  let tooltipStyle = {}
  if (isChatStep) {
    tooltipStyle = {
      position: 'fixed', bottom: 90, right: 24, maxWidth: 380,
    }
  } else {
    tooltipStyle = {
      position: 'fixed',
      top: currentStep.tooltipTop,
      left: currentStep.tooltipLeft,
      maxWidth: 420,
    }
  }

  // Arrow direction
  const arrowOnTop = currentStep.tooltipPosition === 'bottom'
  const arrowOnBottom = currentStep.tooltipPosition === 'top'
  const arrowOnRight = currentStep.tooltipPosition === 'left'

  return (
    <>
      <style>{`
        @keyframes nxfTourPulse {
          0%, 100% { box-shadow: 0 0 0 0 rgba(99,102,241,0.4); }
          50% { box-shadow: 0 0 0 8px rgba(99,102,241,0); }
        }
        @keyframes nxfTourFade {
          from { opacity: 0; transform: translateY(8px); }
          to { opacity: 1; transform: translateY(0); }
        }
      `}</style>

      {/* Full-screen overlay with SVG mask for spotlight hole */}
      <div
        style={{
          position: 'fixed', inset: 0, zIndex: 9998,
          pointerEvents: 'none',
        }}
        aria-label="Tour overlay"
      >
        <svg width="100%" height="100%" style={{ position: 'absolute', inset: 0 }}>
          <defs>
            <mask id="nxf-tour-mask">
              <rect width="100%" height="100%" fill="white" />
              <rect
                x={spotLeft} y={spotTop}
                width={spotW} height={spotH}
                rx="12" fill="black"
              />
            </mask>
          </defs>
          <rect width="100%" height="100%" fill="rgba(0,0,0,0.7)" mask="url(#nxf-tour-mask)" />
        </svg>

        {/* Spotlight border ring */}
        {ready && (
          <div style={{
            position: 'fixed',
            top: spotTop, left: spotLeft,
            width: spotW, height: spotH,
            border: '2px solid rgba(99,102,241,0.5)',
            borderRadius: 12,
            animation: 'nxfTourPulse 2s infinite',
            pointerEvents: 'none',
          }} />
        )}
      </div>

      {/* Tooltip card */}
      {ready && (
        <div
          role="dialog"
          aria-modal="false"
          aria-label={`${t('tourStep' + (step + 1), lang)}`}
          style={{
            ...tooltipStyle,
            zIndex: 9999,
            background: '#161E2E',
            borderRadius: 14,
            border: '1px solid rgba(99,102,241,0.3)',
            padding: '20px 24px',
            boxShadow: '0 16px 48px rgba(0,0,0,0.6), 0 0 30px rgba(99,102,241,0.1)',
            opacity: fadeIn ? 1 : 0,
            transform: fadeIn ? 'translateY(0)' : 'translateY(8px)',
            transition: 'opacity 0.3s ease, transform 0.3s ease',
            animation: 'nxfTourFade 0.35s ease',
          }}
        >
          {/* Arrow pointing up (when tooltip is below spotlight) */}
          {arrowOnTop && (
            <div style={{
              position: 'absolute', top: -8, left: 40,
              width: 0, height: 0,
              borderLeft: '8px solid transparent',
              borderRight: '8px solid transparent',
              borderBottom: '8px solid rgba(99,102,241,0.3)',
            }} />
          )}

          {/* Arrow pointing down (when tooltip is above spotlight) */}
          {arrowOnBottom && (
            <div style={{
              position: 'absolute', bottom: -8, left: 40,
              width: 0, height: 0,
              borderLeft: '8px solid transparent',
              borderRight: '8px solid transparent',
              borderTop: '8px solid rgba(99,102,241,0.3)',
            }} />
          )}

          {/* Arrow pointing right (for chat step) */}
          {arrowOnRight && (
            <div style={{
              position: 'absolute', right: -8, bottom: 20,
              width: 0, height: 0,
              borderTop: '8px solid transparent',
              borderBottom: '8px solid transparent',
              borderLeft: '8px solid rgba(99,102,241,0.3)',
            }} />
          )}

          {/* Step counter badge */}
          <div style={{
            fontSize: 11, fontWeight: 700, color: '#818CF8',
            letterSpacing: '0.08em', marginBottom: 10,
            display: 'flex', alignItems: 'center', gap: 8,
          }}>
            <span style={{
              padding: '2px 8px', borderRadius: 4,
              background: 'rgba(99,102,241,0.15)',
            }}>
              {step + 1} / {totalSteps}
            </span>
          </div>

          {/* Step title */}
          <h3 style={{
            fontSize: 17, fontWeight: 700, color: '#E5E7EB', margin: '0 0 8px',
          }}>
            {t(currentStep.titleKey, lang)}
          </h3>

          {/* Step description */}
          <p style={{
            fontSize: 14, color: '#9CA3AF', lineHeight: 1.6, margin: '0 0 20px',
          }}>
            {t(currentStep.descKey, lang)}
          </p>

          {/* Progress dots */}
          <div style={{
            display: 'flex', gap: 4, marginBottom: 16, justifyContent: 'center',
          }}>
            {Array.from({ length: totalSteps }, (_, i) => (
              <div
                key={i}
                style={{
                  width: i === step ? 20 : 6, height: 6, borderRadius: 3,
                  background: i === step
                    ? 'linear-gradient(90deg, #6366F1, #8B5CF6)'
                    : i < step
                      ? '#6366F1'
                      : 'rgba(255,255,255,0.1)',
                  transition: 'all 0.3s ease',
                }}
              />
            ))}
          </div>

          {/* Controls */}
          <div style={{
            display: 'flex', justifyContent: 'space-between', alignItems: 'center',
          }}>
            <button
              onClick={handleFinish}
              aria-label={t('skip', lang)}
              style={{
                padding: '8px 14px', borderRadius: 8,
                border: '1px solid rgba(255,255,255,0.08)',
                background: 'transparent', color: '#6B7280', fontSize: 12,
                fontWeight: 500, cursor: 'pointer', transition: 'all 0.15s',
              }}
              onMouseEnter={(e) => { e.currentTarget.style.borderColor = 'rgba(255,255,255,0.15)'; e.currentTarget.style.color = '#9CA3AF' }}
              onMouseLeave={(e) => { e.currentTarget.style.borderColor = 'rgba(255,255,255,0.08)'; e.currentTarget.style.color = '#6B7280' }}
            >
              {t('skip', lang)}
            </button>

            <div style={{ display: 'flex', gap: 8 }}>
              {step > 0 && (
                <button
                  onClick={handlePrev}
                  aria-label={t('back', lang)}
                  style={{
                    padding: '8px 16px', borderRadius: 8,
                    border: '1px solid rgba(99,102,241,0.2)',
                    background: 'transparent', color: '#818CF8', fontSize: 13,
                    fontWeight: 500, cursor: 'pointer', transition: 'all 0.15s',
                  }}
                  onMouseEnter={(e) => e.currentTarget.style.borderColor = 'rgba(99,102,241,0.4)'}
                  onMouseLeave={(e) => e.currentTarget.style.borderColor = 'rgba(99,102,241,0.2)'}
                >
                  {t('back', lang)}
                </button>
              )}
              <button
                onClick={handleNext}
                aria-label={isLast ? t('finish', lang) : t('next', lang)}
                style={{
                  padding: '8px 22px', borderRadius: 8, border: 'none',
                  background: 'linear-gradient(135deg, #6366F1, #8B5CF6)',
                  color: '#fff', fontSize: 13, fontWeight: 600, cursor: 'pointer',
                  transition: 'all 0.2s',
                  boxShadow: '0 4px 15px rgba(99, 102, 241, 0.3)',
                }}
                onMouseEnter={(e) => e.currentTarget.style.boxShadow = '0 6px 20px rgba(99, 102, 241, 0.5)'}
                onMouseLeave={(e) => e.currentTarget.style.boxShadow = '0 4px 15px rgba(99, 102, 241, 0.3)'}
              >
                {isLast ? t('finish', lang) : t('next', lang)}
              </button>
            </div>
          </div>

          {/* Progress bar */}
          <div style={{
            height: 3, borderRadius: 2, background: 'rgba(255,255,255,0.06)',
            overflow: 'hidden', marginTop: 14,
          }}>
            <div style={{
              height: '100%', borderRadius: 2, width: `${progress}%`,
              background: 'linear-gradient(90deg, #6366F1, #8B5CF6)',
              transition: 'width 0.4s ease',
            }} />
          </div>
        </div>
      )}
    </>
  )
}
