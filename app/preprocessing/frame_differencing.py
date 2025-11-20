"""
Frame Differencing and Optimization

Implements frame comparison algorithms for change detection and ROI-based capture optimization.
Provides configurable sensitivity settings for frame differencing to optimize performance.
"""

import logging
import time
from typing import Optional, List, Dict, Any, Tuple, Union
from dataclasses import dataclass, field
from enum import Enum
import numpy as np
import cv2

try:
    from ..models import Frame, Rectangle, PerformanceProfile
    from ..interfaces import IPreprocessingLayer
except ImportError:
    from app.models import Frame, Rectangle, PerformanceProfile
    from app.interfaces import IPreprocessingLayer


class DifferenceMethod(Enum):
    """Frame difference calculation methods."""
    ABSOLUTE = "absolute"
    SQUARED = "squared"
    STRUCTURAL = "structural"
    HISTOGRAM = "histogram"


class SensitivityLevel(Enum):
    """Sensitivity levels for change detection."""
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CUSTOM = "custom"


@dataclass
class DifferenceConfig:
    """Configuration for frame differencing operations."""
    method: DifferenceMethod = DifferenceMethod.ABSOLUTE
    sensitivity: SensitivityLevel = SensitivityLevel.MEDIUM
    threshold: float = 0.1  # Custom threshold for CUSTOM sensitivity
    blur_kernel_size: int = 5
    morphology_kernel_size: int = 3
    min_change_area: int = 100  # Minimum area to consider as change
    max_change_percentage: float = 0.8  # Maximum percentage of frame that can be "changed"
    enable_noise_reduction: bool = True
    enable_morphology: bool = True
    
    def __post_init__(self):
        """Validate configuration parameters."""
        if not 0.0 <= self.threshold <= 1.0:
            raise ValueError("Threshold must be between 0.0 and 1.0")
        if self.blur_kernel_size % 2 == 0:
            raise ValueError("Blur kernel size must be odd")
        if self.morphology_kernel_size % 2 == 0:
            raise ValueError("Morphology kernel size must be odd")
        if not 0.0 <= self.max_change_percentage <= 1.0:
            raise ValueError("Max change percentage must be between 0.0 and 1.0")


@dataclass
class ChangeRegion:
    """Represents a region where changes were detected."""
    rectangle: Rectangle
    change_intensity: float  # 0.0 to 1.0
    pixel_count: int
    confidence: float  # 0.0 to 1.0
    
    @property
    def area(self) -> int:
        """Get the area of the change region."""
        return self.rectangle.area
    
    @property
    def is_significant(self) -> bool:
        """Check if this change region is significant."""
        return self.confidence > 0.5 and self.pixel_count > 50


@dataclass
class DifferenceResult:
    """Result of frame difference analysis."""
    has_changes: bool
    change_percentage: float
    change_regions: List[ChangeRegion] = field(default_factory=list)
    difference_map: Optional[np.ndarray] = None
    processing_time_ms: float = 0.0
    method_used: DifferenceMethod = DifferenceMethod.ABSOLUTE
    
    @property
    def significant_changes(self) -> List[ChangeRegion]:
        """Get only significant change regions."""
        return [region for region in self.change_regions if region.is_significant]
    
    @property
    def total_changed_pixels(self) -> int:
        """Get total number of changed pixels."""
        return sum(region.pixel_count for region in self.change_regions)


