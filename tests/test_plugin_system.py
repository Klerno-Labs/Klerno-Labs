"""Tests for plugin system functionality."""

from typing import Never

import pytest
from fastapi import FastAPI

from app.plugin_system import BasePlugin, PluginHook, PluginManager, PluginMetadata


class ExamplePlugin(BasePlugin):
    """Example plugin implementation (renamed to avoid pytest collection warning)."""

    def get_metadata(self) -> PluginMetadata:
        return PluginMetadata(
            name="TestPlugin",
            version="1.0.0",
            description="Test plugin for unit tests",
            author="Test Author",
            tags=["test"],
        )

    def initialize(self, app: FastAPI, plugin_manager: PluginManager) -> None:
        self.initialized = True
        # Register a test hook
        plugin_manager.hooks["test_hook"].register(self.test_callback)

    def test_callback(self, data):
        return {"plugin": "TestPlugin", "data": data}


def test_plugin_hook_creation() -> None:
    """Test PluginHook creation and execution."""
    hook = PluginHook("test_hook", "Test hook description")

    assert hook.name == "test_hook"
    assert hook.description == "Test hook description"
    assert len(hook.callbacks) == 0

    # Register a callback

    def test_callback(data) -> str:
        return f"processed: {data}"

    hook.register(test_callback)
    assert len(hook.callbacks) == 1

    # Execute hook
    results = hook.execute("test_data")
    assert len(results) == 1
    assert results[0] == "processed: test_data"


def test_plugin_manager_initialization() -> None:
    """Test PluginManager initialization."""
    app = FastAPI()
    pm = PluginManager(app)

    # Should have core hooks initialized
    assert "transaction_analyzed" in pm.hooks
    assert "risk_calculated" in pm.hooks
    assert "alert_generated" in pm.hooks
    assert "dashboard_data" in pm.hooks

    # Should have empty plugins dict
    assert len(pm.plugins) == 0


def test_plugin_registration() -> None:
    """Test plugin registration."""
    app = FastAPI()
    pm = PluginManager(app)

    # Add test hook
    pm.hooks["test_hook"] = PluginHook("test_hook", "Test hook")

    # Register example plugin
    success = pm.register_plugin(ExamplePlugin)
    assert success is True

    # Plugin should be registered
    assert "TestPlugin" in pm.plugins
    assert pm.plugins["TestPlugin"].initialized is True

    # Duplicate registration should fail
    success = pm.register_plugin(ExamplePlugin)
    assert success is False


def test_plugin_hook_execution() -> None:
    """Test plugin hook execution through manager."""
    app = FastAPI()
    pm = PluginManager(app)

    # Add test hook
    pm.hooks["test_hook"] = PluginHook("test_hook", "Test hook")

    # Register example plugin
    pm.register_plugin(ExamplePlugin)

    # Execute hook
    results = pm.execute_hook("test_hook", "test_data")
    assert len(results) == 1
    assert results[0]["plugin"] == "TestPlugin"
    assert results[0]["data"] == "test_data"


def test_plugin_info() -> None:
    """Test getting plugin information."""
    app = FastAPI()
    pm = PluginManager(app)

    # Add test hook
    pm.hooks["test_hook"] = PluginHook("test_hook", "Test hook")

    # Register example plugin
    pm.register_plugin(ExamplePlugin)

    # Get plugin info
    info = pm.get_plugin_info("TestPlugin")
    assert info is not None
    assert info["metadata"]["name"] == "TestPlugin"
    assert info["metadata"]["version"] == "1.0.0"
    assert info["status"] == "active"

    # Non - existent plugin
    info = pm.get_plugin_info("NonExistentPlugin")
    assert info is None


def test_plugin_list() -> None:
    """Test listing all plugins."""
    app = FastAPI()
    pm = PluginManager(app)

    # Add test hook
    pm.hooks["test_hook"] = PluginHook("test_hook", "Test hook")

    # No plugins initially
    plugins = pm.list_plugins()
    assert len(plugins) == 0

    # Register example plugin
    pm.register_plugin(ExamplePlugin)

    # Should have one plugin
    plugins = pm.list_plugins()
    assert len(plugins) == 1
    assert plugins[0]["name"] == "TestPlugin"


def test_plugin_data_storage() -> None:
    """Test plugin data storage and retrieval."""
    app = FastAPI()
    pm = PluginManager(app)

    # Set plugin data
    pm.set_plugin_data("TestPlugin", "setting1", "value1")
    pm.set_plugin_data("TestPlugin", "setting2", {"nested": "data"})

    # Get plugin data
    value1 = pm.get_plugin_data("TestPlugin", "setting1")
    assert value1 == "value1"

    value2 = pm.get_plugin_data("TestPlugin", "setting2")
    assert value2 == {"nested": "data"}

    # Get non - existent data with default
    value3 = pm.get_plugin_data("TestPlugin", "setting3", "default")
    assert value3 == "default"


def test_hook_error_handling() -> None:
    """Test hook execution with errors."""
    hook = PluginHook("error_hook", "Hook that might error")

    def good_callback(data) -> str:
        return "good"

    def bad_callback(data) -> Never:
        msg = "Test error"
        raise Exception(msg)

    hook.register(good_callback)
    hook.register(bad_callback)

    # Should still execute good callback despite error in bad callback
    results = hook.execute("test")
    assert len(results) == 1
    assert results[0] == "good"


if __name__ == "__main__":
    pytest.main([__file__])
