"""
Subtitle Overlay Widget

Lightweight always-on-top transparent window that displays translated subtitles
at the bottom of the screen, similar to video player subtitles.

Features:
- Positioned at bottom-center of the primary screen by default
- Auto-fades after a configurable timeout when no new text arrives
- Draggable to any position on screen
- Configurable font size
- Bilingual mode: shows original text above the translation
"""

import logging
import sys

from PyQt6.QtWidgets import (
    QWidget, QLabel, QVBoxLayout, QApplication, QGraphicsDropShadowEffect,
)
from PyQt6.QtCore import (
    Qt, QTimer, QPropertyAnimation, QEasingCurve, QPoint,
)
from PyQt6.QtGui import QColor, QMouseEvent

logger = logging.getLogger(__name__)

_DEFAULT_FONT_SIZE = 24
_DEFAULT_AUTO_HIDE_MS = 5000
_MAX_LABEL_WIDTH = 900
_BOTTOM_MARGIN = 80


class SubtitleOverlay(QWidget):
    """
    Always-on-top subtitle overlay for audio translation.

    Displays translated text at the bottom of the screen with auto-fade,
    drag support, and configurable appearance.
    """

    def __init__(
        self,
        font_size: int = _DEFAULT_FONT_SIZE,
        bilingual: bool = False,
        parent: QWidget | None = None,
    ):
        super().__init__(parent)

        self._font_size = font_size
        self._bilingual = bilingual
        self._drag_offset: QPoint | None = None
        self._fade_animation: QPropertyAnimation | None = None

        self._auto_hide_ms = _DEFAULT_AUTO_HIDE_MS
        self._auto_hide_timer = QTimer(self)
        self._auto_hide_timer.setSingleShot(True)
        self._auto_hide_timer.timeout.connect(self._fade_out)

        self._setup_window()
        self._create_ui()
        self._position_at_bottom()

    # ------------------------------------------------------------------
    # Window setup
    # ------------------------------------------------------------------

    def _setup_window(self):
        """Configure window flags for overlay behaviour."""
        flags = (
            Qt.WindowType.FramelessWindowHint
            | Qt.WindowType.WindowStaysOnTopHint
            | Qt.WindowType.Tool
        )
        # X11/Linux: bypass WM hints for reliable always-on-top overlays.
        # Windows: omit — DWM often handles tool windows without this hint.
        if sys.platform != "win32":
            flags |= Qt.WindowType.BypassWindowManagerHint
        self.setWindowFlags(flags)
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
        self.setAttribute(Qt.WidgetAttribute.WA_ShowWithoutActivating)
        self.setWindowOpacity(0.0)

    def _create_ui(self):
        """Build the subtitle label."""
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)

        self._label = QLabel("", self)
        self._label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self._label.setWordWrap(True)
        self._label.setMaximumWidth(_MAX_LABEL_WIDTH)
        self._apply_style()

        shadow = QGraphicsDropShadowEffect(self)
        shadow.setBlurRadius(12)
        shadow.setColor(QColor(0, 0, 0, 200))
        shadow.setOffset(1, 1)
        self._label.setGraphicsEffect(shadow)

        layout.addWidget(self._label)

    def _apply_style(self):
        """Apply stylesheet based on current font size."""
        self._label.setStyleSheet(f"""
            QLabel {{
                color: rgba(255, 255, 255, 255);
                font-family: 'Segoe UI';
                font-size: {self._font_size}px;
                font-weight: bold;
                background-color: rgba(0, 0, 0, 180);
                border-radius: 8px;
                padding: 12px 20px;
            }}
        """)

    def _position_at_bottom(self):
        """Place the overlay at the bottom-centre of the primary screen."""
        screen = QApplication.primaryScreen()
        if not screen:
            return
        geo = screen.geometry()
        self.adjustSize()
        x = geo.center().x() - self.width() // 2
        y = geo.bottom() - self.height() - _BOTTOM_MARGIN
        self.move(x, y)

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def show_subtitle(
        self,
        translated: str,
        original: str = "",
        detected_language: str = "",
    ):
        """Display a new subtitle line and reset the auto-hide timer.

        Args:
            translated: The translated text to display prominently.
            original: Optional original-language text shown above the
                translation when bilingual mode is enabled.
            detected_language: ISO code of the detected source language
                (e.g. ``"de"``).  Rendered as a small badge prefix.
        """
        lang_prefix = ""
        if detected_language:
            lang_prefix = (
                f"<span style='color:#64B5F6; font-size:"
                f"{max(self._font_size - 6, 9)}px;'>"
                f"[{detected_language.upper()}]</span> "
            )

        if self._bilingual and original:
            small_size = max(self._font_size - 4, 10)
            text = (
                f"<span style='color:#aaa; font-size:{small_size}px;'>"
                f"{original}</span><br>{lang_prefix}{translated}"
            )
            self._label.setTextFormat(Qt.TextFormat.RichText)
        elif lang_prefix:
            text = f"{lang_prefix}{translated}"
            self._label.setTextFormat(Qt.TextFormat.RichText)
        else:
            text = translated
            self._label.setTextFormat(Qt.TextFormat.PlainText)

        self._label.setText(text)
        self.adjustSize()
        self._recentre_horizontally()

        if (
            self._fade_animation is not None
            and self._fade_animation.state()
            == QPropertyAnimation.State.Running
        ):
            self._fade_animation.stop()

        self.setWindowOpacity(0.95)
        if not self.isVisible():
            self.show()
        self.raise_()

        if self._auto_hide_ms > 0:
            self._auto_hide_timer.start(self._auto_hide_ms)

    def hide_subtitle(self):
        """Immediately hide the overlay without animation."""
        self._auto_hide_timer.stop()
        if self._fade_animation is not None:
            self._fade_animation.stop()
            self._fade_animation = None
        self.setWindowOpacity(0.0)
        self.hide()

    def set_font_size(self, size: int):
        """Update the subtitle font size."""
        self._font_size = size
        self._apply_style()

    def set_bilingual(self, enabled: bool):
        """Toggle bilingual display (original + translation)."""
        self._bilingual = enabled

    def set_auto_hide_delay(self, ms: int):
        """Set the auto-hide delay in milliseconds (0 = never auto-hide)."""
        self._auto_hide_ms = ms

    # ------------------------------------------------------------------
    # Internals
    # ------------------------------------------------------------------

    def _recentre_horizontally(self):
        """Keep the overlay centred horizontally after text changes."""
        screen = QApplication.primaryScreen()
        if not screen:
            return
        geo = screen.geometry()
        x = geo.center().x() - self.width() // 2
        self.move(x, self.y())

    def _fade_out(self):
        """Gradually fade the overlay to transparent."""
        self._fade_animation = QPropertyAnimation(self, b"windowOpacity")
        self._fade_animation.setDuration(800)
        self._fade_animation.setStartValue(self.windowOpacity())
        self._fade_animation.setEndValue(0.0)
        self._fade_animation.setEasingCurve(QEasingCurve.Type.InOutQuad)
        self._fade_animation.finished.connect(self.hide)
        self._fade_animation.start()

    # ------------------------------------------------------------------
    # Dragging
    # ------------------------------------------------------------------

    def mousePressEvent(self, event: QMouseEvent):
        if event.button() == Qt.MouseButton.LeftButton:
            self._drag_offset = (
                event.globalPosition().toPoint() - self.pos()
            )
        super().mousePressEvent(event)

    def mouseMoveEvent(self, event: QMouseEvent):
        if (
            self._drag_offset is not None
            and event.buttons() & Qt.MouseButton.LeftButton
        ):
            self.move(event.globalPosition().toPoint() - self._drag_offset)
        super().mouseMoveEvent(event)

    def mouseReleaseEvent(self, event: QMouseEvent):
        self._drag_offset = None
        super().mouseReleaseEvent(event)
