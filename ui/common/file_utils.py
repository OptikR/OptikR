"""
Shared file/folder utilities for the UI layer.
"""

import logging
import os
import platform
import subprocess

from PyQt6.QtWidgets import QMessageBox, QWidget

logger = logging.getLogger(__name__)


def open_folder(folder_path: str, parent_widget: QWidget) -> None:
    """Open *folder_path* in the system file explorer.

    Creates the directory first if it doesn't exist.  On failure a warning
    dialog is shown to the user.

    Args:
        folder_path: Absolute or relative path to open.
        parent_widget: Parent widget for the error dialog.
    """
    try:
        if not os.path.isabs(folder_path):
            folder_path = os.path.abspath(folder_path)
        if not os.path.exists(folder_path):
            os.makedirs(folder_path, exist_ok=True)
            logger.info("Created folder: %s", folder_path)
        system = platform.system()
        if system == "Windows":
            os.startfile(folder_path)
        elif system == "Darwin":
            subprocess.run(["open", folder_path], check=False)
        else:
            subprocess.run(["xdg-open", folder_path], check=False)
        logger.debug("Opened folder: %s", folder_path)
    except Exception as e:
        logger.error("Failed to open folder: %s", e)
        QMessageBox.warning(
            parent_widget,
            "Open Folder Failed",
            f"Could not open folder:\n{folder_path}\n\nError: {str(e)}"
        )
