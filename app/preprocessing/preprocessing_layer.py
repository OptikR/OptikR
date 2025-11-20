"""
Preprocessing Layer Implementation

Implements image preprocessing functionality with frame differencing and ROI optimization.
Provides scaling, grayscale conversion, denoising, and adaptive thresholding for OCR accuracy.
"""

import logging
import time
from typing import Optional, List, Dict, Any, Tuple
from dataclasses import dataclass
from enum import Enum
import numpy as np
import cv2

try:
    from ..models import Frame, Rectangle, PerformanceProfile
    from ..interfaces import IPreprocessingLayer
    from .frame_differencing import (
        FrameDifferencingSystem, DifferenceConfig, DifferenceMethod, 
        SensitivityLevel, DifferenceResult
    )
except ImportError:
    from app.models import Frame, Rectangle, PerformanceProfile
    from app.interfaces import IPreprocessingLayer
    from app.preprocessing.frame_differencing import (
        FrameDifferencingSystem, DifferenceConfig, DifferenceMethod, 
        SensitivityLevel, DifferenceResult
    )


class FilterType(Enum):
    """Available image filters."""
    GAUSSIAN_BLUR = "gaussian_blur"
    BILATERAL = "bilateral"
    MEDIAN = "median"
    SHARPEN = "sharpen"
    DENOISE = "denoise"
    CONTRAST_ENHANCE = "contrast_enhance"


@dataclass
class PreprocessingProfile:
    """Configuration profile for preprocessing operations."""
    # Scaling settings
    target_width: Optional[int] = None
    target_height: Optional[int] = None
    maintain_aspect_ratio: bool = True
    interpolation_method: int = cv2.INTER_CUBIC
    
    # Grayscale conversion
    convert_to_grayscale: bool = True
    grayscale_method: str = "weighted"  # "weighted", "average", "luminance", "desaturate", "max_channel", "adaptive"
    
    # Denoising settings
    enable_denoising: bool = True
    denoise_strength: float = 3.0
    denoise_template_window_size: int = 7
    denoise_search_window_size: int = 21
    
    # Thresholding settings
    enable_adaptive_threshold: bool = True
    threshold_method: int = cv2.THRESH_BINARY
    adaptive_method: int = cv2.ADAPTIVE_THRESH_GAUSSIAN_C
    block_size: int = 11
    c_constant: float = 2.0
    
    # Frame differencing settings
    enable_frame_differencing: bool = True
    difference_method: DifferenceMethod = DifferenceMethod.ABSOLUTE
    sensitivity_level: SensitivityLevel = SensitivityLevel.MEDIUM
    
    # ROI detection settings
    enable_roi_detection: bool = True
    roi_min_area: int = 100
    roi_max_count: int = 10
    
    # Content-specific settings
    content_type: str = "mixed"  # "text", "mixed", "graphics", "screenshot"
    
    # Advanced preprocessing options
    enable_contrast_enhancement: bool = False
    enable_sharpening: bool = False
    enable_morphological_operations: bool = False
    
    @classmethod
    def create_for_performance_profile(cls, profile: PerformanceProfile, content_type: str = "mixed") -> 'PreprocessingProfile':
        """
        Create preprocessing profile optimized for specific performance level and content type.
        
        Args:
            profile: Performance profile
            content_type: Type of content being processed
            
        Returns:
            PreprocessingProfile: Optimized preprocessing configuration
        """
        base_config = {}
        
        # Performance-based settings
        if profile == PerformanceProfile.LOW:
            base_config.update({
                'target_width': 640,
                'target_height': 480,
                'interpolation_method': cv2.INTER_LINEAR,
                'denoise_strength': 1.0,
                'denoise_template_window_size': 5,
                'denoise_search_window_size': 15,
                'block_size': 9,
                'sensitivity_level': SensitivityLevel.LOW,
                'roi_max_count': 3,
                'enable_contrast_enhancement': False,
                'enable_sharpening': False,
                'enable_morphological_operations': False
            })
        elif profile == PerformanceProfile.NORMAL:
            base_config.update({
                'target_width': 1280,
                'target_height': 720,
                'interpolation_method': cv2.INTER_CUBIC,
                'denoise_strength': 3.0,
                'sensitivity_level': SensitivityLevel.MEDIUM,
                'roi_max_count': 5,
                'enable_contrast_enhancement': True,
                'enable_sharpening': False,
                'enable_morphological_operations': True
            })
        else:  # HIGH
            base_config.update({
                'target_width': None,  # No scaling for high quality
                'target_height': None,
                'interpolation_method': cv2.INTER_LANCZOS4,
                'denoise_strength': 5.0,
                'denoise_template_window_size': 9,
                'denoise_search_window_size': 25,
                'block_size': 15,
                'sensitivity_level': SensitivityLevel.HIGH,
                'roi_max_count': 10,
                'enable_contrast_enhancement': True,
                'enable_sharpening': True,
                'enable_morphological_operations': True
            })
        
        # Content-specific adjustments
        if content_type == "text":
            base_config.update({
                'grayscale_method': "luminance",
                'enable_adaptive_threshold': True,
                'enable_sharpening': True,
                'c_constant': 3.0
            })
        elif content_type == "graphics":
            base_config.update({
                'grayscale_method': "weighted",
                'enable_adaptive_threshold': False,
                'enable_contrast_enhancement': True,
                'denoise_strength': base_config.get('denoise_strength', 3.0) * 0.7
            })
        elif content_type == "screenshot":
            base_config.update({
                'grayscale_method': "adaptive",
                'enable_adaptive_threshold': True,
                'enable_contrast_enhancement': True,
                'enable_morphological_operations': True
            })
        
        base_config['content_type'] = content_type
        return cls(**base_config)
    
    @classmethod
    def create_for_content_type(cls, content_type: str) -> 'PreprocessingProfile':
        """
        Create preprocessing profile optimized for specific content type.
        
        Args:
            content_type: Type of content ("text", "mixed", "graphics", "screenshot")
            
        Returns:
            PreprocessingProfile: Content-optimized preprocessing configuration
        """
        return cls.create_for_performance_profile(PerformanceProfile.NORMAL, content_type)


