"""C# / .NET Framework 4.6.1 era code generator.

Produces a synthetic legacy C# app layout with controllers, repositories,
models and a Web.config. Intentionally uses .NET Framework idioms (no
async/await, no DI container, string-concatenation queries, suppressed
exceptions, hardcoded credentials) so the refactor engine picks up the
expected CWE findings.

The generator is deterministic: given the same RNG seed, it produces
identical output.
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
    SuppressedExceptionInjector,
    WeakCryptoInjector,
)


FILE_HEADER = """// ---------------------------------------------------------------------------
// {module} — generated synthetic legacy module
// Framework: .NET Framework 4.6.1
// Intentionally non-idiomatic: string-concat queries, suppressed exceptions,
// hardcoded credentials. Used for NexusForge remediation showcase only.
// ---------------------------------------------------------------------------
using System;
using System.Collections.Generic;
using System.Data.SqlClient;
using System.Security.Cryptography;
using System.Text;
using System.Web.Http;

namespace {ns}
{{
"""


CONTROLLER_TEMPLATE = """    public class {name}Controller : ApiController
    {{
{creds}

        [HttpGet]
        public IHttpActionResult Get(int id)
        {{
            try
            {{
                using (var conn = new SqlConnection(ConnectionString))
                {{
                    conn.Open();
                    var cmd = new SqlCommand("", conn);
{sql_body}
                }}
                return Ok();
            }}
            catch (Exception) {{ }}
            return InternalServerError();
        }}

        [HttpPost]
        public IHttpActionResult Post(string input)
        {{
{crypto_body}
{pii_log}
            return Ok();
        }}
    }}

"""


REPOSITORY_TEMPLATE = """    public class {name}Repository
    {{
{creds}

        public List<dynamic> Find(string filter)
        {{
            var results = new List<dynamic>();
            using (var conn = new SqlConnection(ConnectionString))
            {{
                conn.Open();
                var cmd = new SqlCommand("", conn);
{sql_body}
            }}
            return results;
        }}

        public void Update(int id, string value)
        {{
            try
            {{
                using (var conn = new SqlConnection(ConnectionString))
                {{
                    conn.Open();
                    var cmd = new SqlCommand("", conn);
{sql_body2}
                }}
            }}
{suppressed}
        }}
    }}

"""


MODEL_TEMPLATE = """    public class {name}Model
    {{
        public int Id {{ get; set; }}
{fields}
    }}

"""


FILE_FOOTER = "}\n"


WEB_CONFIG = """<?xml version="1.0" encoding="utf-8"?>
<configuration>
  <appSettings>
{settings}
  </appSettings>
  <connectionStrings>
    <add name="DefaultConnection" connectionString="Data Source=db-prod;Initial Catalog=AppDb;User ID=sa;Password=synth-fake-webcfg;" providerName="System.Data.SqlClient"/>
  </connectionStrings>
</configuration>
"""


@dataclass
class CSharpGenerator:
    app: AppRecipe
    rng: random.Random

    def __post_init__(self) -> None:
        self.sql_inj = SqlInjectionInjector(self.rng)
        self.creds = HardcodedCredsInjector(self.rng)
        self.crypto = WeakCryptoInjector(self.rng)
        self.exc = SuppressedExceptionInjector(self.rng)
        self.pii = PiiLeakInjector(self.rng)
        # Counters for remaining budget from the recipe
        self._sql_budget = self.app.vulnerabilities.sql_injection
        self._creds_budget = self.app.vulnerabilities.hardcoded_creds
        self._crypto_budget = self.app.vulnerabilities.weak_crypto
        self._pii_budget = self.app.vulnerabilities.pii_leak
        self._exc_budget = self.app.vulnerabilities.suppressed_exceptions

    def _ns(self) -> str:
        # Generic namespace, no client hints
        slug = self.app.codename.replace("-", "")
        return f"{slug.capitalize()}.LegacyCore"

    def _sql_snippet(self, table: str, var: str) -> str:
        if self._sql_budget <= 0:
            return '                // (no query in this module)\n'
        self._sql_budget -= 1
        return "                " + self.sql_inj.csharp_snippet(table, var).strip("\n") + "\n"

    def _creds_block(self) -> str:
        lines: list[str] = []
        take = min(2, self._creds_budget)
        for _ in range(take):
            lines.append("        " + self.creds.csharp_line())
            self._creds_budget -= 1
        if not lines:
            lines.append('        private static readonly string ConnectionString = System.Configuration.ConfigurationManager.ConnectionStrings["DefaultConnection"].ConnectionString;')
        return "\n".join(lines)

    def _crypto_line(self) -> str:
        if self._crypto_budget <= 0:
            return "            // (no crypto ops)"
        self._crypto_budget -= 1
        return self.crypto.csharp_line()

    def _pii_line(self) -> str:
        if self._pii_budget <= 0:
            return "            // (no pii logging)"
        self._pii_budget -= 1
        return self.pii.csharp_line()

    def _suppressed(self) -> str:
        if self._exc_budget <= 0:
            return "            catch (Exception ex) { throw; }"
        self._exc_budget -= 1
        return "            catch (Exception) { /* suppressed */ }"

    def _generate_controller_file(self, module_name: str) -> str:
        ns = self._ns()
        return (
            FILE_HEADER.format(module=f"{module_name}Controller", ns=ns)
            + CONTROLLER_TEMPLATE.format(
                name=module_name,
                creds=self._creds_block(),
                sql_body=self._sql_snippet(f"{module_name.lower()}_entries", "id"),
                crypto_body="            " + self._crypto_line(),
                pii_log="            " + self._pii_line(),
            )
            + FILE_FOOTER
        )

    def _generate_repository_file(self, module_name: str) -> str:
        ns = self._ns()
        return (
            FILE_HEADER.format(module=f"{module_name}Repository", ns=ns)
            + REPOSITORY_TEMPLATE.format(
                name=module_name,
                creds=self._creds_block(),
                sql_body=self._sql_snippet(f"{module_name.lower()}_records", "filter"),
                sql_body2=self._sql_snippet(f"{module_name.lower()}_records", "id"),
                suppressed=self._suppressed(),
            )
            + FILE_FOOTER
        )

    def _generate_model_file(self, module_name: str) -> str:
        ns = self._ns()
        fields = "\n".join(
            f"        public string {f} {{ get; set; }}"
            for f in ("Name", "CreatedAt", "Status", "Amount", "Reference")
        )
        return (
            FILE_HEADER.format(module=f"{module_name}Model", ns=ns)
            + MODEL_TEMPLATE.format(name=module_name, fields=fields)
            + FILE_FOOTER
        )

    def generate(self, out_dir: Path) -> list[Path]:
        """Write the generated files and return the list of created paths."""
        out_dir.mkdir(parents=True, exist_ok=True)
        (out_dir / "Controllers").mkdir(exist_ok=True)
        (out_dir / "Repositories").mkdir(exist_ok=True)
        (out_dir / "Models").mkdir(exist_ok=True)

        created: list[Path] = []
        for i in range(self.app.modules):
            module_name = f"Module{i:02d}"

            controller_path = out_dir / "Controllers" / f"{module_name}Controller.cs"
            repo_path = out_dir / "Repositories" / f"{module_name}Repository.cs"
            model_path = out_dir / "Models" / f"{module_name}Model.cs"

            controller_path.write_text(
                self._generate_controller_file(module_name), encoding="utf-8"
            )
            repo_path.write_text(
                self._generate_repository_file(module_name), encoding="utf-8"
            )
            model_path.write_text(
                self._generate_model_file(module_name), encoding="utf-8"
            )
            created.extend([controller_path, repo_path, model_path])

        # Drain any remaining SQLi / creds budget into a single "god class" file
        # so the triage engine sees the shared-module coupling signal.
        if self._sql_budget > 0 or self._creds_budget > 0:
            god_content = self._generate_god_class()
            god_path = out_dir / "Shared" / "LegacyBusinessLayer.cs"
            god_path.parent.mkdir(exist_ok=True)
            god_path.write_text(god_content, encoding="utf-8")
            created.append(god_path)

        # Web.config with hardcoded config credentials
        cfg_settings = []
        take = min(5, self._creds_budget)
        for _ in range(take):
            cfg_settings.append("    " + self.creds.config_line())
            self._creds_budget -= 1
        if not cfg_settings:
            cfg_settings.append('    <add key="Environment" value="production" />')
        cfg_path = out_dir / "Web.config"
        cfg_path.write_text(
            WEB_CONFIG.format(settings="\n".join(cfg_settings)), encoding="utf-8"
        )
        created.append(cfg_path)

        return created

    def _generate_god_class(self) -> str:
        """Fat class that drains the remaining SQLi budget in one place."""
        ns = self._ns()
        lines: list[str] = [
            FILE_HEADER.format(module="LegacyBusinessLayer", ns=ns),
            f"    public class LegacyBusinessLayer  // god-class signal for triage\n",
            "    {\n",
            "        private readonly string ConnectionString = \"Server=db-prod;User=sa;Password=synth-fake-shared;\";\n\n",
        ]
        method_idx = 0
        while self._sql_budget > 0:
            method_idx += 1
            lines.append(f"        public void DoWork{method_idx:04d}(string input)\n")
            lines.append("        {\n")
            lines.append(
                "            using (var conn = new SqlConnection(ConnectionString)) { conn.Open();\n"
            )
            lines.append("            var cmd = new SqlCommand(\"\", conn);\n")
            # Drain up to 3 SQLi per method to keep files readable
            for _ in range(min(3, self._sql_budget)):
                lines.append(
                    "            "
                    + self.sql_inj.csharp_snippet("business_layer", "input").strip("\n")
                    + "\n"
                )
                self._sql_budget -= 1
                if self._sql_budget <= 0:
                    break
            lines.append("            }\n")
            lines.append("        }\n\n")
            if method_idx > 2000:  # safety cap
                break
        lines.append("    }\n")
        lines.append(FILE_FOOTER)
        return "".join(lines)
