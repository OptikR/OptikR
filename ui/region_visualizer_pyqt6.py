"""
Region Visualizer - PyQt6 Implementation

Shows a visual overlay on screen to display the selected capture/overlay regions.
Helps users see exactly where OCR capture and translation display will occur.
"""

from PyQt6.QtWidgets import QWidget, QLabel, QVBoxLayout, QPushButton
from PyQt6.QtCore import Qt, QTimer, QRect
from PyQt6.QtGui import QPainter, QPen, QColor, QFont
from typing import Optional, Dict


class RegionVisualizerOverlay(QWidget):
    """
    Transparent overlay window that shows region boundaries.
    
    Displays a colored border around the selected region with labels.
    """
    
    def __init__(self, region: Dict[int, int], title: str = "Region", 
                 color: QColor = QColor(0, 255, 0, 200), border_width: int = 6, 
                 show_labels: bool = True, parent=None):
        """
        Initialize region visualizer.
        
        Args:
            region: Dictionary with 'x', 'y', 'width', 'height'
            title: Label to display (e.g., "Capture Region", "Overlay Region")
            color: Border color
            border_width: Width of the border in pixels
            show_labels: Whether to show title and info labels
            parent: Parent widget
        """
        super().__init__(parent)
        
        self.region = region
        self.title = title
        self.color = color
        self.border_width = border_width
        self.show_labels = show_labels
        
        # Make window frameless and transparent (but allow keyboard input for ESC)
        self.setWindowFlags(
            Qt.WindowType.FramelessWindowHint |
            Qt.WindowType.WindowStaysOnTopHint |
            Qt.WindowType.Tool
        )
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
        self.setAttribute(Qt.WidgetAttribute.WA_TransparentForMouseEvents)
        
        # Position window at region location
        self.setGeometry(
            region['x'],
            region['y'],
            region['width'],
            region['height']
        )
        
        # Force window to be visible
        self.setWindowOpacity(1.0)
        self.raise_()
        self.activateWindow()
        
        # Auto-hide after 10 seconds
        self.hide_timer = QTimer(self)
        self.hide_timer.timeout.connect(self.close)
        self.hide_timer.setSingleShot(True)
        self.hide_timer.start(10000)  # 10 seconds
    
    def keyPressEvent(self, event):
        """Handle key press events."""
        from PyQt6.QtCore import Qt
        if event.key() == Qt.Key.Key_Escape:
            print("[INFO] ESC pressed - closing region overlay")
            self.close()
        else:
            super().keyPressEvent(event)
    
    def paintEvent(self, event):
        """Draw the region border and label."""
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        
        # Draw thick border
        half_width = self.border_width // 2
        pen = QPen(self.color, self.border_width, Qt.PenStyle.SolidLine)
        painter.setPen(pen)
        painter.drawRect(half_width, half_width, self.width() - self.border_width, self.height() - self.border_width)
        
        # Draw corner markers (for better visibility)
        corner_size = 40
        pen_thick = QPen(self.color, self.border_width + 2, Qt.PenStyle.SolidLine)
        painter.setPen(pen_thick)
        
        painter.drawLine(half_width, half_width, corner_size, half_width)  # Top-left horizontal
        painter.drawLine(half_width, half_width, half_width, corner_size)  # Top-left vertical
        
        painter.drawLine(self.width() - half_width, half_width, self.width() - corner_size, half_width)  # Top-right
        painter.drawLine(self.width() - half_width, half_width, self.width() - half_width, corner_size)
        
        painter.drawLine(half_width, self.height() - half_width, corner_size, self.height() - half_width)  # Bottom-left
        painter.drawLine(half_width, self.height() - half_width, half_width, self.height() - corner_size)
        
        painter.drawLine(self.width() - half_width, self.height() - half_width, self.width() - corner_size, self.height() - half_width)  # Bottom-right
        painter.drawLine(self.width() - half_width, self.height() - half_width, self.width() - half_width, self.height() - corner_size)
        
        # Only draw labels if enabled
        if self.show_labels:
            # Draw label at top
            font = QFont("Segoe UI", 16, QFont.Weight.Bold)
            painter.setFont(font)
            
            # Background for text
            text_rect = QRect(15, 15, 400, 50)
            painter.fillRect(text_rect, QColor(0, 0, 0, 200))
            
            # Text
            painter.setPen(QPen(QColor(255, 255, 255, 255)))
            painter.drawText(text_rect, Qt.AlignmentFlag.AlignCenter, self.title)
            
            # Draw region info at bottom
            x_val = self.region['x']
            y_val = self.region['y']
            w_val = self.region['width']
            h_val = self.region['height']
            
            info_line1 = f"X: {x_val}  Y: {y_val}"
            info_line2 = f"W: {w_val}  H: {h_val}"
            info_line3 = f"Size: {w_val} × {h_val} px"
            
            info_rect = QRect(15, self.height() - 110, 500, 95)
            painter.fillRect(info_rect, QColor(0, 0, 0, 200))
            
            font_info = QFont("Segoe UI", 12, QFont.Weight.Bold)
            painter.setFont(font_info)
            
            painter.drawText(QRect(25, self.height() - 105, 470, 28), 
                            Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter, 
                            info_line1)
            painter.drawText(QRect(25, self.height() - 77, 470, 28), 
                            Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter, 
                            info_line2)
            painter.drawText(QRect(25, self.height() - 49, 470, 28), 
                            Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter, 
                            info_line3)
            
            # Draw ESC hint at top right
            esc_hint = "Press ESC to close"
            esc_rect = QRect(self.width() - 220, 15, 205, 35)
            painter.fillRect(esc_rect, QColor(0, 0, 0, 200))
            
            font_hint = QFont("Segoe UI", 11)
            painter.setFont(font_hint)
            painter.drawText(esc_rect, Qt.AlignmentFlag.AlignCenter, esc_hint)


