"""
Cache Section

Cache settings UI: enable/disable, size limit, directory, and clear operations.
"""

import logging
import os
import shutil
from pathlib import Path

from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QGridLayout, QGroupBox,
    QLabel, QCheckBox, QPushButton, QLineEdit,
    QFileDialog, QMessageBox,
)
from PyQt6.QtCore import Qt, pyqtSignal, QFileInfo

from ui.common.widgets.custom_spinbox import CustomSpinBox
from ui.common.file_utils import open_folder as _open_folder
from app.localization import TranslatableMixin, tr

logger = logging.getLogger(__name__)


class CacheSection(TranslatableMixin, QWidget):
    """Cache settings: enable/disable, size limit, directory, clear operations."""

    settingChanged = pyqtSignal()
    cacheCleared = pyqtSignal()

    def __init__(self, config_manager=None, pipeline=None, parent=None):
        super().__init__(parent)
        self.config_manager = config_manager
        self.pipeline = pipeline

        self.cache_enabled_check = None
        self.cache_size_spinbox = None
        self.cache_dir_edit = None
        self.clear_cache_btn = None
        self.clear_all_cache_btn = None
        self.periodic_clear_check = None

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
        self.set_translatable_text(group, "storage_cache_settings_section")
        group_layout = QVBoxLayout(group)
        group_layout.setSpacing(12)
        group_layout.setContentsMargins(15, 20, 15, 15)

        # Enable cache checkbox
        self.cache_enabled_check = QCheckBox()
        self.set_translatable_text(self.cache_enabled_check, "storage_enable_translation_cache_check")
        self.cache_enabled_check.setChecked(True)
        self.cache_enabled_check.stateChanged.connect(self._on_cache_enabled_changed)
        group_layout.addWidget(self.cache_enabled_check)

        cache_desc = QLabel()
        self.set_translatable_text(cache_desc, "cache_description")
        cache_desc.setWordWrap(True)
        cache_desc.setStyleSheet("color: #666666; font-size: 9pt; margin-top: 5px; margin-bottom: 10px;")
        group_layout.addWidget(cache_desc)

        # Cache size limit
        size_grid = QGridLayout()
        size_grid.setHorizontalSpacing(8)
        size_grid.setVerticalSpacing(8)
        size_grid.setContentsMargins(0, 5, 0, 5)
        size_grid.setColumnStretch(2, 1)

        size_label = self._create_label("", bold=True)
        self.set_translatable_text(size_label, "cache_size_limit_label")

        self.cache_size_spinbox = CustomSpinBox()
        self.cache_size_spinbox.setRange(100, 5000)
        self.cache_size_spinbox.setValue(500)
        self.cache_size_spinbox.setSuffix("MB")
        self.cache_size_spinbox.setSingleStep(100)
        self.cache_size_spinbox.setMinimumWidth(120)
        self.cache_size_spinbox.valueChanged.connect(self._on_change)

        size_grid.addWidget(size_label, 0, 0)
        size_grid.addWidget(self.cache_size_spinbox, 0, 1)
        group_layout.addLayout(size_grid)

        # Cache directory
        cache_dir_layout = QHBoxLayout()
        cache_dir_layout.setSpacing(10)

        cache_dir_label = self._create_label("", bold=True)
        self.set_translatable_text(cache_dir_label, "cache_directory_label")
        cache_dir_layout.addWidget(cache_dir_label)

        self.cache_dir_edit = QLineEdit()
        self.cache_dir_edit.setText("./cache")
        self.set_translatable_text(self.cache_dir_edit, "cache_directory_placeholder", method="setPlaceholderText")
        self.cache_dir_edit.textChanged.connect(self._on_change)
        cache_dir_layout.addWidget(self.cache_dir_edit)

        cache_browse_btn = QPushButton()
        self.set_translatable_text(cache_browse_btn, "storage_browse_button")
        cache_browse_btn.setProperty("class", "action")
        cache_browse_btn.setMinimumWidth(80)
        cache_browse_btn.clicked.connect(
            lambda: self._browse_directory(self.cache_dir_edit, tr("cache_select_directory_dialog")))
        cache_dir_layout.addWidget(cache_browse_btn)

        cache_open_btn = QPushButton()
        self.set_translatable_text(cache_open_btn, "storage_open_button")
        cache_open_btn.setProperty("class", "action")
        cache_open_btn.setMinimumWidth(80)
        cache_open_btn.clicked.connect(lambda: _open_folder(self.cache_dir_edit.text(), self))
        cache_dir_layout.addWidget(cache_open_btn)

        group_layout.addLayout(cache_dir_layout)

        # Clear cache buttons
        clear_layout = QHBoxLayout()
        clear_layout.setSpacing(10)

        self.clear_cache_btn = QPushButton()
        self.set_translatable_text(self.clear_cache_btn, "storage_clear_translation_cache_button")
        self.clear_cache_btn.setProperty("class", "action")
        self.clear_cache_btn.setMinimumWidth(160)
        self.clear_cache_btn.clicked.connect(self._clear_cache)
        clear_layout.addWidget(self.clear_cache_btn)

        self.clear_all_cache_btn = QPushButton()
        self.set_translatable_text(self.clear_all_cache_btn, "storage_clear_all_caches_button")
        self.clear_all_cache_btn.setProperty("class", "action")
        self.clear_all_cache_btn.setMinimumWidth(140)
        self.clear_all_cache_btn.setStyleSheet("""
            QPushButton {
                background-color: #D32F2F;
                color: white;
            }
            QPushButton:hover {
                background-color: #F44336;
            }
        """)
        self.clear_all_cache_btn.clicked.connect(self._clear_all_caches)
        clear_layout.addWidget(self.clear_all_cache_btn)

        clear_layout.addStretch()

        clear_desc = QLabel()
        self.set_translatable_text(clear_desc, "cache_clear_description")
        clear_desc.setStyleSheet("color: #666666; font-size: 9pt;")
        clear_layout.addWidget(clear_desc)

        group_layout.addLayout(clear_layout)

        # Periodic cache clear
        self.periodic_clear_check = QCheckBox()
        self.set_translatable_text(
            self.periodic_clear_check, "storage_periodic_cache_clear_check")
        self.periodic_clear_check.setChecked(False)
        self.periodic_clear_check.stateChanged.connect(self._on_change)
        group_layout.addWidget(self.periodic_clear_check)

        periodic_desc = QLabel()
        self.set_translatable_text(periodic_desc, "storage_periodic_cache_clear_desc")
        periodic_desc.setWordWrap(True)
        periodic_desc.setStyleSheet(
            "color: #666666; font-size: 9pt; margin-top: 2px; margin-bottom: 5px;")
        group_layout.addWidget(periodic_desc)

        layout.addWidget(group)

    def _on_change(self):
        self.settingChanged.emit()

    def _on_cache_enabled_changed(self, state):
        """Handle cache enabled checkbox state change."""
        enabled = state == Qt.CheckState.Checked.value
        self.cache_size_spinbox.setEnabled(enabled)
        self.cache_dir_edit.setEnabled(enabled)
        self.clear_cache_btn.setEnabled(enabled)
        self.settingChanged.emit()

    def _browse_directory(self, line_edit: QLineEdit, title: str):
        """Open directory browser dialog."""
        current_dir = line_edit.text() or "."
        directory = QFileDialog.getExistingDirectory(
            self, title, current_dir,
            QFileDialog.Option.ShowDirsOnly
        )
        if directory:
            line_edit.setText(directory)
            self.settingChanged.emit()

    def calculate_cache_size(self) -> tuple[float, int]:
        """
        Calculate the current cache size.

        Returns:
            Tuple of (size_in_mb, file_count)
        """
        try:
            cache_path = self.cache_dir_edit.text().strip()
            if not cache_path:
                return (0.0, 0)

            file_info = QFileInfo(cache_path)
            if not file_info.exists() or not file_info.isDir():
                return (0.0, 0)

            cache_dir = Path(cache_path)
            total_size = 0
            file_count = 0

            for item in cache_dir.rglob('*'):
                if item.is_file():
                    try:
                        total_size += item.stat().st_size
                        file_count += 1
                    except (OSError, PermissionError):
                        pass

            size_mb = total_size / (1024 * 1024)
            return (size_mb, file_count)

        except Exception as e:
            logger.warning("Failed to calculate cache size: %s", e)
            return (0.0, 0)

    def clear_cache(self) -> bool:
        """
        Clear the cache directory after confirmation.

        Returns:
            True if cache was cleared successfully, False otherwise
        """
        try:
            cache_path = self.cache_dir_edit.text().strip()
            file_info = QFileInfo(cache_path)

            if not file_info.exists():
                QMessageBox.information(
                    self, tr("cache_empty_title"),
                    tr("cache_empty_not_exist_message").format(path=cache_path)
                )
                return False

            if not file_info.isDir():
                QMessageBox.warning(
                    self, tr("cache_invalid_path_title"),
                    tr("cache_invalid_path_message").format(path=cache_path)
                )
                return False

            size_mb, file_count = self.calculate_cache_size()

            if file_count == 0:
                QMessageBox.information(
                    self, tr("cache_empty_title"),
                    tr("cache_empty_already_message")
                )
                return False

            reply = QMessageBox.warning(
                self, tr("cache_clear_confirm_title"),
                tr("cache_clear_confirm_message").format(
                    size_mb=f"{size_mb:.1f}", file_count=file_count, cache_path=cache_path
                ),
                QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
                QMessageBox.StandardButton.No
            )

            if reply != QMessageBox.StandardButton.Yes:
                return False

            cache_dir = Path(cache_path)
            deleted_count = 0
            failed_count = 0

            for item in cache_dir.iterdir():
                try:
                    if item.is_file():
                        item.unlink()
                        deleted_count += 1
                    elif item.is_dir():
                        shutil.rmtree(item)
                        deleted_count += 1
                except Exception as e:
                    logger.warning("Failed to delete %s: %s", item, e)
                    failed_count += 1

            self.cacheCleared.emit()

            if failed_count > 0:
                QMessageBox.warning(
                    self, tr("cache_partially_cleared_title"),
                    tr("cache_partially_cleared_message").format(
                        deleted_count=deleted_count, failed_count=failed_count, cache_path=cache_path
                    )
                )
            else:
                QMessageBox.information(
                    self, tr("cache_cleared_title"),
                    tr("cache_cleared_message").format(
                        deleted_count=deleted_count, size_mb=f"{size_mb:.1f}", cache_path=cache_path
                    )
                )

            logger.info("Cache cleared: %d items deleted, %d failed from %s",
                        deleted_count, failed_count, cache_path)
            return True

        except Exception as e:
            QMessageBox.critical(
                self, tr("cache_clear_failed_title"),
                tr("cache_clear_failed_message").format(error=str(e))
            )
            logger.error("Failed to clear cache: %s", e, exc_info=True)
            return False

    @staticmethod
    def _delete_persistent_translation_cache() -> bool:
        """Remove the on-disk translation cache file."""
        try:
            from app.utils.path_utils import get_cache_dir
            cache_file = get_cache_dir() / "translation_cache.json.gz"
            if cache_file.exists():
                cache_file.unlink()
                logger.info("Deleted persistent translation cache: %s", cache_file)
                return True
        except Exception as e:
            logger.warning("Could not delete persistent translation cache: %s", e)
        return False

    def _clear_cache(self):
        """Handle clear cache button click — clears translation cache plugin."""
        if hasattr(self, 'pipeline') and self.pipeline:
            try:
                if hasattr(self.pipeline, 'translation_cache') and self.pipeline.translation_cache:
                    logger.info("Clearing translation_cache plugin...")
                    self.pipeline.translation_cache.clear()
                    logger.info("Translation cache plugin cleared")

                if hasattr(self.pipeline, 'cache_manager') and self.pipeline.cache_manager:
                    logger.info("Clearing cache_manager...")
                    self.pipeline.cache_manager.clear_all(clear_dictionary=False)
                    logger.info("Cache manager cleared")

                self._delete_persistent_translation_cache()

                QMessageBox.information(
                    self, tr("cache_cleared_title"),
                    tr("cache_cleared_plugin_message")
                )
            except Exception as e:
                logger.error("Failed to clear translation cache: %s", e, exc_info=True)
                QMessageBox.warning(
                    self, tr("cache_clear_failed_title"),
                    tr("cache_clear_failed_plugin_message").format(error=str(e))
                )
        else:
            self._delete_persistent_translation_cache()
            self.clear_cache()

    def _clear_all_caches(self):
        """Clear all caches including Python bytecode, translation cache, and temp files."""
        try:
            reply = QMessageBox.warning(
                self, tr("cache_clear_all_title"),
                tr("cache_clear_all_confirm_message"),
                QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
                QMessageBox.StandardButton.No
            )

            if reply != QMessageBox.StandardButton.Yes:
                return

            from PyQt6.QtWidgets import QProgressDialog

            progress = QProgressDialog(
                tr("cache_clearing_all_progress"), tr("cache_cancel_button"), 0, 100, self)
            progress.setWindowTitle(tr("cache_clearing_caches_window_title"))
            progress.setWindowModality(Qt.WindowModality.WindowModal)
            progress.setMinimumDuration(0)
            progress.setValue(0)

            deleted_count = 0
            failed_count = 0

            # 1. Translation cache plugin + persistent cache file
            progress.setLabelText(tr("cache_clearing_translation_plugin"))
            progress.setValue(5)

            if hasattr(self, 'pipeline') and self.pipeline:
                try:
                    if hasattr(self.pipeline, 'translation_cache') and self.pipeline.translation_cache:
                        logger.info("Clearing translation_cache plugin...")
                        self.pipeline.translation_cache.clear()
                        deleted_count += 1

                    if hasattr(self.pipeline, 'cache_manager') and self.pipeline.cache_manager:
                        logger.info("Clearing cache_manager...")
                        self.pipeline.cache_manager.clear_all(clear_dictionary=False)
                        deleted_count += 1
                except Exception as e:
                    logger.error("Error clearing plugin caches: %s", e)
                    failed_count += 1

            if self._delete_persistent_translation_cache():
                deleted_count += 1

            progress.setValue(15)

            # 2. Cache directory
            progress.setLabelText(tr("cache_clearing_cache_directory"))

            cache_path = Path(self.cache_dir_edit.text().strip())
            if cache_path.exists() and cache_path.is_dir():
                for item in cache_path.iterdir():
                    try:
                        if item.is_file():
                            item.unlink()
                            deleted_count += 1
                        elif item.is_dir():
                            shutil.rmtree(item)
                            deleted_count += 1
                    except Exception as e:
                        logger.warning("Failed to delete %s: %s", item, e)
                        failed_count += 1

            progress.setValue(30)

            # 3. Python bytecode (scoped to app/ and ui/ only)
            progress.setLabelText(tr("cache_clearing_bytecode"))

            from app.utils.path_utils import get_app_root, get_dir
            app_root = get_app_root()

            for scope_dir in [app_root / 'app', app_root / 'ui']:
                if not scope_dir.exists():
                    continue
                for pycache_dir in scope_dir.rglob('__pycache__'):
                    try:
                        shutil.rmtree(pycache_dir)
                        deleted_count += 1
                    except Exception as e:
                        logger.warning("Failed to delete %s: %s", pycache_dir, e)
                        failed_count += 1

            progress.setValue(60)

            # 4. Temp directory
            progress.setLabelText(tr("cache_clearing_temp_files"))

            temp_path = get_dir("temp")
            if temp_path.exists() and temp_path.is_dir():
                for item in temp_path.iterdir():
                    try:
                        if item.is_file():
                            item.unlink()
                            deleted_count += 1
                        elif item.is_dir():
                            shutil.rmtree(item)
                            deleted_count += 1
                    except Exception as e:
                        logger.warning("Failed to delete %s: %s", item, e)
                        failed_count += 1

            progress.setValue(80)

            # 5. Old log files (>7 days)
            progress.setLabelText(tr("cache_clearing_old_logs"))

            logs_path = get_dir("logs")
            if logs_path.exists() and logs_path.is_dir():
                import time
                current_time = time.time()
                for log_file in logs_path.glob('*.log'):
                    try:
                        if log_file.is_file():
                            file_age = current_time - log_file.stat().st_mtime
                            if file_age > (7 * 24 * 60 * 60):
                                log_file.unlink()
                                deleted_count += 1
                    except Exception as e:
                        logger.warning("Failed to delete %s: %s", log_file, e)
                        failed_count += 1

            progress.setValue(100)
            progress.close()

            QMessageBox.information(
                self, tr("cache_all_cleared_title"),
                tr("cache_all_cleared_message").format(
                    deleted_count=deleted_count, failed_count=failed_count
                )
            )

            logger.info("All caches cleared: %d items deleted, %d failed",
                        deleted_count, failed_count)

        except Exception as e:
            QMessageBox.critical(
                self, tr("cache_clear_failed_title"),
                tr("cache_clear_all_failed_message").format(error=str(e)),
            )
            logger.error("Failed to clear all caches: %s", e, exc_info=True)
