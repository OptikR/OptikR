"""
Text Block Merger Optimizer Plugin
Intelligently merges nearby text blocks into complete sentences.
"""

from typing import Dict, Any, List, Tuple
import sys
from pathlib import Path


class TextBlockMerger:
    """Merges nearby text blocks based on proximity and layout."""
    
    def __init__(self, config: Dict[str, Any]):
        self.config = config
        self.horizontal_threshold = config.get('horizontal_threshold', 50)
        self.vertical_threshold = config.get('vertical_threshold', 30)
        self.line_height_tolerance = config.get('line_height_tolerance', 1.5)
        self.merge_strategy = config.get('merge_strategy', 'smart')
        self.respect_punctuation = config.get('respect_punctuation', True)
        self.min_confidence = config.get('min_confidence', 0.3)
        
        # Statistics
        self.total_blocks_in = 0
        self.total_blocks_out = 0
        self.total_merges = 0
        
        print(f"[TEXT_BLOCK_MERGER] Initialized")
        print(f"  Horizontal threshold: {self.horizontal_threshold}px")
        print(f"  Vertical threshold: {self.vertical_threshold}px")
        print(f"  Strategy: {self.merge_strategy}")
    
    def configure(self, config: Dict[str, Any]):
        """Update configuration dynamically."""
        if 'horizontal_threshold' in config:
            self.horizontal_threshold = config['horizontal_threshold']
        if 'vertical_threshold' in config:
            self.vertical_threshold = config['vertical_threshold']
        if 'merge_strategy' in config:
            self.merge_strategy = config['merge_strategy']
        if 'line_height_tolerance' in config:
            self.line_height_tolerance = config['line_height_tolerance']
        if 'respect_punctuation' in config:
            self.respect_punctuation = config['respect_punctuation']
        if 'min_confidence' in config:
            self.min_confidence = config['min_confidence']
        
        print(f"[TEXT_BLOCK_MERGER] Configuration updated: h={self.horizontal_threshold}px, v={self.vertical_threshold}px, strategy={self.merge_strategy}")
    
    def process(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """Post-process: Merge nearby text blocks"""
        texts = data.get('texts', [])
        
        if not texts or len(texts) <= 1:
            return data
        
        self.total_blocks_in += len(texts)
        
        # Merge text blocks
        merged_texts = self._merge_text_blocks(texts)
        
        self.total_blocks_out += len(merged_texts)
        self.total_merges += (len(texts) - len(merged_texts))
        
        # Update data
        data['texts'] = merged_texts
        data['merge_count'] = len(texts) - len(merged_texts)
        
        print(f"[TEXT_BLOCK_MERGER] Merged {len(texts)} blocks -> {len(merged_texts)} blocks")
        
        return data
    
    def _merge_text_blocks(self, texts: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """
        Merge nearby text blocks intelligently.
        
        Args:
            texts: List of text blocks with 'text', 'bbox', 'confidence'
            
        Returns:
            List of merged text blocks
        """
        if not texts:
            return texts
        
        # Filter by confidence
        valid_texts = [t for t in texts if t.get('confidence', 1.0) >= self.min_confidence]
        
        if not valid_texts:
            return texts
        
        # DO NOT SORT - Keep original OCR order (Tesseract already provides correct reading order)
        # Sorting by bbox position breaks the order for curved/manga text
        sorted_texts = valid_texts
        
        # SIMPLIFIED: Just merge sequentially without grouping into lines
        # Tesseract already provides correct reading order, don't re-sort
        # Just merge adjacent blocks that are close together
        
        if not sorted_texts:
            return []
        
        merged = []
        current_group = [sorted_texts[0]]
        
        for i in range(1, len(sorted_texts)):
            prev = current_group[-1]
            curr = sorted_texts[i]
            
            # Check if blocks are close enough to merge
            prev_bbox = prev['bbox']
            curr_bbox = curr['bbox']
            
            # Calculate distance
            prev_bottom = prev_bbox[1] + prev_bbox[3]
            curr_top = curr_bbox[1]
            vertical_gap = abs(curr_top - prev_bottom)
            
            prev_right = prev_bbox[0] + prev_bbox[2]
            curr_left = curr_bbox[0]
            horizontal_gap = abs(curr_left - prev_right)
            
            # Merge if close enough (either horizontally or vertically)
            should_merge = (horizontal_gap <= self.horizontal_threshold or 
                          vertical_gap <= self.vertical_threshold)
            
            if should_merge and not self.respect_punctuation:
                current_group.append(curr)
            elif should_merge and self.respect_punctuation:
                # Check punctuation
                prev_text = current_group[-1]['text'].strip()
                if prev_text and prev_text[-1] not in '.!?。！？':
                    current_group.append(curr)
                else:
                    # Start new group
                    merged.append(self._combine_group(current_group))
                    current_group = [curr]
            else:
                # Too far apart, start new group
                merged.append(self._combine_group(current_group))
                current_group = [curr]
        
        # Add last group
        if current_group:
            merged.append(self._combine_group(current_group))
        
        return merged
    
    def _group_into_lines(self, texts: List[Dict[str, Any]]) -> List[List[Dict[str, Any]]]:
        """Group text blocks into horizontal lines."""
        if not texts:
            return []
        
        lines = []
        current_line = [texts[0]]
        
        for text in texts[1:]:
            # Check if on same line (similar y-coordinate)
            prev_bbox = current_line[-1]['bbox']
            curr_bbox = text['bbox']
            
            prev_y_center = prev_bbox[1] + prev_bbox[3] / 2
            curr_y_center = curr_bbox[1] + curr_bbox[3] / 2
            
            # Calculate line height tolerance
            avg_height = (prev_bbox[3] + curr_bbox[3]) / 2
            max_y_diff = avg_height * self.line_height_tolerance
            
            if abs(curr_y_center - prev_y_center) <= max_y_diff:
                # Same line
                current_line.append(text)
            else:
                # New line
                lines.append(current_line)
                current_line = [text]
        
        # Add last line
        if current_line:
            lines.append(current_line)
        
        return lines
    
    def _merge_line(self, line: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Merge text blocks within a single line."""
        if len(line) <= 1:
            return line
        
        # DO NOT SORT - Keep original OCR order
        sorted_line = line
        
        merged = []
        current_group = [sorted_line[0]]
        
        for text in sorted_line[1:]:
            prev_bbox = current_group[-1]['bbox']
            curr_bbox = text['bbox']
            
            # Calculate horizontal distance
            prev_right = prev_bbox[0] + prev_bbox[2]
            curr_left = curr_bbox[0]
            horizontal_gap = curr_left - prev_right
            
            # Check if should merge
            should_merge = False
            
            if horizontal_gap <= self.horizontal_threshold:
                # Close enough to merge
                if self.respect_punctuation:
                    # Check if previous text ends with sentence-ending punctuation
                    prev_text = current_group[-1]['text'].strip()
                    if prev_text and prev_text[-1] in '.!?。！？':
                        # Don't merge across sentence boundaries
                        should_merge = False
                    else:
                        should_merge = True
                else:
                    should_merge = True
            
            if should_merge:
                # Add to current group
                current_group.append(text)
            else:
                # Finalize current group and start new one
                merged.append(self._combine_group(current_group))
                current_group = [text]
        
        # Add last group
        if current_group:
            merged.append(self._combine_group(current_group))
        
        return merged
    
    def _merge_across_lines(self, lines: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Merge text blocks across lines (for multi-line sentences)."""
        if len(lines) <= 1:
            return lines
        
        merged = []
        current_group = [lines[0]]
        
        for text in lines[1:]:
            prev_bbox = current_group[-1]['bbox']
            curr_bbox = text['bbox']
            
            # Calculate vertical distance
            prev_bottom = prev_bbox[1] + prev_bbox[3]
            curr_top = curr_bbox[1]
            vertical_gap = curr_top - prev_bottom
            
            # Check if should merge vertically
            should_merge = False
            
            if vertical_gap <= self.vertical_threshold:
                # Close enough vertically
                if self.respect_punctuation:
                    # Check if previous text ends with sentence-ending punctuation
                    prev_text = current_group[-1]['text'].strip()
                    if prev_text and prev_text[-1] in '.!?。！？':
                        # Don't merge across sentence boundaries
                        should_merge = False
                    else:
                        should_merge = True
                else:
                    should_merge = True
            
            if should_merge:
                # Add to current group
                current_group.append(text)
            else:
                # Finalize current group and start new one
                merged.append(self._combine_group(current_group))
                current_group = [text]
        
        # Add last group
        if current_group:
            merged.append(self._combine_group(current_group))
        
        return merged
    
    def _combine_group(self, group: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Combine multiple text blocks into one."""
        if len(group) == 1:
            return group[0]
        
        # Combine text with spaces
        combined_text = ' '.join(t['text'] for t in group)
        
        # Calculate combined bounding box (top-left corner + width/height)
        min_x = min(t['bbox'][0] for t in group)
        min_y = min(t['bbox'][1] for t in group)
        max_x = max(t['bbox'][0] + t['bbox'][2] for t in group)
        max_y = max(t['bbox'][1] + t['bbox'][3] for t in group)
        
        width = max_x - min_x
        height = max_y - min_y
        
        # Use top-left as position (standard bbox format)
        combined_bbox = [min_x, min_y, width, height]
        
        # Average confidence
        avg_confidence = sum(t.get('confidence', 1.0) for t in group) / len(group)
        
        return {
            'text': combined_text,
            'bbox': combined_bbox,
            'confidence': avg_confidence,
            'merged_from': len(group)
        }
    
    def get_stats(self) -> Dict[str, Any]:
        """Get optimizer statistics"""
        reduction_rate = (self.total_merges / self.total_blocks_in * 100) if self.total_blocks_in > 0 else 0
        
        return {
            'total_blocks_in': self.total_blocks_in,
            'total_blocks_out': self.total_blocks_out,
            'total_merges': self.total_merges,
            'reduction_rate': f"{reduction_rate:.1f}%",
            'horizontal_threshold': self.horizontal_threshold,
            'vertical_threshold': self.vertical_threshold,
            'strategy': self.merge_strategy
        }
    
    def reset(self):
        """Reset optimizer state"""
        self.total_blocks_in = 0
        self.total_blocks_out = 0
        self.total_merges = 0


# Plugin interface
def initialize(config: Dict[str, Any]) -> TextBlockMerger:
    """Initialize the optimizer plugin"""
    return TextBlockMerger(config)
