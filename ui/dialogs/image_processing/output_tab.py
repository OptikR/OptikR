"""Output tab for the Image Processing dialog.

Provides export folder selection, naming pattern, output format,
a progress bar with status during batch processing, and a results
summary upon completion.
"""

import logging
import os
from pathlib import Path
from typing import Any

from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QGridLayout, QGroupBox,
    QLabel, QComboBox, QLineEdit, QPushButton, QProgressBar,
    QRadioButton, QButtonGroup, QFileDialog, QTextEdit, QSlider,
)
from PyQt6.QtCore import Qt, pyqtSignal

from app.localization import TranslatableMixin, tr

logger = logging.getLogger(__name__)


class OutputTab(TranslatableMixin, QWidget):
    """Export configuration, progress tracking, and results summary."""

    processRequested = pyqtSignal()
    cancelRequested = pyqtSignal()

    def __init__(self, config_manager: Any = None, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.config_manager = config_manager
        self._init_ui()
        self.load_config()

    # ------------------------------------------------------------------
    # UI construction
    # ------------------------------------------------------------------

    def _init_ui(self) -> None:
        layout = QVBoxLayout(self)
        layout.setContentsMargins(10, 10, 10, 10)
        layout.setSpacing(10)

        self._create_output_folder_section(layout)
        self._create_naming_section(layout)
        self._create_format_section(layout)
        self._create_action_section(layout)
        self._create_progress_section(layout)
        self._create_results_section(layout)

        layout.addStretch()

    # ------------------------------------------------------------------
    # Output folder
    # ------------------------------------------------------------------

    def _create_output_folder_section(self, parent_layout: QVBoxLayout) -> None:
        group = QGroupBox()
        self.set_translatable_text(group, "image_processing_output_folder")
        layout = QHBoxLayout(group)
        layout.setContentsMargins(15, 20, 15, 15)

        self.output_folder_edit = QLineEdit()
        self.output_folder_edit.setReadOnly(True)
        self.set_translatable_text(
            self.output_folder_edit,
            "image_processing_output_folder_placeholder",
            method="setPlaceholderText",
        )
        layout.addWidget(self.output_folder_edit, 1)

        browse_btn = QPushButton()
        self.set_translatable_text(browse_btn, "image_processing_browse")
        browse_btn.clicked.connect(self._on_browse_output)
        layout.addWidget(browse_btn)

        parent_layout.addWidget(group)

    # ------------------------------------------------------------------
    # Naming pattern
    # ------------------------------------------------------------------

    def _create_naming_section(self, parent_layout: QVBoxLayout) -> None:
        group = QGroupBox()
        self.set_translatable_text(group, "image_processing_naming_pattern")
        layout = QVBoxLayout(group)
        layout.setSpacing(8)
        layout.setContentsMargins(15, 20, 15, 15)

        self.naming_group = QButtonGroup(self)

        self.suffix_radio = QRadioButton()
        self.set_translatable_text(self.suffix_radio, "image_processing_naming_suffix")
        self.suffix_radio.setChecked(True)
        self.naming_group.addButton(self.suffix_radio, 0)
        layout.addWidget(self.suffix_radio)

        self.prefix_radio = QRadioButton()
        self.set_translatable_text(self.prefix_radio, "image_processing_naming_prefix")
        self.naming_group.addButton(self.prefix_radio, 1)
        layout.addWidget(self.prefix_radio)

        self.subfolder_radio = QRadioButton()
        self.set_translatable_text(self.subfolder_radio, "image_processing_naming_subfolder")
        self.naming_group.addButton(self.subfolder_radio, 2)
        layout.addWidget(self.subfolder_radio)

        # Suffix/prefix text
        suffix_row = QHBoxLayout()
        suffix_label = QLabel()
        self.set_translatable_text(suffix_label, "image_processing_suffix_text")
        self.suffix_edit = QLineEdit("_translated")
        self.suffix_edit.setMaximumWidth(200)
        suffix_row.addWidget(suffix_label)
        suffix_row.addWidget(self.suffix_edit)
        suffix_row.addStretch()
        layout.addLayout(suffix_row)

        parent_layout.addWidget(group)

    # ------------------------------------------------------------------
    # Output format
    # ------------------------------------------------------------------

    def _create_format_section(self, parent_layout: QVBoxLayout) -> None:
        group = QGroupBox()
        self.set_translatable_text(group, "image_processing_output_format")
        layout = QGridLayout(group)
        layout.setSpacing(8)
        layout.setContentsMargins(15, 20, 15, 15)

        format_label = QLabel()
        self.set_translatable_text(format_label, "image_processing_format_label")
        self.format_combo = QComboBox()
        self.format_combo.addItem(tr("image_processing_format_same"), "same")
        self.format_combo.addItem("PNG", "png")
        self.format_combo.addItem("JPG", "jpg")
        self.format_combo.addItem("BMP", "bmp")
        self.format_combo.currentIndexChanged.connect(self._on_format_changed)
        layout.addWidget(format_label, 0, 0)
        layout.addWidget(self.format_combo, 0, 1)

        self.quality_label = QLabel()
        self.set_translatable_text(self.quality_label, "image_processing_jpg_quality")
        self.quality_slider = QSlider(Qt.Orientation.Horizontal)
        self.quality_slider.setRange(1, 100)
        self.quality_slider.setValue(95)
        self.quality_slider.valueChanged.connect(self._on_quality_changed)
        self.quality_value_label = QLabel("95")
        self.quality_value_label.setMinimumWidth(30)
        layout.addWidget(self.quality_label, 1, 0)
        quality_row = QHBoxLayout()
        quality_row.addWidget(self.quality_slider)
        quality_row.addWidget(self.quality_value_label)
        layout.addLayout(quality_row, 1, 1)

        self.quality_label.setVisible(False)
        self.quality_slider.setVisible(False)
        self.quality_value_label.setVisible(False)

        parent_layout.addWidget(group)

    # ------------------------------------------------------------------
    # Action buttons
    # ------------------------------------------------------------------

    def _create_action_section(self, parent_layout: QVBoxLayout) -> None:
        btn_layout = QHBoxLayout()

        self.process_btn = QPushButton()
        self.set_translatable_text(self.process_btn, "image_processing_process_all")
        self.process_btn.setProperty("class", "action")
        self.process_btn.setStyleSheet(
            "background-color: #4CAF50; color: white; font-weight: bold; font-size: 11pt;"
        )
        self.process_btn.setMinimumHeight(45)
        self.process_btn.clicked.connect(self.processRequested.emit)
        btn_layout.addWidget(self.process_btn, 1)

        self.cancel_btn = QPushButton()
        self.set_translatable_text(self.cancel_btn, "image_processing_cancel")
        self.cancel_btn.setMinimumHeight(45)
        self.cancel_btn.setVisible(False)
        self.cancel_btn.clicked.connect(self.cancelRequested.emit)
        btn_layout.addWidget(self.cancel_btn)

        parent_layout.addLayout(btn_layout)

    # ------------------------------------------------------------------
    # Progress
    # ------------------------------------------------------------------

    def _create_progress_section(self, parent_layout: QVBoxLayout) -> None:
        self.progress_widget = QWidget()
        progress_layout = QVBoxLayout(self.progress_widget)
        progress_layout.setContentsMargins(0, 0, 0, 0)
        progress_layout.setSpacing(4)

        self.progress_bar = QProgressBar()
        self.progress_bar.setMinimum(0)
        self.progress_bar.setMaximum(100)
        self.progress_bar.setValue(0)
        progress_layout.addWidget(self.progress_bar)

        self.progress_label = QLabel()
        self.progress_label.setStyleSheet("color: #AAAAAA; font-size: 9pt;")
        progress_layout.addWidget(self.progress_label)

        self.progress_widget.setVisible(False)
        parent_layout.addWidget(self.progress_widget)

    # ------------------------------------------------------------------
    # Results
    # ------------------------------------------------------------------

    def _create_results_section(self, parent_layout: QVBoxLayout) -> None:
        self.results_widget = QWidget()
        results_layout = QVBoxLayout(self.results_widget)
        results_layout.setContentsMargins(0, 5, 0, 0)
        results_layout.setSpacing(6)

        self.results_label = QLabel()
        self.results_label.setStyleSheet("font-weight: bold; font-size: 10pt;")
        results_layout.addWidget(self.results_label)

        self.results_text = QTextEdit()
        self.results_text.setReadOnly(True)
        self.results_text.setMaximumHeight(150)
        results_layout.addWidget(self.results_text)

        self.open_folder_btn = QPushButton()
        self.set_translatable_text(self.open_folder_btn, "image_processing_open_folder")
        self.open_folder_btn.clicked.connect(self._on_open_output_folder)
        results_layout.addWidget(self.open_folder_btn)

        self.results_widget.setVisible(False)
        parent_layout.addWidget(self.results_widget)

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def get_output_config(self) -> dict[str, Any]:
        """Collect output configuration as a dict for the batch processor."""
        naming_id = self.naming_group.checkedId()
        naming_map = {0: "suffix", 1: "prefix", 2: "subfolder"}

        return {
            "output_folder": self.output_folder_edit.text(),
            "naming_pattern": naming_map.get(naming_id, "suffix"),
            "naming_suffix": self.suffix_edit.text() or "_translated",
            "output_format": self.format_combo.currentData() or "same",
            "jpg_quality": self.quality_slider.value(),
        }

    def set_processing_state(self, processing: bool) -> None:
        """Toggle between idle and processing UI states."""
        self.process_btn.setVisible(not processing)
        self.cancel_btn.setVisible(processing)
        self.progress_widget.setVisible(processing)
        if processing:
            self.results_widget.setVisible(False)
            self.progress_bar.setValue(0)
            self.progress_label.clear()

    def update_progress(self, current: int, total: int, filename: str, status: str) -> None:
        if total > 0:
            self.progress_bar.setMaximum(total)
            self.progress_bar.setValue(current)
        self.set_translatable_text(
            self.progress_label, "image_processing_progress",
            current=current, total=total, filename=filename,
        )

    def show_results(self, total: int, succeeded: int, failed: int) -> None:
        self.set_processing_state(False)
        self.results_widget.setVisible(True)
        self.set_translatable_text(self.results_label, "image_processing_complete")
        lines = [
            tr("image_processing_succeeded").format(count=succeeded),
            tr("image_processing_failed").format(count=failed),
            f"Total: {total}",
        ]
        self.results_text.setPlainText("\n".join(lines))

    def append_result_line(self, filepath: str, success: bool, error_msg: str) -> None:
        name = Path(filepath).name
        if success:
            self.results_text.append(f"  OK  {name}")
        else:
            self.results_text.append(f"  FAIL  {name}: {error_msg}")

    # ------------------------------------------------------------------
    # load / save config
    # ------------------------------------------------------------------

    def load_config(self) -> None:
        if not self.config_manager:
            return
        try:
            g = self.config_manager.get_setting
            self.output_folder_edit.setText(g("image_processing.last_output_folder", ""))

            naming = g("image_processing.naming_pattern", "suffix")
            btn_map = {"suffix": self.suffix_radio, "prefix": self.prefix_radio, "subfolder": self.subfolder_radio}
            btn = btn_map.get(naming, self.suffix_radio)
            btn.setChecked(True)

            self.suffix_edit.setText(g("image_processing.naming_suffix", "_translated"))

            fmt = g("image_processing.output_format", "same")
            idx = self.format_combo.findData(fmt)
            if idx >= 0:
                self.format_combo.setCurrentIndex(idx)

            self.quality_slider.setValue(g("image_processing.jpg_quality", 95))
        except Exception as e:
            logger.warning("Failed to load output tab config: %s", e)

    def save_config(self) -> tuple[bool, str]:
        if not self.config_manager:
            return False, "Configuration manager not available"
        try:
            cfg = self.get_output_config()
            s = self.config_manager.set_setting
            s("image_processing.last_output_folder", cfg["output_folder"])
            s("image_processing.naming_pattern", cfg["naming_pattern"])
            s("image_processing.naming_suffix", cfg["naming_suffix"])
            s("image_processing.output_format", cfg["output_format"])
            s("image_processing.jpg_quality", cfg["jpg_quality"])

            success, error_msg = self.config_manager.save_config()
            if not success:
                return False, error_msg
            return True, ""
        except Exception as e:
            return False, str(e)

    # ------------------------------------------------------------------
    # Slots
    # ------------------------------------------------------------------

    def _on_browse_output(self) -> None:
        last = self.output_folder_edit.text()
        folder = QFileDialog.getExistingDirectory(
            self, tr("image_processing_output_folder"), last,
        )
        if folder:
            self.output_folder_edit.setText(folder)
            if self.config_manager:
                self.config_manager.set_setting("image_processing.last_output_folder", folder)

    def _on_format_changed(self, index: int) -> None:
        is_jpg = self.format_combo.currentData() == "jpg"
        self.quality_label.setVisible(is_jpg)
        self.quality_slider.setVisible(is_jpg)
        self.quality_value_label.setVisible(is_jpg)

    def _on_quality_changed(self, value: int) -> None:
        self.quality_value_label.setText(str(value))

    def _on_open_output_folder(self) -> None:
        folder = self.output_folder_edit.text()
        if folder and Path(folder).is_dir():
            os.startfile(folder)
