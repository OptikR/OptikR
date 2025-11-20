"""
Plugin Translation System

Allows plugins to provide their own translations that integrate
with the main translation system.

Plugins must provide an English translation file (en.json) which serves as:
1. The base translation
2. A template for users to translate to other languages
"""

import json
from pathlib import Path
from typing import Dict, Optional
import threading

from .json_translator import get_translator


class PluginTranslationManager:
    """
    Manages translations for plugins.
    
    Each plugin can provide translation files in:
    plugins/{plugin_name}/translations/
    ├── en.json (REQUIRED - English base)
    ├── de.json (optional)
    ├── fr.json (optional)
    └── ... (other languages)
    
    The English file serves as both the translation and a template
    for users to create their own translations.
    """
    
    def __init__(self):
        self.plugin_translations: Dict[str, Dict[str, Dict[str, str]]] = {}
        self._lock = threading.RLock()
    
    def register_plugin(self, plugin_name: str, plugin_dir: Path) -> bool:
        """
        Register a plugin's translations.
        
        Args:
            plugin_name: Name of the plugin
            plugin_dir: Path to plugin directory
        
        Returns:
            True if successful, False otherwise
        
        Note:
            Plugins MUST provide en.json (English translation).
            This serves as both the translation and a template.
        """
        translations_dir = plugin_dir / "translations"
        
        if not translations_dir.exists():
            print(f"[PLUGIN TRANSLATION] No translations directory for plugin: {plugin_name}")
            return False
        
        # Check for required English translation
        en_file = translations_dir / "en.json"
        if not en_file.exists():
            print(f"[PLUGIN TRANSLATION ERROR] Plugin '{plugin_name}' missing required en.json")
            print(f"[PLUGIN TRANSLATION ERROR] Plugins MUST provide English translation as base/template")
            return False
        
        # Load all available translations for this plugin
        plugin_langs = {}
        
        for json_file in translations_dir.glob("*.json"):
            lang_code = json_file.stem
            
            try:
                with open(json_file, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                
                # Extract translations (support both flat and nested structure)
                if 'translations' in data:
                    translations = data['translations']
                else:
                    translations = data
                
                plugin_langs[lang_code] = translations
                print(f"[PLUGIN TRANSLATION] Loaded {lang_code} for plugin: {plugin_name}")
                
            except Exception as e:
                print(f"[PLUGIN TRANSLATION WARNING] Failed to load {json_file}: {e}")
        
        # Store plugin translations
        with self._lock:
            self.plugin_translations[plugin_name] = plugin_langs
        
        print(f"[PLUGIN TRANSLATION] Registered plugin '{plugin_name}' with {len(plugin_langs)} languages")
        return True
    
    def unregister_plugin(self, plugin_name: str):
        """Unregister a plugin's translations."""
        with self._lock:
            if plugin_name in self.plugin_translations:
                del self.plugin_translations[plugin_name]
                print(f"[PLUGIN TRANSLATION] Unregistered plugin: {plugin_name}")
    
    def get_plugin_translation(self, plugin_name: str, key: str, lang_code: Optional[str] = None) -> Optional[str]:
        """
        Get a translation for a plugin.
        
        Args:
            plugin_name: Name of the plugin
            key: Translation key
            lang_code: Language code (if None, uses current language)
        
        Returns:
            Translated string or None if not found
        """
        if lang_code is None:
            translator = get_translator()
            lang_code = translator.get_current_language()
        
        with self._lock:
            if plugin_name not in self.plugin_translations:
                return None
            
            plugin_langs = self.plugin_translations[plugin_name]
            
            # Try requested language
            if lang_code in plugin_langs:
                if key in plugin_langs[lang_code]:
                    return plugin_langs[lang_code][key]
            
            # Fallback to English
            if 'en' in plugin_langs:
                if key in plugin_langs['en']:
                    return plugin_langs['en'][key]
            
            return None
    
    def export_plugin_template(self, plugin_name: str, output_file: str) -> bool:
        """
        Export a plugin's English translation as a template.
        
        Args:
            plugin_name: Name of the plugin
            output_file: Path to save template
        
        Returns:
            True if successful
        """
        with self._lock:
            if plugin_name not in self.plugin_translations:
                print(f"[PLUGIN TRANSLATION ERROR] Plugin not registered: {plugin_name}")
                return False
            
            plugin_langs = self.plugin_translations[plugin_name]
            
            if 'en' not in plugin_langs:
                print(f"[PLUGIN TRANSLATION ERROR] Plugin missing English translation: {plugin_name}")
                return False
            
            try:
                template = {
                    "_metadata": {
                        "plugin_name": plugin_name,
                        "language_code": "NEW",
                        "language_name": "New Language",
                        "version": "1.0.0",
                        "author": "Your Name",
                        "description": f"Translation template for {plugin_name} plugin"
                    },
                    "translations": plugin_langs['en']
                }
                
                with open(output_file, 'w', encoding='utf-8') as f:
                    json.dump(template, f, indent=2, ensure_ascii=False)
                
                print(f"[PLUGIN TRANSLATION] Exported template for {plugin_name} to: {output_file}")
                return True
                
            except Exception as e:
                print(f"[PLUGIN TRANSLATION ERROR] Failed to export template: {e}")
                return False
    
    def import_plugin_translation(self, plugin_name: str, json_file: str) -> bool:
        """
        Import a user-provided translation for a plugin.
        
        Args:
            plugin_name: Name of the plugin
            json_file: Path to translation file
        
        Returns:
            True if successful
        """
        try:
            with open(json_file, 'r', encoding='utf-8') as f:
                data = json.load(f)
            
            # Validate
            if '_metadata' not in data:
                print("[PLUGIN TRANSLATION ERROR] Missing metadata")
                return False
            
            metadata = data['_metadata']
            lang_code = metadata.get('language_code')
            
            if not lang_code:
                print("[PLUGIN TRANSLATION ERROR] Missing language_code in metadata")
                return False
            
            if 'translations' not in data:
                print("[PLUGIN TRANSLATION ERROR] Missing translations")
                return False
            
            # Add to plugin translations
            with self._lock:
                if plugin_name not in self.plugin_translations:
                    self.plugin_translations[plugin_name] = {}
                
                self.plugin_translations[plugin_name][lang_code] = data['translations']
            
            print(f"[PLUGIN TRANSLATION] Imported {lang_code} for plugin: {plugin_name}")
            return True
            
        except Exception as e:
            print(f"[PLUGIN TRANSLATION ERROR] Failed to import: {e}")
            return False
    
    def get_available_languages(self, plugin_name: str) -> list:
        """Get list of available languages for a plugin."""
        with self._lock:
            if plugin_name not in self.plugin_translations:
                return []
            return list(self.plugin_translations[plugin_name].keys())


# Global plugin translation manager
_plugin_manager: Optional[PluginTranslationManager] = None
_manager_lock = threading.Lock()


def get_plugin_manager() -> PluginTranslationManager:
    """Get the global plugin translation manager."""
    global _plugin_manager
    with _manager_lock:
        if _plugin_manager is None:
            _plugin_manager = PluginTranslationManager()
        return _plugin_manager


def register_plugin(plugin_name: str, plugin_dir: Path) -> bool:
    """Register a plugin's translations."""
    return get_plugin_manager().register_plugin(plugin_name, plugin_dir)


def unregister_plugin(plugin_name: str):
    """Unregister a plugin's translations."""
    get_plugin_manager().unregister_plugin(plugin_name)


def plugin_tr(plugin_name: str, key: str, lang_code: Optional[str] = None) -> str:
    """
    Translate a plugin string.
    
    Args:
        plugin_name: Name of the plugin
        key: Translation key
        lang_code: Language code (optional)
    
    Returns:
        Translated string, or key if not found
    """
    translation = get_plugin_manager().get_plugin_translation(plugin_name, key, lang_code)
    return translation if translation is not None else key


def export_plugin_template(plugin_name: str, output_file: str) -> bool:
    """Export a plugin's translation template."""
    return get_plugin_manager().export_plugin_template(plugin_name, output_file)


def import_plugin_translation(plugin_name: str, json_file: str) -> bool:
    """Import a plugin translation."""
    return get_plugin_manager().import_plugin_translation(plugin_name, json_file)


def get_plugin_languages(plugin_name: str) -> list:
    """Get available languages for a plugin."""
    return get_plugin_manager().get_available_languages(plugin_name)
