"""
Usage Section

Storage overview, directory locations, data retention, and usage display.
"""

import logging

from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QGridLayout, QGroupBox,
    QLabel, QPushButton, QLineEdit, QProgressBar, QMessageBox,
)
from PyQt6.QtCore import pyqtSignal

from ui.common.widgets.custom_spinbox import CustomSpinBox
from ui.common.file_utils import open_folder as _open_folder
from app.localization import TranslatableMixin, tr
from app.utils.path_utils import get_dir, get_relative_path, get_hf_cache_dir

logger = logging.getLogger(__name__)


class UsageSection(TranslatableMixin, QWidget):
    """Storage locations, data retention, and usage display."""

    settingChanged = pyqtSignal()

    def __init__(self, config_manager=None, parent=None):
        super().__init__(parent)
        self.config_manager = config_manager

        # Directory display widgets (read-only)
        self.model_dir_edit = None
        self.config_dir_edit = None
        self.cache_dir_edit = None
        self.dict_dir_edit = None
        self.logs_dir_edit = None
        self.backups_dir_edit = None
        self.exports_dir_edit = None

        # Retention
        self.retention_spinbox = None

        # Usage display
        self.cache_usage_bar = None
        self.cache_usage_label = None
        self.refresh_usage_btn = None

        self._init_ui()

    def _create_label(self, text: str, bold: bool = False) -> QLabel:
        """Create a label with consistent styling."""
        label = QLabel(text)
        if bold:
            label.setStyleSheet("font-weight: 600; font-size: 9pt;")
        else:
            label.setStyleSheet("font-size: 9pt;")
        return label

    def _init_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(10)

        self._create_dictionary_redirect_note(layout)
        self._create_storage_locations_section(layout)
        self._create_retention_section(layout)
        self._create_storage_usage_section(layout)

    def _create_dictionary_redirect_note(self, parent_layout):
        """Create note directing users to Smart Dictionary tab."""
        group = QGroupBox()
        self.set_translatable_text(group, "storage_smart_dictionary_section")
        layout = QVBoxLayout(group)
        layout.setContentsMargins(15, 20, 15, 15)

        note = QLabel()
        self.set_translatable_text(note, "storage_dictionary_redirect_note")
        note.setWordWrap(True)
        note.setStyleSheet(
            "color: #2196F3; font-size: 9pt; padding: 15px; "
            "background-color: rgba(33, 150, 243, 0.1); border-radius: 6px; "
            "border-left: 4px solid #2196F3;"
        )
        layout.addWidget(note)

        parent_layout.addWidget(group)

    def _create_storage_locations_section(self, parent_layout):
        """Create storage locations section — all paths from path_utils.PATHS registry."""
        group = QGroupBox()
        self.set_translatable_text(group, "storage_storage_locations_section")
        layout = QVBoxLayout(group)
        layout.setSpacing(12)
        layout.setContentsMargins(15, 20, 15, 15)

        # Editable main directories
        # (registry_key, label_key, desc_key, translatable_open_key, is_editable, edit_attr)
        path_entries = [
            ("config", "storage_config_directory_label",
             "storage_config_directory_desc",
             "storage_open_button_2", True, "config_dir_edit"),
            ("models", "storage_ai_models_directory_label",
             "storage_ai_models_directory_desc",
             "storage_open_button_3", True, "model_dir_edit"),
        ]

        for registry_key, label_key, desc_key, open_key, is_editable, edit_attr in path_entries:
            row_layout = QHBoxLayout()
            row_layout.setSpacing(10)

            row_label = self._create_label("", bold=True)
            self.set_translatable_text(row_label, label_key)
            row_layout.addWidget(row_label)

            line_edit = QLineEdit()
            line_edit.setText(get_relative_path(registry_key))
            line_edit.setReadOnly(True)
            line_edit.setStyleSheet("background-color: transparent; border: 1px solid #ccc; padding: 4px;")
            row_layout.addWidget(line_edit)
            setattr(self, edit_attr, line_edit)

            open_btn = QPushButton()
            self.set_translatable_text(open_btn, open_key)
            open_btn.setProperty("class", "action")
            open_btn.setMinimumWidth(80)
            open_btn.clicked.connect(
                lambda checked=False, k=registry_key: _open_folder(str(get_dir(k)), self))
            row_layout.addWidget(open_btn)

            layout.addLayout(row_layout)

            desc = QLabel()
            self.set_translatable_text(desc, desc_key)
            desc.setStyleSheet("color: #666666; font-size: 9pt; margin-bottom: 10px;")
            layout.addWidget(desc)

        # HuggingFace cache location (where model files actually live)
        hf_layout = QHBoxLayout()
        hf_layout.setSpacing(10)

        hf_label = self._create_label("", bold=False)
        self.set_translatable_text(hf_label, "storage_hf_cache_label")
        hf_label.setStyleSheet("color: #888888; font-size: 9pt; margin-left: 20px;")
        hf_layout.addWidget(hf_label)

        hf_path = str(get_hf_cache_dir())
        hf_path_label = QLabel(hf_path)
        hf_path_label.setStyleSheet("color: #666666; font-size: 9pt;")
        hf_layout.addWidget(hf_path_label)
        hf_layout.addStretch()

        hf_open_btn = QPushButton()
        self.set_translatable_text(hf_open_btn, "storage_open_folder_button")
        hf_open_btn.setProperty("class", "action")
        hf_open_btn.setMinimumWidth(120)
        hf_open_btn.clicked.connect(
            lambda checked=False: _open_folder(hf_path, self))
        hf_layout.addWidget(hf_open_btn)

        layout.addLayout(hf_layout)

        hf_desc = QLabel()
        self.set_translatable_text(hf_desc, "storage_hf_cache_desc")
        hf_desc.setStyleSheet("color: #888888; font-size: 8pt; margin-bottom: 5px; margin-left: 40px;")
        layout.addWidget(hf_desc)

        # Remaining main directories
        # (registry_key, label_key, desc_key, open_key, edit_attr)
        remaining_entries = [
            ("cache", "storage_cache_directory_label", "storage_cache_directory_desc",
             "storage_open_button_4", "cache_dir_edit"),
            ("dictionary", "storage_dictionary_directory_label", "storage_dictionary_directory_desc",
             "storage_open_button_5", "dict_dir_edit"),
            ("logs", "storage_logs_directory_label", "storage_logs_directory_desc",
             "storage_open_button_6", "logs_dir_edit"),
            ("backups", "storage_backups_directory_label", "storage_backups_directory_desc",
             "storage_open_button_7", "backups_dir_edit"),
            ("exports", "storage_exports_directory_label", "storage_exports_directory_desc",
             "storage_open_button_8", "exports_dir_edit"),
        ]

        for registry_key, label_key, desc_key, open_key, edit_attr in remaining_entries:
            row_layout = QHBoxLayout()
            row_layout.setSpacing(10)

            row_label = self._create_label("", bold=True)
            self.set_translatable_text(row_label, label_key)
            row_layout.addWidget(row_label)

            line_edit = QLineEdit()
            line_edit.setText(get_relative_path(registry_key))
            line_edit.setReadOnly(True)
            line_edit.setStyleSheet("background-color: transparent; border: 1px solid #ccc; padding: 4px;")
            row_layout.addWidget(line_edit)
            setattr(self, edit_attr, line_edit)

            open_btn = QPushButton()
            self.set_translatable_text(open_btn, open_key)
            open_btn.setProperty("class", "action")
            open_btn.setMinimumWidth(80)
            open_btn.clicked.connect(
                lambda checked=False, k=registry_key: _open_folder(str(get_dir(k)), self))
            row_layout.addWidget(open_btn)

            layout.addLayout(row_layout)

            desc = QLabel()
            self.set_translatable_text(desc, desc_key)
            desc.setStyleSheet("color: #666666; font-size: 9pt; margin-bottom: 10px;")
            layout.addWidget(desc)

        # Directory info note
        info_note = QLabel()
        self.set_translatable_text(info_note, "storage_paths_info_note")
        info_note.setWordWrap(True)
        info_note.setStyleSheet("color: #666666; font-size: 9pt; margin-top: 10px;")
        layout.addWidget(info_note)

        parent_layout.addWidget(group)

    def _create_retention_section(self, parent_layout):
        """Create data retention policy section."""
        group = QGroupBox()
        self.set_translatable_text(group, "storage_data_retention_policy_section")
        layout = QVBoxLayout(group)
        layout.setSpacing(12)
        layout.setContentsMargins(15, 20, 15, 15)

        retention_grid = QGridLayout()
        retention_grid.setHorizontalSpacing(8)
        retention_grid.setVerticalSpacing(8)
        retention_grid.setContentsMargins(0, 5, 0, 5)
        retention_grid.setColumnStretch(2, 1)

        retention_label = self._create_label("", bold=True)
        self.set_translatable_text(retention_label, "storage_keep_data_for_label")

        self.retention_spinbox = CustomSpinBox()
        self.retention_spinbox.setRange(1, 365)
        self.retention_spinbox.setValue(30)
        self.retention_spinbox.setSuffix("days")
        self.retention_spinbox.setSingleStep(1)
        self.retention_spinbox.setMinimumWidth(120)
        self.set_translatable_text(self.retention_spinbox, "storage_one_day", method="setSpecialValueText")
        self.retention_spinbox.valueChanged.connect(self._on_change)

        retention_grid.addWidget(retention_label, 0, 0)
        retention_grid.addWidget(self.retention_spinbox, 0, 1)
        layout.addLayout(retention_grid)

        retention_desc = QLabel()
        self.set_translatable_text(retention_desc, "storage_retention_description")
        retention_desc.setWordWrap(True)
        retention_desc.setStyleSheet("color: #666666; font-size: 9pt; margin-top: 5px;")
        layout.addWidget(retention_desc)

        parent_layout.addWidget(group)

    def _create_storage_usage_section(self, parent_layout):
        """Create storage usage display section."""
        group = QGroupBox()
        self.set_translatable_text(group, "storage_storage_usage_section")
        layout = QVBoxLayout(group)
        layout.setSpacing(12)
        layout.setContentsMargins(15, 20, 15, 15)

        # Cache usage progress bar
        usage_layout = QVBoxLayout()
        usage_layout.setSpacing(8)

        usage_label_layout = QHBoxLayout()
        cache_label = self._create_label("", bold=True)
        self.set_translatable_text(cache_label, "storage_cache_usage_label")
        usage_label_layout.addWidget(cache_label)

        self.cache_usage_label = QLabel()
        self.set_translatable_text(self.cache_usage_label, "storage_cache_usage_default")
        self.cache_usage_label.setStyleSheet("font-size: 9pt; color: #666666;")
        usage_label_layout.addWidget(self.cache_usage_label)
        usage_label_layout.addStretch()

        usage_layout.addLayout(usage_label_layout)

        self.cache_usage_bar = QProgressBar()
        self.cache_usage_bar.setRange(0, 100)
        self.cache_usage_bar.setValue(0)
        self.cache_usage_bar.setTextVisible(False)
        self.cache_usage_bar.setMinimumHeight(20)
        usage_layout.addWidget(self.cache_usage_bar)

        layout.addLayout(usage_layout)

        # Refresh button
        refresh_layout = QHBoxLayout()
        self.refresh_usage_btn = QPushButton()
        self.set_translatable_text(self.refresh_usage_btn, "storage_refresh_usage_button")
        self.refresh_usage_btn.setProperty("class", "action")
        self.refresh_usage_btn.setMinimumWidth(120)
        refresh_layout.addWidget(self.refresh_usage_btn)
        refresh_layout.addStretch()
        layout.addLayout(refresh_layout)

        # Storage info
        info_label = QLabel()
        self.set_translatable_text(info_label, "storage_usage_info_description")
        info_label.setWordWrap(True)
        info_label.setStyleSheet("color: #666666; font-size: 9pt; margin-top: 5px;")
        layout.addWidget(info_label)

        parent_layout.addWidget(group)

    def _on_change(self):
        self.settingChanged.emit()

    def update_storage_usage(self, size_mb: float, limit_mb: int):
        """Update the storage usage display with pre-calculated values."""
        percentage = min(int((size_mb / limit_mb) * 100), 100) if limit_mb > 0 else 0

        self.cache_usage_label.setText(
            tr("storage_cache_usage_format").format(
                size_mb=f"{size_mb:.1f}", limit_mb=limit_mb, percentage=percentage
            )
        )
        self.cache_usage_bar.setValue(percentage)

        if percentage >= 90:
            self.cache_usage_bar.setStyleSheet("QProgressBar::chunk { background-color: #F44336; }")
        elif percentage >= 75:
            self.cache_usage_bar.setStyleSheet("QProgressBar::chunk { background-color: #FF9800; }")
        else:
            self.cache_usage_bar.setStyleSheet("QProgressBar::chunk { background-color: #4CAF50; }")