class FrameDifferenceEngine:
    """
    Core engine for frame difference calculations.
    
    Implements multiple algorithms for detecting changes between frames
    with configurable sensitivity and optimization settings.
    """
    
    def __init__(self, config: Optional[DifferenceConfig] = None, 
                 logger: Optional[logging.Logger] = None):
        """
        Initialize frame difference engine.
        
        Args:
            config: Configuration for difference calculations
            logger: Optional logger for debugging
        """
        self.config = config or DifferenceConfig()
        self.logger = logger or logging.getLogger(__name__)
        
        # Performance tracking
        self._processing_times = []
        self._max_history = 100
        
        # Cached kernels for morphological operations
        self._blur_kernel = None
        self._morph_kernel = None
        self._update_kernels()
        
        self.logger.debug(f"Frame difference engine initialized with method: {self.config.method.value}")
    
    def _update_kernels(self) -> None:
        """Update cached kernels when configuration changes."""
        self._blur_kernel = cv2.getGaussianKernel(self.config.blur_kernel_size, 0)
        self._morph_kernel = cv2.getStructuringElement(
            cv2.MORPH_ELLIPSE, 
            (self.config.morphology_kernel_size, self.config.morphology_kernel_size)
        )
    
    def set_config(self, config: DifferenceConfig) -> None:
        """
        Update configuration settings.
        
        Args:
            config: New configuration
        """
        self.config = config
        self._update_kernels()
        self.logger.debug(f"Configuration updated: method={config.method.value}, sensitivity={config.sensitivity.value}")
    
    def calculate_difference(self, current_frame: Frame, previous_frame: Frame) -> DifferenceResult:
        """
        Calculate difference between two frames.
        
        Args:
            current_frame: Current frame
            previous_frame: Previous frame for comparison
            
        Returns:
            DifferenceResult: Analysis results
        """
        start_time = time.time()
        
        try:
            # Validate inputs
            if current_frame.data.shape != previous_frame.data.shape:
                raise ValueError("Frame dimensions must match for comparison")
            
            # Convert to grayscale if needed
            current_gray = self._prepare_frame(current_frame.data)
            previous_gray = self._prepare_frame(previous_frame.data)
            
            # Calculate difference based on method
            if self.config.method == DifferenceMethod.ABSOLUTE:
                diff_map = self._calculate_absolute_difference(current_gray, previous_gray)
            elif self.config.method == DifferenceMethod.SQUARED:
                diff_map = self._calculate_squared_difference(current_gray, previous_gray)
            elif self.config.method == DifferenceMethod.STRUCTURAL:
                diff_map = self._calculate_structural_difference(current_gray, previous_gray)
            elif self.config.method == DifferenceMethod.HISTOGRAM:
                diff_map = self._calculate_histogram_difference(current_gray, previous_gray)
            else:
                raise ValueError(f"Unknown difference method: {self.config.method}")
            
            # Apply noise reduction if enabled
            if self.config.enable_noise_reduction:
                diff_map = self._apply_noise_reduction(diff_map)
            
            # Apply morphological operations if enabled
            if self.config.enable_morphology:
                diff_map = self._apply_morphology(diff_map)
            
            # Threshold the difference map
            threshold = self._get_threshold_value()
            binary_diff = (diff_map > threshold).astype(np.uint8) * 255
            
            # Find change regions
            change_regions = self._find_change_regions(binary_diff, diff_map)
            
            # Calculate change percentage
            total_pixels = diff_map.size
            changed_pixels = np.sum(binary_diff > 0)
            change_percentage = changed_pixels / total_pixels if total_pixels > 0 else 0.0
            
            # Determine if there are significant changes
            has_changes = (change_percentage > 0.01 and  # At least 1% change
                          change_percentage < self.config.max_change_percentage and  # Not too much change
                          len([r for r in change_regions if r.is_significant]) > 0)
            
            processing_time = (time.time() - start_time) * 1000
            self._update_performance_stats(processing_time)
            
            return DifferenceResult(
                has_changes=has_changes,
                change_percentage=change_percentage,
                change_regions=change_regions,
                difference_map=diff_map,
                processing_time_ms=processing_time,
                method_used=self.config.method
            )
            
        except Exception as e:
            self.logger.error(f"Frame difference calculation failed: {e}")
            processing_time = (time.time() - start_time) * 1000
            return DifferenceResult(
                has_changes=False,
                change_percentage=0.0,
                processing_time_ms=processing_time,
                method_used=self.config.method
            )
    
    def _prepare_frame(self, frame_data: np.ndarray) -> np.ndarray:
        """
        Prepare frame for difference calculation.
        
        Args:
            frame_data: Raw frame data
            
        Returns:
            np.ndarray: Prepared grayscale frame
        """
        if len(frame_data.shape) == 3:
            # Convert BGR to grayscale
            gray = cv2.cvtColor(frame_data, cv2.COLOR_BGR2GRAY)
        else:
            gray = frame_data.copy()
        
        # Normalize to 0-1 range
        return gray.astype(np.float32) / 255.0
    
    def _calculate_absolute_difference(self, current: np.ndarray, previous: np.ndarray) -> np.ndarray:
        """Calculate absolute difference between frames."""
        return np.abs(current - previous)
    
    def _calculate_squared_difference(self, current: np.ndarray, previous: np.ndarray) -> np.ndarray:
        """Calculate squared difference between frames."""
        diff = current - previous
        return diff * diff
    
    def _calculate_structural_difference(self, current: np.ndarray, previous: np.ndarray) -> np.ndarray:
        """Calculate structural similarity-based difference."""
        # Use SSIM-based approach for structural comparison
        from skimage.metrics import structural_similarity as ssim
        
        # Calculate SSIM for overlapping windows
        win_size = min(7, min(current.shape) // 4)
        if win_size % 2 == 0:
            win_size -= 1
        
        try:
            ssim_map = ssim(current, previous, win_size=win_size, full=True)[1]
            # Convert SSIM to difference (1 - SSIM)
            return 1.0 - ssim_map
        except Exception as e:
            self.logger.warning(f"SSIM calculation failed, falling back to absolute difference: {e}")
            return self._calculate_absolute_difference(current, previous)
    
    def _calculate_histogram_difference(self, current: np.ndarray, previous: np.ndarray) -> np.ndarray:
        """Calculate histogram-based difference."""
        # Calculate local histograms using sliding window
        window_size = 16
        diff_map = np.zeros_like(current)
        
        for y in range(0, current.shape[0] - window_size, window_size // 2):
            for x in range(0, current.shape[1] - window_size, window_size // 2):
                # Extract windows
                curr_window = current[y:y+window_size, x:x+window_size]
                prev_window = previous[y:y+window_size, x:x+window_size]
                
                # Calculate histograms
                curr_hist = np.histogram(curr_window, bins=32, range=(0, 1))[0]
                prev_hist = np.histogram(prev_window, bins=32, range=(0, 1))[0]
                
                # Normalize histograms
                curr_hist = curr_hist / (curr_hist.sum() + 1e-7)
                prev_hist = prev_hist / (prev_hist.sum() + 1e-7)
                
                # Calculate chi-square distance
                chi_square = np.sum((curr_hist - prev_hist) ** 2 / (curr_hist + prev_hist + 1e-7))
                
                # Fill difference map
                diff_map[y:y+window_size, x:x+window_size] = chi_square
        
        return diff_map
    
    def _apply_noise_reduction(self, diff_map: np.ndarray) -> np.ndarray:
        """Apply noise reduction to difference map."""
        # Gaussian blur to reduce noise
        return cv2.GaussianBlur(diff_map, (self.config.blur_kernel_size, self.config.blur_kernel_size), 0)
    
    def _apply_morphology(self, diff_map: np.ndarray) -> np.ndarray:
        """Apply morphological operations to clean up difference map."""
        # Convert to uint8 for morphological operations
        diff_uint8 = (diff_map * 255).astype(np.uint8)
        
        # Apply opening to remove small noise
        opened = cv2.morphologyEx(diff_uint8, cv2.MORPH_OPEN, self._morph_kernel)
        
        # Apply closing to fill small gaps
        closed = cv2.morphologyEx(opened, cv2.MORPH_CLOSE, self._morph_kernel)
        
        # Convert back to float
        return closed.astype(np.float32) / 255.0
    
    def _get_threshold_value(self) -> float:
        """Get threshold value based on sensitivity setting."""
        if self.config.sensitivity == SensitivityLevel.LOW:
            return 0.2
        elif self.config.sensitivity == SensitivityLevel.MEDIUM:
            return 0.1
        elif self.config.sensitivity == SensitivityLevel.HIGH:
            return 0.05
        else:  # CUSTOM
            return self.config.threshold
    
    def _find_change_regions(self, binary_diff: np.ndarray, diff_map: np.ndarray) -> List[ChangeRegion]:
        """
        Find and analyze change regions in the difference map.
        
        Args:
            binary_diff: Binary difference map
            diff_map: Original difference map with intensity values
            
        Returns:
            List[ChangeRegion]: List of detected change regions
        """
        regions = []
        
        try:
            # Find connected components
            num_labels, labels, stats, centroids = cv2.connectedComponentsWithStats(binary_diff, connectivity=8)
            
            for i in range(1, num_labels):  # Skip background (label 0)
                # Get component statistics
                x, y, w, h, area = stats[i]
                
                # Filter out small regions
                if area < self.config.min_change_area:
                    continue
                
                # Create mask for this component
                component_mask = (labels == i)
                
                # Calculate change intensity for this region
                region_diff_values = diff_map[component_mask]
                change_intensity = np.mean(region_diff_values)
                
                # Calculate confidence based on area and intensity
                confidence = min(1.0, (area / 1000.0) * change_intensity * 2.0)
                
                # Create change region
                region = ChangeRegion(
                    rectangle=Rectangle(x, y, w, h),
                    change_intensity=change_intensity,
                    pixel_count=area,
                    confidence=confidence
                )
                
                regions.append(region)
            
            # Sort regions by confidence (highest first)
            regions.sort(key=lambda r: r.confidence, reverse=True)
            
        except Exception as e:
            self.logger.error(f"Error finding change regions: {e}")
        
        return regions
    
    def _update_performance_stats(self, processing_time: float) -> None:
        """Update performance statistics."""
        self._processing_times.append(processing_time)
        if len(self._processing_times) > self._max_history:
            self._processing_times.pop(0)
    
    def get_performance_stats(self) -> Dict[str, float]:
        """
        Get performance statistics.
        
        Returns:
            Dict[str, float]: Performance metrics
        """
        if not self._processing_times:
            return {'avg_processing_time_ms': 0.0, 'min_time_ms': 0.0, 'max_time_ms': 0.0}
        
        return {
            'avg_processing_time_ms': np.mean(self._processing_times),
            'min_time_ms': np.min(self._processing_times),
            'max_time_ms': np.max(self._processing_times),
            'samples': len(self._processing_times)
        }


class ROIOptimizer:
    """
    Region of Interest optimizer for capture optimization.
    
    Uses frame differencing results to optimize capture regions and reduce
    processing overhead by focusing on areas with changes.
    """
    
    def __init__(self, logger: Optional[logging.Logger] = None):
        """
        Initialize ROI optimizer.
        
        Args:
            logger: Optional logger for debugging
        """
        self.logger = logger or logging.getLogger(__name__)
        
        # ROI tracking
        self._active_rois: List[Rectangle] = []
        self._roi_history: List[List[Rectangle]] = []
        self._max_history = 10
        
        # Optimization settings
        self._min_roi_size = 50
        self._max_rois = 5
        self._roi_expansion_factor = 1.2
        self._roi_merge_threshold = 0.3
        
        self.logger.debug("ROI optimizer initialized")
    
    def optimize_capture_regions(self, difference_result: DifferenceResult, 
                                frame_size: Tuple[int, int]) -> List[Rectangle]:
        """
        Optimize capture regions based on frame difference analysis.
        
        Args:
            difference_result: Results from frame difference analysis
            frame_size: Size of the frame (width, height)
            
        Returns:
            List[Rectangle]: Optimized capture regions
        """
        try:
            if not difference_result.has_changes or not difference_result.significant_changes:
                # No significant changes, return previous ROIs or full frame
                if self._active_rois:
                    optimized_regions = self._active_rois
                else:
                    optimized_regions = [Rectangle(0, 0, frame_size[0], frame_size[1])]
            else:
                # Get significant change regions
                change_regions = [region.rectangle for region in difference_result.significant_changes]
                
                # Expand regions to account for potential text areas
                expanded_regions = self._expand_regions(change_regions, frame_size)
                
                # Merge overlapping regions
                merged_regions = self._merge_overlapping_regions(expanded_regions)
                
                # Limit number of ROIs
                optimized_regions = self._limit_roi_count(merged_regions)
                
                # Ensure we have at least one ROI
                if not optimized_regions:
                    optimized_regions = [Rectangle(0, 0, frame_size[0], frame_size[1])]
            
            # Update tracking
            self._active_rois = optimized_regions
            self._roi_history.append(optimized_regions.copy())
            if len(self._roi_history) > self._max_history:
                self._roi_history.pop(0)
            
            self.logger.debug(f"Optimized to {len(optimized_regions)} ROIs")
            return optimized_regions
            
        except Exception as e:
            self.logger.error(f"ROI optimization failed: {e}")
            # Fallback to full frame
            fallback_roi = [Rectangle(0, 0, frame_size[0], frame_size[1])]
            self._active_rois = fallback_roi
            return fallback_roi
    
    def _expand_regions(self, regions: List[Rectangle], frame_size: Tuple[int, int]) -> List[Rectangle]:
        """Expand regions to account for potential text areas."""
        expanded = []
        
        for region in regions:
            # Calculate expansion
            expand_w = int(region.width * (self._roi_expansion_factor - 1) / 2)
            expand_h = int(region.height * (self._roi_expansion_factor - 1) / 2)
            
            # Apply expansion with bounds checking
            new_x = max(0, region.x - expand_w)
            new_y = max(0, region.y - expand_h)
            new_w = min(frame_size[0] - new_x, region.width + 2 * expand_w)
            new_h = min(frame_size[1] - new_y, region.height + 2 * expand_h)
            
            # Only add if meets minimum size requirement
            if new_w >= self._min_roi_size and new_h >= self._min_roi_size:
                expanded.append(Rectangle(new_x, new_y, new_w, new_h))
        
        return expanded
    
    def _merge_overlapping_regions(self, regions: List[Rectangle]) -> List[Rectangle]:
        """Merge overlapping or nearby regions."""
        if len(regions) <= 1:
            return regions
        
        merged = []
        used = set()
        
        for i, region1 in enumerate(regions):
            if i in used:
                continue
            
            # Start with current region
            merged_region = Rectangle(region1.x, region1.y, region1.width, region1.height)
            used.add(i)
            
            # Check for overlaps with remaining regions
            for j, region2 in enumerate(regions[i+1:], i+1):
                if j in used:
                    continue
                
                if self._should_merge_regions(merged_region, region2):
                    # Merge regions
                    min_x = min(merged_region.x, region2.x)
                    min_y = min(merged_region.y, region2.y)
                    max_x = max(merged_region.x + merged_region.width, region2.x + region2.width)
                    max_y = max(merged_region.y + merged_region.height, region2.y + region2.height)
                    
                    merged_region = Rectangle(min_x, min_y, max_x - min_x, max_y - min_y)
                    used.add(j)
            
            merged.append(merged_region)
        
        return merged
    
    def _should_merge_regions(self, region1: Rectangle, region2: Rectangle) -> bool:
        """Check if two regions should be merged."""
        # Calculate overlap
        overlap_x = max(0, min(region1.x + region1.width, region2.x + region2.width) - 
                           max(region1.x, region2.x))
        overlap_y = max(0, min(region1.y + region1.height, region2.y + region2.height) - 
                           max(region1.y, region2.y))
        overlap_area = overlap_x * overlap_y
        
        # Calculate union area
        union_area = region1.area + region2.area - overlap_area
        
        # Merge if overlap ratio is above threshold
        overlap_ratio = overlap_area / union_area if union_area > 0 else 0
        return overlap_ratio > self._roi_merge_threshold
    
    def _limit_roi_count(self, regions: List[Rectangle]) -> List[Rectangle]:
        """Limit the number of ROIs to maximum allowed."""
        if len(regions) <= self._max_rois:
            return regions
        
        # Sort by area (largest first) and take top regions
        sorted_regions = sorted(regions, key=lambda r: r.area, reverse=True)
        return sorted_regions[:self._max_rois]
    
    def get_roi_statistics(self) -> Dict[str, Any]:
        """
        Get ROI optimization statistics.
        
        Returns:
            Dict[str, Any]: ROI statistics
        """
        total_area = sum(roi.area for roi in self._active_rois)
        
        return {
            'active_roi_count': len(self._active_rois),
            'total_roi_area': total_area,
            'history_length': len(self._roi_history),
            'average_rois_per_frame': np.mean([len(rois) for rois in self._roi_history]) if self._roi_history else 0
        }
    
    def reset_rois(self) -> None:
        """Reset ROI tracking."""
        self._active_rois.clear()
        self._roi_history.clear()
        self.logger.debug("ROI tracking reset")


class FrameDifferencingSystem:
    """
    Complete frame differencing and optimization system.
    
    Combines frame difference engine and ROI optimizer to provide
    comprehensive change detection and capture optimization.
    """
    
    def __init__(self, config: Optional[DifferenceConfig] = None,
                 logger: Optional[logging.Logger] = None):
        """
        Initialize frame differencing system.
        
        Args:
            config: Configuration for difference calculations
            logger: Optional logger for debugging
        """
        self.logger = logger or logging.getLogger(__name__)
        
        # Initialize components
        self.difference_engine = FrameDifferenceEngine(config, logger)
        self.roi_optimizer = ROIOptimizer(logger)
        
        # Frame history for comparison
        self._previous_frame: Optional[Frame] = None
        self._frame_history: List[Frame] = []
        self._max_frame_history = 3
        
        # Performance tracking
        self._total_comparisons = 0
        self._optimization_enabled = True
        
        self.logger.info("Frame differencing system initialized")
    
    def process_frame(self, current_frame: Frame) -> Tuple[DifferenceResult, List[Rectangle]]:
        """
        Process frame for changes and optimize capture regions.
        
        Args:
            current_frame: Current frame to process
            
        Returns:
            Tuple[DifferenceResult, List[Rectangle]]: Difference results and optimized ROIs
        """
        try:
            # Increment comparison counter for all frames
            self._total_comparisons += 1
            
            # Initialize result for first frame
            if self._previous_frame is None:
                self._previous_frame = current_frame
                frame_size = (current_frame.width, current_frame.height)
                full_frame_roi = [Rectangle(0, 0, frame_size[0], frame_size[1])]
                
                # Update frame history
                self._update_frame_history(current_frame)
                
                return DifferenceResult(
                    has_changes=True,  # Assume changes for first frame
                    change_percentage=1.0
                ), full_frame_roi
            
            # Calculate frame difference
            difference_result = self.difference_engine.calculate_difference(
                current_frame, self._previous_frame
            )
            
            # Optimize capture regions if enabled
            optimized_rois = []
            if self._optimization_enabled:
                frame_size = (current_frame.width, current_frame.height)
                optimized_rois = self.roi_optimizer.optimize_capture_regions(
                    difference_result, frame_size
                )
            else:
                # Use full frame if optimization disabled
                frame_size = (current_frame.width, current_frame.height)
                optimized_rois = [Rectangle(0, 0, frame_size[0], frame_size[1])]
            
            # Update frame history
            self._update_frame_history(current_frame)
            
            return difference_result, optimized_rois
            
        except Exception as e:
            self.logger.error(f"Frame processing failed: {e}")
            # Return safe defaults
            frame_size = (current_frame.width, current_frame.height)
            return DifferenceResult(has_changes=True, change_percentage=1.0), \
                   [Rectangle(0, 0, frame_size[0], frame_size[1])]
    
    def _update_frame_history(self, frame: Frame) -> None:
        """Update frame history for multi-frame analysis."""
        self._frame_history.append(frame)
        if len(self._frame_history) > self._max_frame_history:
            self._frame_history.pop(0)
        
        # Update previous frame reference
        self._previous_frame = frame
    
    def set_optimization_enabled(self, enabled: bool) -> None:
        """
        Enable or disable ROI optimization.
        
        Args:
            enabled: Whether to enable ROI optimization
        """
        self._optimization_enabled = enabled
        self.logger.info(f"ROI optimization {'enabled' if enabled else 'disabled'}")
    
    def update_config(self, config: DifferenceConfig) -> None:
        """
        Update configuration settings.
        
        Args:
            config: New configuration
        """
        self.difference_engine.set_config(config)
        self.logger.info("Frame differencing configuration updated")
    
    def get_system_statistics(self) -> Dict[str, Any]:
        """
        Get comprehensive system statistics.
        
        Returns:
            Dict[str, Any]: System statistics
        """
        stats = {
            'total_comparisons': self._total_comparisons,
            'optimization_enabled': self._optimization_enabled,
            'frame_history_length': len(self._frame_history),
            'difference_engine_stats': self.difference_engine.get_performance_stats(),
            'roi_optimizer_stats': self.roi_optimizer.get_roi_statistics()
        }
        
        return stats
    
    def reset_system(self) -> None:
        """Reset the entire system state."""
        self._previous_frame = None
        self._frame_history.clear()
        self.roi_optimizer.reset_rois()
        self._total_comparisons = 0
        self.logger.info("Frame differencing system reset")