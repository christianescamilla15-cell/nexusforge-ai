#!/usr/bin/env python3
"""NexusForge CLI — nxf

A standalone command-line tool for interacting with the NexusForge AI platform.
No external dependencies required (uses only Python stdlib).
"""

import argparse
import json
import sys
from urllib.request import urlopen, Request
from urllib.error import URLError

API_BASE = "http://localhost:8000/api"

# ---------------------------------------------------------------------------
# ANSI colour helpers
# ---------------------------------------------------------------------------

RESET = "\033[0m"
BOLD = "\033[1m"
RED = "\033[91m"
GREEN = "\033[92m"
YELLOW = "\033[93m"
CYAN = "\033[96m"
DIM = "\033[2m"


def _supports_color() -> bool:
    """Return True if stdout likely supports ANSI colours."""
    if sys.platform == "win32":
        # Windows 10+ supports ANSI if ENABLE_VIRTUAL_TERMINAL_PROCESSING
        # is set, but also works in most modern terminals.
        try:
            import os
            return os.isatty(sys.stdout.fileno())
        except Exception:
            return False
    return hasattr(sys.stdout, "isatty") and sys.stdout.isatty()


_COLOR = _supports_color()


def c(text: str, color: str) -> str:
    """Wrap *text* in ANSI colour codes if the terminal supports it."""
    if not _COLOR:
        return text
    return f"{color}{text}{RESET}"


def header(text: str) -> str:
    return c(text, CYAN + BOLD)


def success(text: str) -> str:
    return c(text, GREEN)


def error(text: str) -> str:
    return c(text, RED)


def warn(text: str) -> str:
    return c(text, YELLOW)


def dim(text: str) -> str:
    return c(text, DIM)


# ---------------------------------------------------------------------------
# API helpers
# ---------------------------------------------------------------------------

def api_get(path: str) -> dict:
    """Perform a GET request and return parsed JSON."""
    url = f"{API_BASE}{path}"
    try:
        req = Request(url, headers={"Accept": "application/json"})
        with urlopen(req, timeout=10) as resp:
            return json.loads(resp.read().decode())
    except URLError as exc:
        print(error(f"Error: Cannot reach API at {url}"))
        print(dim(f"  {exc}"))
        sys.exit(1)
    except json.JSONDecodeError:
        print(error("Error: Invalid JSON response from API"))
        sys.exit(1)


def api_post(path: str, data: dict) -> dict:
    """Perform a POST request with JSON body and return parsed JSON."""
    url = f"{API_BASE}{path}"
    body = json.dumps(data).encode()
    try:
        req = Request(
            url,
            data=body,
            headers={"Content-Type": "application/json", "Accept": "application/json"},
            method="POST",
        )
        with urlopen(req, timeout=30) as resp:
            return json.loads(resp.read().decode())
    except URLError as exc:
        print(error(f"Error: Cannot reach API at {url}"))
        print(dim(f"  {exc}"))
        sys.exit(1)
    except json.JSONDecodeError:
        print(error("Error: Invalid JSON response from API"))
        sys.exit(1)


def api_post_file(path: str, filepath: str) -> dict:
    """Upload a file via multipart POST."""
    import mimetypes
    import os
    from urllib.request import urlopen, Request

    url = f"{API_BASE}{path}"
    filename = os.path.basename(filepath)
    content_type = mimetypes.guess_type(filepath)[0] or "application/octet-stream"
    boundary = "----NexusForgeUploadBoundary"

    with open(filepath, "rb") as f:
        file_data = f.read()

    body = (
        f"--{boundary}\r\n"
        f'Content-Disposition: form-data; name="file"; filename="{filename}"\r\n'
        f"Content-Type: {content_type}\r\n\r\n"
    ).encode() + file_data + f"\r\n--{boundary}--\r\n".encode()

    try:
        req = Request(
            url,
            data=body,
            headers={
                "Content-Type": f"multipart/form-data; boundary={boundary}",
                "Accept": "application/json",
            },
            method="POST",
        )
        with urlopen(req, timeout=60) as resp:
            return json.loads(resp.read().decode())
    except URLError as exc:
        print(error(f"Error: Cannot reach API at {url}"))
        print(dim(f"  {exc}"))
        sys.exit(1)


