"""
User Consent Dialog Module

Combined first-run dialog that handles:
1. User consent for screen capture and data processing
2. Model setup (online/offline mode)
3. Privacy policy and terms of use

Author: Real-Time Translation System
Date: 2024
"""

import json
from pathlib import Path
from datetime import datetime

from PyQt6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QCheckBox, QTextEdit, QScrollArea, QWidget, QStackedWidget
)
from PyQt6.QtCore import Qt


class UserConsentDialog(QDialog):
    """Combined first-run dialog for consent and model setup."""
    
    def __init__(self, parent=None, config_manager=None):
        super().__init__(parent)
        self.config_manager = config_manager
        self.setWindowTitle("Welcome to OptikR - First Time Setup")
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
        
        # Title
        self.title_label = QLabel("Welcome to OptikR!")
        self.title_label.setStyleSheet("font-size: 18pt; font-weight: bold; color: #2C3E50;")
        layout.addWidget(self.title_label)
        
        # Subtitle
        self.subtitle_label = QLabel("Please read and understand the following before using this application:")
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
        
        self.decline_btn = QPushButton("Decline && Exit")
        self.decline_btn.setMinimumWidth(120)
        self.decline_btn.clicked.connect(self.reject)
        self.button_layout.addWidget(self.decline_btn)
        
        self.back_btn = QPushButton("← Back")
        self.back_btn.setMinimumWidth(100)
        self.back_btn.setVisible(False)
        self.back_btn.clicked.connect(self._go_back)
        self.button_layout.addWidget(self.back_btn)
        
        self.next_btn = QPushButton("Accept && Continue →")
        self.next_btn.setMinimumWidth(150)
        self.next_btn.setEnabled(False)
        self.next_btn.clicked.connect(self._go_next)
        self.button_layout.addWidget(self.next_btn)
        
        layout.addLayout(self.button_layout)
    
    def _create_consent_page(self):
        """Create the consent page."""
        page = QWidget()
        layout = QVBoxLayout(page)
        layout.setContentsMargins(0, 0, 0, 0)
        
        # Important folder creation notice
        folder_notice = QLabel(
            "📁 <b>Important:</b> OptikR will create folders and files in the directory where the EXE is located.\n"
            "It is <b>recommended to place OptikR in a dedicated subfolder</b> (e.g., C:\\OptikR\\) "
            "to keep your files organized."
        )
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
        self.consent_checkbox = QCheckBox(
            "I have read and understand the above. I agree to the terms of use and privacy policy."
        )
        self.consent_checkbox.setStyleSheet("font-size: 10pt; font-weight: bold;")
        self.consent_checkbox.stateChanged.connect(self._on_consent_changed)
        layout.addWidget(self.consent_checkbox)
        
        return page
    
    def _create_setup_page(self):
        """Create the model setup page."""
        # Create the setup page directly (offline_setup_dialog.py was merged into this file)
        page = QWidget()
        layout = QVBoxLayout(page)
        layout.setContentsMargins(0, 0, 0, 0)
        
        # Extract the content from setup dialog (without buttons)
        # We'll recreate the key parts here
        from PyQt6.QtWidgets import QRadioButton, QButtonGroup, QGroupBox, QLineEdit, QFileDialog
        
        desc = QLabel(
            "Choose how you want to set up OCR and translation models:"
        )
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
        from PyQt6.QtWidgets import QRadioButton, QGroupBox
        
        group = QGroupBox()
        layout = QVBoxLayout(group)
        
        self.online_radio = QRadioButton("🌐 Online Mode (Recommended)")
        self.online_radio.setChecked(True)  # Default
        self.online_radio.setStyleSheet("font-weight: 600; font-size: 10pt;")
        self.mode_group.addButton(self.online_radio, 0)
        layout.addWidget(self.online_radio)
        
        desc = QLabel(
            "• Models download automatically when needed\n"
            "• First run: ~500MB download (2-3 minutes)\n"
            "• All future runs: Instant (uses cached models)\n"
            "• Requires internet connection for first run"
        )
        desc.setStyleSheet("color: #666666; font-size: 9pt; margin-left: 25px;")
        layout.addWidget(desc)
        
        return group
    
    def _create_offline_mode_group(self):
        """Create offline mode option group."""
        from PyQt6.QtWidgets import QRadioButton, QGroupBox, QLineEdit, QPushButton
        
        group = QGroupBox()
        layout = QVBoxLayout(group)
        
        self.offline_radio = QRadioButton("📦 Offline Mode (Advanced)")
        self.offline_radio.setStyleSheet("font-weight: 600; font-size: 10pt;")
        self.mode_group.addButton(self.offline_radio, 1)
        self.offline_radio.toggled.connect(self._on_offline_toggled)
        layout.addWidget(self.offline_radio)
        
        desc = QLabel(
            "• Select your pre-downloaded model files\n"
            "• Files will be copied to the correct locations automatically\n"
            "• Plugins will be generated automatically\n"
            "• No internet required after setup"
        )
        desc.setStyleSheet("color: #666666; font-size: 9pt; margin-left: 25px;")
        layout.addWidget(desc)
        
        # Model file inputs (disabled by default)
        self.offline_inputs = QGroupBox("Select Model Files")
        self.offline_inputs.setEnabled(False)
        inputs_layout = QVBoxLayout(self.offline_inputs)
        
        # OCR model files
        ocr_label = QLabel("OCR Model Files (e.g., craft_mlt_25k.pth):")
        ocr_label.setStyleSheet("font-weight: 600; margin-top: 5px;")
        inputs_layout.addWidget(ocr_label)
        
        ocr_layout = QHBoxLayout()
        self.ocr_files_input = QLineEdit()
        self.ocr_files_input.setPlaceholderText("No files selected...")
        self.ocr_files_input.setReadOnly(True)
        ocr_layout.addWidget(self.ocr_files_input)
        ocr_browse = QPushButton("Select Files...")
        ocr_browse.clicked.connect(self._browse_ocr_files)
        ocr_layout.addWidget(ocr_browse)
        inputs_layout.addLayout(ocr_layout)
        
        self.ocr_files = []
        
        # Translation model folders
        trans_label = QLabel("Translation Model Folder (e.g., opus-mt-en-de/):")
        trans_label.setStyleSheet("font-weight: 600; margin-top: 5px;")
        inputs_layout.addWidget(trans_label)
        
        trans_layout = QHBoxLayout()
        self.trans_folder_input = QLineEdit()
        self.trans_folder_input.setPlaceholderText("No folder selected...")
        self.trans_folder_input.setReadOnly(True)
        trans_layout.addWidget(self.trans_folder_input)
        trans_browse = QPushButton("Select Folder...")
        trans_browse.clicked.connect(self._browse_translation_folder)
        trans_layout.addWidget(trans_browse)
        inputs_layout.addLayout(trans_layout)
        
        self.trans_folder = None
        
        layout.addWidget(self.offline_inputs)
        
        return group
    
    def _create_skip_mode_group(self):
        """Create skip option group."""
        from PyQt6.QtWidgets import QRadioButton, QGroupBox
        
        group = QGroupBox()
        layout = QVBoxLayout(group)
        
        self.skip_radio = QRadioButton("⏭️ Skip Setup")
        self.skip_radio.setStyleSheet("font-weight: 600; font-size: 10pt;")
        self.mode_group.addButton(self.skip_radio, 2)
        layout.addWidget(self.skip_radio)
        
        desc = QLabel(
            "• Configure models later in Settings\n"
            "• OCR and translation features will be disabled until configured"
        )
        desc.setStyleSheet("color: #666666; font-size: 9pt; margin-left: 25px;")
        layout.addWidget(desc)
        
        return group
    
    def _on_offline_toggled(self, checked):
        """Enable/disable offline mode inputs."""
        self.offline_inputs.setEnabled(checked)
    
    def _browse_ocr_files(self):
        """Browse for OCR model files."""
        from PyQt6.QtWidgets import QFileDialog
        
        files, _ = QFileDialog.getOpenFileNames(
            self,
            "Select OCR Model Files",
            str(Path.home()),
            "Model Files (*.pth *.pt *.bin *.onnx);;All Files (*.*)"
        )
        
        if files:
            self.ocr_files = files
            file_names = [Path(f).name for f in files]
            self.ocr_files_input.setText(f"{len(files)} file(s): {', '.join(file_names[:3])}{'...' if len(files) > 3 else ''}")
    
    def _browse_translation_folder(self):
        """Browse for translation model folder."""
        from PyQt6.QtWidgets import QFileDialog
        
        folder = QFileDialog.getExistingDirectory(
            self,
            "Select Translation Model Folder",
            str(Path.home())
        )
        
        if folder:
            self.trans_folder = folder
            self.trans_folder_input.setText(Path(folder).name)
    
    def _go_back(self):
        """Go back to consent page."""
        self.stacked_widget.setCurrentIndex(0)
        self.title_label.setText("Welcome to OptikR!")
        self.subtitle_label.setText("Please read and understand the following before using this application:")
        self.back_btn.setVisible(False)
        self.next_btn.setText("Accept && Continue →")
        self.next_btn.setEnabled(self.consent_checkbox.isChecked())
    
    def _go_next(self):
        """Go to next page or finish."""
        current_index = self.stacked_widget.currentIndex()
        
        if current_index == 0:  # Consent page
            # Move to setup page
            self.stacked_widget.setCurrentIndex(1)
            self.title_label.setText("Model Setup")
            self.subtitle_label.setText("Choose how you want to set up OCR and translation models:")
            self.back_btn.setVisible(True)
            self.next_btn.setText("Finish Setup")
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
            # Validate and copy files
            if not self.ocr_files and not self.trans_folder:
                from PyQt6.QtWidgets import QMessageBox
                QMessageBox.warning(
                    self,
                    "No Files Selected",
                    "Please select at least OCR model files or a translation model folder."
                )
                return
            
            # Use the setup dialog's copy method
            success = self.setup_dialog._copy_models_and_generate_plugins()
            
            if success:
                # Copy the file lists to setup dialog
                self.setup_dialog.ocr_files = self.ocr_files
                self.setup_dialog.trans_folder = self.trans_folder
                
                success = self.setup_dialog._copy_models_and_generate_plugins()
                
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
        return """
        <html>
        <body style="font-family: Arial, sans-serif; font-size: 10pt;">
            <h3 style="color: #2C3E50;">What This Application Does:</h3>
            
            <h4 style="color: #34495E;">1. Screen Capture</h4>
            <ul>
                <li>The application will capture the screen region <b>you select</b></li>
                <li>Capture only occurs when <b>you click "Start"</b></li>
                <li>You can stop capture at any time by clicking "Stop"</li>
                <li>Captured images are processed locally and <b>not stored permanently</b></li>
            </ul>
            
            <h4 style="color: #34495E;">2. Data Processing</h4>
            <ul>
                <li>Captured images are processed by OCR (Optical Character Recognition) to extract text</li>
                <li>Extracted text is translated using your chosen translation engine</li>
                <li><b>Offline engines:</b> All processing happens on your computer (no data transmission)</li>
                <li><b>Cloud engines:</b> Only extracted text is sent (never images or screenshots)</li>
            </ul>
            
            <h4 style="color: #34495E;">3. Data Storage (100% Local)</h4>
            <ul>
                <li>Translations are cached locally in <code>v0.1/cache/</code> for performance</li>
                <li><b>Learning Dictionary:</b> Translations are saved <b>ONLY on your computer</b> in <code>dictionary/</code></li>
                <li>Configuration settings are saved in <code>v0.1/config/</code></li>
                <li><b>NO cloud storage:</b> All data stays on your device</li>
                <li><b>NO data transmission:</b> Dictionary never sent anywhere</li>
                <li>You can clear all cached data at any time in Settings → Storage</li>
                <li>You can view/edit dictionary entries in Settings → Smart Dictionary</li>
            </ul>
            
            <h4 style="color: #27AE60;">4. Learning Dictionary - Privacy Guarantee</h4>
            <ul style="background-color: #E8F8F5; padding: 10px; border-left: 4px solid #27AE60;">
                <li><b>✓ 100% Local Storage:</b> All learned translations saved only on your computer</li>
                <li><b>✓ No Cloud Sync:</b> Dictionary never uploaded or synchronized</li>
                <li><b>✓ No Telemetry:</b> No usage data collected or transmitted</li>
                <li><b>✓ Full Control:</b> View, edit, or delete entries anytime</li>
                <li><b>✓ Sentence Validation:</b> Only complete, valid sentences are saved</li>
                <li><b>✓ Quality Check:</b> Minimum confidence threshold (80%) required</li>
                <li><b>✓ Your Data:</b> You own and control all dictionary data</li>
            </ul>
            
            <p style="background-color: #FFF3CD; padding: 10px; border-left: 4px solid #FFC107; margin-top: 10px;">
                <b>⚠️ Important:</b> By using the Learning Dictionary feature, you consent to:
                <br>• Saving translations locally on your device
                <br>• Automatic learning from high-quality translations (≥80% confidence)
                <br>• Storage of source text and translated text pairs
                <br>• All data remains private and local to your device
            </p>
            
            <h4 style="color: #34495E;">5. Data Transmission (Cloud Engines Only)</h4>
            <ul>
                <li><b>Offline engines (EasyOCR, Tesseract, MarianMT):</b> NO data transmitted</li>
                <li><b>Cloud engines (LibreTranslate, Google, Azure):</b> Only extracted text sent via HTTPS</li>
                <li><b>What is NEVER sent:</b> Screenshots, images, system information, personal data</li>
                <li>You can verify by using offline engines and disconnecting from internet</li>
            </ul>
            
            <h3 style="color: #2C3E50;">Your Control:</h3>
            <ul>
                <li>✓ You select what region to capture</li>
                <li>✓ You control when capture starts (click "Start")</li>
                <li>✓ You control when capture stops (click "Stop")</li>
                <li>✓ You choose offline or cloud engines</li>
                <li>✓ You can clear all data at any time</li>
                <li>✓ You can uninstall completely at any time</li>
            </ul>
            
            <h3 style="color: #2C3E50;">Your Responsibility:</h3>
            <ul>
                <li>You are responsible for selecting appropriate capture regions</li>
                <li>Do not capture sensitive, confidential, or copyrighted content without permission</li>
                <li>Comply with all applicable laws and regulations</li>
                <li>Use the application ethically and legally</li>
            </ul>
            
            <h3 style="color: #E74C3C;">Disclaimer:</h3>
            <p style="color: #7F8C8D;">
                This application is provided "as is" without warranty of any kind. 
                Use at your own risk. The developers are not responsible for any misuse 
                or consequences arising from the use of this application.
            </p>
            
            <p style="margin-top: 20px; padding: 10px; background-color: #ECF0F1; border-left: 4px solid #3498DB;">
                <b>Privacy:</b> For complete privacy, use offline engines (EasyOCR + MarianMT). 
                All processing will happen on your computer with no data transmission.
            </p>
        </body>
        </html>
        """
    
    def _on_consent_changed(self, state):
        """Enable/disable accept button based on checkbox state."""
        self.next_btn.setEnabled(state == Qt.CheckState.Checked.value)


