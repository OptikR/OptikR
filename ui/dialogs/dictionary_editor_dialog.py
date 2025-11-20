"""
Dictionary Editor Dialog

Enhanced editor for Smart Dictionary with:
- Search functionality
- Filter by word/sentence mode
- Edit and delete entries
- Bulk operations
"""

from PyQt6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QLineEdit, QTableWidget, QTableWidgetItem, QHeaderView,
    QMessageBox, QComboBox, QCheckBox, QGroupBox, QFormLayout
)
from PyQt6.QtCore import Qt, pyqtSignal
from PyQt6.QtGui import QColor
from pathlib import Path
import gzip
import json
from datetime import datetime


class DictionaryEditorDialog(QDialog):
    """Enhanced dictionary editor with search and filtering."""
    
    # Signal emitted when dictionary is modified
    dictionaryModified = pyqtSignal()
    
    def __init__(self, parent=None, config_manager=None, dictionary_path=None, 
                 source_lang="en", target_lang="de"):
        """
        Initialize dictionary editor.
        
        Args:
            parent: Parent widget
            config_manager: Configuration manager
            dictionary_path: Path to dictionary file
            source_lang: Source language code
            target_lang: Target language code
        """
        super().__init__(parent)
        
        self.config_manager = config_manager
        self.dictionary_path = Path(dictionary_path) if dictionary_path else None
        self.source_lang = source_lang
        self.target_lang = target_lang
        
        # Dictionary data
        self.dictionary_data = {}
        self.filtered_entries = []
        self.modified = False
        
        # Initialize UI
        self._init_ui()
        
        # Load dictionary
        if self.dictionary_path and self.dictionary_path.exists():
            self._load_dictionary()
    
    def _init_ui(self):
        """Initialize the UI."""
        self.setWindowTitle(f"Dictionary Editor - {self.source_lang} → {self.target_lang}")
        self.setMinimumSize(900, 600)
        
        # Main layout
        layout = QVBoxLayout(self)
        layout.setSpacing(10)
        layout.setContentsMargins(15, 15, 15, 15)
        
        # Create sections
        self._create_header_section(layout)
        self._create_filter_section(layout)
        self._create_table_section(layout)
        self._create_actions_section(layout)
        self._create_button_section(layout)
    
    def _create_header_section(self, parent_layout):
        """Create header with statistics."""
        header_layout = QHBoxLayout()
        
        title = QLabel(f"<b>Dictionary Editor</b> - {self.source_lang.upper()} → {self.target_lang.upper()}")
        title.setStyleSheet("font-size: 12pt;")
        header_layout.addWidget(title)
        
        header_layout.addStretch()
        
        self.stats_label = QLabel("0 entries")
        self.stats_label.setStyleSheet("font-size: 10pt; color: #666666;")
        header_layout.addWidget(self.stats_label)
        
        parent_layout.addLayout(header_layout)
    
    def _create_filter_section(self, parent_layout):
        """Create filter and search section."""
        group = QGroupBox("🔍 Search & Filter")
        layout = QHBoxLayout(group)
        layout.setSpacing(10)
        
        # Search box
        search_label = QLabel("Search:")
        layout.addWidget(search_label)
        
        self.search_box = QLineEdit()
        self.search_box.setPlaceholderText("Search source or translation text...")
        self.search_box.textChanged.connect(self._apply_filters)
        layout.addWidget(self.search_box, 1)
        
        # Mode filter
        mode_label = QLabel("Mode:")
        layout.addWidget(mode_label)
        
        self.mode_combo = QComboBox()
        self.mode_combo.addItems(["All", "Words Only", "Sentences Only"])
        self.mode_combo.setToolTip("Filter by entry type")
        self.mode_combo.currentIndexChanged.connect(self._apply_filters)
        layout.addWidget(self.mode_combo)
        
        # Sort by
        sort_label = QLabel("Sort:")
        layout.addWidget(sort_label)
        
        self.sort_combo = QComboBox()
        self.sort_combo.addItems(["Usage (High to Low)", "Usage (Low to High)", 
                                  "Alphabetical (A-Z)", "Alphabetical (Z-A)",
                                  "Confidence (High to Low)", "Confidence (Low to High)"])
        self.sort_combo.currentIndexChanged.connect(self._apply_filters)
        layout.addWidget(self.sort_combo)
        
        # Clear search button
        clear_btn = QPushButton("Clear")
        clear_btn.clicked.connect(self._clear_search)
        layout.addWidget(clear_btn)
        
        parent_layout.addWidget(group)
    
    def _create_table_section(self, parent_layout):
        """Create table for dictionary entries."""
        self.table = QTableWidget()
        self.table.setColumnCount(6)
        self.table.setHorizontalHeaderLabels([
            "Source Text", "Translation", "Type", "Usage", "Confidence", "Last Used"
        ])
        
        # Set column widths
        header = self.table.horizontalHeader()
        header.setSectionResizeMode(0, QHeaderView.ResizeMode.Stretch)  # Source
        header.setSectionResizeMode(1, QHeaderView.ResizeMode.Stretch)  # Translation
        header.setSectionResizeMode(2, QHeaderView.ResizeMode.Fixed)    # Type
        header.setSectionResizeMode(3, QHeaderView.ResizeMode.Fixed)    # Usage
        header.setSectionResizeMode(4, QHeaderView.ResizeMode.Fixed)    # Confidence
        header.setSectionResizeMode(5, QHeaderView.ResizeMode.Fixed)    # Last Used
        
        self.table.setColumnWidth(2, 100)  # Type
        self.table.setColumnWidth(3, 80)   # Usage
        self.table.setColumnWidth(4, 100)  # Confidence
        self.table.setColumnWidth(5, 120)  # Last Used
        
        # Enable sorting
        self.table.setSortingEnabled(False)  # We handle sorting manually
        
        # Selection
        self.table.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
        self.table.setSelectionMode(QTableWidget.SelectionMode.ExtendedSelection)
        
        # Double-click to edit
        self.table.itemDoubleClicked.connect(self._edit_entry)
        
        parent_layout.addWidget(self.table)
    
    def _create_actions_section(self, parent_layout):
        """Create action buttons section."""
        actions_layout = QHBoxLayout()
        
        # Edit button
        edit_btn = QPushButton("✏️ Edit Selected")
        edit_btn.setToolTip("Edit the selected entry")
        edit_btn.clicked.connect(self._edit_selected)
        actions_layout.addWidget(edit_btn)
        
        # Delete button
        delete_btn = QPushButton("🗑️ Delete Selected")
        delete_btn.setToolTip("Delete selected entries")
        delete_btn.clicked.connect(self._delete_selected)
        actions_layout.addWidget(delete_btn)
        
        # Add button
        add_btn = QPushButton("➕ Add Entry")
        add_btn.setToolTip("Add a new dictionary entry")
        add_btn.clicked.connect(self._add_entry)
        actions_layout.addWidget(add_btn)
        
        actions_layout.addStretch()
        
        # Export filtered button
        export_btn = QPushButton("📤 Export Filtered")
        export_btn.setToolTip("Export currently filtered entries")
        export_btn.clicked.connect(self._export_filtered)
        actions_layout.addWidget(export_btn)
        
        parent_layout.addLayout(actions_layout)
    
    def _create_button_section(self, parent_layout):
        """Create dialog buttons."""
        button_layout = QHBoxLayout()
        
        button_layout.addStretch()
        
        # Save button
        save_btn = QPushButton("💾 Save Changes")
        save_btn.setProperty("class", "action")
        save_btn.setMinimumWidth(120)
        save_btn.clicked.connect(self._save_changes)
        button_layout.addWidget(save_btn)
        
        # Close button
        close_btn = QPushButton("Close")
        close_btn.setMinimumWidth(100)
        close_btn.clicked.connect(self._close_dialog)
        button_layout.addWidget(close_btn)
        
        parent_layout.addLayout(button_layout)
    
    def _load_dictionary(self):
        """Load dictionary from file."""
        try:
            with gzip.open(self.dictionary_path, 'rt', encoding='utf-8') as f:
                self.dictionary_data = json.load(f)
            
            # Update UI
            self._apply_filters()
            self._update_stats()
            
            print(f"[DICT EDITOR] Loaded {len(self.dictionary_data.get('translations', {}))} entries")
            
        except Exception as e:
            print(f"[ERROR] Failed to load dictionary: {e}")
            QMessageBox.critical(self, "Load Error", f"Failed to load dictionary:\n{e}")
    
    def _apply_filters(self):
        """Apply search and filter to dictionary entries."""
        try:
            translations = self.dictionary_data.get('translations', {})
            
            # Get filter criteria
            search_text = self.search_box.text().lower()
            mode = self.mode_combo.currentText()
            sort_mode = self.sort_combo.currentText()
            
            # Filter entries
            filtered = []
            
            for source_text, entry in translations.items():
                translation = entry.get('translation', '')
                
                # Apply search filter
                if search_text:
                    if search_text not in source_text.lower() and search_text not in translation.lower():
                        continue
                
                # Apply mode filter
                if mode == "Words Only":
                    # Single word if no spaces
                    if ' ' in source_text.strip() or ' ' in translation.strip():
                        continue
                elif mode == "Sentences Only":
                    # Sentence if has spaces or punctuation
                    if ' ' not in source_text.strip() and ' ' not in translation.strip():
                        continue
                
                # Determine type
                if ' ' in source_text.strip() or any(p in source_text for p in '.!?,;:'):
                    entry_type = "Sentence"
                else:
                    entry_type = "Word"
                
                filtered.append({
                    'source': source_text,
                    'translation': translation,
                    'type': entry_type,
                    'usage': entry.get('usage_count', 0),
                    'confidence': entry.get('confidence', 0.0),
                    'last_used': entry.get('last_used', '')
                })
            
            # Apply sorting
            if sort_mode == "Usage (High to Low)":
                filtered.sort(key=lambda x: x['usage'], reverse=True)
            elif sort_mode == "Usage (Low to High)":
                filtered.sort(key=lambda x: x['usage'])
            elif sort_mode == "Alphabetical (A-Z)":
                filtered.sort(key=lambda x: x['source'].lower())
            elif sort_mode == "Alphabetical (Z-A)":
                filtered.sort(key=lambda x: x['source'].lower(), reverse=True)
            elif sort_mode == "Confidence (High to Low)":
                filtered.sort(key=lambda x: x['confidence'], reverse=True)
            elif sort_mode == "Confidence (Low to High)":
                filtered.sort(key=lambda x: x['confidence'])
            
            self.filtered_entries = filtered
            
            # Update table
            self._update_table()
            
        except Exception as e:
            print(f"[ERROR] Failed to apply filters: {e}")
    
    def _update_table(self):
        """Update table with filtered entries."""
        try:
            self.table.setRowCount(0)
            
            for row, entry in enumerate(self.filtered_entries):
                self.table.insertRow(row)
                
                # Source text
                source_item = QTableWidgetItem(entry['source'])
                self.table.setItem(row, 0, source_item)
                
                # Translation
                translation_item = QTableWidgetItem(entry['translation'])
                self.table.setItem(row, 1, translation_item)
                
                # Type
                type_item = QTableWidgetItem(entry['type'])
                type_item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
                if entry['type'] == "Word":
                    type_item.setForeground(QColor("#2196F3"))
                else:
                    type_item.setForeground(QColor("#4CAF50"))
                self.table.setItem(row, 2, type_item)
                
                # Usage
                usage_item = QTableWidgetItem(f"{entry['usage']}")
                usage_item.setTextAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)
                self.table.setItem(row, 3, usage_item)
                
                # Confidence
                conf_item = QTableWidgetItem(f"{entry['confidence']:.2f}")
                conf_item.setTextAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)
                self.table.setItem(row, 4, conf_item)
                
                # Last used
                last_used = entry['last_used']
                if last_used:
                    try:
                        dt = datetime.fromisoformat(last_used)
                        last_used_str = dt.strftime("%Y-%m-%d %H:%M")
                    except:
                        last_used_str = "Unknown"
                else:
                    last_used_str = "Never"
                
                last_used_item = QTableWidgetItem(last_used_str)
                last_used_item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
                self.table.setItem(row, 5, last_used_item)
            
            # Update stats
            self._update_stats()
            
        except Exception as e:
            print(f"[ERROR] Failed to update table: {e}")
    
    def _update_stats(self):
        """Update statistics label."""
        total = len(self.dictionary_data.get('translations', {}))
        filtered = len(self.filtered_entries)
        
        if filtered == total:
            self.stats_label.setText(f"{total:,} entries")
        else:
            self.stats_label.setText(f"{filtered:,} of {total:,} entries")
    
    def _clear_search(self):
        """Clear search and filters."""
        self.search_box.clear()
        self.mode_combo.setCurrentIndex(0)
        self.sort_combo.setCurrentIndex(0)
    
    def _edit_entry(self, item):
        """Edit entry (double-click handler)."""
        self._edit_selected()
    
    def _edit_selected(self):
        """Edit selected entry."""
        selected_rows = self.table.selectionModel().selectedRows()
        
        if not selected_rows:
            QMessageBox.warning(self, "No Selection", "Please select an entry to edit.")
            return
        
        if len(selected_rows) > 1:
            QMessageBox.warning(self, "Multiple Selection", "Please select only one entry to edit.")
            return
        
        row = selected_rows[0].row()
        entry = self.filtered_entries[row]
        
        # Open edit dialog
        from ui.dialogs.dictionary_entry_edit_dialog import DictionaryEntryEditDialog
        
        dialog = DictionaryEntryEditDialog(
            parent=self,
            source_text=entry['source'],
            translation=entry['translation'],
            confidence=entry['confidence'],
            usage_count=entry['usage']
        )
        
        if dialog.exec() == QDialog.DialogCode.Accepted:
            # Update entry
            translations = self.dictionary_data.get('translations', {})
            old_source = entry['source']
            
            # Get updated values
            new_source = dialog.source_edit.text()
            new_translation = dialog.translation_edit.text()
            new_confidence = dialog.confidence_spin.value()
            
            # Remove old entry if source changed
            if new_source != old_source and old_source in translations:
                del translations[old_source]
            
            # Update or add entry
            translations[new_source] = {
                'translation': new_translation,
                'confidence': new_confidence,
                'usage_count': entry['usage'],
                'last_used': entry['last_used'],
                'created_at': translations.get(old_source, {}).get('created_at', datetime.now().isoformat())
            }
            
            self.modified = True
            self._apply_filters()
    
    def _delete_selected(self):
        """Delete selected entries."""
        selected_rows = self.table.selectionModel().selectedRows()
        
        if not selected_rows:
            QMessageBox.warning(self, "No Selection", "Please select entries to delete.")
            return
        
        reply = QMessageBox.question(
            self,
            "Confirm Delete",
            f"Are you sure you want to delete {len(selected_rows)} entry(ies)?\n\n"
            "This action cannot be undone.",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            QMessageBox.StandardButton.No
        )
        
        if reply == QMessageBox.StandardButton.Yes:
            translations = self.dictionary_data.get('translations', {})
            
            for row in selected_rows:
                entry = self.filtered_entries[row.row()]
                source_text = entry['source']
                
                if source_text in translations:
                    del translations[source_text]
            
            self.modified = True
            self._apply_filters()
    
    def _add_entry(self):
        """Add new entry."""
        from ui.dialogs.dictionary_entry_edit_dialog import DictionaryEntryEditDialog
        
        dialog = DictionaryEntryEditDialog(parent=self)
        
        if dialog.exec() == QDialog.DialogCode.Accepted:
            translations = self.dictionary_data.get('translations', {})
            
            source_text = dialog.source_edit.text()
            translation = dialog.translation_edit.text()
            confidence = dialog.confidence_spin.value()
            
            if source_text in translations:
                reply = QMessageBox.question(
                    self,
                    "Entry Exists",
                    f"An entry for '{source_text}' already exists.\n\n"
                    "Do you want to overwrite it?",
                    QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
                    QMessageBox.StandardButton.No
                )
                
                if reply != QMessageBox.StandardButton.Yes:
                    return
            
            translations[source_text] = {
                'translation': translation,
                'confidence': confidence,
                'usage_count': 0,
                'last_used': datetime.now().isoformat(),
                'created_at': datetime.now().isoformat()
            }
            
            self.modified = True
            self._apply_filters()
    
    def _export_filtered(self):
        """Export filtered entries."""
        from PyQt6.QtWidgets import QFileDialog
        
        if not self.filtered_entries:
            QMessageBox.warning(self, "No Entries", "No entries to export.")
            return
        
        export_path, _ = QFileDialog.getSaveFileName(
            self,
            "Export Filtered Entries",
            f"filtered_{self.source_lang}_{self.target_lang}.json",
            "JSON Files (*.json);;All Files (*)"
        )
        
        if not export_path:
            return
        
        # Create export data
        export_data = {
            'metadata': {
                'source_language': self.source_lang,
                'target_language': self.target_lang,
                'exported_at': datetime.now().isoformat(),
                'total_entries': len(self.filtered_entries)
            },
            'translations': {}
        }
        
        translations = self.dictionary_data.get('translations', {})
        for entry in self.filtered_entries:
            source = entry['source']
            if source in translations:
                export_data['translations'][source] = translations[source]
        
        # Save
        with open(export_path, 'w', encoding='utf-8') as f:
            json.dump(export_data, f, indent=2, ensure_ascii=False)
        
        QMessageBox.information(
            self,
            "Export Complete",
            f"Exported {len(self.filtered_entries)} entries to:\n{export_path}"
        )
    
    def _save_changes(self):
        """Save changes to dictionary file."""
        if not self.modified:
            QMessageBox.information(self, "No Changes", "No changes to save.")
            return
        
        try:
            # Update metadata
            if 'metadata' not in self.dictionary_data:
                self.dictionary_data['metadata'] = {}
            
            self.dictionary_data['metadata']['updated_at'] = datetime.now().isoformat()
            self.dictionary_data['metadata']['total_entries'] = len(self.dictionary_data.get('translations', {}))
            
            # Save to file
            with gzip.open(self.dictionary_path, 'wt', encoding='utf-8') as f:
                json.dump(self.dictionary_data, f, ensure_ascii=False)
            
            self.modified = False
            self.dictionaryModified.emit()
            
            QMessageBox.information(self, "Saved", "Dictionary changes saved successfully!")
            
        except Exception as e:
            print(f"[ERROR] Failed to save dictionary: {e}")
            QMessageBox.critical(self, "Save Error", f"Failed to save dictionary:\n{e}")
    
    def _close_dialog(self):
        """Close dialog with unsaved changes check."""
        if self.modified:
            reply = QMessageBox.question(
                self,
                "Unsaved Changes",
                "You have unsaved changes.\n\n"
                "Do you want to save before closing?",
                QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No | QMessageBox.StandardButton.Cancel,
                QMessageBox.StandardButton.Yes
            )
            
            if reply == QMessageBox.StandardButton.Yes:
                self._save_changes()
                self.accept()
            elif reply == QMessageBox.StandardButton.No:
                self.reject()
            # Cancel - do nothing
        else:
            self.accept()
