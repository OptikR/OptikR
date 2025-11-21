"""
Multi-Monitor Detection and Management System

Provides comprehensive multi-monitor detection, compatibility checking, and management
for cross-monitor overlay support with per-monitor scaling and DPI awareness.
"""

import sys
import platform
from typing import List, Dict, Any, Optional, Tuple
from dataclasses import dataclass
from enum import Enum
import logging

try:
    from ..models import Rectangle
except ImportError:
    # Handle case when running as script
    import os
    sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))
    from app.models import Rectangle


class MonitorOrientation(Enum):
    """Monitor orientation enumeration."""
    LANDSCAPE = "landscape"
    PORTRAIT = "portrait"
    SQUARE = "square"


@dataclass
class MonitorInfo:
    """Information about a detected monitor."""
    monitor_id: int
    name: str
    primary: bool
    bounds: Rectangle
    work_area: Rectangle  # Excludes taskbar/dock areas
    dpi_scale: float
    refresh_rate: int
    orientation: MonitorOrientation
    color_depth: int
    is_available: bool = True
    
    @property
    def aspect_ratio(self) -> float:
        """Calculate monitor aspect ratio."""
        return self.bounds.width / self.bounds.height if self.bounds.height > 0 else 1.0
    
    @property
    def pixel_density(self) -> float:
        """Calculate pixels per inch."""
        # Standard calculation: diagonal pixels / diagonal inches
        diagonal_pixels = (self.bounds.width ** 2 + self.bounds.height ** 2) ** 0.5
        # Assume standard monitor sizes for estimation
        diagonal_inches = diagonal_pixels / (96 * self.dpi_scale)  # 96 DPI baseline
        return diagonal_pixels / diagonal_inches if diagonal_inches > 0 else 96.0
    
    # Compatibility properties for RegionSelector
    @property
    def id(self) -> int:
        """Alias for monitor_id for compatibility."""
        return self.monitor_id
    
    @property
    def x(self) -> int:
        """X coordinate of monitor bounds."""
        return self.bounds.x
    
    @property
    def y(self) -> int:
        """Y coordinate of monitor bounds."""
        return self.bounds.y
    
    @property
    def width(self) -> int:
        """Width of monitor bounds."""
        return self.bounds.width
    
    @property
    def height(self) -> int:
        """Height of monitor bounds."""
        return self.bounds.height
    
    @property
    def is_primary(self) -> bool:
        """Alias for primary for compatibility."""
        return self.primary


