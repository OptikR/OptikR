"""
Quick OCR Switch Dialog Module

Dialog for quickly switching between OCR engines without navigating
through settings tabs.

Author: Real-Time Translation System
Date: 2024
"""

from PyQt6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QRadioButton, QButtonGroup, QMessageBox
)


class QuickOCRSwitchDialog(QDialog):
    """
    Quick OCR engine switch dialog.
    
    Allows users to quickly switch between available OCR engines
    with descriptions and current engine indication.
    """
    
    def __init__(self, config_manager, ocr_tab=None, pipeline=None, parent=None):
        """
        Initialize quick OCR switch dialog.
        
        Args:
            config_manager: Configuration manager instance
            ocr_tab: OCR settings tab (optional, for language pack info)
            pipeline: Pipeline instance (optional, for live switching)
            parent: Parent widget (optional)
        """
        super().__init__(parent)
        self.config_manager = config_manager
        self.ocr_tab = ocr_tab
        self.pipeline = pipeline
        self.parent_window = parent
        
        self.setWindowTitle("Quick Switch OCR Engine")
        self.setMinimumWidth(400)
        
        self.engine_radios = {}
        self.selected_engine = None
        
        self.init_ui()
    
    def init_ui(self):
        """Initialize the dialog UI."""
        layout = QVBoxLayout(self)
        layout.setSpacing(15)
        layout.setContentsMargins(20, 20, 20, 20)
        
        # Header
        header = QLabel("⚡ Quick Switch OCR Engine")
        header.setStyleSheet("font-size: 14pt; font-weight: bold;")
        layout.addWidget(header)
        
        # Description
        desc = QLabel(
            "Select an OCR engine to switch to immediately. "
            "All available engines are shown below."
        )
        desc.setWordWrap(True)
        desc.setStyleSheet("color: #666666; font-size: 9pt; margin-bottom: 10px;")
        layout.addWidget(desc)
        
        # Get all available engines from pipeline or use defaults
        available_engines = self._get_available_engines()
        
        # Get current engine
        current_engine = self._get_current_engine()
        
        if not available_engines:
            no_engines_label = QLabel("❌ No OCR engines are available.")
            no_engines_label.setStyleSheet("color: #F44336; font-size: 10pt; padding: 10px;")
            layout.addWidget(no_engines_label)
            
            close_btn = QPushButton("Close")
            close_btn.clicked.connect(self.reject)
            layout.addWidget(close_btn)
            return
        
        # Create radio buttons for each engine
        button_group = QButtonGroup()
        
        engine_info = {
            'easyocr': ('🔍 EasyOCR', 'Multi-language support with deep learning'),
            'tesseract': ('📝 Tesseract OCR', 'Fast and lightweight, good for printed text'),
            'paddleocr': ('🎯 PaddleOCR', 'High accuracy Chinese/multilingual OCR'),
            'onnx': ('⚙️ ONNX Runtime', 'Optimized cross-platform inference'),
            'manga_ocr': ('📚 Manga OCR', 'Specialized for Japanese manga and comics')
        }
        
        for engine in available_engines:
            engine_lower = engine.lower()
            display_name, description = engine_info.get(engine_lower, (engine, 'OCR engine'))
            
            radio = QRadioButton(display_name)
            radio.setStyleSheet("font-size: 10pt; font-weight: 500;")
            
            if engine_lower == current_engine.lower():
                radio.setChecked(True)
                radio.setText(f"{display_name} (Current)")
            
            button_group.addButton(radio)
            self.engine_radios[engine] = radio
            layout.addWidget(radio)
            
            # Add description
            desc_label = QLabel(f"  • {description}")
            desc_label.setStyleSheet("color: #666666; font-size: 8pt; margin-left: 20px; margin-bottom: 5px;")
            layout.addWidget(desc_label)
        
        # Get installed language packs for current engine
        if self.ocr_tab and hasattr(self.ocr_tab, 'language_list') and self.ocr_tab.language_list:
            lang_count = self.ocr_tab.language_list.count()
            lang_info = QLabel(f"📦 {lang_count} language pack(s) installed")
            lang_info.setStyleSheet("color: #666666; font-size: 9pt; margin-top: 10px; padding: 8px; "
                                   "background-color: #F0F8FF; border-radius: 3px;")
            layout.addWidget(lang_info)
        
        # Buttons
        button_layout = QHBoxLayout()
        button_layout.addStretch()
        
        cancel_btn = QPushButton("Cancel")
        cancel_btn.clicked.connect(self.reject)
        button_layout.addWidget(cancel_btn)
        
        switch_btn = QPushButton("Switch Engine")
        switch_btn.setProperty("class", "action")
        switch_btn.setDefault(True)
        switch_btn.clicked.connect(self._do_switch)
        button_layout.addWidget(switch_btn)
        
        layout.addLayout(button_layout)
    
    def _get_available_engines(self):
        """Get list of available OCR engines."""
        # Try to get from pipeline first (most accurate)
        if self.pipeline and hasattr(self.pipeline, 'get_available_ocr_engines'):
            try:
                engines = self.pipeline.get_available_ocr_engines()
                if engines:
                    return engines
            except Exception as e:
                print(f"[Quick OCR Switch] Could not get engines from pipeline: {e}")
        
        # Fallback to hardcoded list
        return ['easyocr', 'tesseract', 'paddleocr', 'onnx', 'manga_ocr']
    
    def _get_current_engine(self):
        """Get currently selected OCR engine."""
        if self.ocr_tab and hasattr(self.ocr_tab, 'get_selected_engine'):
            return self.ocr_tab.get_selected_engine()
        else:
            return self.config_manager.get_setting('ocr.engine', 'easyocr')
    
    def _do_switch(self):
        """Perform the OCR engine switch."""
        # Find selected engine
        selected_engine = None
        for engine, radio in self.engine_radios.items():
            if radio.isChecked():
                selected_engine = engine
                break
        
        if not selected_engine:
            QMessageBox.warning(self, "No Selection", "Please select an OCR engine.")
            return
        
        # Get current engine
        current_engine = self._get_current_engine()
        
        # Check if it's the current engine
        if selected_engine.lower() == current_engine.lower():
            QMessageBox.information(
                self,
                "Already Active",
                f"{selected_engine} is already the active OCR engine."
            )
            self.accept()
            return
        
        # Store selected engine
        self.selected_engine = selected_engine
        
        # Auto-set languages for Manga OCR (Japanese → English)
        if selected_engine.lower() == 'manga_ocr':
            self._auto_set_manga_languages()
        else:
            # Unlock languages when switching away from Manga OCR
            self._unlock_languages()
        
        # Close dialog
        self.accept()
        
        # Update OCR tab selection first
        if self.ocr_tab and hasattr(self.ocr_tab, 'update_current_engine_display'):
            self.ocr_tab.update_current_engine_display(selected_engine)
        
        # Save to config
        self.config_manager.set_setting('ocr.engine', selected_engine)
        self.config_manager.save_config()
        
        # Perform the pipeline switch if pipeline exists
        if self.pipeline and hasattr(self.pipeline, 'set_ocr_engine'):
            success = self.pipeline.set_ocr_engine(selected_engine)
            
            # Build message
            message = f"OCR engine switched to {selected_engine}.\n\n"
            if selected_engine.lower() == 'manga_ocr':
                message += "✓ Languages auto-set: Japanese → English\n"
            message += "✓ Change is effective immediately!"
            
            if success:
                QMessageBox.information(
                    self.parent_window if self.parent_window else self,
                    "Engine Switched",
                    message
                )
            else:
                QMessageBox.critical(
                    self.parent_window if self.parent_window else self,
                    "Switch Failed",
                    f"Failed to switch to {selected_engine}.\n\n"
                    "The engine may not be available or failed to load."
                )
        else:
            # Build message
            message = f"OCR engine set to {selected_engine}.\n\n"
            if selected_engine.lower() == 'manga_ocr':
                message += "✓ Languages auto-set: Japanese → English\n\n"
            message += "The engine will be loaded when you start translation."
            
            QMessageBox.information(
                self.parent_window if self.parent_window else self,
                "Engine Selected",
                message
            )
        
        # Update sidebar display if parent has the method
        if self.parent_window and hasattr(self.parent_window, 'update_sidebar_ocr_display'):
            self.parent_window.update_sidebar_ocr_display()
    
    def _auto_set_manga_languages(self):
        """Automatically set languages to Japanese → English for Manga OCR."""
        try:
            # Set source language to Japanese
            self.config_manager.set_setting('translation.source_language', 'ja')
            
            # Set target language to English
            self.config_manager.set_setting('translation.target_language', 'en')
            
            # Update sidebar if parent window has sidebar
            if self.parent_window and hasattr(self.parent_window, 'sidebar'):
                sidebar = self.parent_window.sidebar
                sidebar.set_source_language('Japanese')
                sidebar.set_target_language('English')
                # Lock language selection
                sidebar.set_language_lock(True)
            
            # Update General Tab if it exists
            if self.parent_window and hasattr(self.parent_window, 'general_tab'):
                general_tab = self.parent_window.general_tab
                if general_tab:
                    # Find and set Japanese
                    ja_index = general_tab.source_lang_combo.findText('Japanese')
                    if ja_index >= 0:
                        general_tab.source_lang_combo.blockSignals(True)
                        general_tab.source_lang_combo.setCurrentIndex(ja_index)
                        general_tab.source_lang_combo.blockSignals(False)
                    
                    # Find and set English
                    en_index = general_tab.target_lang_combo.findText('English')
                    if en_index >= 0:
                        general_tab.target_lang_combo.blockSignals(True)
                        general_tab.target_lang_combo.setCurrentIndex(en_index)
                        general_tab.target_lang_combo.blockSignals(False)
                    
                    # Lock language selection
                    general_tab.set_language_lock(True)
            
            print("[Quick OCR Switch] Auto-set and locked languages: Japanese → English for Manga OCR")
            
        except Exception as e:
            print(f"[Quick OCR Switch] Failed to auto-set languages: {e}")
    
    def _unlock_languages(self):
        """Unlock language selection when switching away from Manga OCR."""
        try:
            # Unlock sidebar if parent window has sidebar
            if self.parent_window and hasattr(self.parent_window, 'sidebar'):
                self.parent_window.sidebar.set_language_lock(False)
            
            # Unlock General Tab if it exists
            if self.parent_window and hasattr(self.parent_window, 'general_tab'):
                general_tab = self.parent_window.general_tab
                if general_tab:
                    general_tab.set_language_lock(False)
            
            print("[Quick OCR Switch] Unlocked language selection")
            
        except Exception as e:
            print(f"[Quick OCR Switch] Failed to unlock languages: {e}")
    
    def get_selected_engine(self):
        """Get the selected engine (after dialog closes)."""
        return self.selected_engine


def show_quick_ocr_switch_dialog(config_manager, ocr_tab=None, pipeline=None, parent=None):
    """
    Show quick OCR switch dialog.
    
    Args:
        config_manager: Configuration manager instance
        ocr_tab: OCR settings tab (optional)
        pipeline: Pipeline instance (optional)
        parent: Parent widget (optional)
        
    Returns:
        Selected engine name or None if cancelled
    """
    dialog = QuickOCRSwitchDialog(config_manager, ocr_tab, pipeline, parent)
    result = dialog.exec()
    
    if result == QDialog.DialogCode.Accepted:
        return dialog.get_selected_engine()
    return None
