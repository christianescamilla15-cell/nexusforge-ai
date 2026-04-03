"""Base connector interface."""
from abc import ABC, abstractmethod


class ConnectorResult:
    """Standard result object returned by all connector operations."""

    def __init__(self, status="success", data=None, error=None, count=0):
        self.status = status
        self.data = data or {}
        self.error = error
        self.count = count

    def to_dict(self) -> dict:
        return {
            "status": self.status,
            "data": self.data,
            "error": self.error,
            "count": self.count,
        }


class ConnectorBase(ABC):
    """Abstract base class for all connectors."""

    connector_type: str = "unknown"
    name: str = "Unknown Connector"
    description: str = ""
    icon: str = "🔌"
    config_schema: dict = {"fields": []}

    def info(self) -> dict:
        """Return metadata about this connector type."""
        return {
            "type": self.connector_type,
            "name": self.name,
            "description": self.description,
            "icon": self.icon,
            "config_schema": self.config_schema,
        }

    @abstractmethod
    async def test_connection(self, config: dict) -> dict:
        """Validate config and test connectivity. Returns {ok, message}."""
        pass

    @abstractmethod
    async def fetch(self, config: dict, params: dict = None) -> dict:
        """Fetch data from the external service. Returns ConnectorResult dict."""
        pass

    @abstractmethod
    async def push(self, config: dict, data: dict) -> dict:
        """Push data to the external service. Returns ConnectorResult dict."""
        pass
