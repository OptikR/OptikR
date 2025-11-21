"""
System Tray Manager
OptikR Translation Overlay System

This module provides comprehensive system tray integration with:
- System tray icon with context menu
- Quick access controls for translation functions
- Status indicators and notifications
- Application lifecycle management from tray
- Cross-platform system tray support

Author: Niklas Verhasselt
Date: November 2025
"""

import threading
import time
from typing import Optional, Callable, Dict, Any, List
from dataclasses import dataclass
from enum import Enum
import tkinter as tk
from tkinter import messagebox

try:
    import pystray
    from PIL import Image, ImageDraw, ImageFont
    TRAY_AVAILABLE = True
except ImportError:
    TRAY_AVAILABLE = False

from ..models import SystemStatus
from ..interfaces import ILogger


class TrayIconState(Enum):
    """System tray icon states"""
    IDLE = "idle"
    ACTIVE = "active"
    ERROR = "error"
    DISABLED = "disabled"


@dataclass
class TrayNotification:
    """System tray notification"""
    title: str
    message: str
    icon_type: str = "info"  # info, warning, error
    duration: int = 3000  # milliseconds


class SystemTrayManager:
    """
    Comprehensive system tray manager with quick access controls.
    
    Features:
    - System tray icon with dynamic status indication
    - Context menu with translation controls
    - Status notifications and alerts
    - Application lifecycle management
    - Cross-platform compatibility
    """
    
    def __init__(self, logger: Optional[ILogger] = None):
        """Initialize system tray manager."""
        self.logger = logger
        self.tray_icon: Optional[pystray.Icon] = None
        self.icon_state = TrayIconState.IDLE
        self.is_running = False
        self.tray_thread: Optional[threading.Thread] = None
        
        # Callbacks
        self.show_window_callback: Optional[Callable[[], None]] = None
        self.hide_window_callback: Optional[Callable[[], None]] = None
        self.start_translation_callback: Optional[Callable[[], None]] = None
        self.stop_translation_callback: Optional[Callable[[], None]] = None
        self.pause_translation_callback: Optional[Callable[[], None]] = None
        self.resume_translation_callback: Optional[Callable[[], None]] = None
        self.show_settings_callback: Optional[Callable[[], None]] = None
        self.show_performance_callback: Optional[Callable[[], None]] = None
        self.exit_application_callback: Optional[Callable[[], None]] = None
        
        # State
        self.translation_active = False
        self.translation_paused = False
        self.system_status = SystemStatus.STOPPED
        
        # Check availability
        if not TRAY_AVAILABLE:
            if self.logger:
                self.logger.log_warning("System tray not available (pystray/PIL not installed)")
    
    def is_available(self) -> bool:
        """Check if system tray is available."""
        return TRAY_AVAILABLE
    
    def set_show_window_callback(self, callback: Callable[[], None]) -> None:
        """Set callback for showing main window."""
        self.show_window_callback = callback
    
    def set_hide_window_callback(self, callback: Callable[[], None]) -> None:
        """Set callback for hiding main window."""
        self.hide_window_callback = callback
    
    def set_start_translation_callback(self, callback: Callable[[], None]) -> None:
        """Set callback for starting translation."""
        self.start_translation_callback = callback
    
    def set_stop_translation_callback(self, callback: Callable[[], None]) -> None:
        """Set callback for stopping translation."""
        self.stop_translation_callback = callback
    
    def set_pause_translation_callback(self, callback: Callable[[], None]) -> None:
        """Set callback for pausing translation."""
        self.pause_translation_callback = callback
    
    def set_resume_translation_callback(self, callback: Callable[[], None]) -> None:
        """Set callback for resuming translation."""
        self.resume_translation_callback = callback
    
    def set_show_settings_callback(self, callback: Callable[[], None]) -> None:
        """Set callback for showing settings."""
        self.show_settings_callback = callback
    
    def set_show_performance_callback(self, callback: Callable[[], None]) -> None:
        """Set callback for showing performance monitor."""
        self.show_performance_callback = callback
    
    def set_exit_application_callback(self, callback: Callable[[], None]) -> None:
        """Set callback for exiting application."""
        self.exit_application_callback = callback
    
    def update_translation_state(self, active: bool, paused: bool = False) -> None:
        """Update translation state for menu updates."""
        self.translation_active = active
        self.translation_paused = paused
        
        # Update icon state
        if active and not paused:
            self.set_icon_state(TrayIconState.ACTIVE)
        elif active and paused:
            self.set_icon_state(TrayIconState.IDLE)
        else:
            self.set_icon_state(TrayIconState.IDLE)
    
    def update_system_status(self, status: SystemStatus) -> None:
        """Update system status for icon updates."""
        self.system_status = status
        
        # Update icon state based on system status
        if status == SystemStatus.ERROR:
            self.set_icon_state(TrayIconState.ERROR)
        elif status == SystemStatus.RUNNING:
            if self.translation_active:
                self.set_icon_state(TrayIconState.ACTIVE)
            else:
                self.set_icon_state(TrayIconState.IDLE)
        else:
            self.set_icon_state(TrayIconState.IDLE)
    
    def set_icon_state(self, state: TrayIconState) -> None:
        """Set tray icon state and update icon."""
        if self.icon_state != state:
            self.icon_state = state
            if self.tray_icon:
                self.tray_icon.icon = self._create_icon(state)
    
    def _create_icon(self, state: TrayIconState) -> Image.Image:
        """Create tray icon based on state."""
        size = 64
        image = Image.new('RGBA', (size, size), (0, 0, 0, 0))
        draw = ImageDraw.Draw(image)
        
        # Base colors for different states
        colors = {
            TrayIconState.IDLE: (100, 100, 100, 255),      # Gray
            TrayIconState.ACTIVE: (0, 150, 0, 255),        # Green
            TrayIconState.ERROR: (200, 0, 0, 255),         # Red
            TrayIconState.DISABLED: (50, 50, 50, 255)      # Dark gray
        }
        
        color = colors.get(state, colors[TrayIconState.IDLE])
        
        # Draw background circle
        margin = 4
        draw.ellipse([margin, margin, size-margin, size-margin], fill=color)
        
        # Draw "T" for Translation
        try:
            # Try to use a font
            font = ImageFont.truetype("arial.ttf", size//3)
        except:
            # Fallback to default font
            font = ImageFont.load_default()
        
        # Calculate text position
        text = "T"
        bbox = draw.textbbox((0, 0), text, font=font)
        text_width = bbox[2] - bbox[0]
        text_height = bbox[3] - bbox[1]
        text_x = (size - text_width) // 2
        text_y = (size - text_height) // 2
        
        # Draw text
        draw.text((text_x, text_y), text, fill=(255, 255, 255, 255), font=font)
        
        # Add state indicator
        if state == TrayIconState.ACTIVE:
            # Add small green dot for active state
            dot_size = 12
            dot_x = size - dot_size - 2
            dot_y = 2
            draw.ellipse([dot_x, dot_y, dot_x + dot_size, dot_y + dot_size], 
                        fill=(0, 255, 0, 255))
        elif state == TrayIconState.ERROR:
            # Add small red exclamation for error state
            exc_x = size - 16
            exc_y = 4
            draw.text((exc_x, exc_y), "!", fill=(255, 255, 0, 255), font=font)
        
        return image
    
    def _create_menu(self) -> pystray.Menu:
        """Create system tray context menu."""
        menu_items = []
        
        # Show/Hide window
        menu_items.append(pystray.MenuItem(
            "Show Window",
            self._on_show_window,
            default=True
        ))
        
        menu_items.append(pystray.Menu.SEPARATOR)
        
        # Translation controls
        if self.translation_active:
            if self.translation_paused:
                menu_items.append(pystray.MenuItem(
                    "Resume Translation",
                    self._on_resume_translation
                ))
            else:
                menu_items.append(pystray.MenuItem(
                    "Pause Translation",
                    self._on_pause_translation
                ))
            
            menu_items.append(pystray.MenuItem(
                "Stop Translation",
                self._on_stop_translation
            ))
        else:
            menu_items.append(pystray.MenuItem(
                "Start Translation",
                self._on_start_translation
            ))
        
        menu_items.append(pystray.Menu.SEPARATOR)
        
        # Quick access
        menu_items.append(pystray.MenuItem(
            "Settings",
            self._on_show_settings
        ))
        
        menu_items.append(pystray.MenuItem(
            "Performance Monitor",
            self._on_show_performance
        ))
        
        menu_items.append(pystray.Menu.SEPARATOR)
        
        # System status
        status_text = f"Status: {self.system_status.value.title()}"
        menu_items.append(pystray.MenuItem(
            status_text,
            None,  # No action, just informational
            enabled=False
        ))
        
        menu_items.append(pystray.Menu.SEPARATOR)
        
        # Exit
        menu_items.append(pystray.MenuItem(
            "Exit",
            self._on_exit_application
        ))
        
        return pystray.Menu(*menu_items)
    
    def start(self) -> bool:
        """Start system tray."""
        if not TRAY_AVAILABLE:
            if self.logger:
                self.logger.log_warning("Cannot start system tray: not available")
            return False
        
        if self.is_running:
            if self.logger:
                self.logger.log_warning("System tray already running")
            return True
        
        try:
            # Create tray icon
            icon_image = self._create_icon(self.icon_state)
            menu = self._create_menu()
            
            self.tray_icon = pystray.Icon(
                "RealTimeTranslation",
                icon_image,
                "OptikR Translation Overlay",
                menu
            )
            
            # Start tray in separate thread
            self.tray_thread = threading.Thread(
                target=self._run_tray,
                daemon=True
            )
            self.tray_thread.start()
            
            self.is_running = True
            
            if self.logger:
                self.logger.log_info("System tray started")
            
            return True
            
        except Exception as e:
            if self.logger:
                self.logger.log_error(f"Failed to start system tray: {e}")
            return False
    
    def stop(self) -> None:
        """Stop system tray."""
        if not self.is_running:
            return
        
        try:
            if self.tray_icon:
                self.tray_icon.stop()
            
            self.is_running = False
            
            if self.logger:
                self.logger.log_info("System tray stopped")
            
        except Exception as e:
            if self.logger:
                self.logger.log_error(f"Error stopping system tray: {e}")
    
    def _run_tray(self) -> None:
        """Run system tray (called in separate thread)."""
        try:
            if self.tray_icon:
                self.tray_icon.run()
        except Exception as e:
            if self.logger:
                self.logger.log_error(f"System tray error: {e}")
    
    def update_menu(self) -> None:
        """Update tray menu (call when state changes)."""
        if self.tray_icon:
            self.tray_icon.menu = self._create_menu()
    
    def show_notification(self, notification: TrayNotification) -> None:
        """Show system tray notification."""
        if not self.is_running or not self.tray_icon:
            return
        
        try:
            # Use system notification if available
            if hasattr(self.tray_icon, 'notify'):
                self.tray_icon.notify(
                    notification.message,
                    notification.title
                )
            else:
                # Fallback to messagebox
                if notification.icon_type == "error":
                    messagebox.showerror(notification.title, notification.message)
                elif notification.icon_type == "warning":
                    messagebox.showwarning(notification.title, notification.message)
                else:
                    messagebox.showinfo(notification.title, notification.message)
                    
        except Exception as e:
            if self.logger:
                self.logger.log_error(f"Failed to show notification: {e}")
    
    # Menu callback methods
    def _on_show_window(self, icon=None, item=None) -> None:
        """Handle show window menu item."""
        if self.show_window_callback:
            try:
                self.show_window_callback()
            except Exception as e:
                if self.logger:
                    self.logger.log_error(f"Error in show window callback: {e}")
    
    def _on_start_translation(self, icon=None, item=None) -> None:
        """Handle start translation menu item."""
        if self.start_translation_callback:
            try:
                self.start_translation_callback()
                self.update_translation_state(True, False)
                self.update_menu()
            except Exception as e:
                if self.logger:
                    self.logger.log_error(f"Error in start translation callback: {e}")
    
    def _on_stop_translation(self, icon=None, item=None) -> None:
        """Handle stop translation menu item."""
        if self.stop_translation_callback:
            try:
                self.stop_translation_callback()
                self.update_translation_state(False, False)
                self.update_menu()
            except Exception as e:
                if self.logger:
                    self.logger.log_error(f"Error in stop translation callback: {e}")
    
    def _on_pause_translation(self, icon=None, item=None) -> None:
        """Handle pause translation menu item."""
        if self.pause_translation_callback:
            try:
                self.pause_translation_callback()
                self.update_translation_state(True, True)
                self.update_menu()
            except Exception as e:
                if self.logger:
                    self.logger.log_error(f"Error in pause translation callback: {e}")
    
    def _on_resume_translation(self, icon=None, item=None) -> None:
        """Handle resume translation menu item."""
        if self.resume_translation_callback:
            try:
                self.resume_translation_callback()
                self.update_translation_state(True, False)
                self.update_menu()
            except Exception as e:
                if self.logger:
                    self.logger.log_error(f"Error in resume translation callback: {e}")
    
    def _on_show_settings(self, icon=None, item=None) -> None:
        """Handle show settings menu item."""
        if self.show_settings_callback:
            try:
                self.show_settings_callback()
            except Exception as e:
                if self.logger:
                    self.logger.log_error(f"Error in show settings callback: {e}")
    
    def _on_show_performance(self, icon=None, item=None) -> None:
        """Handle show performance monitor menu item."""
        if self.show_performance_callback:
            try:
                self.show_performance_callback()
            except Exception as e:
                if self.logger:
                    self.logger.log_error(f"Error in show performance callback: {e}")
    
    def _on_exit_application(self, icon=None, item=None) -> None:
        """Handle exit application menu item."""
        if self.exit_application_callback:
            try:
                self.exit_application_callback()
            except Exception as e:
                if self.logger:
                    self.logger.log_error(f"Error in exit application callback: {e}")


def create_system_tray_manager(logger: Optional[ILogger] = None) -> SystemTrayManager:
    """
    Create system tray manager instance.
    
    Args:
        logger: Optional logger for error reporting
        
    Returns:
        SystemTrayManager: Configured system tray manager
    """
    return SystemTrayManager(logger)