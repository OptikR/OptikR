"""
OCR Settings Tab and Managers

OCR engine selection, model management, and testing.
"""

from .ocr_tab import OCRSettingsTab, OCREngineManager
from .model_manager import OCRModelManager
from .test_manager import OCRTestManager

__all__ = [
    'OCRSettingsTab',
    'OCREngineManager',
    'OCRModelManager',
    'OCRTestManager',
]
