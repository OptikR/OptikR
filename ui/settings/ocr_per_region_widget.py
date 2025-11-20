"""
OCR per Region Configuration Widget

Allows users to assign different OCR engines to different capture regions.
"""

from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QGroupBox, QLabel,
    QComboBox, QPushButton, QTableWidget, QTableWidgetItem,
    QHeaderView, QMessageBox
)
from PyQt6.QtCore import Qt, pyqtSignal
from typing import Dict, List, Optional


class OCRPerRegionWidget(QWidget):
    """Widget for configuring OCR engines per region."""
    
    # Signal emitted when configuration changes
    configChanged = pyqtSignal()
    
    def __init__(self, config_manager=None, pipeline=None, parent=None):
        """Initialize the widget."""
        super().__init__(parent)
        
        self.config_manager = config_manager
        self.pipeline = pipeline
        self.region_ocr_mapping = {}
        
        self._init_ui()
        self._load_configuration()
    
    def _init_ui(self):
        """Initialize the UI."""
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        
        # Create group box
        group = QGroupBox("🎯 OCR per Region Configuration")
        group_layout = QVBoxLayout(group)
        
        # Description
        desc = QLabel(
            "Assign different OCR engines to different capture regions.\n"
            "Perfect for multi-region setups with varying text styles."
        )
        desc.setWordWrap(True)
        desc.setStyleSheet("color: #666; font-size: 9pt; margin-bottom: 10px;")
        group_layout.addWidget(desc)
        
        # Default OCR selection
        default_layout = QHBoxLayout()
        default_label = QLabel("Default OCR Engine:")
        default_label.setStyleSheet("font-weight: bold;")
        self.default_ocr_combo = QComboBox()
        self.default_ocr_combo.addItems([
            "easyocr",
            "tesseract",
            "paddleocr",
            "manga_ocr",
            "hybrid_ocr"
        ])
        self.default_ocr_combo.currentTextChanged.connect(self._on_default_changed)
        default_layout.addWidget(default_label)
        default_layout.addWidget(self.default_ocr_combo)
        default_layout.addStretch()
        group_layout.addLayout(default_layout)
        
        # Region mappings table
        table_label = QLabel("Region-Specific OCR Engines:")
        table_label.setStyleSheet("font-weight: bold; margin-top: 10px;")
        group_layout.addWidget(table_label)
        
        self.regions_table = QTableWidget()
        self.regions_table.setColumnCount(3)
        self.regions_table.setHorizontalHeaderLabels(["Region Name", "OCR Engine", "Actions"])
        self.regions_table.horizontalHeader().setSectionResizeMode(0, QHeaderView.ResizeMode.Stretch)
        self.regions_table.horizontalHeader().setSectionResizeMode(1, QHeaderView.ResizeMode.ResizeToContents)
        self.regions_table.horizontalHeader().setSectionResizeMode(2, QHeaderView.ResizeMode.ResizeToContents)
        self.regions_table.setMaximumHeight(200)
        group_layout.addWidget(self.regions_table)
        
        # Buttons
        button_layout = QHBoxLayout()
        
        self.refresh_btn = QPushButton("🔄 Refresh Regions")
        self.refresh_btn.clicked.connect(self._refresh_regions)
        button_layout.addWidget(self.refresh_btn)
        
        self.save_btn = QPushButton("💾 Save Configuration")
        self.save_btn.clicked.connect(self._save_configuration)
        button_layout.addWidget(self.save_btn)
        
        button_layout.addStretch()
        group_layout.addLayout(button_layout)
        
        # Status label
        self.status_label = QLabel("")
        self.status_label.setStyleSheet("color: #4CAF50; font-style: italic;")
        group_layout.addWidget(self.status_label)
        
        layout.addWidget(group)
    
    def _load_configuration(self):
        """Load configuration from config manager."""
        if not self.config_manager:
            return
        
        # Load default OCR
        default_ocr = self.config_manager.get_setting('ocr_per_region.default_ocr', 'easyocr')
        index = self.default_ocr_combo.findText(default_ocr)
        if index >= 0:
            self.default_ocr_combo.setCurrentIndex(index)
        
        # Load region mappings
        self.region_ocr_mapping = self.config_manager.get_setting('ocr_per_region.region_ocr_mapping', {})
        
        # Refresh regions display
        self._refresh_regions()
    
    def _refresh_regions(self):
        """Refresh the regions table with current capture regions."""
        self.regions_table.setRowCount(0)
        
        if not self.config_manager:
            return
        
        # Get multi-region configuration
        multi_region_config = self.config_manager.get_setting('capture.multi_region_config', {})
        regions = multi_region_config.get('regions', [])
        
        if not regions:
            self.status_label.setText("ℹ️ No capture regions configured. Go to Capture tab to create regions.")
            self.status_label.setStyleSheet("color: #FF9800;")
            return
        
        # Populate table
        for region in regions:
            region_id = region.get('region_id', '')
            region_name = region.get('name', region_id)
            
            # Get current OCR engine for this region
            current_ocr = self.region_ocr_mapping.get(region_id, self.default_ocr_combo.currentText())
            
            row = self.regions_table.rowCount()
            self.regions_table.insertRow(row)
            
            # Region name
            name_item = QTableWidgetItem(region_name)
            name_item.setFlags(name_item.flags() & ~Qt.ItemFlag.ItemIsEditable)
            self.regions_table.setItem(row, 0, name_item)
            
            # OCR engine combo
            ocr_combo = QComboBox()
            ocr_combo.addItems([
                "easyocr",
                "tesseract",
                "paddleocr",
                "manga_ocr",
                "hybrid_ocr"
            ])
            index = ocr_combo.findText(current_ocr)
            if index >= 0:
                ocr_combo.setCurrentIndex(index)
            ocr_combo.setProperty('region_id', region_id)
            ocr_combo.currentTextChanged.connect(lambda text, rid=region_id: self._on_region_ocr_changed(rid, text))
            self.regions_table.setCellWidget(row, 1, ocr_combo)
            
            # Reset button
            reset_btn = QPushButton("Reset")
            reset_btn.setProperty('region_id', region_id)
            reset_btn.clicked.connect(lambda checked, rid=region_id: self._reset_region(rid))
            self.regions_table.setCellWidget(row, 2, reset_btn)
        
        self.status_label.setText(f"✓ Loaded {len(regions)} region(s)")
        self.status_label.setStyleSheet("color: #4CAF50;")
    
    def _on_default_changed(self, text: str):
        """Handle default OCR engine change."""
        self.configChanged.emit()
    
    def _on_region_ocr_changed(self, region_id: str, ocr_engine: str):
        """Handle region-specific OCR engine change."""
        self.region_ocr_mapping[region_id] = ocr_engine
        self.configChanged.emit()
        print(f"[OCR_PER_REGION] Region '{region_id}' → {ocr_engine}")
    
    def _reset_region(self, region_id: str):
        """Reset region to use default OCR."""
        if region_id in self.region_ocr_mapping:
            del self.region_ocr_mapping[region_id]
            self.configChanged.emit()
            self._refresh_regions()
            self.status_label.setText(f"✓ Reset region '{region_id}' to default")
    
    def _save_configuration(self):
        """Save configuration to config manager."""
        if not self.config_manager:
            return
        
        try:
            # Save default OCR
            self.config_manager.set_setting('ocr_per_region.default_ocr', self.default_ocr_combo.currentText())
            
            # Save region mappings
            self.config_manager.set_setting('ocr_per_region.region_ocr_mapping', self.region_ocr_mapping)
            
            # Save to file
            self.config_manager.save_config()
            
            self.status_label.setText("✓ Configuration saved successfully!")
            self.status_label.setStyleSheet("color: #4CAF50;")
            
            QMessageBox.information(
                self,
                "Configuration Saved",
                "OCR per Region configuration has been saved successfully!"
            )
            
        except Exception as e:
            self.status_label.setText(f"✗ Error saving: {str(e)}")
            self.status_label.setStyleSheet("color: #F44336;")
            
            QMessageBox.critical(
                self,
                "Save Failed",
                f"Failed to save configuration:\n\n{str(e)}"
            )
    
    def get_configuration(self) -> Dict:
        """Get current configuration."""
        return {
            'default_ocr': self.default_ocr_combo.currentText(),
            'region_ocr_mapping': self.region_ocr_mapping.copy()
        }
