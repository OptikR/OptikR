"""
Translation Test Manager
Handles translation testing functionality for all translation engines.
"""

from PyQt6.QtWidgets import QMessageBox, QDialog, QVBoxLayout, QHBoxLayout, QLabel, QPushButton, QTextEdit, QComboBox
from PyQt6.QtCore import Qt
from pathlib import Path


class TranslationTestManager:
    """Manages translation testing operations."""
    
    def __init__(self, parent=None):
        """Initialize the test manager."""
        self.parent = parent
    
    def _get_pipeline(self):
        """Get the pipeline from the main window."""
        # Use window() method to get the top-level window (StyleTestWindow)
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
    
    def test_translation_engine(self, engine_name: str):
        """
        Test a specific translation engine.
        
        Args:
            engine_name: Name of the engine to test (marianmt, google_free, libretranslate, etc.)
        """
        try:
            # Get pipeline
            pipeline = self._get_pipeline()
            
            if not pipeline:
                QMessageBox.warning(
                    self.parent,
                    "Pipeline Not Ready",
                    "Translation pipeline is not initialized yet.\n\n"
                    "Please wait for the application to finish loading."
                )
                return
            
            # Check if translation layer exists
            if not hasattr(pipeline, 'translation_layer') or not pipeline.translation_layer:
                QMessageBox.warning(
                    self.parent,
                    "Translation Not Available",
                    "Translation layer is not initialized.\n\n"
                    "Please check that translation engines are installed."
                )
                return
            
            # Create test dialog
            dialog = TranslationTestDialog(self.parent, pipeline, engine_name)
            dialog.exec()
                
        except Exception as e:
            QMessageBox.critical(
                self.parent,
                "Test Failed",
                f"Failed to test translation engine:\n\n{str(e)}"
            )
    
    def run_quick_test(self, engine_name: str):
        """
        Run a quick translation test.
        
        Args:
            engine_name: Name of the engine to test
        """
        try:
            # Get pipeline
            pipeline = self._get_pipeline()
            
            if not pipeline:
                QMessageBox.warning(
                    self.parent,
                    "Pipeline Not Ready",
                    "Translation pipeline is not initialized yet.\n\n"
                    "Please wait for the application to finish loading."
                )
                return
            
            # Check if translation layer exists
            if not hasattr(pipeline, 'translation_layer') or not pipeline.translation_layer:
                QMessageBox.warning(
                    self.parent,
                    "Translation Not Available",
                    "Translation layer is not initialized.\n\n"
                    "Please check that translation engines are installed."
                )
                return
            
            # Get available engines
            available_engines = pipeline.translation_layer.get_available_engines()
            
            # Check if specific engine is available
            engine_status = "✓ Available" if engine_name in available_engines else "✗ Not Available"
            
            # Get engine info
            engine_display_names = {
                'marianmt': 'MarianMT (Offline AI)',
                'google_free': 'Google Translate Free',
                'libretranslate': 'LibreTranslate (Free AI)',
                'google': 'Google Translate API',
                'deepl': 'DeepL',
                'azure': 'Azure Translator'
            }
            
            display_name = engine_display_names.get(engine_name, engine_name.upper())
            
            # Perform a simple test translation
            test_text = "Hello, world!"
            test_result = "Translation test not performed"
            
            if engine_name in available_engines:
                try:
                    # Try a simple translation
                    from app.interfaces import TranslationEngine
                    engine_enum = TranslationEngine(engine_name)
                    translated = pipeline.translation_layer.translate(
                        test_text,
                        engine_enum,
                        'en',
                        'es',
                        {'use_cache': False}
                    )
                    test_result = f"✓ Test successful: '{test_text}' → '{translated}'"
                except Exception as e:
                    test_result = f"✗ Test failed: {str(e)}"
            
            result_msg = f"""⚡ Quick Translation Test

Engine: {display_name}
Status: {engine_status}

Available Engines: {len(available_engines)}
  ({', '.join(available_engines)})

Test Translation (EN → ES):
{test_result}

System Status:
✓ Translation Layer: Initialized
✓ Pipeline: Ready

Note: For full testing with custom text, use the 'Test Engine' button.
"""
            
            QMessageBox.information(
                self.parent,
                f"Quick Test - {display_name}",
                result_msg
            )
                
        except Exception as e:
            QMessageBox.critical(
                self.parent,
                "Test Failed",
                f"Failed to run quick test:\n\n{str(e)}"
            )


