"""
Bubble-Aware OCR Processor

Combines bubble detection with OCR to:
1. Use grid-based OCR for accurate text recognition
2. Map recognized text back to actual bubble positions
3. Provide accurate overlay positioning

Author: Kiro AI Assistant
Date: 2025-11-25
"""

import logging
from typing import List, Optional, Any
import numpy as np

try:
    from .bubble_detector import BubbleDetector, BubbleRegion
    from .intelligent_ocr_processor import IntelligentOCRProcessor, TextBlock
    from ..models import TextBlock as OCRTextBlock, Rectangle
except ImportError:
    from app.ocr.bubble_detector import BubbleDetector, BubbleRegion
    from app.ocr.intelligent_ocr_processor import IntelligentOCRProcessor, TextBlock
    from app.models import TextBlock as OCRTextBlock, Rectangle


class BubbleAwareOCRProcessor:
    """
    OCR processor that uses bubble detection to improve overlay positioning.
    
    Workflow:
    1. Detect speech bubbles in the frame
    2. Perform grid-based OCR for accurate text recognition
    3. Map OCR results to detected bubbles
    4. Return text blocks with bubble-based positions for accurate overlays
    """
    
    def __init__(self, config: Optional[dict] = None):
        """
        Initialize bubble-aware OCR processor.
        
        Args:
            config: Configuration dictionary
        """
        self.logger = logging.getLogger(__name__)
        self.config = config or {}
        
        # Initialize sub-components
        self.bubble_detector = BubbleDetector(self.config.get('bubble_detection', {}))
        self.ocr_processor = IntelligentOCRProcessor(self.config.get('ocr_processing', {}))
        
        # Configuration
        self.use_bubble_detection = self.config.get('use_bubble_detection', True)
        self.expand_bubble_margin = self.config.get('expand_bubble_margin', 5)
        
    def process(self, text_blocks: List[Any], frame: Optional[np.ndarray] = None) -> List[Any]:
        """
        Process OCR text blocks with bubble awareness.
        
        Args:
            text_blocks: Raw OCR text blocks
            frame: Original frame for bubble detection
            
        Returns:
            Processed text blocks with bubble-based positions
        """
        if not text_blocks:
            return text_blocks
        
        # Step 1: Apply intelligent OCR processing (merging, spell check, etc.)
        processed_blocks = self.ocr_processor.process(text_blocks)
        
        if not processed_blocks:
            return processed_blocks
        
        # Step 2: If bubble detection is disabled or no frame, return processed blocks
        if not self.use_bubble_detection or frame is None:
            return processed_blocks
        
        # Step 3: Detect bubbles in the frame
        try:
            bubbles = self.bubble_detector.detect_bubbles(frame)
            self.logger.debug(f"Detected {len(bubbles)} speech bubbles")
            
            if not bubbles:
                # No bubbles detected, return original processed blocks
                return processed_blocks
            
            # Step 4: Map text blocks to bubbles
            bubble_mapped_blocks = self._map_blocks_to_bubbles(processed_blocks, bubbles)
            
            return bubble_mapped_blocks
            
        except Exception as e:
            self.logger.error(f"Bubble detection failed: {e}")
            # Fall back to original processed blocks
            return processed_blocks
    
    def _map_blocks_to_bubbles(self, text_blocks: List[Any], 
                               bubbles: List[BubbleRegion]) -> List[Any]:
        """
        Map text blocks to detected bubbles for accurate positioning.
        
        Strategy:
        - For each merged text block, find which bubble(s) it belongs to
        - Adjust the text block position to match the bubble position
        - This ensures overlays appear over the actual speech bubble
        
        Args:
            text_blocks: Processed OCR text blocks
            bubbles: Detected bubble regions
            
        Returns:
            Text blocks with bubble-based positions
        """
        mapped_blocks = []
        
        for block in text_blocks:
            try:
                # Get block position
                if hasattr(block, 'position'):
                    pos = block.position
                    block_x = pos.x + pos.width // 2  # Use center point
                    block_y = pos.y + pos.height // 2
                else:
                    # Skip blocks without position
                    mapped_blocks.append(block)
                    continue
                
                # Find bubble containing this text
                bubble = self.bubble_detector.find_bubble_for_text(block_x, block_y, bubbles)
                
                if bubble:
                    # Adjust block position to bubble position
                    # Add small margin to avoid edge clipping
                    adjusted_x = bubble.x + self.expand_bubble_margin
                    adjusted_y = bubble.y + self.expand_bubble_margin
                    adjusted_width = bubble.width - 2 * self.expand_bubble_margin
                    adjusted_height = bubble.height - 2 * self.expand_bubble_margin
                    
                    # Create new block with bubble position
                    adjusted_block = OCRTextBlock(
                        text=block.text,
                        position=Rectangle(
                            x=adjusted_x,
                            y=adjusted_y,
                            width=adjusted_width,
                            height=adjusted_height
                        ),
                        confidence=block.confidence,
                        estimated_font_size=block.estimated_font_size if hasattr(block, 'estimated_font_size') else None
                    )
                    
                    # Store original position in metadata for debugging
                    if not hasattr(adjusted_block, 'metadata'):
                        adjusted_block.metadata = {}
                    adjusted_block.metadata['original_position'] = {
                        'x': pos.x, 'y': pos.y, 
                        'width': pos.width, 'height': pos.height
                    }
                    adjusted_block.metadata['bubble_mapped'] = True
                    
                    mapped_blocks.append(adjusted_block)
                    
                    self.logger.debug(
                        f"Mapped text '{block.text[:20]}...' from "
                        f"({pos.x}, {pos.y}) to bubble ({adjusted_x}, {adjusted_y})"
                    )
                else:
                    # No bubble found, keep original position
                    mapped_blocks.append(block)
                    self.logger.debug(f"No bubble found for text '{block.text[:20]}...'")
                
            except Exception as e:
                self.logger.error(f"Failed to map block to bubble: {e}")
                # Keep original block on error
                mapped_blocks.append(block)
        
        return mapped_blocks
    
    def set_bubble_detection_enabled(self, enabled: bool):
        """Enable or disable bubble detection"""
        self.use_bubble_detection = enabled
        self.logger.info(f"Bubble detection {'enabled' if enabled else 'disabled'}")
    
    def get_stats(self) -> dict:
        """Get processing statistics"""
        stats = self.ocr_processor.get_stats()
        stats['bubble_detection_enabled'] = self.use_bubble_detection
        return stats


# Export
__all__ = ['BubbleAwareOCRProcessor']
