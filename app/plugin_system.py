"""Plugin System for Klerno Labs
Provides extensible API functionality through a plugin architecture.
"""

import importlib.util as importlib_util
import inspect
import logging
from abc import ABC, abstractmethod
from collections.abc import Callable
from pathlib import Path
from typing import Any

from fastapi import FastAPI
from pydantic import BaseModel

logger = logging.getLogger(__name__)


class PluginMetadata(BaseModel):
    """Metadata for a plugin."""

    name: str
    version: str
    description: str
    author: str
    tags: list[str] = []
    dependencies: list[str] = []
    api_version: str = "1.0"


class PluginHook:
    """Represents a hook point in the system."""

    def __init__(self, name: str, description: str = "") -> None:
        self.name = name
        self.description = description
        self.callbacks: list[Callable] = []

    def register(self, callback: Callable) -> None:
        """Register a callback for this hook."""
        self.callbacks.append(callback)

    def execute(self, *args: Any, **kwargs: Any) -> list[Any]:
        """Execute all callbacks for this hook."""
        results = []
        for callback in self.callbacks:
            try:
                result = callback(*args, **kwargs)
                results.append(result)
            except Exception as e:
                logger.exception(f"Error executing hook {self.name}: {e}")
        return results


class BasePlugin(ABC):
    """Base class for all plugins."""

    def __init__(self) -> None:
        self.metadata: PluginMetadata | None = None
        self.hooks: dict[str, PluginHook] = {}

    @abstractmethod
    def get_metadata(self) -> PluginMetadata:
        """Return plugin metadata."""

    @abstractmethod
    def initialize(self, app: FastAPI, plugin_manager: "PluginManager") -> None:
        """Initialize the plugin."""

    def register_hook(self, hook_name: str, callback: Callable) -> None:
        """Register a callback for a specific hook."""
        if hook_name in self.hooks:
            self.hooks[hook_name].register(callback)

    def add_api_route(
        self,
        app: FastAPI,
        path: str,
        endpoint: Callable,
        **kwargs: Any,
    ) -> None:
        """Helper to add API routes with plugin prefix."""
        if self.metadata is None:
            msg = "Plugin metadata not set; cannot add API route"
            raise RuntimeError(msg)

        plugin_path = f"/plugins/{self.metadata.name.lower()}{path}"
        app.add_api_route(plugin_path, endpoint, **kwargs)


