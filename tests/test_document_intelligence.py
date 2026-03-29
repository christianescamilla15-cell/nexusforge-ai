import pytest
import asyncio
from backend.app.use_cases.document_intelligence.services import (
    load_sample_documents, find_document, classify_document,
    extract_fields, validate_extraction, generate_summary,
)
from backend.app.use_cases.document_intelligence.schemas import DocumentIntelligenceInput, DocumentIntelligenceFinalOutput

class TestDocumentServices:
    def test_load_documents(self):
        docs = load_sample_documents()
        assert len(docs) >= 6

    def test_find_document(self):
        doc = find_document("DOC-001")
        assert doc is not None
        assert doc["type"] == "contract"

    def test_find_missing(self):
        assert find_document("DOC-999") is None

    def test_classify_contract(self):
        doc_type, conf = classify_document("Este contrato establece las cláusulas entre las partes")
        assert doc_type == "contract"
        assert conf > 0.5

    def test_classify_invoice(self):
        doc_type, conf = classify_document("Factura #001 - Subtotal: $100 - IVA: $16 - Total: $116")
        assert doc_type == "invoice"

    def test_classify_resume(self):
        doc_type, conf = classify_document("Currículum Vitae - Experiencia laboral - Habilidades")
        assert doc_type == "resume"

    def test_classify_unknown(self):
        doc_type, conf = classify_document("random text without structure")
        assert doc_type == "unknown"
        assert conf < 0.5

    def test_extract_contract_fields(self):
        doc = find_document("DOC-001")
        fields = extract_fields(doc["content"], "contract")
        assert len(fields) >= 2

    def test_extract_invoice_fields(self):
        doc = find_document("DOC-004")
        fields = extract_fields(doc["content"], "invoice")
        assert "invoice_number" in fields or "total" in fields

    def test_validate_valid(self):
        fields = {"start_date": "2026-01-01", "value": "$45,000", "provider": "X"}
        valid, errors = validate_extraction(fields, "contract")
        assert valid is True

    def test_validate_empty(self):
        valid, errors = validate_extraction({}, "contract")
        assert valid is False

    def test_generate_summary(self):
        fields = {"provider": "TechCorp", "client": "Grupo Industrial", "start_date": "2026-01-01", "end_date": "2026-12-31", "value": "$45,000"}
        summary, points = generate_summary("content", "contract", fields, "es")
        assert "TechCorp" in summary
        assert len(points) > 0

class TestSchemas:
    def test_input_defaults(self):
        inp = DocumentIntelligenceInput(content="test")
        assert inp.language == "es"

    def test_output_structure(self):
        out = DocumentIntelligenceFinalOutput(run_id="x", status="ok", document_type="contract")
        assert out.extracted_fields == {}
        assert out.requires_human_review is False
