"""
PyQt6 Overlay System

High-performance translation overlay system with GPU acceleration,
native effects, and seamless integration with PyQt6 main window.

Features:
- GPU-accelerated rendering
- Per-pixel transparency
- Native blur and shadow effects
- Smooth non-blocking animations
- Click-through support
- Multi-monitor support with DPI awareness
- CSS-like styling
- Overlay pooling for performance
"""

from PyQt6.QtWidgets import (
    QWidget, QLabel, QVBoxLayout, QGraphicsDropShadowEffect,
    QGraphicsBlurEffect, QApplication
)
from PyQt6.QtCore import (
    Qt, QTimer, QPropertyAnimation, QEasingCurve, QPoint, QRect,
    pyqtSignal, QObject
)
from PyQt6.QtGui import QColor, QFont, QPainter, QPainterPath, QScreen
from dataclasses import dataclass, field
from typing import Optional, List, Dict, Any, Tuple, Callable
from enum import Enum
import time


class OverlayPosition(Enum):
    """Overlay positioning modes."""
    CUSTOM = "custom"
    TOP_LEFT = "top_left"
    TOP_CENTER = "top_center"
    TOP_RIGHT = "top_right"
    CENTER = "center"
    BOTTOM_LEFT = "bottom_left"
    BOTTOM_CENTER = "bottom_center"
    BOTTOM_RIGHT = "bottom_right"


class AnimationType(Enum):
    """Animation types for overlays."""
    NONE = "none"
    FADE = "fade"
    SLIDE_UP = "slide_up"
    SLIDE_DOWN = "slide_down"
    SLIDE_LEFT = "slide_left"
    SLIDE_RIGHT = "slide_right"
    SCALE = "scale"


@dataclass
class OverlayStyle:
    """Overlay visual style configuration - ALL values loaded from config, NO hardcoded defaults."""
    # Font - NO DEFAULTS, must be provided from config
    font_family: str = field(default="Segoe UI")  # Fallback only
    font_size: int = field(default=14)  # Fallback only
    font_weight: str = field(default="normal")  # Fallback only
    font_italic: bool = field(default=False)  # Fallback only
    
    # Colors - NO DEFAULTS, must be provided from config
    text_color: Tuple[int, int, int, int] = field(default=(255, 255, 255, 255))  # Fallback: white
    background_color: Tuple[int, int, int, int] = field(default=(0, 0, 0, 230))  # Fallback: black
    border_color: Tuple[int, int, int, int] = field(default=(100, 100, 100, 255))  # Fallback: gray
    
    # Background
    background_enabled: bool = field(default=True)
    background_blur: bool = field(default=False)
    background_blur_radius: int = field(default=10)
    
    # Border
    border_enabled: bool = field(default=True)
    border_width: int = field(default=2)  # Thinner default
    border_radius: int = field(default=8)  # Rounded corners
    
    # Shadow
    shadow_enabled: bool = field(default=True)
    shadow_blur_radius: int = field(default=15)
    shadow_color: Tuple[int, int, int, int] = field(default=(0, 0, 0, 180))
    shadow_offset: Tuple[int, int] = field(default=(2, 2))
    
    # Padding
    padding: int = field(default=12)
    
    # Size constraints
    max_width: int = field(default=800)
    max_height: int = field(default=400)
    word_wrap: bool = field(default=True)
    
    # Opacity
    opacity: float = field(default=0.9)
    
    def to_stylesheet(self) -> str:
        """Convert style to Qt stylesheet."""
        r, g, b, a = self.text_color
        bg_r, bg_g, bg_b, bg_a = self.background_color
        border_r, border_g, border_b, border_a = self.border_color
        
        font_weight = "bold" if self.font_weight == "bold" else "normal"
        font_style = "italic" if self.font_italic else "normal"
        
        stylesheet = f"""
            QLabel {{
                color: rgba({r}, {g}, {b}, {a});
                font-family: '{self.font_family}';
                font-size: {self.font_size}px;
                font-weight: {font_weight};
                font-style: {font_style};
                padding: {self.padding}px;
        """
        
        if self.background_enabled:
            stylesheet += f"""
                background-color: rgba({bg_r}, {bg_g}, {bg_b}, {bg_a});
            """
        
        if self.border_enabled:
            stylesheet += f"""
                border: {self.border_width}px solid rgba({border_r}, {border_g}, {border_b}, {border_a});
                border-radius: {self.border_radius}px;
            """
        
        stylesheet += "}"
        
        return stylesheet


