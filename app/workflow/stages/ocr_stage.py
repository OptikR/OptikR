"""
OCR Stage

Performs optical character recognition on frames.
"""

from typing import Any, Optional
import logging

try:
    from ..managers.pipeline_stage_manager import PipelineStage, StageConfig
except ImportError:
    from app.workflow.managers.pipeline_stage_manager import PipelineStage, StageConfig

# Try to import bubble-aware processor
try:
    from app.ocr.bubble_aware_ocr_processor import BubbleAwareOCRProcessor
    BUBBLE_AWARE_AVAILABLE = True
except ImportError:
    BUBBLE_AWARE_AVAILABLE = False


class OCRStage(PipelineStage):
    """
    Performs OCR on frames to extract text.
    
    Input: Frame object
    Output: List of TextBlock objects
    """
    
    def __init__(self, ocr_layer=None, confidence_threshold=0.7, 
                 use_bubble_detection=True, config_manager=None):
        """
        Initialize OCR stage.
        
        Args:
            ocr_layer: IOCRLayer implementation
            confidence_threshold: Minimum confidence for text detection
            use_bubble_detection: Enable bubble-aware OCR processing
            config_manager: Configuration manager for settings
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
        
        # Initialize bubble-aware processor if available
        self.bubble_processor: Optional[BubbleAwareOCRProcessor] = None
        if BUBBLE_AWARE_AVAILABLE and use_bubble_detection:
            try:
                # Load config from config_manager if available
                bubble_config = {}
                if config_manager:
                    bubble_config = {
                        'use_bubble_detection': config_manager.get_setting('ocr.use_bubble_detection', True),
                        'bubble_detection': {
                            'min_bubble_area': config_manager.get_setting('ocr.min_bubble_area', 500),
                            'max_bubble_area': config_manager.get_setting('ocr.max_bubble_area', 50000),
                            'brightness_threshold': config_manager.get_setting('ocr.brightness_threshold', 200),
                        },
                        'expand_bubble_margin': config_manager.get_setting('ocr.expand_bubble_margin', 5)
                    }
                
                self.bubble_processor = BubbleAwareOCRProcessor(bubble_config)
                self.logger.info("Bubble-aware OCR processing enabled")
            except Exception as e:
                self.logger.warning(f"Failed to initialize bubble-aware processing: {e}")
                self.bubble_processor = None
        else:
            if not BUBBLE_AWARE_AVAILABLE:
                self.logger.info("Bubble-aware OCR not available")
            else:
                self.logger.info("Bubble-aware OCR disabled")
    
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
        
        # Apply bubble-aware processing if available
        if self.bubble_processor and filtered_blocks:
            try:
                # Get frame data for bubble detection
                frame_data = frame.data if hasattr(frame, 'data') else frame
                
                # Process with bubble awareness
                processed_blocks = self.bubble_processor.process(filtered_blocks, frame_data)
                
                self.logger.debug(
                    f"Bubble-aware processing: {len(filtered_blocks)} blocks → "
                    f"{len(processed_blocks)} bubble-mapped blocks"
                )
                
                return processed_blocks
            except Exception as e:
                self.logger.error(f"Bubble-aware processing failed: {e}, using original blocks")
                return filtered_blocks
        
        return filtered_blocks
