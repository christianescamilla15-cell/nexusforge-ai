# NexusForge CLI — `nxf`

Standalone command-line tool for interacting with the NexusForge AI platform.
Zero external dependencies — uses only Python 3.11+ standard library.

## Setup

```bash
# Make it executable (Linux/macOS)
chmod +x cli/nxf.py

# Or run directly
python cli/nxf.py <command>

# Optional: create an alias
alias nxf="python $(pwd)/cli/nxf.py"
```

## Commands

| Command | Description |
|---|---|
| `nxf health` | Check system health (DB, Redis, agents) |
| `nxf agents list` | List all registered agents |
| `nxf agents info <type>` | Get details for a specific agent |
| `nxf workflows list` | List all workflows |
| `nxf workflows create <file.json>` | Create a workflow from JSON definition |
| `nxf workflows run <id>` | Trigger workflow execution |
| `nxf runs list` | List recent execution runs |
| `nxf runs detail <id>` | Get detailed run information |
| `nxf swarms list` | List available swarm topologies |
| `nxf swarms execute` | Execute a swarm (interactive or with flags) |
| `nxf docs upload <file>` | Upload a document for RAG ingestion |
| `nxf docs search <query>` | Semantic search across documents |
| `nxf plugins list` | List loaded plugins |

## Options

```
--api URL    Override the API base URL (default: http://localhost:8000/api)
```

## Examples

```bash
# Check if the platform is running
nxf health

# List all agents including plugin-provided ones
nxf agents list

# Create and run a workflow
nxf workflows create my-pipeline.json
nxf workflows run abc12345

# Execute a debate swarm
nxf swarms execute --topology debate --task "Analyze market trends" --agents researcher,analyst,writer

# Upload and search documents
nxf docs upload report.pdf
nxf docs search "quarterly revenue projections"

# View loaded plugins
nxf plugins list
```
