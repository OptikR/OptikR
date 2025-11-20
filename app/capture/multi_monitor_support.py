"""
Multi-Monitor Support for DirectX Desktop Duplication API

Provides comprehensive multi-monitor detection, enumeration, and capture capabilities
for systems with multiple displays.
"""

import ctypes
from ctypes import wintypes, Structure, POINTER, byref, c_int, c_uint, c_void_p
import logging
from typing import List, Dict, Optional, Tuple, Any
from dataclasses import dataclass
from enum import Enum

try:
    from ..models import Rectangle, CaptureRegion
except ImportError:
    from app.models import Rectangle, CaptureRegion


class MonitorOrientation(Enum):
    """Monitor orientation enumeration."""
    LANDSCAPE = "landscape"
    PORTRAIT = "portrait"
    LANDSCAPE_FLIPPED = "landscape_flipped"
    PORTRAIT_FLIPPED = "portrait_flipped"


@dataclass
class MonitorInfo:
    """Comprehensive monitor information."""
    monitor_id: int
    device_name: str
    display_name: str
    bounds: Rectangle
    work_area: Rectangle
    is_primary: bool
    dpi_x: int
    dpi_y: int
    scale_factor: float
    orientation: MonitorOrientation
    refresh_rate: int
    color_depth: int
    is_available: bool = True
    
    @property
    def aspect_ratio(self) -> float:
        """Calculate monitor aspect ratio."""
        return self.bounds.width / self.bounds.height if self.bounds.height > 0 else 1.0
    
    @property
    def pixel_density(self) -> float:
        """Calculate pixels per inch (average of X and Y DPI)."""
        return (self.dpi_x + self.dpi_y) / 2.0


# Windows API structures for monitor enumeration
class RECT(Structure):
    """Windows RECT structure."""
    _fields_ = [
        ("left", c_int),
        ("top", c_int),
        ("right", c_int),
        ("bottom", c_int)
    ]


class MONITORINFO(Structure):
    """Windows MONITORINFO structure."""
    _fields_ = [
        ("cbSize", wintypes.DWORD),
        ("rcMonitor", RECT),
        ("rcWork", RECT),
        ("dwFlags", wintypes.DWORD)
    ]


class MONITORINFOEX(Structure):
    """Windows MONITORINFOEX structure with device name."""
    _fields_ = [
        ("cbSize", wintypes.DWORD),
        ("rcMonitor", RECT),
        ("rcWork", RECT),
        ("dwFlags", wintypes.DWORD),
        ("szDevice", wintypes.CHAR * 32)
    ]


class DEVMODE(Structure):
    """Windows DEVMODE structure for display settings."""
    _fields_ = [
        ("dmDeviceName", wintypes.CHAR * 32),
        ("dmSpecVersion", wintypes.WORD),
        ("dmDriverVersion", wintypes.WORD),
        ("dmSize", wintypes.WORD),
        ("dmDriverExtra", wintypes.WORD),
        ("dmFields", wintypes.DWORD),
        ("dmOrientation", c_int),
        ("dmPaperSize", c_int),
        ("dmPaperLength", c_int),
        ("dmPaperWidth", c_int),
        ("dmScale", c_int),
        ("dmCopies", c_int),
        ("dmDefaultSource", c_int),
        ("dmPrintQuality", c_int),
        ("dmColor", c_int),
        ("dmDuplex", c_int),
        ("dmYResolution", c_int),
        ("dmTTOption", c_int),
        ("dmCollate", c_int),
        ("dmFormName", wintypes.CHAR * 32),
        ("dmLogPixels", wintypes.WORD),
        ("dmBitsPerPel", wintypes.DWORD),
        ("dmPelsWidth", wintypes.DWORD),
        ("dmPelsHeight", wintypes.DWORD),
        ("dmDisplayFlags", wintypes.DWORD),
        ("dmDisplayFrequency", wintypes.DWORD)
    ]


