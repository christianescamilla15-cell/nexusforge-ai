import { useState, useEffect, useCallback, useRef } from 'react'
import { t } from '../../shared/i18n/translations'

const ERROR_TYPES = [
  { key: 'network', label: 'networkError', error: 'TimeoutError: Groq API did not respond within 15s', severity: 'medium', recoverable: true, strategy: 'retry' },
  { key: 'rateLimit', label: 'rateLimitError', error: '429 Too Many Requests — Groq rate limit exceeded', severity: 'medium', recoverable: true, strategy: 'retry' },
  { key: 'dataQuality', label: 'dataQualityError', error: 'JSONDecodeError: Unexpected token at position 847', severity: 'low', recoverable: true, strategy: 'repair' },
  { key: 'schema', label: 'schemaMismatch', error: 'ValidationError: Missing required fields [confidence, entities]', severity: 'medium', recoverable: true, strategy: 'repair' },
  { key: 'auth', label: 'authError', error: 'AuthenticationError: API key expired or invalid', severity: 'high', recoverable: false, strategy: 'escalate' },
  { key: 'unknown', label: 'unknownError', error: 'UnhandledError: Unexpected internal state in step executor', severity: 'high', recoverable: false, strategy: 'fallback' },
]

const STRATEGIES = [
  {
    key: 'retry', name: 'RetryStrategy', color: '#6366F1', bg: 'rgba(99,102,241,0.12)',
    icon: 'M4 4v5h.582m15.356 2A8.001 8.001 0 004.582 9m0 0H9m11 11v-5h-.581m0 0a8.003 8.003 0 01-15.357-2m15.357 2H15',
    desc: { en: 'Retries with exponential backoff. Can switch LLM provider on repeated failures.', es: 'Reintenta con backoff exponencial. Puede cambiar de proveedor LLM en fallos repetidos.' },
    when: { en: 'Network errors, timeouts, rate limits', es: 'Errores de red, timeouts, rate limits' },
    example: { en: 'Timeout on Groq → Retry with Claude fallback', es: 'Timeout en Groq → Reintentar con Claude como fallback' },
    successRate: 94,
    execution: {
      en: ['Retrying with Claude (fallback)...', 'attempt 1/2', 'Response received in 2.1s', 'Success!'],
      es: ['Reintentando con Claude (fallback)...', 'intento 1/2', 'Respuesta recibida en 2.1s', 'Exito!'],
    },
  },
  {
    key: 'skip', name: 'SkipStrategy', color: '#F59E0B', bg: 'rgba(245,158,11,0.12)',
    icon: 'M13 5l7 7-7 7M5 5l7 7-7 7',
    desc: { en: 'Skips the failed step and continues the pipeline. For non-critical steps only.', es: 'Omite el paso fallido y continua el pipeline. Solo para pasos no criticos.' },
    when: { en: 'Optional steps, non-critical enrichment', es: 'Pasos opcionales, enriquecimiento no critico' },
    example: { en: 'Logging step failed → Skip and continue', es: 'Paso de logging fallo → Omitir y continuar' },
    successRate: 100,
    execution: {
      en: ['Step marked as optional...', 'Skipping to next step', 'Pipeline continues', 'Success!'],
      es: ['Paso marcado como opcional...', 'Omitiendo al siguiente paso', 'Pipeline continua', 'Exito!'],
    },
  },
  {
    key: 'repair', name: 'RepairStrategy', color: '#10B981', bg: 'rgba(16,185,129,0.12)',
    icon: 'M11.42 15.17l-5.66-5.66a8 8 0 1111.31 0l-5.65 5.66zM11.42 15.17L7.75 18.84M11.42 15.17l3.66 3.67',
    desc: { en: 'Uses a RepairAgent to analyze and fix malformed data, then retries the step.', es: 'Usa un RepairAgent para analizar y corregir datos malformados, luego reintenta.' },
    when: { en: 'Data quality issues, format mismatches, schema errors', es: 'Problemas de calidad de datos, formatos incorrectos, errores de schema' },
    example: { en: 'Malformed JSON → RepairAgent fixes → Retry succeeds', es: 'JSON malformado → RepairAgent corrige → Reintento exitoso' },
    successRate: 87,
    execution: {
      en: ['RepairAgent analyzing...', 'Diagnosis: malformed JSON at pos 847', 'Fix: re-prompt with strict JSON schema', 'Success!'],
      es: ['RepairAgent analizando...', 'Diagnostico: JSON malformado en pos 847', 'Fix: re-prompt con schema JSON estricto', 'Exito!'],
    },
  },
  {
    key: 'escalate', name: 'EscalateStrategy', color: '#EC4899', bg: 'rgba(236,72,153,0.12)',
    icon: 'M5 10l7-7m0 0l7 7m-7-7v18',
    desc: { en: 'Escalates to human review when automated recovery is not possible.', es: 'Escala a revision humana cuando la recuperacion automatica no es posible.' },
    when: { en: 'Auth failures, unrecoverable errors, compliance flags', es: 'Fallos de auth, errores irrecuperables, alertas de compliance' },
    example: { en: 'Expired API key → Marked for human review', es: 'API key expirada → Marcado para revision humana' },
    successRate: 91,
    execution: {
      en: ['Error classified as non-recoverable', 'Marking for human review...', 'Added to review queue (#847)', 'Escalated'],
      es: ['Error clasificado como no recuperable', 'Marcando para revision humana...', 'Agregado a cola de revision (#847)', 'Escalado'],
    },
  },
  {
    key: 'fallback', name: 'FallbackStrategy', color: '#8B5CF6', bg: 'rgba(139,92,246,0.12)',
    icon: 'M9 17V7m0 10l-3-3m3 3l3-3M15 7v10m0-10l3 3m-3-3l-3 3',
    desc: { en: 'Activates a predefined fallback route using cached results from previous runs.', es: 'Activa una ruta alternativa predefinida usando resultados cacheados de ejecuciones previas.' },
    when: { en: 'Max retries exceeded, critical failures, unknown errors', es: 'Max reintentos excedidos, fallos criticos, errores desconocidos' },
    example: { en: 'Unknown error → Load cached result from run-abc', es: 'Error desconocido → Cargar resultado cacheado de run-abc' },
    successRate: 96,
    execution: {
      en: ['Loading cached result from run-2024-Q4...', 'Cache hit: 98.2% confidence match', 'Cached result applied to pipeline', 'Success!'],
      es: ['Cargando resultado cacheado de run-2024-Q4...', 'Cache hit: 98.2% coincidencia de confianza', 'Resultado cacheado aplicado al pipeline', 'Exito!'],
    },
  },
]

