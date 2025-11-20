"""
Translation Dictionary Manager
Handles learning dictionary operations including export, import, stats, and clearing.
Enhanced with multi-format support and compression capabilities.
"""

from PyQt6.QtWidgets import (QMessageBox, QFileDialog, QDialog, QVBoxLayout, QLabel, 
                              QPushButton, QTextEdit, QCheckBox, QComboBox, QHBoxLayout,
                              QGroupBox, QProgressDialog)
from pathlib import Path
import json
import gzip
from datetime import datetime
import sys
import os

# Add utils to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..'))

# Enhanced dictionary utilities not implemented yet
# Compression is built-in to SmartDictionary (gzip)
# User-friendly formats (CSV, Excel) are planned features
UTILS_AVAILABLE = False


class TranslationDictionaryManager:
    """Manages learning dictionary operations with enhanced format and compression support."""
    
    def __init__(self, parent=None, config_manager=None):
        """Initialize the dictionary manager."""
        self.parent = parent
        self.config_manager = config_manager
        
        # Enhanced utilities not implemented yet
        self.format_handler = None
        self.compressor = None
    
    def export_dictionary(self):
        """Export the learning dictionary with enhanced format and compression support."""
        try:
            # Enhanced file dialog with more formats
            if UTILS_AVAILABLE:
                file_filter = (
                    "JSON files (*.json);;"
                    "CSV files (*.csv);;"
                    "Text files (*.txt);;"
                    "Markdown files (*.md);;"
                    "Compressed JSON (*.json.gz);;"
                    "All files (*.*)"
                )
            else:
                file_filter = "JSON files (*.json);;Text wordbook (*.txt);;All files (*.*)"
            
            # Ask for save location
            file_path, selected_filter = QFileDialog.getSaveFileName(
                self.parent,
                "Export Learning Dictionary",
                "learned_dictionary.json",
                file_filter
            )
            
            if not file_path:
                return
            
            # Get the translation layer's dictionary (NEW SYSTEM)
            main_window = self.parent.window()
            if hasattr(main_window, 'translation_layer'):
                translation_layer = main_window.translation_layer
                
                # Get current language pair
                source_lang = self.config_manager.get_setting('translation.source_language', 'en') if self.config_manager else 'en'
                target_lang = self.config_manager.get_setting('translation.target_language', 'de') if self.config_manager else 'de'
                
                # Use the new export method
                result_path = translation_layer.export_dictionary_wordbook(
                    file_path,
                    source_lang,
                    target_lang
                )
                
                if result_path:
                    QMessageBox.information(
                        self.parent,
                        "Export Successful",
                        f"Dictionary exported successfully!\n\n"
                        f"{source_lang} → {target_lang}\n"
                        f"Saved to: {result_path}"
                    )
                else:
                    QMessageBox.warning(
                        self.parent,
                        "Export Failed",
                        "Failed to export dictionary. Check if dictionary has entries."
                    )
            else:
                QMessageBox.warning(
                    self.parent,
                    "Not Available",
                    "Translation system not initialized."
                )
        except Exception as e:
            QMessageBox.critical(self.parent, "Export Failed", f"Failed to export dictionary:\n\n{e}")
    
    def import_dictionary(self):
        """Import a learning dictionary with enhanced format support."""
        try:
            # Enhanced file dialog with more formats
            if UTILS_AVAILABLE:
                file_filter = (
                    "All supported (*.json *.csv *.txt *.json.gz);;"
                    "JSON files (*.json);;"
                    "CSV files (*.csv);;"
                    "Text files (*.txt);;"
                    "Compressed JSON (*.json.gz);;"
                    "All files (*.*)"
                )
            else:
                file_filter = "JSON files (*.json);;All files (*.*)"
            
            # Ask for file to import
            file_path, _ = QFileDialog.getOpenFileName(
                self.parent,
                "Import Learning Dictionary",
                "",
                file_filter
            )
            
            if not file_path:
                return
            
            # Handle decompression if needed
            actual_file_path = file_path
            temp_decompressed = False
            
            if UTILS_AVAILABLE and self.compressor:
                compression = self.compressor.detect_compression(file_path)
                if compression:
                    # Decompress to temp file
                    success, decompressed_path, stats = self.compressor.decompress_file(
                        file_path,
                        compression='auto'
                    )
                    if success:
                        actual_file_path = decompressed_path
                        temp_decompressed = True
                    else:
                        QMessageBox.critical(
                            self.parent,
                            "Decompression Failed",
                            f"Failed to decompress file:\n\n{stats.get('error', 'Unknown error')}"
                        )
                        return
            
            # Import based on format
            try:
                entries, errors = self._import_with_enhanced_formats(actual_file_path)
                
                # Clean up temp file if created
                if temp_decompressed:
                    try:
                        Path(actual_file_path).unlink()
                    except:
                        pass
                
                if errors:
                    error_msg = "Import completed with errors:\n\n" + "\n".join(errors[:10])
                    if len(errors) > 10:
                        error_msg += f"\n\n... and {len(errors) - 10} more errors"
                    QMessageBox.warning(self.parent, "Import Warnings", error_msg)
                
                if not entries:
                    QMessageBox.warning(
                        self.parent,
                        "No Valid Entries",
                        "No valid dictionary entries found in file."
                    )
                    return
                
                # Convert to internal format and import
                self._import_entries_to_dictionary(entries)
                return
                
            except Exception as e:
                # Fallback to basic JSON import
                if temp_decompressed:
                    try:
                        Path(actual_file_path).unlink()
                    except:
                        pass
                
                # Try basic JSON format
                with open(file_path, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                
                # Validation checks
                validation_errors = []
                
                if not isinstance(data, dict):
                    validation_errors.append("File must contain a JSON object (dictionary)")
                
                if 'translations' not in data:
                    validation_errors.append("Missing 'translations' key")
                
                if 'translations' in data and not isinstance(data['translations'], dict):
                    validation_errors.append("'translations' must be a dictionary")
                
                # Validate translation entries
                if 'translations' in data and isinstance(data['translations'], dict):
                    imported_translations = data['translations']
                    
                    # Check a sample of entries
                    sample_keys = list(imported_translations.keys())[:10]
                    for key in sample_keys:
                        entry = imported_translations[key]
                        
                        if not isinstance(entry, dict):
                            validation_errors.append(f"Entry '{key}' is not a dictionary")
                            break
                        
                        required_fields = ['original', 'translation', 'source_lang', 'target_lang']
                        for field in required_fields:
                            if field not in entry:
                                validation_errors.append(f"Entry '{key}' missing required field: {field}")
                                break
                        
                        if validation_errors:
                            break
                
                # If validation failed, show errors
                if validation_errors:
                    error_msg = "Invalid dictionary format:\n\n" + "\n".join(f"• {err}" for err in validation_errors)
                    error_msg += "\n\nExpected format:\n{\n  \"version\": \"1.0\",\n  \"translations\": {\n    \"key\": {\n      \"original\": \"text\",\n      \"translation\": \"text\",\n      \"source_lang\": \"en\",\n      \"target_lang\": \"de\"\n    }\n  }\n}"
                    QMessageBox.critical(self.parent, "Invalid Format", error_msg)
                    return
                
                # Show validation success and import info
                imported_translations = data['translations']
                total_entries = len(imported_translations)
                
                # Confirm import
                reply = QMessageBox.question(
                    self.parent,
                    "Confirm Import",
                    f"✓ Dictionary format validated successfully!\n\n"
                    f"File contains: {total_entries} translations\n"
                    f"Version: {data.get('version', 'unknown')}\n"
                    f"Last updated: {data.get('last_updated', 'unknown')}\n\n"
                    f"This will merge with your existing dictionary.\n"
                    f"Existing entries will be kept.\n\n"
                    f"Continue?",
                    QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
                    QMessageBox.StandardButton.Yes
                )
                
                if reply == QMessageBox.StandardButton.Yes:
                    # Get the translation layer's dictionary
                    main_window = self.parent.window()
                    if hasattr(main_window, 'translation_layer'):
                        if hasattr(main_window.translation_layer, 'learning_dict'):
                            learning_dict = main_window.translation_layer.learning_dict
                            
                            original_count = len(learning_dict.dictionary)
                            
                            # Merge dictionaries
                            with learning_dict.lock:
                                for key, entry in imported_translations.items():
                                    if key not in learning_dict.dictionary:
                                        learning_dict.dictionary[key] = entry
                                learning_dict.modified = True
                            
                            # Save merged dictionary
                            learning_dict.save()
                            
                            new_count = len(learning_dict.dictionary)
                            added = new_count - original_count
                            
                            QMessageBox.information(
                                self.parent,
                                "Import Successful",
                                f"Dictionary imported successfully!\n\n"
                                f"Added: {added} new translations\n"
                                f"Skipped: {total_entries - added} duplicates\n"
                                f"Total: {new_count} translations"
                            )
                        else:
                            QMessageBox.warning(
                                self.parent,
                                "Not Available",
                                "Learning dictionary not initialized.\nStart translation first."
                            )
                    else:
                        QMessageBox.warning(
                            self.parent,
                            "Not Available",
                            "Translation system not initialized."
                        )
            
            except json.JSONDecodeError as e:
                QMessageBox.critical(
                    self.parent,
                    "Invalid JSON",
                    f"File is not valid JSON:\n\n{e}\n\n"
                    f"Please ensure the file is a properly formatted JSON file."
                )
            except Exception as e:
                QMessageBox.critical(
                    self.parent,
                    "Validation Failed",
                    f"Failed to validate dictionary:\n\n{e}"
                )
        
        except Exception as e:
            QMessageBox.critical(self.parent, "Import Failed", f"Failed to import dictionary:\n\n{e}")
    
    def view_dictionary_stats(self):
        """View learning dictionary statistics."""
        try:
            main_window = self.parent.window()
            if hasattr(main_window, 'translation_layer'):
                if hasattr(main_window.translation_layer, 'learning_dict'):
                    learning_dict = main_window.translation_layer.learning_dict
                    stats = learning_dict.get_stats()
                    
                    # Create stats dialog
                    stats_dialog = QDialog(self.parent)
                    stats_dialog.setWindowTitle("Dictionary Statistics")
                    stats_dialog.setMinimumSize(500, 400)
                    stats_dialog.resize(500, 400)
                    
                    layout = QVBoxLayout(stats_dialog)
                    layout.setContentsMargins(20, 20, 20, 20)
                    layout.setSpacing(15)
                    
                    # Title
                    title = QLabel("📊 Learning Dictionary Statistics")
                    title.setStyleSheet("font-size: 14pt; font-weight: bold;")
                    layout.addWidget(title)
                    
                    # Stats text
                    stats_text = f"""Total Translations: {stats.get('total_entries', 0)}
Total Usage: {stats.get('total_usage', 0)} times
Average Usage: {stats.get('average_usage', 0):.1f} times per translation

Most Used Translations:
"""
                    
                    for i, item in enumerate(stats.get('most_used', [])[:10], 1):
                        stats_text += f"\n{i}. '{item['original']}' → '{item['translation']}' ({item['usage_count']} times)"
                    
                    text_widget = QTextEdit()
                    text_widget.setReadOnly(True)
                    text_widget.setPlainText(stats_text.strip())
                    text_widget.setStyleSheet("font-family: monospace; font-size: 10pt; background-color: #2D2D2D; color: #E0E0E0;")
                    layout.addWidget(text_widget)
                    
                    # Close button
                    close_btn = QPushButton("Close")
                    close_btn.setProperty("class", "action")
                    close_btn.clicked.connect(stats_dialog.accept)
                    layout.addWidget(close_btn)
                    
                    stats_dialog.exec()
                else:
                    QMessageBox.warning(
                        self.parent,
                        "Not Available",
                        "Learning dictionary not initialized.\nStart translation first."
                    )
            else:
                QMessageBox.warning(
                    self.parent,
                    "Not Available",
                    "Translation system not initialized."
                )
        except Exception as e:
            QMessageBox.critical(self.parent, "Error", f"Failed to get statistics:\n\n{e}")
    
    def create_example_dictionary(self):
        """Create an example dictionary file for users to learn the format."""
        if not UTILS_AVAILABLE or not self.format_handler:
            QMessageBox.information(
                self.parent,
                "Not Available",
                "Example dictionary creation requires enhanced utilities.\n"
                "This feature is not available in basic mode."
            )
            return
        
        try:
            # Ask user for format preference
            from PyQt6.QtWidgets import QInputDialog
            
            formats = ["JSON (Recommended)", "CSV (Excel)", "TXT (Simple)", "Markdown"]
            format_choice, ok = QInputDialog.getItem(
                self.parent,
                "Choose Format",
                "Select example dictionary format:",
                formats,
                0,
                False
            )
            
            if not ok:
                return
            
            # Map choice to format
            format_map = {
                "JSON (Recommended)": "json",
                "CSV (Excel)": "csv",
                "TXT (Simple)": "txt",
                "Markdown": "md"
            }
            format_type = format_map.get(format_choice, "json")
            
            # Ask for save location
            default_name = f"example_dictionary.{format_type}"
            file_path, _ = QFileDialog.getSaveFileName(
                self.parent,
                "Save Example Dictionary",
                default_name,
                f"{format_type.upper()} files (*.{format_type});;All files (*.*)"
            )
            
            if not file_path:
                return
            
            # Create example entries
            example_entries = [
                {
                    'source_text': 'Hello',
                    'target_text': 'こんにちは',
                    'source_language': 'en',
                    'target_language': 'ja',
                    'category': 'common',
                    'confidence': 1.0,
                    'tags': ['greeting', 'basic']
                },
                {
                    'source_text': 'Thank you',
                    'target_text': 'ありがとう',
                    'source_language': 'en',
                    'target_language': 'ja',
                    'category': 'common',
                    'confidence': 1.0,
                    'tags': ['greeting', 'polite']
                },
                {
                    'source_text': 'Health',
                    'target_text': '体力',
                    'source_language': 'en',
                    'target_language': 'ja',
                    'category': 'gaming',
                    'confidence': 1.0,
                    'tags': ['rpg', 'stats']
                },
                {
                    'source_text': 'Attack',
                    'target_text': '攻撃',
                    'source_language': 'en',
                    'target_language': 'ja',
                    'category': 'gaming',
                    'confidence': 1.0,
                    'tags': ['rpg', 'combat']
                },
                {
                    'source_text': 'Good morning',
                    'target_text': 'おはよう',
                    'source_language': 'en',
                    'target_language': 'ja',
                    'category': 'common',
                    'confidence': 1.0,
                    'tags': ['greeting', 'morning']
                }
            ]
            
            # Export example
            success = False
            if format_type == 'json':
                success = self.format_handler.export_to_json(example_entries, file_path, pretty=True)
            elif format_type == 'csv':
                success = self.format_handler.export_to_csv(example_entries, file_path, include_metadata=True)
            elif format_type == 'txt':
                success = self.format_handler.export_to_txt(example_entries, file_path, format_style='detailed')
            elif format_type == 'md':
                success = self.format_handler.export_to_txt(example_entries, file_path, format_style='markdown')
            
            if success:
                QMessageBox.information(
                    self.parent,
                    "Example Created",
                    f"Example dictionary created successfully!\n\n"
                    f"File: {file_path}\n"
                    f"Format: {format_type.upper()}\n"
                    f"Entries: {len(example_entries)}\n\n"
                    f"You can now:\n"
                    f"1. Open and edit this file\n"
                    f"2. Add your own translations\n"
                    f"3. Import it back using 'Import Dictionary'"
                )
            else:
                QMessageBox.critical(
                    self.parent,
                    "Creation Failed",
                    "Failed to create example dictionary."
                )
        
        except Exception as e:
            QMessageBox.critical(
                self.parent,
                "Error",
                f"Failed to create example dictionary:\n\n{e}"
            )
    
    def clear_dictionary(self):
        """Clear the learning dictionary."""
        try:
            # Try to use the active dictionary if available
            main_window = self.parent.window()
            if hasattr(main_window, 'translation_layer') and hasattr(main_window.translation_layer, 'learning_dict'):
                learning_dict = main_window.translation_layer.learning_dict
                entry_count = len(learning_dict.dictionary)
                
                # Confirm before clearing
                reply = QMessageBox.question(
                    self.parent,
                    "Confirm Clear",
                    f"⚠️ Warning: This will delete all learned translations!\n\n"
                    f"Current dictionary contains: {entry_count} translations\n\n"
                    f"This action cannot be undone.\n\n"
                    f"Are you sure you want to clear the dictionary?",
                    QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
                    QMessageBox.StandardButton.No
                )
                
                if reply == QMessageBox.StandardButton.Yes:
                    # Clear the dictionary
                    learning_dict.clear()
                    learning_dict.save()
                    
                    QMessageBox.information(
                        self.parent,
                        "Dictionary Cleared",
                        "All learned translations have been deleted.\n\n"
                        "The dictionary will start learning fresh translations."
                    )
            else:
                # Translation system not running - clear the file directly
                cache_dir = Path.home() / '.cache' / 'live_translator'
                dict_path = cache_dir / 'learned_dictionary.json'
                dict_gz_path = cache_dir / 'learned_dictionary.json.gz'
                
                # Check if dictionary files exist
                exists = dict_path.exists() or dict_gz_path.exists()
                
                if not exists:
                    QMessageBox.information(
                        self.parent,
                        "No Dictionary",
                        "No dictionary file found.\n\n"
                        "The dictionary is empty or hasn't been created yet."
                    )
                    return
                
                # Try to count entries
                entry_count = 0
                try:
                    if dict_gz_path.exists():
                        with gzip.open(dict_gz_path, 'rt', encoding='utf-8') as f:
                            data = json.load(f)
                            entry_count = len(data.get('translations', {}))
                    elif dict_path.exists():
                        with open(dict_path, 'r', encoding='utf-8') as f:
                            data = json.load(f)
                            entry_count = len(data.get('translations', {}))
                except:
                    entry_count = "unknown"
                
                # Confirm before clearing
                reply = QMessageBox.question(
                    self.parent,
                    "Confirm Clear",
                    f"⚠️ Warning: This will delete all learned translations!\n\n"
                    f"Dictionary contains: {entry_count} translations\n\n"
                    f"This action cannot be undone.\n\n"
                    f"Are you sure you want to clear the dictionary?",
                    QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
                    QMessageBox.StandardButton.No
                )
                
                if reply == QMessageBox.StandardButton.Yes:
                    # Delete the dictionary files
                    deleted = []
                    if dict_gz_path.exists():
                        dict_gz_path.unlink()
                        deleted.append("learned_dictionary.json.gz")
                    if dict_path.exists():
                        dict_path.unlink()
                        deleted.append("learned_dictionary.json")
                    
                    QMessageBox.information(
                        self.parent,
                        "Dictionary Cleared",
                        f"Dictionary files deleted:\n\n" + "\n".join(f"• {f}" for f in deleted) + "\n\n"
                        "The dictionary will start fresh when you next use translation."
                    )
        
        except Exception as e:
            QMessageBox.critical(self.parent, "Error", f"Failed to clear dictionary:\n\n{e}")
            import traceback
            traceback.print_exc()
    
    def get_dictionary_overview(self, source_lang: str, target_lang: str) -> str:
        """
        Get dictionary overview for current language pair.
        
        Args:
            source_lang: Source language code
            target_lang: Target language code
            
        Returns:
            str: HTML formatted overview text
        """
        try:
            # Get language names
            source_name = self._get_language_name(source_lang)
            target_name = self._get_language_name(target_lang)
            
            # Check if dictionary file exists (try both dev and production paths)
            import os
            from pathlib import Path
            
            dict_paths = [
                Path(f"dev/dictionary/learned_dictionary_{source_lang}_{target_lang}.json.gz"),
                Path(f"dictionary/learned_dictionary_{source_lang}_{target_lang}.json.gz")
            ]
            
            dict_path = None
            for path in dict_paths:
                if path.exists():
                    dict_path = path
                    break
            
            if dict_path:
                # Get file size
                file_size_mb = dict_path.stat().st_size / (1024 * 1024)
                
                # Try to get entry count from the new dictionary engine
                entry_count = "N/A"
                try:
                    main_window = self.parent.window()
                    if hasattr(main_window, 'translation_layer'):
                        dict_engine = main_window.translation_layer._engine_registry.get_engine('dictionary')
                        if dict_engine and hasattr(dict_engine._dictionary, '_dictionaries'):
                            lang_pair = (source_lang, target_lang)
                            if lang_pair in dict_engine._dictionary._dictionaries:
                                entry_count = len(dict_engine._dictionary._dictionaries[lang_pair])
                except:
                    pass
                
                overview_text = f"""
<b>Current Language Pair:</b> {source_name} → {target_name}<br>
<b>Status:</b> ✓ Active<br>
<b>Total Entries:</b> {entry_count}<br>
<b>File Size:</b> {file_size_mb:.2f} MB (compressed)<br>
<b>Location:</b> <code>{dict_path}</code>
                """.strip()
            else:
                overview_text = f"""
<b>Current Language Pair:</b> {source_name} → {target_name}<br>
<b>Status:</b> No dictionary yet<br>
<i>Dictionary will be created automatically when you start translating</i>
                """.strip()
            
            return overview_text
        except Exception as e:
            return f"<b>Error:</b> {str(e)}"
    
    def _get_language_name(self, code: str) -> str:
        """Convert language code to full name."""
        language_names = {
            'en': 'English', 'de': 'German', 'es': 'Spanish', 'fr': 'French',
            'it': 'Italian', 'ja': 'Japanese', 'zh': 'Chinese', 'ko': 'Korean',
            'ru': 'Russian', 'pt': 'Portuguese', 'ar': 'Arabic', 'hi': 'Hindi'
        }
        return language_names.get(code, code.upper())
    
    def _convert_to_standard_format(self, dictionary: dict) -> list:
        """Convert internal dictionary format to standard format for export."""
        entries = []
        for key, entry in dictionary.items():
            standard_entry = {
                'source_text': entry.get('original', ''),
                'target_text': entry.get('translation', ''),
                'source_language': entry.get('source_lang', ''),
                'target_language': entry.get('target_lang', ''),
                'category': entry.get('category', 'user'),
                'confidence': entry.get('confidence', 1.0),
                'tags': entry.get('tags', [])
            }
            entries.append(standard_entry)
        return entries
    
    def _export_with_enhanced_formats(self, file_path: str, file_ext: str, 
                                     entries: list, total_entries: int) -> bool:
        """Export using enhanced format handlers."""
        try:
            # Handle compression
            compress = file_path.endswith('.gz')
            actual_path = file_path[:-3] if compress else file_path
            actual_ext = Path(actual_path).suffix.lower()
            
            # Export based on format
            success = False
            if actual_ext == '.json':
                success = self.format_handler.export_to_json(entries, actual_path, pretty=True)
            elif actual_ext == '.csv':
                success = self.format_handler.export_to_csv(entries, actual_path, include_metadata=True)
            elif actual_ext == '.txt':
                success = self.format_handler.export_to_txt(entries, actual_path, format_style='detailed')
            elif actual_ext == '.md':
                success = self.format_handler.export_to_txt(entries, actual_path, format_style='markdown')
            
            if not success:
                return False
            
            # Compress if requested
            if compress:
                comp_success, comp_path, stats = self.compressor.compress_file(
                    actual_path, 
                    file_path, 
                    compression='gzip'
                )
                
                if comp_success:
                    # Remove uncompressed file
                    Path(actual_path).unlink()
                    
                    QMessageBox.information(
                        self.parent,
                        "Export Successful",
                        f"Dictionary exported and compressed!\n\n"
                        f"File: {file_path}\n"
                        f"Format: {actual_ext.upper()}\n"
                        f"Original: {stats['original_size'] / 1024:.1f} KB\n"
                        f"Compressed: {stats['compressed_size'] / 1024:.1f} KB\n"
                        f"Compression: {stats['compression_ratio']:.1f}x\n"
                        f"Space saved: {stats['space_saved_percent']:.1f}%\n"
                        f"Total entries: {total_entries}"
                    )
                else:
                    QMessageBox.warning(
                        self.parent,
                        "Compression Failed",
                        f"Export succeeded but compression failed.\n"
                        f"Uncompressed file saved at: {actual_path}"
                    )
            else:
                file_size = Path(actual_path).stat().st_size
                QMessageBox.information(
                    self.parent,
                    "Export Successful",
                    f"Dictionary exported successfully!\n\n"
                    f"File: {file_path}\n"
                    f"Format: {actual_ext.upper()}\n"
                    f"Size: {file_size / 1024:.1f} KB\n"
                    f"Total entries: {total_entries}"
                )
            
            return True
            
        except Exception as e:
            QMessageBox.critical(
                self.parent,
                "Export Failed",
                f"Failed to export with enhanced formats:\n\n{e}"
            )
            return False
    
    def _export_basic_format(self, file_path: str, file_ext: str, learning_dict):
        """Fallback to basic export format."""
        if file_ext == '.txt':
            # Export as wordbook (human-readable text)
            learning_dict.export_wordbook(Path(file_path))
            QMessageBox.information(
                self.parent,
                "Export Successful",
                f"Wordbook exported successfully!\n\n{file_path}"
            )
        else:
            # Export as JSON (human-readable, uncompressed)
            data = {
                'version': '1.0',
                'exported': datetime.now().isoformat(),
                'total_entries': len(learning_dict.dictionary),
                'compressed': False,
                'translations': learning_dict.dictionary
            }
            
            # Write uncompressed JSON with indentation
            with open(file_path, 'w', encoding='utf-8') as f:
                json.dump(data, f, indent=2, ensure_ascii=False)
            
            # Show file size
            file_size = Path(file_path).stat().st_size
            
            QMessageBox.information(
                self.parent,
                "Export Successful",
                f"Dictionary exported successfully!\n\n"
                f"File: {file_path}\n"
                f"Format: Human-readable JSON\n"
                f"Size: {file_size / 1024:.1f} KB\n"
                f"Total entries: {len(learning_dict.dictionary)}"
            )
    
    def _import_with_enhanced_formats(self, file_path: str):
        """Import using enhanced format handlers."""
        file_ext = Path(file_path).suffix.lower()
        
        entries = []
        errors = []
        
        if file_ext == '.json':
            entries, errors = self.format_handler.import_from_json(file_path)
        elif file_ext == '.csv':
            entries, errors = self.format_handler.import_from_csv(file_path)
        elif file_ext == '.txt':
            entries, errors = self.format_handler.import_from_txt(file_path)
        else:
            raise ValueError(f"Unsupported file format: {file_ext}")
        
        return entries, errors
    
    def _import_entries_to_dictionary(self, entries: list):
        """Import entries into the learning dictionary."""
        main_window = self.parent.window()
        if not hasattr(main_window, 'translation_layer'):
            QMessageBox.warning(
                self.parent,
                "Not Available",
                "Translation system not initialized."
            )
            return
        
        if not hasattr(main_window.translation_layer, 'learning_dict'):
            QMessageBox.warning(
                self.parent,
                "Not Available",
                "Learning dictionary not initialized.\nStart translation first."
            )
            return
        
        learning_dict = main_window.translation_layer.learning_dict
        original_count = len(learning_dict.dictionary)
        
        # Convert entries to internal format and merge
        added = 0
        with learning_dict.lock:
            for entry in entries:
                # Create key for dictionary
                key = f"{entry['source_text']}_{entry['source_language']}_{entry['target_language']}"
                
                if key not in learning_dict.dictionary:
                    # Convert to internal format
                    internal_entry = {
                        'original': entry['source_text'],
                        'translation': entry['target_text'],
                        'source_lang': entry['source_language'],
                        'target_lang': entry['target_language'],
                        'category': entry.get('category', 'user'),
                        'confidence': entry.get('confidence', 1.0),
                        'tags': entry.get('tags', []),
                        'usage_count': 0
                    }
                    learning_dict.dictionary[key] = internal_entry
                    added += 1
            
            learning_dict.modified = True
        
        # Save merged dictionary
        learning_dict.save()
        
        new_count = len(learning_dict.dictionary)
        skipped = len(entries) - added
        
        QMessageBox.information(
            self.parent,
            "Import Successful",
            f"Dictionary imported successfully!\n\n"
            f"Added: {added} new translations\n"
            f"Skipped: {skipped} duplicates\n"
            f"Total: {new_count} translations"
        )
