"""
Plugin Settings Dialog - PyQt6 Implementation

Generic dialog for configuring any plugin's settings dynamically
based on its plugin.json schema. Used as a fallback for plugins
that don't have hardcoded inline settings in the pipeline tab.
"""

import logging

from PyQt6.QtWidgets import (
    QDialog, QVBoxLayout, QFormLayout, QLabel,
    QLineEdit, QCheckBox, QComboBox, QDialogButtonBox,
    QGroupBox
)
from PyQt6.QtCore import Qt
from ui.common.widgets.custom_spinbox import CustomSpinBox, CustomDoubleSpinBox

from app.workflow.plugin_manager import PluginManager
from app.workflow.base.plugin_interface import PluginMetadata, SettingType
from app.localization import tr

logger = logging.getLogger(__name__)


class PluginSettingsDialog(QDialog):
    """Dialog for configuring plugin settings."""
    
    def __init__(self, plugin: PluginMetadata, plugin_manager: PluginManager, parent=None):
        super().__init__(parent)
        
        self.plugin = plugin
        self.plugin_manager = plugin_manager
        self.setting_widgets = {}
        
        self.setWindowTitle(tr("plugin_settings_configure_title", name=plugin.display_name))
        self.setMinimumWidth(500)
        self.setMinimumHeight(400)
        
        self._init_ui()
        self._load_settings()
    
    def _init_ui(self):
        """Initialize the UI."""
        layout = QVBoxLayout(self)
        
        # Plugin info
        info_group = QGroupBox(tr("plugin_information"))
        info_layout = QFormLayout(info_group)
        
        info_layout.addRow(tr("plugin_settings_name"), QLabel(self.plugin.display_name))
        info_layout.addRow(tr("plugin_settings_version"), QLabel(self.plugin.version))
        info_layout.addRow(tr("plugin_settings_author"), QLabel(self.plugin.author))
        info_layout.addRow(tr("plugin_settings_type"), QLabel(self.plugin.type.value))
        
        desc_label = QLabel(self.plugin.description)
        desc_label.setWordWrap(True)
        info_layout.addRow(tr("plugin_settings_description"), desc_label)
        
        if self.plugin.dependencies:
            deps_label = QLabel(", ".join(self.plugin.dependencies))
            deps_label.setWordWrap(True)
            info_layout.addRow(tr("plugin_settings_dependencies"), deps_label)
        
        layout.addWidget(info_group)
        
        # Settings
        if self.plugin.settings:
            settings_group = QGroupBox(tr("settings"))
            settings_layout = QFormLayout(settings_group)
            
            for setting_name, setting in self.plugin.settings.items():
                widget = self._create_setting_widget(setting)
                self.setting_widgets[setting_name] = widget
                
                label_text = setting_name.replace('_', ' ').title()
                if setting.description:
                    label_text += f"\n({setting.description})"
                
                label = QLabel(label_text)
                label.setWordWrap(True)
                
                settings_layout.addRow(label, widget)
            
            layout.addWidget(settings_group)
        else:
            no_settings_label = QLabel(tr("this_plugin_has_no_configurable_settings"))
            no_settings_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
            no_settings_label.setStyleSheet("color: #666; padding: 20px;")
            layout.addWidget(no_settings_label)
        
        # Buttons
        button_box = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel
        )
        button_box.accepted.connect(self.accept)
        button_box.rejected.connect(self.reject)
        
        layout.addWidget(button_box)
    
    def _create_setting_widget(self, setting):
        """Create appropriate widget for a setting based on its SettingType."""
        if setting.type == SettingType.STRING:
            if setting.options:
                widget = QComboBox()
                widget.addItems(setting.options)
                return widget
            else:
                widget = QLineEdit()
                widget.setPlaceholderText(str(setting.default))
                return widget
        
        elif setting.type == SettingType.INTEGER:
            widget = CustomSpinBox()
            if setting.min_value is not None:
                widget.setMinimum(int(setting.min_value))
            else:
                widget.setMinimum(-999999)
            if setting.max_value is not None:
                widget.setMaximum(int(setting.max_value))
            else:
                widget.setMaximum(999999)
            widget.setValue(int(setting.default))
            return widget
        
        elif setting.type == SettingType.FLOAT:
            widget = CustomDoubleSpinBox()
            if setting.min_value is not None:
                widget.setMinimum(float(setting.min_value))
            else:
                widget.setMinimum(-999999.0)
            if setting.max_value is not None:
                widget.setMaximum(float(setting.max_value))
            else:
                widget.setMaximum(999999.0)
            widget.setValue(float(setting.default))
            widget.setDecimals(2)
            return widget
        
        elif setting.type == SettingType.BOOLEAN:
            widget = QCheckBox()
            widget.setChecked(bool(setting.default))
            return widget
        
        else:
            # Fallback to text input
            widget = QLineEdit()
            widget.setText(str(setting.default))
            return widget
    
    def _load_settings(self):
        """Load current settings from plugin manager."""
        plugin_settings = self.plugin_manager.get_plugin_settings(self.plugin.name)
        
        if not plugin_settings:
            return
        
        for setting_name, widget in self.setting_widgets.items():
            value = plugin_settings.get(setting_name)
            if value is None:
                continue
            
            try:
                if isinstance(widget, QLineEdit):
                    widget.setText(str(value))
                elif isinstance(widget, CustomSpinBox):
                    widget.setValue(int(value))
                elif isinstance(widget, CustomDoubleSpinBox):
                    widget.setValue(float(value))
                elif isinstance(widget, QCheckBox):
                    widget.setChecked(bool(value))
                elif isinstance(widget, QComboBox):
                    index = widget.findText(str(value))
                    if index >= 0:
                        widget.setCurrentIndex(index)
            except (ValueError, TypeError) as e:
                logger.warning("Failed to load setting '%s': %s", setting_name, e)
    
    def accept(self):
        """Save settings and close dialog."""
        for setting_name, widget in self.setting_widgets.items():
            if isinstance(widget, QLineEdit):
                value = widget.text()
            elif isinstance(widget, CustomSpinBox):
                value = widget.value()
            elif isinstance(widget, CustomDoubleSpinBox):
                value = widget.value()
            elif isinstance(widget, QCheckBox):
                value = widget.isChecked()
            elif isinstance(widget, QComboBox):
                value = widget.currentText()
            else:
                value = None
            
            if value is not None:
                self.plugin_manager.set_plugin_setting(self.plugin.name, setting_name, value)
        
        super().accept()
