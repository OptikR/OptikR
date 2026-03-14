"""Input tab for the Image Processing dialog.

Provides file/folder pickers, drag-and-drop, an image queue list with
thumbnails, and basic queue management (remove, clear).
"""

import logging
from pathlib import Path
from typing import Any

from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QListWidget, QListWidgetItem, QFileDialog, QGroupBox, QSplitter,
)
from PyQt6.QtCore import Qt, QSize, pyqtSignal
from PyQt6.QtGui import QPixmap, QIcon

from app.localization import TranslatableMixin, tr

logger = logging.getLogger(__name__)

SUPPORTED_FILTER = "Images (*.png *.jpg *.jpeg *.bmp *.tiff *.tif *.webp)"
SUPPORTED_EXTENSIONS = {".png", ".jpg", ".jpeg", ".bmp", ".tiff", ".tif", ".webp"}

_THUMB_SIZE = QSize(64, 64)


class InputTab(TranslatableMixin, QWidget):
    """Image queue tab with file/folder pickers and drag-and-drop."""

    filesChanged = pyqtSignal()

    def __init__(self, config_manager: Any = None, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.config_manager = config_manager
        self._init_ui()

    # ------------------------------------------------------------------
    # UI construction
    # ------------------------------------------------------------------

    def _init_ui(self) -> None:
        layout = QVBoxLayout(self)
        layout.setContentsMargins(10, 10, 10, 10)
        layout.setSpacing(10)

        # --- Top button row ---
        btn_layout = QHBoxLayout()

        self.add_images_btn = QPushButton()
        self.set_translatable_text(self.add_images_btn, "image_processing_add_images")
        self.add_images_btn.setProperty("class", "action")
        self.add_images_btn.clicked.connect(self._on_add_images)
        btn_layout.addWidget(self.add_images_btn)

        self.add_folder_btn = QPushButton()
        self.set_translatable_text(self.add_folder_btn, "image_processing_add_folder")
        self.add_folder_btn.setProperty("class", "action")
        self.add_folder_btn.clicked.connect(self._on_add_folder)
        btn_layout.addWidget(self.add_folder_btn)

        btn_layout.addStretch()

        self.remove_btn = QPushButton()
        self.set_translatable_text(self.remove_btn, "image_processing_remove_selected")
        self.remove_btn.clicked.connect(self._on_remove_selected)
        btn_layout.addWidget(self.remove_btn)

        self.clear_btn = QPushButton()
        self.set_translatable_text(self.clear_btn, "image_processing_clear_all")
        self.clear_btn.clicked.connect(self._on_clear_all)
        btn_layout.addWidget(self.clear_btn)

        layout.addLayout(btn_layout)

        # --- Splitter: list on left, preview on right ---
        splitter = QSplitter(Qt.Orientation.Horizontal)

        # Image queue list
        self.image_list = QListWidget()
        self.image_list.setIconSize(_THUMB_SIZE)
        self.image_list.setSelectionMode(QListWidget.SelectionMode.ExtendedSelection)
        self.image_list.setDragDropMode(QListWidget.DragDropMode.NoDragDrop)
        self.image_list.setAcceptDrops(True)
        self.image_list.dragEnterEvent = self._drag_enter
        self.image_list.dragMoveEvent = self._drag_move
        self.image_list.dropEvent = self._drop
        self.image_list.currentItemChanged.connect(self._on_selection_changed)
        splitter.addWidget(self.image_list)

        # Preview panel
        preview_group = QGroupBox()
        self.set_translatable_text(preview_group, "image_processing_preview")
        preview_layout = QVBoxLayout(preview_group)
        preview_layout.setContentsMargins(10, 18, 10, 10)

        self.preview_label = QLabel()
        self.preview_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.preview_label.setMinimumSize(200, 200)
        self.preview_label.setStyleSheet("background-color: #1E1E1E; border-radius: 4px;")
        preview_layout.addWidget(self.preview_label)

        self.file_info_label = QLabel()
        self.file_info_label.setStyleSheet("color: #888888; font-size: 9pt;")
        self.file_info_label.setWordWrap(True)
        preview_layout.addWidget(self.file_info_label)

        splitter.addWidget(preview_group)
        splitter.setStretchFactor(0, 3)
        splitter.setStretchFactor(1, 2)

        layout.addWidget(splitter, 1)

        # --- Status bar ---
        status_layout = QHBoxLayout()

        self.count_label = QLabel()
        self.set_translatable_text(self.count_label, "image_processing_images_loaded", count=0)
        self.count_label.setStyleSheet("font-size: 9pt; color: #AAAAAA;")
        status_layout.addWidget(self.count_label)

        status_layout.addStretch()

        hint_label = QLabel()
        self.set_translatable_text(hint_label, "image_processing_drag_drop_hint")
        hint_label.setStyleSheet("font-size: 8pt; color: #666666; font-style: italic;")
        status_layout.addWidget(hint_label)

        layout.addLayout(status_layout)

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def get_files(self) -> list[str]:
        """Return ordered list of queued image file paths."""
        files: list[str] = []
        for i in range(self.image_list.count()):
            item = self.image_list.item(i)
            path = item.data(Qt.ItemDataRole.UserRole)
            if path:
                files.append(path)
        return files

    def file_count(self) -> int:
        return self.image_list.count()

    # ------------------------------------------------------------------
    # Slots
    # ------------------------------------------------------------------

    def _on_add_images(self) -> None:
        last_dir = ""
        if self.config_manager:
            last_dir = self.config_manager.get_setting("image_processing.last_input_folder", "")

        files, _ = QFileDialog.getOpenFileNames(
            self, tr("image_processing_add_images"), last_dir, SUPPORTED_FILTER,
        )
        if files:
            self._add_files(files)
            if self.config_manager:
                self.config_manager.set_setting(
                    "image_processing.last_input_folder", str(Path(files[0]).parent),
                )

    def _on_add_folder(self) -> None:
        last_dir = ""
        if self.config_manager:
            last_dir = self.config_manager.get_setting("image_processing.last_input_folder", "")

        folder = QFileDialog.getExistingDirectory(
            self, tr("image_processing_add_folder"), last_dir,
        )
        if folder:
            images = [
                str(p) for p in Path(folder).rglob("*")
                if p.suffix.lower() in SUPPORTED_EXTENSIONS
            ]
            images.sort()
            self._add_files(images)
            if self.config_manager:
                self.config_manager.set_setting("image_processing.last_input_folder", folder)

    def _on_remove_selected(self) -> None:
        for item in reversed(self.image_list.selectedItems()):
            row = self.image_list.row(item)
            self.image_list.takeItem(row)
        self._update_count()

    def _on_clear_all(self) -> None:
        self.image_list.clear()
        self.preview_label.clear()
        self.file_info_label.clear()
        self._update_count()

    def _on_selection_changed(self, current: QListWidgetItem | None, _prev: QListWidgetItem | None) -> None:
        if current is None:
            self.preview_label.clear()
            self.file_info_label.clear()
            return
        path = current.data(Qt.ItemDataRole.UserRole)
        if not path:
            return
        self._show_preview(path)

    # ------------------------------------------------------------------
    # Drag-and-drop handlers (installed on the list widget)
    # ------------------------------------------------------------------

    def _drag_enter(self, event) -> None:
        if event.mimeData().hasUrls():
            event.acceptProposedAction()

    def _drag_move(self, event) -> None:
        if event.mimeData().hasUrls():
            event.acceptProposedAction()

    def _drop(self, event) -> None:
        paths: list[str] = []
        for url in event.mimeData().urls():
            local = url.toLocalFile()
            p = Path(local)
            if p.is_file() and p.suffix.lower() in SUPPORTED_EXTENSIONS:
                paths.append(str(p))
            elif p.is_dir():
                paths.extend(
                    str(f) for f in p.rglob("*")
                    if f.suffix.lower() in SUPPORTED_EXTENSIONS
                )
        if paths:
            paths.sort()
            self._add_files(paths)
            event.acceptProposedAction()

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------

    def _add_files(self, paths: list[str]) -> None:
        existing = set(self.get_files())
        added = 0
        for path in paths:
            if path in existing:
                continue
            existing.add(path)
            p = Path(path)
            try:
                size_kb = p.stat().st_size / 1024
                label = f"{p.name}  ({size_kb:.0f} KB)"
            except OSError:
                label = p.name

            item = QListWidgetItem(label)
            item.setData(Qt.ItemDataRole.UserRole, path)

            thumb = self._make_thumbnail(path)
            if thumb:
                item.setIcon(QIcon(thumb))

            self.image_list.addItem(item)
            added += 1

        if added:
            self._update_count()

    def _update_count(self) -> None:
        count = self.image_list.count()
        self.set_translatable_text(self.count_label, "image_processing_images_loaded", count=count)
        self.filesChanged.emit()

    @staticmethod
    def _make_thumbnail(path: str) -> QPixmap | None:
        try:
            pixmap = QPixmap(path)
            if pixmap.isNull():
                return None
            return pixmap.scaled(_THUMB_SIZE, Qt.AspectRatioMode.KeepAspectRatio, Qt.TransformationMode.SmoothTransformation)
        except Exception:
            return None

    def _show_preview(self, path: str) -> None:
        try:
            pixmap = QPixmap(path)
            if pixmap.isNull():
                self.preview_label.setText(tr("image_processing_preview_unavailable"))
                self.file_info_label.clear()
                return
            preview_size = self.preview_label.size()
            scaled = pixmap.scaled(preview_size, Qt.AspectRatioMode.KeepAspectRatio, Qt.TransformationMode.SmoothTransformation)
            self.preview_label.setPixmap(scaled)

            p = Path(path)
            try:
                size_kb = p.stat().st_size / 1024
                info = f"{p.name}\n{pixmap.width()} x {pixmap.height()} px  |  {size_kb:.1f} KB"
            except OSError:
                info = p.name
            self.file_info_label.setText(info)
        except Exception:
            self.preview_label.clear()
            self.file_info_label.clear()