class PluginManager:
    """Manages plugin lifecycle and hooks."""

    def __init__(self, app: FastAPI) -> None:
        self.app = app
        self.plugins: dict[str, BasePlugin] = {}
        self.hooks: dict[str, PluginHook] = {}
        self.plugin_data: dict[str, Any] = {}

        # Initialize core hooks
        self._initialize_core_hooks()

    def _initialize_core_hooks(self) -> None:
        """Initialize core system hooks."""
        self.hooks.update(
            {
                "transaction_analyzed": PluginHook(
                    "transaction_analyzed",
                    "Called after a transaction is analyzed",
                ),
                "risk_calculated": PluginHook(
                    "risk_calculated",
                    "Called after risk score is calculated",
                ),
                "alert_generated": PluginHook(
                    "alert_generated",
                    "Called when an alert is generated",
                ),
                "dashboard_data": PluginHook(
                    "dashboard_data",
                    "Called when dashboard data is requested",
                ),
                "api_request": PluginHook("api_request", "Called on API requests"),
                "user_login": PluginHook("user_login", "Called when user logs in"),
                "report_generated": PluginHook(
                    "report_generated",
                    "Called when a report is generated",
                ),
                "settings_changed": PluginHook(
                    "settings_changed",
                    "Called when settings are modified",
                ),
            },
        )

    def register_plugin(self, plugin_class: type) -> bool:
        """Register a plugin class."""
        try:
            plugin = plugin_class()
            metadata = plugin.get_metadata()

            if metadata.name in self.plugins:
                logger.warning(f"Plugin {metadata.name} already registered")
                return False

            plugin.metadata = metadata
            plugin.hooks = self.hooks

            # Initialize the plugin
            plugin.initialize(self.app, self)

            self.plugins[metadata.name] = plugin
            logger.info(f"Registered plugin: {metadata.name} v{metadata.version}")
            return True

        except Exception as e:
            logger.exception(f"Failed to register plugin {plugin_class.__name__}: {e}")
            return False

    def load_plugins_from_directory(self, directory: str | Path) -> None:
        """Load all plugins from a directory."""
        dir_path = Path(directory)
        if not dir_path.exists():
            logger.warning(f"Plugin directory {directory} does not exist")
            return

        for p in dir_path.iterdir():
            if p.is_file() and p.suffix == ".py" and not p.name.startswith("_"):
                self._load_plugin_file(str(p))

    def _load_plugin_file(self, filepath: str) -> None:
        """Load a plugin from a Python file."""
        try:
            spec = importlib_util.spec_from_file_location("plugin", filepath)
            if spec is None:
                msg = "Failed to create module spec for plugin"
                raise ImportError(msg)

            module = importlib_util.module_from_spec(spec)

            # Some environments provide a spec without a loader or with a
            # loader that doesn't expose exec_module. Guard against that.
            loader = getattr(spec, "loader", None)
            if loader is None or not hasattr(loader, "exec_module"):
                msg = "Plugin spec does not have a usable loader"
                raise ImportError(msg)

            exec_fn = loader.exec_module
            if not callable(exec_fn):
                msg = "Plugin loader.exec_module is not callable"
                raise ImportError(msg)

            # Execute plugin module in isolated namespace
            exec_fn(module)

            # Find plugin classes in the module
            for _name, obj in inspect.getmembers(module):
                if (
                    inspect.isclass(obj)
                    and issubclass(obj, BasePlugin)
                    and obj != BasePlugin
                ):
                    self.register_plugin(obj)

        except Exception as e:
            logger.exception(f"Failed to load plugin from {filepath}: {e}")

    def execute_hook(self, hook_name: str, *args: Any, **kwargs: Any) -> list[Any]:
        """Execute all callbacks for a hook."""
        if hook_name in self.hooks:
            return self.hooks[hook_name].execute(*args, **kwargs)
        return []

    def get_plugin_info(self, plugin_name: str) -> dict[str, Any] | None:
        """Get information about a specific plugin."""
        if plugin_name in self.plugins:
            plugin = self.plugins[plugin_name]
            # Normalize metadata to a mapping so callers always receive a dict
            metadata: dict[str, Any] | None = None
            if plugin.metadata is not None:
                try:
                    # pydantic v2+: model_dump
                    metadata = plugin.metadata.model_dump()
                except Exception:
                    try:
                        # pydantic v1: dict()
                        metadata = plugin.metadata.dict()
                    except Exception:
                        # Provide a consistent mapping fallback
                        metadata = {"info": str(plugin.metadata)}

            hooks_registered = 0
            for h in self.hooks.values():
                try:
                    callbacks = [
                        cb.__self__ for cb in h.callbacks if hasattr(cb, "__self__")
                    ]
                    if plugin in callbacks:
                        hooks_registered += 1
                except Exception:
                    continue

            return {
                "metadata": metadata,
                "status": "active",
                "hooks_registered": hooks_registered,
            }
        return None

    def list_plugins(self) -> list[dict[str, Any]]:
        """List all registered plugins."""
        out: list[dict[str, Any]] = []
        for name, plugin in self.plugins.items():
            metadata: dict[str, Any] | None = None
            if plugin.metadata is not None:
                try:
                    metadata = plugin.metadata.model_dump()
                except Exception:
                    try:
                        metadata = plugin.metadata.dict()
                    except Exception:
                        metadata = {"info": str(plugin.metadata)}

            out.append({"name": name, "metadata": metadata, "status": "active"})

        return out

    def set_plugin_data(self, plugin_name: str, key: str, value: Any) -> None:
        """Store data for a plugin."""
        if plugin_name not in self.plugin_data:
            self.plugin_data[plugin_name] = {}
        self.plugin_data[plugin_name][key] = value

    def get_plugin_data(self, plugin_name: str, key: str, default: Any = None) -> Any:
        """Get data for a plugin."""
        return self.plugin_data.get(plugin_name, {}).get(key, default)


# Example plugin implementations