# ---------------------------------------------------------------------------
# Table formatting
# ---------------------------------------------------------------------------

def print_table(headers: list[str], rows: list[list[str]]):
    """Print a nicely formatted ASCII table."""
    if not rows:
        print(dim("  (no results)"))
        return

    # Calculate column widths
    widths = [len(h) for h in headers]
    for row in rows:
        for i, cell in enumerate(row):
            if i < len(widths):
                widths[i] = max(widths[i], len(str(cell)))

    # Header
    header_line = "  ".join(c(h.ljust(widths[i]), CYAN + BOLD) for i, h in enumerate(headers))
    separator = "  ".join("-" * w for w in widths)
    print(f"  {header_line}")
    print(f"  {dim(separator)}")

    # Rows
    for row in rows:
        cells = []
        for i, cell in enumerate(row):
            w = widths[i] if i < len(widths) else 20
            cells.append(str(cell).ljust(w))
        print(f"  {'  '.join(cells)}")


# ---------------------------------------------------------------------------
# Commands
# ---------------------------------------------------------------------------

def cmd_health(args):
    """Check system health."""
    print(header("\n  NexusForge AI — Health Check\n"))
    data = api_get("/health")

    status = data.get("status", "unknown")
    status_display = success(status) if status == "healthy" else warn(status)
    print(f"  Status:       {status_display}")
    print(f"  Service:      {data.get('service', 'N/A')}")

    components = data.get("components", {})
    for comp, state in components.items():
        state_display = success(state) if state == "up" else error(state)
        print(f"  {comp.capitalize():14s}{state_display}")

    print(f"  Agents:       {data.get('agent_count', 0)}")
    print()


def cmd_agents_list(args):
    """List all registered agents."""
    print(header("\n  Registered Agents\n"))
    data = api_get("/agents")

    agents = data if isinstance(data, list) else data.get("agents", [])
    if not agents:
        print(dim("  No agents registered."))
        return

    rows = []
    for agent in agents:
        if isinstance(agent, str):
            rows.append([agent, "", ""])
        else:
            rows.append([
                agent.get("type", agent.get("agent_type", "N/A")),
                agent.get("name", "N/A"),
                agent.get("description", "")[:50],
            ])

    print_table(["TYPE", "NAME", "DESCRIPTION"], rows)
    print(f"\n  Total: {len(agents)} agent(s)\n")


def cmd_agents_info(args):
    """Get details for a specific agent type."""
    print(header(f"\n  Agent Info: {args.type}\n"))
    data = api_get(f"/agents/{args.type}")
    print(f"  {json.dumps(data, indent=2)}\n")


def cmd_workflows_list(args):
    """List all workflows."""
    print(header("\n  Workflows\n"))
    data = api_get("/workflows")

    workflows = data if isinstance(data, list) else data.get("workflows", [])
    rows = []
    for wf in workflows:
        rows.append([
            str(wf.get("id", "N/A"))[:8],
            wf.get("name", "N/A"),
            str(wf.get("steps", wf.get("step_count", "?"))),
            wf.get("status", "N/A"),
        ])

    print_table(["ID", "NAME", "STEPS", "STATUS"], rows)
    print(f"\n  Total: {len(workflows)} workflow(s)\n")


def cmd_workflows_create(args):
    """Create a workflow from a JSON file."""
    try:
        with open(args.file, "r") as f:
            payload = json.load(f)
    except FileNotFoundError:
        print(error(f"Error: File not found: {args.file}"))
        sys.exit(1)
    except json.JSONDecodeError as exc:
        print(error(f"Error: Invalid JSON in {args.file}: {exc}"))
        sys.exit(1)

    print(dim(f"  Creating workflow from {args.file}..."))
    data = api_post("/workflows", payload)
    wf_id = data.get("id", "N/A")
    print(success(f"  Workflow created: {wf_id}"))
    print(f"  {json.dumps(data, indent=2)}\n")


def cmd_workflows_run(args):
    """Trigger workflow execution."""
    print(dim(f"  Triggering workflow {args.id}..."))
    data = api_post(f"/workflows/{args.id}/execute", {})
    run_id = data.get("run_id", data.get("id", "N/A"))
    print(success(f"  Execution started: run_id={run_id}"))
    print(f"  {json.dumps(data, indent=2)}\n")


