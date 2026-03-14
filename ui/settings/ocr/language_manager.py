"""
OCR Language Manager
Handles language pack management including add, remove, and download operations.
"""

from PyQt6.QtWidgets import (
    QMessageBox, QInputDialog, QListWidget, QListWidgetItem,
    QDialog, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QTableWidget, QTableWidgetItem, QHeaderView, QCheckBox, QWidget
)
from PyQt6.QtCore import Qt
from app.localization import tr


class OCRLanguageManager:
    """Manages OCR language packs."""
    
    def __init__(self, parent=None):
        """Initialize the language manager."""
        self.parent = parent
    
    def add_language(self, language_list: QListWidget):
        """
        Add a new language pack.
        
        Args:
            language_list: QListWidget containing current languages
        """
        try:
            # Get currently installed languages
            installed_langs = set()
            for i in range(language_list.count()):
                item_text = language_list.item(i).text()
                if '(' in item_text and ')' in item_text:
                    lang_code = item_text.split('(')[1].split(')')[0]
                    installed_langs.add(lang_code)
            
            # All available languages
            all_languages = [
                ("Arabic", "ar"), ("Bengali", "bn"), ("Bulgarian", "bg"), ("Czech", "cs"),
                ("Danish", "da"), ("Dutch", "nl"), ("Finnish", "fi"), ("Greek", "el"),
                ("Hebrew", "he"), ("Hindi", "hi"), ("Hungarian", "hu"), ("Indonesian", "id"),
                ("Italian", "it"), ("Norwegian", "no"), ("Polish", "pl"), ("Portuguese", "pt"),
                ("Romanian", "ro"), ("Russian", "ru"), ("Swedish", "sv"), ("Thai", "th"),
                ("Turkish", "tr"), ("Ukrainian", "uk"), ("Vietnamese", "vi"),
                ("Chinese Traditional", "zh-TW"), ("Malay", "ms"), ("Tamil", "ta"),
                ("Telugu", "te"), ("Kannada", "kn"), ("Persian", "fa")
            ]
            
            # Filter out already installed languages
            available_languages = [
                f"{name} ({code})" for name, code in all_languages 
                if code not in installed_langs
            ]
            
            if not available_languages:
                QMessageBox.information(
                    self.parent,
                    tr("lang_mgr_all_installed_title"),
                    tr("lang_mgr_all_installed_msg")
                )
                return
            
            language, ok = QInputDialog.getItem(
                self.parent,
                tr("lang_mgr_add_title"),
                tr("lang_mgr_add_prompt"),
                available_languages,
                0,
                False
            )
            
            if ok and language:
                # Add language to list
                item = QListWidgetItem(language)
                language_list.addItem(item)
                
                QMessageBox.information(
                    self.parent,
                    tr("lang_mgr_added_title"),
                    tr("lang_mgr_added_msg").format(language=language)
                )
                
        except Exception as e:
            QMessageBox.critical(
                self.parent,
                tr("lang_mgr_error_title"),
                tr("lang_mgr_add_error").format(error=str(e))
            )
    
    def remove_language(self, language_list: QListWidget):
        """
        Remove selected language pack.
        
        Args:
            language_list: QListWidget containing current languages
        """
        current_item = language_list.currentItem()
        
        if not current_item:
            QMessageBox.warning(
                self.parent,
                tr("lang_mgr_no_selection_title"),
                tr("lang_mgr_select_to_remove")
            )
            return
        
        language = current_item.text()
        
        # Confirm removal
        reply = QMessageBox.question(
            self.parent,
            tr("lang_mgr_remove_title"),
            tr("lang_mgr_confirm_remove").format(language=language),
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            QMessageBox.StandardButton.No
        )
        
        if reply == QMessageBox.StandardButton.Yes:
            row = language_list.row(current_item)
            language_list.takeItem(row)
    
    def show_selective_download_dialog(self):
        """Show dialog to select specific languages for specific OCR engines."""
        
        dialog = QDialog(self.parent)
        dialog.setWindowTitle(tr("download_language_packs"))
        dialog.setMinimumWidth(800)
        dialog.setMinimumHeight(600)
        
        layout = QVBoxLayout(dialog)
        layout.setSpacing(15)
        layout.setContentsMargins(20, 20, 20, 20)
        
        # Header
        header = QLabel(tr("lang_mgr_select_download_header"))
        header.setStyleSheet("font-size: 14pt; font-weight: bold;")
        layout.addWidget(header)
        
        # Description
        desc = QLabel(tr("lang_mgr_select_download_desc"))
        desc.setWordWrap(True)
        desc.setStyleSheet("color: #666666; font-size: 9pt; margin-bottom: 10px;")
        layout.addWidget(desc)
        
        # Create table for language selection
        table = QTableWidget()
        table.setColumnCount(6)
        table.setHorizontalHeaderLabels([
            tr("lang_mgr_col_language"), tr("lang_mgr_col_easyocr"),
            tr("lang_mgr_col_tesseract"), tr("lang_mgr_col_paddleocr"),
            tr("lang_mgr_col_manga"), tr("lang_mgr_col_size")
        ])
        table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Stretch)
        table.setSelectionMode(QTableWidget.SelectionMode.NoSelection)
        table.setAlternatingRowColors(True)
        
        # Define available languages with engine support
        languages_data = [
            ("English", "en", True, True, True, False, "45 MB"),
            ("Chinese Simplified", "zh-CN", True, True, True, False, "52 MB"),
            ("Chinese Traditional", "zh-TW", True, True, True, False, "52 MB"),
            ("Japanese", "ja", True, True, True, True, "156 MB"),
            ("Korean", "ko", True, True, True, False, "48 MB"),
            ("Spanish", "es", True, True, True, False, "45 MB"),
            ("French", "fr", True, True, True, False, "45 MB"),
            ("German", "de", True, True, True, False, "45 MB"),
            ("Italian", "it", True, True, True, False, "45 MB"),
            ("Portuguese", "pt", True, True, True, False, "45 MB"),
            ("Russian", "ru", True, True, True, False, "52 MB"),
            ("Arabic", "ar", True, True, True, False, "48 MB"),
            ("Hindi", "hi", True, True, True, False, "48 MB"),
            ("Thai", "th", True, True, True, False, "48 MB"),
            ("Vietnamese", "vi", True, True, True, False, "48 MB"),
            ("Turkish", "tr", True, True, False, False, "45 MB"),
            ("Polish", "pl", True, True, False, False, "45 MB"),
            ("Dutch", "nl", True, True, False, False, "45 MB"),
            ("Swedish", "sv", True, True, False, False, "45 MB"),
            ("Indonesian", "id", True, True, False, False, "45 MB"),
        ]
        
        table.setRowCount(len(languages_data))
        checkboxes = []
        
        for row, (lang_name, lang_code, easy, tess, paddle, manga, size) in enumerate(languages_data):
            # Language name
            table.setItem(row, 0, QTableWidgetItem(lang_name))
            
            # Checkboxes for each engine
            row_checkboxes = {}
            for col, (engine, supported) in enumerate([
                ("easyocr", easy), ("tesseract", tess), 
                ("paddleocr", paddle), ("mokuro", manga)
            ], start=1):
                checkbox_widget = QWidget()
                checkbox_layout = QHBoxLayout(checkbox_widget)
                checkbox_layout.setContentsMargins(0, 0, 0, 0)
                checkbox_layout.setAlignment(Qt.AlignmentFlag.AlignCenter)
                
                checkbox = QCheckBox()
                checkbox.setEnabled(supported)
                if not supported:
                    checkbox.setToolTip(tr("lang_mgr_not_supported"))
                checkbox_layout.addWidget(checkbox)
                
                table.setCellWidget(row, col, checkbox_widget)
                row_checkboxes[engine] = checkbox
            
            # Size — column index 5 (last column)
            table.setItem(row, 5, QTableWidgetItem(size))
            
            # Store for later
            checkboxes.append((lang_name, lang_code, row_checkboxes))
        
        layout.addWidget(table)
        
        # Selection helpers
        helper_layout = QHBoxLayout()
        
        select_all_btn = QPushButton(tr("lang_mgr_select_all"))
        select_all_btn.clicked.connect(lambda: self._toggle_all_checkboxes(checkboxes, True))
        helper_layout.addWidget(select_all_btn)
        
        clear_all_btn = QPushButton(tr("lang_mgr_clear_all"))
        clear_all_btn.clicked.connect(lambda: self._toggle_all_checkboxes(checkboxes, False))
        helper_layout.addWidget(clear_all_btn)
        
        helper_layout.addStretch()
        layout.addLayout(helper_layout)
        
        # Info label
        info_label = QLabel(tr("lang_mgr_info_label"))
        info_label.setWordWrap(True)
        info_label.setStyleSheet("color: #2196F3; font-size: 9pt; padding: 10px; "
                                "background-color: #1E3A4F; border-left: 3px solid #4A9EFF; border-radius: 3px;")
        layout.addWidget(info_label)
        
        # Buttons
        button_layout = QHBoxLayout()
        button_layout.addStretch()
        
        cancel_btn = QPushButton(tr("lang_mgr_cancel"))
        cancel_btn.clicked.connect(dialog.reject)
        button_layout.addWidget(cancel_btn)
        
        download_btn = QPushButton(tr("lang_mgr_download_selected"))
        download_btn.setProperty("class", "action")
        download_btn.clicked.connect(lambda: self._start_download(dialog, checkboxes))
        button_layout.addWidget(download_btn)
        
        layout.addLayout(button_layout)
        
        dialog.exec()
    
    def _toggle_all_checkboxes(self, checkboxes, checked: bool):
        """Toggle all checkboxes on or off."""
        for lang_name, lang_code, row_checkboxes in checkboxes:
            for engine, checkbox in row_checkboxes.items():
                if checkbox.isEnabled():
                    checkbox.setChecked(checked)
    
    def _start_download(self, dialog, checkboxes):
        """Configure selected language packs."""
        # Count selected
        selected_langs = []
        tesseract_langs = []
        
        for lang_name, lang_code, row_checkboxes in checkboxes:
            for engine, checkbox in row_checkboxes.items():
                if checkbox.isChecked():
                    selected_langs.append((lang_name, lang_code, engine))
                    if engine == "tesseract":
                        tesseract_langs.append((lang_name, lang_code))
        
        if not selected_langs:
            QMessageBox.warning(
                dialog,
                tr("lang_mgr_no_selection_title"),
                tr("lang_mgr_select_at_least_one")
            )
            return
        
        # Build message
        message_parts = []
        
        # Group by engine
        easyocr_langs = [name for name, code, eng in selected_langs if eng == "easyocr"]
        paddleocr_langs = [name for name, code, eng in selected_langs if eng == "paddleocr"]
        manga_langs = [name for name, code, eng in selected_langs if eng == "mokuro"]
        tess_langs = [name for name, code, eng in selected_langs if eng == "tesseract"]
        
        message_parts.append(f"{tr('lang_mgr_configured_summary').format(count=len(selected_langs))}<br><br>")
        
        if easyocr_langs:
            message_parts.append(f"{tr('lang_mgr_engine_header').format(engine='EasyOCR', count=len(easyocr_langs))}<br>")
            message_parts.append(f"  {', '.join(easyocr_langs)}<br>")
            message_parts.append(f"  <i>{tr('lang_mgr_auto_download_note')}</i><br><br>")
        
        if paddleocr_langs:
            message_parts.append(f"{tr('lang_mgr_engine_header').format(engine='PaddleOCR', count=len(paddleocr_langs))}<br>")
            message_parts.append(f"  {', '.join(paddleocr_langs)}<br>")
            message_parts.append(f"  <i>{tr('lang_mgr_auto_download_note')}</i><br><br>")
        
        if manga_langs:
            message_parts.append(f"{tr('lang_mgr_engine_header').format(engine='Manga OCR', count=len(manga_langs))}<br>")
            message_parts.append(f"  {', '.join(manga_langs)}<br>")
            message_parts.append(f"  <i>{tr('lang_mgr_manga_included_note')}</i><br><br>")
        
        if tess_langs:
            message_parts.append(f"{tr('lang_mgr_engine_header_warn').format(engine='Tesseract OCR', count=len(tess_langs))}<br>")
            message_parts.append(f"  {', '.join(tess_langs)}<br>")
            message_parts.append(f"  <i>{tr('lang_mgr_tesseract_manual_note')}</i><br><br>")
        
        message_parts.append(f"<br>{tr('lang_mgr_next_steps_header')}<br>")
        message_parts.append(f"• {tr('lang_mgr_next_configured')}<br>")
        message_parts.append(f"• {tr('lang_mgr_next_auto_download')}<br>")
        if tess_langs:
            message_parts.append(f"• {tr('lang_mgr_next_tesseract')}<br>")
        
        msg_box = QMessageBox(dialog)
        msg_box.setWindowTitle(tr("language_packs_configured"))
        msg_box.setTextFormat(Qt.TextFormat.RichText)
        msg_box.setText("".join(message_parts))
        msg_box.setIcon(QMessageBox.Icon.Information)
        msg_box.exec()
        
        dialog.accept()
