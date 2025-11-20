"""
Base Settings Dialog Framework - PyQt6 Implementation
Provides the foundation for modular settings tabs using PyQt6.
"""

from PyQt6.QtWidgets import (
    QDialog, QTabWidget, QVBoxLayout, QHBoxLayout, 
    QPushButton, QLabel, QWidget, QMessageBox
)
from PyQt6.QtCore import pyqtSignal, Qt
from typing import List, Optional
from ui.custom_spinbox import CustomSpinBox, CustomDoubleSpinBox


class BaseSettingsDialog(QDialog):
    """Base class for settings dialog with tabbed navigation using PyQt6."""
    
    # Signal emitted when configuration changes
    configChanged = pyqtSignal()
    
    def __init__(self, parent=None, config_manager=None, main_window=None):
        """
        Initialize the base settings dialog.
        
        Args:
            parent: Parent widget
            config_manager: Configuration manager instance
            main_window: Reference to main application window
        """
        super().__init__(parent)
        
        self.config_manager = config_manager
        self.main_window = main_window
        
        # Track if configuration has changed
        self._config_changed = False
        
        # Store tabs
        self.tabs: List['BaseSettingsTab'] = []
        
        # UI components
        self.tab_widget: Optional[QTabWidget] = None
        self.status_label: Optional[QLabel] = None
        self.ok_button: Optional[QPushButton] = None
        self.apply_button: Optional[QPushButton] = None
        self.cancel_button: Optional[QPushButton] = None
        
        # Setup the dialog
        self._setup_ui()
        
    def _setup_ui(self):
        """Setup the dialog UI."""
        # Set window properties
        self.setWindowTitle("Settings")
        self.setMinimumSize(800, 600)
        self.resize(900, 700)
        
        # Make dialog modal
        self.setModal(True)
        
        # Create main layout
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(10, 10, 10, 10)
        main_layout.setSpacing(10)
        
        # Create tab widget
        self.tab_widget = QTabWidget()
        main_layout.addWidget(self.tab_widget)
        
        # Create tabs (to be overridden by subclass)
        self.create_tabs()
        
        # Create button frame
        button_layout = self._create_button_frame()
        main_layout.addLayout(button_layout)
        
        # Connect signals
        self.configChanged.connect(self._on_config_change)
        
    def create_tabs(self):
        """
        Create tabs - to be overridden by subclass.
        
        Subclasses should override this method to add their specific tabs
        using the add_tab() method.
        """
        pass
    
    def add_tab(self, tab_instance: 'BaseSettingsTab', title: str):
        """
        Add a tab to the dialog.
        
        Args:
            tab_instance: Instance of BaseSettingsTab or subclass
            title: Tab title to display
        """
        # Create the tab widget
        tab_widget = tab_instance.create_tab()
        
        # Add to tab widget
        self.tab_widget.addTab(tab_widget, title)
        
        # Store tab reference
        self.tabs.append(tab_instance)
        
        # Connect tab's change signal to dialog's change tracking
        tab_instance.settingChanged.connect(self.configChanged)
    
    def _create_button_frame(self) -> QHBoxLayout:
        """
        Create the button frame with OK, Cancel, Apply buttons.
        
        Returns:
            QHBoxLayout containing the buttons
        """
        button_layout = QHBoxLayout()
        button_layout.setSpacing(10)
        
        # Status label on the left
        self.status_label = QLabel("")
        self.status_label.setStyleSheet("color: #666666;")
        button_layout.addWidget(self.status_label)
        
        # Add stretch to push buttons to the right
        button_layout.addStretch()
        
        # OK button
        self.ok_button = QPushButton("OK")
        self.ok_button.setMinimumWidth(100)
        self.ok_button.clicked.connect(self.on_ok)
        button_layout.addWidget(self.ok_button)
        
        # Apply button
        self.apply_button = QPushButton("Apply")
        self.apply_button.setMinimumWidth(100)
        self.apply_button.clicked.connect(self.on_apply)
        button_layout.addWidget(self.apply_button)
        
        # Cancel button
        self.cancel_button = QPushButton("Cancel")
        self.cancel_button.setMinimumWidth(100)
        self.cancel_button.clicked.connect(self.on_cancel)
        button_layout.addWidget(self.cancel_button)
        
        return button_layout
    
    def show(self):
        """Show the settings dialog and load configuration."""
        # Load current configuration into all tabs
        self.load_configuration()
        
        # Reset change tracking
        self._config_changed = False
        self._update_status_label()
        
        # Show dialog
        super().show()
    
    def exec(self) -> int:
        """
        Show the dialog modally and return the result.
        
        Returns:
            QDialog.DialogCode (Accepted or Rejected)
        """
        # Load current configuration into all tabs
        self.load_configuration()
        
        # Reset change tracking
        self._config_changed = False
        self._update_status_label()
        
        # Show dialog modally
        return super().exec()
    
    def load_configuration(self):
        """Load configuration into all tabs."""
        for tab in self.tabs:
            try:
                tab.load_config()
            except Exception as e:
                print(f"[ERROR] Failed to load config for tab: {e}")
                import traceback
                traceback.print_exc()
    
    def save_configuration(self):
        """Save configuration from all tabs."""
        for tab in self.tabs:
            try:
                tab.save_config()
            except Exception as e:
                print(f"[ERROR] Failed to save config for tab: {e}")
                import traceback
                traceback.print_exc()
    
    def validate_all(self) -> bool:
        """
        Validate all tabs.
        
        Returns:
            True if all tabs are valid, False otherwise
        """
        for i, tab in enumerate(self.tabs):
            try:
                if not tab.validate():
                    # Switch to the tab with validation error
                    self.tab_widget.setCurrentIndex(i)
                    return False
            except Exception as e:
                print(f"[ERROR] Validation failed for tab: {e}")
                import traceback
                traceback.print_exc()
                return False
        return True
    
    def _on_config_change(self):
        """Called when any configuration changes."""
        self._config_changed = True
        self._update_status_label()
    
    def _update_status_label(self):
        """Update the status label based on change state."""
        if self._config_changed:
            self.status_label.setText("● Unsaved changes")
            self.status_label.setStyleSheet("color: #FF9800;")
        else:
            self.status_label.setText("")
            self.status_label.setStyleSheet("color: #666666;")
    
    def on_ok(self):
        """Handle OK button click - validate, save, and close."""
        if not self.validate_all():
            QMessageBox.warning(
                self,
                "Validation Error",
                "Please correct the errors before saving."
            )
            return
        
        # Save configuration
        self.save_configuration()
        self._config_changed = False
        
        # Accept and close dialog
        self.accept()
    
    def on_apply(self):
        """Handle Apply button click - validate and save without closing."""
        if not self.validate_all():
            QMessageBox.warning(
                self,
                "Validation Error",
                "Please correct the errors before saving."
            )
            return
        
        # Save configuration
        self.save_configuration()
        self._config_changed = False
        
        # Update status
        self.status_label.setText("✓ Settings saved")
        self.status_label.setStyleSheet("color: #4CAF50;")
        
        # Clear status after 3 seconds
        from PyQt6.QtCore import QTimer
        QTimer.singleShot(3000, lambda: self._update_status_label())
    
    def on_cancel(self):
        """Handle Cancel button click - check for unsaved changes."""
        if self._config_changed:
            reply = QMessageBox.question(
                self,
                "Unsaved Changes",
                "You have unsaved changes. Do you want to save them?",
                QMessageBox.StandardButton.Yes | 
                QMessageBox.StandardButton.No | 
                QMessageBox.StandardButton.Cancel,
                QMessageBox.StandardButton.Cancel
            )
            
            if reply == QMessageBox.StandardButton.Cancel:
                return
            elif reply == QMessageBox.StandardButton.Yes:
                if not self.validate_all():
                    QMessageBox.warning(
                        self,
                        "Validation Error",
                        "Please correct the errors before saving."
                    )
                    return
                self.save_configuration()
        
        # Reject and close dialog
        self.reject()
    
    def closeEvent(self, event):
        """Handle dialog close event."""
        if self._config_changed:
            reply = QMessageBox.question(
                self,
                "Unsaved Changes",
                "You have unsaved changes. Do you want to save them?",
                QMessageBox.StandardButton.Yes | 
                QMessageBox.StandardButton.No | 
                QMessageBox.StandardButton.Cancel,
                QMessageBox.StandardButton.Cancel
            )
            
            if reply == QMessageBox.StandardButton.Cancel:
                event.ignore()
                return
            elif reply == QMessageBox.StandardButton.Yes:
                if not self.validate_all():
                    QMessageBox.warning(
                        self,
                        "Validation Error",
                        "Please correct the errors before saving."
                    )
                    event.ignore()
                    return
                self.save_configuration()
        
        event.accept()


