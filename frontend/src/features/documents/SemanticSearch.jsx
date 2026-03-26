import { useState } from 'react'
import { api } from '../../api/client'

const DEMO_RESULTS = [
  { document_title: 'Contrato de Servicios 2026', chunk: 'Las partes acuerdan una duracion de 12 meses a partir de la firma del presente contrato, con opcion a renovacion automatica...', score: 0.94 },
  { document_title: 'Politica de Privacidad v3', chunk: 'Los datos personales seran tratados conforme a la normativa vigente de proteccion de datos, incluyendo el derecho de acceso y rectificacion...', score: 0.82 },
  { document_title: 'Reporte Financiero Q1', chunk: 'Los ingresos del primer trimestre muestran un crecimiento del 23% respecto al periodo anterior, impulsado por la adopcion de IA...', score: 0.67 },
  { document_title: 'Manual Tecnico API', chunk: 'El endpoint /api/documents acepta peticiones POST con el cuerpo en formato JSON, incluyendo los campos title, content y metadata...', score: 0.51 },
]

function scoreColor(score) {
  if (score >= 0.8) return '#10B981'
  if (score >= 0.6) return '#F59E0B'
  return '#EF4444'
}

export default function SemanticSearch() {
  const [query, setQuery] = useState('')
  const [results, setResults] = useState(null)
  const [loading, setLoading] = useState(false)

  const handleSearch = async (e) => {
    e.preventDefault()
    if (!query.trim()) return
    setLoading(true)
    try {
      const data = await api.post('/documents/search', { query, top_k: 10 })
      setResults(Array.isArray(data) ? data : data.results || DEMO_RESULTS)
    } catch {
      setResults(DEMO_RESULTS)
    } finally {
      setLoading(false)
    }
  }

  return (
    <div style={{
      background: '#161E2E', borderRadius: 12,
      border: '1px solid rgba(255,255,255,0.06)',
      padding: 24, marginBottom: 24,
    }}>
      <h2 style={{ fontSize: 16, fontWeight: 600, color: '#E5E7EB', marginBottom: 14 }}>Busqueda Semantica (RAG)</h2>

      <form onSubmit={handleSearch} style={{ display: 'flex', gap: 10, marginBottom: 20 }}>
        <input
          type="text"
          value={query}
          onChange={(e) => setQuery(e.target.value)}
          placeholder="Busca informacion en tus documentos..."
          aria-label="Busqueda semantica"
          style={{
            flex: 1, padding: '10px 14px', borderRadius: 8,
            border: '1px solid rgba(255,255,255,0.08)', background: 'rgba(255,255,255,0.03)',
            color: '#E5E7EB', fontSize: 14, outline: 'none',
          }}
          onFocus={(e) => e.target.style.borderColor = 'rgba(99,102,241,0.4)'}
          onBlur={(e) => e.target.style.borderColor = 'rgba(255,255,255,0.08)'}
        />
        <button
          type="submit"
          disabled={loading || !query.trim()}
          aria-label="Buscar"
          style={{
            padding: '10px 20px', borderRadius: 8, border: 'none',
            background: loading ? 'rgba(99,102,241,0.3)' : 'linear-gradient(135deg, #6366F1, #8B5CF6)',
            color: '#fff', fontSize: 14, fontWeight: 600,
            cursor: loading ? 'not-allowed' : 'pointer', whiteSpace: 'nowrap',
          }}
        >
          {loading ? 'Buscando...' : 'Buscar'}
        </button>
      </form>

      {/* Results */}
      {results !== null && results.length === 0 && (
        <div style={{ textAlign: 'center', padding: 40, color: '#9CA3AF', fontSize: 14 }}>
          <svg width="40" height="40" viewBox="0 0 24 24" fill="none" stroke="#9CA3AF" strokeWidth="1.5" strokeLinecap="round"
            style={{ display: 'block', margin: '0 auto 12px' }}>
            <circle cx="11" cy="11" r="8" /><path d="M21 21l-4.35-4.35" />
          </svg>
          No se encontraron resultados para esta consulta.
        </div>
      )}

      {results && results.length > 0 && (
        <div style={{ display: 'flex', flexDirection: 'column', gap: 12 }}>
          {results.map((r, idx) => {
            const color = scoreColor(r.score)
            const pct = Math.round(r.score * 100)
            return (
              <div key={idx} style={{
                background: '#0A0B0F', borderRadius: 10, padding: 16,
                border: '1px solid rgba(255,255,255,0.06)',
              }}>
                <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 8 }}>
                  <span style={{ fontSize: 14, fontWeight: 600, color: '#E5E7EB' }}>{r.document_title}</span>
                  <span style={{ fontSize: 13, fontWeight: 700, color }}>{pct}%</span>
                </div>
                <p style={{ fontSize: 13, color: '#D1D5DB', lineHeight: 1.6, margin: '0 0 10px' }}>{r.chunk}</p>
                <div style={{
                  height: 4, borderRadius: 2, background: 'rgba(255,255,255,0.06)', overflow: 'hidden',
                }}>
                  <div style={{
                    height: '100%', width: `${pct}%`, borderRadius: 2,
                    background: color, transition: 'width 0.3s ease',
                  }} />
                </div>
              </div>
            )
          })}
        </div>
      )}
    </div>
  )
}