class MultiMonitorManager:
    """Manages multi-monitor detection and compatibility."""
    
    def __init__(self):
        """Initialize multi-monitor manager."""
        self.logger = logging.getLogger(__name__)
        self.monitors: List[MonitorInfo] = []
        self.primary_monitor: Optional[MonitorInfo] = None
        self._platform = platform.system().lower()
        
        # Initialize platform-specific detection
        self._init_platform_detection()
    
    def _init_platform_detection(self):
        """Initialize platform-specific monitor detection."""
        if self._platform == "windows":
            self._init_windows_detection()
        elif self._platform == "linux":
            self._init_linux_detection()
        elif self._platform == "darwin":  # macOS
            self._init_macos_detection()
        else:
            self.logger.warning(f"Unsupported platform: {self._platform}")
    
    def _init_windows_detection(self):
        """Initialize Windows-specific monitor detection."""
        try:
            import tkinter as tk
            self._tk_root = tk.Tk()
            self._tk_root.withdraw()  # Hide the window
            self.logger.info("Windows monitor detection initialized")
        except ImportError:
            self.logger.error("Tkinter not available for Windows monitor detection")
    
    def _init_linux_detection(self):
        """Initialize Linux-specific monitor detection."""
        try:
            # Try to import X11 libraries
            import subprocess
            result = subprocess.run(['xrandr', '--version'], 
                                  capture_output=True, text=True, timeout=5)
            if result.returncode == 0:
                self.logger.info("Linux X11 monitor detection initialized")
            else:
                self.logger.warning("xrandr not available, using fallback detection")
        except (ImportError, subprocess.TimeoutExpired, FileNotFoundError):
            self.logger.warning("X11 libraries not available, using fallback detection")
    
    def _init_macos_detection(self):
        """Initialize macOS-specific monitor detection."""
        try:
            import subprocess
            result = subprocess.run(['system_profiler', 'SPDisplaysDataType'], 
                                  capture_output=True, text=True, timeout=10)
            if result.returncode == 0:
                self.logger.info("macOS monitor detection initialized")
            else:
                self.logger.warning("system_profiler not available, using fallback detection")
        except (subprocess.TimeoutExpired, FileNotFoundError):
            self.logger.warning("macOS system_profiler not available, using fallback detection")
    
    def detect_monitors(self) -> List[MonitorInfo]:
        """Detect all available monitors.
        
        Returns:
            List of detected monitor information
        """
        self.monitors.clear()
        self.primary_monitor = None
        
        if self._platform == "windows":
            self._detect_windows_monitors()
        elif self._platform == "linux":
            self._detect_linux_monitors()
        elif self._platform == "darwin":
            self._detect_macos_monitors()
        else:
            self._detect_fallback_monitors()
        
        # Ensure we have at least one monitor
        if not self.monitors:
            self._create_default_monitor()
        
        # Set primary monitor
        primary_monitors = [m for m in self.monitors if m.primary]
        if primary_monitors:
            self.primary_monitor = primary_monitors[0]
        elif self.monitors:
            self.primary_monitor = self.monitors[0]
            self.primary_monitor.primary = True
        
        self.logger.info(f"Detected {len(self.monitors)} monitors")
        return self.monitors
    
    def _detect_windows_monitors(self):
        """Detect monitors on Windows using Tkinter and Win32 APIs."""
        try:
            import tkinter as tk
            
            # Get screen dimensions using Tkinter
            if hasattr(self, '_tk_root'):
                screen_width = self._tk_root.winfo_screenwidth()
                screen_height = self._tk_root.winfo_screenheight()
                
                # Try to get DPI scaling
                try:
                    dpi = self._tk_root.winfo_fpixels('1i')
                    dpi_scale = dpi / 96.0  # 96 DPI is standard
                except:
                    dpi_scale = 1.0
                
                # Create primary monitor info
                primary_monitor = MonitorInfo(
                    monitor_id=0,
                    name="Primary Display",
                    primary=True,
                    bounds=Rectangle(0, 0, screen_width, screen_height),
                    work_area=Rectangle(0, 0, screen_width, screen_height - 40),  # Estimate taskbar
                    dpi_scale=dpi_scale,
                    refresh_rate=60,  # Default assumption
                    orientation=self._get_orientation(screen_width, screen_height),
                    color_depth=32  # Default assumption
                )
                self.monitors.append(primary_monitor)
                
                # Try to detect additional monitors using Win32 API
                self._detect_windows_additional_monitors()
                
        except Exception as e:
            self.logger.error(f"Error detecting Windows monitors: {e}")
            self._create_default_monitor()
    
    def _detect_windows_additional_monitors(self):
        """Detect additional monitors on Windows using Win32 API."""
        try:
            # Try to use win32api if available
            import win32api
            import win32con
            
            monitors = win32api.EnumDisplayMonitors()
            for i, (hmonitor, hdc, rect) in enumerate(monitors):
                if i == 0:  # Skip primary monitor (already added)
                    continue
                
                x, y, right, bottom = rect
                width = right - x
                height = bottom - y
                
                monitor_info = MonitorInfo(
                    monitor_id=i,
                    name=f"Display {i + 1}",
                    primary=False,
                    bounds=Rectangle(x, y, width, height),
                    work_area=Rectangle(x, y, width, height),
                    dpi_scale=1.0,  # Default, would need more complex detection
                    refresh_rate=60,
                    orientation=self._get_orientation(width, height),
                    color_depth=32
                )
                self.monitors.append(monitor_info)
                
        except ImportError:
            self.logger.info("Win32 API not available, using single monitor detection")
        except Exception as e:
            self.logger.warning(f"Error detecting additional Windows monitors: {e}")
    
    def _detect_linux_monitors(self):
        """Detect monitors on Linux using xrandr."""
        try:
            import subprocess
            
            # Run xrandr to get monitor information
            result = subprocess.run(['xrandr', '--query'], 
                                  capture_output=True, text=True, timeout=10)
            
            if result.returncode == 0:
                self._parse_xrandr_output(result.stdout)
            else:
                self.logger.warning("xrandr query failed, using fallback")
                self._detect_fallback_monitors()
                
        except (subprocess.TimeoutExpired, FileNotFoundError) as e:
            self.logger.warning(f"xrandr not available: {e}")
            self._detect_fallback_monitors()
        except Exception as e:
            self.logger.error(f"Error detecting Linux monitors: {e}")
            self._detect_fallback_monitors()
    
    def _parse_xrandr_output(self, xrandr_output: str):
        """Parse xrandr output to extract monitor information."""
        lines = xrandr_output.split('\n')
        monitor_id = 0
        
        for line in lines:
            if ' connected' in line:
                parts = line.split()
                name = parts[0]
                is_primary = 'primary' in line
                
                # Extract resolution and position
                resolution_info = None
                for part in parts:
                    if 'x' in part and '+' in part:
                        resolution_info = part
                        break
                
                if resolution_info:
                    # Parse resolution like "1920x1080+0+0"
                    res_parts = resolution_info.split('+')
                    if len(res_parts) >= 3:
                        width_height = res_parts[0].split('x')
                        if len(width_height) == 2:
                            width = int(width_height[0])
                            height = int(width_height[1])
                            x = int(res_parts[1])
                            y = int(res_parts[2])
                            
                            monitor_info = MonitorInfo(
                                monitor_id=monitor_id,
                                name=name,
                                primary=is_primary,
                                bounds=Rectangle(x, y, width, height),
                                work_area=Rectangle(x, y, width, height - 30),  # Estimate panel
                                dpi_scale=1.0,  # Would need additional detection
                                refresh_rate=60,  # Default
                                orientation=self._get_orientation(width, height),
                                color_depth=24  # Default for Linux
                            )
                            self.monitors.append(monitor_info)
                            monitor_id += 1
    
    def _detect_macos_monitors(self):
        """Detect monitors on macOS using system_profiler."""
        try:
            import subprocess
            
            # Get display information
            result = subprocess.run(['system_profiler', 'SPDisplaysDataType', '-json'], 
                                  capture_output=True, text=True, timeout=15)
            
            if result.returncode == 0:
                import json
                data = json.loads(result.stdout)
                self._parse_macos_display_data(data)
            else:
                self.logger.warning("system_profiler failed, using fallback")
                self._detect_fallback_monitors()
                
        except (subprocess.TimeoutExpired, FileNotFoundError, json.JSONDecodeError) as e:
            self.logger.warning(f"macOS display detection failed: {e}")
            self._detect_fallback_monitors()
        except Exception as e:
            self.logger.error(f"Error detecting macOS monitors: {e}")
            self._detect_fallback_monitors()
    
    def _parse_macos_display_data(self, display_data: Dict[str, Any]):
        """Parse macOS system_profiler display data."""
        displays = display_data.get('SPDisplaysDataType', [])
        monitor_id = 0
        
        for display in displays:
            name = display.get('_name', f'Display {monitor_id + 1}')
            
            # Extract resolution information
            displays_info = display.get('spdisplays_ndrvs', [])
            for display_info in displays_info:
                resolution = display_info.get('_spdisplays_resolution', '')
                if 'x' in resolution:
                    width_height = resolution.split(' x ')
                    if len(width_height) == 2:
                        width = int(width_height[0])
                        height = int(width_height[1])
                        
                        monitor_info = MonitorInfo(
                            monitor_id=monitor_id,
                            name=name,
                            primary=monitor_id == 0,  # Assume first is primary
                            bounds=Rectangle(0, 0, width, height),  # macOS coordinates are complex
                            work_area=Rectangle(0, 0, width, height - 25),  # Estimate dock
                            dpi_scale=2.0 if 'Retina' in name else 1.0,  # Retina detection
                            refresh_rate=60,  # Default
                            orientation=self._get_orientation(width, height),
                            color_depth=32  # Default for macOS
                        )
                        self.monitors.append(monitor_info)
                        monitor_id += 1
    
    def _detect_fallback_monitors(self):
        """Fallback monitor detection using Tkinter."""
        try:
            import tkinter as tk
            root = tk.Tk()
            root.withdraw()
            
            width = root.winfo_screenwidth()
            height = root.winfo_screenheight()
            
            monitor_info = MonitorInfo(
                monitor_id=0,
                name="Default Display",
                primary=True,
                bounds=Rectangle(0, 0, width, height),
                work_area=Rectangle(0, 0, width, height - 40),
                dpi_scale=1.0,
                refresh_rate=60,
                orientation=self._get_orientation(width, height),
                color_depth=24
            )
            self.monitors.append(monitor_info)
            
            root.destroy()
            
        except Exception as e:
            self.logger.error(f"Fallback monitor detection failed: {e}")
            self._create_default_monitor()
    
    def _create_default_monitor(self):
        """Create a default monitor when detection fails."""
        default_monitor = MonitorInfo(
            monitor_id=0,
            name="Default Monitor",
            primary=True,
            bounds=Rectangle(0, 0, 1920, 1080),
            work_area=Rectangle(0, 0, 1920, 1040),
            dpi_scale=1.0,
            refresh_rate=60,
            orientation=MonitorOrientation.LANDSCAPE,
            color_depth=24
        )
        self.monitors.append(default_monitor)
        self.logger.warning("Using default monitor configuration")
    
    def _get_orientation(self, width: int, height: int) -> MonitorOrientation:
        """Determine monitor orientation from dimensions."""
        if width > height * 1.1:
            return MonitorOrientation.LANDSCAPE
        elif height > width * 1.1:
            return MonitorOrientation.PORTRAIT
        else:
            return MonitorOrientation.SQUARE
    
    def get_monitor_by_id(self, monitor_id: int) -> Optional[MonitorInfo]:
        """Get monitor information by ID.
        
        Args:
            monitor_id: Monitor ID to search for
            
        Returns:
            MonitorInfo if found, None otherwise
        """
        for monitor in self.monitors:
            if monitor.monitor_id == monitor_id:
                return monitor
        return None
    
    def get_monitors(self) -> List[MonitorInfo]:
        """Get all detected monitors.
        
        Returns:
            List of all MonitorInfo objects
        """
        if not self.monitors:
            self.detect_monitors()
        return self.monitors
    
    def get_primary_monitor(self) -> Optional[MonitorInfo]:
        """Get the primary monitor.
        
        Returns:
            Primary MonitorInfo or None if not found
        """
        return self.primary_monitor
    
    def get_monitor_at_point(self, x: int, y: int) -> Optional[MonitorInfo]:
        """Get monitor containing the specified point.
        
        Args:
            x: X coordinate
            y: Y coordinate
            
        Returns:
            MonitorInfo containing the point or None
        """
        for monitor in self.monitors:
            if monitor.bounds.contains_point(x, y):
                return monitor
        return None
    
    def validate_capture_region(self, region: Rectangle, monitor_id: int) -> Tuple[bool, str]:
        """Validate a capture region against monitor bounds.
        
        Args:
            region: Capture region to validate
            monitor_id: Target monitor ID
            
        Returns:
            Tuple of (is_valid, error_message)
        """
        monitor = self.get_monitor_by_id(monitor_id)
        if not monitor:
            return False, f"Monitor {monitor_id} not found"
        
        if not monitor.is_available:
            return False, f"Monitor {monitor_id} is not available"
        
        # Check if region is within monitor bounds
        monitor_bounds = monitor.bounds
        if (region.x < monitor_bounds.x or 
            region.y < monitor_bounds.y or
            region.x + region.width > monitor_bounds.x + monitor_bounds.width or
            region.y + region.height > monitor_bounds.y + monitor_bounds.height):
            return False, f"Capture region extends beyond monitor {monitor_id} bounds"
        
        # Check minimum size
        if region.width < 10 or region.height < 10:
            return False, "Capture region too small (minimum 10x10 pixels)"
        
        return True, "Valid capture region"
    
    def get_recommended_regions(self, monitor_id: int) -> List[Tuple[str, Rectangle]]:
        """Get recommended capture regions for a monitor.
        
        Args:
            monitor_id: Target monitor ID
            
        Returns:
            List of (name, region) tuples for recommended regions
        """
        monitor = self.get_monitor_by_id(monitor_id)
        if not monitor:
            return []
        
        bounds = monitor.bounds
        work_area = monitor.work_area
        
        recommendations = [
            ("Full Screen", bounds),
            ("Work Area", work_area),
            ("Center Half", Rectangle(
                bounds.x + bounds.width // 4,
                bounds.y + bounds.height // 4,
                bounds.width // 2,
                bounds.height // 2
            )),
            ("Top Half", Rectangle(
                bounds.x,
                bounds.y,
                bounds.width,
                bounds.height // 2
            )),
            ("Bottom Half", Rectangle(
                bounds.x,
                bounds.y + bounds.height // 2,
                bounds.width,
                bounds.height // 2
            )),
            ("Left Half", Rectangle(
                bounds.x,
                bounds.y,
                bounds.width // 2,
                bounds.height
            )),
            ("Right Half", Rectangle(
                bounds.x + bounds.width // 2,
                bounds.y,
                bounds.width // 2,
                bounds.height
            ))
        ]
        
        return recommendations
    
    def get_monitor_layout_info(self) -> Dict[str, Any]:
        """Get comprehensive monitor layout information.
        
        Returns:
            Dictionary with layout information for UI display
        """
        if not self.monitors:
            return {"total_monitors": 0, "layout": "none"}
        
        # Calculate total desktop bounds
        min_x = min(m.bounds.x for m in self.monitors)
        min_y = min(m.bounds.y for m in self.monitors)
        max_x = max(m.bounds.x + m.bounds.width for m in self.monitors)
        max_y = max(m.bounds.y + m.bounds.height for m in self.monitors)
        
        total_width = max_x - min_x
        total_height = max_y - min_y
        
        # Determine layout type
        layout_type = "single"
        if len(self.monitors) > 1:
            if len(self.monitors) == 2:
                layout_type = "dual"
            else:
                layout_type = "multi"
        
        return {
            "total_monitors": len(self.monitors),
            "layout": layout_type,
            "total_bounds": Rectangle(min_x, min_y, total_width, total_height),
            "primary_monitor_id": self.primary_monitor.monitor_id if self.primary_monitor else 0,
            "monitors": [
                {
                    "id": m.monitor_id,
                    "name": m.name,
                    "primary": m.primary,
                    "bounds": m.bounds,
                    "dpi_scale": m.dpi_scale,
                    "orientation": m.orientation.value
                }
                for m in self.monitors
            ]
        }