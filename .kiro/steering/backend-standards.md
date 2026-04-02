---
inclusion: fileMatch
fileMatchPattern: "*.{js,ts,mjs}"
---

# Backend Standards

## API Design
- RESTful naming (plural nouns, HTTP verbs)
- Validate all input at boundaries
- Return consistent error format: { error, code }

## Security
- Never trust client input
- Rate limit all endpoints
- Sanitize before DB queries
- Environment variables for secrets

## Database
- Migrations for schema changes (never manual ALTER)
- Indexes on frequently queried columns
- Connection pooling for production

## Error Handling
- Catch at route level, not deep in business logic
- Log errors with context (request ID, user ID)
- Return 5xx for unexpected, 4xx for client errors