class PreprocessingLayer(IPreprocessingLayer):
    """
    Main preprocessing layer implementation.
    
    Provides comprehensive image preprocessing with frame differencing,
    ROI optimization, and configurable filtering operations.
    """
    
    def __init__(self, logger: Optional[logging.Logger] = None):
        """
        Initialize preprocessing layer.
        
        Args:
            logger: Optional logger for debugging
        """
        self.logger = logger or logging.getLogger(__name__)
        
        # Initialize frame differencing system
        self._frame_differencing = FrameDifferencingSystem(logger=logger)
        
        # Initialize small text enhancer
        try:
            from .small_text_enhancer import SmallTextEnhancer
            self._small_text_enhancer = SmallTextEnhancer(logger=logger)
            self._small_text_enhancement_enabled = False
        except ImportError as e:
            self.logger.warning(f"Small text enhancer not available: {e}")
            self._small_text_enhancer = None
            self._small_text_enhancement_enabled = False
        
        # Current configuration
        self._current_profile = PreprocessingProfile.create_for_performance_profile(
            PerformanceProfile.NORMAL
        )
        
        # Performance tracking
        self._processing_times = []
        self._max_history = 100
        
        # Statistics
        self._stats = {
            'frames_processed': 0,
            'total_processing_time': 0.0,
            'roi_optimizations': 0,
            'frame_differences_calculated': 0
        }
        
        self.logger.info("Preprocessing layer initialized")
    
    def preprocess(self, frame: Frame, profile: PerformanceProfile) -> Frame:
        """
        Preprocess frame for optimal OCR accuracy.
        
        Args:
            frame: Input frame to preprocess
            profile: Performance profile for optimization
            
        Returns:
            Frame: Preprocessed frame
        """
        start_time = time.time()
        
        try:
            # Update profile if needed
            if profile != self._get_current_performance_profile():
                self._update_profile_for_performance(profile)
            
            # Start with original frame data
            processed_data = frame.data.copy()
            
            # Apply small text enhancement if enabled (before other preprocessing)
            if self._small_text_enhancement_enabled and self._small_text_enhancer:
                enhanced_frame = self._small_text_enhancer.enhance_frame(frame)
                processed_data = enhanced_frame.data.copy()
                self.logger.debug("Small text enhancement applied")
            
            # Apply scaling if configured
            if (self._current_profile.target_width is not None and 
                self._current_profile.target_height is not None):
                processed_data = self._apply_scaling(processed_data)
            
            # Convert to grayscale if enabled
            if self._current_profile.convert_to_grayscale:
                processed_data = self._convert_to_grayscale(processed_data)
            
            # Apply denoising if enabled
            if self._current_profile.enable_denoising:
                processed_data = self._apply_denoising(processed_data)
            
            # Apply adaptive thresholding if enabled
            if self._current_profile.enable_adaptive_threshold:
                processed_data = self._apply_adaptive_threshold(processed_data)
            
            # Create preprocessed frame
            preprocessed_frame = Frame(
                data=processed_data,
                timestamp=frame.timestamp,
                source_region=frame.source_region,
                metadata={
                    **frame.metadata,
                    'preprocessing_applied': True,
                    'preprocessing_profile': profile.value,
                    'original_shape': frame.data.shape,
                    'processed_shape': processed_data.shape
                }
            )
            
            # Update statistics
            processing_time = time.time() - start_time
            self._update_processing_stats(processing_time)
            
            return preprocessed_frame
            
        except Exception as e:
            self.logger.error(f"Frame preprocessing failed: {e}")
            # Return original frame on error
            return frame
    
    def detect_roi(self, frame: Frame) -> List[Rectangle]:
        """
        Detect regions of interest containing text.
        
        Args:
            frame: Input frame for ROI detection
            
        Returns:
            List[Rectangle]: List of detected ROI rectangles
        """
        try:
            if not self._current_profile.enable_roi_detection:
                # Return full frame as single ROI
                return [Rectangle(0, 0, frame.width, frame.height)]
            
            # Use frame differencing for ROI optimization if enabled
            if self._current_profile.enable_frame_differencing:
                difference_result, optimized_rois = self._frame_differencing.process_frame(frame)
                self._stats['frame_differences_calculated'] += 1
                
                if optimized_rois:
                    self._stats['roi_optimizations'] += 1
                    return optimized_rois
            
            # Fallback to traditional ROI detection
            return self._detect_text_regions(frame)
            
        except Exception as e:
            self.logger.error(f"ROI detection failed: {e}")
            # Return full frame as fallback
            return [Rectangle(0, 0, frame.width, frame.height)]
    
    def apply_filters(self, frame: Frame, filters: List[str]) -> Frame:
        """
        Apply specified image filters to frame.
        
        Args:
            frame: Input frame
            filters: List of filter names to apply
            
        Returns:
            Frame: Frame with filters applied
        """
        try:
            processed_data = frame.data.copy()
            
            for filter_name in filters:
                try:
                    filter_type = FilterType(filter_name)
                    processed_data = self._apply_filter(processed_data, filter_type)
                except ValueError:
                    self.logger.warning(f"Unknown filter type: {filter_name}")
                    continue
            
            # Create filtered frame
            filtered_frame = Frame(
                data=processed_data,
                timestamp=frame.timestamp,
                source_region=frame.source_region,
                metadata={
                    **frame.metadata,
                    'filters_applied': filters,
                    'original_shape': frame.data.shape,
                    'filtered_shape': processed_data.shape
                }
            )
            
            return filtered_frame
            
        except Exception as e:
            self.logger.error(f"Filter application failed: {e}")
            return frame
    
    def get_frame_diff(self, current: Frame, previous: Frame) -> Frame:
        """
        Calculate difference between frames for change detection.
        
        Args:
            current: Current frame
            previous: Previous frame for comparison
            
        Returns:
            Frame: Frame containing difference data
        """
        try:
            # Use frame differencing system
            difference_result = self._frame_differencing.difference_engine.calculate_difference(
                current, previous
            )
            
            # Create difference frame
            if difference_result.difference_map is not None:
                # Convert difference map to uint8 for frame format
                diff_data = (difference_result.difference_map * 255).astype(np.uint8)
                
                # Ensure 3-channel format if needed
                if len(diff_data.shape) == 2:
                    diff_data = cv2.cvtColor(diff_data, cv2.COLOR_GRAY2BGR)
                
                diff_frame = Frame(
                    data=diff_data,
                    timestamp=current.timestamp,
                    source_region=current.source_region,
                    metadata={
                        'is_difference_frame': True,
                        'has_changes': difference_result.has_changes,
                        'change_percentage': difference_result.change_percentage,
                        'processing_time_ms': difference_result.processing_time_ms,
                        'method_used': difference_result.method_used.value,
                        'change_regions_count': len(difference_result.change_regions)
                    }
                )
                
                return diff_frame
            else:
                # Return empty difference frame
                empty_data = np.zeros_like(current.data)
                return Frame(
                    data=empty_data,
                    timestamp=current.timestamp,
                    source_region=current.source_region,
                    metadata={'is_difference_frame': True, 'has_changes': False}
                )
                
        except Exception as e:
            self.logger.error(f"Frame difference calculation failed: {e}")
            # Return empty difference frame on error
            empty_data = np.zeros_like(current.data)
            return Frame(
                data=empty_data,
                timestamp=current.timestamp,
                source_region=current.source_region,
                metadata={'is_difference_frame': True, 'error': str(e)}
            )
    
    def _apply_scaling(self, image: np.ndarray) -> np.ndarray:
        """
        Apply intelligent scaling to image for optimal OCR processing.
        
        Uses advanced interpolation methods and maintains text clarity.
        
        Args:
            image: Input image array
            
        Returns:
            np.ndarray: Scaled image optimized for text recognition
        """
        target_w = self._current_profile.target_width
        target_h = self._current_profile.target_height
        
        if target_w is None or target_h is None:
            return image
        
        current_h, current_w = image.shape[:2]
        
        # Skip scaling if already at target size
        if current_w == target_w and current_h == target_h:
            return image
        
        if self._current_profile.maintain_aspect_ratio:
            # Calculate scaling factor to fit within target dimensions
            scale_w = target_w / current_w
            scale_h = target_h / current_h
            scale = min(scale_w, scale_h)
            
            new_w = int(current_w * scale)
            new_h = int(current_h * scale)
        else:
            new_w = target_w
            new_h = target_h
        
        # Use different interpolation methods based on scaling direction
        if new_w * new_h > current_w * current_h:
            # Upscaling - use high-quality interpolation
            interpolation = cv2.INTER_CUBIC if self._current_profile.interpolation_method == cv2.INTER_CUBIC else cv2.INTER_LANCZOS4
        else:
            # Downscaling - use area interpolation for better text preservation
            interpolation = cv2.INTER_AREA
        
        try:
            scaled_image = cv2.resize(image, (new_w, new_h), interpolation=interpolation)
            
            # Apply sharpening after scaling to enhance text clarity
            if new_w * new_h < current_w * current_h * 0.5:  # Significant downscaling
                kernel = np.array([[0, -1, 0], [-1, 5, -1], [0, -1, 0]], dtype=np.float32)
                scaled_image = cv2.filter2D(scaled_image, -1, kernel)
                scaled_image = np.clip(scaled_image, 0, 255).astype(np.uint8)
            
            return scaled_image
            
        except Exception as e:
            self.logger.error(f"Scaling failed: {e}")
            return image
    
    def _convert_to_grayscale(self, image: np.ndarray) -> np.ndarray:
        """
        Convert image to grayscale using optimal method for text recognition.
        
        Implements multiple conversion methods optimized for different content types.
        
        Args:
            image: Input color image
            
        Returns:
            np.ndarray: Grayscale image optimized for OCR
        """
        if len(image.shape) == 2:
            return image  # Already grayscale
        
        try:
            if self._current_profile.grayscale_method == "weighted":
                # OpenCV's optimized weighted conversion (0.299*R + 0.587*G + 0.114*B)
                return cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
                
            elif self._current_profile.grayscale_method == "average":
                # Simple average method
                return np.mean(image, axis=2).astype(np.uint8)
                
            elif self._current_profile.grayscale_method == "luminance":
                # ITU-R BT.709 luminance formula for better text contrast
                if image.shape[2] >= 3:  # BGR or BGRA
                    # OpenCV uses BGR format
                    b, g, r = image[:, :, 0], image[:, :, 1], image[:, :, 2]
                    luminance = (0.2126 * r + 0.7152 * g + 0.0722 * b).astype(np.uint8)
                    return luminance
                else:
                    return cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
                    
            elif self._current_profile.grayscale_method == "desaturate":
                # Desaturation method - preserves brightness better for text
                hsv = cv2.cvtColor(image, cv2.COLOR_BGR2HSV)
                return hsv[:, :, 2]  # Return value channel
                
            elif self._current_profile.grayscale_method == "max_channel":
                # Maximum channel method - good for high contrast text
                return np.max(image, axis=2).astype(np.uint8)
                
            elif self._current_profile.grayscale_method == "adaptive":
                # Adaptive method based on image content analysis
                # Analyze image to determine best conversion method
                std_per_channel = np.std(image, axis=(0, 1))
                max_std_channel = np.argmax(std_per_channel)
                
                if max_std_channel == 1:  # Green channel has most variation
                    return image[:, :, 1]  # Use green channel
                else:
                    return cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)  # Use weighted
                    
            else:
                # Default to OpenCV's weighted conversion
                return cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
                
        except Exception as e:
            self.logger.error(f"Grayscale conversion failed: {e}")
            # Fallback to simple weighted conversion
            return cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
    
    def _apply_denoising(self, image: np.ndarray) -> np.ndarray:
        """
        Apply advanced denoising algorithms optimized for text preservation.
        
        Uses multiple denoising techniques based on image characteristics and performance profile.
        
        Args:
            image: Input image with noise
            
        Returns:
            np.ndarray: Denoised image with preserved text clarity
        """
        try:
            # Analyze image noise level to select appropriate denoising method
            noise_level = self._estimate_noise_level(image)
            
            if noise_level < 5:  # Low noise - minimal processing
                return self._apply_light_denoising(image)
            elif noise_level < 15:  # Medium noise - standard denoising
                return self._apply_standard_denoising(image)
            else:  # High noise - aggressive denoising
                return self._apply_aggressive_denoising(image)
                
        except Exception as e:
            self.logger.error(f"Denoising failed: {e}")
            return image
    
    def _estimate_noise_level(self, image: np.ndarray) -> float:
        """
        Estimate noise level in image using Laplacian variance method.
        
        Args:
            image: Input image
            
        Returns:
            float: Estimated noise level (higher = more noise)
        """
        try:
            # Convert to grayscale if needed
            if len(image.shape) == 3:
                gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
            else:
                gray = image
            
            # Calculate Laplacian variance as noise estimate
            laplacian_var = cv2.Laplacian(gray, cv2.CV_64F).var()
            return laplacian_var
            
        except Exception:
            return 10.0  # Default medium noise level
    
    def _apply_light_denoising(self, image: np.ndarray) -> np.ndarray:
        """Apply light denoising for low-noise images."""
        if len(image.shape) == 2:
            # Light bilateral filter for grayscale
            return cv2.bilateralFilter(image, 5, 20, 20)
        else:
            # Light bilateral filter for color
            return cv2.bilateralFilter(image, 5, 20, 20)
    
    def _apply_standard_denoising(self, image: np.ndarray) -> np.ndarray:
        """Apply standard denoising for medium-noise images."""
        if len(image.shape) == 2:
            # Non-local means denoising for grayscale
            return cv2.fastNlMeansDenoising(
                image,
                None,
                self._current_profile.denoise_strength,
                self._current_profile.denoise_template_window_size,
                self._current_profile.denoise_search_window_size
            )
        else:
            # Non-local means denoising for color
            return cv2.fastNlMeansDenoisingColored(
                image,
                None,
                self._current_profile.denoise_strength,
                self._current_profile.denoise_strength,
                self._current_profile.denoise_template_window_size,
                self._current_profile.denoise_search_window_size
            )
    
    def _apply_aggressive_denoising(self, image: np.ndarray) -> np.ndarray:
        """Apply aggressive denoising for high-noise images."""
        # Multi-stage denoising approach
        
        # Stage 1: Bilateral filter to preserve edges
        if len(image.shape) == 2:
            denoised = cv2.bilateralFilter(image, 9, 50, 50)
        else:
            denoised = cv2.bilateralFilter(image, 9, 50, 50)
        
        # Stage 2: Non-local means with higher strength
        strength = min(self._current_profile.denoise_strength * 1.5, 10.0)
        
        if len(denoised.shape) == 2:
            denoised = cv2.fastNlMeansDenoising(
                denoised,
                None,
                strength,
                self._current_profile.denoise_template_window_size,
                self._current_profile.denoise_search_window_size
            )
        else:
            denoised = cv2.fastNlMeansDenoisingColored(
                denoised,
                None,
                strength,
                strength,
                self._current_profile.denoise_template_window_size,
                self._current_profile.denoise_search_window_size
            )
        
        # Stage 3: Light morphological operations to clean up artifacts
        if len(denoised.shape) == 2:
            kernel = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (3, 3))
            denoised = cv2.morphologyEx(denoised, cv2.MORPH_CLOSE, kernel)
        
        return denoised
    
    def _apply_adaptive_threshold(self, image: np.ndarray) -> np.ndarray:
        """
        Apply intelligent adaptive thresholding based on content analysis.
        
        Analyzes image characteristics to select optimal thresholding parameters
        for maximum text clarity and OCR accuracy.
        
        Args:
            image: Input image for thresholding
            
        Returns:
            np.ndarray: Binary image optimized for text recognition
        """
        try:
            # Ensure grayscale for thresholding
            if len(image.shape) == 3:
                gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
            else:
                gray = image.copy()
            
            # Analyze image characteristics for optimal thresholding
            mean_intensity = np.mean(gray)
            std_intensity = np.std(gray)
            
            # Select thresholding method based on image characteristics
            if std_intensity < 30:  # Low contrast image
                return self._apply_low_contrast_threshold(gray, mean_intensity)
            elif std_intensity > 80:  # High contrast image
                return self._apply_high_contrast_threshold(gray)
            else:  # Normal contrast image
                return self._apply_standard_adaptive_threshold(gray)
                
        except Exception as e:
            self.logger.error(f"Adaptive thresholding failed: {e}")
            # Fallback to simple threshold
            if len(image.shape) == 3:
                gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
            else:
                gray = image
            _, binary = cv2.threshold(gray, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)
            return binary
    
    def _apply_low_contrast_threshold(self, gray: np.ndarray, mean_intensity: float) -> np.ndarray:
        """Apply thresholding optimized for low contrast images."""
        # Use CLAHE to enhance contrast first
        clahe = cv2.createCLAHE(clipLimit=3.0, tileGridSize=(8, 8))
        enhanced = clahe.apply(gray)
        
        # Apply adaptive threshold with adjusted parameters
        block_size = max(self._current_profile.block_size + 4, 15)  # Larger block for low contrast
        c_constant = self._current_profile.c_constant + 2  # Higher constant for better separation
        
        return cv2.adaptiveThreshold(
            enhanced,
            255,
            cv2.ADAPTIVE_THRESH_GAUSSIAN_C,
            cv2.THRESH_BINARY,
            block_size,
            c_constant
        )
    
    def _apply_high_contrast_threshold(self, gray: np.ndarray) -> np.ndarray:
        """Apply thresholding optimized for high contrast images."""
        # For high contrast, Otsu's method often works well
        _, otsu_binary = cv2.threshold(gray, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)
        
        # Also try adaptive threshold with smaller block size
        block_size = max(self._current_profile.block_size - 2, 7)  # Smaller block for high contrast
        adaptive_binary = cv2.adaptiveThreshold(
            gray,
            255,
            cv2.ADAPTIVE_THRESH_MEAN_C,
            cv2.THRESH_BINARY,
            block_size,
            self._current_profile.c_constant
        )
        
        # Combine both methods using bitwise operations for best result
        combined = cv2.bitwise_and(otsu_binary, adaptive_binary)
        
        # If combined result is too sparse, use the better individual result
        white_pixels_combined = np.sum(combined == 255)
        white_pixels_otsu = np.sum(otsu_binary == 255)
        
        if white_pixels_combined < white_pixels_otsu * 0.3:  # Too much lost
            return otsu_binary
        else:
            return combined
    
    def _apply_standard_adaptive_threshold(self, gray: np.ndarray) -> np.ndarray:
        """Apply standard adaptive thresholding for normal contrast images."""
        # Try both Gaussian and Mean adaptive methods
        gaussian_binary = cv2.adaptiveThreshold(
            gray,
            255,
            cv2.ADAPTIVE_THRESH_GAUSSIAN_C,
            cv2.THRESH_BINARY,
            self._current_profile.block_size,
            self._current_profile.c_constant
        )
        
        mean_binary = cv2.adaptiveThreshold(
            gray,
            255,
            cv2.ADAPTIVE_THRESH_MEAN_C,
            cv2.THRESH_BINARY,
            self._current_profile.block_size,
            self._current_profile.c_constant
        )
        
        # Select the method that produces more reasonable text-like regions
        gaussian_score = self._evaluate_threshold_quality(gaussian_binary)
        mean_score = self._evaluate_threshold_quality(mean_binary)
        
        return gaussian_binary if gaussian_score >= mean_score else mean_binary
    
    def _evaluate_threshold_quality(self, binary_image: np.ndarray) -> float:
        """
        Evaluate the quality of a thresholded image for text recognition.
        
        Args:
            binary_image: Binary thresholded image
            
        Returns:
            float: Quality score (higher is better)
        """
        try:
            # Find connected components
            num_labels, labels, stats, centroids = cv2.connectedComponentsWithStats(
                binary_image, connectivity=8
            )
            
            if num_labels <= 1:  # No foreground objects
                return 0.0
            
            # Analyze component characteristics
            areas = stats[1:, cv2.CC_STAT_AREA]  # Skip background
            widths = stats[1:, cv2.CC_STAT_WIDTH]
            heights = stats[1:, cv2.CC_STAT_HEIGHT]
            
            # Calculate quality metrics
            # 1. Reasonable component sizes (not too small or too large)
            reasonable_sizes = np.sum((areas >= 20) & (areas <= binary_image.size * 0.1))
            
            # 2. Text-like aspect ratios
            aspect_ratios = widths / np.maximum(heights, 1)
            reasonable_aspects = np.sum((aspect_ratios >= 0.1) & (aspect_ratios <= 10))
            
            # 3. Good distribution of component sizes
            size_variance = np.var(areas) if len(areas) > 1 else 0
            
            # Combine metrics into quality score
            quality_score = (
                reasonable_sizes * 0.4 +
                reasonable_aspects * 0.4 +
                min(size_variance / 1000, 10) * 0.2
            )
            
            return quality_score
            
        except Exception:
            return 0.0
    
    def _apply_filter(self, image: np.ndarray, filter_type: FilterType) -> np.ndarray:
        """Apply specific filter to image."""
        if filter_type == FilterType.GAUSSIAN_BLUR:
            return cv2.GaussianBlur(image, (5, 5), 0)
        
        elif filter_type == FilterType.BILATERAL:
            return cv2.bilateralFilter(image, 9, 75, 75)
        
        elif filter_type == FilterType.MEDIAN:
            return cv2.medianBlur(image, 5)
        
        elif filter_type == FilterType.SHARPEN:
            kernel = np.array([[-1, -1, -1], [-1, 9, -1], [-1, -1, -1]])
            return cv2.filter2D(image, -1, kernel)
        
        elif filter_type == FilterType.DENOISE:
            return self._apply_denoising(image)
        
        elif filter_type == FilterType.CONTRAST_ENHANCE:
            # Apply CLAHE (Contrast Limited Adaptive Histogram Equalization)
            if len(image.shape) == 2:
                clahe = cv2.createCLAHE(clipLimit=2.0, tileGridSize=(8, 8))
                return clahe.apply(image)
            else:
                # Convert to LAB color space for better contrast enhancement
                lab = cv2.cvtColor(image, cv2.COLOR_BGR2LAB)
                clahe = cv2.createCLAHE(clipLimit=2.0, tileGridSize=(8, 8))
                lab[:, :, 0] = clahe.apply(lab[:, :, 0])
                return cv2.cvtColor(lab, cv2.COLOR_LAB2BGR)
        
        else:
            return image
    
    def _detect_text_regions(self, frame: Frame) -> List[Rectangle]:
        """
        Detect text regions using advanced computer vision methods.
        
        Implements comprehensive edge detection, text area identification,
        and heuristic-based text region detection for optimal OCR accuracy.
        
        Args:
            frame: Input frame for text region detection
            
        Returns:
            List[Rectangle]: List of detected text regions optimized for OCR
        """
        try:
            # Convert to grayscale if needed
            if len(frame.data.shape) == 3:
                gray = cv2.cvtColor(frame.data, cv2.COLOR_BGR2GRAY)
            else:
                gray = frame.data.copy()
            
            # Apply preprocessing for better edge detection
            preprocessed = self._preprocess_for_edge_detection(gray)
            
            # Multi-scale edge detection for robust text detection
            text_regions = self._detect_text_regions_multiscale(preprocessed)
            
            # Apply heuristic-based filtering and optimization
            optimized_regions = self._apply_text_region_heuristics(text_regions, gray)
            
            # Optimize ROI regions for OCR accuracy
            final_regions = self._optimize_rois_for_ocr(optimized_regions, gray)
            
            # Sort by confidence score and limit count
            final_regions.sort(key=lambda r: getattr(r, 'confidence', r.area), reverse=True)
            return final_regions[:self._current_profile.roi_max_count]
            
        except Exception as e:
            self.logger.error(f"Advanced ROI detection failed: {e}")
            return [Rectangle(0, 0, frame.width, frame.height)]
    
    def _preprocess_for_edge_detection(self, gray: np.ndarray) -> np.ndarray:
        """
        Preprocess image for optimal edge detection.
        
        Args:
            gray: Grayscale input image
            
        Returns:
            np.ndarray: Preprocessed image optimized for edge detection
        """
        try:
            # Apply light denoising to reduce noise artifacts
            denoised = cv2.bilateralFilter(gray, 5, 50, 50)
            
            # Enhance contrast for better edge detection
            clahe = cv2.createCLAHE(clipLimit=2.0, tileGridSize=(8, 8))
            enhanced = clahe.apply(denoised)
            
            # Apply slight Gaussian blur to smooth minor variations
            smoothed = cv2.GaussianBlur(enhanced, (3, 3), 0.5)
            
            return smoothed
            
        except Exception as e:
            self.logger.error(f"Edge detection preprocessing failed: {e}")
            return gray
    
    def _detect_text_regions_multiscale(self, preprocessed: np.ndarray) -> List[Rectangle]:
        """
        Detect text regions using multi-scale edge detection approach.
        
        Args:
            preprocessed: Preprocessed grayscale image
            
        Returns:
            List[Rectangle]: Initial text region candidates
        """
        try:
            all_regions = []
            
            # Multi-scale Canny edge detection
            scales = [(50, 150), (30, 100), (70, 200)]  # Different threshold pairs
            
            for low_thresh, high_thresh in scales:
                # Apply Canny edge detection
                edges = cv2.Canny(preprocessed, low_thresh, high_thresh, apertureSize=3)
                
                # Morphological operations to connect text components
                kernel_horizontal = cv2.getStructuringElement(cv2.MORPH_RECT, (9, 1))
                kernel_vertical = cv2.getStructuringElement(cv2.MORPH_RECT, (1, 9))
                
                # Connect horizontal text components
                horizontal_connected = cv2.morphologyEx(edges, cv2.MORPH_CLOSE, kernel_horizontal)
                
                # Connect vertical text components (for vertical text)
                vertical_connected = cv2.morphologyEx(edges, cv2.MORPH_CLOSE, kernel_vertical)
                
                # Combine both orientations
                combined_edges = cv2.bitwise_or(horizontal_connected, vertical_connected)
                
                # Find contours
                contours, _ = cv2.findContours(combined_edges, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
                
                # Extract bounding rectangles
                for contour in contours:
                    x, y, w, h = cv2.boundingRect(contour)
                    area = w * h
                    
                    # Basic size filtering
                    if (area >= self._current_profile.roi_min_area and
                        w >= 8 and h >= 8):
                        
                        region = Rectangle(x, y, w, h)
                        region.confidence = self._calculate_initial_confidence(contour, area)
                        all_regions.append(region)
            
            # Remove duplicate regions using non-maximum suppression
            return self._apply_non_maximum_suppression(all_regions)
            
        except Exception as e:
            self.logger.error(f"Multi-scale text detection failed: {e}")
            return []
    
    def _calculate_initial_confidence(self, contour: np.ndarray, area: int) -> float:
        """
        Calculate initial confidence score for a text region candidate.
        
        Args:
            contour: Contour points
            area: Contour area
            
        Returns:
            float: Initial confidence score (0.0 to 1.0)
        """
        try:
            # Calculate contour properties
            perimeter = cv2.arcLength(contour, True)
            
            # Aspect ratio analysis
            x, y, w, h = cv2.boundingRect(contour)
            aspect_ratio = w / max(h, 1)
            
            # Solidity (area / convex hull area)
            hull = cv2.convexHull(contour)
            hull_area = cv2.contourArea(hull)
            solidity = area / max(hull_area, 1)
            
            # Extent (area / bounding rectangle area)
            extent = area / max(w * h, 1)
            
            # Calculate confidence based on text-like characteristics
            confidence = 0.0
            
            # Aspect ratio score (text typically has reasonable aspect ratios)
            if 0.1 <= aspect_ratio <= 20:
                if 0.5 <= aspect_ratio <= 8:
                    confidence += 0.3  # Optimal range
                else:
                    confidence += 0.15  # Acceptable range
            
            # Solidity score (text regions should be reasonably solid)
            if solidity >= 0.3:
                confidence += 0.25
            
            # Extent score (text should fill reasonable portion of bounding box)
            if extent >= 0.2:
                confidence += 0.25
            
            # Size score (prefer medium-sized regions)
            if 100 <= area <= 10000:
                confidence += 0.2
            elif area > 10000:
                confidence += 0.1
            
            return min(confidence, 1.0)
            
        except Exception:
            return 0.5  # Default confidence
    
    def _apply_non_maximum_suppression(self, regions: List[Rectangle]) -> List[Rectangle]:
        """
        Apply non-maximum suppression to remove overlapping regions.
        
        Args:
            regions: List of region candidates
            
        Returns:
            List[Rectangle]: Filtered regions with overlaps removed
        """
        if not regions:
            return []
        
        try:
            # Sort by confidence score (highest first)
            regions.sort(key=lambda r: getattr(r, 'confidence', 0.5), reverse=True)
            
            suppressed = []
            
            for i, region in enumerate(regions):
                # Check if this region overlaps significantly with any already selected region
                should_suppress = False
                
                for selected_region in suppressed:
                    overlap_ratio = self._calculate_overlap_ratio(region, selected_region)
                    
                    # Suppress if overlap is too high
                    if overlap_ratio > 0.5:
                        should_suppress = True
                        break
                
                if not should_suppress:
                    suppressed.append(region)
            
            return suppressed
            
        except Exception as e:
            self.logger.error(f"Non-maximum suppression failed: {e}")
            return regions
    
    def _calculate_overlap_ratio(self, rect1: Rectangle, rect2: Rectangle) -> float:
        """
        Calculate overlap ratio between two rectangles.
        
        Args:
            rect1: First rectangle
            rect2: Second rectangle
            
        Returns:
            float: Overlap ratio (0.0 to 1.0)
        """
        try:
            # Calculate intersection
            x1 = max(rect1.x, rect2.x)
            y1 = max(rect1.y, rect2.y)
            x2 = min(rect1.x + rect1.width, rect2.x + rect2.width)
            y2 = min(rect1.y + rect1.height, rect2.y + rect2.height)
            
            if x2 <= x1 or y2 <= y1:
                return 0.0  # No intersection
            
            intersection_area = (x2 - x1) * (y2 - y1)
            
            # Calculate union
            area1 = rect1.width * rect1.height
            area2 = rect2.width * rect2.height
            union_area = area1 + area2 - intersection_area
            
            return intersection_area / max(union_area, 1)
            
        except Exception:
            return 0.0
    
    def _apply_text_region_heuristics(self, regions: List[Rectangle], gray: np.ndarray) -> List[Rectangle]:
        """
        Apply heuristic-based filtering to improve text region detection.
        
        Uses domain knowledge about text characteristics to filter and refine regions.
        
        Args:
            regions: Initial region candidates
            gray: Grayscale image for analysis
            
        Returns:
            List[Rectangle]: Refined text regions
        """
        try:
            refined_regions = []
            
            for region in regions:
                # Extract region from image
                roi = gray[region.y:region.y + region.height, 
                          region.x:region.x + region.width]
                
                if roi.size == 0:
                    continue
                
                # Apply text-specific heuristics
                heuristic_score = self._calculate_text_heuristic_score(roi, region)
                
                # Update confidence based on heuristics
                original_confidence = getattr(region, 'confidence', 0.5)
                region.confidence = (original_confidence + heuristic_score) / 2
                
                # Only keep regions with reasonable confidence
                if region.confidence >= 0.3:
                    refined_regions.append(region)
            
            return refined_regions
            
        except Exception as e:
            self.logger.error(f"Text region heuristics failed: {e}")
            return regions
    
    def _calculate_text_heuristic_score(self, roi: np.ndarray, region: Rectangle) -> float:
        """
        Calculate heuristic score based on text-like characteristics.
        
        Args:
            roi: Region of interest image data
            region: Region rectangle information
            
        Returns:
            float: Heuristic score (0.0 to 1.0)
        """
        try:
            score = 0.0
            
            # 1. Intensity variation analysis (text has good contrast)
            intensity_std = np.std(roi)
            if intensity_std > 20:  # Good contrast
                score += 0.25
            elif intensity_std > 10:  # Moderate contrast
                score += 0.15
            
            # 2. Edge density analysis (text has many edges)
            edges = cv2.Canny(roi, 50, 150)
            edge_density = np.sum(edges > 0) / roi.size
            
            if edge_density > 0.1:  # High edge density
                score += 0.25
            elif edge_density > 0.05:  # Moderate edge density
                score += 0.15
            
            # 3. Horizontal line analysis (text often has horizontal structure)
            horizontal_kernel = cv2.getStructuringElement(cv2.MORPH_RECT, (min(roi.shape[1] // 4, 15), 1))
            horizontal_lines = cv2.morphologyEx(edges, cv2.MORPH_OPEN, horizontal_kernel)
            horizontal_density = np.sum(horizontal_lines > 0) / roi.size
            
            if horizontal_density > 0.02:
                score += 0.2
            
            # 4. Aspect ratio refinement
            aspect_ratio = region.width / max(region.height, 1)
            if 1.0 <= aspect_ratio <= 6.0:  # Typical text line ratios
                score += 0.15
            elif 0.3 <= aspect_ratio <= 15.0:  # Acceptable range
                score += 0.1
            
            # 5. Size appropriateness for text
            area = region.width * region.height
            if 200 <= area <= 5000:  # Optimal text size range
                score += 0.15
            elif 50 <= area <= 15000:  # Acceptable range
                score += 0.1
            
            return min(score, 1.0)
            
        except Exception as e:
            self.logger.error(f"Heuristic score calculation failed: {e}")
            return 0.5
    
    def _optimize_rois_for_ocr(self, regions: List[Rectangle], gray: np.ndarray) -> List[Rectangle]:
        """
        Optimize ROI regions specifically for OCR accuracy.
        
        Applies OCR-specific optimizations like padding, alignment, and merging.
        
        Args:
            regions: Input text regions
            gray: Grayscale image for analysis
            
        Returns:
            List[Rectangle]: OCR-optimized regions
        """
        try:
            optimized_regions = []
            
            for region in regions:
                # Add padding for better OCR results
                padded_region = self._add_ocr_padding(region, gray.shape)
                
                # Align to text baselines if possible
                aligned_region = self._align_to_text_baseline(padded_region, gray)
                
                # Validate region quality for OCR
                if self._validate_ocr_region_quality(aligned_region, gray):
                    optimized_regions.append(aligned_region)
            
            # Merge nearby regions that likely belong to the same text block
            merged_regions = self._merge_nearby_text_regions(optimized_regions)
            
            return merged_regions
            
        except Exception as e:
            self.logger.error(f"ROI OCR optimization failed: {e}")
            return regions
    
    def _add_ocr_padding(self, region: Rectangle, image_shape: Tuple[int, int]) -> Rectangle:
        """
        Add appropriate padding around text region for better OCR results.
        
        Args:
            region: Original text region
            image_shape: Shape of the source image (height, width)
            
        Returns:
            Rectangle: Padded region
        """
        try:
            # Calculate padding based on region size
            padding_x = max(2, region.width // 20)  # 5% padding or minimum 2 pixels
            padding_y = max(2, region.height // 20)
            
            # Apply padding while staying within image bounds
            new_x = max(0, region.x - padding_x)
            new_y = max(0, region.y - padding_y)
            new_width = min(image_shape[1] - new_x, region.width + 2 * padding_x)
            new_height = min(image_shape[0] - new_y, region.height + 2 * padding_y)
            
            padded_region = Rectangle(new_x, new_y, new_width, new_height)
            padded_region.confidence = getattr(region, 'confidence', 0.5)
            
            return padded_region
            
        except Exception:
            return region
    
    def _align_to_text_baseline(self, region: Rectangle, gray: np.ndarray) -> Rectangle:
        """
        Attempt to align region to text baseline for better OCR accuracy.
        
        Args:
            region: Input region
            gray: Grayscale image
            
        Returns:
            Rectangle: Baseline-aligned region
        """
        try:
            # Extract ROI
            roi = gray[region.y:region.y + region.height, 
                      region.x:region.x + region.width]
            
            if roi.size == 0:
                return region
            
            # Find horizontal projection to detect text baseline
            horizontal_projection = np.sum(roi < 128, axis=1)  # Count dark pixels per row
            
            if len(horizontal_projection) == 0:
                return region
            
            # Find the main text area (rows with significant dark pixels)
            threshold = np.max(horizontal_projection) * 0.3
            text_rows = np.where(horizontal_projection >= threshold)[0]
            
            if len(text_rows) == 0:
                return region
            
            # Adjust region to focus on main text area
            top_row = text_rows[0]
            bottom_row = text_rows[-1]
            
            # Add small margin
            margin = max(1, (bottom_row - top_row) // 10)
            top_row = max(0, top_row - margin)
            bottom_row = min(roi.shape[0] - 1, bottom_row + margin)
            
            # Create aligned region
            aligned_region = Rectangle(
                region.x,
                region.y + top_row,
                region.width,
                bottom_row - top_row + 1
            )
            aligned_region.confidence = getattr(region, 'confidence', 0.5)
            
            return aligned_region
            
        except Exception:
            return region
    
    def _validate_ocr_region_quality(self, region: Rectangle, gray: np.ndarray) -> bool:
        """
        Validate if a region is suitable for OCR processing.
        
        Args:
            region: Region to validate
            gray: Grayscale image
            
        Returns:
            bool: True if region is suitable for OCR
        """
        try:
            # Check minimum size requirements
            if region.width < 8 or region.height < 8:
                return False
            
            # Check maximum size (avoid processing entire image)
            max_area = gray.shape[0] * gray.shape[1] * 0.5  # Max 50% of image
            if region.width * region.height > max_area:
                return False
            
            # Extract ROI for quality analysis
            roi = gray[region.y:region.y + region.height, 
                      region.x:region.x + region.width]
            
            if roi.size == 0:
                return False
            
            # Check if region has sufficient contrast
            intensity_range = np.max(roi) - np.min(roi)
            if intensity_range < 30:  # Too low contrast
                return False
            
            # Check if region is not mostly uniform (likely background)
            intensity_std = np.std(roi)
            if intensity_std < 10:  # Too uniform
                return False
            
            return True
            
        except Exception:
            return False
    
    def _merge_nearby_text_regions(self, regions: List[Rectangle]) -> List[Rectangle]:
        """
        Merge nearby text regions that likely belong to the same text block.
        
        Args:
            regions: List of text regions
            
        Returns:
            List[Rectangle]: Merged regions
        """
        try:
            if len(regions) <= 1:
                return regions
            
            merged_regions = []
            used_indices = set()
            
            for i, region1 in enumerate(regions):
                if i in used_indices:
                    continue
                
                # Start with current region
                merged_region = Rectangle(region1.x, region1.y, region1.width, region1.height)
                merged_region.confidence = getattr(region1, 'confidence', 0.5)
                merged_indices = {i}
                
                # Check for nearby regions to merge
                for j, region2 in enumerate(regions):
                    if j <= i or j in used_indices:
                        continue
                    
                    # Check if regions should be merged
                    if self._should_merge_regions(merged_region, region2):
                        # Expand merged region to include region2
                        min_x = min(merged_region.x, region2.x)
                        min_y = min(merged_region.y, region2.y)
                        max_x = max(merged_region.x + merged_region.width, region2.x + region2.width)
                        max_y = max(merged_region.y + merged_region.height, region2.y + region2.height)
                        
                        merged_region.x = min_x
                        merged_region.y = min_y
                        merged_region.width = max_x - min_x
                        merged_region.height = max_y - min_y
                        
                        # Update confidence (average of merged regions)
                        region2_confidence = getattr(region2, 'confidence', 0.5)
                        merged_region.confidence = (merged_region.confidence + region2_confidence) / 2
                        
                        merged_indices.add(j)
                
                # Mark all merged indices as used
                used_indices.update(merged_indices)
                merged_regions.append(merged_region)
            
            return merged_regions
            
        except Exception as e:
            self.logger.error(f"Region merging failed: {e}")
            return regions
    
    def _should_merge_regions(self, region1: Rectangle, region2: Rectangle) -> bool:
        """
        Determine if two regions should be merged based on proximity and alignment.
        
        Args:
            region1: First region
            region2: Second region
            
        Returns:
            bool: True if regions should be merged
        """
        try:
            # Calculate distances
            horizontal_gap = self._calculate_horizontal_gap(region1, region2)
            vertical_gap = self._calculate_vertical_gap(region1, region2)
            
            # Calculate size-based thresholds
            avg_height = (region1.height + region2.height) / 2
            avg_width = (region1.width + region2.width) / 2
            
            # Merge if regions are close horizontally and aligned vertically (same text line)
            if (horizontal_gap <= avg_height * 0.5 and  # Close horizontally
                vertical_gap <= avg_height * 0.3):      # Well aligned vertically
                return True
            
            # Merge if regions are close vertically and aligned horizontally (text block)
            if (vertical_gap <= avg_height * 0.8 and    # Close vertically
                horizontal_gap <= avg_width * 0.3):     # Well aligned horizontally
                return True
            
            return False
            
        except Exception:
            return False
    
    def _calculate_horizontal_gap(self, region1: Rectangle, region2: Rectangle) -> float:
        """Calculate horizontal gap between two regions."""
        # Check if regions overlap horizontally
        if (region1.x <= region2.x + region2.width and 
            region2.x <= region1.x + region1.width):
            return 0.0  # Overlapping
        
        # Calculate gap
        if region1.x < region2.x:
            return region2.x - (region1.x + region1.width)
        else:
            return region1.x - (region2.x + region2.width)
    
    def _calculate_vertical_gap(self, region1: Rectangle, region2: Rectangle) -> float:
        """Calculate vertical gap between two regions."""
        # Check if regions overlap vertically
        if (region1.y <= region2.y + region2.height and 
            region2.y <= region1.y + region1.height):
            return 0.0  # Overlapping
        
        # Calculate gap
        if region1.y < region2.y:
            return region2.y - (region1.y + region1.height)
        else:
            return region1.y - (region2.y + region2.height)
    
    def _update_profile_for_performance(self, profile: PerformanceProfile) -> None:
        """Update preprocessing profile based on performance requirements."""
        self._current_profile = PreprocessingProfile.create_for_performance_profile(profile)
        
        # Update frame differencing configuration
        diff_config = DifferenceConfig(
            method=self._current_profile.difference_method,
            sensitivity=self._current_profile.sensitivity_level
        )
        self._frame_differencing.update_config(diff_config)
        
        self.logger.info(f"Preprocessing profile updated for {profile.value} performance")
    
    def _get_current_performance_profile(self) -> PerformanceProfile:
        """Get current performance profile based on configuration."""
        if (self._current_profile.target_width == 640 and 
            self._current_profile.sensitivity_level == SensitivityLevel.LOW):
            return PerformanceProfile.LOW
        elif (self._current_profile.target_width == 1280 and 
              self._current_profile.sensitivity_level == SensitivityLevel.MEDIUM):
            return PerformanceProfile.NORMAL
        else:
            return PerformanceProfile.HIGH
    
    def _update_processing_stats(self, processing_time: float) -> None:
        """Update processing statistics."""
        self._stats['frames_processed'] += 1
        self._stats['total_processing_time'] += processing_time
        
        self._processing_times.append(processing_time)
        if len(self._processing_times) > self._max_history:
            self._processing_times.pop(0)
    
    def configure_frame_differencing(self, config: DifferenceConfig) -> None:
        """
        Configure frame differencing settings.
        
        Args:
            config: Frame differencing configuration
        """
        self._frame_differencing.update_config(config)
        self.logger.info("Frame differencing configuration updated")
    
    def set_frame_differencing_enabled(self, enabled: bool) -> None:
        """
        Enable or disable frame differencing.
        
        Args:
            enabled: Whether to enable frame differencing
        """
        self._current_profile.enable_frame_differencing = enabled
        self._frame_differencing.set_optimization_enabled(enabled)
        self.logger.info(f"Frame differencing {'enabled' if enabled else 'disabled'}")
    
    def set_small_text_enhancement_enabled(self, enabled: bool, denoise: bool = False, binarize: bool = False) -> None:
        """
        Enable or disable small text enhancement.
        
        Args:
            enabled: Whether to enable small text enhancement
            denoise: Whether to enable noise reduction
            binarize: Whether to enable binarization
        """
        if self._small_text_enhancer is None:
            self.logger.warning("Small text enhancer not available")
            return
        
        self._small_text_enhancement_enabled = enabled
        
        # Configure the enhancer with the options
        if enabled and self._small_text_enhancer:
            self._small_text_enhancer.denoise = denoise
            self._small_text_enhancer.binarize = binarize
            self.logger.info(f"Small text enhancement enabled (denoise={denoise}, binarize={binarize})")
        else:
            self.logger.info("Small text enhancement disabled")
    
    def configure_small_text_enhancement(self, scale_factor: float = 2.0, 
                                        sharpen_strength: float = 1.5,
                                        contrast_enhancement: bool = True,
                                        denoise: bool = True) -> None:
        """
        Configure small text enhancement parameters.
        
        Args:
            scale_factor: Upscaling factor (1.5-3.0 recommended)
            sharpen_strength: Sharpening strength (0.5-2.0)
            contrast_enhancement: Enable contrast enhancement
            denoise: Enable denoising
        """
        if self._small_text_enhancer is None:
            self.logger.warning("Small text enhancer not available")
            return
        
        self._small_text_enhancer.configure(
            scale_factor=scale_factor,
            sharpen_strength=sharpen_strength,
            contrast_enhancement=contrast_enhancement,
            denoise=denoise
        )
        self.logger.info(f"Small text enhancement configured: scale={scale_factor}x")
    
    def get_preprocessing_statistics(self) -> Dict[str, Any]:
        """
        Get comprehensive preprocessing statistics.
        
        Returns:
            Dict[str, Any]: Preprocessing statistics
        """
        avg_processing_time = (self._stats['total_processing_time'] / 
                             self._stats['frames_processed'] 
                             if self._stats['frames_processed'] > 0 else 0)
        
        stats = {
            **self._stats,
            'average_processing_time': avg_processing_time,
            'current_profile': self._get_current_performance_profile().value,
            'frame_differencing_enabled': self._current_profile.enable_frame_differencing,
            'roi_detection_enabled': self._current_profile.enable_roi_detection,
            'frame_differencing_stats': self._frame_differencing.get_system_statistics()
        }
        
        if self._processing_times:
            stats.update({
                'recent_avg_processing_time': np.mean(self._processing_times),
                'min_processing_time': np.min(self._processing_times),
                'max_processing_time': np.max(self._processing_times)
            })
        
        return stats
    
    def reset_statistics(self) -> None:
        """Reset all statistics."""
        self._stats = {
            'frames_processed': 0,
            'total_processing_time': 0.0,
            'roi_optimizations': 0,
            'frame_differences_calculated': 0
        }
        self._processing_times.clear()
        self._frame_differencing.reset_system()
        self.logger.info("Preprocessing statistics reset")
    
    def update_preprocessing_profile(self, profile: PreprocessingProfile) -> None:
        """
        Update the current preprocessing profile.
        
        Args:
            profile: New preprocessing profile to use
        """
        self._current_profile = profile
        
        # Update frame differencing configuration
        if hasattr(profile, 'difference_method') and hasattr(profile, 'sensitivity_level'):
            diff_config = DifferenceConfig(
                method=profile.difference_method,
                sensitivity=profile.sensitivity_level
            )
            self._frame_differencing.update_config(diff_config)
        
        self.logger.info(f"Preprocessing profile updated for {profile.content_type} content")
    
    def get_preprocessing_profile(self) -> PreprocessingProfile:
        """
        Get the current preprocessing profile.
        
        Returns:
            PreprocessingProfile: Current preprocessing configuration
        """
        return self._current_profile
    
    def benchmark_preprocessing_methods(self, test_frame: Frame) -> Dict[str, float]:
        """
        Benchmark different preprocessing methods on a test frame.
        
        Args:
            test_frame: Frame to use for benchmarking
            
        Returns:
            Dict[str, float]: Benchmark results with method names and processing times
        """
        benchmark_results = {}
        
        try:
            # Test different grayscale methods
            grayscale_methods = ["weighted", "average", "luminance", "desaturate", "max_channel", "adaptive"]
            for method in grayscale_methods:
                start_time = time.time()
                original_method = self._current_profile.grayscale_method
                self._current_profile.grayscale_method = method
                
                if len(test_frame.data.shape) == 3:
                    self._convert_to_grayscale(test_frame.data)
                
                self._current_profile.grayscale_method = original_method
                benchmark_results[f"grayscale_{method}"] = (time.time() - start_time) * 1000
            
            # Test different denoising strengths
            denoise_strengths = [1.0, 3.0, 5.0, 7.0]
            for strength in denoise_strengths:
                start_time = time.time()
                original_strength = self._current_profile.denoise_strength
                self._current_profile.denoise_strength = strength
                
                self._apply_denoising(test_frame.data)
                
                self._current_profile.denoise_strength = original_strength
                benchmark_results[f"denoise_strength_{strength}"] = (time.time() - start_time) * 1000
            
            # Test different threshold block sizes
            block_sizes = [7, 11, 15, 19]
            for block_size in block_sizes:
                start_time = time.time()
                original_block_size = self._current_profile.block_size
                self._current_profile.block_size = block_size
                
                gray_data = test_frame.data
                if len(gray_data.shape) == 3:
                    gray_data = cv2.cvtColor(gray_data, cv2.COLOR_BGR2GRAY)
                self._apply_adaptive_threshold(gray_data)
                
                self._current_profile.block_size = original_block_size
                benchmark_results[f"threshold_block_{block_size}"] = (time.time() - start_time) * 1000
            
            return benchmark_results
            
        except Exception as e:
            self.logger.error(f"Benchmarking failed: {e}")
            return {}
    
    def optimize_for_frame(self, frame: Frame) -> PreprocessingProfile:
        """
        Analyze a frame and suggest optimal preprocessing settings.
        
        Args:
            frame: Frame to analyze for optimization
            
        Returns:
            PreprocessingProfile: Optimized profile for the frame
        """
        try:
            # Analyze frame characteristics
            analysis = self._analyze_frame_characteristics(frame)
            
            # Create optimized profile based on analysis
            optimized_profile = PreprocessingProfile.create_for_performance_profile(
                PerformanceProfile.NORMAL,
                analysis.get('suggested_content_type', 'mixed')
            )
            
            # Adjust settings based on analysis
            if analysis.get('is_low_contrast', False):
                optimized_profile.enable_contrast_enhancement = True
                optimized_profile.c_constant = 4.0
            
            if analysis.get('is_noisy', False):
                optimized_profile.denoise_strength = min(optimized_profile.denoise_strength * 1.5, 8.0)
            
            if analysis.get('has_small_text', False):
                optimized_profile.enable_sharpening = True
                optimized_profile.block_size = max(optimized_profile.block_size - 2, 7)
            
            return optimized_profile
            
        except Exception as e:
            self.logger.error(f"Frame optimization failed: {e}")
            return self._current_profile
    
    def _analyze_frame_characteristics(self, frame: Frame) -> Dict[str, Any]:
        """
        Analyze frame characteristics to determine optimal preprocessing settings.
        
        Args:
            frame: Frame to analyze
            
        Returns:
            Dict[str, Any]: Analysis results
        """
        try:
            # Convert to grayscale for analysis
            if len(frame.data.shape) == 3:
                gray = cv2.cvtColor(frame.data, cv2.COLOR_BGR2GRAY)
            else:
                gray = frame.data
            
            # Calculate basic statistics
            mean_intensity = np.mean(gray)
            std_intensity = np.std(gray)
            
            # Analyze contrast
            is_low_contrast = std_intensity < 30
            is_high_contrast = std_intensity > 80
            
            # Estimate noise level
            noise_level = self._estimate_noise_level(frame.data)
            is_noisy = noise_level > 15
            
            # Detect text-like regions
            edges = cv2.Canny(gray, 50, 150)
            contours, _ = cv2.findContours(edges, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
            
            # Analyze contour characteristics
            small_contours = 0
            text_like_contours = 0
            
            for contour in contours:
                x, y, w, h = cv2.boundingRect(contour)
                area = w * h
                
                if area < 100:
                    small_contours += 1
                
                if 0.1 <= h/max(w, 1) <= 10 and area >= 20:
                    text_like_contours += 1
            
            # Determine content type
            if text_like_contours > len(contours) * 0.6:
                suggested_content_type = "text"
            elif small_contours > len(contours) * 0.7:
                suggested_content_type = "graphics"
            else:
                suggested_content_type = "mixed"
            
            return {
                'mean_intensity': mean_intensity,
                'std_intensity': std_intensity,
                'is_low_contrast': is_low_contrast,
                'is_high_contrast': is_high_contrast,
                'noise_level': noise_level,
                'is_noisy': is_noisy,
                'has_small_text': small_contours > len(contours) * 0.3,
                'text_like_ratio': text_like_contours / max(len(contours), 1),
                'suggested_content_type': suggested_content_type,
                'total_contours': len(contours)
            }
            
        except Exception as e:
            self.logger.error(f"Frame analysis failed: {e}")
            return {'suggested_content_type': 'mixed'}