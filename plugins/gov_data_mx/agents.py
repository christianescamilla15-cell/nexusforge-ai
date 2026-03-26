"""Agent implementations for the gov-data-mx plugin."""

from app.agents.base import BaseAgent, AgentResult


class DatosAbiertoAgent(BaseAgent):
    """Fetches data from datos.gob.mx — Mexico's open data portal.

    Runs in demo mode by default, returning sample procurement data.
    """

    name = "DatosAbiertoAgent"
    agent_type = "datos-abierto"
    description = "Retrieves datasets from datos.gob.mx (Mexico open data portal)"

    async def execute(self, input_data: dict, config: dict = None) -> AgentResult:
        query = input_data.get("query", "presupuesto federal")
        # Demo mode — return realistic sample data
        sample_records = [
            {
                "id": "DA-2026-001",
                "titulo": "Presupuesto de Egresos de la Federación 2026",
                "organismo": "SHCP",
                "fecha_publicacion": "2025-12-15",
                "formato": "CSV",
                "url": "https://datos.gob.mx/busca/dataset/pef-2026",
            },
            {
                "id": "DA-2026-002",
                "titulo": "Gasto Público por Dependencia Q1 2026",
                "organismo": "SHCP",
                "fecha_publicacion": "2026-04-01",
                "formato": "JSON",
                "url": "https://datos.gob.mx/busca/dataset/gasto-q1-2026",
            },
            {
                "id": "DA-2026-003",
                "titulo": "Indicadores de Gestión Pública",
                "organismo": "SFP",
                "fecha_publicacion": "2026-02-28",
                "formato": "CSV",
                "url": "https://datos.gob.mx/busca/dataset/indicadores-gestion",
            },
        ]

        return AgentResult(
            output={
                "source": "datos.gob.mx",
                "query": query,
                "mode": "demo",
                "total_results": len(sample_records),
                "records": sample_records,
            },
            tokens_used=0,
            cost_usd=0.0,
            provider="gov-data-mx",
            model="demo",
        )


class CompranetAgent(BaseAgent):
    """Fetches procurement data from CompraNet portal.

    Runs in demo mode by default, returning sample procurement records.
    """

    name = "CompranetAgent"
    agent_type = "compranet"
    description = "Retrieves procurement data from CompraNet (government procurement portal)"

    async def execute(self, input_data: dict, config: dict = None) -> AgentResult:
        query = input_data.get("query", "licitaciones tecnología")
        sample_records = [
            {
                "expediente": "LA-006000001-E1-2026",
                "descripcion": "Servicios de infraestructura en la nube",
                "dependencia": "Secretaría de la Función Pública",
                "monto_estimado": 15_000_000.00,
                "moneda": "MXN",
                "tipo_contratacion": "Licitación Pública",
                "estado": "En evaluación",
                "fecha_apertura": "2026-03-01",
            },
            {
                "expediente": "LA-006000002-E3-2026",
                "descripcion": "Desarrollo de plataforma de datos abiertos",
                "dependencia": "INAI",
                "monto_estimado": 8_500_000.00,
                "moneda": "MXN",
                "tipo_contratacion": "Licitación Pública",
                "estado": "Publicada",
                "fecha_apertura": "2026-03-15",
            },
        ]

        return AgentResult(
            output={
                "source": "compranet.hacienda.gob.mx",
                "query": query,
                "mode": "demo",
                "total_results": len(sample_records),
                "records": sample_records,
            },
            tokens_used=0,
            cost_usd=0.0,
            provider="gov-data-mx",
            model="demo",
        )
