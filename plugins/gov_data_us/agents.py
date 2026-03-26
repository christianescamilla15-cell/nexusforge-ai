"""Agent implementations for the gov-data-us plugin."""

from app.agents.base import BaseAgent, AgentResult


class DataGovAgent(BaseAgent):
    """Fetches datasets from data.gov — the US federal open data portal.

    Runs in demo mode by default, returning sample datasets.
    """

    name = "DataGovAgent"
    agent_type = "data-gov"
    description = "Retrieves datasets from data.gov (US federal open data portal)"

    async def execute(self, input_data: dict, config: dict = None) -> AgentResult:
        query = input_data.get("query", "federal spending")
        sample_records = [
            {
                "id": "DG-2026-001",
                "title": "Federal Budget Expenditures FY2026",
                "agency": "Department of the Treasury",
                "published": "2025-10-01",
                "format": "CSV",
                "url": "https://catalog.data.gov/dataset/federal-budget-fy2026",
            },
            {
                "id": "DG-2026-002",
                "title": "USAspending Award Data Q1 2026",
                "agency": "Department of the Treasury",
                "published": "2026-01-15",
                "format": "JSON",
                "url": "https://catalog.data.gov/dataset/usaspending-q1-2026",
            },
            {
                "id": "DG-2026-003",
                "title": "Federal IT Dashboard — Agency Spending",
                "agency": "Office of Management and Budget",
                "published": "2026-02-01",
                "format": "CSV",
                "url": "https://catalog.data.gov/dataset/it-dashboard-2026",
            },
        ]

        return AgentResult(
            output={
                "source": "data.gov",
                "query": query,
                "mode": "demo",
                "total_results": len(sample_records),
                "records": sample_records,
            },
            tokens_used=0,
            cost_usd=0.0,
            provider="gov-data-us",
            model="demo",
        )


class SecEdgarAgent(BaseAgent):
    """Fetches SEC EDGAR filing data.

    Runs in demo mode by default, returning sample filing records.
    """

    name = "SecEdgarAgent"
    agent_type = "sec-edgar"
    description = "Retrieves SEC EDGAR filings (10-K, 10-Q, 8-K) for public companies"

    async def execute(self, input_data: dict, config: dict = None) -> AgentResult:
        query = input_data.get("query", "AAPL 10-K")
        company = input_data.get("company", "Apple Inc.")
        sample_records = [
            {
                "accession": "0000320193-26-000012",
                "company": company,
                "cik": "0000320193",
                "form_type": "10-K",
                "filed": "2025-11-01",
                "period": "2025-09-30",
                "url": "https://www.sec.gov/cgi-bin/browse-edgar?action=getcompany&CIK=0000320193",
            },
            {
                "accession": "0000320193-26-000045",
                "company": company,
                "cik": "0000320193",
                "form_type": "10-Q",
                "filed": "2026-02-01",
                "period": "2025-12-31",
                "url": "https://www.sec.gov/cgi-bin/browse-edgar?action=getcompany&CIK=0000320193",
            },
            {
                "accession": "0000320193-26-000078",
                "company": company,
                "cik": "0000320193",
                "form_type": "8-K",
                "filed": "2026-03-10",
                "period": "2026-03-10",
                "url": "https://www.sec.gov/cgi-bin/browse-edgar?action=getcompany&CIK=0000320193",
            },
        ]

        return AgentResult(
            output={
                "source": "sec.gov/edgar",
                "query": query,
                "company": company,
                "mode": "demo",
                "total_results": len(sample_records),
                "filings": sample_records,
            },
            tokens_used=0,
            cost_usd=0.0,
            provider="gov-data-us",
            model="demo",
        )
