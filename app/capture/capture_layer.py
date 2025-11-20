"""
Main Capture Layer Implementation

Provides unified interface for screen capture with multiple backend support
including DirectX Desktop Duplication API and fallback screenshot capture.
"""

import logging
from typing import Optional, List, Dict, Any, Callable, Tuple
import time
import threading
from enum import Enum

try:
    from ..models import Frame, CaptureRegion, Rectangle, CaptureMode, PerformanceProfile
    from ..interfaces import ICaptureLayer, CaptureSource
    from .directx_capture import DirectXCaptureLayer, DirectXCaptureError, CaptureStatus
    from .multi_monitor_support import MultiMonitorManager, MonitorInfo
    from .screenshot_capture import FallbackScreenshotCapture, ScreenshotCaptureError
except ImportError:
    try:
        from app.models import Frame, CaptureRegion, Rectangle, CaptureMode, PerformanceProfile
        from app.interfaces import ICaptureLayer, CaptureSource
        from app.capture.directx_capture import DirectXCaptureLayer, DirectXCaptureError, CaptureStatus
        from app.capture.multi_monitor_support import MultiMonitorManager, MonitorInfo
        from app.capture.screenshot_capture import FallbackScreenshotCapture, ScreenshotCaptureError
    except ImportError:
        from models import Frame, CaptureRegion, Rectangle, CaptureMode, PerformanceProfile
        from interfaces import ICaptureLayer, CaptureSource
        from directx_capture import DirectXCaptureLayer, DirectXCaptureError, CaptureStatus
        from app.capture.multi_monitor_support import MultiMonitorManager, MonitorInfo
        from app.capture.screenshot_capture import FallbackScreenshotCapture, ScreenshotCaptureError


class CaptureBackend(Enum):
    """Available capture backends."""
    DIRECTX = "directx"
    SCREENSHOT = "screenshot"
    AUTO = "auto"


class CaptureLayerError(Exception):
    """Capture layer specific exceptions."""
    pass


class FallbackDetectionSystem:
    """
    Automatic fallback detection and switching mechanism.
    
    Monitors capture performance and automatically switches between DirectX
    and screenshot capture based on availability and performance metrics.
    """
    
    def __init__(self, logger: Optional[logging.Logger] = None):
        """
        Initialize fallback detection system.
        
        Args:
            logger: Optional logger for debugging
        """
        self.logger = logger or logging.getLogger(__name__)
        
        # Enable/disable flag
        self._enabled = True
        
        # Fallback thresholds
        self._failure_threshold = 20  # Consecutive failures before fallback (increased from 5)
        self._performance_threshold = 0.3  # Performance ratio threshold (more lenient)
        self._recovery_attempts = 5  # Attempts to recover primary backend
        
        # State tracking
        self._consecutive_failures = 0
        self._recovery_attempt_count = 0
        self._last_fallback_time = 0
        self._fallback_cooldown = 10.0  # Seconds between fallback attempts
        
        # Performance tracking
        self._performance_history = []
        self._max_history_size = 30
    
    def set_enabled(self, enabled: bool) -> None:
        """
        Enable or disable fallback detection.
        
        Args:
            enabled: True to enable, False to disable
        """
        self._enabled = enabled
        if not enabled:
            # Reset state when disabled
            self._consecutive_failures = 0
            self._recovery_attempt_count = 0
        
    def should_attempt_fallback(self, current_backend: CaptureBackend, 
                              capture_success: bool, capture_time: float) -> bool:
        """
        Determine if fallback should be attempted.
        
        Args:
            current_backend: Currently active backend
            capture_success: Whether last capture was successful
            capture_time: Time taken for last capture
            
        Returns:
            bool: True if fallback should be attempted
        """
        # Check if fallback is enabled
        if not self._enabled:
            return False
        
        current_time = time.time()
        
        # Check cooldown period
        if current_time - self._last_fallback_time < self._fallback_cooldown:
            return False
        
        # Track failures
        if not capture_success:
            self._consecutive_failures += 1
        else:
            self._consecutive_failures = 0
        
        # Track performance
        self._performance_history.append(capture_time)
        if len(self._performance_history) > self._max_history_size:
            self._performance_history.pop(0)
        
        # Check failure threshold
        if self._consecutive_failures >= self._failure_threshold:
            self.logger.warning(f"Fallback triggered by consecutive failures: {self._consecutive_failures}")
            self._last_fallback_time = current_time
            return True
        
        # Check performance threshold
        if len(self._performance_history) >= 10:
            avg_capture_time = sum(self._performance_history[-10:]) / 10
            expected_time = 1.0 / 30.0  # 30 FPS baseline
            
            if avg_capture_time > expected_time / self._performance_threshold:
                self.logger.warning(f"Fallback triggered by poor performance: {avg_capture_time:.3f}s avg")
                self._last_fallback_time = current_time
                return True
        
        return False
    
    def should_attempt_recovery(self, current_backend: CaptureBackend) -> bool:
        """
        Determine if recovery to primary backend should be attempted.
        
        Args:
            current_backend: Currently active backend
            
        Returns:
            bool: True if recovery should be attempted
        """
        # Check if fallback is enabled
        if not self._enabled:
            return False
        
        current_time = time.time()
        
        # Only attempt recovery if we're on fallback backend
        if current_backend != CaptureBackend.SCREENSHOT:
            return False
        
        # Check if we've exceeded recovery attempts
        if self._recovery_attempt_count >= self._recovery_attempts:
            return False
        
        # Check cooldown period (longer for recovery)
        if current_time - self._last_fallback_time < self._fallback_cooldown * 2:
            return False
        
        # Check if performance has stabilized
        if len(self._performance_history) >= 20:
            recent_performance = self._performance_history[-20:]
            if all(t < 0.1 for t in recent_performance):  # Good performance
                self.logger.info("Attempting recovery to primary backend")
                self._recovery_attempt_count += 1
                return True
        
        return False
    
    def reset_recovery_attempts(self) -> None:
        """Reset recovery attempt counter."""
        self._recovery_attempt_count = 0
    
    def get_fallback_statistics(self) -> Dict[str, Any]:
        """
        Get fallback detection statistics.
        
        Returns:
            Dict[str, Any]: Fallback statistics
        """
        avg_performance = (sum(self._performance_history) / len(self._performance_history) 
                         if self._performance_history else 0)
        
        return {
            'consecutive_failures': self._consecutive_failures,
            'recovery_attempts': self._recovery_attempt_count,
            'average_capture_time': avg_performance,
            'performance_samples': len(self._performance_history),
            'last_fallback_time': self._last_fallback_time
        }


