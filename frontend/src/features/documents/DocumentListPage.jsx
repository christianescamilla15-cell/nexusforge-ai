import { useState, useEffect, useRef } from 'react'
import { t } from '../../shared/i18n/translations'
import { searchEngine } from './LocalSearchEngine'
import FileProcessor from './FileProcessor'
import SemanticSearch from './SemanticSearch'

const DEMO_CONTENT_1 = `NexusForge AI Architecture Overview

NexusForge is an enterprise-grade agent orchestration platform designed for production workloads. The platform coordinates 24 specialized AI agents across 6 swarm topologies, enabling complex multi-step reasoning and autonomous task execution.

Core Components:
1. Agent Registry - Manages the lifecycle of all AI agents including provisioning, health checks, and decommissioning. Each agent has a 3-tier memory system: working memory for short-term context, episodic memory for past interactions, and semantic memory backed by pgvector for knowledge retrieval.

2. Workflow Engine - Executes DAG-based pipelines where each node represents an agent action. Supports branching, parallel execution, and conditional logic. The engine tracks costs, tokens, and latency for every step.

3. Swarm Orchestrator - Coordinates multiple agents using topologies like Sequential, Parallel, Hierarchical, Debate, Consensus, and Adaptive. The Debate topology enables agents to argue different perspectives before reaching consensus.

4. Document Pipeline - Handles document ingestion through chunking, embedding with Voyage AI, and indexing into pgvector. Supports semantic search with RAG (Retrieval Augmented Generation) for grounding agent responses in organizational knowledge.

5. LLM Router - Dynamically selects the optimal language model (Claude, GPT-4, Gemini) based on task complexity, cost constraints, and latency requirements. Implements fallback chains and rate limiting.

6. Self-Healing System - Monitors agent health and automatically restarts failed agents, retries failed workflow steps, and scales resources based on demand. Uses circuit breaker patterns to prevent cascade failures.

The platform exposes a RESTful API and WebSocket connections for real-time monitoring. The frontend is built with React and provides dashboards for workflows, executions, agents, swarms, and document management.

Technology Stack: Python FastAPI backend, React frontend, PostgreSQL with pgvector, Redis for caching, Docker and Kubernetes for deployment, Terraform for infrastructure as code.`

const DEMO_CONTENT_2 = `AI Agent Framework - How Agents Work in NexusForge

An AI Agent in NexusForge is an autonomous unit that combines a large language model with tools, memory, and goals. Each agent specializes in a domain such as code generation, data analysis, content writing, or research.

Agent Lifecycle:
- Initialization: Agent loads its configuration, connects to its assigned LLM, and initializes its 3-tier memory system.
- Task Reception: The workflow engine or swarm orchestrator assigns a task with context and constraints.
- Planning: The agent breaks down the task into subtasks using chain-of-thought reasoning.
- Execution: For each subtask, the agent selects tools, queries its memory, and generates outputs.
- Reflection: After execution, the agent evaluates its output quality and stores learnings in episodic memory.

Memory Architecture:
Working Memory stores the current conversation and task context with a sliding window. Episodic Memory records past task executions and their outcomes for learning. Semantic Memory uses vector embeddings to store and retrieve domain knowledge from documents.

Tool Integration:
Agents can use tools like web search, code execution, database queries, API calls, and file operations. The tool registry manages available tools and their permissions per agent type.

Agent Types in NexusForge include: CodeGenerator, DataAnalyst, ContentWriter, Researcher, Planner, Reviewer, Debugger, Summarizer, Translator, and more. Each type has a specialized system prompt and curated tool set.

Communication between agents happens through structured message passing with typed payloads. Agents can request help from other agents, delegate subtasks, and aggregate results.`

