"""
OCR Settings Tab - PyQt6 Implementation (Refactored)
OCR engine selection and configuration.
Uses modular manager classes for better organization.
"""

import logging

from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QGroupBox,
    QLabel, QRadioButton, QCheckBox, QPushButton,
    QButtonGroup, QSlider, QDoubleSpinBox
)
from PyQt6.QtCore import Qt, pyqtSignal

# Import custom scroll area
from ui.common.widgets.scroll_area_no_wheel import ScrollAreaNoWheel

# Import translation system
from app.localization import TranslatableMixin, tr

# Import manager classes
from .test_manager import OCRTestManager

logger = logging.getLogger(__name__)


class OCREngineManager:
    """Manages OCR engine status and initialization."""

    def __init__(self, parent=None):
        self.parent = parent
        self.status_labels = {}

    def register_status_label(self, engine_name: str, label: QLabel):
        self.status_labels[engine_name] = label

    def update_status(self, engine_name: str, status: str):
        if engine_name in self.status_labels:
            label = self.status_labels[engine_name]
            self._update_status_label(label, status)

    def _update_status_label(self, label: QLabel, status: str):
        status_map = {
            "ready": ("🟢", tr("ocr_status_ready"), "#4CAF50"),
            "not_loaded": ("⚪", tr("ocr_status_not_loaded"), "#9E9E9E"),
            "loading": ("🟡", tr("ocr_status_loading"), "#FF9800"),
            "error": ("🔴", tr("ocr_status_error"), "#F44336"),
            "unknown": ("⚪", tr("ocr_status_unknown"), "#9E9E9E")
        }
        icon, text, color = status_map.get(status, status_map["unknown"])
        label.setText(f"{icon} {text}")
        label.setStyleSheet(f"font-size: 9pt; margin-left: 10px; color: {color}; font-weight: 500;")

    def create_status_label(self, status: str = "unknown") -> QLabel:
        label = QLabel()
        label.setStyleSheet("font-size: 9pt; margin-left: 10px;")
        self._update_status_label(label, status)
        return label


