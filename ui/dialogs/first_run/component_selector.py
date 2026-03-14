"""ComponentSelectorPage — wizard page for choosing translation models and OCR engines.

Displays available components grouped by category (Essentials / Optional)
with checkboxes, per-component sizes, and a running total.  GPU-only
components are disabled when CUDA is not available.
"""

from __future__ import annotations

import logging

from PyQt6.QtCore import Qt, pyqtSignal
from PyQt6.QtWidgets import (
    QCheckBox,
    QGroupBox,
    QHBoxLayout,
    QLabel,
    QMessageBox,
    QScrollArea,
    QVBoxLayout,
    QWidget,
)

from app.core.component_manifest import (
    ESSENTIAL_IDS,
    ComponentInfo,
    compute_total_size,
    format_size,
    get_components_by_category,
)
from app.localization import tr

logger = logging.getLogger(__name__)


class ComponentSelectorPage(QWidget):
    """Wizard page displaying selectable components grouped by category."""

    selection_changed = pyqtSignal()

    def __init__(self, installation_info: dict, parent: QWidget | None = None):
        super().__init__(parent)

        # Determine GPU availability, defaulting to False if missing/malformed
        try:
            self._gpu_available: bool = bool(
                installation_info["pytorch"]["cuda_available"]
            )
        except (KeyError, TypeError):
            self._gpu_available = False

        self._checkboxes: dict[str, QCheckBox] = {}

        self._init_ui()

    # ------------------------------------------------------------------
    # UI construction
    # ------------------------------------------------------------------

    def _init_ui(self) -> None:
        layout = QVBoxLayout(self)

        # Scrollable area for component groups
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)

        container = QWidget()
        container_layout = QVBoxLayout(container)

        essentials = get_components_by_category("essential")
        optionals = get_components_by_category("optional")

        regular_optionals = [c for c in optionals if c.component_type != "vision"]
        vision_optionals = [c for c in optionals if c.component_type == "vision"]

        container_layout.addWidget(self._build_category_group("Essentials", essentials))
        container_layout.addWidget(self._build_category_group("Optional", regular_optionals))
        if vision_optionals:
            container_layout.addWidget(
                self._build_category_group(
                    tr("wizard_vision_category"),
                    vision_optionals,
                    description=tr("wizard_vision_description"),
                )
            )
        container_layout.addStretch()

        scroll.setWidget(container)
        layout.addWidget(scroll)

        # Total size label at the bottom
        self._total_size_label = QLabel()
        layout.addWidget(self._total_size_label)

        self._update_total_size()

    # ------------------------------------------------------------------
    # Task 3.2 — _build_category_group
    # ------------------------------------------------------------------

    def _build_category_group(
        self, title: str, components: list[ComponentInfo],
        description: str | None = None,
    ) -> QGroupBox:
        """Create a group box with a checkbox row for each component."""
        group = QGroupBox(title)
        group_layout = QVBoxLayout(group)

        if description:
            desc_label = QLabel(description)
            desc_label.setWordWrap(True)
            desc_label.setStyleSheet("color: #888; font-size: 9pt; margin-bottom: 4px;")
            group_layout.addWidget(desc_label)

        for comp in components:
            row = QHBoxLayout()

            checkbox = QCheckBox(comp.display_name)

            # Pre-check essentials, leave optionals unchecked
            if comp.category == "essential":
                checkbox.setChecked(True)

            # Disable GPU-required components when no GPU
            if comp.gpu_required and not self._gpu_available:
                checkbox.setEnabled(False)
                if comp.component_type == "vision":
                    vram_gb = comp.size_mb / 1000
                    checkbox.setToolTip(
                        tr("wizard_vision_gpu_required").format(vram=f"{vram_gb:.0f}")
                    )
                else:
                    checkbox.setToolTip("Requires a CUDA-capable GPU")

            checkbox.toggled.connect(
                lambda checked, mid=comp.model_id: self._on_checkbox_toggled(
                    mid, checked
                )
            )

            size_label = QLabel(format_size(comp.size_mb))
            desc_label = QLabel(comp.description)

            row.addWidget(checkbox)
            row.addWidget(size_label)
            row.addWidget(desc_label)
            group_layout.addLayout(row)

            self._checkboxes[comp.model_id] = checkbox

        return group

    # ------------------------------------------------------------------
    # Task 3.3 — _on_checkbox_toggled
    # ------------------------------------------------------------------

    def _on_checkbox_toggled(self, model_id: str, checked: bool) -> None:
        """Handle checkbox toggle with essential-deselection confirmation."""
        if not checked and model_id in ESSENTIAL_IDS:
            result = QMessageBox.warning(
                self,
                "Deselect Essential Component",
                (
                    f"Deselecting this component may result in reduced "
                    f"functionality. Are you sure?"
                ),
                QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
                QMessageBox.StandardButton.No,
            )
            if result != QMessageBox.StandardButton.Yes:
                # User cancelled — re-check without triggering recursion
                cb = self._checkboxes[model_id]
                cb.blockSignals(True)
                cb.setChecked(True)
                cb.blockSignals(False)
                return

        self._update_total_size()
        self.selection_changed.emit()

    # ------------------------------------------------------------------
    # Task 3.4 — size helpers and selection accessors
    # ------------------------------------------------------------------

    def _update_total_size(self) -> None:
        """Recalculate total download size and update the label."""
        total = compute_total_size(self.get_selected_ids())
        self._total_size_label.setText(f"Total download size: {format_size(total)}")

    def get_selected_ids(self) -> list[str]:
        """Return model IDs for all currently checked checkboxes."""
        return [
            mid for mid, cb in self._checkboxes.items() if cb.isChecked()
        ]

    def get_total_size_mb(self) -> float:
        """Return numeric total size (MB) of selected components."""
        return compute_total_size(self.get_selected_ids())
