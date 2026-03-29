"""Service layer for Document Intelligence — document loading, classification, extraction."""
import json
import re
from pathlib import Path
from typing import Optional

FIXTURES_DIR = Path(__file__).parent / "fixtures"

def load_sample_documents() -> list:
    with open(FIXTURES_DIR / "sample_documents.json", encoding="utf-8") as f:
        return json.load(f)

def find_document(doc_id: str) -> dict | None:
    docs = load_sample_documents()
    return next((d for d in docs if d["id"] == doc_id), None)

def classify_document(content: str) -> tuple[str, float]:
    """Rule-based document classification (fallback when LLM unavailable)."""
    lower = content.lower()
    if any(w in lower for w in ["contrato", "contract", "cláusula", "clause", "jurisdicción", "jurisdiction"]):
        return "contract", 0.90
    if any(w in lower for w in ["política", "policy", "vigencia", "alcance", "requisitos"]):
        return "policy", 0.88
    if any(w in lower for w in ["factura", "invoice", "subtotal", "iva", "rfc", "emisor"]):
        return "invoice", 0.95
    if any(w in lower for w in ["currículum", "resume", "experiencia laboral", "work experience", "habilidades", "skills"]):
        return "resume", 0.87
    if any(w in lower for w in ["reporte", "report", "hallazgos", "findings", "recomendaciones"]):
        return "report", 0.85
    return "unknown", 0.40

def extract_fields(content: str, doc_type: str) -> dict:
    """Rule-based field extraction (fallback when LLM unavailable)."""
    fields = {}
    lines = content.split("\n")

    if doc_type == "contract":
        for line in lines:
            if "entre:" in line.lower() or "between:" in line.lower():
                fields["provider"] = line.split(":")[-1].strip().split("(")[0].strip()
            if ("y:" in line.lower() and "cliente" in line.lower()) or "and:" in line.lower():
                fields["client"] = line.split(":")[-1].strip().split("(")[0].strip()
            if "fecha de inicio" in line.lower() or "start date" in line.lower():
                fields["start_date"] = line.split(":")[-1].strip()
            if "fecha de fin" in line.lower() or "end date" in line.lower():
                fields["end_date"] = line.split(":")[-1].strip()
            if "valor" in line.lower() or "value" in line.lower():
                fields["value"] = line.split(":")[-1].strip()

    elif doc_type == "policy":
        for line in lines:
            if "vigencia" in line.lower() or "effective" in line.lower():
                fields["effective_date"] = line.split(":")[-1].strip()
            if "alcance" in line.lower() or "scope" in line.lower():
                fields["scope"] = line.split(":")[-1].strip()
            if "responsable" in line.lower() or "responsible" in line.lower():
                fields["responsible"] = line.split(":")[-1].strip()

    elif doc_type == "invoice":
        for line in lines:
            if "factura" in line.lower() or "invoice" in line.lower():
                match = re.search(r'#?\s*(\d{4}-\d+)', line)
                if match: fields["invoice_number"] = match.group(1)
            if "total:" in line.lower() and "subtotal" not in line.lower():
                fields["total"] = line.split(":")[-1].strip()
            if "vencimiento" in line.lower() or "due" in line.lower():
                fields["due_date"] = line.split(":")[-1].strip()

    elif doc_type == "resume":
        for line in lines:
            if "nombre" in line.lower() or "name" in line.lower():
                fields["full_name"] = line.split(":")[-1].strip()
            if "email" in line.lower():
                fields["email"] = line.split(":")[-1].strip()
            if "ubicación" in line.lower() or "location" in line.lower():
                fields["location"] = line.split(":")[-1].strip()

    return fields

def validate_extraction(fields: dict, doc_type: str) -> tuple[bool, list]:
    """Validate extracted fields against business rules."""
    errors = []

    if not fields:
        errors.append({"field": "all", "error": "No fields extracted", "severity": "critical"})
        return False, errors

    if doc_type == "contract":
        if "start_date" not in fields:
            errors.append({"field": "start_date", "error": "Missing start date", "severity": "error"})
        if "value" not in fields:
            errors.append({"field": "value", "error": "Missing contract value", "severity": "warning"})

    elif doc_type == "invoice":
        if "invoice_number" not in fields:
            errors.append({"field": "invoice_number", "error": "Missing invoice number", "severity": "error"})
        if "total" not in fields:
            errors.append({"field": "total", "error": "Missing total amount", "severity": "error"})

    elif doc_type == "resume":
        if "full_name" not in fields:
            errors.append({"field": "full_name", "error": "Missing full name", "severity": "error"})

    is_valid = not any(e["severity"] in ("error", "critical") for e in errors)
    return is_valid, errors

def generate_summary(content: str, doc_type: str, fields: dict, lang: str = "es") -> tuple[str, list]:
    """Generate document summary with key points."""
    word_count = len(content.split())

    summaries = {
        "contract": {
            "es": f"Contrato entre {fields.get('provider', 'proveedor')} y {fields.get('client', 'cliente')}. Vigencia desde {fields.get('start_date', 'N/A')} hasta {fields.get('end_date', 'N/A')}. Valor: {fields.get('value', 'N/A')}.",
            "en": f"Contract between {fields.get('provider', 'provider')} and {fields.get('client', 'client')}. Valid from {fields.get('start_date', 'N/A')} to {fields.get('end_date', 'N/A')}. Value: {fields.get('value', 'N/A')}.",
        },
        "policy": {
            "es": f"Política vigente desde {fields.get('effective_date', 'N/A')}. Alcance: {fields.get('scope', 'general')}.",
            "en": f"Policy effective from {fields.get('effective_date', 'N/A')}. Scope: {fields.get('scope', 'general')}.",
        },
        "invoice": {
            "es": f"Factura #{fields.get('invoice_number', 'N/A')} por un total de {fields.get('total', 'N/A')}. Vencimiento: {fields.get('due_date', 'N/A')}.",
            "en": f"Invoice #{fields.get('invoice_number', 'N/A')} for a total of {fields.get('total', 'N/A')}. Due: {fields.get('due_date', 'N/A')}.",
        },
        "resume": {
            "es": f"CV de {fields.get('full_name', 'candidato')}. Ubicación: {fields.get('location', 'N/A')}.",
            "en": f"Resume of {fields.get('full_name', 'candidate')}. Location: {fields.get('location', 'N/A')}.",
        },
    }

    default = {"es": "Documento procesado. Tipo no específico.", "en": "Document processed. Non-specific type."}
    summary = summaries.get(doc_type, default).get(lang, default["en"])

    key_points = [f"{k}: {v}" for k, v in list(fields.items())[:5]]

    return summary, key_points
