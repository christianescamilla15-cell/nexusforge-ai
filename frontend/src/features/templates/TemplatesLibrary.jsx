import { useState, useEffect } from 'react'
import { fetchAPI } from '../../services/api'
import { useToast } from '../../shared/hooks/useToast'
import { addNotification } from '../../shared/components/NotificationBell'

const CATEGORY_BADGE = {
  support:    { en: 'Support',    es: 'Soporte',      color: '#EF4444', bg: 'rgba(239,68,68,0.1)' },
  finance:    { en: 'Finance',    es: 'Finanzas',     color: '#10B981', bg: 'rgba(16,185,129,0.1)' },
  hr:         { en: 'HR',         es: 'RRHH',         color: '#F59E0B', bg: 'rgba(245,158,11,0.1)' },
  marketing:  { en: 'Marketing',  es: 'Marketing',    color: '#EC4899', bg: 'rgba(236,72,153,0.1)' },
  operations: { en: 'Operations', es: 'Operaciones',  color: '#8B5CF6', bg: 'rgba(139,92,246,0.1)' },
}

const CONNECTOR_ICON = {
  gmail:  '📧',
  slack:  '💬',
  drive:  '📁',
  notion: '📝',
}

function DeployModal({ template, lang, onClose, onConfirm, deploying }) {
  const [nameOverride, setNameOverride] = useState(template.name)

  return (
    <div style={{
      position: 'fixed', inset: 0, background: 'rgba(0,0,0,0.5)',
      display: 'flex', alignItems: 'center', justifyContent: 'center',
      zIndex: 200, backdropFilter: 'blur(4px)',
    }} onClick={onClose}>
      <div onClick={e => e.stopPropagation()} style={{
        background: '#fff', borderRadius: 16, padding: 28, width: '100%', maxWidth: 460,
        border: '1px solid #E5E7EB', boxShadow: '0 24px 48px rgba(0,0,0,0.2)',
      }}>
        <div style={{ display: 'flex', alignItems: 'center', gap: 12, marginBottom: 20 }}>
          <div style={{
            width: 48, height: 48, borderRadius: 12,
            background: `${template.color}15`,
            display: 'flex', alignItems: 'center', justifyContent: 'center', fontSize: 24,
          }}>
            {template.icon}
          </div>
          <div>
            <h3 style={{ fontSize: 17, fontWeight: 700, color: '#111827', margin: 0 }}>
              {lang === 'es' ? 'Desplegar plantilla' : 'Deploy Template'}
            </h3>
            <p style={{ fontSize: 13, color: '#9CA3AF', margin: 0 }}>{template.name}</p>
          </div>
        </div>

        <p style={{ fontSize: 13, color: '#6B7280', lineHeight: 1.6, marginBottom: 20 }}>
          {template.description}
        </p>

        <div style={{ marginBottom: 20 }}>
          <label style={{ fontSize: 12, fontWeight: 600, color: '#6B7280', display: 'block', marginBottom: 6 }}>
            {lang === 'es' ? 'Nombre de la automatizacion' : 'Automation name'}
          </label>
          <input
            type="text"
            value={nameOverride}
            onChange={e => setNameOverride(e.target.value)}
            style={{
              width: '100%', padding: '10px 12px', borderRadius: 8,
              border: '1px solid #E5E7EB', fontSize: 14, outline: 'none',
              boxSizing: 'border-box',
            }}
            onFocus={e => e.currentTarget.style.borderColor = template.color}
            onBlur={e => e.currentTarget.style.borderColor = '#E5E7EB'}
          />
        </div>

        <div style={{ marginBottom: 20, padding: 14, background: '#F9FAFB', borderRadius: 10 }}>
          <div style={{ display: 'flex', justifyContent: 'space-between', fontSize: 13, color: '#6B7280', marginBottom: 8 }}>
            <span>{lang === 'es' ? 'Agentes' : 'Agents'}</span>
            <span style={{ fontWeight: 600, color: '#111827' }}>{template.estimated_agents}</span>
          </div>
          <div style={{ display: 'flex', justifyContent: 'space-between', fontSize: 13, color: '#6B7280', marginBottom: 8 }}>
            <span>{lang === 'es' ? 'Pasos del workflow' : 'Workflow steps'}</span>
            <span style={{ fontWeight: 600, color: '#111827' }}>{template.dag_definition?.steps?.length || 0}</span>
          </div>
          {template.default_rules?.length > 0 && (
            <div style={{ display: 'flex', justifyContent: 'space-between', fontSize: 13, color: '#6B7280' }}>
              <span>{lang === 'es' ? 'Reglas predeterminadas' : 'Default rules'}</span>
              <span style={{ fontWeight: 600, color: '#111827' }}>{template.default_rules.length}</span>
            </div>
          )}
        </div>

        {template.suggested_connectors?.length > 0 && (
          <div style={{ marginBottom: 20 }}>
            <p style={{ fontSize: 12, fontWeight: 600, color: '#9CA3AF', marginBottom: 8 }}>
              {lang === 'es' ? 'Conectores sugeridos' : 'Suggested connectors'}
            </p>
            <div style={{ display: 'flex', gap: 8 }}>
              {template.suggested_connectors.map(c => (
                <span key={c} style={{
                  padding: '4px 10px', borderRadius: 6, fontSize: 12, fontWeight: 500,
                  background: '#F3F4F6', color: '#374151',
                  display: 'flex', alignItems: 'center', gap: 4,
                }}>
                  {CONNECTOR_ICON[c] || '🔗'} {c}
                </span>
              ))}
            </div>
          </div>
        )}

        <div style={{ display: 'flex', gap: 10, justifyContent: 'flex-end' }}>
          <button onClick={onClose} disabled={deploying} style={{
            padding: '9px 18px', borderRadius: 8, border: '1px solid #E5E7EB',
            background: '#fff', fontSize: 13, fontWeight: 600, color: '#6B7280',
            cursor: 'pointer',
          }}>
            {lang === 'es' ? 'Cancelar' : 'Cancel'}
          </button>
          <button
            onClick={() => onConfirm(nameOverride)}
            disabled={deploying || !nameOverride.trim()}
            style={{
              padding: '9px 20px', borderRadius: 8, border: 'none',
              background: deploying ? '#A5B4FC' : `linear-gradient(135deg, ${template.color}, ${template.color}CC)`,
              fontSize: 13, fontWeight: 600, color: '#fff',
              cursor: deploying ? 'default' : 'pointer',
              display: 'flex', alignItems: 'center', gap: 6,
            }}
          >
            {deploying && (
              <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" style={{ animation: 'spin 1s linear infinite' }}>
                <path d="M21 12a9 9 0 11-6.219-8.56" />
              </svg>
            )}
            {deploying
              ? (lang === 'es' ? 'Desplegando...' : 'Deploying...')
              : (lang === 'es' ? 'Desplegar' : 'Deploy')}
          </button>
        </div>
      </div>
    </div>
  )
}


