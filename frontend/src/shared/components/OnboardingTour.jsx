import { useState, useEffect, useRef, useCallback } from 'react'
import { t } from '../i18n/translations'

// ─── Tour Steps ──────────────────────────────────────────────────────────────
const TOUR_STEPS = [
  { id: 'welcome', page: null, target: null, action: null, wait: 0 },
  { id: 'dashboard', page: 'dashboard', target: '[data-tour="dashboard-kpis"]', action: null, wait: 1200 },
  { id: 'workflows', page: 'workflows', target: '[data-tour="workflow-table"]', action: 'clickFirstWorkflowRow', wait: 1000 },
  { id: 'executions', page: 'executions', target: '[data-tour="execution-table"]', action: 'clickFirstExecutionRow', wait: 1000 },
  // execution-detail removed — can't navigate without real workflow selection
  { id: 'agents', page: 'agents', target: '[data-tour="agent-grid"]', action: 'clickFirstAgent', wait: 1000 },
  { id: 'swarms', page: 'swarms', target: '[data-tour="swarm-grid"]', action: null, wait: 500 },
  { id: 'memory', page: 'memory', target: '[data-tour="memory-input"]', action: 'storeMemory', wait: 4000 },
  { id: 'healing', page: 'healing', target: '[data-tour="healing-simulator"]', action: 'simulateFailure', wait: 7000 },
  { id: 'documents', page: 'documents', target: '[data-tour="semantic-search"]', action: 'searchDocs', wait: 1500 },
  { id: 'chat', page: null, target: '[data-tour="chat-button"]', action: 'openChat', wait: 2000 },
  { id: 'final', page: 'dashboard', target: null, action: 'scrollTop', wait: 500 },
]

// ─── Helper: type into a React-controlled input ─────────────────────────────
function typeIntoInput(selector, text) {
  const el = document.querySelector(selector)
  if (!el) return false
  const nativeSetter = Object.getOwnPropertyDescriptor(window.HTMLInputElement.prototype, 'value')?.set
  if (nativeSetter) {
    nativeSetter.call(el, text)
    el.dispatchEvent(new Event('input', { bubbles: true }))
  }
  // Also fire change for some React versions
  el.dispatchEvent(new Event('change', { bubbles: true }))
  return true
}

function clickElement(selector) {
  const el = document.querySelector(selector)
  if (!el) return false
  el.dispatchEvent(new MouseEvent('click', { bubbles: true, cancelable: true }))
  return true
}