class TranslationTestDialog(QDialog):
    """Dialog for testing translation engines with custom text."""
    
    def __init__(self, parent=None, pipeline=None, engine_name=None):
        """Initialize the translation test dialog."""
        super().__init__(parent)
        self.pipeline = pipeline
        self.engine_name = engine_name
        
        engine_display_names = {
            'marianmt': 'MarianMT',
            'google_free': 'Google Translate Free',
            'libretranslate': 'LibreTranslate',
            'google': 'Google Translate API',
            'deepl': 'DeepL',
            'azure': 'Azure Translator'
        }
        
        display_name = engine_display_names.get(engine_name, engine_name)
        self.setWindowTitle(f"Translation Test - {display_name}")
        self.setMinimumSize(700, 600)
        
        self._init_ui()
    
    def _init_ui(self):
        """Initialize the user interface."""
        layout = QVBoxLayout(self)
        
        # Title
        title = QLabel(f"🌐 Translation Engine Test")
        title.setStyleSheet("font-size: 14pt; font-weight: bold;")
        layout.addWidget(title)
        
        # Instructions
        instructions = QLabel(
            "Enter text to translate and select source/target languages.\n"
            "Test the translation engine with your own text."
        )
        instructions.setStyleSheet("color: #666666; margin-bottom: 10px;")
        layout.addWidget(instructions)
        
        # Language selection
        lang_layout = QHBoxLayout()
        
        lang_layout.addWidget(QLabel("Source Language:"))
        self.source_lang_combo = QComboBox()
        self.source_lang_combo.addItems(['English (en)', 'Spanish (es)', 'French (fr)', 'German (de)', 
                                         'Japanese (ja)', 'Chinese (zh)', 'Korean (ko)', 'Russian (ru)'])
        lang_layout.addWidget(self.source_lang_combo)
        
        lang_layout.addWidget(QLabel("Target Language:"))
        self.target_lang_combo = QComboBox()
        self.target_lang_combo.addItems(['Spanish (es)', 'English (en)', 'French (fr)', 'German (de)', 
                                         'Japanese (ja)', 'Chinese (zh)', 'Korean (ko)', 'Russian (ru)'])
        lang_layout.addWidget(self.target_lang_combo)
        
        layout.addLayout(lang_layout)
        
        # Input text
        input_label = QLabel("Input Text:")
        input_label.setStyleSheet("font-weight: bold; margin-top: 10px;")
        layout.addWidget(input_label)
        
        self.input_text = QTextEdit()
        self.input_text.setPlaceholderText("Enter text to translate...")
        self.input_text.setMaximumHeight(150)
        self.input_text.setText("Hello, how are you today?")
        layout.addWidget(self.input_text)
        
        # Translate button
        translate_btn = QPushButton("▶️ Translate")
        translate_btn.setProperty("class", "action")
        translate_btn.clicked.connect(self._run_translation)
        layout.addWidget(translate_btn)
        
        # Output text
        output_label = QLabel("Translation Result:")
        output_label.setStyleSheet("font-weight: bold; margin-top: 10px;")
        layout.addWidget(output_label)
        
        self.output_text = QTextEdit()
        self.output_text.setReadOnly(True)
        self.output_text.setPlaceholderText("Translation will appear here...")
        layout.addWidget(self.output_text)
        
        # Close button
        close_btn = QPushButton("Close")
        close_btn.clicked.connect(self.close)
        layout.addWidget(close_btn, alignment=Qt.AlignmentFlag.AlignRight)
    
    def _run_translation(self):
        """Run translation test."""
        try:
            # Get input text
            text = self.input_text.toPlainText().strip()
            if not text:
                QMessageBox.warning(self, "No Input", "Please enter text to translate.")
                return
            
            # Get language codes
            src_lang = self.source_lang_combo.currentText().split('(')[1].split(')')[0]
            tgt_lang = self.target_lang_combo.currentText().split('(')[1].split(')')[0]
            
            # Show processing message
            self.output_text.setPlainText("Translating...\n\nPlease wait...")
            
            # Perform translation
            from app.interfaces import TranslationEngine
            engine_enum = TranslationEngine(self.engine_name)
            
            import time
            start_time = time.time()
            
            translated = self.pipeline.translation_layer.translate(
                text,
                engine_enum,
                src_lang,
                tgt_lang,
                {'use_cache': False}
            )
            
            processing_time = (time.time() - start_time) * 1000
            
            # Display result
            result_text = f"""Translation Result:
{'=' * 50}

Original Text ({src_lang}):
{text}

Translated Text ({tgt_lang}):
{translated}

Engine: {self.engine_name.upper()}
Processing Time: {processing_time:.2f} ms
Status: ✓ Success

Note: This translation was performed using the {self.engine_name} engine.
"""
            
            self.output_text.setPlainText(result_text)
            
        except Exception as e:
            error_text = f"""Translation Failed:
{'=' * 50}

Error: {str(e)}

This could be due to:
• Engine not properly initialized
• Language pair not supported
• Network connection issues (for cloud services)
• Missing dependencies

Please check the console for more details.
"""
            self.output_text.setPlainText(error_text)
            QMessageBox.critical(
                self,
                "Translation Failed",
                f"Failed to translate text:\n\n{str(e)}"
            )
