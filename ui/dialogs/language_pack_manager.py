"""
Language Pack Manager Dialog

Allows users to:
- View installed language packs
- Export English template
- Import custom language packs
- Switch languages
"""

from PyQt6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QGroupBox,
    QLabel, QPushButton, QListWidget, QListWidgetItem,
    QFileDialog, QMessageBox, QTextEdit
)
from PyQt6.QtCore import Qt
from pathlib import Path

from app.translations import (
    get_available_languages,
    export_template,
    import_language_pack,
    reload_languages,
    get_current_language,
    set_language
)


class LanguagePackManager(QDialog):
    """Dialog for managing language packs."""
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Language Pack Manager")
        self.setMinimumSize(600, 500)
        
        self._init_ui()
        self._load_languages()
    
    def _init_ui(self):
        """Initialize the UI."""
        layout = QVBoxLayout(self)
        
        # Title
        title = QLabel("🌐 Language Pack Manager")
        title.setStyleSheet("font-size: 14pt; font-weight: bold; padding: 10px;")
        layout.addWidget(title)
        
        # Description
        desc = QLabel(
            "Manage language packs for OptikR. You can export the English template, "
            "translate it, and import it back to add new languages."
        )
        desc.setWordWrap(True)
        desc.setStyleSheet("padding: 5px; color: #666;")
        layout.addWidget(desc)
        
        # Installed Languages Section
        lang_group = QGroupBox("📦 Installed Languages")
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
        actions_group = QGroupBox("⚙️ Actions")
        actions_layout = QVBoxLayout(actions_group)
        
        # Export button
        export_btn = QPushButton("📤 Export English Template")
        export_btn.setToolTip("Export English template for translation")
        export_btn.clicked.connect(self._export_template)
        actions_layout.addWidget(export_btn)
        
        # Export split button
        export_split_btn = QPushButton("📤 Export Split (8 Parts for ChatGPT)")
        export_split_btn.setToolTip("Export English template split into 8 smaller files for ChatGPT translation")
        export_split_btn.clicked.connect(self._export_template_split)
        actions_layout.addWidget(export_split_btn)
        
        # Import button
        import_btn = QPushButton("📥 Import Language Pack")
        import_btn.setToolTip("Import a translated language pack")
        import_btn.clicked.connect(self._import_pack)
        actions_layout.addWidget(import_btn)
        
        # Import merged button
        import_merged_btn = QPushButton("📥 Import Merged Split Files")
        import_merged_btn.setToolTip("Import and merge 8 translated split files")
        import_merged_btn.clicked.connect(self._import_merged_split)
        actions_layout.addWidget(import_merged_btn)
        
        # Reload button
        reload_btn = QPushButton("🔄 Reload Languages")
        reload_btn.setToolTip("Reload all language packs from disk")
        reload_btn.clicked.connect(self._reload_languages)
        actions_layout.addWidget(reload_btn)
        
        layout.addWidget(actions_group)
        
        # Instructions Section
        instructions_group = QGroupBox("💡 How to Add a New Language")
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
        close_btn = QPushButton("Close")
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
        # Ask where to save
        file_path, _ = QFileDialog.getSaveFileName(
            self,
            "Export English Template",
            "english_template.json",
            "JSON Files (*.json)"
        )
        
        if not file_path:
            return
        
        # Export
        if export_template(file_path):
            QMessageBox.information(
                self,
                "Export Successful",
                f"English template exported to:\n{file_path}\n\n"
                "You can now translate this file and import it back."
            )
        else:
            QMessageBox.critical(
                self,
                "Export Failed",
                "Failed to export template. Check console for errors."
            )
    
    def _export_template_split(self):
        """Export English template split into 8 parts for ChatGPT."""
        # Ask where to save (folder)
        folder_path = QFileDialog.getExistingDirectory(
            self,
            "Select Folder to Save Split Files",
            "",
            QFileDialog.Option.ShowDirsOnly
        )
        
        if not folder_path:
            return
        
        try:
            import json
            import math
            
            # Load English translations
            en_file = Path("app/translations/locales/en.json")
            with open(en_file, "r", encoding="utf-8") as f:
                data = json.load(f)
            
            translations = data.get("translations", {})
            metadata = data.get("_metadata", {})
            
            # Get all translation items
            items = list(translations.items())
            total_items = len(items)
            items_per_part = math.ceil(total_items / 8)
            
            # Split into 8 parts
            folder = Path(folder_path)
            for i in range(8):
                start_idx = i * items_per_part
                end_idx = min((i + 1) * items_per_part, total_items)
                
                # Get slice of items for this part
                part_items = items[start_idx:end_idx]
                part_dict = {"translations": dict(part_items)}
                
                # Add metadata to first file only
                if i == 0:
                    part_metadata = metadata.copy()
                    part_metadata["language_code"] = "NEW"
                    part_metadata["language_name"] = "New Language"
                    part_metadata["author"] = "Your Name"
                    part_dict["_metadata"] = part_metadata
                
                # Write to file
                output_file = folder / f"en_part_{i+1}_of_8.json"
                with open(output_file, "w", encoding="utf-8") as f:
                    json.dump(part_dict, f, ensure_ascii=False, indent=2)
            
            QMessageBox.information(
                self,
                "Export Successful",
                f"English template split into 8 parts:\n{folder_path}\n\n"
                f"Files: en_part_1_of_8.json through en_part_8_of_8.json\n"
                f"Each file has ~{items_per_part} translation keys\n\n"
                "Instructions:\n"
                "1. Upload each file to ChatGPT\n"
                "2. Ask: 'Translate this JSON to German'\n"
                "3. Save translated files as de_part_X_of_8.json\n"
                "4. Use 'Import Merged Split Files' to combine them"
            )
        except Exception as e:
            QMessageBox.critical(
                self,
                "Export Failed",
                f"Failed to export split template:\n{str(e)}"
            )
    
    def _import_pack(self):
        """Import a translated language pack."""
        # Ask for file
        file_path, _ = QFileDialog.getOpenFileName(
            self,
            "Import Language Pack",
            "",
            "JSON Files (*.json)"
        )
        
        if not file_path:
            return
        
        # Confirm
        reply = QMessageBox.question(
            self,
            "Confirm Import",
            f"Import language pack from:\n{file_path}\n\n"
            "This will add the language to your custom languages folder.",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
        )
        
        if reply != QMessageBox.StandardButton.Yes:
            return
        
        # Import
        if import_language_pack(file_path, custom=True):
            QMessageBox.information(
                self,
                "Import Successful",
                "Language pack imported successfully!\n\n"
                "The new language is now available in the language dropdown."
            )
            self._load_languages()
        else:
            QMessageBox.critical(
                self,
                "Import Failed",
                "Failed to import language pack.\n\n"
                "Please check:\n"
                "- File is valid JSON\n"
                "- Contains _metadata section\n"
                "- Contains translations section\n\n"
                "Check console for detailed errors."
            )
    
    def _reload_languages(self):
        """Reload all language packs."""
        reload_languages()
        self._load_languages()
        
        QMessageBox.information(
            self,
            "Reload Complete",
            "All language packs have been reloaded from disk."
        )
    
    def _import_merged_split(self):
        """Import and merge 8 translated split files."""
        # Ask for folder containing the split files
        folder_path = QFileDialog.getExistingDirectory(
            self,
            "Select Folder with Translated Split Files",
            "",
            QFileDialog.Option.ShowDirsOnly
        )
        
        if not folder_path:
            return
        
        try:
            import json
            
            folder = Path(folder_path)
            merged_translations = {}
            metadata = None
            
            # Look for files matching pattern: *_part_X_of_8.json
            found_files = []
            for i in range(1, 9):
                # Try different naming patterns
                patterns = [
                    f"de_part_{i}_of_8.json",
                    f"part_{i}_of_8.json",
                    f"translated_part_{i}.json",
                    f"part{i}.json"
                ]
                
                for pattern in patterns:
                    file_path = folder / pattern
                    if file_path.exists():
                        found_files.append((i, file_path))
                        break
            
            if not found_files:
                QMessageBox.warning(
                    self,
                    "No Files Found",
                    "Could not find translated split files in the selected folder.\n\n"
                    "Expected files like:\n"
                    "- de_part_1_of_8.json\n"
                    "- de_part_2_of_8.json\n"
                    "- etc."
                )
                return
            
            if len(found_files) < 8:
                reply = QMessageBox.question(
                    self,
                    "Incomplete Set",
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
                
                # Get metadata from first file
                if i == 1 and "_metadata" in part_data:
                    metadata = part_data["_metadata"]
                
                # Merge translations
                if "translations" in part_data:
                    merged_translations.update(part_data["translations"])
            
            # Validate metadata
            if not metadata:
                QMessageBox.warning(
                    self,
                    "Missing Metadata",
                    "No metadata found in the files.\n\n"
                    "Please ensure the first file contains _metadata section."
                )
                return
            
            # Ask for confirmation
            lang_code = metadata.get("language_code", "unknown")
            lang_name = metadata.get("language_name", "Unknown")
            
            reply = QMessageBox.question(
                self,
                "Confirm Import",
                f"Ready to import merged language pack:\n\n"
                f"Language: {lang_name} ({lang_code})\n"
                f"Total keys: {len(merged_translations)}\n"
                f"Files merged: {len(found_files)}\n\n"
                "Continue?",
                QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
            )
            
            if reply != QMessageBox.StandardButton.Yes:
                return
            
            # Create final merged file
            final_data = {
                "_metadata": metadata,
                "translations": merged_translations
            }
            
            # Update metadata
            final_data["_metadata"]["total_keys"] = len(merged_translations)
            final_data["_metadata"]["translated_keys"] = len(merged_translations)
            
            # Save to locales directory
            output_file = Path("app/translations/locales") / f"{lang_code}.json"
            with open(output_file, "w", encoding="utf-8") as f:
                json.dump(final_data, f, ensure_ascii=False, indent=2)
            
            # Reload languages
            reload_languages()
            self._load_languages()
            
            QMessageBox.information(
                self,
                "Import Successful",
                f"Successfully imported and merged {len(found_files)} files!\n\n"
                f"Language: {lang_name} ({lang_code})\n"
                f"Total keys: {len(merged_translations)}\n\n"
                "The new language is now available."
            )
            
        except Exception as e:
            import traceback
            QMessageBox.critical(
                self,
                "Import Failed",
                f"Failed to import merged split files:\n\n{str(e)}\n\n"
                f"Details:\n{traceback.format_exc()}"
            )


# Convenience function to show the dialog
def show_language_pack_manager(parent=None):
    """Show the language pack manager dialog."""
    dialog = LanguagePackManager(parent)
    dialog.exec()
