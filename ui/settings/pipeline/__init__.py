"""
Pipeline Management Settings Tab — Central Pipeline Hub

Pipeline configuration, flow visualization, diagnostics, and all
stage-specific settings (Capture, OCR, Translation, AI Processing,
Vision, Audio, Overlay, Plugins).
"""

from .pipeline_tab import PipelineManagementTab
from .vision_section import VisionSettingsSection

__all__ = ['PipelineManagementTab', 'VisionSettingsSection']