function formatBytes(bytes) {
  if (!bytes) return '--'
  if (bytes < 1024) return `${bytes} B`
  if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(1)} KB`
  return `${(bytes / (1024 * 1024)).toFixed(1)} MB`
}

function formatDate(iso, lang) {
  if (!iso) return '--'
  const locale = lang === 'es' ? 'es-ES' : 'en-US'
  return new Date(iso).toLocaleDateString(locale, { month: 'short', day: 'numeric', year: 'numeric' })
}

export default function DocumentListPage({ lang = 'en' }) {
  const [docs, setDocs] = useState([])
  const [isMobile, setIsMobile] = useState(false)
  const [searchRefreshKey, setSearchRefreshKey] = useState(0)
  const initialized = useRef(false)

  useEffect(() => {
    const check = () => setIsMobile(window.innerWidth <= 768)
    check()
    window.addEventListener('resize', check)
    return () => window.removeEventListener('resize', check)
  }, [])

  // Load demo documents once
  useEffect(() => {
    if (initialized.current) return
    initialized.current = true

    // Only add if no documents exist yet
    if (searchEngine.getStats().totalDocs === 0) {
      searchEngine.addDocument('NexusForge Architecture', DEMO_CONTENT_1, 'md', DEMO_CONTENT_1.length)
      searchEngine.addDocument('AI Agent Framework', DEMO_CONTENT_2, 'md', DEMO_CONTENT_2.length)
    }
    setDocs(searchEngine.getDocuments())
  }, [])

  const handleDocumentAdded = () => {
    setDocs(searchEngine.getDocuments())
    setSearchRefreshKey(k => k + 1)
  }

  const tableHeaders = [
    t('title', lang),
    t('type', lang),
    t('size', lang),
    lang === 'es' ? 'Fragmentos' : 'Chunks',
    t('status', lang),
    t('created', lang),
  ]

  return (
    <div style={{ animation: 'fadeIn 0.3s ease-out' }}>
      {/* Header */}
      <div style={{
        display: 'flex', justifyContent: 'space-between', alignItems: 'center',
        marginBottom: 24, flexWrap: 'wrap', gap: 12,
      }}>
        <div>
          <h1 style={{ fontSize: isMobile ? 20 : 24, fontWeight: 700, color: '#111827', marginBottom: 4 }}>
            {t('documents', lang)}
          </h1>
          <p style={{ fontSize: isMobile ? 13 : 14, color: '#9CA3AF' }}>
            {t('manageDocuments', lang)}
            <span style={{ marginLeft: 8, color: '#6366F1' }}>
              {docs.length} {t('documentsCount', lang)}
            </span>
          </p>
        </div>
        {/* Stats badges */}
        {docs.length > 0 && (
          <div style={{ display: 'flex', gap: 8, flexWrap: 'wrap' }}>
            <span style={{
              padding: '4px 10px', borderRadius: 6, fontSize: 12, fontWeight: 500,
              background: 'rgba(99,102,241,0.1)', color: '#6366F1',
            }}>
              {searchEngine.getStats().totalChunks} chunks
            </span>
            <span style={{
              padding: '4px 10px', borderRadius: 6, fontSize: 12, fontWeight: 500,
              background: 'rgba(16,185,129,0.1)', color: '#10B981',
            }}>
              {searchEngine.getStats().totalChars.toLocaleString()} chars
            </span>
          </div>
        )}
      </div>

      {/* Upload Section */}
      <FileProcessor lang={lang} onDocumentAdded={handleDocumentAdded} />

      {/* Document Table */}
      <div style={{
        background: '#FFFFFF', borderRadius: 12,
        border: '1px solid #E5E7EB', overflow: 'hidden',
        overflowX: 'auto', marginBottom: 24,
      }}>
        <table style={{ width: '100%', borderCollapse: 'collapse', minWidth: isMobile ? 600 : undefined }}>
          <thead>
            <tr style={{ borderBottom: '1px solid #E5E7EB' }}>
              {tableHeaders.map((h) => (
                <th key={h} style={{
                  padding: '12px 16px', fontSize: 12, fontWeight: 600, color: '#9CA3AF',
                  textAlign: 'left', textTransform: 'uppercase', letterSpacing: '0.05em',
                  whiteSpace: 'nowrap',
                }}>{h}</th>
              ))}
            </tr>
          </thead>
          <tbody>
            {docs.length === 0 && (
              <tr>
                <td colSpan={6} style={{ padding: 40, textAlign: 'center', color: '#9CA3AF', fontSize: 14 }}>
                  {t('noDocuments', lang)}
                </td>
              </tr>
            )}
            {docs.map((doc) => (
              <tr key={doc.id} style={{ borderBottom: '1px solid #F3F4F6' }}>
                <td style={{ padding: '12px 16px', color: '#111827', fontSize: 14, fontWeight: 500 }}>
                  {doc.title}
                </td>
                <td style={{ padding: '12px 16px' }}>
                  <span style={{
                    fontSize: 11, padding: '2px 8px', borderRadius: 4,
                    background: 'rgba(99,102,241,0.1)', color: '#6366F1', fontWeight: 500,
                    textTransform: 'uppercase',
                  }}>{doc.fileType}</span>
                </td>
                <td style={{ padding: '12px 16px', color: '#9CA3AF', fontSize: 13 }}>
                  {formatBytes(doc.sizeBytes)}
                </td>
                <td style={{ padding: '12px 16px', color: '#9CA3AF', fontSize: 13 }}>
                  {doc.chunksCount}
                </td>
                <td style={{ padding: '12px 16px' }}>
                  <span style={{
                    display: 'inline-flex', alignItems: 'center', gap: 6,
                    padding: '3px 10px', borderRadius: 9999, fontSize: 12, fontWeight: 500,
                    background: 'rgba(16,185,129,0.15)', color: '#10B981', whiteSpace: 'nowrap',
                  }}>
                    <span style={{ width: 6, height: 6, borderRadius: '50%', background: '#10B981', flexShrink: 0 }} />
                    {lang === 'es' ? 'Indexado' : 'Indexed'}
                  </span>
                </td>
                <td style={{ padding: '12px 16px', color: '#9CA3AF', fontSize: 13, whiteSpace: 'nowrap' }}>
                  {formatDate(doc.addedAt, lang)}
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>

      {/* Semantic Search */}
      <div data-tour="semantic-search">
        <SemanticSearch lang={lang} refreshKey={searchRefreshKey} />
      </div>

      <style>{`
        @keyframes fadeIn {
          from { opacity: 0; }
          to { opacity: 1; }
        }
      `}</style>
    </div>
  )
}
