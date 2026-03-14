"""
OCR Model Manager UI — powered by ModelCatalog.

Provides a dialog for managing OCR models using the unified ModelCatalog
backend.  Displays language coverage, size, GPU requirement, and rationale
from ``ModelMetadata`` for every OCR engine.
"""

import logging
from pathlib import Path

from PyQt6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel, QPushButton, QTreeWidget,
    QTreeWidgetItem, QComboBox, QGroupBox, QMessageBox
)
from PyQt6.QtCore import Qt

from app.localization import tr
from app.core.model_catalog import ModelCatalog
from app.core.model_catalog_types import ModelEntry, ModelMetadata, ModelStatus

logger = logging.getLogger(__name__)


class OCRModelManager:
    """OCR Model Manager UI component backed by ModelCatalog."""

    def __init__(self, parent=None, **kwargs):
        self.parent = parent

    def show_ocr_model_manager(self):
        """Show OCR model management dialog."""
        dialog = QDialog(self.parent)
        dialog.setWindowTitle(tr("model_mgr_title"))
        dialog.setMinimumSize(1000, 700)
        dialog.resize(1000, 700)

        main_layout = QVBoxLayout(dialog)
        main_layout.setContentsMargins(20, 20, 20, 20)
        main_layout.setSpacing(15)

        catalog = ModelCatalog.instance()

        # Get pipeline from parent for runtime engine status
        pipeline = None
        parent = self.parent
        while parent:
            if hasattr(parent, 'pipeline') and parent.pipeline:
                pipeline = parent.pipeline
                break
            parent = parent.parent() if hasattr(parent, 'parent') else None

        # Header
        header_layout = QVBoxLayout()

        title_row = QHBoxLayout()
        title_label = QLabel(tr("model_mgr_title"))
        title_label.setStyleSheet("font-size: 14pt; font-weight: bold;")
        title_row.addWidget(title_label)
        title_row.addStretch()
        header_layout.addLayout(title_row)

        info_row = QHBoxLayout()
        cache_info = catalog.get_cache_info()
        template = tr("model_mgr_cache_info")
        info_values = {
            "path": str(getattr(catalog, "_hf_cache", Path.home() / ".cache")),
            "size": f"{cache_info.total_size_mb:.1f} MB",
            "models": cache_info.total_models,
            "disk": f"{cache_info.total_size_mb:.1f}",
            "available": f"{cache_info.available_space_gb:.1f}",
        }

        class _SafeDict(dict):
            def __missing__(self, key):
                return "{" + key + "}"

        info_text = template.format_map(_SafeDict(info_values))
        info_label = QLabel(info_text)
        info_label.setStyleSheet("color: #666666; font-size: 9pt;")
        info_row.addWidget(info_label)
        info_row.addStretch()
        header_layout.addLayout(info_row)

        main_layout.addLayout(header_layout)

        # Models tree with metadata columns
        models_tree = QTreeWidget()
        models_tree.setHeaderLabels([
            tr("model_mgr_col_model_name"), tr("model_mgr_col_family"),
            tr("model_mgr_col_languages"), tr("model_mgr_col_size"),
            tr("model_mgr_col_speed"), tr("model_mgr_col_quality"),
            tr("model_mgr_col_gpu"), tr("model_mgr_col_status"),
            tr("model_mgr_col_rationale"),
        ])
        models_tree.setColumnWidth(0, 180)
        models_tree.setColumnWidth(1, 100)
        models_tree.setColumnWidth(2, 120)
        models_tree.setColumnWidth(3, 80)
        models_tree.setColumnWidth(4, 70)
        models_tree.setColumnWidth(5, 70)
        models_tree.setColumnWidth(6, 50)
        models_tree.setColumnWidth(7, 100)
        models_tree.setColumnWidth(8, 250)
        models_tree.setAlternatingRowColors(True)
        main_layout.addWidget(models_tree)

        # Determine which engine is currently loaded at runtime
        current_engine = None
        runtime_engines: list = []
        if pipeline:
            try:
                if hasattr(pipeline, 'get_current_ocr_engine'):
                    current_engine = pipeline.get_current_ocr_engine()
                if hasattr(pipeline, 'get_available_ocr_engines'):
                    runtime_engines = pipeline.get_available_ocr_engines()
            except Exception:
                pass

        def _engine_display_status(entry: ModelEntry) -> str:
            """Derive a human-readable status string."""
            meta = entry.metadata
            family_lower = meta.family.lower().replace(" ", "")

            is_runtime = any(
                family_lower == e.lower().replace(" ", "")
                for e in runtime_engines
            )
            if current_engine and family_lower == current_engine.lower().replace(" ", ""):
                return tr("model_mgr_status_loaded")
            if is_runtime:
                return tr("model_mgr_status_available")
            if entry.status.downloaded:
                return tr("model_mgr_status_downloaded")
            return tr("model_mgr_status_not_installed")

        def refresh_models():
            """Populate the tree from ModelCatalog."""
            models_tree.clear()

            # Section 1: Catalog OCR models (with full metadata)
            catalog_header = QTreeWidgetItem([tr("model_mgr_catalog_header"), "", "", "", "", "", "", "", ""])
            catalog_header.setFirstColumnSpanned(True)
            font = catalog_header.font(0)
            font.setBold(True)
            catalog_header.setFont(0, font)
            models_tree.addTopLevelItem(catalog_header)

            entries = catalog.list_available("ocr")
            if not entries:
                item = QTreeWidgetItem([tr("model_mgr_no_catalog_models"), "", "", "", "", "", "", "", ""])
                item.setForeground(0, Qt.GlobalColor.darkGray)
                models_tree.addTopLevelItem(item)
            else:
                for entry in entries:
                    meta = entry.metadata
                    lang_list = ", ".join(meta.languages[:5])
                    if len(meta.languages) > 5:
                        lang_list += tr("model_mgr_langs_more").format(count=len(meta.languages) - 5)

                    status = _engine_display_status(entry)

                    item = QTreeWidgetItem([
                        f"  {meta.family}",
                        meta.family,
                        tr("model_mgr_langs_format").format(count=len(meta.languages), list=lang_list),
                        f"{meta.size_mb:.0f} MB",
                        meta.speed,
                        meta.quality,
                        tr("model_mgr_gpu_yes") if meta.gpu_required else tr("model_mgr_gpu_no"),
                        status,
                        meta.rationale,
                    ])
                    item.setToolTip(2, ", ".join(meta.languages))
                    item.setToolTip(8, meta.rationale)
                    item.setData(0, Qt.ItemDataRole.UserRole, entry.model_id)
                    models_tree.addTopLevelItem(item)

            # Section 2: Custom / imported OCR models
            custom_header = QTreeWidgetItem([tr("model_mgr_custom_header"), "", "", "", "", "", "", "", ""])
            custom_header.setFirstColumnSpanned(True)
            font = custom_header.font(0)
            font.setBold(True)
            custom_header.setFont(0, font)
            models_tree.addTopLevelItem(custom_header)

            custom_entries = [
                e for e in catalog.list_available("ocr")
                if e.model_id.startswith("custom-") or e.model_id.startswith("imported-")
            ]
            if not custom_entries:
                item = QTreeWidgetItem([tr("model_mgr_no_custom_models"), "", "", "", "", "", "", "", ""])
                item.setForeground(0, Qt.GlobalColor.darkGray)
                models_tree.addTopLevelItem(item)
            else:
                for entry in custom_entries:
                    meta = entry.metadata
                    item = QTreeWidgetItem([
                        f"  {entry.model_id}",
                        meta.family,
                        ", ".join(meta.languages),
                        f"{meta.size_mb:.0f} MB",
                        meta.speed,
                        meta.quality,
                        tr("model_mgr_gpu_yes") if meta.gpu_required else tr("model_mgr_gpu_no"),
                        tr("model_mgr_downloaded") if entry.status.downloaded else tr("model_mgr_available"),
                        meta.rationale,
                    ])
                    item.setData(0, Qt.ItemDataRole.UserRole, entry.model_id)
                    models_tree.addTopLevelItem(item)

            models_tree.expandAll()

        refresh_models()

        # Action buttons
        action_layout = QHBoxLayout()

        refresh_btn = QPushButton(tr("model_mgr_refresh"))
        refresh_btn.clicked.connect(refresh_models)
        action_layout.addWidget(refresh_btn)

        import_btn = QPushButton(tr("model_mgr_import_custom"))
        import_btn.setProperty("class", "action")
        import_btn.setToolTip(tr("model_mgr_import_tooltip"))
        import_btn.clicked.connect(lambda: self._import_ocr_model(dialog, catalog, refresh_models))
        action_layout.addWidget(import_btn)

        register_btn = QPushButton(tr("model_mgr_register_plugin"))
        register_btn.setProperty("class", "action")
        register_btn.setToolTip(tr("model_mgr_register_tooltip"))
        register_btn.clicked.connect(
            lambda: self._register_selected_plugin(dialog, catalog, models_tree, refresh_models)
        )
        action_layout.addWidget(register_btn)

        delete_btn = QPushButton(tr("model_mgr_delete"))
        delete_btn.setProperty("class", "action")
        delete_btn.clicked.connect(
            lambda: self._delete_selected_model(dialog, catalog, models_tree, refresh_models)
        )
        action_layout.addWidget(delete_btn)

        action_layout.addStretch()

        close_btn = QPushButton(tr("model_mgr_close"))
        close_btn.clicked.connect(dialog.accept)
        action_layout.addWidget(close_btn)

        main_layout.addLayout(action_layout)

        dialog.exec()

    # ------------------------------------------------------------------
    # Actions
    # ------------------------------------------------------------------

    def _import_ocr_model(self, parent_dialog, catalog, refresh_callback):
        """Import a local OCR model directory via ModelCatalog."""
        from PyQt6.QtWidgets import QFileDialog

        path = QFileDialog.getExistingDirectory(
            parent_dialog,
            tr("model_mgr_select_directory"),
        )
        if not path:
            return

        try:
            success = catalog.import_model(path)
            if success:
                QMessageBox.information(
                    parent_dialog,
                    tr("model_mgr_import_successful"),
                    tr("model_mgr_import_successful_msg").format(path=path),
                )
                refresh_callback()
            else:
                QMessageBox.critical(
                    parent_dialog,
                    tr("model_mgr_import_failed"),
                    tr("model_mgr_import_failed_msg").format(path=path),
                )
        except Exception as e:
            QMessageBox.critical(
                parent_dialog, tr("model_mgr_error"), tr("model_mgr_import_error_msg").format(error=e),
            )

    def _register_selected_plugin(self, parent_dialog, catalog, models_tree, refresh_callback):
        """Register/enable the plugin for the selected OCR model."""
        selected = models_tree.selectedItems()
        if not selected:
            QMessageBox.warning(parent_dialog, tr("model_mgr_no_selection"), tr("model_mgr_select_model_first"))
            return

        model_id = selected[0].data(0, Qt.ItemDataRole.UserRole)
        if not model_id:
            return

        try:
            success = catalog.register_plugin(model_id)
            if success:
                QMessageBox.information(
                    parent_dialog,
                    tr("model_mgr_plugin_registered"),
                    tr("model_mgr_plugin_active_msg").format(model_id=model_id),
                )
                refresh_callback()
            else:
                status = catalog.get_status(model_id)
                if not status.downloaded:
                    QMessageBox.warning(
                        parent_dialog,
                        tr("model_mgr_not_downloaded"),
                        tr("model_mgr_not_downloaded_msg").format(model_id=model_id),
                    )
                else:
                    QMessageBox.critical(
                        parent_dialog,
                        tr("model_mgr_registration_failed"),
                        tr("model_mgr_registration_failed_msg").format(model_id=model_id),
                    )
        except Exception as e:
            QMessageBox.critical(parent_dialog, tr("model_mgr_error"), tr("model_mgr_registration_error_msg").format(error=e))

    def _delete_selected_model(self, parent_dialog, catalog, models_tree, refresh_callback):
        """Delete the selected OCR model."""
        selected = models_tree.selectedItems()
        if not selected:
            QMessageBox.warning(parent_dialog, tr("model_mgr_no_selection"), tr("model_mgr_select_model_first"))
            return

        model_id = selected[0].data(0, Qt.ItemDataRole.UserRole)
        if not model_id:
            return

        reply = QMessageBox.question(
            parent_dialog,
            tr("model_mgr_confirm_delete"),
            tr("model_mgr_confirm_delete_msg").format(model_id=model_id),
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            QMessageBox.StandardButton.No,
        )
        if reply != QMessageBox.StandardButton.Yes:
            return

        try:
            if catalog.delete(model_id):
                QMessageBox.information(parent_dialog, tr("model_mgr_deleted"), tr("model_mgr_deleted_msg").format(model_id=model_id))
                refresh_callback()
            else:
                QMessageBox.warning(
                    parent_dialog,
                    tr("model_mgr_not_downloaded"),
                    tr("model_mgr_not_downloaded_delete_msg").format(model_id=model_id),
                )
        except Exception as e:
            QMessageBox.critical(parent_dialog, tr("model_mgr_error"), tr("model_mgr_delete_error_msg").format(error=e))
