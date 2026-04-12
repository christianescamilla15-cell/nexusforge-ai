"""Strangler UI-over-legacy scaffolder — Gap L.

Generates the skeleton for the "modern UI on top of legacy backend"
pattern discovered in the corpus analysis (H-116, H-022, H-080):

  platform-vendor builds Python/Flask/React UIs that talk to the
  mainframe COBOL core via thin API wrappers. They never rewrite
  the core — they wrap it and present a modern face.

This is complementary to the strangler-pattern planner (Gap 3, in
``strangler_planner.py``): Gap 3 decomposes a monolith for
incremental replacement, while Gap L generates the scaffolding for
the "wrap, don't rewrite" path where the legacy stays but the UX
is modernized.

Output: a directory tree with:
  - ``frontend/`` — React + Vite 5 skeleton with API client stubs
  - ``backend/`` — Flask/FastAPI thin wrapper that proxies to legacy
  - ``adapter/`` — interface definition for the legacy system
  - ``README.md`` — explains the architecture and how to extend
  - ``docker-compose.yml`` — local dev environment

The generated code is intentionally minimal — the point is the
architecture pattern, not a production-ready implementation.
"""
from __future__ import annotations

import logging
from dataclasses import dataclass, field
from pathlib import Path

logger = logging.getLogger(__name__)


@dataclass
class StranglerUIConfig:
    """Configuration for generating a strangler UI scaffold."""

    app_codename: str               # e.g., "app-03-special"
    app_label: str = ""             # human-readable label
    legacy_stack: str = "cobol"     # "cobol" | "dotnet" | "java" | "custom"
    legacy_protocol: str = "rest"   # "rest" | "soap" | "database" | "file-exchange"
    frontend_framework: str = "react"   # "react" | "vue" (React default per corpus)
    backend_framework: str = "flask"    # "flask" | "fastapi" (Flask per corpus, FastAPI for new)
    legacy_endpoints: list[str] = field(default_factory=list)  # known endpoints to wrap


@dataclass
class StranglerUIReport:
    """Report of what was generated."""

    app_codename: str
    files_generated: int = 0
    output_path: Path | None = None
    architecture: str = ""  # narrative description


