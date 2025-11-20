"""
Loading Overlay Module

Professional loading overlay that displays while the application initializes.
Shows progress and status messages during startup.

Author: OptikR Team
Date: 2024
"""

from PyQt6.QtWidgets import QWidget, QVBoxLayout, QLabel, QProgressBar
from PyQt6.QtCore import Qt, QTimer
from PyQt6.QtGui import QFont


class LoadingOverlay(QWidget):
    """
    Loading overlay widget that displays during application initialization.
    
    Shows a progress bar and status messages while components load.
    """
    
    def __init__(self, parent=None):
        """
        Initialize loading overlay.
        
        Args:
            parent: Parent widget (optional)
        """
        super().__init__(parent)
        self.setObjectName("loadingOverlay")
        
        # Make it cover the entire parent
        if parent:
            self.setGeometry(parent.rect())
        
        self.init_ui()
    
    def init_ui(self):
        """Initialize the loading overlay UI."""
        # Semi-transparent background
        self.setStyleSheet("""
            QWidget#loadingOverlay {
                background-color: rgba(0, 0, 0, 180);
            }
            QWidget#contentBox {
                background-color: #2C3E50;
                border: 2px solid #34495E;
                border-radius: 10px;
            }
            QLabel#titleLabel {
                font-size: 24pt;
                font-weight: bold;
                color: #FFFFFF;
            }
            QLabel#statusLabel {
                font-size: 11pt;
                color: #BDC3C7;
            }
            QProgressBar {
                border: 2px solid #34495E;
                border-radius: 5px;
                text-align: center;
                background-color: #34495E;
                height: 25px;
                color: #FFFFFF;
            }
            QProgressBar::chunk {
                background-color: #3498DB;
                border-radius: 3px;
            }
        """)
        
        # Main layout (covers entire window)
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.setAlignment(Qt.AlignmentFlag.AlignCenter)
        
        # Content box (centered black box)
        content_box = QWidget()
        content_box.setObjectName("contentBox")
        content_box.setFixedSize(500, 300)
        
        # Content layout inside the box
        content_layout = QVBoxLayout(content_box)
        content_layout.setContentsMargins(40, 40, 40, 40)
        content_layout.setSpacing(20)
        content_layout.setAlignment(Qt.AlignmentFlag.AlignCenter)
        
        # Title
        self.title_label = QLabel("OptikR")
        self.title_label.setObjectName("titleLabel")
        self.title_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        content_layout.addWidget(self.title_label)
        
        # Status message
        self.status_label = QLabel("Initializing...")
        self.status_label.setObjectName("statusLabel")
        self.status_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        content_layout.addWidget(self.status_label)
        
        # Progress bar
        self.progress_bar = QProgressBar()
        self.progress_bar.setMinimum(0)
        self.progress_bar.setMaximum(100)
        self.progress_bar.setValue(0)
        self.progress_bar.setTextVisible(True)
        content_layout.addWidget(self.progress_bar)
        
        # Add content box to main layout
        main_layout.addWidget(content_box)
        
        # Version info (bottom right) - outside the box
        self.version_label = QLabel("v0.1 (Early Release)")
        self.version_label.setStyleSheet("font-size: 9pt; color: #95A5A6; position: absolute; bottom: 10px; right: 10px;")
        self.version_label.setAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignBottom)
        
        # Create a container for version at bottom right
        version_container = QWidget()
        version_container.setStyleSheet("background: transparent;")
        version_layout = QVBoxLayout(version_container)
        version_layout.setContentsMargins(0, 0, 20, 20)
        version_layout.addStretch()
        version_layout.addWidget(self.version_label, alignment=Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignBottom)
        
        # Overlay version on top
        version_container.setParent(self)
        version_container.setGeometry(0, 0, self.width(), self.height())
    
    def set_status(self, message, progress=None):
        """
        Update status message and optionally progress.
        
        Args:
            message: Status message to display
            progress: Progress value (0-100) or None to keep current
        """
        self.status_label.setText(message)
        if progress is not None:
            self.progress_bar.setValue(progress)
    
    def set_progress(self, value):
        """
        Set progress bar value.
        
        Args:
            value: Progress value (0-100)
        """
        self.progress_bar.setValue(value)
    
    def fade_out(self, duration=300):
        """
        Fade out and hide the overlay.
        
        Args:
            duration: Fade duration in milliseconds
        """
        # Simple hide for now (can add animation later)
        QTimer.singleShot(duration, self.hide)
    
    def resizeEvent(self, event):
        """Handle resize to cover parent."""
        if self.parent():
            self.setGeometry(self.parent().rect())
        
        # Update version container size if it exists
        if hasattr(self, 'version_label') and self.version_label.parent():
            self.version_label.parent().setGeometry(0, 0, self.width(), self.height())
        
        super().resizeEvent(event)