def cmd_runs_list(args):
    """List recent execution runs."""
    print(header("\n  Recent Runs\n"))
    data = api_get("/executions")

    runs = data if isinstance(data, list) else data.get("runs", data.get("executions", []))
    rows = []
    for run in runs:
        rows.append([
            str(run.get("id", "N/A"))[:8],
            str(run.get("workflow_id", "N/A"))[:8],
            run.get("status", "N/A"),
            run.get("started_at", run.get("created_at", "N/A"))[:19],
        ])

    print_table(["RUN ID", "WORKFLOW", "STATUS", "STARTED"], rows)
    print(f"\n  Total: {len(runs)} run(s)\n")


def cmd_runs_detail(args):
    """Get details of a specific run."""
    print(header(f"\n  Run Details: {args.id}\n"))
    data = api_get(f"/executions/{args.id}")
    print(f"  {json.dumps(data, indent=2)}\n")


def cmd_swarms_list(args):
    """List available swarm topologies."""
    print(header("\n  Swarm Topologies\n"))
    data = api_get("/swarms")

    topologies = data if isinstance(data, list) else data.get("topologies", [])
    rows = []
    for topo in topologies:
        if isinstance(topo, str):
            rows.append([topo, ""])
        else:
            rows.append([
                topo.get("name", topo.get("topology", "N/A")),
                topo.get("description", "")[:60],
            ])

    print_table(["TOPOLOGY", "DESCRIPTION"], rows)
    print()


def cmd_swarms_execute(args):
    """Execute a swarm with the given topology."""
    topology = args.topology
    task = args.task

    if not topology:
        topology = input("  Swarm topology (e.g. sequential, parallel, debate): ").strip()
    if not task:
        task = input("  Task description: ").strip()

    if not topology or not task:
        print(error("  Error: Topology and task are required."))
        sys.exit(1)

    agents_csv = args.agents or input("  Agents (comma-separated, e.g. researcher,writer): ").strip()
    agent_types = [a.strip() for a in agents_csv.split(",") if a.strip()]

    print(dim(f"\n  Executing {topology} swarm with {len(agent_types)} agent(s)..."))

    payload = {
        "topology": topology,
        "task": task,
        "agent_types": agent_types,
    }
    data = api_post("/swarms/execute", payload)
    print(success("  Swarm execution complete.\n"))
    print(f"  {json.dumps(data, indent=2)}\n")


def cmd_docs_upload(args):
    """Upload a document for RAG ingestion."""
    import os
    if not os.path.isfile(args.file):
        print(error(f"Error: File not found: {args.file}"))
        sys.exit(1)

    print(dim(f"  Uploading {args.file}..."))
    data = api_post_file("/documents/upload", args.file)
    print(success(f"  Document uploaded successfully."))
    doc_id = data.get("id", data.get("document_id", "N/A"))
    print(f"  Document ID: {doc_id}")
    print(f"  {json.dumps(data, indent=2)}\n")


def cmd_docs_search(args):
    """Semantic search across documents."""
    query = " ".join(args.query)
    print(header(f"\n  Semantic Search: \"{query}\"\n"))

    data = api_post("/documents/search", {"query": query, "top_k": args.top_k})

    results = data.get("results", [])
    for i, result in enumerate(results, 1):
        score = result.get("score", result.get("similarity", "N/A"))
        text = result.get("text", result.get("content", ""))[:120]
        doc = result.get("document_id", result.get("source", "N/A"))
        print(f"  {c(f'#{i}', CYAN)}  score={score}  doc={doc}")
        print(f"      {dim(text)}")
        print()

    if not results:
        print(dim("  No results found."))
    print()


def cmd_plugins_list(args):
    """List loaded plugins."""
    print(header("\n  Loaded Plugins\n"))
    data = api_get("/plugins")

    plugins = data.get("plugins", [])
    rows = []
    for p in plugins:
        rows.append([
            p.get("name", "N/A"),
            p.get("version", "N/A"),
            p.get("author", "N/A"),
            ", ".join(p.get("agent_types", [])),
            p.get("description", "")[:40],
        ])

    print_table(["NAME", "VERSION", "AUTHOR", "AGENTS", "DESCRIPTION"], rows)
    print(f"\n  Total: {len(plugins)} plugin(s)\n")


