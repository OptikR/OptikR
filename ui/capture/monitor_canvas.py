"""
Monitor Layout Canvas

Visual canvas widget that renders a scaled layout of all detected monitors,
with click-to-select interaction.
"""

import logging
from PyQt6.QtWidgets import QFrame
from PyQt6.QtCore import Qt, QRect, pyqtSignal
from PyQt6.QtGui import QPainter, QPen, QColor, QBrush, QFont

logger = logging.getLogger(__name__)


class MonitorLayoutCanvas(QFrame):
    """Canvas widget for visual monitor layout representation."""

    monitorSelected = pyqtSignal(int)

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setFrameStyle(QFrame.Shape.Box | QFrame.Shadow.Sunken)
        self.setMinimumSize(300, 180)
        self.setStyleSheet("background-color: #2D2D2D;")

        self.monitors = []
        self.selected_monitor_index = 0
        self.monitor_rects = []

    def set_monitors(self, monitors):
        """Set monitors to display."""
        self.monitors = monitors
        self._calculate_layout()
        self.update()

    def set_selected_monitor(self, index):
        """Set the selected monitor."""
        if 0 <= index < len(self.monitors):
            self.selected_monitor_index = index
            self.update()

    def _calculate_layout(self):
        """Calculate scaled monitor positions for display."""
        if not self.monitors:
            return

        try:
            min_x = min(m['x'] for m in self.monitors)
            min_y = min(m['y'] for m in self.monitors)
            max_x = max(m['x'] + m['width'] for m in self.monitors)
            max_y = max(m['y'] + m['height'] for m in self.monitors)

            total_width = max_x - min_x
            total_height = max_y - min_y

            padding = 40
            canvas_width = self.width() - 2 * padding
            canvas_height = self.height() - 2 * padding

            if total_width <= 0:
                total_width = 1920
            if total_height <= 0:
                total_height = 1080
            if canvas_width <= 0:
                canvas_width = 600
            if canvas_height <= 0:
                canvas_height = 400

            scale_x = canvas_width / total_width
            scale_y = canvas_height / total_height
            scale = min(scale_x, scale_y)

            self.monitor_rects = []
            for monitor in self.monitors:
                x = padding + (monitor['x'] - min_x) * scale
                y = padding + (monitor['y'] - min_y) * scale
                w = monitor['width'] * scale
                h = monitor['height'] * scale
                self.monitor_rects.append(QRect(int(x), int(y), int(w), int(h)))
        except Exception:
            logger.exception("Failed to calculate monitor layout")
            self.monitor_rects = []

    def paintEvent(self, event):
        """Paint the monitor layout."""
        super().paintEvent(event)

        if not self.monitors or not self.monitor_rects:
            return

        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)

        for i, (monitor, rect) in enumerate(zip(self.monitors, self.monitor_rects)):
            is_selected = (i == self.selected_monitor_index)
            is_primary = monitor.get('is_primary', False)

            if is_selected:
                border_color = QColor(0, 120, 215)
                fill_color = QColor(200, 230, 255)
                border_width = 3
            elif is_primary:
                border_color = QColor(100, 100, 255)
                fill_color = QColor(240, 240, 255)
                border_width = 2
            else:
                border_color = QColor(150, 150, 150)
                fill_color = QColor(255, 255, 255)
                border_width = 1

            painter.setPen(QPen(border_color, border_width))
            painter.setBrush(QBrush(fill_color))
            painter.drawRect(rect)

            icon_rect = QRect(rect.x() + rect.width()//2 - 15, rect.y() + 10, 30, 20)
            painter.setPen(QPen(QColor(80, 80, 80), 1))
            painter.setBrush(QBrush(QColor(200, 200, 200)))
            painter.drawRect(icon_rect)

            res_font = QFont()
            res_font.setPointSize(8)
            res_text = f"{monitor['width']}x{monitor['height']}"
            res_height = 20
            res_rect = QRect(rect.x(), rect.y() + rect.height() - res_height - 5, rect.width(), res_height)

            font = QFont()
            label_font_size = 10 if rect.width() > 100 else 8
            font.setPointSize(label_font_size)
            font.setBold(is_selected or is_primary)
            painter.setFont(font)
            painter.setPen(QColor(0, 0, 0))

            label = monitor['name']
            if is_primary:
                label += "\n[PRIMARY]"

            label_top = rect.y() + 35
            label_bottom = res_rect.y() - 2
            text_rect = QRect(rect.x(), label_top, rect.width(), max(label_bottom - label_top, 20))
            painter.drawText(text_rect, Qt.AlignmentFlag.AlignCenter, label)

            painter.setFont(res_font)
            painter.setPen(QColor(100, 100, 100))
            painter.drawText(res_rect, Qt.AlignmentFlag.AlignCenter, res_text)

    def mousePressEvent(self, event):
        """Handle mouse click to select monitor."""
        if event.button() == Qt.MouseButton.LeftButton:
            for i, rect in enumerate(self.monitor_rects):
                if rect.contains(event.pos()):
                    self.selected_monitor_index = i
                    self.monitorSelected.emit(i)
                    self.update()
                    break

    def resizeEvent(self, event):
        """Recalculate layout on resize."""
        super().resizeEvent(event)
        if self.monitors:
            self._calculate_layout()