const INITIAL_HISTORY = [
  { time: '14:32:01', errorType: 'network', strategy: 'retry', result: 'healed', duration: 3.2 },
  { time: '14:28:45', errorType: 'dataQuality', strategy: 'repair', result: 'healed', duration: 4.8 },
  { time: '14:25:12', errorType: 'rateLimit', strategy: 'retry', result: 'healed', duration: 2.1 },
  { time: '14:21:33', errorType: 'auth', strategy: 'escalate', result: 'escalated', duration: 1.5 },
]

export default function HealingPage({ lang = 'en' }) {
  const [selectedError, setSelectedError] = useState(ERROR_TYPES[0].key)
  const [simPhase, setSimPhase] = useState(null) // null, 'error', 'detect', 'strategy', 'execute', 'resolve'
  const [execStep, setExecStep] = useState(0)
  const [history, setHistory] = useState(INITIAL_HISTORY)
  const [showStrategies, setShowStrategies] = useState(false)
  const [isMobile, setIsMobile] = useState(false)
  const simTimeout = useRef([])

  useEffect(() => {
    const check = () => setIsMobile(window.innerWidth <= 900)
    check()
    window.addEventListener('resize', check)
    return () => window.removeEventListener('resize', check)
  }, [])

  // Cleanup timeouts
  useEffect(() => {
    return () => simTimeout.current.forEach(t => clearTimeout(t))
  }, [])

  const errorDef = ERROR_TYPES.find(e => e.key === selectedError)
  const strategyDef = STRATEGIES.find(s => s.key === errorDef.strategy)
  const isEscalated = errorDef.strategy === 'escalate'

  const totalSims = history.length
  const healedCount = history.filter(h => h.result === 'healed').length
  const successPct = totalSims > 0 ? Math.round((healedCount / totalSims) * 100) : 0
  const fastestTime = history.length > 0 ? Math.min(...history.map(h => h.duration)) : 0
  const errorCounts = {}
  const strategyCounts = {}
  history.forEach(h => {
    errorCounts[h.errorType] = (errorCounts[h.errorType] || 0) + 1
    strategyCounts[h.strategy] = (strategyCounts[h.strategy] || 0) + 1
  })
  const mostCommonError = Object.entries(errorCounts).sort((a, b) => b[1] - a[1])[0]

  const simulate = useCallback(() => {
    if (simPhase !== null) return
    simTimeout.current.forEach(t => clearTimeout(t))
    simTimeout.current = []

    // Phase 0-1: Error
    setSimPhase('error')
    setExecStep(0)

    // Phase 1-2: Detection
    simTimeout.current.push(setTimeout(() => setSimPhase('detect'), 1000))

    // Phase 2-3: Strategy selection
    simTimeout.current.push(setTimeout(() => setSimPhase('strategy'), 2000))

    // Phase 3-5: Execution steps
    simTimeout.current.push(setTimeout(() => { setSimPhase('execute'); setExecStep(0) }, 3000))
    simTimeout.current.push(setTimeout(() => setExecStep(1), 3500))
    simTimeout.current.push(setTimeout(() => setExecStep(2), 4000))
    simTimeout.current.push(setTimeout(() => setExecStep(3), 4500))

    // Phase 5-6: Resolution
    simTimeout.current.push(setTimeout(() => {
      setSimPhase('resolve')
      const duration = +(2 + Math.random() * 4).toFixed(1)
      const now = new Date()
      const time = `${String(now.getHours()).padStart(2, '0')}:${String(now.getMinutes()).padStart(2, '0')}:${String(now.getSeconds()).padStart(2, '0')}`
      setHistory(prev => [{
        time,
        errorType: selectedError,
        strategy: errorDef.strategy,
        result: isEscalated ? 'escalated' : 'healed',
        duration,
      }, ...prev])
    }, 5000))

    // Reset
    simTimeout.current.push(setTimeout(() => setSimPhase(null), 6500))
  }, [simPhase, selectedError, errorDef, isEscalated])

  const phaseColor = (phase) => {
    switch (phase) {
      case 'error': return '#EF4444'
      case 'detect': return '#F59E0B'
      case 'strategy': return '#3B82F6'
      case 'execute': return '#6366F1'
      case 'resolve': return '#10B981'
      default: return '#4B5563'
    }
  }

  const badgeStyle = (bg, color) => ({
    display: 'inline-flex', alignItems: 'center', gap: 4,
    padding: '3px 10px', borderRadius: 6, background: bg, color,
    fontSize: 11, fontWeight: 600, whiteSpace: 'nowrap',
  })

  return (
    <div style={{ animation: 'fadeIn 0.3s ease-out' }}>
      {/* Header */}
      <div style={{ marginBottom: 20 }}>
        <h1 style={{ fontSize: isMobile ? 20 : 24, fontWeight: 700, color: '#111827', marginBottom: 4 }}>
          {t('selfHealing', lang)}
        </h1>
        <p style={{ fontSize: isMobile ? 13 : 14, color: '#9CA3AF' }}>
          {lang === 'es'
            ? 'Simula fallos y observa como el sistema de auto-reparacion detecta, clasifica y resuelve errores automaticamente.'
            : 'Simulate failures and watch the self-healing system detect, classify, and resolve errors automatically.'
          }
        </p>
      </div>

      <div style={{ display: 'flex', flexDirection: isMobile ? 'column' : 'row', gap: 16 }}>
        {/* Main simulator area */}
        <div style={{ flex: 1, minWidth: 0 }}>
          {/* Failure simulator */}
          <div data-tour="healing-simulator" style={{
            background: '#FFFFFF', borderRadius: 14, padding: 20,
            border: `1px solid ${simPhase ? phaseColor(simPhase) + '44' : '#E5E7EB'}`,
            marginBottom: 16, transition: 'border-color 0.3s',
          }}>
            <div style={{ display: 'flex', alignItems: 'center', gap: 12, marginBottom: 16 }}>
              <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="#EF4444" strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round" aria-hidden="true">
                <path d="M12 9v2m0 4h.01m-6.938 4h13.856c1.54 0 2.502-1.667 1.732-2.5L13.732 4.5c-.77-.833-2.694-.833-3.464 0L3.34 16.5c-.77.833.192 2.5 1.732 2.5z" />
              </svg>
              <span style={{ fontSize: 16, fontWeight: 600, color: '#111827' }}>
                {lang === 'es' ? 'Simulador de Fallos' : 'Failure Simulator'}
              </span>
            </div>

            <div style={{ display: 'flex', flexWrap: 'wrap', gap: 10, marginBottom: 16 }}>
              <select
                value={selectedError}
                onChange={(e) => setSelectedError(e.target.value)}
                disabled={simPhase !== null}
                aria-label={t('errorType', lang)}
                style={{
                  padding: '10px 14px', borderRadius: 8, border: '1px solid #D1D5DB',
                  background: '#F9FAFB', color: '#111827', fontSize: 13, outline: 'none',
                  minWidth: 220, opacity: simPhase ? 0.5 : 1,
                }}
              >
                {ERROR_TYPES.map(e => (
                  <option key={e.key} value={e.key}>{t(e.label, lang)}</option>
                ))}
              </select>
              <button
                onClick={simulate}
                disabled={simPhase !== null}
                aria-label={t('simulateFailure', lang)}
                style={{
                  padding: '10px 28px', borderRadius: 8, border: 'none',
                  background: simPhase ? '#374151' : 'linear-gradient(135deg, #EF4444, #DC2626)',
                  color: '#fff', fontSize: 14, fontWeight: 600, cursor: simPhase ? 'not-allowed' : 'pointer',
                  transition: 'all 0.2s', opacity: simPhase ? 0.6 : 1,
                }}
                onMouseEnter={(e) => !simPhase && (e.currentTarget.style.transform = 'scale(1.03)')}
                onMouseLeave={(e) => (e.currentTarget.style.transform = 'scale(1)')}
              >
                {simPhase ? (lang === 'es' ? 'Simulando...' : 'Simulating...') : t('simulateFailure', lang)}
              </button>
            </div>

            {/* Simulation phases */}
            {simPhase && (
              <div style={{ display: 'flex', flexDirection: 'column', gap: 12 }}>
                {/* Phase 1: Error */}
                <div style={{
                  background: simPhase === 'error' ? 'rgba(239,68,68,0.1)' : 'rgba(239,68,68,0.05)',
                  border: `1px solid ${simPhase === 'error' ? 'rgba(239,68,68,0.4)' : 'rgba(239,68,68,0.15)'}`,
                  borderRadius: 10, padding: 14, transition: 'all 0.3s',
                  ...(simPhase === 'error' ? { boxShadow: '0 0 20px rgba(239,68,68,0.15)' } : {}),
                }}>
                  <div style={{ display: 'flex', alignItems: 'center', gap: 8, marginBottom: 6 }}>
                    <div style={{
                      width: 8, height: 8, borderRadius: '50%', background: '#EF4444',
                      ...(simPhase === 'error' ? { animation: 'pulse 1s ease-in-out infinite' } : {}),
                    }} />
                    <span style={{ fontSize: 13, fontWeight: 600, color: '#EF4444' }}>
                      Step: Extract
                    </span>
                    <span style={badgeStyle('rgba(239,68,68,0.2)', '#EF4444')}>FAILED</span>
                  </div>
                  <div style={{ fontFamily: 'monospace', fontSize: 12, color: '#DC2626', padding: '6px 10px', background: '#F3F4F6', borderRadius: 6 }}>
                    {errorDef.error}
                  </div>
                </div>

                {/* Phase 2: Detection */}
                {['detect', 'strategy', 'execute', 'resolve'].includes(simPhase) && (
                  <div style={{
                    background: simPhase === 'detect' ? 'rgba(245,158,11,0.1)' : 'rgba(245,158,11,0.04)',
                    border: `1px solid ${simPhase === 'detect' ? 'rgba(245,158,11,0.4)' : 'rgba(245,158,11,0.12)'}`,
                    borderRadius: 10, padding: 14, transition: 'all 0.3s',
                    ...(simPhase === 'detect' ? { boxShadow: '0 0 20px rgba(245,158,11,0.15)' } : {}),
                  }}>
                    <div style={{ display: 'flex', alignItems: 'center', gap: 8, marginBottom: 6 }}>
                      <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="#F59E0B" strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round" aria-hidden="true">
                        <path d="M21 21l-6-6m2-5a7 7 0 11-14 0 7 7 0 0114 0z" />
                      </svg>
                      <span style={{ fontSize: 13, fontWeight: 600, color: '#FBBF24' }}>
                        FailureDetector
                      </span>
                      <span style={badgeStyle('rgba(245,158,11,0.2)', '#FBBF24')}>{t('detection', lang)}</span>
                    </div>
                    <div style={{ fontSize: 12, color: '#92400E', fontFamily: 'monospace' }}>
                      Type: <span style={{ color: '#111827' }}>{selectedError}</span>
                      {' | '}Severity: <span style={{ color: errorDef.severity === 'high' ? '#EF4444' : errorDef.severity === 'medium' ? '#F59E0B' : '#10B981' }}>{errorDef.severity}</span>
                      {' | '}Recoverable: <span style={{ color: errorDef.recoverable ? '#10B981' : '#EF4444' }}>{errorDef.recoverable ? 'yes' : 'no'}</span>
                    </div>
                  </div>
                )}

                {/* Phase 3: Strategy Selection */}
                {['strategy', 'execute', 'resolve'].includes(simPhase) && (
                  <div style={{
                    background: simPhase === 'strategy' ? 'rgba(59,130,246,0.1)' : 'rgba(59,130,246,0.04)',
                    border: `1px solid ${simPhase === 'strategy' ? 'rgba(59,130,246,0.4)' : 'rgba(59,130,246,0.12)'}`,
                    borderRadius: 10, padding: 14, transition: 'all 0.3s',
                  }}>
                    <div style={{ display: 'flex', alignItems: 'center', gap: 8, marginBottom: 10 }}>
                      <span style={{ fontSize: 13, fontWeight: 600, color: '#60A5FA' }}>
                        {t('strategySelection', lang)}
                      </span>
                    </div>
                    <div style={{ display: 'flex', flexWrap: 'wrap', gap: 8 }}>
                      {STRATEGIES.map(s => {
                        const isSelected = s.key === errorDef.strategy
                        return (
                          <div key={s.key} style={{
                            padding: '8px 14px', borderRadius: 8,
                            background: isSelected ? s.bg : '#F3F4F6',
                            border: `1px solid ${isSelected ? s.color + '66' : '#E5E7EB'}`,
                            transition: 'all 0.3s',
                            ...(isSelected && simPhase === 'strategy' ? { boxShadow: `0 0 16px ${s.bg}` } : {}),
                          }}>
                            <div style={{ display: 'flex', alignItems: 'center', gap: 6 }}>
                              <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke={isSelected ? s.color : '#4B5563'} strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round" aria-hidden="true">
                                <path d={s.icon} />
                              </svg>
                              <span style={{ fontSize: 12, fontWeight: isSelected ? 600 : 400, color: isSelected ? s.color : '#6B7280' }}>
                                {s.name}
                              </span>
                              {isSelected && <span style={{ fontSize: 10, color: s.color }}>&#9668;</span>}
                            </div>
                          </div>
                        )
                      })}
                    </div>
                  </div>
                )}

                {/* Phase 4: Execution */}
                {['execute', 'resolve'].includes(simPhase) && (
                  <div style={{
                    background: simPhase === 'execute' ? `${strategyDef.bg}` : strategyDef.bg.replace('0.12', '0.04'),
                    border: `1px solid ${simPhase === 'execute' ? strategyDef.color + '44' : strategyDef.color + '15'}`,
                    borderRadius: 10, padding: 14, transition: 'all 0.3s',
                  }}>
                    <div style={{ display: 'flex', alignItems: 'center', gap: 8, marginBottom: 8 }}>
                      <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke={strategyDef.color} strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round" aria-hidden="true">
                        <path d={strategyDef.icon} />
                      </svg>
                      <span style={{ fontSize: 13, fontWeight: 600, color: strategyDef.color }}>
                        {strategyDef.name}
                      </span>
                    </div>
                    <div style={{ display: 'flex', flexDirection: 'column', gap: 4 }}>
                      {strategyDef.execution[lang].map((step, i) => (
                        <div key={i} style={{
                          fontSize: 12, fontFamily: 'monospace', padding: '4px 10px',
                          background: i <= execStep ? '#F3F4F6' : 'transparent',
                          borderRadius: 4, transition: 'all 0.3s',
                          color: i <= execStep ? (i === strategyDef.execution[lang].length - 1 ? '#10B981' : '#E5E7EB') : '#374151',
                          borderLeft: i <= execStep ? `2px solid ${strategyDef.color}` : '2px solid transparent',
                        }}>
                          {i <= execStep ? (i < execStep ? '\u2713 ' : '\u25B6 ') : '  '}{step}
                        </div>
                      ))}
                    </div>
                  </div>
                )}

                {/* Phase 5: Resolution */}
                {simPhase === 'resolve' && (
                  <div style={{
                    background: 'rgba(16,185,129,0.1)',
                    border: '1px solid rgba(16,185,129,0.4)',
                    borderRadius: 10, padding: 14,
                    boxShadow: '0 0 20px rgba(16,185,129,0.15)',
                    animation: 'fadeIn 0.3s ease-out',
                  }}>
                    <div style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
                      <span style={{ fontSize: 18 }}>{isEscalated ? '\u26A0' : '\u2705'}</span>
                      <span style={{ fontSize: 14, fontWeight: 700, color: isEscalated ? '#FBBF24' : '#10B981' }}>
                        {isEscalated ? (lang === 'es' ? 'ESCALADO' : 'ESCALATED') : (lang === 'es' ? 'REPARADO' : 'HEALED')}
                      </span>
                    </div>
                    <div style={{ fontSize: 12, color: '#9CA3AF', marginTop: 6 }}>
                      {t('healingTime', lang)}: <span style={{ color: '#111827', fontWeight: 500 }}>{(2 + Math.random() * 4).toFixed(1)}s</span>
                      {' | '}{lang === 'es' ? 'Estrategia' : 'Strategy'}: <span style={{ color: strategyDef.color, fontWeight: 500 }}>{strategyDef.name}</span>
                      {errorDef.strategy === 'retry' && (
                        <>{' | '}{lang === 'es' ? 'Proveedor cambiado' : 'Provider switched'}: <span style={{ color: '#818CF8' }}>Groq → Claude</span></>
                      )}
                    </div>
                  </div>
                )}
              </div>
            )}

            {/* Idle state */}
            {!simPhase && (
              <div style={{
                textAlign: 'center', padding: '30px 20px', color: '#4B5563',
                border: '1px dashed #E5E7EB', borderRadius: 10,
              }}>
                <svg width="40" height="40" viewBox="0 0 24 24" fill="none" stroke="#374151" strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round" style={{ margin: '0 auto 8px' }} aria-hidden="true">
                  <path d="M12 9v2m0 4h.01m-6.938 4h13.856c1.54 0 2.502-1.667 1.732-2.5L13.732 4.5c-.77-.833-2.694-.833-3.464 0L3.34 16.5c-.77.833.192 2.5 1.732 2.5z" />
                </svg>
                <div style={{ fontSize: 13 }}>
                  {lang === 'es' ? 'Selecciona un tipo de error y haz clic en "Simular Fallo"' : 'Select an error type and click "Simulate Failure"'}
                </div>
              </div>
            )}
          </div>

          {/* Healing History */}
          <div style={{
            background: '#FFFFFF', borderRadius: 14, padding: 20,
            border: '1px solid #E5E7EB', marginBottom: 16,
          }}>
            <h3 style={{ fontSize: 15, fontWeight: 600, color: '#111827', marginBottom: 12 }}>
              {t('healingHistory', lang)}
            </h3>
            {history.length === 0 ? (
              <div style={{ color: '#4B5563', fontSize: 13, textAlign: 'center', padding: 16 }}>
                {lang === 'es' ? 'Sin historial. Simula un fallo para comenzar.' : 'No history. Simulate a failure to begin.'}
              </div>
            ) : (
              <div style={{ overflowX: 'auto' }}>
                <table style={{ width: '100%', borderCollapse: 'collapse', fontSize: 12 }}>
                  <thead>
                    <tr>
                      {[
                        lang === 'es' ? 'Hora' : 'Time',
                        t('errorType', lang),
                        lang === 'es' ? 'Estrategia' : 'Strategy',
                        lang === 'es' ? 'Resultado' : 'Result',
                        t('duration', lang),
                      ].map((h, i) => (
                        <th key={i} style={{
                          textAlign: 'left', padding: '8px 10px', color: '#6B7280', fontWeight: 500,
                          borderBottom: '1px solid #E5E7EB',
                        }}>{h}</th>
                      ))}
                    </tr>
                  </thead>
                  <tbody>
                    {history.slice(0, 10).map((h, i) => {
                      const strat = STRATEGIES.find(s => s.key === h.strategy)
                      return (
                        <tr key={i} style={{ borderBottom: '1px solid #F3F4F6' }}>
                          <td style={{ padding: '8px 10px', fontFamily: 'monospace', color: '#9CA3AF' }}>{h.time}</td>
                          <td style={{ padding: '8px 10px' }}>
                            <span style={badgeStyle('#F3F4F6', '#9CA3AF')}>{t(ERROR_TYPES.find(e => e.key === h.errorType)?.label || h.errorType, lang)}</span>
                          </td>
                          <td style={{ padding: '8px 10px' }}>
                            <span style={badgeStyle(strat?.bg || 'transparent', strat?.color || '#9CA3AF')}>{strat?.name || h.strategy}</span>
                          </td>
                          <td style={{ padding: '8px 10px' }}>
                            <span style={{
                              ...badgeStyle(
                                h.result === 'healed' ? 'rgba(16,185,129,0.15)' : 'rgba(245,158,11,0.15)',
                                h.result === 'healed' ? '#10B981' : '#F59E0B'
                              ),
                            }}>
                              {h.result === 'healed' ? t('healed', lang) : (lang === 'es' ? 'Escalado' : 'Escalated')}
                            </span>
                          </td>
                          <td style={{ padding: '8px 10px', color: '#9CA3AF', fontFamily: 'monospace' }}>{h.duration}s</td>
                        </tr>
                      )
                    })}
                  </tbody>
                </table>
              </div>
            )}
          </div>

          {/* Strategy Reference (collapsible) */}
          <div style={{
            background: '#FFFFFF', borderRadius: 14,
            border: '1px solid #E5E7EB', overflow: 'hidden',
          }}>
            <button
              onClick={() => setShowStrategies(!showStrategies)}
              aria-label={lang === 'es' ? 'Mostrar estrategias de referencia' : 'Toggle strategy reference'}
              style={{
                width: '100%', padding: '14px 20px', border: 'none', background: 'transparent',
                display: 'flex', alignItems: 'center', justifyContent: 'space-between',
                color: '#111827', fontSize: 14, fontWeight: 600, cursor: 'pointer',
              }}
            >
              <span>{lang === 'es' ? 'Referencia de Estrategias' : 'Strategy Reference'}</span>
              <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"
                style={{ transform: showStrategies ? 'rotate(180deg)' : 'none', transition: 'transform 0.2s' }} aria-hidden="true">
                <path d="M6 9l6 6 6-6" />
              </svg>
            </button>
            {showStrategies && (
              <div style={{ padding: '0 20px 20px', display: 'flex', flexDirection: 'column', gap: 12 }}>
                {STRATEGIES.map(s => (
                  <div key={s.key} aria-label={`Strategy: ${s.name}`} style={{
                    background: '#F9FAFB', borderRadius: 10, padding: 16,
                    border: `1px solid ${s.color}22`,
                  }}>
                    <div style={{ display: 'flex', alignItems: 'center', gap: 10, marginBottom: 8 }}>
                      <div style={{
                        width: 34, height: 34, borderRadius: 8, background: s.bg,
                        display: 'flex', alignItems: 'center', justifyContent: 'center',
                      }}>
                        <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke={s.color} strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round" aria-hidden="true">
                          <path d={s.icon} />
                        </svg>
                      </div>
                      <div>
                        <div style={{ fontSize: 14, fontWeight: 600, color: '#111827' }}>{s.name}</div>
                        <div style={{ fontSize: 11, color: s.color }}>{s.successRate}% {t('successRate', lang)}</div>
                      </div>
                    </div>
                    <p style={{ fontSize: 12, color: '#9CA3AF', lineHeight: 1.5, margin: '0 0 6px' }}>{s.desc[lang]}</p>
                    <div style={{ fontSize: 11, color: '#6B7280', marginBottom: 4 }}>
                      {lang === 'es' ? 'Cuando se usa' : 'When used'}: <span style={{ color: '#9CA3AF' }}>{s.when[lang]}</span>
                    </div>
                    <div style={{ fontSize: 11, color: '#6B7280' }}>
                      {lang === 'es' ? 'Ejemplo' : 'Example'}: <span style={{ color: s.color }}>{s.example[lang]}</span>
                    </div>
                  </div>
                ))}
              </div>
            )}
          </div>
        </div>

        {/* Stats sidebar */}
        <div style={{
          width: isMobile ? '100%' : 260, flexShrink: 0,
          display: 'flex', flexDirection: 'column', gap: 12,
        }}>
          {/* Total sims */}
          <div style={{
            background: '#FFFFFF', borderRadius: 12, padding: 16,
            border: '1px solid #E5E7EB',
          }}>
            <div style={{ fontSize: 11, color: '#6B7280', marginBottom: 4 }}>
              {lang === 'es' ? 'Simulaciones' : 'Total Simulations'}
            </div>
            <div style={{ fontSize: 28, fontWeight: 700, color: '#111827' }}>{totalSims}</div>
          </div>

          {/* Success rate */}
          <div style={{
            background: '#FFFFFF', borderRadius: 12, padding: 16,
            border: '1px solid #E5E7EB',
          }}>
            <div style={{ fontSize: 11, color: '#6B7280', marginBottom: 4 }}>{t('successRate', lang)}</div>
            <div style={{ fontSize: 28, fontWeight: 700, color: '#10B981' }}>{successPct}%</div>
            <div style={{
              width: '100%', height: 4, background: '#F3F4F6',
              borderRadius: 2, marginTop: 6, overflow: 'hidden',
            }}>
              <div style={{
                width: `${successPct}%`, height: '100%', borderRadius: 2,
                background: 'linear-gradient(90deg, #10B981, #34D399)',
                transition: 'width 0.5s',
              }} />
            </div>
          </div>

          {/* Most common error */}
          <div style={{
            background: '#FFFFFF', borderRadius: 12, padding: 16,
            border: '1px solid #E5E7EB',
          }}>
            <div style={{ fontSize: 11, color: '#6B7280', marginBottom: 4 }}>
              {lang === 'es' ? 'Error mas comun' : 'Most Common Error'}
            </div>
            <div style={{ fontSize: 14, fontWeight: 600, color: '#EF4444' }}>
              {mostCommonError ? t(ERROR_TYPES.find(e => e.key === mostCommonError[0])?.label || mostCommonError[0], lang) : '-'}
            </div>
            {mostCommonError && (
              <div style={{ fontSize: 11, color: '#6B7280', marginTop: 2 }}>{mostCommonError[1]}x</div>
            )}
          </div>

          {/* Fastest healing */}
          <div style={{
            background: '#FFFFFF', borderRadius: 12, padding: 16,
            border: '1px solid #E5E7EB',
          }}>
            <div style={{ fontSize: 11, color: '#6B7280', marginBottom: 4 }}>
              {lang === 'es' ? 'Reparacion mas rapida' : 'Fastest Healing'}
            </div>
            <div style={{ fontSize: 28, fontWeight: 700, color: '#6366F1' }}>{fastestTime}s</div>
          </div>

          {/* Strategy distribution */}
          <div style={{
            background: '#FFFFFF', borderRadius: 12, padding: 16,
            border: '1px solid #E5E7EB',
          }}>
            <div style={{ fontSize: 11, color: '#6B7280', marginBottom: 10 }}>
              {lang === 'es' ? 'Uso de estrategias' : 'Strategy Usage'}
            </div>
            {STRATEGIES.map(s => {
              const count = strategyCounts[s.key] || 0
              const pct = totalSims > 0 ? Math.round((count / totalSims) * 100) : 0
              return (
                <div key={s.key} style={{ marginBottom: 6 }}>
                  <div style={{ display: 'flex', justifyContent: 'space-between', fontSize: 11, marginBottom: 2 }}>
                    <span style={{ color: s.color }}>{s.name}</span>
                    <span style={{ color: '#6B7280' }}>{count} ({pct}%)</span>
                  </div>
                  <div style={{
                    width: '100%', height: 4, background: '#F3F4F6',
                    borderRadius: 2, overflow: 'hidden',
                  }}>
                    <div style={{
                      width: `${pct}%`, height: '100%', borderRadius: 2,
                      background: s.color, transition: 'width 0.5s',
                    }} />
                  </div>
                </div>
              )
            })}
          </div>
        </div>
      </div>

      <style>{`
        @keyframes pulse {
          0%, 100% { opacity: 1; transform: scale(1); }
          50% { opacity: 0.5; transform: scale(1.5); }
        }
        @keyframes fadeIn {
          from { opacity: 0; transform: translateY(8px); }
          to { opacity: 1; transform: translateY(0); }
        }
      `}</style>
    </div>
  )
}
