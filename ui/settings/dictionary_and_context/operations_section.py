"""
Operations Section

Dictionary actions: edit, create example, export, import, clear, and clean bad entries.
"""

import gzip
import json
import logging
import shutil
from datetime import datetime
from pathlib import Path

from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QGroupBox,
    QPushButton, QMessageBox,
)
from PyQt6.QtCore import pyqtSignal

logger = logging.getLogger(__name__)


class OperationsSection(QWidget):
    """Dictionary actions: edit, create example, export, import, clear, clean."""

    dictionaryModified = pyqtSignal()

    def __init__(self, config_manager=None, get_current_pair=None, parent=None):
        super().__init__(parent)
        self.config_manager = config_manager
        self._get_current_pair = get_current_pair or (lambda: None)
        self._init_ui()

    def _init_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(10)
        self._create_actions_group(layout)

    # ------------------------------------------------------------------
    # UI
    # ------------------------------------------------------------------

    def _create_actions_group(self, parent_layout):
        """Create actions section for dictionary management."""
        group = QGroupBox("🔧 Dictionary Actions")
        layout = QHBoxLayout(group)
        layout.setSpacing(10)
        layout.setContentsMargins(15, 20, 15, 15)

        edit_btn = QPushButton("📝 Edit Dictionary")
        edit_btn.setProperty("class", "action")
        edit_btn.setMinimumWidth(140)
        edit_btn.setToolTip("Open dictionary editor to browse, edit, and delete entries")
        edit_btn.clicked.connect(self._open_dictionary_editor)
        layout.addWidget(edit_btn)

        example_btn = QPushButton("📚 Create Example")
        example_btn.setProperty("class", "action")
        example_btn.setMinimumWidth(130)
        example_btn.setToolTip("Create an example dictionary with sample translations")
        example_btn.clicked.connect(self._create_example_dictionary)
        layout.addWidget(example_btn)

        export_btn = QPushButton("📤 Export")
        export_btn.setProperty("class", "action")
        export_btn.setMinimumWidth(90)
        export_btn.setToolTip("Export the selected dictionary")
        export_btn.clicked.connect(self._export_dictionary)
        layout.addWidget(export_btn)

        import_btn = QPushButton("📥 Import")
        import_btn.setProperty("class", "action")
        import_btn.setMinimumWidth(90)
        import_btn.clicked.connect(self._import_dictionary)
        layout.addWidget(import_btn)

        clear_btn = QPushButton("🗑️ Clear")
        clear_btn.setProperty("class", "action")
        clear_btn.setMinimumWidth(80)
        clear_btn.setToolTip("Clear only the selected language pair dictionary")
        clear_btn.clicked.connect(self._clear_dictionary)
        layout.addWidget(clear_btn)

        clean_btn = QPushButton("🧹 Clean Bad Entries")
        clean_btn.setProperty("class", "action")
        clean_btn.setMinimumWidth(150)
        clean_btn.setToolTip("Remove entries with OCR errors (| character, etc.)")
        clean_btn.clicked.connect(self._clean_bad_entries)
        layout.addWidget(clean_btn)

        layout.addStretch()
        parent_layout.addWidget(group)

    # ------------------------------------------------------------------
    # Actions
    # ------------------------------------------------------------------

    def _open_dictionary_editor(self):
        """Open dictionary editor dialog."""
        try:
            from ui.dialogs.dictionary_editor_dialog import DictionaryEditorDialog

            current_data = self._get_current_pair()
            if not current_data:
                QMessageBox.warning(self, "No Selection", "Please select a language pair to edit.")
                return

            source_lang, target_lang, file_path = current_data

            editor = DictionaryEditorDialog(
                parent=self,
                config_manager=self.config_manager,
                dictionary_path=file_path,
                source_lang=source_lang,
                target_lang=target_lang,
            )

            editor.dictionaryModified.connect(self.dictionaryModified.emit)
            editor.exec()

            # Refresh after closing regardless of whether signal fired
            self.dictionaryModified.emit()

        except ImportError:
            QMessageBox.information(
                self,
                "Editor Unavailable",
                "Dictionary editor could not be loaded.\n\n"
                "<b>Alternative:</b>\n"
                "1. Click 'Export' to save dictionary as JSON\n"
                "2. Edit the JSON file in any text editor\n"
                "3. Click 'Import' to load your changes\n\n"
                "This gives you full control over dictionary entries.",
            )
        except Exception as e:
            logger.error("Failed to open dictionary editor: %s", e, exc_info=True)
            QMessageBox.warning(self, "Error", f"Failed to open dictionary editor:\n{e}")

    def _create_example_dictionary(self):
        """Create an example dictionary with sample translations."""
        try:
            from app.utils.path_utils import get_dictionary_dir
            from PyQt6.QtWidgets import QInputDialog

            source_lang, ok1 = QInputDialog.getText(
                self, "Source Language", "Enter source language code (e.g., 'en'):", text="en"
            )
            if not ok1 or not source_lang:
                return

            target_lang, ok2 = QInputDialog.getText(
                self, "Target Language", "Enter target language code (e.g., 'de'):", text="de"
            )
            if not ok2 or not target_lang:
                return

            now = datetime.now().isoformat()
            example_translations = {
                "Hello": {
                    "translation": "Hallo", "confidence": 0.95,
                    "usage_count": 5, "created_at": now, "last_used": now,
                },
                "Good morning": {
                    "translation": "Guten Morgen", "confidence": 0.92,
                    "usage_count": 3, "created_at": now, "last_used": now,
                },
                "Thank you": {
                    "translation": "Danke", "confidence": 0.98,
                    "usage_count": 8, "created_at": now, "last_used": now,
                },
                "How are you?": {
                    "translation": "Wie geht es dir?", "confidence": 0.89,
                    "usage_count": 2, "created_at": now, "last_used": now,
                },
                "Goodbye": {
                    "translation": "Auf Wiedersehen", "confidence": 0.94,
                    "usage_count": 4, "created_at": now, "last_used": now,
                },
            }

            dict_data = {
                "metadata": {
                    "source_language": source_lang,
                    "target_language": target_lang,
                    "created_at": now,
                    "updated_at": now,
                    "version": "1.0",
                    "total_entries": len(example_translations),
                    "hit_rate": 0.75,
                },
                "translations": example_translations,
            }

            dict_dir = get_dictionary_dir()
            dict_dir.mkdir(parents=True, exist_ok=True)

            dict_filename = f"{source_lang}_{target_lang}.json.gz"
            dict_path = dict_dir / dict_filename

            if dict_path.exists():
                reply = QMessageBox.question(
                    self,
                    "File Exists",
                    f"Dictionary for {source_lang} → {target_lang} already exists.\n\n"
                    "Do you want to overwrite it?",
                    QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
                    QMessageBox.StandardButton.No,
                )
                if reply != QMessageBox.StandardButton.Yes:
                    return

            with gzip.open(dict_path, 'wt', encoding='utf-8') as f:
                json.dump(dict_data, f, ensure_ascii=False, indent=2)

            self.dictionaryModified.emit()

            QMessageBox.information(
                self,
                "Example Created",
                f"Example dictionary created successfully!\n\n"
                f"Language Pair: {source_lang} → {target_lang}\n"
                f"Sample Entries: {len(example_translations)}\n"
                f"File: {dict_filename}",
            )

        except Exception as e:
            logger.error("Failed to create example dictionary: %s", e, exc_info=True)
            QMessageBox.critical(self, "Creation Error", f"Failed to create example dictionary:\n{e}")

    def _export_dictionary(self):
        """Export selected dictionary to a JSON file."""
        try:
            from PyQt6.QtWidgets import QFileDialog

            current_data = self._get_current_pair()
            if not current_data:
                QMessageBox.warning(self, "No Selection", "Please select a language pair to export.")
                return

            source_lang, target_lang, file_path = current_data

            dict_path = Path(file_path)
            if not dict_path.exists():
                QMessageBox.warning(self, "File Not Found", "Dictionary file not found.")
                return

            export_path, _ = QFileDialog.getSaveFileName(
                self,
                "Export Dictionary",
                f"dictionary_{source_lang}_{target_lang}.json",
                "JSON Files (*.json);;All Files (*)",
            )
            if not export_path:
                return

            with gzip.open(dict_path, 'rt', encoding='utf-8') as f:
                data = json.load(f)

            with open(export_path, 'w', encoding='utf-8') as f:
                json.dump(data, f, indent=2, ensure_ascii=False)

            QMessageBox.information(
                self,
                "Export Complete",
                f"Dictionary exported to:\n{export_path}\n\n"
                f"Entries: {len(data.get('translations', {})):,}",
            )

        except Exception as e:
            logger.error("Failed to export dictionary: %s", e, exc_info=True)
            QMessageBox.critical(self, "Export Error", f"Failed to export dictionary:\n{e}")

    def _import_dictionary(self):
        """Import dictionary from various formats and convert to smart dict format."""
        try:
            from PyQt6.QtWidgets import QFileDialog, QInputDialog
            from app.utils.path_utils import get_dictionary_dir

            import_path, _ = QFileDialog.getOpenFileName(
                self,
                "Import Dictionary",
                "",
                "JSON Files (*.json);;Compressed JSON (*.json.gz);;All Files (*)",
            )
            if not import_path:
                return

            import_path = Path(import_path)

            if import_path.suffix == '.gz':
                with gzip.open(import_path, 'rt', encoding='utf-8') as f:
                    data = json.load(f)
            else:
                with open(import_path, 'r', encoding='utf-8') as f:
                    data = json.load(f)

            # Defaults from current selection if available
            default_source = 'en'
            default_target = 'de'
            current_data = self._get_current_pair()
            if current_data:
                default_source, default_target, _ = current_data

            source_lang, ok1 = QInputDialog.getText(
                self,
                "Source Language",
                "Enter source language code for imported dictionary:",
                text=default_source,
            )
            if not ok1 or not source_lang:
                return

            target_lang, ok2 = QInputDialog.getText(
                self,
                "Target Language",
                "Enter target language code for imported dictionary:",
                text=default_target,
            )
            if not ok2 or not target_lang:
                return

            converted_data = self._convert_to_smart_dict_format(data)
            if not converted_data:
                QMessageBox.warning(
                    self,
                    "Invalid Format",
                    "Could not recognize dictionary format.\n\n"
                    "Supported formats:\n"
                    "• Smart Dictionary format (with 'translations' key)\n"
                    "• Simple key-value pairs (e.g., {'hello': 'hallo'})\n"
                    "• Array format ([{'source': 'hello', 'target': 'hallo'}])",
                )
                return

            converted_data['source_language'] = source_lang
            converted_data['target_language'] = target_lang

            dict_dir = get_dictionary_dir()
            dict_dir.mkdir(parents=True, exist_ok=True)

            dict_filename = f"{source_lang}_{target_lang}.json.gz"
            dict_path = dict_dir / dict_filename

            merge_mode = False
            if dict_path.exists():
                reply = QMessageBox.question(
                    self,
                    "File Exists",
                    f"Dictionary for {source_lang} → {target_lang} already exists.\n\n"
                    "Do you want to merge with existing dictionary?",
                    QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No | QMessageBox.StandardButton.Cancel,
                    QMessageBox.StandardButton.Yes,
                )
                if reply == QMessageBox.StandardButton.Cancel:
                    return
                elif reply == QMessageBox.StandardButton.Yes:
                    merge_mode = True
                    with gzip.open(dict_path, 'rt', encoding='utf-8') as f:
                        existing_data = json.load(f)

                    existing_translations = existing_data.get('translations', {})
                    new_translations = converted_data['translations']

                    for key, value in new_translations.items():
                        if key not in existing_translations:
                            existing_translations[key] = value

                    converted_data['translations'] = existing_translations
                    converted_data['total_entries'] = len(existing_translations)

            final_data = {
                'version': '1.0',
                'last_updated': datetime.now().isoformat(),
                'total_entries': converted_data['total_entries'],
                'compressed': True,
                'source_language': source_lang,
                'target_language': target_lang,
                'translations': converted_data['translations'],
            }

            with gzip.open(dict_path, 'wt', encoding='utf-8') as f:
                json.dump(final_data, f, indent=2, ensure_ascii=False)

            self.dictionaryModified.emit()

            entry_count = len(final_data['translations'])
            QMessageBox.information(
                self,
                "Import Complete",
                f"✅ Dictionary imported successfully!\n\n"
                f"Language pair: {source_lang} → {target_lang}\n"
                f"Entries: {entry_count:,}\n"
                f"{'Merged with existing dictionary' if merge_mode else 'New dictionary created'}\n\n"
                f"All imported entries have full confidence (1.0) as they are user-trusted.",
            )

        except Exception as e:
            logger.error("Failed to import dictionary: %s", e, exc_info=True)
            QMessageBox.critical(self, "Import Error", f"Failed to import dictionary:\n{e}")

    def _convert_to_smart_dict_format(self, data):
        """Convert various dictionary formats to smart dict format."""
        try:
            translations = {}
            source_lang = 'unknown'
            target_lang = 'unknown'

            # Format 1: Smart Dictionary format (already correct)
            if 'translations' in data and isinstance(data['translations'], dict):
                translations = data['translations']
                source_lang = data.get('source_language', 'unknown')
                target_lang = data.get('target_language', 'unknown')

                for _key, entry in translations.items():
                    if 'confidence' not in entry:
                        entry['confidence'] = 1.0
                    if 'usage_count' not in entry:
                        entry['usage_count'] = 1
                    if 'engine' not in entry:
                        entry['engine'] = 'imported'
                    if 'last_used' not in entry:
                        entry['last_used'] = datetime.now().isoformat()

            # Format 2: Simple key-value pairs {'hello': 'hallo', 'world': 'welt'}
            elif isinstance(data, dict) and all(isinstance(v, str) for v in data.values()):
                for original, translation in data.items():
                    translations[original] = {
                        'original': original,
                        'translation': translation,
                        'usage_count': 1,
                        'confidence': 1.0,
                        'last_used': datetime.now().isoformat(),
                        'engine': 'imported',
                    }

            # Format 3: Array format [{'source': 'hello', 'target': 'hallo'}, ...]
            elif isinstance(data, list):
                for item in data:
                    if isinstance(item, dict):
                        original = (
                            item.get('source') or item.get('original')
                            or item.get('text') or item.get('from')
                        )
                        translation = (
                            item.get('target') or item.get('translation')
                            or item.get('to')
                        )
                        if original and translation:
                            translations[original] = {
                                'original': original,
                                'translation': translation,
                                'usage_count': item.get('usage_count', 1),
                                'confidence': item.get('confidence', 1.0),
                                'last_used': item.get('last_used', datetime.now().isoformat()),
                                'engine': item.get('engine', 'imported'),
                            }

            # Format 4: Nested format {'entries': [...]} or {'data': {...}}
            elif 'entries' in data:
                return self._convert_to_smart_dict_format(data['entries'])
            elif 'data' in data:
                return self._convert_to_smart_dict_format(data['data'])

            if not translations:
                return None

            return {
                'translations': translations,
                'source_language': source_lang,
                'target_language': target_lang,
                'total_entries': len(translations),
            }

        except Exception as e:
            logger.error("Format conversion failed: %s", e)
            return None

    def _clear_dictionary(self):
        """Clear selected dictionary."""
        try:
            current_data = self._get_current_pair()
            if not current_data:
                QMessageBox.warning(self, "No Selection", "Please select a language pair to clear.")
                return

            source_lang, target_lang, file_path = current_data

            reply = QMessageBox.question(
                self,
                "Clear Dictionary",
                f"Are you sure you want to clear the dictionary for {source_lang} → {target_lang}?\n\n"
                "This will permanently delete all learned translations for this language pair.\n"
                "This action cannot be undone.",
                QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
                QMessageBox.StandardButton.No,
            )

            if reply == QMessageBox.StandardButton.Yes:
                dict_path = Path(file_path)
                if dict_path.exists():
                    dict_path.unlink()
                    self.dictionaryModified.emit()
                    QMessageBox.information(
                        self,
                        "Dictionary Cleared",
                        f"Dictionary for {source_lang} → {target_lang} has been cleared.",
                    )
                else:
                    QMessageBox.warning(
                        self,
                        "File Not Found",
                        "Dictionary file not found. It may have already been deleted.",
                    )
                    self.dictionaryModified.emit()

        except Exception as e:
            logger.error("Failed to clear dictionary: %s", e, exc_info=True)
            QMessageBox.critical(self, "Clear Error", f"Failed to clear dictionary:\n{e}")

    def _clean_bad_entries(self):
        """Remove entries with OCR errors (| character, etc.) from selected dictionary."""
        try:
            current_data = self._get_current_pair()
            if not current_data:
                QMessageBox.warning(self, "No Selection", "Please select a language pair to clean.")
                return

            source_lang, target_lang, file_path = current_data
            dict_path = Path(file_path)

            if not dict_path.exists():
                QMessageBox.warning(self, "File Not Found", "Dictionary file not found.")
                return

            with gzip.open(dict_path, 'rt', encoding='utf-8') as f:
                data = json.load(f)

            translations = data.get('translations', {})
            original_count = len(translations)

            bad_patterns = ['|', '¦', '│']
            bad_entries = []

            for key, entry in list(translations.items()):
                original = entry.get('original', '')
                if any(pattern in original for pattern in bad_patterns):
                    bad_entries.append((key, original, entry.get('translation', '')))

            if not bad_entries:
                QMessageBox.information(
                    self,
                    "No Bad Entries",
                    f"No entries with OCR errors found in {source_lang} → {target_lang} dictionary.\n\n"
                    "The dictionary is clean!",
                )
                return

            bad_list = "\n".join([f"• '{orig}' → '{trans}'" for _, orig, trans in bad_entries[:5]])
            if len(bad_entries) > 5:
                bad_list += f"\n... and {len(bad_entries) - 5} more"

            reply = QMessageBox.question(
                self,
                "Clean Bad Entries",
                f"Found {len(bad_entries)} entries with OCR errors in {source_lang} → {target_lang}:\n\n"
                f"{bad_list}\n\n"
                "Remove these entries?\n"
                "(A backup will be created automatically)",
                QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
                QMessageBox.StandardButton.Yes,
            )

            if reply == QMessageBox.StandardButton.Yes:
                backup_path = dict_path.with_suffix('.json.gz.backup')
                shutil.copy2(dict_path, backup_path)

                for key, _, _ in bad_entries:
                    del translations[key]

                data['total_entries'] = len(translations)
                data['last_updated'] = datetime.now().isoformat()

                with gzip.open(dict_path, 'wt', encoding='utf-8') as f:
                    json.dump(data, f, indent=2, ensure_ascii=False)

                self.dictionaryModified.emit()

                QMessageBox.information(
                    self,
                    "Cleaning Complete",
                    f"Removed {len(bad_entries)} bad entries from {source_lang} → {target_lang}.\n\n"
                    f"Original entries: {original_count}\n"
                    f"Cleaned entries: {len(translations)}\n\n"
                    f"Backup saved to:\n{backup_path.name}",
                )

        except Exception as e:
            logger.error("Failed to clean bad entries: %s", e, exc_info=True)
            QMessageBox.critical(self, "Clean Error", f"Failed to clean bad entries:\n{e}")
