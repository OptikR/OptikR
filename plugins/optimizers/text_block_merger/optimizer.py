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
        self.horizontal_threshold = config.get('horizontal_threshold', 15)  # Strict default for manga
        self.vertical_threshold = config.get('vertical_threshold', 20)      # Strict default for manga
        self.line_height_tolerance = config.get('line_height_tolerance', 1.5)
        self.merge_strategy = config.get('merge_strategy', 'smart')
        self.respect_punctuation = config.get('respect_punctuation', False)  # Don't split on punctuation for manga
        self.min_confidence = config.get('min_confidence', 0.3)
        
        # Statistics
        self.total_blocks_in = 0
        self.total_blocks_out = 0
        self.total_merges = 0
        self.frame_count = 0  # Track which frame we're on for debugging
        
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
        
        self.frame_count += 1
        self.total_blocks_in += len(texts)
        
        # DEBUG: Show what we're receiving (detailed for first 3 frames)
        if self.frame_count <= 3:
            print(f"\n{'='*80}")
            print(f"[MERGER FRAME {self.frame_count}] Received {len(texts)} blocks:")
            for i, text in enumerate(texts):
                if hasattr(text, 'position'):
                    pos = text.position
                    print(f"  Block {i}: '{text.text[:30]}' @ ({pos.x},{pos.y}) size={pos.width}x{pos.height}")
                elif isinstance(text, dict) and 'bbox' in text:
                    bbox = text['bbox']
                    print(f"  Block {i}: '{text['text'][:30]}' @ ({bbox[0]},{bbox[1]}) size={bbox[2]}x{bbox[3]}")
                else:
                    print(f"  Block {i}: {type(text)} - {text}")
            print(f"{'='*80}\n")
        else:
            # Brief logging for later frames
            print(f"[MERGER INPUT] Received {len(texts)} blocks:")
            for i, text in enumerate(texts[:5]):  # Show first 5
                if hasattr(text, 'position'):
                    pos = text.position
                    print(f"  Block {i}: '{text.text[:20]}' @ ({pos.x},{pos.y}) size={pos.width}x{pos.height}")
                elif isinstance(text, dict) and 'bbox' in text:
                    bbox = text['bbox']
                    print(f"  Block {i}: '{text['text'][:20]}' @ ({bbox[0]},{bbox[1]}) size={bbox[2]}x{bbox[3]}")
        
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
        Merge nearby text blocks intelligently using spatial clustering.
        
        For manga: Groups text blocks by proximity (same speech bubble)
        instead of sequential merging.
        
        Args:
            texts: List of text blocks with 'text', 'bbox', 'confidence'
            
        Returns:
            List of merged text blocks (one per speech bubble)
        """
        if not texts:
            return texts
        
        # Convert TextBlock objects to dict format if needed
        dict_texts = []
        for t in texts:
            if hasattr(t, 'text'):  # TextBlock object
                dict_texts.append({
                    'text': t.text,
                    'bbox': [t.position.x, t.position.y, t.position.width, t.position.height],
                    'confidence': t.confidence
                })
            else:  # Already dict
                dict_texts.append(t)
        
        # Filter by confidence
        valid_texts = [t for t in dict_texts if t.get('confidence', 1.0) >= self.min_confidence]
        
        if not valid_texts:
            return dict_texts
        
        if len(valid_texts) == 1:
            return valid_texts
        
        # SPATIAL CLUSTERING: Group blocks by proximity (for manga speech bubbles)
        clusters = []
        used = set()
        
        # Extra verbose logging for first 3 frames
        verbose = self.frame_count <= 3
        
        if verbose:
            print(f"\n[MERGER FRAME {self.frame_count}] Starting clustering with {len(valid_texts)} blocks")
            print(f"[MERGER FRAME {self.frame_count}] Thresholds: h={self.horizontal_threshold}px, v={self.vertical_threshold}px")
            print(f"[MERGER FRAME {self.frame_count}] All blocks before clustering:")
            for i, text in enumerate(valid_texts):
                bbox = text['bbox']
                print(f"  Block {i}: '{text['text'][:30]}' @ pos=({bbox[0]},{bbox[1]}) size={bbox[2]}x{bbox[3]}")
        else:
            print(f"[MERGER DEBUG] Starting clustering with {len(valid_texts)} blocks")
            print(f"[MERGER DEBUG] Thresholds: h={self.horizontal_threshold}px, v={self.vertical_threshold}px")
            
            # Show all blocks before clustering
            for i, text in enumerate(valid_texts):
                bbox = text['bbox']
                print(f"[MERGER DEBUG] Block {i}: '{text['text'][:30]}' @ pos=({bbox[0]},{bbox[1]}) size={bbox[2]}x{bbox[3]}")
        
        for i, text in enumerate(valid_texts):
            if i in used:
                continue
            
            # Start new cluster
            cluster = [text]
            used.add(i)
            initial_size = len(cluster)
            
            # Find all nearby blocks that belong to same bubble
            changed = True
            iterations = 0
            while changed:
                changed = False
                iterations += 1
                for j, other in enumerate(valid_texts):
                    if j in used:
                        continue
                    
                    # Check if this block is close to ANY block in current cluster
                    for cluster_block in cluster:
                        if self._blocks_are_close(cluster_block, other):
                            cluster.append(other)
                            used.add(j)
                            changed = True
                            
                            # Debug: Show what got merged
                            bbox_other = other['bbox']
                            bbox_cluster = cluster_block['bbox']
                            print(f"[MERGER DEBUG] Merged block {j} into cluster {len(clusters)} "
                                  f"(pos1={bbox_cluster[0]},{bbox_cluster[1]} pos2={bbox_other[0]},{bbox_other[1]})")
                            break
            
            print(f"[MERGER DEBUG] Cluster {len(clusters)}: {initial_size} → {len(cluster)} blocks after {iterations} iterations")
            clusters.append(cluster)
        
        if self.frame_count <= 3:
            print(f"\n[FRAME {self.frame_count} RESULT] Created {len(clusters)} clusters from {len(valid_texts)} blocks")
            for i, cluster in enumerate(clusters):
                print(f"  Cluster {i}: {len(cluster)} blocks")
                for block in cluster:
                    bbox = block['bbox']
                    print(f"    - '{block['text'][:30]}' @ ({bbox[0]},{bbox[1]})")
            print()
        else:
            print(f"[MERGER DEBUG] Created {len(clusters)} clusters from {len(valid_texts)} blocks")
        
        # Merge each cluster into one text block
        merged = []
        for cluster in clusters:
            if len(cluster) == 1:
                merged.append(cluster[0])
            else:
                # Sort cluster blocks by reading order (top-to-bottom, right-to-left for manga)
                cluster.sort(key=lambda t: (t['bbox'][1], -t['bbox'][0]))
                merged.append(self._combine_group(cluster))
        
        return merged
    
    def _blocks_are_close(self, block1: Dict[str, Any], block2: Dict[str, Any]) -> bool:
        """
        Check if two blocks are close enough to be in the same speech bubble.
        
        Uses edge-to-edge distance, not center-to-center.
        """
        bbox1 = block1['bbox']  # [x, y, width, height]
        bbox2 = block2['bbox']
        
        # Calculate edges
        left1, top1, width1, height1 = bbox1[0], bbox1[1], bbox1[2], bbox1[3]
        right1, bottom1 = left1 + width1, top1 + height1
        
        left2, top2, width2, height2 = bbox2[0], bbox2[1], bbox2[2], bbox2[3]
        right2, bottom2 = left2 + width2, top2 + height2
        
        # Calculate edge-to-edge distances
        # Horizontal: distance between closest edges
        if right1 < left2:
            horizontal_dist = left2 - right1  # Block 2 is to the right
        elif right2 < left1:
            horizontal_dist = left1 - right2  # Block 1 is to the right
        else:
            horizontal_dist = 0  # Overlapping horizontally
        
        # Vertical: distance between closest edges
        if bottom1 < top2:
            vertical_dist = top2 - bottom1  # Block 2 is below
        elif bottom2 < top1:
            vertical_dist = top1 - bottom2  # Block 1 is below
        else:
            vertical_dist = 0  # Overlapping vertically
        
        # Debug logging
        text1 = block1.get('text', '')[:20]
        text2 = block2.get('text', '')[:20]
        is_close = (horizontal_dist <= self.horizontal_threshold and 
                    vertical_dist <= self.vertical_threshold)
        
        # Extra verbose logging for first 3 frames
        if self.frame_count <= 3:
            print(f"[FRAME {self.frame_count} DISTANCE] '{text1}' @ ({left1},{top1}) size=({width1}x{height1})")
            print(f"                      vs '{text2}' @ ({left2},{top2}) size=({width2}x{height2})")
            print(f"  Edges: Block1=[{left1},{top1}]-[{right1},{bottom1}]  Block2=[{left2},{top2}]-[{right2},{bottom2}]")
            print(f"  → H_dist={horizontal_dist}px (thresh={self.horizontal_threshold}), "
                  f"V_dist={vertical_dist}px (thresh={self.vertical_threshold})")
            print(f"  → Decision: {'✓ MERGE' if is_close else '✗ SEPARATE'}\n")
        else:
            print(f"[MERGER DISTANCE] '{text1}' @ ({left1},{top1}) vs '{text2}' @ ({left2},{top2})")
            print(f"  → H_dist={horizontal_dist}px (thresh={self.horizontal_threshold}), "
                  f"V_dist={vertical_dist}px (thresh={self.vertical_threshold}) → {'MERGE' if is_close else 'SEPARATE'}")
        
        # Blocks are close if BOTH distances are within thresholds
        # This prevents merging across different bubbles
        return is_close
    
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
