"""
DirectX Desktop Duplication API Capture Implementation

High-performance screen capture using DirectX Desktop Duplication API with fallback support.
"""

import ctypes
from ctypes import wintypes, byref, POINTER, Structure, c_void_p, c_int, c_uint, c_ubyte
import time
import threading
from typing import Optional, List, Callable, Dict, Any
import numpy as np
from enum import Enum
import logging

try:
    from ..models import Frame, CaptureRegion, Rectangle, CaptureMode, PerformanceProfile
    from ..interfaces import ICaptureLayer, CaptureSource
    from .multi_monitor_support import MultiMonitorManager, MonitorInfo
except ImportError:
    from app.models import Frame, CaptureRegion, Rectangle, CaptureMode, PerformanceProfile
    from app.interfaces import ICaptureLayer, CaptureSource
    from app.capture.multi_monitor_support import MultiMonitorManager, MonitorInfo

# CRITICAL FIX: Delay dxcam import to avoid CUDA/PyTorch conflicts
# dxcam initializes DirectX/CUDA resources on import, which conflicts with PyTorch
# Import it lazily when actually needed (after OCR engines are loaded)
print("[DirectX Module] dxcam import deferred (lazy import to avoid GPU conflicts)")
dxcam = None
DXCAM_AVAILABLE = None  # Will be checked on first use


class CaptureStatus(Enum):
    """Capture system status enumeration."""
    READY = "ready"
    CAPTURING = "capturing"
    ERROR = "error"
    UNAVAILABLE = "unavailable"


class DirectXCaptureError(Exception):
    """DirectX capture specific exceptions."""
    pass


# DirectX/DXGI Constants and Structures
DXGI_ERROR_ACCESS_LOST = 0x887A0026
DXGI_ERROR_WAIT_TIMEOUT = 0x887A0027
DXGI_ERROR_INVALID_CALL = 0x887A0001

class RECT(Structure):
    """Windows RECT structure."""
    _fields_ = [
        ("left", c_int),
        ("top", c_int),
        ("right", c_int),
        ("bottom", c_int)
    ]


class DXGI_OUTDUPL_DESC(Structure):
    """DXGI Output Duplication Description structure."""
    _fields_ = [
        ("ModeDesc", c_void_p),  # Simplified for this implementation
        ("Rotation", c_uint),
        ("DesktopImageInSystemMemory", wintypes.BOOL)
    ]


