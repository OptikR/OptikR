"""
Plugin Discovery Dialog - Manual plugin directory management.

Allows users to:
- Add custom plugin directories
- Discover plugins from external sources
- Manage plugin search paths
"""

from PyQt6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QListWidget, QListWidgetItem, QFileDialog, QMessageBox,
    QGroupBox
)
from PyQt6.QtCore import Qt, pyqtSignal
from pathlib import Path
import json


class PluginDiscoveryDialog(QDialog):
    """Dialog for managing plugin discovery directories."""
    
    # Signals
    pluginsUpdated = pyqtSignal()  # Emitted when plugin directories change
    
    def __init__(self, config_manager=None, parent=None):
        super().__init__(parent)
        self.config_manager = config_manager
        
        self.setWindowTitle("Plugin Discovery")
        self.setModal(True)
        self.setMinimumSize(700, 500)
        
        self._init_ui()
        self._load_plugin_directories()
    
    def _init_ui(self):
        """Initialize the UI."""
        layout = QVBoxLayout(self)
        layout.setSpacing(15)
        
        # Description
        desc = QLabel(
            "Manage plugin search directories. OptikR will scan these locations "
            "for OCR engines, translation engines, and optimizer plugins."
        )
        desc.setWordWrap(True)
        desc.setStyleSheet("font-size: 10pt; margin-bottom: 10px;")
        layout.addWidget(desc)
        
        # Plugin directories list
        dir_group = QGroupBox("Plugin Directories")
        dir_layout = QVBoxLayout(dir_group)
        
        self.dir_list = QListWidget()
        self.dir_list.setSelectionMode(QListWidget.SelectionMode.SingleSelection)
        dir_layout.addWidget(self.dir_list)
        
        # Buttons for directory management
        btn_layout = QHBoxLayout()
        
        add_btn = QPushButton("➕ Add Directory")
        add_btn.setProperty("class", "action")
        add_btn.clicked.connect(self._add_directory)
        btn_layout.addWidget(add_btn)
        
        remove_btn = QPushButton("➖ Remove Selected")
        remove_btn.setProperty("class", "action")
        remove_btn.clicked.connect(self._remove_directory)
        btn_layout.addWidget(remove_btn)
        
        scan_btn = QPushButton("🔍 Scan Now")
        scan_btn.setProperty("class", "action")
        scan_btn.setToolTip("Scan all directories for plugins")
        scan_btn.clicked.connect(self._scan_plugins)
        btn_layout.addWidget(scan_btn)
        
        btn_layout.addStretch()
        dir_layout.addLayout(btn_layout)
        
        layout.addWidget(dir_group)
        
        # Discovered plugins info
        info_group = QGroupBox("Discovered Plugins")
        info_layout = QVBoxLayout(info_group)
        
        self.plugin_info_label = QLabel("Click 'Scan Now' to discover plugins...")
        self.plugin_info_label.setWordWrap(True)
        self.plugin_info_label.setStyleSheet("color: #666666; font-size: 9pt;")
        info_layout.addWidget(self.plugin_info_label)
        
        layout.addWidget(info_group)
        
        # Help text
        help_text = QLabel(
            "💡 Tips:\n"
            "• Default plugin directory: plugins/\n"
            "• Add external directories to use plugins from USB drives or network shares\n"
            "• Plugins must have a valid plugin.json file to be discovered\n"
            "• Changes take effect after restarting the application"
        )
        help_text.setWordWrap(True)
        help_text.setStyleSheet(
            "color: #2196F3; font-size: 9pt; padding: 10px; "
            "background-color: #1E3A4F; border-left: 3px solid #4A9EFF; border-radius: 3px;"
        )
        layout.addWidget(help_text)
        
        # Dialog buttons
        dialog_btn_layout = QHBoxLayout()
        dialog_btn_layout.addStretch()
        
        save_btn = QPushButton("Save")
        save_btn.setProperty("class", "primary")
        save_btn.setMinimumWidth(100)
        save_btn.clicked.connect(self._save_and_close)
        dialog_btn_layout.addWidget(save_btn)
        
        cancel_btn = QPushButton("Cancel")
        cancel_btn.setMinimumWidth(100)
        cancel_btn.clicked.connect(self.reject)
        dialog_btn_layout.addWidget(cancel_btn)
        
        layout.addLayout(dialog_btn_layout)
    
    def _load_plugin_directories(self):
        """Load plugin directories from config."""
        if not self.config_manager:
            # Add default directory
            self.dir_list.addItem("plugins/")
            return
        
        # Load from config
        directories = self.config_manager.get_setting(
            'plugins.search_directories',
            ['plugins/']
        )
        
        for directory in directories:
            item = QListWidgetItem(directory)
            # Mark default directory
            if directory == 'plugins/':
                item.setToolTip("Default plugin directory (cannot be removed)")
            self.dir_list.addItem(item)
    
    def _add_directory(self):
        """Add a new plugin directory."""
        directory = QFileDialog.getExistingDirectory(
            self,
            "Select Plugin Directory",
            str(Path.home())
        )
        
        if not directory:
            return
        
        # Check if already added
        for i in range(self.dir_list.count()):
            if self.dir_list.item(i).text() == directory:
                QMessageBox.information(
                    self,
                    "Already Added",
                    "This directory is already in the list."
                )
                return
        
        # Add to list
        self.dir_list.addItem(directory)
    
    def _remove_directory(self):
        """Remove selected directory."""
        current_item = self.dir_list.currentItem()
        if not current_item:
            QMessageBox.information(
                self,
                "No Selection",
                "Please select a directory to remove."
            )
            return
        
        # Don't allow removing default directory
        if current_item.text() == 'plugins/':
            QMessageBox.warning(
                self,
                "Cannot Remove",
                "The default 'plugins/' directory cannot be removed."
            )
            return
        
        # Confirm removal
        reply = QMessageBox.question(
            self,
            "Confirm Removal",
            f"Remove this directory from plugin search?\n\n{current_item.text()}",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
        )
        
        if reply == QMessageBox.StandardButton.Yes:
            self.dir_list.takeItem(self.dir_list.row(current_item))
    
    def _scan_plugins(self):
        """Scan all directories for plugins."""
        directories = []
        for i in range(self.dir_list.count()):
            directories.append(self.dir_list.item(i).text())
        
        # Scan for plugins
        ocr_plugins = []
        translation_plugins = []
        optimizer_plugins = []
        
        for directory in directories:
            dir_path = Path(directory)
            if not dir_path.exists():
                continue
            
            # Scan for plugin.json files
            for plugin_json in dir_path.rglob('plugin.json'):
                try:
                    with open(plugin_json, 'r', encoding='utf-8') as f:
                        plugin_data = json.load(f)
                    
                    plugin_type = plugin_data.get('type', 'unknown')
                    plugin_name = plugin_data.get('name', 'Unknown')
                    
                    if plugin_type == 'ocr':
                        ocr_plugins.append(plugin_name)
                    elif plugin_type == 'translation':
                        translation_plugins.append(plugin_name)
                    elif plugin_type == 'optimizer':
                        optimizer_plugins.append(plugin_name)
                        
                except Exception as e:
                    print(f"[Plugin Discovery] Error reading {plugin_json}: {e}")
        
        # Update info label
        info_text = f"Found:\n"
        info_text += f"• {len(ocr_plugins)} OCR engine(s): {', '.join(ocr_plugins) if ocr_plugins else 'None'}\n"
        info_text += f"• {len(translation_plugins)} Translation engine(s): {', '.join(translation_plugins) if translation_plugins else 'None'}\n"
        info_text += f"• {len(optimizer_plugins)} Optimizer plugin(s): {', '.join(optimizer_plugins) if optimizer_plugins else 'None'}"
        
        self.plugin_info_label.setText(info_text)
        
        if not ocr_plugins and not translation_plugins and not optimizer_plugins:
            QMessageBox.warning(
                self,
                "No Plugins Found",
                "No valid plugins were found in the specified directories.\n\n"
                "Make sure plugin directories contain valid plugin.json files."
            )
    
    def _save_and_close(self):
        """Save plugin directories and close."""
        if not self.config_manager:
            self.accept()
            return
        
        # Get all directories
        directories = []
        for i in range(self.dir_list.count()):
            directories.append(self.dir_list.item(i).text())
        
        # Save to config
        self.config_manager.set_setting('plugins.search_directories', directories)
        self.config_manager.save_config()
        
        # Emit signal
        self.pluginsUpdated.emit()
        
        QMessageBox.information(
            self,
            "Saved",
            "Plugin directories saved.\n\n"
            "Please restart the application for changes to take effect."
        )
        
        self.accept()
    
    @staticmethod
    def show_discovery_dialog(config_manager=None, parent=None):
        """
        Show the plugin discovery dialog.
        
        Returns:
            bool: True if changes were made, False otherwise
        """
        dialog = PluginDiscoveryDialog(config_manager, parent)
        return dialog.exec() == QDialog.DialogCode.Accepted
