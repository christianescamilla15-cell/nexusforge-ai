"""Tests for the plugin system (Session 3)."""

import pytest
from app.plugins.interface import PluginManifest, NexusPlugin
from app.plugins.loader import list_plugins


class TestPluginManifest:
    """PluginManifest dataclass tests."""

    def test_manifest_has_required_fields(self):
        m = PluginManifest(
            name="test-plugin",
            version="1.0.0",
            description="A test plugin",
            author="Test Author",
        )
        assert m.name == "test-plugin"
        assert m.version == "1.0.0"
        assert m.description == "A test plugin"
        assert m.author == "Test Author"

    def test_manifest_defaults(self):
        m = PluginManifest(name="p", version="0.1", description="d", author="a")
        assert m.agent_types == []
        assert m.connectors == []

    def test_manifest_with_agents_and_connectors(self):
        m = PluginManifest(
            name="rich-plugin",
            version="2.0.0",
            description="Plugin with agents",
            author="Team",
            agent_types=["custom_agent"],
            connectors=["api.example.com"],
        )
        assert m.agent_types == ["custom_agent"]
        assert m.connectors == ["api.example.com"]


class TestNexusPluginAbstract:
    """NexusPlugin ABC cannot be instantiated directly."""

    def test_nexus_plugin_is_abstract(self):
        with pytest.raises(TypeError):
            NexusPlugin()


class TestPluginLoader:
    """Plugin loader module and list_plugins function."""

    def test_plugin_loader_module_exists(self):
        from app.plugins import loader
        assert hasattr(loader, "load_plugin")
        assert hasattr(loader, "load_all_plugins")
        assert hasattr(loader, "list_plugins")

    def test_list_plugins_returns_list(self):
        result = list_plugins()
        assert isinstance(result, list)


class TestConcretePlugin:
    """Test creating a concrete plugin implementation."""

    def test_concrete_plugin_works(self):
        class MyPlugin(NexusPlugin):
            def get_manifest(self) -> PluginManifest:
                return PluginManifest(
                    name="my-plugin",
                    version="1.0.0",
                    description="Test plugin",
                    author="Tester",
                    agent_types=["custom"],
                    connectors=["api.test.com"],
                )

            def register(self, agent_registry, connector_registry=None):
                pass

        p = MyPlugin()
        m = p.get_manifest()
        assert m.name == "my-plugin"
        assert m.agent_types == ["custom"]

    def test_gov_data_mx_manifest_shape(self):
        """Verify the gov-data-mx plugin manifest has expected structure."""
        m = PluginManifest(
            name="gov-data-mx",
            version="1.0.0",
            description="Mexico government open data connectors (datos.gob.mx, CompraNet)",
            author="NexusForge Team",
            agent_types=["datos-abierto", "compranet"],
            connectors=["datos.gob.mx", "compranet.hacienda.gob.mx"],
        )
        assert m.name == "gov-data-mx"
        assert len(m.agent_types) == 2
        assert len(m.connectors) == 2

    def test_gov_data_us_manifest_shape(self):
        """Verify a US gov data plugin manifest structure."""
        m = PluginManifest(
            name="gov-data-us",
            version="1.0.0",
            description="US government open data connectors (data.gov, USAspending)",
            author="NexusForge Team",
            agent_types=["data-gov", "usaspending"],
            connectors=["data.gov", "api.usaspending.gov"],
        )
        assert m.name == "gov-data-us"
        assert len(m.agent_types) == 2
