"""
Plugin Manager - Discovers and loads plugins from disk.

Scans the plugins/ directory for plugin.json files and manages plugin lifecycle.
"""

import json
from pathlib import Path
from typing import Dict, List, Optional
import logging

from .base.plugin_interface import PluginMetadata, PluginType, PluginSettings


class PluginManager:
    """Manages plugin discovery, loading, and lifecycle."""
    
    def __init__(self, plugin_directories: List[str] = None, config_manager=None):
        """
        Initialize plugin manager.
        
        Args:
            plugin_directories: List of directories to scan for plugins
                               Default: ['plugins/']
            config_manager: Configuration manager to check master enable/disable setting
        """
        self.logger = logging.getLogger(__name__)
        self.config_manager = config_manager
        
        # Plugin directories to scan
        if plugin_directories is None:
            plugin_directories = ['plugins/']
        self.plugin_directories = [Path(d) for d in plugin_directories]
        
        # Loaded plugins: {plugin_name: (metadata, plugin_path)}
        self.plugins: Dict[str, tuple[PluginMetadata, Path]] = {}
        
        # Plugin settings: {plugin_name: PluginSettings}
        self.plugin_settings: Dict[str, PluginSettings] = {}
        
        self.logger.info("Plugin manager initialized")
    
    def are_plugins_globally_enabled(self) -> bool:
        """
        Check if plugins are globally enabled via master switch.
        
        Returns:
            True if plugins are enabled globally, False otherwise
        """
        if self.config_manager:
            return self.config_manager.get_setting('pipeline.enable_optimizer_plugins', False)
        return False  # Default to disabled if no config manager
    
    def scan_plugins(self) -> int:
        """
        Scan plugin directories for plugins.
        
        Returns:
            Number of plugins found
        """
        self.plugins.clear()
        found_count = 0
        
        for plugin_dir in self.plugin_directories:
            if not plugin_dir.exists():
                self.logger.warning(f"Plugin directory not found: {plugin_dir}")
                continue
            
            self.logger.info(f"Scanning plugin directory: {plugin_dir}")
            
            # Scan for plugin.json files
            for plugin_json in plugin_dir.rglob('plugin.json'):
                try:
                    plugin_path = plugin_json.parent
                    metadata = self._load_plugin_metadata(plugin_json)
                    
                    if metadata:
                        self.plugins[metadata.name] = (metadata, plugin_path)
                        found_count += 1
                        self.logger.info(f"Loaded plugin: {metadata.name} ({metadata.type.value})")
                    
                except Exception as e:
                    self.logger.error(f"Failed to load plugin from {plugin_json}: {e}")
        
        self.logger.info(f"Found {found_count} plugins")
        return found_count
    
    def _load_plugin_metadata(self, plugin_json_path: Path) -> Optional[PluginMetadata]:
        """
        Load plugin metadata from plugin.json file.
        
        Args:
            plugin_json_path: Path to plugin.json
            
        Returns:
            PluginMetadata or None if invalid
        """
        try:
            with open(plugin_json_path, 'r', encoding='utf-8') as f:
                data = json.load(f)
            
            metadata = PluginMetadata.from_dict(data)
            
            # Validate metadata
            errors = metadata.validate()
            if errors:
                self.logger.error(f"Plugin validation failed: {plugin_json_path}")
                for error in errors:
                    self.logger.error(f"  - {error}")
                return None
            
            # Check if worker script exists
            plugin_dir = plugin_json_path.parent
            worker_path = plugin_dir / metadata.worker_script
            if not worker_path.exists():
                self.logger.error(f"Worker script not found: {worker_path}")
                return None
            
            return metadata
            
        except json.JSONDecodeError as e:
            self.logger.error(f"Invalid JSON in {plugin_json_path}: {e}")
            return None
        except KeyError as e:
            self.logger.error(f"Missing required field in {plugin_json_path}: {e}")
            return None
        except Exception as e:
            self.logger.error(f"Error loading plugin metadata: {e}")
            return None
    
    def is_plugin_active(self, plugin_name: str) -> bool:
        """
        Check if a plugin is active (considering both master switch AND individual enabled setting).
        ESSENTIAL PLUGINS ALWAYS BYPASS THE MASTER SWITCH AND ARE ALWAYS ACTIVE.
        
        Args:
            plugin_name: Name of the plugin
            
        Returns:
            True if plugin should be active, False otherwise
        """
        # Get plugin metadata
        plugin = self.get_plugin(plugin_name)
        if not plugin:
            return False
        
        # HARDCODED: Essential plugins ALWAYS active, bypass master switch
        if plugin.essential:
            return plugin.enabled
        
        # Non-essential plugins: check master switch first
        if not self.are_plugins_globally_enabled():
            return False
        
        # Then check individual plugin's enabled setting
        return plugin.enabled
    
    def is_plugin_essential(self, plugin_name: str) -> bool:
        """
        Check if a plugin is marked as essential.
        Essential plugins cannot be disabled and bypass the master switch.
        
        Args:
            plugin_name: Name of the plugin
            
        Returns:
            True if plugin is essential, False otherwise
        """
        plugin = self.get_plugin(plugin_name)
        return plugin.essential if plugin else False
    
    def get_plugin(self, plugin_name: str) -> Optional[PluginMetadata]:
        """
        Get plugin metadata by name.
        
        Args:
            plugin_name: Name of the plugin
            
        Returns:
            PluginMetadata or None if not found
        """
        if plugin_name in self.plugins:
            return self.plugins[plugin_name][0]
        return None
    
    def get_plugin_path(self, plugin_name: str) -> Optional[Path]:
        """
        Get plugin directory path.
        
        Args:
            plugin_name: Name of the plugin
            
        Returns:
            Path to plugin directory or None
        """
        if plugin_name in self.plugins:
            return self.plugins[plugin_name][1]
        return None
    
    def get_worker_script_path(self, plugin_name: str) -> Optional[str]:
        """
        Get absolute path to plugin's worker script.
        
        Args:
            plugin_name: Name of the plugin
            
        Returns:
            Absolute path to worker script or None
        """
        if plugin_name not in self.plugins:
            return None
        
        metadata, plugin_path = self.plugins[plugin_name]
        worker_path = plugin_path / metadata.worker_script
        return str(worker_path.absolute())
    
    def get_plugins_by_type(self, plugin_type: PluginType) -> List[PluginMetadata]:
        """
        Get all plugins of a specific type.
        
        Args:
            plugin_type: Type of plugins to get
            
        Returns:
            List of PluginMetadata
        """
        return [
            metadata for metadata, _ in self.plugins.values()
            if metadata.type == plugin_type
        ]
    
    def get_all_plugins(self) -> List[PluginMetadata]:
        """
        Get all loaded plugins.
        
        Returns:
            List of all PluginMetadata
        """
        return [metadata for metadata, _ in self.plugins.values()]
    
    def is_plugin_enabled(self, plugin_name: str) -> bool:
        """
        Check if a plugin is enabled.
        
        Args:
            plugin_name: Name of the plugin
            
        Returns:
            True if enabled, False otherwise
        """
        if plugin_name in self.plugin_settings:
            return self.plugin_settings[plugin_name].enabled
        
        # Check default from metadata
        if plugin_name in self.plugins:
            metadata, _ = self.plugins[plugin_name]
            return metadata.enabled_by_default
        
        return False
    
    def set_plugin_enabled(self, plugin_name: str, enabled: bool):
        """
        Enable or disable a plugin.
        
        Args:
            plugin_name: Name of the plugin
            enabled: True to enable, False to disable
        """
        if plugin_name not in self.plugin_settings:
            self.plugin_settings[plugin_name] = PluginSettings(plugin_name=plugin_name)
        
        self.plugin_settings[plugin_name].enabled = enabled
        self.logger.info(f"Plugin {plugin_name} {'enabled' if enabled else 'disabled'}")
    
    def get_plugin_settings(self, plugin_name: str) -> Optional[PluginSettings]:
        """
        Get runtime settings for a plugin.
        
        Args:
            plugin_name: Name of the plugin
            
        Returns:
            PluginSettings or None
        """
        return self.plugin_settings.get(plugin_name)
    
    def set_plugin_setting(self, plugin_name: str, key: str, value):
        """
        Set a plugin setting value.
        
        Args:
            plugin_name: Name of the plugin
            key: Setting key
            value: Setting value
        """
        if plugin_name not in self.plugin_settings:
            self.plugin_settings[plugin_name] = PluginSettings(plugin_name=plugin_name)
        
        self.plugin_settings[plugin_name].set(key, value)
        self.logger.info(f"Plugin {plugin_name} setting '{key}' = {value}")
    
    def reload_plugin(self, plugin_name: str) -> bool:
        """
        Reload a plugin from disk.
        
        Args:
            plugin_name: Name of the plugin to reload
            
        Returns:
            True if successful, False otherwise
        """
        if plugin_name not in self.plugins:
            self.logger.error(f"Plugin not found: {plugin_name}")
            return False
        
        try:
            # Get current plugin path
            _, plugin_path = self.plugins[plugin_name]
            plugin_json = plugin_path / 'plugin.json'
            
            # Reload metadata
            metadata = self._load_plugin_metadata(plugin_json)
            if metadata:
                self.plugins[plugin_name] = (metadata, plugin_path)
                self.logger.info(f"Reloaded plugin: {plugin_name}")
                return True
            else:
                self.logger.error(f"Failed to reload plugin: {plugin_name}")
                return False
                
        except Exception as e:
            self.logger.error(f"Error reloading plugin {plugin_name}: {e}")
            return False
    
    def get_enabled_plugins_by_type(self, plugin_type: PluginType) -> List[PluginMetadata]:
        """
        Get all enabled plugins of a specific type.
        
        Args:
            plugin_type: Type of plugins to get
            
        Returns:
            List of enabled PluginMetadata
        """
        return [
            metadata for metadata in self.get_plugins_by_type(plugin_type)
            if self.is_plugin_enabled(metadata.name)
        ]
    
    def get_plugin_count_by_type(self) -> Dict[str, int]:
        """
        Get count of plugins by type.
        
        Returns:
            Dictionary mapping type name to count
        """
        counts = {ptype.value: 0 for ptype in PluginType}
        
        for metadata, _ in self.plugins.values():
            counts[metadata.type.value] += 1
        
        return counts
    
    def save_settings(self, filepath: str):
        """
        Save plugin settings to file.
        
        Args:
            filepath: Path to save settings
        """
        try:
            settings_data = {
                name: settings.to_dict()
                for name, settings in self.plugin_settings.items()
            }
            
            with open(filepath, 'w', encoding='utf-8') as f:
                json.dump(settings_data, f, indent=2)
            
            self.logger.info(f"Saved plugin settings to {filepath}")
            
        except Exception as e:
            self.logger.error(f"Failed to save plugin settings: {e}")
    
    def load_settings(self, filepath: str):
        """
        Load plugin settings from file.
        
        Args:
            filepath: Path to load settings from
        """
        try:
            with open(filepath, 'r', encoding='utf-8') as f:
                settings_data = json.load(f)
            
            self.plugin_settings.clear()
            for name, data in settings_data.items():
                self.plugin_settings[name] = PluginSettings.from_dict(data)
            
            self.logger.info(f"Loaded plugin settings from {filepath}")
            
        except FileNotFoundError:
            self.logger.info(f"No plugin settings file found: {filepath}")
        except Exception as e:
            self.logger.error(f"Failed to load plugin settings: {e}")
