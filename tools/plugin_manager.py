"""
Anju AI — Plugin Manager
Dynamic plugin discovery, loading, and registration system.
Allows tools and capabilities to be added as plugins without modifying core code.
"""
import os
import sys
import json
import importlib
import inspect
import threading
from datetime import datetime
from typing import Any, Callable, Optional

# ── Plugin Registry ─────────────────────────────────────────────────────────
_plugins = {}           # name -> PluginInfo
_plugin_actions = {}    # action_name -> handler_function
_plugin_lock = threading.Lock()

PLUGIN_DIRS = [
    os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "tools"),
    os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "plugins"),
]

REGISTRY_FILE = os.path.join(
    os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
    "memory", "plugin_registry.json"
)

# ── Plugin Metadata ─────────────────────────────────────────────────────────

class PluginInfo:
    """Metadata about a registered plugin."""
    def __init__(self, name: str, module_path: str, version: str = "1.0.0",
                 description: str = "", author: str = "", actions: list = None,
                 dependencies: list = None):
        self.name = name
        self.module_path = module_path
        self.version = version
        self.description = description
        self.author = author
        self.actions = actions or []
        self.dependencies = dependencies or []
        self.enabled = True
        self.loaded_at = datetime.now()
        self.health_status = "unknown"

    def to_dict(self) -> dict:
        return {
            "name": self.name,
            "module": self.module_path,
            "version": self.version,
            "description": self.description,
            "author": self.author,
            "actions": self.actions,
            "dependencies": self.dependencies,
            "enabled": self.enabled,
            "loaded_at": self.loaded_at.isoformat(),
            "health": self.health_status,
        }


# ══════════════════════════════════════════════════════════════════════════
#  PLUGIN DISCOVERY
# ══════════════════════════════════════════════════════════════════════════

def discover_plugins() -> list[dict]:
    """
    Scan plugin directories for Python files that export an 'anju_plugin' dict
    or have a 'register_plugin()' function.

    Expected plugin structure:

    # my_plugin.py
    anju_plugin = {
        "name": "My Plugin",
        "version": "1.0.0",
        "description": "Does something cool",
        "actions": ["my_action"],
    }

    def handle_my_action(params: dict) -> str:
        return "Result"
    """
    discovered = []

    for plugin_dir in PLUGIN_DIRS:
        if not os.path.isdir(plugin_dir):
            continue

        for fname in sorted(os.listdir(plugin_dir)):
            if not fname.endswith(".py") or fname.startswith("_"):
                continue

            module_name = fname[:-3]
            module_path = f"{os.path.basename(plugin_dir)}.{module_name}"

            try:
                spec = importlib.util.spec_from_file_location(
                    module_name,
                    os.path.join(plugin_dir, fname)
                )
                if spec and spec.loader:
                    module = importlib.util.module_from_spec(spec)
                    spec.loader.exec_module(module)

                    if hasattr(module, 'anju_plugin'):
                        plugin_meta = module.anju_plugin
                        discovered.append({
                            "name": plugin_meta.get("name", module_name),
                            "module": module_path,
                            "version": plugin_meta.get("version", "1.0.0"),
                            "description": plugin_meta.get("description", ""),
                            "author": plugin_meta.get("author", "Unknown"),
                            "actions": plugin_meta.get("actions", []),
                            "dependencies": plugin_meta.get("dependencies", []),
                        })
            except Exception as e:
                print(f"[Plugin] Discovery error for {fname}: {e}")

    return discovered


