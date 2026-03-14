"""
Region Draw Overlays

Fullscreen transparent overlay widgets that let the user draw a rectangular
region by click-and-drag.  Two variants:

* ``RegionDrawOverlay`` — covers a single monitor.
* ``MultiMonitorRegionDrawOverlay`` — spans the entire virtual desktop so the
  user can draw a region on *any* monitor.
"""

from PyQt6.QtWidgets import QWidget
from PyQt6.QtCore import Qt, QRect, pyqtSignal
from PyQt6.QtGui import QPainter, QPen, QColor, QFont


class RegionDrawOverlay(QWidget):
    """Fullscreen overlay for drawing capture/overlay regions."""

    regionSelected = pyqtSignal(dict)

    def __init__(self, monitor_geometry, parent=None):
        super().__init__(parent)
        self.monitor_geometry = monitor_geometry
        self.start_pos = None
        self.current_pos = None
        self.drawing = False

        self.setWindowFlags(
            Qt.WindowType.FramelessWindowHint |
            Qt.WindowType.WindowStaysOnTopHint |
            Qt.WindowType.Tool
        )
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
        self.setGeometry(monitor_geometry)
        self.setCursor(Qt.CursorShape.CrossCursor)

    def paintEvent(self, event):
        """Paint the overlay with semi-transparent background and selection rectangle."""
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)

        painter.fillRect(self.rect(), QColor(0, 0, 0, 100))

        if self.drawing and self.start_pos and self.current_pos:
            x = min(self.start_pos.x(), self.current_pos.x())
            y = min(self.start_pos.y(), self.current_pos.y())
            w = abs(self.current_pos.x() - self.start_pos.x())
            h = abs(self.current_pos.y() - self.start_pos.y())

            painter.setCompositionMode(QPainter.CompositionMode.CompositionMode_Clear)
            painter.fillRect(x, y, w, h, Qt.GlobalColor.transparent)

            painter.setCompositionMode(QPainter.CompositionMode.CompositionMode_SourceOver)
            painter.setPen(QPen(QColor(0, 120, 215), 2, Qt.PenStyle.DashLine))
            painter.drawRect(x, y, w, h)

            painter.setPen(QColor(255, 255, 255))
            painter.setFont(QFont("Arial", 12, QFont.Weight.Bold))
            dim_text = f"{w} x {h}"
            painter.drawText(x + 5, y - 5, dim_text)

        painter.setPen(QColor(255, 255, 255))
        painter.setFont(QFont("Arial", 14))
        painter.drawText(20, 30, "Click and drag to select region. Press ESC to cancel.")

    def mousePressEvent(self, event):
        """Start drawing region."""
        if event.button() == Qt.MouseButton.LeftButton:
            self.start_pos = event.pos()
            self.current_pos = event.pos()
            self.drawing = True
            self.update()

    def mouseMoveEvent(self, event):
        """Update region while dragging."""
        if self.drawing:
            self.current_pos = event.pos()
            self.update()

    def mouseReleaseEvent(self, event):
        """Finish drawing region."""
        if event.button() == Qt.MouseButton.LeftButton and self.drawing:
            self.drawing = False

            if self.start_pos and self.current_pos:
                x = min(self.start_pos.x(), self.current_pos.x())
                y = min(self.start_pos.y(), self.current_pos.y())
                w = abs(self.current_pos.x() - self.start_pos.x())
                h = abs(self.current_pos.y() - self.start_pos.y())

                if w > 10 and h > 10:
                    self.regionSelected.emit({'x': x, 'y': y, 'width': w, 'height': h})
                    self.close()

    def keyPressEvent(self, event):
        """Handle ESC to cancel."""
        if event.key() == Qt.Key.Key_Escape:
            self.close()


