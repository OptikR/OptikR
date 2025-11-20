"""
Subprocess Wrappers - Specific implementations for each pipeline stage.

Each wrapper extends BaseSubprocess and handles:
- Data encoding/decoding for its stage
- Stage-specific message preparation
- Result parsing
"""

from .capture_subprocess import CaptureSubprocess
from .ocr_subprocess import OCRSubprocess
from .translation_subprocess import TranslationSubprocess

__all__ = [
    'CaptureSubprocess',
    'OCRSubprocess',
    'TranslationSubprocess',
]
