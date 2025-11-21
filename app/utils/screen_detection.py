"""
Screen Detection and Resolution Management System

This module provides comprehensive screen detection, resolution management,
and display-aware performance profiling for multi-monitor setups.
"""

import time
import platform
import logging
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Tuple, Any
from enum import Enum
import threading


class DisplayType(Enum):
    """Types of display connections"""
    HDMI = "hdmi"
    DISPLAYPORT = "displayport"
    DVI = "dvi"
    VGA = "vga"
    USB_C = "usb_c"
    THUNDERBOLT = "thunderbolt"
    WIRELESS = "wireless"
    UNKNOWN = "unknown"


class ColorDepth(Enum):
    """Color depth options"""
    BIT_16 = 16
    BIT_24 = 24
    BIT_32 = 32


@dataclass
class DisplayInfo:
    """Comprehensive display information"""
    monitor_id: int
    name: str
    width: int
    height: int
    refresh_rate: float
    dpi: float
    color_depth: ColorDepth
    display_type: DisplayType
    is_primary: bool
    position_x: int
    position_y: int
    rotation: int  # 0, 90, 180, 270 degrees
    scale_factor: float
    color_profile: Optional[str] = None
    manufacturer: Optional[str] = None
    model: Optional[str] = None
    serial_number: Optional[str] = None
    
    @property
    def aspect_ratio(self) -> float:
        """Calculate aspect ratio"""
        return self.width / self.height if self.height > 0 else 1.0
    
    @property
    def pixel_density(self) -> float:
        """Calculate pixels per inch"""
        return self.dpi
    
    @property
    def total_pixels(self) -> int:
        """Calculate total pixel count"""
        return self.width * self.height
    
    @property
    def display_area_inches(self) -> float:
        """Calculate display area in square inches"""
        width_inches = self.width / self.dpi
        height_inches = self.height / self.dpi
        return width_inches * height_inches


@dataclass
class PerformanceImpactProfile:
    """Performance impact profile for different resolutions"""
    resolution: Tuple[int, int]
    expected_fps_impact: float  # Multiplier (1.0 = no impact)
    memory_usage_mb: float
    gpu_load_factor: float
    cpu_load_factor: float
    recommended_quality: str  # "low", "medium", "high", "ultra"
    notes: str = ""


