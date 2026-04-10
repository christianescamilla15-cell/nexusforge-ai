"""SQL injection injector.

Produces realistic string-concatenation query patterns that match the
detection rules in ``backend/app/refactor/csharp_analyzer.py`` and the
multi-language scanner. The goal is that every injected instance is
actually detectable by the existing refactor engine.
"""
from __future__ import annotations

import random


CSHARP_PATTERNS = [
    # Classic string concatenation with +
    '            string query = "SELECT * FROM {table} WHERE id = " + {var};\n'
    '            var cmd = new SqlCommand(query, conn);\n'
    "            cmd.ExecuteReader();\n",
    # String interpolation
    '            string query = $"SELECT * FROM {table} WHERE user_id = {{{var}}}";\n'
    '            cmd.CommandText = query;\n'
    "            cmd.ExecuteNonQuery();\n",
    # String.Format
    '            var sql = String.Format("SELECT name, email FROM {table} WHERE ref = \'{{0}}\'", {var});\n'
    '            cmd.CommandText = sql;\n'
    "            var reader = cmd.ExecuteReader();\n",
    # Direct CommandText concatenation
    '            cmd.CommandText = "UPDATE {table} SET status = \'active\' WHERE id = " + {var};\n'
    "            cmd.ExecuteNonQuery();\n",
]


PYTHON_PATTERNS = [
    # f-string injection
    '    query = f"SELECT * FROM {table} WHERE id = {{{var}}}"\n'
    "    cursor.execute(query)\n"
    "    rows = cursor.fetchall()\n",
    # % formatting
    '    query = "SELECT * FROM {table} WHERE name = \'%s\'" % {var}\n'
    "    cursor.execute(query)\n",
    # String concatenation
    '    sql = "DELETE FROM {table} WHERE ref = \'" + str({var}) + "\'"\n'
    "    cursor.execute(sql)\n",
    # .format() method
    '    q = "SELECT count(*) FROM {table} WHERE agency = \'{{}}\'".format({var})\n'
    "    cursor.execute(q)\n",
]


class SqlInjectionInjector:
    """Produces SQL-injection code snippets on demand."""

    def __init__(self, rng: random.Random) -> None:
        self.rng = rng

    def csharp_snippet(self, table: str, var: str) -> str:
        template = self.rng.choice(CSHARP_PATTERNS)
        return template.format(table=table, var=var)

    def python_snippet(self, table: str, var: str) -> str:
        template = self.rng.choice(PYTHON_PATTERNS)
        return template.format(table=table, var=var)
