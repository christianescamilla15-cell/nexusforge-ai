"""Suppressed exception injector — catch-all blocks that swallow errors."""
from __future__ import annotations

import random


CSHARP = [
    "            catch (Exception) {{ }}",
    "            catch (Exception ex) {{ /* ignored */ }}",
    "            catch {{ }}",
]


PYTHON = [
    "    except Exception:",
    "        pass",
]


class SuppressedExceptionInjector:
    def __init__(self, rng: random.Random) -> None:
        self.rng = rng

    def csharp_block(self) -> str:
        return self.rng.choice(CSHARP)

    def python_block(self) -> str:
        # Return a two-line except/pass block
        return "    except Exception:\n        pass"
