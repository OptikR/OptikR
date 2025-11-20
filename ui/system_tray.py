"""
System Tray Icon
Provides system tray functionality for minimizing to tray.
"""

from PyQt6.QtWidgets import QSystemTrayIcon, QMenu
from PyQt6.QtGui import QIcon, QAction
from PyQt6.QtCore import QObject, pyqtSignal
from pathlib import Path


class SystemTrayManager(QObject):
    """Manages system tray icon and menu."""
    
    # Signals
    showRequested = pyqtSignal()
    quitRequested = pyqtSignal()
    
    def __init__(self, parent=None, config_manager=None):
        """
        Initialize system tray manager.
        
        Args:
            parent: Parent QObject
            config_manager: Configuration manager for settings
        """
        super().__init__(parent)
        
        self.config_manager = config_manager
        self.tray_icon = None
        self.tray_menu = None
        self.main_window = parent
        
        # Check if tray is enabled in config
        self.enabled = self._is_tray_enabled()
        
        if self.enabled:
            self._create_tray_icon()
    
    def _is_tray_enabled(self) -> bool:
        """Check if system tray is enabled in configuration."""
        if not self.config_manager:
            return True  # Default to enabled
        
        return self.config_manager.get_setting('startup.minimize_to_tray', True)
    
    def _create_tray_icon(self):
        """Create system tray icon and menu."""
        # Create tray icon
        self.tray_icon = QSystemTrayIcon(self.main_window)
        
        # Try to load icon
        icon_path = Path(__file__).parent.parent / "assets" / "icon.png"
        if icon_path.exists():
            self.tray_icon.setIcon(QIcon(str(icon_path)))
        else:
            # Use default icon if custom icon not found
            from PyQt6.QtWidgets import QApplication
            self.tray_icon.setIcon(QApplication.style().standardIcon(
                QApplication.style().StandardPixmap.SP_ComputerIcon
            ))
        
        self.tray_icon.setToolTip("OptikR - Real-time Translation")
        
        # Create context menu
        self._create_tray_menu()
        
        # Connect signals
        self.tray_icon.activated.connect(self._on_tray_activated)
        
        # Show tray icon
        self.tray_icon.show()
        
        print("[INFO] System tray icon created")
    
    def _create_tray_menu(self):
        """Create tray icon context menu."""
        self.tray_menu = QMenu()
        
        # Show/Hide action
        show_action = QAction("Show OptikR", self.main_window)
        show_action.triggered.connect(self._on_show_requested)
        self.tray_menu.addAction(show_action)
        
        self.tray_menu.addSeparator()
        
        # Quit action
        quit_action = QAction("Quit", self.main_window)
        quit_action.triggered.connect(self._on_quit_requested)
        self.tray_menu.addAction(quit_action)
        
        # Set menu
        self.tray_icon.setContextMenu(self.tray_menu)
    
    def _on_tray_activated(self, reason):
        """Handle tray icon activation."""
        if reason == QSystemTrayIcon.ActivationReason.Trigger:
            # Single click - show window
            self._on_show_requested()
        elif reason == QSystemTrayIcon.ActivationReason.DoubleClick:
            # Double click - show window
            self._on_show_requested()
    
    def _on_show_requested(self):
        """Handle show window request."""
        self.showRequested.emit()
    
    def _on_quit_requested(self):
        """Handle quit request."""
        self.quitRequested.emit()
    
    def show_message(self, title: str, message: str, icon=QSystemTrayIcon.MessageIcon.Information, duration: int = 3000):
        """
        Show a system tray notification.
        
        Args:
            title: Notification title
            message: Notification message
            icon: Icon type (Information, Warning, Critical)
            duration: Display duration in milliseconds
        """
        if self.tray_icon and self.enabled:
            self.tray_icon.showMessage(title, message, icon, duration)
    
    def set_enabled(self, enabled: bool):
        """
        Enable or disable system tray.
        
        Args:
            enabled: True to enable, False to disable
        """
        print(f"[SYSTEM TRAY] set_enabled called with: {enabled}")
        self.enabled = enabled
        
        if enabled and not self.tray_icon:
            # Create tray icon if it doesn't exist
            self._create_tray_icon()
            print("[INFO] System tray icon enabled and created")
        elif not enabled and self.tray_icon:
            # Hide and destroy tray icon
            self.tray_icon.hide()
            self.tray_icon = None
            print("[INFO] System tray icon disabled and destroyed")
        
        print(f"[SYSTEM TRAY] After set_enabled: enabled={self.enabled}, tray_icon={self.tray_icon is not None}")
    
    def is_enabled(self) -> bool:
        """Check if system tray is enabled."""
        return self.enabled and self.tray_icon is not None
    
    def cleanup(self):
        """Clean up system tray resources."""
        if self.tray_icon:
            self.tray_icon.hide()
            self.tray_icon = None
