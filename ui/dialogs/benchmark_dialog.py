"""
Benchmark Dialog

Dialog for running and visualizing pipeline benchmarks from the UI.

Provides:
- Scope controls (modes, execution, engines, images)
- Progress output and live log
- Results table and summary
- JSON export and persisted runs under user_data/benchmarks
"""

from __future__ import annotations

import json
from dataclasses import asdict
from datetime import datetime
from pathlib import Path
from typing import Iterable, List, Optional

from PyQt6.QtCore import Qt, QThread, pyqtSignal
from PyQt6.QtWidgets import (
    QCheckBox,
    QComboBox,
    QDialog,
    QFileDialog,
    QFormLayout,
    QGridLayout,
    QGroupBox,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QMessageBox,
    QPushButton,
    QPlainTextEdit,
    QProgressBar,
    QRadioButton,
    QTableWidget,
    QTableWidgetItem,
    QVBoxLayout,
    QWidget,
)

from app.localization import TranslatableMixin, tr
from app.benchmark.benchmark_runner import (
    BenchmarkResult,
    TEXT_OCR_ENGINES,
    TEXT_TRANSLATION_ENGINES,
    build_default_combinations,
    guard_vision_async_combinations,
    run_benchmark,
)
from app.utils.path_utils import get_app_path, get_benchmarks_dir


class BenchmarkWorker(QThread):
    """
    Background worker that runs benchmarks without blocking the UI.

    Emits:
        progress(str): human-readable progress messages
        finished(list[BenchmarkResult]): results when the run completes (or empty list on error)
        error(str): error message if the run fails
    """

    progress = pyqtSignal(str)
    finished = pyqtSignal(list)
    error = pyqtSignal(str)

    def __init__(
        self,
        images: Iterable[Path],
        include_vision: bool,
        include_text: bool,
        fast: bool,
        *,
        selected_executions: Optional[list[str]] = None,
        selected_translation_engines: Optional[list[str]] = None,
        selected_ocr_engines: Optional[list[str]] = None,
        allow_vision_async: bool = False,
        config_manager=None,
        parent: Optional[QWidget] = None,
    ):
        super().__init__(parent)
        self._images = list(images)
        self._include_vision = include_vision
        self._include_text = include_text
        self._fast = fast
        self._selected_executions = selected_executions or ["sequential", "async"]
        self._selected_translation_engines = selected_translation_engines or []
        self._selected_ocr_engines = selected_ocr_engines or []
        self._allow_vision_async = allow_vision_async
        self._config_manager = config_manager

    def run(self) -> None:
        """Run benchmark in a background thread."""
        try:
            if not self._images:
                self.error.emit(tr("benchmark_no_images_found"))
                self.finished.emit([])
                return

            def _progress(msg: str) -> None:
                self.progress.emit(str(msg))

            # Build combination matrix based on current scope
            combos = build_default_combinations(
                include_vision=self._include_vision,
                include_text=self._include_text,
                fast=self._fast,
                text_translation_engines=(
                    self._selected_translation_engines or None
                ),
                text_ocr_engines=self._selected_ocr_engines or None,
            )

            if self._selected_executions:
                selected = set(self._selected_executions)
                combos = [
                    c for c in combos if len(c) >= 2 and c[1] in selected
                ]
            if not combos:
                self.error.emit("No benchmark combinations selected.")
                self.finished.emit([])
                return

            guarded_combos = guard_vision_async_combinations(
                combos,
                allow_vision_async=self._allow_vision_async,
            )
            if not self._allow_vision_async and guarded_combos != combos:
                disabled = [
                    c for c in combos if len(c) >= 2 and c[0] == "vision" and c[1] == "async"
                ]
                if disabled:
                    self.progress.emit(
                        f"Vision async combinations are disabled for benchmarks; "
                        f"{len(disabled)} async vision combinations downgraded to sequential."
                    )
            combos = guarded_combos

            results: List[BenchmarkResult] = run_benchmark(
                images=self._images,
                combinations=combos,
                # include_* / fast flags are only used when combinations is None
                include_vision=False,
                include_text=False,
                fast=False,
                progress_callback=_progress,
                config_manager=self._config_manager,
            )
            self.finished.emit(results)
        except Exception as exc:  # pragma: no cover - defensive
            self.error.emit(str(exc))
            self.finished.emit([])


