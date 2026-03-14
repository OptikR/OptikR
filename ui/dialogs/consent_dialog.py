"""
User Consent Dialog Module

Combined first-run dialog that handles:
1. User consent for screen capture and data processing
2. Model setup (online/offline mode)
3. Privacy policy and terms of use
"""

import logging
from pathlib import Path

from PyQt6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QCheckBox, QTextEdit, QScrollArea, QWidget, QStackedWidget,
    QRadioButton, QButtonGroup, QGroupBox, QLineEdit, QFileDialog,
    QMessageBox, QComboBox
)
from PyQt6.QtCore import Qt
from app.localization import TranslatableMixin, tr, get_available_languages, set_language, get_current_language

logger = logging.getLogger(__name__)


class UserConsentDialog(TranslatableMixin, QDialog):
    """Combined first-run dialog for consent and model setup."""
    
    def __init__(self, parent=None, config_manager=None):
        super().__init__(parent)
        self.config_manager = config_manager
        self.setWindowTitle(tr("welcome_to_optikr_first_time_setup"))
        self.setModal(True)
        self.setMinimumWidth(750)
        self.setMinimumHeight(650)
        
        self.setup_config = {}  # Store setup configuration
        
        self.init_ui()
    
    def init_ui(self):
        """Initialize the two-page dialog UI."""
        layout = QVBoxLayout(self)
        layout.setSpacing(15)
        layout.setContentsMargins(20, 20, 20, 20)
        
        # Language selector row
        lang_row = QHBoxLayout()
        lang_row.addStretch()
        lang_icon = QLabel("\U0001f310")
        lang_icon.setStyleSheet("font-size: 13pt;")
        lang_row.addWidget(lang_icon)
        self.lang_combo = QComboBox()
        self.lang_combo.setMinimumWidth(140)
        self.lang_combo.setStyleSheet("font-size: 9pt; padding: 3px 6px;")
        self._populate_language_combo()
        self.lang_combo.currentIndexChanged.connect(self._on_language_changed)
        lang_row.addWidget(self.lang_combo)
        layout.addLayout(lang_row)
        
        # Title
        self.title_label = QLabel(tr("welcome_to_optikr"))
        self.title_label.setStyleSheet("font-size: 18pt; font-weight: bold; color: #2C3E50;")
        layout.addWidget(self.title_label)
        
        # Subtitle
        self.subtitle_label = QLabel(tr("please_read_and_understand_the_following_before_us"))
        self.subtitle_label.setStyleSheet("font-size: 10pt; color: #7F8C8D; margin-bottom: 10px;")
        layout.addWidget(self.subtitle_label)
        
        # Stacked widget for two pages
        self.stacked_widget = QStackedWidget()
        
        # Page 1: Consent
        self.consent_page = self._create_consent_page()
        self.stacked_widget.addWidget(self.consent_page)
        
        # Page 2: Model Setup
        self.setup_page = self._create_setup_page()
        self.stacked_widget.addWidget(self.setup_page)
        
        layout.addWidget(self.stacked_widget)
        
        # Buttons
        self.button_layout = QHBoxLayout()
        self.button_layout.addStretch()
        
        self.decline_btn = QPushButton(tr("decline_exit"))
        self.decline_btn.setMinimumWidth(120)
        self.decline_btn.clicked.connect(self.reject)
        self.button_layout.addWidget(self.decline_btn)
        
        self.back_btn = QPushButton(tr("consent_back"))
        self.back_btn.setMinimumWidth(100)
        self.back_btn.setVisible(False)
        self.back_btn.clicked.connect(self._go_back)
        self.button_layout.addWidget(self.back_btn)
        
        self.next_btn = QPushButton(tr("accept_continue_2"))
        self.next_btn.setMinimumWidth(150)
        self.next_btn.setEnabled(False)
        self.next_btn.clicked.connect(self._go_next)
        self.button_layout.addWidget(self.next_btn)
        
        layout.addLayout(self.button_layout)
    
    def _populate_language_combo(self):
        """Fill the language dropdown with available languages."""
        available = get_available_languages()
        current = get_current_language()
        self.lang_combo.blockSignals(True)
        self.lang_combo.clear()
        current_idx = 0
        for i, (code, name) in enumerate(sorted(available.items(), key=lambda x: x[1])):
            self.lang_combo.addItem(name, code)
            if code == current:
                current_idx = i
        self.lang_combo.setCurrentIndex(current_idx)
        self.lang_combo.blockSignals(False)

    def _on_language_changed(self, index: int):
        """Switch UI language when the user picks a different language."""
        code = self.lang_combo.itemData(index)
        if code and code != get_current_language():
            set_language(code)
            self._retranslate_ui()

    def _retranslate_ui(self):
        """Refresh all visible text after a language change."""
        self.setWindowTitle(tr("welcome_to_optikr_first_time_setup"))
        if self.stacked_widget.currentIndex() == 0:
            self.title_label.setText(tr("welcome_to_optikr"))
            self.subtitle_label.setText(tr("please_read_and_understand_the_following_before_us"))
        else:
            self.title_label.setText(tr("model_setup"))
            self.subtitle_label.setText(tr("choose_how_you_want_to_set_up_ocr_and_translation_models"))
        self.decline_btn.setText(tr("decline_exit"))
        self.back_btn.setText(tr("consent_back"))
        if self.stacked_widget.currentIndex() == 0:
            self.next_btn.setText(tr("accept_continue_2"))
        else:
            self.next_btn.setText(tr("finish_setup"))
        self.consent_checkbox.setText(tr("consent_checkbox_text"))
        self.online_radio.setText(tr("consent_online_mode"))
        self.offline_radio.setText(tr("consent_offline_mode"))
        self.skip_radio.setText(tr("consent_skip_setup"))
        self.offline_inputs.setTitle(tr("consent_select_model_files"))
        # Re-render the consent HTML
        for widget in self.consent_page.findChildren(QTextEdit):
            widget.setHtml(self._get_consent_html())

    def _create_consent_page(self):
        """Create the consent page."""
        page = QWidget()
        layout = QVBoxLayout(page)
        layout.setContentsMargins(0, 0, 0, 0)
        
        # Important folder creation notice
        folder_notice = QLabel(tr("consent_folder_notice"))
        folder_notice.setWordWrap(True)
        folder_notice.setStyleSheet(
            "color: #2196F3; font-size: 9pt; padding: 10px; margin-bottom: 10px; "
            "background-color: #E3F2FD; border-left: 4px solid #2196F3; border-radius: 3px;"
        )
        layout.addWidget(folder_notice)
        
        # Scrollable consent text
        scroll_area = QScrollArea()
        scroll_area.setWidgetResizable(True)
        scroll_area.setMinimumHeight(320)
        
        consent_widget = QWidget()
        consent_layout = QVBoxLayout(consent_widget)
        
        consent_text = QTextEdit()
        consent_text.setReadOnly(True)
        consent_text.setHtml(self._get_consent_html())
        consent_layout.addWidget(consent_text)
        
        scroll_area.setWidget(consent_widget)
        layout.addWidget(scroll_area)
        
        # Consent checkbox
        self.consent_checkbox = QCheckBox(tr("consent_checkbox_text"))
        self.consent_checkbox.setStyleSheet("font-size: 10pt; font-weight: bold;")
        self.consent_checkbox.stateChanged.connect(self._on_consent_changed)
        layout.addWidget(self.consent_checkbox)
        
        return page
    
    def _create_setup_page(self):
        """Create the model setup page."""
        page = QWidget()
        layout = QVBoxLayout(page)
        layout.setContentsMargins(0, 0, 0, 0)
        
        desc = QLabel(tr("consent_setup_description"))
        desc.setStyleSheet("font-size: 10pt; margin-bottom: 10px;")
        layout.addWidget(desc)
        
        # Setup mode selection
        self.mode_group = QButtonGroup()
        
        # Option 1: Online Mode
        online_group = self._create_online_mode_group()
        layout.addWidget(online_group)
        
        # Option 2: Offline Mode
        offline_group = self._create_offline_mode_group()
        layout.addWidget(offline_group)
        
        # Option 3: Skip
        skip_group = self._create_skip_mode_group()
        layout.addWidget(skip_group)
        
        layout.addStretch()
        
        return page
    
    def _create_online_mode_group(self):
        """Create online mode option group."""
        group = QGroupBox()
        layout = QVBoxLayout(group)
        
        self.online_radio = QRadioButton(tr("consent_online_mode"))
        self.online_radio.setChecked(True)  # Default
        self.online_radio.setStyleSheet("font-weight: 600; font-size: 10pt;")
        self.mode_group.addButton(self.online_radio, 0)
        layout.addWidget(self.online_radio)
        
        desc = QLabel(tr("consent_online_desc"))
        desc.setStyleSheet("color: #666666; font-size: 9pt; margin-left: 25px;")
        layout.addWidget(desc)
        
        return group
    
    def _create_offline_mode_group(self):
        """Create offline mode option group."""
        group = QGroupBox()
        layout = QVBoxLayout(group)
        
        self.offline_radio = QRadioButton(tr("consent_offline_mode"))
        self.offline_radio.setStyleSheet("font-weight: 600; font-size: 10pt;")
        self.mode_group.addButton(self.offline_radio, 1)
        self.offline_radio.toggled.connect(self._on_offline_toggled)
        layout.addWidget(self.offline_radio)
        
        desc = QLabel(tr("consent_offline_desc"))
        desc.setStyleSheet("color: #666666; font-size: 9pt; margin-left: 25px;")
        layout.addWidget(desc)
        
        # Model file inputs (disabled by default)
        self.offline_inputs = QGroupBox(tr("consent_select_model_files"))
        self.offline_inputs.setEnabled(False)
        inputs_layout = QVBoxLayout(self.offline_inputs)
        
        # OCR model files
        ocr_label = QLabel(tr("ocr_model_files_e_g_craft_mlt_25k_pth"))
        ocr_label.setStyleSheet("font-weight: 600; margin-top: 5px;")
        inputs_layout.addWidget(ocr_label)
        
        ocr_layout = QHBoxLayout()
        self.ocr_files_input = QLineEdit()
        self.ocr_files_input.setPlaceholderText(tr("no_files_selected"))
        self.ocr_files_input.setReadOnly(True)
        ocr_layout.addWidget(self.ocr_files_input)
        ocr_browse = QPushButton(tr("select_files"))
        ocr_browse.clicked.connect(self._browse_ocr_files)
        ocr_layout.addWidget(ocr_browse)
        inputs_layout.addLayout(ocr_layout)
        
        self.ocr_files = []
        
        # Translation model folders
        trans_label = QLabel(tr("translation_model_folder_e_g_opus_mt_en_de"))
        trans_label.setStyleSheet("font-weight: 600; margin-top: 5px;")
        inputs_layout.addWidget(trans_label)
        
        trans_layout = QHBoxLayout()
        self.trans_folder_input = QLineEdit()
        self.trans_folder_input.setPlaceholderText(tr("no_folder_selected"))
        self.trans_folder_input.setReadOnly(True)
        trans_layout.addWidget(self.trans_folder_input)
        trans_browse = QPushButton(tr("select_folder"))
        trans_browse.clicked.connect(self._browse_translation_folder)
        trans_layout.addWidget(trans_browse)
        inputs_layout.addLayout(trans_layout)
        
        self.trans_folder = None
        
        layout.addWidget(self.offline_inputs)
        
        return group
    
    def _create_skip_mode_group(self):
        """Create skip option group."""
        group = QGroupBox()
        layout = QVBoxLayout(group)
        
        self.skip_radio = QRadioButton(tr("consent_skip_setup"))
        self.skip_radio.setStyleSheet("font-weight: 600; font-size: 10pt;")
        self.mode_group.addButton(self.skip_radio, 2)
        layout.addWidget(self.skip_radio)
        
        desc = QLabel(tr("consent_skip_desc"))
        desc.setStyleSheet("color: #666666; font-size: 9pt; margin-left: 25px;")
        layout.addWidget(desc)
        
        return group
    
    def _on_offline_toggled(self, checked):
        """Enable/disable offline mode inputs."""
        self.offline_inputs.setEnabled(checked)

    def _copy_offline_models(self):
        """Copy user-selected model files to the appropriate cache directories."""
        import shutil
        try:
            from app.utils.path_utils import ensure_dir, get_hf_cache_dir
            copied = 0

            if self.ocr_files:
                ocr_dest = ensure_dir("models") / "ocr_imports"
                ocr_dest.mkdir(parents=True, exist_ok=True)
                for src in self.ocr_files:
                    shutil.copy2(src, ocr_dest / Path(src).name)
                    copied += 1

            if self.trans_folder:
                hf_cache = get_hf_cache_dir()
                hf_cache.mkdir(parents=True, exist_ok=True)
                folder_name = Path(self.trans_folder).name
                dest_folder = hf_cache / folder_name
                if dest_folder.exists():
                    shutil.rmtree(dest_folder)
                shutil.copytree(self.trans_folder, dest_folder)
                copied += 1

            logger.info("Offline setup: copied %d model item(s)", copied)
            return copied > 0
        except Exception as e:
            logger.error("Failed to copy offline models: %s", e)
            QMessageBox.critical(self, tr("consent_copy_failed"), tr("consent_copy_failed_msg").format(error=e))
            return False
    
    def _browse_ocr_files(self):
        """Browse for OCR model files."""
        files, _ = QFileDialog.getOpenFileNames(
            self,
            tr("consent_select_ocr_files"),
            str(Path.home()),
            tr("model_files_filter")
        )
        
        if files:
            self.ocr_files = files
            file_names = [Path(f).name for f in files]
            display = ', '.join(file_names[:3]) + ('...' if len(files) > 3 else '')
            self.ocr_files_input.setText(tr("files_selected_count", count=len(files), names=display))
    
    def _browse_translation_folder(self):
        """Browse for translation model folder."""
        folder = QFileDialog.getExistingDirectory(
            self,
            tr("consent_select_translation_folder"),
            str(Path.home())
        )
        
        if folder:
            self.trans_folder = folder
            self.trans_folder_input.setText(Path(folder).name)
    
    def _go_back(self):
        """Go back to consent page."""
        self.stacked_widget.setCurrentIndex(0)
        self.title_label.setText(tr("welcome_to_optikr"))
        self.subtitle_label.setText(tr("please_read_and_understand_the_following_before_us"))
        self.back_btn.setVisible(False)
        self.next_btn.setText(tr("accept_continue_2"))
        self.next_btn.setEnabled(self.consent_checkbox.isChecked())
    
    def _go_next(self):
        """Go to next page or finish."""
        current_index = self.stacked_widget.currentIndex()
        
        if current_index == 0:  # Consent page
            # Move to setup page
            self.stacked_widget.setCurrentIndex(1)
            self.title_label.setText(tr("model_setup"))
            self.subtitle_label.setText(tr("choose_how_you_want_to_set_up_ocr_and_translation_models"))
            self.back_btn.setVisible(True)
            self.next_btn.setText(tr("finish_setup"))
            self.next_btn.setEnabled(True)
        else:  # Setup page
            # Process setup and finish
            self._finish_setup()
    
    def _finish_setup(self):
        """Process setup configuration and close dialog."""
        selected_id = self.mode_group.checkedId()
        
        if selected_id == 0:  # Online mode
            self.setup_config = {
                'mode': 'online',
                'offline_mode_enabled': False
            }
            self.accept()
            
        elif selected_id == 1:  # Offline mode
            # Validate file selection
            if not self.ocr_files and not self.trans_folder:
                QMessageBox.warning(
                    self,
                    tr("consent_no_files_selected"),
                    tr("consent_no_files_selected_msg")
                )
                return

            # Copy selected model files to canonical locations
            success = self._copy_offline_models()
            if success:
                self.setup_config = {
                    'mode': 'offline',
                    'offline_mode_enabled': True,
                    'models_copied': True
                }
                self.accept()
            
        elif selected_id == 2:  # Skip
            self.setup_config = {
                'mode': 'skip',
                'offline_mode_enabled': False,
                'skip_setup': True
            }
            self.accept()
    
    def _get_consent_html(self):
        """Get the consent text in HTML format."""
        return tr("consent_html")
    
    def _on_consent_changed(self, state):
        """Enable/disable accept button based on checkbox state."""
        self.next_btn.setEnabled(state == Qt.CheckState.Checked.value)


