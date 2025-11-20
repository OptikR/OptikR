"""
General Settings Tab - PyQt6 Implementation
Language, runtime, and startup configuration.
"""

from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QFormLayout, QGroupBox,
    QLabel, QComboBox, QRadioButton, QCheckBox, QPushButton,
    QButtonGroup, QMessageBox, QProgressDialog, QApplication
)
from PyQt6.QtCore import Qt, pyqtSignal, QThread

# Import custom scroll area
from .scroll_area_no_wheel import ScrollAreaNoWheel

# Import translation system
from app.translations import TranslatableMixin


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
        self.start_windows_check = None
        self.minimize_tray_check = None
        
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
    
    def _create_restart_indicator(self, restart_type: str = "pipeline") -> QLabel:
        """
        Create a visual restart indicator.
        
        Args:
            restart_type: "instant", "pipeline", or "app"
        """
        if restart_type == "instant":
            icon = "✅"
            text = "Takes effect immediately"
            color = "#4CAF50"  # Green
            bg_color = "rgba(76, 175, 80, 0.1)"
        elif restart_type == "pipeline":
            icon = "🔄"
            text = "Requires pipeline restart (Stop → Start translation)"
            color = "#FF9800"  # Orange
            bg_color = "rgba(255, 152, 0, 0.1)"
        else:  # app
            icon = "⚠️"
            text = "Requires app restart (Close → Reopen application)"
            color = "#F44336"  # Red
            bg_color = "rgba(244, 67, 54, 0.1)"
        
        label = QLabel(f"{icon} {text}")
        label.setWordWrap(True)
        label.setStyleSheet(
            f"color: {color}; "
            f"font-size: 8pt; "
            f"margin-top: 5px; "
            f"padding: 6px 10px; "
            f"background-color: {bg_color}; "
            f"border-radius: 4px; "
            f"border-left: 3px solid {color};"
        )
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
        if self.start_windows_check:
            state['start_windows'] = self.start_windows_check.isChecked()
        if self.minimize_tray_check:
            state['minimize_tray'] = self.minimize_tray_check.isChecked()
        
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
            'Türkçe (Turkish)': 'tr',
            '日本語 (Japanese)': 'ja'
        }
        
        lang_code = lang_map.get(language_name, 'en')
        
        # Update translation system immediately for new dialogs
        try:
            from app.translations import get_language_manager, tr
            
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
            'Türkçe (Turkish)',
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
        
        # Restart indicator
        restart_note = QLabel()
        self.set_translatable_text(restart_note, "language_restart_note")
        restart_note.setWordWrap(True)
        restart_note.setStyleSheet(
            "color: #FF9800; "
            "font-size: 8pt; "
            "margin-top: 5px; "
            "padding: 6px 10px; "
            "background-color: rgba(255, 152, 0, 0.1); "
            "border-radius: 4px; "
            "border-left: 3px solid #FF9800;"
        )
        layout.addWidget(restart_note)
        
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
        
        # Restart indicator
        restart_note = QLabel()
        self.set_translatable_text(restart_note, "runtime_restart_note")
        restart_note.setWordWrap(True)
        restart_note.setStyleSheet(
            "color: #FF9800; "
            "font-size: 8pt; "
            "margin-top: 5px; "
            "padding: 6px 10px; "
            "background-color: rgba(255, 152, 0, 0.1); "
            "border-radius: 4px; "
            "border-left: 3px solid #FF9800;"
        )
        layout.addWidget(restart_note)
        
        parent_layout.addWidget(group)
    
    def _create_startup_section(self, parent_layout):
        """Create startup options section."""
        group = QGroupBox()
        self.set_translatable_text(group, "startup_options_title")
        layout = QVBoxLayout(group)
        layout.setSpacing(8)
        layout.setContentsMargins(15, 20, 15, 15)
        
        # Start with Windows
        self.start_windows_check = QCheckBox()
        self.set_translatable_text(self.start_windows_check, "start_with_windows_label")
        self.start_windows_check.stateChanged.connect(self.on_change)
        layout.addWidget(self.start_windows_check)
        
        # Minimize to tray
        self.minimize_tray_check = QCheckBox()
        self.set_translatable_text(self.minimize_tray_check, "minimize_to_tray_label")
        self.minimize_tray_check.setChecked(True)
        self.minimize_tray_check.stateChanged.connect(self.on_change)
        layout.addWidget(self.minimize_tray_check)
        
        # Restart indicator
        restart_note = QLabel()
        self.set_translatable_text(restart_note, "startup_instant_note")
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
    

    
    def _create_pytorch_section(self, parent_layout):
        """Create PyTorch version manager section."""
        group = QGroupBox()
        self.set_translatable_text(group, "pytorch_version_manager_title")
        layout = QVBoxLayout(group)
        layout.setSpacing(10)
        layout.setContentsMargins(15, 20, 15, 15)
        
        try:
            # Try to import PyTorch manager
            import sys
            import os
            sys.path.insert(0, os.path.join(os.path.dirname(__file__), '../..'))
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
            version_text = pytorch_info.get('version', 'Not installed') if pytorch_info['installed'] else 'Not installed'
            version_value = QLabel(version_text)
            info_layout.addRow(version_label, version_value)
            
            # Type
            type_label = QLabel()
            self.set_translatable_text(type_label, "pytorch_type_label")
            type_label.setStyleSheet("font-weight: 600; font-size: 9pt;")
            type_text = pytorch_info.get('type', 'Unknown')
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
            
            layout.addLayout(info_layout)
            
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
                QMessageBox.critical(self, "Error", "Invalid version selected")
                return
            
            version_type, download_size, description = version_map[selected]
            
            # Show confirmation dialog
            msg = QMessageBox(self)
            msg.setIcon(QMessageBox.Icon.Warning)
            msg.setWindowTitle("⚠️ Download Warning")
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
            QMessageBox.critical(self, "Error", f"Failed to switch PyTorch version:\n\n{str(e)}")
    
    def _show_pytorch_install_progress(self, pytorch_mgr, version_type):
        """Show PyTorch installation progress dialog with detailed feedback."""
        # Create progress dialog with indeterminate progress bar
        progress = QProgressDialog("Initializing PyTorch installation...", None, 0, 0, self)
        progress.setWindowTitle("Installing PyTorch")
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
                success_box.setWindowTitle("✅ Installation Successful")
                success_box.setText("PyTorch has been successfully installed!")
                success_box.setInformativeText(
                    f"{message}\n\n"
                    f"Please restart the application for changes to take effect.\n\n"
                    f"The new PyTorch version will be active after restart."
                )
                success_box.setStandardButtons(QMessageBox.StandardButton.Ok)
                success_box.exec()
                
                # Update GPU config if switching to CUDA
                import os
                if version_type.name != 'CPU':
                    os.system('python toggle_gpu.py on')
                else:
                    os.system('python toggle_gpu.py off')
            else:
                # Show error message with details
                error_box = QMessageBox(self)
                error_box.setIcon(QMessageBox.Icon.Critical)
                error_box.setWindowTitle("❌ Installation Failed")
                error_box.setText("Failed to switch PyTorch version")
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
            start_windows = self.config_manager.get_setting('startup.start_with_windows', False)
            minimize_tray = self.config_manager.get_setting('startup.minimize_to_tray', True)
            
            self.start_windows_check.setChecked(start_windows)
            self.minimize_tray_check.setChecked(minimize_tray)
            
            # Load UI language
            ui_lang = self.config_manager.get_setting('ui.language', 'en')
            ui_lang_map = {
                'en': 'English',
                'de': 'Deutsch (German)',
                'fr': 'Français (French)',
                'it': 'Italiano (Italian)',
                'tr': 'Türkçe (Turkish)',
                'ja': '日本語 (Japanese)'
            }
            ui_lang_name = ui_lang_map.get(ui_lang, 'English')
            ui_lang_index = self.ui_lang_combo.findText(ui_lang_name)
            if ui_lang_index >= 0:
                self.ui_lang_combo.setCurrentIndex(ui_lang_index)
            
            # Save the original state after loading
            self._original_state = self._get_current_state()
            
            # After first load, mark as no longer first load
            # This prevents the language change dialog from showing on startup
            self._is_first_load = False
            
            print("[DEBUG] General tab configuration loaded")
            
        except Exception as e:
            print(f"[WARNING] Failed to load general tab config: {e}")
            import traceback
            traceback.print_exc()
    
    def save_config(self):
        """Save configuration to config manager."""
        if not self.config_manager:
            return
        
        try:
            # Save runtime mode
            if self.runtime_auto_radio.isChecked():
                runtime_mode = 'auto'
            elif self.runtime_gpu_radio.isChecked():
                runtime_mode = 'gpu'
            else:
                runtime_mode = 'cpu'
            
            self.config_manager.set_setting('performance.runtime_mode', runtime_mode)
            
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
            start_with_windows = self.start_windows_check.isChecked()
            minimize_to_tray = self.minimize_tray_check.isChecked()
            
            self.config_manager.set_setting('startup.start_with_windows', start_with_windows)
            self.config_manager.set_setting('startup.minimize_to_tray', minimize_to_tray)
            
            # Apply Windows startup setting immediately
            try:
                from app.utils.windows_startup import set_windows_startup
                set_windows_startup(start_with_windows)
            except Exception as e:
                print(f"[WARNING] Failed to update Windows startup: {e}")
            
            # Update system tray if main window has tray manager
            try:
                main_window = self.window()
                if hasattr(main_window, 'tray_manager') and main_window.tray_manager:
                    main_window.tray_manager.set_enabled(minimize_to_tray)
            except Exception as e:
                print(f"[WARNING] Failed to update system tray: {e}")
            
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
                    from app.translations import set_language, tr
                    
                    # Get the language name before changing
                    language_name = self.ui_lang_combo.currentText()
                    
                    # Change the language
                    set_language(ui_lang)
                    print(f"[INFO] UI language changed to: {ui_lang}")
                    print(f"[DEBUG] Language change - old: {old_lang}, new: {ui_lang}, first_load: {self._is_first_load}")
                    
                    # Only show dialog if this is not the first load (user actively changed it)
                    if not self._is_first_load:
                        print("[DEBUG] Showing language change dialog")
                        # Notify user that UI will update (using NEW language)
                        from PyQt6.QtWidgets import QMessageBox
                        QMessageBox.information(
                            self,
                            tr("language_changed_title"),
                            tr("language_changed_message", language=language_name)
                        )
                    else:
                        print("[DEBUG] Skipping language change dialog (first load)")
                except Exception as e:
                    print(f"[WARNING] Failed to apply language change: {e}")
            
            # Save the configuration file
            # Handle both MockConfigManager (save_config) and real ConfigurationManager (save_configuration)
            if hasattr(self.config_manager, 'save_config'):
                self.config_manager.save_config()
            elif hasattr(self.config_manager, 'save_configuration'):
                config_dict = self.config_manager._config_to_dict(self.config_manager._config)
                self.config_manager.save_configuration(config_dict)
            
            # Update original state after saving
            self._original_state = self._get_current_state()
            
            print("[INFO] General tab configuration saved")
            
        except Exception as e:
            print(f"[ERROR] Failed to save general tab config: {e}")
            import traceback
            traceback.print_exc()
    
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
        Lock or unlock language selection dropdowns.
        Used when Manga OCR is selected (locks to Japanese → English).
        
        Args:
            locked: True to disable dropdowns, False to enable
        """
        if self.source_lang_combo:
            self.source_lang_combo.setEnabled(not locked)
            
            if locked:
                # Add visual indicator and tooltip
                self.source_lang_combo.setToolTip("🔒 Locked to Japanese for Manga OCR\n\nManga OCR is specialized for Japanese text.\nTo change languages, select a different OCR engine.")
                self.source_lang_combo.setStyleSheet("QComboBox:disabled { background-color: #F0F0F0; color: #666666; }")
            else:
                # Restore original tooltip
                self.source_lang_combo.setToolTip("The language of text in your game/application")
                self.source_lang_combo.setStyleSheet("")
        
        if self.target_lang_combo:
            self.target_lang_combo.setEnabled(not locked)
            
            if locked:
                # Add visual indicator and tooltip
                self.target_lang_combo.setToolTip("🔒 Locked to English for Manga OCR\n\nManga OCR is optimized for Japanese → English translation.\nTo change languages, select a different OCR engine.")
                self.target_lang_combo.setStyleSheet("QComboBox:disabled { background-color: #F0F0F0; color: #666666; }")
            else:
                # Restore original tooltip
                self.target_lang_combo.setToolTip("The language you want to translate into")
                self.target_lang_combo.setStyleSheet("")
