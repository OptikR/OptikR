"""
Overlay Integration Module

Provides easy integration between the pipeline and PyQt6 overlay system.
Drop-in replacement for the old Tkinter overlay system.
"""

import logging
from .overlay_manager import (
    OverlayManager, OverlayConfig, OverlayStyle,
    AnimationType
)

logger = logging.getLogger(__name__)


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
        self.overlay_monitor_map: dict[str, int] = {}  # overlay_id -> monitor_id

    def _detect_monitors(self) -> list[dict]:
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

        logger.debug("Loading overlay configuration from config manager")

        # Load colors (support both hex and comma-separated formats)
        bg_color_str = self.config_manager.get_setting('overlay.background_color', '#000000')
        text_color_str = self.config_manager.get_setting('overlay.font_color', '#FFFFFF')
        border_color_str = self.config_manager.get_setting('overlay.border_color', '#646464')

        # Parse colors
        text_color = self._parse_color(text_color_str)
        bg_color = self._parse_color(bg_color_str)
        border_color = self._parse_color(border_color_str)

        # Load transparency and apply to background
        transparency = self.config_manager.get_setting('overlay.transparency', 0.8)
        bg_color = (bg_color[0], bg_color[1], bg_color[2], int(transparency * 255))

        # Load font settings
        font_family = self.config_manager.get_setting('overlay.font_family', 'Segoe UI')
        font_size = self.config_manager.get_setting('overlay.font_size', 14)

        # Load border settings
        rounded_corners = self.config_manager.get_setting('overlay.rounded_corners', True)
        border_radius = 8 if rounded_corners else 0

        logger.debug("Config: font=%s %dpx, border_radius=%dpx, transparency=%.2f",
                      font_family, font_size, border_radius, transparency)

        style = OverlayStyle(
            # Font
            font_family=font_family,
            font_size=font_size,
            font_weight='normal',
            font_italic=False,

            # Colors
            text_color=text_color,
            background_color=bg_color,
            border_color=border_color,

            # Border
            border_enabled=True,
            border_width=2,
            border_radius=border_radius,

            # Shadow
            shadow_enabled=True,
            shadow_blur_radius=15,
            shadow_color=(0, 0, 0, 180),
            shadow_offset=(2, 2),

            # Other
            opacity=self.config_manager.get_setting('overlay.opacity', 0.8),
            max_width=self._resolve_max_width(font_size),
            max_height=self.config_manager.get_setting('overlay.max_height', 400),
            word_wrap=True,
            padding=12
        )

        # Load overlay config
        interactive_on_hover = self.config_manager.get_setting('overlay.interactive_on_hover', False)

        # Parse animation types with fallback
        animation_in = self._parse_animation_type(
            self.config_manager.get_setting('overlay.animation_in', 'FADE'))
        animation_out = self._parse_animation_type(
            self.config_manager.get_setting('overlay.animation_out', 'FADE'))

        config = OverlayConfig(
            style=style,
            click_through=True,
            interactive_on_hover=interactive_on_hover,
            always_on_top=self.config_manager.get_setting('overlay.always_on_top', True),
            animation_in=animation_in,
            animation_out=animation_out,
            animation_duration=self.config_manager.get_setting('overlay.animation_duration', 300),
            auto_hide_delay=0,  # Pipeline overlays persist until replaced by next frame
            exclude_from_capture=True,
        )

        logger.debug("Overlay configuration loaded successfully")
        return config

    def _resolve_max_width(self, font_size: int) -> int:
        """Resolve overlay max width from config.

        Prefers ``overlay.max_text_width`` (in characters) when set, converting
        to an approximate pixel width based on the configured font size.  Falls
        back to the explicit ``overlay.max_width`` pixel value.
        """
        max_text_chars = self.config_manager.get_setting('overlay.max_text_width', 0)
        if max_text_chars and max_text_chars > 0:
            avg_char_px = max(font_size * 0.6, 6)
            return int(max_text_chars * avg_char_px) + 24  # + padding
        return self.config_manager.get_setting('overlay.max_width', 800)

    @staticmethod
    def _parse_animation_type(value: str) -> AnimationType:
        """Parse animation type string with fallback to FADE."""
        try:
            return AnimationType[value.upper()]
        except (KeyError, AttributeError):
            logger.warning("Invalid animation type '%s', falling back to FADE", value)
            return AnimationType.FADE

    @staticmethod
    def _parse_color(color_str: str) -> tuple[int, int, int, int]:
        """Parse color string to RGBA tuple.

        Supports hex (#RRGGBB, #RRGGBBAA) and comma-separated (R,G,B or R,G,B,A) formats.
        Always returns a 4-tuple (R, G, B, A).
        """
        try:
            # Handle hex color format
            if isinstance(color_str, str) and color_str.startswith('#'):
                hex_str = color_str.lstrip('#')

                if len(hex_str) == 6:
                    r = int(hex_str[0:2], 16)
                    g = int(hex_str[2:4], 16)
                    b = int(hex_str[4:6], 16)
                    return (r, g, b, 255)
                elif len(hex_str) == 8:
                    r = int(hex_str[0:2], 16)
                    g = int(hex_str[2:4], 16)
                    b = int(hex_str[4:6], 16)
                    a = int(hex_str[6:8], 16)
                    return (r, g, b, a)
                else:
                    raise ValueError(f"Invalid hex color length: {len(hex_str)}")

            # Handle comma-separated format (R,G,B or R,G,B,A)
            parts = [int(p.strip()) for p in color_str.split(',')]
            if len(parts) == 3:
                return (parts[0], parts[1], parts[2], 255)
            elif len(parts) == 4:
                return (parts[0], parts[1], parts[2], parts[3])
            else:
                raise ValueError(f"Expected 3 or 4 color components, got {len(parts)}")
        except Exception as e:
            logger.warning("Failed to parse color '%s': %s, returning white", color_str, e)
            return (255, 255, 255, 255)

    def show_translation(self, text: str, position: tuple[int, int],
                        translation_id: str | None = None,
                        monitor_id: int | None = None) -> str:
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
            abs_x = monitor['x'] + position[0]
            abs_y = monitor['y'] + position[1]
            position = (abs_x, abs_y)
            self.overlay_monitor_map[translation_id] = monitor_id
        else:
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
            immediate: If True, hide immediately without animation
        """
        self.manager.hide_all(immediate=immediate)

    def update_translation(self, translation_id: str, text: str | None = None,
                          position: tuple[int, int] | None = None):
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

        Should be called after saving overlay settings to apply changes
        to future overlays.
        """
        if not self.config_manager:
            return

        logger.info("Reloading overlay configuration")
        new_config = self._load_config_from_manager()
        self.manager.default_config = new_config
        logger.info("Overlay configuration reloaded")

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
