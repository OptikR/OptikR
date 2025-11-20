"""
Small Text Enhancement Module

Enhances captured images to improve OCR accuracy for small text (< 12pt).
Uses upscaling and image processing techniques to make small text more readable.
"""

import numpy as np
import cv2
from typing import Optional, Tuple
import logging

try:
    from ..models import Frame
except ImportError:
    from app.models import Frame


class SmallTextEnhancer:
    """
    Enhances images to improve OCR accuracy for small text.
    
    Techniques used:
    - Image upscaling (2x or 3x)
    - Sharpening
    - Contrast enhancement
    - Noise reduction
    """
    
    def __init__(self, logger: Optional[logging.Logger] = None):
        """
        Initialize small text enhancer.
        
        Args:
            logger: Optional logger for debugging
        """
        self.logger = logger or logging.getLogger(__name__)
        
        # Enhancement settings
        self.scale_factor = 2.0  # Default 2x upscaling
        self.sharpen_strength = 1.5
        self.contrast_enhancement = True
        self.denoise = True
        
        # Performance tracking
        self.enhancements_applied = 0
        
        self.logger.info("Small text enhancer initialized")
    
    def configure(self, scale_factor: float = 2.0, sharpen_strength: float = 1.5,
                  contrast_enhancement: bool = True, denoise: bool = True):
        """
        Configure enhancement parameters.
        
        Args:
            scale_factor: Upscaling factor (1.5-3.0 recommended)
            sharpen_strength: Sharpening strength (0.5-2.0)
            contrast_enhancement: Enable contrast enhancement
            denoise: Enable denoising
        """
        self.scale_factor = max(1.0, min(4.0, scale_factor))
        self.sharpen_strength = max(0.0, min(3.0, sharpen_strength))
        self.contrast_enhancement = contrast_enhancement
        self.denoise = denoise
        
        self.logger.info(f"Enhancer configured: scale={self.scale_factor}x, "
                        f"sharpen={self.sharpen_strength}, "
                        f"contrast={self.contrast_enhancement}, "
                        f"denoise={self.denoise}")
    
    def enhance_frame(self, frame: Frame) -> Frame:
        """
        Enhance a frame for better small text recognition.
        
        Args:
            frame: Input frame to enhance
            
        Returns:
            Enhanced frame
        """
        try:
            enhanced_data = self.enhance_image(frame.data)
            
            # Create new frame with enhanced data
            enhanced_frame = Frame(
                data=enhanced_data,
                timestamp=frame.timestamp,
                source_region=frame.source_region,
                metadata={
                    **frame.metadata,
                    'enhanced_for_small_text': True,
                    'scale_factor': self.scale_factor,
                    'original_size': frame.data.shape[:2]
                }
            )
            
            self.enhancements_applied += 1
            return enhanced_frame
            
        except Exception as e:
            self.logger.error(f"Frame enhancement failed: {e}")
            return frame  # Return original on error
    
    def enhance_image(self, image: np.ndarray) -> np.ndarray:
        """
        Enhance an image for better small text recognition.
        
        Args:
            image: Input image (numpy array)
            
        Returns:
            Enhanced image
        """
        try:
            # Convert to grayscale if needed (better for text)
            if len(image.shape) == 3:
                gray = cv2.cvtColor(image, cv2.COLOR_RGB2GRAY)
            else:
                gray = image.copy()
            
            # Step 1: Denoise (if enabled)
            if self.denoise:
                gray = self._apply_denoising(gray)
            
            # Step 2: Upscale image
            upscaled = self._upscale_image(gray)
            
            # Step 3: Enhance contrast (if enabled)
            if self.contrast_enhancement:
                upscaled = self._enhance_contrast(upscaled)
            
            # Step 4: Sharpen image
            sharpened = self._sharpen_image(upscaled)
            
            # Step 5: Binarization (optional, helps with very small text)
            # enhanced = self._adaptive_threshold(sharpened)
            
            # Convert back to RGB for consistency
            if len(image.shape) == 3:
                enhanced_rgb = cv2.cvtColor(sharpened, cv2.COLOR_GRAY2RGB)
                return enhanced_rgb
            else:
                return sharpened
            
        except Exception as e:
            self.logger.error(f"Image enhancement failed: {e}")
            return image  # Return original on error
    
    def _upscale_image(self, image: np.ndarray) -> np.ndarray:
        """
        Upscale image using high-quality interpolation.
        
        Args:
            image: Input image
            
        Returns:
            Upscaled image
        """
        if self.scale_factor <= 1.0:
            return image
        
        height, width = image.shape[:2]
        new_width = int(width * self.scale_factor)
        new_height = int(height * self.scale_factor)
        
        # Use INTER_CUBIC for upscaling (better quality than INTER_LINEAR)
        upscaled = cv2.resize(image, (new_width, new_height), 
                             interpolation=cv2.INTER_CUBIC)
        
        return upscaled
    
    def _sharpen_image(self, image: np.ndarray) -> np.ndarray:
        """
        Sharpen image to enhance text edges.
        
        Args:
            image: Input image
            
        Returns:
            Sharpened image
        """
        if self.sharpen_strength <= 0:
            return image
        
        # Create sharpening kernel
        kernel = np.array([
            [-1, -1, -1],
            [-1,  9, -1],
            [-1, -1, -1]
        ]) * (self.sharpen_strength / 8.0)
        
        # Apply sharpening
        sharpened = cv2.filter2D(image, -1, kernel)
        
        # Blend with original based on strength
        alpha = min(1.0, self.sharpen_strength)
        result = cv2.addWeighted(sharpened, alpha, image, 1 - alpha, 0)
        
        return result
    
    def _enhance_contrast(self, image: np.ndarray) -> np.ndarray:
        """
        Enhance image contrast using CLAHE (Contrast Limited Adaptive Histogram Equalization).
        
        Args:
            image: Input image
            
        Returns:
            Contrast-enhanced image
        """
        # Create CLAHE object
        clahe = cv2.createCLAHE(clipLimit=2.0, tileGridSize=(8, 8))
        
        # Apply CLAHE
        enhanced = clahe.apply(image)
        
        return enhanced
    
    def _apply_denoising(self, image: np.ndarray) -> np.ndarray:
        """
        Apply denoising to reduce noise while preserving text edges.
        
        Args:
            image: Input image
            
        Returns:
            Denoised image
        """
        # Use fastNlMeansDenoising for grayscale images
        # Parameters: h=10 (filter strength), templateWindowSize=7, searchWindowSize=21
        denoised = cv2.fastNlMeansDenoising(image, None, h=10, 
                                           templateWindowSize=7, 
                                           searchWindowSize=21)
        
        return denoised
    
    def _adaptive_threshold(self, image: np.ndarray) -> np.ndarray:
        """
        Apply adaptive thresholding for binarization.
        Useful for very small or low-contrast text.
        
        Args:
            image: Input image
            
        Returns:
            Binarized image
        """
        # Apply adaptive threshold
        binary = cv2.adaptiveThreshold(
            image, 255, 
            cv2.ADAPTIVE_THRESH_GAUSSIAN_C, 
            cv2.THRESH_BINARY, 
            blockSize=11, 
            C=2
        )
        
        return binary
    
    def estimate_text_size(self, image: np.ndarray) -> Tuple[bool, float]:
        """
        Estimate if image contains small text (< 12pt equivalent).
        
        This is a heuristic based on edge detection and connected components.
        
        Args:
            image: Input image
            
        Returns:
            Tuple of (has_small_text, estimated_avg_height_pixels)
        """
        try:
            # Convert to grayscale if needed
            if len(image.shape) == 3:
                gray = cv2.cvtColor(image, cv2.COLOR_RGB2GRAY)
            else:
                gray = image.copy()
            
            # Apply edge detection
            edges = cv2.Canny(gray, 50, 150)
            
            # Find contours (potential text regions)
            contours, _ = cv2.findContours(edges, cv2.RETR_EXTERNAL, 
                                          cv2.CHAIN_APPROX_SIMPLE)
            
            if not contours:
                return False, 0.0
            
            # Analyze contour heights
            heights = []
            for contour in contours:
                x, y, w, h = cv2.boundingRect(contour)
                # Filter out very small or very large regions
                if 3 <= h <= 100 and w >= 3:
                    heights.append(h)
            
            if not heights:
                return False, 0.0
            
            # Calculate average height
            avg_height = np.median(heights)
            
            # Heuristic: Text < 12pt is typically < 16 pixels at 96 DPI
            # At 2560x1440, small text might be 8-15 pixels high
            has_small_text = avg_height < 16
            
            return has_small_text, float(avg_height)
            
        except Exception as e:
            self.logger.error(f"Text size estimation failed: {e}")
            return False, 0.0
    
    def should_enhance(self, frame: Frame) -> bool:
        """
        Determine if a frame should be enhanced based on text size detection.
        
        Args:
            frame: Input frame
            
        Returns:
            True if enhancement is recommended
        """
        has_small_text, avg_height = self.estimate_text_size(frame.data)
        
        if has_small_text:
            self.logger.debug(f"Small text detected (avg height: {avg_height:.1f}px), "
                            f"enhancement recommended")
        
        return has_small_text
    
    def get_stats(self) -> dict:
        """
        Get enhancement statistics.
        
        Returns:
            Dictionary with statistics
        """
        return {
            'enhancements_applied': self.enhancements_applied,
            'scale_factor': self.scale_factor,
            'sharpen_strength': self.sharpen_strength,
            'contrast_enhancement': self.contrast_enhancement,
            'denoise': self.denoise
        }


# Convenience function for quick enhancement
def enhance_for_small_text(image: np.ndarray, scale_factor: float = 2.0) -> np.ndarray:
    """
    Quick enhancement function for small text.
    
    Args:
        image: Input image
        scale_factor: Upscaling factor
        
    Returns:
        Enhanced image
    """
    enhancer = SmallTextEnhancer()
    enhancer.configure(scale_factor=scale_factor)
    return enhancer.enhance_image(image)
