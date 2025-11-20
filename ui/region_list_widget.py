"""
Region List Widget

Widget for managing multiple capture regions.
Displays list of regions with enable/disable, edit, and delete controls.
"""

from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QListWidget, QListWidgetItem,
    QPushButton, QLabel, QCheckBox, QFrame, QComboBox
)
from PyQt6.QtCore import Qt, pyqtSignal
from PyQt6.QtGui import QFont, QColor
from typing import List, Optional, Dict

try:
    from app.models import CaptureRegion
except ImportError:
    from models import CaptureRegion


class RegionListItem(QWidget):
    """Custom widget for a single region in the list."""
    
    # Signals
    enabledChanged = pyqtSignal(str, bool)  # region_id, enabled
    editClicked = pyqtSignal(str)  # region_id
    deleteClicked = pyqtSignal(str)  # region_id
    renameClicked = pyqtSignal(str)  # region_id
    ocrEngineChanged = pyqtSignal(str, str)  # region_id, ocr_engine
    
    def __init__(self, region: CaptureRegion, ocr_engine: str = "default", parent=None):
        super().__init__(parent)
        self.region = region
        self.ocr_engine = ocr_engine
        self._init_ui()
    
    def _init_ui(self):
        """Initialize the UI."""
        layout = QHBoxLayout(self)
        layout.setContentsMargins(5, 5, 5, 5)
        layout.setSpacing(10)
        
        # Enable checkbox
        self.enabled_check = QCheckBox()
        self.enabled_check.setChecked(self.region.enabled)
        self.enabled_check.stateChanged.connect(self._on_enabled_changed)
        layout.addWidget(self.enabled_check)
        
        # Region info
        info_layout = QVBoxLayout()
        info_layout.setSpacing(2)
        
        # Name row with rename button
        name_row = QHBoxLayout()
        name_row.setSpacing(5)
        
        self.name_label = QLabel(self.region.name)
        name_font = QFont()
        name_font.setPointSize(10)
        name_font.setBold(True)
        self.name_label.setFont(name_font)
        name_row.addWidget(self.name_label)
        
        # Rename button (pencil icon)
        rename_btn = QPushButton("✏️")
        rename_btn.setFixedSize(25, 25)
        rename_btn.setToolTip("Rename region")
        rename_btn.setStyleSheet("""
            QPushButton {
                background-color: transparent;
                border: none;
                font-size: 12pt;
            }
            QPushButton:hover {
                background-color: #4A4A4A;
                border-radius: 3px;
            }
        """)
        rename_btn.clicked.connect(lambda: self.renameClicked.emit(self.region.region_id))
        name_row.addWidget(rename_btn)
        name_row.addStretch()
        
        info_layout.addLayout(name_row)
        
        # Details
        details = f"Monitor {self.region.monitor_id} | {self.region.rectangle.width}×{self.region.rectangle.height} | ({self.region.rectangle.x}, {self.region.rectangle.y})"
        details_label = QLabel(details)
        details_label.setStyleSheet("color: #B0B0B0; font-size: 9pt;")
        info_layout.addWidget(details_label)
        
        layout.addLayout(info_layout, 1)
        
        # OCR Engine selector
        ocr_layout = QVBoxLayout()
        ocr_layout.setSpacing(2)
        
        ocr_label = QLabel("OCR Engine:")
        ocr_label.setStyleSheet("color: #B0B0B0; font-size: 8pt;")
        ocr_layout.addWidget(ocr_label)
        
        self.ocr_combo = QComboBox()
        self.ocr_combo.addItems([
            "default",
            "easyocr",
            "tesseract",
            "paddleocr",
            "manga_ocr",
            "hybrid_ocr"
        ])
        self.ocr_combo.setCurrentText(self.ocr_engine)
        self.ocr_combo.currentTextChanged.connect(self._on_ocr_engine_changed)
        self.ocr_combo.setFixedWidth(120)
        self.ocr_combo.setStyleSheet("""
            QComboBox {
                background-color: #3A3A3A;
                border: 1px solid #4E4E4E;
                border-radius: 3px;
                padding: 3px;
                color: #E0E0E0;
            }
            QComboBox::drop-down {
                border: none;
            }
            QComboBox::down-arrow {
                image: none;
                border-left: 4px solid transparent;
                border-right: 4px solid transparent;
                border-top: 6px solid #E0E0E0;
                margin-right: 5px;
            }
        """)
        ocr_layout.addWidget(self.ocr_combo)
        
        layout.addLayout(ocr_layout)
        
        # Edit button
        edit_btn = QPushButton("Edit")
        edit_btn.setFixedWidth(60)
        edit_btn.clicked.connect(lambda: self.editClicked.emit(self.region.region_id))
        layout.addWidget(edit_btn)
        
        # Delete button
        delete_btn = QPushButton("×")
        delete_btn.setFixedWidth(30)
        delete_btn.setStyleSheet("QPushButton { color: #F44336; font-size: 16pt; font-weight: bold; }")
        delete_btn.clicked.connect(lambda: self.deleteClicked.emit(self.region.region_id))
        layout.addWidget(delete_btn)
        
        # Style based on enabled state
        self._update_style()
    
    def _on_enabled_changed(self, state):
        """Handle enabled checkbox change."""
        enabled = (state == Qt.CheckState.Checked.value)
        self.region.enabled = enabled
        self.enabledChanged.emit(self.region.region_id, enabled)
        self._update_style()
    
    def _on_ocr_engine_changed(self, engine: str):
        """Handle OCR engine selection change."""
        self.ocr_engine = engine
        self.ocrEngineChanged.emit(self.region.region_id, engine)
        print(f"[REGION_LIST] Region '{self.region.name}' OCR engine changed to: {engine}")
    
    def _update_style(self):
        """Update widget style based on enabled state."""
        if self.region.enabled:
            self.setStyleSheet("QWidget { background-color: #3A3A3A; border-radius: 5px; }")
        else:
            self.setStyleSheet("QWidget { background-color: #2A2A2A; border-radius: 5px; opacity: 0.6; }")
    
    def update_region(self, region: CaptureRegion):
        """Update the displayed region."""
        self.region = region
        self.name_label.setText(region.name)
        self.enabled_check.setChecked(region.enabled)
        self._update_style()


