"""
Overlay Integration Module

Provides easy integration between the pipeline and PyQt6 overlay system.
Drop-in replacement for the old Tkinter overlay system.
"""

from typing import Optional, Dict, Any, Tuple, List
from .overlay_pyqt6 import (
    OverlayManager, OverlayConfig, OverlayStyle, OverlayPresets,
    OverlayPosition, AnimationType, TranslationOverlay
)


class PyQt6OverlayAdapter:
    """
    Adapter to make PyQt6 overlay system compatible with existing pipeline.
    
    Provides the same interface as the old Tkinter overlay system for
    seamless migration.
    """
    
    def __init__(self, config_manager=None):
        """
        Initialize overlay adapter.
        
        Args:
            config_manager: Configuration manager for loading settings
        """
        self.config_manager = config_manager
        
        # Create overlay manager with default config
        default_config = self._load_config_from_manager()
        self.manager = OverlayManager(config=default_config)
        
        # Track overlay IDs
        self.next_overlay_id = 0
        
        # Multi-monitor support
        self.monitor_info = self._detect_monitors()
        self.overlay_monitor_map: Dict[str, int] = {}  # overlay_id -> monitor_id
    
    def _detect_monitors(self) -> List[Dict]:
        """Detect available monitors and their positions."""
        from PyQt6.QtWidgets import QApplication
        
        app = QApplication.instance()
        if not app:
            return []
        
        screens = app.screens()
        monitors = []
        
        for i, screen in enumerate(screens):
            geometry = screen.geometry()
            monitors.append({
                'index': i,
                'name': screen.name(),
                'x': geometry.x(),
                'y': geometry.y(),
                'width': geometry.width(),
                'height': geometry.height(),
                'is_primary': (screen == app.primaryScreen()),
                'dpi': screen.logicalDotsPerInch()
            })
        
        return monitors
    
    def _get_monitor_for_position(self, x: int, y: int) -> int:
        """
        Determine which monitor a position belongs to.
        
        Args:
            x: X coordinate
            y: Y coordinate
            
        Returns:
            Monitor index
        """
        for monitor in self.monitor_info:
            if (monitor['x'] <= x < monitor['x'] + monitor['width'] and
                monitor['y'] <= y < monitor['y'] + monitor['height']):
                return monitor['index']
        
        # Default to primary monitor
        return 0
    
    def _load_config_from_manager(self) -> OverlayConfig:
        """Load overlay configuration from config manager."""
        if not self.config_manager:
            return OverlayConfig()
        
        # Load style settings
        print("[OVERLAY CONFIG] Loading overlay configuration from config manager...")
        
        # Load colors (support both hex and comma-separated formats)
        bg_color_str = self.config_manager.get_setting('overlay.background_color', '#000000')
        text_color_str = self.config_manager.get_setting('overlay.font_color', '#FFFFFF')  # Note: config uses 'font_color'
        border_color_str = self.config_manager.get_setting('overlay.border_color', '#646464')  # Gray default
        
        print(f"[OVERLAY CONFIG] background_color from config: '{bg_color_str}'")
        print(f"[OVERLAY CONFIG] text_color from config: '{text_color_str}'")
        print(f"[OVERLAY CONFIG] border_color from config: '{border_color_str}'")
        
        # Parse colors
        text_color = self._parse_color(text_color_str)
        bg_color = self._parse_color(bg_color_str)
        border_color = self._parse_color(border_color_str)
        
        # Load transparency and apply to background
        transparency = self.config_manager.get_setting('overlay.transparency', 0.8)
        bg_color = (bg_color[0], bg_color[1], bg_color[2], int(transparency * 255))
        
        print(f"[OVERLAY CONFIG] Parsed text_color: {text_color}")
        print(f"[OVERLAY CONFIG] Parsed bg_color: {bg_color} (with transparency {transparency})")
        print(f"[OVERLAY CONFIG] Parsed border_color: {border_color}")
        
        # Load font settings
        font_family = self.config_manager.get_setting('overlay.font_family', 'Segoe UI')
        font_size = self.config_manager.get_setting('overlay.font_size', 14)
        
        # Load border settings
        rounded_corners = self.config_manager.get_setting('overlay.rounded_corners', True)
        border_radius = 8 if rounded_corners else 0
        
        print(f"[OVERLAY CONFIG] Font: {font_family} {font_size}px")
        print(f"[OVERLAY CONFIG] Border radius: {border_radius}px (rounded_corners={rounded_corners})")
        
        style = OverlayStyle(
            # Font
            font_family=font_family,
            font_size=font_size,
            font_weight='normal',  # Always normal (bold was hardcoded before)
            font_italic=False,  # Always false (italic was hardcoded before)
            
            # Colors
            text_color=text_color,
            background_color=bg_color,
            border_color=border_color,
            
            # Border
            border_enabled=True,  # Always enabled for now
            border_width=2,  # Fixed width for now
            border_radius=border_radius,
            
            # Shadow
            shadow_enabled=True,  # Always enabled for now
            shadow_blur_radius=15,
            shadow_color=(0, 0, 0, 180),
            shadow_offset=(2, 2),
            
            # Other
            opacity=self.config_manager.get_setting('overlay.opacity', 0.9),
            max_width=self.config_manager.get_setting('overlay.max_width', 800),
            max_height=self.config_manager.get_setting('overlay.max_height', 400),
            word_wrap=True,
            padding=12
        )
        
        print("[OVERLAY CONFIG] OverlayStyle created successfully")
        print(f"[OVERLAY CONFIG] Final style - Font: {style.font_family} {style.font_size}px")
        print(f"[OVERLAY CONFIG] Final style - Text: {style.text_color}, BG: {style.background_color}, Border: {style.border_color}")
        
        # Load overlay config
        # Note: interactive_on_hover means overlay is click-through by default, 
        # but becomes interactive when mouse hovers over it
        interactive_on_hover = self.config_manager.get_setting('overlay.interactive_on_hover', False)
        
        config = OverlayConfig(
            style=style,
            click_through=True,  # Always start as click-through
            interactive_on_hover=interactive_on_hover,  # Toggle on hover if enabled
            always_on_top=self.config_manager.get_setting('overlay.always_on_top', True),
            animation_in=AnimationType[self.config_manager.get_setting('overlay.animation_in', 'FADE').upper()],
            animation_out=AnimationType[self.config_manager.get_setting('overlay.animation_out', 'FADE').upper()],
            animation_duration=self.config_manager.get_setting('overlay.animation_duration', 300),
            auto_hide_delay=self.config_manager.get_setting('overlay.auto_hide_delay', 0)
        )
        
        return config
    
    def _parse_color(self, color_str: str) -> Tuple[int, int, int, int]:
        """Parse color string to RGBA tuple. Supports both hex (#RRGGBB) and comma-separated (R,G,B,A) formats."""
        try:
            print(f"[COLOR PARSE] Input: '{color_str}' (type: {type(color_str)})")
            
            # Handle hex color format (#RRGGBB or #RRGGBBAA)
            if isinstance(color_str, str) and color_str.startswith('#'):
                hex_str = color_str.lstrip('#')
                
                if len(hex_str) == 6:
                    # #RRGGBB format - add full opacity
                    r = int(hex_str[0:2], 16)
                    g = int(hex_str[2:4], 16)
                    b = int(hex_str[4:6], 16)
                    result = (r, g, b, 255)
                elif len(hex_str) == 8:
                    # #RRGGBBAA format
                    r = int(hex_str[0:2], 16)
                    g = int(hex_str[2:4], 16)
                    b = int(hex_str[4:6], 16)
                    a = int(hex_str[6:8], 16)
                    result = (r, g, b, a)
                else:
                    raise ValueError(f"Invalid hex color length: {len(hex_str)}")
                
                print(f"[COLOR PARSE] Hex parsed: {result}")
                return result
            
            # Handle comma-separated format (R,G,B,A)
            parts = color_str.split(',')
            result = tuple(int(p.strip()) for p in parts)
            print(f"[COLOR PARSE] Output: {result}")
            return result
        except Exception as e:
            print(f"[COLOR PARSE] ERROR: {e}, returning white")
            return (255, 255, 255, 255)
    
    def show_translation(self, text: str, position: Tuple[int, int], 
                        translation_id: Optional[str] = None,
                        monitor_id: Optional[int] = None) -> str:
        """
        Show a translation overlay.
        
        Args:
            text: Translation text to display
            position: (x, y) screen position (absolute or monitor-relative)
            translation_id: Optional ID (auto-generated if not provided)
            monitor_id: Optional monitor ID (for multi-monitor setups)
            
        Returns:
            Overlay ID for later reference
        """
        if translation_id is None:
            translation_id = f"translation_{self.next_overlay_id}"
            self.next_overlay_id += 1
        
        # Adjust position for monitor if specified
        if monitor_id is not None and monitor_id < len(self.monitor_info):
            monitor = self.monitor_info[monitor_id]
            # Convert monitor-relative to absolute screen coordinates
            abs_x = monitor['x'] + position[0]
            abs_y = monitor['y'] + position[1]
            position = (abs_x, abs_y)
            
            # Track which monitor this overlay belongs to
            self.overlay_monitor_map[translation_id] = monitor_id
        else:
            # Detect monitor from position
            detected_monitor = self._get_monitor_for_position(position[0], position[1])
            self.overlay_monitor_map[translation_id] = detected_monitor
        
        self.manager.show_overlay(translation_id, text, position)
        return translation_id
    
    def hide_translation(self, translation_id: str):
        """Hide a specific translation overlay."""
        self.manager.hide_overlay(translation_id)
    
    def hide_all_translations(self, immediate: bool = False):
        """
        Hide all translation overlays.
        
        Args:
            immediate: If True, hide immediately without animation (faster, prevents errors during shutdown)
        """
        self.manager.hide_all(immediate=immediate)
    
    def update_translation(self, translation_id: str, text: Optional[str] = None,
                          position: Optional[Tuple[int, int]] = None):
        """Update an existing translation overlay."""
        self.manager.update_overlay(translation_id, text, position)
    
    def is_visible(self, translation_id: str) -> bool:
        """Check if translation is visible."""
        return self.manager.is_active(translation_id)
    
    def get_active_count(self) -> int:
        """Get number of active overlays."""
        return self.manager.get_active_count()
    
    def reload_config(self):
        """
        Reload overlay configuration from config manager.
        
        This should be called after saving overlay settings to apply changes
        to future overlays.
        """
        if not self.config_manager:
            return
        
        print("[OVERLAY] Reloading overlay configuration...")
        new_config = self._load_config_from_manager()
        self.manager.default_config = new_config
        print("[OVERLAY] Configuration reloaded successfully")
    
    def apply_preset(self, preset_name: str):
        """
        Apply a preset style to future overlays.
        
        Args:
            preset_name: Name of preset (default, minimal, bold, subtle, high_contrast, glass)
        """
        preset_map = {
            'default': OverlayPresets.default,
            'minimal': OverlayPresets.minimal,
            'bold': OverlayPresets.bold,
            'subtle': OverlayPresets.subtle,
            'high_contrast': OverlayPresets.high_contrast,
            'glass': OverlayPresets.glass
        }
        
        if preset_name in preset_map:
            style = preset_map[preset_name]()
            self.manager.default_config.style = style
    
    def get_performance_stats(self) -> Dict[str, Any]:
        """Get performance statistics."""
        return self.manager.get_performance_stats()
    
    def get_monitor_info(self, monitor_id: Optional[int] = None) -> Optional[Dict]:
        """
        Get information about a specific monitor or all monitors.
        
        Args:
            monitor_id: Monitor index (None for all monitors)
            
        Returns:
            Monitor info dict or list of dicts
        """
        if monitor_id is None:
            return self.monitor_info
        
        if 0 <= monitor_id < len(self.monitor_info):
            return self.monitor_info[monitor_id]
        
        return None
    
    def get_overlay_monitor(self, translation_id: str) -> Optional[int]:
        """
        Get the monitor ID for a specific overlay.
        
        Args:
            translation_id: Overlay ID
            
        Returns:
            Monitor ID or None
        """
        return self.overlay_monitor_map.get(translation_id)
    
    def hide_overlays_on_monitor(self, monitor_id: int):
        """
        Hide all overlays on a specific monitor.
        
        Args:
            monitor_id: Monitor index
        """
        overlays_to_hide = [
            overlay_id for overlay_id, mon_id in self.overlay_monitor_map.items()
            if mon_id == monitor_id
        ]
        
        for overlay_id in overlays_to_hide:
            self.hide_translation(overlay_id)
    
    def cleanup(self):
        """Cleanup overlay system."""
        self.overlay_monitor_map.clear()
        self.manager.cleanup()


def create_overlay_system(config_manager=None) -> PyQt6OverlayAdapter:
    """
    Factory function to create overlay system.
    
    Args:
        config_manager: Optional configuration manager
        
    Returns:
        PyQt6OverlayAdapter instance
    """
    return PyQt6OverlayAdapter(config_manager)
