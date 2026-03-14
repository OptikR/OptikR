"""
Thread-Safe Overlay Wrapper

Wraps the PyQt6 overlay system to make it safe to call from background threads.
Uses Qt signals to ensure all GUI operations happen in the main thread.
"""

import logging
import threading
import time

from PyQt6.QtCore import QObject, pyqtSignal, Qt

logger = logging.getLogger(__name__)

# Monotonic counter for unique translation IDs
_next_id = 0
_next_id_lock = threading.Lock()


class ThreadSafeOverlaySystem(QObject):
    """
    Thread-safe wrapper for overlay system.
    Can be called from any thread — automatically marshals calls to main GUI thread.
    """
    
    # Signals for thread-safe communication
    _show_signal = pyqtSignal(str, str, int, int)       # overlay_id, text, x, y
    _hide_signal = pyqtSignal(str)                       # overlay_id
    _hide_all_signal = pyqtSignal(bool)                  # immediate
    
    def __init__(self, overlay_system):
        """
        Initialize thread-safe wrapper.
        
        Args:
            overlay_system: The actual PyQt6OverlayAdapter instance
        """
        super().__init__()
        self.overlay_system = overlay_system
        
        # Connect signals to slots (runs in main thread via QueuedConnection)
        self._show_signal.connect(self._do_show, Qt.ConnectionType.QueuedConnection)
        self._hide_signal.connect(self._do_hide, Qt.ConnectionType.QueuedConnection)
        self._hide_all_signal.connect(self._do_hide_all, Qt.ConnectionType.QueuedConnection)
        
        logger.info("Thread-safe overlay system initialized")

    # ------------------------------------------------------------------
    # Public API (callable from any thread)
    # ------------------------------------------------------------------

    def show_translation(self, text: str, position: tuple[int, int],
                         translation_id: str | None = None,
                         monitor_id: int | None = None) -> str:
        """
        Show a translation overlay (thread-safe).
        
        Returns:
            Overlay ID
        """
        if translation_id is None:
            global _next_id
            with _next_id_lock:
                _next_id += 1
                translation_id = f"translation_{_next_id}"
        
        x, y = position
        self._show_signal.emit(translation_id, text, x, y)
        return translation_id
    
    def hide_translation(self, translation_id: str):
        """Hide a specific translation overlay (thread-safe)."""
        self._hide_signal.emit(translation_id)
    
    def hide_all_translations(self, immediate: bool = False):
        """
        Hide all translation overlays (thread-safe).
        
        Args:
            immediate: If True, hide immediately without animation
        """
        # Direct call if already on main thread (e.g. during shutdown)
        from PyQt6.QtWidgets import QApplication
        from PyQt6.QtCore import QThread
        if QThread.currentThread() == QApplication.instance().thread():
            logger.debug("hide_all_translations: already on main thread, calling directly")
            self._do_hide_all(immediate)
        else:
            logger.debug("hide_all_translations: on worker thread, using signal")
            self._hide_all_signal.emit(immediate)
    
    def reload_config(self):
        """Reload overlay configuration from config manager."""
        self.overlay_system.reload_config()
    
    def cleanup(self):
        """Cleanup overlay system."""
        self.overlay_system.cleanup()

    # ------------------------------------------------------------------
    # Slots (run in main thread)
    # ------------------------------------------------------------------

    def _do_show(self, overlay_id: str, text: str, x: int, y: int):
        """Actually show overlay (runs in main thread)."""
        try:
            self.overlay_system.show_translation(text, (x, y), overlay_id, None)
            logger.debug("Overlay shown: '%s' at (%d, %d)", text[:30], x, y)
        except Exception:
            logger.exception("Error showing overlay")
    
    def _do_hide(self, overlay_id: str):
        """Actually hide overlay (runs in main thread)."""
        try:
            self.overlay_system.hide_translation(overlay_id)
        except Exception:
            logger.exception("Error hiding overlay '%s'", overlay_id)
    
    def _do_hide_all(self, immediate: bool = False):
        """Actually hide all overlays (runs in main thread)."""
        try:
            self.overlay_system.hide_all_translations(immediate=immediate)
            logger.debug("All overlays hidden (immediate=%s)", immediate)
        except Exception:
            logger.exception("Error hiding all overlays")


def create_thread_safe_overlay_system(config_manager=None):
    """
    Factory function to create thread-safe overlay system.
    
    Args:
        config_manager: Optional configuration manager
        
    Returns:
        ThreadSafeOverlaySystem instance
    """
    from ui.overlays.overlay_adapter import create_overlay_system
    
    overlay_system = create_overlay_system(config_manager)
    return ThreadSafeOverlaySystem(overlay_system)