def check_user_consent(config_manager=None):
    """
    Check if user has given consent.
    
    Args:
        config_manager: Configuration manager instance
        
    Returns:
        bool: True if consent given or not needed
    """
    if not config_manager:
        return False

    consent_info = config_manager.get_consent_info()
    if consent_info.get('consent_given', False):
        logger.info("User consent previously given on %s", consent_info.get('consent_date', 'unknown date'))
        return True

    return False


def save_user_consent(config_manager=None):
    """
    Save user consent to consolidated config.
    
    Args:
        config_manager: Configuration manager instance
        
    Returns:
        bool: True if save successful
    """
    if not config_manager:
        logger.warning("Cannot save consent: no config_manager provided")
        return False

    import app
    version = app.__version__
    config_manager.set_consent_info(consent_given=True, version=version)
    success = config_manager.save_config()

    if success:
        logger.info("User consent saved to consolidated config")
    return success


def show_consent_dialog(parent=None, config_manager=None):
    """
    Show combined consent and setup dialog.
    
    Args:
        parent: Parent widget (optional)
        config_manager: Configuration manager instance (optional)
        
    Returns:
        dict: Setup configuration if accepted, None if declined
    """
    dialog = UserConsentDialog(parent, config_manager)
    result = dialog.exec()
    
    if result == QDialog.DialogCode.Accepted:
        # Save consent
        save_user_consent(config_manager)
        logger.info("User accepted terms and conditions")
        
        # Save setup configuration
        if config_manager and dialog.setup_config:
            if dialog.setup_config['mode'] == 'offline':
                config_manager.set_setting('translation.engine', 'offline')
            
            config_manager.save_config()
            
            logger.info("Setup mode: %s", dialog.setup_config['mode'])
        
        return dialog.setup_config
    else:
        logger.info("User declined terms and conditions")
        return None
