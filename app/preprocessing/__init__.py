"""
Preprocessing Layer

Component responsible for optimizing captured frames for OCR accuracy.
Includes frame differencing, ROI optimization, and configurable image processing.
"""

from .preprocessing_layer import PreprocessingLayer, PreprocessingProfile, FilterType
from .frame_differencing import (
    DifferenceConfig, DifferenceMethod, SensitivityLevel,
    DifferenceResult, ChangeRegion
)

__all__ = [
    'PreprocessingLayer',
    'PreprocessingProfile', 
    'FilterType',
    'DifferenceConfig',
    'DifferenceMethod',
    'SensitivityLevel',
    'DifferenceResult',
    'ChangeRegion'
]