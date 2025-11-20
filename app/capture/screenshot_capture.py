"""
Fallback Screenshot Capture Implementation

GDI+ based screenshot capture for compatibility when DirectX capture is unavailable.
Provides automatic fallback detection, switching mechanism, and comprehensive error handling.
"""

import logging
import time
import threading
from typing import Optional, List, Dict, Any, Callable, Tuple
from enum import Enum
import numpy as np

try:
    from ..models import Frame, CaptureRegion, Rectangle, CaptureMode, PerformanceProfile
    from ..interfaces import ICaptureLayer, CaptureSource
except ImportError:
    from app.models import Frame, CaptureRegion, Rectangle, CaptureMode, PerformanceProfile
    from app.interfaces import ICaptureLayer, CaptureSource


class ScreenshotMethod(Enum):
    """Available screenshot capture methods."""
    WIN32_GDI = "win32_gdi"
    PIL_IMAGEGRAB = "pil_imagegrab"
    MSS = "mss"
    UNAVAILABLE = "unavailable"


class ScreenshotCaptureError(Exception):
    """Screenshot capture specific exceptions."""
    pass


class ScreenshotMethodDetector:
    """
    Detects and validates available screenshot capture methods.
    
    Tests different screenshot libraries and methods to determine the best
    available option for the current system configuration.
    """
    
    def __init__(self, logger: Optional[logging.Logger] = None):
        """
        Initialize screenshot method detector.
        
        Args:
            logger: Optional logger for debugging
        """
        self.logger = logger or logging.getLogger(__name__)
        self._available_methods: List[ScreenshotMethod] = []
        self._method_performance: Dict[ScreenshotMethod, float] = {}
        
    def detect_available_methods(self) -> List[ScreenshotMethod]:
        """
        Detect all available screenshot methods on the system.
        
        Returns:
            List[ScreenshotMethod]: List of available methods ordered by preference
        """
        self._available_methods.clear()
        self._method_performance.clear()
        
        # ALL SCREENSHOT METHODS DISABLED
        # They conflict with DirectX/Qt initialization
        # Screenshot capture is non-functional but doesn't crash
        pass
        
        if not self._available_methods:
            self.logger.error("No screenshot methods available")
            self._available_methods.append(ScreenshotMethod.UNAVAILABLE)
        else:
            self.logger.info(f"Available screenshot methods: {[m.value for m in self._available_methods]}")
        
        return self._available_methods
    
    def _test_win32_gdi(self) -> bool:
        """
        Test Win32 GDI screenshot method availability and performance.
        
        Returns:
            bool: True if Win32 GDI method is available and functional
        """
        # DISABLED: win32gui import hangs after DirectX initialization
        # This is a Qt/DirectX/Win32 conflict
        self.logger.debug("Win32 GDI disabled (conflicts with DirectX)")
        return False
    
    def _test_pil_imagegrab(self) -> bool:
        """
        Test PIL ImageGrab method availability and performance.
        
        Returns:
            bool: True if PIL ImageGrab method is available and functional
        """
        # PIL ImageGrab can hang when called from background threads with PyQt6
        # Disable it for now - Win32 GDI works fine
        self.logger.debug("PIL ImageGrab disabled for background thread safety")
        return False
    
    def _test_mss(self) -> bool:
        """
        Test MSS (Python MSS) method availability and performance.
        
        Returns:
            bool: True if MSS method is available and functional
        """
        # MSS can also hang when called from background threads
        # Disable it for now - Win32 GDI works reliably
        self.logger.debug("MSS disabled for background thread safety")
        return False
    
    def get_optimal_method(self) -> ScreenshotMethod:
        """
        Get the optimal screenshot method based on availability and performance.
        
        Returns:
            ScreenshotMethod: Best available method
        """
        if not self._available_methods:
            self.detect_available_methods()
        
        if not self._available_methods or self._available_methods[0] == ScreenshotMethod.UNAVAILABLE:
            return ScreenshotMethod.UNAVAILABLE
        
        # Sort by performance (fastest first)
        available_with_perf = [
            method for method in self._available_methods 
            if method in self._method_performance
        ]
        
        if available_with_perf:
            optimal = min(available_with_perf, key=lambda m: self._method_performance[m])
            self.logger.info(f"Optimal screenshot method: {optimal.value} "
                           f"(capture time: {self._method_performance[optimal]:.3f}s)")
            return optimal
        
        # Fallback to first available method
        return self._available_methods[0]
    
    def get_method_performance(self) -> Dict[ScreenshotMethod, float]:
        """
        Get performance metrics for all tested methods.
        
        Returns:
            Dict[ScreenshotMethod, float]: Method performance in seconds
        """
        return self._method_performance.copy()


