/**
 * AgentBuilder — fluent builder for constructing agent configuration objects.
 *
 * Usage:
 *   const agent = new AgentBuilder('classifier')
 *     .model('claude-sonnet-4-20250514')
 *     .systemPrompt('You classify documents by topic.')
 *     .temperature(0.2)
 *     .maxTokens(1024)
 *     .addTool('web_search')
 *     .addTool('document_lookup')
 *     .withMemory({ episodic: true, semantic: true })
 *     .build()
 */
export class AgentBuilder {
  /**
   * @param {string} type - Agent type identifier (e.g. "classifier", "summarizer")
   */
  constructor(type) {
    if (!type) throw new Error('Agent type is required')
    this._type = type
    this._model = 'claude-sonnet-4-20250514'
    this._systemPrompt = ''
    this._temperature = 0.7
    this._maxTokens = 2048
    this._tools = []
    this._memory = {}
    this._metadata = {}
  }

  /** Set the LLM model to use. */
  model(modelName) {
    this._model = modelName
    return this
  }

  /** Set the system prompt that defines agent behavior. */
  systemPrompt(prompt) {
    this._systemPrompt = prompt
    return this
  }

  /** Set generation temperature (0.0 - 1.0). */
  temperature(value) {
    if (value < 0 || value > 1) {
      throw new Error('Temperature must be between 0.0 and 1.0')
    }
    this._temperature = value
    return this
  }

  /** Set maximum output tokens. */
  maxTokens(value) {
    this._maxTokens = value
    return this
  }

  /** Register a tool the agent can invoke. */
  addTool(toolName, config = {}) {
    this._tools.push({ name: toolName, ...config })
    return this
  }

  /**
   * Configure memory tiers.
   * @param {Object} config - { working, episodic, semantic }
   */
  withMemory(config) {
    this._memory = { ...this._memory, ...config }
    return this
  }

  /** Attach arbitrary metadata. */
  withMetadata(key, value) {
    this._metadata[key] = value
    return this
  }

  /** Produce the plain-object agent configuration. */
  build() {
    return {
      type: this._type,
      model: this._model,
      system_prompt: this._systemPrompt,
      temperature: this._temperature,
      max_tokens: this._maxTokens,
      tools: this._tools,
      memory: this._memory,
      ...(Object.keys(this._metadata).length > 0 && {
        metadata: this._metadata,
      }),
    }
  }
}
