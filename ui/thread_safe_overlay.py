"""
Thread-Safe Overlay Wrapper

Wraps the PyQt6 overlay system to make it safe to call from background threads.
Uses Qt signals to ensure all GUI operations happen in the main thread.
"""

from PyQt6.QtCore import QObject, pyqtSignal, QMetaObject, Qt, Q_ARG
from typing import Tuple, Optional
import logging


class ThreadSafeOverlaySystem(QObject):
    """
    Thread-safe wrapper for overlay system.
    
    Can be called from any thread - automatically marshals calls to main GUI thread.
    """
    
    # Signals for thread-safe communication
    _show_overlay_signal = pyqtSignal(str, str, int, int)  # overlay_id, text, x, y
    _hide_overlay_signal = pyqtSignal(str)  # overlay_id
    _hide_all_signal = pyqtSignal(bool)  # immediate
    _update_overlay_signal = pyqtSignal(str, str, int, int)  # overlay_id, text, x, y
    
    def __init__(self, overlay_system):
        """
        Initialize thread-safe wrapper.
        
        Args:
            overlay_system: The actual PyQt6OverlayAdapter instance
        """
        super().__init__()
        self.overlay_system = overlay_system
        self.logger = logging.getLogger(__name__)
        
        # Connect signals to actual overlay methods (in main thread)
        self._show_overlay_signal.connect(self._do_show_overlay, Qt.ConnectionType.QueuedConnection)
        self._hide_overlay_signal.connect(self._do_hide_overlay, Qt.ConnectionType.QueuedConnection)
        self._hide_all_signal.connect(self._do_hide_all, Qt.ConnectionType.QueuedConnection)
        self._update_overlay_signal.connect(self._do_update_overlay, Qt.ConnectionType.QueuedConnection)
        
        self.logger.info("Thread-safe overlay system initialized")
    
    def show_translation(self, text: str, position: Tuple[int, int], 
                        translation_id: Optional[str] = None,
                        monitor_id: Optional[int] = None) -> str:
        """
        Show a translation overlay (thread-safe).
        
        Args:
            text: Translation text to display
            position: (x, y) screen position
            translation_id: Optional ID (auto-generated if not provided)
            monitor_id: Optional monitor ID
            
        Returns:
            Overlay ID
        """
        if translation_id is None:
            import time
            translation_id = f"translation_{int(time.time() * 1000)}"
        
        x, y = position
        
        # Use signal for thread-safe communication (simpler and more reliable than invokeMethod)
        self._show_overlay_signal.emit(translation_id, text, x, y)
        
        return translation_id
    
    def hide_translation(self, translation_id: str):
        """Hide a specific translation overlay (thread-safe)."""
        self._hide_overlay_signal.emit(translation_id)
    
    def hide_all_translations(self, immediate: bool = False):
        """
        Hide all translation overlays (thread-safe).
        
        Args:
            immediate: If True, hide immediately without animation (faster, prevents errors)
        """
        print(f"[THREAD-SAFE] hide_all_translations called (immediate={immediate})")
        print(f"[THREAD-SAFE] Current thread: {QObject.thread(self)}")
        print(f"[THREAD-SAFE] Emitting signal...")
        
        # Try direct call if we're already on main thread
        from PyQt6.QtWidgets import QApplication
        from PyQt6.QtCore import QThread
        if QThread.currentThread() == QApplication.instance().thread():
            print(f"[THREAD-SAFE] Already on main thread, calling directly")
            self._do_hide_all(immediate)
        else:
            print(f"[THREAD-SAFE] On worker thread, using signal")
            self._hide_all_signal.emit(immediate)
    
    def update_translation(self, translation_id: str, text: Optional[str] = None,
                          position: Optional[Tuple[int, int]] = None):
        """Update an existing translation overlay (thread-safe)."""
        if text and position:
            x, y = position
            self._update_overlay_signal.emit(translation_id, text, x, y)
    
    # Slot methods (run in main thread)
    def _do_show_overlay(self, overlay_id: str, text: str, x: int, y: int):
        """Actually show overlay (runs in main thread)."""
        try:
            print(f"[THREAD-SAFE] Showing overlay '{text[:20]}' at ({x}, {y})")
            self.overlay_system.show_translation(text, (x, y), overlay_id, None)
            print(f"[THREAD-SAFE] Overlay shown successfully")
        except Exception as e:
            print(f"[THREAD-SAFE] ERROR showing overlay: {e}")
            self.logger.error(f"Error showing overlay: {e}")
            import traceback
            traceback.print_exc()
    
    def _do_hide_overlay(self, overlay_id: str):
        """Actually hide overlay (runs in main thread)."""
        try:
            self.overlay_system.hide_translation(overlay_id)
        except Exception as e:
            self.logger.error(f"Error hiding overlay: {e}")
    
    def _do_hide_all(self, immediate: bool = False):
        """Actually hide all overlays (runs in main thread)."""
        try:
            print(f"[THREAD-SAFE] _do_hide_all executing on main thread (immediate={immediate})")
            self.overlay_system.hide_all_translations(immediate=immediate)
            print(f"[THREAD-SAFE] _do_hide_all completed")
        except Exception as e:
            self.logger.error(f"Error hiding all overlays: {e}")
            import traceback
            traceback.print_exc()
    
    def _do_update_overlay(self, overlay_id: str, text: str, x: int, y: int):
        """Actually update overlay (runs in main thread)."""
        try:
            self.overlay_system.update_translation(overlay_id, text, (x, y))
        except Exception as e:
            self.logger.error(f"Error updating overlay: {e}")
    
    # Pass-through methods for non-GUI operations
    def is_visible(self, translation_id: str) -> bool:
        """Check if translation is visible."""
        return self.overlay_system.is_visible(translation_id)
    
    def get_active_count(self) -> int:
        """Get number of active overlays."""
        return self.overlay_system.get_active_count()
    
    def get_performance_stats(self):
        """Get performance statistics."""
        return self.overlay_system.get_performance_stats()
    
    def reload_config(self):
        """Reload overlay configuration from config manager."""
        self.overlay_system.reload_config()
    
    def cleanup(self):
        """Cleanup overlay system."""
        self.overlay_system.cleanup()


def create_thread_safe_overlay_system(config_manager=None):
    """
    Factory function to create thread-safe overlay system.
    
    Args:
        config_manager: Optional configuration manager
        
    Returns:
        ThreadSafeOverlaySystem instance
    """
    from ui.overlay_integration import create_overlay_system
    
    # Create the actual overlay system
    overlay_system = create_overlay_system(config_manager)
    
    # Wrap it in thread-safe wrapper
    return ThreadSafeOverlaySystem(overlay_system)
