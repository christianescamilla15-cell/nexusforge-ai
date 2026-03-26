# @nexusforge/sdk

Programmatic access to the NexusForge AI agent orchestration platform.

## Installation

```bash
npm install @nexusforge/sdk
```

## Quick Start

```javascript
import { NexusForgeClient, WorkflowBuilder } from '@nexusforge/sdk'

const client = new NexusForgeClient({
  apiUrl: 'http://localhost:8000/api',
  apiKey: process.env.NEXUSFORGE_API_KEY,  // optional
})

// Check API health
const status = await client.health()
console.log(status)
```

## Workflows

### Create a workflow with the builder

```javascript
import { WorkflowBuilder } from '@nexusforge/sdk'

const workflow = new WorkflowBuilder('Document Analysis')
  .description('Classify, extract, and summarize documents')
  .addStep('classify', 'classifier')
  .addStep('extract', 'extractor', ['classify'])
  .addStep('summarize', 'summarizer', ['extract'])
  .withConfig('summarize', { max_tokens: 500, format: 'bullet_points' })
  .build()

const created = await client.createWorkflow(workflow)
console.log('Created workflow:', created.id)
```

### Run a workflow

```javascript
const run = await client.runWorkflow(created.id, {
  document: 'Base64-encoded content or URL...',
})
console.log('Run status:', run.status)  // "queued" | "running" | "completed" | "failed"
```

### Monitor execution

```javascript
const run = await client.getRun(runId)
console.log(run.status, run.steps)

// List runs filtered by status
const active = await client.listRuns({ status: 'running', limit: 10 })
```

## Agents

### Configure agents with the builder

```javascript
import { AgentBuilder } from '@nexusforge/sdk'

const agent = new AgentBuilder('classifier')
  .model('claude-sonnet-4-20250514')
  .systemPrompt('Classify incoming documents by topic and urgency.')
  .temperature(0.2)
  .maxTokens(1024)
  .addTool('web_search')
  .withMemory({ episodic: true, semantic: true })
  .build()
```

### List available agents

```javascript
const agents = await client.listAgents()
agents.forEach(a => console.log(a.type, a.description))
```

## Documents (RAG)

```javascript
// Upload a document for indexing
await client.uploadDocument({
  name: 'Q4 Report',
  content: 'Full text of the document...',
  metadata: { department: 'finance', year: 2025 },
})

// Semantic search
const results = await client.searchDocuments('quarterly revenue growth', {
  top_k: 5,
  threshold: 0.7,
})
```

## Swarms

```javascript
// Execute a swarm with star topology
const result = await client.executeSwarm(
  'star',
  ['classifier', 'extractor', 'summarizer', 'reviewer'],
  { task: 'Analyze this contract for key terms and risks' }
)
console.log(result.output)
```

## Error Handling

```javascript
try {
  await client.runWorkflow('nonexistent-id')
} catch (err) {
  console.error(err.message) // "NexusForge API error 404: ..."
  console.error(err.status)  // 404
}
```

## API Reference

| Method | Description |
|---|---|
| `listWorkflows()` | List all workflows |
| `getWorkflow(id)` | Get workflow by ID |
| `createWorkflow(data)` | Create a workflow |
| `updateWorkflow(id, data)` | Update a workflow |
| `deleteWorkflow(id)` | Delete a workflow |
| `runWorkflow(id, input?)` | Trigger a workflow run |
| `listRuns(filters?)` | List runs with optional filters |
| `getRun(id)` | Get run details |
| `cancelRun(id)` | Cancel a running execution |
| `listAgents()` | List agent types |
| `getAgent(type)` | Get agent metadata |
| `uploadDocument(data)` | Upload document for RAG |
| `searchDocuments(query, opts?)` | Semantic document search |
| `listSwarms()` | List swarm topologies |
| `executeSwarm(topology, agents, input)` | Run a swarm |
| `health()` | API health check |
