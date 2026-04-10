"""C# / .NET Analyzer — deep analysis for ASP.NET, .NET Framework, and .NET Core projects.

Purpose-built for enterprise-scale legacy systems:
- Transaction reconciliation services (C# ASP.NET/IIS + managed MySQL)
- Batch sales management (C# .NET/IIS + SQL Server)
- Document batch ingestion (.NET/IIS + SQL Server)
- Commission engines (C# + Cobol + Java + multi-DB)

Detects:
  1. SQL injection (string concatenation in queries)
  2. Hardcoded credentials (connection strings, passwords, API keys)
  3. God classes (cyclomatic complexity > 20)
  4. Insecure deserialization (BinaryFormatter, etc.)
  5. Missing auth on controllers/endpoints
  6. Exception info leaks (stack traces in responses)
  7. Obsolete crypto (MD5, SHA1, DES)
  8. BusinessLayer.Shared dependency tracking
"""

import logging
import re
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

logger = logging.getLogger(__name__)


@dataclass
class CSharpFinding:
    severity: str       # critical, high, medium, low
    category: str       # sql_injection, hardcoded_cred, god_class, insecure_deser, missing_auth, info_leak, weak_crypto, shared_dep
    title: str
    description: str
    file_path: str
    line_number: int = 0
    code_snippet: str = ""
    fix_suggestion: str = ""


@dataclass
class CSharpClass:
    name: str
    file_path: str
    namespace: str = ""
    base_class: str = ""
    interfaces: list[str] = field(default_factory=list)
    methods: list[dict] = field(default_factory=list)
    properties: list[str] = field(default_factory=list)
    lines: int = 0
    complexity: int = 0     # Estimated cyclomatic complexity
    is_controller: bool = False
    is_service: bool = False


@dataclass
class CSharpProject:
    name: str
    path: str
    framework: str = ""     # net6.0, net48, netstandard2.0, etc.
    project_type: str = ""  # web, console, library, winservice
    classes: list[CSharpClass] = field(default_factory=list)
    findings: list[CSharpFinding] = field(default_factory=list)
    dependencies: list[str] = field(default_factory=list)  # NuGet packages
    shared_refs: list[str] = field(default_factory=list)   # Project references
    total_files: int = 0
    total_lines: int = 0

    def to_dict(self) -> dict:
        return {
            "name": self.name,
            "framework": self.framework,
            "project_type": self.project_type,
            "total_files": self.total_files,
            "total_lines": self.total_lines,
            "classes": len(self.classes),
            "god_classes": [c.name for c in self.classes if c.complexity > 20],
            "controllers": [c.name for c in self.classes if c.is_controller],
            "dependencies": self.dependencies[:20],
            "shared_refs": self.shared_refs,
            "findings_count": len(self.findings),
            "findings_by_severity": self._count_by("severity"),
            "findings_by_category": self._count_by("category"),
            "findings": [
                {
                    "severity": f.severity,
                    "category": f.category,
                    "title": f.title,
                    "file": f.file_path,
                    "line": f.line_number,
                    "fix": f.fix_suggestion,
                }
                for f in sorted(self.findings, key=lambda x: {"critical": 0, "high": 1, "medium": 2, "low": 3}.get(x.severity, 4))
            ],
        }

    def _count_by(self, attr):
        counts = {}
        for f in self.findings:
            val = getattr(f, attr)
            counts[val] = counts.get(val, 0) + 1
        return counts


# ── SQL Injection Patterns ──────────────────────────────────────────────────

_SQL_INJECTION_PATTERNS = [
    # String concatenation in SQL
    (r'"(SELECT|INSERT|UPDATE|DELETE)\s+[^"]*"\s*\+\s*', "SQL injection via string concatenation"),
    (r'\$"(SELECT|INSERT|UPDATE|DELETE)\s+', "SQL injection via string interpolation"),
    (r'string\.Format\(\s*"(SELECT|INSERT|UPDATE|DELETE)', "SQL injection via String.Format"),
    # SqlCommand with concatenated query
    (r'new\s+SqlCommand\(\s*"[^"]*"\s*\+', "SQL injection in SqlCommand constructor"),
    (r'\.CommandText\s*=\s*"[^"]*"\s*\+', "SQL injection in CommandText assignment"),
    (r'\.CommandText\s*=\s*\$"', "SQL injection in CommandText interpolation"),
    # ExecuteReader/NonQuery with concatenated string
    (r'Execute(?:Reader|NonQuery|Scalar)\(\s*"[^"]*"\s*\+', "SQL injection in Execute call"),
]

