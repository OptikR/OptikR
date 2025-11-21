"""
Plugin Validator

Validates that essential plugins are available and loaded.
Essential plugins cannot be disabled and are required for the system to function.
"""

import json
import logging
from pathlib import Path
from typing import List, Dict, Tuple


class PluginValidator:
    """Validates essential plugins are available."""
    
    def __init__(self):
        """Initialize plugin validator."""
        self.logger = logging.getLogger(__name__)
    
    def check_essential_ocr_plugins(self, ocr_engines_dir: Path) -> Tuple[bool, List[str]]:
        """
        Check if at least one essential OCR plugin is available.
        
        Args:
            ocr_engines_dir: Path to OCR engines directory
            
        Returns:
            Tuple of (success, list of available essential plugins)
        """
        if not ocr_engines_dir.exists():
            self.logger.error(f"OCR engines directory not found: {ocr_engines_dir}")
            return False, []
        
        essential_plugins = []
        all_plugins = []
        
        # Scan for OCR engine plugins
        for plugin_dir in ocr_engines_dir.iterdir():
            if not plugin_dir.is_dir() or plugin_dir.name.startswith('__'):
                continue
            
            plugin_json = plugin_dir / "plugin.json"
            if not plugin_json.exists():
                continue
            
            try:
                with open(plugin_json, 'r') as f:
                    metadata = json.load(f)
                
                plugin_name = metadata.get('name', plugin_dir.name)
                all_plugins.append(plugin_name)
                
                # Check if plugin is marked as essential
                if metadata.get('essential', False):
                    essential_plugins.append(plugin_name)
                    self.logger.info(f"Found essential OCR plugin: {plugin_name}")
            
            except Exception as e:
                self.logger.error(f"Error reading plugin metadata for {plugin_dir.name}: {e}")
        
        if not essential_plugins:
            self.logger.error("No essential OCR plugins found!")
            self.logger.error(f"Available plugins: {', '.join(all_plugins) if all_plugins else 'none'}")
            return False, []
        
        self.logger.info(f"Essential OCR plugins available: {', '.join(essential_plugins)}")
        return True, essential_plugins
    
    def validate_essential_plugin_loaded(self, plugin_name: str, plugin_metadata: Dict) -> bool:
        """
        Validate that an essential plugin is loaded and cannot be disabled.
        
        Args:
            plugin_name: Name of the plugin
            plugin_metadata: Plugin metadata dictionary
            
        Returns:
            True if validation passes
        """
        is_essential = plugin_metadata.get('essential', False)
        can_disable = plugin_metadata.get('can_disable', True)
        
        if is_essential and can_disable:
            self.logger.warning(
                f"Plugin {plugin_name} is marked as essential but can_disable=True. "
                f"This is a configuration error - essential plugins should have can_disable=False"
            )
            return False
        
        if is_essential:
            self.logger.info(f"Essential plugin {plugin_name} validated: cannot be disabled")
            reason = plugin_metadata.get('essential_reason', 'No reason provided')
            self.logger.info(f"  Reason: {reason}")
        
        return True
    
    def check_system_requirements(self, app_root: Path) -> Tuple[bool, List[str]]:
        """
        Check all system requirements for essential plugins.
        
        Args:
            app_root: Application root directory
            
        Returns:
            Tuple of (success, list of error messages)
        """
        errors = []
        
        # Check OCR plugins (NEW PLUGIN SYSTEM)
        ocr_plugins_dir = app_root / "plugins" / "ocr"
        success, essential_plugins = self.check_essential_ocr_plugins(ocr_plugins_dir)
        
        if not success:
            errors.append(
                "No essential OCR plugins found. "
                "At least one OCR engine (EasyOCR, Tesseract, PaddleOCR, or Manga OCR) must be available."
            )
        elif len(essential_plugins) == 0:
            errors.append(
                "No OCR engines are marked as essential. "
                "This is a configuration error - at least one OCR engine should be essential."
            )
        
        # Future: Add checks for other essential plugin types
        # - Translation engines
        # - Capture methods
        
        if errors:
            self.logger.error("System requirements check failed:")
            for error in errors:
                self.logger.error(f"  - {error}")
            return False, errors
        
        self.logger.info("✓ All system requirements met")
        return True, []


def validate_system_plugins(app_root: Path = None) -> Tuple[bool, List[str]]:
    """
    Convenience function to validate system plugins.
    
    Args:
        app_root: Application root directory (defaults to current directory)
        
    Returns:
        Tuple of (success, list of error messages)
    """
    if app_root is None:
        app_root = Path(__file__).parent.parent.parent
    
    validator = PluginValidator()
    return validator.check_system_requirements(app_root)
