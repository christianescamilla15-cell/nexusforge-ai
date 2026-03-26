"""Dynamic plugin loader — discovers and loads NexusForge plugins."""

import importlib
import importlib.util
import logging
import os
import sys
from pathlib import Path

from app.plugins.interface import NexusPlugin, PluginManifest
from app.agents.registry import register_agent

logger = logging.getLogger(__name__)

# Internal registry of loaded plugins
_loaded_plugins: dict[str, NexusPlugin] = {}


def load_plugin(plugin_path: str | Path) -> PluginManifest | None:
    """Import a plugin module from *plugin_path* and call register().

    The path should point to a directory containing an ``__init__.py`` that
    exposes a ``plugin`` attribute (an instance of :class:`NexusPlugin`).

    Returns the plugin manifest on success, ``None`` on failure.
    """
    plugin_path = Path(plugin_path).resolve()

    if not plugin_path.is_dir():
        logger.warning("Plugin path is not a directory: %s", plugin_path)
        return None

    init_file = plugin_path / "__init__.py"
    if not init_file.exists():
        logger.warning("No __init__.py found in plugin: %s", plugin_path)
        return None

    module_name = f"nexusforge_plugin_{plugin_path.name}"

    try:
        spec = importlib.util.spec_from_file_location(module_name, str(init_file))
        if spec is None or spec.loader is None:
            logger.error("Could not create module spec for %s", plugin_path)
            return None

        # Ensure the plugin directory's parent is on sys.path so relative
        # imports inside the plugin (e.g. `from .agents import ...`) work.
        parent_dir = str(plugin_path.parent)
        if parent_dir not in sys.path:
            sys.path.insert(0, parent_dir)

        module = importlib.util.module_from_spec(spec)
        sys.modules[module_name] = module
        spec.loader.exec_module(module)

        plugin_instance: NexusPlugin = getattr(module, "plugin", None)
        if plugin_instance is None:
            logger.warning("Plugin %s has no 'plugin' attribute", plugin_path.name)
            return None

        manifest = plugin_instance.get_manifest()

        # Register agents/connectors provided by the plugin
        plugin_instance.register(agent_registry=register_agent)

        _loaded_plugins[manifest.name] = plugin_instance
        logger.info(
            "Loaded plugin '%s' v%s — agents: %s, connectors: %s",
            manifest.name,
            manifest.version,
            manifest.agent_types,
            manifest.connectors,
        )
        return manifest

    except Exception:
        logger.exception("Failed to load plugin from %s", plugin_path)
        return None


def load_all_plugins(plugins_dir: str | Path) -> list[PluginManifest]:
    """Scan *plugins_dir* for subdirectories and load each as a plugin."""
    plugins_dir = Path(plugins_dir).resolve()
    manifests: list[PluginManifest] = []

    if not plugins_dir.is_dir():
        logger.warning("Plugins directory does not exist: %s", plugins_dir)
        return manifests

    for entry in sorted(plugins_dir.iterdir()):
        if entry.is_dir() and (entry / "__init__.py").exists():
            manifest = load_plugin(entry)
            if manifest:
                manifests.append(manifest)

    logger.info("Loaded %d plugin(s) from %s", len(manifests), plugins_dir)
    return manifests


def list_plugins() -> list[dict]:
    """Return all loaded plugin manifests as serialisable dicts."""
    results = []
    for name, plugin_instance in _loaded_plugins.items():
        m = plugin_instance.get_manifest()
        results.append({
            "name": m.name,
            "version": m.version,
            "description": m.description,
            "author": m.author,
            "agent_types": m.agent_types,
            "connectors": m.connectors,
        })
    return results
