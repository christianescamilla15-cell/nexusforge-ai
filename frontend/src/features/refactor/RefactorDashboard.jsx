import { useState } from 'react'
import { fetchAPI } from '../../services/api'
import { useIsMobile } from '../../shared/hooks/useIsMobile'

const PHASES = [
  { key: 'idle', label: { es: 'Listo', en: 'Ready' }, color: '#9CA3AF' },
  { key: 'ingesting', label: { es: 'Escaneando repo...', en: 'Scanning repo...' }, color: '#6366F1' },
  { key: 'refactoring', label: { es: 'Refactorizando...', en: 'Refactoring...' }, color: '#F59E0B' },
  { key: 'testing', label: { es: 'Generando tests...', en: 'Generating tests...' }, color: '#10B981' },
  { key: 'done', label: { es: 'Completado', en: 'Done' }, color: '#059669' },
  { key: 'error', label: { es: 'Error', en: 'Error' }, color: '#EF4444' },
]

export default function RefactorDashboard({ lang = 'es' }) {
  const isMobile = useIsMobile()
  const [repoPath, setRepoPath] = useState('')
  const [phase, setPhase] = useState('idle')
  const [ingestResult, setIngestResult] = useState(null)
  const [refactorResult, setRefactorResult] = useState(null)
  const [testResult, setTestResult] = useState(null)
  const [error, setError] = useState(null)
  const [dryRun, setDryRun] = useState(true)

  const currentPhase = PHASES.find(p => p.key === phase) || PHASES[0]

  const handleIngest = async () => {
    if (!repoPath.trim()) return
    setPhase('ingesting')
    setError(null)
    setIngestResult(null)
    setRefactorResult(null)
    setTestResult(null)

    const res = await fetchAPI('/refactor/ingest', {
      method: 'POST',
      body: JSON.stringify({ path: repoPath.trim() }),
    })

    if (res.error) {
      setPhase('error')
      setError(res.error)
      return
    }
    setIngestResult(res.data)
    setPhase('idle')
  }

  const handleRefactor = async () => {
    setPhase('refactoring')
    setError(null)
    const res = await fetchAPI('/refactor/execute', {
      method: 'POST',
      body: JSON.stringify({ project_path: repoPath.trim(), dry_run: dryRun, use_llm: !dryRun }),
    })
    if (res.error) {
      setPhase('error')
      setError(res.error)
      return
    }
    setRefactorResult(res.data)
    setPhase('idle')
  }

  const handleGenerateTests = async () => {
    setPhase('testing')
    setError(null)
    const res = await fetchAPI('/refactor/generate-tests', {
      method: 'POST',
      body: JSON.stringify({ project_path: repoPath.trim(), dry_run: dryRun }),
    })
    if (res.error) {
      setPhase('error')
      setError(res.error)
      return
    }
    setTestResult(res.data)
    setPhase('done')
  }

  const handleFullPipeline = async () => {
    await handleIngest()
    if (phase === 'error') return
    await handleRefactor()
    if (phase === 'error') return
    await handleGenerateTests()
  }

  return (
    <div style={{ padding: isMobile ? 16 : 32, maxWidth: 1200, margin: '0 auto' }}>
      {/* Header */}
      <div style={{ marginBottom: 24 }}>
        <h1 style={{ fontSize: 24, fontWeight: 800, color: '#111827', marginBottom: 4 }}>
          {lang === 'es' ? 'Refactoring Engine' : 'Refactoring Engine'}
        </h1>
        <p style={{ fontSize: 14, color: '#9CA3AF' }}>
          {lang === 'es'
            ? 'Escanea, refactoriza y genera tests para cualquier codebase en minutos.'
            : 'Scan, refactor, and generate tests for any codebase in minutes.'}
        </p>
      </div>

      {/* Input */}
      <div style={{
        background: '#fff', borderRadius: 12, border: '1px solid #E5E7EB',
        padding: 20, marginBottom: 20,
      }}>
        <label style={{ fontSize: 13, fontWeight: 600, color: '#374151', display: 'block', marginBottom: 8 }}>
          {lang === 'es' ? 'Ruta del repositorio' : 'Repository path'}
        </label>
        <div style={{ display: 'flex', gap: 8, flexWrap: 'wrap' }}>
          <input
            type="text"
            value={repoPath}
            onChange={e => setRepoPath(e.target.value)}
            placeholder={lang === 'es' ? '/ruta/al/repositorio o URL git' : '/path/to/repo or git URL'}
            style={{
              flex: 1, minWidth: 250, padding: '10px 14px', borderRadius: 8,
              border: '1px solid #D1D5DB', fontSize: 14, fontFamily: 'monospace',
            }}
          />
          <label style={{ display: 'flex', alignItems: 'center', gap: 6, fontSize: 13, color: '#6B7280', cursor: 'pointer' }}>
            <input type="checkbox" checked={dryRun} onChange={e => setDryRun(e.target.checked)} />
            Dry run
          </label>
          <button
            onClick={handleFullPipeline}
            disabled={!repoPath.trim() || (phase !== 'idle' && phase !== 'done' && phase !== 'error')}
            style={{
              padding: '10px 20px', borderRadius: 8, border: 'none',
              background: 'linear-gradient(135deg, #6366F1, #8B5CF6)',
              color: '#fff', fontWeight: 600, fontSize: 14, cursor: 'pointer',
              opacity: !repoPath.trim() ? 0.5 : 1,
            }}
          >
            {lang === 'es' ? 'Ejecutar Pipeline Completo' : 'Run Full Pipeline'}
          </button>
        </div>

        {/* Phase indicator */}
        {phase !== 'idle' && (
          <div style={{
            marginTop: 12, padding: '8px 14px', borderRadius: 8,
            background: `${currentPhase.color}15`, color: currentPhase.color,
            fontSize: 13, fontWeight: 600,
          }}>
            {phase === 'ingesting' && '1/3 '}{phase === 'refactoring' && '2/3 '}{phase === 'testing' && '3/3 '}
            {currentPhase.label[lang]}
          </div>
        )}

        {error && (
          <div style={{ marginTop: 12, padding: 12, borderRadius: 8, background: '#FEE2E2', color: '#DC2626', fontSize: 13 }}>
            {error}
          </div>
        )}
      </div>

      {/* Results Grid */}
      <div style={{ display: 'grid', gridTemplateColumns: isMobile ? '1fr' : '1fr 1fr 1fr', gap: 16 }}>
        {/* Ingestion Results */}
        {ingestResult && (
          <div style={{ background: '#fff', borderRadius: 12, border: '1px solid #E5E7EB', padding: 20 }}>
            <h3 style={{ fontSize: 15, fontWeight: 700, color: '#6366F1', marginBottom: 12 }}>
              {lang === 'es' ? 'Analisis del Repo' : 'Repo Analysis'}
            </h3>
            <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 8 }}>
              <Stat label="Files" value={ingestResult.total_files} />
              <Stat label="Lines" value={ingestResult.total_lines?.toLocaleString()} />
              <Stat label="Modules" value={Object.keys(ingestResult.modules || {}).length} />
              <Stat label="Hotspots" value={ingestResult.vulnerability_hotspots?.length || 0} color="#EF4444" />
            </div>
            {ingestResult.languages && (
              <div style={{ marginTop: 12, fontSize: 12, color: '#6B7280' }}>
                {Object.entries(ingestResult.languages).map(([l, c]) => `${l}: ${c}`).join(', ')}
              </div>
            )}
            <div style={{ marginTop: 8, fontSize: 11, color: '#9CA3AF' }}>
              {ingestResult.scan_duration_ms}ms
            </div>
          </div>
        )}

        {/* Refactor Results */}
        {refactorResult && (
          <div style={{ background: '#fff', borderRadius: 12, border: '1px solid #E5E7EB', padding: 20 }}>
            <h3 style={{ fontSize: 15, fontWeight: 700, color: '#F59E0B', marginBottom: 12 }}>
              {lang === 'es' ? 'Refactorizacion' : 'Refactoring'}
            </h3>
            <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 8 }}>
              <Stat label={lang === 'es' ? 'Corregidos' : 'Fixed'} value={refactorResult.summary?.fixed || 0} color="#10B981" />
              <Stat label={lang === 'es' ? 'Fallidos' : 'Failed'} value={refactorResult.summary?.failed || 0} color="#EF4444" />
              <Stat label="Vulns fixed" value={refactorResult.summary?.vulnerabilities_fixed || 0} />
              <Stat label="Tests OK" value={refactorResult.summary?.tests_passing || 0} />
            </div>
            <div style={{ marginTop: 8, fontSize: 11, color: '#9CA3AF' }}>
              {refactorResult.duration_ms}ms | ${refactorResult.cost?.usd?.toFixed(4) || '0.00'}
            </div>
          </div>
        )}

        {/* Test Gen Results */}
        {testResult && (
          <div style={{ background: '#fff', borderRadius: 12, border: '1px solid #E5E7EB', padding: 20 }}>
            <h3 style={{ fontSize: 15, fontWeight: 700, color: '#10B981', marginBottom: 12 }}>
              {lang === 'es' ? 'Tests Generados' : 'Tests Generated'}
            </h3>
            <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 8 }}>
              <Stat label={lang === 'es' ? 'Archivos' : 'Files'} value={testResult.test_files_generated || 0} />
              <Stat label={lang === 'es' ? 'Funciones' : 'Functions'} value={testResult.functions_tested || 0} />
              <Stat label={lang === 'es' ? 'Lineas' : 'Lines'} value={testResult.total_lines || 0} />
              <Stat label={lang === 'es' ? 'Analizados' : 'Analyzed'} value={testResult.files_analyzed || 0} />
            </div>
            <div style={{ marginTop: 8, fontSize: 11, color: '#9CA3AF' }}>
              {testResult.duration_ms}ms
            </div>
          </div>
        )}
      </div>

      {/* Hotspots Table */}
      {ingestResult?.vulnerability_hotspots?.length > 0 && (
        <div style={{ background: '#fff', borderRadius: 12, border: '1px solid #E5E7EB', padding: 20, marginTop: 16 }}>
          <h3 style={{ fontSize: 15, fontWeight: 700, color: '#EF4444', marginBottom: 12 }}>
            {lang === 'es' ? 'Puntos Criticos' : 'Vulnerability Hotspots'}
          </h3>
          <div style={{ overflowX: 'auto' }}>
            <table style={{ width: '100%', fontSize: 13, borderCollapse: 'collapse' }}>
              <thead>
                <tr style={{ borderBottom: '1px solid #E5E7EB' }}>
                  <th style={{ textAlign: 'left', padding: 8, color: '#6B7280' }}>File</th>
                  <th style={{ textAlign: 'center', padding: 8, color: '#6B7280' }}>Vulns</th>
                  <th style={{ textAlign: 'center', padding: 8, color: '#6B7280' }}>Lines</th>
                  <th style={{ textAlign: 'center', padding: 8, color: '#6B7280' }}>Complexity</th>
                </tr>
              </thead>
              <tbody>
                {ingestResult.vulnerability_hotspots.slice(0, 15).map((h, i) => (
                  <tr key={i} style={{ borderBottom: '1px solid #F3F4F6' }}>
                    <td style={{ padding: 8, fontFamily: 'monospace', fontSize: 12 }}>{h.file}</td>
                    <td style={{ padding: 8, textAlign: 'center', fontWeight: 700, color: '#EF4444' }}>{h.vulnerabilities}</td>
                    <td style={{ padding: 8, textAlign: 'center' }}>{h.lines}</td>
                    <td style={{ padding: 8, textAlign: 'center' }}>
                      <span style={{
                        padding: '2px 8px', borderRadius: 4, fontSize: 11, fontWeight: 600,
                        background: h.complexity === 'high' ? '#FEE2E2' : h.complexity === 'medium' ? '#FEF3C7' : '#D1FAE5',
                        color: h.complexity === 'high' ? '#DC2626' : h.complexity === 'medium' ? '#D97706' : '#059669',
                      }}>
                        {h.complexity}
                      </span>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>
      )}
    </div>
  )
}

function Stat({ label, value, color }) {
  return (
    <div>
      <div style={{ fontSize: 11, color: '#9CA3AF', marginBottom: 2 }}>{label}</div>
      <div style={{ fontSize: 20, fontWeight: 800, color: color || '#111827' }}>{value}</div>
    </div>
  )
}
