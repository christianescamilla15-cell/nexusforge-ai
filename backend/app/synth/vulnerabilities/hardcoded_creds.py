"""Hardcoded credentials injector.

Mirrors the credential patterns detected by
``backend/app/refactor/csharp_analyzer.py`` and ``mythos`` secret scanner.
All credential values are clearly-fake sentinels so no real secret ever
lands in the synthetic code tree.
"""
from __future__ import annotations

import random


CSHARP_CREDS = [
    'private const string DB_PASSWORD = "synth-fake-db-pwd-{n}";',
    'private const string API_KEY = "synth-fake-api-key-{n}";',
    'private const string JWT_SECRET = "synth-fake-jwt-secret-{n}-do-not-use";',
    'private const string SMTP_PASS = "synth-fake-smtp-{n}";',
    'static readonly string ConnectionString = "Server=db-{n};User=sa;Password=synth-fake-{n};";',
]


PYTHON_CREDS = [
    'DB_PASSWORD = "synth-fake-db-pwd-{n}"',
    'API_KEY = "synth-fake-api-key-{n}"',
    'JWT_SECRET = "synth-fake-jwt-secret-{n}-do-not-use"',
    'SMTP_PASS = "synth-fake-smtp-{n}"',
    'DATABASE_URL = "postgresql://admin:synth-fake-{n}@db-{n}.internal/app"',
]


CONFIG_CREDS = [
    '<add key="DbPassword" value="synth-fake-db-pwd-{n}" />',
    '<add key="ApiKey" value="synth-fake-api-key-{n}" />',
    '<connectionStrings><add name="Default" connectionString="Data Source=db-{n};User ID=sa;Password=synth-fake-{n};" /></connectionStrings>',
]


class HardcodedCredsInjector:
    """Emit hardcoded credential lines for different contexts."""

    def __init__(self, rng: random.Random) -> None:
        self.rng = rng
        self._counter = 0

    def _next(self) -> int:
        self._counter += 1
        return self._counter

    def csharp_line(self) -> str:
        tpl = self.rng.choice(CSHARP_CREDS)
        return tpl.format(n=self._next())

    def python_line(self) -> str:
        tpl = self.rng.choice(PYTHON_CREDS)
        return tpl.format(n=self._next())

    def config_line(self) -> str:
        tpl = self.rng.choice(CONFIG_CREDS)
        return tpl.format(n=self._next())
