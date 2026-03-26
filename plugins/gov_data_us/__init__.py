"""gov-data-us — US Government Data plugin for NexusForge."""

from app.plugins.interface import NexusPlugin, PluginManifest
from gov_data_us.agents import DataGovAgent, SecEdgarAgent


class GovDataUsPlugin(NexusPlugin):
    """Provides connectors to US government data portals."""

    def get_manifest(self) -> PluginManifest:
        return PluginManifest(
            name="gov-data-us",
            version="1.0.0",
            description="US government data connectors (data.gov, SEC EDGAR)",
            author="NexusForge Team",
            agent_types=["data-gov", "sec-edgar"],
            connectors=["data.gov", "sec.gov/edgar"],
        )

    def register(self, agent_registry, connector_registry=None):
        """Register US government data agents."""
        agent_registry("data-gov", DataGovAgent())
        agent_registry("sec-edgar", SecEdgarAgent())


# The loader expects a module-level `plugin` attribute
plugin = GovDataUsPlugin()