def load_plugin(module_path: str) -> Optional[PluginInfo]:
    """
    Load and register a single plugin by its module path (e.g., "tools.web_search").
    """
    try:
        module = importlib.import_module(module_path)

        if not hasattr(module, 'anju_plugin'):
            print(f"[Plugin] {module_path} has no 'anju_plugin' metadata.")
            return None

        meta = module.anju_plugin
        name = meta.get("name", module_path.split(".")[-1])

        plugin_info = PluginInfo(
            name=name,
            module_path=module_path,
            version=meta.get("version", "1.0.0"),
            description=meta.get("description", ""),
            author=meta.get("author", "Unknown"),
            actions=meta.get("actions", []),
            dependencies=meta.get("dependencies", []),
        )

        # Register actions from the plugin
        for action_name in plugin_info.actions:
            handler_name = f"handle_{action_name}"
            if hasattr(module, handler_name):
                handler = getattr(module, handler_name)
                if callable(handler):
                    register_action(action_name, handler, plugin_info.name)
                    print(f"[Plugin] Registered action '{action_name}' from '{name}'")

        with _plugin_lock:
            _plugins[name] = plugin_info

        _save_registry()
        return plugin_info

    except Exception as e:
        print(f"[Plugin] Load error for {module_path}: {e}")
        return None


def load_all_plugins() -> int:
    """Discover and load all available plugins. Returns count of loaded plugins."""
    discovered = discover_plugins()
    count = 0

    for plugin_info in discovered:
        info = load_plugin(plugin_info["module"])
        if info:
            count += 1

    return count


def register_builtin_plugins() -> int:
    """
    Register all built-in tools as pseudo-plugins for the action routing system.
    This makes all existing tools discoverable through the plugin manager.
    """
    builtins = {
        "tools.web_search": {
            "name": "Web Search",
            "actions": ["web_search"],
            "description": "Search the web for real-time information"
        },
        "tools.image_generator": {
            "name": "Image Generator",
            "actions": ["generate_image"],
            "description": "Generate images from text prompts"
        },
        "tools.pdf_generator": {
            "name": "PDF Generator",
            "actions": ["generate_pdf"],
            "description": "Generate PDF documents"
        },
        "tools.code_execution": {
            "name": "Code Execution",
            "actions": ["execute_code"],
            "description": "Execute Python code and terminal commands"
        },
        "tools.file_ops": {
            "name": "File Operations",
            "actions": ["read_file", "write_file", "list_directory"],
            "description": "Read, write, and manage files on the system"
        },
        "tools.camera": {
            "name": "Camera",
            "actions": ["take_picture"],
            "description": "Capture webcam photos"
        },
        "tools.vision_analyzer": {
            "name": "Vision Analyzer",
            "actions": ["analyze_vision"],
            "description": "Analyze images with AI vision"
        },
        "tools.cyber_tools": {
            "name": "Cyber Tools",
            "actions": ["port_scan", "url_check"],
            "description": "Security scanning and URL verification"
        },
        "tools.phone_control": {
            "name": "Phone Control",
            "actions": ["connect_phone", "open_app", "send_sms", "take_photo",
                       "take_screenshot", "get_battery", "get_notifications",
                       "send_keyevent", "set_volume"],
            "description": "Control Android phone via ADB"
        },
        "automation.app_control": {
            "name": "App Control",
            "actions": ["open_app"],
            "description": "Launch applications on the computer"
        },
        "memory.memory": {
            "name": "Memory System",
            "actions": ["remember", "get_memory"],
            "description": "Store and retrieve information in long-term memory"
        },
    }

    count = 0
    for module_path, meta in builtins.items():
        try:
            # Check if the module can be imported
            spec = importlib.util.find_spec(module_path)
            if spec is None:
                print(f"[Plugin] Built-in {module_path} not available, skipping.")
                continue

            # Register actions generically (handlers resolve via execute_step)
            from brain.workflow_engine import execute_step

            plugin_info = PluginInfo(
                name=meta["name"],
                module_path=module_path,
                version="1.0.0",
                description=meta.get("description", ""),
                actions=meta["actions"],
            )

            with _plugin_lock:
                _plugins[meta["name"]] = plugin_info

                # Register the execute_step as the handler for all actions
                for action_name in meta["actions"]:
                    _plugin_actions[action_name] = {
                        "handler": execute_step,
                        "plugin": meta["name"],
                    }

            count += 1
        except Exception as e:
            print(f"[Plugin] Built-in registration error for {module_path}: {e}")

    _save_registry()
    return count


