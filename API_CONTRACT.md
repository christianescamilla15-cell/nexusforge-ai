# NexusForge AI -- API Contract

Base URL: `http://localhost:8000/api`

All request and response bodies use JSON. Dates are ISO 8601 format. UUIDs are v4.

---

## Health

### GET /health

Check system health.

**Response 200:**
```json
{
  "status": "healthy",
  "service": "NexusForge AI",
  "components": {
    "database": "up",
    "redis": "up"
  },
  "agent_count": 8
}
```

`status` is `"healthy"` when all components are up, `"degraded"` otherwise.

---

## Workflows

### POST /workflows/

Create a new workflow. The DAG is validated before persistence.

**Request:**
```json
{
  "name": "Document Processing Pipeline",
  "description": "Classify, extract, and summarize documents",
  "dag_definition": {
    "steps": [
      {
        "name": "classify",
        "type": "classifier",
        "config": {},
        "depends_on": [],
        "retry_max": 3,
        "timeout_seconds": 300
      },
      {
        "name": "extract",
        "type": "extractor",
        "config": {},
        "depends_on": ["classify"],
        "retry_max": 3,
        "timeout_seconds": 300
      }
    ]
  }
}
```

**Response 201:**
```json
{
  "id": "550e8400-e29b-41d4-a716-446655440000",
  "name": "Document Processing Pipeline",
  "description": "Classify, extract, and summarize documents",
  "dag_definition": { "steps": [...] },
  "version": 1,
  "status": "active",
  "created_at": "2026-03-26T10:00:00Z",
  "updated_at": "2026-03-26T10:00:00Z"
}
```

**Response 422:** Invalid DAG (cycle, missing dependency, duplicate names, empty).

---

### GET /workflows/?skip=0&limit=20

List workflows (excludes archived).

**Query Parameters:**
| Param  | Type | Default | Description      |
|--------|------|---------|------------------|
| skip   | int  | 0       | Offset           |
| limit  | int  | 20      | Max results (1-100) |

**Response 200:** Array of WorkflowResponse objects.

---

### GET /workflows/{id}

Get a single workflow by UUID.

**Response 200:** WorkflowResponse object.
**Response 404:** `{"detail": "Workflow not found"}`

---

### PUT /workflows/{id}

Update workflow fields. Only provided fields are updated. If `dag_definition` is provided, it is validated first. Updating the DAG increments the `version`.

**Request:** (all fields optional)
```json
{
  "name": "Updated Name",
  "description": "Updated description",
  "dag_definition": { "steps": [...] },
  "status": "active"
}
```

**Response 200:** Updated WorkflowResponse.
**Response 404:** Workflow not found.
**Response 422:** Invalid DAG or no fields provided.

---

### DELETE /workflows/{id}

Soft-delete (archive) a workflow.

**Response 200:**
```json
{
  "detail": "Workflow archived",
  "id": "550e8400-e29b-41d4-a716-446655440000"
}
```

**Response 404:** Workflow not found or already archived.

---

## Executions

### POST /executions/

Trigger a workflow execution. Creates a run record and launches execution in the background.

**Request:**
```json
{
  "workflow_id": "550e8400-e29b-41d4-a716-446655440000",
  "trigger_type": "manual",
  "input_data": {
    "text": "Document content to process..."
  }
}
```

**Response 201:**
```json
{
  "run_id": "660e8400-e29b-41d4-a716-446655440000",
  "status": "pending",
  "created_at": "2026-03-26T10:01:00Z"
}
```

**Response 404:** Workflow not found or not active.

---

### GET /executions/?workflow_id=...&status=...&skip=0&limit=20

List execution runs with optional filters.

**Query Parameters:**
| Param       | Type   | Default | Description              |
|-------------|--------|---------|--------------------------|
| workflow_id | UUID   | null    | Filter by workflow       |
| status      | string | null    | Filter by run status     |
| skip        | int    | 0       | Offset                   |
| limit       | int    | 20      | Max results (1-100)      |

**Response 200:** Array of ExecutionResponse objects (without nested steps).

---

### GET /executions/{id}

Get a single execution run with all step details.

