"""
Statistics Section

Overview, dictionary statistics, most-used translations, and all-pairs table.
"""

import gzip
import json
import logging
from pathlib import Path

from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QFormLayout, QGroupBox,
    QLabel, QListWidget,
    QTableWidget, QTableWidgetItem, QHeaderView,
)
from PyQt6.QtCore import Qt

logger = logging.getLogger(__name__)


def _format_file_size(size_bytes: int) -> str:
    """Format byte count as human-readable file size."""
    if size_bytes < 1024:
        return f"{size_bytes} bytes"
    elif size_bytes < 1024 * 1024:
        return f"{size_bytes / 1024:.1f} KB"
    return f"{size_bytes / (1024 * 1024):.1f} MB"


class StatisticsSection(QWidget):
    """Overview, dictionary statistics, most-used translations, and all-pairs table."""

    def __init__(self, parent=None):
        super().__init__(parent)

        self.dict_entries_label = None
        self.dict_usage_label = None
        self.dict_avg_usage_label = None
        self.dict_file_size_label = None
        self.dict_hit_rate_label = None
        self.most_used_list = None
        self.language_pair_table = None

        self._init_ui()

    def _init_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(10)

        self._create_statistics_group(layout)
        self._create_most_used_group(layout)
        self._create_all_pairs_table(layout)

    # ------------------------------------------------------------------
    # Group creation
    # ------------------------------------------------------------------

    def _create_statistics_group(self, parent_layout):
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

    def _create_most_used_group(self, parent_layout):
        """Create most used translations section."""
        group = QGroupBox("⭐ Most Used Translations")
        layout = QVBoxLayout(group)
        layout.setSpacing(10)
        layout.setContentsMargins(15, 20, 15, 15)

        self.most_used_list = QListWidget()
        self.most_used_list.setMaximumHeight(120)
        layout.addWidget(self.most_used_list)

        parent_layout.addWidget(group)

    def _create_all_pairs_table(self, parent_layout):
        """Create table showing all available language pairs."""
        group = QGroupBox("📋 All Language Pairs")
        layout = QVBoxLayout(group)
        layout.setSpacing(10)
        layout.setContentsMargins(15, 20, 15, 15)

        self.language_pair_table = QTableWidget()
        self.language_pair_table.setColumnCount(5)
        self.language_pair_table.setHorizontalHeaderLabels(
            ["Active", "Name", "Language Pair", "Entries", "Size"]
        )
        self.language_pair_table.setMaximumHeight(150)
        self.language_pair_table.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
        self.language_pair_table.setSelectionMode(QTableWidget.SelectionMode.SingleSelection)
        self.language_pair_table.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)

        header = self.language_pair_table.horizontalHeader()
        header.setSectionResizeMode(0, QHeaderView.ResizeMode.Fixed)
        header.setSectionResizeMode(1, QHeaderView.ResizeMode.Stretch)
        header.setSectionResizeMode(2, QHeaderView.ResizeMode.Stretch)
        header.setSectionResizeMode(3, QHeaderView.ResizeMode.Fixed)
        header.setSectionResizeMode(4, QHeaderView.ResizeMode.Fixed)

        self.language_pair_table.setColumnWidth(0, 60)
        self.language_pair_table.setColumnWidth(3, 100)
        self.language_pair_table.setColumnWidth(4, 100)

        layout.addWidget(self.language_pair_table)
        parent_layout.addWidget(group)

    # ------------------------------------------------------------------
    # Data update
    # ------------------------------------------------------------------

    def clear_statistics(self):
        """Clear all statistics labels and the most used translations list."""
        self.dict_entries_label.setText("0")
        self.dict_usage_label.setText("0 lookups")
        self.dict_avg_usage_label.setText("0.0 times per entry")
        self.dict_file_size_label.setText("No dictionary file yet")
        self.dict_hit_rate_label.setText("N/A")
        self.most_used_list.clear()

    def update_statistics(self, current_data, pipeline=None):
        """Update statistics for the given language pair.

        *current_data* is ``(source_lang, target_lang, file_path)`` or
        ``None`` when nothing is selected.
        """
        try:
            if not current_data:
                self.clear_statistics()
                return

            source_lang, target_lang, file_path = current_data

            # Try live in-memory dictionary first (most up-to-date)
            live_dict = None
            if pipeline and hasattr(pipeline, 'cache_manager') and pipeline.cache_manager:
                live_dict = getattr(pipeline.cache_manager, 'persistent_dictionary', None)

            if live_dict:
                stats = live_dict.get_stats(source_lang, target_lang)
                total_entries = stats.total_entries
                total_usage = stats.total_usage
                avg_usage = stats.average_usage
                hit_rate = (stats.cache_hits / stats.total_lookups * 100) if stats.total_lookups > 0 else 0
                hit_rate_str = f"{hit_rate:.1f}%" if stats.total_lookups > 0 else "N/A"

                dict_path = Path(file_path)
                file_size_str = (
                    _format_file_size(dict_path.stat().st_size)
                    if dict_path.exists() else "Not saved yet"
                )

                translations = {}
                for entry in live_dict.get_all_entries(source_lang, target_lang):
                    translations[entry.source_text] = entry.to_dict()
            else:
                dict_path = Path(file_path)

                if not dict_path.exists():
                    self.clear_statistics()
                    return

                with gzip.open(dict_path, 'rt', encoding='utf-8') as f:
                    data = json.load(f)

                translations = data.get('translations', {})

                total_entries = len(translations)
                total_usage = sum(entry.get('usage_count', 0) for entry in translations.values())
                avg_usage = total_usage / total_entries if total_entries > 0 else 0.0

                file_size_str = _format_file_size(dict_path.stat().st_size)

                metadata = data.get('metadata', {})
                hit_rate = metadata.get('hit_rate', 0.0)
                hit_rate_str = f"{hit_rate * 100:.1f}%" if hit_rate > 0 else "N/A"

            # Update labels
            self.dict_entries_label.setText(f"{total_entries:,}")
            self.dict_usage_label.setText(f"{total_usage:,} lookups")
            self.dict_avg_usage_label.setText(f"{avg_usage:.1f} times per entry")
            self.dict_file_size_label.setText(file_size_str)
            self.dict_hit_rate_label.setText(hit_rate_str)

            self._update_most_used_list(translations)

        except Exception as e:
            logger.error("Failed to update statistics: %s", e, exc_info=True)

    def _update_most_used_list(self, translations: dict):
        """Update the most used translations list."""
        try:
            self.most_used_list.clear()

            sorted_entries = sorted(
                translations.items(),
                key=lambda x: x[1].get('usage_count', 0),
                reverse=True,
            )

            for source_text, entry in sorted_entries[:10]:
                translation = entry.get('translation', '')
                usage_count = entry.get('usage_count', 0)

                if len(source_text) > 40:
                    source_text = source_text[:37] + "..."
                if len(translation) > 40:
                    translation = translation[:37] + "..."

                item_text = f"{source_text} → {translation} ({usage_count}x)"
                self.most_used_list.addItem(item_text)

        except Exception as e:
            logger.warning("Failed to update most used list: %s", e)

    def update_language_pairs_table(self):
        """Update the language pairs table with all available dictionaries."""
        try:
            from app.utils.path_utils import get_dictionary_dir

            self.language_pair_table.setRowCount(0)

            dict_dir = get_dictionary_dir()
            if not dict_dir.exists():
                return

            all_dict_files = list(dict_dir.glob("*.json.gz"))
            dict_files = [f for f in all_dict_files if 'backup' not in f.name.lower()]

            if not dict_files:
                return

            for row, dict_file in enumerate(dict_files):
                try:
                    filename = dict_file.stem  # Remove .gz
                    if filename.endswith('.json'):
                        filename = filename[:-5]

                    parts = filename.split('_')
                    if len(parts) == 2 and len(parts[0]) <= 3 and len(parts[1]) <= 3:
                        source_lang = parts[0]
                        target_lang = parts[1]
                    else:
                        continue

                    if '.' in source_lang or '.' in target_lang:
                        continue

                    with gzip.open(dict_file, 'rt', encoding='utf-8') as f:
                        data = json.load(f)

                    translations = data.get('translations', {})
                    total_entries = len(translations)
                    file_size_str = _format_file_size(dict_file.stat().st_size)

                    self.language_pair_table.insertRow(row)

                    active_item = QTableWidgetItem()
                    active_item.setFlags(Qt.ItemFlag.ItemIsUserCheckable | Qt.ItemFlag.ItemIsEnabled)
                    active_item.setCheckState(Qt.CheckState.Checked)
                    self.language_pair_table.setItem(row, 0, active_item)

                    name_item = QTableWidgetItem(f"{source_lang.upper()}-{target_lang.upper()}")
                    self.language_pair_table.setItem(row, 1, name_item)

                    pair_item = QTableWidgetItem(f"{source_lang} → {target_lang}")
                    self.language_pair_table.setItem(row, 2, pair_item)

                    entries_item = QTableWidgetItem(f"{total_entries:,}")
                    entries_item.setTextAlignment(
                        Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter
                    )
                    self.language_pair_table.setItem(row, 3, entries_item)

                    size_item = QTableWidgetItem(file_size_str)
                    size_item.setTextAlignment(
                        Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter
                    )
                    self.language_pair_table.setItem(row, 4, size_item)

                except Exception as e:
                    logger.warning("Failed to process %s: %s", dict_file.name, e)

            logger.debug("Table updated with %d dictionaries", len(dict_files))

        except Exception as e:
            logger.error("Failed to update language pairs table: %s", e, exc_info=True)
