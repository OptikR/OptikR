"""
OCR Engine Installer Dialog

Dialog for installing OCR engines when none are available.
Provides hardware-based recommendations and installation options.
"""

from PyQt6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QRadioButton, QButtonGroup, QTextEdit, QProgressBar, QMessageBox
)
from PyQt6.QtCore import Qt, QThread, pyqtSignal
from PyQt6.QtGui import QFont
import subprocess
import sys


class OCREngineInstallerDialog(QDialog):
    """
    Dialog for installing OCR engines.
    
    Provides hardware-based recommendations and installation options.
    """
    
    def __init__(self, has_gpu=False, parent=None):
        """
        Initialize OCR engine installer dialog.
        
        Args:
            has_gpu: Whether GPU is available
            parent: Parent widget
        """
        super().__init__(parent)
        self.has_gpu = has_gpu
        self.selected_engine = None
        
        self.setWindowTitle("Install OCR Engine")
        self.setMinimumWidth(600)
        self.setMinimumHeight(500)
        self.setModal(True)
        
        self.init_ui()
    
    def init_ui(self):
        """Initialize the dialog UI."""
        layout = QVBoxLayout(self)
        layout.setSpacing(15)
        layout.setContentsMargins(20, 20, 20, 20)
        
        # Header
        header = QLabel("⚠️ No OCR Engine Installed")
        header_font = QFont()
        header_font.setPointSize(14)
        header_font.setBold(True)
        header.setFont(header_font)
        header.setStyleSheet("color: #F44336;")
        layout.addWidget(header)
        
        # Description
        desc = QLabel(
            "OptikR requires at least one OCR engine to function.\n"
            "Please select an engine to install based on your hardware."
        )
        desc.setWordWrap(True)
        desc.setStyleSheet("color: #666666; font-size: 10pt; margin-bottom: 10px;")
        layout.addWidget(desc)
        
        # Hardware info
        hw_info = QLabel(f"🖥️ Detected Hardware: {'GPU Available (CUDA)' if self.has_gpu else 'CPU Only'}")
        hw_info.setStyleSheet("font-size: 10pt; font-weight: bold; color: #2196F3; padding: 8px; "
                             "background-color: #E3F2FD; border-radius: 3px;")
        layout.addWidget(hw_info)
        
        # Engine selection
        engines_label = QLabel("Select OCR Engine to Install:")
        engines_label.setStyleSheet("font-size: 11pt; font-weight: bold; margin-top: 10px;")
        layout.addWidget(engines_label)
        
        # Radio buttons for engines
        self.button_group = QButtonGroup()
        
        # EasyOCR (recommended for GPU)
        self.easyocr_radio = QRadioButton("🔍 EasyOCR (Recommended for GPU)")
        self.easyocr_radio.setStyleSheet("font-size: 10pt; font-weight: 500;")
        if self.has_gpu:
            self.easyocr_radio.setChecked(True)
        self.button_group.addButton(self.easyocr_radio)
        layout.addWidget(self.easyocr_radio)
        
        easyocr_desc = QLabel(
            "  • Best accuracy with GPU acceleration\n"
            "  • Supports 80+ languages\n"
            "  • Requires ~2GB download\n"
            "  • Installation time: 5-10 minutes"
        )
        easyocr_desc.setStyleSheet("color: #666666; font-size: 9pt; margin-left: 20px; margin-bottom: 10px;")
        layout.addWidget(easyocr_desc)
        
        # Tesseract (recommended for CPU)
        self.tesseract_radio = QRadioButton("📝 Tesseract OCR (Recommended for CPU)")
        self.tesseract_radio.setStyleSheet("font-size: 10pt; font-weight: 500;")
        if not self.has_gpu:
            self.tesseract_radio.setChecked(True)
        self.button_group.addButton(self.tesseract_radio)
        layout.addWidget(self.tesseract_radio)
        
        tesseract_desc = QLabel(
            "  • Fast and lightweight\n"
            "  • Good for printed text\n"
            "  • Requires ~100MB download\n"
            "  • Installation time: 2-3 minutes"
        )
        tesseract_desc.setStyleSheet("color: #666666; font-size: 9pt; margin-left: 20px; margin-bottom: 10px;")
        layout.addWidget(tesseract_desc)
        
        # PaddleOCR
        self.paddleocr_radio = QRadioButton("🎯 PaddleOCR (Chinese/Multilingual)")
        self.paddleocr_radio.setStyleSheet("font-size: 10pt; font-weight: 500;")
        self.button_group.addButton(self.paddleocr_radio)
        layout.addWidget(self.paddleocr_radio)
        
        paddleocr_desc = QLabel(
            "  • Excellent for Chinese text\n"
            "  • High accuracy multilingual OCR\n"
            "  • Requires ~500MB download\n"
            "  • Installation time: 5-7 minutes"
        )
        paddleocr_desc.setStyleSheet("color: #666666; font-size: 9pt; margin-left: 20px; margin-bottom: 10px;")
        layout.addWidget(paddleocr_desc)
        
        # Manga OCR
        self.manga_ocr_radio = QRadioButton("📚 Manga OCR (Japanese Manga)")
        self.manga_ocr_radio.setStyleSheet("font-size: 10pt; font-weight: 500;")
        self.button_group.addButton(self.manga_ocr_radio)
        layout.addWidget(self.manga_ocr_radio)
        
        manga_ocr_desc = QLabel(
            "  • Specialized for Japanese manga\n"
            "  • Best for stylized Japanese text\n"
            "  • Requires ~400MB download\n"
            "  • Installation time: 3-5 minutes"
        )
        manga_ocr_desc.setStyleSheet("color: #666666; font-size: 9pt; margin-left: 20px; margin-bottom: 10px;")
        layout.addWidget(manga_ocr_desc)
        
        # Progress area (hidden initially)
        self.progress_widget = QWidget()
        progress_layout = QVBoxLayout(self.progress_widget)
        progress_layout.setContentsMargins(0, 10, 0, 0)
        
        self.progress_label = QLabel("Installing...")
        self.progress_label.setStyleSheet("font-size: 10pt; font-weight: bold;")
        progress_layout.addWidget(self.progress_label)
        
        self.progress_bar = QProgressBar()
        self.progress_bar.setRange(0, 0)  # Indeterminate
        progress_layout.addWidget(self.progress_bar)
        
        self.progress_text = QTextEdit()
        self.progress_text.setReadOnly(True)
        self.progress_text.setMaximumHeight(100)
        self.progress_text.setStyleSheet("font-family: 'Consolas', 'Courier New', monospace; font-size: 8pt;")
        progress_layout.addWidget(self.progress_text)
        
        self.progress_widget.hide()
        layout.addWidget(self.progress_widget)
        
        layout.addStretch()
        
        # Buttons
        button_layout = QHBoxLayout()
        button_layout.addStretch()
        
        self.cancel_btn = QPushButton("Cancel")
        self.cancel_btn.clicked.connect(self.reject)
        button_layout.addWidget(self.cancel_btn)
        
        self.install_btn = QPushButton("Install Selected Engine")
        self.install_btn.setProperty("class", "action")
        self.install_btn.setDefault(True)
        self.install_btn.clicked.connect(self.start_installation)
        button_layout.addWidget(self.install_btn)
        
        layout.addLayout(button_layout)
    
    def start_installation(self):
        """Start the installation process."""
        # Determine selected engine
        if self.easyocr_radio.isChecked():
            self.selected_engine = 'easyocr'
            package = 'easyocr'
        elif self.tesseract_radio.isChecked():
            self.selected_engine = 'tesseract'
            package = 'pytesseract'
        elif self.paddleocr_radio.isChecked():
            self.selected_engine = 'paddleocr'
            package = 'paddleocr'
        elif self.manga_ocr_radio.isChecked():
            self.selected_engine = 'manga_ocr'
            package = 'manga-ocr'
        else:
            QMessageBox.warning(self, "No Selection", "Please select an OCR engine to install.")
            return
        
        # Confirm installation
        reply = QMessageBox.question(
            self,
            "Confirm Installation",
            f"Install {self.selected_engine}?\n\n"
            f"This will download and install the required packages.\n"
            f"The process may take several minutes.\n\n"
            f"Continue?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            QMessageBox.StandardButton.Yes
        )
        
        if reply != QMessageBox.StandardButton.Yes:
            return
        
        # Disable buttons and show progress
        self.install_btn.setEnabled(False)
        self.cancel_btn.setEnabled(False)
        self.progress_widget.show()
        self.progress_label.setText(f"Installing {self.selected_engine}...")
        
        # Start installation thread
        self.installer_thread = InstallerThread(package)
        self.installer_thread.progress.connect(self.on_progress)
        self.installer_thread.finished_signal.connect(self.on_installation_finished)
        self.installer_thread.error.connect(self.on_installation_error)
        self.installer_thread.start()
    
    def on_progress(self, message):
        """Handle progress updates."""
        self.progress_text.append(message)
        # Auto-scroll to bottom
        self.progress_text.verticalScrollBar().setValue(
            self.progress_text.verticalScrollBar().maximum()
        )
    
    def on_installation_finished(self, success):
        """Handle installation completion."""
        self.progress_bar.setRange(0, 100)
        self.progress_bar.setValue(100)
        
        if success:
            self.progress_label.setText(f"✓ {self.selected_engine} installed successfully!")
            self.progress_label.setStyleSheet("font-size: 10pt; font-weight: bold; color: #4CAF50;")
            
            QMessageBox.information(
                self,
                "Installation Complete",
                f"{self.selected_engine} has been installed successfully!\n\n"
                f"The application will now restart to load the OCR engine."
            )
            
            self.accept()
        else:
            self.progress_label.setText(f"✗ Installation failed")
            self.progress_label.setStyleSheet("font-size: 10pt; font-weight: bold; color: #F44336;")
            self.install_btn.setEnabled(True)
            self.cancel_btn.setEnabled(True)
    
    def on_installation_error(self, error_message):
        """Handle installation error."""
        self.progress_bar.setRange(0, 100)
        self.progress_bar.setValue(0)
        self.progress_label.setText(f"✗ Installation failed")
        self.progress_label.setStyleSheet("font-size: 10pt; font-weight: bold; color: #F44336;")
        
        QMessageBox.critical(
            self,
            "Installation Failed",
            f"Failed to install OCR engine:\n\n{error_message}\n\n"
            f"Please try:\n"
            f"1. Check your internet connection\n"
            f"2. Run as administrator\n"
            f"3. Install manually using: pip install {self.selected_engine}"
        )
        
        self.install_btn.setEnabled(True)
        self.cancel_btn.setEnabled(True)
    
    def get_selected_engine(self):
        """Get the selected engine name."""
        return self.selected_engine


