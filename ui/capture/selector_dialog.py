"""
Capture Region Selector Dialog

Main dialog for selecting a monitor, configuring capture/overlay regions,
managing region presets, and multi-region capture.
"""

import logging
from PyQt6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QComboBox, QCheckBox, QGroupBox, QSlider,
    QTextEdit, QFrame, QWidget, QGridLayout, QApplication,
    QScrollArea, QListWidget, QListWidgetItem,
    QInputDialog, QMessageBox,
)
from PyQt6.QtCore import Qt, QRect
from PyQt6.QtGui import QFont
from ui.common.widgets.custom_spinbox import CustomSpinBox
from app.localization import tr

from .monitor_canvas import MonitorLayoutCanvas
from .region_draw_overlay import RegionDrawOverlay, MultiMonitorRegionDrawOverlay

logger = logging.getLogger(__name__)


class CaptureRegionSelectorDialog(QDialog):
    """Dialog for selecting monitor and configuring capture/overlay regions."""

    def __init__(self, parent=None, config_manager=None, initial_region=None, initial_monitor=None, initial_overlay_region=None):
        super().__init__(parent)
        self.setWindowTitle(tr("monitor_selection_and_configuration"))
        self.setModal(False)
        self.resize(1150, 850)

        self.config_manager = config_manager
        self.initial_region = initial_region
        self.initial_monitor = initial_monitor
        self.initial_overlay_region = initial_overlay_region

        try:
            self.monitors = self._detect_monitors()
            logger.debug("Detected %d monitors", len(self.monitors))
        except Exception:
            logger.exception("Failed to detect monitors")
            self.monitors = [dict(self._DEFAULT_MONITOR)]

        self.selected_monitor_index = initial_monitor if initial_monitor is not None else 0
        self.capture_region = {'x': 0, 'y': 0, 'width': 0, 'height': 0}
        self.overlay_region = {'x': 0, 'y': 0, 'width': 0, 'height': 0}
        self.saved_presets = {}

        try:
            self.init_ui()
        except Exception:
            logger.exception("Failed to initialize UI")
            raise

        try:
            self.update_monitor_info()
        except Exception:
            logger.exception("Failed to update monitor info")

        if initial_region:
            try:
                self._set_initial_region(initial_region, initial_overlay_region)
                logger.debug("Initial region set: %s", initial_region)
            except Exception:
                logger.exception("Failed to set initial region")
        else:
            try:
                self.restore_last_preset()
            except Exception:
                logger.exception("Failed to restore last preset")

    _DEFAULT_MONITOR = {'index': 0, 'name': 'Default Monitor', 'x': 0, 'y': 0,
                        'width': 1920, 'height': 1080, 'is_primary': True,
                        'dpi': 96.0, 'refresh_rate': 60.0}

    def _detect_monitors(self):
        """Detect available monitors."""
        try:
            app = QApplication.instance()
            if not app:
                logger.error("No QApplication instance found")
                return [dict(self._DEFAULT_MONITOR)]

            screens = app.screens()
            if not screens:
                logger.error("No screens detected")
                return [dict(self._DEFAULT_MONITOR)]

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
                except Exception:
                    logger.exception("Failed to get info for screen %d", i)
                    continue

            if not monitors:
                logger.error("No monitors could be detected")
                return [dict(self._DEFAULT_MONITOR)]

            return monitors
        except Exception:
            logger.exception("Monitor detection failed")
            return [dict(self._DEFAULT_MONITOR)]

    def init_ui(self):
        """Initialize the UI."""
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(10, 10, 10, 10)
        main_layout.setSpacing(8)

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
        content_layout.setSpacing(10)

        # Left side - Monitor Layout
        left_widget = QWidget()
        left_widget.setObjectName("selectorLeftPanel")
        left_widget.setStyleSheet("#selectorLeftPanel { background-color: #2D2D2D; }")
        left_layout = QVBoxLayout(left_widget)
        left_layout.setContentsMargins(0, 0, 0, 0)
        left_layout.setSpacing(6)

        layout_label = QLabel("Monitor Layout")
        layout_label.setProperty("class", "section-header")
        left_layout.addWidget(layout_label)

        refresh_btn = QPushButton("🔄 Refresh Monitors")
        refresh_btn.clicked.connect(self.refresh_monitors)
        left_layout.addWidget(refresh_btn)

        self.monitor_count_label = QLabel(f"{len(self.monitors)} monitor(s) detected")
        self.monitor_count_label.setStyleSheet("color: #999; font-size: 10pt;")
        left_layout.addWidget(self.monitor_count_label)

        # Legend (compact horizontal)
        legend_frame = QFrame()
        legend_frame.setFrameStyle(QFrame.Shape.Box)
        legend_h_layout = QHBoxLayout(legend_frame)
        legend_h_layout.setContentsMargins(6, 4, 6, 4)
        legend_h_layout.setSpacing(12)

        legend_title = QLabel("Legend:")
        legend_title.setStyleSheet("font-weight: bold; font-size: 9pt;")
        legend_h_layout.addWidget(legend_title)

        primary_label = QLabel("🟦 Primary")
        primary_label.setStyleSheet("font-size: 9pt;")
        legend_h_layout.addWidget(primary_label)

        selected_label = QLabel("🟩 Selected")
        selected_label.setStyleSheet("font-size: 9pt;")
        legend_h_layout.addWidget(selected_label)

        regular_label = QLabel("⬜ Regular")
        regular_label.setStyleSheet("font-size: 9pt;")
        legend_h_layout.addWidget(regular_label)

        legend_h_layout.addStretch()
        left_layout.addWidget(legend_frame)

        self.monitor_canvas = MonitorLayoutCanvas()
        self.monitor_canvas.setMinimumSize(350, 200)
        self.monitor_canvas.set_monitors(self.monitors)
        self.monitor_canvas.monitorSelected.connect(self.on_monitor_selected)
        left_layout.addWidget(self.monitor_canvas, 1)

        self.layout_info_text = QTextEdit()
        self.layout_info_text.setReadOnly(True)
        self.layout_info_text.setMaximumHeight(70)
        self.layout_info_text.setStyleSheet("font-family: monospace; font-size: 8pt; background-color: #2D2D2D; color: #E0E0E0;")
        left_layout.addWidget(self.layout_info_text)

        content_layout.addWidget(left_widget, 2)

        # Right side - Monitor Details & Configuration
        right_widget = QWidget()
        right_widget.setObjectName("selectorRightPanel")
        right_widget.setStyleSheet("#selectorRightPanel { background-color: #2D2D2D; }")
        right_layout = QVBoxLayout(right_widget)
        right_layout.setContentsMargins(0, 0, 0, 0)
        right_layout.setSpacing(6)

        details_label = QLabel("Monitor Details & Configuration")
        details_label.setProperty("class", "section-header")
        right_layout.addWidget(details_label)

        # Selected Monitor dropdown
        monitor_group = QGroupBox("Selected Monitor:")
        monitor_group_layout = QVBoxLayout(monitor_group)
        monitor_group_layout.setContentsMargins(8, 8, 8, 8)

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
        info_layout.setContentsMargins(8, 8, 8, 8)

        self.info_text = QTextEdit()
        self.info_text.setReadOnly(True)
        self.info_text.setMinimumHeight(80)
        self.info_text.setMaximumHeight(160)
        self.info_text.setStyleSheet("font-family: monospace; font-size: 9pt; background-color: #2D2D2D; color: #E0E0E0;")
        info_layout.addWidget(self.info_text)

        right_layout.addWidget(info_group)

        # Capture Region
        capture_group = QGroupBox("Capture Region")
        capture_layout = QVBoxLayout(capture_group)
        capture_layout.setContentsMargins(8, 8, 8, 8)
        capture_layout.setSpacing(4)

        preset_label = QLabel("Quick Presets:")
        preset_label.setStyleSheet("font-weight: bold;")
        capture_layout.addWidget(preset_label)

        preset_info = QLabel("Check multiple presets to translate several regions at once:")
        preset_info.setStyleSheet("font-size: 8pt; color: #999;")
        preset_info.setWordWrap(True)
        capture_layout.addWidget(preset_info)

        self.preset_list = QListWidget()
        self.preset_list.setMaximumHeight(110)
        self.preset_list.setStyleSheet(
            "QListWidget { background-color: #2D2D2D; color: #E0E0E0; font-size: 9pt; }"
            "QListWidget::item { padding: 4px; }"
            "QListWidget::indicator { width: 18px; height: 18px; border: 2px solid #7A7A7A;"
            "  border-radius: 3px; background-color: #1E1E1E; }"
            "QListWidget::indicator:checked { background-color: #2196F3; border: 2px solid #2196F3; }"
            "QListWidget::indicator:hover { border: 2px solid #64B5F6; }"
        )
        self.preset_list.itemChanged.connect(self.on_preset_selection_changed)
        capture_layout.addWidget(self.preset_list)

        self._add_preset_list_item("Full Screen", checked=True)
        self._add_preset_list_item("Custom Region", checked=False)

        preset_btn_row = QHBoxLayout()
        save_preset_btn = QPushButton("💾")
        save_preset_btn.setToolTip("Save current region as preset")
        save_preset_btn.setMaximumWidth(40)
        save_preset_btn.clicked.connect(self.save_preset)
        preset_btn_row.addWidget(save_preset_btn)

        delete_preset_btn = QPushButton("🗑️")
        delete_preset_btn.setToolTip("Delete selected preset")
        delete_preset_btn.setMaximumWidth(40)
        delete_preset_btn.clicked.connect(self.delete_preset)
        preset_btn_row.addWidget(delete_preset_btn)

        capture_layout.addLayout(preset_btn_row)

        self.load_presets()

        custom_label = QLabel("Custom Region:")
        custom_label.setStyleSheet("font-weight: bold; margin-top: 6px;")
        capture_layout.addWidget(custom_label)

        draw_region_btn = QPushButton("✏ Draw Region")
        draw_region_btn.setProperty("class", "action")
        draw_region_btn.clicked.connect(self.draw_capture_region)
        capture_layout.addWidget(draw_region_btn)

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

        self.capture_valid_label = QLabel("✓ Valid region")
        self.capture_valid_label.setStyleSheet("color: green; font-size: 9pt;")
        capture_layout.addWidget(self.capture_valid_label)

        right_layout.addWidget(capture_group)

        # Overlay Region
        overlay_group = QGroupBox("Translation Overlay Region")
        overlay_layout = QVBoxLayout(overlay_group)
        overlay_layout.setContentsMargins(8, 8, 8, 8)
        overlay_layout.setSpacing(4)

        overlay_info = QLabel("Select where translated text should appear:")
        overlay_info.setStyleSheet("font-size: 9pt; color: #999;")
        overlay_info.setWordWrap(True)
        overlay_layout.addWidget(overlay_info)

        draw_overlay_btn = QPushButton("✏ Select Overlay Region")
        draw_overlay_btn.setProperty("class", "action")
        draw_overlay_btn.clicked.connect(self.draw_overlay_region)
        overlay_layout.addWidget(draw_overlay_btn)

        overlay_coords_layout = QGridLayout()
        overlay_coords_layout.setSpacing(5)

        overlay_coords_layout.addWidget(QLabel("X:"), 0, 0)
        self.overlay_x_spin = CustomSpinBox()
        self.overlay_x_spin.setRange(-10000, 10000)
        self.overlay_x_spin.setValue(0)
        self.overlay_x_spin.valueChanged.connect(self.on_overlay_coords_changed)
        overlay_coords_layout.addWidget(self.overlay_x_spin, 0, 1)

        overlay_coords_layout.addWidget(QLabel("Y:"), 0, 2)
        self.overlay_y_spin = CustomSpinBox()
        self.overlay_y_spin.setRange(-10000, 10000)
        self.overlay_y_spin.setValue(0)
        self.overlay_y_spin.valueChanged.connect(self.on_overlay_coords_changed)
        overlay_coords_layout.addWidget(self.overlay_y_spin, 0, 3)

        overlay_coords_layout.addWidget(QLabel("W:"), 1, 0)
        self.overlay_w_spin = CustomSpinBox()
        self.overlay_w_spin.setRange(1, 10000)
        self.overlay_w_spin.setValue(800)
        self.overlay_w_spin.valueChanged.connect(self.on_overlay_coords_changed)
        overlay_coords_layout.addWidget(self.overlay_w_spin, 1, 1)

        overlay_coords_layout.addWidget(QLabel("H:"), 1, 2)
        self.overlay_h_spin = CustomSpinBox()
        self.overlay_h_spin.setRange(1, 10000)
        self.overlay_h_spin.setValue(600)
        self.overlay_h_spin.valueChanged.connect(self.on_overlay_coords_changed)
        overlay_coords_layout.addWidget(self.overlay_h_spin, 1, 3)

        overlay_layout.addLayout(overlay_coords_layout)

        self.overlay_valid_label = QLabel("✓ Valid region")
        self.overlay_valid_label.setStyleSheet("color: #4CAF50; font-weight: bold;")
        overlay_layout.addWidget(self.overlay_valid_label)

        right_layout.addWidget(overlay_group)

        # DPI & Scaling
        dpi_group = QGroupBox("DPI & Scaling")
        dpi_layout = QVBoxLayout(dpi_group)
        dpi_layout.setContentsMargins(8, 8, 8, 8)

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

        # Multi-Region Capture
        multi_region_group = QGroupBox("Multi-Region Capture")
        mr_layout = QVBoxLayout(multi_region_group)
        mr_layout.setContentsMargins(8, 8, 8, 8)
        mr_layout.setSpacing(4)

        mr_info = QLabel("Draw regions across any monitor simultaneously:")
        mr_info.setStyleSheet("font-size: 9pt; color: #999;")
        mr_info.setWordWrap(True)
        mr_layout.addWidget(mr_info)

        draw_all_btn = QPushButton("✏ Draw Region (All Monitors)")
        draw_all_btn.setProperty("class", "action")
        draw_all_btn.setToolTip("Opens an overlay spanning every monitor so you can draw anywhere")
        draw_all_btn.clicked.connect(self.draw_region_all_monitors)
        mr_layout.addWidget(draw_all_btn)

        self.region_list = QListWidget()
        self.region_list.setMaximumHeight(120)
        self.region_list.setStyleSheet(
            "QListWidget { background-color: #2D2D2D; color: #E0E0E0; font-size: 9pt; }"
        )
        mr_layout.addWidget(self.region_list)

        mr_btn_row = QHBoxLayout()
        remove_region_btn = QPushButton("Remove Selected")
        remove_region_btn.clicked.connect(self.remove_selected_region)
        mr_btn_row.addWidget(remove_region_btn)

        clear_regions_btn = QPushButton("Clear All")
        clear_regions_btn.clicked.connect(self.clear_all_regions)
        mr_btn_row.addWidget(clear_regions_btn)
        mr_layout.addLayout(mr_btn_row)

        right_layout.addWidget(multi_region_group)

        self.multi_regions = []

        right_layout.addStretch()

        right_scroll = QScrollArea()
        right_scroll.setWidgetResizable(True)
        right_scroll.setWidget(right_widget)
        right_scroll.setFrameShape(QFrame.Shape.NoFrame)
        right_scroll.setMinimumWidth(360)
        right_scroll.setObjectName("selectorScroll")
        right_scroll.viewport().setObjectName("selectorScrollViewport")
        right_scroll.setStyleSheet(
            "#selectorScroll, #selectorScrollViewport { background-color: #2D2D2D; }"
        )

        content_layout.addWidget(right_scroll, 3)

        main_layout.addLayout(content_layout)

        # Bottom buttons
        button_layout = QHBoxLayout()
        button_layout.setSpacing(10)

        button_layout.addStretch()

        apply_btn = QPushButton("Apply")
        apply_btn.setProperty("class", "primary")
        apply_btn.setMinimumWidth(100)
        apply_btn.clicked.connect(self.accept)
        button_layout.addWidget(apply_btn)

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

        if "Full Screen" in self._get_checked_preset_names():
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

        min_x = min(m['x'] for m in self.monitors)
        min_y = min(m['y'] for m in self.monitors)
        max_x = max(m['x'] + m['width'] for m in self.monitors)
        max_y = max(m['y'] + m['height'] for m in self.monitors)

        total_width = max_x - min_x
        total_height = max_y - min_y

        if len(self.monitors) == 1:
            layout_type = "Single"
        elif all(m['y'] == self.monitors[0]['y'] for m in self.monitors):
            layout_type = "Horizontal"
        elif all(m['x'] == self.monitors[0]['x'] for m in self.monitors):
            layout_type = "Vertical"
        else:
            layout_type = "Mixed"

        primary_index = next((i for i, m in enumerate(self.monitors) if m['is_primary']), 0)

        info_text = f"""Monitor Layout Information:
Total Monitors: {len(self.monitors)}
Layout Type: {layout_type}
Total Desktop: {total_width}x{total_height}
Primary Monitor: {primary_index}"""

        self.layout_info_text.setPlainText(info_text)

    def _add_preset_list_item(self, name, checked=False, monitor_label=None):
        """Add a checkable item to the preset list widget."""
        display = name
        if monitor_label:
            display = f"{name}  [{monitor_label}]"
        item = QListWidgetItem(display)
        item.setData(Qt.ItemDataRole.UserRole, name)
        item.setFlags(item.flags() | Qt.ItemFlag.ItemIsUserCheckable)
        item.setCheckState(Qt.CheckState.Checked if checked else Qt.CheckState.Unchecked)
        self.preset_list.addItem(item)

    def _get_checked_preset_names(self):
        """Return list of currently checked preset names (raw names, not display text)."""
        names = []
        for i in range(self.preset_list.count()):
            item = self.preset_list.item(i)
            if item.checkState() == Qt.CheckState.Checked:
                raw = item.data(Qt.ItemDataRole.UserRole)
                names.append(raw if raw else item.text())
        return names

    def _set_preset_checked(self, name, checked=True):
        """Check or uncheck a preset by its raw name."""
        for i in range(self.preset_list.count()):
            item = self.preset_list.item(i)
            raw = item.data(Qt.ItemDataRole.UserRole)
            if (raw or item.text()) == name:
                self.preset_list.blockSignals(True)
                item.setCheckState(Qt.CheckState.Checked if checked else Qt.CheckState.Unchecked)
                self.preset_list.blockSignals(False)
                return

    def on_preset_selection_changed(self, item):
        """Handle a preset checkbox being toggled in the list."""
        checked_names = self._get_checked_preset_names()

        if not checked_names:
            self.preset_list.blockSignals(True)
            item.setCheckState(Qt.CheckState.Checked)
            self.preset_list.blockSignals(False)
            return

        raw_name = item.data(Qt.ItemDataRole.UserRole) or item.text()

        if len(checked_names) == 1:
            self.on_preset_changed(checked_names[0])
        else:
            if item.checkState() == Qt.CheckState.Checked:
                self.on_preset_changed(raw_name)

        count = len(checked_names)
        logger.info("Active presets (%d): %s", count, checked_names)

    def on_preset_changed(self, preset):
        """Handle preset selection change — loads region + switches monitor."""
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
            preset_data = self.saved_presets[preset]
            self.capture_region = preset_data.get('capture_region', self.capture_region)
            self.overlay_region = preset_data.get('overlay_region', self.overlay_region)

            saved_monitor = preset_data.get('monitor_index')
            if saved_monitor is not None and 0 <= saved_monitor < len(self.monitors):
                self.selected_monitor_index = saved_monitor
                self.monitor_combo.blockSignals(True)
                self.monitor_combo.setCurrentIndex(saved_monitor)
                self.monitor_combo.blockSignals(False)
                self.monitor_canvas.set_selected_monitor(saved_monitor)

            self.update_capture_spinboxes()
            self.update_overlay_spinboxes()
            logger.info("Loaded preset: %s (monitor %s)", preset, saved_monitor)

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

        self._validate_overlay_region()

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

        if len(self.monitors) > 1:
            overlay = MultiMonitorRegionDrawOverlay(self.monitors, self)
            overlay.regionSelected.connect(self._on_capture_region_from_multi)
            overlay.show()
        else:
            monitor = self.monitors[self.selected_monitor_index]
            monitor_geometry = QRect(
                monitor['x'], monitor['y'],
                monitor['width'], monitor['height']
            )
            overlay = RegionDrawOverlay(monitor_geometry, self)
            overlay.regionSelected.connect(self.on_capture_region_drawn)
            overlay.show()

    def _on_capture_region_from_multi(self, region):
        """Handle capture region drawn via multi-monitor overlay."""
        monitor_idx = region.get('monitor_index', self.selected_monitor_index)
        self.selected_monitor_index = monitor_idx
        self.monitor_combo.setCurrentIndex(monitor_idx)
        self.on_capture_region_drawn({
            'x': region['x'], 'y': region['y'],
            'width': region['width'], 'height': region['height'],
        })

    def on_capture_region_drawn(self, region):
        """Handle capture region drawn."""
        self.capture_region = region
        self._set_preset_checked("Custom Region", True)
        self.update_capture_spinboxes()
        logger.info("Capture region drawn: %s", region)

    def draw_overlay_region(self):
        """Open overlay to draw overlay region."""
        if not self.monitors or self.selected_monitor_index >= len(self.monitors):
            return

        if len(self.monitors) > 1:
            overlay = MultiMonitorRegionDrawOverlay(self.monitors, self)
            overlay.regionSelected.connect(self._on_overlay_region_from_multi)
            overlay.show()
        else:
            monitor = self.monitors[self.selected_monitor_index]
            monitor_geometry = QRect(
                monitor['x'], monitor['y'],
                monitor['width'], monitor['height']
            )
            overlay = RegionDrawOverlay(monitor_geometry, self)
            overlay.regionSelected.connect(self.on_overlay_region_drawn)
            overlay.show()

    def _on_overlay_region_from_multi(self, region):
        """Handle overlay region drawn via multi-monitor overlay."""
        monitor_idx = region.get('monitor_index', self.selected_monitor_index)
        self.selected_monitor_index = monitor_idx
        self.monitor_combo.setCurrentIndex(monitor_idx)
        self.on_overlay_region_drawn({
            'x': region['x'], 'y': region['y'],
            'width': region['width'], 'height': region['height'],
        })

    def on_overlay_region_drawn(self, region):
        """Handle overlay region drawn."""
        self.overlay_region = region
        self._set_preset_checked("Custom Region", True)
        self.update_overlay_spinboxes()
        logger.info("Overlay region drawn: %s", region)

    def draw_region_all_monitors(self):
        """Open a single overlay that spans every monitor so the user can draw anywhere."""
        if not self.monitors:
            return
        overlay = MultiMonitorRegionDrawOverlay(self.monitors, self)
        overlay.regionSelected.connect(self._on_multi_monitor_region_drawn)
        overlay.show()

    def _on_multi_monitor_region_drawn(self, region):
        """Handle a region drawn via the all-monitors overlay."""
        monitor_idx = region.get('monitor_index', 0)
        entry = {
            'x': region['x'],
            'y': region['y'],
            'width': region['width'],
            'height': region['height'],
            'monitor_index': monitor_idx,
            'monitor_name': self.monitors[monitor_idx]['name'] if monitor_idx < len(self.monitors) else '?',
        }
        self.multi_regions.append(entry)
        self._refresh_region_list()

        self.selected_monitor_index = monitor_idx
        self.monitor_combo.setCurrentIndex(monitor_idx)
        self.capture_region = {
            'x': region['x'], 'y': region['y'],
            'width': region['width'], 'height': region['height'],
        }
        self._set_preset_checked("Custom Region", True)
        self.update_capture_spinboxes()
        logger.info("Multi-monitor region drawn on %s: %s", entry['monitor_name'], entry)

    def _refresh_region_list(self):
        """Rebuild the QListWidget from self.multi_regions."""
        self.region_list.clear()
        for i, r in enumerate(self.multi_regions):
            text = (f"Region {i+1}: {r['monitor_name']}  "
                    f"({r['x']}, {r['y']}) {r['width']}×{r['height']}")
            self.region_list.addItem(text)

    def remove_selected_region(self):
        """Remove the currently selected region from the multi-region list."""
        row = self.region_list.currentRow()
        if 0 <= row < len(self.multi_regions):
            removed = self.multi_regions.pop(row)
            self._refresh_region_list()
            logger.info("Removed region: %s", removed)

    def clear_all_regions(self):
        """Clear every entry in the multi-region list."""
        self.multi_regions.clear()
        self._refresh_region_list()
        logger.info("Cleared all multi-regions")

    def on_scale_changed(self, value):
        """Handle scaling slider change."""
        scale = value / 100.0
        self.scale_value_label.setText(f"{scale:.1f}×")

    def get_configuration(self):
        """Get the current configuration, including all checked preset regions."""
        checked = self._get_checked_preset_names()

        active_regions = []
        for name in checked:
            if name == "Full Screen" and self.monitors:
                mon = self.monitors[self.selected_monitor_index]
                active_regions.append({
                    'preset': name,
                    'monitor_index': self.selected_monitor_index,
                    'capture_region': {'x': 0, 'y': 0, 'width': mon['width'], 'height': mon['height']},
                    'overlay_region': {'x': 0, 'y': 0, 'width': mon['width'], 'height': mon['height']},
                })
            elif name == "Custom Region":
                active_regions.append({
                    'preset': name,
                    'monitor_index': self.selected_monitor_index,
                    'capture_region': self.capture_region,
                    'overlay_region': self.overlay_region,
                })
            elif name in self.saved_presets:
                pd = self.saved_presets[name]
                active_regions.append({
                    'preset': name,
                    'monitor_index': pd.get('monitor_index', self.selected_monitor_index),
                    'capture_region': pd.get('capture_region', self.capture_region),
                    'overlay_region': pd.get('overlay_region', self.overlay_region),
                })

        config = {
            'monitor': self.selected_monitor_index,
            'monitor_info': self.monitors[self.selected_monitor_index],
            'capture_region': self.capture_region,
            'overlay_region': self.overlay_region,
            'dpi_aware': self.dpi_aware_check.isChecked(),
            'scale_factor': self.scale_slider.value() / 100.0,
            'selected_presets': checked,
            'active_regions': active_regions,
            'multi_regions': self.multi_regions,
        }

        if self.config_manager:
            self.config_manager.set_setting('capture.selected_presets', checked)
            self.config_manager.set_setting('overlay.region', self.overlay_region)

        return config

    def load_presets(self):
        """Load saved region presets from config manager."""
        if not self.config_manager:
            return

        self.saved_presets = self.config_manager.get_region_presets()

        for preset_name, pdata in self.saved_presets.items():
            if preset_name not in ["Full Screen", "Custom Region"]:
                mon_idx = pdata.get('monitor_index')
                mon_label = None
                if mon_idx is not None and mon_idx < len(self.monitors):
                    mon_label = self.monitors[mon_idx]['name']
                self._add_preset_list_item(preset_name, checked=False, monitor_label=mon_label)

        if self.saved_presets:
            logger.info("Loaded %d region presets", len(self.saved_presets))

    def save_preset(self):
        """Save current region configuration as a preset."""
        preset_name, ok = QInputDialog.getText(
            self, "Save Preset",
            "Enter preset name (e.g., 'Manga', 'Game', 'Video'):"
        )

        if not ok or not preset_name:
            return

        if preset_name in ["Full Screen", "Custom Region"]:
            QMessageBox.warning(self, "Invalid Name", "Cannot use reserved preset names.")
            return

        try:
            preset_data = {
                'capture_region': self.capture_region,
                'overlay_region': self.overlay_region,
                'monitor_index': self.selected_monitor_index,
            }

            self.saved_presets[preset_name] = preset_data

            if self.config_manager:
                self.config_manager.set_region_preset(preset_name, preset_data)
                self.config_manager.save_config()

            if not self._find_preset_item(preset_name):
                mon_label = self.monitors[self.selected_monitor_index]['name'] if self.monitors else None
                self._add_preset_list_item(preset_name, checked=True, monitor_label=mon_label)
            else:
                self._set_preset_checked(preset_name, True)

            logger.info("Saved preset: %s", preset_name)

            mon_name = self.monitors[self.selected_monitor_index]['name'] if self.monitors else 'unknown'
            QMessageBox.information(
                self, "Preset Saved",
                f"Region preset '{preset_name}' saved for monitor '{mon_name}'."
            )
        except Exception:
            logger.exception("Failed to save preset")
            QMessageBox.critical(self, "Save Failed", "Failed to save preset.")

    def _find_preset_item(self, name):
        """Return True if a preset with the given name exists in the list widget."""
        for i in range(self.preset_list.count()):
            item = self.preset_list.item(i)
            raw = item.data(Qt.ItemDataRole.UserRole) or item.text()
            if raw == name:
                return True
        return False

    def delete_preset(self):
        """Delete the selected preset."""
        current_item = self.preset_list.currentItem()
        if not current_item:
            return
        preset_name = current_item.data(Qt.ItemDataRole.UserRole) or current_item.text()

        if preset_name in ["Full Screen", "Custom Region"]:
            QMessageBox.warning(self, "Cannot Delete", "Cannot delete built-in presets.")
            return

        reply = QMessageBox.question(
            self, "Delete Preset",
            f"Are you sure you want to delete preset '{preset_name}'?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            QMessageBox.StandardButton.No
        )

        if reply != QMessageBox.StandardButton.Yes:
            return

        if preset_name in self.saved_presets:
            del self.saved_presets[preset_name]

            if self.config_manager:
                self.config_manager.delete_region_preset(preset_name)
                self.config_manager.save_config()

            row = self.preset_list.row(current_item)
            self.preset_list.takeItem(row)

            logger.info("Deleted preset: %s", preset_name)
            QMessageBox.information(self, "Preset Deleted", f"Preset '{preset_name}' has been deleted.")

    def on_overlay_coords_changed(self):
        """Handle overlay region coordinate changes."""
        self.overlay_region = {
            'x': self.overlay_x_spin.value(),
            'y': self.overlay_y_spin.value(),
            'width': self.overlay_w_spin.value(),
            'height': self.overlay_h_spin.value()
        }
        self._validate_overlay_region()

    def _validate_overlay_region(self):
        """Validate overlay region and update the status label."""
        if self.overlay_region['width'] > 0 and self.overlay_region['height'] > 0:
            self.overlay_valid_label.setText("✓ Valid region")
            self.overlay_valid_label.setStyleSheet("color: #4CAF50; font-weight: bold;")
        else:
            self.overlay_valid_label.setText("✗ Invalid region")
            self.overlay_valid_label.setStyleSheet("color: #F44336; font-weight: bold;")

    def restore_last_preset(self):
        """Restore the last selected presets from configuration."""
        if not self.config_manager:
            return

        last_presets = self.config_manager.get_setting('capture.selected_presets', None)
        if last_presets is None:
            single = self.config_manager.get_setting('capture.selected_preset', 'Full Screen')
            last_presets = [single] if single else ['Full Screen']

        self.preset_list.blockSignals(True)
        for i in range(self.preset_list.count()):
            self.preset_list.item(i).setCheckState(Qt.CheckState.Unchecked)

        restored = []
        for name in last_presets:
            for i in range(self.preset_list.count()):
                item = self.preset_list.item(i)
                raw = item.data(Qt.ItemDataRole.UserRole) or item.text()
                if raw == name:
                    item.setCheckState(Qt.CheckState.Checked)
                    restored.append(name)
                    break

        if not restored:
            for i in range(self.preset_list.count()):
                item = self.preset_list.item(i)
                raw = item.data(Qt.ItemDataRole.UserRole) or item.text()
                if raw == "Full Screen":
                    item.setCheckState(Qt.CheckState.Checked)
                    restored.append("Full Screen")
                    break

        self.preset_list.blockSignals(False)

        if restored:
            self.on_preset_changed(restored[-1])

        logger.info("Restored presets: %s", restored)

    def _set_initial_region(self, region, overlay_region=None):
        """
        Set initial region values when editing an existing region.

        Args:
            region: Dictionary with keys 'x', 'y', 'width', 'height'
            overlay_region: Optional dictionary with overlay region coordinates
        """
        self.capture_x_spin.blockSignals(True)
        self.capture_y_spin.blockSignals(True)
        self.capture_w_spin.blockSignals(True)
        self.capture_h_spin.blockSignals(True)

        self.capture_x_spin.setValue(region.get('x', 0))
        self.capture_y_spin.setValue(region.get('y', 0))
        self.capture_w_spin.setValue(region.get('width', 0))
        self.capture_h_spin.setValue(region.get('height', 0))

        self.capture_region = {
            'x': region.get('x', 0),
            'y': region.get('y', 0),
            'width': region.get('width', 0),
            'height': region.get('height', 0)
        }

        self.capture_x_spin.blockSignals(False)
        self.capture_y_spin.blockSignals(False)
        self.capture_w_spin.blockSignals(False)
        self.capture_h_spin.blockSignals(False)

        if overlay_region:
            self.overlay_x_spin.blockSignals(True)
            self.overlay_y_spin.blockSignals(True)
            self.overlay_w_spin.blockSignals(True)
            self.overlay_h_spin.blockSignals(True)

            self.overlay_x_spin.setValue(overlay_region.get('x', 0))
            self.overlay_y_spin.setValue(overlay_region.get('y', 0))
            self.overlay_w_spin.setValue(overlay_region.get('width', 800))
            self.overlay_h_spin.setValue(overlay_region.get('height', 600))

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

            self._validate_overlay_region()

        self.validate_capture_region()

        self._set_preset_checked("Custom Region", True)
