"""
Plugin Manager - Enhanced with proper settings management.

Settings Architecture:
- Plugin defaults: stored in plugin.json
- User can modify via UI: saves back to plugin.json
- Main app settings: stored in user_config.json
"""

import json
from pathlib import Path
from typing import Dict, List, Optional, Any
import logging

from .base.plugin_interface import PluginMetadata, PluginType, PluginSettings


class PluginManager:
    """Manages plugin discovery, loading, and settings."""
    
    def __init__(self, plugin_directories: List[str] = None, config_manager=None):
        """Initialize plugin manager."""
        self.logger = logging.getLogger(__name__)
        self.config_manager = config_manager
        
        if plugin_directories is None:
            plugin_directories = ['plugins/']
        self.plugin_directories = [Path(d) for d in plugin_directories]
        
        # Loaded plugins: {plugin_name: (metadata, plugin_path)}
        self.plugins: Dict[str, tuple[PluginMetadata, Path]] = {}
        
        # Plugin settings cache: {plugin_name: settings_dict}
        self.plugin_settings_cache: Dict[str, Dict[str, Any]] = {}
        
        self.logger.info("Plugin manager initialized")
    
    def scan_plugins(self) -> int:
        """Scan plugin directories for plugins."""
        self.plugins.clear()
        found_count = 0
        
        for plugin_dir in self.plugin_directories:
            if not plugin_dir.exists():
                self.logger.warning(f"Plugin directory not found: {plugin_dir}")
                continue
            
            self.logger.info(f"Scanning plugin directory: {plugin_dir}")
            
            for plugin_json in plugin_dir.rglob('plugin.json'):
                try:
                    plugin_path = plugin_json.parent
                    metadata = self._load_plugin_metadata(plugin_json)
                    
                    if metadata:
                        self.plugins[metadata.name] = (metadata, plugin_path)
                        # Load settings into cache
                        self._load_plugin_settings(metadata.name, plugin_json)
                        found_count += 1
                        self.logger.info(f"Loaded plugin: {metadata.name}")
                
                except Exception as e:
                    self.logger.error(f"Failed to load plugin from {plugin_json}: {e}")
        
        self.logger.info(f"Found {found_count} plugins")
        return found_count
    
    def _load_plugin_metadata(self, plugin_json_path: Path) -> Optional[PluginMetadata]:
        """Load plugin metadata from plugin.json file."""
        try:
            with open(plugin_json_path, 'r', encoding='utf-8') as f:
                data = json.load(f)
            
            metadata = PluginMetadata.from_dict(data)
            
            errors = metadata.validate()
            if errors:
                self.logger.error(f"Plugin validation failed: {plugin_json_path}")
                for error in errors:
                    self.logger.error(f"  - {error}")
                return None
            
            return metadata
        
        except Exception as e:
            self.logger.error(f"Error loading plugin metadata: {e}")
            return None
    
    def _load_plugin_settings(self, plugin_name: str, plugin_json_path: Path):
        """Load plugin settings from plugin.json into cache."""
        try:
            with open(plugin_json_path, 'r', encoding='utf-8') as f:
                data = json.load(f)
            
            settings = {}
            for key, setting_data in data.get('settings', {}).items():
                if isinstance(setting_data, dict) and 'default' in setting_data:
                    settings[key] = setting_data['default']
            
            self.plugin_settings_cache[plugin_name] = settings
        
        except Exception as e:
            self.logger.error(f"Error loading plugin settings: {e}")
            self.plugin_settings_cache[plugin_name] = {}
    
    def get_plugin_setting(self, plugin_name: str, setting_key: str, default=None):
        """
        Get a plugin setting value.
        
        Reads from plugin.json file (via cache).
        
        Args:
            plugin_name: Name of the plugin
            setting_key: Setting key
            default: Default value if not found
            
        Returns:
            Setting value or default
        """
        if plugin_name in self.plugin_settings_cache:
            return self.plugin_settings_cache[plugin_name].get(setting_key, default)
        return default
    
    def set_plugin_setting(self, plugin_name: str, setting_key: str, value: Any) -> bool:
        """
        Set a plugin setting and save to plugin.json.
        
        Args:
            plugin_name: Name of the plugin
            setting_key: Setting key
            value: New value
            
        Returns:
            True if successful, False otherwise
        """
        if plugin_name not in self.plugins:
            self.logger.error(f"Plugin not found: {plugin_name}")
            return False
        
        try:
            _, plugin_path = self.plugins[plugin_name]
            plugin_json = plugin_path / 'plugin.json'
            
            # Load current plugin.json
            with open(plugin_json, 'r', encoding='utf-8') as f:
                data = json.load(f)
            
            # Update the setting
            if 'settings' not in data:
                data['settings'] = {}
            
            if setting_key not in data['settings']:
                # Create new setting entry
                data['settings'][setting_key] = {
                    'type': type(value).__name__,
                    'default': value
                }
            else:
                # Update existing setting
                data['settings'][setting_key]['default'] = value
            
            # Save back to plugin.json
            with open(plugin_json, 'w', encoding='utf-8') as f:
                json.dump(data, f, indent=2, ensure_ascii=False)
            
            # Update cache
            if plugin_name not in self.plugin_settings_cache:
                self.plugin_settings_cache[plugin_name] = {}
            self.plugin_settings_cache[plugin_name][setting_key] = value
            
            self.logger.info(f"Updated {plugin_name}.{setting_key} = {value}")
            return True
        
        except Exception as e:
            self.logger.error(f"Error saving plugin setting: {e}")
            return False
    
    def get_all_plugin_settings(self, plugin_name: str) -> Dict[str, Any]:
        """Get all settings for a plugin."""
        return self.plugin_settings_cache.get(plugin_name, {}).copy()
    
    def reload_plugin_settings(self, plugin_name: str) -> bool:
        """Reload plugin settings from disk."""
        if plugin_name not in self.plugins:
            return False
        
        try:
            _, plugin_path = self.plugins[plugin_name]
            plugin_json = plugin_path / 'plugin.json'
            self._load_plugin_settings(plugin_name, plugin_json)
            return True
        except Exception as e:
            self.logger.error(f"Error reloading plugin settings: {e}")
            return False
    
    def are_plugins_globally_enabled(self) -> bool:
        """Check if plugins are globally enabled via master switch."""
        if self.config_manager:
            return self.config_manager.get_setting('pipeline.enable_optimizer_plugins', False)
        return False
    
    def is_plugin_active(self, plugin_name: str) -> bool:
        """Check if a plugin is active."""
        plugin = self.get_plugin(plugin_name)
        if not plugin:
            return False
        
        # Essential plugins always active
        if plugin.essential:
            return plugin.enabled
        
        # Non-essential: check master switch
        if not self.are_plugins_globally_enabled():
            return False
        
        return plugin.enabled
    
    def get_plugin(self, plugin_name: str) -> Optional[PluginMetadata]:
        """Get plugin metadata by name."""
        if plugin_name in self.plugins:
            return self.plugins[plugin_name][0]
        return None
    
    def get_plugin_path(self, plugin_name: str) -> Optional[Path]:
        """Get plugin directory path."""
        if plugin_name in self.plugins:
            return self.plugins[plugin_name][1]
        return None
    
    def get_all_plugins(self) -> List[PluginMetadata]:
        """Get all loaded plugins."""
        return [metadata for metadata, _ in self.plugins.values()]
