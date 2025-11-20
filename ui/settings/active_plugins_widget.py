"""
Active Plugins Widget - Real-time Plugin Status with Controls

Shows currently active plugins with enable/disable checkboxes and master switch.
"""

from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QGroupBox, QLabel, QCheckBox,
    QPushButton, QScrollArea, QFrame
)
from PyQt6.QtCore import Qt, pyqtSignal, QTimer
from PyQt6.QtGui import QFont
from typing import Dict, List, Optional


class ActivePluginsWidget(QWidget):
    """Widget showing active plugins with real-time status."""
    
    # Signals
    pluginToggled = pyqtSignal(str, bool)  # plugin_name, enabled
    masterSwitchToggled = pyqtSignal(bool)  # enabled
    
    def __init__(self, config_manager=None, plugin_manager=None, parent=None):
        """Initialize active plugins widget."""
        super().__init__(parent)
        
        self.config_manager = config_manager
        self.plugin_manager = plugin_manager
        self.plugin_checkboxes: Dict[str, QCheckBox] = {}
        
        # Update timer
        self.update_timer = QTimer()
        self.update_timer.timeout.connect(self._update_plugin_status)
        self.update_timer.setInterval(2000)  # Update every 2 seconds
        
        self._init_ui()
        
        # Initial update
        QTimer.singleShot(100, self._update_plugin_status)
        
        # Start updates
        self.update_timer.start()
    
    def _init_ui(self):
        """Initialize the UI."""
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(10)
        
        # Header
        header_layout = QHBoxLayout()
        
        title_label = QLabel("🔌 Active Plugins")
        title_font = QFont()
        title_font.setPointSize(11)
        title_font.setBold(True)
        title_label.setFont(title_font)
        header_layout.addWidget(title_label)
        
        header_layout.addStretch()
        
        # Refresh button
        refresh_btn = QPushButton("🔄")
        refresh_btn.setFixedSize(30, 30)
        refresh_btn.setToolTip("Refresh plugin status")
        refresh_btn.clicked.connect(self._update_plugin_status)
        header_layout.addWidget(refresh_btn)
        
        layout.addLayout(header_layout)
        
        # Master switch
        master_frame = QFrame()
        master_frame.setFrameShape(QFrame.Shape.StyledPanel)
        master_frame.setStyleSheet("""
            QFrame {
                background-color: #2D2D2D;
                border: 2px solid #4A9EFF;
                border-radius: 5px;
                padding: 10px;
            }
        """)
        master_layout = QHBoxLayout(master_frame)
        
        self.master_switch = QCheckBox("Enable All Optional Plugins")
        self.master_switch.setStyleSheet("font-weight: bold; font-size: 10pt;")
        self.master_switch.setToolTip(
            "Master switch for optional plugins.\n"
            "Essential plugins (marked with ⭐) are always active."
        )
        self.master_switch.stateChanged.connect(self._on_master_switch_changed)
        master_layout.addWidget(self.master_switch)
        
        master_layout.addStretch()
        
        self.master_status_label = QLabel("Loading...")
        self.master_status_label.setStyleSheet("color: #B0B0B0; font-size: 9pt;")
        master_layout.addWidget(self.master_status_label)
        
        layout.addWidget(master_frame)
        
        # Plugin count summary
        self.summary_label = QLabel("Loading plugin information...")
        self.summary_label.setStyleSheet("color: #B0B0B0; font-size: 9pt; padding: 5px;")
        layout.addWidget(self.summary_label)
        
        # Scroll area for plugins
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QScrollArea.Shape.NoFrame)
        scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        
        # Container for plugin list
        self.plugins_container = QWidget()
        self.plugins_layout = QVBoxLayout(self.plugins_container)
        self.plugins_layout.setContentsMargins(0, 0, 0, 0)
        self.plugins_layout.setSpacing(5)
        
        scroll.setWidget(self.plugins_container)
        layout.addWidget(scroll, 1)
        
        # Info label
        info_label = QLabel(
            "💡 Tip: Essential plugins (⭐) bypass the master switch and work independently."
        )
        info_label.setWordWrap(True)
        info_label.setStyleSheet(
            "background-color: #FFF3CD; color: #856404; padding: 8px; "
            "border: 1px solid #FFE69C; border-radius: 3px; font-size: 8pt;"
        )
        layout.addWidget(info_label)
    
    def _update_plugin_status(self):
        """Update plugin status from config and plugin manager."""
        if not self.config_manager:
            return
        
        # Get master switch status
        master_enabled = self.config_manager.get_setting('plugins.enabled', True)
        self.master_switch.blockSignals(True)
        self.master_switch.setChecked(master_enabled)
        self.master_switch.blockSignals(False)
        
        # Update master status label
        if master_enabled:
            self.master_status_label.setText("✅ Optional plugins enabled")
            self.master_status_label.setStyleSheet("color: #4CAF50; font-size: 9pt; font-weight: bold;")
        else:
            self.master_status_label.setText("⚪ Optional plugins disabled")
            self.master_status_label.setStyleSheet("color: #F44336; font-size: 9pt; font-weight: bold;")
        
        # Get all plugins
        plugins = self._get_all_plugins()
        
        # Update summary
        total = len(plugins)
        enabled = sum(1 for p in plugins if p['enabled'])
        essential = sum(1 for p in plugins if p['essential'])
        
        self.summary_label.setText(
            f"Total: {total} plugins | Enabled: {enabled} | Essential: {essential} | Optional: {total - essential}"
        )
        
        # Clear existing plugin widgets
        for i in reversed(range(self.plugins_layout.count())):
            widget = self.plugins_layout.itemAt(i).widget()
            if widget:
                widget.deleteLater()
        
        self.plugin_checkboxes.clear()
        
        # Group plugins by category
        categories = {
            'Essential': [p for p in plugins if p['essential']],
            'Capture': [p for p in plugins if p['type'] == 'capture' and not p['essential']],
            'OCR': [p for p in plugins if p['type'] == 'ocr' and not p['essential']],
            'Optimizer': [p for p in plugins if p['type'] == 'optimizer' and not p['essential']],
            'Text Processor': [p for p in plugins if p['type'] == 'text_processor' and not p['essential']],
            'Translation': [p for p in plugins if p['type'] == 'translation' and not p['essential']]
        }
        
        # Create sections for each category
        for category, category_plugins in categories.items():
            if not category_plugins:
                continue
            
            # Category header
            category_label = QLabel(f"▼ {category} ({len(category_plugins)})")
            category_label.setStyleSheet(
                "font-weight: bold; font-size: 10pt; color: #4A9EFF; "
                "padding: 5px; margin-top: 5px;"
            )
            self.plugins_layout.addWidget(category_label)
            
            # Add plugins
            for plugin in category_plugins:
                plugin_widget = self._create_plugin_widget(plugin)
                self.plugins_layout.addWidget(plugin_widget)
        
        self.plugins_layout.addStretch()
    
    def _get_all_plugins(self) -> List[Dict]:
        """Get all plugins with their status."""
        plugins = []
        
        # Essential plugins (hardcoded for now)
        essential_plugins = [
            {'name': 'frame_skip', 'display_name': 'Frame Skip', 'type': 'optimizer', 'essential': True},
            {'name': 'learning_dictionary', 'display_name': 'Learning Dictionary', 'type': 'optimizer', 'essential': True},
            {'name': 'priority_queue', 'display_name': 'Priority Queue', 'type': 'optimizer', 'essential': True},
            {'name': 'text_block_merger', 'display_name': 'Text Block Merger', 'type': 'optimizer', 'essential': True},
            {'name': 'text_validator', 'display_name': 'Text Validator', 'type': 'optimizer', 'essential': True},
            {'name': 'translation_cache', 'display_name': 'Translation Cache', 'type': 'optimizer', 'essential': True},
            {'name': 'spell_corrector', 'display_name': 'Spell Corrector', 'type': 'text_processor', 'essential': True},
        ]
        
        # Optional plugins
        optional_plugins = [
            # Optimizers
            {'name': 'batch_processing', 'display_name': 'Batch Processing', 'type': 'optimizer', 'essential': False},
            {'name': 'motion_tracker', 'display_name': 'Motion Tracker', 'type': 'optimizer', 'essential': False},
            {'name': 'ocr_per_region', 'display_name': 'OCR per Region', 'type': 'optimizer', 'essential': False},
            {'name': 'parallel_capture', 'display_name': 'Parallel Capture', 'type': 'optimizer', 'essential': False},
            {'name': 'parallel_ocr', 'display_name': 'Parallel OCR', 'type': 'optimizer', 'essential': False},
            {'name': 'parallel_translation', 'display_name': 'Parallel Translation', 'type': 'optimizer', 'essential': False},
            {'name': 'translation_chain', 'display_name': 'Translation Chain', 'type': 'optimizer', 'essential': False},
            {'name': 'work_stealing', 'display_name': 'Work Stealing', 'type': 'optimizer', 'essential': False},
            {'name': 'async_pipeline', 'display_name': 'Async Pipeline', 'type': 'optimizer', 'essential': False},
            # Text Processors
            {'name': 'regex', 'display_name': 'Regex Processor', 'type': 'text_processor', 'essential': False},
            # Capture
            {'name': 'dxcam_capture_gpu', 'display_name': 'DirectX Capture (GPU)', 'type': 'capture', 'essential': False},
            {'name': 'screenshot_capture_cpu', 'display_name': 'Screenshot Capture (CPU)', 'type': 'capture', 'essential': False},
            # OCR
            {'name': 'easyocr', 'display_name': 'EasyOCR', 'type': 'ocr', 'essential': False},
            {'name': 'tesseract', 'display_name': 'Tesseract', 'type': 'ocr', 'essential': False},
            {'name': 'paddleocr', 'display_name': 'PaddleOCR', 'type': 'ocr', 'essential': False},
            {'name': 'manga_ocr', 'display_name': 'Manga OCR', 'type': 'ocr', 'essential': False},
            {'name': 'hybrid_ocr', 'display_name': 'Hybrid OCR', 'type': 'ocr', 'essential': False},
            # Translation
            {'name': 'marianmt_gpu', 'display_name': 'MarianMT (GPU)', 'type': 'translation', 'essential': False},
            {'name': 'libretranslate', 'display_name': 'LibreTranslate', 'type': 'translation', 'essential': False},
        ]
        
        all_plugins = essential_plugins + optional_plugins
        
        # Get enabled status from config
        for plugin in all_plugins:
            plugin_key = f"plugins.{plugin['name']}.enabled"
            plugin['enabled'] = self.config_manager.get_setting(plugin_key, plugin['essential'])
        
        return all_plugins
    
    def _create_plugin_widget(self, plugin: Dict) -> QWidget:
        """Create a widget for a single plugin."""
        widget = QFrame()
        widget.setFrameShape(QFrame.Shape.StyledPanel)
        widget.setStyleSheet("""
            QFrame {
                background-color: #3A3A3A;
                border: 1px solid #4E4E4E;
                border-radius: 3px;
                padding: 5px;
            }
            QFrame:hover {
                background-color: #404040;
                border: 1px solid #5E5E5E;
            }
        """)
        
        layout = QHBoxLayout(widget)
        layout.setContentsMargins(8, 5, 8, 5)
        
        # Checkbox
        checkbox = QCheckBox()
        checkbox.setChecked(plugin['enabled'])
        checkbox.stateChanged.connect(
            lambda state, name=plugin['name']: self._on_plugin_toggled(name, state == Qt.CheckState.Checked.value)
        )
        
        # Essential plugins have special styling
        if plugin['essential']:
            checkbox.setToolTip("Essential plugin - bypasses master switch")
        
        layout.addWidget(checkbox)
        
        # Store checkbox reference
        self.plugin_checkboxes[plugin['name']] = checkbox
        
        # Plugin name with icon
        icon = "⭐" if plugin['essential'] else "🔌"
        name_label = QLabel(f"{icon} {plugin['display_name']}")
        name_label.setStyleSheet("font-weight: bold; font-size: 9pt;")
        layout.addWidget(name_label)
        
        layout.addStretch()
        
        # Status indicator
        if plugin['enabled']:
            status_label = QLabel("✅ Active")
            status_label.setStyleSheet("color: #4CAF50; font-size: 8pt; font-weight: bold;")
        else:
            status_label = QLabel("⚪ Inactive")
            status_label.setStyleSheet("color: #9E9E9E; font-size: 8pt;")
        
        layout.addWidget(status_label)
        
        return widget
    
    def _on_master_switch_changed(self, state):
        """Handle master switch toggle."""
        enabled = (state == Qt.CheckState.Checked.value)
        
        if self.config_manager:
            self.config_manager.set_setting('plugins.enabled', enabled)
        
        # Emit signal
        self.masterSwitchToggled.emit(enabled)
        
        # Update plugin status
        QTimer.singleShot(100, self._update_plugin_status)
    
    def _on_plugin_toggled(self, plugin_name: str, enabled: bool):
        """Handle individual plugin toggle."""
        if self.config_manager:
            plugin_key = f"plugins.{plugin_name}.enabled"
            self.config_manager.set_setting(plugin_key, enabled)
        
        # Emit signal
        self.pluginToggled.emit(plugin_name, enabled)
        
        # Update status
        QTimer.singleShot(100, self._update_plugin_status)
    
    def refresh(self):
        """Refresh plugin status."""
        self._update_plugin_status()
