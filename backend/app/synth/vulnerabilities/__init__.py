"""Vulnerability injectors.

Each injector knows how to insert a specific vulnerability pattern into
an already-generated piece of source code. Patterns are based on the
detectors in backend/app/refactor/ so the generated code is guaranteed
to trip the same rules as real legacy code.
"""
from .sql_injection import SqlInjectionInjector
from .hardcoded_creds import HardcodedCredsInjector
from .weak_crypto import WeakCryptoInjector
from .suppressed_exceptions import SuppressedExceptionInjector
from .pii_leak import PiiLeakInjector

__all__ = [
    "SqlInjectionInjector",
    "HardcodedCredsInjector",
    "WeakCryptoInjector",
    "SuppressedExceptionInjector",
    "PiiLeakInjector",
]
