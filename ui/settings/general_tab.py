"""
General Settings Tab - PyQt6 Implementation
Language, runtime, and startup configuration.
"""

import logging

from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QFormLayout, QGroupBox,
    QLabel, QLineEdit, QComboBox, QRadioButton, QCheckBox, QPushButton,
    QButtonGroup, QMessageBox, QProgressDialog, QApplication, QFileDialog,
    QDialog, QDialogButtonBox, QKeySequenceEdit,
)
from PyQt6.QtCore import Qt, pyqtSignal, QThread

from ui.common.widgets.scroll_area_no_wheel import ScrollAreaNoWheel
from app.localization import TranslatableMixin, tr
from app.utils.hardware_capability_gate import get_hardware_gate

logger = logging.getLogger(__name__)


class GeneralSettingsTab(TranslatableMixin, QWidget):
    """General settings including language, runtime mode, and startup options."""
    
    # Signal emitted when any setting changes
    settingChanged = pyqtSignal()
    
    def __init__(self, config_manager=None, parent=None):
        """Initialize the General settings tab."""
        super().__init__(parent)
        
        self.config_manager = config_manager
        
        # Track original loaded state to detect real changes
        self._original_state = {}
        
        # Track if this is the first load (to avoid showing dialog on startup)
        self._is_first_load = True
        
        # Language widgets
        self.source_lang_combo = None
        self.target_lang_combo = None
        self.ui_lang_combo = None
        
        # Runtime mode widgets
        self.runtime_auto_radio = None
        self.runtime_gpu_radio = None
        self.runtime_cpu_radio = None
        self.runtime_button_group = None
        
        # Startup option widgets
        self.minimize_tray_check = None
        self.pipeline_hotkey_display = None
        self.pipeline_hotkey_button = None
        self.pipeline_hotkey_value = "Ctrl+T"
        self.screenshot_hotkey_display = None
        self.screenshot_hotkey_button = None
        self.screenshot_hotkey_value = "F9"
        self.recording_flash_hotkey_display = None
        self.recording_flash_hotkey_button = None
        self.recording_flash_hotkey_value = "F10"
        # Manga mode
        self.manga_mode_check = None
        
        # PyTorch widgets
        self.pytorch_version_combo = None
        self.pytorch_switch_btn = None
        self.pytorch_info_label = None
        
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
        self._create_ui_language_section(content_layout)
        self._create_language_section(content_layout)
        self._create_runtime_section(content_layout)
        self._create_startup_section(content_layout)
        self._create_manga_mode_section(content_layout)
        # Overlay interaction moved to Overlay tab
        self._create_pytorch_section(content_layout)
        
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
        
        # Language settings
        if self.source_lang_combo:
            state['source_lang'] = self.source_lang_combo.currentText()
        if self.target_lang_combo:
            state['target_lang'] = self.target_lang_combo.currentText()
        if self.ui_lang_combo:
            state['ui_lang'] = self.ui_lang_combo.currentText()
        
        # Runtime mode
        if self.runtime_gpu_radio and self.runtime_gpu_radio.isChecked():
            state['runtime_mode'] = 'gpu'
        elif self.runtime_cpu_radio and self.runtime_cpu_radio.isChecked():
            state['runtime_mode'] = 'cpu'
        else:
            state['runtime_mode'] = 'auto'
        
        # Startup options
        if self.minimize_tray_check:
            state['minimize_tray'] = self.minimize_tray_check.isChecked()
        state['pipeline_hotkey'] = self.pipeline_hotkey_value
        state['screenshot_hotkey'] = self.screenshot_hotkey_value
        state['recording_flash_hotkey'] = self.recording_flash_hotkey_value
        # Manga mode
        if self.manga_mode_check:
            state['manga_mode'] = self.manga_mode_check.isChecked()
        
        return state
    
    def on_change(self):
        """Called when any setting changes - always emits signal for main window to check."""
        # Always emit the signal - let the main window decide if there are actual changes
        self.settingChanged.emit()
    
    def _on_ui_language_changed(self, language_name: str):
        """Handle UI language change."""
        # Map display names to language codes
        lang_map = {
            'English': 'en',
            'Deutsch (German)': 'de',
            'Français (French)': 'fr',
            'Italiano (Italian)': 'it',
            '日本語 (Japanese)': 'ja'
        }
        
        lang_code = lang_map.get(language_name, 'en')
        
        # Update translation system immediately for new dialogs
        try:
            from app.localization import get_language_manager
            
            # Use language manager to change language (triggers signals)
            language_manager = get_language_manager()
            language_manager.set_language(lang_code)
            
            # Show restart message in the NEW language
            QMessageBox.information(
                self,
                tr("language_changed_title"),
                tr("language_changed_message", language=language_name)
            )
        except ImportError:
            # Fallback if translations not available
            QMessageBox.information(
                self,
                "Language Changed",
                f"UI language has been changed to: {language_name}\n\n"
                "IMPORTANT: You must completely close and restart OptikR for the language change to take full effect.\n\n"
                "Steps:\n"
                "1. Click 'Save Configuration' button below\n"
                "2. Close OptikR completely (not just minimize)\n"
                "3. Restart OptikR\n\n"
                "The new language will be active after restart."
            )
        
        self.on_change()
    
    def _create_ui_language_section(self, parent_layout):
        """Create UI language selection section."""
        group = QGroupBox()
        self.set_translatable_text(group, "ui_language_section_title")
        layout = QVBoxLayout(group)
        layout.setSpacing(10)
        layout.setContentsMargins(15, 20, 15, 15)
        
        # Explanation
        explanation = QLabel()
        self.set_translatable_text(explanation, "ui_language_section_description")
        explanation.setWordWrap(True)
        explanation.setStyleSheet("color: #B0B0B0; font-size: 9pt; margin-bottom: 10px;")
        layout.addWidget(explanation)
        
        # Form layout
        form_layout = QFormLayout()
        form_layout.setSpacing(10)
        
        # UI Language
        ui_lang_label = QLabel()
        self.set_translatable_text(ui_lang_label, "interface_language_label")
        ui_lang_label.setStyleSheet("font-weight: 600; font-size: 9pt;")
        
        self.ui_lang_combo = QComboBox()
        self.ui_lang_combo.addItems([
            'English',
            'Deutsch (German)',
            'Français (French)',
            'Italiano (Italian)',
            '日本語 (Japanese)'
        ])
        self.ui_lang_combo.setCurrentText('English')
        self.ui_lang_combo.currentTextChanged.connect(self._on_ui_language_changed)
        
        form_layout.addRow(ui_lang_label, self.ui_lang_combo)
        layout.addLayout(form_layout)
        
        # Restart indicator
        restart_note = QLabel()
        self.set_translatable_text(restart_note, "ui_update_note")
        restart_note.setWordWrap(True)
        restart_note.setStyleSheet(
            "color: #4CAF50; "
            "font-size: 8pt; "
            "margin-top: 5px; "
            "padding: 6px 10px; "
            "background-color: rgba(76, 175, 80, 0.1); "
            "border-radius: 4px; "
            "border-left: 3px solid #4CAF50;"
        )
        layout.addWidget(restart_note)
        
        parent_layout.addWidget(group)
    
    def _create_language_section(self, parent_layout):
        """Create language configuration section."""
        group = QGroupBox()
        self.set_translatable_text(group, "language_config_section_title")
        layout = QVBoxLayout(group)
        layout.setSpacing(10)
        layout.setContentsMargins(15, 20, 15, 15)
        
        # Explanation
        explanation = QLabel()
        self.set_translatable_text(explanation, "language_config_description")
        explanation.setWordWrap(True)
        explanation.setStyleSheet("color: #666666; font-size: 9pt; margin-bottom: 10px;")
        layout.addWidget(explanation)
        
        # Form layout for language dropdowns
        form_layout = QFormLayout()
        form_layout.setSpacing(10)
        
        # Source Language (OCR Detection)
        source_label = QLabel()
        self.set_translatable_text(source_label, "ocr_source_language_label")
        source_label.setStyleSheet("font-weight: 600; font-size: 9pt;")
        source_help = QLabel()
        self.set_translatable_text(source_help, "ocr_source_language_help")
        source_help.setStyleSheet("color: #888888; font-size: 8pt; font-style: italic;")
        
        self.source_lang_combo = QComboBox()
        self.source_lang_combo.addItems([
            'Auto-Detect', 'English', 'Spanish', 'French', 'German',
            'Japanese', 'Korean', 'Chinese', 'Portuguese', 'Italian', 'Russian'
        ])
        self.source_lang_combo.setCurrentText('English')
        self.source_lang_combo.currentTextChanged.connect(self.on_change)
        
        source_container = QWidget()
        source_container_layout = QVBoxLayout(source_container)
        source_container_layout.setContentsMargins(0, 0, 0, 0)
        source_container_layout.setSpacing(2)
        source_container_layout.addWidget(self.source_lang_combo)
        source_container_layout.addWidget(source_help)
        
        form_layout.addRow(source_label, source_container)
        
        # Target Language (Translation Output)
        target_label = QLabel()
        self.set_translatable_text(target_label, "translation_target_language_label")
        target_label.setStyleSheet("font-weight: 600; font-size: 9pt;")
        target_help = QLabel()
        self.set_translatable_text(target_help, "translation_target_language_help")
        target_help.setStyleSheet("color: #888888; font-size: 8pt; font-style: italic;")
        
        self.target_lang_combo = QComboBox()
        self.target_lang_combo.addItems([
            'English', 'Spanish', 'French', 'German', 'Japanese',
            'Korean', 'Chinese', 'Portuguese', 'Italian', 'Russian'
        ])
        self.target_lang_combo.setCurrentText('German')
        self.target_lang_combo.currentTextChanged.connect(self.on_change)
        
        target_container = QWidget()
        target_container_layout = QVBoxLayout(target_container)
        target_container_layout.setContentsMargins(0, 0, 0, 0)
        target_container_layout.setSpacing(2)
        target_container_layout.addWidget(self.target_lang_combo)
        target_container_layout.addWidget(target_help)
        
        form_layout.addRow(target_label, target_container)
        
        layout.addLayout(form_layout)
        
        # Example
        example = QLabel()
        self.set_translatable_text(example, "language_example")
        example.setWordWrap(True)
        example.setStyleSheet("color: #2196F3; font-size: 8pt; margin-top: 10px; padding: 8px; background-color: rgba(33, 150, 243, 0.1); border-radius: 4px;")
        layout.addWidget(example)
        
        parent_layout.addWidget(group)
    
    def _create_runtime_section(self, parent_layout):
        """Create runtime configuration section."""
        group = QGroupBox()
        self.set_translatable_text(group, "runtime_config_section_title")
        layout = QVBoxLayout(group)
        layout.setSpacing(10)
        layout.setContentsMargins(15, 20, 15, 15)
        
        # Runtime Mode label
        mode_label = QLabel()
        self.set_translatable_text(mode_label, "runtime_mode_label")
        mode_label.setStyleSheet("font-weight: 600; font-size: 9pt;")
        layout.addWidget(mode_label)
        
        # Create button group for radio buttons
        self.runtime_button_group = QButtonGroup()
        
        # Auto mode (recommended)
        self.runtime_auto_radio = QRadioButton()
        self.set_translatable_text(self.runtime_auto_radio, "auto_recommended_label")
        self.runtime_auto_radio.setChecked(True)
        self.runtime_auto_radio.toggled.connect(self.on_change)
        self.runtime_button_group.addButton(self.runtime_auto_radio, 0)
        layout.addWidget(self.runtime_auto_radio)
        
        # GPU mode
        self.runtime_gpu_radio = QRadioButton()
        self.set_translatable_text(self.runtime_gpu_radio, "gpu_acceleration_label")
        self.runtime_gpu_radio.toggled.connect(self.on_change)
        self.runtime_button_group.addButton(self.runtime_gpu_radio, 1)
        layout.addWidget(self.runtime_gpu_radio)
        
        # CPU mode
        self.runtime_cpu_radio = QRadioButton()
        self.set_translatable_text(self.runtime_cpu_radio, "cpu_only_label")
        self.runtime_cpu_radio.toggled.connect(self.on_change)
        self.runtime_button_group.addButton(self.runtime_cpu_radio, 2)
        layout.addWidget(self.runtime_cpu_radio)
        
        # Note about runtime mode
        note_label = QLabel()
        self.set_translatable_text(note_label, "runtime_mode_note")
        note_label.setWordWrap(True)
        note_label.setStyleSheet("color: #666666; font-size: 9pt; margin-top: 5px;")
        layout.addWidget(note_label)
        
        parent_layout.addWidget(group)
    
    def _create_startup_section(self, parent_layout):
        """Create startup options section."""
        group = QGroupBox()
        self.set_translatable_text(group, "startup_options_title")
        layout = QVBoxLayout(group)
        layout.setSpacing(8)
        layout.setContentsMargins(15, 20, 15, 15)
        
        # Minimize to tray
        self.minimize_tray_check = QCheckBox()
        self.set_translatable_text(self.minimize_tray_check, "minimize_to_tray_label")
        self.minimize_tray_check.setChecked(False)
        self.minimize_tray_check.stateChanged.connect(self.on_change)
        layout.addWidget(self.minimize_tray_check)

        hotkey_row = QHBoxLayout()
        hotkey_label = QLabel("Pipeline hotkey:")
        hotkey_label.setStyleSheet("font-size: 9pt;")
        self.pipeline_hotkey_display = QLineEdit()
        self.pipeline_hotkey_display.setReadOnly(True)
        self.pipeline_hotkey_display.setText(self.pipeline_hotkey_value)
        self.pipeline_hotkey_display.setToolTip(
            "Shortcut used to trigger pipeline action "
            "(text/audio: start-stop, vision: one-shot frame)."
        )
        self.pipeline_hotkey_button = QPushButton("Change...")
        self.pipeline_hotkey_button.clicked.connect(self._show_pipeline_hotkey_dialog)
        hotkey_row.addWidget(hotkey_label)
        hotkey_row.addWidget(self.pipeline_hotkey_display, 1)
        hotkey_row.addWidget(self.pipeline_hotkey_button)
        layout.addLayout(hotkey_row)

        screenshot_row = QHBoxLayout()
        screenshot_label = QLabel("Screenshot hotkey:")
        screenshot_label.setStyleSheet("font-size: 9pt;")
        self.screenshot_hotkey_display = QLineEdit()
        self.screenshot_hotkey_display.setReadOnly(True)
        self.screenshot_hotkey_display.setText(self.screenshot_hotkey_value)
        self.screenshot_hotkey_display.setToolTip(
            "Captures the region with overlays visible and copies to clipboard."
        )
        self.screenshot_hotkey_button = QPushButton("Change...")
        self.screenshot_hotkey_button.clicked.connect(self._show_screenshot_hotkey_dialog)
        screenshot_row.addWidget(screenshot_label)
        screenshot_row.addWidget(self.screenshot_hotkey_display, 1)
        screenshot_row.addWidget(self.screenshot_hotkey_button)
        layout.addLayout(screenshot_row)

        recording_row = QHBoxLayout()
        recording_label = QLabel("Recording flash hotkey:")
        recording_label.setStyleSheet("font-size: 9pt;")
        self.recording_flash_hotkey_display = QLineEdit()
        self.recording_flash_hotkey_display.setReadOnly(True)
        self.recording_flash_hotkey_display.setText(self.recording_flash_hotkey_value)
        self.recording_flash_hotkey_display.setToolTip(
            "Shows overlays to screen capture for 5 seconds (pipeline paused). "
            "Useful for recording demo videos."
        )
        self.recording_flash_hotkey_button = QPushButton("Change...")
        self.recording_flash_hotkey_button.clicked.connect(self._show_recording_flash_hotkey_dialog)
        recording_row.addWidget(recording_label)
        recording_row.addWidget(self.recording_flash_hotkey_display, 1)
        recording_row.addWidget(self.recording_flash_hotkey_button)
        layout.addLayout(recording_row)

        parent_layout.addWidget(group)

    def _show_pipeline_hotkey_dialog(self):
        """Open dialog to capture a new pipeline hotkey."""
        dialog = QDialog(self)
        dialog.setWindowTitle("Set pipeline hotkey")
        dialog.setModal(True)
        dialog.setMinimumWidth(420)

        layout = QVBoxLayout(dialog)
        desc = QLabel(
            "Press the key combination you want to use.\n"
            "This shortcut is active when the main window has focus."
        )
        desc.setWordWrap(True)
        layout.addWidget(desc)

        key_edit = QKeySequenceEdit(dialog)
        key_edit.setKeySequence(self.pipeline_hotkey_value)
        layout.addWidget(key_edit)

        buttons = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Ok
            | QDialogButtonBox.StandardButton.Cancel
            | QDialogButtonBox.StandardButton.RestoreDefaults
        )
        ok_btn = buttons.button(QDialogButtonBox.StandardButton.Ok)
        reset_btn = buttons.button(QDialogButtonBox.StandardButton.RestoreDefaults)
        if ok_btn:
            ok_btn.setText("Apply")
        if reset_btn:
            reset_btn.setText("Default (Ctrl+T)")
        layout.addWidget(buttons)

        buttons.accepted.connect(dialog.accept)
        buttons.rejected.connect(dialog.reject)

        def _set_default():
            key_edit.setKeySequence("Ctrl+T")

        if reset_btn:
            reset_btn.clicked.connect(_set_default)

        if dialog.exec() != QDialog.DialogCode.Accepted:
            return

        sequence = key_edit.keySequence().toString().strip()
        if not sequence:
            QMessageBox.warning(
                self,
                "Invalid hotkey",
                "Please enter a valid key combination."
            )
            return

        self.pipeline_hotkey_value = sequence
        if self.pipeline_hotkey_display:
            self.pipeline_hotkey_display.setText(sequence)
        self.on_change()

    def _show_screenshot_hotkey_dialog(self):
        """Open dialog to capture a new screenshot hotkey."""
        dialog = QDialog(self)
        dialog.setWindowTitle("Set screenshot hotkey")
        dialog.setModal(True)
        dialog.setMinimumWidth(420)

        layout = QVBoxLayout(dialog)
        desc = QLabel(
            "Press the key combination you want to use.\n"
            "Takes a screenshot of the capture region with overlays visible."
        )
        desc.setWordWrap(True)
        layout.addWidget(desc)

        key_edit = QKeySequenceEdit(dialog)
        key_edit.setKeySequence(self.screenshot_hotkey_value)
        layout.addWidget(key_edit)

        buttons = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Ok
            | QDialogButtonBox.StandardButton.Cancel
            | QDialogButtonBox.StandardButton.RestoreDefaults
        )
        ok_btn = buttons.button(QDialogButtonBox.StandardButton.Ok)
        reset_btn = buttons.button(QDialogButtonBox.StandardButton.RestoreDefaults)
        if ok_btn:
            ok_btn.setText("Apply")
        if reset_btn:
            reset_btn.setText("Default (F9)")
        layout.addWidget(buttons)

        buttons.accepted.connect(dialog.accept)
        buttons.rejected.connect(dialog.reject)

        def _set_default():
            key_edit.setKeySequence("F9")

        if reset_btn:
            reset_btn.clicked.connect(_set_default)

        if dialog.exec() != QDialog.DialogCode.Accepted:
            return

        sequence = key_edit.keySequence().toString().strip()
        if not sequence:
            QMessageBox.warning(
                self,
                "Invalid hotkey",
                "Please enter a valid key combination."
            )
            return

        self.screenshot_hotkey_value = sequence
        if self.screenshot_hotkey_display:
            self.screenshot_hotkey_display.setText(sequence)
        self.on_change()

    def _show_recording_flash_hotkey_dialog(self):
        """Open dialog to capture a new recording flash hotkey."""
        dialog = QDialog(self)
        dialog.setWindowTitle("Set recording flash hotkey")
        dialog.setModal(True)
        dialog.setMinimumWidth(420)

        layout = QVBoxLayout(dialog)
        desc = QLabel(
            "Press the key combination you want to use.\n"
            "Shows overlays in screen capture for 5 seconds (pipeline paused)."
        )
        desc.setWordWrap(True)
        layout.addWidget(desc)

        key_edit = QKeySequenceEdit(dialog)
        key_edit.setKeySequence(self.recording_flash_hotkey_value)
        layout.addWidget(key_edit)

        buttons = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Ok
            | QDialogButtonBox.StandardButton.Cancel
            | QDialogButtonBox.StandardButton.RestoreDefaults
        )
        ok_btn = buttons.button(QDialogButtonBox.StandardButton.Ok)
        reset_btn = buttons.button(QDialogButtonBox.StandardButton.RestoreDefaults)
        if ok_btn:
            ok_btn.setText("Apply")
        if reset_btn:
            reset_btn.setText("Default (F10)")
        layout.addWidget(buttons)

        buttons.accepted.connect(dialog.accept)
        buttons.rejected.connect(dialog.reject)

        def _set_default():
            key_edit.setKeySequence("F10")

        if reset_btn:
            reset_btn.clicked.connect(_set_default)

        if dialog.exec() != QDialog.DialogCode.Accepted:
            return

        sequence = key_edit.keySequence().toString().strip()
        if not sequence:
            QMessageBox.warning(
                self,
                "Invalid hotkey",
                "Please enter a valid key combination."
            )
            return

        self.recording_flash_hotkey_value = sequence
        if self.recording_flash_hotkey_display:
            self.recording_flash_hotkey_display.setText(sequence)
        self.on_change()

    def _create_manga_mode_section(self, parent_layout):
        """Create Manga mode section to reduce false triggers from mouse movement."""
        group = QGroupBox()
        self.set_translatable_text(group, "manga_mode_section_title")
        layout = QVBoxLayout(group)
        layout.setSpacing(8)
        layout.setContentsMargins(15, 20, 15, 15)
        
        # Checkbox
        self.manga_mode_check = QCheckBox()
        self.set_translatable_text(self.manga_mode_check, "manga_mode_label")
        self.set_translatable_text(
            self.manga_mode_check,
            "manga_mode_tooltip", method="setToolTip",
        )
        self.manga_mode_check.setChecked(False)
        self.manga_mode_check.stateChanged.connect(self.on_change)
        layout.addWidget(self.manga_mode_check)
        
        # Description
        description = QLabel()
        self.set_translatable_text(description, "manga_mode_description")
        description.setWordWrap(True)
        description.setStyleSheet("color: #888888; font-size: 8pt; margin-top: 4px;")
        layout.addWidget(description)
        
        parent_layout.addWidget(group)
    
    def _create_pytorch_section(self, parent_layout):
        """Create PyTorch version manager section."""
        group = QGroupBox()
        self.set_translatable_text(group, "pytorch_version_manager_title")
        layout = QVBoxLayout(group)
        layout.setSpacing(10)
        layout.setContentsMargins(15, 20, 15, 15)
        
        try:
            from app.utils.pytorch_manager import get_pytorch_manager, PyTorchVersion
            
            pytorch_mgr = get_pytorch_manager()
            pytorch_info = pytorch_mgr.get_pytorch_info()
            cuda_info = pytorch_mgr.check_cuda_toolkit()
            
            # Current version display
            info_layout = QFormLayout()
            info_layout.setSpacing(8)
            
            # Version
            version_label = QLabel()
            self.set_translatable_text(version_label, "pytorch_current_version_label")
            version_label.setStyleSheet("font-weight: 600; font-size: 9pt;")
            version_text = pytorch_info.get('version', tr("pytorch_not_installed")) if pytorch_info['installed'] else tr("pytorch_not_installed")
            version_value = QLabel(version_text)
            info_layout.addRow(version_label, version_value)
            
            # Type
            type_label = QLabel()
            self.set_translatable_text(type_label, "pytorch_type_label")
            type_label.setStyleSheet("font-weight: 600; font-size: 9pt;")
            type_text = pytorch_info.get('type', tr("pytorch_type_unknown"))
            type_value = QLabel(type_text)
            if pytorch_info.get('cuda_available'):
                type_value.setStyleSheet("color: #4CAF50; font-weight: 500;")
            else:
                type_value.setStyleSheet("color: #FF9800; font-weight: 500;")
            info_layout.addRow(type_label, type_value)
            
            # GPU info if available
            if pytorch_info.get('cuda_available') and pytorch_info.get('devices'):
                gpu_label = QLabel()
                self.set_translatable_text(gpu_label, "pytorch_gpu_label")
                gpu_label.setStyleSheet("font-weight: 600; font-size: 9pt;")
                gpu_text = pytorch_info['devices'][0]['name']
                gpu_value = QLabel(gpu_text)
                gpu_value.setStyleSheet("font-size: 9pt;")
                info_layout.addRow(gpu_label, gpu_value)
            
            # CUDA Toolkit info
            if cuda_info['installed']:
                cuda_label = QLabel()
                self.set_translatable_text(cuda_label, "pytorch_cuda_toolkit_label")
                cuda_label.setStyleSheet("font-weight: 600; font-size: 9pt;")
                cuda_text = ', '.join(cuda_info['versions'][:2]) if cuda_info['versions'] else 'Installed'
                cuda_value = QLabel(cuda_text)
                cuda_value.setStyleSheet("font-size: 9pt;")
                info_layout.addRow(cuda_label, cuda_value)
            
            # CUDA installation path (user-selectable for portability)
            path_label = QLabel()
            self.set_translatable_text(path_label, "cuda_path_label")
            path_label.setStyleSheet("font-weight: 600; font-size: 9pt;")
            self.cuda_path_edit = QLineEdit()
            self.cuda_path_edit.setReadOnly(True)
            self.cuda_path_edit.setPlaceholderText(tr("cuda_path_hint"))
            self.cuda_path_edit.setStyleSheet("font-size: 9pt;")
            _path = self.config_manager.get_installation_info().get('cuda', {}).get('path', '') or ''
            self.cuda_path_edit.setText(_path)
            cuda_browse_btn = QPushButton()
            self.set_translatable_text(cuda_browse_btn, "cuda_path_browse")
            cuda_browse_btn.setProperty("class", "action")
            cuda_browse_btn.clicked.connect(self._on_cuda_path_browse)
            path_row = QHBoxLayout()
            path_row.addWidget(self.cuda_path_edit)
            path_row.addWidget(cuda_browse_btn)
            info_layout.addRow(path_label, path_row)
            
            layout.addLayout(info_layout)
            cuda_hint = QLabel()
            self.set_translatable_text(cuda_hint, "cuda_path_hint_long")
            cuda_hint.setWordWrap(True)
            cuda_hint.setStyleSheet("color: #666666; font-size: 8pt; margin-top: 4px;")
            layout.addWidget(cuda_hint)
            
            # Version selector
            self._create_pytorch_selector(layout, pytorch_mgr, cuda_info)
            
        except Exception as e:
            # Show error if PyTorch manager unavailable
            error_label = QLabel()
            self.set_translatable_text(error_label, "pytorch_unavailable", error=str(e))
            error_label.setStyleSheet("color: #F44336; font-size: 9pt;")
            error_label.setWordWrap(True)
            layout.addWidget(error_label)
        
        parent_layout.addWidget(group)
    
    def _create_pytorch_selector(self, parent_layout, pytorch_mgr, cuda_info):
        """Create PyTorch version selector."""
        # Selector layout
        selector_layout = QHBoxLayout()
        selector_layout.setSpacing(10)
        
        # Label
        switch_label = QLabel()
        self.set_translatable_text(switch_label, "pytorch_switch_to_label")
        switch_label.setStyleSheet("font-weight: 600; font-size: 9pt;")
        selector_layout.addWidget(switch_label)
        
        # Version combo box
        self.pytorch_version_combo = QComboBox()
        version_options = ["CPU-only (Lightweight)"]
        
        if cuda_info['installed']:
            if any('v12.4' in v or 'v13' in v for v in cuda_info.get('versions', [])):
                version_options.append("CUDA 12.4 (Latest)")
            if any('v12' in v for v in cuda_info.get('versions', [])):
                version_options.append("CUDA 12.1 (Stable)")
            if any('v11.8' in v for v in cuda_info.get('versions', [])):
                version_options.append("CUDA 11.8 (Legacy)")
        
        self.pytorch_version_combo.addItems(version_options)
        self.pytorch_version_combo.setMinimumWidth(200)
        
        # Set current selection based on installed PyTorch version
        pytorch_info = pytorch_mgr.get_pytorch_info()
        if pytorch_info.get('installed') and pytorch_info.get('cuda_available'):
            cuda_version = pytorch_info.get('cuda_version', '')
            if cuda_version:
                # Map CUDA version to combo box option
                if '12.4' in cuda_version or '13' in cuda_version:
                    self.pytorch_version_combo.setCurrentText("CUDA 12.4 (Latest)")
                elif '12.1' in cuda_version or '12.2' in cuda_version or '12.3' in cuda_version:
                    self.pytorch_version_combo.setCurrentText("CUDA 12.1 (Stable)")
                elif '11.8' in cuda_version:
                    self.pytorch_version_combo.setCurrentText("CUDA 11.8 (Legacy)")
        
        selector_layout.addWidget(self.pytorch_version_combo)
        
        # Switch button
        self.pytorch_switch_btn = QPushButton()
        self.set_translatable_text(self.pytorch_switch_btn, "pytorch_switch_button")
        self.pytorch_switch_btn.setProperty("class", "action")
        self.pytorch_switch_btn.clicked.connect(lambda: self._switch_pytorch(pytorch_mgr))
        selector_layout.addWidget(self.pytorch_switch_btn)
        
        selector_layout.addStretch()
        parent_layout.addLayout(selector_layout)
        
        # Help text
        help_label = QLabel()
        self.set_translatable_text(help_label, "pytorch_compatibility_note")
        help_label.setWordWrap(True)
        help_label.setStyleSheet("color: #666666; font-size: 9pt; margin-top: 10px;")
        parent_layout.addWidget(help_label)
    
    def _on_cuda_path_browse(self):
        """Let user select CUDA toolkit root folder; validate and save if valid."""
        from app.utils.cuda_path_utils import validate_cuda_installation, get_cuda_path_hint
        if not self.config_manager:
            return
        start_dir = self.cuda_path_edit.text().strip() or get_cuda_path_hint()
        caption = tr("cuda_path_browse_title")
        folder = QFileDialog.getExistingDirectory(self, caption, start_dir)
        if not folder:
            return
        valid, msg = validate_cuda_installation(folder)
        if not valid:
            QMessageBox.warning(
                self,
                tr("cuda_path_invalid_title"),
                tr("cuda_path_invalid_message", message=msg),
            )
            return
        install_info = self.config_manager.get_installation_info()
        install_info = dict(install_info) if install_info else {}
        cuda_info = dict(install_info.get('cuda', {}) or {})
        cuda_info['path'] = folder
        install_info['cuda'] = cuda_info
        self.config_manager.set_installation_info(install_info)
        self.config_manager.save_config()
        self.cuda_path_edit.setText(folder)
        QMessageBox.information(
            self,
            tr("cuda_path_saved_title"),
            tr("cuda_path_saved_message"),
        )
        self.on_change()
    
    def _switch_pytorch(self, pytorch_mgr):
        """Handle PyTorch version switching."""
        try:
            from app.utils.pytorch_manager import PyTorchVersion
            
            selected = self.pytorch_version_combo.currentText()
            
            # Map selection to version type
            version_map = {
                "CPU-only (Lightweight)": (PyTorchVersion.CPU, "~800 MB", "CPU-only version (no GPU support)"),
                "CUDA 11.8 (Legacy)": (PyTorchVersion.CUDA_118, "~2.5 GB", "For CUDA 11.8 compatible GPUs"),
                "CUDA 12.1 (Stable)": (PyTorchVersion.CUDA_121, "~2.5 GB", "For CUDA 12.x compatible GPUs (Recommended)"),
                "CUDA 12.4 (Latest)": (PyTorchVersion.CUDA_124, "~2.5 GB", "Latest CUDA support")
            }
            
            if selected not in version_map:
                QMessageBox.critical(self, tr("error"), tr("pytorch_invalid_version_selected"))
                return
            
            version_type, download_size, description = version_map[selected]
            
            # Show confirmation dialog
            msg = QMessageBox(self)
            msg.setIcon(QMessageBox.Icon.Warning)
            msg.setWindowTitle(tr("_download_warning"))
            msg.setText(f"Selected Version: {selected}")
            msg.setInformativeText(
                f"Download Size: {download_size}\n"
                f"Description: {description}\n\n"
                f"This will:\n"
                f"  1. Uninstall current PyTorch (~1 minute)\n"
                f"  2. Download new version ({download_size})\n"
                f"  3. Install packages (~2-3 minutes)\n\n"
                f"Total time: 3-5 minutes\n"
                f"Internet connection required\n\n"
                f"⚠️ Do not close the application during installation!"
            )
            msg.setStandardButtons(QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No)
            msg.setDefaultButton(QMessageBox.StandardButton.No)
            
            result = msg.exec()
            
            if result == QMessageBox.StandardButton.Yes:
                self._show_pytorch_install_progress(pytorch_mgr, version_type)
                
        except Exception as e:
            QMessageBox.critical(self, tr("error"), tr("pytorch_switch_failed_message", error=str(e)))
    
    def _show_pytorch_install_progress(self, pytorch_mgr, version_type):
        """Show PyTorch installation progress dialog with detailed feedback."""
        # Create progress dialog with indeterminate progress bar
        progress = QProgressDialog("Initializing PyTorch installation...", None, 0, 0, self)
        progress.setWindowTitle(tr("installing_pytorch"))
        progress.setWindowModality(Qt.WindowModality.WindowModal)
        progress.setMinimumDuration(0)
        progress.setAutoClose(False)
        progress.setAutoReset(False)
        progress.setCancelButton(None)  # No cancel button during installation
        progress.setMinimumWidth(600)
        progress.setMinimumHeight(120)
        
        # Style the progress dialog
        progress.setStyleSheet("""
            QProgressDialog {
                font-size: 9pt;
            }
            QProgressDialog QLabel {
                font-size: 9pt;
                padding: 10px;
            }
            QProgressBar {
                border: 1px solid #D0D0D0;
                border-radius: 3px;
                text-align: center;
                background-color: #F5F5F5;
            }
            QProgressBar::chunk {
                background-color: #2196F3;
            }
        """)
        
        progress.show()
        
        # Create worker thread for installation
        class InstallWorker(QThread):
            """Worker thread for PyTorch installation to keep UI responsive."""
            progress_update = pyqtSignal(str)
            finished_signal = pyqtSignal(bool, str)
            
            def __init__(self, mgr, ver_type):
                super().__init__()
                self.mgr = mgr
                self.ver_type = ver_type
            
            def run(self):
                """Run the installation in background thread."""
                try:
                    self.progress_update.emit("🔄 Starting PyTorch version switch...")
                    success, message = self.mgr.switch_version(
                        self.ver_type,
                        callback=lambda msg: self.progress_update.emit(msg)
                    )
                    self.finished_signal.emit(success, message)
                except Exception as e:
                    import traceback
                    error_details = f"{str(e)}\n\n{traceback.format_exc()}"
                    self.finished_signal.emit(False, error_details)
        
        # Create and configure worker
        worker = InstallWorker(pytorch_mgr, version_type)
        
        def update_progress(message):
            """Update progress dialog with current status message."""
            # Truncate long messages and add ellipsis
            display_message = message[:150] + "..." if len(message) > 150 else message
            progress.setLabelText(display_message)
            # Force UI update
            QApplication.processEvents()
        
        def on_finished(success, message):
            """Handle installation completion."""
            progress.close()
            
            if success:
                # Show success message
                success_box = QMessageBox(self)
                success_box.setIcon(QMessageBox.Icon.Information)
                success_box.setWindowTitle(tr("_installation_successful"))
                success_box.setText(tr("pytorch_has_been_successfully_installed"))
                success_box.setInformativeText(
                    f"{message}\n\n"
                    f"Please restart the application for changes to take effect.\n\n"
                    f"The new PyTorch version will be active after restart."
                )
                success_box.setStandardButtons(QMessageBox.StandardButton.Ok)
                success_box.exec()
            else:
                # Show error message with details
                error_box = QMessageBox(self)
                error_box.setIcon(QMessageBox.Icon.Critical)
                error_box.setWindowTitle(tr("_installation_failed"))
                error_box.setText(tr("failed_to_switch_pytorch_version"))
                error_box.setInformativeText(
                    "The installation process encountered an error.\n\n"
                    "Please check your internet connection and try again.\n"
                    "If the problem persists, you may need to install PyTorch manually."
                )
                error_box.setDetailedText(message)
                error_box.setStandardButtons(QMessageBox.StandardButton.Ok)
                error_box.exec()
        
        # Connect signals
        worker.progress_update.connect(update_progress)
        worker.finished_signal.connect(on_finished)
        
        # Start installation in background thread
        worker.start()
        
        # Keep reference to worker to prevent garbage collection
        self._install_worker = worker
    
    def load_config(self):
        """Load configuration from config manager."""
        if not self.config_manager:
            return
        
        try:
            # Load runtime mode
            runtime_mode = self.config_manager.get_setting('performance.runtime_mode', 'auto')
            mode_map = {'auto': 0, 'gpu': 1, 'cpu': 2}
            button_id = mode_map.get(runtime_mode.lower(), 0)
            
            if button_id == 0:
                self.runtime_auto_radio.setChecked(True)
            elif button_id == 1:
                self.runtime_gpu_radio.setChecked(True)
            elif button_id == 2:
                self.runtime_cpu_radio.setChecked(True)
            
            # Load languages
            source_lang = self.config_manager.get_setting('translation.source_language', 'en')
            target_lang = self.config_manager.get_setting('translation.target_language', 'de')
            
            lang_names = {
                'en': 'English', 'de': 'German', 'es': 'Spanish', 'fr': 'French',
                'ja': 'Japanese', 'zh': 'Chinese', 'ko': 'Korean', 'ru': 'Russian',
                'it': 'Italian', 'pt': 'Portuguese', 'nl': 'Dutch', 'pl': 'Polish',
                'auto': 'Auto-Detect'
            }
            
            source_name = lang_names.get(source_lang, source_lang.capitalize())
            target_name = lang_names.get(target_lang, target_lang.capitalize())
            
            # Set combo box values
            source_index = self.source_lang_combo.findText(source_name)
            if source_index >= 0:
                self.source_lang_combo.setCurrentIndex(source_index)
            
            target_index = self.target_lang_combo.findText(target_name)
            if target_index >= 0:
                self.target_lang_combo.setCurrentIndex(target_index)
            
            # Load startup options
            minimize_tray = self.config_manager.get_setting('startup.minimize_to_tray', False)
            self.minimize_tray_check.setChecked(minimize_tray)
            self.pipeline_hotkey_value = self.config_manager.get_setting(
                'general.pipeline_toggle_hotkey', 'Ctrl+T'
            ) or 'Ctrl+T'
            if self.pipeline_hotkey_display is not None:
                self.pipeline_hotkey_display.setText(self.pipeline_hotkey_value)

            self.screenshot_hotkey_value = self.config_manager.get_setting(
                'general.screenshot_hotkey', 'F9'
            ) or 'F9'
            if self.screenshot_hotkey_display is not None:
                self.screenshot_hotkey_display.setText(self.screenshot_hotkey_value)

            self.recording_flash_hotkey_value = self.config_manager.get_setting(
                'general.recording_flash_hotkey', 'F10'
            ) or 'F10'
            if self.recording_flash_hotkey_display is not None:
                self.recording_flash_hotkey_display.setText(self.recording_flash_hotkey_value)

            # Load manga mode
            manga_mode = self.config_manager.get_setting('general.manga_mode', False)
            if self.manga_mode_check is not None:
                self.manga_mode_check.setChecked(manga_mode)
            
            # Load UI language
            ui_lang = self.config_manager.get_setting('ui.language', 'en')
            ui_lang_map = {
                'en': 'English',
                'de': 'Deutsch (German)',
                'fr': 'Français (French)',
                'it': 'Italiano (Italian)',
                'ja': '日本語 (Japanese)'
            }
            ui_lang_name = ui_lang_map.get(ui_lang, 'English')
            ui_lang_index = self.ui_lang_combo.findText(ui_lang_name)
            if ui_lang_index >= 0:
                self.ui_lang_combo.blockSignals(True)
                self.ui_lang_combo.setCurrentIndex(ui_lang_index)
                self.ui_lang_combo.blockSignals(False)
            
            # Save the original state after loading
            self._original_state = self._get_current_state()
            
            # After first load, mark as no longer first load
            # This prevents the language change dialog from showing on startup
            self._is_first_load = False
            
            logger.debug("General tab configuration loaded")
            
        except Exception as e:
            logger.warning("Failed to load general tab config: %s", e, exc_info=True)
    
    def save_config(self):
        """
        Save configuration to config manager.
        
        Returns:
            tuple: (success: bool, error_message: str)
        """
        if not self.config_manager:
            return False, "Configuration manager not available"
        
        try:
            # Store original values for rollback
            old_minimize_to_tray = self.config_manager.get_setting('startup.minimize_to_tray', False)
            
            # Save runtime mode
            if self.runtime_auto_radio.isChecked():
                runtime_mode = 'auto'
            elif self.runtime_gpu_radio.isChecked():
                runtime_mode = 'gpu'
            else:
                runtime_mode = 'cpu'
            
            self.config_manager.set_setting('performance.runtime_mode', runtime_mode)
            
            # Notify the hardware capability gate about the mode change
            try:
                gate = get_hardware_gate(self.config_manager)
                gate.on_runtime_mode_changed(runtime_mode)
            except Exception as e:
                logger.warning("Failed to notify hardware gate of mode change: %s", e)
            
            # Save languages
            lang_codes = {
                'English': 'en', 'German': 'de', 'Spanish': 'es', 'French': 'fr',
                'Japanese': 'ja', 'Chinese': 'zh', 'Korean': 'ko', 'Russian': 'ru',
                'Italian': 'it', 'Portuguese': 'pt', 'Dutch': 'nl', 'Polish': 'pl',
                'Auto-Detect': 'auto'
            }
            
            source_lang = lang_codes.get(self.source_lang_combo.currentText(), 'en')
            target_lang = lang_codes.get(self.target_lang_combo.currentText(), 'de')
            
            self.config_manager.set_setting('translation.source_language', source_lang)
            self.config_manager.set_setting('translation.target_language', target_lang)
            
            # Save startup options
            minimize_to_tray = self.minimize_tray_check.isChecked()
            
            self.config_manager.set_setting('startup.minimize_to_tray', minimize_to_tray)
            self.config_manager.set_setting(
                'general.pipeline_toggle_hotkey',
                (self.pipeline_hotkey_value or 'Ctrl+T').strip() or 'Ctrl+T'
            )
            self.config_manager.set_setting(
                'general.screenshot_hotkey',
                (self.screenshot_hotkey_value or 'F9').strip() or 'F9'
            )
            self.config_manager.set_setting(
                'general.recording_flash_hotkey',
                (self.recording_flash_hotkey_value or 'F10').strip() or 'F10'
            )

            # Save manga mode
            if self.manga_mode_check is not None:
                self.config_manager.set_setting(
                    'general.manga_mode',
                    self.manga_mode_check.isChecked(),
                )
            
            # Update system tray if main window has tray manager (before saving to disk)
            try:
                main_window = self.window()
                if hasattr(main_window, 'tray_manager') and main_window.tray_manager:
                    main_window.tray_manager.set_enabled(minimize_to_tray)
            except Exception as e:
                logger.warning("Failed to update system tray: %s", e)
            
            # Save UI language
            ui_lang_map = {
                'English': 'en',
                'Deutsch (German)': 'de',
                'Français (French)': 'fr',
                'Italiano (Italian)': 'it',
                'Türkçe (Turkish)': 'tr',
                '日本語 (Japanese)': 'ja'
            }
            ui_lang = ui_lang_map.get(self.ui_lang_combo.currentText(), 'en')
            old_lang = self.config_manager.get_setting('ui.language', 'en')
            self.config_manager.set_setting('ui.language', ui_lang)
            
            # Apply language change immediately if it changed
            if ui_lang != old_lang:
                try:
                    from app.localization import set_language
                    
                    # Get the language name before changing
                    language_name = self.ui_lang_combo.currentText()
                    
                    # Change the language
                    set_language(ui_lang)
                    logger.info("UI language changed to: %s", ui_lang)
                    logger.debug("Language change - old: %s, new: %s, first_load: %s", old_lang, ui_lang, self._is_first_load)
                    
                    # Only show dialog if this is not the first load (user actively changed it)
                    if not self._is_first_load:
                        logger.debug("Showing language change dialog")
                        # Notify user that UI will update (using NEW language)
                        QMessageBox.information(
                            self,
                            tr("language_changed_title"),
                            tr("language_changed_message", language=language_name)
                        )
                    else:
                        logger.debug("Skipping language change dialog (first load)")
                except Exception as e:
                    logger.warning("Failed to apply language change: %s", e)
            
            # Save the configuration file to disk
            success, error_msg = self.config_manager.save_config()
            
            if not success:
                # Rollback system tray state if save failed
                try:
                    main_window = self.window()
                    if hasattr(main_window, 'tray_manager') and main_window.tray_manager:
                        main_window.tray_manager.set_enabled(old_minimize_to_tray)
                        self.minimize_tray_check.setChecked(old_minimize_to_tray)
                except Exception as e:
                    logger.warning("Failed to rollback system tray: %s", e)
                
                return False, error_msg
            
            # Update original state after successful save
            self._original_state = self._get_current_state()
            
            logger.info("General tab configuration saved")
            return True, ""
            
        except Exception as e:
            error_msg = f"Failed to save settings: {e}"
            logger.error(error_msg, exc_info=True)
            return False, error_msg
    
    def validate(self) -> bool:
        """
        Validate settings.
        
        Returns:
            True if settings are valid, False otherwise
        """
        # General tab has no specific validation requirements
        # All selections are from dropdowns/radio buttons, so they're always valid
        return True
    
    def set_language_lock(self, locked: bool):
        """
        Lock or unlock the source language dropdown.
        Only the OCR source language is locked when an engine supports a
        single language (e.g. Manga OCR → Japanese).  The target
        translation language always remains editable.
        """
        if self.source_lang_combo:
            self.source_lang_combo.setEnabled(not locked)
            
            if locked:
                self.source_lang_combo.setToolTip(tr("general_source_lang_locked_tooltip"))
                self.source_lang_combo.setStyleSheet(
                    "QComboBox:disabled { background-color: #F0F0F0; color: #666666; }"
                )
            else:
                self.source_lang_combo.setToolTip(tr("general_source_lang_tooltip"))
                self.source_lang_combo.setStyleSheet("")
