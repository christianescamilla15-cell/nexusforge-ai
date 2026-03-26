/**
 * NexusForgeClient — main SDK client for the NexusForge AI platform.
 *
 * Provides programmatic access to workflows, executions, agents,
 * documents, and swarm orchestration endpoints.
 */
export class NexusForgeClient {
  /**
   * @param {Object} options
   * @param {string} options.apiUrl  - Base URL of the NexusForge API (e.g. http://localhost:8000/api)
   * @param {string} [options.apiKey] - Optional API key for authenticated requests
   */
  constructor({ apiUrl, apiKey } = {}) {
    if (!apiUrl) throw new Error('apiUrl is required')
    this.apiUrl = apiUrl.replace(/\/+$/, '')
    this.apiKey = apiKey || null
  }

  // ── Workflows ──────────────────────────────────────────────────────

  /** List all workflows visible to the current tenant. */
  async listWorkflows() {
    return this._request('GET', '/workflows')
  }

  /** Get a single workflow by ID. */
  async getWorkflow(id) {
    return this._request('GET', `/workflows/${id}`)
  }

  /** Create a new workflow from a definition object. */
  async createWorkflow(data) {
    return this._request('POST', '/workflows', data)
  }

  /** Trigger a workflow execution and return the run object. */
  async runWorkflow(id, input = {}) {
    return this._request('POST', `/workflows/${id}/run`, { input })
  }

  /** Update an existing workflow. */
  async updateWorkflow(id, data) {
    return this._request('PATCH', `/workflows/${id}`, data)
  }

  /** Delete a workflow. */
  async deleteWorkflow(id) {
    return this._request('DELETE', `/workflows/${id}`)
  }

  // ── Executions ─────────────────────────────────────────────────────

  /**
   * List workflow runs with optional filters.
   * @param {Object} [filters] - { status, workflow_id, limit, offset }
   */
  async listRuns(filters = {}) {
    const qs = new URLSearchParams(
      Object.entries(filters).filter(([, v]) => v != null)
    ).toString()
    const path = qs ? `/runs?${qs}` : '/runs'
    return this._request('GET', path)
  }

  /** Get details for a specific run. */
  async getRun(id) {
    return this._request('GET', `/runs/${id}`)
  }

  /** Cancel a running execution. */
  async cancelRun(id) {
    return this._request('POST', `/runs/${id}/cancel`)
  }

  // ── Agents ─────────────────────────────────────────────────────────

  /** List all available agent types. */
  async listAgents() {
    return this._request('GET', '/agents')
  }

  /** Get metadata for a specific agent type. */
  async getAgent(type) {
    return this._request('GET', `/agents/${type}`)
  }

  // ── Documents ──────────────────────────────────────────────────────

  /**
   * Upload a document for RAG indexing.
   * @param {Object} data - { name, content, metadata }
   */
  async uploadDocument(data) {
    return this._request('POST', '/documents', data)
  }

  /**
   * Semantic search across indexed documents.
   * @param {string} query - Natural-language search query
   * @param {Object} [options] - { top_k, threshold }
   */
  async searchDocuments(query, options = {}) {
    return this._request('POST', '/documents/search', { query, ...options })
  }

  // ── Swarms ─────────────────────────────────────────────────────────

  /** List available swarm topologies. */
  async listSwarms() {
    return this._request('GET', '/swarms')
  }

  /**
   * Execute a swarm with the given topology.
   * @param {string} topology   - e.g. "star", "mesh", "hierarchy"
   * @param {string[]} agentTypes - agent types to include
   * @param {Object} inputData  - payload to feed the swarm
   */
  async executeSwarm(topology, agentTypes, inputData) {
    return this._request('POST', '/swarms/execute', {
      topology,
      agent_types: agentTypes,
      input: inputData,
    })
  }

  // ── Health ─────────────────────────────────────────────────────────

  /** Check API health / readiness. */
  async health() {
    return this._request('GET', '/health')
  }

  // ── Private ────────────────────────────────────────────────────────

  async _request(method, path, body) {
    const url = `${this.apiUrl}${path}`
    const headers = { 'Content-Type': 'application/json' }

    if (this.apiKey) {
      headers['Authorization'] = `Bearer ${this.apiKey}`
    }

    const options = { method, headers }
    if (body && method !== 'GET') {
      options.body = JSON.stringify(body)
    }

    const response = await fetch(url, options)

    if (!response.ok) {
      const text = await response.text().catch(() => '')
      const error = new Error(
        `NexusForge API error ${response.status}: ${text || response.statusText}`
      )
      error.status = response.status
      error.body = text
      throw error
    }

    // 204 No Content
    if (response.status === 204) return null

    return response.json()
  }
}
