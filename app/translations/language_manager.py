"""
Language Manager - Central language change coordination

Provides a signal-based system for notifying all UI components
when the language changes, enabling dynamic translation updates.
"""

from PyQt6.QtCore import QObject, pyqtSignal


class LanguageManager(QObject):
    """
    Manages language changes and notifies all registered components.
    
    Emits language_changed signal when language is changed,
    allowing UI components to update their translations dynamically.
    """
    
    language_changed = pyqtSignal(str)  # Emits new language code
    
    def __init__(self):
        super().__init__()
        self.current_language = "en"
    
    def set_language(self, lang_code: str):
        """
        Set the current language and notify all listeners.
        
        Args:
            lang_code: Language code (e.g., 'en', 'de', 'fr')
        """
        if lang_code != self.current_language:
            old_language = self.current_language
            self.current_language = lang_code
            
            # Update the translation system
            from app.translations.translations import set_language
            set_language(lang_code)
            
            # Notify all listeners
            self.language_changed.emit(lang_code)
            
            print(f"[LanguageManager] Language changed: {old_language} -> {lang_code}")
    
    def get_current_language(self) -> str:
        """Get the current language code."""
        return self.current_language


# Global singleton instance
_language_manager = None


def get_language_manager() -> LanguageManager:
    """Get the global language manager instance."""
    global _language_manager
    if _language_manager is None:
        _language_manager = LanguageManager()
    return _language_manager