class ScreenDetectionSystem:
    """
    Advanced screen detection system that provides comprehensive
    display information and performance impact analysis.
    """
    
    def __init__(self, logger=None):
        """Initialize the screen detection system"""
        self.logger = logger or logging.getLogger(__name__)
        
        # Display information cache
        self.displays: List[DisplayInfo] = []
        self.primary_display: Optional[DisplayInfo] = None
        self.last_detection_time = 0
        self.detection_cache_duration = 5.0  # 5 seconds
        
        # Performance impact profiles
        self.performance_profiles: Dict[Tuple[int, int], PerformanceImpactProfile] = {}
        self._initialize_performance_profiles()
        
        # Platform-specific detection
        self.platform = platform.system().lower()
        self._initialize_platform_detection()
        
        self.logger.info("Screen detection system initialized")
    
    def _initialize_platform_detection(self):
        """Initialize platform-specific detection methods"""
        if self.platform == "windows":
            self._init_windows_detection()
        elif self.platform == "linux":
            self._init_linux_detection()
        elif self.platform == "darwin":  # macOS
            self._init_macos_detection()
        else:
            self.logger.warning(f"Unsupported platform for advanced screen detection: {self.platform}")
    
    def _init_windows_detection(self):
        """Initialize Windows-specific screen detection"""
        try:
            # Try to import Windows-specific modules
            import win32api
            import win32con
            import win32gui
            self.windows_api_available = True
            self.logger.debug("Windows API available for screen detection")
        except ImportError:
            self.windows_api_available = False
            self.logger.debug("Windows API not available, using fallback detection")
    
    def _init_linux_detection(self):
        """Initialize Linux-specific screen detection"""
        try:
            # Check for xrandr availability
            import subprocess
            result = subprocess.run(['which', 'xrandr'], capture_output=True)
            self.xrandr_available = result.returncode == 0
            
            if self.xrandr_available:
                self.logger.debug("xrandr available for screen detection")
            else:
                self.logger.debug("xrandr not available, using fallback detection")
        except Exception:
            self.xrandr_available = False
    
    def _init_macos_detection(self):
        """Initialize macOS-specific screen detection"""
        try:
            # Check for system_profiler availability
            import subprocess
            result = subprocess.run(['which', 'system_profiler'], capture_output=True)
            self.system_profiler_available = result.returncode == 0
            
            if self.system_profiler_available:
                self.logger.debug("system_profiler available for screen detection")
            else:
                self.logger.debug("system_profiler not available, using fallback detection")
        except Exception:
            self.system_profiler_available = False
    
    def detect_displays(self, force_refresh: bool = False) -> List[DisplayInfo]:
        """Detect all available displays"""
        current_time = time.time()
        
        # Use cached results if recent and not forcing refresh
        if (not force_refresh and 
            self.displays and 
            current_time - self.last_detection_time < self.detection_cache_duration):
            return self.displays
        
        try:
            if self.platform == "windows":
                displays = self._detect_windows_displays()
            elif self.platform == "linux":
                displays = self._detect_linux_displays()
            elif self.platform == "darwin":
                displays = self._detect_macos_displays()
            else:
                displays = self._detect_fallback_displays()
            
            self.displays = displays
            self.primary_display = next((d for d in displays if d.is_primary), None)
            self.last_detection_time = current_time
            
            self.logger.info(f"Detected {len(displays)} displays")
            return displays
            
        except Exception as e:
            self.logger.error(f"Error detecting displays: {e}")
            return self._detect_fallback_displays()
    
    def _detect_windows_displays(self) -> List[DisplayInfo]:
        """Detect displays on Windows"""
        displays = []
        
        try:
            if hasattr(self, 'windows_api_available') and self.windows_api_available:
                displays = self._detect_windows_displays_api()
            else:
                displays = self._detect_windows_displays_tkinter()
        except Exception as e:
            self.logger.error(f"Error in Windows display detection: {e}")
            displays = self._detect_fallback_displays()
        
        return displays
    
    def _detect_windows_displays_api(self) -> List[DisplayInfo]:
        """Detect Windows displays using Win32 API"""
        import win32api
        import win32con
        import win32gui
        
        displays = []
        
        try:
            # Enumerate display devices
            device_index = 0
            while True:
                try:
                    device = win32api.EnumDisplayDevices(None, device_index)
                    if not device:
                        break
                    
                    # Get display settings
                    try:
                        settings = win32api.EnumDisplaySettings(device.DeviceName, win32con.ENUM_CURRENT_SETTINGS)
                        
                        # Get monitor info
                        monitor_info = self._get_windows_monitor_info(device.DeviceName)
                        
                        display = DisplayInfo(
                            monitor_id=device_index,
                            name=device.DeviceString,
                            width=settings.PelsWidth,
                            height=settings.PelsHeight,
                            refresh_rate=float(settings.DisplayFrequency),
                            dpi=self._calculate_windows_dpi(settings),
                            color_depth=ColorDepth(settings.BitsPerPel),
                            display_type=self._detect_display_type(device.DeviceString),
                            is_primary=(device.StateFlags & win32con.DISPLAY_DEVICE_PRIMARY_DEVICE) != 0,
                            position_x=settings.Position_x,
                            position_y=settings.Position_y,
                            rotation=self._get_display_rotation(settings),
                            scale_factor=self._get_windows_scale_factor(device.DeviceName)
                        )
                        
                        displays.append(display)
                        
                    except Exception as e:
                        self.logger.debug(f"Could not get settings for device {device_index}: {e}")
                    
                    device_index += 1
                    
                except Exception:
                    break
            
        except Exception as e:
            self.logger.error(f"Error in Windows API display detection: {e}")
        
        return displays
    
    def _detect_windows_displays_tkinter(self) -> List[DisplayInfo]:
        """Detect Windows displays using Tkinter (fallback)"""
        import tkinter as tk
        
        displays = []
        
        try:
            root = tk.Tk()
            root.withdraw()
            
            # Get primary display info
            width = root.winfo_screenwidth()
            height = root.winfo_screenheight()
            dpi = root.winfo_fpixels('1i')
            
            display = DisplayInfo(
                monitor_id=0,
                name="Primary Display",
                width=width,
                height=height,
                refresh_rate=60.0,  # Default assumption
                dpi=dpi,
                color_depth=ColorDepth.BIT_32,  # Default assumption
                display_type=DisplayType.UNKNOWN,
                is_primary=True,
                position_x=0,
                position_y=0,
                rotation=0,
                scale_factor=1.0
            )
            
            displays.append(display)
            root.destroy()
            
        except Exception as e:
            self.logger.error(f"Error in Tkinter display detection: {e}")
        
        return displays
    
    def _detect_linux_displays(self) -> List[DisplayInfo]:
        """Detect displays on Linux"""
        displays = []
        
        try:
            if hasattr(self, 'xrandr_available') and self.xrandr_available:
                displays = self._detect_linux_displays_xrandr()
            else:
                displays = self._detect_fallback_displays()
        except Exception as e:
            self.logger.error(f"Error in Linux display detection: {e}")
            displays = self._detect_fallback_displays()
        
        return displays
    
    def _detect_linux_displays_xrandr(self) -> List[DisplayInfo]:
        """Detect Linux displays using xrandr"""
        import subprocess
        
        displays = []
        
        try:
            # Run xrandr to get display information
            result = subprocess.run(['xrandr', '--verbose'], capture_output=True, text=True, timeout=10)
            
            if result.returncode != 0:
                self.logger.error("xrandr command failed")
                return self._detect_fallback_displays()
            
            # Parse xrandr output
            lines = result.stdout.split('\n')
            current_display = None
            monitor_id = 0
            
            for line in lines:
                line = line.strip()
                
                # Check for display connection line
                if ' connected' in line or ' disconnected' in line:
                    if ' connected' in line and 'disconnected' not in line:
                        parts = line.split()
                        display_name = parts[0]
                        is_primary = 'primary' in line
                        
                        # Extract resolution and position
                        resolution_info = self._parse_xrandr_resolution(line)
                        
                        if resolution_info:
                            width, height, pos_x, pos_y, rotation = resolution_info
                            
                            current_display = DisplayInfo(
                                monitor_id=monitor_id,
                                name=display_name,
                                width=width,
                                height=height,
                                refresh_rate=60.0,  # Will be updated if found
                                dpi=96.0,  # Default, will be updated if found
                                color_depth=ColorDepth.BIT_32,
                                display_type=self._detect_display_type(display_name),
                                is_primary=is_primary,
                                position_x=pos_x,
                                position_y=pos_y,
                                rotation=rotation,
                                scale_factor=1.0
                            )
                            
                            displays.append(current_display)
                            monitor_id += 1
                
                # Look for refresh rate information
                elif current_display and '*' in line and 'current' not in line:
                    # This line contains the current mode with refresh rate
                    refresh_match = self._extract_refresh_rate(line)
                    if refresh_match:
                        current_display.refresh_rate = refresh_match
            
        except Exception as e:
            self.logger.error(f"Error parsing xrandr output: {e}")
        
        return displays if displays else self._detect_fallback_displays()
    
    def _detect_macos_displays(self) -> List[DisplayInfo]:
        """Detect displays on macOS"""
        displays = []
        
        try:
            if hasattr(self, 'system_profiler_available') and self.system_profiler_available:
                displays = self._detect_macos_displays_profiler()
            else:
                displays = self._detect_fallback_displays()
        except Exception as e:
            self.logger.error(f"Error in macOS display detection: {e}")
            displays = self._detect_fallback_displays()
        
        return displays
    
    def _detect_macos_displays_profiler(self) -> List[DisplayInfo]:
        """Detect macOS displays using system_profiler"""
        import subprocess
        import json
        
        displays = []
        
        try:
            # Get display information using system_profiler
            result = subprocess.run([
                'system_profiler', 'SPDisplaysDataType', '-json'
            ], capture_output=True, text=True, timeout=15)
            
            if result.returncode != 0:
                self.logger.error("system_profiler command failed")
                return self._detect_fallback_displays()
            
            # Parse JSON output
            data = json.loads(result.stdout)
            
            monitor_id = 0
            for display_data in data.get('SPDisplaysDataType', []):
                displays_info = display_data.get('spdisplays_ndrvs', [])
                
                for display_info in displays_info:
                    resolution = display_info.get('_spdisplays_resolution', '')
                    
                    if resolution:
                        # Parse resolution string (e.g., "1920 x 1080")
                        res_parts = resolution.split(' x ')
                        if len(res_parts) == 2:
                            try:
                                width = int(res_parts[0])
                                height = int(res_parts[1])
                                
                                display = DisplayInfo(
                                    monitor_id=monitor_id,
                                    name=display_info.get('_name', f'Display {monitor_id}'),
                                    width=width,
                                    height=height,
                                    refresh_rate=float(display_info.get('_spdisplays_refresh_rate', 60)),
                                    dpi=float(display_info.get('_spdisplays_pixels_per_inch', 96)),
                                    color_depth=ColorDepth.BIT_32,
                                    display_type=self._detect_display_type(display_info.get('_name', '')),
                                    is_primary=monitor_id == 0,  # Assume first is primary
                                    position_x=0,  # macOS doesn't easily provide this
                                    position_y=0,
                                    rotation=0,
                                    scale_factor=1.0,
                                    manufacturer=display_info.get('_spdisplays_vendor', None),
                                    model=display_info.get('_spdisplays_model', None)
                                )
                                
                                displays.append(display)
                                monitor_id += 1
                                
                            except ValueError as e:
                                self.logger.debug(f"Could not parse resolution '{resolution}': {e}")
            
        except Exception as e:
            self.logger.error(f"Error parsing system_profiler output: {e}")
        
        return displays if displays else self._detect_fallback_displays()
    
    def _detect_fallback_displays(self) -> List[DisplayInfo]:
        """Fallback display detection using basic methods"""
        displays = []
        
        try:
            import tkinter as tk
            
            root = tk.Tk()
            root.withdraw()
            
            # Get basic display info
            width = root.winfo_screenwidth()
            height = root.winfo_screenheight()
            
            try:
                dpi = root.winfo_fpixels('1i')
            except:
                dpi = 96.0  # Default DPI
            
            display = DisplayInfo(
                monitor_id=0,
                name="Primary Display",
                width=width,
                height=height,
                refresh_rate=60.0,
                dpi=dpi,
                color_depth=ColorDepth.BIT_32,
                display_type=DisplayType.UNKNOWN,
                is_primary=True,
                position_x=0,
                position_y=0,
                rotation=0,
                scale_factor=1.0
            )
            
            displays.append(display)
            root.destroy()
            
        except Exception as e:
            self.logger.error(f"Error in fallback display detection: {e}")
            
            # Ultimate fallback
            displays.append(DisplayInfo(
                monitor_id=0,
                name="Default Display",
                width=1920,
                height=1080,
                refresh_rate=60.0,
                dpi=96.0,
                color_depth=ColorDepth.BIT_32,
                display_type=DisplayType.UNKNOWN,
                is_primary=True,
                position_x=0,
                position_y=0,
                rotation=0,
                scale_factor=1.0
            ))
        
        return displays
    
    def _initialize_performance_profiles(self):
        """Initialize performance impact profiles for common resolutions"""
        # Common resolutions and their performance impact
        profiles = [
            # Resolution, FPS Impact, Memory MB, GPU Factor, CPU Factor, Quality, Notes
            ((1280, 720), 1.0, 150, 1.0, 1.0, "high", "720p HD - Good performance"),
            ((1366, 768), 0.95, 170, 1.1, 1.05, "high", "Common laptop resolution"),
            ((1920, 1080), 0.8, 300, 1.3, 1.1, "medium", "1080p Full HD - Moderate impact"),
            ((2560, 1440), 0.6, 500, 1.8, 1.2, "medium", "1440p QHD - Significant impact"),
            ((3840, 2160), 0.3, 1200, 3.0, 1.5, "low", "4K UHD - High performance impact"),
            ((5120, 2880), 0.2, 2000, 4.0, 1.8, "low", "5K - Very high impact"),
            ((7680, 4320), 0.1, 4000, 6.0, 2.0, "low", "8K - Extreme impact")
        ]
        
        for resolution, fps_impact, memory_mb, gpu_factor, cpu_factor, quality, notes in profiles:
            self.performance_profiles[resolution] = PerformanceImpactProfile(
                resolution=resolution,
                expected_fps_impact=fps_impact,
                memory_usage_mb=memory_mb,
                gpu_load_factor=gpu_factor,
                cpu_load_factor=cpu_factor,
                recommended_quality=quality,
                notes=notes
            )
    
    def get_performance_impact(self, width: int, height: int) -> PerformanceImpactProfile:
        """Get performance impact profile for a resolution"""
        resolution = (width, height)
        
        # Check for exact match
        if resolution in self.performance_profiles:
            return self.performance_profiles[resolution]
        
        # Find closest resolution and interpolate
        closest_profile = self._find_closest_performance_profile(width, height)
        
        if closest_profile:
            # Create interpolated profile
            pixel_ratio = (width * height) / (closest_profile.resolution[0] * closest_profile.resolution[1])
            
            return PerformanceImpactProfile(
                resolution=resolution,
                expected_fps_impact=closest_profile.expected_fps_impact * (1.0 / pixel_ratio),
                memory_usage_mb=closest_profile.memory_usage_mb * pixel_ratio,
                gpu_load_factor=closest_profile.gpu_load_factor * pixel_ratio,
                cpu_load_factor=closest_profile.cpu_load_factor * (pixel_ratio ** 0.5),
                recommended_quality=self._interpolate_quality(pixel_ratio),
                notes=f"Interpolated from {closest_profile.resolution}"
            )
        
        # Fallback profile
        return PerformanceImpactProfile(
            resolution=resolution,
            expected_fps_impact=0.5,
            memory_usage_mb=width * height * 4 / (1024 * 1024),  # Rough estimate
            gpu_load_factor=2.0,
            cpu_load_factor=1.5,
            recommended_quality="medium",
            notes="Estimated profile"
        )
    
    def _find_closest_performance_profile(self, width: int, height: int) -> Optional[PerformanceImpactProfile]:
        """Find the closest performance profile by pixel count"""
        target_pixels = width * height
        closest_profile = None
        min_difference = float('inf')
        
        for profile in self.performance_profiles.values():
            profile_pixels = profile.resolution[0] * profile.resolution[1]
            difference = abs(target_pixels - profile_pixels)
            
            if difference < min_difference:
                min_difference = difference
                closest_profile = profile
        
        return closest_profile
    
    def _interpolate_quality(self, pixel_ratio: float) -> str:
        """Interpolate recommended quality based on pixel ratio"""
        if pixel_ratio <= 0.5:
            return "ultra"
        elif pixel_ratio <= 1.0:
            return "high"
        elif pixel_ratio <= 2.0:
            return "medium"
        else:
            return "low"
    
    def get_display_summary(self) -> Dict[str, Any]:
        """Get comprehensive display system summary"""
        displays = self.detect_displays()
        
        if not displays:
            return {"status": "no_displays", "count": 0}
        
        # Calculate total display area and pixels
        total_pixels = sum(d.total_pixels for d in displays)
        total_area = sum(d.display_area_inches for d in displays)
        
        # Find highest resolution display
        max_res_display = max(displays, key=lambda d: d.total_pixels)
        
        # Calculate performance impact for primary display
        primary_display = self.primary_display or displays[0]
        perf_impact = self.get_performance_impact(primary_display.width, primary_display.height)
        
        return {
            "status": "active",
            "display_count": len(displays),
            "primary_display": {
                "name": primary_display.name,
                "resolution": f"{primary_display.width}x{primary_display.height}",
                "refresh_rate": primary_display.refresh_rate,
                "dpi": primary_display.dpi,
                "aspect_ratio": round(primary_display.aspect_ratio, 2)
            },
            "total_pixels": total_pixels,
            "total_display_area": round(total_area, 2),
            "max_resolution": f"{max_res_display.width}x{max_res_display.height}",
            "performance_impact": {
                "fps_multiplier": perf_impact.expected_fps_impact,
                "memory_usage_mb": perf_impact.memory_usage_mb,
                "recommended_quality": perf_impact.recommended_quality,
                "notes": perf_impact.notes
            },
            "displays": [
                {
                    "id": d.monitor_id,
                    "name": d.name,
                    "resolution": f"{d.width}x{d.height}",
                    "refresh_rate": d.refresh_rate,
                    "is_primary": d.is_primary,
                    "position": f"{d.position_x},{d.position_y}"
                }
                for d in displays
            ]
        }
    
    # Helper methods for platform-specific parsing
    
    def _get_windows_monitor_info(self, device_name: str) -> Dict[str, Any]:
        """Get additional Windows monitor information"""
        # Placeholder for additional Windows monitor info
        return {}
    
    def _calculate_windows_dpi(self, settings) -> float:
        """Calculate DPI from Windows display settings"""
        # This is a simplified calculation
        # In practice, you would use GetDeviceCaps or similar APIs
        return 96.0  # Default Windows DPI
    
    def _detect_display_type(self, device_name: str) -> DisplayType:
        """Detect display connection type from device name"""
        name_lower = device_name.lower()
        
        if 'hdmi' in name_lower:
            return DisplayType.HDMI
        elif 'displayport' in name_lower or 'dp' in name_lower:
            return DisplayType.DISPLAYPORT
        elif 'dvi' in name_lower:
            return DisplayType.DVI
        elif 'vga' in name_lower:
            return DisplayType.VGA
        elif 'usb' in name_lower:
            return DisplayType.USB_C
        elif 'thunderbolt' in name_lower:
            return DisplayType.THUNDERBOLT
        elif 'wireless' in name_lower or 'wifi' in name_lower:
            return DisplayType.WIRELESS
        else:
            return DisplayType.UNKNOWN
    
    def _get_display_rotation(self, settings) -> int:
        """Get display rotation from settings"""
        # Placeholder - would extract from actual settings
        return 0
    
    def _get_windows_scale_factor(self, device_name: str) -> float:
        """Get Windows display scale factor"""
        # Placeholder - would use Windows API to get actual scale factor
        return 1.0
    
    def _parse_xrandr_resolution(self, line: str) -> Optional[Tuple[int, int, int, int, int]]:
        """Parse resolution and position from xrandr output line"""
        try:
            # Look for pattern like "1920x1080+0+0"
            import re
            pattern = r'(\d+)x(\d+)\+(\d+)\+(\d+)'
            match = re.search(pattern, line)
            
            if match:
                width = int(match.group(1))
                height = int(match.group(2))
                pos_x = int(match.group(3))
                pos_y = int(match.group(4))
                rotation = 0  # Would need additional parsing for rotation
                
                return width, height, pos_x, pos_y, rotation
        except Exception:
            pass
        
        return None
    
    def _extract_refresh_rate(self, line: str) -> Optional[float]:
        """Extract refresh rate from xrandr mode line"""
        try:
            # Look for refresh rate pattern
            import re
            pattern = r'(\d+\.\d+)\*'
            match = re.search(pattern, line)
            
            if match:
                return float(match.group(1))
        except Exception:
            pass
        
        return None


# Factory function
def create_screen_detection_system(logger=None) -> ScreenDetectionSystem:
    """Factory function to create a screen detection system"""
    return ScreenDetectionSystem(logger=logger)