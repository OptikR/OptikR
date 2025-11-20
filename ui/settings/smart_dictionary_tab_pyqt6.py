"""
Smart Dictionary Settings Tab - PyQt6 Implementation
Dedicated tab for managing the intelligent learning dictionary system.
"""

from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QFormLayout, QGroupBox,
    QLabel, QComboBox, QPushButton, QListWidget, QListWidgetItem,
    QTableWidget, QTableWidgetItem, QHeaderView, QMessageBox,
    QProgressBar, QCheckBox
)
from PyQt6.QtCore import Qt, pyqtSignal, QSettings
from PyQt6.QtGui import QColor
from ui.custom_spinbox import CustomSpinBox, CustomDoubleSpinBox
from pathlib import Path

# Import custom scroll area
from .scroll_area_no_wheel import ScrollAreaNoWheel


class SmartDictionaryTab(QWidget):
    """Smart Dictionary settings - learning dictionary management and configuration."""
    
    # Signal emitted when any setting changes
    settingChanged = pyqtSignal()
    
    def __init__(self, config_manager=None, pipeline=None, parent=None):
        """Initialize the Smart Dictionary settings tab."""
        super().__init__(parent)
        
        self.config_manager = config_manager
        self.pipeline = pipeline
        
        # Track original loaded state to detect real changes
        self._original_state = {}
        
        # Track selected dictionary file path
        self._selected_dict_path = None
        
        # Dictionary widgets
        self.language_pair_combo = None
        self.language_pair_table = None
        self.dict_entries_label = None
        self.dict_usage_label = None
        self.dict_avg_usage_label = None
        self.dict_file_size_label = None
        self.dict_hit_rate_label = None
        self.most_used_list = None
        
        # Settings widgets
        self.auto_learn_check = None
        self.min_confidence_spin = None
        self.max_entries_spin = None
        
        # Initialize UI
        self._init_ui()
    
    def _init_ui(self):
        """Initialize the UI."""
        # Create main layout
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.setSpacing(0)
        
        # Create scroll area
        scroll_area = ScrollAreaNoWheel()
        scroll_area.setWidgetResizable(True)
        scroll_area.setFrameShape(ScrollAreaNoWheel.Shape.NoFrame)
        scroll_area.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        scroll_area.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAsNeeded)
        
        # Create content widget
        content_widget = QWidget()
        content_layout = QVBoxLayout(content_widget)
        content_layout.setContentsMargins(5, 5, 5, 5)
        content_layout.setSpacing(10)
        
        # Create sections
        self._create_overview_section(content_layout)
        self._create_language_pair_selector(content_layout)
        self._create_statistics_section(content_layout)
        self._create_most_used_section(content_layout)
        self._create_actions_section(content_layout)
        self._create_all_pairs_table(content_layout)
        self._create_settings_section(content_layout)
        
        # Add stretch at the end
        content_layout.addStretch()
        
        # Set content widget to scroll area
        scroll_area.setWidget(content_widget)
        
        # Add scroll area to main layout
        main_layout.addWidget(scroll_area)
    
    def _create_label(self, text: str, bold: bool = False) -> QLabel:
        """Create a label with consistent styling."""
        label = QLabel(text)
        if bold:
            label.setStyleSheet("font-weight: 600; font-size: 9pt;")
        else:
            label.setStyleSheet("font-size: 9pt;")
        return label
    
    def on_change(self):
        """Called when any setting changes."""
        self.settingChanged.emit()
    
    def _create_overview_section(self, parent_layout):
        """Create overview section explaining the smart dictionary."""
        group = QGroupBox("📚 Smart Dictionary Overview")
        layout = QVBoxLayout(group)
        layout.setSpacing(10)
        layout.setContentsMargins(15, 20, 15, 15)
        
        overview = QLabel(
            "<b>What is the Smart Dictionary?</b><br>"
            "The Smart Dictionary learns from your translations and stores them for instant reuse. "
            "When you translate the same text again, it retrieves the translation instantly (0.01s) "
            "instead of calling the AI translation engine (3-5s).<br><br>"
            "<b>Benefits:</b><br>"
            "• 100x faster for repeated text<br>"
            "• Consistent translations<br>"
            "• Works offline after learning<br>"
            "• Organized by language pairs<br>"
            "• Persistent across sessions"
        )
        overview.setWordWrap(True)
        overview.setStyleSheet("font-size: 9pt; padding: 10px;")
        layout.addWidget(overview)
        
        # Enable/Disable note
        note = QLabel(
            "💡 <b>Note:</b> To enable/disable the Smart Dictionary plugin, go to "
            "<b>Pipeline Management tab → Translation Stage → Learning Dictionary</b>"
        )
        note.setWordWrap(True)
        note.setStyleSheet(
            "color: #2196F3; font-size: 9pt; padding: 10px; "
            "background-color: rgba(33, 150, 243, 0.1); border-radius: 4px; "
            "border-left: 4px solid #2196F3; margin-top: 10px;"
        )
        layout.addWidget(note)
        
        parent_layout.addWidget(group)
    
    def _create_language_pair_selector(self, parent_layout):
        """Create language pair selector."""
        group = QGroupBox("🌐 Select Language Pair")
        layout = QHBoxLayout(group)
        layout.setSpacing(10)
        layout.setContentsMargins(15, 20, 15, 15)
        
        selector_label = self._create_label("Language Pair:", bold=True)
        layout.addWidget(selector_label)
        
        self.language_pair_combo = QComboBox()
        self.language_pair_combo.setMinimumWidth(300)
        self.language_pair_combo.currentIndexChanged.connect(self._on_language_pair_changed)
        layout.addWidget(self.language_pair_combo)
        
        refresh_btn = QPushButton("🔄 Refresh")
        refresh_btn.setProperty("class", "action")
        refresh_btn.setMinimumWidth(100)
        refresh_btn.clicked.connect(self._refresh_language_pairs)
        layout.addWidget(refresh_btn)
        
        layout.addStretch()
        parent_layout.addWidget(group)
    
    def _create_statistics_section(self, parent_layout):
        """Create statistics section for selected dictionary."""
        group = QGroupBox("📊 Dictionary Statistics")
        layout = QFormLayout(group)
        layout.setSpacing(8)
        layout.setContentsMargins(15, 20, 15, 15)
        
        self.dict_entries_label = QLabel("0")
        self.dict_entries_label.setStyleSheet("font-weight: 600; font-size: 10pt;")
        layout.addRow("Total Entries:", self.dict_entries_label)
        
        self.dict_usage_label = QLabel("0 lookups")
        layout.addRow("Total Usage:", self.dict_usage_label)
        
        self.dict_avg_usage_label = QLabel("0.0 times per entry")
        layout.addRow("Average Usage:", self.dict_avg_usage_label)
        
        self.dict_file_size_label = QLabel("No dictionary file yet")
        layout.addRow("File Size:", self.dict_file_size_label)
        
        self.dict_hit_rate_label = QLabel("N/A")
        layout.addRow("Hit Rate:", self.dict_hit_rate_label)
        
        parent_layout.addWidget(group)
    
    def _create_most_used_section(self, parent_layout):
        """Create most used translations section."""
        group = QGroupBox("⭐ Most Used Translations")
        layout = QVBoxLayout(group)
        layout.setSpacing(10)
        layout.setContentsMargins(15, 20, 15, 15)
        
        self.most_used_list = QListWidget()
        self.most_used_list.setMaximumHeight(120)
        layout.addWidget(self.most_used_list)
        
        parent_layout.addWidget(group)
    
    def _create_actions_section(self, parent_layout):
        """Create actions section for dictionary management."""
        group = QGroupBox("🔧 Dictionary Actions")
        layout = QHBoxLayout(group)
        layout.setSpacing(10)
        layout.setContentsMargins(15, 20, 15, 15)
        
        # Edit Dictionary button
        edit_btn = QPushButton("📝 Edit Dictionary")
        edit_btn.setProperty("class", "action")
        edit_btn.setMinimumWidth(140)
        edit_btn.setToolTip("Open dictionary editor to browse, edit, and delete entries")
        edit_btn.clicked.connect(self._open_dictionary_editor)
        layout.addWidget(edit_btn)
        
        # Create Example button
        example_btn = QPushButton("📚 Create Example")
        example_btn.setProperty("class", "action")
        example_btn.setMinimumWidth(130)
        example_btn.setToolTip("Create an example dictionary with sample translations")
        example_btn.clicked.connect(self._create_example_dictionary)
        layout.addWidget(example_btn)
        
        # Export button
        export_btn = QPushButton("📤 Export")
        export_btn.setProperty("class", "action")
        export_btn.setMinimumWidth(90)
        export_btn.setToolTip("Export the selected dictionary")
        export_btn.clicked.connect(self._export_dictionary)
        layout.addWidget(export_btn)
        
        # Import button
        import_btn = QPushButton("📥 Import")
        import_btn.setProperty("class", "action")
        import_btn.setMinimumWidth(90)
        import_btn.clicked.connect(self._import_dictionary)
        layout.addWidget(import_btn)
        
        # Clear button
        clear_btn = QPushButton("🗑️ Clear")
        clear_btn.setProperty("class", "action")
        clear_btn.setMinimumWidth(80)
        clear_btn.setToolTip("Clear only the selected language pair dictionary")
        clear_btn.clicked.connect(self._clear_dictionary)
        layout.addWidget(clear_btn)
        
        # Clean Bad Entries button
        clean_btn = QPushButton("🧹 Clean Bad Entries")
        clean_btn.setProperty("class", "action")
        clean_btn.setMinimumWidth(150)
        clean_btn.setToolTip("Remove entries with OCR errors (| character, etc.)")
        clean_btn.clicked.connect(self._clean_bad_entries)
        layout.addWidget(clean_btn)
        
        layout.addStretch()
        parent_layout.addWidget(group)
    
    def _create_all_pairs_table(self, parent_layout):
        """Create table showing all available language pairs."""
        group = QGroupBox("📋 All Language Pairs")
        layout = QVBoxLayout(group)
        layout.setSpacing(10)
        layout.setContentsMargins(15, 20, 15, 15)
        
        self.language_pair_table = QTableWidget()
        self.language_pair_table.setColumnCount(5)
        self.language_pair_table.setHorizontalHeaderLabels(["Active", "Name", "Language Pair", "Entries", "Size"])
        self.language_pair_table.setMaximumHeight(150)
        self.language_pair_table.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
        self.language_pair_table.setSelectionMode(QTableWidget.SelectionMode.SingleSelection)
        self.language_pair_table.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        
        # Set column widths
        header = self.language_pair_table.horizontalHeader()
        header.setSectionResizeMode(0, QHeaderView.ResizeMode.Fixed)      # Active - fixed width
        header.setSectionResizeMode(1, QHeaderView.ResizeMode.Stretch)    # Name - stretches
        header.setSectionResizeMode(2, QHeaderView.ResizeMode.Stretch)    # Language Pair - stretches
        header.setSectionResizeMode(3, QHeaderView.ResizeMode.Fixed)      # Entries - fixed width
        header.setSectionResizeMode(4, QHeaderView.ResizeMode.Fixed)      # Size - fixed width
        
        # Set fixed column widths
        self.language_pair_table.setColumnWidth(0, 60)   # Active checkbox
        self.language_pair_table.setColumnWidth(3, 100)  # Entries
        self.language_pair_table.setColumnWidth(4, 100)  # Size
        
        layout.addWidget(self.language_pair_table)
        
        parent_layout.addWidget(group)
    
    def _create_settings_section(self, parent_layout):
        """Create dictionary settings section."""
        group = QGroupBox("⚙️ Dictionary Settings")
        layout = QFormLayout(group)
        layout.setSpacing(10)
        layout.setContentsMargins(15, 20, 15, 15)
        
        # Auto-learn checkbox
        self.auto_learn_check = QCheckBox("Automatically learn new translations")
        self.auto_learn_check.setChecked(True)
        self.auto_learn_check.stateChanged.connect(self.on_change)
        layout.addRow("Auto-Learn:", self.auto_learn_check)
        
        # Learn single words checkbox (NEW)
        self.learn_words_check = QCheckBox("Learn single words")
        self.learn_words_check.setChecked(True)
        self.learn_words_check.setToolTip("Save individual words to dictionary (e.g., 'hello' → 'hallo')")
        self.learn_words_check.stateChanged.connect(self.on_change)
        layout.addRow("", self.learn_words_check)
        
        # Learn sentences checkbox (NEW)
        self.learn_sentences_check = QCheckBox("Learn sentences")
        self.learn_sentences_check.setChecked(True)
        self.learn_sentences_check.setToolTip("Save complete sentences to dictionary (e.g., 'How are you?' → 'Wie geht es dir?')")
        self.learn_sentences_check.stateChanged.connect(self.on_change)
        layout.addRow("", self.learn_sentences_check)
        
        learn_help = QLabel("Choose what to save: single words, sentences, or both")
        learn_help.setStyleSheet("color: #666666; font-size: 8pt; font-style: italic;")
        layout.addRow("", learn_help)
        
        # Word extraction on stop checkbox
        self.extract_words_on_stop_check = QCheckBox("Extract words when stopping translation")
        self.extract_words_on_stop_check.setChecked(True)
        self.extract_words_on_stop_check.setToolTip(
            "After stopping translation, offer to extract and translate individual words from sentences.\n"
            "⚠️ This improves translation quality but takes extra time.\n"
            "Example: 'Hello world' → saves 'hello' and 'world' separately"
        )
        self.extract_words_on_stop_check.stateChanged.connect(self.on_change)
        layout.addRow("Word Extraction:", self.extract_words_on_stop_check)
        
        extract_help = QLabel("⚠️ Improves translation quality but takes time (2-3 sec per word)")
        extract_help.setStyleSheet("color: #FF8C00; font-size: 8pt; font-style: italic; font-weight: bold;")
        layout.addRow("", extract_help)
        
        # Create grid layout for spinboxes (matching ROI Detection Settings style)
        from PyQt6.QtWidgets import QGridLayout, QWidget
        spinbox_container = QWidget()
        spinbox_grid = QGridLayout(spinbox_container)
        spinbox_grid.setHorizontalSpacing(8)
        spinbox_grid.setVerticalSpacing(8)
        spinbox_grid.setContentsMargins(0, 0, 0, 0)
        spinbox_grid.setColumnStretch(2, 1)
        
        # Minimum confidence
        self.min_confidence_spin = CustomDoubleSpinBox()
        self.min_confidence_spin.setRange(0.0, 1.0)
        self.min_confidence_spin.setSingleStep(0.1)
        self.min_confidence_spin.setValue(0.7)
        self.min_confidence_spin.setDecimals(2)
        self.min_confidence_spin.valueChanged.connect(self.on_change)
        
        spinbox_grid.addWidget(QLabel("Min Confidence:"), 0, 0)
        spinbox_grid.addWidget(self.min_confidence_spin, 0, 1)
        
        # Maximum entries
        self.max_entries_spin = CustomSpinBox()
        self.max_entries_spin.setRange(100, 999999)
        self.max_entries_spin.setSingleStep(1000)
        self.max_entries_spin.setValue(999999)
        self.max_entries_spin.setSuffix(" entries")
        self.max_entries_spin.setSpecialValueText("Unlimited")
        self.max_entries_spin.valueChanged.connect(self.on_change)
        
        spinbox_grid.addWidget(QLabel("Max Entries:"), 1, 0)
        spinbox_grid.addWidget(self.max_entries_spin, 1, 1)
        
        layout.addRow(spinbox_container)
        
        # Help text
        help_text = QLabel(
            "   • Min Confidence: Only learn translations with confidence above this threshold\n"
            "   • Max Entries: No artificial limits - grow your dictionary as large as you need!"
        )
        help_text.setWordWrap(True)
        help_text.setStyleSheet("color: #666666; font-size: 8pt; font-style: italic; margin-top: 5px;")
        layout.addRow("", help_text)
        
        parent_layout.addWidget(group)
    
    def _on_language_pair_changed(self, index):
        """Handle language pair selection change."""
        # Update statistics for selected pair
        self._update_statistics()
        self.on_change()
    
    def _refresh_language_pairs(self):
        """Refresh the language pairs list by scanning dictionary directory."""
        try:
            from pathlib import Path
            from app.utils.path_utils import get_app_path
            
            # Get dictionary directory
            dict_dir = Path(get_app_path("dictionary"))
            
            if not dict_dir.exists():
                self.language_pair_combo.clear()
                self.language_pair_combo.addItem("No dictionaries found")
                return
            
            # Scan for dictionary files (exclude backups)
            all_dict_files = list(dict_dir.glob("learned_dictionary_*_*.json.gz"))
            
            # Filter out backup files
            dict_files = [f for f in all_dict_files if 'backup' not in f.name.lower()]
            
            if not dict_files:
                self.language_pair_combo.clear()
                self.language_pair_combo.addItem("No dictionaries found")
                print(f"[SMART DICT] No valid dictionaries found in {dict_dir}")
                print(f"[SMART DICT] Found {len(all_dict_files)} files total, but all were backups")
                return
            
            # Parse language pairs from filenames
            language_pairs = []
            for dict_file in dict_files:
                try:
                    # Parse: learned_dictionary_en_de.json.gz
                    filename = dict_file.stem  # Remove .gz
                    if filename.endswith('.json'):
                        filename = filename[:-5]  # Remove .json
                    
                    parts = filename.split('_')
                    if len(parts) >= 4:  # learned_dictionary_SOURCE_TARGET
                        source_lang = parts[2]
                        target_lang = parts[3]
                        
                        # Skip if language codes contain dots or other invalid characters
                        if '.' in source_lang or '.' in target_lang:
                            print(f"[SMART DICT] Skipping invalid filename: {dict_file.name}")
                            continue
                        
                        # Create display name
                        display_name = f"{source_lang.upper()} → {target_lang.upper()}"
                        language_pairs.append((display_name, source_lang, target_lang, str(dict_file)))
                        print(f"[SMART DICT] Found dictionary: {display_name} at {dict_file}")
                except Exception as e:
                    print(f"[SMART DICT] Failed to parse {dict_file.name}: {e}")
            
            # Update combo box (block signals to avoid multiple updates)
            self.language_pair_combo.blockSignals(True)
            self.language_pair_combo.clear()
            for display_name, source_lang, target_lang, file_path in language_pairs:
                self.language_pair_combo.addItem(display_name, (source_lang, target_lang, file_path))
            self.language_pair_combo.blockSignals(False)
            
            # Update statistics for first pair
            if language_pairs:
                self._update_statistics()
            
            # Update table
            self._update_language_pairs_table()
            
            print(f"[SMART DICT] Found {len(language_pairs)} language pairs")
            
        except Exception as e:
            print(f"[ERROR] Failed to refresh language pairs: {e}")
            import traceback
            traceback.print_exc()
            QMessageBox.warning(self, "Error", f"Failed to refresh language pairs:\n{e}")
    
    def _update_statistics(self):
        """Update statistics for selected language pair."""
        try:
            import gzip
            import json
            
            print(f"[SMART DICT] _update_statistics called")
            print(f"[SMART DICT] Combo box has {self.language_pair_combo.count()} items")
            print(f"[SMART DICT] Current index: {self.language_pair_combo.currentIndex()}")
            
            # Get selected language pair
            current_data = self.language_pair_combo.currentData()
            print(f"[SMART DICT] current_data: {current_data}")
            print(f"[SMART DICT] current_data type: {type(current_data)}")
            
            if not current_data:
                print("[SMART DICT] No current data, setting zeros")
                self.dict_entries_label.setText("0")
                self.dict_usage_label.setText("0 lookups")
                self.dict_avg_usage_label.setText("0.0 times per entry")
                self.dict_file_size_label.setText("No dictionary file yet")
                self.dict_hit_rate_label.setText("N/A")
                return
            
            source_lang, target_lang, file_path = current_data
            print(f"[SMART DICT] Loading dictionary: {source_lang} → {target_lang}")
            print(f"[SMART DICT] File path: {file_path}")
            
            # Load dictionary file
            dict_path = Path(file_path)
            print(f"[SMART DICT] Checking if file exists: {dict_path}")
            print(f"[SMART DICT] File exists: {dict_path.exists()}")
            
            if not dict_path.exists():
                print(f"[SMART DICT] Dictionary file does not exist!")
                self.dict_entries_label.setText("0")
                self.dict_usage_label.setText("0 lookups")
                self.dict_avg_usage_label.setText("0.0 times per entry")
                self.dict_file_size_label.setText("No dictionary file")
                self.dict_hit_rate_label.setText("N/A")
                return
            
            print(f"[SMART DICT] Dictionary file exists, reading...")
            
            # Read dictionary
            with gzip.open(dict_path, 'rt', encoding='utf-8') as f:
                data = json.load(f)
            
            # Extract statistics
            translations = data.get('translations', {})
            metadata = data.get('metadata', {})
            
            total_entries = len(translations)
            total_usage = sum(entry.get('usage_count', 0) for entry in translations.values())
            avg_usage = total_usage / total_entries if total_entries > 0 else 0.0
            
            # File size
            file_size_bytes = dict_path.stat().st_size
            if file_size_bytes < 1024:
                file_size_str = f"{file_size_bytes} bytes"
            elif file_size_bytes < 1024 * 1024:
                file_size_str = f"{file_size_bytes / 1024:.1f} KB"
            else:
                file_size_str = f"{file_size_bytes / (1024 * 1024):.1f} MB"
            
            # Hit rate from metadata
            hit_rate = metadata.get('hit_rate', 0.0)
            hit_rate_str = f"{hit_rate * 100:.1f}%" if hit_rate > 0 else "N/A"
            
            # Update labels
            self.dict_entries_label.setText(f"{total_entries:,}")
            self.dict_usage_label.setText(f"{total_usage:,} lookups")
            self.dict_avg_usage_label.setText(f"{avg_usage:.1f} times per entry")
            self.dict_file_size_label.setText(file_size_str)
            self.dict_hit_rate_label.setText(hit_rate_str)
            
            # Update most used list
            self._update_most_used_list(translations)
            
            print(f"[SMART DICT] Statistics updated: {total_entries} entries, {total_usage} lookups")
            
        except Exception as e:
            print(f"[ERROR] Failed to update statistics: {e}")
            import traceback
            traceback.print_exc()
    
    def _update_most_used_list(self, translations: dict):
        """Update the most used translations list."""
        try:
            self.most_used_list.clear()
            
            # Sort by usage count
            sorted_entries = sorted(
                translations.items(),
                key=lambda x: x[1].get('usage_count', 0),
                reverse=True
            )
            
            # Show top 10
            for source_text, entry in sorted_entries[:10]:
                translation = entry.get('translation', '')
                usage_count = entry.get('usage_count', 0)
                
                # Truncate long text
                if len(source_text) > 40:
                    source_text = source_text[:37] + "..."
                if len(translation) > 40:
                    translation = translation[:37] + "..."
                
                item_text = f"{source_text} → {translation} ({usage_count}x)"
                self.most_used_list.addItem(item_text)
            
        except Exception as e:
            print(f"[ERROR] Failed to update most used list: {e}")
    
    def _open_dictionary_editor(self):
        """Open dictionary editor dialog."""
        try:
            from ui.dialogs.dictionary_editor_dialog import DictionaryEditorDialog
            
            # Get selected language pair
            current_data = self.language_pair_combo.currentData()
            if not current_data:
                QMessageBox.warning(self, "No Selection", "Please select a language pair to edit.")
                return
            
            source_lang, target_lang, file_path = current_data
            
            editor = DictionaryEditorDialog(
                parent=self, 
                config_manager=self.config_manager,
                dictionary_path=file_path,
                source_lang=source_lang,
                target_lang=target_lang
            )
            editor.exec()
            
            # Refresh UI after editing
            self._refresh_language_pairs()
            
        except ImportError as e:
            # Graceful fallback - offer alternative
            QMessageBox.information(
                self,
                "Feature Coming Soon",
                "Dictionary editor is not yet available.\n\n"
                "<b>Alternative:</b>\n"
                "1. Click 'Export' to save dictionary as JSON\n"
                "2. Edit the JSON file in any text editor\n"
                "3. Click 'Import' to load your changes\n\n"
                "This gives you full control over dictionary entries."
            )
        except Exception as e:
            print(f"[ERROR] Failed to open dictionary editor: {e}")
            import traceback
            traceback.print_exc()
            QMessageBox.warning(
                self,
                "Error",
                f"Failed to open dictionary editor:\n{e}"
            )
    
    def _create_example_dictionary(self):
        """Create an example dictionary with sample translations."""
        try:
            import gzip
            import json
            from datetime import datetime
            from app.utils.path_utils import get_app_path
            from PyQt6.QtWidgets import QInputDialog
            
            # Ask user for language pair
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
            
            # Create example translations
            example_translations = {
                "Hello": {
                    "translation": "Hallo",
                    "confidence": 0.95,
                    "usage_count": 5,
                    "created_at": datetime.now().isoformat(),
                    "last_used": datetime.now().isoformat()
                },
                "Good morning": {
                    "translation": "Guten Morgen",
                    "confidence": 0.92,
                    "usage_count": 3,
                    "created_at": datetime.now().isoformat(),
                    "last_used": datetime.now().isoformat()
                },
                "Thank you": {
                    "translation": "Danke",
                    "confidence": 0.98,
                    "usage_count": 8,
                    "created_at": datetime.now().isoformat(),
                    "last_used": datetime.now().isoformat()
                },
                "How are you?": {
                    "translation": "Wie geht es dir?",
                    "confidence": 0.89,
                    "usage_count": 2,
                    "created_at": datetime.now().isoformat(),
                    "last_used": datetime.now().isoformat()
                },
                "Goodbye": {
                    "translation": "Auf Wiedersehen",
                    "confidence": 0.94,
                    "usage_count": 4,
                    "created_at": datetime.now().isoformat(),
                    "last_used": datetime.now().isoformat()
                }
            }
            
            # Create dictionary data
            dict_data = {
                "metadata": {
                    "source_language": source_lang,
                    "target_language": target_lang,
                    "created_at": datetime.now().isoformat(),
                    "updated_at": datetime.now().isoformat(),
                    "version": "1.0",
                    "total_entries": len(example_translations),
                    "hit_rate": 0.75
                },
                "translations": example_translations
            }
            
            # Create dictionary file
            dict_dir = Path(get_app_path("dictionary"))
            dict_dir.mkdir(parents=True, exist_ok=True)
            
            dict_filename = f"learned_dictionary_{source_lang}_{target_lang}.json.gz"
            dict_path = dict_dir / dict_filename
            
            # Check if file exists
            if dict_path.exists():
                reply = QMessageBox.question(
                    self,
                    "File Exists",
                    f"Dictionary for {source_lang} → {target_lang} already exists.\n\n"
                    "Do you want to overwrite it?",
                    QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
                    QMessageBox.StandardButton.No
                )
                
                if reply != QMessageBox.StandardButton.Yes:
                    return
            
            # Save dictionary
            with gzip.open(dict_path, 'wt', encoding='utf-8') as f:
                json.dump(dict_data, f, ensure_ascii=False, indent=2)
            
            # Refresh UI
            self._refresh_language_pairs()
            
            QMessageBox.information(
                self,
                "Example Created",
                f"Example dictionary created successfully!\n\n"
                f"Language Pair: {source_lang} → {target_lang}\n"
                f"Sample Entries: {len(example_translations)}\n"
                f"File: {dict_filename}"
            )
            
        except Exception as e:
            print(f"[ERROR] Failed to create example dictionary: {e}")
            import traceback
            traceback.print_exc()
            QMessageBox.critical(self, "Creation Error", f"Failed to create example dictionary:\n{e}")
    
    def _export_dictionary(self):
        """Export selected dictionary to a JSON file."""
        try:
            from PyQt6.QtWidgets import QFileDialog
            import gzip
            import json
            
            # Get selected language pair
            current_data = self.language_pair_combo.currentData()
            if not current_data:
                QMessageBox.warning(self, "No Selection", "Please select a language pair to export.")
                return
            
            source_lang, target_lang, file_path = current_data
            
            # Check if dictionary file exists
            dict_path = Path(file_path)
            if not dict_path.exists():
                QMessageBox.warning(self, "File Not Found", "Dictionary file not found.")
                return
            
            # Choose export location
            export_path, _ = QFileDialog.getSaveFileName(
                self,
                "Export Dictionary",
                f"dictionary_{source_lang}_{target_lang}.json",
                "JSON Files (*.json);;All Files (*)"
            )
            
            if not export_path:
                return
            
            # Read compressed dictionary
            with gzip.open(dict_path, 'rt', encoding='utf-8') as f:
                data = json.load(f)
            
            # Write uncompressed JSON for easy editing
            with open(export_path, 'w', encoding='utf-8') as f:
                json.dump(data, f, indent=2, ensure_ascii=False)
            
            QMessageBox.information(
                self,
                "Export Complete",
                f"Dictionary exported to:\n{export_path}\n\n"
                f"Entries: {len(data.get('translations', {})):,}"
            )
            
        except Exception as e:
            print(f"[ERROR] Failed to export dictionary: {e}")
            import traceback
            traceback.print_exc()
            QMessageBox.critical(self, "Export Error", f"Failed to export dictionary:\n{e}")
    
    def _import_dictionary(self):
        """Import dictionary from various formats and convert to smart dict format."""
        try:
            from PyQt6.QtWidgets import QFileDialog, QInputDialog
            import gzip
            import json
            from datetime import datetime
            from app.utils.path_utils import get_app_path
            
            # Choose import file
            import_path, _ = QFileDialog.getOpenFileName(
                self,
                "Import Dictionary",
                "",
                "JSON Files (*.json);;Compressed JSON (*.json.gz);;All Files (*)"
            )
            
            if not import_path:
                return
            
            # Read import file
            import_path = Path(import_path)
            
            if import_path.suffix == '.gz':
                with gzip.open(import_path, 'rt', encoding='utf-8') as f:
                    data = json.load(f)
            else:
                with open(import_path, 'r', encoding='utf-8') as f:
                    data = json.load(f)
            
            # ALWAYS ask user for language pair (don't auto-detect)
            # Get default from current selection if available
            default_source = 'en'
            default_target = 'de'
            
            current_data = self.language_pair_combo.currentData()
            if current_data:
                default_source, default_target, _ = current_data
            
            source_lang, ok1 = QInputDialog.getText(
                self, 
                "Source Language", 
                "Enter source language code for imported dictionary:",
                text=default_source
            )
            if not ok1 or not source_lang:
                return
            
            target_lang, ok2 = QInputDialog.getText(
                self, 
                "Target Language", 
                "Enter target language code for imported dictionary:",
                text=default_target
            )
            if not ok2 or not target_lang:
                return
            
            # Detect and convert format
            converted_data = self._convert_to_smart_dict_format(data)
            
            if not converted_data:
                QMessageBox.warning(
                    self,
                    "Invalid Format",
                    "Could not recognize dictionary format.\n\n"
                    "Supported formats:\n"
                    "• Smart Dictionary format (with 'translations' key)\n"
                    "• Simple key-value pairs (e.g., {'hello': 'hallo'})\n"
                    "• Array format ([{'source': 'hello', 'target': 'hallo'}])"
                )
                return
            
            # Set user-specified languages
            converted_data['source_language'] = source_lang
            converted_data['target_language'] = target_lang
            
            # Create dictionary file path
            dict_dir = Path(get_app_path("dictionary"))
            dict_dir.mkdir(parents=True, exist_ok=True)
            
            dict_filename = f"learned_dictionary_{source_lang}_{target_lang}.json.gz"
            dict_path = dict_dir / dict_filename
            
            # Check if file exists
            merge_mode = False
            if dict_path.exists():
                reply = QMessageBox.question(
                    self,
                    "File Exists",
                    f"Dictionary for {source_lang} → {target_lang} already exists.\n\n"
                    "Do you want to merge with existing dictionary?",
                    QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No | QMessageBox.StandardButton.Cancel,
                    QMessageBox.StandardButton.Yes
                )
                
                if reply == QMessageBox.StandardButton.Cancel:
                    return
                elif reply == QMessageBox.StandardButton.Yes:
                    merge_mode = True
                    # Load existing
                    with gzip.open(dict_path, 'rt', encoding='utf-8') as f:
                        existing_data = json.load(f)
                    
                    # Merge translations
                    existing_translations = existing_data.get('translations', {})
                    new_translations = converted_data['translations']
                    
                    merged_count = 0
                    for key, value in new_translations.items():
                        if key not in existing_translations:
                            existing_translations[key] = value
                            merged_count += 1
                    
                    converted_data['translations'] = existing_translations
                    converted_data['total_entries'] = len(existing_translations)
            
            # Save dictionary in smart dict format
            final_data = {
                'version': '1.0',
                'last_updated': datetime.now().isoformat(),
                'total_entries': converted_data['total_entries'],
                'compressed': True,
                'source_language': source_lang,
                'target_language': target_lang,
                'translations': converted_data['translations']
            }
            
            with gzip.open(dict_path, 'wt', encoding='utf-8') as f:
                json.dump(final_data, f, indent=2, ensure_ascii=False)
            
            # Refresh UI
            self._refresh_language_pairs()
            
            entry_count = len(final_data['translations'])
            QMessageBox.information(
                self,
                "Import Complete",
                f"✅ Dictionary imported successfully!\n\n"
                f"Language pair: {source_lang} → {target_lang}\n"
                f"Entries: {entry_count:,}\n"
                f"{'Merged with existing dictionary' if merge_mode else 'New dictionary created'}\n\n"
                f"All imported entries have full confidence (1.0) as they are user-trusted."
            )
            
        except Exception as e:
            print(f"[ERROR] Failed to import dictionary: {e}")
            import traceback
            traceback.print_exc()
            QMessageBox.critical(self, "Import Error", f"Failed to import dictionary:\n{e}")
    
    def _convert_to_smart_dict_format(self, data):
        """Convert various dictionary formats to smart dict format."""
        from datetime import datetime
        
        try:
            translations = {}
            source_lang = 'unknown'
            target_lang = 'unknown'
            
            # Format 1: Smart Dictionary format (already correct)
            if 'translations' in data and isinstance(data['translations'], dict):
                translations = data['translations']
                source_lang = data.get('source_language', 'unknown')
                target_lang = data.get('target_language', 'unknown')
                
                # Ensure all entries have required fields
                for key, entry in translations.items():
                    if 'confidence' not in entry:
                        entry['confidence'] = 1.0  # Full confidence for imported
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
                        'confidence': 1.0,  # Full confidence for imported
                        'last_used': datetime.now().isoformat(),
                        'engine': 'imported'
                    }
            
            # Format 3: Array format [{'source': 'hello', 'target': 'hallo'}, ...]
            elif isinstance(data, list):
                for item in data:
                    if isinstance(item, dict):
                        # Try different key names
                        original = item.get('source') or item.get('original') or item.get('text') or item.get('from')
                        translation = item.get('target') or item.get('translation') or item.get('to')
                        
                        if original and translation:
                            translations[original] = {
                                'original': original,
                                'translation': translation,
                                'usage_count': item.get('usage_count', 1),
                                'confidence': item.get('confidence', 1.0),  # Full confidence if missing
                                'last_used': item.get('last_used', datetime.now().isoformat()),
                                'engine': item.get('engine', 'imported')
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
                'total_entries': len(translations)
            }
            
        except Exception as e:
            print(f"[ERROR] Format conversion failed: {e}")
            return None
    
    def _clear_dictionary(self):
        """Clear selected dictionary."""
        try:
            # Get selected language pair
            current_data = self.language_pair_combo.currentData()
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
                QMessageBox.StandardButton.No
            )
            
            if reply == QMessageBox.StandardButton.Yes:
                # Delete the dictionary file
                dict_path = Path(file_path)
                if dict_path.exists():
                    dict_path.unlink()
                    
                    # Refresh UI
                    self._refresh_language_pairs()
                    
                    QMessageBox.information(
                        self,
                        "Dictionary Cleared",
                        f"Dictionary for {source_lang} → {target_lang} has been cleared."
                    )
                else:
                    QMessageBox.warning(
                        self,
                        "File Not Found",
                        "Dictionary file not found. It may have already been deleted."
                    )
                    # Refresh UI anyway
                    self._refresh_language_pairs()
            
        except Exception as e:
            print(f"[ERROR] Failed to clear dictionary: {e}")
            import traceback
            traceback.print_exc()
            QMessageBox.critical(self, "Clear Error", f"Failed to clear dictionary:\n{e}")
    
    def _clean_bad_entries(self):
        """Remove entries with OCR errors (| character, etc.) from selected dictionary."""
        try:
            # Get selected language pair
            current_data = self.language_pair_combo.currentData()
            if not current_data:
                QMessageBox.warning(self, "No Selection", "Please select a language pair to clean.")
                return
            
            source_lang, target_lang, file_path = current_data
            dict_path = Path(file_path)
            
            if not dict_path.exists():
                QMessageBox.warning(self, "File Not Found", "Dictionary file not found.")
                return
            
            # Load dictionary
            import gzip
            import json
            from datetime import datetime
            
            with gzip.open(dict_path, 'rt', encoding='utf-8') as f:
                data = json.load(f)
            
            translations = data.get('translations', {})
            original_count = len(translations)
            
            # Find bad entries (containing | or other OCR errors)
            bad_patterns = ['|', '¦', '│']  # Pipe and similar characters
            bad_entries = []
            
            for key, entry in list(translations.items()):
                original = entry.get('original', '')
                # Check if original text contains bad characters
                if any(pattern in original for pattern in bad_patterns):
                    bad_entries.append((key, original, entry.get('translation', '')))
            
            if not bad_entries:
                QMessageBox.information(
                    self,
                    "No Bad Entries",
                    f"No entries with OCR errors found in {source_lang} → {target_lang} dictionary.\n\n"
                    "The dictionary is clean!"
                )
                return
            
            # Show confirmation with details
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
                QMessageBox.StandardButton.Yes
            )
            
            if reply == QMessageBox.StandardButton.Yes:
                # Create backup
                backup_path = dict_path.with_suffix('.json.gz.backup')
                import shutil
                shutil.copy2(dict_path, backup_path)
                
                # Remove bad entries
                for key, _, _ in bad_entries:
                    del translations[key]
                
                # Update metadata
                data['total_entries'] = len(translations)
                data['last_updated'] = datetime.now().isoformat()
                
                # Save cleaned dictionary
                with gzip.open(dict_path, 'wt', encoding='utf-8') as f:
                    json.dump(data, f, indent=2, ensure_ascii=False)
                
                # Refresh UI
                self._refresh_language_pairs()
                
                QMessageBox.information(
                    self,
                    "Cleaning Complete",
                    f"Removed {len(bad_entries)} bad entries from {source_lang} → {target_lang}.\n\n"
                    f"Original entries: {original_count}\n"
                    f"Cleaned entries: {len(translations)}\n\n"
                    f"Backup saved to:\n{backup_path.name}"
                )
            
        except Exception as e:
            print(f"[ERROR] Failed to clean bad entries: {e}")
            import traceback
            traceback.print_exc()
            QMessageBox.critical(self, "Clean Error", f"Failed to clean bad entries:\n{e}")
    
    def _restore_table_column_widths(self):
        """Restore saved column widths from QSettings."""
        settings = QSettings("OptikR", "SmartDictionary")
        for i in range(5):
            width = settings.value(f"column_{i}_width", None)
            if width:
                self.language_pair_table.setColumnWidth(i, int(width))
    
    def _save_table_column_widths(self):
        """Save column widths to QSettings."""
        settings = QSettings("OptikR", "SmartDictionary")
        for i in range(5):
            width = self.language_pair_table.columnWidth(i)
            settings.setValue(f"column_{i}_width", width)
    
    def _update_language_pairs_table(self):
        """Update the language pairs table with all available dictionaries."""
        try:
            from app.utils.path_utils import get_app_path
            import gzip
            import json
            
            # Clear table
            self.language_pair_table.setRowCount(0)
            
            # Get dictionary directory
            dict_dir = Path(get_app_path("dictionary"))
            
            if not dict_dir.exists():
                return
            
            # Scan for dictionary files (exclude backups)
            all_dict_files = list(dict_dir.glob("learned_dictionary_*_*.json.gz"))
            dict_files = [f for f in all_dict_files if 'backup' not in f.name.lower()]
            
            if not dict_files:
                return
            
            # Process each dictionary file
            for row, dict_file in enumerate(dict_files):
                try:
                    # Parse filename
                    filename = dict_file.stem  # Remove .gz
                    if filename.endswith('.json'):
                        filename = filename[:-5]  # Remove .json
                    
                    parts = filename.split('_')
                    if len(parts) < 4:
                        continue
                    
                    source_lang = parts[2]
                    target_lang = parts[3]
                    
                    # Skip if language codes contain dots or other invalid characters
                    if '.' in source_lang or '.' in target_lang:
                        continue
                    
                    # Read dictionary for stats
                    with gzip.open(dict_file, 'rt', encoding='utf-8') as f:
                        data = json.load(f)
                    
                    translations = data.get('translations', {})
                    total_entries = len(translations)
                    
                    # File size
                    file_size_bytes = dict_file.stat().st_size
                    if file_size_bytes < 1024:
                        file_size_str = f"{file_size_bytes} B"
                    elif file_size_bytes < 1024 * 1024:
                        file_size_str = f"{file_size_bytes / 1024:.1f} KB"
                    else:
                        file_size_str = f"{file_size_bytes / (1024 * 1024):.1f} MB"
                    
                    # Add row to table
                    self.language_pair_table.insertRow(row)
                    
                    # Active column (checkbox)
                    active_item = QTableWidgetItem()
                    active_item.setFlags(Qt.ItemFlag.ItemIsUserCheckable | Qt.ItemFlag.ItemIsEnabled)
                    active_item.setCheckState(Qt.CheckState.Checked)  # Assume active
                    self.language_pair_table.setItem(row, 0, active_item)
                    
                    # Name column
                    name_item = QTableWidgetItem(f"{source_lang.upper()}-{target_lang.upper()}")
                    self.language_pair_table.setItem(row, 1, name_item)
                    
                    # Language Pair column
                    pair_item = QTableWidgetItem(f"{source_lang} → {target_lang}")
                    self.language_pair_table.setItem(row, 2, pair_item)
                    
                    # Entries column
                    entries_item = QTableWidgetItem(f"{total_entries:,}")
                    entries_item.setTextAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)
                    self.language_pair_table.setItem(row, 3, entries_item)
                    
                    # Size column
                    size_item = QTableWidgetItem(file_size_str)
                    size_item.setTextAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)
                    self.language_pair_table.setItem(row, 4, size_item)
                    
                except Exception as e:
                    print(f"[ERROR] Failed to process {dict_file.name}: {e}")
            
            print(f"[SMART DICT] Table updated with {len(dict_files)} dictionaries")
            
        except Exception as e:
            print(f"[ERROR] Failed to update language pairs table: {e}")
            import traceback
            traceback.print_exc()
    
    def load_config(self):
        """Load configuration from config manager."""
        if not self.config_manager:
            return
        
        try:
            # Load dictionary settings
            auto_learn = self.config_manager.get_setting('dictionary.auto_learn', True)
            learn_words = self.config_manager.get_setting('dictionary.learn_words', True)
            learn_sentences = self.config_manager.get_setting('dictionary.learn_sentences', True)
            extract_words_on_stop = self.config_manager.get_setting('dictionary.extract_words_on_stop', True)
            min_confidence = self.config_manager.get_setting('dictionary.min_confidence', 0.7)
            max_entries = self.config_manager.get_setting('dictionary.max_entries', 999999)
            
            self.auto_learn_check.setChecked(auto_learn)
            self.learn_words_check.setChecked(learn_words)
            self.learn_sentences_check.setChecked(learn_sentences)
            self.extract_words_on_stop_check.setChecked(extract_words_on_stop)
            self.min_confidence_spin.setValue(min_confidence)
            self.max_entries_spin.setValue(max_entries)
            
            # Refresh language pairs
            self._refresh_language_pairs()
            
            # Save original state
            self._original_state = self._get_current_state()
            
            print("[INFO] Smart Dictionary settings loaded")
            
        except Exception as e:
            print(f"[ERROR] Failed to load Smart Dictionary settings: {e}")
            import traceback
            traceback.print_exc()
    
    def save_config(self):
        """Save configuration to config manager."""
        if not self.config_manager:
            return
        
        try:
            # Save dictionary settings
            self.config_manager.set_setting('dictionary.auto_learn', self.auto_learn_check.isChecked())
            self.config_manager.set_setting('dictionary.learn_words', self.learn_words_check.isChecked())
            self.config_manager.set_setting('dictionary.learn_sentences', self.learn_sentences_check.isChecked())
            self.config_manager.set_setting('dictionary.extract_words_on_stop', self.extract_words_on_stop_check.isChecked())
            self.config_manager.set_setting('dictionary.min_confidence', self.min_confidence_spin.value())
            self.config_manager.set_setting('dictionary.max_entries', self.max_entries_spin.value())
            
            # Save the configuration file
            if hasattr(self.config_manager, 'save_config'):
                self.config_manager.save_config()
            elif hasattr(self.config_manager, 'save_configuration'):
                config_dict = self.config_manager._config_to_dict(self.config_manager._config)
                self.config_manager.save_configuration(config_dict)
            
            # Apply settings to running pipeline (if available)
            self._apply_settings_to_pipeline()
            
            # Update original state
            self._original_state = self._get_current_state()
            
            print("[INFO] Smart Dictionary settings saved to disk")
            
        except Exception as e:
            print(f"[ERROR] Failed to save Smart Dictionary settings: {e}")
            import traceback
            traceback.print_exc()
    
    def _apply_settings_to_pipeline(self):
        """Apply settings to running pipeline's SmartDictionary instance."""
        try:
            if not self.pipeline:
                print("[SMART DICT] No pipeline available, settings will apply on next restart")
                return
            
            # Try to access SmartDictionary through translation layer
            if hasattr(self.pipeline, 'translation_layer'):
                translation_layer = self.pipeline.translation_layer
                
                # Check if translation layer has smart_dictionary
                if hasattr(translation_layer, 'smart_dictionary'):
                    smart_dict = translation_layer.smart_dictionary
                    
                    # Apply auto-learn setting
                    if hasattr(smart_dict, 'set_auto_learn'):
                        smart_dict.set_auto_learn(self.auto_learn_check.isChecked())
                        print(f"[SMART DICT] Applied auto_learn: {self.auto_learn_check.isChecked()}")
                    elif hasattr(smart_dict, 'auto_learn'):
                        smart_dict.auto_learn = self.auto_learn_check.isChecked()
                        print(f"[SMART DICT] Applied auto_learn: {self.auto_learn_check.isChecked()}")
                    
                    # Apply min confidence setting
                    if hasattr(smart_dict, 'set_min_confidence'):
                        smart_dict.set_min_confidence(self.min_confidence_spin.value())
                        print(f"[SMART DICT] Applied min_confidence: {self.min_confidence_spin.value()}")
                    elif hasattr(smart_dict, 'min_confidence'):
                        smart_dict.min_confidence = self.min_confidence_spin.value()
                        print(f"[SMART DICT] Applied min_confidence: {self.min_confidence_spin.value()}")
                    
                    # Apply max entries setting
                    if hasattr(smart_dict, 'set_max_entries'):
                        smart_dict.set_max_entries(self.max_entries_spin.value())
                        print(f"[SMART DICT] Applied max_entries: {self.max_entries_spin.value()}")
                    elif hasattr(smart_dict, 'max_entries'):
                        smart_dict.max_entries = self.max_entries_spin.value()
                        print(f"[SMART DICT] Applied max_entries: {self.max_entries_spin.value()}")
                    
                    print("[SMART DICT] Settings applied to running pipeline successfully")
                else:
                    print("[SMART DICT] Translation layer has no smart_dictionary attribute")
            else:
                print("[SMART DICT] Pipeline has no translation_layer attribute")
                
        except Exception as e:
            print(f"[SMART DICT] Failed to apply settings to pipeline: {e}")
            # Don't show error to user - settings are saved and will apply on restart
            import traceback
            traceback.print_exc()
    
    def _get_current_state(self):
        """Get current state of all settings."""
        state = {}
        if self.auto_learn_check:
            state['auto_learn'] = self.auto_learn_check.isChecked()
        if self.learn_words_check:
            state['learn_words'] = self.learn_words_check.isChecked()
        if self.learn_sentences_check:
            state['learn_sentences'] = self.learn_sentences_check.isChecked()
        if self.min_confidence_spin:
            state['min_confidence'] = self.min_confidence_spin.value()
        if self.max_entries_spin:
            state['max_entries'] = self.max_entries_spin.value()
        return state
    
    def validate(self) -> bool:
        """Validate settings."""
        # All settings have valid ranges, no specific validation needed
        return True
