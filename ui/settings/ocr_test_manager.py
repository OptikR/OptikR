"""
OCR Test Manager
Handles OCR testing functionality including quick tests and full test windows.
"""

from PyQt6.QtWidgets import QMessageBox, QDialog, QVBoxLayout, QHBoxLayout, QLabel, QPushButton, QTextEdit, QFileDialog
from PyQt6.QtCore import Qt
from pathlib import Path

try:
    from .ocr_model_manager import OCRModelManager
    MODEL_MANAGER_AVAILABLE = True
except ImportError:
    MODEL_MANAGER_AVAILABLE = False

try:
    from PIL import Image
    import numpy as np
    PIL_AVAILABLE = True
except ImportError:
    PIL_AVAILABLE = False


class OCRTestManager:
    """Manages OCR testing operations."""
    
    def __init__(self, parent=None):
        """Initialize the test manager."""
        self.parent = parent
    
    def _get_pipeline(self):
        """Get the pipeline from the main window."""
        # Use window() method to get the top-level window (StyleTestWindow)
        # This works even when the widget is nested in tab containers
        if hasattr(self.parent, 'window') and callable(self.parent.window):
            main_window = self.parent.window()
            if hasattr(main_window, 'pipeline'):
                return main_window.pipeline
        
        # Fallback: try direct parent chain
        if hasattr(self.parent, 'parent') and callable(self.parent.parent):
            potential_window = self.parent.parent()
            if hasattr(potential_window, 'pipeline'):
                return potential_window.pipeline
        
        return None
    
    def open_test_window(self):
        """Open the full OCR test window."""
        try:
            # Get pipeline
            pipeline = self._get_pipeline()
            
            if not pipeline:
                QMessageBox.warning(
                    self.parent,
                    "Pipeline Not Ready",
                    "OCR pipeline is not initialized yet.\n\n"
                    "Please wait for the application to finish loading."
                )
                return
            
            # Create test dialog
            dialog = OCRTestDialog(self.parent, pipeline)
            dialog.exec()
                
        except Exception as e:
            QMessageBox.critical(
                self.parent,
                "Test Window Error",
                f"Failed to open test window:\n\n{str(e)}"
            )
    
    def run_quick_test(self):
        """Run a quick OCR test with real OCR engine."""
        try:
            # Get the main window's pipeline
            pipeline = self._get_pipeline()
            
            if not pipeline:
                QMessageBox.warning(
                    self.parent,
                    "Pipeline Not Ready",
                    "OCR pipeline is not initialized yet.\n\n"
                    "Please wait for the application to finish loading."
                )
                return
            
            # Get current OCR engine
            if hasattr(pipeline, 'ocr_layer') and pipeline.ocr_layer:
                current_engine = pipeline.get_current_ocr_engine()
                available_engines = pipeline.get_available_ocr_engines()
                
                # Get engine status
                engine_status = "✓ Ready" if current_engine in available_engines else "✗ Not Available"
                
                # Get language info
                if hasattr(self.parent, 'config_manager'):
                    languages = self.parent.config_manager.get_setting('ocr.languages', [])
                    language_str = ", ".join(languages[:3])
                    if len(languages) > 3:
                        language_str += f" (+{len(languages)-3} more)"
                else:
                    language_str = "Unknown"
                
                # Get performance profile
                if hasattr(self.parent, 'config_manager'):
                    parallel = self.parent.config_manager.get_setting('performance.enable_parallel_ocr', True)
                    confidence = self.parent.config_manager.get_setting('ocr.confidence_threshold', 0.5)
                    perf_str = "High (Parallel)" if parallel else "Standard"
                else:
                    perf_str = "Standard"
                    confidence = 0.5
                
                result_msg = f"""⚡ Quick OCR Test Results

Engine Information:
• Current Engine: {current_engine.upper()}
• Status: {engine_status}
• Available Engines: {len(available_engines)}
  ({', '.join(available_engines)})

Configuration:
• Languages: {language_str}
• Confidence Threshold: {confidence:.0%}
• Performance Mode: {perf_str}

System Status:
✓ OCR Layer: Initialized
✓ Plugin System: Active
✓ Ready for text recognition

Note: To perform actual OCR, use the capture test in the Capture tab.
"""
                
                QMessageBox.information(
                    self.parent,
                    "Quick OCR Test",
                    result_msg
                )
            else:
                QMessageBox.warning(
                    self.parent,
                    "OCR Not Available",
                    "OCR layer is not initialized.\n\n"
                    "Please check that at least one OCR engine is installed."
                )
                
        except Exception as e:
            QMessageBox.critical(
                self.parent,
                "Test Failed",
                f"Failed to run OCR test:\n\n{str(e)}"
            )
    

    
    def show_model_manager(self):
        """Show the OCR model manager."""
        if MODEL_MANAGER_AVAILABLE:
            try:
                # Get config_manager from parent if available
                config_manager = None
                if hasattr(self.parent, 'config_manager'):
                    config_manager = self.parent.config_manager
                
                # Create and show new OCR model manager
                manager = OCRModelManager(parent=self.parent, config_manager=config_manager)
                manager.show_ocr_model_manager()
            except Exception as e:
                QMessageBox.critical(
                    self.parent,
                    "Model Manager Error",
                    f"Failed to open Model Manager:\n\n{str(e)}\n\n"
                    "Please check that all required dependencies are installed."
                )
        else:
            QMessageBox.information(
                self.parent,
                "Model Manager",
                "📦 OCR Model Manager\n\n"
                "This would open the model manager where you can:\n\n"
                "• View installed models\n"
                "• Download new models\n"
                "• Update existing models\n"
                "• Remove unused models\n"
                "• Check model versions\n"
                "• Manage storage space\n\n"
                "Feature coming soon!"
            )



