"""
Capture Region Selector - PyQt6 Implementation

Monitor selection and capture region configuration dialog.
"""

from PyQt6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QComboBox, QSpinBox, QCheckBox, QGroupBox, QSlider,
    QTextEdit, QFrame, QWidget, QGridLayout, QApplication
)
from PyQt6.QtCore import Qt, QRect, pyqtSignal, QTimer
from PyQt6.QtGui import QPainter, QPen, QColor, QBrush, QFont, QPalette
from ui.custom_spinbox import CustomSpinBox, CustomDoubleSpinBox
import sys


class MonitorLayoutCanvas(QFrame):
    """Canvas widget for visual monitor layout representation."""
    
    monitorSelected = pyqtSignal(int)  # Emits monitor index when clicked
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setFrameStyle(QFrame.Shape.Box | QFrame.Shadow.Sunken)
        self.setMinimumSize(600, 400)
        self.setStyleSheet("background-color: #2D2D2D;")  # Dark theme
        
        self.monitors = []
        self.selected_monitor_index = 0
        self.monitor_rects = []  # Scaled rectangles for drawing
        
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
            # Find bounding box of all monitors
            min_x = min(m['x'] for m in self.monitors)
            min_y = min(m['y'] for m in self.monitors)
            max_x = max(m['x'] + m['width'] for m in self.monitors)
            max_y = max(m['y'] + m['height'] for m in self.monitors)
            
            total_width = max_x - min_x
            total_height = max_y - min_y
            
            # Calculate scale to fit in canvas with padding
            padding = 40
            canvas_width = self.width() - 2 * padding
            canvas_height = self.height() - 2 * padding
            
            # Prevent division by zero
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
            
            # Calculate scaled rectangles
            self.monitor_rects = []
            for monitor in self.monitors:
                x = padding + (monitor['x'] - min_x) * scale
                y = padding + (monitor['y'] - min_y) * scale
                w = monitor['width'] * scale
                h = monitor['height'] * scale
                self.monitor_rects.append(QRect(int(x), int(y), int(w), int(h)))
        except Exception as e:
            print(f"[ERROR] Failed to calculate monitor layout: {e}")
            import traceback
            traceback.print_exc()
            self.monitor_rects = []
    
    def paintEvent(self, event):
        """Paint the monitor layout."""
        try:
            super().paintEvent(event)
            
            if not self.monitors or not self.monitor_rects:
                return
            
            painter = QPainter(self)
            painter.setRenderHint(QPainter.RenderHint.Antialiasing)
            
            # Draw each monitor
            for i, (monitor, rect) in enumerate(zip(self.monitors, self.monitor_rects)):
                is_selected = (i == self.selected_monitor_index)
                is_primary = monitor.get('is_primary', False)
                
                # Set colors based on state
                if is_selected:
                    border_color = QColor(0, 120, 215)  # Blue
                    fill_color = QColor(200, 230, 255)
                    border_width = 3
                elif is_primary:
                    border_color = QColor(100, 100, 255)  # Light blue
                    fill_color = QColor(240, 240, 255)
                    border_width = 2
                else:
                    border_color = QColor(150, 150, 150)  # Gray
                    fill_color = QColor(255, 255, 255)
                    border_width = 1
                
                # Draw monitor rectangle
                painter.setPen(QPen(border_color, border_width))
                painter.setBrush(QBrush(fill_color))
                painter.drawRect(rect)
                
                # Draw monitor icon
                icon_rect = QRect(rect.x() + rect.width()//2 - 15, rect.y() + 10, 30, 20)
                painter.setPen(QPen(QColor(80, 80, 80), 1))
                painter.setBrush(QBrush(QColor(200, 200, 200)))
                painter.drawRect(icon_rect)
                
                # Draw monitor label
                font = QFont()
                font.setPointSize(10)
                font.setBold(is_selected or is_primary)
                painter.setFont(font)
                painter.setPen(QColor(0, 0, 0))
                
                label = monitor['name']
                if is_primary:
                    label += "\n[PRIMARY]"
                
                text_rect = QRect(rect.x(), rect.y() + 40, rect.width(), rect.height() - 50)
                painter.drawText(text_rect, Qt.AlignmentFlag.AlignCenter, label)
                
                # Draw resolution
                font.setPointSize(8)
                painter.setFont(font)
                painter.setPen(QColor(100, 100, 100))
                res_text = f"{monitor['width']}x{monitor['height']}"
                res_rect = QRect(rect.x(), rect.y() + rect.height() - 30, rect.width(), 20)
                painter.drawText(res_rect, Qt.AlignmentFlag.AlignCenter, res_text)
        except Exception as e:
            print(f"[ERROR] Paint event failed: {e}")
            import traceback
            traceback.print_exc()
    
    def mousePressEvent(self, event):
        """Handle mouse click to select monitor."""
        try:
            if event.button() == Qt.MouseButton.LeftButton:
                # Check which monitor was clicked
                for i, rect in enumerate(self.monitor_rects):
                    if rect.contains(event.pos()):
                        self.selected_monitor_index = i
                        self.monitorSelected.emit(i)
                        self.update()
                        break
        except Exception as e:
            print(f"[ERROR] Mouse press event failed: {e}")
            import traceback
            traceback.print_exc()
    
    def resizeEvent(self, event):
        """Recalculate layout on resize."""
        try:
            super().resizeEvent(event)
            if self.monitors:
                self._calculate_layout()
        except Exception as e:
            print(f"[ERROR] Resize event failed: {e}")
            import traceback
            traceback.print_exc()


class RegionDrawOverlay(QWidget):
    """Fullscreen overlay for drawing capture/overlay regions."""
    
    regionSelected = pyqtSignal(dict)  # Emits {x, y, width, height}
    
    def __init__(self, monitor_geometry, parent=None):
        super().__init__(parent)
        self.monitor_geometry = monitor_geometry
        self.start_pos = None
        self.current_pos = None
        self.drawing = False
        
        # Setup fullscreen overlay
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
        
        # Draw semi-transparent background
        painter.fillRect(self.rect(), QColor(0, 0, 0, 100))
        
        # Draw selection rectangle if drawing
        if self.drawing and self.start_pos and self.current_pos:
            x = min(self.start_pos.x(), self.current_pos.x())
            y = min(self.start_pos.y(), self.current_pos.y())
            w = abs(self.current_pos.x() - self.start_pos.x())
            h = abs(self.current_pos.y() - self.start_pos.y())
            
            # Clear the selected area
            painter.setCompositionMode(QPainter.CompositionMode.CompositionMode_Clear)
            painter.fillRect(x, y, w, h, Qt.GlobalColor.transparent)
            
            # Draw border
            painter.setCompositionMode(QPainter.CompositionMode.CompositionMode_SourceOver)
            painter.setPen(QPen(QColor(0, 120, 215), 2, Qt.PenStyle.DashLine))
            painter.drawRect(x, y, w, h)
            
            # Draw dimensions text
            painter.setPen(QColor(255, 255, 255))
            painter.setFont(QFont("Arial", 12, QFont.Weight.Bold))
            dim_text = f"{w} x {h}"
            painter.drawText(x + 5, y - 5, dim_text)
        
        # Draw instructions
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
                
                if w > 10 and h > 10:  # Minimum size
                    self.regionSelected.emit({'x': x, 'y': y, 'width': w, 'height': h})
                    self.close()
    
    def keyPressEvent(self, event):
        """Handle ESC to cancel."""
        if event.key() == Qt.Key.Key_Escape:
            self.close()



class CaptureRegionSelectorDialog(QDialog):
    """Dialog for selecting monitor and configuring capture/overlay regions."""
    
    def __init__(self, parent=None, config_manager=None, initial_region=None, initial_monitor=None, initial_overlay_region=None):
        super().__init__(parent)
        self.setWindowTitle("Monitor Selection and Configuration")
        self.setModal(False)  # Non-modal - allows interaction with main window
        self.resize(1024, 768)
        
        self.config_manager = config_manager
        self.initial_region = initial_region  # Store initial region for pre-population
        self.initial_monitor = initial_monitor  # Store initial monitor
        self.initial_overlay_region = initial_overlay_region  # Store initial overlay region
        
        try:
            self.monitors = self._detect_monitors()
            print(f"[DEBUG] Detected {len(self.monitors)} monitors")
        except Exception as e:
            print(f"[ERROR] Failed to detect monitors: {e}")
            import traceback
            traceback.print_exc()
            self.monitors = [{'index': 0, 'name': 'Default Monitor', 'x': 0, 'y': 0, 
                            'width': 1920, 'height': 1080, 'is_primary': True, 
                            'dpi': 96.0, 'refresh_rate': 60.0}]
        
        self.selected_monitor_index = initial_monitor if initial_monitor is not None else 0
        self.capture_region = {'x': 0, 'y': 0, 'width': 0, 'height': 0}
        self.overlay_region = {'x': 0, 'y': 0, 'width': 0, 'height': 0}
        self.last_selected_preset = None
        
        try:
            self.init_ui()
            print("[DEBUG] UI initialized")
        except Exception as e:
            print(f"[ERROR] Failed to initialize UI: {e}")
            import traceback
            traceback.print_exc()
            raise
        
        try:
            self.update_monitor_info()
            print("[DEBUG] Monitor info updated")
        except Exception as e:
            print(f"[ERROR] Failed to update monitor info: {e}")
            import traceback
            traceback.print_exc()
        
        # If initial region provided, use it; otherwise restore last preset
        if initial_region:
            try:
                self._set_initial_region(initial_region, initial_overlay_region)
                print(f"[DEBUG] Initial region set: {initial_region}")
                if initial_overlay_region:
                    print(f"[DEBUG] Initial overlay region set: {initial_overlay_region}")
            except Exception as e:
                print(f"[ERROR] Failed to set initial region: {e}")
                import traceback
                traceback.print_exc()
        else:
            try:
                self.restore_last_preset()
                print("[DEBUG] Last preset restored")
            except Exception as e:
                print(f"[ERROR] Failed to restore last preset: {e}")
                import traceback
                traceback.print_exc()
    
    def _detect_monitors(self):
        """Detect available monitors."""
        try:
            app = QApplication.instance()
            if not app:
                print("[ERROR] No QApplication instance found!")
                return [{'index': 0, 'name': 'Default Monitor', 'x': 0, 'y': 0, 
                        'width': 1920, 'height': 1080, 'is_primary': True, 
                        'dpi': 96.0, 'refresh_rate': 60.0}]
            
            screens = app.screens()
            if not screens:
                print("[ERROR] No screens detected!")
                return [{'index': 0, 'name': 'Default Monitor', 'x': 0, 'y': 0, 
                        'width': 1920, 'height': 1080, 'is_primary': True, 
                        'dpi': 96.0, 'refresh_rate': 60.0}]
            
            monitors = []
            for i, screen in enumerate(screens):
                try:
                    geometry = screen.geometry()
                    monitors.append({
                        'index': i,
                        'name': f"Monitor {i}" if screen.name() == "" else screen.name(),
                        'x': geometry.x(),
                        'y': geometry.y(),
                        'width': geometry.width(),
                        'height': geometry.height(),
                        'is_primary': (screen == app.primaryScreen()),
                        'dpi': screen.logicalDotsPerInch(),
                        'refresh_rate': screen.refreshRate()
                    })
                except Exception as e:
                    print(f"[ERROR] Failed to get info for screen {i}: {e}")
                    continue
            
            if not monitors:
                print("[ERROR] No monitors could be detected!")
                return [{'index': 0, 'name': 'Default Monitor', 'x': 0, 'y': 0, 
                        'width': 1920, 'height': 1080, 'is_primary': True, 
                        'dpi': 96.0, 'refresh_rate': 60.0}]
            
            return monitors
        except Exception as e:
            print(f"[ERROR] Monitor detection failed: {e}")
            import traceback
            traceback.print_exc()
            return [{'index': 0, 'name': 'Default Monitor', 'x': 0, 'y': 0, 
                    'width': 1920, 'height': 1080, 'is_primary': True, 
                    'dpi': 96.0, 'refresh_rate': 60.0}]
    
    def init_ui(self):
        """Initialize the UI."""
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(15, 15, 15, 15)
        main_layout.setSpacing(10)
        
        # Title
        title_label = QLabel("Monitor Selection and Configuration")
        title_font = QFont()
        title_font.setPointSize(14)
        title_font.setBold(True)
        title_label.setFont(title_font)
        title_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        main_layout.addWidget(title_label)
        
        # Main content area (horizontal split)
        content_layout = QHBoxLayout()
        content_layout.setSpacing(15)
        
        # Left side - Monitor Layout
        left_widget = QWidget()
        left_layout = QVBoxLayout(left_widget)
        left_layout.setContentsMargins(0, 0, 0, 0)
        
        # Monitor Layout section
        layout_label = QLabel("Monitor Layout")
        layout_label.setProperty("class", "section-header")
        left_layout.addWidget(layout_label)
        
        # Refresh button
        refresh_btn = QPushButton("🔄 Refresh Monitors")
        refresh_btn.clicked.connect(self.refresh_monitors)
        left_layout.addWidget(refresh_btn)
        
        # Monitor count
        self.monitor_count_label = QLabel(f"{len(self.monitors)} monitor(s) detected")
        self.monitor_count_label.setStyleSheet("color: #666; font-size: 10pt;")
        left_layout.addWidget(self.monitor_count_label)
        
        # Legend
        legend_frame = QFrame()
        legend_frame.setFrameStyle(QFrame.Shape.Box)
        legend_layout = QVBoxLayout(legend_frame)
        legend_layout.setContentsMargins(8, 8, 8, 8)
        
        legend_title = QLabel("Legend:")
        legend_title.setStyleSheet("font-weight: bold;")
        legend_layout.addWidget(legend_title)
        
        primary_label = QLabel("🟦 Primary Monitor")
        primary_label.setStyleSheet("font-size: 9pt;")
        legend_layout.addWidget(primary_label)
        
        selected_label = QLabel("🟦 Selected Monitor")
        selected_label.setStyleSheet("font-size: 9pt;")
        legend_layout.addWidget(selected_label)
        
        regular_label = QLabel("⬜ Regular Monitor")
        regular_label.setStyleSheet("font-size: 9pt;")
        legend_layout.addWidget(regular_label)
        
        left_layout.addWidget(legend_frame)
        
        # Monitor canvas
        self.monitor_canvas = MonitorLayoutCanvas()
        self.monitor_canvas.set_monitors(self.monitors)
        self.monitor_canvas.monitorSelected.connect(self.on_monitor_selected)
        left_layout.addWidget(self.monitor_canvas, 1)
        
        # Monitor layout info
        self.layout_info_text = QTextEdit()
        self.layout_info_text.setReadOnly(True)
        self.layout_info_text.setMaximumHeight(80)
        self.layout_info_text.setStyleSheet("font-family: monospace; font-size: 8pt; background-color: #2D2D2D; color: #E0E0E0;")
        left_layout.addWidget(self.layout_info_text)
        
        content_layout.addWidget(left_widget, 1)
        
        # Right side - Monitor Details & Configuration
        right_widget = QWidget()
        right_layout = QVBoxLayout(right_widget)
        right_layout.setContentsMargins(0, 0, 0, 0)
        
        details_label = QLabel("Monitor Details & Configuration")
        details_label.setProperty("class", "section-header")
        right_layout.addWidget(details_label)
        
        # Selected Monitor dropdown
        monitor_group = QGroupBox("Selected Monitor:")
        monitor_group_layout = QVBoxLayout(monitor_group)
        
        self.monitor_combo = QComboBox()
        for monitor in self.monitors:
            label = f"{monitor['name']}"
            if monitor['is_primary']:
                label += " [PRIMARY]"
            self.monitor_combo.addItem(label)
        self.monitor_combo.currentIndexChanged.connect(self.on_monitor_combo_changed)
        monitor_group_layout.addWidget(self.monitor_combo)
        
        right_layout.addWidget(monitor_group)
        
        # Monitor Information
        info_group = QGroupBox("Monitor Information")
        info_layout = QVBoxLayout(info_group)
        
        self.info_text = QTextEdit()
        self.info_text.setReadOnly(True)
        self.info_text.setMaximumHeight(120)
        self.info_text.setStyleSheet("font-family: monospace; font-size: 9pt; background-color: #2D2D2D; color: #E0E0E0;")
        info_layout.addWidget(self.info_text)
        
        right_layout.addWidget(info_group)
        
        # Capture Region
        capture_group = QGroupBox("Capture Region")
        capture_layout = QVBoxLayout(capture_group)
        
        # Quick Presets
        preset_label = QLabel("Quick Presets:")
        preset_label.setStyleSheet("font-weight: bold;")
        capture_layout.addWidget(preset_label)
        
        preset_row = QHBoxLayout()
        self.preset_combo = QComboBox()
        self.preset_combo.addItems(["Full Screen", "Custom Region"])
        self.preset_combo.currentTextChanged.connect(self.on_preset_changed)
        preset_row.addWidget(self.preset_combo, 1)
        
        # Save Preset button
        save_preset_btn = QPushButton("💾")
        save_preset_btn.setToolTip("Save current region as preset")
        save_preset_btn.setMaximumWidth(40)
        save_preset_btn.clicked.connect(self.save_preset)
        preset_row.addWidget(save_preset_btn)
        
        # Delete Preset button
        delete_preset_btn = QPushButton("🗑️")
        delete_preset_btn.setToolTip("Delete selected preset")
        delete_preset_btn.setMaximumWidth(40)
        delete_preset_btn.clicked.connect(self.delete_preset)
        preset_row.addWidget(delete_preset_btn)
        
        capture_layout.addLayout(preset_row)
        
        # Load saved presets
        self.load_presets()
        
        # Custom Region section
        custom_label = QLabel("Custom Region:")
        custom_label.setStyleSheet("font-weight: bold; margin-top: 10px;")
        capture_layout.addWidget(custom_label)
        
        # Draw Region button
        draw_region_btn = QPushButton("✏ Draw Region")
        draw_region_btn.setProperty("class", "action")
        draw_region_btn.clicked.connect(self.draw_capture_region)
        capture_layout.addWidget(draw_region_btn)
        
        # Region coordinates
        coords_layout = QGridLayout()
        coords_layout.setSpacing(5)
        
        coords_layout.addWidget(QLabel("X:"), 0, 0)
        self.capture_x_spin = CustomSpinBox()
        self.capture_x_spin.setRange(0, 10000)
        self.capture_x_spin.valueChanged.connect(self.on_capture_coords_changed)
        coords_layout.addWidget(self.capture_x_spin, 0, 1)
        
        coords_layout.addWidget(QLabel("Y:"), 0, 2)
        self.capture_y_spin = CustomSpinBox()
        self.capture_y_spin.setRange(0, 10000)
        self.capture_y_spin.valueChanged.connect(self.on_capture_coords_changed)
        coords_layout.addWidget(self.capture_y_spin, 0, 3)
        
        coords_layout.addWidget(QLabel("W:"), 1, 0)
        self.capture_w_spin = CustomSpinBox()
        self.capture_w_spin.setRange(0, 10000)
        self.capture_w_spin.valueChanged.connect(self.on_capture_coords_changed)
        coords_layout.addWidget(self.capture_w_spin, 1, 1)
        
        coords_layout.addWidget(QLabel("H:"), 1, 2)
        self.capture_h_spin = CustomSpinBox()
        self.capture_h_spin.setRange(0, 10000)
        self.capture_h_spin.valueChanged.connect(self.on_capture_coords_changed)
        coords_layout.addWidget(self.capture_h_spin, 1, 3)
        
        capture_layout.addLayout(coords_layout)
        
        # Valid region indicator
        self.capture_valid_label = QLabel("✓ Valid region")
        self.capture_valid_label.setStyleSheet("color: green; font-size: 9pt;")
        capture_layout.addWidget(self.capture_valid_label)
        
        right_layout.addWidget(capture_group)
        
        # Overlay Region
        overlay_group = QGroupBox("Translation Overlay Region")
        overlay_layout = QVBoxLayout(overlay_group)
        
        overlay_info = QLabel("Select where translated text should appear:")
        overlay_info.setStyleSheet("font-size: 9pt; color: #666;")
        overlay_info.setWordWrap(True)
        overlay_layout.addWidget(overlay_info)
        
        # Draw Overlay Region button
        draw_overlay_btn = QPushButton("✏ Select Overlay Region")
        draw_overlay_btn.setProperty("class", "action")
        draw_overlay_btn.clicked.connect(self.draw_overlay_region)
        overlay_layout.addWidget(draw_overlay_btn)
        
        # Overlay region coordinates
        overlay_coords_layout = QGridLayout()
        overlay_coords_layout.setSpacing(5)
        
        # X coordinate
        overlay_coords_layout.addWidget(QLabel("X:"), 0, 0)
        self.overlay_x_spin = CustomSpinBox()
        self.overlay_x_spin.setRange(-10000, 10000)
        self.overlay_x_spin.setValue(0)
        self.overlay_x_spin.valueChanged.connect(self.on_overlay_coords_changed)
        overlay_coords_layout.addWidget(self.overlay_x_spin, 0, 1)
        
        # Y coordinate
        overlay_coords_layout.addWidget(QLabel("Y:"), 0, 2)
        self.overlay_y_spin = CustomSpinBox()
        self.overlay_y_spin.setRange(-10000, 10000)
        self.overlay_y_spin.setValue(0)
        self.overlay_y_spin.valueChanged.connect(self.on_overlay_coords_changed)
        overlay_coords_layout.addWidget(self.overlay_y_spin, 0, 3)
        
        # Width
        overlay_coords_layout.addWidget(QLabel("W:"), 1, 0)
        self.overlay_w_spin = CustomSpinBox()
        self.overlay_w_spin.setRange(1, 10000)
        self.overlay_w_spin.setValue(800)
        self.overlay_w_spin.valueChanged.connect(self.on_overlay_coords_changed)
        overlay_coords_layout.addWidget(self.overlay_w_spin, 1, 1)
        
        # Height
        overlay_coords_layout.addWidget(QLabel("H:"), 1, 2)
        self.overlay_h_spin = CustomSpinBox()
        self.overlay_h_spin.setRange(1, 10000)
        self.overlay_h_spin.setValue(600)
        self.overlay_h_spin.valueChanged.connect(self.on_overlay_coords_changed)
        overlay_coords_layout.addWidget(self.overlay_h_spin, 1, 3)
        
        overlay_layout.addLayout(overlay_coords_layout)
        
        # Overlay region validation label
        self.overlay_valid_label = QLabel("✓ Valid region")
        self.overlay_valid_label.setStyleSheet("color: #4CAF50; font-weight: bold;")
        overlay_layout.addWidget(self.overlay_valid_label)
        
        right_layout.addWidget(overlay_group)
        
        # DPI & Scaling
        dpi_group = QGroupBox("DPI & Scaling")
        dpi_layout = QVBoxLayout(dpi_group)
        
        self.dpi_aware_check = QCheckBox("Enable DPI Awareness")
        self.dpi_aware_check.setChecked(True)
        dpi_layout.addWidget(self.dpi_aware_check)
        
        scale_layout = QHBoxLayout()
        scale_layout.addWidget(QLabel("Scaling Factor:"))
        self.scale_slider = QSlider(Qt.Orientation.Horizontal)
        self.scale_slider.setRange(50, 200)
        self.scale_slider.setValue(100)
        self.scale_slider.setTickPosition(QSlider.TickPosition.TicksBelow)
        self.scale_slider.setTickInterval(25)
        scale_layout.addWidget(self.scale_slider)
        self.scale_value_label = QLabel("1.0×")
        scale_layout.addWidget(self.scale_value_label)
        dpi_layout.addLayout(scale_layout)
        
        self.scale_slider.valueChanged.connect(self.on_scale_changed)
        
        right_layout.addWidget(dpi_group)
        
        right_layout.addStretch()
        
        content_layout.addWidget(right_widget, 1)
        
        main_layout.addLayout(content_layout)
        
        # Bottom buttons
        button_layout = QHBoxLayout()
        button_layout.setSpacing(10)
        
        # Test Capture button
        test_btn = QPushButton("Test Capture")
        test_btn.setProperty("class", "action")
        test_btn.clicked.connect(self.test_capture)
        button_layout.addWidget(test_btn)
        
        button_layout.addStretch()
        
        # Apply button
        apply_btn = QPushButton("Apply")
        apply_btn.setProperty("class", "primary")
        apply_btn.setMinimumWidth(100)
        apply_btn.clicked.connect(self.accept)
        button_layout.addWidget(apply_btn)
        
        # Cancel button
        cancel_btn = QPushButton("Cancel")
        cancel_btn.setMinimumWidth(100)
        cancel_btn.clicked.connect(self.reject)
        button_layout.addWidget(cancel_btn)
        
        main_layout.addLayout(button_layout)
    
    def refresh_monitors(self):
        """Refresh monitor detection."""
        self.monitors = self._detect_monitors()
        self.monitor_canvas.set_monitors(self.monitors)
        self.monitor_count_label.setText(f"{len(self.monitors)} monitor(s) detected")
        
        # Update combo box
        self.monitor_combo.clear()
        for monitor in self.monitors:
            label = f"{monitor['name']}"
            if monitor['is_primary']:
                label += " [PRIMARY]"
            self.monitor_combo.addItem(label)
        
        self.update_monitor_info()
        self.update_layout_info()
    
    def on_monitor_selected(self, index):
        """Handle monitor selection from canvas."""
        self.selected_monitor_index = index
        self.monitor_combo.setCurrentIndex(index)
        self.update_monitor_info()
    
    def on_monitor_combo_changed(self, index):
        """Handle monitor selection from combo box."""
        self.selected_monitor_index = index
        self.monitor_canvas.set_selected_monitor(index)
        self.update_monitor_info()
    
    def update_monitor_info(self):
        """Update monitor information display."""
        if not self.monitors or self.selected_monitor_index >= len(self.monitors):
            return
        
        monitor = self.monitors[self.selected_monitor_index]
        
        info_text = f"""Monitor {monitor['index']}: {monitor['name']}

Primary: {'Yes' if monitor['is_primary'] else 'No'}
Resolution: {monitor['width']}x{monitor['height']}
Position: ({monitor['x']}, {monitor['y']})
Work Area: {monitor['width']}x{monitor['height']}
DPI Scale: {monitor['dpi'] / 96.0:.1f}×
Refresh Rate: {monitor['refresh_rate']} Hz"""
        
        self.info_text.setPlainText(info_text)
        
        # Update capture region to full screen by default
        if self.preset_combo.currentText() == "Full Screen":
            self.capture_region = {
                'x': 0,
                'y': 0,
                'width': monitor['width'],
                'height': monitor['height']
            }
            self.update_capture_spinboxes()
        
        self.update_layout_info()
    
    def update_layout_info(self):
        """Update monitor layout information text."""
        if not self.monitors:
            return
        
        # Calculate total desktop size
        min_x = min(m['x'] for m in self.monitors)
        min_y = min(m['y'] for m in self.monitors)
        max_x = max(m['x'] + m['width'] for m in self.monitors)
        max_y = max(m['y'] + m['height'] for m in self.monitors)
        
        total_width = max_x - min_x
        total_height = max_y - min_y
        
        # Determine layout type
        if len(self.monitors) == 1:
            layout_type = "Single"
        elif all(m['y'] == self.monitors[0]['y'] for m in self.monitors):
            layout_type = "Horizontal"
        elif all(m['x'] == self.monitors[0]['x'] for m in self.monitors):
            layout_type = "Vertical"
        else:
            layout_type = "Mixed"
        
        # Find primary monitor
        primary_index = next((i for i, m in enumerate(self.monitors) if m['is_primary']), 0)
        
        info_text = f"""Monitor Layout Information:
Total Monitors: {len(self.monitors)}
Layout Type: {layout_type}
Total Desktop: {total_width}x{total_height}
Primary Monitor: {primary_index}"""
        
        self.layout_info_text.setPlainText(info_text)
    
    def on_preset_changed(self, preset):
        """Handle preset selection change."""
        if preset == "Full Screen" and self.monitors:
            monitor = self.monitors[self.selected_monitor_index]
            self.capture_region = {
                'x': 0,
                'y': 0,
                'width': monitor['width'],
                'height': monitor['height']
            }
            self.overlay_region = {
                'x': 0,
                'y': 0,
                'width': monitor['width'],
                'height': monitor['height']
            }
            self.update_capture_spinboxes()
            self.update_overlay_spinboxes()
        elif preset in self.saved_presets:
            # Load saved preset
            preset_data = self.saved_presets[preset]
            self.capture_region = preset_data.get('capture_region', self.capture_region)
            self.overlay_region = preset_data.get('overlay_region', self.overlay_region)
            self.update_capture_spinboxes()
            self.update_overlay_spinboxes()
            print(f"[INFO] Loaded preset: {preset}")
    
    def update_capture_spinboxes(self):
        """Update capture region spinboxes."""
        self.capture_x_spin.blockSignals(True)
        self.capture_y_spin.blockSignals(True)
        self.capture_w_spin.blockSignals(True)
        self.capture_h_spin.blockSignals(True)
        
        self.capture_x_spin.setValue(self.capture_region['x'])
        self.capture_y_spin.setValue(self.capture_region['y'])
        self.capture_w_spin.setValue(self.capture_region['width'])
        self.capture_h_spin.setValue(self.capture_region['height'])
        
        self.capture_x_spin.blockSignals(False)
        self.capture_y_spin.blockSignals(False)
        self.capture_w_spin.blockSignals(False)
        self.capture_h_spin.blockSignals(False)
        
        self.validate_capture_region()
    
    def update_overlay_spinboxes(self):
        """Update overlay region spinboxes."""
        self.overlay_x_spin.blockSignals(True)
        self.overlay_y_spin.blockSignals(True)
        self.overlay_w_spin.blockSignals(True)
        self.overlay_h_spin.blockSignals(True)
        
        self.overlay_x_spin.setValue(self.overlay_region['x'])
        self.overlay_y_spin.setValue(self.overlay_region['y'])
        self.overlay_w_spin.setValue(self.overlay_region['width'])
        self.overlay_h_spin.setValue(self.overlay_region['height'])
        
        self.overlay_x_spin.blockSignals(False)
        self.overlay_y_spin.blockSignals(False)
        self.overlay_w_spin.blockSignals(False)
        self.overlay_h_spin.blockSignals(False)
        
        # Validate overlay region
        if self.overlay_region['width'] > 0 and self.overlay_region['height'] > 0:
            self.overlay_valid_label.setText("✓ Valid region")
            self.overlay_valid_label.setStyleSheet("color: #4CAF50; font-weight: bold;")
        else:
            self.overlay_valid_label.setText("✗ Invalid region")
            self.overlay_valid_label.setStyleSheet("color: #F44336; font-weight: bold;")
    
    def on_capture_coords_changed(self):
        """Handle capture coordinates change."""
        self.capture_region = {
            'x': self.capture_x_spin.value(),
            'y': self.capture_y_spin.value(),
            'width': self.capture_w_spin.value(),
            'height': self.capture_h_spin.value()
        }
        self.validate_capture_region()
    
    def validate_capture_region(self):
        """Validate capture region."""
        is_valid = (
            self.capture_region['width'] > 0 and
            self.capture_region['height'] > 0
        )
        
        if is_valid:
            self.capture_valid_label.setText("✓ Valid region")
            self.capture_valid_label.setStyleSheet("color: green; font-size: 9pt;")
        else:
            self.capture_valid_label.setText("✗ Invalid region")
            self.capture_valid_label.setStyleSheet("color: red; font-size: 9pt;")
    
    def draw_capture_region(self):
        """Open overlay to draw capture region."""
        if not self.monitors or self.selected_monitor_index >= len(self.monitors):
            return
        
        monitor = self.monitors[self.selected_monitor_index]
        monitor_geometry = QRect(
            monitor['x'],
            monitor['y'],
            monitor['width'],
            monitor['height']
        )
        
        # Create and show overlay
        overlay = RegionDrawOverlay(monitor_geometry, self)
        overlay.regionSelected.connect(self.on_capture_region_drawn)
        overlay.show()
    
    def on_capture_region_drawn(self, region):
        """Handle capture region drawn."""
        self.capture_region = region
        self.preset_combo.setCurrentText("Custom Region")
        self.update_capture_spinboxes()
        print(f"[INFO] Capture region drawn: {region}")
    
    def draw_overlay_region(self):
        """Open overlay to draw overlay region."""
        if not self.monitors or self.selected_monitor_index >= len(self.monitors):
            return
        
        monitor = self.monitors[self.selected_monitor_index]
        monitor_geometry = QRect(
            monitor['x'],
            monitor['y'],
            monitor['width'],
            monitor['height']
        )
        
        # Create and show overlay
        overlay = RegionDrawOverlay(monitor_geometry, self)
        overlay.regionSelected.connect(self.on_overlay_region_drawn)
        overlay.show()
    
    def on_overlay_region_drawn(self, region):
        """Handle overlay region drawn."""
        self.overlay_region = region
        self.preset_combo.setCurrentText("Custom Region")
        self.update_overlay_spinboxes()
        print(f"[INFO] Overlay region drawn: {region}")
    
    def on_scale_changed(self, value):
        """Handle scaling slider change."""
        scale = value / 100.0
        self.scale_value_label.setText(f"{scale:.1f}×")
    
    def test_capture(self):
        """Test the capture configuration."""
        print(f"[INFO] Testing capture configuration:")
        print(f"  Monitor: {self.selected_monitor_index}")
        print(f"  Capture Region: {self.capture_region}")
        print(f"  Overlay Region: {self.overlay_region}")
        
        # Show a message
        from PyQt6.QtWidgets import QMessageBox
        QMessageBox.information(
            self,
            "Test Capture",
            f"Capture configuration:\n\n"
            f"Monitor: {self.monitors[self.selected_monitor_index]['name']}\n"
            f"Capture: {self.capture_region['width']}x{self.capture_region['height']} "
            f"at ({self.capture_region['x']}, {self.capture_region['y']})\n\n"
            f"This would capture the specified region."
        )
    
    def get_configuration(self):
        """Get the current configuration."""
        config = {
            'monitor': self.selected_monitor_index,
            'monitor_info': self.monitors[self.selected_monitor_index],
            'capture_region': self.capture_region,
            'overlay_region': self.overlay_region,
            'dpi_aware': self.dpi_aware_check.isChecked(),
            'scale_factor': self.scale_slider.value() / 100.0,
            'selected_preset': self.preset_combo.currentText()
        }
        
        # Save the selected preset to config if config_manager is available
        if self.config_manager:
            self.config_manager.set_setting('capture.selected_preset', self.preset_combo.currentText())
        
        return config
    
    def load_presets(self):
        """Load saved region presets from consolidated config."""
        if self.config_manager:
            # Load from consolidated config
            self.saved_presets = self.config_manager.get_region_presets()
            
            # Add saved presets to combo box
            for preset_name in self.saved_presets.keys():
                if preset_name not in ["Full Screen", "Custom Region"]:
                    self.preset_combo.addItem(preset_name)
            
            if self.saved_presets:
                print(f"[INFO] Loaded {len(self.saved_presets)} region presets from consolidated config")
        else:
            # Fallback: load from separate file for backward compatibility
            import json
            from pathlib import Path
            
            preset_file = Path('config/region_presets.json')
            if preset_file.exists():
                try:
                    with open(preset_file, 'r', encoding='utf-8') as f:
                        self.saved_presets = json.load(f)
                    
                    # Add saved presets to combo box
                    for preset_name in self.saved_presets.keys():
                        if preset_name not in ["Full Screen", "Custom Region"]:
                            self.preset_combo.addItem(preset_name)
                    
                    print(f"[INFO] Loaded {len(self.saved_presets)} region presets")
                except Exception as e:
                    print(f"[WARNING] Failed to load presets: {e}")
                    self.saved_presets = {}
            else:
                self.saved_presets = {}
    
    def save_preset(self):
        """Save current region configuration as a preset."""
        from PyQt6.QtWidgets import QInputDialog
        import json
        from pathlib import Path
        
        # Ask for preset name
        preset_name, ok = QInputDialog.getText(
            self,
            "Save Preset",
            "Enter preset name (e.g., 'Manga', 'Game', 'Video'):"
        )
        
        if not ok or not preset_name:
            return
        
        # Don't allow overwriting built-in presets
        if preset_name in ["Full Screen", "Custom Region"]:
            from PyQt6.QtWidgets import QMessageBox
            QMessageBox.warning(
                self,
                "Invalid Name",
                "Cannot use reserved preset names."
            )
            return
        
        # Save preset
        try:
            preset_data = {
                'capture_region': self.capture_region,
                'overlay_region': self.overlay_region
            }
            
            self.saved_presets[preset_name] = preset_data
            
            # Save to consolidated config
            if self.config_manager:
                self.config_manager.set_region_preset(preset_name, preset_data)
                self.config_manager.save_config()
                print(f"[INFO] Saved preset '{preset_name}' to consolidated config")
            else:
                # Fallback: save to separate file for backward compatibility
                preset_file = Path('config/region_presets.json')
                preset_file.parent.mkdir(parents=True, exist_ok=True)
                
                try:
                    with open(preset_file, 'w', encoding='utf-8') as f:
                        json.dump(self.saved_presets, f, indent=2)
                    print(f"[INFO] Saved preset '{preset_name}' to separate file")
                except Exception as e:
                    print(f"[ERROR] Failed to save preset: {e}")
                    return
            
            # Add to combo box if not already there
            if self.preset_combo.findText(preset_name) == -1:
                self.preset_combo.addItem(preset_name)
            
            # Select the new preset
            self.preset_combo.setCurrentText(preset_name)
            
            print(f"[INFO] Saved preset: {preset_name}")
            
            from PyQt6.QtWidgets import QMessageBox
            QMessageBox.information(
                self,
                "Preset Saved",
                f"Region preset '{preset_name}' has been saved successfully!"
            )
        except Exception as e:
            print(f"[ERROR] Failed to save preset: {e}")
            from PyQt6.QtWidgets import QMessageBox
            QMessageBox.critical(
                self,
                "Save Failed",
                f"Failed to save preset:\n\n{str(e)}"
            )
    
    def delete_preset(self):
        """Delete the selected preset."""
        preset_name = self.preset_combo.currentText()
        
        # Don't allow deleting built-in presets
        if preset_name in ["Full Screen", "Custom Region"]:
            from PyQt6.QtWidgets import QMessageBox
            QMessageBox.warning(
                self,
                "Cannot Delete",
                "Cannot delete built-in presets."
            )
            return
        
        # Confirm deletion
        from PyQt6.QtWidgets import QMessageBox
        reply = QMessageBox.question(
            self,
            "Delete Preset",
            f"Are you sure you want to delete preset '{preset_name}'?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            QMessageBox.StandardButton.No
        )
        
        if reply != QMessageBox.StandardButton.Yes:
            return
        
        # Delete preset
        if preset_name in self.saved_presets:
            del self.saved_presets[preset_name]
            
            # Save to consolidated config
            if self.config_manager:
                self.config_manager.delete_region_preset(preset_name)
                self.config_manager.save_config()
                print(f"[INFO] Deleted preset '{preset_name}' from consolidated config")
            else:
                # Fallback: save to separate file for backward compatibility
                import json
                from pathlib import Path
                preset_file = Path('config/region_presets.json')
                
                try:
                    with open(preset_file, 'w', encoding='utf-8') as f:
                        json.dump(self.saved_presets, f, indent=2)
                    print(f"[INFO] Deleted preset '{preset_name}' from separate file")
                except Exception as e:
                    print(f"[ERROR] Failed to delete preset: {e}")
                    return
                
                # Remove from combo box
                index = self.preset_combo.findText(preset_name)
                if index >= 0:
                    self.preset_combo.removeItem(index)
                
                # Select "Custom Region"
                self.preset_combo.setCurrentText("Custom Region")
                
                print(f"[INFO] Deleted preset: {preset_name}")
                
                QMessageBox.information(
                    self,
                    "Preset Deleted",
                    f"Preset '{preset_name}' has been deleted."
                )
    
    def on_overlay_coords_changed(self):
        """Handle overlay region coordinate changes."""
        self.overlay_region = {
            'x': self.overlay_x_spin.value(),
            'y': self.overlay_y_spin.value(),
            'width': self.overlay_w_spin.value(),
            'height': self.overlay_h_spin.value()
        }
        
        # Validate region
        if self.overlay_region['width'] > 0 and self.overlay_region['height'] > 0:
            self.overlay_valid_label.setText("✓ Valid region")
            self.overlay_valid_label.setStyleSheet("color: #4CAF50; font-weight: bold;")
        else:
            self.overlay_valid_label.setText("✗ Invalid region")
            self.overlay_valid_label.setStyleSheet("color: #F44336; font-weight: bold;")
    
    def restore_last_preset(self):
        """Restore the last selected preset from configuration."""
        if not self.config_manager:
            return
        
        # Get the last selected preset from config
        last_preset = self.config_manager.get_setting('capture.selected_preset', 'Full Screen')
        
        # Check if the preset exists in the combo box
        index = self.preset_combo.findText(last_preset)
        if index >= 0:
            # Block signals to prevent triggering on_preset_changed during initialization
            self.preset_combo.blockSignals(True)
            self.preset_combo.setCurrentIndex(index)
            self.preset_combo.blockSignals(False)
            
            # Manually trigger preset loading
            self.on_preset_changed(last_preset)
            
            print(f"[INFO] Restored last selected preset: {last_preset}")
        else:
            print(f"[WARNING] Last preset '{last_preset}' not found, defaulting to 'Full Screen'")
    
    def _set_initial_region(self, region, overlay_region=None):
        """
        Set initial region values when editing an existing region.
        
        Args:
            region: Dictionary with keys 'x', 'y', 'width', 'height'
            overlay_region: Optional dictionary with overlay region coordinates
        """
        # Block signals to prevent triggering validation during initialization
        self.capture_x_spin.blockSignals(True)
        self.capture_y_spin.blockSignals(True)
        self.capture_w_spin.blockSignals(True)
        self.capture_h_spin.blockSignals(True)
        
        # Set the capture region values
        self.capture_x_spin.setValue(region.get('x', 0))
        self.capture_y_spin.setValue(region.get('y', 0))
        self.capture_w_spin.setValue(region.get('width', 0))
        self.capture_h_spin.setValue(region.get('height', 0))
        
        # Update capture_region
        self.capture_region = {
            'x': region.get('x', 0),
            'y': region.get('y', 0),
            'width': region.get('width', 0),
            'height': region.get('height', 0)
        }
        
        # Unblock signals
        self.capture_x_spin.blockSignals(False)
        self.capture_y_spin.blockSignals(False)
        self.capture_w_spin.blockSignals(False)
        self.capture_h_spin.blockSignals(False)
        
        # Set overlay region if provided
        if overlay_region:
            self.overlay_x_spin.blockSignals(True)
            self.overlay_y_spin.blockSignals(True)
            self.overlay_w_spin.blockSignals(True)
            self.overlay_h_spin.blockSignals(True)
            
            self.overlay_x_spin.setValue(overlay_region.get('x', 0))
            self.overlay_y_spin.setValue(overlay_region.get('y', 0))
            self.overlay_w_spin.setValue(overlay_region.get('width', 800))
            self.overlay_h_spin.setValue(overlay_region.get('height', 600))
            
            # Update overlay_region
            self.overlay_region = {
                'x': overlay_region.get('x', 0),
                'y': overlay_region.get('y', 0),
                'width': overlay_region.get('width', 800),
                'height': overlay_region.get('height', 600)
            }
            
            self.overlay_x_spin.blockSignals(False)
            self.overlay_y_spin.blockSignals(False)
            self.overlay_w_spin.blockSignals(False)
            self.overlay_h_spin.blockSignals(False)
            
            # Update overlay validation
            self.validate_overlay_region()
        
        # Update capture validation
        self.validate_capture_region()
        
        # Set preset to "Custom Region" since we're editing
        index = self.preset_combo.findText("Custom Region")
        if index >= 0:
            self.preset_combo.blockSignals(True)
            self.preset_combo.setCurrentIndex(index)
            self.preset_combo.blockSignals(False)
