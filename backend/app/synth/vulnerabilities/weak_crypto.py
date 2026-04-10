"""Weak crypto injector — MD5 / SHA1 patterns."""
from __future__ import annotations

import random


CSHARP = [
    "            var hash = MD5.Create().ComputeHash(Encoding.UTF8.GetBytes(input));",
    "            var hash = SHA1.Create().ComputeHash(Encoding.UTF8.GetBytes(input));",
    "            byte[] hash = new MD5CryptoServiceProvider().ComputeHash(data);",
]


PYTHON = [
    "    digest = hashlib.md5(data.encode()).hexdigest()",
    "    digest = hashlib.sha1(data.encode()).hexdigest()",
    "    token = hashlib.md5(str(user_id).encode()).hexdigest()",
]


class WeakCryptoInjector:
    def __init__(self, rng: random.Random) -> None:
        self.rng = rng

    def csharp_line(self) -> str:
        return self.rng.choice(CSHARP)

    def python_line(self) -> str:
        return self.rng.choice(PYTHON)
