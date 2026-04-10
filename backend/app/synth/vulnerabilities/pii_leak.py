"""PII leak injector.

Inserts field / column / variable names that the NexusForge PII scanner
(``backend/app/refactor/pii_scanner.py``) recognises as personal data,
intentionally stored or logged without encryption or masking.
"""
from __future__ import annotations

import random


# These strings match the regex patterns in pii_scanner.py after the
# confidentiality-sanitization pass (generic industry terms only).
PII_FIELDS = [
    "customer_name",
    "customer_email",
    "customer_phone",
    "full_name",
    "address",
    "birth_date",
    "tax_id",
    "national_id",
    "credit_card_num",
    "password",
    "transaction_reference",
]


CSHARP_LEAK_TEMPLATES = [
    '        Logger.Info("Processing record for " + {field});',
    '        public string {field} {{ get; set; }}',
    '        Console.WriteLine($"Loaded {{{field}}}");',
]


PYTHON_LEAK_TEMPLATES = [
    '    logger.info(f"Processing record for {{{field}}}")',
    '    self.{field} = data.get("{field}")',
    '    print(f"Loaded {{{field}}}")',
]


class PiiLeakInjector:
    def __init__(self, rng: random.Random) -> None:
        self.rng = rng

    def _random_field(self) -> str:
        return self.rng.choice(PII_FIELDS)

    def csharp_line(self) -> str:
        tpl = self.rng.choice(CSHARP_LEAK_TEMPLATES)
        return tpl.format(field=self._random_field())

    def python_line(self) -> str:
        tpl = self.rng.choice(PYTHON_LEAK_TEMPLATES)
        return tpl.format(field=self._random_field())
