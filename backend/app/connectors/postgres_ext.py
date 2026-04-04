"""External PostgreSQL connector — query and write to remote databases."""
import logging
import re
from datetime import datetime, timezone

from .base import ConnectorBase, ConnectorResult

logger = logging.getLogger(__name__)


class PostgresExtConnector(ConnectorBase):
    connector_type = "postgres"
    name = "PostgreSQL (External)"
    description = "Connect to external PostgreSQL databases — run queries and insert records"
    icon = "🐘"
    _IDENTIFIER_RE = re.compile(r'^[a-zA-Z_][a-zA-Z0-9_]*$')

    @classmethod
    def _validate_identifier(cls, name: str, label: str = "identifier") -> str:
        """Validate that a name is a safe SQL identifier (no injection)."""
        if not name or not cls._IDENTIFIER_RE.match(name):
            raise ValueError(f"Invalid {label}: '{name}'. Only letters, digits, and underscores are allowed.")
        return name

    config_schema = {
        "fields": [
            {"key": "host", "label": "Host", "type": "text",
             "placeholder": "db.example.com", "required": True},
            {"key": "port", "label": "Port", "type": "number",
             "placeholder": "5432", "required": False},
            {"key": "database", "label": "Database Name", "type": "text",
             "placeholder": "mydb", "required": True},
            {"key": "user", "label": "Username", "type": "text",
             "placeholder": "postgres", "required": True},
            {"key": "password", "label": "Password", "type": "password",
             "placeholder": "••••••••", "required": True},
            {"key": "ssl", "label": "Require SSL", "type": "boolean",
             "placeholder": "true", "required": False},
            {"key": "default_schema", "label": "Default Schema", "type": "text",
             "placeholder": "public", "required": False},
        ]
    }

    def _dsn(self, config: dict) -> str:
        host = config.get("host", "localhost")
        port = config.get("port", 5432)
        database = config.get("database", "postgres")
        user = config.get("user", "postgres")
        password = config.get("password", "")
        ssl = config.get("ssl", False)
        dsn = f"postgresql://{user}:{password}@{host}:{port}/{database}"
        if ssl:
            dsn += "?sslmode=require"
        return dsn

    async def test_connection(self, config: dict) -> dict:
        host = config.get("host", "")
        database = config.get("database", "")
        user = config.get("user", "")

        if not host:
            return {"ok": False, "message": "Missing 'host'"}
        if not database:
            return {"ok": False, "message": "Missing 'database'"}
        if not user:
            return {"ok": False, "message": "Missing 'user'"}

        try:
            import asyncpg
            dsn = self._dsn(config)
            conn = await asyncpg.connect(dsn, timeout=10)
            version = await conn.fetchval("SELECT version()")
            await conn.close()
            short_ver = version.split(",")[0] if version else "unknown"
            return {"ok": True, "message": f"Connected to {short_ver}"}
        except ImportError:
            return {"ok": True, "message": "Config valid (asyncpg not installed — demo mode)"}
        except Exception as e:
            return {"ok": False, "message": f"Connection failed: {str(e)[:200]}"}

    async def fetch(self, config: dict, params: dict = None) -> dict:
        params = params or {}
        query = params.get("query", "")
        table = params.get("table", "")
        limit = params.get("limit", 100)
        schema = params.get("schema") or config.get("default_schema", "public")

        if not query and not table:
            return ConnectorResult(status="error", error="Provide 'query' (SQL) or 'table' name").to_dict()

        # Validate identifiers to prevent SQL injection
        try:
            self._validate_identifier(schema, "schema")
            if table:
                self._validate_identifier(table, "table")
        except ValueError as e:
            return ConnectorResult(status="error", error=str(e)).to_dict()

        # Build query from table if no raw query
        if not query:
            query = f'SELECT * FROM "{schema}"."{table}" LIMIT {limit}'

        # Block semicolons to prevent multi-statement injection
        if ";" in query:
            return ConnectorResult(
                status="error",
                error="Semicolons are not allowed in queries (multi-statement execution is blocked)",
            ).to_dict()

        # Safety: block destructive statements
        normalized = query.strip().upper()
        for forbidden in ("DROP", "DELETE", "TRUNCATE", "ALTER", "UPDATE", "INSERT"):
            if normalized.startswith(forbidden):
                return ConnectorResult(
                    status="error",
                    error=f"Fetch only allows SELECT queries — '{forbidden}' is not permitted",
                ).to_dict()

        try:
            import asyncpg
            dsn = self._dsn(config)
            conn = await asyncpg.connect(dsn, timeout=10)
            try:
                # Run in a read-only transaction for safety
                await conn.execute("SET TRANSACTION READ ONLY")
                rows = await conn.fetch(query)
                records = [dict(r) for r in rows]
                # Serialize non-JSON types
                for record in records:
                    for k, v in record.items():
                        if isinstance(v, (datetime,)):
                            record[k] = v.isoformat()
                        elif not isinstance(v, (str, int, float, bool, type(None), list, dict)):
                            record[k] = str(v)
                return ConnectorResult(
                    status="success",
                    data={"records": records, "query": query},
                    count=len(records),
                ).to_dict()
            finally:
                await conn.close()
        except ImportError:
            pass
        except Exception as e:
            return ConnectorResult(status="error", error=f"Query failed: {str(e)[:300]}").to_dict()

        # Demo mode
        now = datetime.now(timezone.utc).isoformat()
        demo_records = [
            {"id": 1, "name": "Alpha Project", "status": "active", "created_at": now},
            {"id": 2, "name": "Beta Pipeline", "status": "completed", "created_at": now},
            {"id": 3, "name": "Gamma Service", "status": "active", "created_at": now},
        ]
        return ConnectorResult(
            status="success",
            data={"records": demo_records[:limit], "query": query, "mode": "demo"},
            count=min(len(demo_records), limit),
        ).to_dict()

    async def push(self, config: dict, data: dict) -> dict:
        table = data.get("table", "")
        records = data.get("records", [])
        schema = data.get("schema") or config.get("default_schema", "public")

        if not table:
            return ConnectorResult(status="error", error="'table' field is required").to_dict()
        if not records:
            return ConnectorResult(status="error", error="'records' must be a non-empty list of objects").to_dict()

        # Validate identifiers to prevent SQL injection
        try:
            self._validate_identifier(schema, "schema")
            self._validate_identifier(table, "table")
        except ValueError as e:
            return ConnectorResult(status="error", error=str(e)).to_dict()

        # Build INSERT from first record's keys
        columns = list(records[0].keys())
        # Validate column names
        for col in columns:
            try:
                self._validate_identifier(col, "column")
            except ValueError as e:
                return ConnectorResult(status="error", error=str(e)).to_dict()
        col_str = ", ".join(f'"{c}"' for c in columns)
        placeholders = ", ".join(f"${i+1}" for i in range(len(columns)))
        insert_sql = f'INSERT INTO "{schema}"."{table}" ({col_str}) VALUES ({placeholders})'

        try:
            import asyncpg
            dsn = self._dsn(config)
            conn = await asyncpg.connect(dsn, timeout=10)
            try:
                inserted = 0
                for record in records:
                    values = [record.get(c) for c in columns]
                    await conn.execute(insert_sql, *values)
                    inserted += 1
                return ConnectorResult(
                    status="success",
                    data={"table": f"{schema}.{table}", "inserted": inserted},
                    count=inserted,
                ).to_dict()
            finally:
                await conn.close()
        except ImportError:
            pass
        except Exception as e:
            return ConnectorResult(status="error", error=f"Insert failed: {str(e)[:300]}").to_dict()

        # Demo mode
        return ConnectorResult(
            status="success",
            data={
                "table": f"{schema}.{table}",
                "inserted": len(records),
                "mode": "demo",
                "note": "Insert simulated — configure asyncpg and valid credentials for real writes",
            },
            count=len(records),
        ).to_dict()