class BaseSettingsTab(QWidget):
    """Base class for individual settings tabs using PyQt6."""
    
    # Signal emitted when any setting changes
    settingChanged = pyqtSignal()
    
    def __init__(self, dialog: BaseSettingsDialog):
        """
        Initialize the base settings tab.
        
        Args:
            dialog: Parent BaseSettingsDialog instance
        """
        super().__init__()
        
        self.dialog = dialog
        self.config_manager = dialog.config_manager
        self.main_window = dialog.main_window
    
    def create_tab(self) -> QWidget:
        """
        Create the tab widget - to be overridden by subclass.
        
        Subclasses should override this method to create their specific UI.
        
        Returns:
            QWidget containing the tab's UI
        """
        # Default implementation returns self
        return self
    
    def create_scrollable_frame(self) -> QWidget:
        """
        Create a scrollable frame for tab content.
        
        Returns:
            QWidget that can be used as a container for scrollable content
        """
        from PyQt6.QtWidgets import QScrollArea, QWidget, QVBoxLayout
        
        # Create scroll area
        scroll_area = QScrollArea()
        scroll_area.setWidgetResizable(True)
        scroll_area.setFrameShape(QScrollArea.Shape.NoFrame)
        scroll_area.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        scroll_area.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAsNeeded)
        
        # Create content widget
        content_widget = QWidget()
        content_layout = QVBoxLayout(content_widget)
        content_layout.setContentsMargins(15, 15, 15, 15)
        content_layout.setSpacing(15)
        
        # Set content widget to scroll area
        scroll_area.setWidget(content_widget)
        
        return scroll_area, content_widget, content_layout
    
    def create_label(self, text: str, bold: bool = False, 
                    font_size: int = 9) -> QLabel:
        """
        Create a label with consistent styling.
        
        Args:
            text: Label text
            bold: Whether to make text bold
            font_size: Font size in points
            
        Returns:
            QLabel with specified styling
        """
        label = QLabel(text)
        
        if bold:
            label.setStyleSheet(f"font-weight: 600; font-size: {font_size}pt;")
        else:
            label.setStyleSheet(f"font-size: {font_size}pt;")
        
        return label
    
    def create_input(self, input_type: str = "text", **kwargs):
        """
        Create an input widget with consistent styling.
        
        Args:
            input_type: Type of input ("text", "number", "combo", "check", "radio")
            **kwargs: Additional arguments for the widget
            
        Returns:
            Appropriate QWidget based on input_type
        """
        from PyQt6.QtWidgets import (
            QLineEdit, QSpinBox, QComboBox, 
            QCheckBox, QRadioButton
        )
        
        if input_type == "text":
            widget = QLineEdit()
            if "placeholder" in kwargs:
                widget.setPlaceholderText(kwargs["placeholder"])
            return widget
            
        elif input_type == "number":
            widget = CustomSpinBox()
            if "min" in kwargs:
                widget.setMinimum(kwargs["min"])
            if "max" in kwargs:
                widget.setMaximum(kwargs["max"])
            if "value" in kwargs:
                widget.setValue(kwargs["value"])
            return widget
            
        elif input_type == "combo":
            widget = QComboBox()
            if "items" in kwargs:
                widget.addItems(kwargs["items"])
            return widget
            
        elif input_type == "check":
            text = kwargs.get("text", "")
            widget = QCheckBox(text)
            return widget
            
        elif input_type == "radio":
            text = kwargs.get("text", "")
            widget = QRadioButton(text)
            return widget
        
        # Default to line edit
        return QLineEdit()
    
    def on_change(self):
        """Called when any setting changes - emits settingChanged signal."""
        self.settingChanged.emit()
    
    def load_config(self):
        """
        Load configuration - to be overridden by subclass.
        
        Subclasses should override this method to load their specific settings
        from the config manager.
        """
        pass
    
    def save_config(self):
        """
        Save configuration - to be overridden by subclass.
        
        Subclasses should override this method to save their specific settings
        to the config manager.
        """
        pass
    
    def validate(self) -> bool:
        """
        Validate settings - to be overridden by subclass.
        
        Subclasses should override this method to validate their specific settings.
        
        Returns:
            True if settings are valid, False otherwise
        """
        return True