class RegionListWidget(QWidget):
    """Widget for managing a list of capture regions."""
    
    # Signals
    regionEnabledChanged = pyqtSignal(str, bool)  # region_id, enabled
    regionEditRequested = pyqtSignal(str)  # region_id
    regionDeleteRequested = pyqtSignal(str)  # region_id
    regionRenameRequested = pyqtSignal(str)  # region_id
    regionOcrEngineChanged = pyqtSignal(str, str)  # region_id, ocr_engine
    addRegionRequested = pyqtSignal()
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.regions: List[CaptureRegion] = []
        self.ocr_mappings: Dict[str, str] = {}  # region_id -> ocr_engine
        self._init_ui()
    
    def _init_ui(self):
        """Initialize the UI."""
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(10)
        
        # Header
        header_layout = QHBoxLayout()
        
        title_label = QLabel("Capture Regions")
        title_font = QFont()
        title_font.setPointSize(11)
        title_font.setBold(True)
        title_label.setFont(title_font)
        header_layout.addWidget(title_label)
        
        header_layout.addStretch()
        
        # Add region button
        add_btn = QPushButton("+ Add Region")
        add_btn.clicked.connect(self.addRegionRequested.emit)
        header_layout.addWidget(add_btn)
        
        layout.addLayout(header_layout)
        
        # Region list
        self.list_widget = QListWidget()
        self.list_widget.setSpacing(5)
        self.list_widget.setStyleSheet("""
            QListWidget {
                border: 1px solid #4E4E4E;
                border-radius: 5px;
                background-color: #2D2D2D;
            }
            QListWidget::item {
                border: none;
                padding: 0px;
            }
            QListWidget::item:selected {
                background-color: transparent;
            }
        """)
        layout.addWidget(self.list_widget)
        
        # Info label
        self.info_label = QLabel("No regions configured. Click 'Add Region' to create one.")
        self.info_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.info_label.setStyleSheet("color: #B0B0B0; padding: 20px;")
        layout.addWidget(self.info_label)
        
        self._update_info_label()
    
    def set_regions(self, regions: List[CaptureRegion], ocr_mappings: Dict[str, str] = None):
        """Set the list of regions to display."""
        self.regions = regions
        if ocr_mappings:
            self.ocr_mappings = ocr_mappings
        self._refresh_list()
    
    def set_ocr_mappings(self, ocr_mappings: Dict[str, str]):
        """Set OCR engine mappings for regions."""
        self.ocr_mappings = ocr_mappings
        self._refresh_list()
    
    def get_ocr_mappings(self) -> Dict[str, str]:
        """Get current OCR engine mappings."""
        return self.ocr_mappings.copy()
    
    def add_region(self, region: CaptureRegion):
        """Add a region to the list."""
        self.regions.append(region)
        self._refresh_list()
    
    def remove_region(self, region_id: str):
        """Remove a region from the list."""
        self.regions = [r for r in self.regions if r.region_id != region_id]
        self._refresh_list()
    
    def update_region(self, region: CaptureRegion):
        """Update a region in the list."""
        for i, r in enumerate(self.regions):
            if r.region_id == region.region_id:
                self.regions[i] = region
                break
        self._refresh_list()
    
    def get_region(self, region_id: str) -> Optional[CaptureRegion]:
        """Get a region by ID."""
        for region in self.regions:
            if region.region_id == region_id:
                return region
        return None
    
    def _refresh_list(self):
        """Refresh the list widget."""
        self.list_widget.clear()
        
        for region in self.regions:
            # Create list item
            item = QListWidgetItem(self.list_widget)
            
            # Get OCR engine for this region
            ocr_engine = self.ocr_mappings.get(region.region_id, "default")
            
            # Create custom widget
            widget = RegionListItem(region, ocr_engine)
            widget.enabledChanged.connect(self.regionEnabledChanged.emit)
            widget.editClicked.connect(self.regionEditRequested.emit)
            widget.deleteClicked.connect(self.regionDeleteRequested.emit)
            widget.renameClicked.connect(self.regionRenameRequested.emit)
            widget.ocrEngineChanged.connect(self._on_ocr_engine_changed)
            
            # Set item size
            item.setSizeHint(widget.sizeHint())
            
            # Add to list
            self.list_widget.addItem(item)
            self.list_widget.setItemWidget(item, widget)
        
        self._update_info_label()
    
    def _on_ocr_engine_changed(self, region_id: str, ocr_engine: str):
        """Handle OCR engine change for a region."""
        self.ocr_mappings[region_id] = ocr_engine
        self.regionOcrEngineChanged.emit(region_id, ocr_engine)
    
    def _update_info_label(self):
        """Update the info label visibility."""
        if self.regions:
            self.info_label.hide()
            self.list_widget.show()
        else:
            self.info_label.show()
            self.list_widget.hide()
    
    def get_enabled_regions(self) -> List[CaptureRegion]:
        """Get all enabled regions."""
        return [r for r in self.regions if r.enabled]
    
    def get_regions_for_monitor(self, monitor_id: int) -> List[CaptureRegion]:
        """Get all regions for a specific monitor."""
        return [r for r in self.regions if r.monitor_id == monitor_id]
