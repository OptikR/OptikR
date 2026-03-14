"""
Models Section

Language model browser: list, refresh, open, and delete downloaded models.
"""

import logging
import shutil
from pathlib import Path

from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QGroupBox,
    QLabel, QPushButton, QLineEdit, QMessageBox,
    QListWidget, QListWidgetItem,
)
from PyQt6.QtCore import Qt, pyqtSignal

from ui.common.file_utils import open_folder as _open_folder
from app.localization import TranslatableMixin, tr

logger = logging.getLogger(__name__)


class ModelsSection(TranslatableMixin, QWidget):
    """Language models browser: list, refresh, open, delete."""

    settingChanged = pyqtSignal()

    def __init__(self, config_manager=None, parent=None):
        super().__init__(parent)
        self.config_manager = config_manager
        self.models_list = None
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
        layout.setSpacing(0)

        group = QGroupBox()
        self.set_translatable_text(group, "storage_language_models_section")
        group_layout = QVBoxLayout(group)
        group_layout.setSpacing(12)
        group_layout.setContentsMargins(15, 20, 15, 15)

        models_desc = QLabel()
        self.set_translatable_text(models_desc, "models_description")
        models_desc.setWordWrap(True)
        models_desc.setStyleSheet("color: #666666; font-size: 9pt; margin-bottom: 10px;")
        group_layout.addWidget(models_desc)

        # HuggingFace cache location
        hf_cache_layout = QHBoxLayout()
        hf_cache_layout.setSpacing(10)

        hf_cache_label = self._create_label("", bold=True)
        self.set_translatable_text(hf_cache_label, "models_huggingface_cache_label")
        hf_cache_layout.addWidget(hf_cache_label)

        hf_cache_path = Path.home() / '.cache' / 'huggingface' / 'hub'
        hf_cache_edit = QLineEdit()
        hf_cache_edit.setText(str(hf_cache_path))
        hf_cache_edit.setReadOnly(True)
        hf_cache_edit.setStyleSheet("background-color: #2D2D2D;")
        hf_cache_layout.addWidget(hf_cache_edit)

        hf_open_btn = QPushButton()
        self.set_translatable_text(hf_open_btn, "storage_open_button_1")
        hf_open_btn.setProperty("class", "action")
        hf_open_btn.setMinimumWidth(80)
        hf_open_btn.clicked.connect(lambda: _open_folder(str(hf_cache_path), self))
        hf_cache_layout.addWidget(hf_open_btn)

        group_layout.addLayout(hf_cache_layout)

        # Downloaded models list
        models_label = self._create_label("", bold=True)
        self.set_translatable_text(models_label, "models_downloaded_marianmt_label")
        group_layout.addWidget(models_label)

        self.models_list = QListWidget()
        self.models_list.setMaximumHeight(150)
        group_layout.addWidget(self.models_list)

        # Model actions
        actions_layout = QHBoxLayout()
        actions_layout.setSpacing(10)

        refresh_models_btn = QPushButton()
        self.set_translatable_text(refresh_models_btn, "storage_refresh_button")
        refresh_models_btn.setProperty("class", "action")
        refresh_models_btn.setMinimumWidth(100)
        refresh_models_btn.clicked.connect(self._refresh_language_models)
        actions_layout.addWidget(refresh_models_btn)

        open_model_btn = QPushButton()
        self.set_translatable_text(open_model_btn, "storage_open_selected_button")
        open_model_btn.setProperty("class", "action")
        open_model_btn.setMinimumWidth(120)
        open_model_btn.clicked.connect(self._open_selected_model)
        actions_layout.addWidget(open_model_btn)

        delete_model_btn = QPushButton()
        self.set_translatable_text(delete_model_btn, "storage_delete_selected_button")
        delete_model_btn.setProperty("class", "action")
        delete_model_btn.setMinimumWidth(120)
        delete_model_btn.clicked.connect(self._delete_selected_model)
        actions_layout.addWidget(delete_model_btn)

        actions_layout.addStretch()
        group_layout.addLayout(actions_layout)

        model_info = QLabel()
        self.set_translatable_text(model_info, "models_info_note")
        model_info.setWordWrap(True)
        model_info.setStyleSheet("color: #2196F3; font-size: 9pt; margin-top: 10px;")
        group_layout.addWidget(model_info)

        layout.addWidget(group)

        self._refresh_language_models()

    def _refresh_language_models(self):
        """Refresh the language models list."""
        try:
            self.models_list.clear()

            cache_dir = Path.home() / '.cache' / 'huggingface' / 'hub'

            if not cache_dir.exists():
                item = QListWidgetItem(tr("models_no_models_found_warning"))
                item.setData(Qt.ItemDataRole.UserRole, None)
                self.models_list.addItem(item)
                return

            models_found = []

            for model_dir in cache_dir.iterdir():
                if model_dir.is_dir() and 'opus-mt-' in model_dir.name:
                    try:
                        parts = model_dir.name.split('--')
                        if len(parts) >= 3 and parts[1] == 'Helsinki-NLP':
                            model_name = parts[2]
                            lang_pair = model_name.replace('opus-mt-', '')

                            if '-' in lang_pair:
                                src, tgt = lang_pair.split('-', 1)

                                try:
                                    total_size = sum(
                                        f.stat().st_size
                                        for f in model_dir.rglob('*')
                                        if f.is_file()
                                    )
                                    size_mb = total_size / (1024 * 1024)
                                    size_str = f"{size_mb:.0f} MB"
                                except (OSError, PermissionError):
                                    size_str = "Unknown size"

                                models_found.append({
                                    'name': f"{src.upper()} → {tgt.upper()}",
                                    'size': size_str,
                                    'path': model_dir,
                                    'lang_pair': lang_pair
                                })
                    except Exception:
                        continue

            if not models_found:
                item = QListWidgetItem(tr("models_no_marianmt_found_warning"))
                item.setData(Qt.ItemDataRole.UserRole, None)
                self.models_list.addItem(item)
            else:
                models_found.sort(key=lambda x: x['lang_pair'])

                for model in models_found:
                    item_text = f"✅ {model['name']} - {model['size']}"
                    item = QListWidgetItem(item_text)
                    item.setData(Qt.ItemDataRole.UserRole, model['path'])
                    self.models_list.addItem(item)

                total_size = sum(
                    float(m['size'].replace(' MB', ''))
                    for m in models_found
                    if 'Unknown' not in m['size']
                )
                summary_item = QListWidgetItem(
                    f"📊 Total: {len(models_found)} models, {total_size:.0f} MB")
                summary_item.setData(Qt.ItemDataRole.UserRole, None)
                summary_item.setForeground(Qt.GlobalColor.darkGray)
                self.models_list.addItem(summary_item)

        except Exception as e:
            item = QListWidgetItem(f"❌ Error loading models: {str(e)}")
            item.setData(Qt.ItemDataRole.UserRole, None)
            self.models_list.addItem(item)

    def _open_selected_model(self):
        """Open the selected model directory in file explorer."""
        selected_items = self.models_list.selectedItems()
        if not selected_items:
            QMessageBox.warning(
                self, tr("models_no_selection_title"), tr("models_no_selection_open_message"))
            return

        model_path = selected_items[0].data(Qt.ItemDataRole.UserRole)
        if model_path:
            _open_folder(str(model_path), self)
        else:
            QMessageBox.information(
                self, tr("models_no_path_title"), tr("models_no_path_message"))

    def _delete_selected_model(self):
        """Delete the selected model from cache."""
        selected_items = self.models_list.selectedItems()
        if not selected_items:
            QMessageBox.warning(
                self, tr("models_no_selection_title"), tr("models_no_selection_delete_message"))
            return

        model_path = selected_items[0].data(Qt.ItemDataRole.UserRole)
        if not model_path:
            QMessageBox.information(
                self, tr("models_no_path_title"), tr("models_no_path_delete_message"))
            return

        model_name = selected_items[0].text().split(' - ')[0].replace('✅ ', '')

        reply = QMessageBox.question(
            self,
            tr("models_confirm_delete_title"),
            tr("models_confirm_delete_message").format(model_name=model_name),
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            QMessageBox.StandardButton.No
        )

        if reply == QMessageBox.StandardButton.Yes:
            try:
                shutil.rmtree(model_path)
                QMessageBox.information(
                    self,
                    tr("models_deleted_title"),
                    tr("models_deleted_message").format(model_name=model_name)
                )
                self._refresh_language_models()
                self.settingChanged.emit()
            except Exception as e:
                QMessageBox.critical(
                    self,
                    tr("models_delete_failed_title"),
                    tr("models_delete_failed_message").format(error=str(e))
                )
