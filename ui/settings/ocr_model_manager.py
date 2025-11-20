"""
OCR Model Manager UI
Provides a dialog for managing OCR models similar to translation models.
"""
import threading
from pathlib import Path
from PyQt6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel, QPushButton, QTreeWidget, 
    QTreeWidgetItem, QComboBox, QGroupBox, QFormLayout, QSpinBox, 
    QMessageBox, QProgressDialog, QApplication
)
from PyQt6.QtCore import Qt


class OCRModelManager:
    """OCR Model Manager UI component."""
    
    def __init__(self, parent=None, config_manager=None):
        self.parent = parent
        self.config_manager = config_manager
    
    def show_ocr_model_manager(self):
        """Show OCR model management dialog."""
        # Create dialog
        dialog = QDialog(self.parent)
        dialog.setWindowTitle("🔍 OCR Model Manager")
        dialog.setMinimumSize(1000, 700)
        dialog.resize(1000, 700)
        
        # Main layout
        main_layout = QVBoxLayout(dialog)
        main_layout.setContentsMargins(20, 20, 20, 20)
        main_layout.setSpacing(15)
        
        # Get pipeline from parent
        pipeline = None
        parent = self.parent
        while parent:
            if hasattr(parent, 'pipeline') and parent.pipeline:
                pipeline = parent.pipeline
                break
            parent = parent.parent() if hasattr(parent, 'parent') else None
        
        # Header
        header_layout = QVBoxLayout()
        
        # Title row
        title_row = QHBoxLayout()
        title_label = QLabel("🔍 OCR Model Manager")
        title_label.setStyleSheet("font-size: 14pt; font-weight: bold;")
        title_row.addWidget(title_label)
        title_row.addStretch()
        header_layout.addLayout(title_row)
        
        # Info row
        info_row = QHBoxLayout()
        if pipeline:
            try:
                engines = pipeline.get_available_ocr_engines() if hasattr(pipeline, 'get_available_ocr_engines') else []
                info_text = f"Installed OCR Engines: {len(engines)}"
            except:
                info_text = "OCR Engines: Loading..."
        else:
            info_text = "Pipeline not available"
        info_label = QLabel(info_text)
        info_label.setStyleSheet("color: #666666; font-size: 9pt;")
        info_row.addWidget(info_label)
        info_row.addStretch()
        header_layout.addLayout(info_row)
        
        main_layout.addLayout(header_layout)
        
        # Models tree
        models_tree = QTreeWidget()
        models_tree.setHeaderLabels(["Model Name", "Engine Type", "Language", "Size", "Status"])
        models_tree.setColumnWidth(0, 300)
        models_tree.setColumnWidth(1, 120)
        models_tree.setColumnWidth(2, 100)
        models_tree.setColumnWidth(3, 100)
        models_tree.setColumnWidth(4, 150)
        models_tree.setAlternatingRowColors(True)
        main_layout.addWidget(models_tree)
        
        def refresh_models():
            """Refresh the models tree to show both installed engines and custom models."""
            models_tree.clear()
            
            # Initialize OCR model manager for custom models
            try:
                from app.ocr.ocr_model_manager import create_ocr_model_manager
                manager = create_ocr_model_manager()
            except ImportError:
                manager = None
            
            # Section 1: Installed OCR Engines
            engines_header = QTreeWidgetItem(["📦 Installed OCR Engines", "", "", "", ""])
            engines_header.setFirstColumnSpanned(True)
            font = engines_header.font(0)
            font.setBold(True)
            engines_header.setFont(0, font)
            engines_header.setBackground(0, Qt.GlobalColor.darkGray)
            models_tree.addTopLevelItem(engines_header)
            
            if not pipeline:
                item = QTreeWidgetItem(["  Pipeline not available", "", "", "", ""])
                item.setForeground(0, Qt.GlobalColor.darkGray)
                models_tree.addTopLevelItem(item)
            else:
                # Get installed OCR engines
                try:
                    engines = pipeline.get_available_ocr_engines() if hasattr(pipeline, 'get_available_ocr_engines') else []
                    
                    if not engines:
                        item = QTreeWidgetItem(["  No OCR engines discovered", "", "", "", ""])
                        item.setForeground(0, Qt.GlobalColor.darkGray)
                        models_tree.addTopLevelItem(item)
                    else:
                        # Engine info
                        engine_info = {
                            'easyocr': ('EasyOCR', 'Multi-language deep learning OCR'),
                            'tesseract': ('Tesseract OCR', 'Fast printed text recognition'),
                            'paddleocr': ('PaddleOCR', 'High accuracy multilingual OCR'),
                            'manga_ocr': ('Manga OCR', 'Japanese manga specialized'),
                            'onnx': ('ONNX Runtime', 'Optimized inference engine')
                        }
                        
                        # Get current engine
                        current_engine = None
                        if hasattr(pipeline, 'get_current_ocr_engine'):
                            current_engine = pipeline.get_current_ocr_engine()
                        
                        # Add each engine
                        for engine in engines:
                            engine_lower = engine.lower()
                            display_name, description = engine_info.get(engine_lower, (engine, 'OCR engine'))
                            
                            # Check if loaded
                            is_loaded = engine_lower == (current_engine or '').lower()
                            status = "✓ Loaded" if is_loaded else "Available"
                            
                            # Try to get language info
                            languages = "Multiple"
                            if engine_lower == 'manga_ocr':
                                languages = "Japanese"
                            
                            item = QTreeWidgetItem([
                                f"  {display_name}",
                                engine,
                                languages,
                                "-",
                                status
                            ])
                            
                            # Set tooltip with description
                            item.setToolTip(0, description)
                            
                            models_tree.addTopLevelItem(item)
                    
                except Exception as e:
                    item = QTreeWidgetItem([f"  Error loading engines: {e}", "", "", "", ""])
                    item.setForeground(0, Qt.GlobalColor.red)
                    models_tree.addTopLevelItem(item)
            
            # Section 2: Custom Model Files
            custom_header = QTreeWidgetItem(["🔧 Custom Model Files", "", "", "", ""])
            custom_header.setFirstColumnSpanned(True)
            font = custom_header.font(0)
            font.setBold(True)
            custom_header.setFont(0, font)
            custom_header.setBackground(0, Qt.GlobalColor.darkGray)
            models_tree.addTopLevelItem(custom_header)
            
            if not manager:
                item = QTreeWidgetItem(["  Model manager not available", "", "", "", ""])
                item.setForeground(0, Qt.GlobalColor.darkGray)
                models_tree.addTopLevelItem(item)
            else:
                # Get custom models
                custom_models = manager.discover_models()
                
                if not custom_models:
                    item = QTreeWidgetItem(["  No custom models found", "", "", "", ""])
                    item.setForeground(0, Qt.GlobalColor.darkGray)
                    models_tree.addTopLevelItem(item)
                else:
                    for model in custom_models:
                        status = "✓ Registered" if model.is_downloaded else "Available"
                        item = QTreeWidgetItem([
                            f"  {model.model_name}",
                            model.engine_type,
                            model.language,
                            f"{model.size_mb:.1f} MB",
                            status
                        ])
                        models_tree.addTopLevelItem(item)
            
            # Expand all
            models_tree.expandAll()
        
        # Initial refresh
        refresh_models()
        
        # Action buttons
        action_layout = QHBoxLayout()
        
        refresh_btn = QPushButton("🔄 Refresh")
        refresh_btn.clicked.connect(refresh_models)
        action_layout.addWidget(refresh_btn)
        
        discover_btn = QPushButton("🔍 Discover Custom Models")
        discover_btn.setProperty("class", "action")
        discover_btn.setToolTip("Scan OCR models folder for custom model files")
        discover_btn.clicked.connect(lambda: self._show_custom_models_dialog(dialog))
        action_layout.addWidget(discover_btn)
        
        action_layout.addStretch()
        
        close_btn = QPushButton("Close")
        close_btn.clicked.connect(dialog.accept)
        action_layout.addWidget(close_btn)
        
        main_layout.addLayout(action_layout)
        
        # Show dialog
        dialog.exec()
    
    def _show_custom_models_dialog(self, parent_dialog):
        """Show dialog for discovering custom OCR model files."""
        # Initialize OCR model manager
        try:
            from app.ocr.ocr_model_manager import create_ocr_model_manager
            manager = create_ocr_model_manager()
        except ImportError as e:
            QMessageBox.critical(
                parent_dialog,
                "Import Error",
                f"Failed to import OCR model manager:\n{e}\n\n"
                f"Please ensure the OCR model manager is properly installed."
            )
            return
        
        self._discover_custom_ocr_models(parent_dialog, manager, None)
    
    def _discover_custom_ocr_models(self, parent_dialog, manager, refresh_callback):
        """Discover custom OCR models and allow registration."""
        # Create dialog
        dialog = QDialog(parent_dialog)
        dialog.setWindowTitle("🔍 Discover Custom OCR Models")
        dialog.setMinimumSize(800, 600)
        
        layout = QVBoxLayout(dialog)
        layout.setContentsMargins(20, 20, 20, 20)
        layout.setSpacing(15)
        
        # Title
        title = QLabel("Discover Custom OCR Models")
        title.setStyleSheet("font-size: 12pt; font-weight: bold;")
        layout.addWidget(title)
        
        # Description
        desc = QLabel(
            "This tool scans your OCR models folder for custom OCR models.\n\n"
            f"📁 OCR models folder: {manager.cache_dir}\n\n"
            "To add a custom OCR model:\n"
            f"1. Place your model folder in: {manager.cache_dir}/your-model-name/\n"
            "2. Model folder should contain model files (.pth, .bin, config.json, etc.)\n"
            "3. Click 'Scan for Models' below\n"
            "4. Select the model and provide engine and language information\n"
            "5. Model will be registered for use!"
        )
        desc.setWordWrap(True)
        desc.setStyleSheet("color: #666666; font-size: 9pt; padding: 10px; background-color: rgba(100, 100, 100, 0.1); border-radius: 5px;")
        layout.addWidget(desc)
        
        # Scan button
        scan_btn = QPushButton("🔍 Scan for Models")
        scan_btn.setProperty("class", "action")
        layout.addWidget(scan_btn)
        
        # Discovered models list
        models_tree = QTreeWidget()
        models_tree.setHeaderLabels(["Model Folder", "Size", "Status"])
        models_tree.setColumnWidth(0, 400)
        models_tree.setColumnWidth(1, 100)
        models_tree.setColumnWidth(2, 200)
        models_tree.setAlternatingRowColors(True)
        layout.addWidget(models_tree)
        
        def scan_for_models():
            """Scan the OCR models folder for custom models."""
            models_tree.clear()
            
            if not manager.cache_dir.exists():
                QMessageBox.warning(
                    dialog,
                    "Folder Not Found",
                    f"OCR models folder not found:\n{manager.cache_dir}"
                )
                return
            
            discovered = []
            
            # Scan all subdirectories
            for model_dir in manager.cache_dir.iterdir():
                if not model_dir.is_dir() or model_dir.name in ["ocr_registry"]:
                    continue
                
                # Calculate size
                size = sum(f.stat().st_size for f in model_dir.rglob('*') if f.is_file())
                size_mb = size / (1024 * 1024)
                
                # Check if already registered
                is_registered = model_dir.name in manager.registry.get("models", {})
                status = "✓ Registered" if is_registered else "⚠️ Not Registered"
                
                discovered.append((model_dir.name, size_mb, status, is_registered))
            
            # Populate tree
            if not discovered:
                item = QTreeWidgetItem(["No custom OCR models found", "", ""])
                item.setForeground(0, Qt.GlobalColor.darkGray)
                models_tree.addTopLevelItem(item)
            else:
                for model_name, size_mb, status, is_registered in discovered:
                    item = QTreeWidgetItem([
                        model_name,
                        f"{size_mb:.1f} MB",
                        status
                    ])
                    if is_registered:
                        item.setForeground(0, Qt.GlobalColor.darkGray)
                    models_tree.addTopLevelItem(item)
                
                QMessageBox.information(
                    dialog,
                    "Scan Complete",
                    f"Found {len(discovered)} OCR model(s) in the models folder.\n\n"
                    f"Select a model and click 'Register Model' to register it."
                )
        
        scan_btn.clicked.connect(scan_for_models)
        
        # Action buttons
        button_layout = QHBoxLayout()
        
        register_btn = QPushButton("📝 Register Selected Model")
        register_btn.setProperty("class", "action")
        register_btn.clicked.connect(lambda: self._register_ocr_model(
            dialog, manager, models_tree, refresh_callback
        ))
        button_layout.addWidget(register_btn)
        
        button_layout.addStretch()
        
        close_btn = QPushButton("Close")
        close_btn.clicked.connect(dialog.accept)
        button_layout.addWidget(close_btn)
        
        layout.addLayout(button_layout)
        
        # Show dialog
        dialog.exec()
    
    def _register_ocr_model(self, parent_dialog, manager, models_tree, refresh_callback):
        """Register a selected OCR model."""
        # Get selected model
        selected_items = models_tree.selectedItems()
        if not selected_items:
            QMessageBox.warning(
                parent_dialog,
                "No Selection",
                "Please select a model from the list first."
            )
            return
        
        model_name = selected_items[0].text(0)
        if model_name == "No custom OCR models found":
            return
        
        # Check if already registered
        if "✓ Registered" in selected_items[0].text(2):
            QMessageBox.information(
                parent_dialog,
                "Already Registered",
                f"Model '{model_name}' is already registered."
            )
            return
        
        # Show registration dialog
        reg_dialog = QDialog(parent_dialog)
        reg_dialog.setWindowTitle(f"Register OCR Model: {model_name}")
        reg_dialog.setMinimumSize(500, 300)
        
        layout = QVBoxLayout(reg_dialog)
        layout.setContentsMargins(20, 20, 20, 20)
        layout.setSpacing(15)
        
        # Title
        title = QLabel(f"Register OCR Model: {model_name}")
        title.setStyleSheet("font-size: 11pt; font-weight: bold;")
        layout.addWidget(title)
        
        # Engine type selector
        engine_group = QGroupBox("OCR Engine Type")
        engine_layout = QVBoxLayout()
        engine_combo = QComboBox()
        engine_combo.addItem("EasyOCR", "easyocr")
        engine_combo.addItem("Tesseract", "tesseract")
        engine_combo.addItem("PaddleOCR", "paddleocr")
        engine_combo.addItem("Manga OCR", "manga_ocr")
        engine_combo.addItem("Custom", "custom")
        engine_layout.addWidget(engine_combo)
        engine_group.setLayout(engine_layout)
        layout.addWidget(engine_group)
        
        # Language selector
        lang_group = QGroupBox("Language")
        lang_layout = QVBoxLayout()
        lang_combo = QComboBox()
        lang_combo.setEditable(True)
        lang_combo.addItems([
            "en", "de", "es", "fr", "it", "pt", "ja", "zh", "ko", "ru", "ar",
            "hi", "th", "vi", "id", "uk", "cs", "pl", "nl", "tr", "multilingual"
        ])
        lang_layout.addWidget(lang_combo)
        lang_group.setLayout(lang_layout)
        layout.addWidget(lang_group)
        
        # Info message
        info_label = QLabel(
            "ℹ️ This will register the model for use with the OCR system.\n"
            "The model will be available for selection in OCR settings."
        )
        info_label.setWordWrap(True)
        info_label.setStyleSheet("color: #4A9EFF; font-size: 9pt; padding: 10px; background-color: rgba(74, 158, 255, 0.1); border-radius: 5px;")
        layout.addWidget(info_label)
        
        # Buttons
        button_layout = QHBoxLayout()
        button_layout.addStretch()
        
        cancel_btn = QPushButton("Cancel")
        cancel_btn.clicked.connect(reg_dialog.reject)
        button_layout.addWidget(cancel_btn)
        
        register_btn = QPushButton("📝 Register Model")
        register_btn.setProperty("class", "action")
        register_btn.clicked.connect(lambda: self._finalize_ocr_registration(
            reg_dialog, manager, model_name, engine_combo, lang_combo, refresh_callback
        ))
        button_layout.addWidget(register_btn)
        
        layout.addLayout(button_layout)
        
        # Show dialog
        reg_dialog.exec()
    
    def _finalize_ocr_registration(self, dialog, manager, model_name, engine_combo, 
                                   lang_combo, refresh_callback):
        """Finalize OCR model registration."""
        # Get values
        engine_type = engine_combo.currentData()
        language = lang_combo.currentText().strip()
        
        # Validate
        if not language:
            QMessageBox.warning(
                dialog,
                "Invalid Input",
                "Please provide a language code."
            )
            return
        
        # Register model
        try:
            success = manager.register_model(model_name, engine_type, language)
            
            if success:
                QMessageBox.information(
                    dialog,
                    "Registration Complete",
                    f"✅ Successfully registered OCR model: {model_name}!\n\n"
                    f"Engine: {engine_combo.currentText()}\n"
                    f"Language: {language}\n\n"
                    f"The model is now available for use."
                )
                dialog.accept()
                if refresh_callback:
                    refresh_callback()
            else:
                QMessageBox.critical(
                    dialog,
                    "Registration Failed",
                    f"❌ Failed to register model: {model_name}.\n\n"
                    f"Check logs for details."
                )
        except Exception as e:
            QMessageBox.critical(
                dialog,
                "Error",
                f"❌ Error registering model:\n\n{str(e)}"
            )
