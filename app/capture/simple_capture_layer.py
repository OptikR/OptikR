"""
Simple Capture Layer - Screenshot-only implementation to avoid DLL conflicts.
"""

import time
import numpy as np
from PIL import ImageGrab
from typing import Optional

try:
    from ..models import Frame, CaptureRegion, Rectangle
    from ..interfaces import CaptureSource
except ImportError:
    # Fallback for direct execution
    from app.models import Frame, CaptureRegion, Rectangle
    from app.interfaces import CaptureSource


class SimpleCaptureLayer:
    """
    Simple screenshot-based capture layer.
    Avoids DirectX to prevent DLL conflicts.
    """
    
    def __init__(self):
        """Initialize simple capture layer."""
        self.frame_rate = 30
        self.last_capture_time = 0
        print("[INFO] Simple capture layer initialized (screenshot mode)")
    
    def capture_frame(self, source: CaptureSource, region: CaptureRegion) -> Optional[Frame]:
        """
        Capture a frame from the specified region.
        
        Args:
            source: Capture source (ignored, always uses screenshot)
            region: Region to capture
            
        Returns:
            Frame object or None if capture fails
        """
        try:
            # Rate limiting
            current_time = time.time()
            min_interval = 1.0 / self.frame_rate
            if current_time - self.last_capture_time < min_interval:
                return None
            
            # Capture screenshot of region
            bbox = (
                region.rectangle.x,
                region.rectangle.y,
                region.rectangle.x + region.rectangle.width,
                region.rectangle.y + region.rectangle.height
            )
            
            screenshot = ImageGrab.grab(bbox=bbox)
            
            # Convert to numpy array (RGB)
            frame_data = np.array(screenshot)
            
            # Create Frame object
            frame = Frame(
                data=frame_data,
                timestamp=current_time,
                source_region=region,
                metadata={'capture_method': 'screenshot'}
            )
            
            self.last_capture_time = current_time
            return frame
            
        except Exception as e:
            print(f"[ERROR] Screenshot capture failed: {e}")
            return None
    
    def configure_capture_rate(self, fps: int) -> bool:
        """
        Configure capture frame rate.
        
        Args:
            fps: Target frames per second
            
        Returns:
            True if successful
        """
        if 1 <= fps <= 120:
            self.frame_rate = fps
            return True
        return False
    
    def is_available(self) -> bool:
        """Check if capture is available."""
        return True
