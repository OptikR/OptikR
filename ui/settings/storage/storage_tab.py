"""
Storage Settings Tab

Main container composing CacheSection, ModelsSection, and UsageSection.
Handles config load/save, validation, and cross-section coordination.
"""

import logging

from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QGroupBox,
    QLabel, QMessageBox,
)
from PyQt6.QtCore import Qt, pyqtSignal, QFileInfo, QDir

from ui.common.widgets.scroll_area_no_wheel import ScrollAreaNoWheel
from app.localization import TranslatableMixin, tr
from app.utils.path_utils import get_relative_path

from .cache_section import CacheSection
from .models_section import ModelsSection
from .usage_section import UsageSection

logger = logging.getLogger(__name__)


class StorageSettingsTab(TranslatableMixin, QWidget):
    """Storage settings including cache, directories, and retention policies."""

    settingChanged = pyqtSignal()

    def __init__(self, config_manager=None, pipeline=None, parent=None):
        """Initialize the Storage settings tab."""
        super().__init__(parent)

        self.config_manager = config_manager
        self.pipeline = pipeline

        self._original_state = {}

        self._init_ui()

    # ------------------------------------------------------------------
    # UI construction
    # ------------------------------------------------------------------

    def _init_ui(self):
        """Initialize the UI."""
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.setSpacing(0)

        scroll_area = ScrollAreaNoWheel()
        scroll_area.setWidgetResizable(True)
        scroll_area.setFrameShape(ScrollAreaNoWheel.Shape.NoFrame)
        scroll_area.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        scroll_area.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAsNeeded)

        content_widget = QWidget()
        content_layout = QVBoxLayout(content_widget)
        content_layout.setContentsMargins(5, 5, 5, 5)
        content_layout.setSpacing(10)

        # Sections
        self.cache_section = CacheSection(
            config_manager=self.config_manager, pipeline=self.pipeline)
        self.models_section = ModelsSection(config_manager=self.config_manager)
        self.usage_section = UsageSection(config_manager=self.config_manager)

        # Preserve original layout order:
        #   1. Storage overview  2. Cache  3. Models
        #   4. Dict redirect  5. Locations  6. Retention  7. Usage display
        self._create_storage_overview_section(content_layout)
        content_layout.addWidget(self.cache_section)
        content_layout.addWidget(self.models_section)
        content_layout.addWidget(self.usage_section)

        content_layout.addStretch()

        scroll_area.setWidget(content_widget)
        main_layout.addWidget(scroll_area)

        # Connect section signals
        self.cache_section.settingChanged.connect(self.on_change)
        self.cache_section.cacheCleared.connect(self._calculate_storage_usage)
        self.models_section.settingChanged.connect(self.on_change)
        self.usage_section.settingChanged.connect(self.on_change)
        self.usage_section.refresh_usage_btn.clicked.connect(self._calculate_storage_usage)

        # Initial usage calculation
        self._calculate_storage_usage()

    def _create_storage_overview_section(self, parent_layout):
        """Create storage overview section showing all file locations."""
        group = QGroupBox()
        self.set_translatable_text(group, "storage_storage_overview_section")
        layout = QVBoxLayout(group)
        layout.setSpacing(8)
        layout.setContentsMargins(15, 20, 15, 15)

        overview_desc = QLabel(tr("storage_overview_description"))
        overview_desc.setWordWrap(True)
        overview_desc.setStyleSheet("color: #666666; font-size: 9pt; margin-bottom: 10px;")
        layout.addWidget(overview_desc)

        locations_widget = QWidget()
        locations_layout = QVBoxLayout(locations_widget)
        locations_layout.setSpacing(6)
        locations_layout.setContentsMargins(10, 10, 10, 10)
        locations_widget.setStyleSheet("QWidget { background-color: #2D2D2D; border-radius: 4px; }")

        file_locations = [
            (tr("storage_location_config_files"), "user_data/config", tr("storage_location_config_desc")),
            (tr("storage_location_cache"), "system_data/cache", tr("storage_location_cache_desc")),
            (tr("storage_location_dictionary"), "user_data/learned/translations", tr("storage_location_dictionary_desc")),
            (tr("storage_location_ai_models"), "system_data/ai_models", tr("storage_location_ai_models_desc")),
            (tr("storage_location_data"), "user_data", tr("storage_location_data_desc")),
            (tr("storage_location_logs"), "system_data/logs", tr("storage_location_logs_desc")),
            (tr("storage_location_styles"), "app/styles", tr("storage_location_styles_desc")),
            (tr("storage_location_plugins"), "plugins", tr("storage_location_plugins_desc")),
        ]

        for icon_name, path, description in file_locations:
            entry_layout = QHBoxLayout()
            entry_layout.setSpacing(8)

            name_label = QLabel(icon_name)
            name_label.setStyleSheet("font-weight: 600; font-size: 9pt; min-width: 120px;")
            entry_layout.addWidget(name_label)

            path_label = QLabel(path)
            path_label.setStyleSheet(
                "font-family: 'Consolas', 'Courier New', monospace; font-size: 9pt; "
                "color: #2196F3; min-width: 100px;"
            )
            entry_layout.addWidget(path_label)

            desc_label = QLabel(description)
            desc_label.setStyleSheet("font-size: 8pt; color: #666666;")
            desc_label.setWordWrap(True)
            entry_layout.addWidget(desc_label, 1)

            locations_layout.addLayout(entry_layout)

        layout.addWidget(locations_widget)

        info_note = QLabel(tr("storage_paths_relative_note"))
        info_note.setWordWrap(True)
        info_note.setStyleSheet("color: #2196F3; font-size: 9pt; margin-top: 10px;")
        layout.addWidget(info_note)

        parent_layout.addWidget(group)

    # ------------------------------------------------------------------
    # Change tracking
    # ------------------------------------------------------------------

    def _get_current_state(self):
        """Get current state of all settings."""
        state = {}
        if self.cache_section.cache_enabled_check:
            state['cache_enabled'] = self.cache_section.cache_enabled_check.isChecked()
        if self.cache_section.cache_size_spinbox:
            state['cache_size'] = self.cache_section.cache_size_spinbox.value()
        if self.cache_section.cache_dir_edit:
            state['cache_dir'] = self.cache_section.cache_dir_edit.text()
        if self.cache_section.periodic_clear_check:
            state['periodic_clear'] = self.cache_section.periodic_clear_check.isChecked()
        if hasattr(self.usage_section, 'retention_spinbox') and self.usage_section.retention_spinbox:
            state['retention_days'] = self.usage_section.retention_spinbox.value()
        return state

    def on_change(self):
        """Called when any setting changes - always emits signal for main window to check."""
        self.settingChanged.emit()

    # ------------------------------------------------------------------
    # Cross-section coordination
    # ------------------------------------------------------------------

    def _calculate_storage_usage(self):
        """Calculate and display current storage usage."""
        try:
            size_mb, file_count = self.cache_section.calculate_cache_size()
            limit_mb = self.cache_section.cache_size_spinbox.value()
            self.usage_section.update_storage_usage(size_mb, limit_mb)
        except Exception as e:
            logger.warning("Failed to calculate storage usage: %s", e)
            self.usage_section.cache_usage_label.setText(tr("error_calculating_usage"))
            self.usage_section.cache_usage_bar.setValue(0)

    # ------------------------------------------------------------------
    # Public API proxies (backward compatibility)
    # ------------------------------------------------------------------

    def clear_cache(self) -> bool:
        """Clear the cache directory after confirmation."""
        return self.cache_section.clear_cache()

    def calculate_cache_size(self) -> tuple[float, int]:
        """Calculate the current cache size."""
        return self.cache_section.calculate_cache_size()

    # ------------------------------------------------------------------
    # Config load / save / validate
    # ------------------------------------------------------------------

    def load_config(self):
        """Load configuration from config manager."""
        if not self.config_manager:
            return

        try:
            self.blockSignals(True)

            # Cache settings
            cache_enabled = self.config_manager.get_setting('storage.cache_enabled', True)
            self.cache_section.cache_enabled_check.setChecked(cache_enabled)

            cache_size = self.config_manager.get_setting('storage.cache_size_mb', 500)
            self.cache_section.cache_size_spinbox.setValue(cache_size)

            self.cache_section.cache_dir_edit.setText(get_relative_path("cache"))

            periodic_clear = self.config_manager.get_setting(
                'storage.periodic_cache_clear_enabled', False)
            self.cache_section.periodic_clear_check.setChecked(periodic_clear)

            # Directory displays (read-only, from registry)
            if self.usage_section.dict_dir_edit is not None:
                self.usage_section.dict_dir_edit.setText(get_relative_path("dictionary"))

            if getattr(self.usage_section, 'config_dir_edit', None) is not None:
                self.usage_section.config_dir_edit.setText(get_relative_path("config"))

            self.usage_section.model_dir_edit.setText(get_relative_path("models"))

            if getattr(self.usage_section, 'logs_dir_edit', None) is not None:
                self.usage_section.logs_dir_edit.setText(get_relative_path("logs"))

            # Retention policy
            retention_days = self.config_manager.get_setting('storage.retention_days', 30)
            self.usage_section.retention_spinbox.setValue(retention_days)

            # Update cache controls enabled state
            self.cache_section.cache_size_spinbox.setEnabled(cache_enabled)
            self.cache_section.cache_dir_edit.setEnabled(cache_enabled)
            self.cache_section.clear_cache_btn.setEnabled(cache_enabled)

            self.blockSignals(False)

            self._calculate_storage_usage()

            self._original_state = self._get_current_state()

            logger.debug("Storage tab configuration loaded")

        except Exception as e:
            self.blockSignals(False)
            logger.warning("Failed to load storage tab config: %s", e, exc_info=True)

    def save_config(self):
        """
        Save configuration to config manager.

        Returns:
            tuple: (success: bool, error_message: str)
        """
        if not self.config_manager:
            return False, "Configuration manager not available"

        try:
            self.config_manager.set_setting(
                'storage.cache_enabled',
                self.cache_section.cache_enabled_check.isChecked())
            self.config_manager.set_setting(
                'storage.cache_size_mb',
                self.cache_section.cache_size_spinbox.value())

            self.config_manager.set_setting(
                'storage.retention_days',
                self.usage_section.retention_spinbox.value())

            self.config_manager.set_setting(
                'storage.periodic_cache_clear_enabled',
                self.cache_section.periodic_clear_check.isChecked())

            success, error_msg = self.config_manager.save_config()

            if not success:
                return False, error_msg

            self._original_state = self._get_current_state()

            logger.info("Storage tab configuration saved")
            return True, ""

        except Exception as e:
            error_msg = f"Failed to save settings: {e}"
            logger.error(error_msg, exc_info=True)
            return False, error_msg

    def validate(self) -> bool:
        """
        Validate settings using QFileInfo for directory path validation.

        Returns:
            True if settings are valid, False otherwise
        """
        try:
            if self.cache_section.cache_dir_edit is not None:
                cache_path = self.cache_section.cache_dir_edit.text().strip()
                if not cache_path:
                    QMessageBox.warning(self, tr("invalid_path"),
                                        tr("storage_cache_path_empty"))
                    return False
                if not self._validate_directory_path(cache_path, "Cache"):
                    return False

            if self.usage_section.model_dir_edit is not None:
                model_path = self.usage_section.model_dir_edit.text().strip()
                if not model_path:
                    QMessageBox.warning(self, tr("invalid_path"),
                                        tr("storage_model_path_empty"))
                    return False
                if not self._validate_directory_path(model_path, "Model"):
                    return False

            if self.cache_section.cache_size_spinbox is not None:
                cache_size = self.cache_section.cache_size_spinbox.value()
                if cache_size < 100:
                    QMessageBox.warning(self, tr("invalid_cache_size"),
                                        tr("storage_cache_size_min"))
                    return False

            if self.usage_section.retention_spinbox is not None:
                retention = self.usage_section.retention_spinbox.value()
                if retention < 1:
                    QMessageBox.warning(self, tr("invalid_retention_period"),
                                        tr("storage_retention_min"))
                    return False

            return True

        except Exception as e:
            QMessageBox.critical(
                self, tr("validation_error"),
                tr("storage_validation_failed", error=str(e))
            )
            return False

    def _validate_directory_path(self, path: str, dir_type: str) -> bool:
        """
        Validate a directory path using QFileInfo.

        Args:
            path: Directory path to validate
            dir_type: Type of directory (for error messages)

        Returns:
            True if path is valid, False otherwise
        """
        try:
            file_info = QFileInfo(path)

            if file_info.exists():
                if not file_info.isDir():
                    QMessageBox.warning(
                        self, tr("invalid_path"),
                        tr("storage_path_not_directory", dir_type=dir_type, path=path)
                    )
                    return False

                if not file_info.isWritable():
                    QMessageBox.warning(
                        self, tr("permission_denied"),
                        tr("storage_directory_not_writable", dir_type=dir_type, path=path)
                    )
                    return False

                return True
            else:
                qdir = QDir()
                if qdir.mkpath(path):
                    logger.info("Created %s directory: %s", dir_type.lower(), path)
                    return True
                else:
                    QMessageBox.warning(
                        self, tr("cannot_create_directory"),
                        tr("storage_cannot_create_directory", dir_type=dir_type, path=path)
                    )
                    return False

        except Exception as e:
            QMessageBox.warning(
                self, tr("invalid_path"),
                tr("storage_path_invalid", dir_type=dir_type, path=path, error=str(e))
            )
            return False
