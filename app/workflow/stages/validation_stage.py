"""
Validation Stage

Validates detected text blocks to filter out false positives.
"""

from typing import Any, List
import logging

try:
    from ..managers.pipeline_stage_manager import PipelineStage, StageConfig
except ImportError:
    from app.workflow.managers.pipeline_stage_manager import PipelineStage, StageConfig


class ValidationStage(PipelineStage):
    """
    Validates text blocks to filter false positives.
    
    Input: List of TextBlock objects
    Output: List of validated TextBlock objects
    """
    
    def __init__(self, text_validator=None, config_manager=None):
        """
        Initialize validation stage.
        
        Args:
            text_validator: TextValidator implementation
            config_manager: Optional config manager for settings
        """
        config = StageConfig(
            name="validation",
            enabled=True,
            required=False,  # Optional - can skip validation
            timeout=0.5,
            dependencies=["ocr"],
            metadata={
                "description": "Validates detected text blocks",
                "input": "List[TextBlock]",
                "output": "List[TextBlock] (validated)"
            }
        )
        super().__init__(config)
        
        self.text_validator = text_validator
        self.config_manager = config_manager
        self.logger = logging.getLogger(__name__)
    
    def process(self, input_data: Any) -> Any:
        """
        Validate text blocks.
        
        Args:
            input_data: List of TextBlock objects
            
        Returns:
            List[TextBlock]: Validated text blocks
        """
        if not input_data:
            self.logger.debug("No text blocks to validate")
            return []
        
        text_blocks = input_data
        
        # If no validator, pass through
        if not self.text_validator:
            self.logger.debug("No text validator, passing through")
            return text_blocks
        
        # Validate each block
        validated_blocks = []
        rejected_count = 0
        
        # Get min_confidence from config_manager (default 0.3)
        min_conf = self.config_manager.get_setting(
            'pipeline.plugins.text_validator.min_confidence', 0.3
        ) if self.config_manager else 0.3
        
        for block in text_blocks:
            is_valid, confidence, reason = self.text_validator.is_valid_text(
                block.text,
                min_confidence=min_conf
            )
            
            if is_valid:
                validated_blocks.append(block)
            else:
                rejected_count += 1
                self.logger.debug(f"Rejected text: '{block.text}' - {reason} (confidence: {confidence:.2f})")
        
        self.logger.debug(
            f"Validated {len(validated_blocks)} blocks, "
            f"rejected {rejected_count}"
        )
        
        return validated_blocks
