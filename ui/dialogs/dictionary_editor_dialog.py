"""
Dictionary Editor Dialog

Enhanced editor for Smart Dictionary with:
- Search functionality
- Filter by word/sentence mode
- Edit and delete entries
- Bulk operations
"""

import logging

from PyQt6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QLineEdit, QTableWidget, QTableWidgetItem, QHeaderView,
    QMessageBox, QComboBox, QGroupBox, QFileDialog,
    QFormLayout, QDoubleSpinBox, QCheckBox, QSpinBox
)
from PyQt6.QtCore import Qt, pyqtSignal
from PyQt6.QtGui import QColor
from pathlib import Path
import gzip
import json
from datetime import datetime
from app.localization import TranslatableMixin, tr

logger = logging.getLogger(__name__)


class _EntryEditDialog(TranslatableMixin, QDialog):
    """Dialog for editing or adding a single dictionary entry."""

    def __init__(self, parent=None, source_text="", translation="",
                 confidence=0.9, usage_count=0):
        super().__init__(parent)
        self._source_text = source_text
        self._translation = translation
        self._confidence = confidence
        self._usage_count = usage_count
        self._init_ui()

    def _init_ui(self):
        if self._source_text:
            self.setWindowTitle(tr("edit_dictionary_entry"))
        else:
            self.setWindowTitle(tr("add_dictionary_entry"))
        self.setMinimumWidth(500)

        layout = QVBoxLayout(self)
        layout.setSpacing(15)
        layout.setContentsMargins(20, 20, 20, 20)

        form_group = QGroupBox(tr("dict_editor_entry_details"))
        form_layout = QFormLayout(form_group)
        form_layout.setSpacing(10)

        self.source_edit = QLineEdit(self._source_text)
        self.source_edit.setPlaceholderText(tr("dict_editor_source_placeholder"))
        form_layout.addRow(tr("dict_editor_source_text_label"), self.source_edit)

        self.translation_edit = QLineEdit(self._translation)
        self.translation_edit.setPlaceholderText(tr("dict_editor_translation_placeholder"))
        form_layout.addRow(tr("dict_editor_translation_label"), self.translation_edit)

        self.confidence_spin = QDoubleSpinBox()
        self.confidence_spin.setRange(0.0, 1.0)
        self.confidence_spin.setSingleStep(0.1)
        self.confidence_spin.setDecimals(2)
        self.confidence_spin.setValue(self._confidence)
        form_layout.addRow(tr("dict_editor_confidence_label"), self.confidence_spin)

        usage_label = QLabel(tr("dict_editor_times_used").format(count=self._usage_count))
        usage_label.setStyleSheet("color: #666666;")
        form_layout.addRow(tr("dict_editor_usage_count_label"), usage_label)

        layout.addWidget(form_group)

        self._type_hint = QLabel()
        self._type_hint.setStyleSheet("color: #666666; font-style: italic; padding: 5px;")
        self._update_type_hint()
        layout.addWidget(self._type_hint)

        self.source_edit.textChanged.connect(self._update_type_hint)
        self.translation_edit.textChanged.connect(self._update_type_hint)

        button_layout = QHBoxLayout()
        button_layout.addStretch()
        save_btn = QPushButton(tr("dict_editor_save_btn"))
        save_btn.setProperty("class", "action")
        save_btn.setMinimumWidth(100)
        save_btn.clicked.connect(self._save)
        button_layout.addWidget(save_btn)
        cancel_btn = QPushButton(tr("cancel"))
        cancel_btn.setMinimumWidth(100)
        cancel_btn.clicked.connect(self.reject)
        button_layout.addWidget(cancel_btn)
        layout.addLayout(button_layout)

    def _update_type_hint(self):
        source = self.source_edit.text().strip()
        translation = self.translation_edit.text().strip()
        if not source or not translation:
            self._type_hint.setText("")
            return
        is_word = ' ' not in source and ' ' not in translation
        has_punctuation = any(p in source for p in '.!?,;:')
        if is_word and not has_punctuation:
            self._type_hint.setText(tr("this_will_be_saved_as_a_b_single_word_b_entry"))
            self._type_hint.setStyleSheet("color: #2196F3; font-style: italic; padding: 5px;")
        else:
            self._type_hint.setText(tr("this_will_be_saved_as_a_b_sentence_b_entry"))
            self._type_hint.setStyleSheet("color: #4CAF50; font-style: italic; padding: 5px;")

    def _save(self):
        source = self.source_edit.text().strip()
        translation = self.translation_edit.text().strip()
        if not source:
            QMessageBox.warning(self, tr("invalid_input"), tr("source_text_cannot_be_empty"))
            return
        if not translation:
            QMessageBox.warning(self, tr("invalid_input"), tr("translation_cannot_be_empty"))
            return
        self.accept()

    def get_result(self):
        """Return the edited values as a dict."""
        return {
            'source': self.source_edit.text().strip(),
            'translation': self.translation_edit.text().strip(),
            'confidence': self.confidence_spin.value(),
        }