class DirectXDesktopCapture:
    """
    DirectX Desktop Duplication API capture implementation.
    
    Provides high-performance screen capture using DirectX Desktop Duplication API
    with automatic fallback to GDI+ screenshot capture when DirectX is unavailable.
    """
    
    def __init__(self, logger: Optional[logging.Logger] = None):
        """
        Initialize DirectX capture system.
        
        Args:
            logger: Optional logger for debugging and monitoring
        """
        self.logger = logger or logging.getLogger(__name__)
        self._is_initialized = False
        self._capture_active = False
        self._current_region: Optional[CaptureRegion] = None
        self._frame_rate = 30
        self._capture_thread: Optional[threading.Thread] = None
        self._stop_event = threading.Event()
        self._frame_callbacks: List[Callable[[Frame], None]] = []
        self._performance_profile = PerformanceProfile.NORMAL
        self._dxcam_use_fullscreen = False  # Flag for full screen capture mode
        self._dxcam_failed = False  # Flag to prevent repeated DXCam initialization attempts
        
        # Multi-monitor support
        print("[DirectXDesktopCapture] Creating MultiMonitorManager...")
        self._monitor_manager = MultiMonitorManager(logger)
        print("[DirectXDesktopCapture] MultiMonitorManager created")
        
        # DirectX/DXGI objects (will be initialized when needed)
        self._dxgi_factory = None
        self._dxgi_adapter = None
        self._dxgi_output = None
        self._dxgi_duplication = None
        self._d3d_device = None
        self._d3d_context = None
        
        # Per-monitor DirectX objects for multi-monitor support
        self._monitor_duplications: Dict[int, Any] = {}
        
        # Capture statistics
        self._stats = {
            'frames_captured': 0,
            'frames_dropped': 0,
            'last_capture_time': 0,
            'average_fps': 0,
            'capture_errors': 0,
            'active_monitors': 0
        }
        
        # Initialize DirectX capture
        print("[DirectXDesktopCapture] Calling _initialize_directx_capture...")
        self._initialize_directx_capture()
        print("[DirectXDesktopCapture] Initialization complete")
    
    def _initialize_directx_capture(self) -> bool:
        """
        Initialize DirectX Desktop Duplication API using dxcam.
        
        Returns:
            bool: True if initialization successful, False otherwise
        """
        global dxcam, DXCAM_AVAILABLE
        
        try:
            self.logger.info("Initializing DirectX Desktop Duplication API via dxcam")
            print("[DirectX Init] Lazy importing dxcam...")
            
            # Lazy import dxcam to avoid GPU conflicts during startup
            if DXCAM_AVAILABLE is None:
                try:
                    import dxcam as dxcam_module
                    dxcam = dxcam_module
                    DXCAM_AVAILABLE = True
                    print("[DirectX Init] dxcam imported successfully!")
                except ImportError as e:
                    print(f"[DirectX Init] dxcam not available: {e}")
                    DXCAM_AVAILABLE = False
                    return False
                except Exception as e:
                    print(f"[DirectX Init] Error importing dxcam: {e}")
                    DXCAM_AVAILABLE = False
                    return False
            
            if not DXCAM_AVAILABLE or dxcam is None:
                print("[DirectX Init] dxcam not available")
                self.logger.warning("dxcam not available, DirectX capture will not work")
                return False
            
            print("[DirectX Init] dxcam is available!")
            self.logger.info("dxcam library available")
            
            # Skip dxcam test - it can hang on some systems
            # The camera will be created on first actual capture
            
            # Enumerate monitors using multi-monitor manager
            if not self._enumerate_display_adapters():
                return False
            
            self._is_initialized = True
            self._dxcam_camera = None  # Will be created on first capture
            self.logger.info("DirectX Desktop Duplication API initialized successfully via dxcam")
            return True
            
        except Exception as e:
            self.logger.error(f"DirectX initialization failed: {e}")
            return False
    
    def _create_dxgi_factory(self) -> bool:
        """Create DXGI Factory for adapter enumeration."""
        try:
            # This is a simplified implementation
            # In a real implementation, you would use proper DXGI COM interfaces
            self.logger.debug("Creating DXGI Factory")
            self._dxgi_factory = True  # Placeholder for actual DXGI factory
            return True
        except Exception as e:
            self.logger.error(f"Failed to create DXGI Factory: {e}")
            return False
    
    def _enumerate_display_adapters(self) -> bool:
        """Enumerate display adapters and outputs for multi-monitor support."""
        try:
            self.logger.debug("Enumerating display adapters for multi-monitor support")
            
            # Get monitor information from multi-monitor manager
            monitors = self._monitor_manager.get_all_monitors()
            self._stats['active_monitors'] = len(monitors)
            
            self.logger.info(f"Found {len(monitors)} monitors for DirectX capture")
            for monitor_id, monitor in monitors.items():
                self.logger.debug(f"Monitor {monitor_id}: {monitor.display_name} "
                                f"({monitor.bounds.width}x{monitor.bounds.height})")
            
            # Simplified implementation - would enumerate actual adapters per monitor
            self._dxgi_adapter = True  # Placeholder
            self._dxgi_output = True   # Placeholder
            return True
            
        except Exception as e:
            self.logger.error(f"Failed to enumerate display adapters: {e}")
            return False
    
    def _create_d3d_device(self) -> bool:
        """Create D3D11 device and context."""
        try:
            self.logger.debug("Creating D3D11 device")
            # Simplified implementation - would create actual D3D11 device
            self._d3d_device = True   # Placeholder
            self._d3d_context = True  # Placeholder
            return True
        except Exception as e:
            self.logger.error(f"Failed to create D3D11 device: {e}")
            return False
    
    def _initialize_desktop_duplication(self) -> bool:
        """Initialize desktop duplication interface."""
        try:
            self.logger.debug("Initializing desktop duplication")
            # Simplified implementation - would create actual duplication interface
            self._dxgi_duplication = True  # Placeholder
            return True
        except Exception as e:
            self.logger.error(f"Failed to initialize desktop duplication: {e}")
            return False
    
    def is_available(self) -> bool:
        """
        Check if DirectX capture is available.
        
        Returns:
            bool: True if DirectX capture is available and initialized
        """
        return self._is_initialized
    
    def get_supported_modes(self) -> List[str]:
        """
        Get list of supported capture modes.
        
        Returns:
            List[str]: List of supported capture mode names
        """
        modes = []
        if self._is_initialized:
            modes.append(CaptureMode.DIRECTX.value)
            modes.append(CaptureMode.DESKTOP_DUPLICATION.value)
        modes.append(CaptureMode.SCREENSHOT.value)  # Always available as fallback
        return modes
    
    def set_capture_region(self, region: CaptureRegion) -> bool:
        """
        Set the capture region with multi-monitor validation.
        
        Args:
            region: CaptureRegion defining the area to capture
            
        Returns:
            bool: True if region set successfully
        """
        try:
            # Validate monitor ID
            monitor_info = self._monitor_manager.get_monitor_info(region.monitor_id)
            if not monitor_info:
                self.logger.error(f"Invalid monitor ID: {region.monitor_id}")
                return False
            
            # Validate region is within monitor bounds
            monitor_bounds = monitor_info.bounds
            region_rect = region.rectangle
            
            if (region_rect.x < monitor_bounds.x or 
                region_rect.y < monitor_bounds.y or
                region_rect.x + region_rect.width > monitor_bounds.x + monitor_bounds.width or
                region_rect.y + region_rect.height > monitor_bounds.y + monitor_bounds.height):
                
                self.logger.warning(f"Capture region extends beyond monitor {region.monitor_id} bounds, clipping")
                
                # Clip region to monitor bounds
                clipped_region = CaptureRegion(
                    rectangle=Rectangle(
                        x=max(region_rect.x, monitor_bounds.x),
                        y=max(region_rect.y, monitor_bounds.y),
                        width=min(region_rect.width, 
                                monitor_bounds.x + monitor_bounds.width - max(region_rect.x, monitor_bounds.x)),
                        height=min(region_rect.height,
                                 monitor_bounds.y + monitor_bounds.height - max(region_rect.y, monitor_bounds.y))
                    ),
                    monitor_id=region.monitor_id,
                    window_handle=region.window_handle
                )
                self._current_region = clipped_region
            else:
                self._current_region = region
            
            # IMPORTANT: Delete existing DXCam camera when region changes
            # DXCam requires manual deletion to change capture parameters
            if hasattr(self, '_dxcam_camera') and self._dxcam_camera is not None:
                try:
                    self.logger.info("Releasing old DXCam camera due to region change")
                    self._dxcam_camera.release()
                    del self._dxcam_camera
                    self._dxcam_camera = None
                    # Reset flags
                    if hasattr(self, '_region_logged'):
                        del self._region_logged
                    if hasattr(self, '_dxcam_use_fullscreen'):
                        self._dxcam_use_fullscreen = False
                    
                    # CRITICAL: Clear DXCam's global device cache
                    # DXCam stores devices globally and won't recreate without this
                    try:
                        import dxcam
                        # Access internal device list and clear it
                        if hasattr(dxcam, 'device_list'):
                            dxcam.device_list = None
                        if hasattr(dxcam, '_device'):
                            dxcam._device = None
                        self.logger.info("DXCam global cache cleared")
                    except Exception as clear_error:
                        self.logger.warning(f"Could not clear DXCam global cache: {clear_error}")
                    
                    self.logger.info("DXCam camera released successfully")
                except Exception as e:
                    self.logger.warning(f"Error releasing DXCam camera: {e}")
                    # Force reset even if release failed
                    self._dxcam_camera = None
                    # Mark DXCam as failed to prevent further attempts
                    self._dxcam_failed = True
            
            self.logger.info(f"Capture region set on monitor {region.monitor_id} ({monitor_info.display_name}): "
                           f"{self._current_region.rectangle.width}x{self._current_region.rectangle.height} "
                           f"at ({self._current_region.rectangle.x}, {self._current_region.rectangle.y})")
            return True
            
        except Exception as e:
            self.logger.error(f"Failed to set capture region: {e}")
            return False
    
    def set_frame_rate(self, fps: int) -> bool:
        """
        Set the target frame rate for capture.
        
        Args:
            fps: Target frames per second (1-120)
            
        Returns:
            bool: True if frame rate set successfully
        """
        if not 1 <= fps <= 120:
            self.logger.error(f"Invalid frame rate: {fps}. Must be between 1 and 120")
            return False
        
        self._frame_rate = fps
        self.logger.info(f"Frame rate set to {fps} FPS")
        return True
    
    def set_performance_profile(self, profile: PerformanceProfile) -> None:
        """
        Set performance profile for adaptive optimization.
        
        Args:
            profile: Performance profile (LOW, NORMAL, HIGH)
        """
        self._performance_profile = profile
        
        # Adjust frame rate based on profile
        if profile == PerformanceProfile.LOW:
            self._frame_rate = min(self._frame_rate, 15)
        elif profile == PerformanceProfile.NORMAL:
            self._frame_rate = min(self._frame_rate, 30)
        elif profile == PerformanceProfile.HIGH:
            self._frame_rate = min(self._frame_rate, 60)
        
        self.logger.info(f"Performance profile set to {profile.value}, frame rate: {self._frame_rate}")
    
    def add_frame_callback(self, callback: Callable[[Frame], None]) -> None:
        """
        Add callback function to receive captured frames.
        
        Args:
            callback: Function to call with each captured frame
        """
        self._frame_callbacks.append(callback)
        self.logger.debug(f"Frame callback added. Total callbacks: {len(self._frame_callbacks)}")
    
    def remove_frame_callback(self, callback: Callable[[Frame], None]) -> None:
        """
        Remove frame callback.
        
        Args:
            callback: Callback function to remove
        """
        if callback in self._frame_callbacks:
            self._frame_callbacks.remove(callback)
            self.logger.debug(f"Frame callback removed. Total callbacks: {len(self._frame_callbacks)}")
    
    def start_capture(self) -> bool:
        """
        Start continuous frame capture.
        
        Returns:
            bool: True if capture started successfully
        """
        if self._capture_active:
            self.logger.warning("Capture already active")
            return True
        
        if not self._current_region:
            self.logger.error("No capture region set")
            return False
        
        try:
            self._stop_event.clear()
            self._capture_thread = threading.Thread(target=self._capture_loop, daemon=True)
            self._capture_thread.start()
            self._capture_active = True
            
            self.logger.info("Frame capture started")
            return True
            
        except Exception as e:
            self.logger.error(f"Failed to start capture: {e}")
            return False
    
    def stop_capture(self) -> bool:
        """
        Stop continuous frame capture.
        
        Returns:
            bool: True if capture stopped successfully
        """
        if not self._capture_active:
            return True
        
        try:
            self._stop_event.set()
            if self._capture_thread and self._capture_thread.is_alive():
                self._capture_thread.join(timeout=2.0)
            
            self._capture_active = False
            self.logger.info("Frame capture stopped")
            return True
            
        except Exception as e:
            self.logger.error(f"Failed to stop capture: {e}")
            return False
    
    def capture_single_frame(self) -> Optional[Frame]:
        """
        Capture a single frame.
        
        Returns:
            Optional[Frame]: Captured frame or None if capture failed
        """
        if not self._current_region:
            self.logger.error("No capture region set")
            return None
        
        try:
            if self._is_initialized:
                return self._capture_directx_frame()
            else:
                return self._capture_fallback_frame()
                
        except Exception as e:
            self.logger.error(f"Single frame capture failed: {e}")
            return None
    
    def _capture_loop(self) -> None:
        """Main capture loop running in separate thread."""
        frame_interval = 1.0 / self._frame_rate
        last_capture_time = 0
        
        self.logger.debug(f"Capture loop started with {self._frame_rate} FPS target")
        
        while not self._stop_event.is_set():
            current_time = time.time()
            
            # Frame rate limiting
            if current_time - last_capture_time < frame_interval:
                time.sleep(0.001)  # Small sleep to prevent busy waiting
                continue
            
            try:
                frame = self.capture_single_frame()
                if frame:
                    self._update_capture_stats(current_time)
                    
                    # Notify all callbacks
                    for callback in self._frame_callbacks:
                        try:
                            callback(frame)
                        except Exception as e:
                            self.logger.error(f"Frame callback error: {e}")
                else:
                    self._stats['frames_dropped'] += 1
                
                last_capture_time = current_time
                
            except Exception as e:
                self.logger.error(f"Capture loop error: {e}")
                self._stats['capture_errors'] += 1
                time.sleep(0.1)  # Brief pause on error
    
    def _capture_directx_frame(self) -> Optional[Frame]:
        """
        Capture frame using DirectX Desktop Duplication API via dxcam.
        
        Returns:
            Optional[Frame]: Captured frame or None if failed
        """
        try:
            # Use dxcam for real DirectX capture
            import dxcam
            
            # Check if DXCam has already failed - don't keep trying
            if hasattr(self, '_dxcam_failed') and self._dxcam_failed:
                return self._capture_fallback_frame()
            
            # Create camera if not exists
            if not hasattr(self, '_dxcam_camera') or self._dxcam_camera is None:
                try:
                    # Get monitor ID from current region
                    monitor_id = self._current_region.monitor_id if self._current_region else 0
                    
                    self.logger.info(f"Creating DXCam camera for monitor {monitor_id}")
                    
                    # List available devices for debugging
                    try:
                        devices = dxcam.device_info()
                        outputs = dxcam.output_info()
                        self.logger.info(f"Available DXCam devices: {devices}")
                        self.logger.info(f"Available DXCam outputs: {outputs}")
                    except Exception as e:
                        self.logger.warning(f"Could not get DXCam device info: {e}")
                    
                    # Create camera without starting it first
                    # Try with default device (None) first, which auto-selects
                    self._dxcam_camera = dxcam.create(output_idx=monitor_id)
                    
                    if self._dxcam_camera is None:
                        self.logger.error("Failed to create DXCam camera - returned None")
                        return self._capture_fallback_frame()
                    
                    # Log camera details for debugging
                    self.logger.info(f"DXCam camera object created: {self._dxcam_camera}")
                    self.logger.info(f"DXCam output device: {self._dxcam_camera.output if hasattr(self._dxcam_camera, 'output') else 'unknown'}")
                    
                    # DO NOT start the camera! Just use grab() directly
                    # Starting with video_mode=True creates a background thread that conflicts with our grab() calls
                    # DXCam's grab() works fine without calling start() first
                    self.logger.info(f"DXCam camera created (not started - will use direct grab())")
                    
                    # Give a small delay for initialization
                    time.sleep(0.1)
                    
                    # Get the actual region we'll be capturing
                    region = self._current_region.rectangle
                    
                    # Do a test grab with the actual region to ensure camera is working
                    # Note: dxcam region is (left, top, right, bottom)
                    test_region = (region.x, region.y, region.x + region.width, region.y + region.height)
                    
                    self.logger.info(f"Testing DXCam with region: {test_region}")
                    
                    # Try multiple test grabs - DXCam sometimes needs a few frames to warm up
                    test_frame = None
                    for attempt in range(5):
                        test_frame = self._dxcam_camera.grab(region=test_region)
                        if test_frame is not None:
                            self.logger.info(f"DXCam test successful on attempt {attempt + 1}")
                            break
                        time.sleep(0.1)
                    
                    if test_frame is None:
                        self.logger.warning("DXCam test grab with region returned None after 5 attempts, trying full screen")
                        # Try full screen grab as fallback test
                        for attempt in range(5):
                            test_frame = self._dxcam_camera.grab()
                            if test_frame is not None:
                                self.logger.info(f"DXCam full screen test successful on attempt {attempt + 1}")
                                break
                            time.sleep(0.1)
                        
                        if test_frame is None:
                            self.logger.error("DXCam camera not working (both region and full screen failed after multiple attempts)")
                            self.logger.error("This might be a threading issue or DXCam incompatibility")
                            # Just release the camera (no need to stop since we never started it)
                            self._dxcam_camera.release()
                            self._dxcam_camera = None
                            # Don't try to recreate - just use fallback permanently
                            self._dxcam_failed = True
                            return self._capture_fallback_frame()
                        else:
                            self.logger.warning("DXCam works with full screen but not with region - will use full screen + crop")
                            # Mark that we need to use full screen mode
                            self._dxcam_use_fullscreen = True
                    else:
                        self._dxcam_use_fullscreen = False
                    
                    self.logger.info(f"DXCam camera created and started for monitor {monitor_id} (FPS: {self._frame_rate}, fullscreen_mode: {self._dxcam_use_fullscreen})")
                except Exception as e:
                    self.logger.error(f"Failed to create DXCam camera: {e}")
                    return self._capture_fallback_frame()
            
            # Get region coordinates
            region = self._current_region.rectangle
            
            # Log region details once for debugging
            if not hasattr(self, '_region_logged'):
                self.logger.info(f"Capture region: x={region.x}, y={region.y}, w={region.width}, h={region.height}")
                self._region_logged = True
            
            # Capture frame with dxcam (much faster than screenshot)
            # dxcam uses DirectX Desktop Duplication API internally
            # Note: dxcam region is (left, top, right, bottom)
            try:
                # Check if we need to use full screen mode
                if hasattr(self, '_dxcam_use_fullscreen') and self._dxcam_use_fullscreen:
                    # Grab full screen and crop
                    frame_data = self._dxcam_camera.grab()
                    if frame_data is not None:
                        # Crop to desired region
                        frame_data = frame_data[region.y:region.y+region.height, 
                                              region.x:region.x+region.width]
                else:
                    # Try to grab with region directly
                    frame_data = self._dxcam_camera.grab(region=(region.x, region.y, 
                                                                 region.x + region.width, 
                                                                 region.y + region.height))
            except Exception as grab_error:
                # If grab fails, try to recreate the camera
                self.logger.warning(f"DXCam grab failed, attempting to recreate camera: {type(grab_error).__name__}")
                try:
                    # Stop and release old camera
                    if hasattr(self, '_dxcam_camera') and self._dxcam_camera is not None:
                        try:
                            # Just release (no need to stop since we never started it)
                            self._dxcam_camera.release()
                        except:
                            pass
                    
                    # Recreate camera
                    monitor_id = self._current_region.monitor_id if self._current_region else 0
                    self._dxcam_camera = dxcam.create(output_idx=monitor_id)
                    
                    if self._dxcam_camera is None:
                        self.logger.warning("Failed to recreate DXCam camera, using screenshot fallback")
                        return self._capture_fallback_frame()
                    
                    # Don't start the camera - just use grab() directly
                    time.sleep(0.1)
                    
                    # Try grab again
                    frame_data = self._dxcam_camera.grab(region=(region.x, region.y, 
                                                                 region.x + region.width, 
                                                                 region.y + region.height))
                except Exception as recreate_error:
                    self.logger.warning(f"Camera recreation failed: {type(recreate_error).__name__}, using screenshot fallback")
                    return self._capture_fallback_frame()
            
            if frame_data is None:
                # DXCam sometimes returns None temporarily, retry a few times before giving up
                retry_count = 0
                max_retries = self.config_manager.get_setting('retry.max_retries', 3) if self.config_manager else 3
                
                while frame_data is None and retry_count < max_retries:
                    retry_count += 1
                    time.sleep(0.01)  # Small delay between retries
                    
                    try:
                        # Try full screen grab first
                        frame_data = self._dxcam_camera.grab()
                        
                        if frame_data is not None:
                            # Crop to desired region
                            frame_data = frame_data[region.y:region.y+region.height, 
                                                  region.x:region.x+region.width]
                            break
                    except Exception as e:
                        if retry_count == max_retries:
                            self.logger.warning(f"DXCam grab failed after {max_retries} retries: {e}")
                
                # If still None after retries, use fallback
                if frame_data is None:
                    # Only log warning occasionally to avoid spam
                    if not hasattr(self, '_fallback_warning_count'):
                        self._fallback_warning_count = 0
                    
                    self._fallback_warning_count += 1
                    if self._fallback_warning_count % 10 == 1:  # Log every 10th failure
                        self.logger.warning(f"DXCam returned None after {max_retries} retries (count: {self._fallback_warning_count}), using screenshot fallback")
                    
                    return self._capture_fallback_frame()
            
            # dxcam returns RGB already, no need to convert
            frame = Frame(
                data=frame_data,
                timestamp=time.time(),
                source_region=self._current_region,
                metadata={
                    'capture_method': 'directx_dxcam',
                    'frame_rate': self._frame_rate,
                    'performance_profile': self._performance_profile.value
                }
            )
            
            return frame
            
        except ImportError:
            self.logger.warning("dxcam not available, falling back to screenshot")
            return self._capture_fallback_frame()
        except Exception as e:
            # DirectX capture failed, but fallback to screenshot works fine
            # Only log as warning since this is expected on some systems
            self.logger.warning(f"DirectX capture unavailable, using screenshot fallback (Reason: {type(e).__name__})")
            # Fallback to screenshot capture
            return self._capture_fallback_frame()
    
    def _capture_fallback_frame(self) -> Optional[Frame]:
        """
        Fallback frame capture using GDI+ screenshot.
        
        Returns:
            Optional[Frame]: Captured frame or None if failed
        """
        try:
            import win32gui
            import win32ui
            import win32con
            from PIL import Image
            
            # Get device context
            hwnd = win32gui.GetDesktopWindow()
            hwndDC = win32gui.GetWindowDC(hwnd)
            mfcDC = win32ui.CreateDCFromHandle(hwndDC)
            saveDC = mfcDC.CreateCompatibleDC()
            
            # Create bitmap
            region = self._current_region.rectangle
            saveBitMap = win32ui.CreateBitmap()
            saveBitMap.CreateCompatibleBitmap(mfcDC, region.width, region.height)
            saveDC.SelectObject(saveBitMap)
            
            # Copy screen content
            saveDC.BitBlt((0, 0), (region.width, region.height), mfcDC, 
                         (region.x, region.y), win32con.SRCCOPY)
            
            # Convert to numpy array
            bmpinfo = saveBitMap.GetInfo()
            bmpstr = saveBitMap.GetBitmapBits(True)
            
            # Convert to PIL Image then numpy
            img = Image.frombuffer('RGB', (bmpinfo['bmWidth'], bmpinfo['bmHeight']), 
                                 bmpstr, 'raw', 'BGRX', 0, 1)
            frame_data = np.array(img)
            
            # Cleanup
            win32gui.DeleteObject(saveBitMap.GetHandle())
            saveDC.DeleteDC()
            mfcDC.DeleteDC()
            win32gui.ReleaseDC(hwnd, hwndDC)
            
            frame = Frame(
                data=frame_data,
                timestamp=time.time(),
                source_region=self._current_region,
                metadata={
                    'capture_method': 'screenshot_fallback',
                    'frame_rate': self._frame_rate,
                    'performance_profile': self._performance_profile.value
                }
            )
            
            return frame
            
        except ImportError:
            self.logger.error("Win32 libraries not available for fallback capture")
            return None
        except Exception as e:
            self.logger.error(f"Fallback frame capture failed: {e}")
            return None
    
    def _update_capture_stats(self, current_time: float) -> None:
        """Update capture statistics."""
        self._stats['frames_captured'] += 1
        
        # Calculate average FPS over last 30 frames
        if self._stats['frames_captured'] % 30 == 0:
            if self._stats['last_capture_time'] > 0:
                time_diff = current_time - self._stats['last_capture_time']
                if time_diff > 0:
                    self._stats['average_fps'] = 30.0 / time_diff
        
        self._stats['last_capture_time'] = current_time
    
    def get_capture_stats(self) -> Dict[str, Any]:
        """
        Get capture statistics.
        
        Returns:
            Dict[str, Any]: Dictionary containing capture statistics
        """
        return self._stats.copy()
    
    def get_status(self) -> CaptureStatus:
        """
        Get current capture status.
        
        Returns:
            CaptureStatus: Current status of the capture system
        """
        if not self._is_initialized:
            return CaptureStatus.UNAVAILABLE
        elif self._capture_active:
            return CaptureStatus.CAPTURING
        elif self._stats['capture_errors'] > 10:
            return CaptureStatus.ERROR
        else:
            return CaptureStatus.READY
    
    def get_monitor_manager(self) -> MultiMonitorManager:
        """
        Get the multi-monitor manager.
        
        Returns:
            MultiMonitorManager: Monitor manager instance
        """
        return self._monitor_manager
    
    def get_available_monitors(self) -> Dict[int, MonitorInfo]:
        """
        Get information about all available monitors.
        
        Returns:
            Dict[int, MonitorInfo]: Dictionary of monitor ID to monitor info
        """
        return self._monitor_manager.get_all_monitors()
    
    def get_primary_monitor_id(self) -> Optional[int]:
        """
        Get the ID of the primary monitor.
        
        Returns:
            Optional[int]: Primary monitor ID or None if not found
        """
        return self._monitor_manager.get_primary_monitor_id()
    
    def create_full_screen_region(self, monitor_id: Optional[int] = None) -> Optional[CaptureRegion]:
        """
        Create a capture region for full screen capture.
        
        Args:
            monitor_id: Optional monitor ID, uses primary if None
            
        Returns:
            Optional[CaptureRegion]: Full screen capture region or None if failed
        """
        if monitor_id is None:
            # Use virtual screen (all monitors)
            return self._monitor_manager.create_full_screen_region()
        else:
            # Use specific monitor
            return self._monitor_manager.create_capture_region_for_monitor(monitor_id)
    
    def create_monitor_region(self, monitor_id: int, 
                            custom_region: Optional[Rectangle] = None) -> Optional[CaptureRegion]:
        """
        Create a capture region for a specific monitor.
        
        Args:
            monitor_id: Monitor ID
            custom_region: Optional custom region within the monitor
            
        Returns:
            Optional[CaptureRegion]: Capture region or None if failed
        """
        return self._monitor_manager.create_capture_region_for_monitor(monitor_id, custom_region)
    
    def refresh_monitors(self) -> bool:
        """
        Refresh monitor information (useful when displays are added/removed).
        
        Returns:
            bool: True if refresh successful
        """
        try:
            success = self._monitor_manager.refresh_monitor_info()
            if success:
                self._stats['active_monitors'] = self._monitor_manager.get_monitor_count()
                self.logger.info("Monitor information refreshed")
            return success
        except Exception as e:
            self.logger.error(f"Failed to refresh monitors: {e}")
            return False
    
    def get_monitor_summary(self) -> Dict[str, Any]:
        """
        Get a summary of monitor configuration.
        
        Returns:
            Dict[str, Any]: Monitor summary
        """
        return self._monitor_manager.get_monitor_summary()
    
    def cleanup(self) -> None:
        """Clean up DirectX resources."""
        try:
            self.stop_capture()
            
            # Release dxcam camera
            if hasattr(self, '_dxcam_camera') and self._dxcam_camera is not None:
                try:
                    # Only stop if it was started (we don't start it anymore)
                    # Just release it directly
                    self._dxcam_camera.release()
                    del self._dxcam_camera
                    self._dxcam_camera = None
                    self.logger.debug("Released dxcam camera")
                except Exception as e:
                    self.logger.error(f"Error releasing dxcam camera: {e}")
            
            # Release per-monitor DirectX resources
            for monitor_id, duplication in self._monitor_duplications.items():
                try:
                    self.logger.debug(f"Released DirectX resources for monitor {monitor_id}")
                except Exception as e:
                    self.logger.error(f"Error releasing resources for monitor {monitor_id}: {e}")
            
            self._monitor_duplications.clear()
            
            self._is_initialized = False
            self.logger.info("DirectX capture resources cleaned up")
            
        except Exception as e:
            self.logger.error(f"Cleanup error: {e}")


