"""
Quick OCR Switch Dialog Module

Dialog for quickly switching between OCR engines without navigating
through settings tabs.
"""

import logging

from PyQt6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QRadioButton, QButtonGroup, QMessageBox
)
from app.localization import tr

logger = logging.getLogger(__name__)


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
        
        self.setWindowTitle(tr("quick_switch_ocr_engine"))
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
        header = QLabel(tr("_quick_switch_ocr_engine"))
        header.setStyleSheet("font-size: 14pt; font-weight: bold;")
        layout.addWidget(header)
        
        # Description
        desc = QLabel(tr("select_an_ocr_engine_to_switch_to_immediately_all_available_"))
        desc.setWordWrap(True)
        desc.setStyleSheet("color: #666666; font-size: 9pt; margin-bottom: 10px;")
        layout.addWidget(desc)
        
        # Get all available engines from pipeline or use defaults
        available_engines = self._get_available_engines()
        
        # Get current engine
        current_engine = self._get_current_engine()
        
        if not available_engines:
            no_engines_label = QLabel(tr("_no_ocr_engines_are_available"))
            no_engines_label.setStyleSheet("color: #F44336; font-size: 10pt; padding: 10px;")
            layout.addWidget(no_engines_label)
            
            close_btn = QPushButton(tr("close"))
            close_btn.clicked.connect(self.reject)
            layout.addWidget(close_btn)
            return
        
        # Create radio buttons for each engine
        button_group = QButtonGroup()
        
        engine_info = {
            'easyocr': (tr("ocr_switch_easyocr_label"), tr("ocr_switch_easyocr_desc")),
            'tesseract': (tr("ocr_switch_tesseract_label"), tr("ocr_switch_tesseract_desc")),
            'paddleocr': (tr("ocr_switch_paddleocr_label"), tr("ocr_switch_paddleocr_desc")),
            'hybrid_ocr': (tr("ocr_switch_hybrid_ocr_label"), tr("ocr_switch_hybrid_ocr_desc")),
            'judge_ocr': (tr("ocr_switch_judge_ocr_label"), tr("ocr_switch_judge_ocr_desc")),
        }
        
        for engine in available_engines:
            engine_lower = engine.lower()
            display_name, description = engine_info.get(engine_lower, (engine, tr("ocr_switch_default_desc")))
            
            radio = QRadioButton(display_name)
            radio.setStyleSheet("font-size: 10pt; font-weight: 500;")
            
            if engine_lower == current_engine.lower():
                radio.setChecked(True)
                radio.setText(f'{display_name} ({tr("ocr_switch_current")})')
            
            button_group.addButton(radio)
            self.engine_radios[engine] = radio
            layout.addWidget(radio)
            
            # Add description
            desc_label = QLabel(f"  • {description}")
            desc_label.setStyleSheet("color: #666666; font-size: 8pt; margin-left: 20px; margin-bottom: 5px;")
            layout.addWidget(desc_label)
        
        # Buttons
        button_layout = QHBoxLayout()
        button_layout.addStretch()
        
        cancel_btn = QPushButton(tr("cancel"))
        cancel_btn.clicked.connect(self.reject)
        button_layout.addWidget(cancel_btn)
        
        switch_btn = QPushButton(tr("switch_engine"))
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
                logger.warning("Could not get engines from pipeline: %s", e)

        # Fallback: dependency-aware discovery so we don't offer engines
        # that are present on disk but not installable on this PC.
        try:
            from app.ocr.ocr_plugin_manager import OCRPluginManager
            manager = OCRPluginManager(config_manager=self.config_manager)
            discovered = manager.discover_plugins()
            return [plugin.name for plugin in discovered]
        except Exception as e:
            logger.warning("Could not discover installable OCR engines: %s", e)

        return []
    
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
            QMessageBox.warning(self, tr("no_selection"), tr("please_select_an_ocr_engine"))
            return
        
        # Get current engine
        current_engine = self._get_current_engine()
        
        # Check if it's the current engine
        if selected_engine.lower() == current_engine.lower():
            QMessageBox.information(
                self,
                tr("already_active"),
                tr("ocr_switch_already_active_msg", engine=selected_engine)
            )
            self.accept()
            return
        
        # Store selected engine
        self.selected_engine = selected_engine
        
        # Constrain languages based on the new engine's supported_languages metadata
        self._apply_engine_language_constraints(selected_engine)
        
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
            
            from ui.settings.language_engine_validator import get_ocr_supported_languages, LANG_CODE_TO_NAME
            supported = get_ocr_supported_languages(selected_engine)
            message = tr("ocr_switch_engine_switched_to", engine=selected_engine) + "\n\n"
            if supported is not None and len(supported) == 1:
                lang_name = LANG_CODE_TO_NAME.get(supported[0], supported[0])
                tgt = 'English' if supported[0] != 'en' else 'German'
                message += tr("ocr_switch_languages_auto_set", source=lang_name, target=tgt) + "\n"
            message += tr("ocr_switch_change_effective")
            
            if success:
                QMessageBox.information(
                    self.parent_window if self.parent_window else self,
                    tr("engine_switched"),
                    message
                )
            else:
                QMessageBox.critical(
                    self.parent_window if self.parent_window else self,
                    tr("switch_failed"),
                    tr("ocr_switch_failed_msg", engine=selected_engine)
                )
        else:
            from ui.settings.language_engine_validator import get_ocr_supported_languages, LANG_CODE_TO_NAME
            supported_fallback = get_ocr_supported_languages(selected_engine)
            message = tr("ocr_switch_engine_set_to", engine=selected_engine) + "\n\n"
            if supported_fallback is not None and len(supported_fallback) == 1:
                lang_nm = LANG_CODE_TO_NAME.get(supported_fallback[0], supported_fallback[0])
                tgt_fb = 'English' if supported_fallback[0] != 'en' else 'German'
                message += tr("ocr_switch_languages_auto_set", source=lang_nm, target=tgt_fb) + "\n\n"
            message += tr("ocr_switch_engine_loaded_on_start")
            
            QMessageBox.information(
                self.parent_window if self.parent_window else self,
                tr("engine_selected"),
                message
            )
        
        # Update sidebar display if parent has the method
        if self.parent_window and hasattr(self.parent_window, 'update_sidebar_ocr_display'):
            self.parent_window.update_sidebar_ocr_display()
    
    def _apply_engine_language_constraints(self, engine_name: str):
        """Apply language constraints based on the engine's supported_languages metadata."""
        try:
            from ui.settings.language_engine_validator import (
                get_ocr_supported_languages, LANG_CODE_TO_NAME,
            )

            supported = get_ocr_supported_languages(engine_name)
            ui_mgr = getattr(self.parent_window, 'ui_manager', None) if self.parent_window else None
            sidebar = ui_mgr.get_sidebar() if ui_mgr else None
            general_tab = ui_mgr.get_tab('general') if ui_mgr else None

            if supported is not None and len(supported) == 1:
                lang_code = supported[0]
                lang_name = LANG_CODE_TO_NAME.get(lang_code, lang_code.upper())

                self.config_manager.set_setting('translation.source_language', lang_code)

                if sidebar:
                    sidebar.set_source_language(lang_name)
                    sidebar.set_language_lock(True)

                if general_tab:
                    idx = general_tab.source_lang_combo.findText(lang_name)
                    if idx >= 0:
                        general_tab.source_lang_combo.blockSignals(True)
                        general_tab.source_lang_combo.setCurrentIndex(idx)
                        general_tab.source_lang_combo.blockSignals(False)

                    general_tab.set_language_lock(True)

                logger.info("Auto-set and locked source language: %s for %s",
                            lang_name, engine_name)
            else:
                if sidebar:
                    sidebar.set_language_lock(False)
                if general_tab:
                    general_tab.set_language_lock(False)
                logger.info("Unlocked language selection for %s", engine_name)

        except Exception as exc:
            logger.warning("Failed to apply language constraints: %s", exc)

    def _auto_set_manga_languages(self):
        """Backward-compatible alias."""
        self._apply_engine_language_constraints('mokuro')

    def _unlock_languages(self):
        """Backward-compatible alias."""
        self._apply_engine_language_constraints('easyocr')
    
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
