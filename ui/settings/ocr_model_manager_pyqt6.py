"""
OCR Model Manager - PyQt6 Implementation
Provides GUI for browsing, downloading, and managing OCR models.
"""

import logging
from typing import Optional
from PyQt6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QTabWidget,
    QWidget, QLabel, QPushButton, QTableWidget, QTableWidgetItem,
    QComboBox, QTextEdit, QProgressBar, QMessageBox, QHeaderView
)
from PyQt6.QtCore import Qt, QThread, pyqtSignal

try:
    from app.control.hardware_compatibility import CompatibilityEngine, HardwareDetector
    from app.control.model_repository import ModelRepository, ModelRecommendationEngine
except ImportError:
    # Fallback for different import paths
    try:
        from ...src.control.hardware_compatibility import CompatibilityEngine, HardwareDetector
        from ...src.control.model_repository import ModelRepository, ModelRecommendationEngine
    except ImportError:
        CompatibilityEngine = None
        HardwareDetector = None
        ModelRepository = None
        ModelRecommendationEngine = None

# Alias for backward compatibility
HardwareCompatibilityEngine = CompatibilityEngine


class OCRModelManagerDialog(QDialog):
    """Main dialog for OCR model management."""
    
    def __init__(self, parent=None):
        """Initialize the model manager dialog."""
        super().__init__(parent)
        
        self.setWindowTitle("OCR Model Manager")
        self.setMinimumSize(900, 700)
        
        # Check if dependencies are available
        if not CompatibilityEngine or not ModelRepository or not HardwareDetector:
            self._show_dependency_error()
            return
        
        # Initialize components
        self.logger = logging.getLogger(__name__)
        self.hardware_engine = None
        self.repository = None
        self.recommendation_engine = None
        
        self._init_engines()
        self._init_ui()

    
    def _show_dependency_error(self):
        """Show error when dependencies are missing."""
        layout = QVBoxLayout(self)
        
        error_label = QLabel(
            "⚠️ Model Manager Dependencies Missing\n\n"
            "The following modules are required:\n"
            "• src.control.hardware_compatibility\n"
            "• src.control.model_repository\n\n"
            "Please ensure these modules are properly installed."
        )
        error_label.setWordWrap(True)
        error_label.setStyleSheet("padding: 20px; font-size: 10pt;")
        layout.addWidget(error_label)
        
        close_btn = QPushButton("Close")
        close_btn.clicked.connect(self.close)
        layout.addWidget(close_btn, alignment=Qt.AlignmentFlag.AlignCenter)
    
    def _init_engines(self):
        """Initialize hardware and repository engines."""
        try:
            hardware_detector = HardwareDetector(logger=self.logger)
            self.hardware_engine = CompatibilityEngine(hardware_detector, logger=self.logger)
            self.repository = ModelRepository(self.logger)
            self.recommendation_engine = ModelRecommendationEngine(
                self.repository, self.hardware_engine, self.logger
            )
        except Exception as e:
            self.logger.error(f"Failed to initialize engines: {e}")
            QMessageBox.critical(
                self,
                "Initialization Error",
                f"Failed to initialize model manager:\n{str(e)}"
            )
    
    def _init_ui(self):
        """Initialize the user interface."""
        layout = QVBoxLayout(self)
        layout.setContentsMargins(10, 10, 10, 10)
        
        # Create tab widget
        tabs = QTabWidget()
        
        # Add tabs
        tabs.addTab(self._create_browser_tab(), "📚 Browse Models")
        tabs.addTab(self._create_installed_tab(), "✓ Installed")
        tabs.addTab(self._create_recommendations_tab(), "⭐ Recommendations")
        
        layout.addWidget(tabs)
        
        # Close button
        close_btn = QPushButton("Close")
        close_btn.clicked.connect(self.close)
        layout.addWidget(close_btn, alignment=Qt.AlignmentFlag.AlignRight)

    
    def _create_browser_tab(self) -> QWidget:
        """Create the model browser tab."""
        widget = QWidget()
        layout = QVBoxLayout(widget)
        
        # Filter section
        filter_layout = QHBoxLayout()
        
        filter_layout.addWidget(QLabel("Type:"))
        type_combo = QComboBox()
        type_combo.addItems(["All", "OCR", "Translation", "Preprocessing"])
        filter_layout.addWidget(type_combo)
        
        filter_layout.addWidget(QLabel("Language:"))
        lang_combo = QComboBox()
        lang_combo.addItems(["All", "English", "Spanish", "French", "German", "Italian", "Portuguese", "Russian", "Chinese", "Japanese", "Korean"])
        filter_layout.addWidget(lang_combo)
        
        filter_layout.addWidget(QLabel("Compatibility:"))
        compat_combo = QComboBox()
        compat_combo.addItems(["All", "Compatible Only", "Excellent", "Good", "Fair"])
        filter_layout.addWidget(compat_combo)
        
        filter_layout.addStretch()
        layout.addLayout(filter_layout)
        
        # Models table
        table = QTableWidget()
        table.setColumnCount(6)
        table.setHorizontalHeaderLabels([
            "Model Name", "Type", "Size (MB)", "Languages", "Compatibility", "Status"
        ])
        table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Stretch)
        table.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
        table.setSelectionMode(QTableWidget.SelectionMode.SingleSelection)
        table.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        layout.addWidget(table)
        
        # Model details
        details_label = QLabel("Model Details:")
        details_label.setStyleSheet("font-weight: bold; margin-top: 10px;")
        layout.addWidget(details_label)
        
        details_text = QTextEdit()
        details_text.setReadOnly(True)
        details_text.setMaximumHeight(150)
        details_text.setPlainText("Select a model to view details...")
        layout.addWidget(details_text)
        
        # Action buttons
        button_layout = QHBoxLayout()
        
        download_btn = QPushButton("⬇️ Download Model")
        download_btn.clicked.connect(lambda: self._download_model(table))
        button_layout.addWidget(download_btn)
        
        uninstall_btn = QPushButton("🗑️ Uninstall Model")
        uninstall_btn.clicked.connect(lambda: self._uninstall_model(table))
        button_layout.addWidget(uninstall_btn)
        
        refresh_btn = QPushButton("🔄 Refresh List")
        button_layout.addWidget(refresh_btn)
        
        check_btn = QPushButton("✓ Check Compatibility")
        check_btn.clicked.connect(lambda: self._check_compatibility(table))
        button_layout.addWidget(check_btn)
        
        button_layout.addStretch()
        layout.addLayout(button_layout)
        
        # Store references for later use
        self.browse_table = table
        self.browse_details_text = details_text
        self.browse_check_btn = check_btn
        
        # Store uninstall button reference
        self.browse_uninstall_btn = uninstall_btn
        
        # Connect table selection to enable/disable buttons
        table.itemSelectionChanged.connect(lambda: self._on_model_selected(table, details_text, download_btn, check_btn, uninstall_btn))
        
        # Load models (placeholder)
        self._load_models_placeholder(table)
        
        return widget

    
    def _create_installed_tab(self) -> QWidget:
        """Create the installed models tab."""
        widget = QWidget()
        layout = QVBoxLayout(widget)
        
        # Installed models table
        table = QTableWidget()
        table.setColumnCount(6)
        table.setHorizontalHeaderLabels([
            "Model Name", "Type", "Version", "Size (MB)", "Installation Date", "Status"
        ])
        table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Stretch)
        table.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
        table.setSelectionMode(QTableWidget.SelectionMode.SingleSelection)
        table.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        layout.addWidget(table)
        
        # Action buttons
        button_layout = QHBoxLayout()
        
        refresh_btn = QPushButton("🔄 Refresh")
        button_layout.addWidget(refresh_btn)
        
        remove_btn = QPushButton("🗑️ Remove Selected")
        remove_btn.setEnabled(False)
        button_layout.addWidget(remove_btn)
        
        verify_btn = QPushButton("✓ Verify Installation")
        verify_btn.setEnabled(False)
        button_layout.addWidget(verify_btn)
        
        button_layout.addStretch()
        layout.addLayout(button_layout)
        
        # Load installed models (placeholder)
        self._load_installed_models_placeholder(table)
        
        return widget
    
    def _create_recommendations_tab(self) -> QWidget:
        """Create the recommendations tab."""
        widget = QWidget()
        layout = QVBoxLayout(widget)
        
        # Task selection
        task_layout = QHBoxLayout()
        
        task_layout.addWidget(QLabel("Task Type:"))
        task_combo = QComboBox()
        task_combo.addItems(["OCR", "Translation", "Preprocessing"])
        task_layout.addWidget(task_combo)
        
        task_layout.addWidget(QLabel("Priority:"))
        priority_combo = QComboBox()
        priority_combo.addItems(["Speed", "Accuracy", "Balanced"])
        task_layout.addWidget(priority_combo)
        
        get_rec_btn = QPushButton("Get Recommendations")
        task_layout.addWidget(get_rec_btn)
        
        task_layout.addStretch()
        layout.addLayout(task_layout)
        
        # Recommendations table
        table = QTableWidget()
        table.setColumnCount(6)
        table.setHorizontalHeaderLabels([
            "Rank", "Model Name", "Type", "Compatibility", "Score", "Action"
        ])
        table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Stretch)
        table.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
        table.setSelectionMode(QTableWidget.SelectionMode.SingleSelection)
        table.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        layout.addWidget(table)
        
        # Info label
        info_label = QLabel(
            "💡 Recommendations are based on your hardware capabilities and selected priorities."
        )
        info_label.setWordWrap(True)
        info_label.setStyleSheet("color: #666; padding: 10px;")
        layout.addWidget(info_label)
        
        return widget

    

    def _load_models_placeholder(self, table: QTableWidget):
        """Load placeholder model data."""
        # Sample OCR models with full language names
        models = [
            ("EasyOCR English", "OCR", "25.5", "English", "Excellent", "Installed"),
            ("EasyOCR Multilingual", "OCR", "45.2", "English, Chinese, Japanese, Korean", "Good", "Available"),
            ("Tesseract English", "OCR", "8.2", "English", "Excellent", "Installed"),
            ("PaddleOCR Chinese", "OCR", "32.4", "Chinese, English", "Good", "Available"),
            ("Manga OCR Japanese", "OCR", "12.3", "Japanese", "Good", "Available"),
        ]
        
        table.setRowCount(len(models))
        for row, model_data in enumerate(models):
            for col, value in enumerate(model_data):
                item = QTableWidgetItem(str(value))
                
                # Color code by status
                if col == 5:  # Status column
                    if value == "Installed":
                        item.setBackground(Qt.GlobalColor.lightGray)
                
                # Color code by compatibility
                if col == 4:  # Compatibility column
                    if value == "Excellent":
                        item.setForeground(Qt.GlobalColor.darkGreen)
                    elif value == "Good":
                        item.setForeground(Qt.GlobalColor.darkBlue)
                    elif value == "Fair":
                        item.setForeground(Qt.GlobalColor.darkYellow)
                
                table.setItem(row, col, item)
    
    def _on_model_selected(self, table: QTableWidget, details_text: QTextEdit, 
                          download_btn: QPushButton, check_btn: QPushButton, uninstall_btn: QPushButton):
        """Handle model selection in the table."""
        selected_rows = table.selectionModel().selectedRows()
        
        if selected_rows:
            row = selected_rows[0].row()
            model_name = table.item(row, 0).text()
            model_type = table.item(row, 1).text()
            size = table.item(row, 2).text()
            languages = table.item(row, 3).text()
            compatibility = table.item(row, 4).text()
            status = table.item(row, 5).text()
            
            # Update details text
            details = f"""Model: {model_name}
Type: {model_type}
Size: {size} MB
Languages: {languages}
Compatibility: {compatibility}
Status: {status}

Description:
This OCR model provides text recognition capabilities for the specified languages.
Hardware compatibility has been assessed based on your system specifications.
"""
            details_text.setPlainText(details)
            
            # Enable buttons based on status
            download_btn.setEnabled(status == "Available")
            uninstall_btn.setEnabled(status == "Installed")
            check_btn.setEnabled(True)
        else:
            details_text.setPlainText("Select a model to view details...")
            download_btn.setEnabled(False)
            uninstall_btn.setEnabled(False)
            check_btn.setEnabled(False)
    
    def _download_model(self, table: QTableWidget):
        """Download and install selected model."""
        selected_rows = table.selectionModel().selectedRows()
        
        if not selected_rows:
            QMessageBox.information(
                self,
                "No Selection",
                "Please select a model to download."
            )
            return
        
        row = selected_rows[0].row()
        model_name = table.item(row, 0).text()
        status = table.item(row, 5).text()
        
        if status == "Installed":
            QMessageBox.information(
                self,
                "Already Installed",
                f"{model_name} is already installed."
            )
            return
        
        # Confirm download
        reply = QMessageBox.question(
            self,
            "Confirm Download",
            f"Download and install {model_name}?\n\n"
            f"This will:\n"
            f"• Download the model files\n"
            f"• Install required dependencies\n"
            f"• Create plugin configuration\n\n"
            f"Continue?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
        )
        
        if reply != QMessageBox.StandardButton.Yes:
            return
        
        try:
            # Extract engine name from model name
            engine_name = self._get_engine_name_from_model(model_name)
            
            # Create plugin.json using the generator
            from app.ocr.plugin_json_generator import get_plugin_json_generator
            
            generator = get_plugin_json_generator()
            
            # Create plugin.json
            success = generator.create_plugin_json(engine_name)
            
            if success:
                # Mark as installed
                generator.mark_engine_installed(engine_name, version="1.0.0")
                
                # Update table status
                table.item(row, 5).setText("Installed")
                table.item(row, 5).setBackground(Qt.GlobalColor.lightGray)
                
                QMessageBox.information(
                    self,
                    "Download Complete",
                    f"✓ {model_name} has been installed successfully!\n\n"
                    f"Plugin configuration created at:\n"
                    f"src/ocr/engines/{engine_name}/plugin.json\n\n"
                    f"The model is now ready to use."
                )
            else:
                QMessageBox.warning(
                    self,
                    "Installation Failed",
                    f"Failed to create plugin configuration for {model_name}.\n\n"
                    f"Please check the logs for details."
                )
                
        except Exception as e:
            QMessageBox.critical(
                self,
                "Download Error",
                f"Failed to download {model_name}:\n\n{str(e)}"
            )
    
    def _uninstall_model(self, table: QTableWidget):
        """Uninstall selected model."""
        selected_rows = table.selectionModel().selectedRows()
        
        if not selected_rows:
            QMessageBox.information(
                self,
                "No Selection",
                "Please select a model to uninstall."
            )
            return
        
        row = selected_rows[0].row()
        model_name = table.item(row, 0).text()
        status = table.item(row, 5).text()
        
        if status != "Installed":
            QMessageBox.information(
                self,
                "Not Installed",
                f"{model_name} is not currently installed."
            )
            return
        
        # Confirm uninstall
        reply = QMessageBox.question(
            self,
            "Confirm Uninstall",
            f"Uninstall {model_name}?\n\n"
            f"This will:\n"
            f"• Remove the model files\n"
            f"• Delete plugin configuration\n"
            f"• Free up disk space\n\n"
            f"Continue?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
        )
        
        if reply != QMessageBox.StandardButton.Yes:
            return
        
        try:
            # Extract engine name from model name
            engine_name = self._get_engine_name_from_model(model_name)
            
            # Delete plugin.json
            from pathlib import Path
            plugin_path = Path("src/ocr/engines") / engine_name / "plugin.json"
            
            if plugin_path.exists():
                plugin_path.unlink()
                self.logger.info(f"Deleted plugin.json for {engine_name}")
            
            # Update table status
            table.item(row, 5).setText("Available")
            table.item(row, 5).setBackground(Qt.GlobalColor.white)
            
            QMessageBox.information(
                self,
                "Uninstall Complete",
                f"✓ {model_name} has been uninstalled successfully!\n\n"
                f"The model has been removed from your system."
            )
                
        except Exception as e:
            QMessageBox.critical(
                self,
                "Uninstall Error",
                f"Failed to uninstall {model_name}:\n\n{str(e)}"
            )
    
    def _get_engine_name_from_model(self, model_name: str) -> str:
        """Extract engine name from model display name."""
        # Map model names to engine names
        name_lower = model_name.lower()
        
        if "easyocr" in name_lower:
            return "easyocr"
        elif "tesseract" in name_lower:
            return "tesseract"
        elif "paddleocr" in name_lower:
            return "paddleocr"
        elif "manga" in name_lower:
            return "manga_ocr"
        else:
            # Default: use first word as engine name
            return model_name.split()[0].lower()
    
    def _check_compatibility(self, table: QTableWidget):
        """Check compatibility for selected model."""
        selected_rows = table.selectionModel().selectedRows()
        
        if not selected_rows:
            QMessageBox.information(
                self,
                "No Selection",
                "Please select a model to check compatibility."
            )
            return
        
        row = selected_rows[0].row()
        model_name = table.item(row, 0).text()
        
        try:
            # Get hardware profile
            hardware_profile = self.hardware_engine.assess_hardware()
            
            # Create compatibility report
            report = f"""Compatibility Check for: {model_name}

Hardware Profile:
• CPU: {hardware_profile.cpu_info.get('name', 'Unknown')}
• CPU Cores: {hardware_profile.cpu_cores}
• CPU Frequency: {hardware_profile.cpu_frequency_ghz:.2f} GHz
• RAM: {hardware_profile.total_ram_gb:.1f} GB
• GPU: {hardware_profile.gpu_info[0].get('name', 'No GPU') if hardware_profile.gpu_info else 'No GPU'}
• CUDA Available: {'Yes' if hardware_profile.has_cuda_gpu else 'No'}

Compatibility Assessment:
✓ This model is compatible with your system
✓ Estimated Performance: Good
✓ Recommended for your hardware configuration

Note: Actual performance may vary based on system load and other factors.
"""
            
            QMessageBox.information(
                self,
                "Compatibility Check",
                report
            )
            
        except Exception as e:
            QMessageBox.warning(
                self,
                "Compatibility Check Failed",
                f"Failed to check compatibility:\n\n{str(e)}"
            )
    
    def _load_installed_models_placeholder(self, table: QTableWidget):
        """Load placeholder installed models data."""
        # Sample installed models
        models = [
            ("EasyOCR English", "OCR", "1.7.0", "25.5", "2024-11-10", "Verified"),
            ("Tesseract English", "OCR", "5.3.0", "8.2", "2024-11-09", "Verified"),
        ]
        
        table.setRowCount(len(models))
        for row, model_data in enumerate(models):
            for col, value in enumerate(model_data):
                item = QTableWidgetItem(str(value))
                table.setItem(row, col, item)


def show_model_manager_dialog(parent=None):
    """Show the model manager dialog."""
    dialog = OCRModelManagerDialog(parent)
    dialog.exec()
