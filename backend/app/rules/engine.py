"""Rules Engine — evaluate if/then/else conditions against input data."""

import json
import logging
import re
from uuid import UUID

from app.db.client import get_db_pool

logger = logging.getLogger(__name__)

# ── Supported operators ──────────────────────────────────────────────────────

OPERATORS = {
    "equals": lambda a, b: str(a).lower() == str(b).lower(),
    "not_equals": lambda a, b: str(a).lower() != str(b).lower(),
    "contains": lambda a, b: str(b).lower() in str(a).lower(),
    "greater_than": lambda a, b: float(a) > float(b),
    "less_than": lambda a, b: float(a) < float(b),
    "starts_with": lambda a, b: str(a).lower().startswith(str(b).lower()),
    "is_empty": lambda a, b: not a or str(a).strip() == "",
    "is_not_empty": lambda a, b: a and str(a).strip() != "",
    "regex": lambda a, b: bool(re.search(str(b), str(a))),
}

OPERATOR_LABELS = {
    "equals": "equals",
    "not_equals": "not equals",
    "contains": "contains",
    "greater_than": "greater than",
    "less_than": "less than",
    "starts_with": "starts with",
    "is_empty": "is empty",
    "is_not_empty": "is not empty",
    "regex": "matches regex",
}


def _check_condition(field_value, operator: str, expected_value) -> bool:
    """Evaluate a single condition. Returns False on any error."""
    op_fn = OPERATORS.get(operator)
    if not op_fn:
        logger.warning("Unknown operator: %s", operator)
        return False
    try:
        return op_fn(field_value, expected_value)
    except (ValueError, TypeError, re.error) as exc:
        logger.debug("Condition eval error (%s): %s", operator, exc)
        return False


async def evaluate_rules(automation_id: UUID, input_data: dict) -> list[dict]:
    """Evaluate all active rules for an automation.

    Returns a list of matched rules with their actions:
    [{"rule_id": "...", "name": "...", "actions": [...], "priority": N}]
    """
    pool = await get_db_pool()
    async with pool.acquire() as conn:
        rules = await conn.fetch(
            """SELECT * FROM automation_rules
               WHERE automation_id = $1 AND is_active = true
               ORDER BY priority DESC""",
            automation_id,
        )

    matched = []
    for rule in rules:
        conditions = rule["conditions"]
        if isinstance(conditions, str):
            conditions = json.loads(conditions)

        # All conditions must match (AND logic)
        all_match = True
        for cond in conditions:
            field_val = input_data.get(cond.get("field", ""))
            op = cond.get("operator", "")
            expected = cond.get("value", "")
            if not _check_condition(field_val, op, expected):
                all_match = False
                break

        if all_match:
            actions = rule["actions"]
            if isinstance(actions, str):
                actions = json.loads(actions)
            matched.append({
                "rule_id": str(rule["id"]),
                "name": rule["name"],
                "priority": rule["priority"],
                "actions": actions,
            })

    return matched