class MultiMonitorManager:
    """
    Multi-monitor management system for DirectX Desktop Duplication API.
    
    Provides comprehensive multi-monitor detection, enumeration, and management
    capabilities for systems with multiple displays.
    """
    
    def __init__(self, logger: Optional[logging.Logger] = None):
        """
        Initialize multi-monitor manager.
        
        Args:
            logger: Optional logger for debugging and monitoring
        """
        self.logger = logger or logging.getLogger(__name__)
        self._monitors: Dict[int, MonitorInfo] = {}
        self._primary_monitor_id: Optional[int] = None
        self._virtual_screen_bounds: Optional[Rectangle] = None
        
        # Windows API constants
        self.MONITOR_DEFAULTTONULL = 0
        self.MONITOR_DEFAULTTOPRIMARY = 1
        self.MONITOR_DEFAULTTONEAREST = 2
        self.MONITORINFOF_PRIMARY = 1
        
        # Initialize monitor detection
        self._detect_monitors()
    
    def _detect_monitors(self) -> None:
        """Detect and enumerate all available monitors."""
        try:
            self.logger.info("Detecting monitors...")
            
            # Clear existing monitor data
            self._monitors.clear()
            self._primary_monitor_id = None
            
            # Enumerate monitors using Windows API
            monitor_count = 0
            
            def monitor_enum_proc(hmonitor, hdc, rect_ptr, data):
                nonlocal monitor_count
                try:
                    monitor_info = self._get_monitor_info(hmonitor)
                    if monitor_info:
                        self._monitors[monitor_count] = monitor_info
                        if monitor_info.is_primary:
                            self._primary_monitor_id = monitor_count
                        monitor_count += 1
                        self.logger.debug(f"Detected monitor {monitor_count}: {monitor_info.device_name}")
                except Exception as e:
                    self.logger.error(f"Error processing monitor {monitor_count}: {e}")
                return True
            
            # Set up callback function type
            MONITORENUMPROC = ctypes.WINFUNCTYPE(
                wintypes.BOOL,
                wintypes.HMONITOR,
                wintypes.HDC,
                POINTER(RECT),
                wintypes.LPARAM
            )
            
            # Call Windows API to enumerate monitors
            try:
                user32 = ctypes.windll.user32
                enum_proc = MONITORENUMPROC(monitor_enum_proc)
                user32.EnumDisplayMonitors(None, None, enum_proc, 0)
                
                self.logger.info(f"Detected {len(self._monitors)} monitors")
                
                # If no monitors were detected, use fallback
                if len(self._monitors) == 0:
                    self.logger.warning("No monitors detected via enumeration, using fallback")
                    self._create_fallback_monitor()
                else:
                    # Calculate virtual screen bounds
                    self._calculate_virtual_screen_bounds()
                
            except Exception as e:
                self.logger.error(f"Failed to enumerate monitors: {e}")
                # Fallback: create single monitor entry for primary display
                self._create_fallback_monitor()
                
        except Exception as e:
            self.logger.error(f"Monitor detection failed: {e}")
            self._create_fallback_monitor()
    
    def _get_monitor_info(self, hmonitor) -> Optional[MonitorInfo]:
        """
        Get detailed information for a specific monitor.
        
        Args:
            hmonitor: Monitor handle from Windows API
            
        Returns:
            Optional[MonitorInfo]: Monitor information or None if failed
        """
        try:
            user32 = ctypes.windll.user32
            
            # Try with MONITORINFOEX first (includes device name)
            try:
                monitor_info = MONITORINFOEX()
                monitor_info.cbSize = ctypes.sizeof(MONITORINFOEX)
                
                if not user32.GetMonitorInfoW(hmonitor, byref(monitor_info)):
                    # Try with basic MONITORINFO if MONITORINFOEX fails
                    raise Exception("GetMonitorInfoW with MONITORINFOEX failed")
                    
                device_name = monitor_info.szDevice.decode('utf-8').rstrip('\x00')
                
            except Exception as e:
                self.logger.debug(f"MONITORINFOEX failed, trying MONITORINFO: {e}")
                # Fallback to basic MONITORINFO
                monitor_info_basic = MONITORINFO()
                monitor_info_basic.cbSize = ctypes.sizeof(MONITORINFO)
                
                if not user32.GetMonitorInfoW(hmonitor, byref(monitor_info_basic)):
                    self.logger.error("Failed to get monitor info with both methods")
                    return None
                
                # Use basic info and generate device name
                monitor_info = monitor_info_basic
                device_name = f"\\\\.\\DISPLAY{len(self._monitors) + 1}"
            
            # Extract device name (only available if we successfully got MONITORINFOEX)
            if hasattr(monitor_info, 'szDevice'):
                device_name = monitor_info.szDevice.decode('utf-8').rstrip('\x00')
            else:
                device_name = f"\\\\.\\DISPLAY{len(self._monitors) + 1}"
            
            # Get monitor bounds
            bounds = Rectangle(
                x=monitor_info.rcMonitor.left,
                y=monitor_info.rcMonitor.top,
                width=monitor_info.rcMonitor.right - monitor_info.rcMonitor.left,
                height=monitor_info.rcMonitor.bottom - monitor_info.rcMonitor.top
            )
            
            # Get work area (excluding taskbar, etc.)
            work_area = Rectangle(
                x=monitor_info.rcWork.left,
                y=monitor_info.rcWork.top,
                width=monitor_info.rcWork.right - monitor_info.rcWork.left,
                height=monitor_info.rcWork.bottom - monitor_info.rcWork.top
            )
            
            # Check if primary monitor
            is_primary = bool(monitor_info.dwFlags & self.MONITORINFOF_PRIMARY)
            
            # Get DPI information
            dpi_x, dpi_y = self._get_monitor_dpi(hmonitor)
            
            # Get display settings
            display_settings = self._get_display_settings(device_name)
            
            # Determine orientation
            orientation = self._determine_orientation(bounds.width, bounds.height)
            
            # Create monitor info object
            monitor_info_obj = MonitorInfo(
                monitor_id=len(self._monitors),
                device_name=device_name,
                display_name=self._get_display_name(device_name),
                bounds=bounds,
                work_area=work_area,
                is_primary=is_primary,
                dpi_x=dpi_x,
                dpi_y=dpi_y,
                scale_factor=dpi_x / 96.0,  # Windows standard DPI is 96
                orientation=orientation,
                refresh_rate=display_settings.get('refresh_rate', 60),
                color_depth=display_settings.get('color_depth', 32)
            )
            
            return monitor_info_obj
            
        except Exception as e:
            self.logger.error(f"Failed to get monitor info: {e}")
            return None
    
    def _get_monitor_dpi(self, hmonitor) -> Tuple[int, int]:
        """
        Get DPI information for a monitor.
        
        Args:
            hmonitor: Monitor handle
            
        Returns:
            Tuple[int, int]: DPI X and Y values
        """
        try:
            # Try to use GetDpiForMonitor (Windows 8.1+)
            shcore = ctypes.windll.shcore
            dpi_x = wintypes.UINT()
            dpi_y = wintypes.UINT()
            
            # MDT_EFFECTIVE_DPI = 0
            result = shcore.GetDpiForMonitor(hmonitor, 0, byref(dpi_x), byref(dpi_y))
            
            if result == 0:  # S_OK
                return int(dpi_x.value), int(dpi_y.value)
            
        except (AttributeError, OSError):
            pass
        
        # Fallback to system DPI
        try:
            user32 = ctypes.windll.user32
            hdc = user32.GetDC(None)
            dpi_x = ctypes.windll.gdi32.GetDeviceCaps(hdc, 88)  # LOGPIXELSX
            dpi_y = ctypes.windll.gdi32.GetDeviceCaps(hdc, 90)  # LOGPIXELSY
            user32.ReleaseDC(None, hdc)
            return dpi_x, dpi_y
        except Exception:
            # Ultimate fallback
            return 96, 96
    
    def _get_display_settings(self, device_name: str) -> Dict[str, Any]:
        """
        Get display settings for a device.
        
        Args:
            device_name: Device name
            
        Returns:
            Dict[str, Any]: Display settings
        """
        try:
            user32 = ctypes.windll.user32
            devmode = DEVMODE()
            devmode.dmSize = ctypes.sizeof(DEVMODE)
            
            if user32.EnumDisplaySettingsW(device_name, -1, byref(devmode)):  # ENUM_CURRENT_SETTINGS
                return {
                    'refresh_rate': int(devmode.dmDisplayFrequency),
                    'color_depth': int(devmode.dmBitsPerPel),
                    'width': int(devmode.dmPelsWidth),
                    'height': int(devmode.dmPelsHeight)
                }
        except Exception as e:
            self.logger.debug(f"Failed to get display settings for {device_name}: {e}")
        
        return {'refresh_rate': 60, 'color_depth': 32}
    
    def _get_display_name(self, device_name: str) -> str:
        """
        Get friendly display name for a device.
        
        Args:
            device_name: Device name
            
        Returns:
            str: Friendly display name
        """
        try:
            # Try to get friendly name from registry or system
            # For now, return a formatted version of device name
            if "DISPLAY" in device_name:
                display_num = device_name.replace("\\\\.\\DISPLAY", "")
                return f"Display {display_num}"
            return device_name
        except Exception:
            return device_name
    
    def _determine_orientation(self, width: int, height: int) -> MonitorOrientation:
        """
        Determine monitor orientation based on dimensions.
        
        Args:
            width: Monitor width
            height: Monitor height
            
        Returns:
            MonitorOrientation: Detected orientation
        """
        if width > height:
            return MonitorOrientation.LANDSCAPE
        elif height > width:
            return MonitorOrientation.PORTRAIT
        else:
            return MonitorOrientation.LANDSCAPE  # Square displays default to landscape
    
    def _calculate_virtual_screen_bounds(self) -> None:
        """Calculate the bounds of the virtual screen (all monitors combined)."""
        if not self._monitors:
            return
        
        min_x = min(monitor.bounds.x for monitor in self._monitors.values())
        min_y = min(monitor.bounds.y for monitor in self._monitors.values())
        max_x = max(monitor.bounds.x + monitor.bounds.width for monitor in self._monitors.values())
        max_y = max(monitor.bounds.y + monitor.bounds.height for monitor in self._monitors.values())
        
        self._virtual_screen_bounds = Rectangle(
            x=min_x,
            y=min_y,
            width=max_x - min_x,
            height=max_y - min_y
        )
        
        self.logger.debug(f"Virtual screen bounds: {self._virtual_screen_bounds.width}x{self._virtual_screen_bounds.height}")
    
    def _create_fallback_monitor(self) -> None:
        """Create fallback monitor entry when detection fails."""
        try:
            user32 = ctypes.windll.user32
            
            # Get primary monitor dimensions
            width = user32.GetSystemMetrics(0)  # SM_CXSCREEN
            height = user32.GetSystemMetrics(1)  # SM_CYSCREEN
            
            fallback_monitor = MonitorInfo(
                monitor_id=0,
                device_name="\\\\.\\DISPLAY1",
                display_name="Primary Display",
                bounds=Rectangle(0, 0, width, height),
                work_area=Rectangle(0, 0, width, height),
                is_primary=True,
                dpi_x=96,
                dpi_y=96,
                scale_factor=1.0,
                orientation=MonitorOrientation.LANDSCAPE,
                refresh_rate=60,
                color_depth=32
            )
            
            self._monitors[0] = fallback_monitor
            self._primary_monitor_id = 0
            self._virtual_screen_bounds = Rectangle(0, 0, width, height)
            
            self.logger.info("Created fallback monitor configuration")
            
        except Exception as e:
            self.logger.error(f"Failed to create fallback monitor: {e}")
    
    def get_monitor_count(self) -> int:
        """
        Get the number of detected monitors.
        
        Returns:
            int: Number of monitors
        """
        return len(self._monitors)
    
    def get_monitor_info(self, monitor_id: int) -> Optional[MonitorInfo]:
        """
        Get information for a specific monitor.
        
        Args:
            monitor_id: Monitor ID
            
        Returns:
            Optional[MonitorInfo]: Monitor information or None if not found
        """
        return self._monitors.get(monitor_id)
    
    def get_all_monitors(self) -> Dict[int, MonitorInfo]:
        """
        Get information for all monitors.
        
        Returns:
            Dict[int, MonitorInfo]: Dictionary of monitor ID to monitor info
        """
        return self._monitors.copy()
    
    def get_primary_monitor_id(self) -> Optional[int]:
        """
        Get the ID of the primary monitor.
        
        Returns:
            Optional[int]: Primary monitor ID or None if not found
        """
        return self._primary_monitor_id
    
    def get_primary_monitor(self) -> Optional[MonitorInfo]:
        """
        Get the primary monitor information.
        
        Returns:
            Optional[MonitorInfo]: Primary monitor info or None if not found
        """
        if self._primary_monitor_id is not None:
            return self._monitors.get(self._primary_monitor_id)
        return None
    
    def get_virtual_screen_bounds(self) -> Optional[Rectangle]:
        """
        Get the bounds of the virtual screen (all monitors combined).
        
        Returns:
            Optional[Rectangle]: Virtual screen bounds or None if not calculated
        """
        return self._virtual_screen_bounds
    
    def get_monitor_at_point(self, x: int, y: int) -> Optional[MonitorInfo]:
        """
        Get the monitor that contains the specified point.
        
        Args:
            x: X coordinate
            y: Y coordinate
            
        Returns:
            Optional[MonitorInfo]: Monitor containing the point or None if not found
        """
        for monitor in self._monitors.values():
            if monitor.bounds.contains_point(x, y):
                return monitor
        return None
    
    def get_monitor_for_region(self, region: Rectangle) -> Optional[MonitorInfo]:
        """
        Get the monitor that best contains the specified region.
        
        Args:
            region: Region to check
            
        Returns:
            Optional[MonitorInfo]: Best matching monitor or None if not found
        """
        best_monitor = None
        best_overlap = 0
        
        for monitor in self._monitors.values():
            # Calculate overlap area
            overlap_x = max(0, min(region.x + region.width, monitor.bounds.x + monitor.bounds.width) - 
                          max(region.x, monitor.bounds.x))
            overlap_y = max(0, min(region.y + region.height, monitor.bounds.y + monitor.bounds.height) - 
                          max(region.y, monitor.bounds.y))
            overlap_area = overlap_x * overlap_y
            
            if overlap_area > best_overlap:
                best_overlap = overlap_area
                best_monitor = monitor
        
        return best_monitor
    
    def create_capture_region_for_monitor(self, monitor_id: int, 
                                        custom_region: Optional[Rectangle] = None) -> Optional[CaptureRegion]:
        """
        Create a capture region for a specific monitor.
        
        Args:
            monitor_id: Monitor ID
            custom_region: Optional custom region within the monitor
            
        Returns:
            Optional[CaptureRegion]: Capture region or None if monitor not found
        """
        monitor = self.get_monitor_info(monitor_id)
        if not monitor:
            return None
        
        if custom_region:
            # Ensure custom region is within monitor bounds
            region_rect = Rectangle(
                x=max(monitor.bounds.x, monitor.bounds.x + custom_region.x),
                y=max(monitor.bounds.y, monitor.bounds.y + custom_region.y),
                width=min(custom_region.width, 
                         monitor.bounds.width - (custom_region.x if custom_region.x > 0 else 0)),
                height=min(custom_region.height,
                          monitor.bounds.height - (custom_region.y if custom_region.y > 0 else 0))
            )
        else:
            # Use entire monitor
            region_rect = monitor.bounds
        
        return CaptureRegion(
            rectangle=region_rect,
            monitor_id=monitor_id
        )
    
    def create_full_screen_region(self) -> Optional[CaptureRegion]:
        """
        Create a capture region for the entire virtual screen.
        
        Returns:
            Optional[CaptureRegion]: Full screen capture region or None if failed
        """
        if not self._virtual_screen_bounds:
            return None
        
        return CaptureRegion(
            rectangle=self._virtual_screen_bounds,
            monitor_id=self._primary_monitor_id or 0
        )
    
    def refresh_monitor_info(self) -> bool:
        """
        Refresh monitor information (useful when displays are added/removed).
        
        Returns:
            bool: True if refresh successful
        """
        try:
            old_count = len(self._monitors)
            self._detect_monitors()
            new_count = len(self._monitors)
            
            if old_count != new_count:
                self.logger.info(f"Monitor configuration changed: {old_count} -> {new_count} monitors")
            
            return True
            
        except Exception as e:
            self.logger.error(f"Failed to refresh monitor info: {e}")
            return False
    
    def get_monitor_summary(self) -> Dict[str, Any]:
        """
        Get a summary of all monitor information.
        
        Returns:
            Dict[str, Any]: Monitor summary
        """
        return {
            'monitor_count': len(self._monitors),
            'primary_monitor_id': self._primary_monitor_id,
            'virtual_screen_bounds': self._virtual_screen_bounds,
            'monitors': {
                monitor_id: {
                    'device_name': monitor.device_name,
                    'display_name': monitor.display_name,
                    'bounds': f"{monitor.bounds.width}x{monitor.bounds.height}@{monitor.bounds.x},{monitor.bounds.y}",
                    'is_primary': monitor.is_primary,
                    'dpi': f"{monitor.dpi_x}x{monitor.dpi_y}",
                    'scale_factor': monitor.scale_factor,
                    'refresh_rate': monitor.refresh_rate,
                    'orientation': monitor.orientation.value
                }
                for monitor_id, monitor in self._monitors.items()
            }
        }