@dataclass
class OverlayConfig:
    """Overlay configuration."""
    style: OverlayStyle = field(default_factory=OverlayStyle)
    position_mode: OverlayPosition = OverlayPosition.CUSTOM
    click_through: bool = True
    interactive_on_hover: bool = False  # Toggle click-through on hover
    always_on_top: bool = True
    animation_in: AnimationType = AnimationType.FADE
    animation_out: AnimationType = AnimationType.FADE
    animation_duration: int = 300  # milliseconds
    auto_hide_delay: int = 0  # 0 = no auto-hide, milliseconds
    
    # Multi-monitor
    monitor_index: int = -1  # -1 = auto-detect from position


class TranslationOverlay(QWidget):
    """
    High-performance translation overlay window.
    
    Features:
    - GPU-accelerated rendering
    - Per-pixel transparency
    - Native effects (shadow, blur)
    - Smooth animations
    - Click-through support
    """
    
    # Signals
    clicked = pyqtSignal()
    closed = pyqtSignal()
    
    def __init__(self, text: str, position: Tuple[int, int], 
                 config: Optional[OverlayConfig] = None, parent=None):
        """
        Initialize translation overlay.
        
        Args:
            text: Text to display
            position: (x, y) position on screen
            config: Overlay configuration
            parent: Parent widget (optional)
        """
        super().__init__(parent)
        
        self.text = text
        self.position = position
        self.config = config or OverlayConfig()
        self.is_visible = False
        self.animation = None
        self.auto_hide_timer = None
        
        # Setup window
        self._setup_window()
        
        # Create UI
        self._create_ui()
        
        # Apply effects
        self._apply_effects()
        
        # Position window
        self._position_window()
    
    def _setup_window(self):
        """Configure window properties."""
        # Window flags for Windows - AGGRESSIVE stay-on-top mode
        # TEMPORARY FIX: Remove WindowDoesNotAcceptFocus to test if that's blocking overlays
        flags = (Qt.WindowType.FramelessWindowHint | 
                 Qt.WindowType.WindowStaysOnTopHint |
                 Qt.WindowType.Tool |  # Tool windows stay on top better on Windows
                 # Qt.WindowType.WindowDoesNotAcceptFocus |  # DISABLED - testing if this blocks overlays
                 Qt.WindowType.BypassWindowManagerHint)  # Bypass window manager (more aggressive)
        
        self.setWindowFlags(flags)
        
        # Force window to stay on top (Windows-specific)
        self.setAttribute(Qt.WidgetAttribute.WA_ShowWithoutActivating)
        self.setAttribute(Qt.WidgetAttribute.WA_AlwaysStackOnTop)  # Extra aggressive
        
        # Transparency
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
        
        # Click-through and hover tracking
        if self.config.click_through:
            self.setAttribute(Qt.WidgetAttribute.WA_TransparentForMouseEvents)
        
        # Enable hover events if interactive_on_hover is enabled
        if self.config.interactive_on_hover:
            self.setAttribute(Qt.WidgetAttribute.WA_Hover)
            self.setMouseTracking(True)
        
        # Set opacity
        self.setWindowOpacity(0.0)  # Start invisible for fade-in
    
    def _create_ui(self):
        """Create overlay UI."""
        # Main layout
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)
        
        # Text label
        self.label = QLabel(self.text, self)
        self.label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        
        # Apply styling
        stylesheet = self.config.style.to_stylesheet()
        self.label.setStyleSheet(stylesheet)
        
        # Word wrap
        if self.config.style.word_wrap:
            self.label.setWordWrap(True)
            self.label.setMaximumWidth(self.config.style.max_width)
        
        layout.addWidget(self.label)
        
        # Adjust size to content
        self.adjustSize()
    
    def _apply_effects(self):
        """Apply visual effects (shadow, blur)."""
        # Shadow effect
        if self.config.style.shadow_enabled:
            shadow = QGraphicsDropShadowEffect(self)
            shadow.setBlurRadius(self.config.style.shadow_blur_radius)
            
            r, g, b, a = self.config.style.shadow_color
            shadow.setColor(QColor(r, g, b, a))
            
            offset_x, offset_y = self.config.style.shadow_offset
            shadow.setOffset(offset_x, offset_y)
            
            self.label.setGraphicsEffect(shadow)
        
        # Background blur (if enabled)
        if self.config.style.background_blur:
            blur = QGraphicsBlurEffect(self)
            blur.setBlurRadius(self.config.style.background_blur_radius)
            # Note: Apply to background widget if needed
    
    def _position_window(self):
        """Position window on screen."""
        if self.config.position_mode == OverlayPosition.CUSTOM:
            # Use provided position
            self.move(self.position[0], self.position[1])
        else:
            # Calculate position based on mode
            screen = self._get_target_screen()
            screen_rect = screen.geometry()
            
            x, y = self._calculate_position(screen_rect)
            self.move(x, y)
    
    def _get_target_screen(self) -> QScreen:
        """Get target screen for overlay."""
        app = QApplication.instance()
        
        if self.config.monitor_index >= 0:
            # Use specified monitor
            screens = app.screens()
            if self.config.monitor_index < len(screens):
                return screens[self.config.monitor_index]
        
        # Auto-detect from position
        point = QPoint(self.position[0], self.position[1])
        screen = app.screenAt(point)
        
        return screen or app.primaryScreen()
    
    def _calculate_position(self, screen_rect: QRect) -> Tuple[int, int]:
        """Calculate position based on position mode."""
        width = self.width()
        height = self.height()
        
        mode = self.config.position_mode
        
        if mode == OverlayPosition.TOP_LEFT:
            return screen_rect.left() + 10, screen_rect.top() + 10
        elif mode == OverlayPosition.TOP_CENTER:
            return screen_rect.center().x() - width // 2, screen_rect.top() + 10
        elif mode == OverlayPosition.TOP_RIGHT:
            return screen_rect.right() - width - 10, screen_rect.top() + 10
        elif mode == OverlayPosition.CENTER:
            return screen_rect.center().x() - width // 2, screen_rect.center().y() - height // 2
        elif mode == OverlayPosition.BOTTOM_LEFT:
            return screen_rect.left() + 10, screen_rect.bottom() - height - 10
        elif mode == OverlayPosition.BOTTOM_CENTER:
            return screen_rect.center().x() - width // 2, screen_rect.bottom() - height - 10
        elif mode == OverlayPosition.BOTTOM_RIGHT:
            return screen_rect.right() - width - 10, screen_rect.bottom() - height - 10
        else:
            return self.position
    
    def show_animated(self):
        """Show overlay with animation."""
        
        # CRITICAL: Always set opacity first, then animate if needed
        # This ensures overlay is visible even if animation fails
        self.setWindowOpacity(self.config.style.opacity)
        
        # Show window
        self.show()
        self.raise_()  # Bring to front
        self.setWindowState(self.windowState() & ~Qt.WindowState.WindowMinimized | Qt.WindowState.WindowActive)
        
        # REMOVED: repaint() causes recursive repaint and freezes UI
        # REMOVED: Win32 SetWindowPos blocks main thread
        
        self.is_visible = True
        
        # Animate based on type (optional visual effect)
        if self.config.animation_in == AnimationType.FADE:
            self._animate_fade_in()
        elif self.config.animation_in == AnimationType.SLIDE_UP:
            self._animate_slide(0, -20)
        elif self.config.animation_in == AnimationType.SLIDE_DOWN:
            self._animate_slide(0, 20)
        elif self.config.animation_in == AnimationType.SLIDE_LEFT:
            self._animate_slide(-20, 0)
        elif self.config.animation_in == AnimationType.SLIDE_RIGHT:
            self._animate_slide(20, 0)
        elif self.config.animation_in == AnimationType.SCALE:
            self._animate_scale()
        # else: No animation - opacity already set above
        
        # Setup auto-hide timer
        if self.config.auto_hide_delay > 0:
            self.auto_hide_timer = QTimer(self)
            self.auto_hide_timer.setSingleShot(True)
            self.auto_hide_timer.timeout.connect(self.hide_animated)
            self.auto_hide_timer.start(self.config.auto_hide_delay)
    
    def hide_animated(self):
        """Hide overlay with animation."""
        if not self.is_visible:
            return
        
        self.is_visible = False
        
        # Stop auto-hide timer
        if self.auto_hide_timer:
            self.auto_hide_timer.stop()
        
        # Animate based on type
        if self.config.animation_out == AnimationType.FADE:
            self._animate_fade_out()
        else:
            self.hide()
            self.closed.emit()
    
    def _animate_fade_in(self):
        """Fade in animation."""
        self.animation = QPropertyAnimation(self, b"windowOpacity")
        self.animation.setDuration(self.config.animation_duration)
        self.animation.setStartValue(0.0)
        self.animation.setEndValue(self.config.style.opacity)
        self.animation.setEasingCurve(QEasingCurve.Type.InOutQuad)
        self.animation.start()
    
    def _animate_fade_out(self):
        """Fade out animation."""
        self.animation = QPropertyAnimation(self, b"windowOpacity")
        self.animation.setDuration(self.config.animation_duration)
        self.animation.setStartValue(self.config.style.opacity)
        self.animation.setEndValue(0.0)
        self.animation.setEasingCurve(QEasingCurve.Type.InOutQuad)
        self.animation.finished.connect(self._on_animation_finished)
        self.animation.start()
    
    def _animate_slide(self, offset_x: int, offset_y: int):
        """Slide animation."""
        # Store original position
        original_pos = self.pos()
        
        # Start from offset position
        self.move(original_pos.x() + offset_x, original_pos.y() + offset_y)
        
        # Animate to original position
        from PyQt6.QtCore import QPoint, QPropertyAnimation
        self.animation = QPropertyAnimation(self, b"pos")
        self.animation.setDuration(self.config.animation_duration)
        self.animation.setStartValue(self.pos())
        self.animation.setEndValue(original_pos)
        self.animation.setEasingCurve(QEasingCurve.Type.OutCubic)
        
        # Also fade in
        self.setWindowOpacity(0.0)
        opacity_anim = QPropertyAnimation(self, b"windowOpacity")
        opacity_anim.setDuration(self.config.animation_duration)
        opacity_anim.setStartValue(0.0)
        opacity_anim.setEndValue(self.config.style.opacity)
        
        self.animation.start()
        opacity_anim.start()
    
    def _animate_scale(self):
        """Scale animation (simulated with opacity and size)."""
        # For now, just use fade
        # Full scale animation would require QGraphicsView
        self._animate_fade_in()
    
    def _on_animation_finished(self):
        """Called when animation finishes."""
        self.hide()
        self.closed.emit()
    
    def update_text(self, text: str):
        """Update overlay text."""
        self.text = text
        self.label.setText(text)
        self.adjustSize()
    
    def update_position(self, position: Tuple[int, int]):
        """Update overlay position."""
        self.position = position
        self.move(position[0], position[1])
    
    def mousePressEvent(self, event):
        """Handle mouse press (if not click-through)."""
        if not self.config.click_through:
            self.clicked.emit()
        super().mousePressEvent(event)
    
    def enterEvent(self, event):
        """Handle mouse enter - make overlay interactive if configured."""
        if self.config.interactive_on_hover:
            # Remove click-through attribute to make overlay interactive
            self.setAttribute(Qt.WidgetAttribute.WA_TransparentForMouseEvents, False)
            # Optional: Add visual feedback
            self.setWindowOpacity(min(1.0, self.windowOpacity() + 0.1))
        super().enterEvent(event)
    
    def leaveEvent(self, event):
        """Handle mouse leave - restore click-through if configured."""
        if self.config.interactive_on_hover:
            # Restore click-through attribute
            self.setAttribute(Qt.WidgetAttribute.WA_TransparentForMouseEvents, True)
            # Restore original opacity
            self.setWindowOpacity(self.config.style.opacity)
        super().leaveEvent(event)


