"""
Text Processor Plugin Manager with Auto-Generation

Manages text processor plugins and auto-generates plugins for installed text processing libraries.
"""

import logging
import importlib.util
import json
from pathlib import Path
from typing import List, Dict, Optional

# Import PluginMetadata for proper plugin representation
from app.workflow.base.plugin_interface import PluginMetadata


class TextProcessorPluginManager:
    """Manages text processor plugins with auto-generation support."""
    
    def __init__(self, plugin_directories: Optional[List[str]] = None):
        """Initialize text processor plugin manager."""
        self.logger = logging.getLogger(__name__)
        self._plugin_directories = plugin_directories or []
        self._add_default_plugin_directories()
        self.discovered_plugins = []
    
    def _add_default_plugin_directories(self):
        """Add default plugin search directories."""
        current_dir = Path(__file__).parent
        
        # Main plugins directory
        self._plugin_directories.extend([
            str(current_dir.parent.parent / "plugins" / "text_processors"),
        ])
        
        # User plugins directory
        user_plugins = Path.home() / ".translation_system" / "plugins" / "text_processors"
        self._plugin_directories.append(str(user_plugins))
    
    def discover_plugins(self) -> List[PluginMetadata]:
        """
        Discover available text processor plugins.
        Auto-generates plugins for installed text processing libraries.
        
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
            
            self.logger.info(f"Scanning for text processor plugins in: {directory}")
            
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
                                self.logger.info(f"Discovered text processor plugin: {plugin_info.name}")
                            else:
                                self.logger.debug(f"Skipping {plugin_data.get('name')} - dependencies not installed")
                        except Exception as e:
                            self.logger.error(f"Failed to load plugin {plugin_json}: {e}")
        
        self.discovered_plugins = discovered
        self.logger.info(f"Discovered {len(discovered)} text processor plugins")
        return discovered
    
    def _auto_generate_missing_plugins(self):
        """
        Auto-generate text processor plugins for installed packages.
        
        Checks for common text processing libraries and creates plugins if missing.
        """
        # Check for installed text processing libraries
        text_processor_libraries = {
            'nltk': {
                'display_name': 'NLTK Text Processor',
                'description': 'Natural language processing using NLTK'
            },
            'spacy': {
                'display_name': 'spaCy Text Processor',
                'description': 'Industrial-strength NLP with spaCy'
            },
            'textblob': {
                'display_name': 'TextBlob Processor',
                'description': 'Simple text processing with TextBlob'
            },
            'regex': {
                'display_name': 'Regex Text Processor',
                'description': 'Advanced regex-based text processing'
            },
        }
        
        main_plugin_dir = None
        for directory in self._plugin_directories:
            if 'plugins' in directory and 'text_processors' in directory and '.translation_system' not in directory:
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
        
        for package_name, info in text_processor_libraries.items():
            # Skip if already exists
            if package_name in existing_packages:
                continue
            
            # Check if package is installed
            spec = importlib.util.find_spec(package_name)
            if spec is not None:
                plugin_folder = main_plugin_dir / package_name
                if not (plugin_folder / "plugin.json").exists():
                    self.logger.info(f"Auto-generating text processor plugin for {package_name}")
                    self._create_text_processor_plugin(
                        plugin_folder,
                        package_name,
                        info['display_name'],
                        info['description']
                    )
    
    def _create_text_processor_plugin(self, plugin_folder: Path, package_name: str,
                                      display_name: str, description: str):
        """Create a basic text processor plugin."""
        plugin_folder.mkdir(parents=True, exist_ok=True)
        
        # Create plugin.json
        plugin_json = {
            "name": package_name,
            "display_name": display_name,
            "version": "1.0.0",
            "author": "OptikR Auto-Generator",
            "description": description,
            "type": "text_processor",
            "enabled_by_default": False,
            "dependencies": [package_name],
            "settings": {
                "filter_mode": {
                    "type": "string",
                    "default": "basic",
                    "description": "Text filtering mode"
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
    """Initialize text processor."""
    try:
        import {package_name}
        logger.info(f"{display_name} initialized")
        return True
    except ImportError:
        logger.error(f"{package_name} not available")
        return False

def process_text(text: str) -> str:
    """Process/filter text."""
    # TODO: Implement text processing logic
    return text

def cleanup():
    """Clean up resources."""
    logger.info(f"{display_name} cleanup")
'''
        
        with open(plugin_folder / "__init__.py", 'w', encoding='utf-8') as f:
            f.write(init_content)
        
        self.logger.info(f"✓ Created text processor plugin for {package_name}")
    
    def _check_dependencies(self, dependencies: List[str]) -> bool:
        """Check if all dependencies are installed."""
        if not dependencies:
            return True
        
        for dep in dependencies:
            spec = importlib.util.find_spec(dep)
            if spec is None:
                return False
        return True
