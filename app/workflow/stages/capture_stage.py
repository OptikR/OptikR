"""
Capture Stage

Captures frames from the screen based on the configured region.
"""

from typing import Any
import logging

try:
    from ..managers.pipeline_stage_manager import PipelineStage, StageConfig
except ImportError:
    from app.workflow.managers.pipeline_stage_manager import PipelineStage, StageConfig


class CaptureStage(PipelineStage):
    """
    Captures screen frames from the specified region.
    
    Input: CaptureRegion or None
    Output: Frame object with image data
    """
    
    def __init__(self, capture_layer=None):
        """
        Initialize capture stage.
        
        Args:
            capture_layer: ICaptureLayer implementation
        """
        config = StageConfig(
            name="capture",
            enabled=True,
            required=True,
            timeout=1.0,
            dependencies=[],
            metadata={
                "description": "Captures screen frames",
                "input": "CaptureRegion",
                "output": "Frame"
            }
        )
        super().__init__(config)
        
        self.capture_layer = capture_layer
        self.logger = logging.getLogger(__name__)
    
    def process(self, input_data: Any) -> Any:
        """
        Capture a frame from the screen.
        
        Args:
            input_data: CaptureRegion or None (uses default)
            
        Returns:
            Frame: Captured frame with image data
        """
        if not self.capture_layer:
            raise RuntimeError("Capture layer not initialized")
        
        # Use provided region or default
        region = input_data if input_data else None
        
        # Capture frame
        frame = self.capture_layer.capture_frame(region)
        
        if not frame or not frame.image:
            raise RuntimeError("Failed to capture frame")
        
        self.logger.debug(f"Captured frame: {frame.width}x{frame.height}")
        
        return frame