# Keep backward-compatible alias for any external imports
DictionaryEntryEditDialog = _EntryEditDialog


class _PromoteToContextDialog(TranslatableMixin, QDialog):
    """Dialog for promoting a dictionary entry to the active context profile."""

    def __init__(self, parent=None, source_text="", translation=""):
        super().__init__(parent)
        self.setWindowTitle(tr("promote_to_context_title"))
        self.setMinimumWidth(480)

        layout = QVBoxLayout(self)
        layout.setSpacing(12)
        layout.setContentsMargins(20, 20, 20, 20)

        info = QLabel(tr("promote_to_context_info"))
        info.setWordWrap(True)
        info.setStyleSheet(
            "background-color: #E6F2FF; color: #0066CC; padding: 10px; "
            "border-radius: 5px; font-size: 9pt;"
        )
        layout.addWidget(info)

        form_group = QGroupBox(tr("promote_entry_details"))
        form = QFormLayout(form_group)
        form.setSpacing(8)

        src_label = QLabel(source_text)
        src_label.setStyleSheet("font-weight: bold;")
        form.addRow(tr("dict_editor_source_text_label"), src_label)

        tgt_label = QLabel(translation)
        tgt_label.setStyleSheet("font-weight: bold;")
        form.addRow(tr("dict_editor_translation_label"), tgt_label)

        self.target_combo = QComboBox()
        self.target_combo.addItems([
            tr("promote_as_locked_term"),
            tr("promote_as_translation_memory"),
        ])
        self.target_combo.currentIndexChanged.connect(self._on_target_changed)
        form.addRow(tr("promote_target_type"), self.target_combo)

        self.type_combo = QComboBox()
        self.type_combo.addItems(["general", "character", "location", "organization", "attack"])
        self.type_label = QLabel(tr("promote_term_type"))
        form.addRow(self.type_label, self.type_combo)

        self.priority_spin = QSpinBox()
        self.priority_spin.setRange(1, 1000)
        self.priority_spin.setValue(100)
        form.addRow(tr("promote_priority"), self.priority_spin)

        self.case_sensitive_check = QCheckBox(tr("promote_case_sensitive"))
        self.case_sensitive_check.setChecked(True)
        self.cs_label = QLabel("")
        form.addRow(self.cs_label, self.case_sensitive_check)

        self.notes_edit = QLineEdit()
        self.notes_edit.setPlaceholderText(tr("promote_notes_placeholder"))
        form.addRow(tr("promote_notes"), self.notes_edit)

        self.remove_check = QCheckBox(tr("promote_remove_from_dict"))
        self.remove_check.setChecked(False)
        form.addRow("", self.remove_check)

        layout.addWidget(form_group)

        btn_layout = QHBoxLayout()
        btn_layout.addStretch()
        promote_btn = QPushButton(tr("promote_confirm_btn"))
        promote_btn.setProperty("class", "action")
        promote_btn.setMinimumWidth(120)
        promote_btn.clicked.connect(self.accept)
        btn_layout.addWidget(promote_btn)
        cancel_btn = QPushButton(tr("cancel"))
        cancel_btn.setMinimumWidth(100)
        cancel_btn.clicked.connect(self.reject)
        btn_layout.addWidget(cancel_btn)
        layout.addLayout(btn_layout)

    def _on_target_changed(self, index):
        is_locked = index == 0
        self.type_combo.setVisible(is_locked)
        self.type_label.setVisible(is_locked)
        self.case_sensitive_check.setVisible(is_locked)
        self.priority_spin.setValue(100 if is_locked else 50)

    def get_result(self):
        return {
            'is_locked_term': self.target_combo.currentIndex() == 0,
            'type': self.type_combo.currentText(),
            'priority': self.priority_spin.value(),
            'case_sensitive': self.case_sensitive_check.isChecked(),
            'notes': self.notes_edit.text().strip(),
            'remove_from_dict': self.remove_check.isChecked(),
        }


