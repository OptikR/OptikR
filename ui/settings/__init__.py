"""
Settings Dialog Components
Modular settings dialog system with tabbed navigation.
"""

from .base_settings_dialog import BaseSettingsDialog, BaseSettingsTab

# Import PyQt6 tabs
from .general_tab_pyqt6 import GeneralSettingsTab
from .capture_tab_pyqt6 import CaptureSettingsTab
from .ocr_tab_pyqt6 import OCRSettingsTab
from .translation_tab_pyqt6 import TranslationSettingsTab
from .overlay_tab_pyqt6 import OverlaySettingsTab
from .storage_tab_pyqt6 import StorageSettingsTab
from .pipeline_management_tab_pyqt6 import PipelineManagementTab
from .advanced_tab_pyqt6 import AdvancedSettingsTab

__all__ = [
    'BaseSettingsDialog',
    'BaseSettingsTab',
    'GeneralSettingsTab',
    'CaptureSettingsTab',
    'OCRSettingsTab',
    'TranslationSettingsTab',
    'OverlaySettingsTab',
    'StorageSettingsTab',
    'PipelineManagementTab',
    'AdvancedSettingsTab',
]
