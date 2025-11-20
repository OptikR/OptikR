"""
Translatable Mixin - Auto-updating translation support for widgets

Provides a mixin class that allows widgets to automatically update
their text when the language changes.
"""

from typing import Dict, Tuple, Any
from PyQt6.QtWidgets import QWidget


class TranslatableMixin:
    """
    Mixin for widgets that need automatic translation updates.
    
    Usage:
        class MyWidget(TranslatableMixin, QWidget):
            def __init__(self):
                super().__init__()
                
                label = QLabel()
                self.set_translatable_text(label, "my_translation_key")
                
                # With formatting
                self.set_translatable_text(label, "welcome_message", name="User")
    """
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._translation_keys: Dict[Any, Tuple[str, dict]] = {}
        self._connected_to_language_manager = False
    
    def _ensure_language_connection(self):
        """Ensure we're connected to language change signals."""
        if not self._connected_to_language_manager:
            from app.translations.language_manager import get_language_manager
            language_manager = get_language_manager()
            language_manager.language_changed.connect(self._update_translations)
            self._connected_to_language_manager = True
    
    def set_translatable_text(self, widget, key: str, **format_args):
        """
        Set text that will auto-update on language change.
        
        Args:
            widget: The widget to update (QLabel, QPushButton, QGroupBox, etc.)
            key: Translation key from translations.py
            **format_args: Optional formatting arguments for the translation
        """
        self._ensure_language_connection()
        self._translation_keys[widget] = (key, format_args)
        self._update_widget_text(widget, key, format_args)
    
    def set_translatable_title(self, key: str, **format_args):
        """
        Set window title that will auto-update on language change.
        
        Args:
            key: Translation key from translations.py
            **format_args: Optional formatting arguments for the translation
        """
        self._ensure_language_connection()
        self._translation_keys['__window_title__'] = (key, format_args)
        self._update_window_title(key, format_args)
    
    def _update_widget_text(self, widget, key: str, format_args: dict):
        """Update a single widget's text."""
        from app.translations.translations import tr
        
        try:
            text = tr(key, **format_args)
            
            # Handle different widget types
            if hasattr(widget, 'setText'):
                widget.setText(text)
            elif hasattr(widget, 'setTitle'):
                widget.setTitle(text)
            elif hasattr(widget, 'setWindowTitle'):
                widget.setWindowTitle(text)
            elif hasattr(widget, 'setPlaceholderText'):
                widget.setPlaceholderText(text)
        except Exception as e:
            # Silently fail - translation updates are not critical
            pass
    
    def _update_window_title(self, key: str, format_args: dict):
        """Update window title."""
        from app.translations.translations import tr
        
        try:
            text = tr(key, **format_args)
            if hasattr(self, 'setWindowTitle'):
                self.setWindowTitle(text)
        except Exception as e:
            # Silently fail - translation updates are not critical
            pass
    
    def _update_translations(self, lang_code: str):
        """Update all registered widgets when language changes."""
        for widget_or_key, (key, format_args) in self._translation_keys.items():
            if widget_or_key == '__window_title__':
                self._update_window_title(key, format_args)
            else:
                self._update_widget_text(widget_or_key, key, format_args)
    
    def clear_translations(self):
        """Clear all registered translations (useful for cleanup)."""
        self._translation_keys.clear()
