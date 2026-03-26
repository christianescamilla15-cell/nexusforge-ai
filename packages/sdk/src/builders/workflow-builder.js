/**
 * WorkflowBuilder — fluent builder for constructing workflow definitions.
 *
 * Usage:
 *   const wf = new WorkflowBuilder('My Pipeline')
 *     .description('Classify then summarize')
 *     .addStep('classify', 'classifier')
 *     .addStep('summarize', 'summarizer', ['classify'])
 *     .withConfig('summarize', { max_tokens: 500 })
 *     .build()
 */
export class WorkflowBuilder {
  /**
   * @param {string} name - Human-readable workflow name
   */
  constructor(name) {
    if (!name) throw new Error('Workflow name is required')
    this._name = name
    this._description = ''
    this._steps = []
    this._metadata = {}
  }

  /** Set a description for the workflow. */
  description(desc) {
    this._description = desc
    return this
  }

  /**
   * Append a step to the DAG.
   * @param {string} name      - Unique step identifier
   * @param {string} agentType - Agent type that executes this step
   * @param {string[]} deps    - Step names this step depends on
   */
  addStep(name, agentType, deps = []) {
    if (this._steps.some((s) => s.name === name)) {
      throw new Error(`Duplicate step name: "${name}"`)
    }
    this._steps.push({
      name,
      agent_type: agentType,
      depends_on: deps,
      config: {},
    })
    return this
  }

  /**
   * Merge configuration into an existing step.
   * @param {string} stepName - The step to configure
   * @param {Object} config   - Key/value config to merge
   */
  withConfig(stepName, config) {
    const step = this._steps.find((s) => s.name === stepName)
    if (!step) throw new Error(`Step not found: "${stepName}"`)
    step.config = { ...step.config, ...config }
    return this
  }

  /** Attach arbitrary metadata to the workflow. */
  withMetadata(key, value) {
    this._metadata[key] = value
    return this
  }

  /** Produce the plain-object workflow definition. */
  build() {
    if (this._steps.length === 0) {
      throw new Error('Workflow must have at least one step')
    }

    // Validate dependency references
    const stepNames = new Set(this._steps.map((s) => s.name))
    for (const step of this._steps) {
      for (const dep of step.depends_on) {
        if (!stepNames.has(dep)) {
          throw new Error(
            `Step "${step.name}" depends on unknown step "${dep}"`
          )
        }
      }
    }

    return {
      name: this._name,
      description: this._description,
      dag_definition: { steps: this._steps },
      ...(Object.keys(this._metadata).length > 0 && {
        metadata: this._metadata,
      }),
    }
  }
}
