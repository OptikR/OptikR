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
from app.localization import TranslatableMixin, tr


class FullPipelineTestDialog(TranslatableMixin, QDialog):
    """Dialog for comprehensive pipeline testing."""
    
    def __init__(self, parent=None, pipeline=None, config_manager=None):
        """Initialize the full pipeline test dialog."""
        super().__init__(parent)
        self.pipeline = pipeline
        self.config_manager = config_manager
        self.parent_window = parent
        self.test_image_path = None
        self.test_image_data = None
        
        self.setWindowTitle(tr("full_pipeline_test"))
        self.setMinimumSize(900, 700)
        
        self._init_ui()
    
    def _init_ui(self):
        """Initialize the user interface."""
        layout = QVBoxLayout(self)
        
        # Title
        title = QLabel(tr("comprehensive_pipeline_test_suite"))
        title.setStyleSheet("font-size: 16pt; font-weight: bold; margin-bottom: 10px;")
        layout.addWidget(title)
        
        # Description
        desc = QLabel(tr("pipeline_test_description"))
        desc.setStyleSheet("color: #666666; margin-bottom: 15px;")
        desc.setWordWrap(True)
        layout.addWidget(desc)
        
        # Create tab widget for different test types
        tab_widget = QTabWidget()
        
        # Tab 1: Full Pipeline Test
        full_test_tab = self._create_full_pipeline_tab()
        tab_widget.addTab(full_test_tab, tr("pipeline_test_tab_full_pipeline"))
        
        # Tab 2: Individual Component Tests
        component_test_tab = self._create_component_tests_tab()
        tab_widget.addTab(component_test_tab, tr("pipeline_test_tab_individual_tests"))
        
        layout.addWidget(tab_widget)
        
        # Close button at bottom
        close_btn = QPushButton(tr("close"))
        close_btn.setMinimumHeight(35)
        close_btn.clicked.connect(self.close)
        layout.addWidget(close_btn)
    
    def _create_full_pipeline_tab(self):
        """Create the full pipeline test tab."""
        tab = QWidget()
        layout = QVBoxLayout(tab)
        # Test source selection
        source_group = QGroupBox(tr("test_image_source"))
        source_layout = QVBoxLayout(source_group)
        
        self.capture_radio = QRadioButton(tr("pipeline_test_capture_frame_radio"))
        self.capture_radio.setChecked(True)
        source_layout.addWidget(self.capture_radio)
        
        self.upload_radio = QRadioButton(tr("pipeline_test_upload_image_radio"))
        source_layout.addWidget(self.upload_radio)
        
        upload_btn = QPushButton(tr("select_image"))
        upload_btn.setMaximumWidth(150)
        upload_btn.clicked.connect(self._upload_image)
        source_layout.addWidget(upload_btn)
        
        self.image_label = QLabel(tr("no_image_selected"))
        self.image_label.setStyleSheet("color: #888888; font-style: italic;")
        source_layout.addWidget(self.image_label)
        
        layout.addWidget(source_group)
        
        # Progress bar
        self.progress_bar = QProgressBar()
        self.progress_bar.setVisible(False)
        layout.addWidget(self.progress_bar)
        
        # Results area
        results_label = QLabel(tr("test_results"))
        results_label.setStyleSheet("font-weight: bold; margin-top: 15px;")
        layout.addWidget(results_label)
        
        self.results_text = QTextEdit()
        self.results_text.setReadOnly(True)
        self.results_text.setPlaceholderText(tr("click_run_full_pipeline_test_to_start_testing"))
        layout.addWidget(self.results_text)
        
        # Run button
        self.run_btn = QPushButton(tr("run_full_pipeline_test"))
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
        info = QLabel(tr("test_individual_pipeline_components_separately"))
        info.setStyleSheet("color: #666666; margin-bottom: 10px;")
        layout.addWidget(info)
        
        # Capture Test
        capture_group = QGroupBox(tr("capture_test"))
        capture_layout = QVBoxLayout(capture_group)
        capture_desc = QLabel(tr("test_screen_capture_functionality"))
        capture_desc.setStyleSheet("color: #666666; font-size: 9pt;")
        capture_layout.addWidget(capture_desc)
        capture_btn = QPushButton(tr("test_capture_2"))
        capture_btn.setProperty("class", "action")
        capture_btn.clicked.connect(self._test_capture_only)
        capture_layout.addWidget(capture_btn)
        layout.addWidget(capture_group)
        
        # OCR Test
        ocr_group = QGroupBox(tr("ocr_test"))
        ocr_layout = QVBoxLayout(ocr_group)
        ocr_desc = QLabel(tr("test_ocr_text_detection_requires_test_image"))
        ocr_desc.setStyleSheet("color: #666666; font-size: 9pt;")
        ocr_layout.addWidget(ocr_desc)
        ocr_btn = QPushButton(tr("test_ocr"))
        ocr_btn.setProperty("class", "action")
        ocr_btn.clicked.connect(self._test_ocr_only)
        ocr_layout.addWidget(ocr_btn)
        layout.addWidget(ocr_group)
        
        # Translation Test
        translation_group = QGroupBox(tr("translation_test"))
        translation_layout = QVBoxLayout(translation_group)
        translation_desc = QLabel(tr("test_translation_with_sample_text"))
        translation_desc.setStyleSheet("color: #666666; font-size: 9pt;")
        translation_layout.addWidget(translation_desc)
        translation_btn = QPushButton(tr("test_translation"))
        translation_btn.setProperty("class", "action")
        translation_btn.clicked.connect(self._test_translation_only)
        translation_layout.addWidget(translation_btn)
        layout.addWidget(translation_group)
        
        # Results area for component tests
        results_label = QLabel(tr("component_test_results"))
        results_label.setStyleSheet("font-weight: bold; margin-top: 10px;")
        layout.addWidget(results_label)
        
        self.component_results_text = QTextEdit()
        self.component_results_text.setReadOnly(True)
        self.component_results_text.setPlaceholderText(tr("select_a_component_test_to_run"))
        self.component_results_text.setMaximumHeight(200)
        layout.addWidget(self.component_results_text)
        
        layout.addStretch()
        return tab
    
    def _upload_image(self):
        """Upload a test image."""
        file_path, _ = QFileDialog.getOpenFileName(
            self,
            tr("pipeline_test_select_test_image"),
            "",
            "Image Files (*.png *.jpg *.jpeg *.bmp);;All Files (*.*)"
        )
        
        if file_path:
            self.test_image_path = file_path
            self.upload_radio.setChecked(True)
            self.image_label.setText(tr("pipeline_test_selected").format(name=Path(file_path).name))
            self.image_label.setStyleSheet("color: #4CAF50;")
    
    def _run_full_test(self):
        """Run the full pipeline test."""
        if not self.pipeline:
            QMessageBox.warning(
                self,
                tr("pipeline_test_pipeline_not_ready"),
                tr("pipeline_test_pipeline_not_initialized")
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
            self._log(tr("pipeline_test_starting"))
            self._log("=" * 70)
            self._log("")
            
            # Stage 1: Get test image
            self._log(tr("pipeline_test_stage1_image"))
            self.progress_bar.setValue(10)
            
            if self.capture_radio.isChecked():
                success, image_data = self._capture_test_frame()
            else:
                success, image_data = self._load_test_image()
            
            if not success:
                self._log(tr("pipeline_test_failed_acquire_image"))
                self._test_complete(False)
                return
            
            self._log(f"✓ Image acquired: {image_data.shape if hasattr(image_data, 'shape') else 'loaded'}")
            self.progress_bar.setValue(25)
            
            # Stage 2: OCR
            self._log("")
            self._log(tr("pipeline_test_stage2_ocr"))
            self.progress_bar.setValue(30)
            
            success, ocr_results = self._test_ocr(image_data)
            if not success:
                self._log(tr("pipeline_test_failed_ocr"))
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
            self._log(tr("pipeline_test_stage3_translation"))
            self.progress_bar.setValue(55)
            
            success, translations = self._test_translation(ocr_results)
            if not success:
                self._log(tr("pipeline_test_failed_translation"))
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
            self._log(tr("pipeline_test_stage4_overlay"))
            self.progress_bar.setValue(80)
            
            overlay_available = self._check_overlay_system()
            if overlay_available:
                self._log(tr("pipeline_test_overlay_ready"))
            else:
                self._log(tr("pipeline_test_overlay_unavailable"))
            
            self.progress_bar.setValue(100)
            
            # Success!
            self._log("")
            self._log("=" * 70)
            self._log(tr("pipeline_test_passed"))
            self._log("=" * 70)
            self._log("")
            self._log(tr("pipeline_test_summary"))
            self._log(tr("pipeline_test_summary_image_acquisition"))
            self._log(tr("pipeline_test_summary_ocr_detection").format(count=len(ocr_results)))
            self._log(tr("pipeline_test_summary_translation_count").format(count=len(translations)))
            overlay_text = tr("pipeline_test_summary_overlay_available") if overlay_available else tr("pipeline_test_summary_overlay_unavailable")
            self._log(overlay_text)
            self._log("")
            self._log(tr("pipeline_test_all_working"))
            self._log(tr("pipeline_test_safe_to_start"))
            
            self._test_complete(True)
            
        except Exception as e:
            self._log("")
            self._log("=" * 70)
            self._log(tr("pipeline_test_failed_title"))
            self._log("=" * 70)
            self._log(f"{tr('pipeline_test_error_label')}: {str(e)}")
            self._log("")
            
            import traceback
            self._log(tr("pipeline_test_traceback"))
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
            from app.models import Frame
            ocr_frame = Frame(data=image_data, timestamp=time.time(), source_region=None)
            start_time = time.time()
            ocr_results = self.pipeline.ocr_layer.extract_text(ocr_frame)
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
            src_lang = self.config_manager.get_setting('translation.source_language', 'en') if self.config_manager else 'en'
            tgt_lang = self.config_manager.get_setting('translation.target_language', 'de') if self.config_manager else 'de'
            
            self._log(f"  Translating: {src_lang} → {tgt_lang}")
            
            translations = []
            start_time = time.time()
            
            engine = self.config_manager.get_setting('translation.engine', 'marianmt') if self.config_manager else 'marianmt'
            
            for result in ocr_results:
                text = result.text if hasattr(result, 'text') else str(result)
                
                # Translate
                translated = self.pipeline.translation_layer.translate(
                    text, engine, src_lang, tgt_lang, {}
                )
                
                # Create translation object
                from app.models import Translation, Rectangle
                trans = Translation(
                    original_text=text,
                    translated_text=translated,
                    source_language=src_lang,
                    target_language=tgt_lang,
                    position=Rectangle(0, 0, 0, 0),
                    confidence=result.confidence if hasattr(result, 'confidence') else 1.0,
                    engine_used=engine
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
            if self.pipeline and hasattr(self.pipeline, 'overlay_system') and self.pipeline.overlay_system:
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
            self.run_btn.setText(tr("test_passed_run_again"))
            self.run_btn.setStyleSheet("background-color: #4CAF50;")
        else:
            self.run_btn.setText(tr("test_failed_try_again"))
            self.run_btn.setStyleSheet("background-color: #F44336;")
        
        # Reset button text after 3 seconds
        QTimer.singleShot(3000, lambda: self.run_btn.setText(tr("run_full_pipeline_test")))
        QTimer.singleShot(3000, lambda: self.run_btn.setStyleSheet(""))
    
    def _test_capture_only(self):
        """Test capture component only."""
        self.component_results_text.clear()
        self.component_results_text.append(tr("pipeline_test_testing_capture"))
        self.component_results_text.append("")
        
        try:
            success, image_data = self._capture_test_frame()
            
            if success:
                self.component_results_text.append(tr("pipeline_test_capture_passed"))
                self.component_results_text.append(f"  Image shape: {image_data.shape}")
                self.component_results_text.append(f"  Image size: {image_data.nbytes / 1024:.2f} KB")
            else:
                self.component_results_text.append(tr("pipeline_test_capture_failed"))
                self.component_results_text.append(f"  {tr('pipeline_test_check_capture_layer')}")
        except Exception as e:
            self.component_results_text.append(f"✗ ERROR: {e}")
    
    def _test_ocr_only(self):
        """Test OCR component only."""
        self.component_results_text.clear()
        self.component_results_text.append(tr("pipeline_test_testing_ocr"))
        self.component_results_text.append("")
        
        try:
            # Get test image
            if self.capture_radio.isChecked():
                success, image_data = self._capture_test_frame()
            else:
                success, image_data = self._load_test_image()
            
            if not success:
                self.component_results_text.append(tr("pipeline_test_failed_get_image"))
                return
            
            # Test OCR
            success, ocr_results = self._test_ocr(image_data)
            
            if success:
                self.component_results_text.append(tr("pipeline_test_ocr_passed"))
                self.component_results_text.append(f"  Text blocks detected: {len(ocr_results)}")
                for i, result in enumerate(ocr_results[:3], 1):  # Show first 3
                    text = result.text if hasattr(result, 'text') else str(result)
                    self.component_results_text.append(f"  Block {i}: \"{text[:40]}...\"")
            else:
                self.component_results_text.append(tr("pipeline_test_ocr_failed"))
                self.component_results_text.append(f"  {tr('pipeline_test_check_ocr_layer')}")
        except Exception as e:
            self.component_results_text.append(f"✗ ERROR: {e}")
    
    def _test_translation_only(self):
        """Test translation component only."""
        self.component_results_text.clear()
        self.component_results_text.append(tr("pipeline_test_testing_translation"))
        self.component_results_text.append("")
        
        try:
            if not hasattr(self.pipeline, 'translation_layer') or not self.pipeline.translation_layer:
                self.component_results_text.append(tr("pipeline_test_translation_unavailable"))
                return
            
            # Test with sample text
            test_text = "Hello, world!"
            src_lang = 'en'
            tgt_lang = 'es'
            
            self.component_results_text.append(f"  Test text: \"{test_text}\"")
            self.component_results_text.append(f"  Language: {src_lang} → {tgt_lang}")
            self.component_results_text.append("")
            
            engine = self.config_manager.get_setting('translation.engine', 'marianmt') if self.config_manager else 'marianmt'
            translated = self.pipeline.translation_layer.translate(
                test_text, engine, src_lang, tgt_lang, {}
            )
            
            self.component_results_text.append(tr("pipeline_test_translation_passed"))
            self.component_results_text.append(f"  Original: \"{test_text}\"")
            self.component_results_text.append(f"  Translated: \"{translated}\"")
            
        except Exception as e:
            self.component_results_text.append(tr("pipeline_test_translation_test_failed"))
            self.component_results_text.append(f"  Error: {e}")


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
