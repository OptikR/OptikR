"""
Speech Bubble Detector for Manga OCR

Detects speech bubbles and text regions in manga panels to improve
overlay positioning accuracy.

Author: Kiro AI Assistant
Date: 2025-11-25
"""

import cv2
import numpy as np
from typing import List, Tuple, Optional
from dataclasses import dataclass


@dataclass
class BubbleRegion:
    """Represents a detected speech bubble or text region"""
    x: int
    y: int
    width: int
    height: int
    contour: np.ndarray
    area: int
    confidence: float = 1.0
    
    @property
    def center_x(self) -> int:
        return self.x + self.width // 2
    
    @property
    def center_y(self) -> int:
        return self.y + self.height // 2
    
    def contains_point(self, x: int, y: int) -> bool:
        """Check if point is inside this bubble region"""
        return (self.x <= x <= self.x + self.width and 
                self.y <= y <= self.y + self.height)
    
    def overlaps_with(self, other: 'BubbleRegion', threshold: float = 0.3) -> bool:
        """Check if this bubble overlaps with another"""
        # Calculate intersection
        x_overlap = max(0, min(self.x + self.width, other.x + other.width) - max(self.x, other.x))
        y_overlap = max(0, min(self.y + self.height, other.y + other.height) - max(self.y, other.y))
        intersection = x_overlap * y_overlap
        
        # Calculate union
        union = self.area + other.area - intersection
        
        # IoU (Intersection over Union)
        iou = intersection / union if union > 0 else 0
        return iou > threshold


class BubbleDetector:
    """
    Detects speech bubbles and text regions in manga images.
    
    Uses computer vision techniques to find white/light regions that
    typically contain text in manga panels.
    """
    
    def __init__(self, config: Optional[dict] = None):
        """
        Initialize bubble detector.
        
        Args:
            config: Configuration dictionary
        """
        self.config = config or {}
        
        # Detection parameters
        self.min_bubble_area = self.config.get('min_bubble_area', 500)
        self.max_bubble_area = self.config.get('max_bubble_area', 50000)
        self.brightness_threshold = self.config.get('brightness_threshold', 200)
        self.merge_nearby_bubbles = self.config.get('merge_nearby_bubbles', True)
        self.merge_distance = self.config.get('merge_distance', 20)
        
    def detect_bubbles(self, frame: np.ndarray) -> List[BubbleRegion]:
        """
        Detect speech bubbles in the frame.
        
        Args:
            frame: Input image (BGR or grayscale)
            
        Returns:
            List of detected bubble regions
        """
        # Convert to grayscale if needed
        if len(frame.shape) == 3:
            gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
        else:
            gray = frame.copy()
        
        # Find bright regions (speech bubbles are typically white/light)
        _, binary = cv2.threshold(gray, self.brightness_threshold, 255, cv2.THRESH_BINARY)
        
        # Morphological operations to clean up and connect nearby regions
        kernel = cv2.getStructuringElement(cv2.MORPH_RECT, (5, 5))
        binary = cv2.morphologyEx(binary, cv2.MORPH_CLOSE, kernel)
        binary = cv2.morphologyEx(binary, cv2.MORPH_OPEN, kernel)
        
        # Find contours
        contours, _ = cv2.findContours(binary, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
        
        # Filter and convert contours to bubble regions
        bubbles = []
        for contour in contours:
            area = cv2.contourArea(contour)
            
            # Filter by area
            if area < self.min_bubble_area or area > self.max_bubble_area:
                continue
            
            # Get bounding rectangle
            x, y, w, h = cv2.boundingRect(contour)
            
            # Filter by aspect ratio (avoid very thin regions)
            aspect_ratio = w / h if h > 0 else 0
            if aspect_ratio < 0.1 or aspect_ratio > 10:
                continue
            
            bubble = BubbleRegion(
                x=x, y=y, width=w, height=h,
                contour=contour, area=area
            )
            bubbles.append(bubble)
        
        # Merge nearby bubbles if enabled
        if self.merge_nearby_bubbles:
            bubbles = self._merge_nearby_bubbles(bubbles)
        
        return bubbles
    
    def _merge_nearby_bubbles(self, bubbles: List[BubbleRegion]) -> List[BubbleRegion]:
        """Merge bubbles that are close to each other"""
        if len(bubbles) <= 1:
            return bubbles
        
        merged = []
        used = set()
        
        for i, bubble1 in enumerate(bubbles):
            if i in used:
                continue
            
            # Find all bubbles to merge with this one
            to_merge = [bubble1]
            used.add(i)
            
            for j, bubble2 in enumerate(bubbles):
                if j in used or j <= i:
                    continue
                
                # Check if bubbles are close enough to merge
                if self._are_bubbles_close(bubble1, bubble2):
                    to_merge.append(bubble2)
                    used.add(j)
            
            # Merge all collected bubbles
            if len(to_merge) == 1:
                merged.append(bubble1)
            else:
                merged_bubble = self._merge_bubble_group(to_merge)
                merged.append(merged_bubble)
        
        return merged
    
    def _are_bubbles_close(self, b1: BubbleRegion, b2: BubbleRegion) -> bool:
        """Check if two bubbles are close enough to merge"""
        # Calculate distance between bubble centers
        dx = b1.center_x - b2.center_x
        dy = b1.center_y - b2.center_y
        distance = np.sqrt(dx*dx + dy*dy)
        
        # Also check if they overlap
        if b1.overlaps_with(b2, threshold=0.1):
            return True
        
        # Check if distance is less than merge threshold
        return distance < self.merge_distance
    
    def _merge_bubble_group(self, bubbles: List[BubbleRegion]) -> BubbleRegion:
        """Merge multiple bubbles into one"""
        # Calculate bounding box of all bubbles
        min_x = min(b.x for b in bubbles)
        min_y = min(b.y for b in bubbles)
        max_x = max(b.x + b.width for b in bubbles)
        max_y = max(b.y + b.height for b in bubbles)
        
        width = max_x - min_x
        height = max_y - min_y
        area = sum(b.area for b in bubbles)
        
        # Create merged contour (simplified bounding box)
        merged_contour = np.array([
            [[min_x, min_y]],
            [[max_x, min_y]],
            [[max_x, max_y]],
            [[min_x, max_y]]
        ], dtype=np.int32)
        
        return BubbleRegion(
            x=min_x, y=min_y, width=width, height=height,
            contour=merged_contour, area=area
        )
    
    def find_bubble_for_text(self, text_x: int, text_y: int, 
                            bubbles: List[BubbleRegion]) -> Optional[BubbleRegion]:
        """
        Find which bubble contains the given text position.
        
        Args:
            text_x: X coordinate of text
            text_y: Y coordinate of text
            bubbles: List of detected bubbles
            
        Returns:
            Bubble region containing the text, or None
        """
        for bubble in bubbles:
            if bubble.contains_point(text_x, text_y):
                return bubble
        
        # If no exact match, find closest bubble
        if bubbles:
            closest = min(bubbles, key=lambda b: 
                         np.sqrt((b.center_x - text_x)**2 + (b.center_y - text_y)**2))
            return closest
        
        return None


# Export
__all__ = ['BubbleDetector', 'BubbleRegion']