**Response 200:**
```json
{
  "id": "660e8400-...",
  "workflow_id": "550e8400-...",
  "status": "completed",
  "trigger_type": "manual",
  "started_at": "2026-03-26T10:01:01Z",
  "completed_at": "2026-03-26T10:01:15Z",
  "error_message": null,
  "total_tokens": 1250,
  "total_cost_usd": 0.0042,
  "metadata": {},
  "created_at": "2026-03-26T10:01:00Z",
  "steps": [
    {
      "id": "770e8400-...",
      "step_name": "classify",
      "step_type": "classifier",
      "agent_type": "classifier",
      "status": "completed",
      "input_data": { "text": "..." },
      "output_data": { "category": "financial", "confidence": 0.95 },
      "error_message": null,
      "retry_count": 0,
      "tokens_used": 450,
      "cost_usd": 0.0012,
      "duration_ms": 2300,
      "started_at": "2026-03-26T10:01:01Z",
      "completed_at": "2026-03-26T10:01:03Z"
    }
  ]
}
```

**Response 404:** Execution run not found.

---

### DELETE /executions/{id}

Cancel a running, pending, or queued execution.

**Response 200:**
```json
{
  "detail": "Execution cancelled",
  "run_id": "660e8400-..."
}
```

**Response 404:** Run not found or not in a cancellable state.

---

### WebSocket /executions/ws/{run_id}

Connect to receive real-time execution events.

**Protocol:**
1. Client opens WebSocket connection to `ws://localhost:8000/api/executions/ws/{run_id}`
2. Server accepts and subscribes to Redis pub/sub channel `run:{run_id}`
3. Server pushes JSON event messages as they occur
4. Client may send `"ping"` to receive `"pong"` (keep-alive)
5. Connection closes when the client disconnects

**Event messages:**
```json
{"event": "run_started", "groups": 3}
{"event": "group_started", "group": 0, "steps": ["classify"]}
{"event": "step_completed", "step": "classify", "duration_ms": 2300, "tokens": 450}
{"event": "run_completed", "total_tokens": 1250, "total_cost_usd": 0.0042}
{"event": "run_failed", "failed_step": "extract"}
```

---

## Agents

### GET /agents/

List all registered agents.

**Response 200:**
```json
[
  {
    "agent_type": "classifier",
    "name": "ClassifierAgent",
    "description": "Classifies documents into categories: legal, financial, technical, medical, general.",
    "tools": ["llm_chat"],
    "status": "active"
  }
]
```

---

### GET /agents/{agent_type}

Get details for a specific agent type.

**Response 200:**
```json
{
  "agent_type": "classifier",
  "name": "ClassifierAgent",
  "description": "Classifies documents into categories...",
  "tools": ["llm_chat"],
  "status": "active",
  "config_schema": {}
}
```

**Response 404:** `{"detail": "Agent type 'xyz' not found"}`

---

## Documents

### POST /documents/

Upload a document and index it for RAG retrieval.

**Request:**
```json
{
  "title": "Q3 Financial Report",
  "content": "Revenue increased by 15% in Q3 2026...",
  "file_type": "text",
  "language": "en",
  "metadata": { "source": "finance-dept", "year": 2026 }
}
```

**Response 201:**
```json
{
  "id": "880e8400-...",
  "title": "Q3 Financial Report",
  "content": "Revenue increased by 15%...",
  "file_type": "text",
  "language": "en",
  "status": "indexed",
  "created_at": "2026-03-26T10:05:00Z"
}
```

Content must be at least 10 characters. Title must be 1-500 characters.

---

### GET /documents/?skip=0&limit=20

List documents with pagination.

**Response 200:** Array of DocumentResponse objects.

---

### POST /documents/search

Semantic search across indexed documents.

**Request:**
```json
{
  "query": "revenue growth Q3",
  "top_k": 5
}
```

**Response 200:**
```json
[
  {
    "id": "990e8400-...",
    "document_id": "880e8400-...",
    "content": "Revenue increased by 15% in Q3 2026...",
    "chunk_index": 0,
    "similarity": 0.923,
    "metadata": {}
  }
]
```

Query must be at least 1 character. `top_k` range: 1-20 (default 5).

---

## Error Response Format

All errors follow this structure:

```json
{
  "detail": "Human-readable error message"
}
```

### HTTP Status Codes

| Code | Meaning                                      |
|------|----------------------------------------------|
| 200  | Success                                      |
| 201  | Created                                      |
| 404  | Resource not found                           |
| 422  | Validation error (bad input, invalid DAG)    |
| 500  | Internal server error                        |

---

## Pagination

List endpoints accept `skip` and `limit` query parameters:

| Param | Type | Default | Range   | Description             |
|-------|------|---------|---------|-------------------------|
| skip  | int  | 0       | >= 0    | Number of items to skip |
| limit | int  | 20      | 1-100   | Max items to return     |

Results are ordered by `created_at DESC` (newest first).
