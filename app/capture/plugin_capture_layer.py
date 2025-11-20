"""
Plugin-Based Capture Layer

Uses subprocess-isolated capture plugins to avoid GPU conflicts with OCR.
Each capture method runs in its own process for maximum stability.
"""

import logging
import numpy as np
import base64
from typing import Optional, List, Dict, Any
from enum import Enum

try:
    from ..models import Frame, CaptureRegion, Rectangle, CaptureMode, PerformanceProfile
    from ..interfaces import ICaptureLayer, CaptureSource
    from .capture_plugin_manager import CapturePluginManager
except ImportError:
    from app.models import Frame, CaptureRegion, Rectangle, CaptureMode, PerformanceProfile
    from app.interfaces import ICaptureLayer, CaptureSource
    from app.capture.capture_plugin_manager import CapturePluginManager


class PluginCaptureLayer(ICaptureLayer):
    """
    Plugin-based capture layer with subprocess isolation.
    
    Benefits:
    - Process isolation (no GPU conflicts with OCR)
    - Crash isolation (plugin crash doesn't kill app)
    - Modular architecture (easy to add new capture methods)
    - Consistent with OCR plugin system
    """
    
    def __init__(self, logger: Optional[logging.Logger] = None, config_manager=None):
        """
        Initialize plugin-based capture layer.
        
        Args:
            logger: Optional logger for debugging
            config_manager: Configuration manager for runtime settings
        """
        self.logger = logger or logging.getLogger(__name__)
        self.config_manager = config_manager
        
        print("[PLUGIN CAPTURE] Initializing plugin-based capture layer...")
        
        # Get runtime mode from config
        self.runtime_mode = 'auto'
        if self.config_manager:
            self.runtime_mode = self.config_manager.get_setting('performance.runtime_mode', 'auto')
            print(f"[PLUGIN CAPTURE] Runtime mode: {self.runtime_mode}")
        
        # Create plugin manager
        self.plugin_manager = CapturePluginManager()
        
        # Discover available plugins
        print("[PLUGIN CAPTURE] Discovering capture plugins...")
        plugins = self.plugin_manager.discover_plugins()
        
        if not plugins:
            self.logger.warning("No capture plugins found!")
            print("[PLUGIN CAPTURE] ⚠ No capture plugins found")
        else:
            plugin_names = [p.name for p in plugins]
            print(f"[PLUGIN CAPTURE] Found {len(plugins)} plugin(s): {', '.join(plugin_names)}")
            self.logger.info(f"Discovered {len(plugins)} capture plugins: {plugin_names}")
        
        # State
        self._current_region: Optional[CaptureRegion] = None
        self._frame_rate = 30
        self._performance_profile = PerformanceProfile.NORMAL
        
        # Statistics
        self._stats = {
            'total_frames': 0,
            'successful_captures': 0,
            'failed_captures': 0,
            'average_capture_time': 0
        }
        
        print("[PLUGIN CAPTURE] Initialization complete")
    
    def capture_frame(self, source: CaptureSource, region: CaptureRegion) -> Frame:
        """
        Capture a frame using the active plugin.
        
        Args:
            source: Capture source type
            region: Region to capture
            
        Returns:
            Frame: Captured frame data
            
        Raises:
            RuntimeError: If capture fails
        """
        import time
        start_time = time.time()
        
        try:
            self._current_region = region
            
            # Prepare region data for plugin
            region_data = {
                'x': region.rectangle.x,
                'y': region.rectangle.y,
                'width': region.rectangle.width,
                'height': region.rectangle.height,
                'monitor_id': region.monitor_id
            }
            
            # Capture frame via plugin
            response = self.plugin_manager.capture_frame(region_data)
            
            if not response:
                self._stats['failed_captures'] += 1
                raise RuntimeError("Plugin returned no response")
            
            if 'error' in response:
                self._stats['failed_captures'] += 1
                raise RuntimeError(f"Plugin error: {response['error']}")
            
            # Decode frame data
            frame_data = self._decode_frame(response)
            
            if frame_data is None:
                self._stats['failed_captures'] += 1
                raise RuntimeError("Failed to decode frame data")
            
            # Create Frame object
            frame = Frame(
                data=frame_data,
                timestamp=time.time(),
                source_region=region,
                metadata={'source': source.value if hasattr(source, 'value') else str(source)}
            )
            
            # Update statistics
            capture_time = time.time() - start_time
            self._update_stats(capture_time)
            
            return frame
            
        except Exception as e:
            self._stats['failed_captures'] += 1
            self.logger.error(f"Frame capture failed: {e}")
            raise RuntimeError(f"Capture failed: {e}")
    
    def _decode_frame(self, response: Dict[str, Any]) -> Optional[np.ndarray]:
        """
        Decode frame data from plugin response.
        
        Args:
            response: Plugin response containing frame data
            
        Returns:
            Numpy array with frame data or None if failed
        """
        try:
            # Get frame data
            frame_b64 = response.get('frame')
            shape = response.get('shape')
            dtype = response.get('dtype', 'uint8')
            
            if not frame_b64 or not shape:
                self.logger.error("Missing frame data in response")
                return None
            
            # Decode base64
            frame_bytes = base64.b64decode(frame_b64)
            
            # Convert to numpy array
            frame_array = np.frombuffer(frame_bytes, dtype=dtype)
            frame_array = frame_array.reshape(shape)
            
            return frame_array
            
        except Exception as e:
            self.logger.error(f"Failed to decode frame: {e}")
            return None
    
    def _update_stats(self, capture_time: float) -> None:
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
    
    def set_capture_mode(self, mode: str) -> bool:
        """
        Set the capture mode by activating the corresponding plugin.
        
        Args:
            mode: Capture mode string (e.g., 'directx', 'screenshot')
            
        Returns:
            bool: True if mode set successfully
        """
        try:
            # Map mode to plugin name
            plugin_map = {
                'directx': 'dxcam_capture_gpu',
                'dxcam': 'dxcam_capture_gpu',
                'screenshot': 'screenshot_capture_cpu',
                'auto': 'dxcam_capture_gpu'  # Default to dxcam
            }
            
            plugin_name = plugin_map.get(mode.lower())
            
            if not plugin_name:
                self.logger.error(f"Unknown capture mode: {mode}")
                return False
            
            # Prepare plugin config with runtime mode
            plugin_config = {
                'runtime_mode': self.runtime_mode
            }
            
            # Activate plugin with config
            if self.plugin_manager.set_active_plugin(plugin_name, plugin_config):
                self.logger.info(f"Capture mode set to: {mode} (plugin: {plugin_name}, runtime_mode: {self.runtime_mode})")
                return True
            else:
                self.logger.error(f"Failed to activate plugin: {plugin_name}")
                
                # If DXCam fails in auto mode, try screenshot fallback
                if mode.lower() == 'auto' and plugin_name == 'dxcam_capture_gpu':
                    self.logger.info("DXCam failed, falling back to screenshot_capture_cpu")
                    fallback_config = {'runtime_mode': self.runtime_mode}
                    if self.plugin_manager.set_active_plugin('screenshot_capture_cpu', fallback_config):
                        self.logger.info("Successfully fell back to screenshot_capture_cpu")
                        return True
                
                return False
                
        except Exception as e:
            self.logger.error(f"Failed to set capture mode {mode}: {e}")
            return False
    
    def get_supported_modes(self) -> List[str]:
        """
        Get list of supported capture modes.
        
        Returns:
            List[str]: List of supported capture mode names
        """
        # Get available plugins
        plugins = self.plugin_manager.get_available_plugins()
        
        # Map plugin names to mode names
        modes = []
        if 'dxcam_capture_gpu' in plugins:
            modes.extend(['directx', 'dxcam', 'auto'])
        if 'screenshot_capture_cpu' in plugins:
            modes.append('screenshot')
        
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
        self.logger.info(f"Frame rate configured to {fps} FPS")
        return True
    
    def is_available(self) -> bool:
        """
        Check if capture functionality is available.
        
        Returns:
            bool: True if at least one capture plugin is available
        """
        plugins = self.plugin_manager.get_available_plugins()
        return len(plugins) > 0
    
    def set_performance_profile(self, profile: PerformanceProfile) -> None:
        """
        Set performance profile.
        
        Args:
            profile: Performance profile
        """
        self._performance_profile = profile
        
        # Adjust frame rate based on profile
        if profile == PerformanceProfile.LOW:
            self.configure_capture_rate(min(self._frame_rate, 15))
        elif profile == PerformanceProfile.NORMAL:
            self.configure_capture_rate(min(self._frame_rate, 30))
        elif profile == PerformanceProfile.HIGH:
            self.configure_capture_rate(min(self._frame_rate, 60))
        
        self.logger.info(f"Performance profile set to {profile.value}")
    
    def get_capture_statistics(self) -> Dict[str, Any]:
        """
        Get comprehensive capture statistics.
        
        Returns:
            Dict[str, Any]: Capture statistics
        """
        stats = self._stats.copy()
        stats.update({
            'active_plugin': self.plugin_manager.get_active_plugin(),
            'available_plugins': self.plugin_manager.get_available_plugins(),
            'loaded_plugins': self.plugin_manager.get_loaded_plugins(),
            'frame_rate': self._frame_rate,
            'performance_profile': self._performance_profile.value
        })
        return stats
    
    def cleanup(self) -> None:
        """Clean up capture resources."""
        try:
            self.plugin_manager.cleanup()
            self.logger.info("Plugin capture layer cleaned up")
        except Exception as e:
            self.logger.error(f"Cleanup error: {e}")