# ── Credential Patterns ─────────────────────────────────────────────────────

_CREDENTIAL_PATTERNS = [
    (r'(?:password|pwd|passwd)\s*=\s*"[^"]{3,}"', "Hardcoded password"),
    (r'(?:connectionstring|connstring|connection_string)\s*=\s*"[^"]*(?:Password|pwd)=[^"]*"', "Hardcoded connection string with password"),
    (r'Server\s*=\s*[^;]+;\s*.*Password\s*=\s*[^;"]+', "SQL Server connection with embedded password"),
    (r'(?:api_?key|apikey|secret_?key|secretkey)\s*=\s*"[^"]{8,}"', "Hardcoded API key"),
    (r'(?:smtp|mail).*(?:password|pwd)\s*=\s*"[^"]{3,}"', "Hardcoded SMTP password"),
    (r'JWT_SECRET\s*=\s*"[^"]{5,}"', "Hardcoded JWT secret"),
    (r'new\s+NetworkCredential\(\s*"[^"]+"\s*,\s*"[^"]+"', "Hardcoded NetworkCredential"),
]

# ── Weak Crypto Patterns ────────────────────────────────────────────────────

_WEAK_CRYPTO = [
    (r'MD5\.Create\(\)|new\s+MD5CryptoServiceProvider', "Weak hash: MD5"),
    (r'SHA1\.Create\(\)|new\s+SHA1CryptoServiceProvider', "Weak hash: SHA1"),
    (r'new\s+DESCryptoServiceProvider', "Weak cipher: DES"),
    (r'new\s+TripleDESCryptoServiceProvider', "Weak cipher: 3DES"),
    (r'new\s+RC2CryptoServiceProvider', "Weak cipher: RC2"),
]

# ── Insecure Deserialization ────────────────────────────────────────────────

_INSECURE_DESER = [
    (r'BinaryFormatter', "Insecure deserialization: BinaryFormatter (RCE risk)"),
    (r'JavaScriptSerializer', "Insecure deserialization: JavaScriptSerializer"),
    (r'TypeNameHandling\s*=\s*TypeNameHandling\.All', "Insecure JSON deserialization: TypeNameHandling.All"),
    (r'XmlSerializer.*typeof\(object\)', "Insecure XML deserialization"),
]

# ── Info Leak Patterns ──────────────────────────────────────────────────────

_INFO_LEAK = [
    (r'Exception\.ToString\(\)|ex\.ToString\(\)|exc\.ToString\(\)', "Stack trace exposed to client"),
    (r'ex\.StackTrace|exc\.StackTrace', "StackTrace exposed"),
    (r'ex\.Message|exc\.Message', "Exception message exposed (may leak internals)"),
    (r'customErrors\s*mode\s*=\s*"Off"', "Custom errors disabled — stack traces in production"),
    (r'<compilation\s+debug\s*=\s*"true"', "Debug compilation enabled"),
]


