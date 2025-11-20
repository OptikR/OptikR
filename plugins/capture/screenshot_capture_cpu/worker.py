"""
Screenshot Capture Worker - Subprocess for screenshot-based screen capture.

Runs in separate process, captures frames using Win32 GDI/MSS/PIL and sends them back.
This is a fallback method when DirectX capture is unavailable.
"""

import sys
from pathlib import Path

# Add parent directories to path
sys.path.insert(0, str(Path(__file__).parent.parent.parent.parent))

from app.workflow.base.base_worker import BaseWorker

import numpy as np

# Try to import screenshot methods (in order of preference)
SCREENSHOT_METHOD = None

# Method 1: Win32 GDI (fastest - ~11ms)
try:
    import win32gui
    import win32ui
    import win32con
    from ctypes import windll
    SCREENSHOT_METHOD = "win32"
    print("[SCREENSHOT WORKER] Using Win32 GDI method", file=sys.stderr)
except ImportError:
    pass

# Method 2: MSS (fast - ~12ms)
if not SCREENSHOT_METHOD:
    try:
        import mss
        SCREENSHOT_METHOD = "mss"
        print("[SCREENSHOT WORKER] Using MSS method", file=sys.stderr)
    except ImportError:
        pass

# Method 3: PIL ImageGrab (slower - ~15ms)
if not SCREENSHOT_METHOD:
    try:
        from PIL import ImageGrab
        SCREENSHOT_METHOD = "pil"
        print("[SCREENSHOT WORKER] Using PIL ImageGrab method", file=sys.stderr)
    except ImportError:
        pass

if not SCREENSHOT_METHOD:
    print("[SCREENSHOT WORKER] ERROR: No screenshot method available!", file=sys.stderr)


class CaptureWorker(BaseWorker):
    """Worker for screen capture using screenshot methods."""
    
    def initialize(self, config: dict) -> bool:
        """Initialize capture system."""
        try:
            if not SCREENSHOT_METHOD:
                self.log("No screenshot method available")
                return False
            
            self.method = config.get('method', 'auto')
            if self.method == 'auto':
                self.method = SCREENSHOT_METHOD
            
            self.log(f"Screenshot capture initialized (method: {self.method})")
            
            # Initialize MSS if using that method
            if self.method == 'mss':
                import mss
                self.sct = mss.mss()
            
            return True
            
        except Exception as e:
            self.log(f"Failed to initialize capture: {e}")
            return False
    
    def process(self, data: dict) -> dict:
        """
        Capture a frame using screenshot method.
        
        Args:
            data: {'region': CaptureRegion or dict}
            
        Returns:
            {'frame': base64_encoded_frame, 'shape': [h, w, c]}
        """
        try:
            region = data.get('region')
            if not region:
                return {'error': 'No region specified'}
            
            # Extract region coordinates
            if hasattr(region, 'x'):
                x, y, w, h = region.x, region.y, region.width, region.height
            else:
                x = region.get('x', 0)
                y = region.get('y', 0)
                w = region.get('width', 800)
                h = region.get('height', 600)
            
            # Capture frame using selected method
            if self.method == 'win32':
                frame = self._capture_win32(x, y, w, h)
            elif self.method == 'mss':
                frame = self._capture_mss(x, y, w, h)
            elif self.method == 'pil':
                frame = self._capture_pil(x, y, w, h)
            else:
                return {'error': f'Unknown method: {self.method}'}
            
            if frame is None:
                return {'error': 'Failed to capture frame'}
            
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
    
    def _capture_win32(self, x: int, y: int, w: int, h: int) -> np.ndarray:
        """Capture using Win32 GDI."""
        try:
            # Get device contexts
            hdesktop = win32gui.GetDesktopWindow()
            desktop_dc = win32gui.GetWindowDC(hdesktop)
            img_dc = win32ui.CreateDCFromHandle(desktop_dc)
            mem_dc = img_dc.CreateCompatibleDC()
            
            # Create bitmap
            screenshot = win32ui.CreateBitmap()
            screenshot.CreateCompatibleBitmap(img_dc, w, h)
            mem_dc.SelectObject(screenshot)
            
            # Copy screen to bitmap
            mem_dc.BitBlt((0, 0), (w, h), img_dc, (x, y), win32con.SRCCOPY)
            
            # Convert to numpy array
            bmpinfo = screenshot.GetInfo()
            bmpstr = screenshot.GetBitmapBits(True)
            frame = np.frombuffer(bmpstr, dtype=np.uint8)
            frame = frame.reshape((h, w, 4))  # BGRA format
            frame = frame[:, :, :3]  # Remove alpha channel -> BGR
            
            # Cleanup
            mem_dc.DeleteDC()
            win32gui.DeleteObject(screenshot.GetHandle())
            win32gui.ReleaseDC(hdesktop, desktop_dc)
            
            return frame
            
        except Exception as e:
            self.log(f"Win32 capture failed: {e}")
            return None
    
    def _capture_mss(self, x: int, y: int, w: int, h: int) -> np.ndarray:
        """Capture using MSS."""
        try:
            monitor = {"top": y, "left": x, "width": w, "height": h}
            sct_img = self.sct.grab(monitor)
            
            # Convert to numpy array (BGRA -> BGR)
            frame = np.array(sct_img)
            frame = frame[:, :, :3]  # Remove alpha channel
            frame = frame[:, :, ::-1]  # RGB -> BGR
            
            return frame
            
        except Exception as e:
            self.log(f"MSS capture failed: {e}")
            return None
    
    def _capture_pil(self, x: int, y: int, w: int, h: int) -> np.ndarray:
        """Capture using PIL ImageGrab."""
        try:
            from PIL import ImageGrab
            
            bbox = (x, y, x + w, y + h)
            img = ImageGrab.grab(bbox=bbox)
            
            # Convert to numpy array (RGB -> BGR)
            frame = np.array(img)
            frame = frame[:, :, ::-1]  # RGB -> BGR
            
            return frame
            
        except Exception as e:
            self.log(f"PIL capture failed: {e}")
            return None
    
    def cleanup(self):
        """Cleanup resources."""
        if hasattr(self, 'sct'):
            self.sct.close()


if __name__ == "__main__":
    worker = CaptureWorker(name="ScreenshotCaptureWorker")
    worker.run()