class SampleAnalyticsPlugin(BasePlugin):
    """Sample analytics plugin demonstrating the plugin system."""

    def get_metadata(self) -> PluginMetadata:
        return PluginMetadata(
            name="SampleAnalytics",
            version="1.0.0",
            description="Sample analytics plugin showing enhanced transaction insights",
            author="Klerno Labs",
            tags=["analytics", "insights", "demo"],
            dependencies=[],
        )

    def initialize(self, app: FastAPI, plugin_manager: PluginManager) -> None:
        """Initialize the sample analytics plugin."""
        # Register hook callbacks
        plugin_manager.hooks["transaction_analyzed"].register(
            self.on_transaction_analyzed,
        )

        # Add custom API endpoints
        self.add_api_route(
            app,
            "/custom - analytics",
            self.get_custom_analytics,
            methods=["GET"],
            tags=["plugins"],
        )

    def on_transaction_analyzed(
        self,
        transaction_data: dict[str, Any],
    ) -> dict[str, Any]:
        """Called when a transaction is analyzed."""
        # Add custom analysis
        custom_score = (
            transaction_data.get("amount", 0) * 0.001
        )  # Simple risk multiplier
        return {
            "plugin": "SampleAnalytics",
            "custom_risk_score": min(custom_score, 1.0),
            "analysis_note": "Custom analytics applied",
        }

    async def get_custom_analytics(self) -> dict[str, Any]:
        """Custom analytics endpoint."""
        return {
            "plugin": "SampleAnalytics",
            "message": "Custom analytics data from plugin",
            "data": {
                "analysis_type": "enhanced",
                "features": ["custom_scoring", "pattern_detection", "trend_analysis"],
            },
        }


class CompliancePlugin(BasePlugin):
    """Sample compliance plugin for regulatory reporting."""

    def get_metadata(self) -> PluginMetadata:
        return PluginMetadata(
            name="ComplianceReporting",
            version="1.0.0",
            description="Enhanced compliance reporting and regulatory tools",
            author="Klerno Labs",
            tags=["compliance", "reporting", "regulatory"],
            dependencies=[],
        )

    def initialize(self, app: FastAPI, plugin_manager: PluginManager) -> None:
        """Initialize the compliance plugin."""
        plugin_manager.hooks["alert_generated"].register(self.on_alert_generated)
        plugin_manager.hooks["report_generated"].register(self.on_report_generated)

        self.add_api_route(
            app,
            "/compliance - report",
            self.generate_compliance_report,
            methods=["GET"],
            tags=["plugins"],
        )

    def on_alert_generated(self, alert_data: dict[str, Any]) -> dict[str, Any]:
        """Process compliance requirements when alerts are generated."""
        return {
            "plugin": "ComplianceReporting",
            "compliance_checked": True,
            "regulatory_flags": self._check_regulatory_requirements(alert_data),
        }

    def on_report_generated(self, report_data: dict[str, Any]) -> dict[str, Any]:
        """Add compliance information to reports."""
        return {
            "plugin": "ComplianceReporting",
            "compliance_summary": "All transactions reviewed for regulatory compliance",
            "regulatory_score": 0.95,
        }

    def _check_regulatory_requirements(self, alert_data: dict[str, Any]) -> list[str]:
        """Check alert against regulatory requirements."""
        flags = []
        risk_score = alert_data.get("risk_score", 0)

        if risk_score > 0.8:
            flags.append("SAR_FILING_REQUIRED")
        if alert_data.get("amount", 0) > 10000:
            flags.append("CTR_THRESHOLD_EXCEEDED")

        return flags

    async def generate_compliance_report(self) -> dict[str, Any]:
        """Generate a compliance - focused report."""
        return {
            "plugin": "ComplianceReporting",
            "report_type": "regulatory_compliance",
            "summary": {
                "total_alerts_reviewed": 150,
                "sar_filings_required": 5,
                "ctr_reports_generated": 12,
                "compliance_score": 0.95,
            },
        }


# Global plugin manager instance (to be initialized with FastAPI app)
plugin_manager: PluginManager | None = None


def initialize_plugin_system(app: FastAPI) -> PluginManager:
    """Initialize the plugin system."""
    global plugin_manager
    plugin_manager = PluginManager(app)

    # Register built - in sample plugins
    plugin_manager.register_plugin(SampleAnalyticsPlugin)
    plugin_manager.register_plugin(CompliancePlugin)

    # Load plugins from directory if it exists
    plugins_dir = Path(__file__).parent / "plugins"
    if plugins_dir.exists():
        plugin_manager.load_plugins_from_directory(str(plugins_dir))

    return plugin_manager


def get_plugin_manager() -> PluginManager | None:
    """Get the global plugin manager instance."""
    return plugin_manager