class CSharpAnalyzer:
    """Analyze C# / .NET projects for vulnerabilities and architectural issues."""

    def __init__(self, project_root: str):
        self.root = Path(project_root)

    async def analyze(self) -> list[CSharpProject]:
        """Analyze all .csproj projects in the repository."""
        projects = []

        # Find all .csproj files
        csproj_files = list(self.root.rglob("*.csproj"))
        if not csproj_files:
            # No project files — scan .cs files directly
            proj = await self._analyze_loose_files()
            if proj:
                projects.append(proj)
            return projects

        for csproj in csproj_files:
            proj = await self._analyze_project(csproj)
            projects.append(proj)

        return projects

    async def _analyze_project(self, csproj_path: Path) -> CSharpProject:
        """Analyze a single .csproj and its source files."""
        proj_dir = csproj_path.parent
        proj_name = csproj_path.stem

        project = CSharpProject(
            name=proj_name,
            path=str(proj_dir.relative_to(self.root)),
        )

        # Parse .csproj for framework, dependencies, references
        try:
            csproj_content = csproj_path.read_text(encoding="utf-8", errors="ignore")
            project.framework = self._detect_framework(csproj_content)
            project.project_type = self._detect_project_type(csproj_content, proj_name)
            project.dependencies = self._extract_nuget_packages(csproj_content)
            project.shared_refs = self._extract_project_references(csproj_content)
        except Exception:
            pass

        # Scan all .cs files
        cs_files = list(proj_dir.rglob("*.cs"))
        project.total_files = len(cs_files)

        for cs_file in cs_files:
            if any(skip in str(cs_file) for skip in ["bin/", "obj/", "Migrations/"]):
                continue
            self._analyze_cs_file(cs_file, project)

        return project

    async def _analyze_loose_files(self) -> CSharpProject | None:
        """Analyze .cs files without a .csproj."""
        cs_files = list(self.root.rglob("*.cs"))
        cs_files = [f for f in cs_files if "bin/" not in str(f) and "obj/" not in str(f)]
        if not cs_files:
            return None

        project = CSharpProject(name=self.root.name, path=".", total_files=len(cs_files))
        for cs_file in cs_files:
            self._analyze_cs_file(cs_file, project)
        return project

    def _analyze_cs_file(self, file_path: Path, project: CSharpProject):
        """Analyze a single .cs file for vulnerabilities and class structure."""
        try:
            content = file_path.read_text(encoding="utf-8", errors="ignore")
            rel = str(file_path.relative_to(self.root))
            lines = content.splitlines()
            project.total_lines += len(lines)

            # Extract classes
            for cls in self._extract_classes(content, rel):
                project.classes.append(cls)

            # Scan for vulnerabilities
            for line_num, line in enumerate(lines, 1):
                # SQL injection
                for pattern, desc in _SQL_INJECTION_PATTERNS:
                    if re.search(pattern, line, re.IGNORECASE):
                        project.findings.append(CSharpFinding(
                            severity="critical",
                            category="sql_injection",
                            title=desc,
                            description=f"Use SqlParameter or parameterized queries instead",
                            file_path=rel,
                            line_number=line_num,
                            code_snippet=line.strip()[:120],
                            fix_suggestion="Replace with: cmd.Parameters.AddWithValue(\"@param\", value)",
                        ))

                # Credentials
                for pattern, desc in _CREDENTIAL_PATTERNS:
                    if re.search(pattern, line, re.IGNORECASE):
                        if "example" in line.lower() or "placeholder" in line.lower():
                            continue
                        project.findings.append(CSharpFinding(
                            severity="critical",
                            category="hardcoded_cred",
                            title=desc,
                            description="Move to appsettings.json, environment variables, or AWS Secrets Manager",
                            file_path=rel,
                            line_number=line_num,
                            code_snippet=line.strip()[:80] + "...",
                            fix_suggestion="Use: Configuration[\"ConnectionStrings:Default\"] or Environment.GetEnvironmentVariable()",
                        ))

                # Weak crypto
                for pattern, desc in _WEAK_CRYPTO:
                    if re.search(pattern, line):
                        project.findings.append(CSharpFinding(
                            severity="high",
                            category="weak_crypto",
                            title=desc,
                            description="Use SHA256, SHA512, or AES-256-GCM instead",
                            file_path=rel,
                            line_number=line_num,
                            fix_suggestion="Replace with SHA256.Create() or Aes.Create()",
                        ))

                # Insecure deserialization
                for pattern, desc in _INSECURE_DESER:
                    if re.search(pattern, line):
                        project.findings.append(CSharpFinding(
                            severity="critical",
                            category="insecure_deser",
                            title=desc,
                            description="BinaryFormatter allows arbitrary code execution",
                            file_path=rel,
                            line_number=line_num,
                            fix_suggestion="Use System.Text.Json or Newtonsoft.Json with safe settings",
                        ))

                # Info leaks
                for pattern, desc in _INFO_LEAK:
                    if re.search(pattern, line):
                        project.findings.append(CSharpFinding(
                            severity="medium",
                            category="info_leak",
                            title=desc,
                            description="Internal details exposed to clients",
                            file_path=rel,
                            line_number=line_num,
                            fix_suggestion="Return generic error; log details server-side",
                        ))

            # Check controller auth
            self._check_controller_auth(content, rel, project)

        except Exception as exc:
            logger.warning("Failed to analyze %s: %s", file_path, exc)

    def _extract_classes(self, content: str, file_path: str) -> list[CSharpClass]:
        """Extract class definitions with complexity estimation."""
        classes = []
        for m in re.finditer(
            r'(?:public|internal|private|protected)\s+(?:abstract\s+|static\s+|sealed\s+|partial\s+)*class\s+(\w+)'
            r'(?:\s*:\s*([^\{]+))?',
            content
        ):
            name = m.group(1)
            inheritance = m.group(2) or ""

            # Parse base class and interfaces
            base_class = ""
            interfaces = []
            if inheritance:
                parts = [p.strip() for p in inheritance.split(",")]
                for p in parts:
                    if p.startswith("I") and p[1:2].isupper():
                        interfaces.append(p)
                    elif not base_class:
                        base_class = p

            # Count methods
            methods = []
            for mm in re.finditer(
                r'(?:public|private|protected|internal)\s+(?:async\s+)?(?:static\s+)?(?:virtual\s+)?(?:override\s+)?'
                r'(\w[\w<>\[\]?]*)\s+(\w+)\s*\(([^)]*)\)',
                content
            ):
                methods.append({
                    "return_type": mm.group(1),
                    "name": mm.group(2),
                    "params": len([p for p in mm.group(3).split(",") if p.strip()]),
                })

            # Estimate complexity (branches = if/else/switch/for/while/catch/&&/||)
            branch_keywords = len(re.findall(
                r'\b(?:if|else|switch|case|for|foreach|while|do|catch|&&|\|\|)\b',
                content
            ))
            complexity = max(1, branch_keywords)

            # Detect if controller or service
            is_controller = "Controller" in name or "ApiController" in (base_class + " ".join(interfaces))
            is_service = "Service" in name or "Repository" in name

            lines = content.count("\n") + 1

            classes.append(CSharpClass(
                name=name,
                file_path=file_path,
                namespace=self._extract_namespace(content),
                base_class=base_class,
                interfaces=interfaces,
                methods=methods,
                lines=lines,
                complexity=complexity,
                is_controller=is_controller,
                is_service=is_service,
            ))
        return classes

    def _check_controller_auth(self, content: str, file_path: str, project: CSharpProject):
        """Check if controllers have [Authorize] attribute."""
        # Find controller classes
        controller_match = re.search(r'class\s+(\w+Controller)', content)
        if not controller_match:
            return

        controller_name = controller_match.group(1)

        # Check for [Authorize] at class level
        class_pos = controller_match.start()
        preceding = content[max(0, class_pos - 200):class_pos]

        if "[Authorize" not in preceding and "[AllowAnonymous" not in preceding:
            # Check if individual actions have [Authorize]
            action_count = len(re.findall(r'\[Http(?:Get|Post|Put|Delete|Patch)\]', content))
            auth_count = content.count("[Authorize")

            if action_count > 0 and auth_count == 0:
                project.findings.append(CSharpFinding(
                    severity="high",
                    category="missing_auth",
                    title=f"Controller {controller_name} has no [Authorize] attribute",
                    description=f"{action_count} endpoints without authentication",
                    file_path=file_path,
                    fix_suggestion="Add [Authorize] at class level or per-action",
                ))

    def _detect_framework(self, csproj: str) -> str:
        m = re.search(r'<TargetFramework>([\w.]+)</TargetFramework>', csproj)
        return m.group(1) if m else "unknown"

    def _detect_project_type(self, csproj: str, name: str) -> str:
        if "Microsoft.NET.Sdk.Web" in csproj:
            return "web"
        if "Exe" in csproj:
            return "console"
        if "WinExe" in csproj:
            return "winservice"
        if "Library" in csproj or "lib" in name.lower():
            return "library"
        return "unknown"

    def _extract_nuget_packages(self, csproj: str) -> list[str]:
        return re.findall(r'<PackageReference\s+Include="([^"]+)"', csproj)

    def _extract_project_references(self, csproj: str) -> list[str]:
        refs = re.findall(r'<ProjectReference\s+Include="([^"]+)"', csproj)
        return [Path(r).stem for r in refs]

    def _extract_namespace(self, content: str) -> str:
        m = re.search(r'namespace\s+([\w.]+)', content)
        return m.group(1) if m else ""
