"""
Region Visualizer - PyQt6 Implementation

Shows a visual overlay on screen to display the selected capture/overlay regions.
Helps users see exactly where OCR capture and translation display will occur.

Color coding:
  - GREEN: Region boundary (outermost)
  - RED:   OCR capture area (inset 12px)
  - BLUE:  Translation overlay area (inset 24px)
"""

import logging

from PyQt6.QtWidgets import QWidget, QApplication
from PyQt6.QtCore import Qt, QTimer, QRect, QObject, QEvent
from PyQt6.QtGui import QPainter, QPen, QColor, QFont

logger = logging.getLogger(__name__)

# Minimum region size (px) required to show inset overlays
_MIN_INSET_SIZE = 48


class RegionVisualizerOverlay(QWidget):
    """
    Transparent overlay window that shows region boundaries.
    Displays a colored border around the selected region with labels.
    """

    def __init__(self, region: dict[str, int], title: str = "Region",
                 color: QColor = QColor(0, 255, 0, 200), border_width: int = 6,
                 show_labels: bool = True, parent=None):
        super().__init__(parent)

        self.region = region
        self.title = title
        self.color = color
        self.border_width = border_width
        self.show_labels = show_labels

        # Frameless, always-on-top, transparent, click-through
        self.setWindowFlags(
            Qt.WindowType.FramelessWindowHint |
            Qt.WindowType.WindowStaysOnTopHint |
            Qt.WindowType.Tool
        )
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
        self.setAttribute(Qt.WidgetAttribute.WA_TransparentForMouseEvents)

        # Position window at region location
        self.setGeometry(
            region['x'], region['y'],
            region['width'], region['height']
        )

        self.setWindowOpacity(1.0)
        self.raise_()
        self.activateWindow()

        # Auto-hide after 10 seconds
        self.hide_timer = QTimer(self)
        self.hide_timer.timeout.connect(self.close)
        self.hide_timer.setSingleShot(True)
        self.hide_timer.start(10000)

    def paintEvent(self, event):
        """Draw the region border and label."""
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)

        half = self.border_width // 2
        w, h = self.width(), self.height()

        # Draw thick border
        pen = QPen(self.color, self.border_width, Qt.PenStyle.SolidLine)
        painter.setPen(pen)
        painter.drawRect(half, half, w - self.border_width, h - self.border_width)

        # Draw corner markers for better visibility
        corner_size = 40
        pen_thick = QPen(self.color, self.border_width + 2, Qt.PenStyle.SolidLine)
        painter.setPen(pen_thick)

        # Top-left
        painter.drawLine(half, half, corner_size, half)
        painter.drawLine(half, half, half, corner_size)
        # Top-right
        painter.drawLine(w - half, half, w - corner_size, half)
        painter.drawLine(w - half, half, w - half, corner_size)
        # Bottom-left
        painter.drawLine(half, h - half, corner_size, h - half)
        painter.drawLine(half, h - half, half, h - corner_size)
        # Bottom-right
        painter.drawLine(w - half, h - half, w - corner_size, h - half)
        painter.drawLine(w - half, h - half, w - half, h - corner_size)

        if not self.show_labels:
            return

        # Title label at top-left
        font = QFont("Segoe UI", 16, QFont.Weight.Bold)
        painter.setFont(font)

        text_rect = QRect(15, 15, 400, 50)
        painter.fillRect(text_rect, QColor(0, 0, 0, 200))
        painter.setPen(QPen(QColor(255, 255, 255, 255)))
        painter.drawText(text_rect, Qt.AlignmentFlag.AlignCenter, self.title)

        # Region info at bottom-left
        x_val, y_val = self.region['x'], self.region['y']
        w_val, h_val = self.region['width'], self.region['height']

        info_rect = QRect(15, h - 80, 500, 65)
        painter.fillRect(info_rect, QColor(0, 0, 0, 200))

        font_info = QFont("Segoe UI", 12, QFont.Weight.Bold)
        painter.setFont(font_info)
        painter.drawText(QRect(25, h - 75, 470, 28),
                         Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter,
                         f"X: {x_val}  Y: {y_val}")
        painter.drawText(QRect(25, h - 47, 470, 28),
                         Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter,
                         f"W: {w_val}  H: {h_val}")

        # ESC hint at top-right
        esc_rect = QRect(w - 220, 15, 205, 35)
        painter.fillRect(esc_rect, QColor(0, 0, 0, 200))
        font_hint = QFont("Segoe UI", 11)
        painter.setFont(font_hint)
        painter.drawText(esc_rect, Qt.AlignmentFlag.AlignCenter, "Press ESC to close")


