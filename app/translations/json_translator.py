"""
JSON-based Translation System for OptikR

This module provides a flexible, user-friendly translation system that:
- Loads translations from JSON files
- Supports user-provided custom languages
- Falls back to English for missing translations
- Allows hot-reloading of language packs
"""

import json
from pathlib import Path
from typing import Dict, Any, Optional
import threading


class JSONTranslator:
    """
    JSON-based translator with support for:
    - Multiple language packs
    - User-provided custom languages
    - Nested key access (e.g., "ui.buttons.save")
    - Parameter substitution
    - Fallback to English
    - Thread-safe operations
    """
    
    def __init__(self, locales_dir: Optional[str] = None):
        if locales_dir is None:
            # Default to app/translations/locales
            locales_dir = Path(__file__).parent / "locales"
        
        self.locales_dir = Path(locales_dir)
        self.current_language = "en"
        self.translations: Dict[str, Dict[str, Any]] = {}
        self.available_languages: Dict[str, str] = {}
        self._lock = threading.RLock()
        
        # Ensure locales directory exists
        self.locales_dir.mkdir(parents=True, exist_ok=True)
        
        # Load all available language packs
        self._discover_languages()
        self._load_language("en")  # Always load English as fallback
    
    def _discover_languages(self):
        """Discover all available language packs."""
        if not self.locales_dir.exists():
            return
        
        with self._lock:
            # Check main locales directory
            for json_file in self.locales_dir.glob("*.json"):
                self._register_language_file(json_file)
            
            # Check custom directory for user-provided languages
            custom_dir = self.locales_dir / "custom"
            if custom_dir.exists():
                for json_file in custom_dir.glob("*.json"):
                    self._register_language_file(json_file, is_custom=True)
    
    def _register_language_file(self, json_file: Path, is_custom: bool = False):
        """Register a language file."""
        lang_code = json_file.stem
        try:
            with open(json_file, 'r', encoding='utf-8') as f:
                data = json.load(f)
                metadata = data.get('_metadata', {})
                lang_name = metadata.get('language_name', lang_code.upper())
                
                if is_custom:
                    lang_name += " (Custom)"
                
                self.available_languages[lang_code] = lang_name
        except Exception as e:
            print(f"[WARNING] Failed to register {json_file}: {e}")
    
    def _load_language(self, lang_code: str) -> bool:
        """Load a language pack into memory."""
        # Try main locales directory first
        json_file = self.locales_dir / f"{lang_code}.json"
        
        # Try custom directory if not found
        if not json_file.exists():
            json_file = self.locales_dir / "custom" / f"{lang_code}.json"
        
        if not json_file.exists():
            print(f"[WARNING] Language pack not found: {lang_code}")
            return False
        
        try:
            with open(json_file, 'r', encoding='utf-8') as f:
                data = json.load(f)
            
            with self._lock:
                self.translations[lang_code] = data.get('translations', {})
            
            return True
        except Exception as e:
            print(f"[ERROR] Failed to load {lang_code}: {e}")
            return False
    
    def set_language(self, lang_code: str):
        """Set the current language."""
        with self._lock:
            if lang_code not in self.translations:
                if not self._load_language(lang_code):
                    print(f"[WARNING] Failed to set language to {lang_code}, using English")
                    return
            
            self.current_language = lang_code
            print(f"[INFO] Language changed to: {lang_code}")
    
    def get_current_language(self) -> str:
        """Get the current language code."""
        with self._lock:
            return self.current_language
    
    def tr(self, key: str, **kwargs) -> str:
        """
        Translate a key.
        
        Args:
            key: Translation key (can be nested with dots or flat)
            **kwargs: Parameters for string formatting
        
        Returns:
            Translated string with parameters substituted
        
        Examples:
            tr("save")  # Returns "Save"
            tr("buttons.save")  # Also works if organized
            tr("error_message", error="File not found")
        """
        with self._lock:
            # Try current language
            translation = self._get_translation(self.current_language, key)
            
            # Fallback to English
            if translation is None and self.current_language != "en":
                translation = self._get_translation("en", key)
            
            # Fallback to key itself
            if translation is None:
                translation = key
            
            # Substitute parameters
            if kwargs:
                try:
                    translation = translation.format(**kwargs)
                except (KeyError, ValueError) as e:
                    print(f"[WARNING] Failed to format translation '{key}': {e}")
            
            return translation
    
    def _get_translation(self, lang_code: str, key: str) -> Optional[str]:
        """Get translation for a specific language and key."""
        if lang_code not in self.translations:
            return None
        
        translations = self.translations[lang_code]
        
        # Try direct key first (flat structure)
        if key in translations:
            return translations[key]
        
        # Try nested key (e.g., "buttons.save")
        if '.' in key:
            parts = key.split('.')
            value = translations
            for part in parts:
                if isinstance(value, dict) and part in value:
                    value = value[part]
                else:
                    return None
            
            if isinstance(value, str):
                return value
        
        return None
    
    def get_available_languages(self) -> Dict[str, str]:
        """Get dictionary of available languages {code: name}."""
        with self._lock:
            return self.available_languages.copy()
    
    def reload_languages(self):
        """Reload all language packs (useful for hot-reload)."""
        with self._lock:
            self.translations.clear()
            self.available_languages.clear()
            self._discover_languages()
            self._load_language("en")
            if self.current_language != "en":
                self._load_language(self.current_language)
    
    def export_template(self, output_file: str, lang_code: str = "en") -> bool:
        """Export a language template for users to translate."""
        with self._lock:
            if lang_code not in self.translations:
                print(f"[ERROR] Language {lang_code} not loaded")
                return False
            
            try:
                # Create template with metadata
                template = {
                    "_metadata": {
                        "language_code": "NEW",
                        "language_name": "New Language",
                        "version": "1.0.0",
                        "author": "Your Name",
                        "last_updated": "2025-11-18",
                        "total_keys": len(self.translations[lang_code])
                    },
                    "translations": self.translations[lang_code]
                }
                
                with open(output_file, 'w', encoding='utf-8') as f:
                    json.dump(template, f, indent=2, ensure_ascii=False)
                
                print(f"[SUCCESS] Template exported to: {output_file}")
                return True
            except Exception as e:
                print(f"[ERROR] Failed to export template: {e}")
                return False
    
    def import_language_pack(self, json_file: str, custom: bool = True) -> bool:
        """
        Import a user-provided language pack.
        
        Args:
            json_file: Path to JSON language pack
            custom: If True, save to custom directory
        
        Returns:
            True if successful
        """
        try:
            # Load and validate
            with open(json_file, 'r', encoding='utf-8') as f:
                data = json.load(f)
            
            # Check for metadata
            if '_metadata' not in data:
                print("[WARNING] Language pack missing metadata")
                return False
            
            metadata = data['_metadata']
            lang_code = metadata.get('language_code')
            lang_name = metadata.get('language_name')
            
            if not lang_code or not lang_name:
                print("[ERROR] Invalid metadata: missing language_code or language_name")
                return False
            
            # Check for translations
            if 'translations' not in data:
                print("[ERROR] Language pack missing translations")
                return False
            
            # Determine save location
            if custom:
                save_dir = self.locales_dir / "custom"
                save_dir.mkdir(parents=True, exist_ok=True)
            else:
                save_dir = self.locales_dir
            
            save_path = save_dir / f"{lang_code}.json"
            
            # Save the language pack
            with open(save_path, 'w', encoding='utf-8') as f:
                json.dump(data, f, indent=2, ensure_ascii=False)
            
            # Load it into memory
            with self._lock:
                self.translations[lang_code] = data['translations']
                self.available_languages[lang_code] = lang_name + (" (Custom)" if custom else "")
            
            print(f"[SUCCESS] Imported language pack: {lang_name} ({lang_code})")
            return True
            
        except Exception as e:
            print(f"[ERROR] Failed to import language pack: {e}")
            import traceback
            traceback.print_exc()
            return False


