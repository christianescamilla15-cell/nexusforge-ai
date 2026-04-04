"""Schema declarations for all agents — enables auto-composition."""

AGENT_SCHEMAS = {
    # TRIGGERS
    "manual_trigger": {
        "category": "trigger",
        "input_schema": {},
        "output_schema": {"text": "string", "metadata": "object"},
        "config_schema": {"input_type": {"type": "select", "options": ["text", "file", "form", "json"]}},
    },
    "schedule_trigger": {
        "category": "trigger",
        "input_schema": {},
        "output_schema": {"triggered_at": "datetime", "schedule": "string"},
        "config_schema": {"cron": "string", "timezone": "string"},
    },
    "webhook_trigger": {
        "category": "trigger",
        "input_schema": {},
        "output_schema": {"body": "object", "headers": "object"},
        "config_schema": {"secret": "string"},
    },
    "email_trigger": {
        "category": "trigger",
        "input_schema": {},
        "output_schema": {"from": "string", "subject": "string", "body": "string", "attachments": "array"},
        "config_schema": {"filter_from": "string", "filter_subject": "string"},
    },
    "file_trigger": {
        "category": "trigger",
        "input_schema": {},
        "output_schema": {"filename": "string", "content": "string", "file_type": "string", "size": "number"},
        "config_schema": {"folder": "string", "extensions": "array"},
    },

    # TRANSFORMS (existing agents)
    "classifier": {
        "category": "transform",
        "input_schema": {"text": "string"},
        "output_schema": {"category": "string", "confidence": "number", "sub_category": "string"},
        "config_schema": {"categories": "array", "model": "string"},
    },
    "extractor": {
        "category": "transform",
        "input_schema": {"text": "string"},
        "output_schema": {"entities": "array", "fields": "object"},
        "config_schema": {"extraction_schema": "object"},
    },
    "summarizer": {
        "category": "transform",
        "input_schema": {"text": "string"},
        "output_schema": {"summary": "string", "key_points": "array"},
        "config_schema": {"max_length": "number", "style": "string"},
    },
    "sentiment": {
        "category": "transform",
        "input_schema": {"text": "string"},
        "output_schema": {"sentiment": "string", "score": "number", "emotions": "object"},
        "config_schema": {},
    },
    "translator": {
        "category": "transform",
        "input_schema": {"text": "string"},
        "output_schema": {"translated": "string", "source_lang": "string", "target_lang": "string"},
        "config_schema": {"target_language": "string"},
    },
    "ocr": {
        "category": "transform",
        "input_schema": {"file": "string"},
        "output_schema": {"text": "string", "pages": "number", "confidence": "number"},
        "config_schema": {},
    },
    "normalizer": {
        "category": "transform",
        "input_schema": {"data": "object"},
        "output_schema": {"normalized": "object", "changes": "array"},
        "config_schema": {"rules": "array"},
    },
    "analyzer": {
        "category": "transform",
        "input_schema": {"text": "string"},
        "output_schema": {"analysis": "object", "trends": "array", "anomalies": "array"},
        "config_schema": {"focus": "string"},
    },
    "enricher": {
        "category": "transform",
        "input_schema": {"data": "object"},
        "output_schema": {"enriched": "object", "sources": "array"},
        "config_schema": {"sources": "array"},
    },
    "compliance": {
        "category": "transform",
        "input_schema": {"text": "string"},
        "output_schema": {"compliant": "boolean", "issues": "array", "framework": "string"},
        "config_schema": {"framework": {"type": "select", "options": ["GDPR", "HIPAA", "SOX", "PCI"]}},
    },
    "knowledge": {
        "category": "transform",
        "input_schema": {"query": "string"},
        "output_schema": {"answer": "string", "sources": "array", "confidence": "number"},
        "config_schema": {"index_name": "string"},
    },
    "router": {
        "category": "transform",
        "input_schema": {"data": "object", "classification": "string"},
        "output_schema": {"target": "string", "reason": "string"},
        "config_schema": {"routes": "object"},
    },
    "validator": {
        "category": "transform",
        "input_schema": {"data": "object"},
        "output_schema": {"valid": "boolean", "errors": "array", "score": "number"},
        "config_schema": {"rules": "array"},
    },
    "reporter": {
        "category": "transform",
        "input_schema": {"data": "object"},
        "output_schema": {"report": "string", "format": "string", "sections": "array"},
        "config_schema": {"format": {"type": "select", "options": ["markdown", "html", "json"]}},
    },

    # ACTIONS
    "email_action": {
        "category": "action",
        "input_schema": {"to": "string", "subject": "string", "body": "string"},
        "output_schema": {"sent": "boolean", "message_id": "string"},
        "config_schema": {"smtp_host": "string", "from_email": "string"},
    },
    "slack_action": {
        "category": "action",
        "input_schema": {"message": "string", "channel": "string"},
        "output_schema": {"sent": "boolean", "ts": "string"},
        "config_schema": {"webhook_url": "string"},
    },
    "webhook_action": {
        "category": "action",
        "input_schema": {"data": "object"},
        "output_schema": {"status_code": "number", "response": "object"},
        "config_schema": {"url": "string", "method": "string", "headers": "object"},
    },
    "notion_action": {
        "category": "action",
        "input_schema": {"title": "string", "content": "string"},
        "output_schema": {"page_id": "string", "url": "string"},
        "config_schema": {"database_id": "string", "api_key": "string"},
    },
    "drive_action": {
        "category": "action",
        "input_schema": {"filename": "string", "content": "string"},
        "output_schema": {"file_id": "string", "url": "string"},
        "config_schema": {"folder_id": "string"},
    },
    "database_action": {
        "category": "action",
        "input_schema": {"data": "object"},
        "output_schema": {"inserted": "boolean", "id": "string"},
        "config_schema": {"table": "string"},
    },
}


def get_triggers():
    return {k: v for k, v in AGENT_SCHEMAS.items() if v["category"] == "trigger"}


def get_transforms():
    return {k: v for k, v in AGENT_SCHEMAS.items() if v["category"] == "transform"}


def get_actions():
    return {k: v for k, v in AGENT_SCHEMAS.items() if v["category"] == "action"}


def get_schema(agent_type):
    return AGENT_SCHEMAS.get(agent_type)
