"""
Advanced Settings Tab - PyQt6 Implementation
Debug logging, performance monitoring, experimental features, and system diagnostics.
"""

import sys
import platform
import json
from pathlib import Path
from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QFormLayout, QGroupBox,
    QLabel, QComboBox, QCheckBox, QPushButton, QTextEdit,
    QMessageBox, QFileDialog
)
from PyQt6.QtCore import Qt, pyqtSignal
from PyQt6.QtGui import QFont
from ui.custom_spinbox import CustomSpinBox, CustomDoubleSpinBox

# Import custom scroll area
from .scroll_area_no_wheel import ScrollAreaNoWheel

# Import translation system
from app.translations import TranslatableMixin

# Import path utilities for EXE compatibility
from app.utils.path_utils import get_app_path


class AdvancedSettingsTab(TranslatableMixin, QWidget):
    """Advanced settings including logging, monitoring, experimental features, and diagnostics."""
    
    # Signal emitted when any setting changes
    settingChanged = pyqtSignal()
    
    def __init__(self, config_manager=None, parent=None):
        """Initialize the Advanced settings tab."""
        super().__init__(parent)
        
        self.config_manager = config_manager
        
        # Track original loaded state to detect real changes
        self._original_state = {}
        
        # Log level widget
        self.log_level_combo = None
        
        # Performance monitoring widget
        self.performance_monitoring_check = None
        
        # Multi-threading widgets
        self.enable_multithreading_check = None
        self.cpu_workers_spin = None
        self.gpu_workers_spin = None
        self.enable_frame_skip_check = None
        self.enable_roi_detection_check = None
        self.enable_parallel_ocr_check = None
        self.batch_translation_check = None
        
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
        
        # Experimental features widgets
        self.experimental_checks = {}
        
        # Debug mode widget
        self.debug_mode_check = None
        
        # System diagnostics widget
        self.diagnostics_text = None
        
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
        self._create_multithreading_section(content_layout)
        self._create_roi_detection_section(content_layout)
        self._create_experimental_section(content_layout)
        self._create_debug_section(content_layout)
        self._create_diagnostics_section(content_layout)
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
        
        level_label = self._create_label("Log Level:", bold=True)
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
        desc_label = QLabel(
            "• DEBUG: Detailed information for diagnosing problems\n"
            "• INFO: General informational messages (recommended)\n"
            "• WARNING: Warning messages for potential issues\n"
            "• ERROR: Error messages for serious problems\n"
            "• CRITICAL: Critical errors that may cause application failure"
        )
        desc_label.setWordWrap(True)
        desc_label.setStyleSheet("color: #666666; font-size: 9pt; margin-top: 5px;")
        layout.addWidget(desc_label)
        
        # Log file location info
        log_info = QLabel("💡 Logs are saved to: ./logs/application.log")
        log_info.setStyleSheet("color: #666666; font-size: 9pt; margin-top: 10px;")
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
        desc_label = QLabel(
            "When enabled, the application will track and display performance metrics including:\n"
            "• OCR processing time\n"
            "• Translation processing time\n"
            "• Memory usage\n"
            "• Frame rate\n"
            "• API call statistics\n\n"
            "Note: Performance monitoring may slightly impact application performance."
        )
        desc_label.setWordWrap(True)
        desc_label.setStyleSheet("color: #666666; font-size: 9pt; margin-top: 5px;")
        layout.addWidget(desc_label)
        
        parent_layout.addWidget(group)
    
    def _create_multithreading_section(self, parent_layout):
        """Create multi-threading configuration section."""
        from PyQt6.QtWidgets import QSpinBox
        
        group = QGroupBox()
        self.set_translatable_text(group, "advanced_multi-threading_optimization_section")
        layout = QVBoxLayout(group)
        layout.setSpacing(12)
        layout.setContentsMargins(15, 20, 15, 15)
        
        # Enable multi-threading
        self.enable_multithreading_check = QCheckBox()
        self.set_translatable_text(self.enable_multithreading_check, "advanced_enable_multi-threading_check")
        self.enable_multithreading_check.setChecked(True)
        self.enable_multithreading_check.stateChanged.connect(self._on_multithreading_toggled)
        self.enable_multithreading_check.stateChanged.connect(self.on_change)
        layout.addWidget(self.enable_multithreading_check)
        
        # Description
        desc_label = QLabel(
            "Multi-threading enables parallel processing of OCR and translation tasks for better performance."
        )
        desc_label.setWordWrap(True)
        desc_label.setStyleSheet("color: #666666; font-size: 9pt; margin-bottom: 10px;")
        layout.addWidget(desc_label)
        
        # Create grid layout for worker threads (matching ROI Detection Settings style)
        from PyQt6.QtWidgets import QGridLayout
        workers_grid = QGridLayout()
        workers_grid.setHorizontalSpacing(8)
        workers_grid.setVerticalSpacing(8)
        workers_grid.setContentsMargins(0, 0, 0, 0)
        workers_grid.setColumnStretch(2, 1)  # Stretch last column to push everything left
        
        # CPU Workers
        self.cpu_workers_spin = CustomSpinBox()
        self.cpu_workers_spin.setMinimum(1)
        self.cpu_workers_spin.setMaximum(16)
        self.cpu_workers_spin.setValue(2)
        self.cpu_workers_spin.setSuffix("threads")
        self.cpu_workers_spin.valueChanged.connect(self.on_change)
        
        # GPU Workers
        self.gpu_workers_spin = CustomSpinBox()
        self.gpu_workers_spin.setMinimum(1)
        self.gpu_workers_spin.setMaximum(8)
        self.gpu_workers_spin.setValue(2)
        self.gpu_workers_spin.setSuffix("threads")
        self.gpu_workers_spin.valueChanged.connect(self.on_change)
        
        # Add to grid: Row 0 = CPU, Row 1 = GPU
        # Columns: 0=Label, 1=Spinbox
        workers_grid.addWidget(QLabel("💻 CPU Worker Threads:"), 0, 0)
        workers_grid.addWidget(self.cpu_workers_spin, 0, 1)
        
        workers_grid.addWidget(QLabel("🎮 GPU Worker Threads:"), 1, 0)
        workers_grid.addWidget(self.gpu_workers_spin, 1, 1)
        
        layout.addLayout(workers_grid)
        
        # Info text
        info_label = QLabel(
            "   Recommended: 2-4 threads for CPU-based OCR processing.\n"
            "   More threads = faster processing but higher CPU usage.\n\n"
            "   Recommended: 2-4 threads for GPU-accelerated translation.\n"
            "   GPU mode required for optimal performance. More threads = better throughput."
        )
        info_label.setWordWrap(True)
        info_label.setStyleSheet("color: #666666; font-size: 8pt; margin-left: 10px; margin-top: 5px; margin-bottom: 10px;")
        layout.addWidget(info_label)
        
        # Optimization options
        opt_label = self._create_label("🎯 Optimization Options:", bold=True)
        layout.addWidget(opt_label)
        
        # Frame skip detection
        self.enable_frame_skip_check = QCheckBox()
        self.set_translatable_text(self.enable_frame_skip_check, "advanced_enable_frame_skip_detection_check")
        self.enable_frame_skip_check.setChecked(True)
        self.enable_frame_skip_check.stateChanged.connect(self.on_change)
        layout.addWidget(self.enable_frame_skip_check)
        
        frame_skip_desc = QLabel(
            "   Skip processing identical frames (95% similarity threshold) to save CPU/GPU resources."
        )
        frame_skip_desc.setWordWrap(True)
        frame_skip_desc.setStyleSheet("color: #666666; font-size: 8pt; margin-left: 20px; margin-bottom: 8px;")
        layout.addWidget(frame_skip_desc)
        
        # ROI detection
        self.enable_roi_detection_check = QCheckBox()
        self.set_translatable_text(self.enable_roi_detection_check, "advanced_enable_roi_region_of_interest_detection_check")
        self.enable_roi_detection_check.setChecked(True)
        self.enable_roi_detection_check.stateChanged.connect(self.on_change)
        layout.addWidget(self.enable_roi_detection_check)
        
        roi_desc = QLabel(
            "   Detect and process only text regions, reducing OCR workload by up to 70%."
        )
        roi_desc.setWordWrap(True)
        roi_desc.setStyleSheet("color: #666666; font-size: 8pt; margin-left: 20px; margin-bottom: 8px;")
        layout.addWidget(roi_desc)
        
        # Parallel OCR
        self.enable_parallel_ocr_check = QCheckBox()
        self.set_translatable_text(self.enable_parallel_ocr_check, "advanced_enable_parallel_ocr_processing_check")
        self.enable_parallel_ocr_check.setChecked(True)
        self.enable_parallel_ocr_check.stateChanged.connect(self.on_change)
        layout.addWidget(self.enable_parallel_ocr_check)
        
        parallel_desc = QLabel(
            "   Process multiple text regions simultaneously using worker threads (4x speedup)."
        )
        parallel_desc.setWordWrap(True)
        parallel_desc.setStyleSheet("color: #666666; font-size: 8pt; margin-left: 20px; margin-bottom: 8px;")
        layout.addWidget(parallel_desc)
        
        # Batch translation
        self.batch_translation_check = QCheckBox()
        self.set_translatable_text(self.batch_translation_check, "advanced_enable_batch_translation_check")
        self.batch_translation_check.setChecked(True)
        self.batch_translation_check.stateChanged.connect(self.on_change)
        layout.addWidget(self.batch_translation_check)
        
        batch_desc = QLabel(
            "   Group multiple translations into single requests for better GPU utilization (3x speedup)."
        )
        batch_desc.setWordWrap(True)
        batch_desc.setStyleSheet("color: #666666; font-size: 8pt; margin-left: 20px; margin-bottom: 8px;")
        layout.addWidget(batch_desc)
        
        # Performance note
        perf_note = QLabel(
            "💡 Note: Total worker threads = CPU workers + GPU workers. "
            "Recommended total: 4-8 threads depending on your hardware."
        )
        perf_note.setWordWrap(True)
        perf_note.setStyleSheet("color: #4A9EFF; font-size: 9pt; margin-top: 10px; padding: 10px; background-color: #1E3A4F; border-radius: 4px; border: 1px solid #2A5A7F;")
        layout.addWidget(perf_note)
        
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
        desc_label = QLabel(
            "Configure Region of Interest detection for optimized OCR processing. "
            "ROI detection identifies text regions to process instead of the entire frame."
        )
        desc_label.setWordWrap(True)
        desc_label.setStyleSheet("color: #666666; font-size: 9pt; margin-bottom: 10px;")
        layout.addRow(desc_label)
        
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
        size_grid.addWidget(QLabel("Minimum Region Size:"), 0, 0)
        size_grid.addWidget(QLabel("Width:"), 0, 1)
        size_grid.addWidget(self.roi_min_width_spin, 0, 2)
        size_grid.addWidget(QLabel("Height:"), 0, 3)
        size_grid.addWidget(self.roi_min_height_spin, 0, 4)
        
        size_grid.addWidget(QLabel("Maximum Region Size:"), 1, 0)
        size_grid.addWidget(QLabel("Width:"), 1, 1)
        size_grid.addWidget(self.roi_max_width_spin, 1, 2)
        size_grid.addWidget(QLabel("Height:"), 1, 3)
        size_grid.addWidget(self.roi_max_height_spin, 1, 4)
        
        # Create spinboxes for single-value rows
        self.roi_padding_spin = CustomSpinBox()
        self.roi_padding_spin.setRange(0, 50)
        self.roi_padding_spin.setValue(10)
        self.roi_padding_spin.setSuffix("px")
        self.roi_padding_spin.setToolTip("Extra space around detected regions")
        self.roi_padding_spin.valueChanged.connect(self.settingChanged.emit)
        
        self.roi_merge_distance_spin = CustomSpinBox()
        self.roi_merge_distance_spin.setRange(0, 100)
        self.roi_merge_distance_spin.setValue(20)
        self.roi_merge_distance_spin.setSuffix("px")
        self.roi_merge_distance_spin.setToolTip("Distance threshold for merging nearby regions")
        self.roi_merge_distance_spin.valueChanged.connect(self.settingChanged.emit)
        
        self.roi_confidence_spin = CustomDoubleSpinBox()
        self.roi_confidence_spin.setRange(0.0, 1.0)
        self.roi_confidence_spin.setSingleStep(0.05)
        self.roi_confidence_spin.setValue(0.3)
        self.roi_confidence_spin.setDecimals(2)
        self.roi_confidence_spin.setToolTip("Minimum confidence for text region detection")
        self.roi_confidence_spin.valueChanged.connect(self.settingChanged.emit)
        
        # Add single-value rows to grid (rows 2, 3, 4)
        size_grid.addWidget(QLabel("Region Padding:"), 2, 0)
        size_grid.addWidget(self.roi_padding_spin, 2, 1, 1, 2)  # Span 2 columns
        
        size_grid.addWidget(QLabel("Merge Distance:"), 3, 0)
        size_grid.addWidget(self.roi_merge_distance_spin, 3, 1, 1, 2)  # Span 2 columns
        
        size_grid.addWidget(QLabel("Confidence Threshold:"), 4, 0)
        size_grid.addWidget(self.roi_confidence_spin, 4, 1, 1, 2)  # Span 2 columns
        
        # Add grid to main layout
        layout.addRow(size_grid)
        
        # Adaptive threshold
        self.roi_adaptive_threshold_check = QCheckBox()
        self.set_translatable_text(self.roi_adaptive_threshold_check, "advanced_use_adaptive_thresholding_check")
        self.roi_adaptive_threshold_check.setChecked(True)
        self.roi_adaptive_threshold_check.setToolTip("Adaptive thresholding for better text detection")
        self.roi_adaptive_threshold_check.stateChanged.connect(self.settingChanged.emit)
        layout.addRow("", self.roi_adaptive_threshold_check)
        
        # Morphology
        self.roi_use_morphology_check = QCheckBox()
        self.set_translatable_text(self.roi_use_morphology_check, "advanced_use_morphological_operations_check")
        self.roi_use_morphology_check.setChecked(True)
        self.roi_use_morphology_check.setToolTip("Morphological operations to connect text regions")
        self.roi_use_morphology_check.stateChanged.connect(self.settingChanged.emit)
        layout.addRow("", self.roi_use_morphology_check)
        
        # Note
        note_label = QLabel(
            "💡 Tip: Lower confidence threshold detects more regions but may include noise. "
            "Higher values are more selective."
        )
        note_label.setWordWrap(True)
        note_label.setStyleSheet("color: #2196F3; font-size: 8pt; margin-top: 10px;")
        layout.addRow(note_label)
        
        parent_layout.addWidget(group)
    
    def _on_multithreading_toggled(self, state):
        """Handle multi-threading checkbox toggle."""
        enabled = (state == Qt.CheckState.Checked.value)
        
        # Enable/disable worker thread spinboxes
        if hasattr(self, 'cpu_workers_spin'):
            self.cpu_workers_spin.setEnabled(enabled)
        if hasattr(self, 'gpu_workers_spin'):
            self.gpu_workers_spin.setEnabled(enabled)
        if hasattr(self, 'enable_parallel_ocr_check'):
            self.enable_parallel_ocr_check.setEnabled(enabled)
        if hasattr(self, 'batch_translation_check'):
            self.batch_translation_check.setEnabled(enabled)
    
    def _create_experimental_section(self, parent_layout):
        """Create experimental features section."""
        group = QGroupBox()
        self.set_translatable_text(group, "advanced_advanced_features_section")
        layout = QVBoxLayout(group)
        layout.setSpacing(8)
        layout.setContentsMargins(15, 20, 15, 15)
        
        # Info label
        info_label = QLabel(
            "ℹ️ <b>Note:</b> All features listed here are fully implemented and stable. "
            "Parallel OCR is already enabled by default."
        )
        info_label.setWordWrap(True)
        info_label.setStyleSheet("color: #2196F3; font-size: 9pt; margin-bottom: 10px; padding: 8px; "
                                "background-color: rgba(33, 150, 243, 0.1); border-radius: 4px;")
        layout.addWidget(info_label)
        
        # Experimental features list (removed parallel_ocr since it's default)
        experimental_features = [
            ('smart_caching', '🧠 Smart Translation Caching', 
             'Intelligent cache management with context-aware matching'),
            ('auto_language_detection', '🌐 Enhanced Auto Language Detection', 
             'Improved language detection using multiple algorithms'),
            ('gpu_memory_optimization', '🎮 GPU Memory Optimization', 
             'Advanced GPU memory management - recommended for GPU users'),
            ('adaptive_quality', '🎯 Adaptive Quality Mode', 
             'Automatically adjust quality based on content complexity')
        ]
        
        for feature_id, feature_name, feature_desc in experimental_features:
            # Feature checkbox
            check = QCheckBox(feature_name)
            check.setChecked(False)
            check.stateChanged.connect(self.on_change)
            self.experimental_checks[feature_id] = check
            layout.addWidget(check)
            
            # Feature description
            desc = QLabel(f"   {feature_desc}")
            desc.setWordWrap(True)
            desc.setStyleSheet("color: #666666; font-size: 9pt; margin-left: 20px; margin-bottom: 8px;")
            layout.addWidget(desc)
        
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
        desc_label = QLabel(
            "Debug mode enables additional diagnostic features:\n"
            "• Verbose console output\n"
            "• Detailed error messages\n"
            "• Performance profiling\n"
            "• Memory leak detection\n"
            "• API request/response logging\n\n"
            "⚠️ Debug mode will significantly increase log file size and may impact performance."
        )
        desc_label.setWordWrap(True)
        desc_label.setStyleSheet("color: #666666; font-size: 9pt; margin-top: 5px;")
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
        info_label = QLabel(
            "System diagnostics provide information about your hardware, software, "
            "and application configuration to help troubleshoot issues."
        )
        info_label.setWordWrap(True)
        info_label.setStyleSheet("color: #666666; font-size: 9pt; margin-top: 5px;")
        layout.addWidget(info_label)
        
        parent_layout.addWidget(group)
        
        # Initial diagnostics display
        self._display_diagnostics()
    
    def _create_config_management_section(self, parent_layout):
        """Create configuration management section."""
        group = QGroupBox()
        self.set_translatable_text(group, "advanced_configuration_management_section")
        layout = QVBoxLayout(group)
        layout.setSpacing(12)
        layout.setContentsMargins(15, 20, 15, 15)
        
        # Description
        desc_label = QLabel(
            "Export your configuration to backup settings or share with other devices. "
            "Import a configuration file to restore previous settings."
        )
        desc_label.setWordWrap(True)
        desc_label.setStyleSheet("color: #666666; font-size: 9pt; margin-bottom: 10px;")
        layout.addWidget(desc_label)
        
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
        warning_label = QLabel(
            "⚠️ Reset to Defaults will restore all settings to their original values. "
            "This action cannot be undone."
        )
        warning_label.setWordWrap(True)
        warning_label.setStyleSheet("color: #FF9800; font-size: 9pt; margin-top: 10px;")
        layout.addWidget(warning_label)
        
        parent_layout.addWidget(group)
    
    def _display_diagnostics(self):
        """Display system diagnostics information."""
        try:
            diagnostics = []
            
            # System information
            diagnostics.append("=== SYSTEM INFORMATION ===")
            diagnostics.append(f"Operating System: {platform.system()} {platform.release()}")
            diagnostics.append(f"Platform: {platform.platform()}")
            diagnostics.append(f"Architecture: {platform.machine()}")
            diagnostics.append(f"Processor: {platform.processor()}")
            diagnostics.append(f"Python Version: {sys.version.split()[0]}")
            diagnostics.append("")
            
            # PyQt6 information
            diagnostics.append("=== PYQT6 INFORMATION ===")
            try:
                from PyQt6.QtCore import QT_VERSION_STR, PYQT_VERSION_STR
                diagnostics.append(f"Qt Version: {QT_VERSION_STR}")
                diagnostics.append(f"PyQt6 Version: {PYQT_VERSION_STR}")
            except:
                diagnostics.append("PyQt6 version information unavailable")
            diagnostics.append("")
            
            # PyTorch information
            diagnostics.append("=== PYTORCH INFORMATION ===")
            try:
                import torch
                diagnostics.append(f"PyTorch Version: {torch.__version__}")
                diagnostics.append(f"CUDA Available: {torch.cuda.is_available()}")
                if torch.cuda.is_available():
                    diagnostics.append(f"CUDA Version: {torch.version.cuda}")
                    diagnostics.append(f"GPU Count: {torch.cuda.device_count()}")
                    if torch.cuda.device_count() > 0:
                        diagnostics.append(f"GPU 0: {torch.cuda.get_device_name(0)}")
                        diagnostics.append(f"GPU Memory: {torch.cuda.get_device_properties(0).total_memory / 1024**3:.1f} GB")
            except ImportError:
                diagnostics.append("PyTorch not installed")
            except Exception as e:
                diagnostics.append(f"Error getting PyTorch info: {e}")
            diagnostics.append("")
            
            # Application paths (EXE-compatible)
            diagnostics.append("=== APPLICATION PATHS ===")
            diagnostics.append(f"Working Directory: {Path.cwd()}")
            diagnostics.append(f"Config File: {get_app_path('config', 'user_config.json')}")
            diagnostics.append(f"Models Directory: {get_app_path('models')}")
            diagnostics.append(f"Cache Directory: {get_app_path('cache')}")
            diagnostics.append(f"Logs Directory: {get_app_path('logs')}")
            diagnostics.append(f"Dictionary Directory: {get_app_path('dictionary')}")
            diagnostics.append(f"Data Directory: {get_app_path('data')}")
            diagnostics.append("")
            
            # Configuration status
            diagnostics.append("=== CONFIGURATION STATUS ===")
            if self.config_manager:
                try:
                    runtime_mode = self.config_manager.get_setting('performance.runtime_mode', 'unknown')
                    diagnostics.append(f"Runtime Mode: {runtime_mode}")
                    
                    source_lang = self.config_manager.get_setting('translation.source_language', 'unknown')
                    target_lang = self.config_manager.get_setting('translation.target_language', 'unknown')
                    diagnostics.append(f"Languages: {source_lang} → {target_lang}")
                    
                    cache_enabled = self.config_manager.get_setting('storage.cache_enabled', False)
                    diagnostics.append(f"Cache Enabled: {cache_enabled}")
                except Exception as e:
                    diagnostics.append(f"Error reading configuration: {e}")
            else:
                diagnostics.append("Configuration manager not available")
            diagnostics.append("")
            
            # Memory information
            diagnostics.append("=== MEMORY INFORMATION ===")
            try:
                import psutil
                memory = psutil.virtual_memory()
                diagnostics.append(f"Total Memory: {memory.total / 1024**3:.1f} GB")
                diagnostics.append(f"Available Memory: {memory.available / 1024**3:.1f} GB")
                diagnostics.append(f"Memory Usage: {memory.percent}%")
            except ImportError:
                diagnostics.append("psutil not installed (memory info unavailable)")
            except Exception as e:
                diagnostics.append(f"Error getting memory info: {e}")
            
            # Display diagnostics
            self.diagnostics_text.setPlainText("\n".join(diagnostics))
            
            print("[DEBUG] System diagnostics displayed")
            
        except Exception as e:
            error_msg = f"Error displaying diagnostics:\n\n{str(e)}"
            self.diagnostics_text.setPlainText(error_msg)
            print(f"[ERROR] Failed to display diagnostics: {e}")
            import traceback
            traceback.print_exc()
    
    def _export_config(self):
        """Export configuration to file."""
        try:
            if not self.config_manager:
                QMessageBox.warning(
                    self,
                    "Export Failed",
                    "Configuration manager not available."
                )
                return
            
            # Open file dialog
            file_path, _ = QFileDialog.getSaveFileName(
                self,
                "Export Configuration",
                str(Path.home() / "translation_config.json"),
                "JSON Files (*.json);;All Files (*.*)"
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
                "Export Successful",
                f"Configuration exported successfully to:\n\n{file_path}"
            )
            
            print(f"[INFO] Configuration exported to: {file_path}")
            
        except Exception as e:
            QMessageBox.critical(
                self,
                "Export Failed",
                f"Failed to export configuration:\n\n{str(e)}"
            )
            print(f"[ERROR] Failed to export config: {e}")
            import traceback
            traceback.print_exc()
    
    def _import_config(self):
        """Import configuration from file."""
        try:
            if not self.config_manager:
                QMessageBox.warning(
                    self,
                    "Import Failed",
                    "Configuration manager not available."
                )
                return
            
            # Show warning
            reply = QMessageBox.warning(
                self,
                "Import Configuration",
                "Importing a configuration will replace all current settings.\n\n"
                "Are you sure you want to continue?",
                QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
                QMessageBox.StandardButton.No
            )
            
            if reply != QMessageBox.StandardButton.Yes:
                return
            
            # Open file dialog
            file_path, _ = QFileDialog.getOpenFileName(
                self,
                "Import Configuration",
                str(Path.home()),
                "JSON Files (*.json);;All Files (*.*)"
            )
            
            if not file_path:
                return  # User cancelled
            
            # Read configuration file
            with open(file_path, 'r', encoding='utf-8') as f:
                imported_config = json.load(f)
            
            # Validate it's a dictionary
            if not isinstance(imported_config, dict):
                raise ValueError("Invalid configuration file format")
            
            # Update configuration
            self.config_manager.config = imported_config
            self.config_manager.save_config()
            
            QMessageBox.information(
                self,
                "Import Successful",
                f"Configuration imported successfully from:\n\n{file_path}\n\n"
                "Please restart the application for all changes to take effect."
            )
            
            print(f"[INFO] Configuration imported from: {file_path}")
            
        except json.JSONDecodeError as e:
            QMessageBox.critical(
                self,
                "Import Failed",
                f"Invalid JSON file:\n\n{str(e)}"
            )
        except Exception as e:
            QMessageBox.critical(
                self,
                "Import Failed",
                f"Failed to import configuration:\n\n{str(e)}"
            )
            print(f"[ERROR] Failed to import config: {e}")
            import traceback
            traceback.print_exc()
    
    def _reset_to_defaults(self):
        """Reset configuration to default values."""
        try:
            # Show confirmation dialog
            reply = QMessageBox.warning(
                self,
                "Reset to Defaults",
                "Are you sure you want to reset all settings to their default values?\n\n"
                "This will:\n"
                "• Reset all configuration options\n"
                "• Clear custom settings\n"
                "• Restore factory defaults\n\n"
                "⚠️ This action cannot be undone!",
                QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
                QMessageBox.StandardButton.No
            )
            
            if reply != QMessageBox.StandardButton.Yes:
                return
            
            if not self.config_manager:
                QMessageBox.warning(
                    self,
                    "Reset Failed",
                    "Configuration manager not available."
                )
                return
            
            # Reset to defaults
            default_config = self.config_manager._get_default_config()
            self.config_manager.config = default_config
            self.config_manager.save_config()
            
            QMessageBox.information(
                self,
                "Reset Successful",
                "All settings have been reset to their default values.\n\n"
                "Please restart the application for changes to take effect."
            )
            
            print("[INFO] Configuration reset to defaults")
            
        except Exception as e:
            QMessageBox.critical(
                self,
                "Reset Failed",
                f"Failed to reset configuration:\n\n{str(e)}"
            )
            print(f"[ERROR] Failed to reset config: {e}")
            import traceback
            traceback.print_exc()
    
    def load_config(self):
        """Load configuration from config manager."""
        if not self.config_manager:
            return
        
        try:
            # Block signals during loading
            self.blockSignals(True)
            
            # Load log level
            log_level = self.config_manager.get_setting('advanced.log_level', 'INFO')
            index = self.log_level_combo.findText(log_level)
            if index >= 0:
                self.log_level_combo.setCurrentIndex(index)
            
            # Load performance monitoring
            performance_monitoring = self.config_manager.get_setting('advanced.enable_monitoring', False)
            self.performance_monitoring_check.setChecked(performance_monitoring)
            
            # Load experimental features
            experimental_features = self.config_manager.get_setting('advanced.experimental_features', [])
            for feature_id, check in self.experimental_checks.items():
                check.setChecked(feature_id in experimental_features)
            
            # Load debug mode
            debug_mode = self.config_manager.get_setting('advanced.debug_mode', False)
            self.debug_mode_check.setChecked(debug_mode)
            
            # Load multi-threading settings
            enable_multithreading = self.config_manager.get_setting('performance.enable_multithreading', True)
            self.enable_multithreading_check.setChecked(enable_multithreading)
            
            cpu_workers = self.config_manager.get_setting('performance.cpu_worker_threads', 2)
            self.cpu_workers_spin.setValue(cpu_workers)
            
            gpu_workers = self.config_manager.get_setting('performance.gpu_worker_threads', 2)
            self.gpu_workers_spin.setValue(gpu_workers)
            
            enable_frame_skip = self.config_manager.get_setting('performance.enable_frame_skip', True)
            self.enable_frame_skip_check.setChecked(enable_frame_skip)
            
            enable_roi = self.config_manager.get_setting('performance.enable_roi_detection', True)
            self.enable_roi_detection_check.setChecked(enable_roi)
            
            enable_parallel_ocr = self.config_manager.get_setting('performance.enable_parallel_ocr', True)
            self.enable_parallel_ocr_check.setChecked(enable_parallel_ocr)
            
            batch_translation = self.config_manager.get_setting('performance.batch_translation', True)
            self.batch_translation_check.setChecked(batch_translation)
            
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
            
            # Refresh diagnostics
            self._display_diagnostics()
            
            # Save the original state after loading
            self._original_state = self._get_current_state()
            
            print("[DEBUG] Advanced tab configuration loaded")
            
        except Exception as e:
            self.blockSignals(False)
            print(f"[WARNING] Failed to load advanced tab config: {e}")
            import traceback
            traceback.print_exc()
    
    def save_config(self):
        """Save configuration to config manager."""
        if not self.config_manager:
            return
        
        try:
            # Save log level
            self.config_manager.set_setting('advanced.log_level', self.log_level_combo.currentText())
            
            # Save performance monitoring
            self.config_manager.set_setting('advanced.enable_monitoring', self.performance_monitoring_check.isChecked())
            
            # Save experimental features
            enabled_features = [
                feature_id for feature_id, check in self.experimental_checks.items()
                if check.isChecked()
            ]
            self.config_manager.set_setting('advanced.experimental_features', enabled_features)
            
            # Save debug mode
            self.config_manager.set_setting('advanced.debug_mode', self.debug_mode_check.isChecked())
            
            # Save multi-threading settings
            self.config_manager.set_setting('performance.enable_multithreading', self.enable_multithreading_check.isChecked())
            self.config_manager.set_setting('performance.cpu_worker_threads', self.cpu_workers_spin.value())
            self.config_manager.set_setting('performance.gpu_worker_threads', self.gpu_workers_spin.value())
            self.config_manager.set_setting('performance.max_worker_threads', 
                                           self.cpu_workers_spin.value() + self.gpu_workers_spin.value())
            self.config_manager.set_setting('performance.enable_frame_skip', self.enable_frame_skip_check.isChecked())
            self.config_manager.set_setting('performance.enable_roi_detection', self.enable_roi_detection_check.isChecked())
            self.config_manager.set_setting('performance.enable_parallel_ocr', self.enable_parallel_ocr_check.isChecked())
            self.config_manager.set_setting('performance.batch_translation', self.batch_translation_check.isChecked())
            
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
            if hasattr(self.config_manager, 'save_config'):
                self.config_manager.save_config()
            elif hasattr(self.config_manager, 'save_configuration'):
                config_dict = self.config_manager._config_to_dict(self.config_manager._config)
                self.config_manager.save_configuration(config_dict)
            
            # Update original state after saving
            self._original_state = self._get_current_state()
            
            print("[INFO] Advanced tab configuration saved")
            
        except Exception as e:
            print(f"[ERROR] Failed to save advanced tab config: {e}")
            import traceback
            traceback.print_exc()
    
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
                        "Configuration Conflict",
                        "⚠️ EasyOCR requires GPU acceleration for optimal performance.\n\n"
                        "Current configuration:\n"
                        "• Runtime Mode: CPU Only\n"
                        "• OCR Engine: EasyOCR\n\n"
                        "Recommendations:\n"
                        "1. Change Runtime Mode to 'Auto' or 'GPU' in the General tab\n"
                        "2. Or switch to Tesseract OCR in the OCR Engines tab\n\n"
                        "EasyOCR may run very slowly or fail in CPU-only mode."
                    )
                    return False
                
                # PaddleOCR also benefits from GPU
                if ocr_engine == 'paddleocr':
                    QMessageBox.warning(
                        self,
                        "Configuration Conflict",
                        "⚠️ PaddleOCR requires GPU acceleration for optimal performance.\n\n"
                        "Current configuration:\n"
                        "• Runtime Mode: CPU Only\n"
                        "• OCR Engine: PaddleOCR\n\n"
                        "Recommendations:\n"
                        "1. Change Runtime Mode to 'Auto' or 'GPU' in the General tab\n"
                        "2. Or switch to Tesseract OCR in the OCR Engines tab\n\n"
                        "PaddleOCR may run very slowly in CPU-only mode."
                    )
                    return False
                
                # Manga OCR requires GPU
                if ocr_engine == 'manga_ocr':
                    QMessageBox.warning(
                        self,
                        "Configuration Conflict",
                        "⚠️ Manga OCR requires GPU acceleration.\n\n"
                        "Current configuration:\n"
                        "• Runtime Mode: CPU Only\n"
                        "• OCR Engine: Manga OCR\n\n"
                        "Recommendations:\n"
                        "1. Change Runtime Mode to 'Auto' or 'GPU' in the General tab\n"
                        "2. Or switch to Tesseract OCR in the OCR Engines tab\n\n"
                        "Manga OCR will not function in CPU-only mode."
                    )
                    return False
            
            # Validate experimental features compatibility
            experimental_features = self.config_manager.get_setting('advanced.experimental_features', [])
            
            # Parallel OCR requires GPU for best performance
            if 'parallel_ocr' in experimental_features and runtime_mode == 'cpu':
                reply = QMessageBox.question(
                    self,
                    "Performance Warning",
                    "⚠️ Parallel OCR Processing is enabled with CPU-only mode.\n\n"
                    "This experimental feature works best with GPU acceleration.\n"
                    "Performance may be limited in CPU-only mode.\n\n"
                    "Do you want to continue with this configuration?",
                    QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
                    QMessageBox.StandardButton.No
                )
                
                if reply != QMessageBox.StandardButton.Yes:
                    return False
            
            # GPU memory optimization requires GPU mode
            if 'gpu_memory_optimization' in experimental_features and runtime_mode == 'cpu':
                QMessageBox.warning(
                    self,
                    "Configuration Conflict",
                    "⚠️ GPU Memory Optimization is enabled but Runtime Mode is set to CPU.\n\n"
                    "This experimental feature requires GPU mode to function.\n\n"
                    "Please either:\n"
                    "1. Change Runtime Mode to 'Auto' or 'GPU' in the General tab\n"
                    "2. Or disable GPU Memory Optimization"
                )
                return False
            
            # All validations passed
            return True
            
        except Exception as e:
            print(f"[ERROR] Validation error in Advanced tab: {e}")
            import traceback
            traceback.print_exc()
            # Don't block on validation errors
            return True
