"""
OCR Stage

Performs optical character recognition on frames.
"""

from typing import Any
import logging

try:
    from ..managers.pipeline_stage_manager import PipelineStage, StageConfig
except ImportError:
    from app.workflow.managers.pipeline_stage_manager import PipelineStage, StageConfig


class OCRStage(PipelineStage):
    """
    Performs OCR on frames to extract text.
    
    Input: Frame object
    Output: List of TextBlock objects
    """
    
    def __init__(self, ocr_layer=None, confidence_threshold=0.7):
        """
        Initialize OCR stage.
        
        Args:
            ocr_layer: IOCRLayer implementation
            confidence_threshold: Minimum confidence for text detection
        """
        config = StageConfig(
            name="ocr",
            enabled=True,
            required=True,
            timeout=2.0,
            dependencies=["capture"],  # Can work with or without preprocessing
            metadata={
                "description": "Extracts text from frames",
                "input": "Frame",
                "output": "List[TextBlock]"
            }
        )
        super().__init__(config)
        
        self.ocr_layer = ocr_layer
        self.confidence_threshold = confidence_threshold
        self.logger = logging.getLogger(__name__)
    
    def process(self, input_data: Any) -> Any:
        """
        Perform OCR on the frame.
        
        Args:
            input_data: Frame object
            
        Returns:
            List[TextBlock]: Detected text blocks
        """
        if not self.ocr_layer:
            raise RuntimeError("OCR layer not initialized")
        
        if not input_data:
            raise ValueError("No frame provided for OCR")
        
        frame = input_data
        
        # Perform OCR
        text_blocks = self.ocr_layer.recognize_text(frame)
        
        # Filter by confidence
        filtered_blocks = [
            block for block in text_blocks
            if block.confidence >= self.confidence_threshold
        ]
        
        self.logger.debug(
            f"OCR detected {len(text_blocks)} blocks, "
            f"{len(filtered_blocks)} above threshold ({self.confidence_threshold})"
        )
        
        return filtered_blocks
