"""Image processing dialog package.

Provides a batch image translation dialog with input queue,
settings configuration, and output/progress management.
"""

from .image_processing_dialog import ImageProcessingDialog


def show_image_processing_dialog(parent=None, pipeline=None, config_manager=None):
    """Show the image processing dialog modally.

    Parameters
    ----------
    parent :
        Parent widget (usually ``MainWindow``).
    pipeline :
        The startup pipeline that provides OCR/translation layers.
    config_manager :
        Application configuration facade.
    """
    dialog = ImageProcessingDialog(parent, pipeline, config_manager)
    dialog.exec()


__all__ = ["ImageProcessingDialog", "show_image_processing_dialog"]