# ---------------------------------------------------------------------------
# CLI entry point
# ---------------------------------------------------------------------------

def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="nxf",
        description="NexusForge AI — Command Line Interface",
        epilog="Run 'nxf <command> --help' for more information on a command.",
    )
    parser.add_argument("--api", default=API_BASE, help="API base URL (default: %(default)s)")
    subparsers = parser.add_subparsers(dest="command", help="Available commands")

    # health
    sp = subparsers.add_parser("health", help="Check system health")
    sp.set_defaults(func=cmd_health)

    # agents
    agents_parser = subparsers.add_parser("agents", help="Manage agents")
    agents_sub = agents_parser.add_subparsers(dest="agents_cmd")

    sp = agents_sub.add_parser("list", help="List all registered agents")
    sp.set_defaults(func=cmd_agents_list)

    sp = agents_sub.add_parser("info", help="Get agent details")
    sp.add_argument("type", help="Agent type identifier")
    sp.set_defaults(func=cmd_agents_info)

    # workflows
    wf_parser = subparsers.add_parser("workflows", help="Manage workflows")
    wf_sub = wf_parser.add_subparsers(dest="workflows_cmd")

    sp = wf_sub.add_parser("list", help="List all workflows")
    sp.set_defaults(func=cmd_workflows_list)

    sp = wf_sub.add_parser("create", help="Create workflow from JSON file")
    sp.add_argument("file", help="Path to workflow JSON file")
    sp.set_defaults(func=cmd_workflows_create)

    sp = wf_sub.add_parser("run", help="Trigger workflow execution")
    sp.add_argument("id", help="Workflow ID")
    sp.set_defaults(func=cmd_workflows_run)

    # runs
    runs_parser = subparsers.add_parser("runs", help="View execution runs")
    runs_sub = runs_parser.add_subparsers(dest="runs_cmd")

    sp = runs_sub.add_parser("list", help="List recent runs")
    sp.set_defaults(func=cmd_runs_list)

    sp = runs_sub.add_parser("detail", help="Get run details")
    sp.add_argument("id", help="Run ID")
    sp.set_defaults(func=cmd_runs_detail)

    # swarms
    sw_parser = subparsers.add_parser("swarms", help="Manage swarm topologies")
    sw_sub = sw_parser.add_subparsers(dest="swarms_cmd")

    sp = sw_sub.add_parser("list", help="List available topologies")
    sp.set_defaults(func=cmd_swarms_list)

    sp = sw_sub.add_parser("execute", help="Execute a swarm")
    sp.add_argument("--topology", "-t", default="", help="Swarm topology")
    sp.add_argument("--task", default="", help="Task description")
    sp.add_argument("--agents", "-a", default="", help="Comma-separated agent types")
    sp.set_defaults(func=cmd_swarms_execute)

    # docs
    docs_parser = subparsers.add_parser("docs", help="Document management & search")
    docs_sub = docs_parser.add_subparsers(dest="docs_cmd")

    sp = docs_sub.add_parser("upload", help="Upload a document")
    sp.add_argument("file", help="Path to document file")
    sp.set_defaults(func=cmd_docs_upload)

    sp = docs_sub.add_parser("search", help="Semantic search across documents")
    sp.add_argument("query", nargs="+", help="Search query")
    sp.add_argument("--top-k", type=int, default=5, help="Number of results (default: 5)")
    sp.set_defaults(func=cmd_docs_search)

    # plugins
    pl_parser = subparsers.add_parser("plugins", help="Plugin management")
    pl_sub = pl_parser.add_subparsers(dest="plugins_cmd")

    sp = pl_sub.add_parser("list", help="List loaded plugins")
    sp.set_defaults(func=cmd_plugins_list)

    return parser


def main():
    global API_BASE
    parser = build_parser()
    args = parser.parse_args()

    # Override API base if provided
    if args.api != API_BASE:
        API_BASE = args.api

    if not hasattr(args, "func"):
        parser.print_help()
        sys.exit(0)

    args.func(args)


if __name__ == "__main__":
    main()
