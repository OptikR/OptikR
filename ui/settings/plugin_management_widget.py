"""
Plugin Management Widget - PyQt6 Implementation

Widget for managing plugins: list, enable/disable, configure, create new.
"""

from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QGroupBox, QLabel, QPushButton,
    QListWidget, QListWidgetItem, QCheckBox, QMessageBox, QDialog
)
from PyQt6.QtCore import Qt, pyqtSignal

from app.workflow.plugin_manager import PluginManager
from app.workflow.base.plugin_interface import PluginType


class PluginManagementWidget(QWidget):
    """Widget for managing plugins."""
    
    # Signal emitted when plugin settings change
    pluginChanged = pyqtSignal()
    
    def __init__(self, config_manager=None, parent=None):
        """
        Initialize plugin management widget.
        
        Args:
            config_manager: Configuration manager
            parent: Parent widget
        """
        super().__init__(parent)
        
        self.config_manager = config_manager
        self.plugin_manager = PluginManager(plugin_directories=['plugins/'])
        
        # Scan for plugins
        self.plugin_manager.scan_plugins()
        
        # Initialize UI
        self._init_ui()
        
        # Load initial state
        self._refresh_plugin_list()
    
    def _init_ui(self):
        """Initialize the UI."""
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(10)
        
        # Header with title and buttons
        header_layout = QHBoxLayout()
        
        title_label = QLabel("🔌 Plugin Management")
        title_label.setStyleSheet("font-size: 14pt; font-weight: bold;")
        header_layout.addWidget(title_label)
        
        header_layout.addStretch()
        
        # Rescan button
        self.rescan_btn = QPushButton("🔄 Rescan Plugins")
        self.rescan_btn.clicked.connect(self._rescan_plugins)
        header_layout.addWidget(self.rescan_btn)
        
        # Create plugin button
        self.create_btn = QPushButton("➕ Create New Plugin")
        self.create_btn.clicked.connect(self._create_plugin)
        header_layout.addWidget(self.create_btn)
        
        layout.addLayout(header_layout)
        
        # Plugin count summary
        self.summary_label = QLabel()
        self.summary_label.setStyleSheet("color: #666; font-size: 9pt;")
        layout.addWidget(self.summary_label)
        
        # Plugin lists by type
        for plugin_type in PluginType:
            group = self._create_plugin_type_group(plugin_type)
            layout.addWidget(group)
        
        layout.addStretch()
    
    def _create_plugin_type_group(self, plugin_type: PluginType) -> QGroupBox:
        """
        Create a group box for a plugin type.
        
        Args:
            plugin_type: Type of plugins to show
            
        Returns:
            QGroupBox with plugin list
        """
        # Type icons
        type_icons = {
            PluginType.CAPTURE: "📷",
            PluginType.OCR: "📝",
            PluginType.TRANSLATION: "🌐",
            PluginType.OPTIMIZER: "⚡"
        }
        
        icon = type_icons.get(plugin_type, "🔌")
        title = f"{icon} {plugin_type.value.title()} Plugins"
        
        group = QGroupBox(title)
        layout = QVBoxLayout(group)
        
        # Plugin list
        plugin_list = QListWidget()
        plugin_list.setMaximumHeight(150)
        
        # Store reference for later updates
        setattr(self, f"{plugin_type.value}_list", plugin_list)
        
        layout.addWidget(plugin_list)
        
        # Buttons
        button_layout = QHBoxLayout()
        
        configure_btn = QPushButton("⚙️ Configure")
        configure_btn.clicked.connect(lambda: self._configure_plugin(plugin_type))
        button_layout.addWidget(configure_btn)
        
        reload_btn = QPushButton("🔄 Reload")
        reload_btn.clicked.connect(lambda: self._reload_plugin(plugin_type))
        button_layout.addWidget(reload_btn)
        
        button_layout.addStretch()
        
        layout.addLayout(button_layout)
        
        return group
    
    def _refresh_plugin_list(self):
        """Refresh the plugin lists."""
        # Update summary
        counts = self.plugin_manager.get_plugin_count_by_type()
        total = sum(counts.values())
        self.summary_label.setText(
            f"Total: {total} plugins | "
            f"Capture: {counts['capture']} | "
            f"OCR: {counts['ocr']} | "
            f"Translation: {counts['translation']} | "
            f"Optimizer: {counts['optimizer']}"
        )
        
        # Update each type list
        for plugin_type in PluginType:
            list_widget = getattr(self, f"{plugin_type.value}_list")
            list_widget.clear()
            
            plugins = self.plugin_manager.get_plugins_by_type(plugin_type)
            
            for plugin in plugins:
                item = QListWidgetItem()
                
                # Create checkbox widget
                checkbox = QCheckBox(f"{plugin.display_name} v{plugin.version}")
                checkbox.setChecked(self.plugin_manager.is_plugin_enabled(plugin.name))
                checkbox.stateChanged.connect(
                    lambda state, name=plugin.name: self._toggle_plugin(name, state == Qt.CheckState.Checked.value)
                )
                
                # Add tooltip with description
                checkbox.setToolTip(
                    f"{plugin.description}\n\n"
                    f"Author: {plugin.author}\n"
                    f"Dependencies: {', '.join(plugin.dependencies) if plugin.dependencies else 'None'}"
                )
                
                list_widget.addItem(item)
                list_widget.setItemWidget(item, checkbox)
    
    def _rescan_plugins(self):
        """Rescan for plugins."""
        count = self.plugin_manager.scan_plugins()
        self._refresh_plugin_list()
        
        QMessageBox.information(
            self,
            "Plugins Rescanned",
            f"Found {count} plugins."
        )
        
        self.pluginChanged.emit()
    
    def _toggle_plugin(self, plugin_name: str, enabled: bool):
        """
        Toggle plugin enabled state.
        
        Args:
            plugin_name: Name of the plugin
            enabled: True to enable, False to disable
        """
        self.plugin_manager.set_plugin_enabled(plugin_name, enabled)
        self.pluginChanged.emit()
    
    def _configure_plugin(self, plugin_type: PluginType):
        """
        Configure selected plugin.
        
        Args:
            plugin_type: Type of plugin
        """
        list_widget = getattr(self, f"{plugin_type.value}_list")
        current_item = list_widget.currentItem()
        
        if not current_item:
            QMessageBox.information(
                self,
                "No Plugin Selected",
                f"Please select a {plugin_type.value} plugin to configure."
            )
            return
        
        # Get plugin name from checkbox text
        checkbox = list_widget.itemWidget(current_item)
        plugin_name = checkbox.text().split(' v')[0]  # Remove version
        
        # Find plugin by display name
        plugins = self.plugin_manager.get_plugins_by_type(plugin_type)
        plugin = next((p for p in plugins if p.display_name == plugin_name), None)
        
        if not plugin:
            return
        
        # Show settings dialog
        from ui.dialogs.plugin_settings_dialog import PluginSettingsDialog
        dialog = PluginSettingsDialog(plugin, self.plugin_manager, self)
        if dialog.exec() == QDialog.DialogCode.Accepted:
            self.pluginChanged.emit()
    
    def _reload_plugin(self, plugin_type: PluginType):
        """
        Reload selected plugin.
        
        Args:
            plugin_type: Type of plugin
        """
        list_widget = getattr(self, f"{plugin_type.value}_list")
        current_item = list_widget.currentItem()
        
        if not current_item:
            QMessageBox.information(
                self,
                "No Plugin Selected",
                f"Please select a {plugin_type.value} plugin to reload."
            )
            return
        
        # Get plugin name from checkbox text
        checkbox = list_widget.itemWidget(current_item)
        plugin_name = checkbox.text().split(' v')[0]
        
        # Find plugin by display name
        plugins = self.plugin_manager.get_plugins_by_type(plugin_type)
        plugin = next((p for p in plugins if p.display_name == plugin_name), None)
        
        if not plugin:
            return
        
        # Reload plugin
        if self.plugin_manager.reload_plugin(plugin.name):
            QMessageBox.information(
                self,
                "Plugin Reloaded",
                f"Plugin '{plugin.display_name}' has been reloaded successfully."
            )
            self._refresh_plugin_list()
            self.pluginChanged.emit()
        else:
            QMessageBox.warning(
                self,
                "Reload Failed",
                f"Failed to reload plugin '{plugin.display_name}'."
            )
    
    def _create_plugin(self):
        """Launch plugin generator."""
        QMessageBox.information(
            self,
            "Plugin Generator",
            "To create a new plugin, run:\n\n"
            "python -m src.workflow.plugin_generator\n\n"
            "in the terminal, then click 'Rescan Plugins'.\n\n"
            "GUI plugin generator coming soon!"
        )
    
    def get_plugin_manager(self) -> PluginManager:
        """
        Get the plugin manager instance.
        
        Returns:
            PluginManager instance
        """
        return self.plugin_manager
