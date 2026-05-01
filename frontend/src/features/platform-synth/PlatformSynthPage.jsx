/**
 * Platform Synthesizer — chat + template suggestion fusion.
 *
 * UX shape:
 *   ┌────────────────────────┬────────────────────┐
 *   │ Chat panel (60%)       │ Template panel     │
 *   │ - history bubbles      │ (40%)              │
 *   │ - input box            │ - live suggestions │
 *   │                        │ - score bars       │
 *   │                        │ - Build button     │
 *   └────────────────────────┴────────────────────┘
 *
 * Each chat turn updates the spec on the right in real time.
 * The template list re-ranks as the spec accumulates. Click a
 * template card to lock it in; once a project_name + template
 * are set, the Build button activates.
 */
import { useEffect, useRef, useState } from 'react'
import { fetchAPI } from '../../services/api'

const T = {
  en: {
    title: 'Platform Synthesizer',
    subtitle: 'Describe what you want to build and I\'ll generate the project.',
    placeholder: 'Tell me what you\'re building (e.g., "an inventory tracker for my warehouse, with Slack alerts")...',
    send: 'Send',
    thinking: 'Thinking…',
    templatesTitle: 'Template suggestions',
    noSuggestions: 'Templates will rank as you describe more about your project.',
    selected: 'Selected',
    select: 'Use this',
    specTitle: 'Detected spec',
    buildButton: 'Build project',
    buildPath: 'Output directory (server-side, must be under PLATFORM_SYNTH_ROOT)',
    building: 'Building…',
    buildSuccess: 'Project generated',
    nextSteps: 'Next steps',
    optionsTitle: 'Build options',
    gitInitLabel: 'Initialize git repo + first commit',
    gitInitHelp: 'Runs git init in the project dir and commits all files. Idempotent.',
    ghCreateLabel: 'Create GitHub repo (requires gh CLI authenticated)',
    ghCreateHelp: 'Calls `gh repo create --source=. --push`. Needs git_init.',
    ghVisibilityLabel: 'GitHub repo visibility',
    ghVisibilityPrivate: 'Private',
    ghVisibilityPublic: 'Public',
    mythosLabel: 'Mythos pre-flight scan',
    mythosHelp: 'Runs the security scanner on the generated project (~1-3s). Surfaces critical/high findings before delivery.',
    mythosScore: 'Mythos score',
    mythosFindings: 'Findings flagged',
    githubRepo: 'GitHub repo',
    gitCommit: 'First commit',
    warningsTitle: 'Warnings',
  },
  es: {
    title: 'Sintetizador de Plataformas',
    subtitle: 'Describe lo que quieres construir y te genero el proyecto.',
    placeholder: 'Dime qué estás construyendo (ej: "un tracker de inventario para mi almacén, con alertas Slack")...',
    send: 'Enviar',
    thinking: 'Pensando…',
    templatesTitle: 'Templates sugeridos',
    noSuggestions: 'Los templates se rankean conforme describes tu proyecto.',
    selected: 'Seleccionado',
    select: 'Usar este',
    specTitle: 'Spec detectado',
    buildButton: 'Construir proyecto',
    buildPath: 'Directorio de salida (server-side, debe estar bajo PLATFORM_SYNTH_ROOT)',
    building: 'Construyendo…',
    buildSuccess: 'Proyecto generado',
    nextSteps: 'Próximos pasos',
    optionsTitle: 'Opciones de build',
    gitInitLabel: 'Inicializar repo git + primer commit',
    gitInitHelp: 'Ejecuta git init en el directorio y commitea todos los archivos. Idempotente.',
    ghCreateLabel: 'Crear repo en GitHub (requiere gh CLI autenticado)',
    ghCreateHelp: 'Llama `gh repo create --source=. --push`. Requiere git_init.',
    ghVisibilityLabel: 'Visibilidad del repo GitHub',
    ghVisibilityPrivate: 'Privado',
    ghVisibilityPublic: 'Público',
    mythosLabel: 'Scan Mythos pre-flight',
    mythosHelp: 'Corre el scanner de seguridad sobre el proyecto generado (~1-3s). Marca findings critical/high antes de entregar.',
    mythosScore: 'Mythos score',
    mythosFindings: 'Findings detectados',
    githubRepo: 'Repo GitHub',
    gitCommit: 'Primer commit',
    warningsTitle: 'Advertencias',
  },
}