class FallbackScreenshotCapture:
    """
    Fallback screenshot capture implementation using multiple methods.
    
    Provides robust screenshot capture with automatic method selection,
    fallback switching, and comprehensive error handling.
    """
    
    def __init__(self, logger: Optional[logging.Logger] = None):
        """
        Initialize fallback screenshot capture.
        
        Args:
            logger: Optional logger for debugging
        """
        self.logger = logger or logging.getLogger(__name__)
        
        # Initialize method detector (silent in background thread)
        self._method_detector = ScreenshotMethodDetector(logger)
        self._available_methods = self._method_detector.detect_available_methods()
        self._current_method = self._method_detector.get_optimal_method()
        
        # Capture configuration
        self._frame_rate = 30
        self._performance_profile = PerformanceProfile.NORMAL
        self._capture_quality = 1.0  # Quality scaling factor
        
        # Capture state
        self._current_region: Optional[CaptureRegion] = None
        self._continuous_capture_active = False
        self._capture_thread: Optional[threading.Thread] = None
        self._stop_event = threading.Event()
        self._frame_callbacks: List[Callable[[Frame], None]] = []
        
        # Error handling and fallback
        self._consecutive_failures = 0
        self._max_consecutive_failures = 5
        self._fallback_attempted = False
        
        # Performance monitoring
        self._capture_stats = {
            'total_captures': 0,
            'successful_captures': 0,
            'failed_captures': 0,
            'method_switches': 0,
            'average_capture_time': 0.0,
            'current_fps': 0.0
        }
        
        # Initialize monitor information
        self._monitor_info = self._get_monitor_information()
        
        self.logger.info(f"Fallback screenshot capture initialized with method: {self._current_method.value}")
        self.logger.info(f"Detected {len(self._monitor_info)} monitors")
    
    def is_available(self) -> bool:
        """
        Check if screenshot capture is available.
        
        Returns:
            bool: True if at least one screenshot method is available
        """
        return self._current_method != ScreenshotMethod.UNAVAILABLE
    
    def _get_monitor_information(self) -> List[Dict[str, Any]]:
        """
        Get information about all available monitors.
        
        Returns:
            List[Dict[str, Any]]: List of monitor information dictionaries
        """
        monitors = []
        
        # Skip MSS - it hangs in background threads
        # Skip Win32 API - can also crash in background threads with PyQt6
        # Just use default fallback for background thread safety
        
        # Skip tkinter - can also hang in background threads
        
        # Fallback to default single monitor
        monitors.append({
            'id': 0,
            'left': 0,
            'top': 0,
            'width': 1920,  # Default assumption
            'height': 1080,
            'primary': True,
            'source': 'default'
        })
        
        self.logger.warning("No monitor detection method available, using default single monitor")
        return monitors
    
    def get_monitor_information(self) -> List[Dict[str, Any]]:
        """
        Get information about all available monitors.
        
        Returns:
            List[Dict[str, Any]]: List of monitor information dictionaries
        """
        return self._monitor_info.copy()
    
    def validate_monitor_id(self, monitor_id: int) -> bool:
        """
        Validate if monitor ID is available.
        
        Args:
            monitor_id: Monitor ID to validate
            
        Returns:
            bool: True if monitor ID is valid
        """
        return 0 <= monitor_id < len(self._monitor_info)
    
    def get_supported_methods(self) -> List[str]:
        """
        Get list of supported screenshot methods.
        
        Returns:
            List[str]: List of available method names
        """
        return [method.value for method in self._available_methods 
                if method != ScreenshotMethod.UNAVAILABLE]
    
    def set_capture_method(self, method: str) -> bool:
        """
        Set specific screenshot capture method.
        
        Args:
            method: Screenshot method name
            
        Returns:
            bool: True if method set successfully
        """
        try:
            screenshot_method = ScreenshotMethod(method)
            
            if screenshot_method not in self._available_methods:
                self.logger.error(f"Screenshot method not available: {method}")
                return False
            
            self._current_method = screenshot_method
            self._consecutive_failures = 0
            self._fallback_attempted = False
            
            self.logger.info(f"Screenshot method set to: {method}")
            return True
            
        except ValueError:
            self.logger.error(f"Invalid screenshot method: {method}")
            return False
    
    def set_frame_rate(self, fps: int) -> bool:
        """
        Set target frame rate for screenshot capture.
        
        Args:
            fps: Target frames per second (1-60 for screenshot capture)
            
        Returns:
            bool: True if frame rate set successfully
        """
        if not 1 <= fps <= 60:  # Screenshot capture is limited to 60 FPS
            self.logger.error(f"Invalid frame rate for screenshot capture: {fps}. Must be 1-60")
            return False
        
        self._frame_rate = fps
        self.logger.info(f"Screenshot capture frame rate set to {fps} FPS")
        return True
    
    def set_performance_profile(self, profile: PerformanceProfile) -> None:
        """
        Set performance profile for screenshot capture.
        
        Args:
            profile: Performance profile
        """
        self._performance_profile = profile
        
        # Adjust settings based on profile
        if profile == PerformanceProfile.LOW:
            self._frame_rate = min(self._frame_rate, 10)
            self._capture_quality = 0.7
        elif profile == PerformanceProfile.NORMAL:
            self._frame_rate = min(self._frame_rate, 20)
            self._capture_quality = 0.85
        elif profile == PerformanceProfile.HIGH:
            self._frame_rate = min(self._frame_rate, 30)
            self._capture_quality = 1.0
        
        self.logger.info(f"Screenshot capture performance profile set to {profile.value}")
    
    def capture_frame(self, region: CaptureRegion) -> Optional[Frame]:
        """
        Capture a single frame using screenshot method.
        
        Args:
            region: Region to capture
            
        Returns:
            Optional[Frame]: Captured frame or None if failed
        """
        if not self.is_available():
            self.logger.error("No screenshot methods available")
            return None
        
        start_time = time.time()
        
        try:
            self._current_region = region
            
            # Attempt capture with current method
            frame = self._capture_with_method(region, self._current_method)
            
            if frame is None:
                # Try fallback method if available
                if not self._fallback_attempted and len(self._available_methods) > 1:
                    fallback_method = self._get_fallback_method()
                    if fallback_method != self._current_method:
                        self.logger.warning(f"Primary method failed, trying fallback: {fallback_method.value}")
                        frame = self._capture_with_method(region, fallback_method)
                        
                        if frame is not None:
                            self._switch_to_method(fallback_method)
            
            # Update statistics
            capture_time = time.time() - start_time
            self._update_capture_stats(frame is not None, capture_time)
            
            return frame
            
        except Exception as e:
            self.logger.error(f"Screenshot capture failed: {e}")
            self._update_capture_stats(False, time.time() - start_time)
            return None
    
    def _capture_with_method(self, region: CaptureRegion, method: ScreenshotMethod) -> Optional[Frame]:
        """
        Capture frame with specific screenshot method.
        
        Args:
            region: Region to capture
            method: Screenshot method to use
            
        Returns:
            Optional[Frame]: Captured frame or None if failed
        """
        try:
            if method == ScreenshotMethod.WIN32_GDI:
                return self._capture_win32_gdi(region)
            elif method == ScreenshotMethod.PIL_IMAGEGRAB:
                return self._capture_pil_imagegrab(region)
            elif method == ScreenshotMethod.MSS:
                return self._capture_mss(region)
            else:
                self.logger.error(f"Unsupported screenshot method: {method}")
                return None
                
        except Exception as e:
            self.logger.error(f"Screenshot method {method.value} failed: {e}")
            self._consecutive_failures += 1
            return None
    
    def _capture_win32_gdi(self, region: CaptureRegion) -> Optional[Frame]:
        """
        Capture frame using Win32 GDI method with multi-monitor support.
        
        Args:
            region: Region to capture
            
        Returns:
            Optional[Frame]: Captured frame or None if failed
        """
        try:
            import win32gui
            import win32ui
            import win32con
            import win32api
            from PIL import Image
            import numpy as np
            
            # Calculate absolute coordinates considering monitor offset
            rect = region.rectangle
            monitor_offset_x = 0
            monitor_offset_y = 0
            
            # Validate and get monitor information
            if self.validate_monitor_id(region.monitor_id):
                monitor_info = self._monitor_info[region.monitor_id]
                monitor_offset_x = monitor_info['left']
                monitor_offset_y = monitor_info['top']
                
                self.logger.debug(f"Win32 GDI - Monitor {region.monitor_id} offset: ({monitor_offset_x}, {monitor_offset_y})")
            else:
                self.logger.warning(f"Invalid monitor ID {region.monitor_id}, using primary monitor")
            
            # Adjust coordinates for monitor offset
            absolute_x = rect.x + monitor_offset_x
            absolute_y = rect.y + monitor_offset_y
            
            # Get device context for the entire virtual desktop
            hwnd = win32gui.GetDesktopWindow()
            hwndDC = win32gui.GetWindowDC(hwnd)
            mfcDC = win32ui.CreateDCFromHandle(hwndDC)
            saveDC = mfcDC.CreateCompatibleDC()
            
            # Calculate capture dimensions with quality scaling
            capture_width = int(rect.width * self._capture_quality)
            capture_height = int(rect.height * self._capture_quality)
            
            # Create bitmap
            saveBitMap = win32ui.CreateBitmap()
            saveBitMap.CreateCompatibleBitmap(mfcDC, capture_width, capture_height)
            saveDC.SelectObject(saveBitMap)
            
            # Copy screen content with scaling if needed, using absolute coordinates
            if self._capture_quality != 1.0:
                saveDC.StretchBlt((0, 0), (capture_width, capture_height), mfcDC,
                                (absolute_x, absolute_y, absolute_x + rect.width, absolute_y + rect.height),
                                win32con.SRCCOPY)
            else:
                saveDC.BitBlt((0, 0), (capture_width, capture_height), mfcDC,
                            (absolute_x, absolute_y), win32con.SRCCOPY)
            
            # Convert to numpy array
            bmpinfo = saveBitMap.GetInfo()
            bmpstr = saveBitMap.GetBitmapBits(True)
            
            # Convert to PIL Image then numpy
            img = Image.frombuffer('RGB', (bmpinfo['bmWidth'], bmpinfo['bmHeight']),
                                 bmpstr, 'raw', 'BGRX', 0, 1)
            
            # Resize back to original dimensions if scaled
            if self._capture_quality != 1.0:
                img = img.resize((rect.width, rect.height), Image.LANCZOS)
            
            frame_data = np.array(img)
            
            # Cleanup
            win32gui.DeleteObject(saveBitMap.GetHandle())
            saveDC.DeleteDC()
            mfcDC.DeleteDC()
            win32gui.ReleaseDC(hwnd, hwndDC)
            
            frame = Frame(
                data=frame_data,
                timestamp=time.time(),
                source_region=region,
                metadata={
                    'capture_method': 'win32_gdi_screenshot',
                    'frame_rate': self._frame_rate,
                    'performance_profile': self._performance_profile.value,
                    'capture_quality': self._capture_quality
                }
            )
            
            self._consecutive_failures = 0
            return frame
            
        except Exception as e:
            self.logger.error(f"Win32 GDI screenshot capture failed: {e}")
            return None
    
    def _capture_pil_imagegrab(self, region: CaptureRegion) -> Optional[Frame]:
        """
        Capture frame using PIL ImageGrab method with multi-monitor support.
        
        Args:
            region: Region to capture
            
        Returns:
            Optional[Frame]: Captured frame or None if failed
        """
        try:
            from PIL import ImageGrab, Image
            import numpy as np
            
            rect = region.rectangle
            
            # Calculate absolute coordinates for multi-monitor support
            monitor_offset_x = 0
            monitor_offset_y = 0
            
            # Validate and get monitor information
            if self.validate_monitor_id(region.monitor_id):
                monitor_info = self._monitor_info[region.monitor_id]
                monitor_offset_x = monitor_info['left']
                monitor_offset_y = monitor_info['top']
                
                self.logger.debug(f"PIL capture - Monitor {region.monitor_id} offset: ({monitor_offset_x}, {monitor_offset_y})")
            else:
                self.logger.warning(f"Invalid monitor ID {region.monitor_id}, using primary monitor")
                # PIL ImageGrab handles the virtual desktop automatically on most systems
            
            # Adjust coordinates for monitor offset
            absolute_x = rect.x + monitor_offset_x
            absolute_y = rect.y + monitor_offset_y
            
            # Calculate capture area with quality scaling
            if self._capture_quality != 1.0:
                # Capture at reduced resolution then scale up
                scaled_width = int(rect.width * self._capture_quality)
                scaled_height = int(rect.height * self._capture_quality)
                scaled_bbox = (absolute_x, absolute_y, 
                             absolute_x + scaled_width, absolute_y + scaled_height)
                
                img = ImageGrab.grab(bbox=scaled_bbox)
                img = img.resize((rect.width, rect.height), Image.LANCZOS)
            else:
                bbox = (absolute_x, absolute_y, absolute_x + rect.width, absolute_y + rect.height)
                img = ImageGrab.grab(bbox=bbox)
            
            frame_data = np.array(img)
            
            frame = Frame(
                data=frame_data,
                timestamp=time.time(),
                source_region=region,
                metadata={
                    'capture_method': 'pil_imagegrab_screenshot',
                    'frame_rate': self._frame_rate,
                    'performance_profile': self._performance_profile.value,
                    'capture_quality': self._capture_quality
                }
            )
            
            self._consecutive_failures = 0
            return frame
            
        except Exception as e:
            self.logger.error(f"PIL ImageGrab screenshot capture failed: {e}")
            return None
    
    def _capture_mss(self, region: CaptureRegion) -> Optional[Frame]:
        """
        Capture frame using MSS method with native multi-monitor support.
        
        Args:
            region: Region to capture
            
        Returns:
            Optional[Frame]: Captured frame or None if failed
        """
        try:
            import mss
            import numpy as np
            from PIL import Image
            
            rect = region.rectangle
            
            with mss.mss() as sct:
                # Calculate absolute coordinates based on monitor
                monitor_offset_x = 0
                monitor_offset_y = 0
                
                # Validate and get monitor information
                if self.validate_monitor_id(region.monitor_id):
                    monitor_info = self._monitor_info[region.monitor_id]
                    monitor_offset_x = monitor_info['left']
                    monitor_offset_y = monitor_info['top']
                    
                    self.logger.debug(f"MSS capture - Monitor {region.monitor_id} offset: ({monitor_offset_x}, {monitor_offset_y})")
                else:
                    self.logger.warning(f"Invalid monitor ID {region.monitor_id}, using primary monitor")
                
                # Adjust coordinates for monitor offset
                absolute_x = rect.x + monitor_offset_x
                absolute_y = rect.y + monitor_offset_y
                
                # Define monitor region with absolute coordinates
                monitor = {
                    "top": absolute_y,
                    "left": absolute_x,
                    "width": rect.width,
                    "height": rect.height
                }
                
                # Capture screenshot
                screenshot = sct.grab(monitor)
                
                # Convert to numpy array
                frame_data = np.array(screenshot)
                
                # Apply quality scaling if needed
                if self._capture_quality != 1.0:
                    img = Image.fromarray(frame_data)
                    scaled_size = (int(rect.width * self._capture_quality),
                                 int(rect.height * self._capture_quality))
                    img = img.resize(scaled_size, Image.LANCZOS)
                    img = img.resize((rect.width, rect.height), Image.LANCZOS)
                    frame_data = np.array(img)
            
            frame = Frame(
                data=frame_data,
                timestamp=time.time(),
                source_region=region,
                metadata={
                    'capture_method': 'mss_screenshot',
                    'frame_rate': self._frame_rate,
                    'performance_profile': self._performance_profile.value,
                    'capture_quality': self._capture_quality
                }
            )
            
            self._consecutive_failures = 0
            return frame
            
        except Exception as e:
            self.logger.error(f"MSS screenshot capture failed: {e}")
            return None
    
    def _get_fallback_method(self) -> ScreenshotMethod:
        """
        Get fallback method for current method.
        
        Returns:
            ScreenshotMethod: Fallback method
        """
        available_methods = [m for m in self._available_methods 
                           if m != self._current_method and m != ScreenshotMethod.UNAVAILABLE]
        
        if available_methods:
            # Return fastest available fallback method
            performance = self._method_detector.get_method_performance()
            if performance:
                return min(available_methods, key=lambda m: performance.get(m, float('inf')))
            else:
                return available_methods[0]
        
        return self._current_method
    
    def _switch_to_method(self, method: ScreenshotMethod) -> None:
        """
        Switch to different screenshot method.
        
        Args:
            method: New method to switch to
        """
        if method != self._current_method:
            old_method = self._current_method
            self._current_method = method
            self._consecutive_failures = 0
            self._fallback_attempted = True
            self._capture_stats['method_switches'] += 1
            
            self.logger.info(f"Switched screenshot method from {old_method.value} to {method.value}")
    
    def _should_attempt_fallback(self) -> bool:
        """
        Check if fallback method should be attempted.
        
        Returns:
            bool: True if fallback should be attempted
        """
        return (self._consecutive_failures >= self._max_consecutive_failures and
                not self._fallback_attempted and
                len(self._available_methods) > 1)
    
    def start_continuous_capture(self, callback: Callable[[Frame], None]) -> bool:
        """
        Start continuous screenshot capture.
        
        Args:
            callback: Function to call with each captured frame
            
        Returns:
            bool: True if continuous capture started successfully
        """
        if self._continuous_capture_active:
            self.logger.warning("Continuous screenshot capture already active")
            return True
        
        if not self._current_region:
            self.logger.error("No capture region set for continuous capture")
            return False
        
        try:
            self._frame_callbacks.append(callback)
            self._stop_event.clear()
            self._capture_thread = threading.Thread(target=self._continuous_capture_loop, daemon=True)
            self._capture_thread.start()
            self._continuous_capture_active = True
            
            self.logger.info("Continuous screenshot capture started")
            return True
            
        except Exception as e:
            self.logger.error(f"Failed to start continuous screenshot capture: {e}")
            return False
    
    def stop_continuous_capture(self) -> bool:
        """
        Stop continuous screenshot capture.
        
        Returns:
            bool: True if capture stopped successfully
        """
        if not self._continuous_capture_active:
            return True
        
        try:
            self._stop_event.set()
            if self._capture_thread and self._capture_thread.is_alive():
                self._capture_thread.join(timeout=2.0)
            
            self._continuous_capture_active = False
            self._frame_callbacks.clear()
            
            self.logger.info("Continuous screenshot capture stopped")
            return True
            
        except Exception as e:
            self.logger.error(f"Failed to stop continuous screenshot capture: {e}")
            return False
    
    def _continuous_capture_loop(self) -> None:
        """Continuous capture loop running in separate thread."""
        frame_interval = 1.0 / self._frame_rate
        last_capture_time = 0
        
        self.logger.debug(f"Continuous screenshot capture loop started with {self._frame_rate} FPS target")
        
        while not self._stop_event.is_set():
            current_time = time.time()
            
            # Frame rate limiting
            if current_time - last_capture_time < frame_interval:
                time.sleep(0.001)
                continue
            
            try:
                # Capture frame
                frame = self.capture_frame(self._current_region)
                
                if frame:
                    # Notify callbacks
                    for callback in self._frame_callbacks:
                        try:
                            callback(frame)
                        except Exception as e:
                            self.logger.error(f"Screenshot capture callback error: {e}")
                
                last_capture_time = current_time
                
            except Exception as e:
                self.logger.error(f"Continuous screenshot capture loop error: {e}")
                time.sleep(0.1)
    
    def _update_capture_stats(self, success: bool, capture_time: float) -> None:
        """
        Update capture statistics.
        
        Args:
            success: Whether capture was successful
            capture_time: Time taken for capture
        """
        self._capture_stats['total_captures'] += 1
        
        if success:
            self._capture_stats['successful_captures'] += 1
        else:
            self._capture_stats['failed_captures'] += 1
        
        # Update average capture time
        if self._capture_stats['total_captures'] > 1:
            self._capture_stats['average_capture_time'] = (
                (self._capture_stats['average_capture_time'] * (self._capture_stats['total_captures'] - 1) + capture_time) /
                self._capture_stats['total_captures']
            )
        else:
            self._capture_stats['average_capture_time'] = capture_time
        
        # Calculate current FPS
        if capture_time > 0:
            self._capture_stats['current_fps'] = 1.0 / capture_time
    
    def get_capture_statistics(self) -> Dict[str, Any]:
        """
        Get comprehensive capture statistics.
        
        Returns:
            Dict[str, Any]: Capture statistics
        """
        stats = self._capture_stats.copy()
        stats.update({
            'current_method': self._current_method.value,
            'available_methods': [m.value for m in self._available_methods],
            'consecutive_failures': self._consecutive_failures,
            'fallback_attempted': self._fallback_attempted,
            'frame_rate': self._frame_rate,
            'performance_profile': self._performance_profile.value,
            'capture_quality': self._capture_quality
        })
        
        return stats
    
    def get_status_info(self) -> Dict[str, Any]:
        """
        Get detailed status information.
        
        Returns:
            Dict[str, Any]: Status information
        """
        return {
            'available': self.is_available(),
            'current_method': self._current_method.value,
            'available_methods': self.get_supported_methods(),
            'continuous_capture_active': self._continuous_capture_active,
            'current_region': self._current_region,
            'frame_rate': self._frame_rate,
            'performance_profile': self._performance_profile.value,
            'capture_quality': self._capture_quality,
            'method_performance': self._method_detector.get_method_performance(),
            'monitor_count': len(self._monitor_info),
            'monitor_info': self._monitor_info
        }
    
    def validate_capture_mode(self) -> Tuple[bool, str]:
        """
        Validate current capture mode and configuration.
        
        Returns:
            Tuple[bool, str]: (is_valid, validation_message)
        """
        if not self.is_available():
            return False, "No screenshot capture methods available"
        
        if self._current_method == ScreenshotMethod.UNAVAILABLE:
            return False, "Current screenshot method is unavailable"
        
        if self._consecutive_failures >= self._max_consecutive_failures:
            return False, f"Too many consecutive failures ({self._consecutive_failures})"
        
        if not self._current_region:
            return False, "No capture region configured"
        
        # Validate capture region
        rect = self._current_region.rectangle
        if rect.width <= 0 or rect.height <= 0:
            return False, "Invalid capture region dimensions"
        
        if rect.width > 7680 or rect.height > 4320:  # 8K resolution limit
            return False, "Capture region too large (exceeds 8K resolution)"
        
        # Validate monitor ID
        if not self.validate_monitor_id(self._current_region.monitor_id):
            return False, f"Invalid monitor ID {self._current_region.monitor_id} (available: 0-{len(self._monitor_info)-1})"
        
        # Validate region is within monitor bounds
        monitor_info = self._monitor_info[self._current_region.monitor_id]
        if (rect.x + rect.width > monitor_info['width'] or 
            rect.y + rect.height > monitor_info['height']):
            return False, f"Capture region extends beyond monitor {self._current_region.monitor_id} bounds"
        
        return True, "Screenshot capture mode is valid and ready"
    
    def cleanup(self) -> None:
        """Clean up screenshot capture resources."""
        try:
            self.stop_continuous_capture()
            self._frame_callbacks.clear()
            
            self.logger.info("Screenshot capture resources cleaned up")
            
        except Exception as e:
            self.logger.error(f"Screenshot capture cleanup error: {e}")