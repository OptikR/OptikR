"""
Preprocessing Stage

Preprocesses captured frames to improve OCR accuracy.
"""

from typing import Any
import logging

try:
    from ..managers.pipeline_stage_manager import PipelineStage, StageConfig
except ImportError:
    from app.workflow.managers.pipeline_stage_manager import PipelineStage, StageConfig


class PreprocessingStage(PipelineStage):
    """
    Preprocesses frames for better OCR results.
    
    Input: Frame object
    Output: Frame object with preprocessed image
    """
    
    def __init__(self, preprocessing_layer=None):
        """
        Initialize preprocessing stage.
        
        Args:
            preprocessing_layer: IPreprocessingLayer implementation
        """
        config = StageConfig(
            name="preprocessing",
            enabled=True,
            required=False,  # Optional - can skip if not needed
            timeout=0.5,
            dependencies=["capture"],
            metadata={
                "description": "Preprocesses frames for OCR",
                "input": "Frame",
                "output": "Frame (preprocessed)"
            }
        )
        super().__init__(config)
        
        self.preprocessing_layer = preprocessing_layer
        self.logger = logging.getLogger(__name__)
    
    def process(self, input_data: Any) -> Any:
        """
        Preprocess the frame.
        
        Args:
            input_data: Frame object
            
        Returns:
            Frame: Frame with preprocessed image
        """
        if not input_data:
            raise ValueError("No frame provided for preprocessing")
        
        frame = input_data
        
        # If no preprocessing layer, pass through
        if not self.preprocessing_layer:
            self.logger.debug("No preprocessing layer, passing through")
            return frame
        
        # Preprocess the frame
        preprocessed_frame = self.preprocessing_layer.preprocess(frame)
        
        self.logger.debug(f"Preprocessed frame: {preprocessed_frame.width}x{preprocessed_frame.height}")
        
        return preprocessed_frame