class DirectXCaptureLayer(ICaptureLayer):
    """
    DirectX capture layer implementation conforming to ICaptureLayer interface.
    
    Provides high-level interface for DirectX-based screen capture with automatic
    fallback support and adaptive frame rate control.
    """
    
    def __init__(self, logger: Optional[logging.Logger] = None):
        """
        Initialize DirectX capture layer.
        
        Args:
            logger: Optional logger for debugging and monitoring
        """
        self.logger = logger or logging.getLogger(__name__)
        self._capture_engine = DirectXDesktopCapture(logger)
        self._current_mode = CaptureMode.DIRECTX if self._capture_engine.is_available() else CaptureMode.SCREENSHOT
        
        self.logger.info(f"DirectX Capture Layer initialized with mode: {self._current_mode.value}")
    
    def capture_frame(self, source: CaptureSource, region: CaptureRegion) -> Frame:
        """
        Capture a frame from the specified source and region with multi-monitor support.
        
        Args:
            source: Capture source type (FULL_SCREEN, WINDOW, CUSTOM_REGION)
            region: Region to capture
            
        Returns:
            Frame: Captured frame data
            
        Raises:
            DirectXCaptureError: If capture fails
        """
        try:
            # Set capture region based on source type
            if source == CaptureSource.FULL_SCREEN:
                # Create full screen region for specified monitor or all monitors
                full_screen_region = self._capture_engine.create_full_screen_region(region.monitor_id)
                if not full_screen_region:
                    raise DirectXCaptureError(f"Failed to create full screen region for monitor {region.monitor_id}")
                self._capture_engine.set_capture_region(full_screen_region)
            elif source == CaptureSource.WINDOW:
                # For window capture, use the region as-is but validate monitor
                monitor_info = self._capture_engine.get_monitor_manager().get_monitor_info(region.monitor_id)
                if not monitor_info:
                    raise DirectXCaptureError(f"Invalid monitor ID: {region.monitor_id}")
                self._capture_engine.set_capture_region(region)
            else:  # CUSTOM_REGION
                # Validate custom region against monitor bounds
                monitor_info = self._capture_engine.get_monitor_manager().get_monitor_info(region.monitor_id)
                if not monitor_info:
                    raise DirectXCaptureError(f"Invalid monitor ID: {region.monitor_id}")
                self._capture_engine.set_capture_region(region)
            
            frame = self._capture_engine.capture_single_frame()
            if frame is None:
                raise DirectXCaptureError("Failed to capture frame")
            
            return frame
            
        except Exception as e:
            self.logger.error(f"Frame capture failed: {e}")
            raise DirectXCaptureError(f"Capture failed: {e}")
    
    def set_capture_mode(self, mode: str) -> bool:
        """
        Set the capture mode.
        
        Args:
            mode: Capture mode string
            
        Returns:
            bool: True if mode set successfully
        """
        try:
            capture_mode = CaptureMode(mode)
            
            if capture_mode == CaptureMode.DIRECTX and not self._capture_engine.is_available():
                self.logger.warning("DirectX mode requested but not available, using fallback")
                return False
            
            self._current_mode = capture_mode
            self.logger.info(f"Capture mode set to: {mode}")
            return True
            
        except ValueError:
            self.logger.error(f"Invalid capture mode: {mode}")
            return False
    
    def get_supported_modes(self) -> List[str]:
        """
        Get list of supported capture modes.
        
        Returns:
            List[str]: List of supported capture mode names
        """
        return self._capture_engine.get_supported_modes()
    
    def configure_capture_rate(self, fps: int) -> bool:
        """
        Configure the capture frame rate.
        
        Args:
            fps: Target frames per second
            
        Returns:
            bool: True if frame rate configured successfully
        """
        return self._capture_engine.set_frame_rate(fps)
    
    def is_available(self) -> bool:
        """
        Check if capture functionality is available.
        
        Returns:
            bool: True if capture is available
        """
        return self._capture_engine.get_status() != CaptureStatus.UNAVAILABLE
    
    def start_continuous_capture(self, callback: Callable[[Frame], None]) -> bool:
        """
        Start continuous frame capture with callback.
        
        Args:
            callback: Function to call with each captured frame
            
        Returns:
            bool: True if continuous capture started successfully
        """
        self._capture_engine.add_frame_callback(callback)
        return self._capture_engine.start_capture()
    
    def stop_continuous_capture(self) -> bool:
        """
        Stop continuous frame capture.
        
        Returns:
            bool: True if capture stopped successfully
        """
        return self._capture_engine.stop_capture()
    
    def set_performance_profile(self, profile: PerformanceProfile) -> None:
        """
        Set performance profile for adaptive optimization.
        
        Args:
            profile: Performance profile
        """
        self._capture_engine.set_performance_profile(profile)
    
    def get_capture_statistics(self) -> Dict[str, Any]:
        """
        Get capture performance statistics.
        
        Returns:
            Dict[str, Any]: Capture statistics
        """
        return self._capture_engine.get_capture_stats()
    
    def get_available_monitors(self) -> Dict[int, MonitorInfo]:
        """
        Get information about all available monitors.
        
        Returns:
            Dict[int, MonitorInfo]: Dictionary of monitor ID to monitor info
        """
        return self._capture_engine.get_available_monitors()
    
    def get_primary_monitor_id(self) -> Optional[int]:
        """
        Get the ID of the primary monitor.
        
        Returns:
            Optional[int]: Primary monitor ID or None if not found
        """
        return self._capture_engine.get_primary_monitor_id()
    
    def create_full_screen_region(self, monitor_id: Optional[int] = None) -> Optional[CaptureRegion]:
        """
        Create a capture region for full screen capture.
        
        Args:
            monitor_id: Optional monitor ID, uses all monitors if None
            
        Returns:
            Optional[CaptureRegion]: Full screen capture region or None if failed
        """
        return self._capture_engine.create_full_screen_region(monitor_id)
    
    def create_monitor_region(self, monitor_id: int, 
                            custom_region: Optional[Rectangle] = None) -> Optional[CaptureRegion]:
        """
        Create a capture region for a specific monitor.
        
        Args:
            monitor_id: Monitor ID
            custom_region: Optional custom region within the monitor
            
        Returns:
            Optional[CaptureRegion]: Capture region or None if failed
        """
        return self._capture_engine.create_monitor_region(monitor_id, custom_region)
    
    def refresh_monitors(self) -> bool:
        """
        Refresh monitor information.
        
        Returns:
            bool: True if refresh successful
        """
        return self._capture_engine.refresh_monitors()
    
    def get_monitor_summary(self) -> Dict[str, Any]:
        """
        Get a summary of monitor configuration.
        
        Returns:
            Dict[str, Any]: Monitor summary
        """
        return self._capture_engine.get_monitor_summary()
    
    def cleanup(self) -> None:
        """Clean up capture resources."""
        self._capture_engine.cleanup()