def check_user_consent(config_manager=None):
    """
    Check if user has given consent.
    
    Args:
        config_manager: Configuration manager instance (optional)
        
    Returns:
        bool: True if consent given or not needed
    """
    if config_manager:
        # Use consolidated config
        consent_info = config_manager.get_consent_info()
        if consent_info.get('consent_given', False):
            print(f"[INFO] User consent previously given on {consent_info.get('consent_date', 'unknown date')}")
            return True
    else:
        # Fallback: check old separate file for backward compatibility
        consent_file = Path('config/user_consent.json')
        if consent_file.exists():
            try:
                with open(consent_file, 'r', encoding='utf-8') as f:
                    consent_data = json.load(f)
                
                if consent_data.get('consent_given', False):
                    print(f"[INFO] User consent previously given on {consent_data.get('consent_date', 'unknown date')}")
                    return True
            except Exception as e:
                print(f"[WARNING] Failed to read consent file: {e}")
    
    return False


def save_user_consent(config_manager=None):
    """
    Save user consent to consolidated config.
    
    Args:
        config_manager: Configuration manager instance (optional)
        
    Returns:
        bool: True if save successful
    """
    if config_manager:
        # Save to consolidated config
        version = config_manager.get_setting('ui.version', '0.1.0')
        config_manager.set_consent_info(consent_given=True, version=version)
        success = config_manager.save_config()
        
        if success:
            print("[INFO] User consent saved to consolidated config")
        return success
    else:
        # Fallback: save to separate file for backward compatibility
        consent_file = Path('config/user_consent.json')
        
        try:
            consent_file.parent.mkdir(parents=True, exist_ok=True)
            
            consent_data = {
                'consent_given': True,
                'consent_date': datetime.now().isoformat(),
                'version': '0.1.0'
            }
            
            with open(consent_file, 'w', encoding='utf-8') as f:
                json.dump(consent_data, f, indent=2)
            
            print(f"[INFO] User consent saved to {consent_file}")
            return True
        except Exception as e:
            print(f"[ERROR] Failed to save consent: {e}")
            return False


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
        print("[INFO] User accepted terms and conditions")
        
        # Save setup configuration
        if config_manager and dialog.setup_config:
            if dialog.setup_config['mode'] == 'offline':
                config_manager.set_setting('offline_mode.enabled', True)
            
            config_manager.set_setting('setup.completed', True)
            config_manager.set_setting('setup.mode', dialog.setup_config['mode'])
            config_manager.save_config()
            
            print(f"[INFO] Setup mode: {dialog.setup_config['mode']}")
        
        return dialog.setup_config
    else:
        print("[INFO] User declined terms and conditions")
        return None
