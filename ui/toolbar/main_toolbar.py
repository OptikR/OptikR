"""
Main Toolbar Module

Bottom toolbar with action buttons for the Real-Time Translation System.

Author: Real-Time Translation System
Date: 2024
"""

from PyQt6.QtWidgets import QWidget, QHBoxLayout, QLabel, QPushButton
from PyQt6.QtCore import pyqtSignal

# Import translation system
from app.translations import TranslatableMixin


class MainToolbar(TranslatableMixin, QWidget):
    """
    Bottom toolbar widget with action buttons.
    
    Signals:
        startClicked: Emitted when Start/Stop button clicked
        captureRegionClicked: Emitted when Select Capture Region clicked
        monitorClicked: Emitted when Monitor button clicked
        helpClicked: Emitted when Help button clicked
        regionOverlayClicked: Emitted when Region Overlay button clicked
        saveClicked: Emitted when Save button clicked
        importClicked: Emitted when Import button clicked
        exportClicked: Emitted when Export button clicked
    """
    
    # Signals
    startClicked = pyqtSignal()
    captureRegionClicked = pyqtSignal()
    monitorClicked = pyqtSignal()
    helpClicked = pyqtSignal()
    regionOverlayClicked = pyqtSignal()
    saveClicked = pyqtSignal()
    importClicked = pyqtSignal()
    exportClicked = pyqtSignal()
    themeToggled = pyqtSignal(bool)  # True = dark mode, False = light mode
    
    def __init__(self, parent=None):
        """
        Initialize toolbar widget.
        
        Args:
            parent: Parent widget (optional)
        """
        super().__init__(parent)
        self.init_ui()
    
    def init_ui(self):
        """Initialize the toolbar UI."""
        self.setObjectName("toolbar")
        self.setStyleSheet(
            "QWidget#toolbar { background-color: #FFFFFF; border-top: 1px solid #D0D0D0; }"
        )
        
        toolbar_layout = QHBoxLayout(self)
        toolbar_layout.setContentsMargins(10, 8, 10, 8)
        toolbar_layout.setSpacing(10)
        
        # Start button (Green)
        self.start_btn = QPushButton()
        self.set_translatable_text(self.start_btn, "start")
        self.start_btn.setObjectName("startButton")
        self.start_btn.setMinimumWidth(100)
        self.start_btn.clicked.connect(self.startClicked.emit)
        toolbar_layout.addWidget(self.start_btn)
        
        # Select Capture Region button (Teal)
        self.capture_region_btn = QPushButton()
        self.set_translatable_text(self.capture_region_btn, "select_capture_region")
        self.capture_region_btn.setObjectName("captureRegionButton")
        self.capture_region_btn.setMinimumWidth(160)
        self.capture_region_btn.clicked.connect(self.captureRegionClicked.emit)
        toolbar_layout.addWidget(self.capture_region_btn)
        
        # Monitor button (Orange)
        self.monitor_btn = QPushButton()
        self.set_translatable_text(self.monitor_btn, "monitor")
        self.monitor_btn.setObjectName("monitorButton")
        self.monitor_btn.setMinimumWidth(100)
        self.monitor_btn.clicked.connect(self.monitorClicked.emit)
        toolbar_layout.addWidget(self.monitor_btn)
        
        # Help button (Purple)
        self.help_btn = QPushButton()
        self.set_translatable_text(self.help_btn, "help")
        self.help_btn.setObjectName("helpButton")
        self.help_btn.setMinimumWidth(100)
        self.help_btn.clicked.connect(self.helpClicked.emit)
        toolbar_layout.addWidget(self.help_btn)
        
        # Region Overlay button (Blue Gray)
        self.region_btn = QPushButton()
        self.set_translatable_text(self.region_btn, "region_overlay")
        self.region_btn.setObjectName("regionButton")
        self.region_btn.setMinimumWidth(120)
        self.region_btn.clicked.connect(self.regionOverlayClicked.emit)
        toolbar_layout.addWidget(self.region_btn)
        
        # Save Settings button
        self.save_btn = QPushButton()
        self.set_translatable_text(self.save_btn, "save")
        self.save_btn.setProperty("class", "action")
        self.save_btn.setMinimumWidth(80)
        self.save_btn.setEnabled(False)  # Disabled by default (no changes yet)
        self.save_btn.setToolTip("No unsaved changes")
        self.save_btn.clicked.connect(self.saveClicked.emit)
        toolbar_layout.addWidget(self.save_btn)
        
        # Import Settings button
        self.import_btn = QPushButton()
        self.set_translatable_text(self.import_btn, "import")
        self.import_btn.setProperty("class", "action")
        self.import_btn.setMinimumWidth(80)
        self.import_btn.clicked.connect(self.importClicked.emit)
        toolbar_layout.addWidget(self.import_btn)
        
        # Export Settings button
        self.export_btn = QPushButton()
        self.set_translatable_text(self.export_btn, "export")
        self.export_btn.setProperty("class", "action")
        self.export_btn.setMinimumWidth(80)
        self.export_btn.clicked.connect(self.exportClicked.emit)
        toolbar_layout.addWidget(self.export_btn)
        
        toolbar_layout.addStretch()
        
        # Theme toggle button
        self.theme_btn = QPushButton()
        self.theme_btn.setProperty("class", "action")
        self.theme_btn.setMinimumWidth(100)
        self.theme_btn.clicked.connect(self._on_theme_toggle)
        toolbar_layout.addWidget(self.theme_btn)
        
        # Track current theme (default is light mode)
        self.is_dark_mode = False
        
        # Set initial theme button text
        self._update_theme_button_text()
    
    # Public methods for controlling toolbar state
    
    def set_start_button_text(self, text):
        """
        Set start button text.
        
        Args:
            text: Button text (e.g., '▶ Start' or '⏸ Stop')
        """
        self.start_btn.setText(text)
    
    def set_start_button_style(self, style):
        """
        Set start button style.
        
        Args:
            style: CSS style string (e.g., 'background-color: #F44336;')
        """
        self.start_btn.setStyleSheet(style)
    
    def set_save_enabled(self, enabled):
        """
        Enable/disable save button.
        
        Args:
            enabled: True to enable, False to disable
        """
        self.save_btn.setEnabled(enabled)
        if enabled:
            self.save_btn.setToolTip("Save all settings")
        else:
            self.save_btn.setToolTip("No unsaved changes")
    
    def set_status(self, text, color="#4CAF50"):
        """
        Set status label text and color.
        
        Args:
            text: Status text
            color: CSS color (default: green)
        
        Note: Status label removed from toolbar - this method is kept for compatibility
        """
        pass  # Status label removed from UI
    
    def get_start_button(self):
        """Get reference to start button."""
        return self.start_btn
    
    def get_save_button(self):
        """Get reference to save button."""
        return self.save_btn
    
    def _on_theme_toggle(self):
        """Handle theme toggle button click."""
        self.is_dark_mode = not self.is_dark_mode
        self._update_theme_button_text()
        self.themeToggled.emit(self.is_dark_mode)
    
    def _update_theme_button_text(self):
        """Update theme button text based on current mode."""
        from app.translations import tr
        if self.is_dark_mode:
            self.set_translatable_text(self.theme_btn, "light_mode")
            self.theme_btn.setToolTip(tr("switch_to_light_mode"))
        else:
            self.set_translatable_text(self.theme_btn, "dark_mode")
            self.theme_btn.setToolTip(tr("switch_to_dark_mode"))
    
    def set_theme(self, is_dark):
        """
        Set the current theme without emitting signal.
        
        Args:
            is_dark: True for dark mode, False for light mode
        """
        self.is_dark_mode = is_dark
        self._update_theme_button_text()
