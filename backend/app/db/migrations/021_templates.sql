-- 021: Automation templates / pre-built kits

CREATE TABLE IF NOT EXISTS automation_templates (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    slug VARCHAR(50) UNIQUE NOT NULL,
    name VARCHAR(100) NOT NULL,
    description TEXT,
    icon VARCHAR(10) DEFAULT '📋',
    color VARCHAR(20) DEFAULT '#6366F1',
    category VARCHAR(30) NOT NULL, -- support, finance, hr, marketing, operations
    dag_definition JSONB NOT NULL,
    input_config JSONB DEFAULT '{"type": "none"}',
    default_rules JSONB DEFAULT '[]',
    suggested_connectors JSONB DEFAULT '[]',
    estimated_agents INT DEFAULT 3,
    created_at TIMESTAMPTZ DEFAULT now()
);

-- Seed 5 templates

INSERT INTO automation_templates (slug, name, description, icon, color, category, dag_definition, input_config, default_rules, suggested_connectors, estimated_agents)
VALUES
(
    'ticket-triage',
    'Ticket Triage & Auto-Response',
    'Classify support tickets by urgency, extract key info, route to the right team, and generate initial response.',
    '🎫',
    '#EF4444',
    'support',
    '{"steps": [{"name": "intake", "type": "extractor", "depends_on": []}, {"name": "classify_urgency", "type": "classifier", "depends_on": ["intake"]}, {"name": "extract_entities", "type": "extractor", "depends_on": ["intake"]}, {"name": "route_team", "type": "router", "depends_on": ["classify_urgency", "extract_entities"]}, {"name": "generate_response", "type": "summarizer", "depends_on": ["route_team"]}, {"name": "notify_team", "type": "webhook", "depends_on": ["route_team"]}, {"name": "validate_output", "type": "validator", "depends_on": ["generate_response"]}]}'::jsonb,
    '{"type": "text", "label": "Ticket content", "placeholder": "Paste the support ticket here..."}'::jsonb,
    '[{"name": "Escalate urgent", "conditions": [{"field": "urgency", "operator": "equals", "value": "critical"}], "actions": [{"type": "notify", "channel": "slack", "message": "URGENT ticket: {{ticket_id}}"}]}, {"name": "Auto-close spam", "conditions": [{"field": "category", "operator": "equals", "value": "spam"}], "actions": [{"type": "skip_step", "step_name": "generate_response"}]}]'::jsonb,
    '["gmail", "slack"]'::jsonb,
    7
),
(
    'invoice-processing',
    'Invoice Data Extraction',
    'Extract data from PDF invoices: vendor, amount, date, line items. Validate and store structured data.',
    '🧾',
    '#10B981',
    'finance',
    '{"steps": [{"name": "pdf_ocr", "type": "ocr", "depends_on": []}, {"name": "extract_fields", "type": "extractor", "depends_on": ["pdf_ocr"]}, {"name": "normalize_data", "type": "normalizer", "depends_on": ["extract_fields"]}, {"name": "validate_invoice", "type": "validator", "depends_on": ["normalize_data"]}, {"name": "generate_report", "type": "reporter", "depends_on": ["validate_invoice"]}]}'::jsonb,
    '{"type": "file", "label": "Upload invoice", "accept": ".pdf,.jpg,.png"}'::jsonb,
    '[]'::jsonb,
    '["drive", "notion"]'::jsonb,
    5
),
(
    'email-responder',
    'Smart Email Auto-Responder',
    'Read incoming emails, classify intent, check knowledge base, generate and send personalized response.',
    '📧',
    '#3B82F6',
    'support',
    '{"steps": [{"name": "read_email", "type": "extractor", "depends_on": []}, {"name": "classify_intent", "type": "classifier", "depends_on": ["read_email"]}, {"name": "search_knowledge", "type": "knowledge", "depends_on": ["classify_intent"]}, {"name": "draft_response", "type": "summarizer", "depends_on": ["search_knowledge"]}, {"name": "quality_check", "type": "validator", "depends_on": ["draft_response"]}, {"name": "send_response", "type": "webhook", "depends_on": ["quality_check"]}]}'::jsonb,
    '{"type": "text", "label": "Email content", "placeholder": "Paste the email to respond to..."}'::jsonb,
    '[]'::jsonb,
    '["gmail"]'::jsonb,
    6
),
(
    'report-generator',
    'Executive Report Generator',
    'Gather data from multiple sources, analyze trends, generate executive summary with KPIs.',
    '📊',
    '#F59E0B',
    'operations',
    '{"steps": [{"name": "gather_data", "type": "scraper", "depends_on": []}, {"name": "analyze_trends", "type": "analyzer", "depends_on": ["gather_data"]}, {"name": "sentiment_check", "type": "sentiment", "depends_on": ["gather_data"]}, {"name": "compile_report", "type": "reporter", "depends_on": ["analyze_trends", "sentiment_check"]}, {"name": "validate_report", "type": "validator", "depends_on": ["compile_report"]}]}'::jsonb,
    '{"type": "form", "fields": [{"key": "topic", "label": "Report topic", "type": "text"}, {"key": "period", "label": "Time period", "type": "select", "options": ["Last week", "Last month", "Last quarter"]}]}'::jsonb,
    '[]'::jsonb,
    '["notion", "slack"]'::jsonb,
    5
),
(
    'approval-workflow',
    'Request Approval Pipeline',
    'Receive requests (purchases, expenses, access), validate rules, route for approval, notify stakeholders.',
    '✅',
    '#8B5CF6',
    'operations',
    '{"steps": [{"name": "intake_request", "type": "extractor", "depends_on": []}, {"name": "validate_policy", "type": "compliance", "depends_on": ["intake_request"]}, {"name": "classify_type", "type": "classifier", "depends_on": ["intake_request"]}, {"name": "route_approver", "type": "router", "depends_on": ["validate_policy", "classify_type"]}, {"name": "notify_approver", "type": "webhook", "depends_on": ["route_approver"]}, {"name": "record_decision", "type": "reporter", "depends_on": ["notify_approver"]}]}'::jsonb,
    '{"type": "form", "fields": [{"key": "request_type", "label": "Request type", "type": "select", "options": ["Purchase", "Expense", "Access", "Leave"]}, {"key": "description", "label": "Description", "type": "text"}, {"key": "amount", "label": "Amount (USD)", "type": "text"}]}'::jsonb,
    '[]'::jsonb,
    '["slack", "notion"]'::jsonb,
    6
)
ON CONFLICT (slug) DO NOTHING;
