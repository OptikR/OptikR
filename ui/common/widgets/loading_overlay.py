"""
Loading Overlay Module

Standalone loading overlay shown during application startup.
Displays a centered content box with progress bar and status messages.
"""

from PyQt6.QtWidgets import QWidget, QVBoxLayout, QLabel, QProgressBar, QApplication
from PyQt6.QtCore import Qt, QTimer

import app


class LoadingOverlay(QWidget):
    """
    Loading overlay that displays during application initialization.

    Can run as a standalone top-level window (no parent) for startup,
    or as a child overlay covering a parent widget.
    """

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setObjectName("loadingOverlay")

        if parent:
            # Child mode — cover the parent
            self.setGeometry(parent.rect())
        else:
            # Standalone splash mode — frameless centered window
            self.setWindowFlags(
                Qt.WindowType.FramelessWindowHint
                | Qt.WindowType.WindowStaysOnTopHint
            )
            self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
            self.setFixedSize(560, 360)

        self._init_ui()

        if not parent:
            self._center_on_screen()

    def _center_on_screen(self):
        """Center the overlay on the primary screen."""
        screen = QApplication.primaryScreen()
        if screen:
            geo = screen.availableGeometry()
            x = geo.x() + (geo.width() - self.width()) // 2
            y = geo.y() + (geo.height() - self.height()) // 2
            self.move(x, y)

    def _init_ui(self):
        """Build the UI."""
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
            QLabel#subtitleLabel {
                font-size: 11pt;
                color: #BDC3C7;
            }
            QLabel#statusLabel {
                font-size: 10pt;
                color: #BDC3C7;
            }
            QLabel#versionLabel {
                font-size: 9pt;
                color: #95A5A6;
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

        # Main layout
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.setAlignment(Qt.AlignmentFlag.AlignCenter)

        # Content box
        content_box = QWidget()
        content_box.setObjectName("contentBox")
        content_box.setFixedSize(500, 300)

        content_layout = QVBoxLayout(content_box)
        content_layout.setContentsMargins(40, 30, 40, 30)
        content_layout.setSpacing(12)
        content_layout.setAlignment(Qt.AlignmentFlag.AlignCenter)

        # Title
        self.title_label = QLabel("OptikR")
        self.title_label.setObjectName("titleLabel")
        self.title_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        content_layout.addWidget(self.title_label)

        # Subtitle
        subtitle = QLabel("Real-Time Screen Translation")
        subtitle.setObjectName("subtitleLabel")
        subtitle.setAlignment(Qt.AlignmentFlag.AlignCenter)
        content_layout.addWidget(subtitle)

        content_layout.addSpacing(10)

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

        # Version
        self.version_label = QLabel(f"v{app.__version__}")
        self.version_label.setObjectName("versionLabel")
        self.version_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        content_layout.addWidget(self.version_label)

        main_layout.addWidget(content_box)

    # -- Public API (compatible with OptikRSplashScreen) ------------------

    def set_status(self, message, progress=None):
        """Update status message and optionally progress."""
        self.status_label.setText(message)
        if progress is not None:
            self.progress_bar.setValue(progress)

    def set_progress(self, value, status=""):
        """Update progress and status text (splash-screen compatible API)."""
        self.progress_bar.setValue(min(value, 100))
        if status:
            self.status_label.setText(status)
        QApplication.processEvents()

    def finish_with_delay(self, window, delay_ms=500):
        """Close the overlay after a short delay."""
        QTimer.singleShot(delay_ms, self.close)

    def resizeEvent(self, event):
        """Handle resize to cover parent when used as child overlay."""
        if self.parent():
            self.setGeometry(self.parent().rect())
        super().resizeEvent(event)
