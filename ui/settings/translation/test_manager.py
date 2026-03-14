"""
Translation Test Manager
Handles translation testing functionality for all translation engines.
"""

from PyQt6.QtWidgets import QMessageBox, QDialog, QVBoxLayout, QHBoxLayout, QLabel, QPushButton, QTextEdit, QComboBox
from PyQt6.QtCore import Qt
from app.localization import tr

# Shared engine display name mapping
ENGINE_DISPLAY_NAMES = {
    'marianmt': 'MarianMT',
    'google_free': 'Google Translate Free',
    'libretranslate': 'LibreTranslate',
    'google_api': 'Google Translate API',
    'deepl': 'DeepL',
    'azure': 'Azure Translator',
}


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
                    tr("trans_test_pipeline_not_ready_title"),
                    tr("trans_test_pipeline_not_ready_msg")
                )
                return
            
            # Check if translation layer exists
            if not hasattr(pipeline, 'translation_layer') or not pipeline.translation_layer:
                QMessageBox.warning(
                    self.parent,
                    tr("trans_test_not_available_title"),
                    tr("trans_test_not_available_msg")
                )
                return
            
            # Create test dialog
            dialog = TranslationTestDialog(self.parent, pipeline, engine_name)
            dialog.exec()
                
        except Exception as e:
            QMessageBox.critical(
                self.parent,
                tr("trans_test_failed_title"),
                f"{tr('trans_test_failed_msg')}\n\n{str(e)}"
            )


class TranslationTestDialog(QDialog):
    """Dialog for testing translation engines with custom text."""
    
    def __init__(self, parent=None, pipeline=None, engine_name=None):
        """Initialize the translation test dialog."""
        super().__init__(parent)
        self.pipeline = pipeline
        self.engine_name = engine_name
        
        display_name = ENGINE_DISPLAY_NAMES.get(engine_name, engine_name)
        self.setWindowTitle(f"{tr('trans_test_window_title')} - {display_name}")
        self.setMinimumSize(700, 600)
        
        self._init_ui()
    
    def _init_ui(self):
        """Initialize the user interface."""
        layout = QVBoxLayout(self)
        
        # Title
        title = QLabel(tr("trans_test_title"))
        title.setStyleSheet("font-size: 14pt; font-weight: bold;")
        layout.addWidget(title)
        
        # Instructions
        instructions = QLabel(tr("trans_test_instructions"))
        instructions.setStyleSheet("color: #666666; margin-bottom: 10px;")
        layout.addWidget(instructions)
        
        # Language selection
        lang_layout = QHBoxLayout()
        
        lang_layout.addWidget(QLabel(tr("trans_test_source_language")))
        self.source_lang_combo = QComboBox()
        self.source_lang_combo.addItems(['English (en)', 'Spanish (es)', 'French (fr)', 'German (de)', 
                                         'Japanese (ja)', 'Chinese (zh)', 'Korean (ko)', 'Russian (ru)'])
        lang_layout.addWidget(self.source_lang_combo)
        
        lang_layout.addWidget(QLabel(tr("trans_test_target_language")))
        self.target_lang_combo = QComboBox()
        self.target_lang_combo.addItems(['Spanish (es)', 'English (en)', 'French (fr)', 'German (de)', 
                                         'Japanese (ja)', 'Chinese (zh)', 'Korean (ko)', 'Russian (ru)'])
        lang_layout.addWidget(self.target_lang_combo)
        
        layout.addLayout(lang_layout)
        
        # Input text
        input_label = QLabel(tr("trans_test_input_label"))
        input_label.setStyleSheet("font-weight: bold; margin-top: 10px;")
        layout.addWidget(input_label)
        
        self.input_text = QTextEdit()
        self.input_text.setPlaceholderText(tr("trans_test_input_placeholder"))
        self.input_text.setMaximumHeight(150)
        self.input_text.setText("Hello, how are you today?")
        layout.addWidget(self.input_text)
        
        # Translate button
        translate_btn = QPushButton(tr("trans_test_translate_btn"))
        translate_btn.setProperty("class", "action")
        translate_btn.clicked.connect(self._run_translation)
        layout.addWidget(translate_btn)
        
        # Output text
        output_label = QLabel(tr("trans_test_result_label"))
        output_label.setStyleSheet("font-weight: bold; margin-top: 10px;")
        layout.addWidget(output_label)
        
        self.output_text = QTextEdit()
        self.output_text.setReadOnly(True)
        self.output_text.setPlaceholderText(tr("trans_test_result_placeholder"))
        layout.addWidget(self.output_text)
        
        # Close button
        close_btn = QPushButton(tr("trans_test_close_btn"))
        close_btn.clicked.connect(self.close)
        layout.addWidget(close_btn, alignment=Qt.AlignmentFlag.AlignRight)
    
    def _run_translation(self):
        """Run translation test."""
        try:
            # Get input text
            text = self.input_text.toPlainText().strip()
            if not text:
                QMessageBox.warning(self, tr("trans_test_no_input_title"), tr("trans_test_no_input_msg"))
                return
            
            # Get language codes
            src_lang = self.source_lang_combo.currentText().split('(')[1].split(')')[0]
            tgt_lang = self.target_lang_combo.currentText().split('(')[1].split(')')[0]
            
            self.output_text.setPlainText(tr("trans_test_translating_msg"))
            
            # Perform translation
            import time
            start_time = time.time()
            translated = self.pipeline.translation_layer.translate(
                text,
                self.engine_name,
                src_lang,
                tgt_lang,
                {'use_cache': False}
            )
            
            processing_time = (time.time() - start_time) * 1000
            
            result_text = (
                f"{tr('trans_test_result_header')}:\n"
                f"{'=' * 50}\n\n"
                f"{tr('trans_test_original_text')} ({src_lang}):\n"
                f"{text}\n\n"
                f"{tr('trans_test_translated_text')} ({tgt_lang}):\n"
                f"{translated}\n\n"
                f"{tr('trans_test_engine_label')}: {self.engine_name.upper()}\n"
                f"{tr('trans_test_processing_time')}: {processing_time:.2f} ms\n"
                f"{tr('trans_test_status_label')}: ✓ {tr('trans_test_status_success')}\n\n"
                f"{tr('trans_test_engine_note').format(engine=self.engine_name)}\n"
            )
            
            self.output_text.setPlainText(result_text)
            
        except Exception as e:
            error_text = (
                f"{tr('trans_test_error_header')}:\n"
                f"{'=' * 50}\n\n"
                f"{tr('trans_test_error_prefix')}: {str(e)}\n\n"
                f"{tr('trans_test_error_causes')}\n"
            )
            self.output_text.setPlainText(error_text)
            QMessageBox.critical(
                self,
                tr("trans_test_translation_failed_title"),
                f"{tr('trans_test_translation_failed_msg')}\n\n{str(e)}"
            )
