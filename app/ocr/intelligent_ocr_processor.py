"""
Intelligent OCR Post-Processor

Improves OCR results through:
1. Spatial text block merging (merge nearby fragments)
2. Context-aware validation (consider surrounding text)
3. Spell checking and correction (fix common OCR errors)
4. Consistent processing (same results for same input)

Author: Kiro AI Assistant
Date: 2025-11-17
"""

import re
import logging
from typing import List, Dict, Any, Tuple, Optional
from dataclasses import dataclass


@dataclass
class TextBlock:
    """Represents a text block with position and metadata"""
    text: str
    x: int
    y: int
    width: int
    height: int
    confidence: float
    
    @property
    def center_x(self) -> float:
        return self.x + self.width / 2
    
    @property
    def center_y(self) -> float:
        return self.y + self.height / 2
    
    @property
    def area(self) -> int:
        return self.width * self.height


class IntelligentOCRProcessor:
    """
    Intelligent OCR post-processor that improves OCR results through
    spatial analysis, context awareness, and spell checking.
    """
    
    def __init__(self, config: Optional[Dict[str, Any]] = None):
        """
        Initialize intelligent OCR processor.
        
        Args:
            config: Configuration dictionary
        """
        self.logger = logging.getLogger(__name__)
        self.config = config or {}
        
        # Merging parameters
        self.horizontal_threshold = self.config.get('horizontal_threshold', 30)
        self.vertical_threshold = self.config.get('vertical_threshold', 15)
        self.min_confidence = self.config.get('min_confidence', 0.2)
        
        # Spell checking
        self.enable_spell_check = self.config.get('enable_spell_check', True)
        self.common_ocr_errors = {
            # Common OCR mistakes
            'DENTIFICATION': 'IDENTIFICATION',
            'IDENTIF CATION': 'IDENTIFICATION',
            'IDENTIF1CATION': 'IDENTIFICATION',
            'Wouldnt': "Wouldn't",
            'Nouldnt': "Wouldn't",
            'Couldnt': "Couldn't",
            'Shouldnt': "Shouldn't",
            'Doesnt': "Doesn't",
            'Didnt': "Didn't",
            'Wont': "Won't",
            'Cant': "Can't",
            'Isnt': "Isn't",
            'Arent': "Aren't",
            'Wasnt': "Wasn't",
            'Werent': "Weren't",
            'Hasnt': "Hasn't",
            'Havent': "Haven't",
            'Hadnt': "Hadn't",
        }
        
        # Statistics
        self.stats = {
            'blocks_processed': 0,
            'blocks_merged': 0,
            'spell_corrections': 0,
            'validation_filtered': 0
        }
    
    def process(self, text_blocks: List[Any]) -> List[Any]:
        """
        Process OCR text blocks intelligently.
        
        Args:
            text_blocks: List of text blocks from OCR
            
        Returns:
            List of processed text blocks
        """
        if not text_blocks:
            return text_blocks
        
        self.stats['blocks_processed'] += len(text_blocks)
        
        # Step 1: Convert to internal format
        blocks = self._convert_to_internal_format(text_blocks)
        
        # Step 2: Spatial merging (merge nearby fragments FIRST)
        merged_blocks = self._spatial_merge(blocks)
        self.stats['blocks_merged'] += len(blocks) - len(merged_blocks)
        
        # Step 3: Spell checking and correction
        if self.enable_spell_check:
            corrected_blocks = self._spell_check_blocks(merged_blocks)
        else:
            corrected_blocks = merged_blocks
        
        # Step 4: Context-aware validation
        validated_blocks = self._context_aware_validation(corrected_blocks)
        self.stats['validation_filtered'] += len(corrected_blocks) - len(validated_blocks)
        
        # Step 5: Convert back to original format
        result = self._convert_from_internal_format(validated_blocks, text_blocks)
        
        return result
    
    def _convert_to_internal_format(self, text_blocks: List[Any]) -> List[TextBlock]:
        """Convert OCR text blocks to internal format."""
        blocks = []
        
        for block in text_blocks:
            try:
                # Extract text
                text = block.text if hasattr(block, 'text') else str(block)
                
                # Extract position
                if hasattr(block, 'position'):
                    pos = block.position
                    x, y = pos.x, pos.y
                    width, height = pos.width, pos.height
                elif hasattr(block, 'bbox'):
                    bbox = block.bbox
                    x, y = bbox[0], bbox[1]
                    width = bbox[2] if len(bbox) > 2 else 100
                    height = bbox[3] if len(bbox) > 3 else 30
                else:
                    x, y, width, height = 0, 0, 100, 30
                
                # Extract confidence
                confidence = block.confidence if hasattr(block, 'confidence') else 1.0
                
                blocks.append(TextBlock(
                    text=text,
                    x=int(x),
                    y=int(y),
                    width=int(width),
                    height=int(height),
                    confidence=float(confidence)
                ))
            except Exception as e:
                self.logger.debug(f"Failed to convert block: {e}")
                continue
        
        return blocks
    
    def _spatial_merge(self, blocks: List[TextBlock]) -> List[TextBlock]:
        """
        Merge spatially close text blocks.
        
        This fixes fragmented OCR like:
        "DENTIFICATION" + "Skill" → "IDENTIFICATION Skill"
        "VUL-" + "GAR HUMAN" → "VULGAR HUMAN" (removes line-break hyphen)
        """
        if len(blocks) <= 1:
            return blocks
        
        # Sort blocks by position (top to bottom, left to right)
        sorted_blocks = sorted(blocks, key=lambda b: (b.y, b.x))
        
        # First pass: Merge horizontally on same lines
        merged_lines = []
        current_line = [sorted_blocks[0]]
        
        for block in sorted_blocks[1:]:
            # Check if block is on the same line as current_line
            if self._is_same_line(current_line[-1], block):
                # Check if block is close enough to merge
                if self._is_horizontally_close(current_line[-1], block):
                    current_line.append(block)
                else:
                    # Too far horizontally, finish current line
                    merged_lines.append(self._merge_line(current_line))
                    current_line = [block]
            else:
                # Different line, finish current line
                merged_lines.append(self._merge_line(current_line))
                current_line = [block]
        
        # Don't forget the last line
        if current_line:
            merged_lines.append(self._merge_line(current_line))
        
        # Second pass: Merge vertically close lines (for multi-line text blocks like speech bubbles)
        final_merged = self._merge_vertical_lines(merged_lines)
        
        return final_merged
    
    def _merge_vertical_lines(self, lines: List[TextBlock]) -> List[TextBlock]:
        """
        Merge vertically close lines that belong to the same text block.
        
        This handles multi-line text in speech bubbles:
        "...CALLING"
        "THEM "VUL-"
        "GAR HUMAN"
        "INFERIORS,""
        """
        if len(lines) <= 1:
            return lines
        
        merged = []
        current_group = [lines[0]]
        
        for line in lines[1:]:
            prev_line = current_group[-1]
            
            # Check if lines are vertically close (within 2x line height)
            vertical_gap = line.y - (prev_line.y + prev_line.height)
            max_gap = prev_line.height * 2.0
            
            # Check if lines are horizontally aligned (similar x position or overlapping)
            horizontal_overlap = not (line.x > prev_line.x + prev_line.width or 
                                     prev_line.x > line.x + line.width)
            horizontal_close = abs(line.x - prev_line.x) < prev_line.width * 0.5
            
            if vertical_gap < max_gap and (horizontal_overlap or horizontal_close):
                # Lines are close vertically and aligned horizontally - merge them
                current_group.append(line)
            else:
                # Lines are too far apart - finish current group
                merged.append(self._merge_vertical_group(current_group))
                current_group = [line]
        
        # Don't forget the last group
        if current_group:
            merged.append(self._merge_vertical_group(current_group))
        
        return merged
    
    def _merge_vertical_group(self, lines: List[TextBlock]) -> TextBlock:
        """Merge multiple lines vertically into one text block."""
        if len(lines) == 1:
            return lines[0]
        
        # Combine text from multiple lines with intelligent hyphen handling
        merged_parts = []
        for line in lines:
            text = line.text.strip()
            
            # Check if previous line ended with hyphen (line-break)
            if merged_parts and merged_parts[-1].endswith('-'):
                # Remove hyphen and join without space
                merged_parts[-1] = merged_parts[-1][:-1] + text
            else:
                # Normal line break - add space
                merged_parts.append(text)
        
        merged_text = ' '.join(merged_parts)
        
        # Calculate bounding box
        min_x = min(l.x for l in lines)
        min_y = min(l.y for l in lines)
        max_x = max(l.x + l.width for l in lines)
        max_y = max(l.y + l.height for l in lines)
        
        # Average confidence
        avg_confidence = sum(l.confidence for l in lines) / len(lines)
        
        return TextBlock(
            text=merged_text,
            x=min_x,
            y=min_y,
            width=max_x - min_x,
            height=max_y - min_y,
            confidence=avg_confidence
        )
    
    def _is_same_line(self, block1: TextBlock, block2: TextBlock) -> bool:
        """Check if two blocks are on the same line."""
        vertical_distance = abs(block1.center_y - block2.center_y)
        return vertical_distance < self.vertical_threshold
    
    def _is_horizontally_close(self, block1: TextBlock, block2: TextBlock) -> bool:
        """Check if two blocks are horizontally close enough to merge."""
        # Distance between right edge of block1 and left edge of block2
        gap = block2.x - (block1.x + block1.width)
        return gap < self.horizontal_threshold
    
    def _merge_line(self, blocks: List[TextBlock]) -> TextBlock:
        """Merge multiple blocks on the same line into one."""
        if len(blocks) == 1:
            return blocks[0]
        
        # Combine text with intelligent hyphen handling
        merged_parts = []
        for i, block in enumerate(blocks):
            text = block.text.strip()
            
            # Check if previous block ended with hyphen
            if merged_parts and merged_parts[-1].endswith('-'):
                # Remove hyphen from previous part and join without space
                merged_parts[-1] = merged_parts[-1][:-1]
                merged_parts.append(text)
            else:
                merged_parts.append(text)
        
        # Join with spaces (hyphens already handled above)
        merged_text = ' '.join(merged_parts)
        
        # Calculate bounding box
        min_x = min(b.x for b in blocks)
        min_y = min(b.y for b in blocks)
        max_x = max(b.x + b.width for b in blocks)
        max_y = max(b.y + b.height for b in blocks)
        
        # Average confidence
        avg_confidence = sum(b.confidence for b in blocks) / len(blocks)
        
        return TextBlock(
            text=merged_text,
            x=min_x,
            y=min_y,
            width=max_x - min_x,
            height=max_y - min_y,
            confidence=avg_confidence
        )
    
    def _spell_check_blocks(self, blocks: List[TextBlock]) -> List[TextBlock]:
        """Apply spell checking and correction to text blocks."""
        corrected = []
        
        for block in blocks:
            corrected_text = self._spell_check_text(block.text)
            
            if corrected_text != block.text:
                self.stats['spell_corrections'] += 1
                self.logger.debug(f"Spell corrected: '{block.text}' → '{corrected_text}'")
            
            corrected.append(TextBlock(
                text=corrected_text,
                x=block.x,
                y=block.y,
                width=block.width,
                height=block.height,
                confidence=block.confidence
            ))
        
        return corrected
    
    def _spell_check_text(self, text: str) -> str:
        """Apply spell checking to text."""
        # Check for exact matches in common OCR errors
        for error, correction in self.common_ocr_errors.items():
            if error in text:
                text = text.replace(error, correction)
        
        # Fix common patterns
        # Missing apostrophes in contractions
        text = re.sub(r'\b(won|can|don|doesn|didn|wouldn|couldn|shouldn|isn|aren|wasn|weren|hasn|haven|hadn)t\b', 
                     lambda m: m.group(1) + "'t", text, flags=re.IGNORECASE)
        
        # Fix spacing issues
        text = re.sub(r'\s+', ' ', text)  # Multiple spaces → single space
        text = text.strip()
        
        return text
    
    def _context_aware_validation(self, blocks: List[TextBlock]) -> List[TextBlock]:
        """
        Validate text blocks with context awareness.
        
        Instead of filtering individual fragments, consider the merged context.
        """
        validated = []
        
        for block in blocks:
            # Skip empty blocks
            if not block.text or not block.text.strip():
                continue
            
            # Check minimum confidence
            if block.confidence < self.min_confidence:
                self.logger.debug(f"Filtered low confidence: '{block.text[:30]}' (conf={block.confidence:.2f})")
                continue
            
            # Context-aware checks
            if self._is_valid_in_context(block):
                validated.append(block)
            else:
                self.logger.debug(f"Filtered invalid context: '{block.text[:30]}'")
        
        return validated
    
    def _is_valid_in_context(self, block: TextBlock) -> bool:
        """Check if text block is valid considering context."""
        text = block.text.strip()
        
        # Always accept if confidence is high
        if block.confidence > 0.7:
            return True
        
        # Check text length
        if len(text) < 2:
            return False
        
        # Check if text has at least some alphanumeric characters
        if not re.search(r'[a-zA-Z0-9]', text):
            return False
        
        # Check if text is mostly punctuation
        alnum_count = sum(1 for c in text if c.isalnum())
        if alnum_count / len(text) < 0.3:
            return False
        
        # Accept if text looks like a word or sentence
        word_count = len(text.split())
        if word_count >= 2:  # Multi-word text is usually valid
            return True
        
        # Single word - check if it looks reasonable
        if len(text) >= 3 and alnum_count >= 2:
            return True
        
        return False
    
    def _convert_from_internal_format(self, blocks: List[TextBlock], 
                                     original_blocks: List[Any]) -> List[Any]:
        """Convert internal format back to original OCR format."""
        if not blocks:
            return []
        
        # Import the proper TextBlock type
        try:
            from app.models import TextBlock as OCRTextBlock, Rectangle
        except ImportError:
            from models import TextBlock as OCRTextBlock, Rectangle
        
        result = []
        
        for block in blocks:
            try:
                # Estimate font size from bounding box height
                # Typical font size is roughly 70-80% of the bounding box height
                estimated_font_size = int(block.height * 0.75)
                
                # Create proper OCR TextBlock object
                ocr_block = OCRTextBlock(
                    text=block.text,
                    position=Rectangle(
                        x=block.x,
                        y=block.y,
                        width=block.width,
                        height=block.height
                    ),
                    confidence=block.confidence,
                    estimated_font_size=estimated_font_size
                )
                result.append(ocr_block)
            except Exception as e:
                self.logger.error(f"Failed to convert block: {e}")
                # Try to preserve original if possible
                for orig in original_blocks:
                    if hasattr(orig, 'text') and orig.text == block.text:
                        result.append(orig)
                        break
        
        return result
    
    def get_stats(self) -> Dict[str, Any]:
        """Get processing statistics."""
        return self.stats.copy()
    
    def reset_stats(self):
        """Reset statistics."""
        self.stats = {
            'blocks_processed': 0,
            'blocks_merged': 0,
            'spell_corrections': 0,
            'validation_filtered': 0
        }


# Export
__all__ = ['IntelligentOCRProcessor', 'TextBlock']
