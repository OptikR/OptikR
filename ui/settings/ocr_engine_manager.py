"""
OCR Engine Manager
Handles OCR engine status management and initialization.
"""

from PyQt6.QtWidgets import QLabel


class OCREngineManager:
    """Manages OCR engine status and initialization."""
    
    def __init__(self, parent=None):
        """Initialize the engine manager."""
        self.parent = parent
        self.status_labels = {}
    
    def register_status_label(self, engine_name: str, label: QLabel):
        """
        Register a status label for an engine.
        
        Args:
            engine_name: Name of the engine (e.g., 'easyocr', 'tesseract')
            label: QLabel widget to update with status
        """
        self.status_labels[engine_name] = label
    
    def update_status(self, engine_name: str, status: str):
        """
        Update status for a specific engine.
        
        Args:
            engine_name: Name of the engine
            status: Status string ('ready', 'not_loaded', 'loading', 'error', 'unknown')
        """
        if engine_name in self.status_labels:
            label = self.status_labels[engine_name]
            self._update_status_label(label, status)
    
    def _update_status_label(self, label: QLabel, status: str):
        """Update status label with appropriate icon and color."""
        status_map = {
            "ready": ("🟢", "Ready", "#4CAF50"),
            "not_loaded": ("⚪", "Not Loaded", "#9E9E9E"),
            "loading": ("🟡", "Loading...", "#FF9800"),
            "error": ("🔴", "Error", "#F44336"),
            "unknown": ("⚪", "Unknown", "#9E9E9E")
        }
        
        icon, text, color = status_map.get(status, status_map["unknown"])
        label.setText(f"{icon} {text}")
        label.setStyleSheet(f"font-size: 9pt; margin-left: 10px; color: {color}; font-weight: 500;")
    
    def create_status_label(self, status: str = "unknown") -> QLabel:
        """
        Create a status indicator label with colored icon.
        
        Args:
            status: Initial status
            
        Returns:
            QLabel: Configured status label
        """
        label = QLabel()
        label.setStyleSheet("font-size: 9pt; margin-left: 10px;")
        self._update_status_label(label, status)
        return label
    
    def ensure_plugin_jsons_exist(self):
        """
        DEPRECATED: This method is no longer needed.
        Plugin auto-generation is now handled by OCRPluginManager.discover_plugins()
        which creates plugins in dev/plugins/ocr/ for installed packages.
        """
        # Do nothing - plugin auto-generation is handled by the plugin manager
        pass
