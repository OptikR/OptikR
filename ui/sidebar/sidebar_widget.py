"""
Sidebar Widget Module

Left sidebar displaying system status, metrics, and language controls.

Author: OptikR Team
Date: 2024
"""

from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QComboBox, QRadioButton, QFrame
)
from PyQt6.QtCore import pyqtSignal


class SidebarWidget(QWidget):
    """
    Left sidebar widget with system status and controls.
    
    Signals:
        performanceClicked: Emitted when Performance button clicked
        logsClicked: Emitted when View Logs button clicked
        quickOcrSwitchClicked: Emitted when Quick Switch OCR button clicked
        sourceLanguageChanged: Emitted when source language changed (str: language_name)
        targetLanguageChanged: Emitted when target language changed (str: language_name)
    """
    
    # Signals
    performanceClicked = pyqtSignal()
    logsClicked = pyqtSignal()
    quickOcrSwitchClicked = pyqtSignal()
    fullTestClicked = pyqtSignal()
    languagePackClicked = pyqtSignal()  # NEW: Language pack manager
    sourceLanguageChanged = pyqtSignal(str)
    targetLanguageChanged = pyqtSignal(str)
    presetLoaded = pyqtSignal(str)  # Emitted when preset is loaded (preset_name)
    
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
        # Get sidebar width from config (increased to prevent text cutoff)
        sidebar_width = self.config_manager.get_setting('ui.sidebar_width', 220)
        
        self.setObjectName("sidebar")
        self.setFixedWidth(sidebar_width)
        self.setStyleSheet("QWidget#sidebar { background-color: #E8E8E8; border-right: 1px solid #D0D0D0; }")
        
        layout = QVBoxLayout(self)
        layout.setContentsMargins(10, 10, 10, 10)
        layout.setSpacing(8)
        
        # System Status section
        self._create_system_status_section(layout)
        
        # Presets section (NEW)
        self._create_presets_section(layout)
        
        # Runtime Mode section
        self._create_runtime_mode_section(layout)
        
        # Metrics section
        self._create_metrics_section(layout)
        
        # Action buttons
        self._create_action_buttons(layout)
        
        # Languages section
        self._create_languages_section(layout)
        
        # Overlay section
        self._create_overlay_section(layout)
        
        layout.addStretch()
    
    def _create_system_status_section(self, layout):
        """Create system status section."""
        status_label = QLabel("● System Status")
        status_label.setProperty("class", "sidebar-label")
        layout.addWidget(status_label)
        
        status_frame = QFrame()
        status_frame.setProperty("class", "card")
        status_layout = QVBoxLayout(status_frame)
        status_layout.setContentsMargins(6, 6, 6, 6)
        status_layout.setSpacing(2)
        
        status_item = QLabel("● Status")
        status_item.setStyleSheet("font-size: 8pt;")
        status_layout.addWidget(status_item)
        
        # Status indicator (will be updated during startup)
        self.status_label = QLabel("🟡  Initializing...")
        self.status_label.setStyleSheet("font-size: 8pt; margin-left: 10px;")
        status_layout.addWidget(self.status_label)
        
        layout.addWidget(status_frame)
    
    def _create_presets_section(self, layout):
        """Create presets section for saving/loading configurations."""
        presets_label = QLabel("● Presets")
        presets_label.setProperty("class", "sidebar-label")
        layout.addWidget(presets_label)
        
        presets_frame = QFrame()
        presets_frame.setProperty("class", "card")
        presets_layout = QVBoxLayout(presets_frame)
        presets_layout.setContentsMargins(6, 6, 6, 6)
        presets_layout.setSpacing(4)
        
        # Preset selector
        self.preset_combo = QComboBox()
        self.preset_combo.setToolTip("Select a preset configuration")
        self.preset_combo.setStyleSheet("font-size: 8pt;")
        presets_layout.addWidget(self.preset_combo)
        
        # Buttons row
        buttons_layout = QHBoxLayout()
        buttons_layout.setSpacing(4)
        
        # Load button
        load_btn = QPushButton("Load")
        load_btn.setProperty("class", "action")
        load_btn.setStyleSheet("font-size: 7pt; padding: 2px;")
        load_btn.setToolTip("Load selected preset")
        load_btn.clicked.connect(self._load_preset)
        buttons_layout.addWidget(load_btn)
        
        # Save button
        save_btn = QPushButton("Save")
        save_btn.setProperty("class", "action")
        save_btn.setStyleSheet("font-size: 7pt; padding: 2px;")
        save_btn.setToolTip("Save current settings as preset")
        save_btn.clicked.connect(self._save_preset)
        buttons_layout.addWidget(save_btn)
        
        # Delete button
        delete_btn = QPushButton("Del")
        delete_btn.setProperty("class", "action")
        delete_btn.setStyleSheet("font-size: 7pt; padding: 2px; background-color: #f44336;")
        delete_btn.setToolTip("Delete selected preset")
        delete_btn.clicked.connect(self._delete_preset)
        buttons_layout.addWidget(delete_btn)
        
        presets_layout.addLayout(buttons_layout)
        
        layout.addWidget(presets_frame)
        
        # Load available presets
        self._refresh_preset_list()
    
    def _create_runtime_mode_section(self, layout):
        """Create runtime mode section."""
        runtime_label = QLabel("● Runtime Mode")
        runtime_label.setProperty("class", "sidebar-label")
        layout.addWidget(runtime_label)
        
        runtime_frame = QFrame()
        runtime_frame.setProperty("class", "card")
        runtime_layout = QVBoxLayout(runtime_frame)
        runtime_layout.setContentsMargins(6, 6, 6, 6)
        
        gpu_label = QLabel("■  GPU Mode")
        gpu_label.setStyleSheet("font-size: 9pt;")
        runtime_layout.addWidget(gpu_label)
        
        layout.addWidget(runtime_frame)
    

    
    def _create_metrics_section(self, layout):
        """Create metrics section."""
        metrics_label = QLabel("● Metrics")
        metrics_label.setProperty("class", "sidebar-label")
        layout.addWidget(metrics_label)
        
        metrics_frame = QFrame()
        metrics_frame.setProperty("class", "card")
        metrics_layout = QVBoxLayout(metrics_frame)
        metrics_layout.setContentsMargins(6, 6, 6, 6)
        metrics_layout.setSpacing(4)
        
        # Store labels as instance variables for updating
        self.fps_label = QLabel("📊 0 FPS")
        self.fps_label.setStyleSheet("font-size: 8pt;")
        metrics_layout.addWidget(self.fps_label)
        
        self.cpu_label = QLabel("💻 CPU: 0%")
        self.cpu_label.setStyleSheet("font-size: 8pt;")
        metrics_layout.addWidget(self.cpu_label)
        
        self.gpu_label = QLabel("🎮 GPU: 0%")
        self.gpu_label.setStyleSheet("font-size: 8pt;")
        metrics_layout.addWidget(self.gpu_label)
        
        self.ram_label = QLabel("💾 RAM: 0.0GB")
        self.ram_label.setStyleSheet("font-size: 8pt;")
        metrics_layout.addWidget(self.ram_label)
        
        layout.addWidget(metrics_frame)
    
    def _create_action_buttons(self, layout):
        """Create action buttons."""
        # Full Test button (prominent)
        full_test_btn = QPushButton("🧪 Full Test")
        full_test_btn.setProperty("class", "action")
        full_test_btn.setStyleSheet("background-color: #FF9800; font-weight: bold;")
        full_test_btn.setToolTip("Test all pipeline components (Capture, OCR, Translation)")
        full_test_btn.clicked.connect(self.fullTestClicked.emit)
        layout.addWidget(full_test_btn)
        
        # View Logs button
        logs_btn = QPushButton("View Logs")
        logs_btn.setProperty("class", "action")
        logs_btn.clicked.connect(self.logsClicked.emit)
        layout.addWidget(logs_btn)
        
        # Language Pack Manager button (NEW)
        lang_pack_btn = QPushButton("🌐 Language Packs")
        lang_pack_btn.setProperty("class", "action")
        lang_pack_btn.setStyleSheet("background-color: #9C27B0; color: white; font-weight: bold;")
        lang_pack_btn.setToolTip("Manage language packs - Import/Export translations")
        lang_pack_btn.clicked.connect(self.languagePackClicked.emit)
        layout.addWidget(lang_pack_btn)
    
    def _create_languages_section(self, layout):
        """Create languages section."""
        lang_label = QLabel("● Languages")
        lang_label.setProperty("class", "sidebar-label")
        layout.addWidget(lang_label)
        
        # Current OCR Engine display
        ocr_engine_label = QLabel("OCR Engine:")
        ocr_engine_label.setStyleSheet("font-size: 8pt; color: #666666;")
        layout.addWidget(ocr_engine_label)
        
        self.ocr_engine_display = QLabel("🔍 Loading...")
        self.ocr_engine_display.setStyleSheet("font-size: 9pt; font-weight: 600; margin-left: 5px; color: #2196F3;")
        self.ocr_engine_display.setToolTip("Currently active OCR engine")
        layout.addWidget(self.ocr_engine_display)
        
        # Quick OCR Engine Switch button
        self.quick_ocr_switch_btn = QPushButton("⚡ Quick Switch OCR")
        self.quick_ocr_switch_btn.setProperty("class", "action")
        self.quick_ocr_switch_btn.setToolTip("Quickly switch between installed OCR engines")
        self.quick_ocr_switch_btn.clicked.connect(self.quickOcrSwitchClicked.emit)
        layout.addWidget(self.quick_ocr_switch_btn)
        
        layout.addSpacing(5)
        
        # Source language
        from_label = QLabel("OCR (Detect):")
        from_label.setStyleSheet("font-size: 8pt; color: #666666;")
        from_label.setToolTip("Language to recognize in images (OCR)")
        layout.addWidget(from_label)
        
        # Get available languages from config (as codes)
        language_codes = self.config_manager.get_setting('ocr.languages', 
            ["en", "de", "es", "fr", "ja", "zh-CN", "ko"])
        
        # Convert codes to full names
        available_languages = [self.language_map.get(code, code.upper()) for code in language_codes]
        
        self.source_combo = QComboBox()
        self.source_combo.addItems(available_languages)
        self.source_combo.setToolTip("Select the language to recognize in captured images")
        self.source_combo.currentTextChanged.connect(self.sourceLanguageChanged.emit)
        layout.addWidget(self.source_combo)
        
        layout.addSpacing(5)
        
        # Target language
        to_label = QLabel("Translate To:")
        to_label.setStyleSheet("font-size: 8pt; color: #666666;")
        to_label.setToolTip("Target language for translation")
        layout.addWidget(to_label)
        
        self.target_combo = QComboBox()
        self.target_combo.addItems(available_languages)
        self.target_combo.setToolTip("Select the target language for translation")
        self.target_combo.currentTextChanged.connect(self.targetLanguageChanged.emit)
        layout.addWidget(self.target_combo)
    
    def _create_overlay_section(self, layout):
        """Create overlay section."""
        overlay_label = QLabel("● Overlay")
        overlay_label.setProperty("class", "sidebar-label")
        layout.addWidget(overlay_label)
        
        visible_radio = QRadioButton("Visible")
        visible_radio.setChecked(True)
        visible_radio.setStyleSheet("font-size: 8pt;")
        layout.addWidget(visible_radio)
        
        style_label = QLabel("⚙ Style: Default")
        style_label.setStyleSheet("font-size: 8pt;")
        layout.addWidget(style_label)
    
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
        
        # If message contains pipeline stage info, show generic "Loading OCR..." in status
        # and display the actual stage in main window's status bar
        if message.startswith("["):
            # Show generic loading message in status line
            self.status_label.setText(f"{icon}  Loading OCR...")
            # Display actual stage in main window's status bar
            self.update_pipeline_stage(message)
        else:
            # Normal status message
            self.status_label.setText(f"{icon}  {message}")
            
            # Clear pipeline stages when ready
            if status_type == "ready":
                self.update_pipeline_stage("")
    
    def update_pipeline_stage(self, stage_message):
        """
        Update pipeline stage display in main window's status bar.
        
        Args:
            stage_message: Pipeline stage message (e.g., "[1/5] Discovering OCR plugins...")
        """
        # Update parent window's pipeline stages label if it exists
        if hasattr(self.parent(), 'pipeline_stages_label'):
            if stage_message:
                self.parent().pipeline_stages_label.setText(stage_message)
            else:
                self.parent().pipeline_stages_label.setText("")
    
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
            'manga_ocr': '📚 Manga OCR',
            'unknown': '❓ Unknown'
        }
        
        display_name = engine_display_map.get(engine_name.lower(), f'🔍 {engine_name}')
        self.ocr_engine_display.setText(display_name)
        self.ocr_engine_display.setToolTip(f"Currently selected: {engine_name}")
    
    def set_source_language(self, language_name):
        """
        Set source language combo box.
        
        Args:
            language_name: Full language name (e.g., 'English')
        """
        index = self.source_combo.findText(language_name)
        if index >= 0:
            self.source_combo.blockSignals(True)
            self.source_combo.setCurrentIndex(index)
            self.source_combo.blockSignals(False)
    
    def set_target_language(self, language_name):
        """
        Set target language combo box.
        
        Args:
            language_name: Full language name (e.g., 'German')
        """
        index = self.target_combo.findText(language_name)
        if index >= 0:
            self.target_combo.blockSignals(True)
            self.target_combo.setCurrentIndex(index)
            self.target_combo.blockSignals(False)
    
    def get_source_language(self):
        """Get currently selected source language."""
        return self.source_combo.currentText()
    
    def get_target_language(self):
        """Get currently selected target language."""
        return self.target_combo.currentText()
    
    def update_metrics(self, fps: float = 0.0, cpu: float = 0.0, gpu: float = 0.0, memory_gb: float = 0.0):
        """
        Update metrics display with real-time values.
        
        Args:
            fps: Frames per second
            cpu: CPU usage percentage
            gpu: GPU usage percentage
            memory_gb: Memory usage in GB
        """
        self.fps_label.setText(f"📊 {fps:.1f} FPS")
        self.cpu_label.setText(f"💻 CPU: {cpu:.1f}%")
        self.gpu_label.setText(f"🎮 GPU: {gpu:.1f}%")
        self.ram_label.setText(f"💾 RAM: {memory_gb:.1f}GB")
    
    def set_language_lock(self, locked: bool):
        """
        Lock or unlock language selection dropdowns.
        Used when Manga OCR is selected (locks to Japanese → English).
        
        Args:
            locked: True to disable dropdowns, False to enable
        """
        self.source_combo.setEnabled(not locked)
        self.target_combo.setEnabled(not locked)
        
        if locked:
            # Add tooltip explaining why locked
            self.source_combo.setToolTip("🔒 Locked to Japanese for Manga OCR")
            self.target_combo.setToolTip("🔒 Locked to English for Manga OCR")
        else:
            # Restore original tooltips
            self.source_combo.setToolTip("Select the language to recognize in captured images")
            self.target_combo.setToolTip("Select the target language for translation")
    
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
            self.preset_combo.addItem("No presets")
        
        self.preset_combo.blockSignals(False)
    
    def _save_preset(self):
        """Save current configuration as a preset."""
        from PyQt6.QtWidgets import QInputDialog, QMessageBox
        
        # Ask for preset name
        # Generate default name based on existing presets
        existing_presets = self.config_manager.get_setting('presets.saved', {})
        preset_count = len(existing_presets) + 1
        default_name = f"Preset {preset_count}"
        
        name, ok = QInputDialog.getText(
            self,
            "Save Preset",
            "Enter preset name:",
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
                    'source_language': self.config_manager.get_setting('ocr.source_language', 'en'),
                    'languages': self.config_manager.get_setting('ocr.languages', []),
                },
                # Translation settings
                'translation': {
                    'target_language': self.config_manager.get_setting('translation.target_language', 'en'),
                    'engine': self.config_manager.get_setting('translation.engine', 'google'),
                },
                # Capture settings (including multi-monitor)
                'capture': {
                    'regions': self.config_manager.get_setting('capture.regions', []),
                    'active_region_ids': self.config_manager.get_setting('capture.active_region_ids', []),
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
                    'enable_optimizer_plugins': self.config_manager.get_setting('pipeline.enable_optimizer_plugins', True),
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
                        'text_validator': {
                            'min_confidence': self.config_manager.get_setting('pipeline.plugins.text_validator.min_confidence', 0.3),
                            'enable_smart_grammar': self.config_manager.get_setting('pipeline.plugins.text_validator.enable_smart_grammar', False),
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
            "Preset Saved",
            f"Preset '{name}' has been saved successfully!\n\n"
            f"Includes:\n"
            f"• OCR engine and languages\n"
            f"• Translation settings\n"
            f"• Pipeline configuration (plugins, async mode)\n"
            f"• Multi-monitor capture regions\n"
            f"• Overlay configuration\n"
            f"• Plugin settings\n"
            f"• Performance settings"
        )
    
    def _load_preset(self):
        """Load selected preset configuration."""
        from PyQt6.QtWidgets import QMessageBox
        
        preset_name = self.preset_combo.currentText()
        
        if not preset_name or preset_name == "No presets":
            QMessageBox.warning(
                self,
                "No Preset Selected",
                "Please select a preset to load."
            )
            return
        
        # Get preset data
        presets = self.config_manager.get_setting('presets', {})
        preset_data = presets.get(preset_name)
        
        if not preset_data:
            QMessageBox.critical(
                self,
                "Preset Not Found",
                f"Preset '{preset_name}' not found."
            )
            return
        
        # Confirm load
        reply = QMessageBox.question(
            self,
            "Load Preset",
            f"Load preset '{preset_name}'?\n\n"
            f"This will apply all saved settings including:\n"
            f"• OCR engine and languages\n"
            f"• Translation settings\n"
            f"• Pipeline mode (sequential/async)\n"
            f"• Optimizer plugins configuration\n"
            f"• Multi-monitor capture regions\n"
            f"• Overlay configuration\n"
            f"• Performance settings\n\n"
            f"Current unsaved changes will be lost.",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            QMessageBox.StandardButton.No
        )
        
        if reply != QMessageBox.StandardButton.Yes:
            return
        
        # Apply preset settings
        settings = preset_data.get('settings', {})
        
        for category, category_settings in settings.items():
            if isinstance(category_settings, dict):
                for key, value in category_settings.items():
                    self.config_manager.set_setting(f'{category}.{key}', value)
            else:
                self.config_manager.set_setting(category, category_settings)
        
        # Save config
        self.config_manager.save_config()
        
        # Emit signal to notify main window
        self.presetLoaded.emit(preset_name)
        
        QMessageBox.information(
            self,
            "Preset Loaded",
            f"Preset '{preset_name}' has been loaded!\n\n"
            f"The application will reload with the new settings."
        )
        
        # Request application reload
        if self.parent():
            self.parent().reload_all_settings()
    
    def _delete_preset(self):
        """Delete selected preset."""
        from PyQt6.QtWidgets import QMessageBox
        
        preset_name = self.preset_combo.currentText()
        
        if not preset_name or preset_name == "No presets":
            QMessageBox.warning(
                self,
                "No Preset Selected",
                "Please select a preset to delete."
            )
            return
        
        # Confirm deletion
        reply = QMessageBox.question(
            self,
            "Delete Preset",
            f"Are you sure you want to delete preset '{preset_name}'?\n\n"
            f"This action cannot be undone.",
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
            "Preset Deleted",
            f"Preset '{preset_name}' has been deleted."
        )
    
    def _get_current_datetime(self):
        """Get current datetime as formatted string."""
        from datetime import datetime
        return datetime.now().strftime("%Y-%m-%d %H:%M:%S")
