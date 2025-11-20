"""
Region of Interest (ROI) Detection Module

Detects text regions in images to optimize OCR processing.
Instead of processing the entire frame, only process regions likely to contain text.
"""

import cv2
import numpy as np
from typing import List, Tuple, Optional
from dataclasses import dataclass
import logging

try:
    from models import Rectangle, Frame
except ImportError:
    from app.models import Rectangle, Frame


@dataclass
class ROIConfig:
    """Configuration for ROI detection."""
    # Minimum region size (width, height)
    min_region_width: int = 50
    min_region_height: int = 20
    
    # Maximum region size (to avoid processing huge areas)
    max_region_width: int = 2000
    max_region_height: int = 1000
    
    # Padding around detected regions (pixels)
    padding: int = 10
    
    # Merge nearby regions (distance threshold)
    merge_distance: int = 20
    
    # Confidence threshold for text detection
    confidence_threshold: float = 0.3
    
    # Enable adaptive thresholding
    adaptive_threshold: bool = True
    
    # Enable morphological operations
    use_morphology: bool = True


class ROIDetector:
    """
    Detects regions of interest (text regions) in images.
    
    Uses computer vision techniques to identify areas likely to contain text,
    reducing OCR processing time and improving accuracy.
    """
    
    def __init__(self, config: Optional[ROIConfig] = None):
        """
        Initialize ROI detector.
        
        Args:
            config: ROI detection configuration
        """
        self.config = config or ROIConfig()
        self.logger = logging.getLogger(__name__)
    
    def detect_text_regions(self, frame: Frame) -> List[Rectangle]:
        """
        Detect text regions in frame.
        
        Args:
            frame: Input frame to analyze
            
        Returns:
            List of Rectangle objects representing detected text regions
        """
        try:
            image = frame.data
            
            # Convert to grayscale if needed
            if len(image.shape) == 3:
                gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
            else:
                gray = image.copy()
            
            # Detect regions using multiple methods
            regions = []
            
            # Method 1: Edge detection
            edge_regions = self._detect_by_edges(gray)
            regions.extend(edge_regions)
            
            # Method 2: Contour detection
            contour_regions = self._detect_by_contours(gray)
            regions.extend(contour_regions)
            
            # Method 3: Text-like patterns (horizontal lines)
            pattern_regions = self._detect_by_patterns(gray)
            regions.extend(pattern_regions)
            
            # Merge overlapping and nearby regions
            merged_regions = self._merge_regions(regions)
            
            # Filter by size constraints
            filtered_regions = self._filter_regions(merged_regions)
            
            # If no regions detected, return entire frame
            if not filtered_regions:
                self.logger.debug("No ROI detected, using entire frame")
                return [Rectangle(
                    x=0,
                    y=0,
                    width=image.shape[1],
                    height=image.shape[0]
                )]
            
            self.logger.debug(f"Detected {len(filtered_regions)} text regions")
            return filtered_regions
            
        except Exception as e:
            self.logger.error(f"ROI detection failed: {e}")
            # Fallback: return entire frame
            return [Rectangle(
                x=0,
                y=0,
                width=frame.data.shape[1],
                height=frame.data.shape[0]
            )]
    
    def _detect_by_edges(self, gray: np.ndarray) -> List[Rectangle]:
        """Detect regions using edge detection."""
        regions = []
        
        try:
            # Apply Canny edge detection
            edges = cv2.Canny(gray, 50, 150)
            
            # Dilate to connect nearby edges
            kernel = cv2.getStructuringElement(cv2.MORPH_RECT, (5, 5))
            dilated = cv2.dilate(edges, kernel, iterations=2)
            
            # Find contours
            contours, _ = cv2.findContours(dilated, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
            
            for contour in contours:
                x, y, w, h = cv2.boundingRect(contour)
                
                # Add padding
                x = max(0, x - self.config.padding)
                y = max(0, y - self.config.padding)
                w = w + 2 * self.config.padding
                h = h + 2 * self.config.padding
                
                regions.append(Rectangle(x=x, y=y, width=w, height=h))
        
        except Exception as e:
            self.logger.debug(f"Edge detection failed: {e}")
        
        return regions
    
    def _detect_by_contours(self, gray: np.ndarray) -> List[Rectangle]:
        """Detect regions using contour detection."""
        regions = []
        
        try:
            # Apply adaptive thresholding
            if self.config.adaptive_threshold:
                thresh = cv2.adaptiveThreshold(
                    gray, 255, cv2.ADAPTIVE_THRESH_GAUSSIAN_C,
                    cv2.THRESH_BINARY_INV, 11, 2
                )
            else:
                _, thresh = cv2.threshold(gray, 0, 255, cv2.THRESH_BINARY_INV + cv2.THRESH_OTSU)
            
            # Morphological operations to connect text
            if self.config.use_morphology:
                kernel = cv2.getStructuringElement(cv2.MORPH_RECT, (9, 3))
                morph = cv2.morphologyEx(thresh, cv2.MORPH_CLOSE, kernel)
            else:
                morph = thresh
            
            # Find contours
            contours, _ = cv2.findContours(morph, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
            
            for contour in contours:
                x, y, w, h = cv2.boundingRect(contour)
                
                # Add padding
                x = max(0, x - self.config.padding)
                y = max(0, y - self.config.padding)
                w = w + 2 * self.config.padding
                h = h + 2 * self.config.padding
                
                regions.append(Rectangle(x=x, y=y, width=w, height=h))
        
        except Exception as e:
            self.logger.debug(f"Contour detection failed: {e}")
        
        return regions
    
    def _detect_by_patterns(self, gray: np.ndarray) -> List[Rectangle]:
        """Detect regions using text-like patterns."""
        regions = []
        
        try:
            # Look for horizontal lines (common in text)
            horizontal_kernel = cv2.getStructuringElement(cv2.MORPH_RECT, (25, 1))
            detected_lines = cv2.morphologyEx(gray, cv2.MORPH_OPEN, horizontal_kernel, iterations=2)
            
            # Find contours of detected lines
            contours, _ = cv2.findContours(detected_lines, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
            
            for contour in contours:
                x, y, w, h = cv2.boundingRect(contour)
                
                # Expand vertically to capture full text height
                y = max(0, y - 20)
                h = h + 40
                
                # Add padding
                x = max(0, x - self.config.padding)
                w = w + 2 * self.config.padding
                
                regions.append(Rectangle(x=x, y=y, width=w, height=h))
        
        except Exception as e:
            self.logger.debug(f"Pattern detection failed: {e}")
        
        return regions
    
    def _merge_regions(self, regions: List[Rectangle]) -> List[Rectangle]:
        """Merge overlapping and nearby regions."""
        if not regions:
            return []
        
        # Sort by x coordinate
        sorted_regions = sorted(regions, key=lambda r: (r.y, r.x))
        
        merged = []
        current = sorted_regions[0]
        
        for next_region in sorted_regions[1:]:
            # Check if regions overlap or are close
            if self._should_merge(current, next_region):
                # Merge regions
                x1 = min(current.x, next_region.x)
                y1 = min(current.y, next_region.y)
                x2 = max(current.x + current.width, next_region.x + next_region.width)
                y2 = max(current.y + current.height, next_region.y + next_region.height)
                
                current = Rectangle(x=x1, y=y1, width=x2-x1, height=y2-y1)
            else:
                merged.append(current)
                current = next_region
        
        merged.append(current)
        return merged
    
    def _should_merge(self, rect1: Rectangle, rect2: Rectangle) -> bool:
        """Check if two rectangles should be merged."""
        # Check if they overlap
        if (rect1.x < rect2.x + rect2.width and
            rect1.x + rect1.width > rect2.x and
            rect1.y < rect2.y + rect2.height and
            rect1.y + rect1.height > rect2.y):
            return True
        
        # Check if they're close enough
        horizontal_distance = min(
            abs(rect1.x - (rect2.x + rect2.width)),
            abs(rect2.x - (rect1.x + rect1.width))
        )
        vertical_distance = min(
            abs(rect1.y - (rect2.y + rect2.height)),
            abs(rect2.y - (rect1.y + rect1.height))
        )
        
        if horizontal_distance < self.config.merge_distance and vertical_distance < self.config.merge_distance:
            return True
        
        return False
    
    def _filter_regions(self, regions: List[Rectangle]) -> List[Rectangle]:
        """Filter regions by size constraints."""
        filtered = []
        
        for region in regions:
            # Check minimum size
            if (region.width < self.config.min_region_width or
                region.height < self.config.min_region_height):
                continue
            
            # Check maximum size
            if (region.width > self.config.max_region_width or
                region.height > self.config.max_region_height):
                continue
            
            filtered.append(region)
        
        return filtered
    
    def visualize_regions(self, frame: Frame, regions: List[Rectangle]) -> np.ndarray:
        """
        Visualize detected regions on frame (for debugging).
        
        Args:
            frame: Input frame
            regions: Detected regions
            
        Returns:
            Image with regions drawn
        """
        image = frame.data.copy()
        
        # Convert to BGR if grayscale
        if len(image.shape) == 2:
            image = cv2.cvtColor(image, cv2.COLOR_GRAY2BGR)
        
        # Draw rectangles
        for i, region in enumerate(regions):
            color = (0, 255, 0)  # Green
            cv2.rectangle(
                image,
                (region.x, region.y),
                (region.x + region.width, region.y + region.height),
                color,
                2
            )
            
            # Add label
            label = f"ROI {i+1}"
            cv2.putText(
                image,
                label,
                (region.x, region.y - 5),
                cv2.FONT_HERSHEY_SIMPLEX,
                0.5,
                color,
                1
            )
        
        return image


def create_roi_detector(config: Optional[ROIConfig] = None) -> ROIDetector:
    """
    Factory function to create ROI detector.
    
    Args:
        config: Optional ROI configuration
        
    Returns:
        ROIDetector instance
    """
    return ROIDetector(config)
