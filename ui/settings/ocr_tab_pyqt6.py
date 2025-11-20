"""
OCR Settings Tab - PyQt6 Implementation (Refactored)
OCR engine selection, language packs, and configuration.
Uses modular manager classes for better organization.
"""

from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QGroupBox,
    QLabel, QRadioButton, QCheckBox, QPushButton,
    QButtonGroup, QListWidget, QSlider, QListWidgetItem
)
from PyQt6.QtCore import Qt, pyqtSignal

# Import custom scroll area
from .scroll_area_no_wheel import ScrollAreaNoWheel

# Import translation system
from app.translations import TranslatableMixin

# Import manager classes
from .ocr_engine_manager import OCREngineManager
from .ocr_language_manager import OCRLanguageManager
from .ocr_test_manager import OCRTestManager


class OCRSettingsTab(TranslatableMixin, QWidget):
    """OCR settings including engine selection, languages, and configuration."""
    
    # Signal emitted when any setting changes
    settingChanged = pyqtSignal()
    
    def __init__(self, config_manager=None, parent=None):
        """Initialize the OCR settings tab."""
        super().__init__(parent)
        
        self.config_manager = config_manager
        self.pipeline = None  # Will be set by parent window
        
        # Track original loaded state to detect real changes
        self._original_state = {}
        
        # Initialize manager classes
        self.engine_manager = OCREngineManager(parent=self)
        self.language_manager = OCRLanguageManager(parent=self)
        self.test_manager = OCRTestManager(parent=self)
        
        # OCR engine widgets (dynamic)
        self.engine_radios = {}  # Store engine radio buttons dynamically
        self.engine_button_group = None
        
        # Language pack widgets
        self.language_list = None
        self.add_language_btn = None
        self.remove_language_btn = None
        
        # Configuration widgets
        self.confidence_slider = None
        self.confidence_value_label = None
        
        # Test buttons
        self.quick_test_btn = None
        self.test_ocr_btn = None
        
        # Initialize plugin JSONs on startup
        self.engine_manager.ensure_plugin_jsons_exist()
        
        # Initialize UI
        self._init_ui()
        
        # Update engine statuses after UI is created
        from PyQt6.QtCore import QTimer
        QTimer.singleShot(1000, self._update_engine_statuses)
    
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
        self._create_engine_selection_section(content_layout)
        self._create_language_pack_section(content_layout)
        self._create_configuration_section(content_layout)
        self._create_test_section(content_layout)
        
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
        
        # OCR engine
        for engine_name, radio in self.engine_radios.items():
            if radio.isChecked():
                state['ocr_engine'] = engine_name
                break
        
        # Confidence threshold
        if self.confidence_slider:
            state['confidence'] = self.confidence_slider.value()
        
        # Languages (if applicable)
        if self.language_list:
            languages = []
            for i in range(self.language_list.count()):
                languages.append(self.language_list.item(i).text())
            state['languages'] = tuple(sorted(languages))  # tuple for hashability
        
        return state
    
    def on_change(self):
        """Called when any setting changes - always emits signal for main window to check."""
        # Always emit the signal - let the main window decide if there are actual changes
        self.settingChanged.emit()
    
    def on_engine_radio_changed(self):
        """Called when engine radio button changes."""
        # Check if Manga OCR is selected (check dynamically)
        selected_engine = self.get_selected_engine()
        is_manga_ocr = selected_engine and selected_engine.lower() == 'manga_ocr'
        
        if is_manga_ocr:
            self._auto_set_manga_languages()
            self._lock_languages_for_manga_ocr(True)
        else:
            self._lock_languages_for_manga_ocr(False)
        
        # Update language pack info based on selected engine
        self._update_language_pack_info()
        
        self.on_change()
    
    def _update_language_pack_info(self):
        """Update language pack information based on selected OCR engine."""
        selected_engine = self.get_selected_engine()
        if not selected_engine or not hasattr(self, 'lang_info_label'):
            return
        
        engine_lower = selected_engine.lower()
        
        # Define which engines use language packs
        language_pack_info = {
            'easyocr': ('✓ EasyOCR uses language packs', 
                       'Language models are downloaded automatically when first used for each language.'),
            'manga_ocr': ('✗ Manga OCR does not use language packs', 
                         'Manga OCR is specialized for Japanese only and has built-in language support.'),
            'paddleocr': ('✓ PaddleOCR uses language packs', 
                         'Language models are downloaded automatically when first used for each language.'),
            'tesseract': ('✓ Tesseract OCR uses language packs', 
                         'Language data must be installed separately. Download from: https://github.com/tesseract-ocr/tessdata')
        }
        
        if engine_lower in language_pack_info:
            title, description = language_pack_info[engine_lower]
            self.lang_info_label.setText(f"<b>{title}</b><br>{description}")
        else:
            self.lang_info_label.setText("Language pack support varies by OCR engine.")
    
    def _auto_set_manga_languages(self):
        """Automatically set languages to Japanese → English for Manga OCR."""
        try:
            # Set source language to Japanese
            self.config_manager.set_setting('translation.source_language', 'ja')
            
            # Set target language to English
            self.config_manager.set_setting('translation.target_language', 'en')
            
            # Update parent window's sidebar if it exists
            parent = self.parent()
            while parent:
                if hasattr(parent, 'sidebar'):
                    parent.sidebar.set_source_language('Japanese')
                    parent.sidebar.set_target_language('English')
                    break
                parent = parent.parent()
            
            # Update General Tab if it exists
            parent = self.parent()
            while parent:
                if hasattr(parent, 'general_tab'):
                    general_tab = parent.general_tab
                    if general_tab:
                        # Find and set Japanese
                        ja_index = general_tab.source_lang_combo.findText('Japanese')
                        if ja_index >= 0:
                            general_tab.source_lang_combo.blockSignals(True)
                            general_tab.source_lang_combo.setCurrentIndex(ja_index)
                            general_tab.source_lang_combo.blockSignals(False)
                        
                        # Find and set English
                        en_index = general_tab.target_lang_combo.findText('English')
                        if en_index >= 0:
                            general_tab.target_lang_combo.blockSignals(True)
                            general_tab.target_lang_combo.setCurrentIndex(en_index)
                            general_tab.target_lang_combo.blockSignals(False)
                    break
                parent = parent.parent()
            
            print("[OCR Tab] Auto-set languages: Japanese → English for Manga OCR")
            
        except Exception as e:
            print(f"[OCR Tab] Failed to auto-set languages: {e}")
    
    def _lock_languages_for_manga_ocr(self, lock: bool):
        """Lock or unlock language selection when Manga OCR is selected.
        
        Args:
            lock: True to lock languages (disable dropdowns), False to unlock
        """
        try:
            # Update parent window's sidebar if it exists
            parent = self.parent()
            while parent:
                if hasattr(parent, 'sidebar'):
                    parent.sidebar.set_language_lock(lock)
                    break
                parent = parent.parent()
            
            # Update General Tab if it exists
            parent = self.parent()
            while parent:
                if hasattr(parent, 'general_tab'):
                    general_tab = parent.general_tab
                    if general_tab:
                        general_tab.set_language_lock(lock)
                    break
                parent = parent.parent()
            
            if lock:
                print("[OCR Tab] Locked languages to Japanese → English for Manga OCR")
            else:
                print("[OCR Tab] Unlocked language selection")
            
        except Exception as e:
            print(f"[OCR Tab] Failed to lock/unlock languages: {e}")

    
    def _create_engine_selection_section(self, parent_layout):
        """Create OCR engine selection section with dynamic engine discovery."""
        group = QGroupBox()
        self.set_translatable_text(group, "ocr_ocr_engine_selection_section")
        layout = QVBoxLayout(group)
        layout.setSpacing(12)
        layout.setContentsMargins(15, 20, 15, 15)
        
        # Engine selection label
        engine_label = self._create_label("", bold=True)
        self.set_translatable_text(engine_label, "ocr_select_engine_label")
        layout.addWidget(engine_label)
        
        # Create button group for radio buttons
        self.engine_button_group = QButtonGroup()
        
        # Get available engines dynamically from pipeline
        available_engines = self._get_available_engines()
        
        if not available_engines:
            # No engines found - show warning
            no_engines_label = QLabel()
            self.set_translatable_text(no_engines_label, "ocr_no_engines_warning")
            no_engines_label.setStyleSheet("color: #FF9800; font-size: 10pt; padding: 10px;")
            layout.addWidget(no_engines_label)
        else:
            # Engine info (display names and descriptions)
            engine_info = {
                'easyocr': ('🔍 EasyOCR', 'Multi-language support with deep learning'),
                'easyocr_gpu': ('🔍 EasyOCR', 'Multi-language support with deep learning'),
                'tesseract': ('📝 Tesseract OCR (CPU only)', 'Fast and lightweight, good for printed text (requires separate installation)'),
                'paddleocr': ('🎯 PaddleOCR', 'High accuracy Chinese/multilingual OCR'),
                'onnx': ('⚙️ ONNX Runtime', 'Optimized cross-platform inference'),
                'manga_ocr': ('📚 Manga OCR', 'Specialized for Japanese manga and comics')
            }
            
            # Get current engine
            current_engine = self.config_manager.get_setting('ocr.engine', 'easyocr') if self.config_manager else 'easyocr'
            
            # Create radio buttons for each discovered engine
            for button_id, engine in enumerate(available_engines):
                engine_lower = engine.lower()
                display_name, description = engine_info.get(engine_lower, (engine, 'OCR engine'))
                
                # Engine layout
                engine_layout = QHBoxLayout()
                engine_layout.setSpacing(10)
                
                # Radio button
                radio = QRadioButton(display_name)
                radio.toggled.connect(self.on_change)
                radio.toggled.connect(self.on_engine_radio_changed)
                self.engine_button_group.addButton(radio, button_id)
                self.engine_radios[engine] = radio
                engine_layout.addWidget(radio)
                
                # Check if this is the current engine
                if engine_lower == current_engine.lower():
                    radio.setChecked(True)
                
                # Status label
                status_label = self.engine_manager.create_status_label("not_loaded")
                self.engine_manager.register_status_label(engine_lower, status_label)
                engine_layout.addWidget(status_label)
                
                engine_layout.addStretch()
                layout.addLayout(engine_layout)
                
                # Description
                desc = QLabel(f"  • {description}")
                desc.setStyleSheet("color: #666666; font-size: 8pt; margin-left: 20px; margin-bottom: 5px;")
                layout.addWidget(desc)
        
        # Note about engine selection
        note_label = QLabel()
        self.set_translatable_text(note_label, "ocr_engines_note")
        note_label.setWordWrap(True)
        note_label.setStyleSheet("color: #2196F3; font-size: 9pt; margin-top: 10px;")
        layout.addWidget(note_label)
        
        parent_layout.addWidget(group)
    
    def _get_available_engines(self):
        """Get list of available OCR engines from pipeline."""
        # Try to get from parent window's pipeline first (most accurate)
        parent = self.parent()
        while parent:
            if hasattr(parent, 'pipeline') and parent.pipeline:
                try:
                    engines = parent.pipeline.get_available_ocr_engines()
                    if engines:
                        print(f"[OCR Tab] Discovered {len(engines)} OCR engines: {engines}")
                        return engines
                except Exception as e:
                    print(f"[OCR Tab] Could not get engines from pipeline: {e}")
                break
            parent = parent.parent()
        
        # Fallback: return empty list (will show warning message)
        print("[OCR Tab] No pipeline available yet - engines will be discovered later")
        return []

    
    def _create_language_pack_section(self, parent_layout):
        """Create language pack management section."""
        group = QGroupBox()
        self.set_translatable_text(group, "ocr_language_packs_section")
        layout = QVBoxLayout(group)
        layout.setSpacing(10)
        layout.setContentsMargins(15, 20, 15, 15)
        
        # Info label about which engines use language packs
        self.lang_info_label = QLabel()
        self.lang_info_label.setWordWrap(True)
        self.lang_info_label.setStyleSheet("color: #2196F3; font-size: 9pt; margin-bottom: 10px; padding: 8px; "
                                           "background-color: #1E3A4F; border-left: 3px solid #4A9EFF; border-radius: 3px;")
        layout.addWidget(self.lang_info_label)
        
        # Language pack label
        lang_label = self._create_label("", bold=True)
        self.set_translatable_text(lang_label, "ocr_installed_languages_label")
        layout.addWidget(lang_label)
        
        # Language list widget
        self.language_list = QListWidget()
        self.language_list.setMaximumHeight(150)
        self.language_list.setSelectionMode(QListWidget.SelectionMode.SingleSelection)
        
        # Add default languages (English first as it's the most common)
        default_languages = [
            "English (en)",
            "Japanese (ja)",
            "German (de)",
            "Spanish (es)",
            "French (fr)",
            "Chinese Simplified (zh-CN)",
            "Korean (ko)"
        ]
        
        for lang in default_languages:
            item = QListWidgetItem(lang)
            self.language_list.addItem(item)
        
        layout.addWidget(self.language_list)
        
        # Button layout for language management
        button_layout = QHBoxLayout()
        button_layout.setSpacing(10)
        
        self.add_language_btn = QPushButton()
        self.set_translatable_text(self.add_language_btn, "ocr_add_language_button")
        self.add_language_btn.setProperty("class", "action")
        self.add_language_btn.setToolTip("Add a new language to the list")
        self.add_language_btn.clicked.connect(lambda: self.language_manager.add_language(self.language_list))
        button_layout.addWidget(self.add_language_btn)
        
        self.remove_language_btn = QPushButton()
        self.set_translatable_text(self.remove_language_btn, "ocr_remove_language_button")
        self.remove_language_btn.setProperty("class", "action")
        self.remove_language_btn.setToolTip("Remove selected language from the list")
        self.remove_language_btn.clicked.connect(lambda: self.language_manager.remove_language(self.language_list))
        button_layout.addWidget(self.remove_language_btn)
        
        download_btn = QPushButton()
        self.set_translatable_text(download_btn, "ocr_download_packs_button")
        download_btn.setProperty("class", "action")
        download_btn.setToolTip("Download language packs for selected engines")
        download_btn.clicked.connect(self.language_manager.show_selective_download_dialog)
        button_layout.addWidget(download_btn)
        
        button_layout.addStretch()
        layout.addLayout(button_layout)
        
        # Help text
        help_label = QLabel()
        self.set_translatable_text(help_label, "ocr_lang_packs_help")
        help_label.setWordWrap(True)
        help_label.setStyleSheet("color: #666666; font-size: 9pt; margin-top: 5px;")
        layout.addWidget(help_label)
        
        parent_layout.addWidget(group)
    
    def _create_configuration_section(self, parent_layout):
        """Create OCR configuration section."""
        group = QGroupBox()
        self.set_translatable_text(group, "ocr_ocr_configuration_section")
        layout = QVBoxLayout(group)
        layout.setSpacing(12)
        layout.setContentsMargins(15, 20, 15, 15)
        
        # Confidence threshold slider
        conf_label = self._create_label("", bold=True)
        self.set_translatable_text(conf_label, "ocr_confidence_threshold_label")
        layout.addWidget(conf_label)
        
        conf_layout = QHBoxLayout()
        conf_layout.setSpacing(10)
        
        self.confidence_slider = QSlider(Qt.Orientation.Horizontal)
        self.confidence_slider.setRange(0, 100)
        self.confidence_slider.setValue(50)
        self.confidence_slider.setTickPosition(QSlider.TickPosition.TicksBelow)
        self.confidence_slider.setTickInterval(10)
        self.confidence_slider.valueChanged.connect(self._update_confidence_label)
        self.confidence_slider.sliderReleased.connect(self.on_change)
        conf_layout.addWidget(self.confidence_slider)
        
        self.confidence_value_label = QLabel("0.50")
        self.confidence_value_label.setStyleSheet("font-weight: 600; font-size: 9pt; min-width: 40px;")
        conf_layout.addWidget(self.confidence_value_label)
        
        layout.addLayout(conf_layout)
        
        # Confidence description
        conf_desc = QLabel()
        self.set_translatable_text(conf_desc, "ocr_confidence_desc")
        conf_desc.setWordWrap(True)
        conf_desc.setStyleSheet("color: #666666; font-size: 8pt; margin-bottom: 10px;")
        layout.addWidget(conf_desc)
        
        # Image Preprocessing checkbox
        self.preprocessing_enabled = QCheckBox("🔍 Enable Intelligent Image Preprocessing")
        self.preprocessing_enabled.setChecked(False)
        self.preprocessing_enabled.setStyleSheet("font-weight: bold; margin-top: 10px;")
        self.preprocessing_enabled.stateChanged.connect(self._on_preprocessing_changed)
        layout.addWidget(self.preprocessing_enabled)
        
        preprocessing_desc = QLabel(
            "Two-pass intelligent preprocessing:\n"
            "1️⃣ Quick OCR to detect text regions\n"
            "2️⃣ Enhance only text areas (upscale 2x, sharpen, contrast)\n"
            "3️⃣ Re-OCR enhanced regions for better accuracy\n\n"
            "✓ 80% faster than full-image preprocessing\n"
            "✓ Better recognition for low-quality/small text\n"
            "✗ Adds ~20-30ms per frame (vs ~100ms for full preprocessing)\n"
            "💡 Best for: Manga, screenshots, low-res images"
        )
        preprocessing_desc.setWordWrap(True)
        preprocessing_desc.setStyleSheet(
            "color: #888; font-size: 8pt; margin-left: 25px; margin-bottom: 5px; "
            "padding: 8px; background-color: #1e1e1e; border-radius: 3px;"
        )
        layout.addWidget(preprocessing_desc)
        
        # Performance impact indicator
        perf_impact = QLabel("⚡ Performance Impact: OCR stage ~50ms → ~70-80ms (still 12-14 FPS)")
        perf_impact.setStyleSheet(
            "color: #66bb6a; font-size: 9pt; font-weight: bold; margin-left: 25px; "
            "margin-bottom: 10px; padding: 6px; background-color: #1e3a1e; border-radius: 3px;"
        )
        layout.addWidget(perf_impact)
        
        # Preprocessing mode (intelligent vs full)
        self.preprocessing_mode_intelligent = QCheckBox("Use intelligent mode (recommended)")
        self.preprocessing_mode_intelligent.setChecked(True)
        self.preprocessing_mode_intelligent.setEnabled(False)
        self.preprocessing_mode_intelligent.setStyleSheet("margin-left: 25px; color: #888;")
        self.preprocessing_mode_intelligent.stateChanged.connect(self.on_change)
        layout.addWidget(self.preprocessing_mode_intelligent)
        
        # Engine loading information
        loading_info_label = self._create_label("", bold=True)
        self.set_translatable_text(loading_info_label, "ocr_engine_loading_label")
        layout.addWidget(loading_info_label)
        
        loading_info = QLabel()
        self.set_translatable_text(loading_info, "ocr_engine_loading_info")
        loading_info.setWordWrap(True)
        loading_info.setStyleSheet("color: #B0B0B0; font-size: 9pt; margin-bottom: 10px; padding: 8px; "
                                   "background-color: #1E3A4F; border-left: 3px solid #4A9EFF; border-radius: 3px;")
        layout.addWidget(loading_info)
        
        parent_layout.addWidget(group)
    
    def _update_confidence_label(self, value):
        """Update confidence value label when slider changes."""
        confidence = value / 100.0
        self.confidence_value_label.setText(f"{confidence:.2f}")
    
    def _on_preprocessing_changed(self, state):
        """Handle preprocessing checkbox state change."""
        enabled = state == 2  # Qt.CheckState.Checked
        self.preprocessing_mode_intelligent.setEnabled(enabled)
        self.on_change()
    
    def _create_test_section(self, parent_layout):
        """Create OCR test section."""
        group = QGroupBox()
        self.set_translatable_text(group, "ocr_test_ocr_section")
        layout = QVBoxLayout(group)
        layout.setSpacing(10)
        layout.setContentsMargins(15, 20, 15, 15)
        
        # Test description
        test_desc = QLabel()
        self.set_translatable_text(test_desc, "ocr_test_desc")
        test_desc.setWordWrap(True)
        test_desc.setStyleSheet("font-size: 9pt; margin-bottom: 10px;")
        layout.addWidget(test_desc)
        
        # Buttons layout
        test_layout = QHBoxLayout()
        
        # Quick test button
        self.quick_test_btn = QPushButton()
        self.set_translatable_text(self.quick_test_btn, "ocr_quick_ocr_test_button")
        self.quick_test_btn.setProperty("class", "action")
        self.quick_test_btn.setMinimumWidth(150)
        self.quick_test_btn.clicked.connect(self.test_manager.run_quick_test)
        test_layout.addWidget(self.quick_test_btn)
        
        # Full test button
        self.test_ocr_btn = QPushButton()
        self.set_translatable_text(self.test_ocr_btn, "ocr_run_ocr_test_button")
        self.test_ocr_btn.setProperty("class", "action")
        self.test_ocr_btn.setMinimumWidth(150)
        self.test_ocr_btn.clicked.connect(self.test_manager.open_test_window)
        test_layout.addWidget(self.test_ocr_btn)
        
        test_layout.addStretch()
        
        layout.addLayout(test_layout)
        
        parent_layout.addWidget(group)
        
        # Add OCR Model Management section
        self._create_ocr_model_management_section(parent_layout)
    
    def _create_ocr_model_management_section(self, parent_layout):
        """Create OCR model management section."""
        group = QGroupBox()
        self.set_translatable_text(group, "ocr_ocr_model_management_section")
        layout = QVBoxLayout(group)
        layout.setSpacing(10)
        layout.setContentsMargins(15, 20, 15, 15)
        
        # Description
        model_desc = QLabel()
        self.set_translatable_text(model_desc, "ocr_model_desc")
        model_desc.setWordWrap(True)
        model_desc.setStyleSheet("color: #666666; font-size: 9pt;")
        layout.addWidget(model_desc)
        
        # Button layout
        model_btn_layout = QHBoxLayout()
        
        # Manage OCR Models button
        manage_models_btn = QPushButton()
        self.set_translatable_text(manage_models_btn, "ocr_manage_ocr_models_button")
        manage_models_btn.setProperty("class", "action")
        manage_models_btn.setToolTip("Open OCR model manager to discover and register custom models")
        manage_models_btn.clicked.connect(self._show_ocr_model_manager)
        model_btn_layout.addWidget(manage_models_btn)
        
        model_btn_layout.addStretch()
        
        layout.addLayout(model_btn_layout)
        
        parent_layout.addWidget(group)
    
    def _show_ocr_model_manager(self):
        """Show OCR model manager dialog."""
        try:
            from ui.settings.ocr_model_manager import OCRModelManager
            manager = OCRModelManager(parent=self, config_manager=self.config_manager)
            manager.show_ocr_model_manager()
        except ImportError as e:
            from PyQt6.QtWidgets import QMessageBox
            QMessageBox.warning(
                self,
                "Feature Not Available",
                f"OCR model manager is not available:\n{e}\n\n"
                f"Please ensure all components are properly installed."
            )

    
    def load_config(self):
        """Load configuration from config manager."""
        if not self.config_manager:
            return
        
        try:
            # Load OCR engine (dynamic)
            engine = self.config_manager.get_setting('ocr.engine', 'paddleocr')
            
            # Find and check the corresponding radio button
            for engine_name, radio in self.engine_radios.items():
                if engine_name.lower() == engine.lower():
                    radio.setChecked(True)
                    break
            
            # Update language pack info for the loaded engine
            self._update_language_pack_info()
            
            # Load confidence threshold
            confidence = self.config_manager.get_setting('ocr.confidence_threshold', 0.5)
            self.confidence_slider.setValue(int(confidence * 100))
            self._update_confidence_label(int(confidence * 100))
            
            # Load preprocessing settings
            preprocessing = self.config_manager.get_setting('ocr.preprocessing_enabled', False)
            self.preprocessing_enabled.setChecked(preprocessing)
            
            preprocessing_intelligent = self.config_manager.get_setting('ocr.preprocessing_intelligent', True)
            self.preprocessing_mode_intelligent.setChecked(preprocessing_intelligent)
            self.preprocessing_mode_intelligent.setEnabled(preprocessing)
            
            # Load languages
            languages = self.config_manager.get_setting('ocr.languages', [])
            if languages:
                self.language_list.clear()
                
                # Language code to full name mapping
                lang_map = {
                    'en': 'English (en)',
                    'ja': 'Japanese (ja)',
                    'de': 'German (de)',
                    'es': 'Spanish (es)',
                    'fr': 'French (fr)',
                    'zh-CN': 'Chinese Simplified (zh-CN)',
                    'zh-TW': 'Chinese Traditional (zh-TW)',
                    'ko': 'Korean (ko)',
                    'ar': 'Arabic (ar)',
                    'bn': 'Bengali (bn)',
                    'bg': 'Bulgarian (bg)',
                    'cs': 'Czech (cs)',
                    'da': 'Danish (da)',
                    'nl': 'Dutch (nl)',
                    'fi': 'Finnish (fi)',
                    'el': 'Greek (el)',
                    'he': 'Hebrew (he)',
                    'hi': 'Hindi (hi)',
                    'hu': 'Hungarian (hu)',
                    'id': 'Indonesian (id)',
                    'it': 'Italian (it)',
                    'no': 'Norwegian (no)',
                    'pl': 'Polish (pl)',
                    'pt': 'Portuguese (pt)',
                    'ro': 'Romanian (ro)',
                    'ru': 'Russian (ru)',
                    'sv': 'Swedish (sv)',
                    'th': 'Thai (th)',
                    'tr': 'Turkish (tr)',
                    'uk': 'Ukrainian (uk)',
                    'vi': 'Vietnamese (vi)'
                }
                
                for lang in languages:
                    # If it's already in full format (contains parentheses), use as-is
                    if '(' in lang and ')' in lang:
                        display_name = lang
                    # Otherwise, convert code to full name
                    else:
                        display_name = lang_map.get(lang, f"{lang.upper()} ({lang})")
                    
                    self.language_list.addItem(display_name)
            
            # Save the original state after loading
            self._original_state = self._get_current_state()
            
        except Exception as e:
            print(f"[ERROR] Failed to load OCR settings: {e}")
            import traceback
            traceback.print_exc()
    
    def get_selected_engine(self):
        """Get the currently selected OCR engine."""
        for engine_name, radio in self.engine_radios.items():
            if radio.isChecked():
                return engine_name
        return None
    
    def update_current_engine_display(self, engine_name):
        """Update the UI to show the selected engine (called by Quick Switch dialog)."""
        # Find and check the corresponding radio button
        for eng_name, radio in self.engine_radios.items():
            if eng_name.lower() == engine_name.lower():
                radio.setChecked(True)
                print(f"[OCR Tab] Updated display to show {engine_name} as selected")
                return
        print(f"[OCR Tab] Warning: Could not find radio button for engine '{engine_name}'")
    
    def save_config(self):
        """Save configuration to config manager and switch OCR engine if changed."""
        if not self.config_manager:
            return
        
        try:
            # Get selected engine (dynamic)
            engine = self.get_selected_engine()
            if not engine:
                engine = 'easyocr'  # Fallback
            
            # Check if engine changed
            old_engine = self.config_manager.get_setting('ocr.engine', 'easyocr')
            engine_changed = (engine.lower() != old_engine.lower())
            
            # Save settings
            self.config_manager.set_setting('ocr.engine', engine)
            self.config_manager.set_setting('ocr.confidence_threshold', self.confidence_slider.value() / 100.0)
            self.config_manager.set_setting('ocr.preprocessing_enabled', self.preprocessing_enabled.isChecked())
            self.config_manager.set_setting('ocr.preprocessing_intelligent', self.preprocessing_mode_intelligent.isChecked())
            
            # Save languages (extract just the codes from "Name (code)" format)
            languages = []
            for i in range(self.language_list.count()):
                item_text = self.language_list.item(i).text()
                # Extract code from "Name (code)" format
                if '(' in item_text and ')' in item_text:
                    lang_code = item_text.split('(')[1].split(')')[0]
                    languages.append(lang_code)
                else:
                    # If no parentheses, assume it's already a code
                    languages.append(item_text)
            self.config_manager.set_setting('ocr.languages', languages)
            
            # If engine changed, switch it in the pipeline
            if engine_changed and self.pipeline:
                print(f"[OCR Tab] Engine changed from '{old_engine}' to '{engine}', switching...")
                success = self.pipeline.set_ocr_engine(engine)
                if success:
                    print(f"[OCR Tab] ✓ Successfully switched to {engine}")
                    # Update status labels
                    from PyQt6.QtCore import QTimer
                    QTimer.singleShot(500, self._update_engine_statuses)
                else:
                    print(f"[OCR Tab] ✗ Failed to switch to {engine}")
            
            # Update original state after saving
            self._original_state = self._get_current_state()
            
            # CRITICAL FIX: Save the configuration file to disk!
            if hasattr(self.config_manager, 'save_config'):
                self.config_manager.save_config()
            elif hasattr(self.config_manager, 'save_configuration'):
                config_dict = self.config_manager._config_to_dict(self.config_manager._config)
                self.config_manager.save_configuration(config_dict)
            
            print(f"[INFO] OCR settings saved to disk")
            
        except Exception as e:
            print(f"[ERROR] Failed to save OCR settings: {e}")
            import traceback
            traceback.print_exc()
    
    def _update_engine_statuses(self):
        """Update engine status indicators from pipeline."""
        try:
            # Get pipeline from parent window
            parent = self.parent()
            while parent:
                if hasattr(parent, 'pipeline') and parent.pipeline:
                    pipeline = parent.pipeline
                    
                    # Get currently loaded engine
                    current_engine = None
                    if hasattr(pipeline, 'get_current_ocr_engine'):
                        current_engine = pipeline.get_current_ocr_engine()
                    elif hasattr(pipeline, 'ocr_layer') and hasattr(pipeline.ocr_layer, 'config'):
                        current_engine = pipeline.ocr_layer.config.default_engine
                    
                    # Get all discovered engines
                    discovered_engines = []
                    if hasattr(pipeline, 'get_available_ocr_engines'):
                        discovered_engines = pipeline.get_available_ocr_engines()
                    
                    # Update status for each discovered engine
                    for engine_name in discovered_engines:
                        engine_key = engine_name.lower()
                        if engine_name.lower() == (current_engine or '').lower():
                            # This engine is currently loaded
                            self.engine_manager.update_status(engine_key, "ready")
                        else:
                            # This engine is discovered but not loaded yet
                            self.engine_manager.update_status(engine_key, "not_loaded")
                    
                    print(f"[INFO] Updated OCR engine statuses: current={current_engine}, discovered={discovered_engines}")
                    break
                parent = parent.parent()
        except Exception as e:
            print(f"[WARNING] Failed to update engine statuses: {e}")
    
    def refresh_engine_list(self):
        """Refresh the engine list when pipeline becomes available."""
        print("[OCR Tab] Refreshing engine list...")
        
        # Get the scroll area content
        for i in range(self.layout().count()):
            widget = self.layout().itemAt(i).widget()
            if isinstance(widget, ScrollAreaNoWheel):
                scroll_content = widget.widget()
                if scroll_content:
                    content_layout = scroll_content.layout()
                    if content_layout:
                        # Find and remove the old engine selection group
                        old_group_index = -1
                        for j in range(content_layout.count()):
                            item = content_layout.itemAt(j)
                            if item and item.widget():
                                group = item.widget()
                                if isinstance(group, QGroupBox) and "Engine Selection" in group.title():
                                    old_group_index = j
                                    # Remove old group
                                    content_layout.removeWidget(group)
                                    group.deleteLater()
                                    break
                        
                        if old_group_index >= 0:
                            # Create new engine selection group
                            from PyQt6.QtWidgets import QVBoxLayout as TempVLayout
                            temp_layout = TempVLayout()
                            self._create_engine_selection_section(temp_layout)
                            
                            # Insert at the same position (should be 0 for top)
                            if temp_layout.count() > 0:
                                new_group = temp_layout.itemAt(0).widget()
                                content_layout.insertWidget(old_group_index, new_group)
                            
                            # Reload config to select the right engine
                            self.load_config()
                            
                            # Update statuses
                            self._update_engine_statuses()
                            
                            print("[OCR Tab] Engine list refreshed successfully")
                            return
        
        print("[OCR Tab] Could not find engine selection group to refresh")
    
    def validate(self) -> bool:
        """Validate settings."""
        # Check if at least one language is selected
        if self.language_list.count() == 0:
            from PyQt6.QtWidgets import QMessageBox
            QMessageBox.warning(
                self,
                "No Languages",
                "Please add at least one language for OCR recognition."
            )
            return False
        
        return True