class OverlayManager(QObject):
    """
    Manages multiple translation overlays.
    
    Features:
    - Overlay pooling for performance
    - Automatic cleanup
    - Batch operations
    - Performance monitoring
    """
    
    def __init__(self, config: Optional[OverlayConfig] = None, parent=None):
        """
        Initialize overlay manager.
        
        Args:
            config: Default overlay configuration
            parent: Parent QObject
        """
        super().__init__(parent)
        
        self.default_config = config or OverlayConfig()
        self.active_overlays: Dict[str, TranslationOverlay] = {}
        self.overlay_pool: List[TranslationOverlay] = []
        self.max_pool_size = 10
        
        # Performance metrics
        self.total_created = 0
        self.total_reused = 0
        self.render_times: List[float] = []
    
    def show_overlay(self, overlay_id: str, text: str, position: Tuple[int, int],
                    config: Optional[OverlayConfig] = None) -> TranslationOverlay:
        """
        Show a translation overlay.
        
        Args:
            overlay_id: Unique identifier for this overlay
            text: Text to display
            position: (x, y) position
            config: Optional custom configuration
            
        Returns:
            TranslationOverlay instance
        """
        start_time = time.time()
        
        # Check if overlay already exists and is active
        if overlay_id in self.active_overlays:
            existing_overlay = self.active_overlays[overlay_id]
            # Update existing overlay instead of hiding/showing (prevents flash)
            existing_overlay.update_text(text)
            existing_overlay.update_position(position)
            # Update config if provided
            if config:
                existing_overlay.config = config
                existing_overlay.label.setStyleSheet(config.style.to_stylesheet())
            # CRITICAL: Always ensure overlay stays on top and visible
            # Windows can sometimes hide overlays or lose their "always on top" status
            was_visible = existing_overlay.isVisible()
            if not was_visible:
                existing_overlay.show_animated()
            else:
                # Even if visible, ensure it stays on top (Windows compositor can push it behind)
                # NOTE: Don't call activateWindow() - it conflicts with WindowDoesNotAcceptFocus
                existing_overlay.raise_()
            return existing_overlay
        
        # Try to reuse from pool (for performance)
        overlay = self._get_from_pool()
        
        if overlay:
            # Reuse existing overlay
            overlay.update_text(text)
            overlay.update_position(position)
            # ALWAYS update config to ensure correct colors
            overlay.config = config or self.default_config
            # Re-apply stylesheet with correct colors
            overlay.label.setStyleSheet(overlay.config.style.to_stylesheet())
            self.total_reused += 1
        else:
            # Create new overlay
            overlay = TranslationOverlay(
                text=text,
                position=position,
                config=config or self.default_config
            )
            overlay.closed.connect(lambda: self._on_overlay_closed(overlay_id))
            self.total_created += 1
        
        # Show overlay
        overlay.show_animated()
        self.active_overlays[overlay_id] = overlay
        
        # Track performance
        render_time = time.time() - start_time
        self.render_times.append(render_time)
        if len(self.render_times) > 100:
            self.render_times.pop(0)
        
        return overlay
    
    def hide_overlay(self, overlay_id: str):
        """Hide and pool an overlay."""
        if overlay_id in self.active_overlays:
            overlay = self.active_overlays.pop(overlay_id)
            overlay.hide_animated()
            self._return_to_pool(overlay)
    
    def hide_all(self, immediate: bool = False):
        """
        Hide all active overlays.
        
        Args:
            immediate: If True, hide immediately without animation (faster, prevents window handle errors)
        """
        overlay_ids = list(self.active_overlays.keys())
        
        for overlay_id in overlay_ids:
            if immediate:
                self.hide_overlay_immediate(overlay_id)
            else:
                self.hide_overlay(overlay_id)
        
        # ADDITIONAL CLEANUP: Also hide any overlays in the pool that might still be visible
        if immediate:
            for overlay in self.overlay_pool:
                try:
                    if overlay.isVisible():
                        overlay.hide()
                        overlay.close()
                except:
                    pass  # Ignore errors for already-deleted overlays
        
        # Force Qt to process events immediately (ensures overlays are actually hidden)
        if immediate:
            from PyQt6.QtWidgets import QApplication
            for _ in range(3):  # Process multiple times to ensure cleanup
                QApplication.processEvents()
    
    def hide_overlay_immediate(self, overlay_id: str):
        """Hide overlay immediately without animation (for fast cleanup)."""
        if overlay_id in self.active_overlays:
            overlay = self.active_overlays.pop(overlay_id)
            
            # Stop any running animations
            if hasattr(overlay, 'animation') and overlay.animation:
                overlay.animation.stop()
                overlay.animation = None
            
            # Stop auto-hide timer if running
            if hasattr(overlay, 'auto_hide_timer') and overlay.auto_hide_timer:
                overlay.auto_hide_timer.stop()
                overlay.auto_hide_timer = None
            
            # Mark as not visible
            overlay.is_visible = False
            
            # Make completely invisible immediately
            overlay.setWindowOpacity(0.0)
            
            # Hide the window
            overlay.hide()
            
            # Close the window (releases window handle)
            overlay.close()
            
            # Force immediate deletion (more aggressive than deleteLater)
            try:
                overlay.setParent(None)  # Detach from parent
                overlay.deleteLater()
            except:
                pass
    
    def update_overlay(self, overlay_id: str, text: Optional[str] = None,
                      position: Optional[Tuple[int, int]] = None):
        """Update an existing overlay."""
        if overlay_id in self.active_overlays:
            overlay = self.active_overlays[overlay_id]
            if text is not None:
                overlay.update_text(text)
            if position is not None:
                overlay.update_position(position)
    
    def get_overlay(self, overlay_id: str) -> Optional[TranslationOverlay]:
        """Get an active overlay by ID."""
        return self.active_overlays.get(overlay_id)
    
    def is_active(self, overlay_id: str) -> bool:
        """Check if overlay is active."""
        return overlay_id in self.active_overlays
    
    def get_active_count(self) -> int:
        """Get number of active overlays."""
        return len(self.active_overlays)
    
    def get_performance_stats(self) -> Dict[str, Any]:
        """Get performance statistics."""
        avg_render_time = sum(self.render_times) / len(self.render_times) if self.render_times else 0
        
        return {
            'active_overlays': len(self.active_overlays),
            'pooled_overlays': len(self.overlay_pool),
            'total_created': self.total_created,
            'total_reused': self.total_reused,
            'reuse_rate': self.total_reused / max(self.total_created, 1),
            'avg_render_time_ms': avg_render_time * 1000,
            'recent_render_times': self.render_times[-10:]
        }
    
    def _get_from_pool(self) -> Optional[TranslationOverlay]:
        """Get overlay from pool."""
        if self.overlay_pool:
            return self.overlay_pool.pop()
        return None
    
    def _return_to_pool(self, overlay: TranslationOverlay):
        """Return overlay to pool."""
        if len(self.overlay_pool) < self.max_pool_size:
            self.overlay_pool.append(overlay)
        else:
            overlay.deleteLater()
    
    def _on_overlay_closed(self, overlay_id: str):
        """Handle overlay closed signal."""
        if overlay_id in self.active_overlays:
            self.active_overlays.pop(overlay_id)
    
    def cleanup(self):
        """Cleanup all overlays."""
        # Hide all active overlays
        self.hide_all()
        
        # Clear pool
        for overlay in self.overlay_pool:
            overlay.deleteLater()
        self.overlay_pool.clear()


