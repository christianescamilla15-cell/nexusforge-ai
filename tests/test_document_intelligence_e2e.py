"""End-to-end tests for Document Intelligence workflow."""
import pytest
import asyncio
from backend.app.use_cases.document_intelligence.workflow import run_document_intelligence_workflow
from backend.app.use_cases.document_intelligence.schemas import DocumentIntelligenceInput
from backend.app.use_cases.document_intelligence.services import load_sample_documents

class TestDocumentIntelligenceE2E:
    def _run(self, coro):
        return asyncio.get_event_loop().run_until_complete(coro)

    def _get_doc(self, doc_id):
        docs = load_sample_documents()
        return next(d for d in docs if d["id"] == doc_id)

    def test_contract_processing_es(self):
        doc = self._get_doc("DOC-001")
        request = DocumentIntelligenceInput(content=doc["content"], filename=doc["filename"], language="es")
        result = self._run(run_document_intelligence_workflow(request))
        assert result.status == "completed"
        assert result.document_type == "contract"
        assert result.schema_valid is True
        assert len(result.extracted_fields) >= 2
        assert result.summary != ""
        assert len(result.agents_used) == 7

    def test_contract_processing_en(self):
        doc = self._get_doc("DOC-002")
        request = DocumentIntelligenceInput(content=doc["content"], filename=doc["filename"], language="en")
        result = self._run(run_document_intelligence_workflow(request))
        assert result.status == "completed"
        assert result.document_type == "contract"

    def test_invoice_extraction(self):
        doc = self._get_doc("DOC-004")
        request = DocumentIntelligenceInput(content=doc["content"], language="es")
        result = self._run(run_document_intelligence_workflow(request))
        assert result.document_type == "invoice"
        assert "invoice_number" in result.extracted_fields or "total" in result.extracted_fields

    def test_resume_classification(self):
        doc = self._get_doc("DOC-005")
        request = DocumentIntelligenceInput(content=doc["content"], language="es")
        result = self._run(run_document_intelligence_workflow(request))
        assert result.document_type == "resume"
        assert "full_name" in result.extracted_fields

    def test_malformed_document(self):
        doc = self._get_doc("DOC-006")
        request = DocumentIntelligenceInput(content=doc["content"], language="es")
        result = self._run(run_document_intelligence_workflow(request))
        assert result.document_type == "unknown"
        assert result.requires_human_review is True

    def test_empty_document(self):
        request = DocumentIntelligenceInput(content="", language="es")
        result = self._run(run_document_intelligence_workflow(request))
        assert result.status == "error"

    def test_type_hint_override(self):
        request = DocumentIntelligenceInput(content="Some text", document_type_hint="policy", language="es")
        result = self._run(run_document_intelligence_workflow(request))
        assert result.document_type == "policy"