class RegionVisualizer:
    """
    Manager for showing region visualizations.
    
    Can show multiple regions simultaneously (e.g., capture + overlay regions).
    """
    
    def __init__(self, config_manager=None):
        """
        Initialize region visualizer.
        
        Args:
            config_manager: Configuration manager to read regions from
        """
        self.config_manager = config_manager
        self.active_overlays = []
    
    def show_capture_region(self):
        """Show the capture region from config."""
        if not self.config_manager:
            return None
        
        # Try to get region from multi-region config first (new system)
        regions_data = self.config_manager.get_setting('capture.regions', [])
        active_ids = self.config_manager.get_setting('capture.active_region_ids', [])
        
        region = None
        
        # If multi-region config exists and has active regions, use the first active region
        if regions_data and active_ids:
            # Find the first active region
            for region_data in regions_data:
                # Check both 'id' and 'region_id' for compatibility
                region_id = region_data.get('region_id') or region_data.get('id')
                if region_id in active_ids and region_data.get('enabled', True):
                    region = {
                        'x': region_data.get('x', 0),
                        'y': region_data.get('y', 0),
                        'width': region_data.get('width', 800),
                        'height': region_data.get('height', 600)
                    }
                    print(f"[INFO] Using multi-region config: {region}")
                    break
        
        # Fallback to old single-region config if no multi-region found
        if not region:
            region = {
                'x': self.config_manager.get_setting('capture.region_x', 0),
                'y': self.config_manager.get_setting('capture.region_y', 0),
                'width': self.config_manager.get_setting('capture.region_width', 800),
                'height': self.config_manager.get_setting('capture.region_height', 600)
            }
            print(f"[INFO] Using legacy single-region config: {region}")
        
        # Validate region
        if region['width'] <= 0 or region['height'] <= 0:
            print(f"[WARNING] Invalid capture region: {region}")
            return None
        
        # Create and show overlay
        print(f"[DEBUG] Creating capture region overlay: {region}")
        overlay = RegionVisualizerOverlay(
            region=region,
            title="📷 OCR Capture Region",
            color=QColor(255, 0, 0, 200)  # Red
        )
        print(f"[DEBUG] Overlay created, showing...")
        overlay.show()
        print(f"[DEBUG] Overlay.isVisible() = {overlay.isVisible()}")
        print(f"[DEBUG] Overlay geometry: {overlay.geometry()}")
        self.active_overlays.append(overlay)
        
        print(f"[INFO] Showing capture region: {region}")
        return overlay
    
    def show_overlay_region(self):
        """Show the translation overlay region from config."""
        if not self.config_manager:
            return None
        
        # Try to get region from multi-region config first (new system)
        # For overlay, we use the same region as capture (they should match)
        regions_data = self.config_manager.get_setting('capture.regions', [])
        active_ids = self.config_manager.get_setting('capture.active_region_ids', [])
        
        region = None
        
        # If multi-region config exists and has active regions, use the first active region
        if regions_data and active_ids:
            # Find the first active region
            for region_data in regions_data:
                # Check both 'id' and 'region_id' for compatibility
                region_id = region_data.get('region_id') or region_data.get('id')
                if region_id in active_ids and region_data.get('enabled', True):
                    region = {
                        'x': region_data.get('x', 0),
                        'y': region_data.get('y', 0),
                        'width': region_data.get('width', 800),
                        'height': region_data.get('height', 600)
                    }
                    print(f"[INFO] Using multi-region config for overlay: {region}")
                    break
        
        # Fallback to old overlay.region config if no multi-region found
        if not region:
            overlay_region = self.config_manager.get_setting('overlay.region', None)
            
            if not overlay_region:
                # If no overlay region set, show message
                from PyQt6.QtWidgets import QMessageBox
                QMessageBox.information(
                    None,
                    "No Overlay Region Set",
                    "No overlay region has been configured yet.\n\n"
                    "Use 'Select Capture Region' to set up the overlay region."
                )
                return None
            
            region = {
                'x': overlay_region.get('x', 0),
                'y': overlay_region.get('y', 0),
                'width': overlay_region.get('width', 800),
                'height': overlay_region.get('height', 600)
            }
            print(f"[INFO] Using legacy overlay.region config: {region}")
        
        # Validate region
        if region['width'] <= 0 or region['height'] <= 0:
            print(f"[WARNING] Invalid overlay region: {region}")
            return None
        
        # Create and show overlay
        print(f"[DEBUG] Creating translation overlay: {region}")
        overlay = RegionVisualizerOverlay(
            region=region,
            title="💬 Translation Display Region",
            color=QColor(0, 120, 255, 200)  # Blue
        )
        print(f"[DEBUG] Overlay created, showing...")
        overlay.show()
        print(f"[DEBUG] Overlay.isVisible() = {overlay.isVisible()}")
        print(f"[DEBUG] Overlay geometry: {overlay.geometry()}")
        self.active_overlays.append(overlay)
        
        print(f"[INFO] Showing overlay region: {region}")
        return overlay
    
    def show_all_regions(self):
        """Show ALL enabled regions in green."""
        if not self.config_manager:
            return []
        
        regions_data = self.config_manager.get_setting('capture.regions', [])
        active_ids = self.config_manager.get_setting('capture.active_region_ids', [])
        
        if not regions_data or not active_ids:
            from PyQt6.QtWidgets import QMessageBox
            QMessageBox.warning(
                None,
                "No Regions Configured",
                "No regions have been configured yet.\n\n"
                "Use 'Select Capture Region' to set up regions."
            )
            return []
        
        overlays = []
        
        for region_data in regions_data:
            region_id = region_data.get('region_id')
            if region_id in active_ids and region_data.get('enabled', True):
                region = {
                    'x': region_data.get('x', 0),
                    'y': region_data.get('y', 0),
                    'width': region_data.get('width', 800),
                    'height': region_data.get('height', 600)
                }
                
                name = region_data.get('name', f'Region {region_id}')
                monitor_id = region_data.get('monitor_id', 0)
                
                # Create overlay in GREEN
                overlay = RegionVisualizerOverlay(
                    region=region,
                    title=f"🟢 {name} (Monitor {monitor_id})",
                    color=QColor(0, 255, 0, 200)  # GREEN
                )
                overlay.show()
                overlays.append(overlay)
                self.active_overlays.append(overlay)
                
                print(f"[INFO] Showing region '{name}' (ID: {region_id}) in green")
        
        # Install global event filter for ESC key
        if overlays:
            self._install_esc_handler()
        
        return overlays
    
    def show_both_regions(self):
        """
        Show all three region types for each configured region:
        - RED: OCR capture region
        - BLUE: Translation/overlay region
        - GREEN: Configured region boundary
        
        Returns:
            tuple: (capture_overlays, translation_overlays) - lists of overlay objects
        """
        if not self.config_manager:
            return [], []
        
        # Get capture region (primary or from multi-region config)
        capture_region = self.config_manager.get_setting('capture.region')
        overlay_region = self.config_manager.get_setting('overlay.region')
        
        # Get multi-region data
        regions_data = self.config_manager.get_setting('capture.regions', [])
        active_ids = self.config_manager.get_setting('capture.active_region_ids', [])
        
        capture_overlays = []
        translation_overlays = []
        
        # If we have multi-region setup, show all active regions
        if regions_data and active_ids:
            for region_data in regions_data:
                region_id = region_data.get('region_id')
                if region_id in active_ids and region_data.get('enabled', True):
                    # Get capture and overlay regions for this region
                    capture_rect = region_data.get('capture_region', {})
                    overlay_rect = region_data.get('overlay_region', {})
                    
                    name = region_data.get('name', f'Region {region_id}')
                    monitor_id = region_data.get('monitor_id', 0)
                    
                    # Get the main region coordinates
                    region_x = region_data.get('x', 0)
                    region_y = region_data.get('y', 0)
                    region_width = region_data.get('width', 800)
                    region_height = region_data.get('height', 600)
                    
                    # GREEN overlay for region boundary (outermost, no inset)
                    region_boundary = {
                        'x': region_x,
                        'y': region_y,
                        'width': region_width,
                        'height': region_height
                    }
                    boundary_overlay = RegionVisualizerOverlay(
                        region=region_boundary,
                        title=f"🟢 Region: {name} (Monitor {monitor_id})",
                        color=QColor(0, 255, 0, 200),  # GREEN
                        border_width=6,
                        show_labels=True  # Only GREEN shows labels
                    )
                    boundary_overlay.show()
                    self.active_overlays.append(boundary_overlay)
                    
                    # RED overlay for OCR capture (inset by 12px to avoid overlap)
                    # Use the same region coordinates (OCR captures from this region)
                    capture_rect_inset = {
                        'x': region_x + 12,
                        'y': region_y + 12,
                        'width': region_width - 24,
                        'height': region_height - 24
                    }
                    capture_overlay = RegionVisualizerOverlay(
                        region=capture_rect_inset,
                        title=f"🔴 OCR Capture: {name} (Monitor {monitor_id})",
                        color=QColor(255, 0, 0, 200),  # RED
                        border_width=6,
                        show_labels=False  # No labels for RED
                    )
                    capture_overlay.show()
                    capture_overlays.append(capture_overlay)
                    self.active_overlays.append(capture_overlay)
                    
                    # BLUE overlay for translation/overlay (inset by 24px to avoid overlap with both)
                    # Use the same region coordinates (overlay appears in this region)
                    overlay_rect_inset = {
                        'x': region_x + 24,
                        'y': region_y + 24,
                        'width': region_width - 48,
                        'height': region_height - 48
                    }
                    translation_overlay = RegionVisualizerOverlay(
                        region=overlay_rect_inset,
                        title=f"🔵 Translation Overlay: {name} (Monitor {monitor_id})",
                        color=QColor(0, 0, 255, 200),  # BLUE
                        border_width=6,
                        show_labels=False  # No labels for BLUE
                    )
                    translation_overlay.show()
                    translation_overlays.append(translation_overlay)
                    self.active_overlays.append(translation_overlay)
                    
                    print(f"[INFO] Showing 3 overlays for '{name}' (ID: {region_id}): RED (OCR), BLUE (Translation), GREEN (Boundary)")
        
        # Fallback: Show single region if no multi-region setup
        elif capture_region:
            # GREEN overlay for overall region (outermost)
            boundary_overlay = RegionVisualizerOverlay(
                region=capture_region,
                title="🟢 Configured Region",
                color=QColor(0, 255, 0, 200),  # GREEN
                border_width=6,
                show_labels=True  # Only GREEN shows labels
            )
            boundary_overlay.show()
            self.active_overlays.append(boundary_overlay)
            
            # RED overlay for OCR capture (inset by 12px)
            capture_region_inset = {
                'x': capture_region.get('x', 0) + 12,
                'y': capture_region.get('y', 0) + 12,
                'width': capture_region.get('width', 800) - 24,
                'height': capture_region.get('height', 600) - 24
            }
            capture_overlay = RegionVisualizerOverlay(
                region=capture_region_inset,
                title="🔴 OCR Capture Region",
                color=QColor(255, 0, 0, 200),  # RED
                border_width=6,
                show_labels=False  # No labels for RED
            )
            capture_overlay.show()
            capture_overlays.append(capture_overlay)
            self.active_overlays.append(capture_overlay)
            
            # BLUE overlay for translation/overlay (inset by 24px)
            if overlay_region:
                overlay_region_inset = {
                    'x': overlay_region.get('x', 0) + 24,
                    'y': overlay_region.get('y', 0) + 24,
                    'width': overlay_region.get('width', 800) - 48,
                    'height': overlay_region.get('height', 600) - 48
                }
                translation_overlay = RegionVisualizerOverlay(
                    region=overlay_region_inset,
                    title="🔵 Translation Overlay Region",
                    color=QColor(0, 0, 255, 200),  # BLUE
                    border_width=6,
                    show_labels=False  # No labels for BLUE
                )
                translation_overlay.show()
                translation_overlays.append(translation_overlay)
                self.active_overlays.append(translation_overlay)
            
            print("[INFO] Showing single region: GREEN (Boundary), RED (OCR), BLUE (Translation)")
        else:
            from PyQt6.QtWidgets import QMessageBox
            QMessageBox.warning(
                None,
                "No Regions Configured",
                "No regions have been configured yet.\n\n"
                "Use 'Select Capture Region' to set up regions."
            )
            return [], []
        
        # Install global event filter for ESC key
        if capture_overlays or translation_overlays:
            self._install_esc_handler()
        
        return capture_overlays, translation_overlays
    
    def _install_esc_handler(self):
        """Install global ESC key handler."""
        from PyQt6.QtWidgets import QApplication
        from PyQt6.QtCore import QObject, QEvent, Qt
        
        class EscapeHandler(QObject):
            def __init__(self, visualizer):
                super().__init__()
                self.visualizer = visualizer
            
            def eventFilter(self, obj, event):
                if event.type() == QEvent.Type.KeyPress:
                    if event.key() == Qt.Key.Key_Escape:
                        print("[INFO] ESC pressed - closing all region overlays")
                        self.visualizer.hide_all()
                        # Remove this event filter
                        QApplication.instance().removeEventFilter(self)
                        return True
                return False
        
        self.esc_handler = EscapeHandler(self)
        QApplication.instance().installEventFilter(self.esc_handler)
    
    def hide_all(self):
        """Hide all active region overlays."""
        for overlay in self.active_overlays:
            overlay.close()
        self.active_overlays.clear()
        
        # Remove ESC handler if it exists
        if hasattr(self, 'esc_handler'):
            from PyQt6.QtWidgets import QApplication
            QApplication.instance().removeEventFilter(self.esc_handler)
            delattr(self, 'esc_handler')