class BenchmarkDialog(TranslatableMixin, QDialog):
    """Full benchmark dialog with scope controls, results table, and persistence."""

    def __init__(self, parent=None, pipeline=None, config_manager=None):
        super().__init__(parent)
        self.pipeline = pipeline
        self.config_manager = config_manager

        self._worker: BenchmarkWorker | None = None
        self._current_results: list[BenchmarkResult] = []
        self._previous_runs: list[Path] = []

        self.setWindowTitle(tr("benchmark_dialog_title"))
        self.setMinimumSize(900, 650)

        self._init_ui()
        self._load_last_selections()
        self._load_default_images()
        self._refresh_previous_runs()

    # ------------------------------------------------------------------ UI setup

    def _init_ui(self) -> None:
        layout = QVBoxLayout(self)
        layout.setContentsMargins(12, 12, 12, 12)
        layout.setSpacing(10)

        # Header
        header = QLabel(tr("benchmark_dialog_title"))
        header.setStyleSheet("font-size: 16pt; font-weight: bold;")
        layout.addWidget(header)

        desc = QLabel(tr("benchmark_dialog_description"))
        desc.setWordWrap(True)
        desc.setStyleSheet("color: #999999; font-size: 9pt; margin-bottom: 6px;")
        layout.addWidget(desc)

        # Top row: scope + run controls
        top_row = QHBoxLayout()
        top_row.setSpacing(12)

        scope_group = self._create_scope_group()
        top_row.addWidget(scope_group, 2)

        run_group = self._create_run_group()
        top_row.addWidget(run_group, 1)

        layout.addLayout(top_row)

        # Log output
        log_group = QGroupBox(tr("benchmark_log_section_title"))
        log_layout = QVBoxLayout(log_group)
        log_layout.setContentsMargins(8, 8, 8, 8)
        self.log_output = QPlainTextEdit()
        self.log_output.setReadOnly(True)
        self.log_output.setMaximumHeight(140)
        self.log_output.setStyleSheet(
            "font-family: Consolas, 'Courier New', monospace; font-size: 9pt;"
        )
        log_layout.addWidget(self.log_output)
        layout.addWidget(log_group)

        # Results + summary
        middle_row = QHBoxLayout()
        middle_row.setSpacing(10)

        self.results_table = QTableWidget(0, 10, self)
        self.results_table.setHorizontalHeaderLabels(
            [
                tr("benchmark_col_mode"),
                tr("benchmark_col_execution"),
                tr("benchmark_col_plugins"),
                tr("benchmark_col_translation_engine"),
                tr("benchmark_col_ocr_engine"),
                tr("benchmark_col_image"),
                tr("benchmark_col_ok"),
                tr("benchmark_col_time_ms"),
                tr("benchmark_col_blocks"),
                tr("benchmark_col_error"),
            ]
        )
        self.results_table.setSortingEnabled(True)
        self.results_table.setAlternatingRowColors(True)
        middle_row.addWidget(self.results_table, 3)

        summary_group = QGroupBox(tr("benchmark_summary_section_title"))
        summary_layout = QVBoxLayout(summary_group)
        summary_layout.setContentsMargins(8, 8, 8, 8)
        self.summary_output = QPlainTextEdit()
        self.summary_output.setReadOnly(True)
        self.summary_output.setStyleSheet(
            "font-family: Consolas, 'Courier New', monospace; font-size: 9pt;"
        )
        summary_layout.addWidget(self.summary_output)
        middle_row.addWidget(summary_group, 2)

        layout.addLayout(middle_row, 1)

        # Bottom: previous runs + export / close
        bottom_row = QHBoxLayout()
        bottom_row.setSpacing(8)

        prev_group = QGroupBox(tr("benchmark_previous_runs_section_title"))
        prev_layout = QHBoxLayout(prev_group)
        prev_layout.setContentsMargins(8, 8, 8, 8)
        self.previous_runs_combo = QComboBox()
        self.previous_runs_combo.currentIndexChanged.connect(
            self._on_previous_run_selected
        )
        prev_layout.addWidget(self.previous_runs_combo, 1)

        load_btn = QPushButton(tr("benchmark_load_run_btn"))
        load_btn.clicked.connect(self._load_selected_previous_run)
        prev_layout.addWidget(load_btn)

        bottom_row.addWidget(prev_group, 2)

        export_btn = QPushButton(tr("benchmark_export_json_btn"))
        export_btn.clicked.connect(self._export_json)
        bottom_row.addWidget(export_btn)

        close_btn = QPushButton(tr("close"))
        close_btn.clicked.connect(self.close)
        bottom_row.addWidget(close_btn)

        layout.addLayout(bottom_row)

    def _create_scope_group(self) -> QGroupBox:
        group = QGroupBox(tr("benchmark_scope_section_title"))
        layout = QGridLayout(group)
        layout.setContentsMargins(8, 12, 8, 8)
        layout.setHorizontalSpacing(8)
        layout.setVerticalSpacing(6)

        # Modes
        modes_label = QLabel(tr("benchmark_modes_label"))
        modes_label.setStyleSheet("font-weight: 600;")
        self.mode_text_check = QCheckBox(tr("benchmark_mode_text"))
        self.mode_text_check.setChecked(True)
        self.mode_vision_check = QCheckBox(tr("benchmark_mode_vision"))
        self.mode_vision_check.setChecked(True)

        layout.addWidget(modes_label, 0, 0)
        layout.addWidget(self.mode_text_check, 0, 1)
        layout.addWidget(self.mode_vision_check, 0, 2)

        # Execution
        exec_label = QLabel(tr("benchmark_execution_label"))
        exec_label.setStyleSheet("font-weight: 600;")
        self.exec_sequential_check = QCheckBox(tr("benchmark_exec_sequential"))
        self.exec_async_check = QCheckBox(tr("benchmark_exec_async"))
        self.exec_sequential_check.setChecked(True)
        self.exec_async_check.setChecked(True)

        layout.addWidget(exec_label, 1, 0)
        layout.addWidget(self.exec_sequential_check, 1, 1)
        layout.addWidget(self.exec_async_check, 1, 2)

        # Scope presets
        scope_label = QLabel(tr("benchmark_scope_label"))
        scope_label.setStyleSheet("font-weight: 600;")
        self.scope_fast_radio = QRadioButton(tr("benchmark_scope_fast"))
        self.scope_full_radio = QRadioButton(tr("benchmark_scope_full"))
        self.scope_custom_radio = QRadioButton(tr("benchmark_scope_custom"))
        self.scope_fast_radio.setChecked(True)

        layout.addWidget(scope_label, 2, 0)
        layout.addWidget(self.scope_fast_radio, 2, 1)
        layout.addWidget(self.scope_full_radio, 2, 2)
        layout.addWidget(self.scope_custom_radio, 2, 3)

        # Engine selection (only used when custom is active)
        engines_group = QGroupBox(tr("benchmark_engines_section_title"))
        engines_layout = QFormLayout(engines_group)
        engines_layout.setContentsMargins(6, 10, 6, 6)

        self.text_engines_combo = QComboBox()
        self.text_engines_combo.setEditable(False)
        self.text_engines_combo.setInsertPolicy(QComboBox.InsertPolicy.NoInsert)
        self.text_engines_combo.setToolTip(tr("benchmark_text_engines_tooltip"))
        # Multi-select via checkable items
        self._populate_checkable_items(
            self.text_engines_combo, TEXT_TRANSLATION_ENGINES
        )

        self.ocr_engines_combo = QComboBox()
        self.ocr_engines_combo.setEditable(False)
        self.ocr_engines_combo.setInsertPolicy(QComboBox.InsertPolicy.NoInsert)
        self.ocr_engines_combo.setToolTip(tr("benchmark_ocr_engines_tooltip"))
        self._populate_checkable_items(self.ocr_engines_combo, TEXT_OCR_ENGINES)

        engines_layout.addRow(tr("benchmark_text_engines_label"), self.text_engines_combo)
        engines_layout.addRow(tr("benchmark_ocr_engines_label"), self.ocr_engines_combo)

        layout.addWidget(engines_group, 3, 0, 1, 4)

        # Image selection
        images_group = QGroupBox(tr("benchmark_images_section_title"))
        images_layout = QVBoxLayout(images_group)
        images_layout.setContentsMargins(6, 10, 6, 6)

        self.use_all_images_radio = QRadioButton(tr("benchmark_images_all"))
        self.use_single_image_radio = QRadioButton(tr("benchmark_images_single"))
        self.use_all_images_radio.setChecked(True)

        images_layout.addWidget(self.use_all_images_radio)

        single_row = QHBoxLayout()
        self.single_image_path_edit = QLineEdit()
        browse_btn = QPushButton(tr("browse"))
        browse_btn.clicked.connect(self._browse_single_image)
        single_row.addWidget(self.use_single_image_radio)
        single_row.addWidget(self.single_image_path_edit, 1)
        single_row.addWidget(browse_btn)
        images_layout.addLayout(single_row)

        layout.addWidget(images_group, 4, 0, 1, 4)

        return group

    def _create_run_group(self) -> QGroupBox:
        group = QGroupBox(tr("benchmark_run_section_title"))
        layout = QVBoxLayout(group)
        layout.setContentsMargins(8, 12, 8, 8)
        layout.setSpacing(8)

        self.progress_label = QLabel(tr("benchmark_status_idle"))
        self.progress_label.setStyleSheet("font-size: 9pt; color: #CCCCCC;")
        layout.addWidget(self.progress_label)

        self.progress_bar = QProgressBar()
        self.progress_bar.setMinimum(0)
        self.progress_bar.setMaximum(100)
        self.progress_bar.setValue(0)
        layout.addWidget(self.progress_bar)

        btn_row = QHBoxLayout()
        self.run_button = QPushButton(tr("benchmark_run_btn"))
        self.run_button.setProperty("class", "action")
        self.run_button.clicked.connect(self._on_run_clicked)
        btn_row.addWidget(self.run_button)

        self.cancel_button = QPushButton(tr("cancel"))
        self.cancel_button.setEnabled(False)
        self.cancel_button.clicked.connect(self._on_cancel_clicked)
        btn_row.addWidget(self.cancel_button)

        btn_row.addStretch()
        layout.addLayout(btn_row)

        info = QLabel(tr("benchmark_run_warning"))
        info.setWordWrap(True)
        info.setStyleSheet("color: #888888; font-size: 8pt;")
        layout.addWidget(info)

        return group

    # ------------------------------------------------------------------ Helpers

    def _load_last_selections(self) -> None:
        """
        Restore last benchmark selections from user configuration, if available.
        """
        if not self.config_manager:
            return

        try:
            modes = self.config_manager.get_setting(
                "benchmark.last_mode_selection", ["text", "vision"]
            )
            execs = self.config_manager.get_setting(
                "benchmark.last_execution_selection", ["sequential", "async"]
            )
            scope = self.config_manager.get_setting(
                "benchmark.last_scope", "fast"
            )
            last_text_engines = self.config_manager.get_setting(
                "benchmark.last_selected_translation_engines", []
            )
            last_ocr_engines = self.config_manager.get_setting(
                "benchmark.last_selected_ocr_engines", []
            )
        except Exception:
            return

        self.mode_text_check.setChecked("text" in modes)
        self.mode_vision_check.setChecked("vision" in modes)

        self.exec_sequential_check.setChecked("sequential" in execs)
        self.exec_async_check.setChecked("async" in execs)

        if scope == "full":
            self.scope_full_radio.setChecked(True)
        elif scope == "custom":
            self.scope_custom_radio.setChecked(True)
        else:
            self.scope_fast_radio.setChecked(True)

        if last_text_engines:
            self._set_checked_items(self.text_engines_combo, last_text_engines)
        if last_ocr_engines:
            self._set_checked_items(self.ocr_engines_combo, last_ocr_engines)

    def _populate_checkable_items(self, combo: QComboBox, values: list[str]) -> None:
        """
        Populate a QComboBox with checkable items for simple multi-select.
        """
        combo.clear()
        for value in values:
            combo.addItem(value)
            index = combo.count() - 1
            item = combo.model().item(index, 0)
            if item is not None:
                item.setFlags(item.flags() | Qt.ItemFlag.ItemIsUserCheckable)
                item.setData(Qt.CheckState.Checked, Qt.ItemDataRole.CheckStateRole)

    def _set_checked_items(self, combo: QComboBox, selected_values: list[str]) -> None:
        """
        Apply a list of selected values to a checkable combo box.
        """
        selected_set = set(selected_values)
        for index in range(combo.count()):
            item = combo.model().item(index, 0)
            if item is None:
                continue
            value = combo.itemText(index)
            state = (
                Qt.CheckState.Checked
                if value in selected_set
                else Qt.CheckState.Unchecked
            )
            item.setData(state, Qt.ItemDataRole.CheckStateRole)

    def _get_checked_items(self, combo: QComboBox) -> list[str]:
        checked: list[str] = []
        for index in range(combo.count()):
            item = combo.model().item(index, 0)
            if item is not None and item.data(Qt.ItemDataRole.CheckStateRole) == Qt.CheckState.Checked:
                checked.append(combo.itemText(index))
        return checked

    def _load_default_images(self) -> None:
        """
        Discover default test images under tests/images (if available).
        """
        images_dir = get_app_path("tests", "images")
        candidates: list[Path] = []
        if images_dir.exists():
            for pattern in ("*.png", "*.jpg", "*.jpeg", "*.webp"):
                candidates.extend(images_dir.glob(pattern))
        candidates = sorted(set(candidates))
        self._default_images = candidates
        if candidates and not self.single_image_path_edit.text():
            self.single_image_path_edit.setText(str(candidates[0]))

    def _resolve_images(self) -> list[Path]:
        if self.use_all_images_radio.isChecked():
            if self._default_images:
                return self._default_images
            # Fallback to single image if specified
        path_text = self.single_image_path_edit.text().strip()
        if path_text:
            p = Path(path_text)
            if p.is_file():
                return [p]
        return []

    # ------------------------------------------------------------------ Run / cancel

    def _on_run_clicked(self) -> None:
        if self._worker and self._worker.isRunning():
            return

        include_text = self.mode_text_check.isChecked()
        include_vision = self.mode_vision_check.isChecked()
        if not include_text and not include_vision:
            QMessageBox.warning(
                self,
                tr("benchmark_invalid_scope_title"),
                tr("benchmark_invalid_scope_msg"),
            )
            return

        images = self._resolve_images()
        if not images:
            QMessageBox.warning(
                self,
                tr("benchmark_no_images_title"),
                tr("benchmark_no_images_msg"),
            )
            return

        fast = self.scope_fast_radio.isChecked()
        custom = self.scope_custom_radio.isChecked()

        selected_trans = []
        selected_ocr = []
        selected_execs = []
        if self.exec_sequential_check.isChecked():
            selected_execs.append("sequential")
        if self.exec_async_check.isChecked():
            selected_execs.append("async")
        if not selected_execs:
            QMessageBox.warning(
                self,
                tr("benchmark_invalid_scope_title"),
                "Select at least one execution mode.",
            )
            return

        if custom:
            selected_trans = self._get_checked_items(self.text_engines_combo)
            selected_ocr = self._get_checked_items(self.ocr_engines_combo)
            if not selected_trans or not selected_ocr:
                QMessageBox.warning(
                    self,
                    tr("benchmark_invalid_engines_title"),
                    tr("benchmark_invalid_engines_msg"),
                )
                return

        allow_vision_async = "async" in selected_execs

        self.log_output.clear()
        self.summary_output.clear()
        self.results_table.setRowCount(0)
        self._current_results = []

        self.progress_bar.setRange(0, 0)  # Indeterminate until we parse counts
        self.progress_label.setText(tr("benchmark_status_running"))
        self.run_button.setEnabled(False)
        self.cancel_button.setEnabled(True)

        self._worker = BenchmarkWorker(
            images=images,
            include_vision=include_vision,
            include_text=include_text,
            fast=fast and not custom,
            selected_executions=selected_execs,
            selected_translation_engines=selected_trans,
            selected_ocr_engines=selected_ocr,
            allow_vision_async=allow_vision_async,
            config_manager=self.config_manager,
            parent=self,
        )
        self._worker.progress.connect(self._on_worker_progress)
        self._worker.finished.connect(self._on_worker_finished)
        self._worker.error.connect(self._on_worker_error)
        self._worker.start()

    def _on_cancel_clicked(self) -> None:
        if self._worker and self._worker.isRunning():
            self._worker.requestInterruption()
            self._worker.terminate()
        self._worker = None
        self.progress_bar.setRange(0, 100)
        self.progress_bar.setValue(0)
        self.progress_label.setText(tr("benchmark_status_cancelled"))
        self.run_button.setEnabled(True)
        self.cancel_button.setEnabled(False)

    def _on_worker_progress(self, message: str) -> None:
        self.log_output.appendPlainText(message)
        # Try to parse " [3/40] " from message to update progress bar
        try:
            if "[" in message and "/" in message:
                prefix = message.split("[", 1)[1]
                numbers = prefix.split("]", 1)[0]
                current_str, total_str = numbers.split("/", 1)
                current = int(current_str.strip())
                total = int(total_str.strip())
                if total > 0:
                    self.progress_bar.setRange(0, total)
                    self.progress_bar.setValue(current)
        except Exception:
            # Ignore parse errors; keep bar indeterminate or last value
            pass

    def _on_worker_error(self, error_msg: str) -> None:
        self.log_output.appendPlainText(f"ERROR: {error_msg}")
        QMessageBox.critical(
            self,
            tr("benchmark_run_failed_title"),
            tr("benchmark_run_failed_msg", error=error_msg),
        )

    def _on_worker_finished(self, results: list[BenchmarkResult]) -> None:
        self._worker = None
        self.run_button.setEnabled(True)
        self.cancel_button.setEnabled(False)
        self.progress_bar.setRange(0, 100)
        self.progress_bar.setValue(100)

        self._current_results = results or []
        if not self._current_results:
            self.progress_label.setText(tr("benchmark_status_finished_no_results"))
            return

        self.progress_label.setText(
            tr("benchmark_status_finished", count=len(self._current_results))
        )
        self._populate_results_table(self._current_results)
        summary = self._build_summary(self._current_results)
        self.summary_output.setPlainText(summary)

        # Persist JSON under user_data/benchmarks
        try:
            json_path = self._auto_save_json(self._current_results, summary_text=summary)
            if json_path:
                self.log_output.appendPlainText(
                    tr("benchmark_saved_to_path", path=str(json_path))
                )
                self._save_last_run_metadata(json_path)
        except Exception as exc:  # pragma: no cover - defensive
            self.log_output.appendPlainText(f"ERROR saving benchmark JSON: {exc}")

        self._refresh_previous_runs()

    def _save_last_run_metadata(self, json_path: Path) -> None:
        """
        Save last selections and run metadata into user configuration.
        """
        if not self.config_manager:
            return

        try:
            modes: list[str] = []
            if self.mode_text_check.isChecked():
                modes.append("text")
            if self.mode_vision_check.isChecked():
                modes.append("vision")

            execs: list[str] = []
            if self.exec_sequential_check.isChecked():
                execs.append("sequential")
            if self.exec_async_check.isChecked():
                execs.append("async")

            if self.scope_full_radio.isChecked():
                scope = "full"
            elif self.scope_custom_radio.isChecked():
                scope = "custom"
            else:
                scope = "fast"

            last_text_engines = self._get_checked_items(self.text_engines_combo)
            last_ocr_engines = self._get_checked_items(self.ocr_engines_combo)

            self.config_manager.set_setting("benchmark.last_mode_selection", modes)
            self.config_manager.set_setting("benchmark.last_execution_selection", execs)
            self.config_manager.set_setting("benchmark.last_scope", scope)
            self.config_manager.set_setting(
                "benchmark.last_selected_translation_engines", last_text_engines
            )
            self.config_manager.set_setting(
                "benchmark.last_selected_ocr_engines", last_ocr_engines
            )
            self.config_manager.set_setting(
                "benchmark.last_full_run_timestamp",
                datetime.now().isoformat(timespec="seconds"),
            )
            self.config_manager.set_setting(
                "benchmark.last_full_run_path",
                str(json_path),
            )
            self.config_manager.save_config()
        except Exception:
            # Config persistence failures should not break the benchmark flow
            pass

    # ------------------------------------------------------------------ Results / summary

    def _populate_results_table(self, results: list[BenchmarkResult]) -> None:
        self.results_table.setSortingEnabled(False)
        self.results_table.setRowCount(len(results))
        for row, r in enumerate(results):
            values = [
                r.mode,
                r.execution,
                r.plugins,
                r.translation_engine or "-",
                r.ocr_engine or "-",
                r.image_name,
                "yes" if r.success else "no",
                f"{r.time_ms:.0f}",
                str(r.block_count),
                (r.error or "")[:40],
            ]
            for col, value in enumerate(values):
                item = QTableWidgetItem(value)
                if col == 6:  # OK column
                    if r.success:
                        item.setForeground(Qt.GlobalColor.darkGreen)
                    else:
                        item.setForeground(Qt.GlobalColor.red)
                self.results_table.setItem(row, col, item)
        self.results_table.resizeColumnsToContents()
        self.results_table.setSortingEnabled(True)

    def _build_summary(self, results: list[BenchmarkResult]) -> str:
        """
        Build a human-readable summary grouped by combination.
        """
        if not results:
            return ""

        by_key: dict[tuple, list[BenchmarkResult]] = {}
        for r in results:
            key = (
                r.mode,
                r.execution,
                r.plugins,
                r.translation_engine or "-",
                r.ocr_engine or "-",
            )
            by_key.setdefault(key, []).append(r)

        lines: list[str] = []
        lines.append(tr("benchmark_summary_header"))
        lines.append("-" * 72)
        for key in sorted(by_key.keys()):
            vals = by_key[key]
            ok = [v for v in vals if v.success]
            avg_ms = sum(v.time_ms for v in ok) / len(ok) if ok else 0.0
            mode, exec_, plugins, trans, ocr = key
            extra = ""
            if trans != "-" or ocr != "-":
                extra = f"  trans={trans}  ocr={ocr}"
            lines.append(
                f"{mode} | {exec_} | {plugins}{extra}: "
                f"success={len(ok)}/{len(vals)}, avg_time_ms={avg_ms:.0f}"
            )
        return "\n".join(lines)

    # ------------------------------------------------------------------ Persistence

    def _auto_save_json(self, results: list[BenchmarkResult], *, summary_text: str) -> Path | None:
        """
        Auto-save benchmark run JSON under user_data/benchmarks.
        """
        if not results:
            return None

        benchmarks_dir = get_benchmarks_dir()
        benchmarks_dir.mkdir(parents=True, exist_ok=True)

        ts = datetime.now().strftime("%Y%m%d_%H%M%S")
        json_path = benchmarks_dir / f"benchmark_{ts}.json"

        metadata = {
            "timestamp": datetime.now().isoformat(timespec="seconds"),
            "include_text": any(r.mode == "text" for r in results),
            "include_vision": any(r.mode == "vision" for r in results),
        }
        if self.config_manager:
            try:
                metadata["source_language"] = self.config_manager.get_setting(
                    "translation.source_language", "ja"
                )
                metadata["target_language"] = self.config_manager.get_setting(
                    "translation.target_language", "en"
                )
                metadata["translation_engine"] = self.config_manager.get_setting(
                    "translation.engine", ""
                )
                metadata["ocr_engine"] = self.config_manager.get_setting(
                    "ocr.engine", ""
                )
                metadata["pipeline_mode"] = self.config_manager.get_setting(
                    "pipeline.mode", "text"
                )
                metadata["pipeline_execution_mode"] = self.config_manager.get_setting(
                    "pipeline.execution_mode", "sequential"
                )
                metadata["benchmark_scope"] = self.config_manager.get_setting(
                    "benchmark.last_scope", "fast"
                )
            except Exception:
                pass

        by_key: dict[tuple, list[BenchmarkResult]] = {}
        for r in results:
            key = (
                r.mode,
                r.execution,
                r.plugins,
                r.translation_engine or "-",
                r.ocr_engine or "-",
            )
            by_key.setdefault(key, []).append(r)

        summary_rows = []
        for key, vals in by_key.items():
            ok = [v for v in vals if v.success]
            avg_ms = sum(v.time_ms for v in ok) / len(ok) if ok else 0.0
            mode, exec_, plugins, trans, ocr = key
            summary_rows.append(
                {
                    "mode": mode,
                    "execution": exec_,
                    "plugins": plugins,
                    "translation_engine": trans,
                    "ocr_engine": ocr,
                    "success_count": len(ok),
                    "total_runs": len(vals),
                    "avg_time_ms": avg_ms,
                }
            )

        data = {
            "metadata": metadata,
            "results": [asdict(r) for r in results],
            "summary_by_combination": summary_rows,
            "summary_text": summary_text,
        }
        json_path.write_text(json.dumps(data, indent=2, ensure_ascii=False), encoding="utf-8")
        return json_path

    def _refresh_previous_runs(self) -> None:
        benchmarks_dir = get_benchmarks_dir()
        self._previous_runs = []
        self.previous_runs_combo.blockSignals(True)
        self.previous_runs_combo.clear()
        if not benchmarks_dir.exists():
            self.previous_runs_combo.addItem(tr("benchmark_no_previous_runs"))
            self.previous_runs_combo.setEnabled(False)
            self.previous_runs_combo.blockSignals(False)
            return

        files = sorted(benchmarks_dir.glob("benchmark_*.json"))
        if not files:
            self.previous_runs_combo.addItem(tr("benchmark_no_previous_runs"))
            self.previous_runs_combo.setEnabled(False)
            self.previous_runs_combo.blockSignals(False)
            return

        self.previous_runs_combo.setEnabled(True)
        for path in files:
            label = path.stem.replace("benchmark_", "")
            self.previous_runs_combo.addItem(label)
            self._previous_runs.append(path)
        self.previous_runs_combo.blockSignals(False)

    def _on_previous_run_selected(self, index: int) -> None:
        # Do not auto-load on placeholder item
        if index < 0 or index >= len(self._previous_runs):
            return

    def _load_selected_previous_run(self) -> None:
        index = self.previous_runs_combo.currentIndex()
        if index < 0 or index >= len(self._previous_runs):
            return
        path = self._previous_runs[index]
        try:
            text = path.read_text(encoding="utf-8")
            data = json.loads(text)
        except Exception as exc:
            QMessageBox.critical(
                self,
                tr("benchmark_load_failed_title"),
                tr("benchmark_load_failed_msg", error=str(exc)),
            )
            return

        results_data = data.get("results") or []
        loaded_results: list[BenchmarkResult] = []
        for row in results_data:
            try:
                loaded_results.append(
                    BenchmarkResult(
                        mode=row.get("mode", ""),
                        execution=row.get("execution", ""),
                        plugins=row.get("plugins", ""),
                        image_name=row.get("image_name", ""),
                        success=bool(row.get("success", False)),
                        time_ms=float(row.get("time_ms", 0.0)),
                        block_count=int(row.get("block_count", 0)),
                        error=row.get("error"),
                        translation_engine=row.get("translation_engine", ""),
                        ocr_engine=row.get("ocr_engine", ""),
                    )
                )
            except Exception:
                continue

        self._current_results = loaded_results
        self._populate_results_table(self._current_results)
        summary_text = data.get("summary_text") or self._build_summary(
            self._current_results
        )
        self.summary_output.setPlainText(summary_text)
        self.progress_label.setText(
            tr("benchmark_status_loaded_previous", count=len(self._current_results))
        )

    # ------------------------------------------------------------------ Image browse / export

    def _browse_single_image(self) -> None:
        file_path, _ = QFileDialog.getOpenFileName(
            self,
            tr("benchmark_select_image_title"),
            "",
            tr("image_files_filter"),
        )
        if file_path:
            self.use_single_image_radio.setChecked(True)
            self.single_image_path_edit.setText(file_path)

    def _export_json(self) -> None:
        if not self._current_results:
            QMessageBox.information(
                self,
                tr("benchmark_export_no_results_title"),
                tr("benchmark_export_no_results_msg"),
            )
            return

        benchmarks_dir = get_benchmarks_dir()
        benchmarks_dir.mkdir(parents=True, exist_ok=True)
        default_name = f"benchmark_export_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
        default_path = str(benchmarks_dir / default_name)

        file_path, _ = QFileDialog.getSaveFileName(
            self,
            tr("benchmark_export_json_dialog_title"),
            default_path,
            tr("json_files_filter"),
        )
        if not file_path:
            return

        summary = self._build_summary(self._current_results)
        try:
            # Reuse auto-save structure for consistency
            # but write to user-chosen path.
            benchmarks_dir = Path(file_path).parent
            benchmarks_dir.mkdir(parents=True, exist_ok=True)

            # Build payload
            metadata_ts = datetime.now().isoformat(timespec="seconds")
            payload = {
                "metadata": {
                    "timestamp": metadata_ts,
                },
                "results": [asdict(r) for r in self._current_results],
                "summary_text": summary,
            }
            Path(file_path).write_text(
                json.dumps(payload, indent=2, ensure_ascii=False),
                encoding="utf-8",
            )
            QMessageBox.information(
                self,
                tr("benchmark_export_success_title"),
                tr("benchmark_export_success_msg", path=file_path),
            )
        except Exception as exc:
            QMessageBox.critical(
                self,
                tr("benchmark_export_failed_title"),
                tr("benchmark_export_failed_msg", error=str(exc)),
            )


def show_benchmark_dialog(parent=None, pipeline=None, config_manager=None) -> None:
    """
    Show the benchmark dialog.
    """
    dialog = BenchmarkDialog(parent=parent, pipeline=pipeline, config_manager=config_manager)
    dialog.exec()

