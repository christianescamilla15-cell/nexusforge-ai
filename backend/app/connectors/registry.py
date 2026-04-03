"""Connector registry — single source of truth for all available connectors."""
from typing import Dict, Type

from .base import ConnectorBase
from .gmail import GmailConnector
from .slack import SlackConnector
from .notion import NotionConnector
from .drive import DriveConnector
from .rest import RestConnector
from .postgres_ext import PostgresExtConnector

# All registered connector classes
_CONNECTOR_CLASSES: Dict[str, Type[ConnectorBase]] = {}


def _register(cls: Type[ConnectorBase]) -> None:
    _CONNECTOR_CLASSES[cls.connector_type] = cls


# Register built-in connectors
_register(GmailConnector)
_register(SlackConnector)
_register(NotionConnector)
_register(DriveConnector)
_register(RestConnector)
_register(PostgresExtConnector)


def get_connector(connector_type: str) -> ConnectorBase:
    """Instantiate and return a connector by type."""
    cls = _CONNECTOR_CLASSES.get(connector_type)
    if not cls:
        raise KeyError(f"Unknown connector type: {connector_type}")
    return cls()


def list_connector_types() -> list:
    """Return metadata for all registered connector types."""
    return [cls().info() for cls in _CONNECTOR_CLASSES.values()]


def register_connector(cls: Type[ConnectorBase]) -> None:
    """Register a custom connector at runtime."""
    _register(cls)