// ─── Spotlight Overlay ───────────────────────────────────────────────────────
function TourSpotlight({ targetRect, padding = 12 }) {
  if (!targetRect) return null
  const { top, left, width, height } = targetRect
  return (
    <div style={{
      position: 'fixed', inset: 0, zIndex: 9998, pointerEvents: 'none',
    }}>
      {/* Dark overlay with cutout */}
      <div style={{
        position: 'absolute', inset: 0,
        background: 'rgba(0,0,0,0.7)',
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
      {/* Spotlight border (pulsing) */}
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

// ─── Tooltip ─────────────────────────────────────────────────────────────────
function TourTooltip({ step, stepIndex, totalSteps, targetRect, lang, actionRunning, onNext, onPrev, onSkip }) {
  const stepTitles = {
    welcome: 'tourStepWelcome',
    dashboard: 'tourStepDashboard',
    workflows: 'tourStepWorkflows',
    executions: 'tourStepExecutions',
    'execution-detail': 'tourStepExecutionDetail',
    agents: 'tourStepAgents',
    swarms: 'tourStepSwarms',
    memory: 'tourStepMemory',
    healing: 'tourStepHealing',
    documents: 'tourStepDocuments',
    chat: 'tourStepChat',
    final: 'tourStepFinal',
  }
  const stepDescs = {
    welcome: 'tourStepWelcomeDesc',
    dashboard: 'tourStepDashboardDesc',
    workflows: 'tourStepWorkflowsDesc',
    executions: 'tourStepExecutionsDesc',
    'execution-detail': 'tourStepExecutionDetailDesc',
    agents: 'tourStepAgentsDesc',
    swarms: 'tourStepSwarmsDesc',
    memory: 'tourStepMemoryDesc',
    healing: 'tourStepHealingDesc',
    documents: 'tourStepDocumentsDesc',
    chat: 'tourStepChatDesc',
    final: 'tourStepFinalDesc',
  }

  // Position below or to the right of target
  let tooltipStyle = {
    position: 'fixed',
    zIndex: 9999,
    background: '#1A1F2E',
    border: '1px solid rgba(99,102,241,0.4)',
    borderRadius: 14,
    padding: '20px 22px',
    width: 360,
    maxWidth: 'calc(100vw - 32px)',
    boxShadow: '0 12px 48px rgba(0,0,0,0.6), 0 0 0 1px rgba(99,102,241,0.15)',
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
    // Center on screen (welcome / final)
    tooltipStyle.top = '50%'
    tooltipStyle.left = '50%'
    tooltipStyle.transform = 'translate(-50%, -50%)'
    tooltipStyle.width = 420
  }

  return (
    <div style={tooltipStyle}>
      {/* Step counter badge */}
      <div style={{
        display: 'inline-flex', alignItems: 'center', gap: 6,
        padding: '3px 10px', borderRadius: 12,
        background: 'rgba(99,102,241,0.15)', color: '#A5B4FC',
        fontSize: 11, fontWeight: 600, marginBottom: 10,
      }}>
        {stepIndex + 1} / {totalSteps}
      </div>

      {/* Title */}
      <h3 style={{
        fontSize: 18, fontWeight: 700, color: '#E5E7EB',
        marginBottom: 6, lineHeight: 1.3,
      }}>
        {t(stepTitles[step.id], lang)}
      </h3>

      {/* Description */}
      <p style={{
        fontSize: 14, color: '#9CA3AF', lineHeight: 1.5,
        marginBottom: 16,
      }}>
        {t(stepDescs[step.id], lang)}
      </p>

      {/* Action running indicator */}
      {actionRunning && (
        <div style={{
          display: 'flex', alignItems: 'center', gap: 8,
          padding: '8px 12px', borderRadius: 8, marginBottom: 14,
          background: 'rgba(99,102,241,0.1)',
          border: '1px solid rgba(99,102,241,0.2)',
        }}>
          <div style={{
            width: 8, height: 8, borderRadius: '50%',
            background: '#6366F1',
            animation: 'tourActionPulse 1s ease-in-out infinite',
          }} />
          <span style={{ fontSize: 12, color: '#A5B4FC', fontWeight: 500 }}>
            {t('watchingDemo', lang)}
          </span>
        </div>
      )}

      {/* Progress dots */}
      <div style={{
        display: 'flex', gap: 4, marginBottom: 14, flexWrap: 'wrap',
      }}>
        {TOUR_STEPS.map((_, i) => (
          <div key={i} style={{
            width: i === stepIndex ? 20 : 6, height: 6, borderRadius: 3,
            background: i < stepIndex ? '#6366F1' : i === stepIndex ? '#818CF8' : 'rgba(255,255,255,0.1)',
            transition: 'all 0.3s',
          }} />
        ))}
      </div>

      {/* Buttons */}
      <div style={{ display: 'flex', gap: 8, alignItems: 'center' }}>
        {stepIndex > 0 && !actionRunning && (
          <button
            onClick={onPrev}
            style={{
              padding: '8px 16px', borderRadius: 8,
              border: '1px solid rgba(255,255,255,0.1)',
              background: 'transparent', color: '#9CA3AF',
              fontSize: 13, fontWeight: 500, cursor: 'pointer',
              transition: 'all 0.15s',
            }}
          >
            {t('prev', lang)}
          </button>
        )}

        <div style={{ flex: 1 }} />

        {!actionRunning && (
          <button
            onClick={onSkip}
            style={{
              padding: '8px 16px', borderRadius: 8, border: 'none',
              background: 'transparent', color: '#6B7280',
              fontSize: 12, cursor: 'pointer',
              transition: 'all 0.15s',
            }}
          >
            {t('skip', lang)}
          </button>
        )}

        {!actionRunning && (
          <button
            onClick={onNext}
            style={{
              padding: '8px 20px', borderRadius: 8, border: 'none',
              background: 'linear-gradient(135deg, #6366F1, #8B5CF6)',
              color: '#fff', fontSize: 13, fontWeight: 600,
              cursor: 'pointer', transition: 'all 0.15s',
            }}
          >
            {stepIndex === totalSteps - 1 ? t('finish', lang) : t('next', lang)}
          </button>
        )}
      </div>
    </div>
  )
}

// ─── Completion Modal ────────────────────────────────────────────────────────
function CompletionModal({ lang, onRestart, onExplore }) {
  return (
    <div style={{
      position: 'fixed', inset: 0, zIndex: 10000,
      display: 'flex', alignItems: 'center', justifyContent: 'center',
      background: 'rgba(0,0,0,0.8)',
      animation: 'tourFadeIn 0.4s ease-out',
    }}>
      <div style={{
        background: '#1A1F2E',
        border: '1px solid rgba(99,102,241,0.4)',
        borderRadius: 20, padding: '36px 40px',
        maxWidth: 460, width: '90%',
        textAlign: 'center',
        animation: 'tourScaleIn 0.4s ease-out',
        boxShadow: '0 24px 64px rgba(0,0,0,0.5)',
      }}>
        {/* Success icon */}
        <div style={{
          width: 64, height: 64, borderRadius: '50%',
          background: 'linear-gradient(135deg, #6366F1, #8B5CF6)',
          display: 'flex', alignItems: 'center', justifyContent: 'center',
          margin: '0 auto 20px',
          boxShadow: '0 0 30px rgba(99,102,241,0.3)',
        }}>
          <svg width="32" height="32" viewBox="0 0 24 24" fill="none" stroke="#fff" strokeWidth="2.5" strokeLinecap="round" strokeLinejoin="round">
            <polyline points="20 6 9 17 4 12" />
          </svg>
        </div>

        <h2 style={{ fontSize: 24, fontWeight: 700, color: '#E5E7EB', marginBottom: 8 }}>
          {t('tourComplete', lang)}
        </h2>
        <p style={{ fontSize: 14, color: '#9CA3AF', lineHeight: 1.6, marginBottom: 24 }}>
          {t('tourCompleteDesc', lang)}
        </p>

        {/* Stats row */}
        <div style={{
          display: 'flex', justifyContent: 'center', gap: 24,
          marginBottom: 28, flexWrap: 'wrap',
        }}>
          {[
            { value: '10', label: t('pagesVisited', lang), color: '#6366F1' },
            { value: '5', label: t('demosPlayed', lang), color: '#10B981' },
            { value: '22', label: t('featuresExplored', lang), color: '#F59E0B' },
          ].map((s) => (
            <div key={s.label} style={{ textAlign: 'center' }}>
              <div style={{ fontSize: 22, fontWeight: 700, color: s.color }}>{s.value}</div>
              <div style={{ fontSize: 11, color: '#6B7280', marginTop: 2 }}>{s.label}</div>
            </div>
          ))}
        </div>

        {/* Buttons */}
        <div style={{ display: 'flex', gap: 12, justifyContent: 'center' }}>
          <button
            onClick={onRestart}
            style={{
              padding: '10px 24px', borderRadius: 10,
              border: '1px solid rgba(99,102,241,0.3)',
              background: 'transparent', color: '#A5B4FC',
              fontSize: 14, fontWeight: 500, cursor: 'pointer',
              transition: 'all 0.15s',
            }}
          >
            {t('restartTour', lang)}
          </button>
          <button
            onClick={onExplore}
            style={{
              padding: '10px 28px', borderRadius: 10, border: 'none',
              background: 'linear-gradient(135deg, #6366F1, #8B5CF6)',
              color: '#fff', fontSize: 14, fontWeight: 600, cursor: 'pointer',
              transition: 'all 0.15s',
            }}
          >
            {t('explore', lang)}
          </button>
        </div>
      </div>
    </div>
  )
}

// ─── Main OnboardingTour Component ───────────────────────────────────────────
export default function OnboardingTour({ lang, onNavigate, onSetLang, onComplete, onSelectWorkflow, onSelectExecution }) {
  const [stepIndex, setStepIndex] = useState(0)
  const [targetRect, setTargetRect] = useState(null)
  const [actionRunning, setActionRunning] = useState(false)
  const [showCompletion, setShowCompletion] = useState(false)
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

  // Cleanup
  useEffect(() => {
    return () => clearAllTimeouts()
  }, [clearAllTimeouts])

  const currentStep = TOUR_STEPS[stepIndex]

  // Measure target element
  const measureTarget = useCallback(() => {
    if (!currentStep?.target) {
      setTargetRect(null)
      return
    }
    const el = document.querySelector(currentStep.target)
    if (el) {
      const rect = el.getBoundingClientRect()
      setTargetRect({ top: rect.top, left: rect.left, width: rect.width, height: rect.height })
      // Scroll into view if needed
      if (rect.top < 0 || rect.bottom > window.innerHeight) {
        el.scrollIntoView({ behavior: 'smooth', block: 'center' })
        // Re-measure after scroll
        addTimeout(() => {
          const r2 = el.getBoundingClientRect()
          setTargetRect({ top: r2.top, left: r2.left, width: r2.width, height: r2.height })
        }, 400)
      }
    } else {
      setTargetRect(null)
    }
  }, [currentStep, addTimeout])

  // Navigate to page and measure on step change
  useEffect(() => {
    if (!currentStep) return
    clearAllTimeouts()

    if (currentStep.page) {
      onNavigate(currentStep.page)
    }

    // Wait for page render, then measure
    const delay = currentStep.page ? 400 : 100
    addTimeout(() => measureTarget(), delay)
  }, [stepIndex, currentStep, onNavigate, measureTarget, clearAllTimeouts, addTimeout])

  // Re-measure on resize
  useEffect(() => {
    const handler = () => measureTarget()
    window.addEventListener('resize', handler)
    return () => window.removeEventListener('resize', handler)
  }, [measureTarget])

  // Execute step action
  const executeAction = useCallback(() => {
    if (!currentStep?.action) return

    setActionRunning(true)

    switch (currentStep.action) {
      case 'clickFirstWorkflowRow': {
        // Skip the click action — just show the table and auto-advance
        addTimeout(() => setActionRunning(false), 800)
        break
      }

      case 'clickFirstExecutionRow': {
        addTimeout(() => setActionRunning(false), 800)
        break
      }

      case 'clickFirstAgent': {
        addTimeout(() => setActionRunning(false), 800)
        break
      }

      case 'storeMemory': {
        addTimeout(() => {
          // Find the text input inside memory-input section
          const input = document.querySelector('[data-tour="memory-input"] input[type="text"]')
          if (input) {
            typeIntoInput('[data-tour="memory-input"] input[type="text"]', 'Classify financial report')
          }
        }, 500)
        addTimeout(() => {
          // Click the Store button
          const btns = document.querySelectorAll('[data-tour="memory-input"] button')
          for (const btn of btns) {
            if (btn.textContent.includes('Store') || btn.textContent.includes('Almacenar')) {
              btn.click()
              break
            }
          }
        }, 1000)
        addTimeout(() => {
          setActionRunning(false)
          measureTarget()
        }, currentStep.wait)
        break
      }

      case 'simulateFailure': {
        addTimeout(() => {
          // Find and click the "Simulate Failure" button
          const btns = document.querySelectorAll('[data-tour="healing-simulator"] button')
          for (const btn of btns) {
            const text = btn.textContent || ''
            if (text.includes('Simulate') || text.includes('Simular')) {
              btn.click()
              break
            }
          }
        }, 500)
        addTimeout(() => {
          setActionRunning(false)
          measureTarget()
        }, currentStep.wait)
        break
      }

      case 'searchDocs': {
        addTimeout(() => {
          // Find the search input inside semantic-search section
          const input = document.querySelector('[data-tour="semantic-search"] input[type="text"]')
          if (input) {
            typeIntoInput('[data-tour="semantic-search"] input[type="text"]', 'NexusForge architecture')
          }
        }, 300)
        addTimeout(() => {
          setActionRunning(false)
          measureTarget()
        }, currentStep.wait)
        break
      }

      case 'openChat': {
        addTimeout(() => {
          // Click the chat button
          const chatBtn = document.querySelector('[data-tour="chat-button"]')
          if (chatBtn) chatBtn.click()
        }, 300)
        addTimeout(() => {
          // Type into chat input
          const chatInput = document.querySelector('.nf-chat-panel input[type="text"]')
          if (chatInput) {
            const nativeSetter = Object.getOwnPropertyDescriptor(window.HTMLInputElement.prototype, 'value')?.set
            if (nativeSetter) {
              nativeSetter.call(chatInput, 'What is NexusForge?')
              chatInput.dispatchEvent(new Event('input', { bubbles: true }))
              chatInput.dispatchEvent(new Event('change', { bubbles: true }))
            }
          }
        }, 800)
        addTimeout(() => {
          // Click send button
          const sendBtn = document.querySelector('.nf-chat-panel button[type="submit"]')
          if (sendBtn) sendBtn.click()
        }, 1200)
        addTimeout(() => setActionRunning(false), currentStep.wait)
        break
      }

      case 'scrollTop': {
        window.scrollTo({ top: 0, behavior: 'smooth' })
        addTimeout(() => setActionRunning(false), currentStep.wait)
        break
      }

      default:
        setActionRunning(false)
    }
  }, [currentStep, addTimeout, measureTarget])

  const goToStep = useCallback((idx) => {
    if (idx < 0 || idx >= TOUR_STEPS.length) return
    clearAllTimeouts()
    setActionRunning(false)
    setTargetRect(null)
    setStepIndex(idx)
  }, [clearAllTimeouts])

  const handleNext = useCallback(() => {
    if (actionRunning) return

    // If current step has an action and it hasn't been executed yet, execute it first
    if (currentStep?.action && !actionRunning) {
      executeAction()
      // After the action completes, auto-advance
      addTimeout(() => {
        if (stepIndex < TOUR_STEPS.length - 1) {
          goToStep(stepIndex + 1)
        } else {
          // Tour complete
          window.scrollTo({ top: 0, behavior: 'smooth' })
          onNavigate('dashboard')
          setShowCompletion(true)
        }
      }, (currentStep.wait || 0) + 200)
      return
    }

    if (stepIndex < TOUR_STEPS.length - 1) {
      goToStep(stepIndex + 1)
    } else {
      window.scrollTo({ top: 0, behavior: 'smooth' })
      onNavigate('dashboard')
      setShowCompletion(true)
    }
  }, [stepIndex, currentStep, actionRunning, executeAction, goToStep, onNavigate, addTimeout])

  const handlePrev = useCallback(() => {
    if (actionRunning) return
    goToStep(stepIndex - 1)
  }, [stepIndex, actionRunning, goToStep])

  const handleSkip = useCallback(() => {
    clearAllTimeouts()
    setActionRunning(false)
    onNavigate('dashboard')
    window.scrollTo({ top: 0, behavior: 'smooth' })
    onComplete()
  }, [clearAllTimeouts, onNavigate, onComplete])

  const handleRestart = useCallback(() => {
    setShowCompletion(false)
    setTargetRect(null)
    setActionRunning(false)
    clearAllTimeouts()
    setStepIndex(0)
  }, [clearAllTimeouts])

  const handleExplore = useCallback(() => {
    setShowCompletion(false)
    onComplete()
  }, [onComplete])

  if (showCompletion) {
    return (
      <>
        <style>{tourKeyframes}</style>
        <CompletionModal lang={lang} onRestart={handleRestart} onExplore={handleExplore} />
      </>
    )
  }

  return (
    <>
      <style>{tourKeyframes}</style>

      {/* Dark overlay with spotlight cutout OR full overlay for welcome/final */}
      {currentStep?.target && targetRect ? (
        <TourSpotlight targetRect={targetRect} />
      ) : (
        <div style={{
          position: 'fixed', inset: 0, zIndex: 9998,
          background: 'rgba(0,0,0,0.75)',
          pointerEvents: 'none',
        }} />
      )}

      {/* Clickable overlay to prevent interaction outside tooltip */}
      <div style={{
        position: 'fixed', inset: 0, zIndex: 9998,
        pointerEvents: actionRunning ? 'none' : 'auto',
        background: 'transparent',
      }} onClick={(e) => e.stopPropagation()}>
        <TourTooltip
          step={currentStep}
          stepIndex={stepIndex}
          totalSteps={TOUR_STEPS.length}
          targetRect={targetRect}
          lang={lang}
          actionRunning={actionRunning}
          onNext={handleNext}
          onPrev={handlePrev}
          onSkip={handleSkip}
        />
      </div>
    </>
  )
}

// ─── Keyframes ───────────────────────────────────────────────────────────────
const tourKeyframes = `
@keyframes tourPulse {
  0%, 100% { border-color: rgba(99,102,241,0.6); box-shadow: 0 0 0 0 rgba(99,102,241,0.2); }
  50% { border-color: rgba(99,102,241,0.9); box-shadow: 0 0 20px 4px rgba(99,102,241,0.15); }
}
@keyframes tourTooltipIn {
  from { opacity: 0; transform: translateY(10px); }
  to { opacity: 1; transform: translateY(0); }
}
@keyframes tourActionPulse {
  0%, 100% { opacity: 1; transform: scale(1); }
  50% { opacity: 0.5; transform: scale(0.8); }
}
@keyframes tourFadeIn {
  from { opacity: 0; }
  to { opacity: 1; }
}
@keyframes tourScaleIn {
  from { opacity: 0; transform: scale(0.9); }
  to { opacity: 1; transform: scale(1); }
}
`
