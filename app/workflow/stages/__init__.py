"""
Pipeline Stages Package

Individual stage implementations for the translation pipeline.
Each stage is a self-contained processing unit.
"""

from .capture_stage import CaptureStage
from .preprocessing_stage import PreprocessingStage
from .ocr_stage import OCRStage
from .validation_stage import ValidationStage
from .translation_stage import TranslationStage
from .overlay_stage import OverlayStage

__all__ = [
    "CaptureStage",
    "PreprocessingStage",
    "OCRStage",
    "ValidationStage",
    "TranslationStage",
    "OverlayStage",
]
