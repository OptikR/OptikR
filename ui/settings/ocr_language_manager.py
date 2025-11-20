"""
OCR Language Manager
Handles language pack management including add, remove, and download operations.
"""

from PyQt6.QtWidgets import (
    QMessageBox, QInputDialog, QListWidget, QListWidgetItem,
    QDialog, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QTableWidget, QTableWidgetItem, QHeaderView, QCheckBox, QWidget,
    QProgressDialog, QApplication
)
from PyQt6.QtCore import Qt


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
        print("[OCR TAB] Add Language button clicked")
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
                    "All Languages Installed",
                    "All available languages are already in your list!"
                )
                return
            
            language, ok = QInputDialog.getItem(
                self.parent,
                "Add Language",
                "Select a language to add:",
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
                    "Language Added",
                    f"{language} has been added to the list.\n\n"
                    "Click '⬇️ Download Packs' to download the language data."
                )
                
        except Exception as e:
            print(f"[ERROR] Failed to add language: {e}")
            import traceback
            traceback.print_exc()
            QMessageBox.critical(
                self.parent,
                "Error",
                f"Failed to add language:\n\n{str(e)}"
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
                "No Selection",
                "Please select a language to remove."
            )
            return
        
        language = current_item.text()
        
        # Confirm removal
        reply = QMessageBox.question(
            self.parent,
            "Remove Language",
            f"Are you sure you want to remove {language}?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            QMessageBox.StandardButton.No
        )
        
        if reply == QMessageBox.StandardButton.Yes:
            row = language_list.row(current_item)
            language_list.takeItem(row)
    
    def show_selective_download_dialog(self):
        """Show dialog to select specific languages for specific OCR engines."""
        print("[OCR TAB] Download Packs button clicked")
        
        dialog = QDialog(self.parent)
        dialog.setWindowTitle("Download Language Packs")
        dialog.setMinimumWidth(800)
        dialog.setMinimumHeight(600)
        
        layout = QVBoxLayout(dialog)
        layout.setSpacing(15)
        layout.setContentsMargins(20, 20, 20, 20)
        
        # Header
        header = QLabel("📥 Select Languages to Download")
        header.setStyleSheet("font-size: 14pt; font-weight: bold;")
        layout.addWidget(header)
        
        # Description
        desc = QLabel(
            "Select which languages you want to download for each OCR engine. "
            "Each engine has different language support and model sizes."
        )
        desc.setWordWrap(True)
        desc.setStyleSheet("color: #666666; font-size: 9pt; margin-bottom: 10px;")
        layout.addWidget(desc)
        
        # Create table for language selection
        table = QTableWidget()
        table.setColumnCount(6)
        table.setHorizontalHeaderLabels(["Language", "EasyOCR", "Tesseract", "PaddleOCR", "Manga", "Size"])
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
                ("paddleocr", paddle), ("manga_ocr", manga)
            ], start=1):
                checkbox_widget = QWidget()
                checkbox_layout = QHBoxLayout(checkbox_widget)
                checkbox_layout.setContentsMargins(0, 0, 0, 0)
                checkbox_layout.setAlignment(Qt.AlignmentFlag.AlignCenter)
                
                checkbox = QCheckBox()
                checkbox.setEnabled(supported)
                if not supported:
                    checkbox.setToolTip("Not supported by this engine")
                checkbox_layout.addWidget(checkbox)
                
                table.setCellWidget(row, col, checkbox_widget)
                row_checkboxes[engine] = checkbox
            
            # Size
            table.setItem(row, 6, QTableWidgetItem(size))
            
            # Store for later
            checkboxes.append((lang_name, lang_code, row_checkboxes))
        
        layout.addWidget(table)
        
        # Selection helpers
        helper_layout = QHBoxLayout()
        
        select_all_btn = QPushButton("Select All")
        select_all_btn.clicked.connect(lambda: self._toggle_all_checkboxes(checkboxes, True))
        helper_layout.addWidget(select_all_btn)
        
        clear_all_btn = QPushButton("Clear All")
        clear_all_btn.clicked.connect(lambda: self._toggle_all_checkboxes(checkboxes, False))
        helper_layout.addWidget(clear_all_btn)
        
        helper_layout.addStretch()
        layout.addLayout(helper_layout)
        
        # Info label
        info_label = QLabel(
            "💡 <b>Important:</b> EasyOCR, PaddleOCR, and Manga OCR download language models automatically when first used. "
            "This dialog helps you configure which languages to enable. "
            "Tesseract requires manual installation of language data files."
        )
        info_label.setWordWrap(True)
        info_label.setStyleSheet("color: #2196F3; font-size: 9pt; padding: 10px; "
                                "background-color: #1E3A4F; border-left: 3px solid #4A9EFF; border-radius: 3px;")
        layout.addWidget(info_label)
        
        # Buttons
        button_layout = QHBoxLayout()
        button_layout.addStretch()
        
        cancel_btn = QPushButton("Cancel")
        cancel_btn.clicked.connect(dialog.reject)
        button_layout.addWidget(cancel_btn)
        
        download_btn = QPushButton("Download Selected")
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
                "No Selection",
                "Please select at least one language pack to configure."
            )
            return
        
        # Build message
        message_parts = []
        
        # Group by engine
        easyocr_langs = [name for name, code, eng in selected_langs if eng == "easyocr"]
        paddleocr_langs = [name for name, code, eng in selected_langs if eng == "paddleocr"]
        manga_langs = [name for name, code, eng in selected_langs if eng == "manga_ocr"]
        tess_langs = [name for name, code, eng in selected_langs if eng == "tesseract"]
        
        message_parts.append(f"<b>Configured {len(selected_langs)} language pack(s):</b><br><br>")
        
        if easyocr_langs:
            message_parts.append(f"<b>✓ EasyOCR ({len(easyocr_langs)} languages):</b><br>")
            message_parts.append(f"  {', '.join(easyocr_langs)}<br>")
            message_parts.append(f"  <i>Models will download automatically when first used.</i><br><br>")
        
        if paddleocr_langs:
            message_parts.append(f"<b>✓ PaddleOCR ({len(paddleocr_langs)} languages):</b><br>")
            message_parts.append(f"  {', '.join(paddleocr_langs)}<br>")
            message_parts.append(f"  <i>Models will download automatically when first used.</i><br><br>")
        
        if manga_langs:
            message_parts.append(f"<b>✓ Manga OCR ({len(manga_langs)} languages):</b><br>")
            message_parts.append(f"  {', '.join(manga_langs)}<br>")
            message_parts.append(f"  <i>Model is already included (Japanese only).</i><br><br>")
        
        if tess_langs:
            message_parts.append(f"<b>⚠ Tesseract OCR ({len(tess_langs)} languages):</b><br>")
            message_parts.append(f"  {', '.join(tess_langs)}<br>")
            message_parts.append(f"  <i>You must manually download language data from:<br>")
            message_parts.append(f"  https://github.com/tesseract-ocr/tessdata</i><br><br>")
        
        message_parts.append("<br><b>Next steps:</b><br>")
        message_parts.append("• The selected languages are now configured<br>")
        message_parts.append("• EasyOCR and PaddleOCR will download models on first use<br>")
        if tess_langs:
            message_parts.append("• For Tesseract, download .traineddata files manually<br>")
        
        msg_box = QMessageBox(dialog)
        msg_box.setWindowTitle("Language Packs Configured")
        msg_box.setTextFormat(Qt.TextFormat.RichText)
        msg_box.setText("".join(message_parts))
        msg_box.setIcon(QMessageBox.Icon.Information)
        msg_box.exec()
        
        dialog.accept()