class DictionaryEditorDialog(TranslatableMixin, QDialog):
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
        self.setWindowTitle(tr("dict_editor_window_title").format(src=self.source_lang, tgt=self.target_lang))
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
        
        title = QLabel(tr("dict_editor_header_title").format(src=self.source_lang.upper(), tgt=self.target_lang.upper()))
        title.setStyleSheet("font-size: 12pt;")
        header_layout.addWidget(title)
        
        header_layout.addStretch()
        
        self.stats_label = QLabel(tr("dict_editor_entries_count").format(count=0))
        self.stats_label.setStyleSheet("font-size: 10pt; color: #666666;")
        header_layout.addWidget(self.stats_label)
        
        parent_layout.addLayout(header_layout)
    
    def _create_filter_section(self, parent_layout):
        """Create filter and search section."""
        group = QGroupBox(tr("dict_editor_search_filter"))
        layout = QHBoxLayout(group)
        layout.setSpacing(10)
        
        # Search box
        search_label = QLabel(tr("search_2"))
        layout.addWidget(search_label)
        
        self.search_box = QLineEdit()
        self.search_box.setPlaceholderText(tr("search_source_or_translation_text"))
        self.search_box.textChanged.connect(self._apply_filters)
        layout.addWidget(self.search_box, 1)
        
        # Mode filter
        mode_label = QLabel(tr("mode"))
        layout.addWidget(mode_label)
        
        self.mode_combo = QComboBox()
        self.mode_combo.addItems([tr("dict_editor_filter_all"), tr("dict_editor_filter_words"), tr("dict_editor_filter_sentences")])
        self.mode_combo.setToolTip(tr("dict_editor_filter_tooltip"))
        self.mode_combo.currentIndexChanged.connect(self._apply_filters)
        layout.addWidget(self.mode_combo)
        
        # Sort by
        sort_label = QLabel(tr("sort"))
        layout.addWidget(sort_label)
        
        self.sort_combo = QComboBox()
        self.sort_combo.addItems([tr("dict_editor_sort_usage_high"), tr("dict_editor_sort_usage_low"),
                                  tr("dict_editor_sort_alpha_az"), tr("dict_editor_sort_alpha_za"),
                                  tr("dict_editor_sort_conf_high"), tr("dict_editor_sort_conf_low")])
        self.sort_combo.currentIndexChanged.connect(self._apply_filters)
        layout.addWidget(self.sort_combo)
        
        # Clear search button
        clear_btn = QPushButton(tr("clear"))
        clear_btn.clicked.connect(self._clear_search)
        layout.addWidget(clear_btn)
        
        parent_layout.addWidget(group)
    
    def _create_table_section(self, parent_layout):
        """Create table for dictionary entries."""
        self.table = QTableWidget()
        self.table.setColumnCount(6)
        self.table.setHorizontalHeaderLabels([
            tr("dict_editor_col_source"), tr("dict_editor_col_translation"),
            tr("dict_editor_col_type"), tr("dict_editor_col_usage"),
            tr("dict_editor_col_confidence"), tr("dict_editor_col_last_used")
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
        edit_btn = QPushButton(tr("dict_editor_edit_selected"))
        edit_btn.setToolTip(tr("dict_editor_edit_tooltip"))
        edit_btn.clicked.connect(self._edit_selected)
        actions_layout.addWidget(edit_btn)
        
        # Delete button
        delete_btn = QPushButton(tr("dict_editor_delete_selected"))
        delete_btn.setToolTip(tr("dict_editor_delete_tooltip"))
        delete_btn.clicked.connect(self._delete_selected)
        actions_layout.addWidget(delete_btn)
        
        # Add button
        add_btn = QPushButton(tr("dict_editor_add_entry"))
        add_btn.setToolTip(tr("dict_editor_add_tooltip"))
        add_btn.clicked.connect(self._add_entry)
        actions_layout.addWidget(add_btn)

        # Promote to Context button
        promote_btn = QPushButton(tr("promote_to_context_btn"))
        promote_btn.setToolTip(tr("promote_to_context_tooltip"))
        promote_btn.clicked.connect(self._promote_to_context)
        actions_layout.addWidget(promote_btn)
        
        actions_layout.addStretch()
        
        # Export filtered button
        export_btn = QPushButton(tr("dict_editor_export_filtered"))
        export_btn.setToolTip(tr("dict_editor_export_tooltip"))
        export_btn.clicked.connect(self._export_filtered)
        actions_layout.addWidget(export_btn)
        
        parent_layout.addLayout(actions_layout)
    
    def _create_button_section(self, parent_layout):
        """Create dialog buttons."""
        button_layout = QHBoxLayout()
        
        button_layout.addStretch()
        
        # Save button
        save_btn = QPushButton(tr("dict_editor_save_changes"))
        save_btn.setProperty("class", "action")
        save_btn.setMinimumWidth(120)
        save_btn.clicked.connect(self._save_changes)
        button_layout.addWidget(save_btn)
        
        # Close button
        close_btn = QPushButton(tr("close"))
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
            
            logger.info("Loaded %d dictionary entries", len(self.dictionary_data.get('translations', {})))
            
        except Exception as e:
            logger.error("Failed to load dictionary: %s", e)
            QMessageBox.critical(self, tr("load_error"), tr("dict_editor_load_failed").format(error=e))
    
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
                if mode == tr("dict_editor_filter_words"):
                    if ' ' in source_text.strip() or ' ' in translation.strip():
                        continue
                elif mode == tr("dict_editor_filter_sentences"):
                    if ' ' not in source_text.strip() and ' ' not in translation.strip():
                        continue
                
                # Determine type
                if ' ' in source_text.strip() or any(p in source_text for p in '.!?,;:'):
                    entry_type = tr("dict_editor_type_sentence")
                else:
                    entry_type = tr("dict_editor_type_word")
                
                filtered.append({
                    'source': source_text,
                    'translation': translation,
                    'type': entry_type,
                    'usage': entry.get('usage_count', 0),
                    'confidence': entry.get('confidence', 0.0),
                    'last_used': entry.get('last_used', '')
                })
            
            # Apply sorting
            if sort_mode == tr("dict_editor_sort_usage_high"):
                filtered.sort(key=lambda x: x['usage'], reverse=True)
            elif sort_mode == tr("dict_editor_sort_usage_low"):
                filtered.sort(key=lambda x: x['usage'])
            elif sort_mode == tr("dict_editor_sort_alpha_az"):
                filtered.sort(key=lambda x: x['source'].lower())
            elif sort_mode == tr("dict_editor_sort_alpha_za"):
                filtered.sort(key=lambda x: x['source'].lower(), reverse=True)
            elif sort_mode == tr("dict_editor_sort_conf_high"):
                filtered.sort(key=lambda x: x['confidence'], reverse=True)
            elif sort_mode == tr("dict_editor_sort_conf_low"):
                filtered.sort(key=lambda x: x['confidence'])
            
            self.filtered_entries = filtered
            
            # Update table
            self._update_table()
            
        except Exception as e:
            logger.debug("Failed to apply filters: %s", e)
    
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
                if entry['type'] == tr("dict_editor_type_word"):
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
                    except (ValueError, TypeError):
                        last_used_str = tr("dict_editor_unknown")
                else:
                    last_used_str = tr("dict_editor_never")
                
                last_used_item = QTableWidgetItem(last_used_str)
                last_used_item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
                self.table.setItem(row, 5, last_used_item)
            
            # Update stats
            self._update_stats()
            
        except Exception as e:
            logger.debug("Failed to update table: %s", e)
    
    def _update_stats(self):
        """Update statistics label."""
        total = len(self.dictionary_data.get('translations', {}))
        filtered = len(self.filtered_entries)
        
        if filtered == total:
            self.stats_label.setText(tr("dict_editor_entries_count").format(count=f"{total:,}"))
        else:
            self.stats_label.setText(tr("dict_editor_entries_filtered").format(filtered=f"{filtered:,}", total=f"{total:,}"))
    
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
            QMessageBox.warning(self, tr("no_selection"), tr("please_select_an_entry_to_edit"))
            return
        
        if len(selected_rows) > 1:
            QMessageBox.warning(self, tr("multiple_selection"), tr("please_select_only_one_entry_to_edit"))
            return
        
        row = selected_rows[0].row()
        entry = self.filtered_entries[row]
        
        # Open edit dialog
        dialog = _EntryEditDialog(
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
            result = dialog.get_result()
            new_source = result['source']
            new_translation = result['translation']
            new_confidence = result['confidence']
            
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
            QMessageBox.warning(self, tr("no_selection"), tr("please_select_entries_to_delete"))
            return
        
        reply = QMessageBox.question(
            self,
            tr("dict_editor_confirm_delete"),
            tr("dict_editor_confirm_delete_msg").format(count=len(selected_rows)),
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
        dialog = _EntryEditDialog(parent=self)
        
        if dialog.exec() == QDialog.DialogCode.Accepted:
            translations = self.dictionary_data.get('translations', {})
            
            result = dialog.get_result()
            source_text = result['source']
            translation = result['translation']
            confidence = result['confidence']
            
            if source_text in translations:
                reply = QMessageBox.question(
                    self,
                    tr("dict_editor_entry_exists"),
                    tr("dict_editor_entry_exists_msg").format(source=source_text),
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
    
    def _promote_to_context(self):
        """Promote selected entry to the active context profile."""
        selected_rows = self.table.selectionModel().selectedRows()

        if not selected_rows:
            QMessageBox.warning(self, tr("no_selection"), tr("promote_select_entry"))
            return

        if len(selected_rows) > 1:
            QMessageBox.warning(self, tr("multiple_selection"), tr("promote_one_at_a_time"))
            return

        row = selected_rows[0].row()
        entry = self.filtered_entries[row]

        # Find active context profile
        active_profile_name = ""
        active_profile_path = None
        if self.config_manager:
            active_profile_name = self.config_manager.get_setting(
                'plugins.context_manager.active_profile', '')
            if active_profile_name:
                from app.utils.path_utils import get_context_profiles_dir
                profiles_dir = get_context_profiles_dir()
                for f in profiles_dir.glob("*.json"):
                    try:
                        raw = json.loads(f.read_text(encoding="utf-8"))
                        name = raw.get("meta", {}).get("name", f.stem)
                        if name == active_profile_name:
                            active_profile_path = f
                            break
                    except Exception:
                        continue

        if not active_profile_path:
            QMessageBox.warning(
                self,
                tr("promote_no_profile_title"),
                tr("promote_no_profile_msg"),
            )
            return

        dialog = _PromoteToContextDialog(
            parent=self,
            source_text=entry['source'],
            translation=entry['translation'],
        )

        if dialog.exec() != QDialog.DialogCode.Accepted:
            return

        result = dialog.get_result()

        try:
            from plugins.enhancers.optimizers.context_manager.context_profile import (
                ContextProfile, LockedTerm, TranslationMemoryEntry
            )
            profile = ContextProfile.from_file(str(active_profile_path))

            if result['is_locked_term']:
                # Check for duplicate
                existing = [t for t in profile.global_context.locked_terms
                            if t.source == entry['source']]
                if existing:
                    reply = QMessageBox.question(
                        self,
                        tr("promote_duplicate_title"),
                        tr("promote_duplicate_msg").format(source=entry['source']),
                        QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
                        QMessageBox.StandardButton.No,
                    )
                    if reply != QMessageBox.StandardButton.Yes:
                        return
                    profile.global_context.locked_terms = [
                        t for t in profile.global_context.locked_terms
                        if t.source != entry['source']
                    ]

                profile.global_context.locked_terms.append(LockedTerm(
                    source=entry['source'],
                    target=entry['translation'],
                    type=result['type'],
                    case_sensitive=result['case_sensitive'],
                    priority=result['priority'],
                    notes=result['notes'],
                ))
            else:
                existing = [t for t in profile.global_context.translation_memory
                            if t.source == entry['source']]
                if existing:
                    reply = QMessageBox.question(
                        self,
                        tr("promote_duplicate_title"),
                        tr("promote_duplicate_msg").format(source=entry['source']),
                        QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
                        QMessageBox.StandardButton.No,
                    )
                    if reply != QMessageBox.StandardButton.Yes:
                        return
                    profile.global_context.translation_memory = [
                        t for t in profile.global_context.translation_memory
                        if t.source != entry['source']
                    ]

                profile.global_context.translation_memory.append(TranslationMemoryEntry(
                    source=entry['source'],
                    target=entry['translation'],
                    priority=result['priority'],
                    notes=result['notes'],
                ))

            profile.save(str(active_profile_path))

            if result['remove_from_dict']:
                translations = self.dictionary_data.get('translations', {})
                if entry['source'] in translations:
                    del translations[entry['source']]
                    self.modified = True
                    self._apply_filters()

            target_type = tr("promote_as_locked_term") if result['is_locked_term'] else tr("promote_as_translation_memory")
            QMessageBox.information(
                self,
                tr("promote_success_title"),
                tr("promote_success_msg").format(
                    source=entry['source'],
                    target_type=target_type,
                    profile=active_profile_name,
                ),
            )
            logger.info("Promoted '%s' to context profile '%s' as %s",
                         entry['source'], active_profile_name, target_type)

        except Exception as e:
            logger.error("Failed to promote entry to context: %s", e, exc_info=True)
            QMessageBox.critical(
                self,
                tr("promote_failed_title"),
                tr("promote_failed_msg").format(error=str(e)),
            )

    def _export_filtered(self):
        """Export filtered entries."""
        if not self.filtered_entries:
            QMessageBox.warning(self, tr("no_entries"), tr("no_entries_to_export"))
            return
        
        export_path, _ = QFileDialog.getSaveFileName(
            self,
            tr("dict_editor_export_title"),
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
        try:
            with open(export_path, 'w', encoding='utf-8') as f:
                json.dump(export_data, f, indent=2, ensure_ascii=False)
        except Exception as e:
            logger.error("Failed to export dictionary: %s", e)
            QMessageBox.critical(self, tr("dict_editor_export_failed"), tr("dict_editor_export_failed_msg").format(error=e))
            return
        
        QMessageBox.information(
            self,
            tr("dict_editor_export_complete"),
            tr("dict_editor_export_complete_msg").format(count=len(self.filtered_entries), path=export_path)
        )
    
    def _save_changes(self):
        """Save changes to dictionary file."""
        if not self.modified:
            QMessageBox.information(self, tr("no_changes"), tr("no_changes_to_save"))
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
            
            QMessageBox.information(self, tr("saved"), tr("dictionary_changes_saved_successfully"))
            
        except Exception as e:
            logger.error("Failed to save dictionary: %s", e)
            QMessageBox.critical(self, tr("save_error"), tr("dict_editor_save_failed").format(error=e))
    
    def _close_dialog(self):
        """Close dialog with unsaved changes check."""
        if self.modified:
            reply = QMessageBox.question(
                self,
                tr("dict_editor_unsaved_changes"),
                tr("dict_editor_unsaved_changes_msg"),
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
