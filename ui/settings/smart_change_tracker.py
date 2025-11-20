"""
Smart Change Tracker Mixin

Provides intelligent change detection for settings tabs.
Only triggers "settings changed" when values actually differ from saved state.
"""


class SmartChangeTrackerMixin:
    """
    Mixin to add smart change tracking to settings tabs.
    
    Usage:
    1. Add this mixin to your tab class
    2. Call self._init_change_tracker() in __init__
    3. Implement self._get_current_state() to return dict of current settings
    4. Call self._save_original_state() after load_config
    5. Call self._update_original_state() after save_config
    6. Replace on_change() with self._on_change_smart()
    """
    
    def _init_change_tracker(self):
        """Initialize the change tracker."""
        self._original_state = {}
    
    def _get_current_state(self):
        """
        Get current state of all settings.
        
        Override this method in your tab class to return a dict
        of all current setting values.
        
        Returns:
            dict: Current state of all settings
        """
        raise NotImplementedError("Subclass must implement _get_current_state()")
    
    def _save_original_state(self):
        """Save the current state as the original state."""
        self._original_state = self._get_current_state()
    
    def _update_original_state(self):
        """Update the original state (call after saving config)."""
        self._original_state = self._get_current_state()
    
    def _on_change_smart(self):
        """
        Smart change handler - only emits signal if actually changed.
        
        Call this instead of directly emitting settingChanged.
        """
        current_state = self._get_current_state()
        
        if current_state != self._original_state:
            # Settings actually changed from saved state
            if hasattr(self, 'settingChanged'):
                self.settingChanged.emit()
        # If states match, don't emit signal (no unsaved changes)