class OCRSettingsTab(TranslatableMixin, QWidget):
    """OCR settings including engine selection, languages, and configuration."""
    
    # Signal emitted when any setting changes
    settingChanged = pyqtSignal()
    # Emitted with the engine name when the user picks a different OCR engine
    ocrEngineChanged = pyqtSignal(str)
    
    def __init__(self, config_manager=None, parent=None):
        """Initialize the OCR settings tab."""
        super().__init__(parent)
        
        self.config_manager = config_manager
        self.pipeline = None  # Will be set by parent window
        
        # Track original loaded state to detect real changes
        self._original_state = {}
        
        # Initialize manager classes
        self.engine_manager = OCREngineManager(parent=self)
        self.test_manager = OCRTestManager(parent=self)
        
        # OCR engine widgets (dynamic)
        self.engine_radios = {}  # Store engine radio buttons dynamically
        self.engine_button_group = None
        
        # Configuration widgets
        self.confidence_slider = None
        self.confidence_spinbox = None
        
        # Test buttons
        self.quick_test_btn = None
        self.test_ocr_btn = None
        
        # Store reference to engine selection group for refresh
        self._engine_group = None

        # Vision-mode awareness
        self._content_widget = None
        self._vision_mode_banner = None
        
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

        # Banner shown when this tab is partially disabled in vision mode.
        self._vision_mode_banner = QLabel()
        self._vision_mode_banner.setWordWrap(True)
        self._vision_mode_banner.setStyleSheet(
            "color: #999999; font-size: 8pt; padding: 4px 6px;"
        )
        self._vision_mode_banner.setVisible(False)
        self.set_translatable_text(
            self._vision_mode_banner,
            "vision_mode_ocr_tab_disabled",
        )
        self._vision_mode_banner.setToolTip(tr("vision_mode_disabled_setting_hint"))
        main_layout.addWidget(self._vision_mode_banner)
        
        # Create scroll area (custom - only scrolls when mouse is over it)
        scroll_area = ScrollAreaNoWheel()
        scroll_area.setWidgetResizable(True)
        scroll_area.setFrameShape(ScrollAreaNoWheel.Shape.NoFrame)
        scroll_area.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        scroll_area.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAsNeeded)
        
        # Create content widget
        content_widget = QWidget()
        self._content_widget = content_widget
        content_layout = QVBoxLayout(content_widget)
        content_layout.setContentsMargins(5, 5, 5, 5)
        content_layout.setSpacing(10)
        
        # Create sections
        self._create_engine_selection_section(content_layout)
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
        if self.confidence_spinbox:
            state['confidence'] = self.confidence_spinbox.value()
        
        # Preprocessing settings
        if hasattr(self, 'preprocessing_enabled') and self.preprocessing_enabled:
            state['preprocessing_enabled'] = self.preprocessing_enabled.isChecked()
        if hasattr(self, 'preprocessing_mode_intelligent') and self.preprocessing_mode_intelligent:
            state['preprocessing_intelligent'] = self.preprocessing_mode_intelligent.isChecked()
        if hasattr(self, 'manga_bubble_detection') and self.manga_bubble_detection:
            state['manga_bubble_detection'] = self.manga_bubble_detection.isChecked()
        
        return state
    
    def on_change(self):
        """Called when any setting changes - always emits signal for main window to check."""
        # Always emit the signal - let the main window decide if there are actual changes
        self.settingChanged.emit()

    # ── Vision-mode awareness ─────────────────────────────────────────

    def set_pipeline_mode(self, is_vision: bool) -> None:
        """
        Enable/disable OCR controls based on pipeline mode.

        In vision mode the Qwen3-VL stage replaces classic OCR, so these
        settings become read-only for clarity.
        """
        if self._content_widget is not None:
            self._content_widget.setEnabled(not is_vision)
        if self._vision_mode_banner is not None:
            self._vision_mode_banner.setVisible(is_vision)

    def on_setting_changed(self, key: str, value) -> None:
        """React to cross-tab setting changes from SettingsCoordinator."""
        if key == "pipeline.mode":
            self.set_pipeline_mode(str(value) == "vision")
    
    def on_engine_radio_changed(self):
        """Called when engine radio button changes.

        Uses ``supported_languages`` metadata from plugin.json to decide
        whether to constrain or lock languages, instead of hard-coding
        engine names.

        Also loads the selected engine immediately so the status updates
        without requiring a separate save step.
        """
        if not hasattr(self, 'preprocessing_enabled'):
            return

        selected_engine = self.get_selected_engine()
        if not selected_engine:
            self.on_change()
            return

        from ui.settings.language_engine_validator import get_ocr_supported_languages

        supported = get_ocr_supported_languages(selected_engine)

        if supported is not None and len(supported) == 1:
            self._auto_set_single_language(supported[0])
            self._set_language_lock(True)
        else:
            self._set_language_lock(False)

        self._update_preprocessing_for_engine(selected_engine)

        self._load_selected_engine(selected_engine)

        self.ocrEngineChanged.emit(selected_engine)
        self.on_change()

    def _load_selected_engine(self, engine_name: str):
        """Load the selected OCR engine via the pipeline immediately."""
        pipeline = self._get_pipeline()
        if not pipeline:
            return

        current_engine = None
        if hasattr(pipeline, 'get_current_ocr_engine'):
            current_engine = pipeline.get_current_ocr_engine()

        if current_engine and current_engine.lower() == engine_name.lower():
            return

        engine_key = engine_name.lower()
        self.engine_manager.update_status(engine_key, "loading")

        self.config_manager.set_setting('ocr.engine', engine_name)

        from PyQt6.QtCore import QTimer
        QTimer.singleShot(50, lambda: self._do_load_engine(pipeline, engine_name))

    def _do_load_engine(self, pipeline, engine_name: str):
        """Perform the actual engine load and update status."""
        try:
            success = pipeline.set_ocr_engine(engine_name)
            if success:
                logger.info("Loaded OCR engine: %s", engine_name)
            else:
                logger.warning("Failed to load OCR engine: %s", engine_name)
                self.engine_manager.update_status(engine_name.lower(), "error")
        except Exception as exc:
            logger.error("Error loading OCR engine %s: %s", engine_name, exc)
            self.engine_manager.update_status(engine_name.lower(), "error")
        finally:
            from PyQt6.QtCore import QTimer
            QTimer.singleShot(500, self._update_engine_statuses)

    def _get_pipeline(self):
        """Walk up the parent chain to find the pipeline."""
        parent = self.parent()
        while parent:
            if hasattr(parent, 'pipeline') and parent.pipeline:
                return parent.pipeline
            parent = parent.parent()
        return None
    
    def _auto_set_single_language(self, lang_code: str):
        """Set source language when an OCR engine only supports one language.

        Only the source (OCR) language is forced; the target (translation)
        language is left unchanged so the user can translate into any language.
        """
        from ui.settings.language_engine_validator import LANG_CODE_TO_NAME

        lang_name = LANG_CODE_TO_NAME.get(lang_code, lang_code.upper())

        try:
            self.config_manager.set_setting('translation.source_language', lang_code)

            parent = self.parent()
            while parent:
                if hasattr(parent, 'sidebar'):
                    parent.sidebar.set_source_language(lang_name)
                    break
                parent = parent.parent()

            parent = self.parent()
            while parent:
                if hasattr(parent, 'general_tab'):
                    gt = parent.general_tab
                    if gt:
                        idx = gt.source_lang_combo.findText(lang_name)
                        if idx >= 0:
                            gt.source_lang_combo.blockSignals(True)
                            gt.source_lang_combo.setCurrentIndex(idx)
                            gt.source_lang_combo.blockSignals(False)
                    break
                parent = parent.parent()

            logger.info("Auto-set source language: %s for OCR engine constraint",
                        lang_name)
        except Exception as exc:
            logger.warning("Failed to auto-set languages: %s", exc)

    def _auto_set_manga_languages(self):
        """Backward-compatible alias — delegates to metadata-driven method."""
        self._auto_set_single_language('ja')

    def _set_language_lock(self, lock: bool):
        """Lock or unlock language selection based on OCR engine constraints."""
        try:
            parent = self.parent()
            while parent:
                if hasattr(parent, 'sidebar'):
                    parent.sidebar.set_language_lock(lock)
                    break
                parent = parent.parent()

            parent = self.parent()
            while parent:
                if hasattr(parent, 'general_tab'):
                    gt = parent.general_tab
                    if gt:
                        gt.set_language_lock(lock)
                    break
                parent = parent.parent()

            logger.debug("Language lock %s", "enabled" if lock else "disabled")
        except Exception as exc:
            logger.warning("Failed to set language lock: %s", exc)

    # Backward-compatible alias used by quick_ocr_switch_dialog
    _lock_languages_for_mokuro = _set_language_lock

    
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
                'easyocr': (tr("ocr_engine_easyocr_name"), tr("ocr_engine_easyocr_desc")),
                'easyocr_gpu': (tr("ocr_engine_easyocr_name"), tr("ocr_engine_easyocr_desc")),
                'tesseract': (tr("ocr_engine_tesseract_name"), tr("ocr_engine_tesseract_desc")),
                'paddleocr': (tr("ocr_engine_paddleocr_name"), tr("ocr_engine_paddleocr_desc")),
                'onnx': (tr("ocr_engine_onnx_name"), tr("ocr_engine_onnx_desc")),
                'mokuro': (tr("ocr_engine_mokuro_name"), tr("ocr_engine_mokuro_desc"))
            }
            
            # Get current engine
            current_engine = self.config_manager.get_setting('ocr.engine', 'easyocr') if self.config_manager else 'easyocr'
            
            # Create radio buttons for each discovered engine
            for button_id, engine in enumerate(available_engines):
                engine_lower = engine.lower()
                display_name, description = engine_info.get(engine_lower, (engine, tr("ocr_engine_default_desc")))
                if display_name == "ocr_engine_mokuro_name":
                    display_name = "Mokuro"
                if description == "ocr_engine_mokuro_desc":
                    description = "Manga OCR engine plugin"
                
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
        
        # Store reference for refresh_engine_list
        self._engine_group = group
    
    def _get_available_engines(self):
        """Get list of available OCR engines from pipeline, or from disk if pipeline not ready."""
        def _visible_plugin_names() -> set[str]:
            defaults = {"easyocr", "mokuro", "judge_ocr", "hybrid_ocr"}
            if not self.config_manager:
                return defaults
            configured = self.config_manager.get_setting("ocr.visible_plugins", None)
            if isinstance(configured, list):
                custom = {str(x).strip().lower() for x in configured if str(x).strip()}
                if custom:
                    defaults = custom
            current_engine = self.config_manager.get_setting("ocr.engine", "")
            if current_engine:
                defaults.add(str(current_engine).strip().lower())
            return defaults

        visible_names = _visible_plugin_names()
        merged_engines: list[str] = []

        def _merge(items: list[str]) -> None:
            seen = {name.lower() for name in merged_engines}
            for name in items:
                if name.lower() in seen:
                    continue
                merged_engines.append(name)
                seen.add(name.lower())

        # Try to get from parent window's pipeline first (most accurate).
        # If pipeline returns engines, trust that list and do not merge in
        # disk-only names that may be missing dependencies on this machine.
        parent = self.parent()
        while parent:
            if hasattr(parent, 'pipeline') and parent.pipeline:
                try:
                    engines = parent.pipeline.get_available_ocr_engines()
                    if engines:
                        _merge(engines)
                        logger.info(f"Discovered {len(engines)} OCR engines: {engines}")
                except Exception as e:
                    logger.warning(f"Could not get engines from pipeline: {e}")
                break
            parent = parent.parent()

        if merged_engines:
            filtered = [name for name in merged_engines if name.lower() in visible_names]
            if filtered:
                return filtered
            return merged_engines

        # Fallback when pipeline is not ready: dependency-aware discovery.
        # This avoids showing engines that exist on disk but cannot run.
        try:
            from app.ocr.ocr_plugin_manager import OCRPluginManager
            manager = OCRPluginManager(config_manager=self.config_manager)
            discovered = manager.discover_plugins()
            installable = [plugin.name for plugin in discovered]
            if installable:
                logger.debug(
                    "Showing %d installable OCR engine(s): %s",
                    len(installable),
                    installable,
                )
                _merge(installable)
        except Exception as e:
            logger.debug("Installable OCR engine discovery failed: %s", e)

        filtered = [name for name in merged_engines if name.lower() in visible_names]
        if filtered:
            return filtered
        return merged_engines

    
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
        self.confidence_slider.setSingleStep(5)
        self.confidence_slider.setPageStep(10)
        self.confidence_slider.setTickPosition(QSlider.TickPosition.TicksBelow)
        self.confidence_slider.setTickInterval(10)
        self.confidence_slider.setMaximumWidth(220)
        self.confidence_slider.valueChanged.connect(self._on_slider_changed)
        self.confidence_slider.sliderReleased.connect(self.on_change)
        conf_layout.addWidget(self.confidence_slider)
        
        self.confidence_spinbox = QDoubleSpinBox()
        self.confidence_spinbox.setRange(0.00, 1.00)
        self.confidence_spinbox.setSingleStep(0.05)
        self.confidence_spinbox.setDecimals(2)
        self.confidence_spinbox.setValue(0.50)
        self.confidence_spinbox.setFixedWidth(70)
        self.confidence_spinbox.setStyleSheet("font-weight: 600; font-size: 9pt;")
        self.confidence_spinbox.valueChanged.connect(self._on_spinbox_changed)
        conf_layout.addWidget(self.confidence_spinbox)
        
        conf_layout.addStretch()
        layout.addLayout(conf_layout)
        
        # Confidence description
        conf_desc = QLabel()
        self.set_translatable_text(conf_desc, "ocr_confidence_desc")
        conf_desc.setWordWrap(True)
        conf_desc.setStyleSheet("color: #666666; font-size: 8pt; margin-bottom: 10px;")
        layout.addWidget(conf_desc)
        
        # Image Preprocessing checkbox + Tesseract-only badge
        preproc_row = QHBoxLayout()
        preproc_row.setSpacing(8)

        self.preprocessing_enabled = QCheckBox()
        self.set_translatable_text(self.preprocessing_enabled, "ocr_enable_preprocessing")
        self.preprocessing_enabled.setChecked(False)
        self.preprocessing_enabled.setStyleSheet("font-weight: bold; margin-top: 10px;")
        self.preprocessing_enabled.stateChanged.connect(self._on_preprocessing_changed)
        preproc_row.addWidget(self.preprocessing_enabled)

        self._preprocessing_tesseract_badge = QLabel(tr("ocr_tesseract_only_badge"))
        self._preprocessing_tesseract_badge.setStyleSheet(
            "color: #FF9800; font-size: 8pt; font-weight: bold; margin-top: 10px; "
            "padding: 2px 6px; background-color: #3a2a00; border-radius: 3px;"
        )
        self._preprocessing_tesseract_badge.setToolTip(tr("ocr_preprocessing_tooltip"))
        preproc_row.addWidget(self._preprocessing_tesseract_badge)
        preproc_row.addStretch()
        layout.addLayout(preproc_row)
        
        preprocessing_desc = QLabel()
        self.set_translatable_text(preprocessing_desc, "ocr_preprocessing_desc")
        preprocessing_desc.setWordWrap(True)
        preprocessing_desc.setStyleSheet(
            "color: #888; font-size: 8pt; margin-left: 25px; margin-bottom: 5px; "
            "padding: 8px; background-color: #1e1e1e; border-radius: 3px;"
        )
        layout.addWidget(preprocessing_desc)
        
        # Performance impact indicator
        perf_impact = QLabel()
        self.set_translatable_text(perf_impact, "ocr_perf_impact")
        perf_impact.setStyleSheet(
            "color: #66bb6a; font-size: 9pt; font-weight: bold; margin-left: 25px; "
            "margin-bottom: 10px; padding: 6px; background-color: #1e3a1e; border-radius: 3px;"
        )
        layout.addWidget(perf_impact)
        
        # Preprocessing mode (intelligent vs full)
        self.preprocessing_mode_intelligent = QCheckBox()
        self.set_translatable_text(self.preprocessing_mode_intelligent, "ocr_use_intelligent_mode")
        self.preprocessing_mode_intelligent.setChecked(True)
        self.preprocessing_mode_intelligent.setEnabled(False)
        self.preprocessing_mode_intelligent.setStyleSheet("margin-left: 25px; color: #888;")
        self.preprocessing_mode_intelligent.stateChanged.connect(self.on_change)
        layout.addWidget(self.preprocessing_mode_intelligent)
        
        # --- Manga bubble detection ---
        bubble_row = QHBoxLayout()
        bubble_row.setSpacing(8)

        self.manga_bubble_detection = QCheckBox()
        self.set_translatable_text(self.manga_bubble_detection, "ocr_manga_bubble_detection")
        self.manga_bubble_detection.setChecked(False)
        self.manga_bubble_detection.setStyleSheet("font-weight: bold; margin-top: 10px;")
        self.manga_bubble_detection.stateChanged.connect(self.on_change)
        bubble_row.addWidget(self.manga_bubble_detection)

        self._bubble_manga_badge = QLabel()
        self.set_translatable_text(self._bubble_manga_badge, "ocr_manga_bubble_detection_badge")
        self._bubble_manga_badge.setStyleSheet(
            "color: #CE93D8; font-size: 8pt; font-weight: bold; margin-top: 10px; "
            "padding: 2px 6px; background-color: #2a1a3a; border-radius: 3px;"
        )
        self._bubble_manga_badge.setToolTip(tr("ocr_manga_bubble_tooltip"))
        bubble_row.addWidget(self._bubble_manga_badge)
        bubble_row.addStretch()
        layout.addLayout(bubble_row)

        bubble_desc = QLabel()
        self.set_translatable_text(bubble_desc, "ocr_manga_bubble_detection_desc")
        bubble_desc.setWordWrap(True)
        bubble_desc.setStyleSheet(
            "color: #888; font-size: 8pt; margin-left: 25px; margin-bottom: 10px; "
            "padding: 8px; background-color: #1e1e1e; border-radius: 3px;"
        )
        layout.addWidget(bubble_desc)

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
    
    def _on_slider_changed(self, value):
        """Sync spinbox when slider moves."""
        self.confidence_spinbox.blockSignals(True)
        self.confidence_spinbox.setValue(value / 100.0)
        self.confidence_spinbox.blockSignals(False)

    def _on_spinbox_changed(self, value):
        """Sync slider when spinbox value changes, and mark dirty."""
        self.confidence_slider.blockSignals(True)
        self.confidence_slider.setValue(int(round(value * 100)))
        self.confidence_slider.blockSignals(False)
        self.on_change()
    
    def _on_preprocessing_changed(self, state):
        """Handle preprocessing checkbox state change."""
        enabled = state == 2  # Qt.CheckState.Checked
        self.preprocessing_mode_intelligent.setEnabled(enabled)
        self.on_change()

    def _is_tesseract_selected(self) -> bool:
        """Check if the currently selected engine is Tesseract."""
        engine = self.get_selected_engine()
        return engine is not None and 'tesseract' in engine.lower()

    def _update_preprocessing_for_engine(self, engine_name: str):
        """Enable or disable preprocessing controls based on the selected OCR engine.

        Preprocessing (grayscale conversion, adaptive thresholding, denoising)
        is only beneficial for Tesseract. Other engines handle their own
        preprocessing internally and may produce worse results with
        pre-binarized input.

        Engines with built-in text detection (e.g. Mokuro) bypass this
        and receive the full frame directly.
        """
        is_tesseract = 'tesseract' in engine_name.lower()
        is_manga = 'manga' in engine_name.lower()

        self.preprocessing_enabled.setEnabled(is_tesseract)
        self._preprocessing_tesseract_badge.setVisible(not is_tesseract)

        if not is_tesseract:
            self.preprocessing_enabled.setChecked(False)
            self.preprocessing_mode_intelligent.setEnabled(False)

        # Show badge only when a non-manga engine is selected
        self._bubble_manga_badge.setVisible(not is_manga)
    
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
        self.set_translatable_text(manage_models_btn, "ocr_manage_models_tooltip", method="setToolTip")
        manage_models_btn.clicked.connect(self._show_ocr_model_manager)
        model_btn_layout.addWidget(manage_models_btn)
        
        model_btn_layout.addStretch()
        
        layout.addLayout(model_btn_layout)
        
        parent_layout.addWidget(group)
    
    def _show_ocr_model_manager(self):
        """Show OCR model manager dialog."""
        try:
            from .model_manager import OCRModelManager
            manager = OCRModelManager(parent=self, config_manager=self.config_manager)
            manager.show_ocr_model_manager()
        except ImportError as e:
            from PyQt6.QtWidgets import QMessageBox
            QMessageBox.warning(
                self,
                tr("ocr_feature_not_available"),
                tr("ocr_model_manager_not_available").format(error=e)
            )

    
    def load_config(self):
        """Load configuration from config manager."""
        if not self.config_manager:
            return
        
        try:
            # Load OCR engine (dynamic)
            engine = self.config_manager.get_setting('ocr.engine', 'easyocr')
            
            # Find and check the corresponding radio button
            for engine_name, radio in self.engine_radios.items():
                if engine_name.lower() == engine.lower():
                    radio.setChecked(True)
                    break
            
            # Load confidence threshold
            confidence = self.config_manager.get_setting('ocr.confidence_threshold', 0.5)
            self.confidence_spinbox.setValue(confidence)
            self.confidence_slider.setValue(int(confidence * 100))
            
            # Load preprocessing settings (Tesseract-only)
            self._update_preprocessing_for_engine(engine)
            preprocessing = self.config_manager.get_setting('ocr.preprocessing_enabled', False)
            if self.preprocessing_enabled.isEnabled():
                self.preprocessing_enabled.setChecked(preprocessing)
            
            preprocessing_intelligent = self.config_manager.get_setting('ocr.preprocessing_intelligent', True)
            self.preprocessing_mode_intelligent.setChecked(preprocessing_intelligent)
            self.preprocessing_mode_intelligent.setEnabled(
                preprocessing and self.preprocessing_enabled.isEnabled()
            )
            
            # Load manga bubble detection
            manga_bubble = self.config_manager.get_setting('ocr.manga_bubble_detection', False)
            self.manga_bubble_detection.setChecked(manga_bubble)
            
            # Save the original state after loading
            self._original_state = self._get_current_state()

            # Apply pipeline-mode specific enabling/disabling on load
            try:
                mode = self.config_manager.get_setting('pipeline.mode', 'text')
                self.set_pipeline_mode(mode == "vision")
            except Exception:
                # If anything goes wrong, leave controls enabled.
                pass
            
        except Exception as e:
            logger.error(f"Failed to load OCR settings: {e}", exc_info=True)
    
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
                logger.debug(f"Updated display to show {engine_name} as selected")
                return
        logger.warning(f"Could not find radio button for engine '{engine_name}'")
    
    def save_config(self):
        """
        Save configuration to config manager and switch OCR engine if changed.
        
        Returns:
            tuple: (success: bool, error_message: str)
        """
        if not self.config_manager:
            return False, "Configuration manager not available"
        
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
            self.config_manager.set_setting('ocr.confidence_threshold', self.confidence_spinbox.value())
            self.config_manager.set_setting('ocr.preprocessing_enabled', self.preprocessing_enabled.isChecked())
            self.config_manager.set_setting('ocr.preprocessing_intelligent', self.preprocessing_mode_intelligent.isChecked())
            self.config_manager.set_setting('ocr.manga_bubble_detection', self.manga_bubble_detection.isChecked())
            
            # If engine changed, switch it in the pipeline
            if engine_changed and self.pipeline:
                logger.info(f"Engine changed from '{old_engine}' to '{engine}', switching...")
                success = self.pipeline.set_ocr_engine(engine)
                if success:
                    logger.info(f"Successfully switched to {engine}")
                    # Update status labels
                    from PyQt6.QtCore import QTimer
                    QTimer.singleShot(500, self._update_engine_statuses)
                else:
                    logger.warning(f"Failed to switch to {engine}")
            
            # Save the configuration file to disk
            success, error_msg = self.config_manager.save_config()
            
            if not success:
                return False, error_msg
            
            # Update original state after saving
            self._original_state = self._get_current_state()
            
            logger.debug("OCR settings saved to disk")
            return True, ""
            
        except Exception as e:
            error_msg = f"Failed to save settings: {e}"
            logger.error(error_msg, exc_info=True)
            return False, error_msg
    
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
                    
                    loaded_plugins = []
                    if hasattr(pipeline, 'ocr_layer') and hasattr(pipeline.ocr_layer, 'plugin_manager'):
                        loaded_plugins = pipeline.ocr_layer.plugin_manager.get_loaded_plugins()

                    for engine_name in discovered_engines:
                        engine_key = engine_name.lower()
                        is_current = engine_name.lower() == (current_engine or '').lower()
                        is_loaded = engine_key in [p.lower() for p in loaded_plugins]

                        if is_current and is_loaded:
                            self.engine_manager.update_status(engine_key, "ready")
                        elif is_current and not is_loaded:
                            self.engine_manager.update_status(engine_key, "error")
                        else:
                            self.engine_manager.update_status(engine_key, "not_loaded")
                    
                    logger.debug(f"Updated OCR engine statuses: current={current_engine}, discovered={discovered_engines}")
                    break
                parent = parent.parent()
        except Exception as e:
            logger.warning(f"Failed to update engine statuses: {e}")
    
    def refresh_engine_list(self):
        """Refresh the engine list when pipeline becomes available."""
        if not self._engine_group:
            return
        
        # Get the scroll area content
        for i in range(self.layout().count()):
            widget = self.layout().itemAt(i).widget()
            if isinstance(widget, ScrollAreaNoWheel):
                scroll_content = widget.widget()
                if scroll_content:
                    content_layout = scroll_content.layout()
                    if content_layout:
                        # Find the stored engine group by reference
                        old_group_index = content_layout.indexOf(self._engine_group)
                        
                        if old_group_index >= 0:
                            # Remove old group
                            content_layout.removeWidget(self._engine_group)
                            self._engine_group.deleteLater()
                            self._engine_group = None
                            
                            # Reset engine radios since we're rebuilding
                            self.engine_radios = {}
                            
                            # Create new engine selection group
                            from PyQt6.QtWidgets import QVBoxLayout as TempVLayout
                            temp_layout = TempVLayout()
                            self._create_engine_selection_section(temp_layout)
                            
                            # Insert at the same position
                            if temp_layout.count() > 0:
                                new_group = temp_layout.itemAt(0).widget()
                                content_layout.insertWidget(old_group_index, new_group)
                            
                            # Reload config to select the right engine
                            self.load_config()
                            
                            # Update statuses
                            self._update_engine_statuses()
                            return
    
    def validate(self) -> bool:
        """Validate settings."""
        return True
