"""Image Processing dialog.

Main dialog that assembles the Input, Settings, and Output tabs and
wires them to the :class:`BatchProcessor` for batch image translation.
"""

import logging
from typing import Any

from PyQt6.QtWidgets import (
    QDialog, QVBoxLayout, QLabel, QTabWidget, QMessageBox,
)
from PyQt6.QtCore import Qt

from app.localization import TranslatableMixin, tr
from app.image_processing.image_compositor import ImageCompositor
from app.image_processing.image_pipeline import ImagePipeline
from app.image_processing.batch_processor import BatchProcessor

from .input_tab import InputTab
from .settings_tab import SettingsTab
from .output_tab import OutputTab

logger = logging.getLogger(__name__)


class ImageProcessingDialog(TranslatableMixin, QDialog):
    """Batch image translation dialog.

    Parameters
    ----------
    parent :
        Parent widget (usually ``MainWindow``).
    pipeline :
        The startup pipeline that provides OCR/translation layers.
    config_manager :
        Application configuration facade.
    """

    def __init__(
        self,
        parent: Any = None,
        pipeline: Any = None,
        config_manager: Any = None,
    ) -> None:
        super().__init__(parent)
        self.pipeline = pipeline
        self.config_manager = config_manager

        self._batch_processor: BatchProcessor | None = None

        self.setWindowTitle(tr("image_processing_title"))
        self.setMinimumSize(1000, 750)

        self._init_ui()

    # ------------------------------------------------------------------
    # UI construction
    # ------------------------------------------------------------------

    def _init_ui(self) -> None:
        layout = QVBoxLayout(self)

        title = QLabel(tr("image_processing_title"))
        title.setStyleSheet("font-size: 16pt; font-weight: bold; margin-bottom: 5px;")
        layout.addWidget(title)

        desc = QLabel(tr("image_processing_description"))
        desc.setStyleSheet("color: #666666; margin-bottom: 10px;")
        desc.setWordWrap(True)
        layout.addWidget(desc)

        self.tab_widget = QTabWidget()

        self.input_tab = InputTab(config_manager=self.config_manager, parent=self)
        self.tab_widget.addTab(self.input_tab, tr("image_processing_tab_input"))

        self.settings_tab = SettingsTab(config_manager=self.config_manager, parent=self)
        self.tab_widget.addTab(self.settings_tab, tr("image_processing_tab_settings"))

        self.output_tab = OutputTab(config_manager=self.config_manager, parent=self)
        self.tab_widget.addTab(self.output_tab, tr("image_processing_tab_output"))

        layout.addWidget(self.tab_widget, 1)

        # Wire signals
        self.output_tab.processRequested.connect(self._on_process)
        self.output_tab.cancelRequested.connect(self._on_cancel)

    # ------------------------------------------------------------------
    # Batch processing
    # ------------------------------------------------------------------

    def _on_process(self) -> None:
        """Validate inputs and start the batch processor."""
        files = self.input_tab.get_files()
        if not files:
            QMessageBox.warning(
                self,
                tr("image_processing_title"),
                tr("image_processing_no_images"),
            )
            return

        output_config = self.output_tab.get_output_config()
        if not output_config.get("output_folder"):
            QMessageBox.warning(
                self,
                tr("image_processing_title"),
                tr("image_processing_no_output_folder"),
            )
            return

        # Build the pipeline & compositor
        compositor = ImageCompositor(self.settings_tab.get_compositor_config())

        if self.pipeline is not None:
            img_pipeline = ImagePipeline.from_startup_pipeline(
                self.pipeline, self.config_manager, compositor,
            )
        else:
            QMessageBox.warning(
                self,
                tr("image_processing_title"),
                tr("image_processing_pipeline_unavailable"),
            )
            return

        # Language overrides
        src_lang, tgt_lang = self.settings_tab.get_language_overrides()

        # Persist settings before processing
        self.settings_tab.save_config()
        self.output_tab.save_config()

        # Create batch processor
        self._batch_processor = BatchProcessor(
            pipeline=img_pipeline,
            compositor=compositor,
            config_manager=self.config_manager,
            parent=self,
        )
        self._batch_processor.set_files(files)
        self._batch_processor.set_output_config(output_config)
        self._batch_processor.set_compositor_config(self.settings_tab.get_compositor_config())
        if src_lang and tgt_lang:
            self._batch_processor.set_languages(src_lang, tgt_lang)

        # Connect signals
        self._batch_processor.progress.connect(self._on_progress)
        self._batch_processor.image_completed.connect(self._on_image_completed)
        self._batch_processor.batch_completed.connect(self._on_batch_completed)

        # Switch to processing state
        self.output_tab.set_processing_state(True)
        self.tab_widget.setCurrentWidget(self.output_tab)

        self._batch_processor.start()

    def _on_cancel(self) -> None:
        if self._batch_processor is not None:
            self._batch_processor.stop()

    def _on_progress(self, current: int, total: int, filename: str, status: str) -> None:
        self.output_tab.update_progress(current, total, filename, status)

    def _on_image_completed(self, filepath: str, success: bool, error_msg: str) -> None:
        self.output_tab.append_result_line(filepath, success, error_msg)

    def _on_batch_completed(self, total: int, succeeded: int, failed: int) -> None:
        self.output_tab.show_results(total, succeeded, failed)
        self._batch_processor = None

    # ------------------------------------------------------------------
    # Cleanup
    # ------------------------------------------------------------------

    def closeEvent(self, event) -> None:
        if self._batch_processor is not None and self._batch_processor.isRunning():
            reply = QMessageBox.question(
                self,
                tr("image_processing_title"),
                tr("image_processing_cancel_confirm"),
            )
            if reply != QMessageBox.StandardButton.Yes:
                event.ignore()
                return
            self._batch_processor.stop()
            self._batch_processor.wait(5000)

        self.settings_tab.save_config()
        self.output_tab.save_config()
        super().closeEvent(event)
