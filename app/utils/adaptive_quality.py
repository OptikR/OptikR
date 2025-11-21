"""
Adaptive Quality Mode - Experimental Feature
Automatically adjust quality based on content complexity.
"""

import numpy as np
from typing import Tuple, Dict
from PIL import Image


class AdaptiveQualityManager:
    """
    Adaptive quality manager that adjusts OCR/translation quality based on content.
    
    Features:
    - Analyzes image complexity
    - Adjusts OCR confidence threshold
    - Adjusts preprocessing intensity
    - Balances quality vs speed
    """
    
    def __init__(self):
        """Initialize adaptive quality manager."""
        self.complexity_history = []
        self.max_history = 10
    
    def analyze_complexity(self, image: np.ndarray) -> Dict[str, float]:
        """
        Analyze image complexity.
        
        Args:
            image: Input image as numpy array
            
        Returns:
            Dictionary with complexity metrics
        """
        # Convert to grayscale if needed
        if len(image.shape) == 3:
            gray = np.mean(image, axis=2).astype(np.uint8)
        else:
            gray = image
        
        # Calculate complexity metrics
        metrics = {}
        
        # 1. Edge density (high edges = complex)
        edges = self._detect_edges(gray)
        metrics['edge_density'] = np.sum(edges > 0) / edges.size
        
        # 2. Contrast (high contrast = easier to read)
        metrics['contrast'] = np.std(gray) / 255.0
        
        # 3. Brightness variance (uniform = simple, varied = complex)
        metrics['brightness_variance'] = np.var(gray) / (255.0 ** 2)
        
        # 4. Text density estimate (more text = more complex)
        metrics['text_density'] = self._estimate_text_density(gray)
        
        # Overall complexity score (0-1, higher = more complex)
        complexity = (
            metrics['edge_density'] * 0.3 +
            (1.0 - metrics['contrast']) * 0.2 +
            metrics['brightness_variance'] * 0.2 +
            metrics['text_density'] * 0.3
        )
        metrics['overall_complexity'] = complexity
        
        # Update history
        self.complexity_history.append(complexity)
        if len(self.complexity_history) > self.max_history:
            self.complexity_history.pop(0)
        
        return metrics
    
    def _detect_edges(self, gray: np.ndarray) -> np.ndarray:
        """Simple edge detection using Sobel-like filter."""
        # Horizontal edges
        kernel_h = np.array([[-1, -2, -1], [0, 0, 0], [1, 2, 1]])
        # Vertical edges
        kernel_v = np.array([[-1, 0, 1], [-2, 0, 2], [-1, 0, 1]])
        
        # Pad image
        padded = np.pad(gray, 1, mode='edge')
        
        # Convolve
        edges_h = np.zeros_like(gray, dtype=float)
        edges_v = np.zeros_like(gray, dtype=float)
        
        for i in range(gray.shape[0]):
            for j in range(gray.shape[1]):
                patch = padded[i:i+3, j:j+3]
                edges_h[i, j] = np.abs(np.sum(patch * kernel_h))
                edges_v[i, j] = np.abs(np.sum(patch * kernel_v))
        
        # Combine
        edges = np.sqrt(edges_h**2 + edges_v**2)
        return edges
    
    def _estimate_text_density(self, gray: np.ndarray) -> float:
        """Estimate text density in image."""
        # Simple heuristic: count transitions from dark to light
        # Text typically has many such transitions
        
        # Binarize
        threshold = np.mean(gray)
        binary = (gray > threshold).astype(int)
        
        # Count horizontal transitions
        h_transitions = np.sum(np.abs(np.diff(binary, axis=1)))
        
        # Count vertical transitions
        v_transitions = np.sum(np.abs(np.diff(binary, axis=0)))
        
        # Normalize by image size
        total_transitions = h_transitions + v_transitions
        max_transitions = binary.size * 2  # Theoretical maximum
        
        density = total_transitions / max_transitions
        return min(density, 1.0)
    
    def get_adaptive_settings(self, image: np.ndarray) -> Dict[str, any]:
        """
        Get adaptive settings based on image complexity.
        
        Args:
            image: Input image
            
        Returns:
            Dictionary with recommended settings
        """
        metrics = self.analyze_complexity(image)
        complexity = metrics['overall_complexity']
        
        # Adjust settings based on complexity
        settings = {}
        
        # OCR confidence threshold (lower for complex images)
        if complexity < 0.3:
            settings['ocr_confidence'] = 0.8  # High confidence for simple images
            settings['quality_mode'] = 'fast'
        elif complexity < 0.6:
            settings['ocr_confidence'] = 0.7  # Medium confidence
            settings['quality_mode'] = 'balanced'
        else:
            settings['ocr_confidence'] = 0.6  # Lower confidence for complex images
            settings['quality_mode'] = 'high_quality'
        
        # Preprocessing intensity
        if complexity < 0.3:
            settings['preprocessing'] = 'minimal'
            settings['denoise_strength'] = 1
            settings['sharpen_strength'] = 1
        elif complexity < 0.6:
            settings['preprocessing'] = 'standard'
            settings['denoise_strength'] = 2
            settings['sharpen_strength'] = 2
        else:
            settings['preprocessing'] = 'aggressive'
            settings['denoise_strength'] = 3
            settings['sharpen_strength'] = 3
        
        # Translation quality (higher for complex text)
        if complexity < 0.4:
            settings['translation_quality'] = 'fast'
        elif complexity < 0.7:
            settings['translation_quality'] = 'balanced'
        else:
            settings['translation_quality'] = 'high'
        
        # Add metrics for debugging
        settings['complexity_metrics'] = metrics
        
        return settings
    
    def get_average_complexity(self) -> float:
        """Get average complexity from recent history."""
        if not self.complexity_history:
            return 0.5  # Default medium complexity
        return np.mean(self.complexity_history)
    
    def should_skip_frame(self, image: np.ndarray, threshold: float = 0.2) -> bool:
        """
        Determine if frame should be skipped based on complexity.
        Very simple frames (low complexity) might not need processing.
        
        Args:
            image: Input image
            threshold: Complexity threshold below which to skip
            
        Returns:
            True if frame should be skipped
        """
        metrics = self.analyze_complexity(image)
        complexity = metrics['overall_complexity']
        
        # Skip very simple frames (likely static/empty)
        return complexity < threshold