# ScreenshotCapture class has been replaced by FallbackScreenshotCapture
# in screenshot_capture.py for enhanced functionality and better error handling


class AdaptiveCaptureController:
    """
    Adaptive capture controller that manages frame rate and quality based on performance.
    
    Monitors capture performance and automatically adjusts settings to maintain
    target performance while maximizing quality.
    """
    
    def __init__(self, logger: Optional[logging.Logger] = None):
        """
        Initialize adaptive capture controller.
        
        Args:
            logger: Optional logger for debugging
        """
        self.logger = logger or logging.getLogger(__name__)
        self._enabled = True
        self._target_fps = 30
        self._current_fps = 0
        self._frame_times = []
        self._max_frame_history = 30
        self._adjustment_threshold = 0.8  # Adjust if performance drops below 80% of target
        self._last_adjustment_time = 0
        self._adjustment_cooldown = 5.0  # Seconds between adjustments
    
    def set_enabled(self, enabled: bool) -> None:
        """
        Enable or disable adaptive capture control.
        
        Args:
            enabled: True to enable, False to disable
        """
        self._enabled = enabled
        if not enabled:
            # Reset state when disabled
            self._frame_times = []
            self._current_fps = 0
        
    def set_target_fps(self, fps: int) -> None:
        """
        Set target FPS for adaptive control.
        
        Args:
            fps: Target frames per second
        """
        self._target_fps = fps
        self.logger.debug(f"Adaptive controller target FPS set to {fps}")
    
    def record_frame_time(self, frame_time: float) -> None:
        """
        Record frame capture time for performance monitoring.
        
        Args:
            frame_time: Time taken to capture frame in seconds
        """
        self._frame_times.append(frame_time)
        
        # Keep only recent frame times
        if len(self._frame_times) > self._max_frame_history:
            self._frame_times.pop(0)
        
        # Calculate current FPS
        if len(self._frame_times) >= 5:
            avg_frame_time = sum(self._frame_times[-5:]) / 5
            self._current_fps = 1.0 / avg_frame_time if avg_frame_time > 0 else 0
    
    def should_adjust_settings(self) -> bool:
        """
        Check if capture settings should be adjusted.
        
        Returns:
            bool: True if settings should be adjusted
        """
        # Check if adaptive control is enabled
        if not self._enabled:
            return False
        current_time = time.time()
        
        # Check cooldown period
        if current_time - self._last_adjustment_time < self._adjustment_cooldown:
            return False
        
        # Check if performance is below threshold
        if len(self._frame_times) >= 10:
            performance_ratio = self._current_fps / self._target_fps
            if performance_ratio < self._adjustment_threshold:
                self._last_adjustment_time = current_time
                return True
        
        return False
    
    def get_recommended_adjustments(self) -> Dict[str, Any]:
        """
        Get recommended performance adjustments.
        
        Returns:
            Dict[str, Any]: Dictionary of recommended adjustments
        """
        performance_ratio = self._current_fps / self._target_fps if self._target_fps > 0 else 1.0
        
        adjustments = {}
        
        if performance_ratio < 0.5:
            # Severe performance issues
            adjustments['frame_rate_reduction'] = 0.5
            adjustments['quality_reduction'] = 0.3
            adjustments['suggested_profile'] = PerformanceProfile.LOW
        elif performance_ratio < 0.8:
            # Moderate performance issues
            adjustments['frame_rate_reduction'] = 0.2
            adjustments['quality_reduction'] = 0.1
            adjustments['suggested_profile'] = PerformanceProfile.NORMAL
        
        return adjustments
    
    def get_performance_metrics(self) -> Dict[str, float]:
        """
        Get current performance metrics.
        
        Returns:
            Dict[str, float]: Performance metrics
        """
        return {
            'current_fps': self._current_fps,
            'target_fps': self._target_fps,
            'performance_ratio': self._current_fps / self._target_fps if self._target_fps > 0 else 1.0,
            'avg_frame_time': sum(self._frame_times) / len(self._frame_times) if self._frame_times else 0
        }