# Preset styles
class OverlayPresets:
    """Predefined overlay styles."""
    
    @staticmethod
    def default() -> OverlayStyle:
        """Default style."""
        return OverlayStyle()
    
    @staticmethod
    def minimal() -> OverlayStyle:
        """Minimal style with no border or shadow."""
        return OverlayStyle(
            border_enabled=False,
            shadow_enabled=False,
            background_color=(0, 0, 0, 200),
            padding=8
        )
    
    @staticmethod
    def bold() -> OverlayStyle:
        """Bold style with thick border."""
        return OverlayStyle(
            font_weight="bold",
            font_size=16,
            border_width=3,
            border_color=(255, 255, 255, 255),
            shadow_blur_radius=20
        )
    
    @staticmethod
    def subtle() -> OverlayStyle:
        """Subtle style with low opacity."""
        return OverlayStyle(
            opacity=0.7,
            background_color=(30, 30, 30, 150),
            shadow_enabled=False,
            border_enabled=False
        )
    
    @staticmethod
    def high_contrast() -> OverlayStyle:
        """High contrast style."""
        return OverlayStyle(
            text_color=(255, 255, 0, 255),  # Yellow
            background_color=(0, 0, 0, 255),  # Black
            border_color=(255, 255, 0, 255),  # Yellow
            border_width=3,
            font_weight="bold"
        )
    
    @staticmethod
    def glass() -> OverlayStyle:
        """Glass effect style."""
        return OverlayStyle(
            background_color=(255, 255, 255, 50),
            background_blur=True,
            border_color=(255, 255, 255, 100),
            shadow_blur_radius=25,
            opacity=0.85
        )