class InstallerThread(QThread):
    """Background thread for installing OCR engines."""
    
    progress = pyqtSignal(str)
    finished_signal = pyqtSignal(bool)
    error = pyqtSignal(str)
    
    def __init__(self, package_name):
        super().__init__()
        self.package_name = package_name
    
    def run(self):
        """Run the installation."""
        try:
            self.progress.emit(f"Starting installation of {self.package_name}...")
            self.progress.emit(f"Running: pip install {self.package_name}")
            
            # Run pip install
            process = subprocess.Popen(
                [sys.executable, "-m", "pip", "install", self.package_name],
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                text=True,
                bufsize=1
            )
            
            # Stream output
            for line in process.stdout:
                self.progress.emit(line.strip())
            
            # Wait for completion
            return_code = process.wait()
            
            if return_code == 0:
                self.progress.emit(f"\n✓ Installation completed successfully!")
                self.finished_signal.emit(True)
            else:
                self.progress.emit(f"\n✗ Installation failed with code {return_code}")
                self.finished_signal.emit(False)
                
        except Exception as e:
            self.error.emit(str(e))


def show_ocr_engine_installer(has_gpu=False, parent=None):
    """
    Show OCR engine installer dialog.
    
    Args:
        has_gpu: Whether GPU is available
        parent: Parent widget
        
    Returns:
        Selected engine name or None if cancelled
    """
    dialog = OCREngineInstallerDialog(has_gpu, parent)
    result = dialog.exec()
    
    if result == QDialog.DialogCode.Accepted:
        return dialog.get_selected_engine()
    return None
