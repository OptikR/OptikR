"""
Advanced Settings Tab - PyQt6 Implementation
Debug logging, performance monitoring, ROI detection, and system diagnostics.
"""

import logging
import sys
import platform
import json
import time
from pathlib import Path
from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QFormLayout, QGroupBox,
    QLabel, QComboBox, QCheckBox, QPushButton, QTextEdit,
    QMessageBox, QFileDialog
)
from PyQt6.QtCore import Qt, pyqtSignal, QTimer
from PyQt6.QtGui import QFont
from ui.common.widgets.custom_spinbox import CustomSpinBox, CustomDoubleSpinBox

# Import custom scroll area
from ui.common.widgets.scroll_area_no_wheel import ScrollAreaNoWheel

# Import translation system
from app.localization import TranslatableMixin, tr

# Import path utilities for EXE compatibility
from app.utils.path_utils import get_app_path

# Import diagnostics worker
from .diagnostics_worker import DiagnosticsWorker

# Import module test worker
from .module_test_worker import ModuleTestWorker


_logger = logging.getLogger(__name__)


class AdvancedSettingsTab(TranslatableMixin, QWidget):
    """Advanced settings including logging, monitoring, ROI detection, and diagnostics."""
    
    # Signal emitted when any setting changes
    settingChanged = pyqtSignal()
    
    def __init__(self, config_manager=None, parent=None):
        """Initialize the Advanced settings tab."""
        super().__init__(parent)
        
        self.config_manager = config_manager
        
        # Track original loaded state to detect real changes
        self._original_state = {}
        
        # Diagnostics caching
        self._diagnostics_cache = None
        self._diagnostics_cache_time = None
        self._diagnostics_worker = None
        
        # Log level widget
        self.log_level_combo = None
        
        # Performance monitoring widget
        self.performance_monitoring_check = None
        
        # ROI Detection widgets
        self.roi_min_width_spin = None
        self.roi_min_height_spin = None
        self.roi_max_width_spin = None
        self.roi_max_height_spin = None
        self.roi_padding_spin = None
        self.roi_merge_distance_spin = None
        self.roi_confidence_spin = None
        self.roi_adaptive_threshold_check = None
        self.roi_use_morphology_check = None
        
        # Quiet console widget
        self.quiet_console_check = None
        
        # Debug mode widget
        self.debug_mode_check = None
        
        # Startup widget
        self.show_wizard_check = None
        
        # System diagnostics widget
        self.diagnostics_text = None
        
        # Module test widgets
        self._test_buttons = {}
        self._test_status_labels = {}
        self._test_results_text = None
        self._module_test_worker = None
        
        # Initialize UI
        self._init_ui()
    
    def _init_ui(self):
        """Initialize the UI."""
        # Create main layout
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.setSpacing(0)
        
        # Create scroll area (custom - only scrolls when mouse is over it)
        scroll_area = ScrollAreaNoWheel()
        scroll_area.setWidgetResizable(True)
        scroll_area.setFrameShape(ScrollAreaNoWheel.Shape.NoFrame)
        scroll_area.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        scroll_area.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAsNeeded)
        
        # Create content widget
        content_widget = QWidget()
        content_layout = QVBoxLayout(content_widget)
        content_layout.setContentsMargins(5, 5, 5, 5)
        content_layout.setSpacing(10)
        
        # Create sections
        self._create_logging_section(content_layout)
        self._create_performance_section(content_layout)
        self._create_roi_detection_section(content_layout)
        self._create_debug_section(content_layout)
        self._create_startup_section(content_layout)
        self._create_diagnostics_section(content_layout)
        self._create_module_tests_section(content_layout)
        self._create_privacy_consent_section(content_layout)
        self._create_config_management_section(content_layout)
        
        # Add stretch at the end
        content_layout.addStretch()
        
        # Set content widget to scroll area
        scroll_area.setWidget(content_widget)
        
        # Add scroll area to main layout
        main_layout.addWidget(scroll_area)
    
    def _create_label(self, text: str, bold: bool = False) -> QLabel:
        """Create a label with consistent styling."""
        label = QLabel(text)
        if bold:
            label.setStyleSheet("font-weight: 600; font-size: 9pt;")
        else:
            label.setStyleSheet("font-size: 9pt;")
        return label
    
    def _get_current_state(self):
        """Get current state of all settings."""
        state = {}
        if self.log_level_combo:
            state['log_level'] = self.log_level_combo.currentText()
        if self.performance_monitoring_check:
            state['performance_monitoring'] = self.performance_monitoring_check.isChecked()
        if self.quiet_console_check:
            state['quiet_console'] = self.quiet_console_check.isChecked()
        if self.debug_mode_check:
            state['debug_mode'] = self.debug_mode_check.isChecked()
        if self.show_wizard_check:
            state['show_wizard'] = self.show_wizard_check.isChecked()
        if hasattr(self, 'roi_min_width_spin') and self.roi_min_width_spin:
            state['roi_min_width'] = self.roi_min_width_spin.value()
            state['roi_min_height'] = self.roi_min_height_spin.value()
            state['roi_max_width'] = self.roi_max_width_spin.value()
            state['roi_max_height'] = self.roi_max_height_spin.value()
            state['roi_padding'] = self.roi_padding_spin.value()
            state['roi_merge_distance'] = self.roi_merge_distance_spin.value()
            state['roi_confidence'] = self.roi_confidence_spin.value()
            state['roi_adaptive_threshold'] = self.roi_adaptive_threshold_check.isChecked()
            state['roi_use_morphology'] = self.roi_use_morphology_check.isChecked()
        return state
    
    def on_change(self):
        """Called when any setting changes - always emits signal for main window to check."""
        self.settingChanged.emit()
    
    def _create_logging_section(self, parent_layout):
        """Create logging configuration section."""
        group = QGroupBox()
        self.set_translatable_text(group, "advanced_logging_configuration_section")
        layout = QVBoxLayout(group)
        layout.setSpacing(12)
        layout.setContentsMargins(15, 20, 15, 15)
        
        # Log level selector
        level_layout = QHBoxLayout()
        level_layout.setSpacing(10)
        
        level_label = QLabel()
        level_label.setStyleSheet("font-weight: 600; font-size: 9pt;")
        self.set_translatable_text(level_label, "advanced_log_level_label")
        level_layout.addWidget(level_label)
        
        self.log_level_combo = QComboBox()
        self.log_level_combo.addItems([
            'DEBUG',
            'INFO',
            'WARNING',
            'ERROR',
            'CRITICAL'
        ])
        self.log_level_combo.setCurrentText('INFO')
        self.log_level_combo.setMinimumWidth(150)
        self.log_level_combo.currentTextChanged.connect(self.on_change)
        level_layout.addWidget(self.log_level_combo)
        
        level_layout.addStretch()
        layout.addLayout(level_layout)
        
        # Log level descriptions
        desc_label = QLabel()
        desc_label.setWordWrap(True)
        desc_label.setStyleSheet("color: #666666; font-size: 9pt; margin-top: 5px;")
        self.set_translatable_text(desc_label, "advanced_log_level_desc")
        layout.addWidget(desc_label)
        
        # Quiet console checkbox
        self.quiet_console_check = QCheckBox()
        self.set_translatable_text(self.quiet_console_check, "advanced_quiet_console_check")
        self.quiet_console_check.setChecked(False)
        self.quiet_console_check.stateChanged.connect(self.on_change)
        layout.addWidget(self.quiet_console_check)

        quiet_desc = QLabel()
        quiet_desc.setWordWrap(True)
        quiet_desc.setStyleSheet("color: #666666; font-size: 9pt; margin-top: 2px;")
        self.set_translatable_text(quiet_desc, "advanced_quiet_console_desc")
        layout.addWidget(quiet_desc)

        # Log file location info
        log_info = QLabel()
        log_info.setStyleSheet("color: #666666; font-size: 9pt; margin-top: 10px;")
        self.set_translatable_text(log_info, "advanced_log_path_info")
        layout.addWidget(log_info)
        
        parent_layout.addWidget(group)
    
    def _create_performance_section(self, parent_layout):
        """Create performance monitoring section."""
        group = QGroupBox()
        self.set_translatable_text(group, "advanced_performance_monitoring_section")
        layout = QVBoxLayout(group)
        layout.setSpacing(10)
        layout.setContentsMargins(15, 20, 15, 15)
        
        # Performance monitoring checkbox
        self.performance_monitoring_check = QCheckBox()
        self.set_translatable_text(self.performance_monitoring_check, "advanced_enable_performance_monitoring_check")
        self.performance_monitoring_check.setChecked(False)
        self.performance_monitoring_check.stateChanged.connect(self.on_change)
        layout.addWidget(self.performance_monitoring_check)
        
        # Description
        perf_desc_label = QLabel()
        perf_desc_label.setWordWrap(True)
        perf_desc_label.setStyleSheet("color: #666666; font-size: 9pt; margin-top: 5px;")
        self.set_translatable_text(perf_desc_label, "advanced_perf_monitor_desc")
        layout.addWidget(perf_desc_label)
        
        parent_layout.addWidget(group)
    
    
    def _create_roi_detection_section(self, parent_layout):
        """Create ROI (Region of Interest) detection configuration section."""
        from PyQt6.QtWidgets import QSpinBox, QDoubleSpinBox
        
        group = QGroupBox()
        self.set_translatable_text(group, "advanced_roi_detection_settings_section")
        layout = QFormLayout(group)
        layout.setSpacing(10)
        layout.setContentsMargins(15, 20, 15, 15)
        layout.setLabelAlignment(Qt.AlignmentFlag.AlignRight)
        
        # Description
        roi_desc_label = QLabel()
        roi_desc_label.setWordWrap(True)
        roi_desc_label.setStyleSheet("color: #666666; font-size: 9pt; margin-bottom: 10px;")
        self.set_translatable_text(roi_desc_label, "advanced_roi_desc")
        layout.addRow(roi_desc_label)
        
        # Create grid layout for aligned spinboxes (invisible cells)
        from PyQt6.QtWidgets import QGridLayout
        size_grid = QGridLayout()
        size_grid.setHorizontalSpacing(8)  # Space between columns
        size_grid.setVerticalSpacing(8)    # Space between rows
        size_grid.setContentsMargins(0, 0, 0, 0)
        size_grid.setColumnStretch(5, 1)   # Only stretch the last column to push everything left
        
        # Minimum region size widgets
        self.roi_min_width_spin = CustomSpinBox()
        self.roi_min_width_spin.setRange(10, 500)
        self.roi_min_width_spin.setValue(50)
        self.roi_min_width_spin.setSuffix("px")
        self.roi_min_width_spin.valueChanged.connect(self.settingChanged.emit)
        
        self.roi_min_height_spin = CustomSpinBox()
        self.roi_min_height_spin.setRange(10, 500)
        self.roi_min_height_spin.setValue(20)
        self.roi_min_height_spin.setSuffix("px")
        self.roi_min_height_spin.valueChanged.connect(self.settingChanged.emit)
        
        # Maximum region size widgets
        self.roi_max_width_spin = CustomSpinBox()
        self.roi_max_width_spin.setRange(100, 5000)
        self.roi_max_width_spin.setValue(2000)
        self.roi_max_width_spin.setSuffix("px")
        self.roi_max_width_spin.valueChanged.connect(self.settingChanged.emit)
        
        self.roi_max_height_spin = CustomSpinBox()
        self.roi_max_height_spin.setRange(100, 5000)
        self.roi_max_height_spin.setValue(1000)
        self.roi_max_height_spin.setSuffix("px")
        self.roi_max_height_spin.valueChanged.connect(self.settingChanged.emit)
        
        # Grid layout: Row 0 = Min, Row 1 = Max
        # Columns: 0=Label, 1=Width Label, 2=Width Spin, 3=Height Label, 4=Height Spin
        min_size_label = QLabel()
        self.set_translatable_text(min_size_label, "advanced_roi_min_region_size")
        width_label_1 = QLabel()
        self.set_translatable_text(width_label_1, "advanced_roi_width")
        height_label_1 = QLabel()
        self.set_translatable_text(height_label_1, "advanced_roi_height")
        size_grid.addWidget(min_size_label, 0, 0)
        size_grid.addWidget(width_label_1, 0, 1)
        size_grid.addWidget(self.roi_min_width_spin, 0, 2)
        size_grid.addWidget(height_label_1, 0, 3)
        size_grid.addWidget(self.roi_min_height_spin, 0, 4)
        
        max_size_label = QLabel()
        self.set_translatable_text(max_size_label, "advanced_roi_max_region_size")
        width_label_2 = QLabel()
        self.set_translatable_text(width_label_2, "advanced_roi_width")
        height_label_2 = QLabel()
        self.set_translatable_text(height_label_2, "advanced_roi_height")
        size_grid.addWidget(max_size_label, 1, 0)
        size_grid.addWidget(width_label_2, 1, 1)
        size_grid.addWidget(self.roi_max_width_spin, 1, 2)
        size_grid.addWidget(height_label_2, 1, 3)
        size_grid.addWidget(self.roi_max_height_spin, 1, 4)
        
        # Create spinboxes for single-value rows
        self.roi_padding_spin = CustomSpinBox()
        self.roi_padding_spin.setRange(0, 50)
        self.roi_padding_spin.setValue(10)
        self.roi_padding_spin.setSuffix("px")
        self.set_translatable_text(self.roi_padding_spin, "advanced_roi_padding_tooltip", method="setToolTip")
        self.roi_padding_spin.valueChanged.connect(self.settingChanged.emit)
        
        self.roi_merge_distance_spin = CustomSpinBox()
        self.roi_merge_distance_spin.setRange(0, 100)
        self.roi_merge_distance_spin.setValue(20)
        self.roi_merge_distance_spin.setSuffix("px")
        self.set_translatable_text(self.roi_merge_distance_spin, "advanced_roi_merge_distance_tooltip", method="setToolTip")
        self.roi_merge_distance_spin.valueChanged.connect(self.settingChanged.emit)
        
        self.roi_confidence_spin = CustomDoubleSpinBox()
        self.roi_confidence_spin.setRange(0.0, 1.0)
        self.roi_confidence_spin.setSingleStep(0.05)
        self.roi_confidence_spin.setValue(0.3)
        self.roi_confidence_spin.setDecimals(2)
        self.set_translatable_text(self.roi_confidence_spin, "advanced_roi_confidence_tooltip", method="setToolTip")
        self.roi_confidence_spin.valueChanged.connect(self.settingChanged.emit)
        
        # Add single-value rows to grid (rows 2, 3, 4)
        padding_label = QLabel()
        self.set_translatable_text(padding_label, "advanced_roi_region_padding")
        size_grid.addWidget(padding_label, 2, 0)
        size_grid.addWidget(self.roi_padding_spin, 2, 1, 1, 2)
        
        merge_dist_label = QLabel()
        self.set_translatable_text(merge_dist_label, "advanced_roi_merge_distance")
        size_grid.addWidget(merge_dist_label, 3, 0)
        size_grid.addWidget(self.roi_merge_distance_spin, 3, 1, 1, 2)
        
        confidence_label = QLabel()
        self.set_translatable_text(confidence_label, "advanced_roi_confidence_threshold")
        size_grid.addWidget(confidence_label, 4, 0)
        size_grid.addWidget(self.roi_confidence_spin, 4, 1, 1, 2)
        
        # Add grid to main layout
        layout.addRow(size_grid)
        
        # Adaptive threshold
        self.roi_adaptive_threshold_check = QCheckBox()
        self.set_translatable_text(self.roi_adaptive_threshold_check, "advanced_use_adaptive_thresholding_check")
        self.roi_adaptive_threshold_check.setChecked(True)
        self.set_translatable_text(self.roi_adaptive_threshold_check, "advanced_roi_adaptive_threshold_tooltip", method="setToolTip")
        self.roi_adaptive_threshold_check.stateChanged.connect(self.settingChanged.emit)
        layout.addRow("", self.roi_adaptive_threshold_check)
        
        # Morphology
        self.roi_use_morphology_check = QCheckBox()
        self.set_translatable_text(self.roi_use_morphology_check, "advanced_use_morphological_operations_check")
        self.roi_use_morphology_check.setChecked(True)
        self.set_translatable_text(self.roi_use_morphology_check, "advanced_roi_morphology_tooltip", method="setToolTip")
        self.roi_use_morphology_check.stateChanged.connect(self.settingChanged.emit)
        layout.addRow("", self.roi_use_morphology_check)
        
        # Note
        note_label = QLabel()
        note_label.setWordWrap(True)
        note_label.setStyleSheet("color: #2196F3; font-size: 8pt; margin-top: 10px;")
        self.set_translatable_text(note_label, "advanced_roi_tip")
        layout.addRow(note_label)
        
        parent_layout.addWidget(group)
    
    
    def _create_debug_section(self, parent_layout):
        """Create debug mode section."""
        group = QGroupBox()
        self.set_translatable_text(group, "advanced_debug_mode_section")
        layout = QVBoxLayout(group)
        layout.setSpacing(10)
        layout.setContentsMargins(15, 20, 15, 15)
        
        # Debug mode checkbox
        self.debug_mode_check = QCheckBox()
        self.set_translatable_text(self.debug_mode_check, "advanced_enable_debug_mode_check")
        self.debug_mode_check.setChecked(False)
        self.debug_mode_check.stateChanged.connect(self.on_change)
        layout.addWidget(self.debug_mode_check)
        
        # Description
        debug_desc_label = QLabel()
        debug_desc_label.setWordWrap(True)
        debug_desc_label.setStyleSheet("color: #666666; font-size: 9pt; margin-top: 5px;")
        self.set_translatable_text(debug_desc_label, "advanced_debug_mode_desc")
        layout.addWidget(debug_desc_label)
        
        parent_layout.addWidget(group)
    
    def _create_startup_section(self, parent_layout):
        """Create startup behaviour section."""
        group = QGroupBox()
        self.set_translatable_text(group, "advanced_startup_section")
        layout = QVBoxLayout(group)
        layout.setSpacing(10)
        layout.setContentsMargins(15, 20, 15, 15)

        self.show_wizard_check = QCheckBox()
        self.set_translatable_text(self.show_wizard_check, "advanced_show_wizard_check")
        self.show_wizard_check.setChecked(True)
        self.show_wizard_check.stateChanged.connect(self.on_change)
        layout.addWidget(self.show_wizard_check)

        desc_label = QLabel()
        desc_label.setWordWrap(True)
        desc_label.setStyleSheet("color: #666666; font-size: 9pt; margin-top: 5px;")
        self.set_translatable_text(desc_label, "advanced_show_wizard_desc")
        layout.addWidget(desc_label)

        parent_layout.addWidget(group)

    def _create_diagnostics_section(self, parent_layout):
        """Create system diagnostics section."""
        group = QGroupBox()
        self.set_translatable_text(group, "advanced_system_diagnostics_section")
        layout = QVBoxLayout(group)
        layout.setSpacing(12)
        layout.setContentsMargins(15, 20, 15, 15)
        
        # Diagnostics text display
        self.diagnostics_text = QTextEdit()
        self.diagnostics_text.setReadOnly(True)
        self.diagnostics_text.setMinimumHeight(200)
        self.diagnostics_text.setMaximumHeight(300)
        
        # Set monospace font for diagnostics
        font = QFont("Consolas", 9)
        if not font.exactMatch():
            font = QFont("Courier New", 9)
        self.diagnostics_text.setFont(font)
        
        # Show loading message initially
        self.diagnostics_text.setPlainText(tr("advanced_loading_diagnostics"))
        
        layout.addWidget(self.diagnostics_text)
        
        # Refresh button
        refresh_layout = QHBoxLayout()
        refresh_btn = QPushButton()
        self.set_translatable_text(refresh_btn, "advanced_refresh_diagnostics_button")
        refresh_btn.setProperty("class", "action")
        refresh_btn.setMinimumWidth(150)
        refresh_btn.clicked.connect(self._display_diagnostics)
        refresh_layout.addWidget(refresh_btn)
        refresh_layout.addStretch()
        layout.addLayout(refresh_layout)
        
        # Info label
        diag_info_label = QLabel()
        diag_info_label.setWordWrap(True)
        diag_info_label.setStyleSheet("color: #666666; font-size: 9pt; margin-top: 5px;")
        self.set_translatable_text(diag_info_label, "advanced_diagnostics_desc")
        layout.addWidget(diag_info_label)
        
        parent_layout.addWidget(group)
        
        # Start async diagnostics collection after a short delay
        QTimer.singleShot(100, self._load_diagnostics_async)
    
    def _load_diagnostics_async(self):
        """Load diagnostics asynchronously with caching."""
        # Check cache validity (60 second TTL)
        if self._diagnostics_cache and self._diagnostics_cache_time:
            age = time.time() - self._diagnostics_cache_time
            if age < 60:
                # Cache is valid, use it
                self.diagnostics_text.setPlainText(self._diagnostics_cache)
                return
        
        # Cache is invalid or doesn't exist, collect diagnostics in background
        if self._diagnostics_worker and self._diagnostics_worker.isRunning():
            # Worker already running, don't start another
            return
        
        # Create and start worker thread
        self._diagnostics_worker = DiagnosticsWorker(self.config_manager)
        self._diagnostics_worker.diagnostics_ready.connect(self._on_diagnostics_loaded)
        self._diagnostics_worker.error.connect(self._on_diagnostics_error)
        self._diagnostics_worker.start()
    
    def _on_diagnostics_loaded(self, diagnostics_text):
        """
        Handle diagnostics loaded successfully.
        
        Args:
            diagnostics_text: The collected diagnostics text
        """
        # Update cache
        self._diagnostics_cache = diagnostics_text
        self._diagnostics_cache_time = time.time()
        
        # Display diagnostics
        self.diagnostics_text.setPlainText(diagnostics_text)
        
        _logger.debug("System diagnostics loaded asynchronously")
    
    def _on_diagnostics_error(self, error_msg):
        """
        Handle diagnostics collection error.
        
        Args:
            error_msg: The error message
        """
        error_text = tr("advanced_diagnostics_error").format(error=error_msg)
        self.diagnostics_text.setPlainText(error_text)
        
        _logger.error("Failed to load diagnostics: %s", error_msg)
    
    def _create_module_tests_section(self, parent_layout):
        """Create module & pipeline tests section with 5 test buttons and results area."""
        group = QGroupBox()
        self.set_translatable_text(group, "advanced_module_tests_section")
        layout = QVBoxLayout(group)
        layout.setSpacing(12)
        layout.setContentsMargins(15, 20, 15, 15)

        # Description
        desc_label = QLabel()
        desc_label.setWordWrap(True)
        desc_label.setStyleSheet("color: #666666; font-size: 9pt; margin-bottom: 10px;")
        self.set_translatable_text(desc_label, "advanced_module_tests_desc")
        layout.addWidget(desc_label)

        # Test definitions: (test_id, label_key, icon)
        test_defs = [
            (ModuleTestWorker.TEST_CAPTURE, "advanced_test_capture_btn", "📸"),
            (ModuleTestWorker.TEST_OCR, "advanced_test_ocr_btn", "🔤"),
            (ModuleTestWorker.TEST_TRANSLATION, "advanced_test_translation_btn", "🌐"),
            (ModuleTestWorker.TEST_OVERLAY, "advanced_test_overlay_btn", "🖥️"),
            (ModuleTestWorker.TEST_FULL_PIPELINE, "advanced_test_full_pipeline_btn", "🚀"),
        ]

        for test_id, label_key, icon in test_defs:
            row_layout = QHBoxLayout()
            row_layout.setSpacing(10)

            btn = QPushButton()
            self.set_translatable_text(btn, label_key)
            btn.setProperty("class", "action")
            btn.setMinimumWidth(200)
            btn.clicked.connect(lambda checked, tid=test_id: self._run_single_test(tid))
            row_layout.addWidget(btn)

            status_label = QLabel(tr("advanced_test_status_idle"))
            status_label.setFixedWidth(26)
            status_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
            status_label.setStyleSheet("font-size: 14pt;")
            row_layout.addWidget(status_label)

            row_layout.addStretch()

            self._test_buttons[test_id] = btn
            self._test_status_labels[test_id] = status_label

            layout.addLayout(row_layout)

        # "Run All" button
        run_all_layout = QHBoxLayout()
        run_all_layout.setSpacing(10)

        run_all_btn = QPushButton()
        self.set_translatable_text(run_all_btn, "advanced_test_run_all_btn")
        run_all_btn.setProperty("class", "action")
        run_all_btn.setMinimumWidth(200)
        run_all_btn.clicked.connect(self._run_all_tests)
        run_all_layout.addWidget(run_all_btn)
        self._test_buttons["run_all"] = run_all_btn

        run_all_layout.addStretch()
        layout.addLayout(run_all_layout)

        # Results text area
        self._test_results_text = QTextEdit()
        self._test_results_text.setReadOnly(True)
        self._test_results_text.setMinimumHeight(180)
        self._test_results_text.setMaximumHeight(350)
        self._test_results_text.setPlaceholderText(tr("advanced_test_results_placeholder"))

        results_font = QFont("Consolas", 9)
        if not results_font.exactMatch():
            results_font = QFont("Courier New", 9)
        self._test_results_text.setFont(results_font)
        layout.addWidget(self._test_results_text)

        parent_layout.addWidget(group)

    # ------------------------------------------------------------------
    # Module test handlers
    # ------------------------------------------------------------------

    def _get_pipeline(self):
        """Lazily resolve the StartupPipeline from the main window."""
        window = self.window()
        return getattr(window, "pipeline", None)

    def _set_tests_enabled(self, enabled: bool):
        """Enable or disable all test buttons."""
        for btn in self._test_buttons.values():
            btn.setEnabled(enabled)

    def _run_single_test(self, test_id: str):
        """Run a single module test in a background thread."""
        self._start_test_worker([test_id])

    def _run_all_tests(self):
        """Run all five module tests sequentially in a background thread."""
        self._start_test_worker(None)

    def _start_test_worker(self, tests):
        """Create and start the ModuleTestWorker.

        Parameters
        ----------
        tests : list or None
            List of test IDs to run, or ``None`` to run all.
        """
        if self._module_test_worker and self._module_test_worker.isRunning():
            return

        pipeline = self._get_pipeline()
        if pipeline is None:
            self._test_results_text.setPlainText(tr("advanced_module_tests_no_pipeline"))
            return

        # Reset relevant status indicators
        ids_to_reset = tests if tests else [
            ModuleTestWorker.TEST_CAPTURE,
            ModuleTestWorker.TEST_OCR,
            ModuleTestWorker.TEST_TRANSLATION,
            ModuleTestWorker.TEST_OVERLAY,
            ModuleTestWorker.TEST_FULL_PIPELINE,
        ]
        for tid in ids_to_reset:
            if tid in self._test_status_labels:
                self._test_status_labels[tid].setText(tr("advanced_test_status_running"))

        self._test_results_text.clear()
        self._set_tests_enabled(False)

        self._module_test_worker = ModuleTestWorker(
            pipeline=pipeline,
            config_manager=self.config_manager,
            tests=tests,
            parent=self,
        )
        self._module_test_worker.progress.connect(self._on_test_progress)
        self._module_test_worker.test_finished.connect(self._on_test_finished)
        self._module_test_worker.all_finished.connect(self._on_all_tests_finished)
        self._module_test_worker.start()

    def _on_test_progress(self, message: str):
        """Append a progress line to the results text area."""
        self._test_results_text.append(message)

    def _on_test_finished(self, test_id: str, passed: bool):
        """Update the status indicator for a single test."""
        label = self._test_status_labels.get(test_id)
        if label:
            label.setText("✅" if passed else "❌")

    def _on_all_tests_finished(self):
        """Re-enable buttons after all tests complete."""
        self._set_tests_enabled(True)

    def _create_privacy_consent_section(self, parent_layout):
        """Create privacy / consent management section with revoke button."""
        group = QGroupBox()
        self.set_translatable_text(group, "advanced_privacy_consent_section")
        layout = QVBoxLayout(group)
        layout.setSpacing(12)
        layout.setContentsMargins(15, 20, 15, 15)

        desc_label = QLabel()
        desc_label.setWordWrap(True)
        desc_label.setStyleSheet("color: #666666; font-size: 9pt; margin-bottom: 5px;")
        self.set_translatable_text(desc_label, "advanced_privacy_consent_desc")
        layout.addWidget(desc_label)

        self._consent_status_label = QLabel()
        self._consent_status_label.setWordWrap(True)
        self._consent_status_label.setStyleSheet("font-size: 9pt; margin-bottom: 5px;")
        layout.addWidget(self._consent_status_label)
        self._refresh_consent_status()

        btn_layout = QHBoxLayout()
        btn_layout.setSpacing(10)

        revoke_btn = QPushButton()
        self.set_translatable_text(revoke_btn, "advanced_revoke_consent_button")
        revoke_btn.setProperty("class", "danger")
        revoke_btn.setMinimumWidth(180)
        revoke_btn.clicked.connect(self._revoke_consent)
        btn_layout.addWidget(revoke_btn)

        btn_layout.addStretch()
        layout.addLayout(btn_layout)

        warning_label = QLabel()
        warning_label.setWordWrap(True)
        warning_label.setStyleSheet("color: #FF9800; font-size: 9pt; margin-top: 5px;")
        self.set_translatable_text(warning_label, "advanced_revoke_consent_warning")
        layout.addWidget(warning_label)

        parent_layout.addWidget(group)

    def _refresh_consent_status(self):
        """Update the consent status label from current config."""
        if not self.config_manager:
            self._consent_status_label.setText(tr("advanced_consent_status_unknown"))
            return

        consent_info = self.config_manager.get_consent_info()
        if consent_info.get("consent_given", False):
            date_str = consent_info.get("consent_date", "")
            if date_str:
                try:
                    from datetime import datetime
                    dt = datetime.fromisoformat(date_str)
                    date_str = dt.strftime("%Y-%m-%d %H:%M")
                except (ValueError, TypeError):
                    pass
            version = consent_info.get("version", "?")
            self._consent_status_label.setText(
                tr("advanced_consent_status_given").format(date=date_str, version=version)
            )
            self._consent_status_label.setStyleSheet(
                "font-size: 9pt; margin-bottom: 5px; color: #27AE60;"
            )
        else:
            self._consent_status_label.setText(tr("advanced_consent_status_not_given"))
            self._consent_status_label.setStyleSheet(
                "font-size: 9pt; margin-bottom: 5px; color: #E74C3C;"
            )

    def _revoke_consent(self):
        """Revoke user consent after confirmation."""
        reply = QMessageBox.warning(
            self,
            tr("advanced_revoke_consent_confirm_title"),
            tr("advanced_revoke_consent_confirm_msg"),
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            QMessageBox.StandardButton.No,
        )
        if reply != QMessageBox.StandardButton.Yes:
            return

        if not self.config_manager:
            QMessageBox.warning(
                self,
                tr("advanced_revoke_consent_failed_title"),
                tr("advanced_config_mgr_unavailable"),
            )
            return

        try:
            self.config_manager.set_consent_info(consent_given=False, version="")
            self.config_manager.save_config()
            self._refresh_consent_status()

            _logger.info("User consent revoked via Settings")

            QMessageBox.information(
                self,
                tr("advanced_revoke_consent_success_title"),
                tr("advanced_revoke_consent_success_msg"),
            )
        except Exception as e:
            _logger.error("Failed to revoke consent: %s", e, exc_info=True)
            QMessageBox.critical(
                self,
                tr("advanced_revoke_consent_failed_title"),
                tr("advanced_revoke_consent_failed_msg").format(error=str(e)),
            )

    def _create_config_management_section(self, parent_layout):
        """Create configuration management section."""
        group = QGroupBox()
        self.set_translatable_text(group, "advanced_configuration_management_section")
        layout = QVBoxLayout(group)
        layout.setSpacing(12)
        layout.setContentsMargins(15, 20, 15, 15)
        
        # Description
        config_desc_label = QLabel()
        config_desc_label.setWordWrap(True)
        config_desc_label.setStyleSheet("color: #666666; font-size: 9pt; margin-bottom: 10px;")
        self.set_translatable_text(config_desc_label, "advanced_config_mgmt_desc")
        layout.addWidget(config_desc_label)
        
        # Buttons layout
        buttons_layout = QHBoxLayout()
        buttons_layout.setSpacing(10)
        
        # Export button
        export_btn = QPushButton()
        self.set_translatable_text(export_btn, "advanced_export_configuration_button")
        export_btn.setProperty("class", "action")
        export_btn.setMinimumWidth(150)
        export_btn.clicked.connect(self._export_config)
        buttons_layout.addWidget(export_btn)
        
        # Import button
        import_btn = QPushButton()
        self.set_translatable_text(import_btn, "advanced_import_configuration_button")
        import_btn.setProperty("class", "action")
        import_btn.setMinimumWidth(150)
        import_btn.clicked.connect(self._import_config)
        buttons_layout.addWidget(import_btn)
        
        # Reset button
        reset_btn = QPushButton()
        self.set_translatable_text(reset_btn, "advanced_reset_to_defaults_button")
        reset_btn.setProperty("class", "danger")
        reset_btn.setMinimumWidth(150)
        reset_btn.clicked.connect(self._reset_to_defaults)
        buttons_layout.addWidget(reset_btn)
        
        buttons_layout.addStretch()
        layout.addLayout(buttons_layout)
        
        # Warning for reset
        warning_label = QLabel()
        warning_label.setWordWrap(True)
        warning_label.setStyleSheet("color: #FF9800; font-size: 9pt; margin-top: 10px;")
        self.set_translatable_text(warning_label, "advanced_reset_warning")
        layout.addWidget(warning_label)
        
        parent_layout.addWidget(group)
    
    def _display_diagnostics(self):
        """Display system diagnostics information (called by refresh button)."""
        # Invalidate cache to force fresh collection
        self._diagnostics_cache = None
        self._diagnostics_cache_time = None
        
        # Show loading message
        self.diagnostics_text.setPlainText(tr("advanced_loading_diagnostics"))
        
        # Load diagnostics asynchronously
        self._load_diagnostics_async()
    
    def _export_config(self):
        """Export configuration to file."""
        try:
            if not self.config_manager:
                QMessageBox.warning(
                    self,
                    tr("advanced_export_failed_title"),
                    tr("advanced_config_mgr_unavailable")
                )
                return
            
            # Open file dialog
            file_path, _ = QFileDialog.getSaveFileName(
                self,
                tr("advanced_export_config_dialog_title"),
                str(Path.home() / "translation_config.json"),
                tr("advanced_file_filter_json")
            )
            
            if not file_path:
                return  # User cancelled
            
            # Get current configuration
            config_dict = self.config_manager.config
            
            # Write to file
            with open(file_path, 'w', encoding='utf-8') as f:
                json.dump(config_dict, f, indent=2, ensure_ascii=False)
            
            QMessageBox.information(
                self,
                tr("advanced_export_success_title"),
                tr("advanced_export_success_msg").format(path=file_path)
            )
            
            _logger.info("Configuration exported to: %s", file_path)
            
        except Exception as e:
            _logger.error("Failed to export config: %s", e, exc_info=True)
            QMessageBox.critical(
                self,
                tr("advanced_export_failed_title"),
                tr("advanced_export_failed_msg").format(error=str(e))
            )
    
    def _import_config(self):
        """Import configuration from file."""
        try:
            if not self.config_manager:
                QMessageBox.warning(
                    self,
                    tr("advanced_import_failed_title"),
                    tr("advanced_config_mgr_unavailable")
                )
                return
            
            # Show warning
            reply = QMessageBox.warning(
                self,
                tr("advanced_import_confirm_title"),
                tr("advanced_import_confirm_msg"),
                QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
                QMessageBox.StandardButton.No
            )
            
            if reply != QMessageBox.StandardButton.Yes:
                return
            
            # Open file dialog
            file_path, _ = QFileDialog.getOpenFileName(
                self,
                tr("advanced_import_config_dialog_title"),
                str(Path.home()),
                tr("advanced_file_filter_json")
            )
            
            if not file_path:
                return  # User cancelled
            
            # Read configuration file
            with open(file_path, 'r', encoding='utf-8') as f:
                imported_config = json.load(f)
            
            # Validate it's a dictionary
            if not isinstance(imported_config, dict):
                raise ValueError(tr("advanced_invalid_config_format"))
            
            # Update configuration
            self.config_manager.config = imported_config
            self.config_manager.save_config()
            
            QMessageBox.information(
                self,
                tr("advanced_import_success_title"),
                tr("advanced_import_success_msg").format(path=file_path)
            )
            
            _logger.info("Configuration imported from: %s", file_path)
            
        except json.JSONDecodeError as e:
            QMessageBox.critical(
                self,
                tr("advanced_import_failed_title"),
                tr("advanced_import_invalid_json").format(error=str(e))
            )
        except Exception as e:
            _logger.error("Failed to import config: %s", e, exc_info=True)
            QMessageBox.critical(
                self,
                tr("advanced_import_failed_title"),
                tr("advanced_import_failed_msg").format(error=str(e))
            )
    
    def _reset_to_defaults(self):
        """Reset configuration to default values."""
        try:
            # Show confirmation dialog
            reply = QMessageBox.warning(
                self,
                tr("advanced_reset_confirm_title"),
                tr("advanced_reset_confirm_msg"),
                QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
                QMessageBox.StandardButton.No
            )
            
            if reply != QMessageBox.StandardButton.Yes:
                return
            
            if not self.config_manager:
                QMessageBox.warning(
                    self,
                    tr("advanced_reset_failed_title"),
                    tr("advanced_config_mgr_unavailable")
                )
                return
            
            # Reset to defaults
            default_config = self.config_manager._get_default_config()
            self.config_manager.config = default_config
            self.config_manager.save_config()
            
            QMessageBox.information(
                self,
                tr("advanced_reset_success_title"),
                tr("advanced_reset_success_msg")
            )
            
            _logger.info("Configuration reset to defaults")
            
        except Exception as e:
            _logger.error("Failed to reset config: %s", e, exc_info=True)
            QMessageBox.critical(
                self,
                tr("advanced_reset_failed_title"),
                tr("advanced_reset_failed_msg").format(error=str(e))
            )
    
    def load_config(self):
        """Load configuration from config manager."""
        if not self.config_manager:
            return
        
        try:
            # Block signals during loading
            self.blockSignals(True)
            
            # Load log level
            log_level = self.config_manager.get_setting('logging.log_level', 'INFO')
            index = self.log_level_combo.findText(log_level)
            if index >= 0:
                self.log_level_combo.setCurrentIndex(index)
            
            # Load performance monitoring
            performance_monitoring = self.config_manager.get_setting('advanced.enable_monitoring', False)
            self.performance_monitoring_check.setChecked(performance_monitoring)
            
            # Load quiet console
            quiet_console = self.config_manager.get_setting('advanced.quiet_console', False)
            if self.quiet_console_check:
                self.quiet_console_check.setChecked(quiet_console)

            # Load debug mode
            debug_mode = self.config_manager.get_setting('advanced.debug_mode', False)
            self.debug_mode_check.setChecked(debug_mode)
            
            # Load show wizard setting
            show_wizard = self.config_manager.get_setting('startup.show_setup_wizard', True)
            if self.show_wizard_check:
                self.show_wizard_check.setChecked(show_wizard)
            
            # Load ROI detection settings
            if hasattr(self, 'roi_min_width_spin'):
                self.roi_min_width_spin.setValue(self.config_manager.get_setting('roi_detection.min_region_width', 50))
                self.roi_min_height_spin.setValue(self.config_manager.get_setting('roi_detection.min_region_height', 20))
                self.roi_max_width_spin.setValue(self.config_manager.get_setting('roi_detection.max_region_width', 2000))
                self.roi_max_height_spin.setValue(self.config_manager.get_setting('roi_detection.max_region_height', 1000))
                self.roi_padding_spin.setValue(self.config_manager.get_setting('roi_detection.padding', 10))
                self.roi_merge_distance_spin.setValue(self.config_manager.get_setting('roi_detection.merge_distance', 20))
                self.roi_confidence_spin.setValue(self.config_manager.get_setting('roi_detection.confidence_threshold', 0.3))
                self.roi_adaptive_threshold_check.setChecked(self.config_manager.get_setting('roi_detection.adaptive_threshold', True))
                self.roi_use_morphology_check.setChecked(self.config_manager.get_setting('roi_detection.use_morphology', True))
            
            # Unblock signals
            self.blockSignals(False)
            
            # Refresh diagnostics asynchronously
            if hasattr(self, 'diagnostics_text'):
                QTimer.singleShot(100, self._load_diagnostics_async)
            
            # Save the original state after loading
            self._original_state = self._get_current_state()
            
            _logger.debug("Advanced tab configuration loaded")
            
        except Exception as e:
            self.blockSignals(False)
            _logger.warning("Failed to load advanced tab config: %s", e, exc_info=True)
    
    def save_config(self):
        """
        Save configuration to config manager.
        
        Returns:
            tuple: (success: bool, error_message: str)
        """
        if not self.config_manager:
            return False, tr("advanced_config_mgr_unavailable")
        
        try:
            # Save log level
            self.config_manager.set_setting('logging.log_level', self.log_level_combo.currentText())
            
            # Save performance monitoring
            self.config_manager.set_setting('advanced.enable_monitoring', self.performance_monitoring_check.isChecked())
            
            # Save quiet console
            if self.quiet_console_check:
                self.config_manager.set_setting('advanced.quiet_console', self.quiet_console_check.isChecked())

            # Save debug mode
            self.config_manager.set_setting('advanced.debug_mode', self.debug_mode_check.isChecked())
            
            # Save show wizard setting
            if self.show_wizard_check:
                self.config_manager.set_setting('startup.show_setup_wizard', self.show_wizard_check.isChecked())
            
            # Save ROI detection settings
            if hasattr(self, 'roi_min_width_spin'):
                self.config_manager.set_setting('roi_detection.min_region_width', self.roi_min_width_spin.value())
                self.config_manager.set_setting('roi_detection.min_region_height', self.roi_min_height_spin.value())
                self.config_manager.set_setting('roi_detection.max_region_width', self.roi_max_width_spin.value())
                self.config_manager.set_setting('roi_detection.max_region_height', self.roi_max_height_spin.value())
                self.config_manager.set_setting('roi_detection.padding', self.roi_padding_spin.value())
                self.config_manager.set_setting('roi_detection.merge_distance', self.roi_merge_distance_spin.value())
                self.config_manager.set_setting('roi_detection.confidence_threshold', self.roi_confidence_spin.value())
                self.config_manager.set_setting('roi_detection.adaptive_threshold', self.roi_adaptive_threshold_check.isChecked())
                self.config_manager.set_setting('roi_detection.use_morphology', self.roi_use_morphology_check.isChecked())
            
            # Save the configuration file
            success, error_msg = self.config_manager.save_config()
            
            if not success:
                return False, error_msg
            
            # Update original state after saving
            self._original_state = self._get_current_state()
            
            _logger.info("Advanced tab configuration saved")
            return True, ""
            
        except Exception as e:
            error_msg = tr("advanced_save_failed_msg").format(error=e)
            _logger.error("%s", error_msg, exc_info=True)
            return False, error_msg
    
    def validate(self) -> bool:
        """
        Validate settings including CPU/GPU mode conflicts with OCR engines.
        
        Returns:
            True if settings are valid, False otherwise
        """
        if not self.config_manager:
            return True
        
        try:
            # Get runtime mode from performance settings
            runtime_mode = self.config_manager.get_setting('performance.runtime_mode', 'auto')
            
            # Get selected OCR engine
            ocr_engine = self.config_manager.get_setting('ocr.engine', 'easyocr')
            
            # Validate CPU mode conflicts with GPU-dependent OCR engines
            if runtime_mode == 'cpu':
                # EasyOCR requires GPU for optimal performance
                if ocr_engine == 'easyocr':
                    QMessageBox.warning(
                        self,
                        tr("advanced_config_conflict_title"),
                        tr("advanced_easyocr_cpu_warning")
                    )
                    return False
                
                # PaddleOCR also benefits from GPU
                if ocr_engine == 'paddleocr':
                    QMessageBox.warning(
                        self,
                        tr("advanced_config_conflict_title"),
                        tr("advanced_paddleocr_cpu_warning")
                    )
                    return False
                
                # Manga OCR requires GPU
                if ocr_engine == 'mokuro':
                    QMessageBox.warning(
                        self,
                        tr("advanced_config_conflict_title"),
                        tr("advanced_mangaocr_cpu_warning")
                    )
                    return False
            
            # All validations passed
            return True
            
        except Exception as e:
            _logger.error("Validation error in Advanced tab: %s", e, exc_info=True)
            # Don't block on validation errors
            return True
