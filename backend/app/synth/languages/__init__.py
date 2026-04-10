"""Per-language generators.

Each generator produces idiomatic but intentionally-legacy code for one
language, inserts the configured vulnerability density, and writes files
onto disk under a target directory.

MVP (phase 2): csharp, python, cobol.
Later phases: vbnet, java, php, typescript, cpp.
"""
from .csharp import CSharpGenerator
from .python import PythonGenerator
from .cobol import CobolGenerator

__all__ = ["CSharpGenerator", "PythonGenerator", "CobolGenerator"]
