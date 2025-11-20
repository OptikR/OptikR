"""
Multi-Region Selector Dialog

Enhanced dialog for selecting multiple capture regions across multiple monitors.
Wraps the existing CaptureRegionSelectorDialog and adds multi-region management.
"""

from PyQt6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QPushButton, QLabel,
    QSplitter, QMessageBox, QInputDialog
)
from PyQt6.QtCore import Qt, pyqtSignal
from PyQt6.QtGui import QFont
from typing import List, Optional
import uuid

try:
    from app.models import CaptureRegion, MultiRegionConfig, Rectangle
    from ui.region_list_widget import RegionListWidget
    from ui.capture_region_selector_pyqt6 import CaptureRegionSelectorDialog
    from translations.translations import tr
except ImportError:
    from models import CaptureRegion, MultiRegionConfig, Rectangle
    from region_list_widget import RegionListWidget
    from capture_region_selector_pyqt6 import CaptureRegionSelectorDialog
    # Fallback if translations not available
    def tr(key, *args):
        return key


class MultiRegionSelectorDialog(QDialog):
    """
    Dialog for managing multiple capture regions across monitors.
    
    Features:
    - Add/edit/delete regions
    - Enable/disable regions
    - Visual preview of all regions
    - Per-region configuration
    """
    
    # Signal emitted when configuration changes
    configurationChanged = pyqtSignal(object)  # MultiRegionConfig
    
    def __init__(self, config: Optional[MultiRegionConfig] = None, parent=None, config_manager=None):
        super().__init__(parent)
        self.config = config or MultiRegionConfig()
        self.current_edit_region_id: Optional[str] = None
        self.config_manager = config_manager
        self.ocr_mappings = {}  # region_id -> ocr_engine
        
        self.setWindowTitle("Multi-Region Capture Configuration")
        self.setModal(False)  # Non-modal - allows interaction with main window
        self.resize(1200, 800)
        
        self._init_ui()
        self._load_regions()
        self._load_ocr_mappings()
    
    def _init_ui(self):
        """Initialize the UI."""
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(15, 15, 15, 15)
        main_layout.setSpacing(15)
        
        # Title
        title_label = QLabel("Multi-Region Capture Configuration")
        title_font = QFont()
        title_font.setPointSize(14)
        title_font.setBold(True)
        title_label.setFont(title_font)
        title_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        main_layout.addWidget(title_label)
        
        # Description
        desc_label = QLabel("Configure multiple capture regions across your monitors. Enable/disable regions as needed.")
        desc_label.setWordWrap(True)
        desc_label.setStyleSheet("color: #B0B0B0; padding: 5px;")
        main_layout.addWidget(desc_label)
        
        # Splitter for region list and preview
        splitter = QSplitter(Qt.Orientation.Horizontal)
        
        # Left side: Region list
        self.region_list = RegionListWidget()
        self.region_list.regionEnabledChanged.connect(self._on_region_enabled_changed)
        self.region_list.regionEditRequested.connect(self._on_edit_region)
        self.region_list.regionDeleteRequested.connect(self._on_delete_region)
        self.region_list.regionRenameRequested.connect(self._on_rename_region)
        self.region_list.regionOcrEngineChanged.connect(self._on_ocr_engine_changed)
        self.region_list.addRegionRequested.connect(self._on_add_region)
        splitter.addWidget(self.region_list)
        
        # Right side: How to Use guide
        how_to_widget = self._create_how_to_guide()
        splitter.addWidget(how_to_widget)
        
        splitter.setStretchFactor(0, 1)
        splitter.setStretchFactor(1, 1)
        
        main_layout.addWidget(splitter, 1)
        
        # Statistics
        self.stats_label = QLabel()
        self.stats_label.setStyleSheet("color: #B0B0B0; font-size: 9pt; padding: 5px;")
        main_layout.addWidget(self.stats_label)
        
        # Buttons
        button_layout = QHBoxLayout()
        button_layout.addStretch()
        
        # Save button
        save_btn = QPushButton("Save Configuration")
        save_btn.clicked.connect(self._on_save_clicked)
        save_btn.setMinimumWidth(120)
        button_layout.addWidget(save_btn)
        
        # Cancel button
        cancel_btn = QPushButton("Cancel")
        cancel_btn.clicked.connect(self.close)
        cancel_btn.setMinimumWidth(120)
        button_layout.addWidget(cancel_btn)
        
        main_layout.addLayout(button_layout)
        
        self._update_stats()
    
    def _create_how_to_guide(self):
        """Create the how-to guide widget."""
        from PyQt6.QtWidgets import QTextEdit
        
        guide_widget = QTextEdit()
        guide_widget.setReadOnly(True)
        guide_widget.setStyleSheet("""
            QTextEdit {
                background-color: #2D2D2D;
                border: 1px solid #4E4E4E;
                border-radius: 5px;
                padding: 15px;
                color: #E0E0E0;
                font-size: 10pt;
            }
        """)
        
        guide_html = """
        <div style="font-family: 'Segoe UI', Arial, sans-serif;">
            <h2 style="color: #4A9EFF; margin-top: 0;">📖 How to Use Multi-Region Capture</h2>
            
            <h3 style="color: #4A9EFF; margin-top: 20px;">🎯 What is Multi-Region?</h3>
            <p style="line-height: 1.6;">
                Multi-region allows you to capture and translate <b>multiple areas</b> on your screen 
                simultaneously. Perfect for games, videos, or applications with text in different locations.
            </p>
            
            <h3 style="color: #4A9EFF; margin-top: 20px;">➕ Adding a Region</h3>
            <ol style="line-height: 1.8;">
                <li>Click <b>"+ Add Region"</b> button</li>
                <li>Select your monitor from the visual layout</li>
                <li>Click <b>"Draw Region"</b> to select the area</li>
                <li>Draw a rectangle around the text you want to translate</li>
                <li>Click <b>"Apply"</b> to save the region</li>
            </ol>
            
            <h3 style="color: #4A9EFF; margin-top: 20px;">✏️ Editing a Region</h3>
            <ul style="line-height: 1.8;">
                <li>Click the <b>"Edit"</b> button next to any region</li>
                <li>Adjust the coordinates or redraw the region</li>
                <li>Click <b>"Apply"</b> to save changes</li>
            </ul>
            
            <h3 style="color: #4A9EFF; margin-top: 20px;">🔄 Enable/Disable Regions</h3>
            <ul style="line-height: 1.8;">
                <li>Use the <b>checkbox</b> next to each region to enable/disable it</li>
                <li>Disabled regions won't be captured (useful for temporary exclusions)</li>
                <li>You can have multiple regions enabled at once</li>
            </ul>
            
            <h3 style="color: #4A9EFF; margin-top: 20px;">🗑️ Deleting a Region</h3>
            <ul style="line-height: 1.8;">
                <li>Click the red <b>"×"</b> button to delete a region</li>
                <li>Confirm the deletion when prompted</li>
            </ul>
            
            <h3 style="color: #4A9EFF; margin-top: 20px;">💡 Tips</h3>
            <ul style="line-height: 1.8;">
                <li><b>Multiple monitors:</b> You can create regions on different monitors</li>
                <li><b>Overlapping regions:</b> Regions can overlap - each will be processed separately</li>
                <li><b>Performance:</b> More regions = more CPU usage. Start with 1-2 regions</li>
                <li><b>Testing:</b> Use the "Region Overlay" button in the toolbar to visualize your regions</li>
            </ul>
            
            <div style="background-color: #3A3A3A; padding: 10px; border-radius: 5px; margin-top: 20px;">
                <p style="margin: 0; color: #4A9EFF;"><b>💾 Don't forget to click "Save Configuration" when done!</b></p>
            </div>
        </div>
        """
        
        guide_widget.setHtml(guide_html)
        return guide_widget
    
    def _load_regions(self):
        """Load regions from config into the list."""
        self.region_list.set_regions(self.config.regions, self.ocr_mappings)
        self._update_stats()
    
    def _load_ocr_mappings(self):
        """Load OCR engine mappings from config."""
        if self.config_manager:
            self.ocr_mappings = self.config_manager.get_setting('plugins.ocr_per_region.region_ocr_mapping', {})
            self.region_list.set_ocr_mappings(self.ocr_mappings)
            print(f"[MULTI_REGION] Loaded OCR mappings: {self.ocr_mappings}")
    
    def _save_ocr_mappings(self):
        """Save OCR engine mappings to config."""
        if self.config_manager:
            self.ocr_mappings = self.region_list.get_ocr_mappings()
            self.config_manager.set_setting('plugins.ocr_per_region.region_ocr_mapping', self.ocr_mappings)
            print(f"[MULTI_REGION] Saved OCR mappings: {self.ocr_mappings}")
    
    def _update_stats(self):
        """Update statistics label."""
        total = len(self.config.regions)
        enabled = len(self.config.get_enabled_regions())
        
        # Count regions per monitor
        monitor_counts = {}
        for region in self.config.regions:
            monitor_counts[region.monitor_id] = monitor_counts.get(region.monitor_id, 0) + 1
        
        monitor_info = ", ".join([f"{tr('monitor')} {mid}: {count}" for mid, count in sorted(monitor_counts.items())])
        
        stats_text = f"{tr('total_regions')}: {total} | {tr('enabled')}: {enabled} | {monitor_info if monitor_info else tr('no_regions')}"
        self.stats_label.setText(stats_text)
    
    def _on_region_enabled_changed(self, region_id: str, enabled: bool):
        """Handle region enabled/disabled."""
        if enabled:
            self.config.enable_region(region_id)
        else:
            self.config.disable_region(region_id)
        
        self._update_stats()
        self.configurationChanged.emit(self.config)
    
    def _on_ocr_engine_changed(self, region_id: str, ocr_engine: str):
        """Handle OCR engine change for a region."""
        self.ocr_mappings[region_id] = ocr_engine
        print(f"[MULTI_REGION] Region '{region_id}' OCR engine set to: {ocr_engine}")
    
    def _on_add_region(self):
        """Handle add region request."""
        # Try to get the last used overlay region from config for pre-population
        initial_overlay_region = None
        if self.config_manager:
            last_overlay = self.config_manager.get_setting('capture.last_overlay_region', None)
            if last_overlay:
                initial_overlay_region = last_overlay
        
        # Open single region selector dialog
        dialog = CaptureRegionSelectorDialog(
            self, 
            config_manager=self.config_manager,
            initial_overlay_region=initial_overlay_region
        )
        
        if dialog.exec() == QDialog.DialogCode.Accepted:
            config = dialog.get_configuration()
            
            # Get region name from user
            name, ok = QInputDialog.getText(
                self,
                tr("region_name"),
                tr("enter_region_name"),
                text=f"{tr('region')} {len(self.config.regions) + 1}"
            )
            
            if not ok or not name:
                name = f"{tr('region')} {len(self.config.regions) + 1}"
            
            # Create new region
            region_id = str(uuid.uuid4())[:8]
            capture_region = config['capture_region']
            
            new_region = CaptureRegion(
                rectangle=Rectangle(
                    x=capture_region['x'],
                    y=capture_region['y'],
                    width=capture_region['width'],
                    height=capture_region['height']
                ),
                monitor_id=config['monitor'],
                region_id=region_id,
                enabled=True,
                name=name
            )
            
            # Save the overlay region to config for future use
            if self.config_manager and config.get('overlay_region'):
                self.config_manager.set_setting('capture.last_overlay_region', config['overlay_region'])
            
            # Add to config
            self.config.add_region(new_region)
            
            # Refresh the entire list from config instead of adding individually
            # This prevents duplicates if the method is somehow called twice
            self.region_list.set_regions(self.config.regions)
            self._update_stats()
            self.configurationChanged.emit(self.config)
    
    def _on_edit_region(self, region_id: str):
        """Handle edit region request."""
        region = self.config.get_region(region_id)
        if not region:
            return
        
        # Prepare initial region values from the existing region
        initial_region = {
            'x': region.rectangle.x,
            'y': region.rectangle.y,
            'width': region.rectangle.width,
            'height': region.rectangle.height
        }
        
        # Try to get the last used overlay region from config
        initial_overlay_region = None
        if self.config_manager:
            # Get last used overlay region from config (if available)
            last_overlay = self.config_manager.get_setting('capture.last_overlay_region', None)
            if last_overlay:
                initial_overlay_region = last_overlay
        
        # Open single region selector dialog with current values pre-populated
        dialog = CaptureRegionSelectorDialog(
            self, 
            config_manager=self.config_manager,
            initial_region=initial_region,
            initial_monitor=region.monitor_id,
            initial_overlay_region=initial_overlay_region
        )
        
        if dialog.exec() == QDialog.DialogCode.Accepted:
            config = dialog.get_configuration()
            
            # Update region
            capture_region = config['capture_region']
            region.rectangle = Rectangle(
                x=capture_region['x'],
                y=capture_region['y'],
                width=capture_region['width'],
                height=capture_region['height']
            )
            region.monitor_id = config['monitor']
            
            # Save the overlay region to config for future edits
            if self.config_manager and config.get('overlay_region'):
                self.config_manager.set_setting('capture.last_overlay_region', config['overlay_region'])
            
            # Update in config
            self.config.add_region(region)  # This updates existing region
            
            # Update list
            self.region_list.update_region(region)
            self._update_stats()
            self.configurationChanged.emit(self.config)
    
    def _on_rename_region(self, region_id: str):
        """Handle rename region request."""
        region = self.config.get_region(region_id)
        if not region:
            return
        
        # Ask for new name
        from PyQt6.QtWidgets import QInputDialog
        
        # Try to use translations, fallback to English
        try:
            title = tr("rename_region")
            prompt = tr("enter_new_region_name")
        except:
            title = "Rename Region"
            prompt = "Enter new region name:"
        
        new_name, ok = QInputDialog.getText(
            self,
            title,
            prompt,
            text=region.name
        )
        
        if ok and new_name.strip():
            # Update region name
            region.name = new_name.strip()
            
            # Update in config
            self.config.add_region(region)  # This updates existing region
            
            # Update list
            self.region_list.update_region(region)
            self.configurationChanged.emit(self.config)
    
    def _on_delete_region(self, region_id: str):
        """Handle delete region request."""
        region = self.config.get_region(region_id)
        if not region:
            return
        
        # Confirm deletion
        reply = QMessageBox.question(
            self,
            tr("delete_region"),
            tr("delete_region_confirm", region.name),
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            QMessageBox.StandardButton.No
        )
        
        if reply == QMessageBox.StandardButton.Yes:
            # Remove from config
            self.config.remove_region(region_id)
            
            # Update list
            self.region_list.remove_region(region_id)
            self._update_stats()
            self.configurationChanged.emit(self.config)
    
    def _on_save_clicked(self):
        """Handle save button click."""
        # Save OCR mappings
        self._save_ocr_mappings()
        # Emit configuration changed signal
        self.configurationChanged.emit(self.config)
        # Close the dialog
        self.close()
    
    def get_configuration(self) -> MultiRegionConfig:
        """Get the current multi-region configuration."""
        return self.config
    
    def set_configuration(self, config: MultiRegionConfig):
        """Set the multi-region configuration."""
        self.config = config
        self._load_regions()


def show_multi_region_selector(config: Optional[MultiRegionConfig] = None, parent=None, config_manager=None) -> Optional[MultiRegionConfig]:
    """
    Show multi-region selector dialog.
    
    Args:
        config: Initial configuration
        parent: Parent widget
        config_manager: Configuration manager for saving/loading presets
        
    Returns:
        MultiRegionConfig if accepted, None if cancelled
    """
    dialog = MultiRegionSelectorDialog(config, parent, config_manager=config_manager)
    
    if dialog.exec() == QDialog.DialogCode.Accepted:
        return dialog.get_configuration()
    
    return None
