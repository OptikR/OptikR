"""
Optimizer Plugin Manager with Auto-Generation

Manages optimizer plugins and auto-generates plugins for installed optimization libraries.
"""

import logging
import importlib.util
import json
from pathlib import Path
from typing import List, Dict, Optional

# Import PluginMetadata for proper plugin representation
from app.workflow.base.plugin_interface import PluginMetadata


class OptimizerPluginManager:
    """Manages optimizer plugins with auto-generation support."""
    
    def __init__(self, plugin_directories: Optional[List[str]] = None):
        """Initialize optimizer plugin manager."""
        self.logger = logging.getLogger(__name__)
        self._plugin_directories = plugin_directories or []
        self._add_default_plugin_directories()
        self.discovered_plugins = []
    
    def _add_default_plugin_directories(self):
        """Add default plugin search directories."""
        current_dir = Path(__file__).parent
        
        # Main plugins directory
        self._plugin_directories.extend([
            str(current_dir.parent.parent / "plugins" / "optimizers"),
        ])
        
        # User plugins directory
        user_plugins = Path.home() / ".translation_system" / "plugins" / "optimizers"
        self._plugin_directories.append(str(user_plugins))
    
    def discover_plugins(self) -> List[PluginMetadata]:
        """
        Discover available optimizer plugins.
        Auto-generates plugins for installed optimization libraries.
        
        Returns:
            List of discovered plugin metadata objects
        """
        # First, auto-generate missing plugins for installed packages
        self._auto_generate_missing_plugins()
        
        discovered = []
        
        for directory in self._plugin_directories:
            dir_path = Path(directory)
            if not dir_path.exists():
                continue
            
            self.logger.info(f"Scanning for optimizer plugins in: {directory}")
            
            for item in dir_path.iterdir():
                if item.is_dir():
                    plugin_json = item / "plugin.json"
                    if plugin_json.exists():
                        try:
                            with open(plugin_json, 'r', encoding='utf-8') as f:
                                plugin_data = json.load(f)
                            
                            # Check if dependencies are installed
                            if self._check_dependencies(plugin_data.get('dependencies', [])):
                                # Convert dict to PluginMetadata object
                                plugin_info = PluginMetadata.from_dict(plugin_data)
                                discovered.append(plugin_info)
                                self.logger.info(f"Discovered optimizer plugin: {plugin_info.name}")
                            else:
                                self.logger.debug(f"Skipping {plugin_data.get('name')} - dependencies not installed")
                        except Exception as e:
                            self.logger.error(f"Failed to load plugin {plugin_json}: {e}")
        
        self.discovered_plugins = discovered
        self.logger.info(f"Discovered {len(discovered)} optimizer plugins")
        return discovered
    
    def _auto_generate_missing_plugins(self):
        """
        Auto-generate optimizer plugins for installed packages.
        
        Checks for common optimization libraries and creates plugins if missing.
        """
        # Check for installed optimization libraries
        optimizer_libraries = {
            'numba': {
                'display_name': 'Numba JIT Optimizer',
                'description': 'JIT compilation for numerical Python code using Numba'
            },
            'cython': {
                'display_name': 'Cython Optimizer',
                'description': 'C-extensions for Python optimization using Cython'
            },
        }
        
        main_plugin_dir = None
        for directory in self._plugin_directories:
            if 'plugins' in directory and 'optimizers' in directory and '.translation_system' not in directory:
                main_plugin_dir = Path(directory)
                break
        
        if not main_plugin_dir:
            return
        
        # Scan existing plugins to avoid duplicates
        existing_packages = set()
        if main_plugin_dir.exists():
            for item in main_plugin_dir.iterdir():
                if item.is_dir():
                    plugin_json = item / "plugin.json"
                    if plugin_json.exists():
                        try:
                            with open(plugin_json, 'r', encoding='utf-8') as f:
                                data = json.load(f)
                                deps = data.get('dependencies', [])
                                existing_packages.update(deps)
                        except:
                            pass
        
        for package_name, info in optimizer_libraries.items():
            # Skip if already exists
            if package_name in existing_packages:
                continue
            
            # Check if package is installed
            spec = importlib.util.find_spec(package_name)
            if spec is not None:
                plugin_folder = main_plugin_dir / package_name
                if not (plugin_folder / "plugin.json").exists():
                    self.logger.info(f"Auto-generating optimizer plugin for {package_name}")
                    self._create_optimizer_plugin(
                        plugin_folder,
                        package_name,
                        info['display_name'],
                        info['description']
                    )
    
    def _create_optimizer_plugin(self, plugin_folder: Path, package_name: str, 
                                 display_name: str, description: str):
        """Create a basic optimizer plugin."""
        plugin_folder.mkdir(parents=True, exist_ok=True)
        
        # Create plugin.json
        plugin_json = {
            "name": package_name,
            "display_name": display_name,
            "version": "1.0.0",
            "author": "OptikR Auto-Generator",
            "description": description,
            "type": "optimizer",
            "enabled_by_default": False,
            "dependencies": [package_name],
            "settings": {
                "optimization_level": {
                    "type": "int",
                    "default": 2,
                    "description": "Optimization level (0-3)"
                }
            }
        }
        
        with open(plugin_folder / "plugin.json", 'w', encoding='utf-8') as f:
            json.dump(plugin_json, f, indent=2)
        
        # Create basic __init__.py
        init_content = f'''"""
{display_name} - Auto-generated

{description}
"""

import logging

logger = logging.getLogger(__name__)

def initialize(config: dict) -> bool:
    """Initialize optimizer."""
    try:
        import {package_name}
        logger.info(f"{display_name} initialized")
        return True
    except ImportError:
        logger.error(f"{package_name} not available")
        return False

def optimize(data):
    """Optimize data processing."""
    # TODO: Implement optimization logic
    return data

def cleanup():
    """Clean up resources."""
    logger.info(f"{display_name} cleanup")
'''
        
        with open(plugin_folder / "__init__.py", 'w', encoding='utf-8') as f:
            f.write(init_content)
        
        self.logger.info(f"✓ Created optimizer plugin for {package_name}")
    
    def _check_dependencies(self, dependencies: List[str]) -> bool:
        """Check if all dependencies are installed."""
        if not dependencies:
            return True
        
        for dep in dependencies:
            spec = importlib.util.find_spec(dep)
            if spec is None:
                return False
        return True
