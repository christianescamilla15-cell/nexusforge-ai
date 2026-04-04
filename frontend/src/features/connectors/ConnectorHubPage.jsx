import { useState, useEffect } from 'react'
import { fetchAPI } from '../../services/api'
import ConfirmModal from '../../shared/components/ConfirmModal'
import { useConfirm } from '../../shared/hooks/useConfirm'

const CONNECTOR_ICONS = {
  gmail: '📧', slack: '💬', notion: '📝', drive: '📁', rest: '🌐', postgres: '🐘',
}

export default function ConnectorHubPage({ lang = 'en' }) {
  const [types, setTypes] = useState([])
  const [connectors, setConnectors] = useState([])
  const [loading, setLoading] = useState(true)
  const [configuring, setConfiguring] = useState(null)
  const [configValues, setConfigValues] = useState({})
  const [saving, setSaving] = useState(false)
  const [testing, setTesting] = useState(null)
  const [testResult, setTestResult] = useState(null)
  const [isMobile, setIsMobile] = useState(false)
  const [confirmState, showConfirm] = useConfirm()

  useEffect(() => {
    const check = () => setIsMobile(window.innerWidth <= 768)
    check()
    window.addEventListener('resize', check)
    return () => window.removeEventListener('resize', check)
  }, [])

  const load = async () => {
    setLoading(true)
    const [typesRes, connRes] = await Promise.all([
      fetchAPI('/connectors/types'),
      fetchAPI('/connectors/'),
    ])
    if (!typesRes.error && typesRes.data) setTypes(Array.isArray(typesRes.data) ? typesRes.data : typesRes.data.types || [])
    if (!connRes.error && connRes.data) setConnectors(connRes.data?.connectors || (Array.isArray(connRes.data) ? connRes.data : []))
    setLoading(false)
  }

  useEffect(() => { load() }, [])

  const handleConfigure = (type) => {
    setConfiguring(type)
    setConfigValues({})
    setTestResult(null)
  }

  const handleSave = async () => {
    if (!configuring) return
    setSaving(true)
    const res = await fetchAPI('/connectors/', {
      method: 'POST',
      body: JSON.stringify({
        connector_type: configuring.connector_type || configuring.id,
        name: configValues._name || `${configuring.name} connector`,
        config: Object.fromEntries(Object.entries(configValues).filter(([k]) => !k.startsWith('_'))),
      }),
    })
    setSaving(false)
    if (!res.error) {
      setConfiguring(null)
      load()
    }
  }

  const handleTest = async (connectorId) => {
    setTesting(connectorId)
    setTestResult(null)
    const res = await fetchAPI(`/connectors/${connectorId}/test`, { method: 'POST' })
    setTestResult({ id: connectorId, ...(res.data || { status: 'failed', error: res.error }) })
    setTesting(null)
  }

  const handleDelete = async (connectorId) => {
    const ok = await showConfirm(lang === 'es' ? '¿Eliminar este conector?' : 'Delete this connector?')
    if (!ok) return
    await fetchAPI(`/connectors/${connectorId}`, { method: 'DELETE' })
    load()
  }

  return (
    <div style={{ animation: 'fadeIn 0.3s ease-out' }}>
      <div style={{ marginBottom: 24 }}>
        <h1 style={{ fontSize: isMobile ? 20 : 24, fontWeight: 700, color: '#111827', marginBottom: 4 }}>
          {lang === 'es' ? 'Conectores' : 'Connectors'}
        </h1>
        <p style={{ fontSize: 14, color: '#9CA3AF' }}>
          {lang === 'es'
            ? 'Conecta servicios externos para usar en tus automatizaciones.'
            : 'Connect external services to use in your automations.'}
        </p>
      </div>

      {loading && <p style={{ color: '#9CA3AF', textAlign: 'center', padding: 40 }}>{lang === 'es' ? 'Cargando...' : 'Loading...'}</p>}

      {/* Available connector types */}
      {!loading && (
        <>
          <h3 style={{ fontSize: 14, fontWeight: 600, color: '#6B7280', marginBottom: 12, textTransform: 'uppercase' }}>
            {lang === 'es' ? 'Tipos disponibles' : 'Available types'}
          </h3>
          <div style={{
            display: 'grid',
            gridTemplateColumns: isMobile ? '1fr' : 'repeat(auto-fill, minmax(280px, 1fr))',
            gap: 12, marginBottom: 32,
          }}>
            {types.map(type => (
              <div key={type.connector_type || type.type || type.id} style={{
                padding: 16, borderRadius: 12, border: '1px solid #E5E7EB',
                background: '#fff', cursor: 'pointer', transition: 'all 0.15s',
              }}
                onMouseEnter={e => e.currentTarget.style.borderColor = '#6366F1'}
                onMouseLeave={e => e.currentTarget.style.borderColor = '#E5E7EB'}
              >
                <div style={{ display: 'flex', alignItems: 'center', gap: 10, marginBottom: 8 }}>
                  <span style={{ fontSize: 24 }}>{type.icon || CONNECTOR_ICONS[type.connector_type || type.type || type.id] || '🔌'}</span>
                  <div>
                    <div style={{ fontSize: 15, fontWeight: 600, color: '#111827' }}>{type.name}</div>
                    <div style={{ fontSize: 11, color: '#9CA3AF' }}>{type.connector_type || type.type || type.id}</div>
                  </div>
                </div>
                <p style={{ fontSize: 12, color: '#6B7280', marginBottom: 12, minHeight: 32 }}>
                  {type.description || ''}
                </p>
                <button
                  onClick={() => handleConfigure(type)}
                  style={{
                    width: '100%', padding: '8px 0', borderRadius: 8, border: '1px solid #6366F1',
                    background: 'transparent', color: '#6366F1', fontSize: 13, fontWeight: 600,
                    cursor: 'pointer', transition: 'all 0.15s',
                  }}
                >
                  {lang === 'es' ? 'Configurar' : 'Configure'}
                </button>
              </div>
            ))}
          </div>

          {/* User's configured connectors */}
          {connectors.length > 0 && (
            <>
              <h3 style={{ fontSize: 14, fontWeight: 600, color: '#6B7280', marginBottom: 12, textTransform: 'uppercase' }}>
                {lang === 'es' ? 'Mis conectores' : 'My connectors'} ({connectors.length})
              </h3>
              <div style={{ display: 'flex', flexDirection: 'column', gap: 8, marginBottom: 32 }}>
                {connectors.map(conn => (
                  <div key={conn.id} style={{
                    display: 'flex', alignItems: 'center', justifyContent: 'space-between',
                    padding: '12px 16px', borderRadius: 10, border: '1px solid #E5E7EB', background: '#fff',
                    position: 'relative',
                  }}>
                    <div style={{ display: 'flex', alignItems: 'center', gap: 10 }}>
                      <span style={{ fontSize: 20 }}>{CONNECTOR_ICONS[conn.connector_type] || '🔌'}</span>
                      <div>
                        <div style={{ fontSize: 14, fontWeight: 600, color: '#111827' }}>{conn.name}</div>
                        <div style={{ fontSize: 11, color: '#9CA3AF' }}>{conn.connector_type}</div>
                      </div>
                    </div>
                    <div style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
                      {/* Status badge */}
                      <span style={{
                        padding: '3px 8px', borderRadius: 6, fontSize: 11, fontWeight: 600,
                        background: conn.last_test_status === 'success' ? 'rgba(16,185,129,0.1)' : conn.last_test_status === 'failed' ? 'rgba(239,68,68,0.1)' : '#F3F4F6',
                        color: conn.last_test_status === 'success' ? '#059669' : conn.last_test_status === 'failed' ? '#DC2626' : '#9CA3AF',
                      }}>
                        {conn.last_test_status === 'success' ? '✓ OK' : conn.last_test_status === 'failed' ? '✕ Failed' : 'Not tested'}
                      </span>
                      {/* Test button */}
                      <button
                        onClick={() => handleTest(conn.id)}
                        disabled={testing === conn.id}
                        style={{
                          padding: '6px 12px', borderRadius: 6, border: '1px solid #E5E7EB',
                          background: '#fff', color: '#6B7280', fontSize: 12, cursor: 'pointer',
                        }}
                      >
                        {testing === conn.id ? '...' : (lang === 'es' ? 'Probar' : 'Test')}
                      </button>
                      {/* Delete button */}
                      <button
                        onClick={() => handleDelete(conn.id)}
                        style={{
                          padding: '6px 12px', borderRadius: 6, border: '1px solid rgba(239,68,68,0.3)',
                          background: 'transparent', color: '#EF4444', fontSize: 12, cursor: 'pointer',
                        }}
                      >
                        {lang === 'es' ? 'Eliminar' : 'Delete'}
                      </button>
                    </div>
                    {/* Test result */}
                    {testResult?.id === conn.id && (
                      <div style={{
                        position: 'absolute', right: 16, top: '100%', zIndex: 10,
                        padding: '8px 12px', borderRadius: 8, fontSize: 12, marginTop: 4,
                        background: testResult.status === 'success' ? '#D1FAE5' : '#FEE2E2',
                        color: testResult.status === 'success' ? '#065F46' : '#991B1B',
                      }}>
                        {testResult.status === 'success' ? '✓ Connection OK' : `✕ ${testResult.error || 'Failed'}`}
                      </div>
                    )}
                  </div>
                ))}
              </div>
            </>
          )}
        </>
      )}

      {/* Configuration modal */}
      {configuring && (
        <div style={{
          position: 'fixed', inset: 0, background: 'rgba(0,0,0,0.4)', zIndex: 100,
          display: 'flex', alignItems: 'center', justifyContent: 'center',
        }} onClick={() => setConfiguring(null)}>
          <div style={{
            background: '#fff', borderRadius: 16, padding: 24, width: 480, maxHeight: '80vh',
            overflowY: 'auto', boxShadow: '0 20px 60px rgba(0,0,0,0.2)',
          }} onClick={e => e.stopPropagation()}>
            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 20 }}>
              <h2 style={{ fontSize: 18, fontWeight: 700, color: '#111827' }}>
                {CONNECTOR_ICONS[configuring.connector_type || configuring.id] || '🔌'} {configuring.name}
              </h2>
              <button onClick={() => setConfiguring(null)} style={{ background: 'none', border: 'none', fontSize: 20, cursor: 'pointer', color: '#9CA3AF' }}>✕</button>
            </div>

            {/* Name field */}
            <div style={{ marginBottom: 16 }}>
              <label style={{ fontSize: 13, fontWeight: 600, color: '#374151', display: 'block', marginBottom: 4 }}>
                {lang === 'es' ? 'Nombre' : 'Name'}
              </label>
              <input
                value={configValues._name || ''}
                onChange={e => setConfigValues(prev => ({ ...prev, _name: e.target.value }))}
                placeholder={`My ${configuring.name}`}
                style={{
                  width: '100%', padding: '8px 12px', borderRadius: 8, border: '1px solid #E5E7EB',
                  fontSize: 13, outline: 'none', boxSizing: 'border-box',
                }}
              />
            </div>

            {/* Dynamic config fields from schema */}
            {(configuring.config_schema?.fields || []).map(field => (
              <div key={field.key} style={{ marginBottom: 14 }}>
                <label style={{ fontSize: 13, fontWeight: 600, color: '#374151', display: 'block', marginBottom: 4 }}>
                  {field.label}
                </label>
                {field.type === 'textarea' ? (
                  <textarea
                    value={configValues[field.key] || ''}
                    onChange={e => setConfigValues(prev => ({ ...prev, [field.key]: e.target.value }))}
                    placeholder={field.placeholder || ''}
                    rows={4}
                    style={{
                      width: '100%', padding: '8px 12px', borderRadius: 8, border: '1px solid #E5E7EB',
                      fontSize: 13, outline: 'none', resize: 'vertical', boxSizing: 'border-box',
                    }}
                  />
                ) : field.type === 'select' ? (
                  <select
                    value={configValues[field.key] || ''}
                    onChange={e => setConfigValues(prev => ({ ...prev, [field.key]: e.target.value }))}
                    style={{
                      width: '100%', padding: '8px 12px', borderRadius: 8, border: '1px solid #E5E7EB',
                      fontSize: 13, outline: 'none', boxSizing: 'border-box', background: '#fff',
                    }}
                  >
                    <option value="">{lang === 'es' ? 'Seleccionar...' : 'Select...'}</option>
                    {(field.options || []).map(opt => <option key={opt} value={opt}>{opt}</option>)}
                  </select>
                ) : field.type === 'boolean' ? (
                  <label style={{ display: 'flex', alignItems: 'center', gap: 8, cursor: 'pointer' }}>
                    <input
                      type="checkbox"
                      checked={configValues[field.key] === true || configValues[field.key] === 'true'}
                      onChange={e => setConfigValues(prev => ({ ...prev, [field.key]: e.target.checked }))}
                      style={{ accentColor: '#6366F1' }}
                    />
                    <span style={{ fontSize: 13, color: '#374151' }}>{field.placeholder || 'Enable'}</span>
                  </label>
                ) : (
                  <input
                    type={field.type === 'password' ? 'password' : field.type === 'number' ? 'number' : 'text'}
                    value={configValues[field.key] || ''}
                    onChange={e => setConfigValues(prev => ({ ...prev, [field.key]: e.target.value }))}
                    placeholder={field.placeholder || ''}
                    style={{
                      width: '100%', padding: '8px 12px', borderRadius: 8, border: '1px solid #E5E7EB',
                      fontSize: 13, outline: 'none', boxSizing: 'border-box',
                    }}
                  />
                )}
                {field.help && <p style={{ fontSize: 11, color: '#9CA3AF', marginTop: 4 }}>{field.help}</p>}
              </div>
            ))}

            <div style={{ display: 'flex', gap: 8, marginTop: 20 }}>
              <button
                onClick={handleSave}
                disabled={saving}
                style={{
                  flex: 1, padding: '10px 0', borderRadius: 8, border: 'none',
                  background: '#6366F1', color: '#fff', fontSize: 14, fontWeight: 600,
                  cursor: saving ? 'default' : 'pointer', opacity: saving ? 0.6 : 1,
                }}
              >
                {saving ? '...' : (lang === 'es' ? 'Guardar Conector' : 'Save Connector')}
              </button>
              <button
                onClick={() => setConfiguring(null)}
                style={{
                  padding: '10px 20px', borderRadius: 8, border: '1px solid #E5E7EB',
                  background: '#fff', color: '#6B7280', fontSize: 14, cursor: 'pointer',
                }}
              >
                {lang === 'es' ? 'Cancelar' : 'Cancel'}
              </button>
            </div>
          </div>
        </div>
      )}
      {confirmState && <ConfirmModal {...confirmState} />}
    </div>
  )
}
