"""
Localization Manager Dialog

Manages OptikR's own UI language packs (NOT translation models).
Allows users to:
- View installed UI locale packs
- Export English template for community translation
- Import custom locale packs
- Split/merge for ChatGPT-assisted translation workflow
"""

import json
import logging
import math
import traceback

from PyQt6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QGroupBox,
    QLabel, QPushButton, QListWidget, QListWidgetItem,
    QFileDialog, QMessageBox, QTextEdit
)
from PyQt6.QtCore import Qt
from pathlib import Path

from app.localization import (
    tr,
    get_available_languages,
    export_template,
    import_language_pack,
    reload_languages,
    get_current_language,
)

logger = logging.getLogger(__name__)


class LocalizationManager(QDialog):
    """Dialog for managing UI localization packs."""
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle(tr("language_pack_manager"))
        self.setMinimumSize(600, 500)
        
        self._init_ui()
        self._load_languages()
    
    def _init_ui(self):
        """Initialize the UI."""
        layout = QVBoxLayout(self)
        
        # Title
        title = QLabel(tr("language_pack_manager_2"))
        title.setStyleSheet("font-size: 14pt; font-weight: bold; padding: 10px;")
        layout.addWidget(title)
        
        # Description
        desc = QLabel(tr("manage_language_packs_for_optikr_you_can_export_the_english_"))
        desc.setWordWrap(True)
        desc.setStyleSheet("padding: 5px; color: #666;")
        layout.addWidget(desc)
        
        # Installed Languages Section
        lang_group = QGroupBox(tr("installed_languages"))
        lang_layout = QVBoxLayout(lang_group)
        
        self.lang_list = QListWidget()
        self.lang_list.setStyleSheet("font-size: 10pt;")
        lang_layout.addWidget(self.lang_list)
        
        # Language info
        self.lang_info = QLabel()
        self.lang_info.setStyleSheet("padding: 5px; background: #f0f0f0; border-radius: 3px;")
        self.lang_info.setWordWrap(True)
        lang_layout.addWidget(self.lang_info)
        
        layout.addWidget(lang_group)
        
        # Actions Section
        actions_group = QGroupBox(tr("actions"))
        actions_layout = QVBoxLayout(actions_group)
        
        # Export button
        export_btn = QPushButton(tr("export_english_template"))
        export_btn.setToolTip(tr("export_english_template_for_translation"))
        export_btn.clicked.connect(self._export_template)
        actions_layout.addWidget(export_btn)
        
        # Export split button
        export_split_btn = QPushButton(tr("export_split_8_parts_for_chatgpt"))
        export_split_btn.setToolTip(tr("export_english_template_split_into_8_smaller_files_for_chatg"))
        export_split_btn.clicked.connect(self._export_template_split)
        actions_layout.addWidget(export_split_btn)
        
        # Import button
        import_btn = QPushButton(tr("import_language_pack"))
        import_btn.setToolTip(tr("import_a_translated_language_pack"))
        import_btn.clicked.connect(self._import_pack)
        actions_layout.addWidget(import_btn)
        
        # Import merged button
        import_merged_btn = QPushButton(tr("import_merged_split_files"))
        import_merged_btn.setToolTip(tr("import_and_merge_8_translated_split_files"))
        import_merged_btn.clicked.connect(self._import_merged_split)
        actions_layout.addWidget(import_merged_btn)
        
        # Reload button
        reload_btn = QPushButton(tr("reload_languages"))
        reload_btn.setToolTip(tr("reload_all_language_packs_from_disk"))
        reload_btn.clicked.connect(self._reload_languages)
        actions_layout.addWidget(reload_btn)
        
        layout.addWidget(actions_group)
        
        # Instructions Section
        instructions_group = QGroupBox(tr("how_to_add_a_new_language"))
        instructions_layout = QVBoxLayout(instructions_group)
        
        instructions = QTextEdit()
        instructions.setReadOnly(True)
        instructions.setMaximumHeight(150)
        instructions.setStyleSheet("""
            QTextEdit {
                background-color: #2b2b2b;
                color: #e0e0e0;
                border: 1px solid #555;
                border-radius: 3px;
                padding: 5px;
            }
        """)
        instructions.setHtml("""
        <ol>
            <li><b>Export Template:</b> 
                <ul>
                    <li>Small file: Click "Export English Template"</li>
                    <li>For ChatGPT: Click "Export Split (8 Parts)" - splits into manageable chunks</li>
                </ul>
            </li>
            <li><b>Translate:</b> 
                <ul>
                    <li>Option A: Edit the JSON file manually</li>
                    <li>Option B (Recommended): Upload each part to ChatGPT and ask: "Translate this JSON to Spanish"</li>
                    <li>Option C: Use an online JSON translation tool</li>
                </ul>
            </li>
            <li><b>Update Metadata:</b> Change language_code and language_name in the first file</li>
            <li><b>Import:</b> 
                <ul>
                    <li>Single file: Click "Import Language Pack"</li>
                    <li>Split files: Click "Import Merged Split Files" and select the folder</li>
                </ul>
            </li>
            <li><b>Done!</b> Your language will appear in the language dropdown</li>
        </ol>
        """)
        instructions_layout.addWidget(instructions)
        
        layout.addWidget(instructions_group)
        
        # Close button
        close_btn = QPushButton(tr("close"))
        close_btn.clicked.connect(self.accept)
        layout.addWidget(close_btn)
    
    def _load_languages(self):
        """Load and display installed languages."""
        self.lang_list.clear()
        
        languages = get_available_languages()
        current_lang = get_current_language()
        
        for code, name in sorted(languages.items()):
            item = QListWidgetItem(f"{name} ({code})")
            
            # Highlight current language
            if code == current_lang:
                item.setText(f"✓ {name} ({code}) - Current")
                item.setBackground(Qt.GlobalColor.lightGray)
            
            self.lang_list.addItem(item)
        
        # Update info
        self.lang_info.setText(
            f"Total languages installed: {len(languages)}\n"
            f"Current language: {languages.get(current_lang, 'Unknown')}"
        )
    
    def _export_template(self):
        """Export English template for translation."""
        file_path, _ = QFileDialog.getSaveFileName(
            self,
            "Export English Template",
            "english_template.json",
            "JSON Files (*.json)"
        )
        
        if not file_path:
            return
        
        if export_template(file_path):
            QMessageBox.information(
                self,
                tr("export_successful"),
                f"English template exported to:\n{file_path}\n\n"
                "You can now translate this file and import it back."
            )
        else:
            QMessageBox.critical(
                self,
                tr("export_failed"),
                tr("failed_to_export_template_check_console_for_errors")
            )
    
    def _export_template_split(self):
        """Export English template split into 8 parts for ChatGPT.
        
        Uses the localization module's export_template() to get a consistent
        template, then splits the translations into 8 files.
        """
        folder_path = QFileDialog.getExistingDirectory(
            self,
            "Select Folder to Save Split Files",
            "",
            QFileDialog.Option.ShowDirsOnly
        )
        
        if not folder_path:
            return
        
        try:
            folder = Path(folder_path)
            
            # Export full template to a temp file first, then split it
            # This ensures consistency with the single-file export
            temp_file = folder / "_temp_full_template.json"
            if not export_template(str(temp_file)):
                QMessageBox.critical(
                    self,
                    tr("export_failed"),
                    tr("failed_to_export_template_check_console_for_errors")
                )
                return
            
            with open(temp_file, "r", encoding="utf-8") as f:
                data = json.load(f)
            
            # Clean up temp file
            temp_file.unlink(missing_ok=True)
            
            translations = data.get("translations", {})
            metadata = data.get("_metadata", {})
            
            items = list(translations.items())
            total_items = len(items)
            items_per_part = math.ceil(total_items / 8)
            
            for i in range(8):
                start_idx = i * items_per_part
                end_idx = min((i + 1) * items_per_part, total_items)
                
                part_items = items[start_idx:end_idx]
                part_dict = {"translations": dict(part_items)}
                
                # Add metadata to first file only
                if i == 0:
                    part_metadata = metadata.copy()
                    part_metadata["language_code"] = "NEW"
                    part_metadata["language_name"] = "New Language"
                    part_metadata["author"] = "Your Name"
                    part_dict["_metadata"] = part_metadata
                
                output_file = folder / f"en_part_{i+1}_of_8.json"
                with open(output_file, "w", encoding="utf-8") as f:
                    json.dump(part_dict, f, ensure_ascii=False, indent=2)
            
            QMessageBox.information(
                self,
                tr("export_successful"),
                f"English template split into 8 parts:\n{folder_path}\n\n"
                f"Files: en_part_1_of_8.json through en_part_8_of_8.json\n"
                f"Each file has ~{items_per_part} translation keys\n\n"
                "Instructions:\n"
                "1. Upload each file to ChatGPT\n"
                "2. Ask: 'Translate this JSON to [language]'\n"
                "3. Save translated files with any name containing _part_X_of_8\n"
                "4. Use 'Import Merged Split Files' to combine them"
            )
        except Exception as e:
            logger.error("Failed to export split template: %s", e, exc_info=True)
            QMessageBox.critical(
                self,
                tr("export_failed"),
                f"Failed to export split template:\n{str(e)}"
            )
    
    def _import_pack(self):
        """Import a translated language pack."""
        file_path, _ = QFileDialog.getOpenFileName(
            self,
            "Import Language Pack",
            "",
            "JSON Files (*.json)"
        )
        
        if not file_path:
            return
        
        reply = QMessageBox.question(
            self,
            tr("confirm_import"),
            f"Import language pack from:\n{file_path}\n\n"
            "This will add the language to your custom languages folder.",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
        )
        
        if reply != QMessageBox.StandardButton.Yes:
            return
        
        result = import_language_pack(file_path, custom=True)
        if result.success:
            QMessageBox.information(
                self,
                tr("import_successful"),
                tr("language_pack_imported_successfully_the_new_language_is_now_")
            )
            self._load_languages()
        else:
            QMessageBox.critical(
                self,
                tr("import_failed"),
                tr("failed_to_import_language_pack_please_check_file_is_valid_js")
            )
    
    def _reload_languages(self):
        """Reload all language packs."""
        reload_languages()
        self._load_languages()
        
        QMessageBox.information(
            self,
            tr("reload_complete"),
            tr("all_language_packs_have_been_reloaded_from_disk")
        )
    
    def _import_merged_split(self):
        """Import and merge translated split files.
        
        Scans the selected folder for files matching *_part_X_of_8.json
        (any language prefix), merges them, and imports via the localization
        module's import_language_pack() API.
        """
        folder_path = QFileDialog.getExistingDirectory(
            self,
            "Select Folder with Translated Split Files",
            "",
            QFileDialog.Option.ShowDirsOnly
        )
        
        if not folder_path:
            return
        
        try:
            folder = Path(folder_path)
            merged_translations = {}
            metadata = None
            
            # Find files matching *_part_X_of_8.json (any language prefix)
            found_files = []
            for i in range(1, 9):
                # Use glob to match any prefix
                matches = list(folder.glob(f"*_part_{i}_of_8.json"))
                if not matches:
                    # Try alternative patterns
                    for pattern in [f"part_{i}_of_8.json", f"translated_part_{i}.json", f"part{i}.json"]:
                        candidate = folder / pattern
                        if candidate.exists():
                            matches = [candidate]
                            break
                
                if matches:
                    found_files.append((i, matches[0]))
            
            if not found_files:
                QMessageBox.warning(
                    self,
                    tr("no_files_found"),
                    tr("could_not_find_translated_split_files_in_the_selected_folder")
                )
                return
            
            if len(found_files) < 8:
                reply = QMessageBox.question(
                    self,
                    tr("incomplete_set"),
                    f"Only found {len(found_files)} of 8 files.\n\n"
                    "Do you want to continue with partial import?",
                    QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
                )
                if reply != QMessageBox.StandardButton.Yes:
                    return
            
            # Read and merge all parts
            for i, file_path in sorted(found_files):
                with open(file_path, "r", encoding="utf-8") as f:
                    part_data = json.load(f)
                
                if i == 1 and "_metadata" in part_data:
                    metadata = part_data["_metadata"]
                
                if "translations" in part_data:
                    merged_translations.update(part_data["translations"])
            
            if not metadata:
                QMessageBox.warning(
                    self,
                    tr("missing_metadata"),
                    tr("no_metadata_found_in_the_files_please_ensure_the_first_file_")
                )
                return
            
            lang_code = metadata.get("language_code", "unknown")
            lang_name = metadata.get("language_name", "Unknown")
            
            reply = QMessageBox.question(
                self,
                tr("confirm_import"),
                f"Ready to import merged language pack:\n\n"
                f"Language: {lang_name} ({lang_code})\n"
                f"Total keys: {len(merged_translations)}\n"
                f"Files merged: {len(found_files)}\n\n"
                "Continue?",
                QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
            )
            
            if reply != QMessageBox.StandardButton.Yes:
                return
            
            # Build final merged data and save to a temp file for import
            final_data = {
                "_metadata": metadata,
                "translations": merged_translations
            }
            final_data["_metadata"]["total_keys"] = len(merged_translations)
            final_data["_metadata"]["translated_keys"] = len(merged_translations)
            
            # Write to temp file, then import via the localization API
            # This ensures the file goes to locales/custom/ with proper validation
            temp_merged = folder / f"_merged_{lang_code}.json"
            with open(temp_merged, "w", encoding="utf-8") as f:
                json.dump(final_data, f, ensure_ascii=False, indent=2)
            
            result = import_language_pack(str(temp_merged), custom=True)
            
            # Clean up temp file
            temp_merged.unlink(missing_ok=True)
            
            if result.success:
                self._load_languages()
                QMessageBox.information(
                    self,
                    tr("import_successful"),
                    f"Successfully imported and merged {len(found_files)} files!\n\n"
                    f"Language: {lang_name} ({lang_code})\n"
                    f"Total keys: {len(merged_translations)}\n\n"
                    "The new language is now available."
                )
            else:
                QMessageBox.critical(
                    self,
                    tr("import_failed"),
                    f"Merged file failed validation.\n"
                    f"Please check that the first file has valid _metadata "
                    f"with language_code and language_name."
                )
            
        except Exception as e:
            logger.error("Failed to import merged split files: %s", e, exc_info=True)
            QMessageBox.critical(
                self,
                tr("import_failed"),
                f"Failed to import merged split files:\n\n{str(e)}\n\n"
                f"Details:\n{traceback.format_exc()}"
            )


# Backward-compatible alias
LanguagePackManager = LocalizationManager


def show_localization_manager(parent=None):
    """Show the localization manager dialog."""
    dialog = LocalizationManager(parent)
    dialog.exec()


# Backward-compatible alias
show_language_pack_manager = show_localization_manager
