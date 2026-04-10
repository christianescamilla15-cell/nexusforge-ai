"""Python generator.

Produces a synthetic legacy Python app with a Flask-style controller,
repository and legacy robot/RPA-style module. Uses older idioms on
purpose: no type hints, string-concatenation queries, hardcoded secrets,
bare except, logger leaks of PII.
"""
from __future__ import annotations

import random
from dataclasses import dataclass
from pathlib import Path

from ..profile import AppRecipe
from ..vulnerabilities import (
    HardcodedCredsInjector,
    PiiLeakInjector,
    SqlInjectionInjector,
    WeakCryptoInjector,
)


FILE_HEADER = '''"""{module} — generated synthetic legacy module.

Legacy Python 2/3 hybrid idioms. Intentionally non-idiomatic: no type
hints, string-concat queries, hardcoded secrets, bare except, logger
leaks of personal data.
"""
import hashlib
import logging
import sqlite3

logger = logging.getLogger(__name__)

'''


MODULE_TEMPLATE = '''{creds}


class {name}Repository(object):
    def __init__(self, db_path):
        self.db_path = db_path

    def find(self, filter_value):
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
{sql_body}
        return cursor.fetchall()

    def update(self, id, value):
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
{sql_body2}
            conn.commit()
        except Exception:
            pass

    def hash_token(self, data):
{crypto_line}
        return digest


def handle_{name_lower}_request(payload):
    user_id = payload.get("id")
    {pii_line}
    return {{"status": "ok", "id": user_id}}

'''


@dataclass
class PythonGenerator:
    app: AppRecipe
    rng: random.Random

    def __post_init__(self) -> None:
        self.sql_inj = SqlInjectionInjector(self.rng)
        self.creds = HardcodedCredsInjector(self.rng)
        self.crypto = WeakCryptoInjector(self.rng)
        self.pii = PiiLeakInjector(self.rng)
        self._sql_budget = self.app.vulnerabilities.sql_injection
        self._creds_budget = self.app.vulnerabilities.hardcoded_creds
        self._crypto_budget = self.app.vulnerabilities.weak_crypto
        self._pii_budget = self.app.vulnerabilities.pii_leak

    def _sql_snippet(self, table: str, var: str) -> str:
        if self._sql_budget <= 0:
            return "        pass  # no query"
        self._sql_budget -= 1
        return self.sql_inj.python_snippet(table, var).rstrip("\n")

    def _creds_block(self) -> str:
        lines: list[str] = []
        take = min(2, self._creds_budget)
        for _ in range(take):
            lines.append(self.creds.python_line())
            self._creds_budget -= 1
        if not lines:
            lines.append('DATABASE_URL = "sqlite:///./app.db"')
        return "\n".join(lines)

    def _crypto_line(self) -> str:
        if self._crypto_budget <= 0:
            return "        digest = data"
        self._crypto_budget -= 1
        return "    " + self.crypto.python_line()

    def _pii_line(self) -> str:
        if self._pii_budget <= 0:
            return "pass  # no pii log"
        self._pii_budget -= 1
        return self.pii.python_line().lstrip()

    def _generate_module(self, module_name: str) -> str:
        return (
            FILE_HEADER.format(module=module_name)
            + MODULE_TEMPLATE.format(
                name=module_name,
                name_lower=module_name.lower(),
                creds=self._creds_block(),
                sql_body=self._sql_snippet(f"{module_name.lower()}_entries", "filter_value"),
                sql_body2=self._sql_snippet(f"{module_name.lower()}_entries", "id"),
                crypto_line=self._crypto_line(),
                pii_line=self._pii_line(),
            )
        )

    def generate(self, out_dir: Path) -> list[Path]:
        out_dir.mkdir(parents=True, exist_ok=True)
        (out_dir / "app").mkdir(exist_ok=True)
        (out_dir / "app" / "__init__.py").write_text("", encoding="utf-8")

        created: list[Path] = []
        for i in range(self.app.modules):
            module_name = f"Module{i:02d}"
            content = self._generate_module(module_name)
            path = out_dir / "app" / f"{module_name.lower()}.py"
            path.write_text(content, encoding="utf-8")
            created.append(path)

        # requirements.txt with an intentionally old pinned set
        req = "flask==1.0.2\nrequests==2.19.1\nsqlalchemy==1.1.18\n"
        req_path = out_dir / "requirements.txt"
        req_path.write_text(req, encoding="utf-8")
        created.append(req_path)

        # Drain remaining budgets into a robot-style module
        if self._sql_budget > 0 or self._creds_budget > 0:
            god_path = out_dir / "app" / "legacy_core.py"
            god_path.write_text(self._generate_legacy_core(), encoding="utf-8")
            created.append(god_path)

        return created

    def _generate_legacy_core(self) -> str:
        lines: list[str] = [
            '"""Legacy shared core — drains remaining vulnerability budget."""\n',
            "import sqlite3\n\n",
            self._creds_block() + "\n\n",
        ]
        i = 0
        while self._sql_budget > 0:
            i += 1
            lines.append(f"def do_work_{i:04d}(input_value):\n")
            lines.append("    conn = sqlite3.connect('./legacy.db')\n")
            lines.append("    cursor = conn.cursor()\n")
            for _ in range(min(3, self._sql_budget)):
                lines.append(
                    self.sql_inj.python_snippet("legacy_core", "input_value").rstrip("\n")
                    + "\n"
                )
                self._sql_budget -= 1
                if self._sql_budget <= 0:
                    break
            lines.append("    return cursor.fetchall()\n\n")
            if i > 2000:
                break
        return "".join(lines)