export default function PlatformSynthPage({ lang = 'en' }) {
  const t = T[lang] || T.en
  const [history, setHistory] = useState([
    {
      role: 'assistant',
      content:
        lang === 'es'
          ? '¡Hola! Cuéntame qué quieres construir. Puede ser un dashboard, un API, una herramienta interna — describe el problema en tus palabras y vamos refinando.'
          : "Hi! Tell me what you want to build. A dashboard, an API, an internal tool — describe the problem in your own words and we'll refine from there.",
    },
  ])
  const [input, setInput] = useState('')
  const [spec, setSpec] = useState({})
  const [suggestions, setSuggestions] = useState([])
  const [selectedTemplate, setSelectedTemplate] = useState(null)
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState(null)
  const [buildState, setBuildState] = useState(null) // null | 'building' | result | error
  const [targetDir, setTargetDir] = useState('')
  // Build option toggles (mirror BuildRequest backend flags)
  const [gitInit, setGitInit] = useState(false)
  const [ghCreate, setGhCreate] = useState(false)
  const [ghVisibility, setGhVisibility] = useState('private')
  const [mythosPreflight, setMythosPreflight] = useState(false)
  const chatEndRef = useRef(null)

  useEffect(() => {
    chatEndRef.current?.scrollIntoView({ behavior: 'smooth' })
  }, [history, loading])

  // On mount, fetch the templates list so the panel isn't blank
  // before any chat happens.
  useEffect(() => {
    fetchAPI('/platform-synth/templates').then(res => {
      if (res.data?.templates) {
        // Show all templates with score 0 until chat populates them.
        setSuggestions(
          res.data.templates.map(template => ({
            template,
            score: 0,
            matched_signals: [],
          }))
        )
      }
    })
  }, [])

  async function send() {
    if (!input.trim() || loading) return
    const userMsg = input.trim()
    setInput('')
    setError(null)
    const newHistory = [...history, { role: 'user', content: userMsg }]
    setHistory(newHistory)
    setLoading(true)

    const res = await fetchAPI('/platform-synth/chat', {
      method: 'POST',
      body: JSON.stringify({
        user_message: userMsg,
        history: newHistory.slice(0, -1), // exclude the just-added msg from history
        current_spec: Object.keys(spec).length ? spec : null,
      }),
    })

    setLoading(false)

    if (res.error) {
      setError(res.error)
      return
    }
    const data = res.data
    setHistory(h => [...h, { role: 'assistant', content: data.assistant_message }])
    setSpec(data.spec || {})
    setSuggestions(data.template_suggestions || [])

    // Auto-pre-fill targetDir suggestion the first time we have a project_name.
    if (data.spec?.project_name && !targetDir) {
      setTargetDir(`~/nexusforge-generated/${data.spec.project_name}`)
    }
  }

  function onKeyDown(e) {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault()
      send()
    }
  }

  async function build() {
    if (!selectedTemplate || !spec.project_name || !targetDir.trim()) return
    setBuildState('building')
    setError(null)
    const res = await fetchAPI('/platform-synth/build', {
      method: 'POST',
      body: JSON.stringify({
        template_id: selectedTemplate,
        spec,
        target_dir: targetDir.trim(),
        git_init: gitInit,
        github_repo_create: ghCreate,
        github_repo_visibility: ghVisibility,
        mythos_preflight: mythosPreflight,
      }),
    })
    if (res.error) {
      setError(res.error)
      setBuildState('error')
      return
    }
    setBuildState(res.data)
  }

  const canBuild =
    selectedTemplate &&
    spec.project_name &&
    targetDir.trim() &&
    buildState !== 'building'

  return (
    <div style={{ maxWidth: 1280, margin: '0 auto', padding: 20 }}>
      <h1 style={{ fontSize: 24, fontWeight: 700, marginBottom: 4 }}>{t.title}</h1>
      <p style={{ fontSize: 14, color: '#6B7280', marginBottom: 20 }}>{t.subtitle}</p>

      <div
        style={{
          display: 'grid',
          gridTemplateColumns: '1.5fr 1fr',
          gap: 16,
          minHeight: 600,
        }}
      >
        {/* CHAT PANEL */}
        <section
          style={{
            background: '#fff',
            border: '1px solid #E5E7EB',
            borderRadius: 12,
            padding: 16,
            display: 'flex',
            flexDirection: 'column',
            minHeight: 600,
          }}
        >
          <div style={{ flex: 1, overflowY: 'auto', maxHeight: 480, paddingRight: 8 }}>
            {history.map((m, i) => (
              <div
                key={i}
                style={{
                  marginBottom: 12,
                  display: 'flex',
                  justifyContent: m.role === 'user' ? 'flex-end' : 'flex-start',
                }}
              >
                <div
                  style={{
                    maxWidth: '80%',
                    padding: '10px 14px',
                    borderRadius: 12,
                    background: m.role === 'user' ? '#6366F1' : '#F3F4F6',
                    color: m.role === 'user' ? '#fff' : '#111827',
                    fontSize: 14,
                    lineHeight: 1.5,
                    whiteSpace: 'pre-wrap',
                  }}
                >
                  {m.content}
                </div>
              </div>
            ))}
            {loading && (
              <div style={{ color: '#9CA3AF', fontSize: 13, padding: 8 }}>{t.thinking}</div>
            )}
            <div ref={chatEndRef} />
          </div>

          <div style={{ display: 'flex', gap: 8, marginTop: 12 }}>
            <textarea
              value={input}
              onChange={e => setInput(e.target.value)}
              onKeyDown={onKeyDown}
              placeholder={t.placeholder}
              rows={2}
              style={{
                flex: 1,
                padding: 10,
                borderRadius: 8,
                border: '1px solid #D1D5DB',
                fontSize: 14,
                resize: 'vertical',
                outline: 'none',
                fontFamily: 'inherit',
              }}
            />
            <button
              onClick={send}
              disabled={loading || !input.trim()}
              style={{
                padding: '0 20px',
                borderRadius: 8,
                border: 'none',
                background: loading || !input.trim() ? '#9CA3AF' : '#6366F1',
                color: '#fff',
                fontWeight: 600,
                cursor: loading || !input.trim() ? 'default' : 'pointer',
              }}
            >
              {t.send}
            </button>
          </div>
          {error && (
            <p style={{ color: '#DC2626', fontSize: 13, marginTop: 8 }}>{error}</p>
          )}
        </section>

        {/* RIGHT PANEL */}
        <section style={{ display: 'flex', flexDirection: 'column', gap: 16 }}>
          {/* Template suggestions */}
          <div
            style={{
              background: '#fff',
              border: '1px solid #E5E7EB',
              borderRadius: 12,
              padding: 16,
            }}
          >
            <h3 style={{ fontSize: 14, fontWeight: 600, marginBottom: 8 }}>
              {t.templatesTitle}
            </h3>
            {suggestions.length === 0 && (
              <p style={{ fontSize: 12, color: '#9CA3AF' }}>{t.noSuggestions}</p>
            )}
            {suggestions.map(s => {
              const isSelected = selectedTemplate === s.template.template_id
              const isCompatible = s.score > 0
              return (
                <div
                  key={s.template.template_id}
                  style={{
                    border: isSelected ? '2px solid #6366F1' : '1px solid #E5E7EB',
                    borderRadius: 8,
                    padding: 12,
                    marginBottom: 8,
                    opacity: isCompatible ? 1 : 0.5,
                    background: isSelected ? '#EEF2FF' : '#fff',
                  }}
                >
                  <div
                    style={{
                      display: 'flex',
                      justifyContent: 'space-between',
                      alignItems: 'baseline',
                      marginBottom: 4,
                    }}
                  >
                    <strong style={{ fontSize: 13 }}>{s.template.name}</strong>
                    <span style={{ fontSize: 11, color: '#6B7280' }}>
                      {Math.round(s.score * 100)}%
                    </span>
                  </div>
                  <p style={{ fontSize: 12, color: '#6B7280', marginBottom: 6 }}>
                    {s.template.short_description}
                  </p>
                  <div style={{ fontSize: 11, color: '#9CA3AF', marginBottom: 8 }}>
                    {s.template.stack.join(' · ')}
                  </div>
                  {/* Score bar */}
                  <div
                    style={{
                      height: 4,
                      background: '#E5E7EB',
                      borderRadius: 2,
                      marginBottom: 8,
                      overflow: 'hidden',
                    }}
                  >
                    <div
                      style={{
                        width: `${s.score * 100}%`,
                        height: '100%',
                        background: isCompatible ? '#10B981' : '#9CA3AF',
                        transition: 'width 0.3s',
                      }}
                    />
                  </div>
                  <button
                    onClick={() => isCompatible && setSelectedTemplate(s.template.template_id)}
                    disabled={!isCompatible}
                    style={{
                      width: '100%',
                      padding: '6px 10px',
                      fontSize: 12,
                      borderRadius: 6,
                      border: '1px solid',
                      borderColor: isSelected ? '#6366F1' : '#D1D5DB',
                      background: isSelected ? '#6366F1' : '#fff',
                      color: isSelected ? '#fff' : isCompatible ? '#374151' : '#9CA3AF',
                      cursor: isCompatible ? 'pointer' : 'not-allowed',
                      fontWeight: 600,
                    }}
                  >
                    {isSelected ? t.selected : t.select}
                  </button>
                  {s.matched_signals?.length > 0 && (
                    <details style={{ fontSize: 11, color: '#9CA3AF', marginTop: 6 }}>
                      <summary style={{ cursor: 'pointer' }}>signals</summary>
                      <ul style={{ margin: '4px 0 0 16px', padding: 0 }}>
                        {s.matched_signals.map((sig, i) => (
                          <li key={i}>{sig}</li>
                        ))}
                      </ul>
                    </details>
                  )}
                </div>
              )
            })}
          </div>

          {/* Spec preview */}
          <div
            style={{
              background: '#fff',
              border: '1px solid #E5E7EB',
              borderRadius: 12,
              padding: 16,
            }}
          >
            <h3 style={{ fontSize: 14, fontWeight: 600, marginBottom: 8 }}>{t.specTitle}</h3>
            <pre
              style={{
                fontSize: 11,
                background: '#F9FAFB',
                padding: 10,
                borderRadius: 6,
                margin: 0,
                overflow: 'auto',
                maxHeight: 200,
                fontFamily: 'monospace',
              }}
            >
              {Object.keys(spec).length === 0
                ? '{}'
                : JSON.stringify(spec, null, 2)}
            </pre>
          </div>

          {/* Build */}
          <div
            style={{
              background: '#fff',
              border: '1px solid #E5E7EB',
              borderRadius: 12,
              padding: 16,
            }}
          >
            <label style={{ fontSize: 12, color: '#6B7280', display: 'block', marginBottom: 4 }}>
              {t.buildPath}
            </label>
            <input
              value={targetDir}
              onChange={e => setTargetDir(e.target.value)}
              placeholder="~/nexusforge-generated/my-project"
              style={{
                width: '100%',
                padding: 8,
                borderRadius: 6,
                border: '1px solid #D1D5DB',
                fontSize: 13,
                marginBottom: 12,
                fontFamily: 'monospace',
                boxSizing: 'border-box',
              }}
            />

            {/* Build options — mirror BuildRequest backend flags */}
            <div
              style={{
                fontSize: 12,
                color: '#374151',
                marginBottom: 12,
                paddingTop: 8,
                borderTop: '1px solid #F3F4F6',
              }}
            >
              <div style={{ fontWeight: 600, marginBottom: 8, color: '#6B7280' }}>
                {t.optionsTitle}
              </div>

              <label style={{ display: 'block', marginBottom: 8, cursor: 'pointer' }}>
                <input
                  type="checkbox"
                  checked={gitInit}
                  onChange={e => setGitInit(e.target.checked)}
                  style={{ marginRight: 6, verticalAlign: 'middle' }}
                />
                <strong>{t.gitInitLabel}</strong>
                <div style={{ fontSize: 11, color: '#9CA3AF', marginLeft: 22, marginTop: 2 }}>
                  {t.gitInitHelp}
                </div>
              </label>

              <label
                style={{
                  display: 'block',
                  marginBottom: 8,
                  cursor: gitInit ? 'pointer' : 'not-allowed',
                  opacity: gitInit ? 1 : 0.5,
                }}
              >
                <input
                  type="checkbox"
                  checked={ghCreate}
                  disabled={!gitInit}
                  onChange={e => setGhCreate(e.target.checked)}
                  style={{ marginRight: 6, verticalAlign: 'middle' }}
                />
                <strong>{t.ghCreateLabel}</strong>
                <div style={{ fontSize: 11, color: '#9CA3AF', marginLeft: 22, marginTop: 2 }}>
                  {t.ghCreateHelp}
                </div>
                {ghCreate && (
                  <div style={{ marginLeft: 22, marginTop: 6 }}>
                    <span style={{ fontSize: 11, color: '#6B7280', marginRight: 8 }}>
                      {t.ghVisibilityLabel}:
                    </span>
                    <label style={{ marginRight: 12, fontSize: 11 }}>
                      <input
                        type="radio"
                        name="gh-vis"
                        value="private"
                        checked={ghVisibility === 'private'}
                        onChange={e => setGhVisibility(e.target.value)}
                        style={{ marginRight: 4 }}
                      />
                      {t.ghVisibilityPrivate}
                    </label>
                    <label style={{ fontSize: 11 }}>
                      <input
                        type="radio"
                        name="gh-vis"
                        value="public"
                        checked={ghVisibility === 'public'}
                        onChange={e => setGhVisibility(e.target.value)}
                        style={{ marginRight: 4 }}
                      />
                      {t.ghVisibilityPublic}
                    </label>
                  </div>
                )}
              </label>

              <label style={{ display: 'block', marginBottom: 4, cursor: 'pointer' }}>
                <input
                  type="checkbox"
                  checked={mythosPreflight}
                  onChange={e => setMythosPreflight(e.target.checked)}
                  style={{ marginRight: 6, verticalAlign: 'middle' }}
                />
                <strong>{t.mythosLabel}</strong>
                <div style={{ fontSize: 11, color: '#9CA3AF', marginLeft: 22, marginTop: 2 }}>
                  {t.mythosHelp}
                </div>
              </label>
            </div>

            <button
              onClick={build}
              disabled={!canBuild}
              style={{
                width: '100%',
                padding: '10px 16px',
                borderRadius: 8,
                border: 'none',
                background: canBuild ? '#10B981' : '#D1D5DB',
                color: '#fff',
                fontWeight: 600,
                fontSize: 14,
                cursor: canBuild ? 'pointer' : 'not-allowed',
              }}
            >
              {buildState === 'building' ? t.building : t.buildButton}
            </button>
            {buildState && typeof buildState === 'object' && buildState.project_path && (
              <div
                style={{
                  marginTop: 12,
                  padding: 10,
                  background: buildState.status === 'partial' ? '#FFFBEB' : '#ECFDF5',
                  borderRadius: 6,
                  fontSize: 12,
                  color: buildState.status === 'partial' ? '#92400E' : '#065F46',
                  border: `1px solid ${buildState.status === 'partial' ? '#FCD34D' : '#A7F3D0'}`,
                }}
              >
                <strong>{t.buildSuccess}</strong>
                {buildState.status === 'partial' && (
                  <span style={{ marginLeft: 6, fontSize: 11, fontWeight: 600 }}>
                    ({buildState.status})
                  </span>
                )}
                <div style={{ marginTop: 4, fontFamily: 'monospace', fontSize: 11 }}>
                  {buildState.project_path}
                </div>
                <div style={{ marginTop: 4 }}>{buildState.files_written} files</div>

                {buildState.git_initialized && (
                  <div style={{ marginTop: 6 }}>
                    <strong>{t.gitCommit}:</strong>{' '}
                    <code style={{ fontSize: 10, background: 'rgba(0,0,0,0.05)', padding: '1px 4px', borderRadius: 3 }}>
                      {(buildState.git_first_commit_sha || '').slice(0, 12)}
                    </code>
                  </div>
                )}

                {buildState.github_repo_url && (
                  <div style={{ marginTop: 6 }}>
                    <strong>{t.githubRepo}:</strong>{' '}
                    <a
                      href={buildState.github_repo_url}
                      target="_blank"
                      rel="noopener noreferrer"
                      style={{ color: '#1D4ED8', textDecoration: 'underline' }}
                    >
                      {buildState.github_repo_url}
                    </a>
                  </div>
                )}

                {buildState.mythos_ran && (
                  <div style={{ marginTop: 6 }}>
                    <strong>{t.mythosScore}:</strong>{' '}
                    <span
                      style={{
                        fontWeight: 700,
                        color:
                          (buildState.mythos_score ?? 100) >= 90
                            ? '#059669'
                            : (buildState.mythos_score ?? 100) >= 70
                            ? '#D97706'
                            : '#DC2626',
                      }}
                    >
                      {buildState.mythos_score}/100
                    </span>
                    {(buildState.mythos_critical_count > 0 ||
                      buildState.mythos_high_count > 0) && (
                      <span style={{ marginLeft: 8 }}>
                        ({buildState.mythos_critical_count} critical,{' '}
                        {buildState.mythos_high_count} high)
                      </span>
                    )}
                  </div>
                )}

                {buildState.mythos_findings_summary?.length > 0 && (
                  <details style={{ marginTop: 6 }}>
                    <summary style={{ cursor: 'pointer', fontSize: 11 }}>
                      {t.mythosFindings}: {buildState.mythos_findings_summary.length}
                    </summary>
                    <ul style={{ margin: '4px 0 0 16px', padding: 0, fontSize: 11, fontFamily: 'monospace' }}>
                      {buildState.mythos_findings_summary.map((f, i) => (
                        <li key={i}>{f}</li>
                      ))}
                    </ul>
                  </details>
                )}

                {buildState.post_build_warnings?.length > 0 && (
                  <details style={{ marginTop: 6 }}>
                    <summary style={{ cursor: 'pointer', fontSize: 11 }}>
                      {t.warningsTitle}: {buildState.post_build_warnings.length}
                    </summary>
                    <ul style={{ margin: '4px 0 0 16px', padding: 0, fontSize: 11 }}>
                      {buildState.post_build_warnings.map((w, i) => (
                        <li key={i}>{w}</li>
                      ))}
                    </ul>
                  </details>
                )}

                <div style={{ marginTop: 8, fontSize: 11 }}>
                  <strong>{t.nextSteps}:</strong>
                  <ul style={{ margin: '4px 0 0 16px', padding: 0 }}>
                    {buildState.next_steps?.map((step, i) => (
                      <li key={i}>{step}</li>
                    ))}
                  </ul>
                </div>
              </div>
            )}
          </div>
        </section>
      </div>
    </div>
  )
}