class _EscapeHandler(QObject):
    """Global ESC key handler that closes all region overlays."""

    def __init__(self, visualizer: 'RegionVisualizer'):
        super().__init__()
        self.visualizer = visualizer

    def eventFilter(self, obj, event):
        if event.type() == QEvent.Type.KeyPress and event.key() == Qt.Key.Key_Escape:
            logger.info("ESC pressed — closing all region overlays")
            self.visualizer.hide_all()
            return True
        return False


class RegionVisualizer:
    """
    Manager for showing region visualizations.
    Can show multiple regions simultaneously (capture + overlay regions).
    """

    def __init__(self, config_manager=None):
        self.config_manager = config_manager
        self.active_overlays: list[QWidget] = []
        self._esc_handler = None

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def show_both_regions(self) -> tuple[list[RegionVisualizerOverlay], list[RegionVisualizerOverlay]]:
        """
        Show all three region types for each configured region:
          GREEN — region boundary (outermost)
          RED   — OCR capture area (inset 12px)
          BLUE  — translation overlay area (inset 24px)

        Returns (capture_overlays, translation_overlays).
        """
        if not self.config_manager:
            return [], []

        regions_data = self.config_manager.get_setting('capture.regions', [])
        capture_region = self.config_manager.get_setting('capture.region')
        overlay_region = self.config_manager.get_setting('overlay.region')

        # Normalise old string-type capture_region to dict
        if capture_region and not isinstance(capture_region, dict):
            custom = self.config_manager.get_setting('capture.custom_region', None)
            if custom and isinstance(custom, dict):
                capture_region = custom
            else:
                capture_region = {
                    'x': self.config_manager.get_setting('capture.region_x', 0),
                    'y': self.config_manager.get_setting('capture.region_y', 0),
                    'width': self.config_manager.get_setting('capture.region_width', 800),
                    'height': self.config_manager.get_setting('capture.region_height', 600),
                }
        if overlay_region and not isinstance(overlay_region, dict):
            overlay_region = None

        capture_overlays: list[RegionVisualizerOverlay] = []
        translation_overlays: list[RegionVisualizerOverlay] = []

        if regions_data:
            # Multi-region path
            for rd in regions_data:
                if not rd.get('enabled', True):
                    continue
                mon_id = rd.get('monitor_id', 0)
                mon_x, mon_y = self._get_monitor_origin(mon_id)
                cap, trans = self._create_region_overlays(
                    x=rd.get('x', 0) + mon_x,
                    y=rd.get('y', 0) + mon_y,
                    width=rd.get('width', 800), height=rd.get('height', 600),
                    name=rd.get('name', f"Region {rd.get('region_id')}"),
                    monitor_id=mon_id,
                )
                capture_overlays.extend(cap)
                translation_overlays.extend(trans)
                logger.info("Showing 3 overlays for '%s' (ID: %s)",
                            rd.get('name'), rd.get('region_id'))

        elif capture_region and isinstance(capture_region, dict):
            # Single-region fallback — coordinates are monitor-relative,
            # so offset by the monitor's screen origin for correct placement.
            monitor_id = self.config_manager.get_setting('capture.monitor_index', 0)
            mon_x, mon_y = self._get_monitor_origin(monitor_id)

            abs_overlay = None
            if overlay_region and isinstance(overlay_region, dict):
                abs_overlay = {
                    'x': overlay_region.get('x', 0) + mon_x,
                    'y': overlay_region.get('y', 0) + mon_y,
                    'width': overlay_region.get('width', 800),
                    'height': overlay_region.get('height', 600),
                }

            cap, trans = self._create_region_overlays(
                x=capture_region.get('x', 0) + mon_x,
                y=capture_region.get('y', 0) + mon_y,
                width=capture_region.get('width', 800),
                height=capture_region.get('height', 600),
                name="Configured Region", monitor_id=monitor_id,
                overlay_region=abs_overlay,
            )
            capture_overlays.extend(cap)
            translation_overlays.extend(trans)
            logger.info("Showing single region: GREEN (Boundary), RED (OCR), BLUE (Translation)")

        else:
            from PyQt6.QtWidgets import QMessageBox
            QMessageBox.warning(
                None, "No Regions Configured",
                "No regions have been configured yet.\n\n"
                "Use 'Select Capture Region' to set up regions."
            )
            return [], []

        if capture_overlays or translation_overlays:
            self._install_esc_handler()

        return capture_overlays, translation_overlays

    def hide_all(self):
        """Hide all active region overlays and clean up the ESC handler."""
        for overlay in self.active_overlays:
            overlay.close()
        self.active_overlays.clear()
        self._remove_esc_handler()

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    @staticmethod
    def _get_monitor_origin(monitor_id: int) -> tuple[int, int]:
        """Return the (x, y) screen origin of the given monitor index."""
        app = QApplication.instance()
        if app:
            screens = app.screens()
            if 0 <= monitor_id < len(screens):
                geo = screens[monitor_id].geometry()
                return geo.x(), geo.y()
        return 0, 0

    def _create_region_overlays(
        self, x: int, y: int, width: int, height: int,
        name: str, monitor_id: int,
        overlay_region: dict = None,
    ) -> tuple[list[RegionVisualizerOverlay], list[RegionVisualizerOverlay]]:
        """Create GREEN + RED + BLUE overlays for a single region."""
        capture_overlays: list[RegionVisualizerOverlay] = []
        translation_overlays: list[RegionVisualizerOverlay] = []

        # GREEN — region boundary (outermost, labels enabled)
        boundary = self._make_overlay(
            x, y, width, height,
            title=f"🟢 Region: {name} (Monitor {monitor_id})",
            color=QColor(0, 255, 0, 200),
            show_labels=True,
        )
        boundary.show()
        self.active_overlays.append(boundary)

        # RED — OCR capture (inset 12px)
        if width > 24 and height > 24:
            cap = self._make_overlay(
                x + 12, y + 12, width - 24, height - 24,
                title=f"🔴 OCR Capture: {name} (Monitor {monitor_id})",
                color=QColor(255, 0, 0, 200),
                show_labels=False,
            )
            cap.show()
            capture_overlays.append(cap)
            self.active_overlays.append(cap)

        # BLUE — translation overlay (inset 24px, or from explicit overlay_region)
        blue_rect = None
        if overlay_region and isinstance(overlay_region, dict):
            bx = overlay_region.get('x', x + 24)
            by = overlay_region.get('y', y + 24)
            bw = overlay_region.get('width', width - 48)
            bh = overlay_region.get('height', height - 48)
            if bw > 0 and bh > 0:
                blue_rect = (bx, by, bw, bh)
        elif width > _MIN_INSET_SIZE and height > _MIN_INSET_SIZE:
            blue_rect = (x + 24, y + 24, width - 48, height - 48)

        if blue_rect:
            trans = self._make_overlay(
                *blue_rect,
                title=f"🔵 Translation Overlay: {name} (Monitor {monitor_id})",
                color=QColor(0, 0, 255, 200),
                show_labels=False,
            )
            trans.show()
            translation_overlays.append(trans)
            self.active_overlays.append(trans)

        return capture_overlays, translation_overlays

    @staticmethod
    def _make_overlay(x, y, w, h, title, color, show_labels) -> RegionVisualizerOverlay:
        return RegionVisualizerOverlay(
            region={'x': x, 'y': y, 'width': w, 'height': h},
            title=title, color=color,
            border_width=6, show_labels=show_labels,
        )

    def _install_esc_handler(self):
        """Install global ESC key handler."""
        self._remove_esc_handler()  # clean up any stale handler first
        self._esc_handler = _EscapeHandler(self)
        QApplication.instance().installEventFilter(self._esc_handler)

    def _remove_esc_handler(self):
        """Remove global ESC key handler if installed."""
        if self._esc_handler is not None:
            app = QApplication.instance()
            if app:
                app.removeEventFilter(self._esc_handler)
            self._esc_handler = None
