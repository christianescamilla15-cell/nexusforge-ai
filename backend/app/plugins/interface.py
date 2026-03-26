"""Plugin contract — all NexusForge plugins must implement NexusPlugin."""

from abc import ABC, abstractmethod
from dataclasses import dataclass, field


@dataclass
class PluginManifest:
    """Metadata describing a plugin's capabilities."""
    name: str
    version: str
    description: str
    author: str
    agent_types: list[str] = field(default_factory=list)   # agents this plugin provides
    connectors: list[str] = field(default_factory=list)     # data connectors it adds


class NexusPlugin(ABC):
    """Abstract base class for all NexusForge plugins."""

    @abstractmethod
    def get_manifest(self) -> PluginManifest:
        """Return the plugin manifest with metadata."""
        pass

    @abstractmethod
    def register(self, agent_registry, connector_registry=None):
        """Called when plugin is loaded. Register agents/connectors."""
        pass
