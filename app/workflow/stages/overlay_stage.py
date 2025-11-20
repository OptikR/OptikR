"""
Overlay Stage

Renders translated text as overlay on screen.
"""

from typing import Any, List
import logging

try:
    from ..managers.pipeline_stage_manager import PipelineStage, StageConfig
except ImportError:
    from app.workflow.managers.pipeline_stage_manager import PipelineStage, StageConfig


class OverlayStage(PipelineStage):
    """
    Renders translations as overlay.
    
    Input: List of Translation objects
    Output: None (displays overlay)
    """
    
    def __init__(self, overlay_renderer=None):
        """
        Initialize overlay stage.
        
        Args:
            overlay_renderer: IOverlayRenderer implementation
        """
        config = StageConfig(
            name="overlay",
            enabled=True,
            required=True,
            timeout=0.5,
            dependencies=["translation"],
            metadata={
                "description": "Renders translated text overlay",
                "input": "List[Translation]",
                "output": "None (displays overlay)"
            }
        )
        super().__init__(config)
        
        self.overlay_renderer = overlay_renderer
        self.logger = logging.getLogger(__name__)
    
    def process(self, input_data: Any) -> Any:
        """
        Render overlay with translations.
        
        Args:
            input_data: List of Translation objects
            
        Returns:
            None: Overlay is displayed
        """
        if not self.overlay_renderer:
            raise RuntimeError("Overlay renderer not initialized")
        
        if not input_data:
            # Clear overlay if no translations
            self.overlay_renderer.clear()
            self.logger.debug("No translations, cleared overlay")
            return None
        
        translations = input_data
        
        # Render overlay
        self.overlay_renderer.render(translations)
        
        self.logger.debug(f"Rendered overlay with {len(translations)} translations")
        
        return None  # Overlay stage doesn't produce output for next stage