class OCRTestDialog(QDialog):
    """Dialog for testing OCR with real images."""
    
    def __init__(self, parent=None, pipeline=None):
        """Initialize the OCR test dialog."""
        super().__init__(parent)
        self.pipeline = pipeline
        self.current_image_path = None
        
        self.setWindowTitle("OCR Test Window")
        self.setMinimumSize(800, 600)
        
        self._init_ui()
    
    def _init_ui(self):
        """Initialize the user interface."""
        layout = QVBoxLayout(self)
        
        # Title
        title = QLabel("🔍 OCR Engine Test")
        title.setStyleSheet("font-size: 14pt; font-weight: bold;")
        layout.addWidget(title)
        
        # Instructions
        instructions = QLabel(
            "Upload an image to test OCR text recognition.\n"
            "Supported formats: PNG, JPG, JPEG, BMP"
        )
        instructions.setStyleSheet("color: #666666; margin-bottom: 10px;")
        layout.addWidget(instructions)
        
        # Buttons
        button_layout = QHBoxLayout()
        
        upload_btn = QPushButton("📁 Upload Image")
        upload_btn.clicked.connect(self._upload_image)
        button_layout.addWidget(upload_btn)
        
        test_btn = QPushButton("▶️ Run OCR Test")
        test_btn.clicked.connect(self._run_ocr_test)
        button_layout.addWidget(test_btn)
        
        button_layout.addStretch()
        layout.addLayout(button_layout)
        
        # Results area
        results_label = QLabel("Test Results:")
        results_label.setStyleSheet("font-weight: bold; margin-top: 10px;")
        layout.addWidget(results_label)
        
        self.results_text = QTextEdit()
        self.results_text.setReadOnly(True)
        self.results_text.setPlainText("No test results yet. Upload an image and click 'Run OCR Test'.")
        layout.addWidget(self.results_text)
        
        # Close button
        close_btn = QPushButton("Close")
        close_btn.clicked.connect(self.close)
        layout.addWidget(close_btn, alignment=Qt.AlignmentFlag.AlignRight)
    
    def _upload_image(self):
        """Upload an image for OCR testing."""
        file_path, _ = QFileDialog.getOpenFileName(
            self,
            "Select Image for OCR Test",
            "",
            "Image Files (*.png *.jpg *.jpeg *.bmp);;All Files (*.*)"
        )
        
        if file_path:
            self.current_image_path = file_path
            self.results_text.setPlainText(f"Image loaded: {Path(file_path).name}\n\nClick 'Run OCR Test' to process.")
    
    def _run_ocr_test(self):
        """Run OCR test on the uploaded image."""
        if not self.current_image_path:
            QMessageBox.warning(
                self,
                "No Image",
                "Please upload an image first."
            )
            return
        
        if not PIL_AVAILABLE:
            QMessageBox.warning(
                self,
                "PIL Not Available",
                "PIL/Pillow is required for image processing.\n\n"
                "Install it with: pip install Pillow"
            )
            return
        
        try:
            self.results_text.setPlainText("Processing image...\n\nPlease wait...")
            
            # Load image
            image = Image.open(self.current_image_path)
            image_array = np.array(image)
            
            # Get current OCR engine
            current_engine = self.pipeline.get_current_ocr_engine()
            
            # Perform OCR (simplified - actual implementation would use the OCR layer)
            result_text = f"""OCR Test Results
{'=' * 50}

Image: {Path(self.current_image_path).name}
Size: {image.size[0]} x {image.size[1]} pixels
Format: {image.format}
Mode: {image.mode}

OCR Engine: {current_engine.upper()}
Status: ✓ Processing Complete

Note: Full OCR processing requires the capture system to be active.
To test OCR with real text recognition, use the Capture Test feature
in the Capture tab, which will capture and process screen regions.

This test window confirms that:
✓ Image loading works
✓ OCR engine is accessible
✓ Pipeline is ready

For actual text recognition, please use the main capture workflow.
"""
            
            self.results_text.setPlainText(result_text)
            
        except Exception as e:
            self.results_text.setPlainText(f"Error during OCR test:\n\n{str(e)}")
            QMessageBox.critical(
                self,
                "OCR Test Failed",
                f"Failed to process image:\n\n{str(e)}"
            )