# ══════════════════════════════════════════════════════════════════════════
#  ACTION ROUTING
# ══════════════════════════════════════════════════════════════════════════

def register_action(action_name: str, handler: Callable, plugin_name: str = "unknown"):
    """Register an action handler function."""
    with _plugin_lock:
        _plugin_actions[action_name] = {
            "handler": handler,
            "plugin": plugin_name,
        }


def execute_action(action_name: str, params: dict) -> str:
    """
    Execute an action by name, routing to the appropriate plugin handler.
    Falls back to the workflow engine's execute_step for built-in actions.
    """
    with _plugin_lock:
        action_info = _plugin_actions.get(action_name)

    if action_info:
        try:
            return action_info["handler"](action_name, params)
        except Exception as e:
            return f"[Plugin:{action_info['plugin']}] Error: {e}"

    # Fallback to workflow engine
    from brain.workflow_engine import execute_step
    return execute_step(action_name, params)


def get_available_actions() -> dict:
    """Get a dictionary of all registered actions and their plugins."""
    with _plugin_lock:
        actions = {}
        for action_name, info in _plugin_actions.items():
            actions[action_name] = info["plugin"]
        return actions


# ══════════════════════════════════════════════════════════════════════════
#  PLUGIN MANAGEMENT
# ══════════════════════════════════════════════════════════════════════════

def list_plugins() -> list[dict]:
    """List all registered plugins with their metadata."""
    with _plugin_lock:
        return [p.to_dict() for p in _plugins.values()]


def get_plugin(name: str) -> Optional[PluginInfo]:
    """Get plugin info by name."""
    with _plugin_lock:
        return _plugins.get(name)


def enable_plugin(name: str) -> str:
    """Enable a plugin."""
    with _plugin_lock:
        if name in _plugins:
            _plugins[name].enabled = True
            _save_registry()
            return f"Plugin '{name}' enabled."
    return f"Plugin '{name}' not found."


def disable_plugin(name: str) -> str:
    """Disable a plugin."""
    with _plugin_lock:
        if name in _plugins:
            _plugins[name].enabled = False
            _save_registry()
            return f"Plugin '{name}' disabled."
    return f"Plugin '{name}' not found."


def reload_plugins() -> int:
    """Reload all plugins. Returns count of successfully loaded plugins."""
    with _plugin_lock:
        _plugins.clear()
        _plugin_actions.clear()

    builtin_count = register_builtin_plugins()
    external_count = load_all_plugins()

    return builtin_count + external_count


def _save_registry():
    """Persist plugin registry to disk."""
    try:
        with _plugin_lock:
            data = {name: info.to_dict() for name, info in _plugins.items()}
        os.makedirs(os.path.dirname(REGISTRY_FILE), exist_ok=True)
        with open(REGISTRY_FILE, "w") as f:
            json.dump(data, f, indent=2)
    except Exception as e:
        print(f"[Plugin] Registry save error: {e}")


def plugins_help() -> str:
    """Generate help text showing all available plugins and actions."""
    actions = get_available_actions()
    plugins_list = list_plugins()

    lines = ["🧩 **Plugin Ecosystem — Available Capabilities**", ""]

    for p in plugins_list:
        status = "✅" if p["enabled"] else "⛔"
        lines.append(f"{status} **{p['name']}** v{p['version']}")
        lines.append(f"   {p['description']}")
        if p["actions"]:
            lines.append(f"   Actions: `{'`, `'.join(p['actions'])}`")
        lines.append("")

    if not plugins_list:
        lines.append("_No plugins registered yet._")

    lines.append(f"**Total: {len(plugins_list)} plugins, {len(actions)} actions**")

    return "\n".join(lines)


# ══════════════════════════════════════════════════════════════════════════
#  INIT
# ══════════════════════════════════════════════════════════════════════════

def init_plugins():
    """Initialize the plugin system - registers built-ins and discovers external plugins."""
    count = register_builtin_plugins()
    ext_count = load_all_plugins()
    print(f"[Plugin] System initialized: {count} built-in, {ext_count} external plugins loaded.")
    return count + ext_count
