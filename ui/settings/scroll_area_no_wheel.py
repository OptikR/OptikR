"""
Custom QScrollArea that ignores wheel events unless mouse is hovering over it.
This prevents the scroll area from stealing wheel events from parent widgets.
"""

from PyQt6.QtWidgets import QScrollArea
from PyQt6.QtCore import Qt, QEvent


class ScrollAreaNoWheel(QScrollArea):
    """
    Custom QScrollArea that only accepts wheel events when mouse is hovering.
    
    This prevents the scroll area from capturing wheel events when the user
    is scrolling the main window, which can be frustrating.
    """
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self._mouse_over = False
        self.setMouseTracking(True)
    
    def enterEvent(self, event):
        """Mouse entered the scroll area."""
        self._mouse_over = True
        super().enterEvent(event)
    
    def leaveEvent(self, event):
        """Mouse left the scroll area."""
        self._mouse_over = False
        super().leaveEvent(event)
    
    def wheelEvent(self, event):
        """Only process wheel events if mouse is hovering over this widget."""
        if self._mouse_over:
            # Mouse is over this scroll area - allow scrolling
            super().wheelEvent(event)
        else:
            # Mouse is not over this scroll area - ignore the event
            # This allows the event to propagate to parent widgets
            event.ignore()