class CaptureLayer(ICaptureLayer):
    """
    Main capture layer implementation with multiple backend support.
    
    Provides unified interface for screen capture with automatic backend selection,
    fallback support, and adaptive performance optimization.
    """
    
    def __init__(self, logger: Optional[logging.Logger] = None):
        """
        Initialize capture layer with multiple backends.
        
        Args:
            logger: Optional logger for debugging and monitoring
        """
        self.logger = logger or logging.getLogger(__name__)
        
        try:
            # Initialize capture backends
            print("[CAPTURE LAYER] Initializing DirectX capture...")
            self._directx_capture = DirectXCaptureLayer(logger)
            print("[CAPTURE LAYER] DirectX capture initialized")
            
            # Screenshot capture not used - capture uses plugin system instead
            # Only dxcam plugin is loaded via plugin manager
            self._screenshot_capture = None
            print("[CAPTURE LAYER] Screenshot capture not initialized (using plugin system)")
            
            # Initialize fallback detection system
            self._fallback_detector = FallbackDetectionSystem(logger)
            
            # Determine active backend
            self._active_backend = self._select_optimal_backend()
            
            # Initialize adaptive controller
            self._adaptive_controller = AdaptiveCaptureController(logger)
            
            # Capture state
            self._current_region: Optional[CaptureRegion] = None
            self._frame_rate = 30
            self._performance_profile = PerformanceProfile.NORMAL
            self._continuous_capture_active = False
            self._capture_thread: Optional[threading.Thread] = None
            self._stop_event = threading.Event()
            self._frame_callbacks: List[Callable[[Frame], None]] = []
            
            # Statistics
            self._stats = {
                'total_frames': 0,
                'successful_captures': 0,
                'failed_captures': 0,
                'backend_switches': 0,
                'average_capture_time': 0,
                'fallback_triggers': 0,
                'recovery_attempts': 0
            }
            
            self.logger.info(f"Capture layer initialized with backend: {self._active_backend.value}")
            print(f"[CAPTURE LAYER] Initialization complete with backend: {self._active_backend.value}")
            
        except Exception as e:
            print(f"[CAPTURE LAYER] FATAL ERROR during initialization: {e}")
            import traceback
            traceback.print_exc()
            raise
    

    def _select_optimal_backend(self) -> CaptureBackend:
        """
        Select optimal capture backend based on availability and performance.
        
        Returns:
            CaptureBackend: Selected backend
        """
        if self._directx_capture.is_available():
            self.logger.info("DirectX capture available, using DirectX backend")
            return CaptureBackend.DIRECTX
        else:
            self.logger.error("DirectX not available and screenshot is disabled")
            return CaptureBackend.DIRECTX  # Still return DirectX as default
    
    def capture_frame(self, source: CaptureSource, region: CaptureRegion) -> Frame:
        """
        Capture a frame from the specified source and region.
        
        Args:
            source: Capture source type
            region: Region to capture
            
        Returns:
            Frame: Captured frame data
            
        Raises:
            CaptureLayerError: If capture fails with all backends
        """
        start_time = time.time()
        
        try:
            self._current_region = region
            
            # Try primary backend
            frame = self._capture_with_backend(source, region, self._active_backend)
            capture_success = frame is not None
            capture_time = time.time() - start_time
            
            # Check if fallback should be attempted
            if self._fallback_detector.should_attempt_fallback(
                self._active_backend, capture_success, capture_time):
                
                fallback_backend = self._get_fallback_backend()
                if fallback_backend != self._active_backend:
                    self.logger.warning(f"Automatic fallback triggered, switching to: {fallback_backend.value}")
                    fallback_frame = self._capture_with_backend(source, region, fallback_backend)
                    
                    if fallback_frame is not None:
                        frame = fallback_frame
                        self._active_backend = fallback_backend
                        self._stats['backend_switches'] += 1
                        self._stats['fallback_triggers'] += 1
                        self.logger.info(f"Successfully switched to fallback backend: {fallback_backend.value}")
            
            # Check if recovery should be attempted
            elif self._fallback_detector.should_attempt_recovery(self._active_backend):
                primary_backend = CaptureBackend.DIRECTX
                if primary_backend != self._active_backend and self._directx_capture.is_available():
                    self.logger.info("Attempting recovery to primary backend")
                    recovery_frame = self._capture_with_backend(source, region, primary_backend)
                    
                    if recovery_frame is not None:
                        frame = recovery_frame
                        self._active_backend = primary_backend
                        self._stats['backend_switches'] += 1
                        self._stats['recovery_attempts'] += 1
                        self._fallback_detector.reset_recovery_attempts()
                        self.logger.info("Successfully recovered to primary backend")
            
            if frame is None:
                self._stats['failed_captures'] += 1
                raise CaptureLayerError("All capture backends failed")
            
            # Update statistics
            final_capture_time = time.time() - start_time
            self._adaptive_controller.record_frame_time(final_capture_time)
            self._update_capture_stats(final_capture_time)
            
            return frame
            
        except Exception as e:
            self._stats['failed_captures'] += 1
            self.logger.error(f"Frame capture failed: {e}")
            raise CaptureLayerError(f"Capture failed: {e}")
    
    def _capture_with_backend(self, source: CaptureSource, region: CaptureRegion, 
                            backend: CaptureBackend) -> Optional[Frame]:
        """
        Capture frame with specific backend.
        
        Args:
            source: Capture source type
            region: Region to capture
            backend: Backend to use for capture
            
        Returns:
            Optional[Frame]: Captured frame or None if failed
        """
        try:
            if backend == CaptureBackend.DIRECTX:
                return self._directx_capture.capture_frame(source, region)
            elif backend == CaptureBackend.SCREENSHOT:
                if self._screenshot_capture:
                    return self._screenshot_capture.capture_frame(region)
                else:
                    self.logger.error("Screenshot backend requested but disabled")
                    return None
            else:
                self.logger.error(f"Unknown backend: {backend}")
                return None
                
        except Exception as e:
            self.logger.error(f"Backend {backend.value} capture failed: {e}")
            return None
    
    def _get_fallback_backend(self) -> CaptureBackend:
        """
        Get fallback backend for current active backend.
        
        Returns:
            CaptureBackend: Fallback backend
        """
        if self._active_backend == CaptureBackend.DIRECTX:
            return CaptureBackend.SCREENSHOT
        else:
            return CaptureBackend.DIRECTX
    
    def set_capture_mode(self, mode: str) -> bool:
        """
        Set the capture mode.
        
        Args:
            mode: Capture mode string
            
        Returns:
            bool: True if mode set successfully
        """
        try:
            if mode == CaptureMode.DIRECTX.value:
                if self._directx_capture.is_available():
                    self._active_backend = CaptureBackend.DIRECTX
                    return self._directx_capture.set_capture_mode(mode)
                else:
                    self.logger.warning("DirectX mode requested but not available")
                    return False
            elif mode == CaptureMode.SCREENSHOT.value:
                self._active_backend = CaptureBackend.SCREENSHOT
                return True
            else:
                return self._directx_capture.set_capture_mode(mode)
                
        except Exception as e:
            self.logger.error(f"Failed to set capture mode {mode}: {e}")
            return False
    
    def get_supported_modes(self) -> List[str]:
        """
        Get list of supported capture modes.
        
        Returns:
            List[str]: List of supported capture mode names
        """
        modes = []
        
        # Add DirectX modes if available
        if self._directx_capture.is_available():
            modes.extend(self._directx_capture.get_supported_modes())
        
        # Add screenshot mode (always available as fallback)
        if CaptureMode.SCREENSHOT.value not in modes:
            modes.append(CaptureMode.SCREENSHOT.value)
        
        return modes
    
    def configure_capture_rate(self, fps: int) -> bool:
        """
        Configure the capture frame rate.
        
        Args:
            fps: Target frames per second
            
        Returns:
            bool: True if frame rate configured successfully
        """
        if not 1 <= fps <= 120:
            self.logger.error(f"Invalid frame rate: {fps}")
            return False
        
        self._frame_rate = fps
        self._adaptive_controller.set_target_fps(fps)
        
        # Configure backends
        success = True
        if self._directx_capture.is_available():
            success &= self._directx_capture.configure_capture_rate(fps)
        
        if self._screenshot_capture:
            success &= self._screenshot_capture.set_frame_rate(fps)
        
        self.logger.info(f"Frame rate configured to {fps} FPS")
        return success
    
    def is_available(self) -> bool:
        """
        Check if capture functionality is available.
        
        Returns:
            bool: True if at least one capture backend is available
        """
        return self._directx_capture.is_available()
    
    def set_performance_profile(self, profile: PerformanceProfile) -> None:
        """
        Set performance profile for all backends.
        
        Args:
            profile: Performance profile
        """
        self._performance_profile = profile
        
        # Configure backends
        if self._directx_capture.is_available():
            self._directx_capture.set_performance_profile(profile)
        
        if self._screenshot_capture:
            self._screenshot_capture.set_performance_profile(profile)
        
        # Adjust frame rate based on profile
        if profile == PerformanceProfile.LOW:
            self.configure_capture_rate(min(self._frame_rate, 15))
        elif profile == PerformanceProfile.NORMAL:
            self.configure_capture_rate(min(self._frame_rate, 30))
        elif profile == PerformanceProfile.HIGH:
            self.configure_capture_rate(min(self._frame_rate, 60))
        
        self.logger.info(f"Performance profile set to {profile.value}")
    
    def set_adaptive_capture(self, enabled: bool) -> None:
        """
        Enable or disable adaptive capture rate adjustment.
        
        Args:
            enabled: True to enable adaptive capture, False to disable
        """
        if hasattr(self._adaptive_controller, 'set_enabled'):
            self._adaptive_controller.set_enabled(enabled)
        self.logger.info(f"Adaptive capture {'enabled' if enabled else 'disabled'}")
    
    def set_fallback_enabled(self, enabled: bool) -> None:
        """
        Enable or disable automatic fallback between capture backends.
        
        Args:
            enabled: True to enable fallback, False to disable
        """
        if hasattr(self._fallback_detector, 'set_enabled'):
            self._fallback_detector.set_enabled(enabled)
        elif hasattr(self._fallback_detector, '_enabled'):
            self._fallback_detector._enabled = enabled
        self.logger.info(f"Fallback mode {'enabled' if enabled else 'disabled'}")
    
    def start_continuous_capture(self, callback: Callable[[Frame], None]) -> bool:
        """
        Start continuous frame capture.
        
        Args:
            callback: Function to call with each captured frame
            
        Returns:
            bool: True if continuous capture started successfully
        """
        if self._continuous_capture_active:
            self.logger.warning("Continuous capture already active")
            return True
        
        if not self._current_region:
            self.logger.error("No capture region set")
            return False
        
        try:
            self._frame_callbacks.append(callback)
            self._stop_event.clear()
            self._capture_thread = threading.Thread(target=self._continuous_capture_loop, daemon=True)
            self._capture_thread.start()
            self._continuous_capture_active = True
            
            self.logger.info("Continuous capture started")
            return True
            
        except Exception as e:
            self.logger.error(f"Failed to start continuous capture: {e}")
            return False
    
    def stop_continuous_capture(self) -> bool:
        """
        Stop continuous frame capture.
        
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
            
            self.logger.info("Continuous capture stopped")
            return True
            
        except Exception as e:
            self.logger.error(f"Failed to stop continuous capture: {e}")
            return False
    
    def _continuous_capture_loop(self) -> None:
        """Continuous capture loop running in separate thread."""
        frame_interval = 1.0 / self._frame_rate
        last_capture_time = 0
        
        self.logger.debug(f"Continuous capture loop started with {self._frame_rate} FPS target")
        
        while not self._stop_event.is_set():
            current_time = time.time()
            
            # Frame rate limiting
            if current_time - last_capture_time < frame_interval:
                time.sleep(0.001)
                continue
            
            try:
                # Capture frame
                frame = self.capture_frame(CaptureSource.CUSTOM_REGION, self._current_region)
                
                # Notify callbacks
                for callback in self._frame_callbacks:
                    try:
                        callback(frame)
                    except Exception as e:
                        self.logger.error(f"Frame callback error: {e}")
                
                # Check for adaptive adjustments
                if self._adaptive_controller.should_adjust_settings():
                    self._apply_adaptive_adjustments()
                
                last_capture_time = current_time
                
            except Exception as e:
                self.logger.error(f"Continuous capture loop error: {e}")
                time.sleep(0.1)
    
    def _apply_adaptive_adjustments(self) -> None:
        """Apply adaptive performance adjustments."""
        adjustments = self._adaptive_controller.get_recommended_adjustments()
        
        if adjustments:
            self.logger.info(f"Applying adaptive adjustments: {adjustments}")
            
            # Adjust frame rate
            if 'frame_rate_reduction' in adjustments:
                new_fps = int(self._frame_rate * (1 - adjustments['frame_rate_reduction']))
                self.configure_capture_rate(max(new_fps, 5))
            
            # Adjust performance profile
            if 'suggested_profile' in adjustments:
                self.set_performance_profile(adjustments['suggested_profile'])
    
    def _update_capture_stats(self, capture_time: float) -> None:
        """Update capture statistics."""
        self._stats['total_frames'] += 1
        self._stats['successful_captures'] += 1
        
        # Update average capture time
        if self._stats['total_frames'] > 1:
            self._stats['average_capture_time'] = (
                (self._stats['average_capture_time'] * (self._stats['total_frames'] - 1) + capture_time) /
                self._stats['total_frames']
            )
        else:
            self._stats['average_capture_time'] = capture_time
    
    def get_capture_statistics(self) -> Dict[str, Any]:
        """
        Get comprehensive capture statistics.
        
        Returns:
            Dict[str, Any]: Capture statistics including performance metrics
        """
        stats = self._stats.copy()
        stats.update({
            'active_backend': self._active_backend.value,
            'frame_rate': self._frame_rate,
            'performance_profile': self._performance_profile.value,
            'adaptive_metrics': self._adaptive_controller.get_performance_metrics()
        })
        
        # Add backend-specific stats
        if self._active_backend == CaptureBackend.DIRECTX:
            stats['backend_stats'] = self._directx_capture.get_capture_statistics()
        elif self._active_backend == CaptureBackend.SCREENSHOT:
            if self._screenshot_capture:
                stats['backend_stats'] = self._screenshot_capture.get_capture_statistics()
        
        # Add fallback detection stats
        stats['fallback_stats'] = self._fallback_detector.get_fallback_statistics()
        
        return stats
    
    def get_status_info(self) -> Dict[str, Any]:
        """
        Get detailed status information.
        
        Returns:
            Dict[str, Any]: Status information
        """
        return {
            'available': self.is_available(),
            'active_backend': self._active_backend.value,
            'directx_available': self._directx_capture.is_available(),
            'screenshot_available': self._screenshot_capture.is_available() if self._screenshot_capture else False,
            'continuous_capture_active': self._continuous_capture_active,
            'supported_modes': self.get_supported_modes(),
            'current_region': self._current_region,
            'frame_rate': self._frame_rate,
            'performance_profile': self._performance_profile.value
        }
    
    def validate_capture_mode(self) -> Tuple[bool, str]:
        """
        Validate current capture mode and configuration.
        
        Returns:
            Tuple[bool, str]: (is_valid, validation_message)
        """
        try:
            # Check if any backend is available
            if not self.is_available():
                return False, "No capture backends available"
            
            # Validate active backend
            if self._active_backend == CaptureBackend.DIRECTX:
                if not self._directx_capture.is_available():
                    return False, "DirectX backend selected but not available"
            elif self._active_backend == CaptureBackend.SCREENSHOT:
                if not self._screenshot_capture or not self._screenshot_capture.is_available():
                    return False, "Screenshot backend selected but not available"
            
            # Validate screenshot backend specifically
            if self._active_backend == CaptureBackend.SCREENSHOT and self._screenshot_capture:
                screenshot_valid, screenshot_msg = self._screenshot_capture.validate_capture_mode()
                if not screenshot_valid:
                    return False, f"Screenshot backend validation failed: {screenshot_msg}"
            
            # Check capture region if set
            if self._current_region:
                rect = self._current_region.rectangle
                if rect.width <= 0 or rect.height <= 0:
                    return False, "Invalid capture region dimensions"
                
                # Check for reasonable size limits
                if rect.width > 7680 or rect.height > 4320:  # 8K resolution
                    return False, "Capture region exceeds maximum supported size"
            
            # Check frame rate configuration
            if not 1 <= self._frame_rate <= 120:
                return False, f"Invalid frame rate: {self._frame_rate}"
            
            return True, "Capture mode validation successful"
            
        except Exception as e:
            return False, f"Capture mode validation error: {e}"
    
    def handle_capture_error(self, error: Exception, context: Dict[str, Any]) -> bool:
        """
        Handle capture errors with automatic recovery attempts.
        
        Args:
            error: The capture error that occurred
            context: Additional context about the error
            
        Returns:
            bool: True if error was handled and recovery attempted
        """
        try:
            self.logger.error(f"Capture error occurred: {error}")
            self.logger.debug(f"Error context: {context}")
            
            # Increment error statistics
            self._stats['failed_captures'] += 1
            
            # Determine error type and appropriate response
            if isinstance(error, DirectXCaptureError):
                self.logger.warning("DirectX capture error, attempting fallback to screenshot")
                if self._screenshot_capture and self._screenshot_capture.is_available():
                    self._active_backend = CaptureBackend.SCREENSHOT
                    self._stats['backend_switches'] += 1
                    return True
            
            elif isinstance(error, ScreenshotCaptureError):
                self.logger.warning("Screenshot capture error, attempting fallback to DirectX")
                if self._directx_capture.is_available():
                    self._active_backend = CaptureBackend.DIRECTX
                    self._stats['backend_switches'] += 1
                    return True
            
            # Generic error handling
            elif "access" in str(error).lower():
                self.logger.warning("Access denied error, may need elevated permissions")
                # Try switching backends as access requirements may differ
                fallback_backend = self._get_fallback_backend()
                if fallback_backend != self._active_backend:
                    self._active_backend = fallback_backend
                    self._stats['backend_switches'] += 1
                    return True
            
            elif "memory" in str(error).lower() or "resource" in str(error).lower():
                self.logger.warning("Resource error, reducing performance profile")
                # Automatically reduce performance profile
                if self._performance_profile == PerformanceProfile.HIGH:
                    self.set_performance_profile(PerformanceProfile.NORMAL)
                elif self._performance_profile == PerformanceProfile.NORMAL:
                    self.set_performance_profile(PerformanceProfile.LOW)
                return True
            
            return False
            
        except Exception as e:
            self.logger.error(f"Error in capture error handler: {e}")
            return False
    
    def get_error_recovery_suggestions(self) -> List[str]:
        """
        Get suggestions for error recovery based on current state.
        
        Returns:
            List[str]: List of recovery suggestions
        """
        suggestions = []
        
        try:
            # Check backend availability
            screenshot_available = self._screenshot_capture.is_available() if self._screenshot_capture else False
            if not self._directx_capture.is_available() and not screenshot_available:
                suggestions.append("No capture methods available - check system permissions and dependencies")
            
            elif not self._directx_capture.is_available():
                suggestions.append("DirectX capture unavailable - try running as administrator or updating graphics drivers")
                suggestions.append("Screenshot capture is available as fallback")
            
            elif not screenshot_available:
                suggestions.append("Screenshot capture unavailable - install PIL or win32 libraries")
                suggestions.append("DirectX capture is available")
            
            # Check performance issues
            if self._stats['failed_captures'] > self._stats['successful_captures']:
                suggestions.append("High failure rate - consider reducing frame rate or capture region size")
                suggestions.append("Try switching to a lower performance profile")
            
            # Check fallback statistics
            fallback_stats = self._fallback_detector.get_fallback_statistics()
            if fallback_stats['consecutive_failures'] > 3:
                suggestions.append("Multiple consecutive failures - restart application or check system resources")
            
            # Check capture region
            if self._current_region:
                rect = self._current_region.rectangle
                if rect.width * rect.height > 1920 * 1080:
                    suggestions.append("Large capture region may cause performance issues - consider reducing size")
            
            return suggestions
            
        except Exception as e:
            self.logger.error(f"Error generating recovery suggestions: {e}")
            return ["Unable to generate recovery suggestions due to internal error"]
    
    def get_available_monitors(self) -> Dict[int, MonitorInfo]:
        """
        Get information about all available monitors.
        
        Returns:
            Dict[int, MonitorInfo]: Dictionary of monitor ID to monitor info
        """
        if self._directx_capture and self._directx_capture.is_available():
            return self._directx_capture.get_available_monitors()
        else:
            # Fallback: create basic monitor manager
            monitor_manager = MultiMonitorManager(self.logger)
            return monitor_manager.get_all_monitors()
    
    def get_primary_monitor_id(self) -> Optional[int]:
        """
        Get the ID of the primary monitor.
        
        Returns:
            Optional[int]: Primary monitor ID or None if not found
        """
        if self._directx_capture and self._directx_capture.is_available():
            return self._directx_capture.get_primary_monitor_id()
        else:
            # Fallback: create basic monitor manager
            monitor_manager = MultiMonitorManager(self.logger)
            return monitor_manager.get_primary_monitor_id()
    
    def create_full_screen_region(self, monitor_id: Optional[int] = None) -> Optional[CaptureRegion]:
        """
        Create a capture region for full screen capture.
        
        Args:
            monitor_id: Optional monitor ID, uses all monitors if None
            
        Returns:
            Optional[CaptureRegion]: Full screen capture region or None if failed
        """
        if self._directx_capture and self._directx_capture.is_available():
            return self._directx_capture.create_full_screen_region(monitor_id)
        else:
            # Fallback: create basic monitor manager
            monitor_manager = MultiMonitorManager(self.logger)
            if monitor_id is None:
                return monitor_manager.create_full_screen_region()
            else:
                return monitor_manager.create_capture_region_for_monitor(monitor_id)
    
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
        if self._directx_capture and self._directx_capture.is_available():
            return self._directx_capture.create_monitor_region(monitor_id, custom_region)
        else:
            # Fallback: create basic monitor manager
            monitor_manager = MultiMonitorManager(self.logger)
            return monitor_manager.create_capture_region_for_monitor(monitor_id, custom_region)
    
    def refresh_monitors(self) -> bool:
        """
        Refresh monitor information (useful when displays are added/removed).
        
        Returns:
            bool: True if refresh successful
        """
        success = True
        
        if self._directx_capture and self._directx_capture.is_available():
            success &= self._directx_capture.refresh_monitors()
        
        # Update statistics
        monitors = self.get_available_monitors()
        self._stats['active_monitors'] = len(monitors)
        
        self.logger.info(f"Monitor refresh completed: {len(monitors)} monitors detected")
        return success
    
    def get_monitor_summary(self) -> Dict[str, Any]:
        """
        Get a summary of monitor configuration.
        
        Returns:
            Dict[str, Any]: Monitor summary including capture capabilities
        """
        if self._directx_capture and self._directx_capture.is_available():
            summary = self._directx_capture.get_monitor_summary()
        else:
            # Fallback: create basic monitor manager
            monitor_manager = MultiMonitorManager(self.logger)
            summary = monitor_manager.get_monitor_summary()
        
        # Add capture layer specific information
        summary['capture_backend'] = self._active_backend.value
        summary['directx_available'] = self._directx_capture.is_available() if self._directx_capture else False
        summary['screenshot_available'] = self._screenshot_capture.is_available() if self._screenshot_capture else False
        
        return summary
    
    def validate_capture_region_for_monitor(self, region: CaptureRegion) -> Tuple[bool, str]:
        """
        Validate a capture region against available monitors.
        
        Args:
            region: Capture region to validate
            
        Returns:
            Tuple[bool, str]: (is_valid, error_message)
        """
        try:
            monitors = self.get_available_monitors()
            
            # Check if monitor exists
            if region.monitor_id not in monitors:
                return False, f"Monitor {region.monitor_id} not found"
            
            monitor = monitors[region.monitor_id]
            
            # Check if region is within monitor bounds
            monitor_bounds = monitor.bounds
            region_rect = region.rectangle
            
            if (region_rect.x < monitor_bounds.x or 
                region_rect.y < monitor_bounds.y or
                region_rect.x + region_rect.width > monitor_bounds.x + monitor_bounds.width or
                region_rect.y + region_rect.height > monitor_bounds.y + monitor_bounds.height):
                return False, f"Region extends beyond monitor {region.monitor_id} bounds"
            
            return True, "Valid"
            
        except Exception as e:
            return False, f"Validation error: {e}"
    
    def cleanup(self) -> None:
        """Clean up capture resources."""
        try:
            self.stop_continuous_capture()
            
            if self._directx_capture:
                self._directx_capture.cleanup()
            
            if self._screenshot_capture:
                self._screenshot_capture.cleanup()
            
            self.logger.info("Capture layer cleaned up")
            
        except Exception as e:
            self.logger.error(f"Cleanup error: {e}")