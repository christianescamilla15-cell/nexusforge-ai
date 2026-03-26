"""gov-data-mx — Mexico Government Open Data plugin for NexusForge."""

from app.plugins.interface import NexusPlugin, PluginManifest
from gov_data_mx.agents import DatosAbiertoAgent, CompranetAgent


class GovDataMxPlugin(NexusPlugin):
    """Provides connectors to Mexican government open data portals."""

    def get_manifest(self) -> PluginManifest:
        return PluginManifest(
            name="gov-data-mx",
            version="1.0.0",
            description="Mexico government open data connectors (datos.gob.mx, CompraNet)",
            author="NexusForge Team",
            agent_types=["datos-abierto", "compranet"],
            connectors=["datos.gob.mx", "compranet.hacienda.gob.mx"],
        )

    def register(self, agent_registry, connector_registry=None):
        """Register Mexican government data agents."""
        agent_registry("datos-abierto", DatosAbiertoAgent())
        agent_registry("compranet", CompranetAgent())


# The loader expects a module-level `plugin` attribute
plugin = GovDataMxPlugin()
