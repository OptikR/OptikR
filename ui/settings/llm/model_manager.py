"""
LLM Model Manager UI — powered by ModelCatalog.

Provides a dialog for managing LLM models using the unified ModelCatalog
backend.  Displays size, speed, quality, GPU requirement, and rationale
from ``ModelMetadata`` for every LLM model entry.
"""

import logging

from PyQt6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QTreeWidget, QTreeWidgetItem, QGroupBox, QMessageBox,
)
from PyQt6.QtCore import Qt

from app.localization import tr
from app.core.model_catalog import ModelCatalog
from app.core.model_catalog_types import ModelEntry, ModelMetadata, ModelStatus

logger = logging.getLogger(__name__)


class LLMModelManager:
    """LLM Model Manager UI component backed by ModelCatalog."""

    def __init__(self, parent=None, **kwargs):
        self.parent = parent
        self.config_manager = kwargs.get("config_manager")

    def show_llm_model_manager(self):
        """Show LLM model management dialog."""
        dialog = QDialog(self.parent)
        dialog.setWindowTitle("LLM Model Manager")
        dialog.setMinimumSize(950, 600)
        dialog.resize(950, 600)

        main_layout = QVBoxLayout(dialog)
        main_layout.setContentsMargins(20, 20, 20, 20)
        main_layout.setSpacing(15)

        catalog = ModelCatalog.instance()

        # ── Header ────────────────────────────────────────────────────
        header_layout = QVBoxLayout()

        title_row = QHBoxLayout()
        title_label = QLabel("LLM Model Manager")
        title_label.setStyleSheet("font-size: 14pt; font-weight: bold;")
        title_row.addWidget(title_label)
        title_row.addStretch()
        header_layout.addLayout(title_row)

        cache_info = catalog.get_cache_info()
        info_text = (
            f"Models cached: {cache_info.total_models}  |  "
            f"Disk used: {cache_info.total_size_mb:.1f} MB  |  "
            f"Available: {cache_info.available_space_gb:.1f} GB"
        )
        info_label = QLabel(info_text)
        info_label.setStyleSheet("color: #666666; font-size: 9pt;")
        header_layout.addWidget(info_label)

        main_layout.addLayout(header_layout)

        # ── Model tree ────────────────────────────────────────────────
        models_tree = QTreeWidget()
        models_tree.setHeaderLabels([
            "Model", "Family", "Languages", "Size",
            "Speed", "Quality", "GPU", "Status", "Description",
        ])
        models_tree.setColumnWidth(0, 180)
        models_tree.setColumnWidth(1, 90)
        models_tree.setColumnWidth(2, 100)
        models_tree.setColumnWidth(3, 80)
        models_tree.setColumnWidth(4, 70)
        models_tree.setColumnWidth(5, 70)
        models_tree.setColumnWidth(6, 50)
        models_tree.setColumnWidth(7, 100)
        models_tree.setColumnWidth(8, 250)
        models_tree.setAlternatingRowColors(True)
        main_layout.addWidget(models_tree)

        def _status_text(entry: ModelEntry) -> str:
            if entry.status.downloaded:
                return "Downloaded"
            return "Not installed"

        def refresh_models():
            models_tree.clear()

            section_header = QTreeWidgetItem(["Catalog LLM Models", "", "", "", "", "", "", "", ""])
            section_header.setFirstColumnSpanned(True)
            font = section_header.font(0)
            font.setBold(True)
            section_header.setFont(0, font)
            models_tree.addTopLevelItem(section_header)

            entries = catalog.list_available("llm")
            if not entries:
                item = QTreeWidgetItem(["No LLM models in catalog", "", "", "", "", "", "", "", ""])
                item.setForeground(0, Qt.GlobalColor.darkGray)
                models_tree.addTopLevelItem(item)
            else:
                for entry in entries:
                    meta = entry.metadata
                    lang_list = ", ".join(meta.languages[:5])
                    if len(meta.languages) > 5:
                        lang_list += f" +{len(meta.languages) - 5} more"

                    item = QTreeWidgetItem([
                        f"  {entry.model_id}",
                        meta.family,
                        f"{len(meta.languages)} ({lang_list})",
                        f"{meta.size_mb:.0f} MB",
                        meta.speed,
                        meta.quality,
                        "Yes" if meta.gpu_required else "No",
                        _status_text(entry),
                        meta.rationale,
                    ])
                    item.setToolTip(2, ", ".join(meta.languages))
                    item.setToolTip(8, meta.rationale)
                    item.setData(0, Qt.ItemDataRole.UserRole, entry.model_id)
                    models_tree.addTopLevelItem(item)

            models_tree.expandAll()

        refresh_models()

        # ── Action buttons ────────────────────────────────────────────
        action_layout = QHBoxLayout()

        refresh_btn = QPushButton("Refresh")
        refresh_btn.clicked.connect(refresh_models)
        action_layout.addWidget(refresh_btn)

        delete_btn = QPushButton("Delete")
        delete_btn.setProperty("class", "action")
        delete_btn.clicked.connect(
            lambda: self._delete_selected_model(dialog, catalog, models_tree, refresh_models)
        )
        action_layout.addWidget(delete_btn)

        action_layout.addStretch()

        close_btn = QPushButton("Close")
        close_btn.clicked.connect(dialog.accept)
        action_layout.addWidget(close_btn)

        main_layout.addLayout(action_layout)

        dialog.exec()

    # ------------------------------------------------------------------
    # Actions
    # ------------------------------------------------------------------

    def _delete_selected_model(self, parent_dialog, catalog, models_tree, refresh_callback):
        """Delete the selected LLM model."""
        selected = models_tree.selectedItems()
        if not selected:
            QMessageBox.warning(parent_dialog, "No selection", "Select a model first.")
            return

        model_id = selected[0].data(0, Qt.ItemDataRole.UserRole)
        if not model_id:
            return

        reply = QMessageBox.question(
            parent_dialog,
            "Confirm delete",
            f"Delete model '{model_id}' and all cached files?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            QMessageBox.StandardButton.No,
        )
        if reply != QMessageBox.StandardButton.Yes:
            return

        try:
            if catalog.delete(model_id):
                QMessageBox.information(
                    parent_dialog, "Deleted",
                    f"Model '{model_id}' has been removed.",
                )
                refresh_callback()
            else:
                QMessageBox.warning(
                    parent_dialog, "Not downloaded",
                    f"Model '{model_id}' is not downloaded locally.",
                )
        except Exception as exc:
            QMessageBox.critical(
                parent_dialog, "Error",
                f"Failed to delete model:\n{exc}",
            )
