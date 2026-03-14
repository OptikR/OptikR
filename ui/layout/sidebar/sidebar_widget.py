"""
Sidebar Widget Module

Left sidebar displaying system status, metrics, and language controls.
"""

from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QComboBox, QFrame
)
from PyQt6.QtCore import pyqtSignal
from app.localization import TranslatableMixin, tr


class SidebarWidget(TranslatableMixin, QWidget):
    """
    Left sidebar widget with system status and controls.
    
    Signals:
        logsClicked: Emitted when View Logs button clicked
        quickOcrSwitchClicked: Emitted when Quick Switch OCR button clicked
        fullTestClicked: Emitted when Full Test button clicked
        benchmarkClicked: Emitted when Benchmark button clicked
        languagePackClicked: Emitted when Language Packs button clicked
        imageProcessingClicked: Emitted when Image Processing button clicked
        presetLoaded: Emitted when preset is loaded (preset_name)
        contentModeChanged: Emitted when content mode changes ('static' or 'dynamic')
        pipelineModeChanged: Emitted when pipeline mode changes ('text', 'vision', or 'audio')
    """
    
    # Signals
    logsClicked = pyqtSignal()
    quickOcrSwitchClicked = pyqtSignal()
    fullTestClicked = pyqtSignal()
    benchmarkClicked = pyqtSignal()
    languagePackClicked = pyqtSignal()
    imageProcessingClicked = pyqtSignal()
    presetLoaded = pyqtSignal(str)
    contentModeChanged = pyqtSignal(str)
    pipelineModeChanged = pyqtSignal(str)
    
    def __init__(self, config_manager, parent=None):
        """
        Initialize sidebar widget.
        
        Args:
            config_manager: Configuration manager instance
            parent: Parent widget (optional)
        """
        super().__init__(parent)
        self.config_manager = config_manager
        
        # Language mapping
        self.language_map = {
            'en': 'English',
            'de': 'German',
            'es': 'Spanish',
            'fr': 'French',
            'ja': 'Japanese',
            'ko': 'Korean',
            'zh': 'Chinese',
            'zh-CN': 'Chinese (Simplified)',
            'zh-TW': 'Chinese (Traditional)',
            'pt': 'Portuguese',
            'it': 'Italian',
            'ru': 'Russian',
            'ar': 'Arabic',
            'hi': 'Hindi',
            'th': 'Thai',
            'vi': 'Vietnamese',
            'tr': 'Turkish',
            'pl': 'Polish',
            'nl': 'Dutch',
            'sv': 'Swedish',
            'id': 'Indonesian'
        }
        
        self.init_ui()
    
    def init_ui(self):
        """Initialize the sidebar UI."""
        # Get sidebar width from config but clamp to avoid clipped content.
        sidebar_width = self.config_manager.get_setting('ui.sidebar_width', 220)
        try:
            sidebar_width = int(sidebar_width)
        except (TypeError, ValueError):
            sidebar_width = 220
        sidebar_width = max(sidebar_width, 260)
        
        self.setObjectName("sidebar")
        self.setMinimumWidth(260)
        self.setFixedWidth(sidebar_width)
        
        layout = QVBoxLayout(self)
        layout.setContentsMargins(10, 10, 10, 10)
        layout.setSpacing(8)
        
        # System Status section
        self._create_system_status_section(layout)
        
        # Presets section (NEW)
        self._create_presets_section(layout)
        
        # Runtime Mode section
        self._create_runtime_mode_section(layout)
        
        # Pipeline Mode section (text / vision / audio)
        self._create_pipeline_mode_section(layout)
        
        # Metrics section
        self._create_metrics_section(layout)
        
        # Action buttons
        self._create_action_buttons(layout)
        
        # Languages section
        self._create_languages_section(layout)
        
        layout.addStretch()
    
    def _create_system_status_section(self, layout):
        """Create system status section."""
        status_label = QLabel()
        self.set_translatable_text(status_label, "sidebar_system_status")
        status_label.setStyleSheet(
            "font-size: 9pt; font-weight: 600; color: #9E9E9E; "
            "padding: 2px 0; letter-spacing: 0.5px;"
        )
        layout.addWidget(status_label)

        status_frame = QFrame()
        status_frame.setStyleSheet(
            "QFrame { background-color: #2A2A2A; border: 1px solid #3A3A3A; "
            "border-radius: 6px; }"
        )
        status_layout = QVBoxLayout(status_frame)
        status_layout.setContentsMargins(8, 8, 8, 8)
        status_layout.setSpacing(2)

        status_item = QLabel()
        self.set_translatable_text(status_item, "sidebar_status")
        status_item.setStyleSheet("font-size: 8pt; color: #B0B0B0;")
        status_layout.addWidget(status_item)

        self.status_label = QLabel()
        self.set_translatable_text(self.status_label, "sidebar_initializing")
        self.status_label.setStyleSheet("font-size: 8pt; margin-left: 10px; color: #D0D0D0;")
        status_layout.addWidget(self.status_label)

        layout.addWidget(status_frame)
    
    def _create_presets_section(self, layout):
        """Create presets section for saving/loading configurations."""
        presets_label = QLabel()
        self.set_translatable_text(presets_label, "sidebar_presets")
        presets_label.setStyleSheet(
            "font-size: 9pt; font-weight: 600; color: #9E9E9E; "
            "padding: 2px 0; letter-spacing: 0.5px;"
        )
        layout.addWidget(presets_label)

        presets_frame = QFrame()
        presets_frame.setStyleSheet(
            "QFrame { background-color: #2A2A2A; border: 1px solid #3A3A3A; "
            "border-radius: 6px; }"
        )
        presets_layout = QVBoxLayout(presets_frame)
        presets_layout.setContentsMargins(8, 8, 8, 8)
        presets_layout.setSpacing(6)

        self.preset_combo = QComboBox()
        self.set_translatable_text(self.preset_combo, "sidebar_preset_tooltip", method="setToolTip")
        self.preset_combo.setStyleSheet(
            "QComboBox { font-size: 8pt; background-color: #1E1E1E; "
            "border: 1px solid #3E3E3E; border-radius: 4px; padding: 4px 8px; color: #E0E0E0; }"
            "QComboBox:hover { border: 1px solid #5E5E5E; }"
            "QComboBox::drop-down { border: none; width: 18px; }"
            "QComboBox::down-arrow { border-left: 4px solid transparent; "
            "border-right: 4px solid transparent; border-top: 5px solid #888; margin-right: 5px; }"
        )
        presets_layout.addWidget(self.preset_combo)

        buttons_layout = QHBoxLayout()
        buttons_layout.setSpacing(4)

        sidebar_btn_style = (
            "QPushButton {{ font-size: 7pt; padding: 4px 0; border-radius: 4px; "
            "border: none; font-weight: 600; color: #FFF; min-width: 0; "
            "background-color: {bg}; }}"
            "QPushButton:hover {{ background-color: {hover}; }}"
            "QPushButton:pressed {{ background-color: {pressed}; }}"
        )

        load_btn = QPushButton()
        self.set_translatable_text(load_btn, "sidebar_load_btn")
        self.set_translatable_text(load_btn, "sidebar_load_preset_tooltip", method="setToolTip")
        load_btn.setStyleSheet(sidebar_btn_style.format(
            bg="#00897B", hover="#00796B", pressed="#00695C"
        ))
        load_btn.clicked.connect(self._load_preset)
        buttons_layout.addWidget(load_btn)

        save_btn = QPushButton()
        self.set_translatable_text(save_btn, "sidebar_save_btn")
        self.set_translatable_text(save_btn, "sidebar_save_preset_tooltip", method="setToolTip")
        save_btn.setStyleSheet(sidebar_btn_style.format(
            bg="#1976D2", hover="#1565C0", pressed="#0D47A1"
        ))
        save_btn.clicked.connect(self._save_preset)
        buttons_layout.addWidget(save_btn)

        delete_btn = QPushButton()
        self.set_translatable_text(delete_btn, "sidebar_delete_btn")
        self.set_translatable_text(delete_btn, "sidebar_delete_preset_tooltip", method="setToolTip")
        delete_btn.setStyleSheet(sidebar_btn_style.format(
            bg="#C62828", hover="#B71C1C", pressed="#8E0000"
        ))
        delete_btn.clicked.connect(self._delete_preset)
        buttons_layout.addWidget(delete_btn)

        presets_layout.addLayout(buttons_layout)
        layout.addWidget(presets_frame)

        self._refresh_preset_list()
    
    def _create_runtime_mode_section(self, layout):
        """Create runtime mode section."""
        runtime_label = QLabel()
        self.set_translatable_text(runtime_label, "sidebar_runtime_mode")
        runtime_label.setStyleSheet(
            "font-size: 9pt; font-weight: 600; color: #9E9E9E; "
            "padding: 2px 0; letter-spacing: 0.5px;"
        )
        layout.addWidget(runtime_label)

        runtime_frame = QFrame()
        runtime_frame.setStyleSheet(
            "QFrame { background-color: #2A2A2A; border: 1px solid #3A3A3A; "
            "border-radius: 6px; }"
        )
        runtime_layout = QVBoxLayout(runtime_frame)
        runtime_layout.setContentsMargins(8, 8, 8, 8)

        gpu_label = QLabel()
        self.set_translatable_text(gpu_label, "sidebar_gpu_mode")
        gpu_label.setStyleSheet("font-size: 9pt; color: #D0D0D0;")
        runtime_layout.addWidget(gpu_label)

        layout.addWidget(runtime_frame)

    def _create_pipeline_mode_section(self, layout):
        """Create pipeline mode dropdown (text / vision / audio)."""
        mode_label = QLabel()
        self.set_translatable_text(mode_label, "sidebar_pipeline_mode")
        mode_label.setStyleSheet(
            "font-size: 9pt; font-weight: 600; color: #9E9E9E; "
            "padding: 2px 0; letter-spacing: 0.5px;"
        )
        layout.addWidget(mode_label)

        mode_frame = QFrame()
        mode_frame.setStyleSheet(
            "QFrame { background-color: #2A2A2A; border: 1px solid #3A3A3A; "
            "border-radius: 6px; }"
        )
        mode_layout = QVBoxLayout(mode_frame)
        mode_layout.setContentsMargins(8, 10, 8, 10)
        mode_layout.setSpacing(6)

        current_mode = 'text'
        if self.config_manager:
            current_mode = self.config_manager.get_setting('pipeline.mode', 'text')

        self._pipeline_mode_values = ['text', 'vision', 'audio']
        self._pipeline_mode_tr_keys = [
            'pipeline_mode_text',
            'pipeline_mode_vision',
            'pipeline_mode_audio',
        ]

        self.pipeline_mode_combo = QComboBox()
        self.pipeline_mode_combo.setStyleSheet(
            "QComboBox { font-size: 8pt; background-color: #1E1E1E; "
            "border: 1px solid #3E3E3E; border-radius: 4px; padding: 4px 8px; color: #E0E0E0; }"
            "QComboBox:hover { border: 1px solid #5E5E5E; }"
            "QComboBox::drop-down { border: none; width: 18px; }"
            "QComboBox::down-arrow { border-left: 4px solid transparent; "
            "border-right: 4px solid transparent; border-top: 5px solid #888; margin-right: 5px; }"
        )

        for key in self._pipeline_mode_tr_keys:
            self.pipeline_mode_combo.addItem(tr(key))

        idx = self._pipeline_mode_values.index(current_mode) if current_mode in self._pipeline_mode_values else 0
        self.pipeline_mode_combo.setCurrentIndex(idx)

        self.pipeline_mode_combo.currentIndexChanged.connect(self._on_pipeline_mode_changed)

        mode_layout.addWidget(self.pipeline_mode_combo)
        layout.addWidget(mode_frame)

    def _on_pipeline_mode_changed(self, index: int):
        """Handle pipeline mode combo box change."""
        if index < 0 or index >= len(self._pipeline_mode_values):
            return
        mode = self._pipeline_mode_values[index]
        if self.config_manager:
            self.config_manager.set_setting('pipeline.mode', mode)
        self.pipelineModeChanged.emit(mode)
    

    
    def _create_metrics_section(self, layout):
        """Create metrics section."""
        metrics_label = QLabel()
        self.set_translatable_text(metrics_label, "sidebar_metrics")
        metrics_label.setStyleSheet(
            "font-size: 9pt; font-weight: 600; color: #9E9E9E; "
            "padding: 2px 0; letter-spacing: 0.5px;"
        )
        layout.addWidget(metrics_label)

        metrics_frame = QFrame()
        metrics_frame.setStyleSheet(
            "QFrame { background-color: #2A2A2A; border: 1px solid #3A3A3A; "
            "border-radius: 6px; }"
        )
        metrics_layout = QVBoxLayout(metrics_frame)
        metrics_layout.setContentsMargins(8, 8, 8, 8)
        metrics_layout.setSpacing(4)

        metric_style = "font-size: 8pt; color: #C0C0C0;"

        self.fps_label = QLabel("📊 0 FPS")
        self.fps_label.setStyleSheet(metric_style)
        metrics_layout.addWidget(self.fps_label)

        self.cpu_label = QLabel("💻 CPU: 0%")
        self.cpu_label.setStyleSheet(metric_style)
        metrics_layout.addWidget(self.cpu_label)

        self.gpu_label = QLabel("🎮 GPU: 0%")
        self.gpu_label.setStyleSheet(metric_style)
        metrics_layout.addWidget(self.gpu_label)

        self.ram_label = QLabel("💾 RAM: 0.0GB")
        self.ram_label.setStyleSheet(metric_style)
        metrics_layout.addWidget(self.ram_label)

        layout.addWidget(metrics_frame)
    
    def _create_action_buttons(self, layout):
        """Create action buttons."""
        action_btn_template = (
            "QPushButton {{ font-size: 8pt; font-weight: 600; padding: 6px 10px; "
            "border-radius: 5px; border: none; color: #FFF; min-width: 0; "
            "background-color: {bg}; }}"
            "QPushButton:hover {{ background-color: {hover}; }}"
            "QPushButton:pressed {{ background-color: {pressed}; }}"
        )

        full_test_btn = QPushButton()
        self.set_translatable_text(full_test_btn, "sidebar_full_test_btn")
        self.set_translatable_text(full_test_btn, "sidebar_full_test_tooltip", method="setToolTip")
        full_test_btn.setStyleSheet(action_btn_template.format(
            bg="#E65100", hover="#BF360C", pressed="#A63000"
        ))
        full_test_btn.clicked.connect(self.fullTestClicked.emit)
        layout.addWidget(full_test_btn)

        benchmark_btn = QPushButton()
        self.set_translatable_text(benchmark_btn, "sidebar_benchmark_btn")
        self.set_translatable_text(benchmark_btn, "sidebar_benchmark_tooltip", method="setToolTip")
        benchmark_btn.setStyleSheet(action_btn_template.format(
            bg="#43A047", hover="#388E3C", pressed="#2E7D32"
        ))
        benchmark_btn.clicked.connect(self.benchmarkClicked.emit)
        layout.addWidget(benchmark_btn)

        logs_btn = QPushButton()
        self.set_translatable_text(logs_btn, "sidebar_view_logs_btn")
        logs_btn.setStyleSheet(action_btn_template.format(
            bg="#37474F", hover="#455A64", pressed="#263238"
        ))
        logs_btn.clicked.connect(self.logsClicked.emit)
        layout.addWidget(logs_btn)

        lang_pack_btn = QPushButton()
        self.set_translatable_text(lang_pack_btn, "sidebar_language_packs_btn")
        self.set_translatable_text(lang_pack_btn, "sidebar_language_packs_tooltip", method="setToolTip")
        lang_pack_btn.setStyleSheet(action_btn_template.format(
            bg="#6A1B9A", hover="#7B1FA2", pressed="#4A148C"
        ))
        lang_pack_btn.clicked.connect(self.languagePackClicked.emit)
        layout.addWidget(lang_pack_btn)

        img_proc_btn = QPushButton()
        self.set_translatable_text(img_proc_btn, "sidebar_image_processing_btn")
        self.set_translatable_text(img_proc_btn, "sidebar_image_processing_tooltip", method="setToolTip")
        img_proc_btn.setStyleSheet(action_btn_template.format(
            bg="#00838F", hover="#00ACC1", pressed="#006064"
        ))
        img_proc_btn.clicked.connect(self.imageProcessingClicked.emit)
        layout.addWidget(img_proc_btn)
    
    def _create_languages_section(self, layout):
        """Create languages section (OCR engine display only, language config is in General tab)."""
        lang_label = QLabel()
        self.set_translatable_text(lang_label, "sidebar_languages")
        lang_label.setStyleSheet(
            "font-size: 9pt; font-weight: 600; color: #9E9E9E; "
            "padding: 2px 0; letter-spacing: 0.5px;"
        )
        layout.addWidget(lang_label)

        ocr_engine_label = QLabel()
        self.set_translatable_text(ocr_engine_label, "sidebar_ocr_engine_label")
        ocr_engine_label.setStyleSheet("font-size: 8pt; color: #888;")
        layout.addWidget(ocr_engine_label)

        self.ocr_engine_display = QLabel()
        self.set_translatable_text(self.ocr_engine_display, "sidebar_ocr_loading")
        self.ocr_engine_display.setStyleSheet(
            "font-size: 9pt; font-weight: 600; margin-left: 5px; color: #42A5F5;"
        )
        self.ocr_engine_display.setToolTip("Currently active OCR engine")
        layout.addWidget(self.ocr_engine_display)

        self.quick_ocr_switch_btn = QPushButton()
        self.set_translatable_text(self.quick_ocr_switch_btn, "sidebar_quick_switch_ocr_btn")
        self.set_translatable_text(self.quick_ocr_switch_btn, "sidebar_quick_switch_ocr_tooltip", method="setToolTip")
        self.quick_ocr_switch_btn.setStyleSheet(
            "QPushButton { font-size: 8pt; font-weight: 600; padding: 6px 10px; "
            "border-radius: 5px; border: none; color: #FFF; min-width: 0; "
            "background-color: #1976D2; }"
            "QPushButton:hover { background-color: #1E88E5; }"
            "QPushButton:pressed { background-color: #1565C0; }"
        )
        self.quick_ocr_switch_btn.clicked.connect(self.quickOcrSwitchClicked.emit)
        layout.addWidget(self.quick_ocr_switch_btn)

        layout.addSpacing(5)

        from_label = QLabel()
        self.set_translatable_text(from_label, "sidebar_ocr_detect_label")
        from_label.setStyleSheet("font-size: 8pt; color: #888;")
        layout.addWidget(from_label)

        source_lang = self.config_manager.get_setting('translation.source_language', 'en')
        source_display = self.language_map.get(source_lang, source_lang.upper())
        self.source_lang_label = QLabel(f"  {source_display}")
        self.source_lang_label.setStyleSheet("font-size: 9pt; font-weight: 600; color: #D0D0D0;")
        layout.addWidget(self.source_lang_label)

        layout.addSpacing(5)

        to_label = QLabel()
        self.set_translatable_text(to_label, "sidebar_translate_to_label")
        to_label.setStyleSheet("font-size: 8pt; color: #888;")
        layout.addWidget(to_label)

        target_lang = self.config_manager.get_setting('translation.target_language', 'de')
        target_display = self.language_map.get(target_lang, target_lang.upper())
        self.target_lang_label = QLabel(f"  {target_display}")
        self.target_lang_label.setStyleSheet("font-size: 9pt; font-weight: 600; color: #D0D0D0;")
        layout.addWidget(self.target_lang_label)
    
    # Public methods for updating sidebar state
    
    def update_status(self, message, status_type="ready"):
        """
        Update system status display.
        
        Args:
            message: Status message to display
            status_type: Type of status ('ready', 'loading', 'error')
        """
        icons = {
            "ready": "🟢",
            "loading": "🟡",
            "error": "🔴"
        }
        icon = icons.get(status_type, "🟢")
        self.status_label.setText(f"{icon}  {message}")
    
    def update_ocr_engine(self, engine_name):
        """
        Update OCR engine display.
        
        Args:
            engine_name: Name of the OCR engine
        """
        engine_display_map = {
            'easyocr': '🔍 EasyOCR',
            'tesseract': '📝 Tesseract',
            'paddleocr': '🎯 PaddleOCR',
            'onnx': '⚙️ ONNX',
            'mokuro': '📚 Mokuro',
            'vision': '👁 Vision',
            'unknown': '❓ Unknown'
        }

        key = (engine_name or "").lower()
        display_name = engine_display_map.get(key, f'🔍 {engine_name}' if engine_name else '❓ Unknown')
        self.ocr_engine_display.setText(display_name)
        self.ocr_engine_display.setToolTip(f"Currently selected: {engine_name}")
    
    def set_source_language(self, language_name):
        """
        Update source language display.
        
        Args:
            language_name: Full language name (e.g., 'English')
        """
        if hasattr(self, 'source_lang_label'):
            self.source_lang_label.setText(f"  {language_name}")
    
    def set_target_language(self, language_name):
        """
        Update target language display.
        
        Args:
            language_name: Full language name (e.g., 'German')
        """
        if hasattr(self, 'target_lang_label'):
            self.target_lang_label.setText(f"  {language_name}")
    
    def update_metrics(self, fps: float = 0.0, cpu: float = 0.0, gpu=None, memory_gb: float = 0.0):
        """
        Update metrics display with real-time values.
        
        Args:
            fps: Frames per second
            cpu: CPU usage percentage
            gpu: GPU usage percentage, or None if unavailable
            memory_gb: Memory usage in GB
        """
        self.fps_label.setText(f"📊 {fps:.1f} FPS")
        self.cpu_label.setText(f"💻 CPU: {cpu:.1f}%")
        if gpu is None:
            self.gpu_label.setText("🎮 GPU: N/A")
        else:
            self.gpu_label.setText(f"🎮 GPU: {gpu:.1f}%")
        self.ram_label.setText(f"💾 RAM: {memory_gb:.1f}GB")
    
    def set_language_lock(self, locked: bool):
        """
        Show lock indicator on the source language label.
        Only the OCR source language is locked when an engine supports a
        single language; the target language remains freely editable.
        """
        if locked:
            if hasattr(self, 'source_lang_label'):
                self.source_lang_label.setToolTip(tr("locked_to_japanese_for_mokuro"))
        else:
            if hasattr(self, 'source_lang_label'):
                self.source_lang_label.setToolTip("")
        if hasattr(self, 'target_lang_label'):
            self.target_lang_label.setToolTip("")
    
    # Preset Management Methods
    
    def _refresh_preset_list(self):
        """Refresh the preset combo box with available presets."""
        self.preset_combo.blockSignals(True)
        self.preset_combo.clear()
        
        # Get presets from config
        presets = self.config_manager.get_setting('presets', {})
        
        if presets:
            self.preset_combo.addItems(sorted(presets.keys()))
        else:
            self.preset_combo.addItem(tr("no_presets"))
        
        self.preset_combo.blockSignals(False)
    
    def _save_preset(self):
        """Save current configuration as a preset."""
        from PyQt6.QtWidgets import QInputDialog, QMessageBox
        
        # Ask for preset name
        # Generate default name based on existing presets
        existing_presets = self.config_manager.get_setting('presets', {})
        preset_count = len(existing_presets) + 1
        default_name = f"Preset {preset_count}"
        
        name, ok = QInputDialog.getText(
            self,
            tr("sidebar_save_preset_title"),
            tr("sidebar_enter_preset_name"),
            text=default_name
        )
        
        if not ok or not name.strip():
            return
        
        name = name.strip()
        
        # Collect current settings
        preset_data = {
            'description': f'Preset saved on {self._get_current_datetime()}',
            'settings': {
                # General settings
                'ui': {
                    'language': self.config_manager.get_setting('ui.language', 'en'),
                    'theme': self.config_manager.get_setting('ui.theme', 'default'),
                },
                # OCR settings
                'ocr': {
                    'engine': self.config_manager.get_setting('ocr.engine', 'easyocr'),
                    'source_language': self.config_manager.get_setting('translation.source_language', 'en'),
                    'languages': self.config_manager.get_setting('ocr.languages', []),
                },
                # Translation settings
                'translation': {
                    'target_language': self.config_manager.get_setting('translation.target_language', 'de'),
                    'engine': self.config_manager.get_setting('translation.engine', 'google_api'),
                },
                # Capture settings (including multi-monitor)
                'capture': {
                    'regions': self.config_manager.get_setting('capture.regions', []),
                    'capture_mode': self.config_manager.get_setting('capture.capture_mode', 'continuous'),
                    'capture_interval': self.config_manager.get_setting('capture.capture_interval', 1.0),
                },
                # Overlay settings
                'overlay': {
                    'enabled': self.config_manager.get_setting('overlay.enabled', True),
                    'style': self.config_manager.get_setting('overlay.style', 'default'),
                    'font_size': self.config_manager.get_setting('overlay.font_size', 14),
                    'opacity': self.config_manager.get_setting('overlay.opacity', 0.9),
                },
                # Plugin settings
                'plugins': {
                    'enabled_plugins': self.config_manager.get_setting('plugins.enabled_plugins', []),
                    'plugin_configs': self.config_manager.get_setting('plugins.plugin_configs', {}),
                },
                # Pipeline settings (optimizer plugins)
                'pipeline': {
                    'enable_optimizer_plugins': self.config_manager.get_setting('pipeline.enable_optimizer_plugins', False),
                    # Parallel processing
                    'parallel_capture': {
                        'enabled': self.config_manager.get_setting('pipeline.parallel_capture.enabled', False),
                        'workers': self.config_manager.get_setting('pipeline.parallel_capture.workers', 4),
                    },
                    'parallel_translation': {
                        'enabled': self.config_manager.get_setting('pipeline.parallel_translation.enabled', False),
                        'workers': self.config_manager.get_setting('pipeline.parallel_translation.workers', 4),
                    },
                    # Optimizer plugins
                    'plugins': {
                        'motion_tracker': {
                            'enabled': self.config_manager.get_setting('pipeline.plugins.motion_tracker.enabled', True),
                            'threshold': self.config_manager.get_setting('pipeline.plugins.motion_tracker.threshold', 10.0),
                            'smoothing': self.config_manager.get_setting('pipeline.plugins.motion_tracker.smoothing', 0.5),
                        },
                        'spell_corrector': {
                            'enabled': self.config_manager.get_setting('pipeline.plugins.spell_corrector.enabled', True),
                            'aggressive_mode': self.config_manager.get_setting('pipeline.plugins.spell_corrector.aggressive_mode', False),
                            'fix_capitalization': self.config_manager.get_setting('pipeline.plugins.spell_corrector.fix_capitalization', True),
                            'min_confidence': self.config_manager.get_setting('pipeline.plugins.spell_corrector.min_confidence', 0.5),
                        },
                        'translation_chain': {
                            'enabled': self.config_manager.get_setting('pipeline.plugins.translation_chain.enabled', False),
                            'intermediate_language': self.config_manager.get_setting('pipeline.plugins.translation_chain.intermediate_language', 'en'),
                            'quality_threshold': self.config_manager.get_setting('pipeline.plugins.translation_chain.quality_threshold', 0.7),
                            'save_all_mappings': self.config_manager.get_setting('pipeline.plugins.translation_chain.save_all_mappings', True),
                        },
                    },
                },
                # Advanced settings
                'advanced': {
                    'gpu_acceleration': self.config_manager.get_setting('advanced.gpu_acceleration', True),
                    'batch_size': self.config_manager.get_setting('advanced.batch_size', 1),
                    'thread_count': self.config_manager.get_setting('advanced.thread_count', 4),
                }
            }
        }
        
        # Save to config
        presets = self.config_manager.get_setting('presets', {})
        presets[name] = preset_data
        self.config_manager.set_setting('presets', presets)
        self.config_manager.save_config()
        
        # Refresh list
        self._refresh_preset_list()
        
        # Select the newly saved preset
        index = self.preset_combo.findText(name)
        if index >= 0:
            self.preset_combo.setCurrentIndex(index)
        
        QMessageBox.information(
            self,
            tr("preset_saved"),
            tr("sidebar_preset_saved_msg", name=name)
        )
    
    def _load_preset(self):
        """Load selected preset configuration."""
        from PyQt6.QtWidgets import QMessageBox
        
        preset_name = self.preset_combo.currentText()
        
        if not preset_name or preset_name == tr("no_presets"):
            QMessageBox.warning(
                self,
                tr("no_preset_selected"),
                tr("please_select_a_preset_to_load")
            )
            return
        
        # Get preset data
        presets = self.config_manager.get_setting('presets', {})
        preset_data = presets.get(preset_name)
        
        if not preset_data:
            QMessageBox.critical(
                self,
                tr("preset_not_found"),
                tr("sidebar_preset_not_found_msg", name=preset_name)
            )
            return
        
        # Confirm load
        reply = QMessageBox.question(
            self,
            tr("sidebar_load_preset_title"),
            tr("sidebar_load_preset_confirm", name=preset_name),
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            QMessageBox.StandardButton.No
        )
        
        if reply != QMessageBox.StandardButton.Yes:
            return
        
        # Apply preset settings (recursively flatten nested dicts to dotted keys)
        settings = preset_data.get('settings', {})
        
        def _apply_settings(prefix, data):
            """Recursively apply nested settings as dotted keys."""
            for key, value in data.items():
                full_key = f'{prefix}.{key}' if prefix else key
                if isinstance(value, dict):
                    _apply_settings(full_key, value)
                else:
                    self.config_manager.set_setting(full_key, value)
        
        _apply_settings('', settings)
        
        # Save config
        self.config_manager.save_config()
        
        # Emit signal to notify main window
        self.presetLoaded.emit(preset_name)
        
        QMessageBox.information(
            self,
            tr("preset_loaded"),
            tr("sidebar_preset_loaded_msg", name=preset_name)
        )
    
    def _delete_preset(self):
        """Delete selected preset."""
        from PyQt6.QtWidgets import QMessageBox
        
        preset_name = self.preset_combo.currentText()
        
        if not preset_name or preset_name == tr("no_presets"):
            QMessageBox.warning(
                self,
                tr("no_preset_selected"),
                tr("please_select_a_preset_to_delete")
            )
            return
        
        # Confirm deletion
        reply = QMessageBox.question(
            self,
            tr("sidebar_delete_preset_title"),
            tr("sidebar_delete_preset_confirm", name=preset_name),
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            QMessageBox.StandardButton.No
        )
        
        if reply != QMessageBox.StandardButton.Yes:
            return
        
        # Delete preset
        presets = self.config_manager.get_setting('presets', {})
        if preset_name in presets:
            del presets[preset_name]
            self.config_manager.set_setting('presets', presets)
            self.config_manager.save_config()
        
        # Refresh list
        self._refresh_preset_list()
        
        QMessageBox.information(
            self,
            tr("sidebar_preset_deleted_title"),
            tr("sidebar_preset_deleted_msg", name=preset_name)
        )
    
    def _get_current_datetime(self):
        """Get current datetime as formatted string."""
        from datetime import datetime
        return datetime.now().strftime("%Y-%m-%d %H:%M:%S")
