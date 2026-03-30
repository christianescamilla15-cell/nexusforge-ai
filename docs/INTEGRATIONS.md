# NexusForge Integrations

## Available Integrations

| Integration | Status | Use Cases |
|------------|--------|-----------|
| Google Drive | Read files, fetch content | Document AI, Knowledge Copilot |
| Gmail | Read messages, extract context | Operations Assistant |
| Google Calendar | Read events, check availability | Operations Assistant |
| Notion | Write results, store summaries | All use cases |
| Webhooks | Send structured outputs | All use cases |

## Configuration

Set these environment variables:

```bash
# Google (service account JSON)
GOOGLE_CREDENTIALS_PATH=/path/to/service-account.json
GMAIL_USER=your@gmail.com
GOOGLE_CALENDAR_ID=primary

# Notion
NOTION_API_KEY=ntn_xxx
NOTION_DATABASE_ID=xxx

# Webhooks
NEXUSFORGE_WEBHOOK_URL=https://your-endpoint.com/webhook
```

## API Endpoints

- `GET /api/integrations/status` — Check which integrations are configured
- `GET /api/integrations/drive/files` — List Google Drive files
- `GET /api/integrations/gmail/messages` — List Gmail messages
- `GET /api/integrations/calendar/events` — List calendar events
- `GET /api/integrations/calendar/availability` — Check available slots
- `POST /api/integrations/notion/write` — Write to Notion
- `POST /api/integrations/webhook/send` — Send webhook

## How Integrations Support Each Service

### Document AI
1. Fetch documents from Google Drive
2. Process through Document Intelligence workflow
3. Store results in Notion or send via webhook

### Operations Assistant
1. Read customer emails from Gmail
2. Check calendar for availability
3. Process through Enterprise Ops workflow
4. Write action log to Notion

### Knowledge Copilot
1. Index Drive/Notion content as knowledge sources
2. Answer questions using Portfolio Copilot workflow
3. Return structured answers with source attribution