# Global translator instance
_translator: Optional[JSONTranslator] = None
_init_lock = threading.Lock()


def init_translator(locales_dir: Optional[str] = None):
    """Initialize the global translator."""
    global _translator
    with _init_lock:
        if _translator is None:
            _translator = JSONTranslator(locales_dir)


def get_translator() -> JSONTranslator:
    """Get the global translator instance."""
    if _translator is None:
        init_translator()
    return _translator


def set_language(lang_code: str):
    """Set the current language."""
    get_translator().set_language(lang_code)


def get_current_language() -> str:
    """Get the current language code."""
    return get_translator().get_current_language()


def tr(key: str, **kwargs) -> str:
    """Translate a key."""
    return get_translator().tr(key, **kwargs)


def get_available_languages() -> Dict[str, str]:
    """Get available languages."""
    return get_translator().get_available_languages()


def reload_languages():
    """Reload all language packs."""
    get_translator().reload_languages()


def export_template(output_file: str, lang_code: str = "en") -> bool:
    """Export a language template."""
    return get_translator().export_template(output_file, lang_code)


def import_language_pack(json_file: str, custom: bool = True) -> bool:
    """Import a language pack."""
    return get_translator().import_language_pack(json_file, custom)


# Backward compatibility with old system
class Translator:
    """Backward compatibility wrapper."""
    
    def __init__(self, language: str = "en"):
        self.set_language(language)
    
    def set_language(self, language: str):
        set_language(language)
    
    def tr(self, key: str, *args) -> str:
        # Convert positional args to kwargs if needed
        if args:
            return tr(key).format(*args)
        return tr(key)


# For backward compatibility
TRANSLATIONS = {}  # Empty dict, not used anymore