def generate_strangler_ui(
    config: StranglerUIConfig,
    output_dir: Path,
) -> StranglerUIReport:
    """Generate a strangler UI scaffold under ``output_dir/<codename>/``.

    The scaffold follows the pattern observed in the discovery corpus:
    a modern frontend (React) talks to a thin backend (Flask/FastAPI)
    that in turn proxies requests to the legacy system via an adapter
    layer. The adapter abstracts the legacy protocol so the frontend
    and backend never need to know whether the legacy is COBOL, .NET,
    Java, or something else.

    Returns a ``StranglerUIReport`` with metrics.
    """
    app_dir = output_dir / config.app_codename
    app_dir.mkdir(parents=True, exist_ok=True)

    files = 0

    # ── Adapter layer (the abstraction over legacy)
    adapter_dir = app_dir / "adapter"
    adapter_dir.mkdir(exist_ok=True)

    (adapter_dir / "__init__.py").write_text(
        '"""Adapter layer — abstracts the legacy system protocol."""\n',
        encoding="utf-8",
    )
    files += 1

    (adapter_dir / "legacy_client.py").write_text(
        f'"""Client for the legacy {config.legacy_stack} system.\n\n'
        f'Protocol: {config.legacy_protocol}\n'
        f'Stack: {config.legacy_stack}\n\n'
        f'This module is the ONLY place that knows how to talk to the\n'
        f'legacy system. The backend and frontend never import from here\n'
        f'directly — they go through the service layer.\n\n'
        f'TODO: implement the actual calls to the legacy endpoints.\n'
        f'Known endpoints to wrap:\n'
        + "".join(f"  - {ep}\n" for ep in config.legacy_endpoints)
        + '"""\n\n'
        'from abc import ABC, abstractmethod\n'
        'from typing import Any\n\n\n'
        'class LegacyClient(ABC):\n'
        '    """Abstract interface for the legacy system."""\n\n'
        '    @abstractmethod\n'
        '    def query(self, operation: str, params: dict) -> Any:\n'
        '        """Execute a query against the legacy system."""\n'
        '        ...\n\n'
        '    @abstractmethod\n'
        '    def health_check(self) -> bool:\n'
        '        """Return True if the legacy system is reachable."""\n'
        '        ...\n\n\n'
        f'class {config.legacy_stack.title()}LegacyClient(LegacyClient):\n'
        f'    """Concrete client for the {config.legacy_stack} legacy backend.\n\n'
        f'    Protocol: {config.legacy_protocol}\n'
        f'    """\n\n'
        '    def __init__(self, base_url: str = "http://legacy-host:8080"):\n'
        '        self.base_url = base_url\n\n'
        '    def query(self, operation: str, params: dict) -> Any:\n'
        '        # TODO: implement actual legacy call\n'
        f'        raise NotImplementedError("Wire to {config.legacy_stack} system")\n\n'
        '    def health_check(self) -> bool:\n'
        '        # TODO: implement actual health check\n'
        '        return False\n',
        encoding="utf-8",
    )
    files += 1

    # ── Backend (thin wrapper)
    backend_dir = app_dir / "backend"
    backend_dir.mkdir(exist_ok=True)

    if config.backend_framework == "flask":
        (backend_dir / "app.py").write_text(
            f'"""Thin Flask backend for {config.app_label or config.app_codename}.\n\n'
            f'Proxies requests from the React frontend to the legacy\n'
            f'{config.legacy_stack} system via the adapter layer.\n'
            f'"""\n'
            'from flask import Flask, jsonify, request\n\n'
            'app = Flask(__name__)\n\n\n'
            '@app.route("/api/health")\n'
            'def health():\n'
            '    return jsonify({"status": "ok", "legacy": "not-connected"})\n\n\n'
            '@app.route("/api/query", methods=["POST"])\n'
            'def query():\n'
            '    """Proxy a query to the legacy system."""\n'
            '    body = request.get_json(force=True)\n'
            '    operation = body.get("operation", "")\n'
            '    params = body.get("params", {})\n'
            '    # TODO: wire to adapter/legacy_client.py\n'
            '    return jsonify({"error": "not implemented", "operation": operation}), 501\n\n\n'
            'if __name__ == "__main__":\n'
            '    app.run(debug=True, port=5000)\n',
            encoding="utf-8",
        )
    else:
        (backend_dir / "app.py").write_text(
            f'"""Thin FastAPI backend for {config.app_label or config.app_codename}.\n\n'
            f'Proxies requests from the React frontend to the legacy\n'
            f'{config.legacy_stack} system via the adapter layer.\n'
            f'"""\n'
            'from fastapi import FastAPI\n'
            'from pydantic import BaseModel\n\n'
            'app = FastAPI()\n\n\n'
            'class QueryRequest(BaseModel):\n'
            '    operation: str\n'
            '    params: dict = {}\n\n\n'
            '@app.get("/api/health")\n'
            'def health():\n'
            '    return {"status": "ok", "legacy": "not-connected"}\n\n\n'
            '@app.post("/api/query")\n'
            'def query(body: QueryRequest):\n'
            '    # TODO: wire to adapter/legacy_client.py\n'
            '    return {"error": "not implemented", "operation": body.operation}\n',
            encoding="utf-8",
        )
    files += 1

    (backend_dir / "requirements.txt").write_text(
        f'{config.backend_framework}\n'
        'requests\n'
        'python-dotenv\n',
        encoding="utf-8",
    )
    files += 1

    # ── Frontend (React skeleton)
    frontend_dir = app_dir / "frontend" / "src"
    frontend_dir.mkdir(parents=True, exist_ok=True)

    (app_dir / "frontend" / "package.json").write_text(
        '{\n'
        f'  "name": "{config.app_codename}-ui",\n'
        '  "version": "0.1.0",\n'
        '  "scripts": {\n'
        '    "dev": "vite",\n'
        '    "build": "vite build"\n'
        '  },\n'
        '  "dependencies": {\n'
        '    "react": "^18.3.0",\n'
        '    "react-dom": "^18.3.0"\n'
        '  },\n'
        '  "devDependencies": {\n'
        '    "vite": "^5.0.0",\n'
        '    "@vitejs/plugin-react": "^4.0.0"\n'
        '  }\n'
        '}\n',
        encoding="utf-8",
    )
    files += 1

    (frontend_dir / "App.jsx").write_text(
        f'/**\n'
        f' * {config.app_label or config.app_codename} — Modern UI over legacy.\n'
        f' * \n'
        f' * This React app communicates with the Flask/FastAPI backend\n'
        f' * which proxies to the legacy {config.legacy_stack} system.\n'
        f' */\n'
        'import { useState } from "react";\n\n'
        'const API_BASE = import.meta.env.VITE_API_URL || "http://localhost:5000";\n\n'
        'export default function App() {\n'
        '  const [result, setResult] = useState(null);\n'
        '  const [loading, setLoading] = useState(false);\n\n'
        '  async function queryLegacy(operation) {\n'
        '    setLoading(true);\n'
        '    try {\n'
        '      const res = await fetch(`${API_BASE}/api/query`, {\n'
        '        method: "POST",\n'
        '        headers: { "Content-Type": "application/json" },\n'
        '        body: JSON.stringify({ operation, params: {} }),\n'
        '      });\n'
        '      setResult(await res.json());\n'
        '    } catch (err) {\n'
        '      setResult({ error: err.message });\n'
        '    } finally {\n'
        '      setLoading(false);\n'
        '    }\n'
        '  }\n\n'
        '  return (\n'
        '    <div>\n'
        f'      <h1>{config.app_label or config.app_codename}</h1>\n'
        '      <p>Modern UI over legacy system</p>\n'
        '      <button onClick={() => queryLegacy("test")} disabled={loading}>\n'
        '        {loading ? "Loading..." : "Test Legacy Query"}\n'
        '      </button>\n'
        '      {result && <pre>{JSON.stringify(result, null, 2)}</pre>}\n'
        '    </div>\n'
        '  );\n'
        '}\n',
        encoding="utf-8",
    )
    files += 1

    # ── Docker compose for local dev
    (app_dir / "docker-compose.yml").write_text(
        f'# {config.app_label or config.app_codename} — local dev environment\n'
        '#\n'
        '# Pattern: strangler UI over legacy\n'
        f'# Legacy: {config.legacy_stack} ({config.legacy_protocol})\n'
        f'# Frontend: {config.frontend_framework}\n'
        f'# Backend: {config.backend_framework}\n\n'
        'services:\n'
        '  backend:\n'
        '    build: ./backend\n'
        '    ports:\n'
        '      - "5000:5000"\n'
        '    environment:\n'
        '      - LEGACY_HOST=legacy\n'
        '      - LEGACY_PORT=8080\n\n'
        '  frontend:\n'
        '    build: ./frontend\n'
        '    ports:\n'
        '      - "3000:3000"\n'
        '    environment:\n'
        '      - VITE_API_URL=http://localhost:5000\n\n'
        '  # Uncomment when you have a legacy system stub:\n'
        '  # legacy:\n'
        '  #   image: legacy-stub:latest\n'
        '  #   ports:\n'
        '  #     - "8080:8080"\n',
        encoding="utf-8",
    )
    files += 1

    # ── README
    label = config.app_label or config.app_codename
    (app_dir / "README.md").write_text(
        f'# {label} — Strangler UI over legacy\n\n'
        f'**Pattern**: modern UI wrapping a legacy {config.legacy_stack} backend\n'
        f'**Frontend**: {config.frontend_framework} + Vite 5\n'
        f'**Backend**: {config.backend_framework} (thin proxy)\n'
        f'**Legacy protocol**: {config.legacy_protocol}\n\n'
        '## Architecture\n\n'
        '```\n'
        f'┌──────────────┐     ┌──────────────┐     ┌───────────────────┐\n'
        f'│   React UI   │────▶│ Flask/FastAPI │────▶│ Legacy {config.legacy_stack.upper():<9s} │\n'
        f'│   (modern)   │     │   (proxy)     │     │ (unchanged core)  │\n'
        f'└──────────────┘     └──────────────┘     └───────────────────┘\n'
        '```\n\n'
        'The legacy system is **never rewritten** — only wrapped. The adapter\n'
        'layer (`adapter/legacy_client.py`) abstracts the legacy protocol so\n'
        'the frontend and backend never need to know implementation details.\n\n'
        '## Quick start\n\n'
        '```bash\n'
        'docker compose up -d\n'
        '# Frontend: http://localhost:3000\n'
        '# Backend:  http://localhost:5000/api/health\n'
        '```\n\n'
        '## How to extend\n\n'
        '1. Add legacy endpoints to `adapter/legacy_client.py`\n'
        '2. Add proxy routes to `backend/app.py`\n'
        '3. Add UI pages to `frontend/src/`\n\n'
        '_Auto-generated by NexusForge strangler UI scaffolder (Gap L)._\n',
        encoding="utf-8",
    )
    files += 1

    architecture = (
        f"Strangler UI pattern: {config.frontend_framework} frontend → "
        f"{config.backend_framework} proxy → {config.legacy_stack} legacy "
        f"({config.legacy_protocol}). {files} files generated."
    )

    logger.info(
        "Generated strangler UI scaffold for %s: %d files at %s",
        config.app_codename, files, app_dir,
    )

    return StranglerUIReport(
        app_codename=config.app_codename,
        files_generated=files,
        output_path=app_dir,
        architecture=architecture,
    )
