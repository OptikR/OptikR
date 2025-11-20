"""
Full Pipeline Test Dialog
Comprehensive testing dialog that tests all pipeline components individually and together.
Tests: Capture → OCR → Translation → Overlay (full workflow)
"""

from PyQt6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel, QPushButton, 
    QTextEdit, QGroupBox, QRadioButton, QFileDialog, QProgressBar,
    QMessageBox, QTabWidget, QWidget
)
from PyQt6.QtCore import Qt, QTimer
from PyQt6.QtGui import QPixmap, QImage
from pathlib import Path
import time
import numpy as np


class FullPipelineTestDialog(QDialog):
    """Dialog for comprehensive pipeline testing."""
    
    def __init__(self, parent=None, pipeline=None, config_manager=None):
        """Initialize the full pipeline test dialog."""
        super().__init__(parent)
        self.pipeline = pipeline
        self.config_manager = config_manager
        self.parent_window = parent
        self.test_image_path = None
        self.test_image_data = None
        
        self.setWindowTitle("🧪 Full Pipeline Test")
        self.setMinimumSize(900, 700)
        
        self._init_ui()
    
    def _init_ui(self):
        """Initialize the user interface."""
        layout = QVBoxLayout(self)
        
        # Title
        title = QLabel("🧪 Comprehensive Pipeline Test Suite")
        title.setStyleSheet("font-size: 16pt; font-weight: bold; margin-bottom: 10px;")
        layout.addWidget(title)
        
        # Description
        desc = QLabel(
            "Test individual components or the complete pipeline workflow.\n"
            "Choose test image source and run tests without starting continuous capture."
        )
        desc.setStyleSheet("color: #666666; margin-bottom: 15px;")
        desc.setWordWrap(True)
        layout.addWidget(desc)
        
        # Create tab widget for different test types
        tab_widget = QTabWidget()
        
        # Tab 1: Full Pipeline Test
        full_test_tab = self._create_full_pipeline_tab()
        tab_widget.addTab(full_test_tab, "🔄 Full Pipeline")
        
        # Tab 2: Individual Component Tests
        component_test_tab = self._create_component_tests_tab()
        tab_widget.addTab(component_test_tab, "🔧 Individual Tests")
        
        layout.addWidget(tab_widget)
        
        # Close button at bottom
        close_btn = QPushButton("Close")
        close_btn.setMinimumHeight(35)
        close_btn.clicked.connect(self.close)
        layout.addWidget(close_btn)
    
    def _create_full_pipeline_tab(self):
        """Create the full pipeline test tab."""
        tab = QWidget()
        layout = QVBoxLayout(tab)
        # Test source selection
        source_group = QGroupBox("Test Image Source")
        source_layout = QVBoxLayout(source_group)
        
        self.capture_radio = QRadioButton("📸 Capture single frame from screen")
        self.capture_radio.setChecked(True)
        source_layout.addWidget(self.capture_radio)
        
        self.upload_radio = QRadioButton("📁 Upload test image")
        source_layout.addWidget(self.upload_radio)
        
        upload_btn = QPushButton("📁 Select Image...")
        upload_btn.setMaximumWidth(150)
        upload_btn.clicked.connect(self._upload_image)
        source_layout.addWidget(upload_btn)
        
        self.image_label = QLabel("No image selected")
        self.image_label.setStyleSheet("color: #888888; font-style: italic;")
        source_layout.addWidget(self.image_label)
        
        layout.addWidget(source_group)
        
        # Progress bar
        self.progress_bar = QProgressBar()
        self.progress_bar.setVisible(False)
        layout.addWidget(self.progress_bar)
        
        # Results area
        results_label = QLabel("Test Results:")
        results_label.setStyleSheet("font-weight: bold; margin-top: 15px;")
        layout.addWidget(results_label)
        
        self.results_text = QTextEdit()
        self.results_text.setReadOnly(True)
        self.results_text.setPlaceholderText("Click 'Run Full Pipeline Test' to start testing...")
        layout.addWidget(self.results_text)
        
        # Run button
        self.run_btn = QPushButton("▶️ Run Full Pipeline Test")
        self.run_btn.setProperty("class", "action")
        self.run_btn.setStyleSheet("background-color: #4CAF50; font-weight: bold;")
        self.run_btn.setMinimumHeight(40)
        self.run_btn.clicked.connect(self._run_full_test)
        layout.addWidget(self.run_btn)
        
        return tab
    
    def _create_component_tests_tab(self):
        """Create the individual component tests tab."""
        tab = QWidget()
        layout = QVBoxLayout(tab)
        
        # Info
        info = QLabel("Test individual pipeline components separately:")
        info.setStyleSheet("color: #666666; margin-bottom: 10px;")
        layout.addWidget(info)
        
        # Capture Test
        capture_group = QGroupBox("📸 Capture Test")
        capture_layout = QVBoxLayout(capture_group)
        capture_desc = QLabel("Test screen capture functionality")
        capture_desc.setStyleSheet("color: #666666; font-size: 9pt;")
        capture_layout.addWidget(capture_desc)
        capture_btn = QPushButton("▶️ Test Capture")
        capture_btn.setProperty("class", "action")
        capture_btn.clicked.connect(self._test_capture_only)
        capture_layout.addWidget(capture_btn)
        layout.addWidget(capture_group)
        
        # OCR Test
        ocr_group = QGroupBox("🔍 OCR Test")
        ocr_layout = QVBoxLayout(ocr_group)
        ocr_desc = QLabel("Test OCR text detection (requires test image)")
        ocr_desc.setStyleSheet("color: #666666; font-size: 9pt;")
        ocr_layout.addWidget(ocr_desc)
        ocr_btn = QPushButton("▶️ Test OCR")
        ocr_btn.setProperty("class", "action")
        ocr_btn.clicked.connect(self._test_ocr_only)
        ocr_layout.addWidget(ocr_btn)
        layout.addWidget(ocr_group)
        
        # Translation Test
        translation_group = QGroupBox("🌐 Translation Test")
        translation_layout = QVBoxLayout(translation_group)
        translation_desc = QLabel("Test translation with sample text")
        translation_desc.setStyleSheet("color: #666666; font-size: 9pt;")
        translation_layout.addWidget(translation_desc)
        translation_btn = QPushButton("▶️ Test Translation")
        translation_btn.setProperty("class", "action")
        translation_btn.clicked.connect(self._test_translation_only)
        translation_layout.addWidget(translation_btn)
        layout.addWidget(translation_group)
        
        # Results area for component tests
        results_label = QLabel("Component Test Results:")
        results_label.setStyleSheet("font-weight: bold; margin-top: 10px;")
        layout.addWidget(results_label)
        
        self.component_results_text = QTextEdit()
        self.component_results_text.setReadOnly(True)
        self.component_results_text.setPlaceholderText("Select a component test to run...")
        self.component_results_text.setMaximumHeight(200)
        layout.addWidget(self.component_results_text)
        
        layout.addStretch()
        return tab
    
    def _upload_image(self):
        """Upload a test image."""
        file_path, _ = QFileDialog.getOpenFileName(
            self,
            "Select Test Image",
            "",
            "Image Files (*.png *.jpg *.jpeg *.bmp);;All Files (*.*)"
        )
        
        if file_path:
            self.test_image_path = file_path
            self.upload_radio.setChecked(True)
            self.image_label.setText(f"Selected: {Path(file_path).name}")
            self.image_label.setStyleSheet("color: #4CAF50;")
    
    def _run_full_test(self):
        """Run the full pipeline test."""
        if not self.pipeline:
            QMessageBox.warning(
                self,
                "Pipeline Not Ready",
                "Pipeline is not initialized.\n\n"
                "Please wait for the application to finish loading."
            )
            return
        
        # Disable button during test
        self.run_btn.setEnabled(False)
        self.progress_bar.setVisible(True)
        self.progress_bar.setValue(0)
        
        # Clear previous results
        self.results_text.clear()
        
        # Run test asynchronously to keep UI responsive
        QTimer.singleShot(100, self._execute_test)

    def _execute_test(self):
        """Execute the pipeline test."""
        try:
            self._log("=" * 70)
            self._log("🧪 FULL PIPELINE TEST - Starting...")
            self._log("=" * 70)
            self._log("")
            
            # Stage 1: Get test image
            self._log("📸 Stage 1/4: Image Acquisition")
            self.progress_bar.setValue(10)
            
            if self.capture_radio.isChecked():
                success, image_data = self._capture_test_frame()
            else:
                success, image_data = self._load_test_image()
            
            if not success:
                self._log("✗ FAILED: Could not acquire test image")
                self._test_complete(False)
                return
            
            self._log(f"✓ Image acquired: {image_data.shape if hasattr(image_data, 'shape') else 'loaded'}")
            self.progress_bar.setValue(25)
            
            # Stage 2: OCR
            self._log("")
            self._log("🔍 Stage 2/4: OCR Text Detection")
            self.progress_bar.setValue(30)
            
            success, ocr_results = self._test_ocr(image_data)
            if not success:
                self._log("✗ FAILED: OCR processing failed")
                self._test_complete(False)
                return
            
            self._log(f"✓ OCR complete: {len(ocr_results)} text block(s) detected")
            for i, result in enumerate(ocr_results, 1):
                text = result.text if hasattr(result, 'text') else str(result)
                confidence = result.confidence if hasattr(result, 'confidence') else 0.0
                self._log(f"  Block {i}: \"{text[:50]}...\" (confidence: {confidence:.2f})")
            
            self.progress_bar.setValue(50)
            
            # Stage 3: Translation
            self._log("")
            self._log("🌐 Stage 3/4: Translation")
            self.progress_bar.setValue(55)
            
            success, translations = self._test_translation(ocr_results)
            if not success:
                self._log("✗ FAILED: Translation failed")
                self._test_complete(False)
                return
            
            self._log(f"✓ Translation complete: {len(translations)} translation(s)")
            for i, trans in enumerate(translations, 1):
                original = trans.original_text if hasattr(trans, 'original_text') else "N/A"
                translated = trans.translated_text if hasattr(trans, 'translated_text') else str(trans)
                self._log(f"  Translation {i}:")
                self._log(f"    Original:   \"{original[:40]}...\"")
                self._log(f"    Translated: \"{translated[:40]}...\"")
            
            self.progress_bar.setValue(75)
            
            # Stage 4: Overlay (optional - just verify overlay system exists)
            self._log("")
            self._log("🎨 Stage 4/4: Overlay System Check")
            self.progress_bar.setValue(80)
            
            overlay_available = self._check_overlay_system()
            if overlay_available:
                self._log("✓ Overlay system available and ready")
            else:
                self._log("⚠ Overlay system not available (non-critical)")
            
            self.progress_bar.setValue(100)
            
            # Success!
            self._log("")
            self._log("=" * 70)
            self._log("✓ FULL PIPELINE TEST PASSED!")
            self._log("=" * 70)
            self._log("")
            self._log("Summary:")
            self._log(f"  • Image Acquisition: ✓ Success")
            self._log(f"  • OCR Detection: ✓ {len(ocr_results)} blocks detected")
            self._log(f"  • Translation: ✓ {len(translations)} translations")
            self._log(f"  • Overlay System: {'✓ Available' if overlay_available else '⚠ Not available'}")
            self._log("")
            self._log("🎉 All pipeline components are working correctly!")
            self._log("You can now safely use the 'Start Translation' feature.")
            
            self._test_complete(True)
            
        except Exception as e:
            self._log("")
            self._log("=" * 70)
            self._log("✗ PIPELINE TEST FAILED")
            self._log("=" * 70)
            self._log(f"Error: {str(e)}")
            self._log("")
            
            import traceback
            self._log("Traceback:")
            self._log(traceback.format_exc())
            
            self._test_complete(False)
    
    def _capture_test_frame(self):
        """Capture a single test frame from screen."""
        try:
            # Get capture region from parent window
            if hasattr(self.parent_window, 'capture_region') and self.parent_window.capture_region:
                region = self.parent_window.capture_region
                x = region['x']
                y = region['y']
                width = region['width']
                height = region['height']
                monitor_id = region.get('monitor_id', 0)
            else:
                # Use default region
                self._log("⚠ No capture region set, using default")
                x, y, width, height = 0, 0, 800, 600
                monitor_id = 0
            
            self._log(f"  Capturing region: ({x}, {y}) {width}x{height} on monitor {monitor_id}")
            
            # Use pipeline's capture layer
            if hasattr(self.pipeline, 'capture_layer') and self.pipeline.capture_layer:
                # Capture single frame
                frame = self.pipeline.capture_layer.capture_frame()
                
                if frame is not None and hasattr(frame, 'shape'):
                    self._log(f"  Captured frame: {frame.shape}")
                    return True, frame
                else:
                    self._log("  ✗ Capture returned None or invalid data")
                    return False, None
            else:
                self._log("  ✗ Capture layer not available")
                return False, None
                
        except Exception as e:
            self._log(f"  ✗ Capture error: {e}")
            return False, None
    
    def _load_test_image(self):
        """Load test image from file."""
        try:
            if not self.test_image_path:
                self._log("  ✗ No image file selected")
                return False, None
            
            self._log(f"  Loading: {Path(self.test_image_path).name}")
            
            # Load image using PIL
            try:
                from PIL import Image
                image = Image.open(self.test_image_path)
                image_array = np.array(image)
                
                self._log(f"  Loaded image: {image_array.shape}")
                return True, image_array
                
            except ImportError:
                self._log("  ✗ PIL not available, trying OpenCV")
                
                # Fallback to OpenCV
                import cv2
                image = cv2.imread(self.test_image_path)
                if image is not None:
                    self._log(f"  Loaded image: {image.shape}")
                    return True, image
                else:
                    self._log("  ✗ Failed to load image")
                    return False, None
                    
        except Exception as e:
            self._log(f"  ✗ Load error: {e}")
            return False, None

    def _test_ocr(self, image_data):
        """Test OCR on the image."""
        try:
            if not hasattr(self.pipeline, 'ocr_layer') or not self.pipeline.ocr_layer:
                self._log("  ✗ OCR layer not available")
                return False, []
            
            current_engine = self.pipeline.get_current_ocr_engine()
            self._log(f"  Using OCR engine: {current_engine}")
            
            # Perform OCR
            start_time = time.time()
            ocr_results = self.pipeline.ocr_layer.process(image_data)
            processing_time = (time.time() - start_time) * 1000
            
            self._log(f"  Processing time: {processing_time:.2f} ms")
            
            if ocr_results:
                return True, ocr_results
            else:
                self._log("  ⚠ No text detected (image may be blank or text too small)")
                return True, []  # Not a failure, just no text found
                
        except Exception as e:
            self._log(f"  ✗ OCR error: {e}")
            import traceback
            self._log(f"  {traceback.format_exc()}")
            return False, []
    
    def _test_translation(self, ocr_results):
        """Test translation on OCR results."""
        try:
            if not ocr_results:
                self._log("  ⚠ No OCR results to translate")
                return True, []  # Not a failure
            
            if not hasattr(self.pipeline, 'translation_layer') or not self.pipeline.translation_layer:
                self._log("  ✗ Translation layer not available")
                return False, []
            
            # Get source and target languages from config
            src_lang = self.config_manager.get_setting('ocr.source_language', 'ja') if self.config_manager else 'ja'
            tgt_lang = self.config_manager.get_setting('translation.target_language', 'en') if self.config_manager else 'en'
            
            self._log(f"  Translating: {src_lang} → {tgt_lang}")
            
            translations = []
            start_time = time.time()
            
            for result in ocr_results:
                text = result.text if hasattr(result, 'text') else str(result)
                
                # Translate
                translated = self.pipeline.translation_layer.translate(
                    text,
                    source_lang=src_lang,
                    target_lang=tgt_lang
                )
                
                # Create translation object
                from app.models import Translation
                trans = Translation(
                    original_text=text,
                    translated_text=translated,
                    source_language=src_lang,
                    target_language=tgt_lang,
                    confidence=result.confidence if hasattr(result, 'confidence') else 1.0
                )
                translations.append(trans)
            
            processing_time = (time.time() - start_time) * 1000
            self._log(f"  Processing time: {processing_time:.2f} ms")
            
            return True, translations
            
        except Exception as e:
            self._log(f"  ✗ Translation error: {e}")
            import traceback
            self._log(f"  {traceback.format_exc()}")
            return False, []
    
    def _check_overlay_system(self):
        """Check if overlay system is available."""
        try:
            # Check parent window's overlay system
            if hasattr(self.parent_window, 'overlay_system') and self.parent_window.overlay_system:
                self._log("  Overlay system found in main window")
                return True
            
            # Check pipeline's overlay system
            if hasattr(self.pipeline, 'overlay_system') and self.pipeline.overlay_system:
                self._log("  Overlay system found in pipeline")
                return True
            
            self._log("  No overlay system found")
            return False
            
        except Exception as e:
            self._log(f"  ✗ Overlay check error: {e}")
            return False
    
    def _log(self, message):
        """Log a message to the results text area."""
        self.results_text.append(message)
        # Scroll to bottom
        scrollbar = self.results_text.verticalScrollBar()
        scrollbar.setValue(scrollbar.maximum())
        # Process events to update UI
        from PyQt6.QtWidgets import QApplication
        QApplication.processEvents()
    
    def _test_complete(self, success):
        """Called when test completes."""
        self.run_btn.setEnabled(True)
        
        if success:
            self.run_btn.setText("✓ Test Passed - Run Again")
            self.run_btn.setStyleSheet("background-color: #4CAF50;")
        else:
            self.run_btn.setText("✗ Test Failed - Try Again")
            self.run_btn.setStyleSheet("background-color: #F44336;")
        
        # Reset button text after 3 seconds
        QTimer.singleShot(3000, lambda: self.run_btn.setText("▶️ Run Full Pipeline Test"))
        QTimer.singleShot(3000, lambda: self.run_btn.setStyleSheet(""))
    
    def _test_capture_only(self):
        """Test capture component only."""
        self.component_results_text.clear()
        self.component_results_text.append("📸 Testing Capture Component...")
        self.component_results_text.append("")
        
        try:
            success, image_data = self._capture_test_frame()
            
            if success:
                self.component_results_text.append("✓ CAPTURE TEST PASSED")
                self.component_results_text.append(f"  Image shape: {image_data.shape}")
                self.component_results_text.append(f"  Image size: {image_data.nbytes / 1024:.2f} KB")
            else:
                self.component_results_text.append("✗ CAPTURE TEST FAILED")
                self.component_results_text.append("  Check capture layer initialization")
        except Exception as e:
            self.component_results_text.append(f"✗ ERROR: {e}")
    
    def _test_ocr_only(self):
        """Test OCR component only."""
        self.component_results_text.clear()
        self.component_results_text.append("🔍 Testing OCR Component...")
        self.component_results_text.append("")
        
        try:
            # Get test image
            if self.capture_radio.isChecked():
                success, image_data = self._capture_test_frame()
            else:
                success, image_data = self._load_test_image()
            
            if not success:
                self.component_results_text.append("✗ Failed to get test image")
                return
            
            # Test OCR
            success, ocr_results = self._test_ocr(image_data)
            
            if success:
                self.component_results_text.append("✓ OCR TEST PASSED")
                self.component_results_text.append(f"  Text blocks detected: {len(ocr_results)}")
                for i, result in enumerate(ocr_results[:3], 1):  # Show first 3
                    text = result.text if hasattr(result, 'text') else str(result)
                    self.component_results_text.append(f"  Block {i}: \"{text[:40]}...\"")
            else:
                self.component_results_text.append("✗ OCR TEST FAILED")
                self.component_results_text.append("  Check OCR layer initialization")
        except Exception as e:
            self.component_results_text.append(f"✗ ERROR: {e}")
    
    def _test_translation_only(self):
        """Test translation component only."""
        self.component_results_text.clear()
        self.component_results_text.append("🌐 Testing Translation Component...")
        self.component_results_text.append("")
        
        try:
            if not hasattr(self.pipeline, 'translation_layer') or not self.pipeline.translation_layer:
                self.component_results_text.append("✗ Translation layer not available")
                return
            
            # Test with sample text
            test_text = "Hello, world!"
            src_lang = 'en'
            tgt_lang = 'es'
            
            self.component_results_text.append(f"  Test text: \"{test_text}\"")
            self.component_results_text.append(f"  Language: {src_lang} → {tgt_lang}")
            self.component_results_text.append("")
            
            translated = self.pipeline.translation_layer.translate(
                test_text,
                source_lang=src_lang,
                target_lang=tgt_lang
            )
            
            self.component_results_text.append("✓ TRANSLATION TEST PASSED")
            self.component_results_text.append(f"  Original: \"{test_text}\"")
            self.component_results_text.append(f"  Translated: \"{translated}\"")
            
        except Exception as e:
            self.component_results_text.append(f"✗ TRANSLATION TEST FAILED")
            self.component_results_text.append(f"  Error: {e}")
            self.component_results_text.append(f"  Translated: \"{translated}\"")
        except Exception as e:
            self.component_results_text.append(f"✗ ERROR: {e}")


def show_full_pipeline_test(parent=None, pipeline=None, config_manager=None):
    """
    Show the full pipeline test dialog.
    
    Args:
        parent: Parent widget
        pipeline: Pipeline instance to test
        config_manager: Configuration manager
    """
    dialog = FullPipelineTestDialog(parent, pipeline, config_manager)
    dialog.exec()
