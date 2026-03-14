"""
System Tray Icon
Provides system tray functionality for minimizing to tray.
"""

import logging

from PyQt6.QtWidgets import QSystemTrayIcon, QMenu
from PyQt6.QtGui import QAction
from PyQt6.QtCore import QObject, pyqtSignal

from app.localization import tr

logger = logging.getLogger(__name__)


class SystemTrayManager(QObject):
    """Manages system tray icon and menu."""
    
    # Signals
    showRequested = pyqtSignal()
    quitRequested = pyqtSignal()
    
    def __init__(self, parent=None, config_manager=None):
        """
        Initialize system tray manager.
        
        Args:
            parent: Parent QObject (typically MainWindow)
            config_manager: Configuration manager for settings
        """
        super().__init__(parent)
        
        self.config_manager = config_manager
        self.tray_icon = None
        self.tray_menu = None
        self.main_window = parent
        
        self.enabled = self._is_tray_enabled()
        
        if self.enabled:
            self._create_tray_icon()
    
    def _is_tray_enabled(self) -> bool:
        """Check if system tray is enabled in configuration."""
        if not self.config_manager:
            return False
        return self.config_manager.get_setting('startup.minimize_to_tray', False)

    def _create_tray_icon(self):
        """Create system tray icon and menu."""
        self.tray_icon = QSystemTrayIcon(self.main_window)
        
        # Use default system icon (assets/icon.png does not exist)
        from PyQt6.QtWidgets import QApplication
        self.tray_icon.setIcon(QApplication.style().standardIcon(
            QApplication.style().StandardPixmap.SP_ComputerIcon
        ))
        
        self.tray_icon.setToolTip("OptikR - Real-time Translation")
        
        self._create_tray_menu()
        self.tray_icon.activated.connect(self._on_tray_activated)
        self.tray_icon.show()
        
        logger.info("System tray icon created")
    
    def _create_tray_menu(self):
        """Create tray icon context menu."""
        self.tray_menu = QMenu()
        
        show_action = QAction(tr("show_optikr", "Show OptikR"), self.main_window)
        show_action.triggered.connect(self._on_show_requested)
        self.tray_menu.addAction(show_action)
        
        self.tray_menu.addSeparator()
        
        quit_action = QAction(tr("quit", "Quit"), self.main_window)
        quit_action.triggered.connect(self._on_quit_requested)
        self.tray_menu.addAction(quit_action)
        
        self.tray_icon.setContextMenu(self.tray_menu)
    
    def _on_tray_activated(self, reason):
        """Handle tray icon activation (single or double click)."""
        if reason in (QSystemTrayIcon.ActivationReason.Trigger,
                      QSystemTrayIcon.ActivationReason.DoubleClick):
            self._on_show_requested()
    
    def _on_show_requested(self):
        """Handle show window request."""
        self.showRequested.emit()
    
    def _on_quit_requested(self):
        """Handle quit request."""
        self.quitRequested.emit()
    
    def show_message(self, title: str, message: str,
                     icon=QSystemTrayIcon.MessageIcon.Information, duration: int = 3000):
        """Show a system tray notification."""
        if self.tray_icon and self.enabled:
            self.tray_icon.showMessage(title, message, icon, duration)
    
    def set_enabled(self, enabled: bool):
        """Enable or disable system tray at runtime."""
        logger.debug("System tray set_enabled: %s", enabled)
        self.enabled = enabled
        
        if enabled and not self.tray_icon:
            self._create_tray_icon()
        elif not enabled and self.tray_icon:
            self.tray_icon.hide()
            self.tray_icon = None
            logger.info("System tray icon disabled")
    
    def is_enabled(self) -> bool:
        """Check if system tray is enabled."""
        return self.enabled and self.tray_icon is not None
    
    def cleanup(self):
        """Clean up system tray resources."""
        if self.tray_icon:
            self.tray_icon.hide()
            self.tray_icon = None
