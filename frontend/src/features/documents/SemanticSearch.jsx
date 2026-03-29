import { useState, useRef, useCallback, useEffect } from 'react'
import { searchEngine } from './LocalSearchEngine'
import { t } from '../../shared/i18n/translations'

function scoreColor(score) {
  if (score >= 80) return '#10B981'
  if (score >= 60) return '#F59E0B'
  return '#EF4444'
}

function HighlightedText({ text }) {
  // Split on **term** markers and render with highlights
  const parts = text.split(/\*\*(.+?)\*\*/g)
  return (
    <span>
      {parts.map((part, i) =>
        i % 2 === 1 ? (
          <mark key={i} style={{
            background: 'rgba(245,158,11,0.25)', color: '#B45309',
            fontWeight: 700, borderRadius: 2, padding: '0 2px',
          }}>{part}</mark>
        ) : (
          <span key={i}>{part}</span>
        )
      )}
    </span>
  )
}

export default function SemanticSearch({ lang = 'en', refreshKey = 0 }) {
  const [query, setQuery] = useState('')
  const [results, setResults] = useState(null)
  const [stats, setStats] = useState(null)
  const debounceRef = useRef(null)

  const doSearch = useCallback((q) => {
    if (!q || q.trim().length < 3) {
      setResults(null)
      setStats(null)
      return
    }
    const hits = searchEngine.search(q.trim(), 8)
    const engineStats = searchEngine.getStats()
    setResults(hits)
    setStats({
      found: hits.length,
      totalChunks: engineStats.totalChunks,
      totalDocs: engineStats.totalDocs,
    })
  }, [])

  const handleChange = useCallback((e) => {
    const val = e.target.value
    setQuery(val)
    clearTimeout(debounceRef.current)
    debounceRef.current = setTimeout(() => doSearch(val), 300)
  }, [doSearch])

  const handleSubmit = (e) => {
    e.preventDefault()
    clearTimeout(debounceRef.current)
    doSearch(query)
  }

  // Re-search when refreshKey changes (after doc upload)
  useEffect(() => {
    if (query.trim().length >= 3) {
      doSearch(query)
    }
  }, [refreshKey, doSearch, query])

  return (
    <div style={{
      background: '#FFFFFF', borderRadius: 12,
      border: '1px solid #E5E7EB',
      padding: 24, marginBottom: 24,
    }}>
      <h2 style={{ fontSize: 16, fontWeight: 600, color: '#111827', marginBottom: 4 }}>
        {t('semanticSearch', lang)} (RAG)
      </h2>
      <p style={{ fontSize: 12, color: '#6B7280', marginBottom: 14 }}>
        {lang === 'es'
          ? 'Busca en los documentos indexados usando coincidencia de términos'
          : 'Search indexed documents using term matching'}
      </p>

      <form onSubmit={handleSubmit} style={{ display: 'flex', gap: 10, marginBottom: 16 }}>
        <input
          type="text"
          value={query}
          onChange={handleChange}
          placeholder={t('searchPlaceholder', lang)}
          aria-label={t('semanticSearch', lang)}
          style={{
            flex: 1, padding: '10px 14px', borderRadius: 8,
            border: '1px solid #E5E7EB', background: '#F3F4F6',
            color: '#111827', fontSize: 14, outline: 'none',
          }}
          onFocus={(e) => e.target.style.borderColor = 'rgba(99,102,241,0.4)'}
          onBlur={(e) => e.target.style.borderColor = '#E5E7EB'}
        />
        <button
          type="submit"
          disabled={!query.trim()}
          aria-label={t('search', lang)}
          style={{
            padding: '10px 20px', borderRadius: 8, border: 'none',
            background: !query.trim() ? 'rgba(99,102,241,0.3)' : 'linear-gradient(135deg, #2563EB, #3B82F6)',
            color: '#fff', fontSize: 14, fontWeight: 600,
            cursor: !query.trim() ? 'not-allowed' : 'pointer', whiteSpace: 'nowrap',
          }}
        >
          {t('search', lang)}
        </button>
      </form>

      {/* Search stats */}
      {stats && (
        <div style={{ fontSize: 12, color: '#6B7280', marginBottom: 12 }}>
          {lang === 'es'
            ? `${stats.found} resultados en ${stats.totalChunks} fragmentos de ${stats.totalDocs} documentos`
            : `Found ${stats.found} results in ${stats.totalChunks} chunks across ${stats.totalDocs} documents`}
        </div>
      )}

      {/* No results */}
      {results !== null && results.length === 0 && (
        <div style={{ textAlign: 'center', padding: 32, color: '#9CA3AF' }}>
          <svg width="40" height="40" viewBox="0 0 24 24" fill="none" stroke="#6B7280" strokeWidth="1.5" strokeLinecap="round"
            style={{ display: 'block', margin: '0 auto 12px' }}>
            <circle cx="11" cy="11" r="8" /><path d="M21 21l-4.35-4.35" />
          </svg>
          <p style={{ fontSize: 14, marginBottom: 8 }}>
            {t('noSearchResults', lang)}
          </p>
          <p style={{ fontSize: 12, color: '#6B7280' }}>
            {t('searchTip', lang)}
          </p>
        </div>
      )}

      {/* Results */}
      {results && results.length > 0 && (
        <div style={{ display: 'flex', flexDirection: 'column', gap: 12 }}>
          {results.map((r, idx) => {
            const color = scoreColor(r.similarity)
            return (
              <div key={idx} style={{
                background: '#F9FAFB', borderRadius: 10, padding: 16,
                border: '1px solid #E5E7EB',
                animation: 'fadeIn 0.2s ease-out',
              }}>
                <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 8 }}>
                  <div style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
                    <span style={{ fontSize: 14, fontWeight: 600, color: '#111827' }}>{r.docTitle}</span>
                    <span style={{
                      fontSize: 10, padding: '2px 6px', borderRadius: 4,
                      background: 'rgba(99,102,241,0.1)', color: '#6366F1',
                    }}>
                      Fragmento #{r.chunkIndex}
                    </span>
                  </div>
                  <span style={{ fontSize: 13, fontWeight: 700, color }}>{r.similarity}%</span>
                </div>
                <p style={{ fontSize: 13, color: '#374151', lineHeight: 1.6, margin: '0 0 10px' }}>
                  <HighlightedText text={r.highlight} />
                </p>
                <div style={{
                  height: 4, borderRadius: 2, background: '#E5E7EB', overflow: 'hidden',
                }}>
                  <div style={{
                    height: '100%', width: `${r.similarity}%`, borderRadius: 2,
                    background: color, transition: 'width 0.3s ease',
                  }} />
                </div>
                {r.matchedTerms.length > 0 && (
                  <div style={{ display: 'flex', gap: 4, marginTop: 8, flexWrap: 'wrap' }}>
                    {r.matchedTerms.map((term, ti) => (
                      <span key={ti} style={{
                        fontSize: 10, padding: '1px 6px', borderRadius: 4,
                        background: 'rgba(245,158,11,0.1)', color: '#B45309',
                      }}>
                        {term}
                      </span>
                    ))}
                  </div>
                )}
              </div>
            )
          })}
        </div>
      )}

      <style>{`
        @keyframes fadeIn {
          from { opacity: 0; transform: translateY(4px); }
          to { opacity: 1; transform: translateY(0); }
        }
      `}</style>
    </div>
  )
}