export default function TemplatesLibrary({ lang = 'en', onDeployed, isMobile = false }) {
  const [templates, setTemplates] = useState([])
  const [loading, setLoading] = useState(true)
  const [hoveredSlug, setHoveredSlug] = useState(null)
  const [deployTarget, setDeployTarget] = useState(null)
  const [deploying, setDeploying] = useState(false)
  const toast = useToast()

  useEffect(() => {
    fetchAPI('/templates/').then(res => {
      if (!res.error && Array.isArray(res.data)) {
        setTemplates(res.data)
      }
      setLoading(false)
    })
  }, [])

  const handleDeploy = async (nameOverride) => {
    if (!deployTarget) return
    setDeploying(true)
    const res = await fetchAPI(`/templates/${deployTarget.slug}/deploy`, {
      method: 'POST',
      body: JSON.stringify({ name_override: nameOverride }),
    })
    setDeploying(false)
    if (res.error) {
      toast.show(lang === 'es' ? `Error al desplegar: ${res.error}` : `Deploy failed: ${res.error}`, 'error')
      addNotification(lang === 'es' ? `Error al desplegar: ${res.error}` : `Deploy failed: ${res.error}`, 'error')
      return
    }
    setDeployTarget(null)
    const deployMsg = lang === 'es'
      ? `\u2705 ${nameOverride} desplegado exitosamente`
      : `\u2705 ${nameOverride} deployed successfully`
    toast.show(deployMsg, 'success')
    addNotification(deployMsg, 'success')
    if (res.data?.automation_id) {
      if (onDeployed) onDeployed(res.data)
    }
  }

  if (loading) {
    return (
      <div style={{ padding: 20, textAlign: 'center', color: '#9CA3AF', fontSize: 13 }}>
        {lang === 'es' ? 'Cargando plantillas...' : 'Loading templates...'}
      </div>
    )
  }

  if (templates.length === 0) return null

  const gridStyle = {
    display: 'grid',
    gridTemplateColumns: isMobile ? '1fr' : 'repeat(auto-fill, minmax(320px, 1fr))',
    gap: 20,
  }

  return (
    <div style={{ marginBottom: 32 }}>
      <p style={{ fontSize: 12, fontWeight: 700, color: '#9CA3AF', textTransform: 'uppercase', letterSpacing: '0.05em', marginBottom: 12 }}>
        {lang === 'es' ? 'Plantillas / Templates' : 'Templates'}
      </p>

      <div style={gridStyle}>
        {templates.map(tpl => {
          const cat = CATEGORY_BADGE[tpl.category] || CATEGORY_BADGE.operations
          const isHovered = hoveredSlug === tpl.slug
          const bgTint = `${tpl.color}12`

          return (
            <div
              key={tpl.slug}
              onMouseEnter={() => setHoveredSlug(tpl.slug)}
              onMouseLeave={() => setHoveredSlug(null)}
              style={{
                background: '#fff', borderRadius: 16, padding: 24,
                border: `1px solid ${isHovered ? tpl.color : '#E5E7EB'}`,
                transition: 'all 0.2s',
                boxShadow: isHovered ? `0 8px 24px ${bgTint}` : 'none',
              }}
            >
              {/* Header: icon + category */}
              <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start', marginBottom: 16 }}>
                <div style={{
                  width: 52, height: 52, borderRadius: 14, background: bgTint,
                  display: 'flex', alignItems: 'center', justifyContent: 'center', fontSize: 26,
                }}>
                  {tpl.icon}
                </div>
                <span style={{
                  padding: '4px 10px', borderRadius: 20, fontSize: 11, fontWeight: 600,
                  background: cat.bg, color: cat.color,
                }}>
                  {cat[lang]}
                </span>
              </div>

              {/* Name + description */}
              <h3 style={{ fontSize: 16, fontWeight: 700, color: '#111827', marginBottom: 8 }}>
                {tpl.name}
              </h3>
              <p style={{ fontSize: 13, color: '#6B7280', lineHeight: 1.5, marginBottom: 16, minHeight: 36 }}>
                {tpl.description}
              </p>

              {/* Connectors */}
              {tpl.suggested_connectors?.length > 0 && (
                <div style={{ display: 'flex', flexWrap: 'wrap', gap: 6, marginBottom: 16 }}>
                  {tpl.suggested_connectors.map(c => (
                    <span key={c} style={{
                      padding: '3px 10px', borderRadius: 6, fontSize: 11, fontWeight: 500,
                      background: bgTint, color: tpl.color,
                    }}>
                      {CONNECTOR_ICON[c] || '🔗'} {c}
                    </span>
                  ))}
                </div>
              )}

              {/* Footer: agent count + deploy button */}
              <div style={{
                display: 'flex', justifyContent: 'space-between', alignItems: 'center',
                paddingTop: 12, borderTop: '1px solid #F3F4F6',
              }}>
                <span style={{ fontSize: 12, color: '#9CA3AF' }}>
                  {tpl.estimated_agents} {lang === 'es' ? 'agentes' : 'agents'}
                  {' / '}
                  {tpl.dag_definition?.steps?.length || 0} {lang === 'es' ? 'pasos' : 'steps'}
                </span>
                <button
                  onClick={() => setDeployTarget(tpl)}
                  style={{
                    padding: '7px 16px', borderRadius: 8, border: 'none', fontSize: 13, fontWeight: 600,
                    background: `linear-gradient(135deg, ${tpl.color}, ${tpl.color}CC)`,
                    color: '#fff', cursor: 'pointer',
                    display: 'flex', alignItems: 'center', gap: 6,
                    transition: 'opacity 0.15s',
                    opacity: isHovered ? 1 : 0.85,
                  }}
                >
                  {lang === 'es' ? 'Desplegar' : 'Deploy'}
                  <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round">
                    <path d="M5 12h14m-7-7l7 7-7 7" />
                  </svg>
                </button>
              </div>
            </div>
          )
        })}
      </div>

      {deployTarget && (
        <DeployModal
          template={deployTarget}
          lang={lang}
          onClose={() => { if (!deploying) setDeployTarget(null) }}
          onConfirm={handleDeploy}
          deploying={deploying}
        />
      )}

      <style>{`@keyframes spin { from { transform: rotate(0deg) } to { transform: rotate(360deg) } }`}</style>
    </div>
  )
}
