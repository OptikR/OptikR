"""
Frame Skip Optimizer Plugin
Skips processing of unchanged frames to reduce CPU usage
"""

import hashlib
import numpy as np
from typing import Dict, Any, Optional
from PIL import Image


class FrameSkipOptimizer:
    """Skips unchanged frames to reduce processing"""
    
    def __init__(self, config: Dict[str, Any]):
        self.config = config
        self.threshold = config.get('similarity_threshold', 0.95)
        self.min_skip = config.get('min_skip_frames', 3)
        self.max_skip = config.get('max_skip_frames', 30)
        self.method = config.get('comparison_method', 'hash')
        
        # State
        self.previous_frame = None
        self.previous_hash = None
        self.skip_count = 0
        self.consecutive_skips = 0
        
        # Statistics
        self.total_frames = 0
        self.skipped_frames = 0
        self.processed_frames = 0
    
    def _compute_hash(self, frame: np.ndarray) -> str:
        """Compute perceptual hash of frame"""
        # Resize to small size for fast comparison
        img = Image.fromarray(frame)
        img = img.resize((16, 16), Image.Resampling.LANCZOS)
        img = img.convert('L')  # Grayscale
        
        # Compute hash
        pixels = np.array(img).flatten()
        hash_str = hashlib.md5(pixels.tobytes()).hexdigest()
        return hash_str
    
    def _compute_mse(self, frame1: np.ndarray, frame2: np.ndarray) -> float:
        """Compute Mean Squared Error between frames"""
        # Resize for faster comparison
        img1 = Image.fromarray(frame1).resize((64, 64))
        img2 = Image.fromarray(frame2).resize((64, 64))
        
        arr1 = np.array(img1, dtype=np.float32)
        arr2 = np.array(img2, dtype=np.float32)
        
        mse = np.mean((arr1 - arr2) ** 2)
        
        # Normalize to 0-1 range (lower is more similar)
        max_mse = 255.0 ** 2
        similarity = 1.0 - (mse / max_mse)
        
        return similarity
    
    def _compute_ssim(self, frame1: np.ndarray, frame2: np.ndarray) -> float:
        """Compute Structural Similarity Index (simplified)"""
        # Simplified SSIM for speed
        # Full SSIM requires scipy/skimage
        
        # Use MSE as fallback
        return self._compute_mse(frame1, frame2)
    
    def _is_similar(self, frame: np.ndarray) -> bool:
        """Check if frame is similar to previous frame"""
        if self.previous_frame is None:
            return False
        
        if self.method == 'hash':
            current_hash = self._compute_hash(frame)
            similar = (current_hash == self.previous_hash)
            self.previous_hash = current_hash
            return similar
        
        elif self.method == 'mse':
            similarity = self._compute_mse(frame, self.previous_frame)
            return similarity >= self.threshold
        
        elif self.method == 'ssim':
            similarity = self._compute_ssim(frame, self.previous_frame)
            return similarity >= self.threshold
        
        return False
    
    def process(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """Post-process: Decide if frame should be skipped"""
        self.total_frames += 1
        
        frame = data.get('frame')
        if frame is None:
            return data
        
        # Convert to numpy array if needed
        if isinstance(frame, Image.Image):
            frame = np.array(frame)
        
        # Check similarity
        is_similar = self._is_similar(frame)
        
        # Decide whether to skip
        should_skip = False
        
        if is_similar:
            self.skip_count += 1
            
            # Skip if we've seen enough similar frames
            if self.skip_count >= self.min_skip:
                # But don't skip too many consecutive frames
                if self.consecutive_skips < self.max_skip:
                    should_skip = True
                    self.consecutive_skips += 1
                else:
                    # Force process after max skips
                    self.skip_count = 0
                    self.consecutive_skips = 0
        else:
            # Frame changed - reset counters
            self.skip_count = 0
            self.consecutive_skips = 0
        
        # Update state
        self.previous_frame = frame.copy() if not should_skip else self.previous_frame
        
        # Mark for skipping
        if should_skip:
            data['skip_processing'] = True
            self.skipped_frames += 1
        else:
            data['skip_processing'] = False
            self.processed_frames += 1
        
        return data
    
    def get_stats(self) -> Dict[str, Any]:
        """Get optimizer statistics"""
        skip_rate = (self.skipped_frames / self.total_frames * 100) if self.total_frames > 0 else 0
        
        return {
            'total_frames': self.total_frames,
            'skipped_frames': self.skipped_frames,
            'processed_frames': self.processed_frames,
            'skip_rate': f"{skip_rate:.1f}%",
            'cpu_saved': f"{skip_rate:.0f}%"
        }
    
    def reset(self):
        """Reset optimizer state"""
        self.previous_frame = None
        self.previous_hash = None
        self.skip_count = 0
        self.consecutive_skips = 0
        self.total_frames = 0
        self.skipped_frames = 0
        self.processed_frames = 0


# Plugin interface
def initialize(config: Dict[str, Any]) -> FrameSkipOptimizer:
    """Initialize the optimizer plugin"""
    return FrameSkipOptimizer(config)
