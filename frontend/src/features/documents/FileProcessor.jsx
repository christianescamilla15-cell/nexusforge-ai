import { useState, useRef, useCallback } from 'react'
import { searchEngine } from './LocalSearchEngine'
import { t } from '../../shared/i18n/translations'

const TEXT_EXTENSIONS = ['txt', 'csv', 'json', 'md', 'html', 'xml', 'log', 'js', 'jsx', 'ts', 'tsx', 'py', 'css', 'yml', 'yaml', 'toml', 'ini', 'cfg', 'env', 'sh', 'bat', 'sql']

function getFileExtension(name) {
  return (name || '').split('.').pop().toLowerCase()
}

function isTextFile(name) {
  return TEXT_EXTENSIONS.includes(getFileExtension(name))
}

function formatBytes(bytes) {
  if (bytes < 1024) return `${bytes} B`
  if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(1)} KB`
  return `${(bytes / (1024 * 1024)).toFixed(1)} MB`
}

const STAGES = [
  { key: 'upload', icon: '\u2B06', duration: 500 },
  { key: 'extract', icon: '\uD83D\uDCC4', duration: 500 },
  { key: 'chunk', icon: '\u2702', duration: 1000 },
  { key: 'embed', icon: '\uD83E\uDDE0', duration: 1500 },
  { key: 'index', icon: '\uD83D\uDDC3', duration: 500 },
]

const stageLabels = {
  en: {
    upload: { active: 'Uploading...', done: 'Uploaded' },
    extract: { active: 'Extracting text...', done: 'Extracted' },
    chunk: { active: 'Chunking...', done: 'Chunked' },
    embed: { active: 'Generating embeddings...', done: 'Embedded' },
    index: { active: 'Indexing...', done: 'Indexed' },
  },
  es: {
    upload: { active: 'Subiendo...', done: 'Subido' },
    extract: { active: 'Extrayendo texto...', done: 'Extraido' },
    chunk: { active: 'Fragmentando...', done: 'Fragmentado' },
    embed: { active: 'Generando embeddings...', done: 'Vectorizado' },
    index: { active: 'Indexando...', done: 'Indexado' },
  },
}

function MiniHeatmap() {
  const bars = Array.from({ length: 16 }, () => {
    const hue = Math.floor(Math.random() * 260 + 200) % 360
    return `hsl(${hue}, 70%, ${Math.floor(Math.random() * 30 + 40)}%)`
  })
  return (
    <div style={{ display: 'flex', gap: 1, height: 8, borderRadius: 2, overflow: 'hidden' }}>
      {bars.map((color, i) => (
        <div key={i} style={{ flex: 1, background: color }} />
      ))}
    </div>
  )
}

export default function FileProcessor({ lang = 'en', onDocumentAdded }) {
  const [dragOver, setDragOver] = useState(false)
  const [processing, setProcessing] = useState(false)
  const [currentStage, setCurrentStage] = useState(-1)
  const [completedStages, setCompletedStages] = useState([])
  const [fileInfo, setFileInfo] = useState(null)
  const [extractedText, setExtractedText] = useState('')
  const [chunks, setChunks] = useState([])
  const [visibleChunks, setVisibleChunks] = useState(0)
  const [embeddedChunks, setEmbeddedChunks] = useState(0)
  const [pipelineComplete, setPipelineComplete] = useState(false)
  const fileInputRef = useRef(null)
  const labels = stageLabels[lang] || stageLabels.en

  const resetState = () => {
    setProcessing(false)
    setCurrentStage(-1)
    setCompletedStages([])
    setFileInfo(null)
    setExtractedText('')
    setChunks([])
    setVisibleChunks(0)
    setEmbeddedChunks(0)
    setPipelineComplete(false)
  }

  const processFile = useCallback(async (file) => {
    resetState()
    setProcessing(true)
    const info = { name: file.name, size: file.size, type: file.type || getFileExtension(file.name) }
    setFileInfo(info)

    // Stage 0: Upload
    setCurrentStage(0)
    await wait(500)
    setCompletedStages(prev => [...prev, 'upload'])

    // Stage 1: Extract
    setCurrentStage(1)
    let text = ''
    if (isTextFile(file.name)) {
      text = await readFileAsText(file)
    } else {
      text = `[Text extraction simulated for ${file.name}]\n\nFile: ${file.name}\nSize: ${formatBytes(file.size)}\nType: ${file.type || getFileExtension(file.name)}\n\nThis file format does not support direct text extraction in the browser. In production, this would be processed by the backend extraction pipeline using Apache Tika or similar tools.`
    }
    setExtractedText(text)
    await wait(500)
    setCompletedStages(prev => [...prev, 'extract'])

    // Stage 2: Chunk
    setCurrentStage(2)
    const chunkList = searchEngine.chunkText(text, 500, 50)
    setChunks(chunkList)
    for (let i = 0; i <= chunkList.length; i++) {
      setVisibleChunks(i)
      await wait(Math.min(800 / Math.max(chunkList.length, 1), 200))
    }
    await wait(200)
    setCompletedStages(prev => [...prev, 'chunk'])

    // Stage 3: Embed
    setCurrentStage(3)
    for (let i = 0; i <= chunkList.length; i++) {
      setEmbeddedChunks(i)
      await wait(Math.min(1200 / Math.max(chunkList.length, 1), 300))
    }
    await wait(200)
    setCompletedStages(prev => [...prev, 'embed'])

    // Stage 4: Index
    setCurrentStage(4)
    const doc = searchEngine.addDocument(file.name, text, getFileExtension(file.name), file.size)
    await wait(500)
    setCompletedStages(prev => [...prev, 'index'])

    setPipelineComplete(true)
    setCurrentStage(5)
    onDocumentAdded?.(doc)
  }, [lang, onDocumentAdded])

  const handleDrop = useCallback((e) => {
    e.preventDefault()
    setDragOver(false)
    const file = e.dataTransfer?.files?.[0]
    if (file && !processing) processFile(file)
  }, [processing, processFile])

  const handleFileSelect = useCallback((e) => {
    const file = e.target.files?.[0]
    if (file && !processing) processFile(file)
    if (fileInputRef.current) fileInputRef.current.value = ''
  }, [processing, processFile])

  return (
    <div style={{
      background: '#161E2E', borderRadius: 12,
      border: '1px solid rgba(255,255,255,0.06)',
      padding: 24, marginBottom: 24,
    }}>
      {/* Drag & Drop Zone */}
      {!processing && !pipelineComplete && (
        <div
          role="button"
          tabIndex={0}
          aria-label={t('dragDropHere', lang)}
          onDragOver={(e) => { e.preventDefault(); setDragOver(true) }}
          onDragLeave={() => setDragOver(false)}
          onDrop={handleDrop}
          onClick={() => fileInputRef.current?.click()}
          onKeyDown={(e) => { if (e.key === 'Enter') fileInputRef.current?.click() }}
          style={{
            border: `2px dashed ${dragOver ? '#6366F1' : 'rgba(255,255,255,0.12)'}`,
            borderRadius: 12,
            padding: '40px 24px',
            textAlign: 'center',
            cursor: 'pointer',
            background: dragOver ? 'rgba(99,102,241,0.06)' : 'rgba(255,255,255,0.02)',
            transition: 'all 0.2s',
          }}
        >
          <svg width="48" height="48" viewBox="0 0 24 24" fill="none" stroke={dragOver ? '#6366F1' : '#6B7280'} strokeWidth="1.5" strokeLinecap="round" style={{ display: 'block', margin: '0 auto 16px' }}>
            <path d="M21 15v4a2 2 0 01-2 2H5a2 2 0 01-2-2v-4" />
            <polyline points="17 8 12 3 7 8" />
            <line x1="12" y1="3" x2="12" y2="15" />
          </svg>
          <p style={{ fontSize: 15, color: dragOver ? '#A5B4FC' : '#9CA3AF', marginBottom: 6 }}>
            {t('dragDropHere', lang)}
          </p>
          <p style={{ fontSize: 12, color: '#6B7280' }}>
            .txt, .csv, .json, .md, .pdf, .html, .xml, .log, .py, .js
          </p>
          <input
            ref={fileInputRef}
            type="file"
            onChange={handleFileSelect}
            aria-label="File input"
            style={{ display: 'none' }}
          />
        </div>
      )}

      {/* Processing Pipeline */}
      {(processing || pipelineComplete) && fileInfo && (
        <div>
          <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 20 }}>
            <h3 style={{ fontSize: 16, fontWeight: 600, color: '#E5E7EB', margin: 0 }}>
              {pipelineComplete ? (t('processingComplete', lang)) : (lang === 'es' ? 'Procesando...' : 'Processing...')}
            </h3>
            {pipelineComplete && (
              <button
                onClick={resetState}
                aria-label={lang === 'es' ? 'Subir otro archivo' : 'Upload another file'}
                style={{
                  padding: '6px 14px', borderRadius: 6, border: '1px solid rgba(99,102,241,0.3)',
                  background: 'transparent', color: '#A5B4FC', fontSize: 13, cursor: 'pointer',
                }}
              >
                {lang === 'es' ? '+ Subir otro' : '+ Upload another'}
              </button>
            )}
          </div>

          {/* Pipeline Steps */}
          <div style={{ position: 'relative', paddingLeft: 32 }}>
            {/* Connecting line */}
            <div style={{
              position: 'absolute', left: 11, top: 12, bottom: 12, width: 2,
              background: 'rgba(255,255,255,0.06)',
            }} />

            {STAGES.map((stage, idx) => {
              const isCompleted = completedStages.includes(stage.key)
              const isActive = currentStage === idx
              return (
                <div key={stage.key} style={{ position: 'relative', marginBottom: idx < STAGES.length - 1 ? 16 : 0 }}>
                  {/* Node dot */}
                  <div style={{
                    position: 'absolute', left: -32, top: 2,
                    width: 22, height: 22, borderRadius: '50%',
                    display: 'flex', alignItems: 'center', justifyContent: 'center',
                    fontSize: 11,
                    background: isCompleted ? '#10B981' : isActive ? '#6366F1' : 'rgba(255,255,255,0.08)',
                    boxShadow: isActive ? '0 0 12px rgba(99,102,241,0.5)' : 'none',
                    animation: isActive ? 'pulse 1.5s infinite' : 'none',
                    transition: 'all 0.3s',
                    zIndex: 1,
                  }}>
                    {isCompleted ? '\u2713' : stage.icon}
                  </div>

                  {/* Stage content */}
                  <div style={{
                    padding: '8px 14px', borderRadius: 8,
                    background: isActive ? 'rgba(99,102,241,0.08)' : isCompleted ? 'rgba(16,185,129,0.05)' : 'transparent',
                    border: isActive ? '1px solid rgba(99,102,241,0.2)' : '1px solid transparent',
                    transition: 'all 0.3s',
                  }}>
                    <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                      <span style={{
                        fontSize: 13, fontWeight: 600,
                        color: isCompleted ? '#10B981' : isActive ? '#A5B4FC' : '#6B7280',
                      }}>
                        {isCompleted ? labels[stage.key].done + ' \u2713' : isActive ? labels[stage.key].active : labels[stage.key].done}
                      </span>
                    </div>

                    {/* Stage-specific details */}
                    {stage.key === 'upload' && (isActive || isCompleted) && (
                      <div style={{ marginTop: 8 }}>
                        <div style={{ display: 'flex', alignItems: 'center', gap: 8, fontSize: 12, color: '#9CA3AF' }}>
                          <span>{fileInfo.name}</span>
                          <span style={{ color: '#6B7280' }}>|</span>
                          <span>{formatBytes(fileInfo.size)}</span>
                        </div>
                        {isActive && (
                          <div style={{ marginTop: 6, height: 4, borderRadius: 2, background: 'rgba(255,255,255,0.06)', overflow: 'hidden' }}>
                            <div style={{
                              height: '100%', borderRadius: 2,
                              background: 'linear-gradient(90deg, #6366F1, #8B5CF6)',
                              animation: 'progressFill 0.5s ease-out forwards',
                            }} />
                          </div>
                        )}
                      </div>
                    )}

                    {stage.key === 'extract' && (isActive || isCompleted) && extractedText && (
                      <div style={{ marginTop: 8 }}>
                        <p style={{
                          fontSize: 11, color: '#9CA3AF', margin: '0 0 4px',
                          fontFamily: 'monospace', lineHeight: 1.5,
                          maxHeight: 60, overflow: 'hidden',
                          background: 'rgba(0,0,0,0.3)', padding: 8, borderRadius: 4,
                        }}>
                          {extractedText.slice(0, 200)}{extractedText.length > 200 ? '...' : ''}
                        </p>
                        <div style={{ display: 'flex', gap: 12, fontSize: 11, color: '#6B7280' }}>
                          <span>{extractedText.length.toLocaleString()} chars</span>
                          <span>{extractedText.split(/\s+/).length.toLocaleString()} words</span>
                        </div>
                      </div>
                    )}

                    {stage.key === 'chunk' && (isActive || isCompleted) && chunks.length > 0 && (
                      <div style={{ marginTop: 8 }}>
                        <div style={{ fontSize: 11, color: '#6B7280', marginBottom: 6 }}>
                          {t('chunkParams', lang)} | {visibleChunks}/{chunks.length} chunks
                        </div>
                        <div style={{ display: 'flex', flexWrap: 'wrap', gap: 6, maxHeight: 120, overflow: 'hidden' }}>
                          {chunks.slice(0, Math.min(visibleChunks, 8)).map((chunk, ci) => (
                            <div key={ci} style={{
                              background: 'rgba(0,0,0,0.4)', borderRadius: 4, padding: '4px 8px',
                              fontSize: 10, fontFamily: 'monospace', color: '#9CA3AF',
                              border: '1px solid rgba(255,255,255,0.06)',
                              maxWidth: 180, overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap',
                              animation: 'fadeIn 0.2s ease-out',
                            }}>
                              <span style={{ color: '#A5B4FC', marginRight: 4 }}>#{ci}</span>
                              {chunk.text.slice(0, 40)}...
                              <span style={{ color: '#6B7280', marginLeft: 4 }}>{chunk.text.length}c</span>
                            </div>
                          ))}
                          {chunks.length > 8 && visibleChunks >= 8 && (
                            <div style={{ fontSize: 10, color: '#6B7280', padding: '4px 8px' }}>
                              +{chunks.length - 8} more
                            </div>
                          )}
                        </div>
                      </div>
                    )}

                    {stage.key === 'embed' && (isActive || isCompleted) && (
                      <div style={{ marginTop: 8 }}>
                        <div style={{ fontSize: 11, color: '#6B7280', marginBottom: 6 }}>
                          Voyage AI voyage-3-lite &bull; 512 dimensions
                        </div>
                        <div style={{ display: 'flex', flexDirection: 'column', gap: 4, maxHeight: 100, overflow: 'hidden' }}>
                          {chunks.slice(0, Math.min(embeddedChunks, 6)).map((_, ci) => (
                            <div key={ci} style={{ display: 'flex', alignItems: 'center', gap: 8, animation: 'fadeIn 0.2s ease-out' }}>
                              <span style={{ fontSize: 10, color: '#A5B4FC', fontFamily: 'monospace', minWidth: 24 }}>#{ci}</span>
                              <div style={{ flex: 1 }}><MiniHeatmap /></div>
                              <span style={{ fontSize: 10, color: '#10B981' }}>{'\u2713'}</span>
                            </div>
                          ))}
                          {isActive && embeddedChunks < chunks.length && (
                            <div style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
                              <span style={{ fontSize: 10, color: '#6B7280', fontFamily: 'monospace', minWidth: 24 }}>#{embeddedChunks}</span>
                              <div style={{
                                flex: 1, height: 8, borderRadius: 2,
                                background: 'linear-gradient(90deg, rgba(99,102,241,0.3), rgba(139,92,246,0.3))',
                                animation: 'shimmer 1s infinite',
                              }} />
                            </div>
                          )}
                        </div>
                        <div style={{ fontSize: 10, color: '#6B7280', marginTop: 4 }}>
                          {embeddedChunks}/{chunks.length} {lang === 'es' ? 'vectorizados' : 'embedded'}
                        </div>
                      </div>
                    )}

                    {stage.key === 'index' && isActive && (
                      <div style={{ marginTop: 8 }}>
                        <div style={{
                          fontSize: 11, color: '#A5B4FC',
                          animation: 'shimmer 1s infinite',
                        }}>
                          {lang === 'es' ? 'Almacenando en pgvector...' : 'Storing in pgvector...'}
                        </div>
                      </div>
                    )}

                    {stage.key === 'index' && isCompleted && (
                      <div style={{ marginTop: 8, fontSize: 11, color: '#10B981' }}>
                        {t('processingComplete', lang)}
                      </div>
                    )}
                  </div>
                </div>
              )
            })}
          </div>
        </div>
      )}

      {/* Animations */}
      <style>{`
        @keyframes pulse {
          0%, 100% { box-shadow: 0 0 8px rgba(99,102,241,0.3); }
          50% { box-shadow: 0 0 16px rgba(99,102,241,0.6); }
        }
        @keyframes progressFill {
          from { width: 0%; }
          to { width: 100%; }
        }
        @keyframes shimmer {
          0% { opacity: 0.5; }
          50% { opacity: 1; }
          100% { opacity: 0.5; }
        }
        @keyframes fadeIn {
          from { opacity: 0; transform: translateY(4px); }
          to { opacity: 1; transform: translateY(0); }
        }
      `}</style>
    </div>
  )
}

function wait(ms) {
  return new Promise(resolve => setTimeout(resolve, ms))
}

function readFileAsText(file) {
  return new Promise((resolve, reject) => {
    const reader = new FileReader()
    reader.onload = () => resolve(reader.result)
    reader.onerror = () => reject(reader.error)
    reader.readAsText(file)
  })
}
