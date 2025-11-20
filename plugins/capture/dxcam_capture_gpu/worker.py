"""
Capture Worker - Subprocess for screen capture.

Runs in separate process, captures frames and sends them back.
"""

import sys
from pathlib import Path

# Add parent directories to path
sys.path.insert(0, str(Path(__file__).parent.parent.parent.parent))

from app.workflow.base.base_worker import BaseWorker

try:
    import dxcam
    import numpy as np
    DXCAM_AVAILABLE = True
except ImportError:
    DXCAM_AVAILABLE = False
    print("[CAPTURE WORKER] Warning: dxcam not available, using fallback", file=sys.stderr)


class CaptureWorker(BaseWorker):
    """Worker for screen capture using DXCam."""
    
    def initialize(self, config: dict) -> bool:
        """Initialize capture system."""
        try:
            # Check runtime mode
            runtime_mode = config.get('runtime_mode', 'auto')
            
            if runtime_mode == 'cpu':
                self.log("CPU-only mode: DXCam disabled (requires GPU/DirectX)")
                self.log("Please use screenshot_capture plugin instead")
                return False
            
            if not DXCAM_AVAILABLE:
                self.log("DXCam not available - library not installed")
                return False
            
            # Try to initialize DXCam
            self.camera = dxcam.create()
            if self.camera is None:
                self.log("DXCam initialization failed - GPU/DirectX not available")
                return False
                
            self.log(f"DXCam capture initialized successfully (runtime_mode: {runtime_mode})")
            return True
            
        except Exception as e:
            self.log(f"Failed to initialize DXCam capture: {e}")
            self.log("Fallback to screenshot_capture recommended")
            return False
    
    def process(self, data: dict) -> dict:
        """
        Capture a frame.
        
        Args:
            data: {'region': CaptureRegion or dict}
            
        Returns:
            {'frame': base64_encoded_frame, 'shape': [h, w, c]}
        """
        try:
            self.log(f"Received data keys: {list(data.keys())}")
            self.log(f"Full data: {data}")
            
            region = data.get('region')
            if not region:
                return {'error': 'No region specified'}
            
            # Extract region coordinates
            if hasattr(region, 'x'):
                # CaptureRegion object
                x, y, w, h = region.x, region.y, region.width, region.height
            else:
                # Dict
                x = region.get('x', 0)
                y = region.get('y', 0)
                w = region.get('width', 800)
                h = region.get('height', 600)
            
            self.log(f"Capturing region: ({x}, {y}, {w}, {h})")
            
            # Capture frame
            frame = self.camera.grab(region=(x, y, x + w, y + h))
            
            if frame is None:
                # Try without region (full screen)
                self.log("Region capture failed, trying full screen")
                frame = self.camera.grab()
                
                if frame is None:
                    return {'error': 'Failed to capture frame (both region and full screen)'}
                
                # Crop to region manually
                frame = frame[y:y+h, x:x+w]
            
            self.log(f"Captured frame shape: {frame.shape}")
            
            # Encode frame as base64
            import base64
            frame_bytes = frame.tobytes()
            frame_b64 = base64.b64encode(frame_bytes).decode('utf-8')
            
            return {
                'frame': frame_b64,
                'shape': list(frame.shape),
                'dtype': str(frame.dtype)
            }
            
        except Exception as e:
            return {'error': f'Capture failed: {e}'}
    
    def cleanup(self):
        """Clean up capture resources."""
        if hasattr(self, 'camera'):
            del self.camera
        self.log("Capture worker shutdown")


if __name__ == '__main__':
    worker = CaptureWorker(name="CaptureWorker")
    worker.run()