class MultiMonitorRegionDrawOverlay(QWidget):
    """
    Fullscreen overlay that spans ALL monitors simultaneously,
    allowing the user to draw a region anywhere across the virtual desktop.
    """

    regionSelected = pyqtSignal(dict)

    def __init__(self, monitors, parent=None):
        super().__init__(parent)
        self.monitors = monitors
        self.start_pos = None
        self.current_pos = None
        self.drawing = False

        min_x = min(m['x'] for m in monitors)
        min_y = min(m['y'] for m in monitors)
        max_x = max(m['x'] + m['width'] for m in monitors)
        max_y = max(m['y'] + m['height'] for m in monitors)
        self.virtual_rect = QRect(min_x, min_y, max_x - min_x, max_y - min_y)

        self.setWindowFlags(
            Qt.WindowType.FramelessWindowHint
            | Qt.WindowType.WindowStaysOnTopHint
            | Qt.WindowType.Tool
        )
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
        self.setGeometry(self.virtual_rect)
        self.setCursor(Qt.CursorShape.CrossCursor)

    def _to_local(self, global_pos):
        """Convert a global screen position to widget-local coordinates."""
        return global_pos - self.virtual_rect.topLeft()

    def _monitor_index_at(self, global_x, global_y):
        """Return the monitor index that contains the given global point."""
        for i, m in enumerate(self.monitors):
            if (m['x'] <= global_x < m['x'] + m['width']
                    and m['y'] <= global_y < m['y'] + m['height']):
                return i
        return 0

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)

        painter.fillRect(self.rect(), QColor(0, 0, 0, 100))

        painter.setPen(QPen(QColor(255, 255, 255, 60), 1, Qt.PenStyle.DashLine))
        for m in self.monitors:
            local = self._to_local(QRect(m['x'], m['y'], m['width'], m['height']).topLeft())
            painter.drawRect(local.x(), local.y(), m['width'], m['height'])
            painter.setPen(QColor(255, 255, 255, 120))
            painter.setFont(QFont("Arial", 10))
            label = m['name']
            if m.get('is_primary'):
                label += " [PRIMARY]"
            painter.drawText(local.x() + 10, local.y() + 25, label)
            painter.setPen(QPen(QColor(255, 255, 255, 60), 1, Qt.PenStyle.DashLine))

        if self.drawing and self.start_pos and self.current_pos:
            x = min(self.start_pos.x(), self.current_pos.x())
            y = min(self.start_pos.y(), self.current_pos.y())
            w = abs(self.current_pos.x() - self.start_pos.x())
            h = abs(self.current_pos.y() - self.start_pos.y())

            painter.setCompositionMode(QPainter.CompositionMode.CompositionMode_Clear)
            painter.fillRect(x, y, w, h, Qt.GlobalColor.transparent)

            painter.setCompositionMode(QPainter.CompositionMode.CompositionMode_SourceOver)
            painter.setPen(QPen(QColor(0, 120, 215), 2, Qt.PenStyle.DashLine))
            painter.drawRect(x, y, w, h)

            painter.setPen(QColor(255, 255, 255))
            painter.setFont(QFont("Arial", 12, QFont.Weight.Bold))
            painter.drawText(x + 5, y - 5, f"{w} x {h}")

        painter.setPen(QColor(255, 255, 255))
        painter.setFont(QFont("Arial", 14))
        painter.drawText(20, 30, "Click and drag to select region on any monitor. Press ESC to cancel.")

    def mousePressEvent(self, event):
        if event.button() == Qt.MouseButton.LeftButton:
            self.start_pos = event.pos()
            self.current_pos = event.pos()
            self.drawing = True
            self.update()

    def mouseMoveEvent(self, event):
        if self.drawing:
            self.current_pos = event.pos()
            self.update()

    def mouseReleaseEvent(self, event):
        if event.button() == Qt.MouseButton.LeftButton and self.drawing:
            self.drawing = False
            if self.start_pos and self.current_pos:
                lx = min(self.start_pos.x(), self.current_pos.x())
                ly = min(self.start_pos.y(), self.current_pos.y())
                w = abs(self.current_pos.x() - self.start_pos.x())
                h = abs(self.current_pos.y() - self.start_pos.y())

                if w > 10 and h > 10:
                    gx = lx + self.virtual_rect.x()
                    gy = ly + self.virtual_rect.y()
                    monitor_idx = self._monitor_index_at(gx, gy)
                    mon = self.monitors[monitor_idx]
                    rel_x = gx - mon['x']
                    rel_y = gy - mon['y']
                    self.regionSelected.emit({
                        'x': rel_x, 'y': rel_y,
                        'width': w, 'height': h,
                        'monitor_index': monitor_idx,
                    })
                    self.close()

    def keyPressEvent(self, event):
        if event.key() == Qt.Key.Key_Escape:
            self.close()
