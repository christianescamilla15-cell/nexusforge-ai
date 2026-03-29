"""Service layer for Enterprise Operations — loads fixtures and provides data access."""
import json
from pathlib import Path

FIXTURES_DIR = Path(__file__).parent / "fixtures"

def load_customers():
    with open(FIXTURES_DIR / "customers.json", encoding="utf-8") as f:
        return json.load(f)

def load_policies():
    with open(FIXTURES_DIR / "policies.json", encoding="utf-8") as f:
        return json.load(f)

def load_calendar():
    with open(FIXTURES_DIR / "calendar.json", encoding="utf-8") as f:
        return json.load(f)

def find_customer(customer_id: str) -> dict | None:
    customers = load_customers()
    return next((c for c in customers if c["id"] == customer_id), None)

def find_policy(intent: str, lang: str = "es") -> dict | None:
    policies = load_policies()
    intent_policy_map = {
        "reschedule_meeting": "POL-001",
        "verify_contract": "POL-002",
        "check_onboarding": "POL-003",
        "update_crm": "POL-004",
        "consult_policy": None,
    }
    policy_id = intent_policy_map.get(intent)
    if policy_id:
        policy = next((p for p in policies if p["id"] == policy_id), None)
        if policy:
            return {
                "id": policy["id"],
                "title": policy.get(f"title_{lang}", policy["title"]),
                "content": policy.get(f"content_{lang}", policy["content"]),
            }
    return None

def get_available_slots(limit: int = 3) -> list:
    calendar = load_calendar()
    slots = []
    for day in calendar:
        for slot in day["slots"][:2]:
            slots.append(f"{day['date']} {slot}")
            if len(slots) >= limit:
                return slots
    return slots

def classify_intent(message: str) -> str:
    """Simple keyword-based intent classification (fallback when LLM unavailable)."""
    lower = message.lower()
    if any(w in lower for w in ["reprogramar", "reschedule", "reunión", "meeting", "cita"]):
        return "reschedule_meeting"
    if any(w in lower for w in ["contrato", "contract", "cobertura", "coverage", "soporte", "support"]):
        return "verify_contract"
    if any(w in lower for w in ["onboarding", "configuración", "setup", "inicio"]):
        return "check_onboarding"
    if any(w in lower for w in ["política", "policy", "norma", "regla"]):
        return "consult_policy"
    if any(w in lower for w in ["crm", "actualizar", "update", "cambiar plan"]):
        return "update_crm"
    return "general_inquiry"
