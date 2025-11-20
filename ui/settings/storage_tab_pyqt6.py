"""
Storage Settings Tab - PyQt6 Implementation
Cache management, storage locations, and data retention configuration.
"""

import os
import shutil
from pathlib import Path
from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QFormLayout, QGroupBox,
    QLabel, QCheckBox, QSpinBox, QPushButton, QLineEdit,
    QProgressBar, QFileDialog, QMessageBox,
    QComboBox, QListWidget, QListWidgetItem, QTableWidget, QTableWidgetItem, QHeaderView
)
from PyQt6.QtCore import Qt, pyqtSignal, QFileInfo, QDir, QSettings
from PyQt6.QtGui import QColor
from ui.custom_spinbox import CustomSpinBox, CustomDoubleSpinBox

# Import custom scroll area
from .scroll_area_no_wheel import ScrollAreaNoWheel

# Import translation system
from app.translations import TranslatableMixin

# Import path utilities for EXE compatibility
from app.utils.path_utils import get_app_path, ensure_app_directory


class StorageSettingsTab(TranslatableMixin, QWidget):
    """Storage settings including cache, directories, and retention policies."""
    
    # Signal emitted when any setting changes
    settingChanged = pyqtSignal()
    
    def __init__(self, config_manager=None, pipeline=None, parent=None):
        """Initialize the Storage settings tab."""
        super().__init__(parent)
        
        self.config_manager = config_manager
        self.pipeline = pipeline  # Pipeline for dictionary management
        
        # Track original loaded state to detect real changes
        self._original_state = {}
        
        # Track selected dictionary file path (for multiple dicts per language pair)
        self._selected_dict_path = None
        
        # Cache widgets
        self.cache_enabled_check = None
        self.cache_size_spinbox = None
        self.cache_usage_bar = None
        self.cache_usage_label = None
        self.clear_cache_btn = None
        
        # Directory widgets
        self.model_dir_edit = None
        self.data_dir_edit = None
        self.cache_dir_edit = None
        self.dict_dir_edit = None
        
        # Dictionary widgets - REMOVED (moved to Smart Dictionary tab)
        # self.dict_entries_label = None
        # self.dict_usage_label = None
        # self.dict_avg_usage_label = None
        # self.dict_file_size_label = None
        # self.dict_hit_rate_label = None
        # self.language_pair_combo = None
        # self.language_pair_list = None
        # self.most_used_list = None
        
        # Retention widget
        self.retention_spinbox = None
        
        # Initialize UI
        self._init_ui()
    
    def _init_ui(self):
        """Initialize the UI."""
        # Create main layout
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.setSpacing(0)
        
        # Create scroll area (custom - only scrolls when mouse is over it)
        scroll_area = ScrollAreaNoWheel()
        scroll_area.setWidgetResizable(True)
        scroll_area.setFrameShape(ScrollAreaNoWheel.Shape.NoFrame)
        scroll_area.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        scroll_area.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAsNeeded)
        
        # Create content widget
        content_widget = QWidget()
        content_layout = QVBoxLayout(content_widget)
        content_layout.setContentsMargins(5, 5, 5, 5)
        content_layout.setSpacing(10)
        
        # Create sections
        self._create_storage_overview_section(content_layout)
        self._create_cache_section(content_layout)
        self._create_language_models_section(content_layout)
        self._create_dictionary_redirect_note(content_layout)  # Dictionary management moved to Smart Dictionary tab
        self._create_storage_locations_section(content_layout)
        self._create_retention_section(content_layout)
        self._create_storage_usage_section(content_layout)
        
        # Add stretch at the end
        content_layout.addStretch()
        
        # Set content widget to scroll area
        scroll_area.setWidget(content_widget)
        
        # Add scroll area to main layout
        main_layout.addWidget(scroll_area)
    
    def _create_label(self, text: str, bold: bool = False) -> QLabel:
        """Create a label with consistent styling."""
        label = QLabel(text)
        if bold:
            label.setStyleSheet("font-weight: 600; font-size: 9pt;")
        else:
            label.setStyleSheet("font-size: 9pt;")
        return label
    
    def _get_current_state(self):
        """Get current state of all settings."""
        state = {}
        if self.cache_enabled_check:
            state['cache_enabled'] = self.cache_enabled_check.isChecked()
        if self.cache_size_spinbox:
            state['cache_size'] = self.cache_size_spinbox.value()
        if self.cache_dir_edit:
            state['cache_dir'] = self.cache_dir_edit.text()
        return state
    
    def on_change(self):
        """Called when any setting changes - always emits signal for main window to check."""
        self.settingChanged.emit()
    
    def _create_storage_overview_section(self, parent_layout):
        """Create storage overview section showing all file locations."""
        group = QGroupBox()
        self.set_translatable_text(group, "storage_storage_overview_section")
        layout = QVBoxLayout(group)
        layout.setSpacing(8)
        layout.setContentsMargins(15, 20, 15, 15)
        
        # Overview description
        overview_desc = QLabel(
            "All application files are organized in a structured directory layout. "
            "Paths are shown relative to run.py and work for both development and production. "
            "You can customize these locations below for better organization."
        )
        overview_desc.setWordWrap(True)
        overview_desc.setStyleSheet("color: #666666; font-size: 9pt; margin-bottom: 10px;")
        layout.addWidget(overview_desc)
        
        # Create a grid-like layout for file locations
        locations_widget = QWidget()
        locations_layout = QVBoxLayout(locations_widget)
        locations_layout.setSpacing(6)
        locations_layout.setContentsMargins(10, 10, 10, 10)
        locations_widget.setStyleSheet("QWidget { background-color: #2D2D2D; border-radius: 4px; }")
        
        # File location entries (relative to run.py)
        file_locations = [
            ("📁 Config Files", "user_data/config", "user_config.json (consolidated configuration)"),
            ("📦 Cache", "system_data/cache", "Translation cache and temporary data"),
            ("📚 Dictionary", "user_data/learned/translations", "Learned translations (learned_dictionary_*.json.gz)"),
            ("🤖 AI Models", "system_data/ai_models", "OCR and translation models (downloaded automatically)"),
            ("📊 Data", "user_data", "User data and exports"),
            ("📝 Logs", "system_data/logs", "Application logs and debug information"),
            ("🎨 Styles", "app/styles", "UI stylesheets (dark.qss)"),
            ("🔌 Plugins", "plugins", "Optimizer and text processor plugins"),
        ]
        
        for icon_name, path, description in file_locations:
            entry_layout = QHBoxLayout()
            entry_layout.setSpacing(8)
            
            # Icon and name
            name_label = QLabel(icon_name)
            name_label.setStyleSheet("font-weight: 600; font-size: 9pt; min-width: 120px;")
            entry_layout.addWidget(name_label)
            
            # Path
            path_label = QLabel(path)
            path_label.setStyleSheet("font-family: 'Consolas', 'Courier New', monospace; font-size: 9pt; color: #2196F3; min-width: 100px;")
            entry_layout.addWidget(path_label)
            
            # Description
            desc_label = QLabel(description)
            desc_label.setStyleSheet("font-size: 8pt; color: #666666;")
            desc_label.setWordWrap(True)
            entry_layout.addWidget(desc_label, 1)
            
            locations_layout.addLayout(entry_layout)
        
        layout.addWidget(locations_widget)
        
        # Info note
        info_note = QLabel(
            "💡 All paths are relative to run.py (the application root directory). "
            "You can change the main directories below to customize your storage layout."
        )
        info_note.setWordWrap(True)
        info_note.setStyleSheet("color: #2196F3; font-size: 9pt; margin-top: 10px;")
        layout.addWidget(info_note)
        
        parent_layout.addWidget(group)
    
    def _create_cache_section(self, parent_layout):
        """Create cache settings section."""
        group = QGroupBox()
        self.set_translatable_text(group, "storage_cache_settings_section")
        layout = QVBoxLayout(group)
        layout.setSpacing(12)
        layout.setContentsMargins(15, 20, 15, 15)
        
        # Enable cache checkbox
        self.cache_enabled_check = QCheckBox()
        self.set_translatable_text(self.cache_enabled_check, "storage_enable_translation_cache_check")
        self.cache_enabled_check.setChecked(True)
        self.cache_enabled_check.stateChanged.connect(self._on_cache_enabled_changed)
        layout.addWidget(self.cache_enabled_check)
        
        # Cache description
        cache_desc = QLabel(
            "Caching stores previously translated text to improve performance and reduce API calls. "
            "Recommended for better speed and lower costs."
        )
        cache_desc.setWordWrap(True)
        cache_desc.setStyleSheet("color: #666666; font-size: 9pt; margin-top: 5px; margin-bottom: 10px;")
        layout.addWidget(cache_desc)
        
        # Cache size limit - using grid layout
        from PyQt6.QtWidgets import QGridLayout
        size_grid = QGridLayout()
        size_grid.setHorizontalSpacing(8)
        size_grid.setVerticalSpacing(8)
        size_grid.setContentsMargins(0, 5, 0, 5)
        size_grid.setColumnStretch(2, 1)
        
        size_label = self._create_label("Cache Size Limit:", bold=True)
        
        self.cache_size_spinbox = CustomSpinBox()
        self.cache_size_spinbox.setRange(100, 5000)
        self.cache_size_spinbox.setValue(500)
        self.cache_size_spinbox.setSuffix("MB")
        self.cache_size_spinbox.setSingleStep(100)
        self.cache_size_spinbox.setMinimumWidth(120)
        self.cache_size_spinbox.valueChanged.connect(self.on_change)
        
        size_grid.addWidget(size_label, 0, 0)
        size_grid.addWidget(self.cache_size_spinbox, 0, 1)
        layout.addLayout(size_grid)
        
        # Cache directory
        cache_dir_layout = QHBoxLayout()
        cache_dir_layout.setSpacing(10)
        
        cache_dir_label = self._create_label("Cache Directory:", bold=True)
        cache_dir_layout.addWidget(cache_dir_label)
        
        self.cache_dir_edit = QLineEdit()
        self.cache_dir_edit.setText("./cache")
        self.cache_dir_edit.setPlaceholderText("Path to cache directory")
        self.cache_dir_edit.textChanged.connect(self.on_change)
        cache_dir_layout.addWidget(self.cache_dir_edit)
        
        cache_browse_btn = QPushButton()
        self.set_translatable_text(cache_browse_btn, "storage_browse_button")
        cache_browse_btn.setProperty("class", "action")
        cache_browse_btn.setMinimumWidth(80)
        cache_browse_btn.clicked.connect(lambda: self._browse_directory(self.cache_dir_edit, "Select Cache Directory"))
        cache_dir_layout.addWidget(cache_browse_btn)
        
        cache_open_btn = QPushButton()
        self.set_translatable_text(cache_open_btn, "storage_open_button")
        cache_open_btn.setProperty("class", "action")
        cache_open_btn.setMinimumWidth(80)
        cache_open_btn.clicked.connect(lambda: self._open_folder(self.cache_dir_edit.text()))
        cache_dir_layout.addWidget(cache_open_btn)
        
        layout.addLayout(cache_dir_layout)
        
        # Clear cache buttons
        clear_layout = QHBoxLayout()
        clear_layout.setSpacing(10)
        
        self.clear_cache_btn = QPushButton()
        self.set_translatable_text(self.clear_cache_btn, "storage_clear_translation_cache_button")
        self.clear_cache_btn.setProperty("class", "action")
        self.clear_cache_btn.setMinimumWidth(160)
        self.clear_cache_btn.clicked.connect(self._clear_cache)
        clear_layout.addWidget(self.clear_cache_btn)
        
        self.clear_all_cache_btn = QPushButton()
        self.set_translatable_text(self.clear_all_cache_btn, "storage_clear_all_caches_button")
        self.clear_all_cache_btn.setProperty("class", "action")
        self.clear_all_cache_btn.setMinimumWidth(140)
        self.clear_all_cache_btn.setStyleSheet("""
            QPushButton {
                background-color: #D32F2F;
                color: white;
            }
            QPushButton:hover {
                background-color: #F44336;
            }
        """)
        self.clear_all_cache_btn.clicked.connect(self._clear_all_caches)
        clear_layout.addWidget(self.clear_all_cache_btn)
        
        clear_layout.addStretch()
        
        clear_desc = QLabel("Clear translation cache or all caches (including Python bytecode)")
        clear_desc.setStyleSheet("color: #666666; font-size: 9pt;")
        clear_layout.addWidget(clear_desc)
        
        layout.addLayout(clear_layout)
        
        parent_layout.addWidget(group)
    
    def _create_language_models_section(self, parent_layout):
        """Create language models browser section."""
        group = QGroupBox()
        self.set_translatable_text(group, "storage_language_models_section")
        layout = QVBoxLayout(group)
        layout.setSpacing(12)
        layout.setContentsMargins(15, 20, 15, 15)
        
        # Description
        models_desc = QLabel(
            "Browse and manage downloaded AI language models. "
            "Models are cached by HuggingFace Transformers library and used for translation."
        )
        models_desc.setWordWrap(True)
        models_desc.setStyleSheet("color: #666666; font-size: 9pt; margin-bottom: 10px;")
        layout.addWidget(models_desc)
        
        # HuggingFace cache location
        hf_cache_layout = QHBoxLayout()
        hf_cache_layout.setSpacing(10)
        
        hf_cache_label = self._create_label("HuggingFace Cache:", bold=True)
        hf_cache_layout.addWidget(hf_cache_label)
        
        hf_cache_path = Path.home() / '.cache' / 'huggingface' / 'hub'
        hf_cache_edit = QLineEdit()
        hf_cache_edit.setText(str(hf_cache_path))
        hf_cache_edit.setReadOnly(True)
        hf_cache_edit.setStyleSheet("background-color: #2D2D2D;")
        hf_cache_layout.addWidget(hf_cache_edit)
        
        hf_open_btn = QPushButton()
        self.set_translatable_text(hf_open_btn, "storage_open_button_1")
        hf_open_btn.setProperty("class", "action")
        hf_open_btn.setMinimumWidth(80)
        hf_open_btn.clicked.connect(lambda: self._open_folder(str(hf_cache_path)))
        hf_cache_layout.addWidget(hf_open_btn)
        
        layout.addLayout(hf_cache_layout)
        
        # Downloaded models list
        models_label = self._create_label("Downloaded MarianMT Models:", bold=True)
        layout.addWidget(models_label)
        
        self.models_list = QListWidget()
        self.models_list.setMaximumHeight(150)
        layout.addWidget(self.models_list)
        
        # Model actions
        actions_layout = QHBoxLayout()
        actions_layout.setSpacing(10)
        
        refresh_models_btn = QPushButton()
        self.set_translatable_text(refresh_models_btn, "storage_refresh_button")
        refresh_models_btn.setProperty("class", "action")
        refresh_models_btn.setMinimumWidth(100)
        refresh_models_btn.clicked.connect(self._refresh_language_models)
        actions_layout.addWidget(refresh_models_btn)
        
        open_model_btn = QPushButton()
        self.set_translatable_text(open_model_btn, "storage_open_selected_button")
        open_model_btn.setProperty("class", "action")
        open_model_btn.setMinimumWidth(120)
        open_model_btn.clicked.connect(self._open_selected_model)
        actions_layout.addWidget(open_model_btn)
        
        delete_model_btn = QPushButton()
        self.set_translatable_text(delete_model_btn, "storage_delete_selected_button")
        delete_model_btn.setProperty("class", "action")
        delete_model_btn.setMinimumWidth(120)
        delete_model_btn.clicked.connect(self._delete_selected_model)
        actions_layout.addWidget(delete_model_btn)
        
        actions_layout.addStretch()
        layout.addLayout(actions_layout)
        
        # Model info
        model_info = QLabel(
            "💡 Models are downloaded automatically when first used. "
            "Each model is ~300-500 MB. You can safely delete unused models to free up space."
        )
        model_info.setWordWrap(True)
        model_info.setStyleSheet("color: #2196F3; font-size: 9pt; margin-top: 10px;")
        layout.addWidget(model_info)
        
        parent_layout.addWidget(group)
        
        # Initialize models list
        self._refresh_language_models()
    
    def _refresh_language_models(self):
        """Refresh the language models list."""
        try:
            self.models_list.clear()
            
            # Check HuggingFace cache directory
            cache_dir = Path.home() / '.cache' / 'huggingface' / 'hub'
            
            if not cache_dir.exists():
                item = QListWidgetItem("⚠️ No models found - HuggingFace cache directory doesn't exist")
                item.setData(Qt.ItemDataRole.UserRole, None)
                self.models_list.addItem(item)
                return
            
            models_found = []
            
            # Look for MarianMT model directories
            for model_dir in cache_dir.iterdir():
                if model_dir.is_dir() and 'opus-mt-' in model_dir.name:
                    try:
                        # Extract language pair from model name
                        parts = model_dir.name.split('--')
                        if len(parts) >= 3 and parts[1] == 'Helsinki-NLP':
                            model_name = parts[2]  # opus-mt-en-de
                            lang_pair = model_name.replace('opus-mt-', '')  # en-de
                            
                            if '-' in lang_pair:
                                src, tgt = lang_pair.split('-', 1)
                                
                                # Calculate directory size
                                try:
                                    total_size = sum(
                                        f.stat().st_size 
                                        for f in model_dir.rglob('*') 
                                        if f.is_file()
                                    )
                                    size_mb = total_size / (1024 * 1024)
                                    size_str = f"{size_mb:.0f} MB"
                                except:
                                    size_str = "Unknown size"
                                
                                models_found.append({
                                    'name': f"{src.upper()} → {tgt.upper()}",
                                    'size': size_str,
                                    'path': model_dir,
                                    'lang_pair': lang_pair
                                })
                    except Exception as e:
                        continue
            
            if not models_found:
                item = QListWidgetItem("⚠️ No MarianMT models found in cache")
                item.setData(Qt.ItemDataRole.UserRole, None)
                self.models_list.addItem(item)
            else:
                # Sort by language pair
                models_found.sort(key=lambda x: x['lang_pair'])
                
                for model in models_found:
                    item_text = f"✅ {model['name']} - {model['size']}"
                    item = QListWidgetItem(item_text)
                    item.setData(Qt.ItemDataRole.UserRole, model['path'])
                    self.models_list.addItem(item)
                
                # Add summary
                total_size = sum(
                    float(m['size'].replace(' MB', '')) 
                    for m in models_found 
                    if 'Unknown' not in m['size']
                )
                summary_item = QListWidgetItem(f"📊 Total: {len(models_found)} models, {total_size:.0f} MB")
                summary_item.setData(Qt.ItemDataRole.UserRole, None)
                summary_item.setForeground(Qt.GlobalColor.darkGray)
                self.models_list.addItem(summary_item)
        
        except Exception as e:
            item = QListWidgetItem(f"❌ Error loading models: {str(e)}")
            item.setData(Qt.ItemDataRole.UserRole, None)
            self.models_list.addItem(item)
    
    def _open_selected_model(self):
        """Open the selected model directory in file explorer."""
        selected_items = self.models_list.selectedItems()
        if not selected_items:
            QMessageBox.warning(self, "No Selection", "Please select a model to open.")
            return
        
        model_path = selected_items[0].data(Qt.ItemDataRole.UserRole)
        if model_path:
            self._open_folder(str(model_path))
        else:
            QMessageBox.information(self, "No Path", "This item doesn't have a folder path.")
    
    def _delete_selected_model(self):
        """Delete the selected model from cache."""
        selected_items = self.models_list.selectedItems()
        if not selected_items:
            QMessageBox.warning(self, "No Selection", "Please select a model to delete.")
            return
        
        model_path = selected_items[0].data(Qt.ItemDataRole.UserRole)
        if not model_path:
            QMessageBox.information(self, "No Path", "This item cannot be deleted.")
            return
        
        model_name = selected_items[0].text().split(' - ')[0].replace('✅ ', '')
        
        reply = QMessageBox.question(
            self,
            "Confirm Delete",
            f"Delete model '{model_name}'?\n\n"
            f"This will permanently remove the model from your cache. "
            f"You can re-download it later if needed.",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            QMessageBox.StandardButton.No
        )
        
        if reply == QMessageBox.StandardButton.Yes:
            try:
                import shutil
                shutil.rmtree(model_path)
                QMessageBox.information(
                    self,
                    "Model Deleted",
                    f"Model '{model_name}' has been deleted successfully."
                )
                self._refresh_language_models()
            except Exception as e:
                QMessageBox.critical(
                    self,
                    "Delete Failed",
                    f"Failed to delete model:\n{str(e)}"
                )
    
    def _create_dictionary_redirect_note(self, parent_layout):
        """Create note directing users to Smart Dictionary tab."""
        group = QGroupBox()
        self.set_translatable_text(group, "storage_smart_dictionary_section")
        layout = QVBoxLayout(group)
        layout.setContentsMargins(15, 20, 15, 15)
        
        note = QLabel(
            "<b>Dictionary management has moved!</b><br><br>"
            "All dictionary features are now in the dedicated <b>Smart Dictionary</b> tab.<br><br>"
            "<b>Go to Settings → Smart Dictionary to:</b><br>"
            "• View and edit dictionary entries<br>"
            "• Export/Import dictionaries<br>"
            "• Configure auto-learning settings<br>"
            "• Manage language pairs<br>"
            "• View usage statistics"
        )
        note.setWordWrap(True)
        note.setStyleSheet(
            "color: #2196F3; font-size: 9pt; padding: 15px; "
            "background-color: rgba(33, 150, 243, 0.1); border-radius: 6px; "
            "border-left: 4px solid #2196F3;"
        )
        layout.addWidget(note)
        
        parent_layout.addWidget(group)
    
    def _create_storage_locations_section(self, parent_layout):
        """Create storage locations section."""
        group = QGroupBox()
        self.set_translatable_text(group, "storage_storage_locations_section")
        layout = QVBoxLayout(group)
        layout.setSpacing(12)
        layout.setContentsMargins(15, 20, 15, 15)
        
        # Config directory
        config_layout = QHBoxLayout()
        config_layout.setSpacing(10)
        
        config_label = self._create_label("Config Directory:", bold=True)
        config_layout.addWidget(config_label)
        
        self.config_dir_edit = QLineEdit()
        self.config_dir_edit.setText("user_data/config")
        self.config_dir_edit.setPlaceholderText("Path to config directory")
        self.config_dir_edit.textChanged.connect(self.on_change)
        config_layout.addWidget(self.config_dir_edit)
        
        config_browse_btn = QPushButton()
        self.set_translatable_text(config_browse_btn, "storage_browse_button_1")
        config_browse_btn.setProperty("class", "action")
        config_browse_btn.setMinimumWidth(80)
        config_browse_btn.clicked.connect(lambda: self._browse_directory(self.config_dir_edit, "Select Config Directory"))
        config_layout.addWidget(config_browse_btn)
        
        config_open_btn = QPushButton()
        self.set_translatable_text(config_open_btn, "storage_open_button_2")
        config_open_btn.setProperty("class", "action")
        config_open_btn.setMinimumWidth(80)
        config_open_btn.clicked.connect(lambda: self._open_folder(self.config_dir_edit.text()))
        config_layout.addWidget(config_open_btn)
        
        layout.addLayout(config_layout)
        
        # Config directory description
        config_desc = QLabel("User configuration (user_config.json - all settings consolidated)")
        config_desc.setStyleSheet("color: #666666; font-size: 9pt; margin-bottom: 10px;")
        layout.addWidget(config_desc)
        
        # AI Models directory
        model_layout = QHBoxLayout()
        model_layout.setSpacing(10)
        
        model_label = self._create_label("AI Models Directory:", bold=True)
        model_layout.addWidget(model_label)
        
        self.model_dir_edit = QLineEdit()
        self.model_dir_edit.setText("system_data/ai_models")
        self.model_dir_edit.setPlaceholderText("Path to AI models directory")
        self.model_dir_edit.textChanged.connect(self.on_change)
        model_layout.addWidget(self.model_dir_edit)
        
        model_browse_btn = QPushButton()
        self.set_translatable_text(model_browse_btn, "storage_browse_button_2")
        model_browse_btn.setProperty("class", "action")
        model_browse_btn.setMinimumWidth(80)
        model_browse_btn.clicked.connect(lambda: self._browse_directory(self.model_dir_edit, "Select AI Models Directory"))
        model_layout.addWidget(model_browse_btn)
        
        model_open_btn = QPushButton()
        self.set_translatable_text(model_open_btn, "storage_open_button_3")
        model_open_btn.setProperty("class", "action")
        model_open_btn.setMinimumWidth(80)
        model_open_btn.clicked.connect(lambda: self._open_folder(self.model_dir_edit.text()))
        model_layout.addWidget(model_open_btn)
        
        layout.addLayout(model_layout)
        
        # Model directory description
        model_desc = QLabel("AI models for OCR and translation (downloaded automatically)")
        model_desc.setStyleSheet("color: #666666; font-size: 9pt; margin-bottom: 10px;")
        layout.addWidget(model_desc)
        
        # Translation Models subdirectory
        lang_model_layout = QHBoxLayout()
        lang_model_layout.setSpacing(10)
        
        lang_model_label = self._create_label("  ↳ Translation Models:", bold=False)
        lang_model_label.setStyleSheet("color: #888888; font-size: 9pt; margin-left: 20px;")
        lang_model_layout.addWidget(lang_model_label)
        
        lang_model_path_label = QLabel("system_data/ai_models/translation/")
        lang_model_path_label.setStyleSheet("color: #666666; font-size: 9pt;")
        lang_model_layout.addWidget(lang_model_path_label)
        lang_model_layout.addStretch()
        
        lang_model_open_btn = QPushButton()
        self.set_translatable_text(lang_model_open_btn, "storage_open_folder_button")
        lang_model_open_btn.setProperty("class", "action")
        lang_model_open_btn.setMinimumWidth(120)
        lang_model_open_btn.setToolTip("Open translation models folder in file explorer")
        lang_model_open_btn.clicked.connect(lambda: self._open_folder(get_app_path("system_data", "ai_models", "translation")))
        lang_model_layout.addWidget(lang_model_open_btn)
        
        layout.addLayout(lang_model_layout)
        
        # Translation models description
        lang_model_desc = QLabel("      Translation models (MarianMT, NLLB, M2M-100, mBART)")
        lang_model_desc.setStyleSheet("color: #888888; font-size: 8pt; margin-bottom: 5px; margin-left: 40px;")
        layout.addWidget(lang_model_desc)
        
        # OCR Models subdirectory
        ocr_model_layout = QHBoxLayout()
        ocr_model_layout.setSpacing(10)
        
        ocr_model_label = self._create_label("  ↳ OCR Models:", bold=False)
        ocr_model_label.setStyleSheet("color: #888888; font-size: 9pt; margin-left: 20px;")
        ocr_model_layout.addWidget(ocr_model_label)
        
        ocr_model_path_label = QLabel("system_data/ai_models/ocr/")
        ocr_model_path_label.setStyleSheet("color: #666666; font-size: 9pt;")
        ocr_model_layout.addWidget(ocr_model_path_label)
        ocr_model_layout.addStretch()
        
        ocr_model_open_btn = QPushButton()
        self.set_translatable_text(ocr_model_open_btn, "storage_open_folder_button_1")
        ocr_model_open_btn.setProperty("class", "action")
        ocr_model_open_btn.setMinimumWidth(120)
        ocr_model_open_btn.setToolTip("Open OCR models folder in file explorer")
        ocr_model_open_btn.clicked.connect(lambda: self._open_folder(get_app_path("system_data", "ai_models", "ocr")))
        ocr_model_layout.addWidget(ocr_model_open_btn)
        
        layout.addLayout(ocr_model_layout)
        
        # OCR models description
        ocr_model_desc = QLabel("      OCR models (EasyOCR, Tesseract, PaddleOCR, Manga OCR)")
        ocr_model_desc.setStyleSheet("color: #888888; font-size: 8pt; margin-bottom: 10px; margin-left: 40px;")
        layout.addWidget(ocr_model_desc)
        
        # Cache directory
        cache_layout = QHBoxLayout()
        cache_layout.setSpacing(10)
        
        cache_label = self._create_label("Cache Directory:", bold=True)
        cache_layout.addWidget(cache_label)
        
        self.cache_dir_edit = QLineEdit()
        self.cache_dir_edit.setText("system_data/cache")
        self.cache_dir_edit.setPlaceholderText("Path to cache directory")
        self.cache_dir_edit.textChanged.connect(self.on_change)
        cache_layout.addWidget(self.cache_dir_edit)
        
        cache_browse_btn = QPushButton()
        self.set_translatable_text(cache_browse_btn, "storage_browse_button_3")
        cache_browse_btn.setProperty("class", "action")
        cache_browse_btn.setMinimumWidth(80)
        cache_browse_btn.clicked.connect(lambda: self._browse_directory(self.cache_dir_edit, "Select Cache Directory"))
        cache_layout.addWidget(cache_browse_btn)
        
        cache_open_btn = QPushButton()
        self.set_translatable_text(cache_open_btn, "storage_open_button_4")
        cache_open_btn.setProperty("class", "action")
        cache_open_btn.setMinimumWidth(80)
        cache_open_btn.clicked.connect(lambda: self._open_folder(self.cache_dir_edit.text()))
        cache_layout.addWidget(cache_open_btn)
        
        layout.addLayout(cache_layout)
        
        # Cache directory description
        cache_desc = QLabel("Translation cache and temporary processing files")
        cache_desc.setStyleSheet("color: #666666; font-size: 9pt; margin-bottom: 10px;")
        layout.addWidget(cache_desc)
        
        # Dictionary directory
        dict_layout = QHBoxLayout()
        dict_layout.setSpacing(10)
        
        dict_label = self._create_label("Dictionary Directory:", bold=True)
        dict_layout.addWidget(dict_label)
        
        self.dict_dir_edit = QLineEdit()
        self.dict_dir_edit.setText("user_data/learned/translations")
        self.dict_dir_edit.setPlaceholderText("Path to dictionary directory")
        self.dict_dir_edit.textChanged.connect(self.on_change)
        dict_layout.addWidget(self.dict_dir_edit)
        
        dict_browse_btn = QPushButton()
        self.set_translatable_text(dict_browse_btn, "storage_browse_button_4")
        dict_browse_btn.setProperty("class", "action")
        dict_browse_btn.setMinimumWidth(80)
        dict_browse_btn.clicked.connect(lambda: self._browse_directory(self.dict_dir_edit, "Select Dictionary Directory"))
        dict_layout.addWidget(dict_browse_btn)
        
        dict_open_btn = QPushButton()
        self.set_translatable_text(dict_open_btn, "storage_open_button_5")
        dict_open_btn.setProperty("class", "action")
        dict_open_btn.setMinimumWidth(80)
        dict_open_btn.clicked.connect(lambda: self._open_folder(self.dict_dir_edit.text()))
        dict_layout.addWidget(dict_open_btn)
        
        layout.addLayout(dict_layout)
        
        # Dictionary directory description
        dict_desc = QLabel("Learned translations (learned_dictionary_*.json.gz)")
        dict_desc.setStyleSheet("color: #666666; font-size: 9pt; margin-bottom: 10px;")
        layout.addWidget(dict_desc)
        
        # Logs directory
        logs_layout = QHBoxLayout()
        logs_layout.setSpacing(10)
        
        logs_label = self._create_label("Logs Directory:", bold=True)
        logs_layout.addWidget(logs_label)
        
        self.logs_dir_edit = QLineEdit()
        self.logs_dir_edit.setText("system_data/logs")
        self.logs_dir_edit.setPlaceholderText("Path to logs directory")
        self.logs_dir_edit.textChanged.connect(self.on_change)
        logs_layout.addWidget(self.logs_dir_edit)
        
        logs_browse_btn = QPushButton()
        self.set_translatable_text(logs_browse_btn, "storage_browse_button_5")
        logs_browse_btn.setProperty("class", "action")
        logs_browse_btn.setMinimumWidth(80)
        logs_browse_btn.clicked.connect(lambda: self._browse_directory(self.logs_dir_edit, "Select Logs Directory"))
        logs_layout.addWidget(logs_browse_btn)
        
        logs_open_btn = QPushButton()
        self.set_translatable_text(logs_open_btn, "storage_open_button_6")
        logs_open_btn.setProperty("class", "action")
        logs_open_btn.setMinimumWidth(80)
        logs_open_btn.clicked.connect(lambda: self._open_folder(self.logs_dir_edit.text()))
        logs_layout.addWidget(logs_open_btn)
        
        layout.addLayout(logs_layout)
        
        # Logs directory description
        logs_desc = QLabel("Application logs and debug information")
        logs_desc.setStyleSheet("color: #666666; font-size: 9pt;")
        layout.addWidget(logs_desc)
        
        # Directory info note
        info_note = QLabel(
            "💡 All paths are relative to run.py (the application root). "
            "The directory structure separates user data from system data for better organization."
        )
        info_note.setWordWrap(True)
        info_note.setStyleSheet("color: #666666; font-size: 9pt; margin-top: 10px;")
        layout.addWidget(info_note)
        
        parent_layout.addWidget(group)
    
    def _create_retention_section(self, parent_layout):
        """Create data retention policy section."""
        group = QGroupBox()
        self.set_translatable_text(group, "storage_data_retention_policy_section")
        layout = QVBoxLayout(group)
        layout.setSpacing(12)
        layout.setContentsMargins(15, 20, 15, 15)
        
        # Retention period - using grid layout
        from PyQt6.QtWidgets import QGridLayout
        retention_grid = QGridLayout()
        retention_grid.setHorizontalSpacing(8)
        retention_grid.setVerticalSpacing(8)
        retention_grid.setContentsMargins(0, 5, 0, 5)
        retention_grid.setColumnStretch(2, 1)
        
        retention_label = self._create_label("Keep Data For:", bold=True)
        
        self.retention_spinbox = CustomSpinBox()
        self.retention_spinbox.setRange(1, 365)
        self.retention_spinbox.setValue(30)
        self.retention_spinbox.setSuffix("days")
        self.retention_spinbox.setSingleStep(1)
        self.retention_spinbox.setMinimumWidth(120)
        self.retention_spinbox.setSpecialValueText("1 day")
        self.retention_spinbox.valueChanged.connect(self.on_change)
        
        retention_grid.addWidget(retention_label, 0, 0)
        retention_grid.addWidget(self.retention_spinbox, 0, 1)
        layout.addLayout(retention_grid)
        
        # Retention description
        retention_desc = QLabel(
            "Automatically delete cached translations and temporary data older than the specified period. "
            "This helps manage disk space usage. Set to 1 day for minimal storage, or 365 days to keep data for a year."
        )
        retention_desc.setWordWrap(True)
        retention_desc.setStyleSheet("color: #666666; font-size: 9pt; margin-top: 5px;")
        layout.addWidget(retention_desc)
        
        parent_layout.addWidget(group)
    
    def _create_storage_usage_section(self, parent_layout):
        """Create storage usage display section."""
        group = QGroupBox()
        self.set_translatable_text(group, "storage_storage_usage_section")
        layout = QVBoxLayout(group)
        layout.setSpacing(12)
        layout.setContentsMargins(15, 20, 15, 15)
        
        # Cache usage progress bar
        usage_layout = QVBoxLayout()
        usage_layout.setSpacing(8)
        
        usage_label_layout = QHBoxLayout()
        cache_label = self._create_label("Cache Usage:", bold=True)
        usage_label_layout.addWidget(cache_label)
        
        self.cache_usage_label = QLabel("0 MB / 500 MB (0%)")
        self.cache_usage_label.setStyleSheet("font-size: 9pt; color: #666666;")
        usage_label_layout.addWidget(self.cache_usage_label)
        usage_label_layout.addStretch()
        
        usage_layout.addLayout(usage_label_layout)
        
        self.cache_usage_bar = QProgressBar()
        self.cache_usage_bar.setRange(0, 100)
        self.cache_usage_bar.setValue(0)
        self.cache_usage_bar.setTextVisible(False)
        self.cache_usage_bar.setMinimumHeight(20)
        usage_layout.addWidget(self.cache_usage_bar)
        
        layout.addLayout(usage_layout)
        
        # Refresh button
        refresh_layout = QHBoxLayout()
        refresh_btn = QPushButton()
        self.set_translatable_text(refresh_btn, "storage_refresh_usage_button")
        refresh_btn.setProperty("class", "action")
        refresh_btn.setMinimumWidth(120)
        refresh_btn.clicked.connect(self._calculate_storage_usage)
        refresh_layout.addWidget(refresh_btn)
        refresh_layout.addStretch()
        layout.addLayout(refresh_layout)
        
        # Storage info
        info_label = QLabel(
            "Storage usage is calculated based on the cache directory size. "
            "Click 'Refresh Usage' to update the current usage statistics."
        )
        info_label.setWordWrap(True)
        info_label.setStyleSheet("color: #666666; font-size: 9pt; margin-top: 5px;")
        layout.addWidget(info_label)
        
        parent_layout.addWidget(group)
        
        # Initial calculation
        self._calculate_storage_usage()
    
    def _on_cache_enabled_changed(self, state):
        """Handle cache enabled checkbox state change."""
        enabled = state == Qt.CheckState.Checked.value
        self.cache_size_spinbox.setEnabled(enabled)
        self.cache_dir_edit.setEnabled(enabled)
        self.clear_cache_btn.setEnabled(enabled)
        self.on_change()
    
    def _browse_directory(self, line_edit: QLineEdit, title: str):
        """Open directory browser dialog."""
        current_dir = line_edit.text() or "."
        directory = QFileDialog.getExistingDirectory(
            self,
            title,
            current_dir,
            QFileDialog.Option.ShowDirsOnly
        )
        
        if directory:
            line_edit.setText(directory)
            self.on_change()
    
    def _open_folder(self, folder_path: str):
        """Open folder in system file explorer."""
        import os
        import subprocess
        import platform
        
        try:
            # Expand relative paths
            if not os.path.isabs(folder_path):
                folder_path = os.path.abspath(folder_path)
            
            # Create folder if it doesn't exist
            if not os.path.exists(folder_path):
                os.makedirs(folder_path, exist_ok=True)
                print(f"[INFO] Created folder: {folder_path}")
            
            # Open folder in file explorer
            system = platform.system()
            if system == "Windows":
                os.startfile(folder_path)
            elif system == "Darwin":  # macOS
                subprocess.run(["open", folder_path])
            else:  # Linux
                subprocess.run(["xdg-open", folder_path])
            
            print(f"[INFO] Opened folder: {folder_path}")
            
        except Exception as e:
            print(f"[ERROR] Failed to open folder: {e}")
            from PyQt6.QtWidgets import QMessageBox
            QMessageBox.warning(
                self,
                "Open Folder Failed",
                f"Could not open folder:\n{folder_path}\n\nError: {str(e)}"
            )
    
    def clear_cache(self) -> bool:
        """
        Clear the cache directory after confirmation.
        
        Returns:
            True if cache was cleared successfully, False otherwise
        """
        try:
            cache_path = self.cache_dir_edit.text().strip()
            
            # Validate cache directory using QFileInfo
            file_info = QFileInfo(cache_path)
            
            if not file_info.exists():
                QMessageBox.information(
                    self,
                    "Cache Empty",
                    f"Cache directory does not exist:\n{cache_path}\n\nNothing to clear."
                )
                return False
            
            if not file_info.isDir():
                QMessageBox.warning(
                    self,
                    "Invalid Path",
                    f"Cache path is not a directory:\n{cache_path}"
                )
                return False
            
            # Get current cache size before clearing
            size_mb, file_count = self.calculate_cache_size()
            
            if file_count == 0:
                QMessageBox.information(
                    self,
                    "Cache Empty",
                    "Cache directory is already empty."
                )
                return False
            
            # Show confirmation dialog with size information
            reply = QMessageBox.warning(
                self,
                "Clear Cache",
                f"Are you sure you want to clear the cache?\n\n"
                f"Current cache size: {size_mb:.1f} MB ({file_count} files)\n"
                f"Location: {cache_path}\n\n"
                f"This will delete all cached translations and cannot be undone.\n"
                f"The application may be slower until the cache is rebuilt.",
                QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
                QMessageBox.StandardButton.No
            )
            
            if reply != QMessageBox.StandardButton.Yes:
                return False
            
            # Delete cache contents
            cache_dir = Path(cache_path)
            deleted_count = 0
            failed_count = 0
            
            for item in cache_dir.iterdir():
                try:
                    if item.is_file():
                        item.unlink()
                        deleted_count += 1
                    elif item.is_dir():
                        shutil.rmtree(item)
                        deleted_count += 1
                except Exception as e:
                    print(f"[WARNING] Failed to delete {item}: {e}")
                    failed_count += 1
            
            # Update storage usage
            self._calculate_storage_usage()
            
            # Show success message
            if failed_count > 0:
                QMessageBox.warning(
                    self,
                    "Cache Partially Cleared",
                    f"Cache partially cleared!\n\n"
                    f"Deleted: {deleted_count} items\n"
                    f"Failed: {failed_count} items\n"
                    f"Location: {cache_path}\n\n"
                    f"Some files could not be deleted. They may be in use."
                )
            else:
                QMessageBox.information(
                    self,
                    "Cache Cleared",
                    f"Successfully cleared cache!\n\n"
                    f"Deleted {deleted_count} items ({size_mb:.1f} MB)\n"
                    f"Location: {cache_path}"
                )
            
            print(f"[INFO] Cache cleared: {deleted_count} items deleted, {failed_count} failed from {cache_path}")
            return True
            
        except Exception as e:
            QMessageBox.critical(
                self,
                "Clear Failed",
                f"Failed to clear cache:\n\n{str(e)}"
            )
            print(f"[ERROR] Failed to clear cache: {e}")
            import traceback
            traceback.print_exc()
            return False
    
    def _clear_cache(self):
        """Internal method to handle clear cache button click - clears translation cache plugin."""
        # Clear the translation_cache plugin (in-memory cache)
        if hasattr(self, 'pipeline') and self.pipeline:
            try:
                # Clear translation_cache plugin
                if hasattr(self.pipeline, 'translation_cache') and self.pipeline.translation_cache:
                    print("[CACHE CLEAR] Clearing translation_cache plugin...")
                    self.pipeline.translation_cache.clear()
                    print("[CACHE CLEAR] ✓ Translation cache plugin cleared")
                
                # Clear cache_manager
                if hasattr(self.pipeline, 'cache_manager') and self.pipeline.cache_manager:
                    print("[CACHE CLEAR] Clearing cache_manager...")
                    self.pipeline.cache_manager.clear_all(clear_dictionary=False)
                    print("[CACHE CLEAR] ✓ Cache manager cleared")
                
                QMessageBox.information(
                    self,
                    "Cache Cleared",
                    "✅ Translation cache cleared successfully!\n\n"
                    "All cached translations have been removed."
                )
            except Exception as e:
                print(f"[CACHE CLEAR] Error: {e}")
                import traceback
                traceback.print_exc()
                QMessageBox.warning(
                    self,
                    "Clear Failed",
                    f"Failed to clear translation cache:\n\n{str(e)}"
                )
        else:
            # Fallback to clearing cache directory
            self.clear_cache()
    
    def _clear_all_caches(self):
        """Clear all caches including Python bytecode, translation cache, and temp files."""
        try:
            # Show comprehensive warning
            reply = QMessageBox.warning(
                self,
                "Clear All Caches",
                "⚠️ This will clear ALL caches:\n\n"
                "• Translation cache\n"
                "• Python bytecode (__pycache__/*.pyc)\n"
                "• Temporary files\n"
                "• Plugin caches\n\n"
                "This is useful for troubleshooting but will:\n"
                "• Make the app slower on next startup\n"
                "• Require re-downloading some data\n"
                "• Cannot be undone\n\n"
                "Are you sure you want to continue?",
                QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
                QMessageBox.StandardButton.No
            )
            
            if reply != QMessageBox.StandardButton.Yes:
                return
            
            from PyQt6.QtWidgets import QProgressDialog
            from PyQt6.QtCore import Qt
            
            # Create progress dialog
            progress = QProgressDialog("Clearing all caches...", "Cancel", 0, 100, self)
            progress.setWindowTitle("Clearing Caches")
            progress.setWindowModality(Qt.WindowModality.WindowModal)
            progress.setMinimumDuration(0)
            progress.setValue(0)
            
            deleted_count = 0
            failed_count = 0
            
            # 1. Clear translation cache plugin (10%)
            progress.setLabelText("Clearing translation cache plugin...")
            progress.setValue(5)
            
            if hasattr(self, 'pipeline') and self.pipeline:
                try:
                    # Clear translation_cache plugin
                    if hasattr(self.pipeline, 'translation_cache') and self.pipeline.translation_cache:
                        print("[CACHE CLEAR] Clearing translation_cache plugin...")
                        self.pipeline.translation_cache.clear()
                        print("[CACHE CLEAR] ✓ Translation cache plugin cleared")
                        deleted_count += 1
                    
                    # Clear cache_manager
                    if hasattr(self.pipeline, 'cache_manager') and self.pipeline.cache_manager:
                        print("[CACHE CLEAR] Clearing cache_manager...")
                        self.pipeline.cache_manager.clear_all(clear_dictionary=False)
                        print("[CACHE CLEAR] ✓ Cache manager cleared")
                        deleted_count += 1
                except Exception as e:
                    print(f"[CACHE CLEAR] Error clearing plugin caches: {e}")
                    failed_count += 1
            
            progress.setValue(15)
            
            # 2. Clear cache directory (15%)
            progress.setLabelText("Clearing cache directory...")
            
            cache_path = Path(self.cache_dir_edit.text().strip())
            if cache_path.exists() and cache_path.is_dir():
                for item in cache_path.iterdir():
                    try:
                        if item.is_file():
                            item.unlink()
                            deleted_count += 1
                        elif item.is_dir():
                            shutil.rmtree(item)
                            deleted_count += 1
                    except Exception as e:
                        print(f"[WARNING] Failed to delete {item}: {e}")
                        failed_count += 1
            
            progress.setValue(30)
            
            # 2. Clear Python bytecode (40%)
            progress.setLabelText("Clearing Python bytecode cache...")
            
            # Get the application root directory
            app_root = Path(__file__).parent.parent.parent
            
            # Find and delete all __pycache__ directories
            for pycache_dir in app_root.rglob('__pycache__'):
                try:
                    shutil.rmtree(pycache_dir)
                    deleted_count += 1
                    print(f"[INFO] Deleted {pycache_dir}")
                except Exception as e:
                    print(f"[WARNING] Failed to delete {pycache_dir}: {e}")
                    failed_count += 1
            
            # Delete .pyc files
            for pyc_file in app_root.rglob('*.pyc'):
                try:
                    pyc_file.unlink()
                    deleted_count += 1
                except Exception as e:
                    print(f"[WARNING] Failed to delete {pyc_file}: {e}")
                    failed_count += 1
            
            progress.setValue(60)
            
            # 3. Clear temp directory (20%)
            progress.setLabelText("Clearing temporary files...")
            
            temp_path = app_root / 'temp'
            if temp_path.exists() and temp_path.is_dir():
                for item in temp_path.iterdir():
                    try:
                        if item.is_file():
                            item.unlink()
                            deleted_count += 1
                        elif item.is_dir():
                            shutil.rmtree(item)
                            deleted_count += 1
                    except Exception as e:
                        print(f"[WARNING] Failed to delete {item}: {e}")
                        failed_count += 1
            
            progress.setValue(80)
            
            # 4. Clear logs directory (optional - only old logs)
            progress.setLabelText("Clearing old log files...")
            
            logs_path = app_root / 'logs'
            if logs_path.exists() and logs_path.is_dir():
                import time
                current_time = time.time()
                # Delete logs older than 7 days
                for log_file in logs_path.glob('*.log'):
                    try:
                        if log_file.is_file():
                            file_age = current_time - log_file.stat().st_mtime
                            if file_age > (7 * 24 * 60 * 60):  # 7 days in seconds
                                log_file.unlink()
                                deleted_count += 1
                    except Exception as e:
                        print(f"[WARNING] Failed to delete {log_file}: {e}")
                        failed_count += 1
            
            progress.setValue(100)
            progress.close()
            
            # Show results
            QMessageBox.information(
                self,
                "Caches Cleared",
                f"✅ All caches cleared successfully!\n\n"
                f"Deleted: {deleted_count} items\n"
                f"Failed: {failed_count} items\n\n"
                f"The application will be slower on next startup\n"
                f"as caches are rebuilt."
            )
            
            print(f"[INFO] All caches cleared: {deleted_count} items deleted, {failed_count} failed")
            
        except Exception as e:
            QMessageBox.critical(
                self,
                "Clear Failed",
                f"Failed to clear all caches:\n\n{str(e)}"
            )
            print(f"[ERROR] Failed to clear all caches: {e}")
            import traceback
            traceback.print_exc()
    
    def calculate_cache_size(self) -> tuple[float, int]:
        """
        Calculate the current cache size.
        
        Returns:
            Tuple of (size_in_mb, file_count)
        """
        try:
            cache_path = self.cache_dir_edit.text().strip()
            if not cache_path:
                return (0.0, 0)
            
            # Use QFileInfo to check if directory exists
            file_info = QFileInfo(cache_path)
            if not file_info.exists() or not file_info.isDir():
                return (0.0, 0)
            
            cache_dir = Path(cache_path)
            
            # Calculate total size in bytes and count files
            total_size = 0
            file_count = 0
            
            for item in cache_dir.rglob('*'):
                if item.is_file():
                    try:
                        total_size += item.stat().st_size
                        file_count += 1
                    except (OSError, PermissionError):
                        # Skip files we can't access
                        pass
            
            # Convert to MB
            size_mb = total_size / (1024 * 1024)
            
            return (size_mb, file_count)
            
        except Exception as e:
            print(f"[WARNING] Failed to calculate cache size: {e}")
            return (0.0, 0)
    
    def _calculate_storage_usage(self):
        """Calculate and display current storage usage."""
        try:
            # Get cache size
            size_mb, file_count = self.calculate_cache_size()
            limit_mb = self.cache_size_spinbox.value()
            
            # Calculate percentage
            percentage = min(int((size_mb / limit_mb) * 100), 100) if limit_mb > 0 else 0
            
            # Update UI
            self.cache_usage_label.setText(f"{size_mb:.1f} MB / {limit_mb} MB ({percentage}%)")
            self.cache_usage_bar.setValue(percentage)
            
            # Change color based on usage
            if percentage >= 90:
                self.cache_usage_bar.setStyleSheet("QProgressBar::chunk { background-color: #F44336; }")
            elif percentage >= 75:
                self.cache_usage_bar.setStyleSheet("QProgressBar::chunk { background-color: #FF9800; }")
            else:
                self.cache_usage_bar.setStyleSheet("QProgressBar::chunk { background-color: #4CAF50; }")
            
            # Removed duplicate debug log - already shown in UI
            
        except Exception as e:
            print(f"[WARNING] Failed to calculate storage usage: {e}")
            self.cache_usage_label.setText("Error calculating usage")
            self.cache_usage_bar.setValue(0)
    
    def _export_dictionary(self):
        """Export dictionary as wordbook (NEW SYSTEM)."""
        try:
            file_path, _ = QFileDialog.getSaveFileName(
                self,
                "Export Dictionary Wordbook",
                "learned_wordbook.txt",
                "Text Files (*.txt);;All Files (*.*)"
            )
            
            if file_path:
                # Use the new translation layer export method
                if self.pipeline and hasattr(self.pipeline.translation_layer, 'export_dictionary_wordbook'):
                    # Get current language pair from config
                    source_lang = self.config_manager.get_setting('translation.source_language', 'en') if self.config_manager else 'en'
                    target_lang = self.config_manager.get_setting('translation.target_language', 'de') if self.config_manager else 'de'
                    
                    result_path = self.pipeline.translation_layer.export_dictionary_wordbook(
                        file_path,
                        source_lang,
                        target_lang
                    )
                    
                    if result_path:
                        QMessageBox.information(
                            self,
                            "Export Successful",
                            f"Dictionary wordbook exported successfully!\n\n{result_path}"
                        )
                    else:
                        QMessageBox.warning(
                            self,
                            "Export Failed",
                            "Failed to export dictionary. Check if dictionary has entries."
                        )
                else:
                    QMessageBox.warning(
                        self,
                        "Not Available",
                        "Translation system not initialized."
                    )
        
        except Exception as e:
            QMessageBox.critical(
                self,
                "Export Failed",
                f"Failed to export dictionary:\n\n{e}"
            )
    
    def _import_dictionary(self):
        """Import dictionary from file."""
        try:
            file_path, _ = QFileDialog.getOpenFileName(
                self,
                "Import Dictionary",
                "",
                "JSON Files (*.json *.json.gz);;All Files (*.*)"
            )
            
            if file_path:
                # Dictionary import is now available in the Smart Dictionary tab
                QMessageBox.information(
                    self,
                    "Dictionary Import",
                    "Dictionary import functionality has been moved to the Smart Dictionary tab.\n\n"
                    "Go to Settings → Smart Dictionary to import dictionaries."
                )
        
        except Exception as e:
            QMessageBox.critical(
                self,
                "Import Failed",
                f"Failed to import dictionary:\n\n{e}"
            )
    
    def _clear_dictionary(self):
        """Clear all dictionary entries (NEW SYSTEM)."""
        try:
            reply = QMessageBox.question(
                self,
                "Clear Dictionary",
                "Are you sure you want to clear all learned translations?\n\n"
                "This action cannot be undone.",
                QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
                QMessageBox.StandardButton.No
            )
            
            if reply == QMessageBox.StandardButton.Yes:
                # Use the new dictionary engine
                if self.pipeline:
                    dict_engine = self.pipeline.translation_layer._engine_registry.get_engine('dictionary')
                    if dict_engine and hasattr(dict_engine._dictionary, '_dictionaries'):
                        # Get current language pair
                        source_lang = self.config_manager.get_setting('translation.source_language', 'en') if self.config_manager else 'en'
                        target_lang = self.config_manager.get_setting('translation.target_language', 'de') if self.config_manager else 'de'
                        lang_pair = (source_lang, target_lang)
                        
                        if lang_pair in dict_engine._dictionary._dictionaries:
                            entry_count = len(dict_engine._dictionary._dictionaries[lang_pair])
                            # Clear the dictionary
                            dict_engine._dictionary._dictionaries[lang_pair] = {}
                            
                            # Save the empty dictionary
                            from pathlib import Path
                            dict_paths = [
                                Path(f"dev/dictionary/learned_dictionary_{source_lang}_{target_lang}.json.gz"),
                                Path(f"dictionary/learned_dictionary_{source_lang}_{target_lang}.json.gz")
                            ]
                            
                            dict_path = None
                            for path in dict_paths:
                                if path.exists():
                                    dict_path = path
                                    break
                            
                            if dict_path:
                                dict_engine._dictionary.save_dictionary(
                                    str(dict_path),
                                    source_lang,
                                    target_lang
                                )
                            
                            QMessageBox.information(
                                self,
                                "Dictionary Cleared",
                                f"Successfully cleared {entry_count} dictionary entries."
                            )
                        else:
                            QMessageBox.information(
                                self,
                                "Dictionary Empty",
                                "Dictionary is already empty."
                            )
                    else:
                        QMessageBox.warning(
                            self,
                            "Not Available",
                            "Dictionary engine not initialized."
                        )
                else:
                    QMessageBox.warning(
                        self,
                        "Not Available",
                        "Translation system not initialized."
                    )
                
                # Refresh stats (if pipeline is available)
                if hasattr(self, '_refresh_all_dictionaries'):
                    self._refresh_all_dictionaries()
        
        except Exception as e:
            QMessageBox.critical(
                self,
                "Clear Failed",
                f"Failed to clear dictionary:\n\n{e}"
            )
    
    def _get_language_name(self, code: str) -> str:
        """Convert language code to full name."""
        language_names = {
            'en': 'English', 'de': 'German', 'ja': 'Japanese',
            'es': 'Spanish', 'fr': 'French', 'zh': 'Chinese',
            'zh-CN': 'Chinese (Simplified)', 'zh-TW': 'Chinese (Traditional)',
            'ko': 'Korean', 'ru': 'Russian', 'it': 'Italian',
            'pt': 'Portuguese', 'ar': 'Arabic', 'hi': 'Hindi',
            'nl': 'Dutch', 'pl': 'Polish', 'tr': 'Turkish'
        }
        return language_names.get(code, code.upper())
    
    def _populate_language_pair_dropdown(self):
        """Populate dropdown with available language pairs."""
        self.language_pair_combo.clear()
        
        if not self.pipeline:
            print("[STORAGE TAB] Pipeline not initialized")
            self.language_pair_combo.addItem("Pipeline not initialized", None)
            return
        
        try:
            # Get current language pair from config
            if self.config_manager:
                current_source = self.config_manager.get_setting('translation.source_language', 'en')
                current_target = self.config_manager.get_setting('translation.target_language', 'de')
            else:
                current_source, current_target = 'en', 'de'
            
            print(f"[STORAGE TAB] Current language pair: {current_source} → {current_target}")
            
            # Get all available language pairs by scanning dictionary folder
            from app.translation.smart_dictionary import SmartDictionary
            from pathlib import Path
            
            # Prefer dev/dictionary if it exists, otherwise use dictionary/
            dict_folder = Path("dev/dictionary") if Path("dev/dictionary").exists() else Path("dictionary")
            
            language_pairs = []
            
            if dict_folder.exists():
                for dict_file in dict_folder.glob("learned_dictionary_*_*.json.gz"):
                    try:
                        filename = dict_file.stem
                        if filename.endswith('.json'):
                            filename = filename[:-5]
                        
                        name_parts = filename.split('_')
                        if len(name_parts) >= 4:
                            source_lang = name_parts[2]
                            target_lang = name_parts[3]
                            
                            smart_dict = SmartDictionary(dictionary_path=str(dict_file))
                            stats = smart_dict.get_stats(source_lang, target_lang)
                            entry_count = stats.total_entries
                            
                            # Include file path in the tuple so we can distinguish multiple files
                            language_pairs.append((source_lang, target_lang, str(dict_file), entry_count))
                    except Exception as e:
                        print(f"[STORAGE TAB] Failed to parse {dict_file}: {e}")
            
            print(f"[STORAGE TAB] Found {len(language_pairs)} language pairs: {language_pairs}")
            
            # Group by language pair to detect duplicates
            from collections import defaultdict
            pairs_by_lang = defaultdict(list)
            for source, target, path, count in language_pairs:
                pairs_by_lang[(source, target)].append((path, count))
            
            # Add current pair first (even if no dictionary yet)
            current_found = False
            if (current_source, current_target) in pairs_by_lang:
                files = pairs_by_lang[(current_source, current_target)]
                if len(files) == 1:
                    # Single file - show simple format
                    path, count = files[0]
                    pair_text = f"{self._get_language_name(current_source)} → {self._get_language_name(current_target)} ({count:,} entries)"
                    self.language_pair_combo.addItem(pair_text, (current_source, current_target, path))
                else:
                    # Multiple files - show filename to distinguish
                    for path, count in files:
                        filename = Path(path).name
                        pair_text = f"{self._get_language_name(current_source)} → {self._get_language_name(current_target)} ({count:,} entries) - {filename}"
                        self.language_pair_combo.addItem(pair_text, (current_source, current_target, path))
                current_found = True
            
            # If current pair has no dictionary yet, add it anyway
            if not current_found:
                current_pair_text = f"{self._get_language_name(current_source)} → {self._get_language_name(current_target)} (no dictionary yet)"
                self.language_pair_combo.addItem(current_pair_text, (current_source, current_target, None))
            
            # Add other available pairs
            for (source, target), files in pairs_by_lang.items():
                if source != current_source or target != current_target:
                    if len(files) == 1:
                        # Single file - show simple format
                        path, count = files[0]
                        pair_text = f"{self._get_language_name(source)} → {self._get_language_name(target)} ({count:,} entries)"
                        self.language_pair_combo.addItem(pair_text, (source, target, path))
                    else:
                        # Multiple files - show filename to distinguish
                        for path, count in files:
                            filename = Path(path).name
                            pair_text = f"{self._get_language_name(source)} → {self._get_language_name(target)} ({count:,} entries) - {filename}"
                            self.language_pair_combo.addItem(pair_text, (source, target, path))
            
            # Set current selection
            self.language_pair_combo.setCurrentIndex(0)
            
        except Exception as e:
            # Silently handle - show friendly message instead of error
            self.language_pair_combo.addItem("Dictionary feature not available", None)
    
    def _populate_language_pair_list(self):
        """Populate table of all available language pairs (Excel-like)."""
        self.language_pair_table.setRowCount(0)
        
        try:
            # Scan dictionary directory for all dictionary files
            from pathlib import Path
            import gzip
            import json
            
            dict_dir = Path("dev/dictionary") if Path("dev/dictionary").exists() else Path("dictionary")
            
            if not dict_dir.exists():
                return
            
            # Get current language pair if available
            current_source, current_target = None, None
            if self.config_manager:
                current_source = self.config_manager.get_setting('translation.source_language', 'en')
                current_target = self.config_manager.get_setting('translation.target_language', 'de')
            
            row = 0
            for dict_file in dict_dir.glob("learned_dictionary_*.json.gz"):
                try:
                    # Extract language pair from filename
                    filename = dict_file.stem
                    if filename.endswith('.json'):
                        filename = filename[:-5]
                    
                    name_parts = filename.split('_')
                    if len(name_parts) >= 4:
                        source_lang = name_parts[2]
                        target_lang = name_parts[3]
                        
                        # Load dictionary to get entry count
                        with gzip.open(dict_file, 'rt', encoding='utf-8') as f:
                            data = json.load(f)
                        
                        # Extract translations
                        if isinstance(data, dict) and 'translations' in data:
                            dictionary = data['translations']
                        else:
                            dictionary = data
                        
                        entry_count = len(dictionary)
                        
                        # Get file size
                        file_size_mb = dict_file.stat().st_size / (1024 * 1024)
                        size_str = f"{file_size_mb:.2f} MB" if file_size_mb >= 0.01 else f"{dict_file.stat().st_size / 1024:.1f} KB"
                        
                        # Add row to table
                        self.language_pair_table.insertRow(row)
                        
                        # Check if this is the current pair
                        is_current = (source_lang == current_source and target_lang == current_target)
                        
                        # Column 0: Active (checkmark)
                        active_item = QTableWidgetItem("✓" if is_current else "")
                        active_item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
                        self.language_pair_table.setItem(row, 0, active_item)
                        
                        # Column 1: Name (filename)
                        name_item = QTableWidgetItem(dict_file.name)
                        self.language_pair_table.setItem(row, 1, name_item)
                        
                        # Column 2: Language Pair
                        pair_item = QTableWidgetItem(f"{self._get_language_name(source_lang)} → {self._get_language_name(target_lang)}")
                        self.language_pair_table.setItem(row, 2, pair_item)
                        
                        # Column 3: Entries
                        entries_item = QTableWidgetItem(f"{entry_count:,}")
                        entries_item.setTextAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)
                        self.language_pair_table.setItem(row, 3, entries_item)
                        
                        # Column 4: Size
                        size_item = QTableWidgetItem(size_str)
                        size_item.setTextAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)
                        self.language_pair_table.setItem(row, 4, size_item)
                        
                        # Highlight current row
                        if is_current:
                            for col in range(5):
                                item = self.language_pair_table.item(row, col)
                                if item:
                                    item.setBackground(QColor(70, 130, 180, 50))  # Light blue highlight
                        
                        row += 1
                        
                except Exception as e:
                    print(f"[STORAGE TAB] Failed to parse {dict_file}: {e}")
                    continue
            
            # If no dictionaries found, show a message
            if row == 0:
                self.language_pair_table.insertRow(0)
                no_dict_item = QTableWidgetItem("No dictionaries found")
                no_dict_item.setForeground(QColor(150, 150, 150))
                self.language_pair_table.setItem(0, 0, no_dict_item)
                self.language_pair_table.setSpan(0, 0, 1, 5)  # Span across all 5 columns
                
        except Exception as e:
            print(f"[STORAGE TAB] Error populating language pair table: {e}")
            import traceback
            traceback.print_exc()
    
    def _on_language_pair_changed(self, index):
        """Handle language pair selection change in dropdown."""
        if index < 0:
            return
        
        pair_data = self.language_pair_combo.itemData(index)
        if not pair_data or not self.pipeline:
            return
        
        try:
            # Unpack data - now includes optional file path
            if len(pair_data) == 3:
                source, target, file_path = pair_data
            else:
                source, target = pair_data
                file_path = None
            
            # Switch to selected language pair
            self.pipeline.translation_layer.set_language_pair(source, target)
            
            # Store selected file path for operations on this specific dictionary
            self._selected_dict_path = file_path
            
            # If a specific file was selected, reload it in the translation layer
            if file_path:
                print(f"[STORAGE TAB] Reloading dictionary from: {file_path}")
                self.pipeline.translation_layer.reload_dictionary_from_file(file_path, source, target)
            
            # Refresh statistics display
            self._refresh_selected_dictionary_stats()
            
            # Refresh list to update checkmark
            self._populate_language_pair_list()
            
        except Exception as e:
            QMessageBox.warning(self, "Error", f"Failed to switch language pair: {e}")
    
    def _refresh_selected_dictionary_stats(self):
        """Refresh dictionary statistics for selected pair (NEW SYSTEM - dict_engine)."""
        if not self.pipeline:
            self.dict_entries_label.setText("Pipeline not initialized")
            return
        
        try:
            # Get current language pair from dropdown
            current_text = self.language_pair_combo.currentText()
            if not current_text or current_text == "Dictionary feature not available":
                self.dict_entries_label.setText("0")
                self.dict_usage_label.setText("0 lookups")
                self.dict_avg_usage_label.setText("0.0 times per entry")
                self.dict_hit_rate_label.setText("N/A")
                self.dict_file_size_label.setText("No dictionary file yet")
                self._update_most_used_list([])
                return
            
            # Parse language pair (format: "English → German (1 entries)")
            parts = current_text.split(" → ")
            if len(parts) != 2:
                return
            
            # Map language names to codes
            lang_map = {
                'English': 'en', 'German': 'de', 'Spanish': 'es', 'French': 'fr',
                'Japanese': 'ja', 'Korean': 'ko', 'Chinese': 'zh', 'Russian': 'ru'
            }
            source_lang = lang_map.get(parts[0].strip(), 'en')
            # Extract target language (remove entry count if present)
            target_part = parts[1].strip()
            if '(' in target_part:
                target_part = target_part.split('(')[0].strip()
            target_lang = lang_map.get(target_part, 'de')
            
            # Load dictionary directly from file (NEW SYSTEM - matches dictionary editor)
            import gzip
            import json
            
            # Find dictionary file
            dict_paths = [
                Path(f"dev/dictionary/learned_dictionary_{source_lang}_{target_lang}.json.gz"),
                Path(f"dictionary/learned_dictionary_{source_lang}_{target_lang}.json.gz")
            ]
            
            dict_path = None
            for path in dict_paths:
                if path.exists():
                    dict_path = path
                    break
            
            if not dict_path:
                self.dict_entries_label.setText("0")
                self.dict_usage_label.setText("0 lookups")
                self.dict_avg_usage_label.setText("0.0 times per entry")
                self.dict_hit_rate_label.setText("N/A")
                self.dict_file_size_label.setText("No dictionary file yet")
                self._update_most_used_list([])
                return
            
            # Load dictionary from file
            with gzip.open(dict_path, 'rt', encoding='utf-8') as f:
                data = json.load(f)
            
            # Extract translations from the NEW file format
            # Format: {"version": "1.0", "translations": {...}, ...}
            if isinstance(data, dict) and 'translations' in data:
                dictionary = data['translations']
            else:
                # Old format: direct dictionary
                dictionary = data
            
            total_entries = len(dictionary)
            print(f"[STORAGE TAB] Dictionary stats for {source_lang}→{target_lang}: {total_entries} entries from {dict_path}")
            
            # Calculate statistics
            total_usage = 0
            most_used = []
            for key, entry_data in dictionary.items():
                if isinstance(entry_data, dict):
                    usage_count = entry_data.get('usage_count', 0)
                    total_usage += usage_count
                    
                    # Key is the source text directly (no prefix in new format)
                    source_text = key
                    
                    most_used.append({
                        'original': source_text,
                        'translation': entry_data.get('translation', ''),
                        'usage_count': usage_count
                    })
                else:
                    # Old format: entry_data is just a string
                    most_used.append({
                        'original': key,
                        'translation': str(entry_data),
                        'usage_count': 0
                    })
            
            # Sort by usage count
            most_used.sort(key=lambda x: x['usage_count'], reverse=True)
            
            # Update labels
            self.dict_entries_label.setText(f"{total_entries:,}")
            self.dict_usage_label.setText(f"{total_usage:,} lookups")
            avg_usage = total_usage / total_entries if total_entries > 0 else 0
            self.dict_avg_usage_label.setText(f"{avg_usage:.1f} times per entry")
            self.dict_hit_rate_label.setText("N/A")  # Not tracked yet
            
            # File size (already have dict_path from above)
            file_size_mb = dict_path.stat().st_size / (1024 * 1024)
            self.dict_file_size_label.setText(f"{file_size_mb:.2f} MB (compressed)")
            
            # Update most used list
            self._update_most_used_list(most_used[:10])
            
            print(f"[STORAGE TAB] Stats updated: {total_entries} entries, {total_usage} total usage, {len(most_used)} unique entries")
            
        except Exception as e:
            # Show error in console for debugging
            print(f"[STORAGE TAB ERROR] Failed to load dictionary stats: {e}")
            import traceback
            traceback.print_exc()
            
            # Show empty stats in UI
            self.dict_entries_label.setText("0")
            self.dict_usage_label.setText("0 lookups")
            self.dict_avg_usage_label.setText("0.0 times per entry")
            self.dict_hit_rate_label.setText("N/A")
            self.dict_file_size_label.setText("No dictionary file yet")
            self._update_most_used_list([])
    
    def _update_most_used_list(self, most_used):
        """Update the most used translations list."""
        self.most_used_list.clear()
        
        for i, entry in enumerate(most_used[:10], 1):
            original = entry.get('original', '')
            translation = entry.get('translation', '')
            usage_count = entry.get('usage_count', 0)
            
            item_text = f"{i}. {original} → {translation} ({usage_count} times)"
            self.most_used_list.addItem(item_text)
    
    def _export_selected_dictionary(self):
        """Export the selected language pair dictionary."""
        from PyQt6.QtWidgets import QFileDialog
        
        if not self.pipeline:
            QMessageBox.warning(self, "Pipeline Not Ready", "Translation pipeline is not initialized yet.")
            return
        
        try:
            source, target = self.pipeline.translation_layer.get_current_language_pair()
            source_name = self._get_language_name(source)
            target_name = self._get_language_name(target)
            
            # Default filename
            default_filename = f"learned_wordbook_{source}_{target}.txt"
            
            # Show file dialog
            file_path, _ = QFileDialog.getSaveFileName(
                self,
                f"Export Dictionary: {source_name} → {target_name}",
                default_filename,
                "Text Files (*.txt);;All Files (*.*)"
            )
            
            if not file_path:
                return
            
            # Export
            result_path = self.pipeline.translation_layer.export_dictionary_wordbook(file_path)
            
            if result_path:
                QMessageBox.information(
                    self,
                    "Export Successful",
                    f"Dictionary exported successfully!\n\n"
                    f"{source_name} → {target_name}\n"
                    f"Saved to: {result_path}"
                )
            else:
                QMessageBox.warning(self, "Export Failed", "Failed to export dictionary")
                
        except Exception as e:
            QMessageBox.critical(self, "Error", f"Export failed: {e}")
    
    def _export_specific_pair(self, source: str, target: str):
        """Export a specific language pair from the list."""
        from PyQt6.QtWidgets import QFileDialog
        
        if not self.pipeline:
            return
        
        # Remember original pair
        original_source, original_target = self.pipeline.translation_layer.get_current_language_pair()
        
        try:
            # Temporarily switch to target pair
            self.pipeline.translation_layer.set_language_pair(source, target)
            
            source_name = self._get_language_name(source)
            target_name = self._get_language_name(target)
            
            # Default filename
            default_filename = f"learned_wordbook_{source}_{target}.txt"
            
            # Show file dialog
            file_path, _ = QFileDialog.getSaveFileName(
                self,
                f"Export Dictionary: {source_name} → {target_name}",
                default_filename,
                "Text Files (*.txt);;All Files (*.*)"
            )
            
            if file_path:
                result_path = self.pipeline.translation_layer.export_dictionary_wordbook(file_path)
                if result_path:
                    QMessageBox.information(
                        self,
                        "Export Successful",
                        f"Dictionary exported!\n\n{source_name} → {target_name}\nSaved to: {result_path}"
                    )
        
        finally:
            # Switch back to original pair
            self.pipeline.translation_layer.set_language_pair(original_source, original_target)
            self._refresh_selected_dictionary_stats()
            self._populate_language_pair_dropdown()
    
    def _clear_selected_dictionary(self):
        """Clear the selected language pair dictionary."""
        if not self.pipeline:
            QMessageBox.warning(self, "Pipeline Not Ready", "Translation pipeline is not initialized yet.")
            return
        
        try:
            source, target = self.pipeline.translation_layer.get_current_language_pair()
            source_name = self._get_language_name(source)
            target_name = self._get_language_name(target)
            
            stats = self.pipeline.translation_layer.get_dictionary_stats()
            entry_count = stats.get('total_entries', 0)
            
            # Confirmation dialog
            reply = QMessageBox.question(
                self,
                "Clear Dictionary",
                f"Are you sure you want to clear the dictionary?\n\n"
                f"Language Pair: {source_name} → {target_name}\n"
                f"Entries to delete: {entry_count:,}\n\n"
                f"Other language pairs will not be affected.\n"
                f"This action cannot be undone!",
                QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
                QMessageBox.StandardButton.No
            )
            
            if reply == QMessageBox.StandardButton.Yes:
                self.pipeline.translation_layer.clear_dictionary()
                self._refresh_all_dictionaries()
                QMessageBox.information(
                    self,
                    "Dictionary Cleared",
                    f"Dictionary cleared for {source_name} → {target_name}"
                )
        
        except Exception as e:
            QMessageBox.critical(self, "Error", f"Failed to clear dictionary: {e}")
    
    def _open_dictionary_editor(self):
        """Open the dictionary editor dialog."""
        try:
            from ui.dialogs.dictionary_editor_dialog import DictionaryEditorDialog
            
            # Get translation layer from pipeline
            if not self.pipeline or not hasattr(self.pipeline, 'translation_layer'):
                QMessageBox.warning(
                    self,
                    "Pipeline Not Available",
                    "Translation pipeline is not initialized.\n\n"
                    "Please start the application first."
                )
                return
            
            # Create and show editor
            editor = DictionaryEditorDialog(
                translation_layer=self.pipeline.translation_layer,
                parent=self
            )
            editor.exec()
            
            # Refresh dictionary stats after editing
            self._refresh_all_dictionaries()
            
        except ImportError as e:
            QMessageBox.warning(
                self,
                "Feature Not Available",
                f"Dictionary editor is not available:\n{e}\n\n"
                f"Please ensure all components are properly installed."
            )
        except Exception as e:
            QMessageBox.critical(
                self,
                "Error",
                f"Failed to open dictionary editor:\n{e}"
            )
    
    def _create_example_dictionary(self):
        """Create an example English-German dictionary with sample translations."""
        try:
            import json
            import gzip
            from pathlib import Path
            from datetime import datetime
            
            # Confirm creation
            reply = QMessageBox.question(
                self,
                "Create Example Dictionary",
                "This will create an example English-German dictionary with 20 sample translations.\n\n"
                "The dictionary will be saved to:\n"
                "dictionary/learned_dictionary_en_de.json.gz\n\n"
                "If a dictionary already exists, it will be backed up first.\n\n"
                "Continue?",
                QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
                QMessageBox.StandardButton.Yes
            )
            
            if reply != QMessageBox.StandardButton.Yes:
                return
            
            # Create example dictionary data
            example_entries = {
                "Hello": {
                    "translation": "Hallo",
                    "usage_count": 15,
                    "confidence": 0.95,
                    "last_used": datetime.now().isoformat()
                },
                "Good morning": {
                    "translation": "Guten Morgen",
                    "usage_count": 12,
                    "confidence": 0.98,
                    "last_used": datetime.now().isoformat()
                },
                "Thank you": {
                    "translation": "Danke",
                    "usage_count": 25,
                    "confidence": 0.99,
                    "last_used": datetime.now().isoformat()
                },
                "Please": {
                    "translation": "Bitte",
                    "usage_count": 18,
                    "confidence": 0.97,
                    "last_used": datetime.now().isoformat()
                },
                "Yes": {
                    "translation": "Ja",
                    "usage_count": 30,
                    "confidence": 1.0,
                    "last_used": datetime.now().isoformat()
                },
                "No": {
                    "translation": "Nein",
                    "usage_count": 28,
                    "confidence": 1.0,
                    "last_used": datetime.now().isoformat()
                },
                "Goodbye": {
                    "translation": "Auf Wiedersehen",
                    "usage_count": 10,
                    "confidence": 0.96,
                    "last_used": datetime.now().isoformat()
                },
                "How are you?": {
                    "translation": "Wie geht es dir?",
                    "usage_count": 8,
                    "confidence": 0.94,
                    "last_used": datetime.now().isoformat()
                },
                "I'm fine": {
                    "translation": "Mir geht es gut",
                    "usage_count": 7,
                    "confidence": 0.93,
                    "last_used": datetime.now().isoformat()
                },
                "Welcome": {
                    "translation": "Willkommen",
                    "usage_count": 14,
                    "confidence": 0.98,
                    "last_used": datetime.now().isoformat()
                },
                "Excuse me": {
                    "translation": "Entschuldigung",
                    "usage_count": 11,
                    "confidence": 0.95,
                    "last_used": datetime.now().isoformat()
                },
                "I don't understand": {
                    "translation": "Ich verstehe nicht",
                    "usage_count": 6,
                    "confidence": 0.92,
                    "last_used": datetime.now().isoformat()
                },
                "Help": {
                    "translation": "Hilfe",
                    "usage_count": 9,
                    "confidence": 0.99,
                    "last_used": datetime.now().isoformat()
                },
                "Water": {
                    "translation": "Wasser",
                    "usage_count": 13,
                    "confidence": 1.0,
                    "last_used": datetime.now().isoformat()
                },
                "Food": {
                    "translation": "Essen",
                    "usage_count": 12,
                    "confidence": 0.98,
                    "last_used": datetime.now().isoformat()
                },
                "Where is...?": {
                    "translation": "Wo ist...?",
                    "usage_count": 10,
                    "confidence": 0.96,
                    "last_used": datetime.now().isoformat()
                },
                "How much?": {
                    "translation": "Wie viel?",
                    "usage_count": 11,
                    "confidence": 0.97,
                    "last_used": datetime.now().isoformat()
                },
                "Beautiful": {
                    "translation": "Schön",
                    "usage_count": 8,
                    "confidence": 0.95,
                    "last_used": datetime.now().isoformat()
                },
                "Friend": {
                    "translation": "Freund",
                    "usage_count": 9,
                    "confidence": 0.98,
                    "last_used": datetime.now().isoformat()
                },
                "Love": {
                    "translation": "Liebe",
                    "usage_count": 7,
                    "confidence": 0.97,
                    "last_used": datetime.now().isoformat()
                }
            }
            
            # Create dictionary directory if it doesn't exist (EXE-compatible)
            dict_dir = ensure_app_directory("dictionary")
            
            # Dictionary file path
            dict_file = dict_dir / "learned_dictionary_en_de.json.gz"
            
            # Backup existing dictionary if it exists
            if dict_file.exists():
                backup_file = dict_dir / f"learned_dictionary_en_de_backup_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json.gz"
                import shutil
                shutil.copy2(dict_file, backup_file)
                print(f"[Storage] Backed up existing dictionary to: {backup_file}")
            
            # Save example dictionary
            with gzip.open(dict_file, 'wt', encoding='utf-8') as f:
                json.dump(example_entries, f, indent=2, ensure_ascii=False)
            
            print(f"[Storage] Created example dictionary: {dict_file}")
            print(f"[Storage] Total entries: {len(example_entries)}")
            
            # Show success message
            QMessageBox.information(
                self,
                "Example Dictionary Created",
                f"Successfully created example English-German dictionary!\n\n"
                f"Location: {dict_file}\n"
                f"Entries: {len(example_entries)}\n\n"
                f"The dictionary contains common phrases and their German translations.\n"
                f"You can now see it in the Storage tab and use it for translations."
            )
            
            # Refresh displays
            self._refresh_all_dictionaries()
            
        except Exception as e:
            QMessageBox.critical(
                self,
                "Creation Failed",
                f"Failed to create example dictionary:\n\n{str(e)}\n\n"
                f"Please check the console for detailed error messages."
            )
            import traceback
            traceback.print_exc()
    
    def _load_dictionary_stats_from_file(self):
        """Load dictionary statistics directly from file (fallback when pipeline doesn't support it)."""
        try:
            import gzip
            import json
            from pathlib import Path
            from datetime import datetime
            
            # Try to find dictionary files (EXE-compatible)
            dict_dir = get_app_path("dictionary")
            if not dict_dir.exists():
                # No dictionary directory
                self.dict_entries_label.setText("0")
                self.dict_usage_label.setText("0 lookups")
                self.dict_avg_usage_label.setText("0.0 times per entry")
                self.dict_hit_rate_label.setText("N/A")
                self.dict_file_size_label.setText("No dictionary file yet")
                self._update_most_used_list([])
                return
            
            # Look for English-German dictionary (default example)
            dict_file = dict_dir / "learned_dictionary_en_de.json.gz"
            
            if not dict_file.exists():
                # No dictionary file found
                self.dict_entries_label.setText("0")
                self.dict_usage_label.setText("0 lookups")
                self.dict_avg_usage_label.setText("0.0 times per entry")
                self.dict_hit_rate_label.setText("N/A")
                self.dict_file_size_label.setText("No dictionary file yet")
                self._update_most_used_list([])
                return
            
            # Load dictionary file
            with gzip.open(dict_file, 'rt', encoding='utf-8') as f:
                dictionary = json.load(f)
            
            # Calculate statistics
            total_entries = len(dictionary)
            total_usage = sum(entry.get('usage_count', 0) for entry in dictionary.values())
            avg_usage = total_usage / total_entries if total_entries > 0 else 0.0
            
            # Update labels
            self.dict_entries_label.setText(f"{total_entries:,}")
            self.dict_usage_label.setText(f"{total_usage:,} lookups")
            self.dict_avg_usage_label.setText(f"{avg_usage:.1f} times per entry")
            self.dict_hit_rate_label.setText("N/A")  # Can't calculate without runtime data
            
            # File size
            file_size_mb = dict_file.stat().st_size / (1024 * 1024)
            self.dict_file_size_label.setText(f"{file_size_mb:.2f} MB (compressed)")
            
            # Get most used translations
            sorted_entries = sorted(
                dictionary.items(),
                key=lambda x: x[1].get('usage_count', 0),
                reverse=True
            )[:10]  # Top 10
            
            most_used = [
                {
                    'original': source,  # Use 'original' key to match expected format
                    'translation': data.get('translation', ''),
                    'usage_count': data.get('usage_count', 0),
                    'confidence': data.get('confidence', 0.0)
                }
                for source, data in sorted_entries
            ]
            
            self._update_most_used_list(most_used)
            
        except Exception as e:
            # Silently handle errors - show empty stats
            print(f"[Storage] Could not load dictionary stats from file: {e}")
            self.dict_entries_label.setText("0")
            self.dict_usage_label.setText("0 lookups")
            self.dict_avg_usage_label.setText("0.0 times per entry")
            self.dict_hit_rate_label.setText("N/A")
            self.dict_file_size_label.setText("Error reading file")
            self._update_most_used_list([])
    
    def _refresh_all_dictionaries(self):
        """Refresh all dictionary displays."""
        self._populate_language_pair_dropdown()
        self._populate_language_pair_list()
        self._refresh_selected_dictionary_stats()
    
    def load_config(self):
        """Load configuration from config manager."""
        if not self.config_manager:
            return
        
        try:
            # Block signals during loading
            self.blockSignals(True)
            
            # Load cache settings
            cache_enabled = self.config_manager.get_setting('storage.cache_enabled', True)
            self.cache_enabled_check.setChecked(cache_enabled)
            
            cache_size = self.config_manager.get_setting('storage.cache_size_mb', 500)
            self.cache_size_spinbox.setValue(cache_size)
            
            cache_dir = self.config_manager.get_setting('storage.cache_directory', './cache')
            self.cache_dir_edit.setText(cache_dir)
            
            # Load dictionary directory
            dict_dir = self.config_manager.get_setting('storage.dictionary_directory', './dictionary')
            if hasattr(self, 'dict_dir_edit'):
                self.dict_dir_edit.setText(dict_dir)
            
            # Load storage locations
            config_dir = self.config_manager.get_setting('storage.config_directory', './config')
            if hasattr(self, 'config_dir_edit'):
                self.config_dir_edit.setText(config_dir)
            
            model_dir = self.config_manager.get_setting('storage.model_directory', './models')
            self.model_dir_edit.setText(model_dir)
            
            data_dir = self.config_manager.get_setting('storage.data_directory', './data')
            if hasattr(self, 'data_dir_edit') and self.data_dir_edit is not None:
                self.data_dir_edit.setText(data_dir)
            
            logs_dir = self.config_manager.get_setting('storage.logs_directory', './logs')
            if hasattr(self, 'logs_dir_edit'):
                self.logs_dir_edit.setText(logs_dir)
            
            # Load retention policy
            retention_days = self.config_manager.get_setting('storage.retention_days', 30)
            self.retention_spinbox.setValue(retention_days)
            
            # Update cache controls enabled state
            self.cache_size_spinbox.setEnabled(cache_enabled)
            self.cache_dir_edit.setEnabled(cache_enabled)
            self.clear_cache_btn.setEnabled(cache_enabled)
            
            # Unblock signals
            self.blockSignals(False)
            
            # Update storage usage
            self._calculate_storage_usage()
            
            # Refresh dictionary stats (if pipeline is available)
            if self.pipeline and hasattr(self, '_refresh_all_dictionaries'):
                try:
                    self._refresh_all_dictionaries()
                except Exception as e:
                    print(f"[DEBUG] Could not refresh dictionary stats: {e}")
            
            # Save the original state after loading
            self._original_state = self._get_current_state()
            
            print("[DEBUG] Storage tab configuration loaded")
            
        except Exception as e:
            self.blockSignals(False)
            print(f"[WARNING] Failed to load storage tab config: {e}")
            import traceback
            traceback.print_exc()
    
    def _save_table_column_widths(self):
        """Save table column widths to QSettings (registry/config, not config file)."""
        try:
            settings = QSettings("OptikR", "StorageTab")
            header = self.language_pair_table.horizontalHeader()
            
            # Save each column width
            for col in range(self.language_pair_table.columnCount()):
                width = header.sectionSize(col)
                settings.setValue(f"language_pair_table/column_{col}_width", width)
            
            print(f"[STORAGE TAB] Saved column widths to QSettings")
        except Exception as e:
            print(f"[STORAGE TAB] Failed to save column widths: {e}")
    
    def _restore_table_column_widths(self):
        """Restore table column widths from QSettings."""
        try:
            settings = QSettings("OptikR", "StorageTab")
            header = self.language_pair_table.horizontalHeader()
            
            # Default column widths
            default_widths = [60, 250, 150, 80, 80]  # Active, Name, Language Pair, Entries, Size
            
            # Restore each column width
            for col in range(self.language_pair_table.columnCount()):
                saved_width = settings.value(f"language_pair_table/column_{col}_width", default_widths[col], type=int)
                header.resizeSection(col, saved_width)
            
            print(f"[STORAGE TAB] Restored column widths from QSettings")
        except Exception as e:
            print(f"[STORAGE TAB] Failed to restore column widths: {e}")
            # Set default widths if restore fails
            header = self.language_pair_table.horizontalHeader()
            default_widths = [60, 250, 150, 80, 80]
            for col, width in enumerate(default_widths):
                header.resizeSection(col, width)
    
    def save_config(self):
        """Save configuration to config manager."""
        if not self.config_manager:
            return
        
        try:
            # Save cache settings
            self.config_manager.set_setting('storage.cache_enabled', self.cache_enabled_check.isChecked())
            self.config_manager.set_setting('storage.cache_size_mb', self.cache_size_spinbox.value())
            self.config_manager.set_setting('storage.cache_directory', self.cache_dir_edit.text())
            
            # Save dictionary directory
            if hasattr(self, 'dict_dir_edit'):
                self.config_manager.set_setting('storage.dictionary_directory', self.dict_dir_edit.text())
            
            # Save storage locations
            if hasattr(self, 'config_dir_edit'):
                self.config_manager.set_setting('storage.config_directory', self.config_dir_edit.text())
            
            self.config_manager.set_setting('storage.model_directory', self.model_dir_edit.text())
            self.config_manager.set_setting('storage.data_directory', self.data_dir_edit.text())
            
            if hasattr(self, 'logs_dir_edit'):
                self.config_manager.set_setting('storage.logs_directory', self.logs_dir_edit.text())
            
            # Save retention policy
            self.config_manager.set_setting('storage.retention_days', self.retention_spinbox.value())
            
            # Save the configuration file
            if hasattr(self.config_manager, 'save_config'):
                self.config_manager.save_config()
            elif hasattr(self.config_manager, 'save_configuration'):
                config_dict = self.config_manager._config_to_dict(self.config_manager._config)
                self.config_manager.save_configuration(config_dict)
            
            # Update original state after saving
            self._original_state = self._get_current_state()
            
            print("[INFO] Storage tab configuration saved")
            
        except Exception as e:
            print(f"[ERROR] Failed to save storage tab config: {e}")
            import traceback
            traceback.print_exc()
    
    def validate(self) -> bool:
        """
        Validate settings using QFileInfo for directory path validation.
        
        Returns:
            True if settings are valid, False otherwise
        """
        try:
            # Validate cache directory
            cache_path = self.cache_dir_edit.text().strip()
            if not cache_path:
                QMessageBox.warning(
                    self,
                    "Invalid Path",
                    "Cache directory path cannot be empty."
                )
                return False
            
            if not self._validate_directory_path(cache_path, "Cache"):
                return False
            
            # Validate dictionary directory
            if hasattr(self, 'dict_dir_edit'):
                dict_path = self.dict_dir_edit.text().strip()
                if dict_path and not self._validate_directory_path(dict_path, "Dictionary"):
                    return False
            
            # Validate config directory
            if hasattr(self, 'config_dir_edit'):
                config_path = self.config_dir_edit.text().strip()
                if config_path and not self._validate_directory_path(config_path, "Config"):
                    return False
            
            # Validate model directory
            model_path = self.model_dir_edit.text().strip()
            if not model_path:
                QMessageBox.warning(
                    self,
                    "Invalid Path",
                    "Model directory path cannot be empty."
                )
                return False
            
            if not self._validate_directory_path(model_path, "Model"):
                return False
            
            # Validate data directory
            data_path = self.data_dir_edit.text().strip()
            if not data_path:
                QMessageBox.warning(
                    self,
                    "Invalid Path",
                    "Data directory path cannot be empty."
                )
                return False
            
            if not self._validate_directory_path(data_path, "Data"):
                return False
            
            # Validate logs directory
            if hasattr(self, 'logs_dir_edit'):
                logs_path = self.logs_dir_edit.text().strip()
                if logs_path and not self._validate_directory_path(logs_path, "Logs"):
                    return False
            
            # Validate cache size is reasonable
            cache_size = self.cache_size_spinbox.value()
            if cache_size < 100:
                QMessageBox.warning(
                    self,
                    "Invalid Cache Size",
                    "Cache size must be at least 100 MB."
                )
                return False
            
            # Validate retention period
            retention = self.retention_spinbox.value()
            if retention < 1:
                QMessageBox.warning(
                    self,
                    "Invalid Retention Period",
                    "Retention period must be at least 1 day."
                )
                return False
            
            return True
            
        except Exception as e:
            QMessageBox.critical(
                self,
                "Validation Error",
                f"Failed to validate storage settings:\n\n{str(e)}"
            )
            return False
    
    def _validate_directory_path(self, path: str, dir_type: str) -> bool:
        """
        Validate a directory path using QFileInfo.
        
        Args:
            path: Directory path to validate
            dir_type: Type of directory (for error messages)
            
        Returns:
            True if path is valid, False otherwise
        """
        try:
            # Use QFileInfo to check the path
            file_info = QFileInfo(path)
            
            # Check if path exists
            if file_info.exists():
                # Check if it's a directory
                if not file_info.isDir():
                    QMessageBox.warning(
                        self,
                        "Invalid Path",
                        f"{dir_type} directory path exists but is not a directory:\n{path}"
                    )
                    return False
                
                # Check if it's writable
                if not file_info.isWritable():
                    QMessageBox.warning(
                        self,
                        "Permission Denied",
                        f"{dir_type} directory is not writable:\n{path}\n\n"
                        "Please choose a directory with write permissions."
                    )
                    return False
                
                return True
            else:
                # Directory doesn't exist, try to create it
                qdir = QDir()
                if qdir.mkpath(path):
                    print(f"[INFO] Created {dir_type.lower()} directory: {path}")
                    return True
                else:
                    QMessageBox.warning(
                        self,
                        "Cannot Create Directory",
                        f"{dir_type} directory does not exist and cannot be created:\n{path}\n\n"
                        "Please check the path and permissions."
                    )
                    return False
        
        except Exception as e:
            QMessageBox.warning(
                self,
                "Invalid Path",
                f"{dir_type} directory path is invalid:\n{path}\n\nError: {str(e)}"
            )
            return False

    def _clear_selected_dictionary(self):
        """Clear the selected dictionary (delete all entries)."""
        try:
            # Get selected language pair from combo box
            current_text = self.language_pair_combo.currentText()
            if not current_text or "No dictionaries" in current_text:
                QMessageBox.warning(
                    self,
                    "No Dictionary Selected",
                    "Please select a language pair dictionary to clear."
                )
                return
            
            # Get current language pair from config (en -> de)
            src_lang = self.config_manager.get_setting('translation.source_language', 'en')
            tgt_lang = self.config_manager.get_setting('translation.target_language', 'de')
            
            # Build dictionary filename
            dict_filename = f"learned_dictionary_{src_lang}_{tgt_lang}.json.gz"
            lang_info = current_text.split(" (")[0] if "(" in current_text else current_text
            
            # Confirm deletion
            reply = QMessageBox.question(
                self,
                "Clear Dictionary",
                f"Are you sure you want to clear the dictionary?\n\n"
                f"Language Pair: {lang_info}\n"
                f"Entries to delete: {self.dict_entries_label.text()}\n\n"
                f"Other language pairs will not be affected.\n"
                f"This action cannot be undone!",
                QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
                QMessageBox.StandardButton.No
            )
            
            if reply != QMessageBox.StandardButton.Yes:
                return
            
            # Find and delete the dictionary file (use absolute path)
            dict_dir = Path("dictionary")  # Relative to run.py location
            if not dict_dir.exists():
                dict_dir = Path("dev") / "dictionary"  # Try dev/dictionary
            
            dict_file = dict_dir / dict_filename
            
            print(f"[STORAGE TAB] Looking for dictionary at: {dict_file.absolute()}")
            
            deleted_count = 0
            
            if dict_file.exists():
                dict_file.unlink()
                deleted_count += 1
                print(f"[STORAGE TAB] Deleted dictionary file: {dict_file}")
            
            # Also delete backup files for this language pair
            base_name = dict_filename.replace(".json.gz", "")
            for backup_file in dict_dir.glob(f"{base_name}_backup_*.json.gz"):
                backup_file.unlink()
                deleted_count += 1
                print(f"[STORAGE TAB] Deleted backup: {backup_file}")
            
            if deleted_count > 0:
                QMessageBox.information(
                    self,
                    "Dictionary Cleared",
                    f"Dictionary cleared successfully!\n\n"
                    f"Files deleted: {deleted_count}\n"
                    f"Main file: {dict_filename}\n"
                    f"Backups: {deleted_count - 1}"
                )
                
                # Refresh the dictionary list
                if hasattr(self, '_refresh_all_dictionaries'):
                    self._refresh_all_dictionaries()
            else:
                QMessageBox.warning(
                    self,
                    "File Not Found",
                    f"Dictionary file not found:\n{dict_file.absolute()}\n\n"
                    f"Searched in: {dict_dir.absolute()}\n"
                    f"It may have already been deleted."
                )
                
        except Exception as e:
            QMessageBox.critical(
                self,
                "Error",
                f"Failed to clear dictionary:\n{str(e)}"
            )
            import traceback
            traceback.print_exc()
    
    def _export_selected_dictionary(self):
        """Export the selected dictionary to a file."""
        QMessageBox.information(
            self,
            "Not Implemented",
            "Dictionary export feature coming soon!"
        )
    
    def _import_dictionary(self):
        """Import a dictionary from a file."""
        QMessageBox.information(
            self,
            "Not Implemented",
            "Dictionary import feature coming soon!"
        )

    def _clear_cache(self):
        """Clear the translation cache (in-memory cache)."""
        try:
            if not self.pipeline:
                QMessageBox.warning(
                    self,
                    "Pipeline Not Available",
                    "Translation pipeline is not running.\n\n"
                    "The cache will be empty when you start the pipeline."
                )
                return
            
            # Confirm
            reply = QMessageBox.question(
                self,
                "Clear Translation Cache",
                "Clear the in-memory translation cache?\n\n"
                "This will remove all cached translations from memory.\n"
                "Translations will need to be looked up again.\n\n"
                "Note: This does NOT clear the Learning Dictionary.",
                QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
                QMessageBox.StandardButton.No
            )
            
            if reply != QMessageBox.StandardButton.Yes:
                return
            
            # Try to clear the translation cache
            cleared = False
            
            # Method 1: Try to access translation layer cache
            if hasattr(self.pipeline, 'translation_layer'):
                translation_layer = self.pipeline.translation_layer
                
                # Clear translation cache plugin if it exists
                if hasattr(translation_layer, '_cache'):
                    translation_layer._cache.clear()
                    cleared = True
                    print("[STORAGE TAB] Cleared translation layer cache")
                
                # Clear any engine caches
                if hasattr(translation_layer, '_engine_registry'):
                    for engine_name, engine in translation_layer._engine_registry._engines.items():
                        if hasattr(engine, 'clear_cache'):
                            engine.clear_cache()
                            cleared = True
                            print(f"[STORAGE TAB] Cleared cache for engine: {engine_name}")
            
            # Method 2: Try to access pipeline's translation cache plugin
            if hasattr(self.pipeline, '_plugins'):
                for plugin_name, plugin in self.pipeline._plugins.items():
                    if 'cache' in plugin_name.lower():
                        if hasattr(plugin, 'clear'):
                            plugin.clear()
                            cleared = True
                            print(f"[STORAGE TAB] Cleared plugin cache: {plugin_name}")
            
            if cleared:
                QMessageBox.information(
                    self,
                    "Cache Cleared",
                    "Translation cache cleared successfully!\n\n"
                    "All cached translations have been removed from memory."
                )
            else:
                QMessageBox.information(
                    self,
                    "No Cache Found",
                    "No active translation cache found.\n\n"
                    "The cache may already be empty or the pipeline is not running."
                )
                
        except Exception as e:
            QMessageBox.critical(
                self,
                "Error",
                f"Failed to clear translation cache:\n{str(e)}"
            )
            import traceback
            traceback.print_exc()
    
    def _clear_all_caches(self):
        """Clear ALL caches (translation cache + Python bytecode cache)."""
        try:
            # Confirm
            reply = QMessageBox.question(
                self,
                "Clear All Caches",
                "Clear ALL caches?\n\n"
                "This will:\n"
                "• Clear translation cache (in-memory)\n"
                "• Delete Python bytecode cache (__pycache__)\n"
                "• Clear any temporary files\n\n"
                "Note: This does NOT clear the Learning Dictionary.\n"
                "This action cannot be undone!",
                QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
                QMessageBox.StandardButton.No
            )
            
            if reply != QMessageBox.StandardButton.Yes:
                return
            
            deleted_count = 0
            
            # 1. Clear translation cache (in-memory)
            if self.pipeline:
                try:
                    if hasattr(self.pipeline, 'translation_layer'):
                        translation_layer = self.pipeline.translation_layer
                        if hasattr(translation_layer, '_cache'):
                            translation_layer._cache.clear()
                            deleted_count += 1
                except:
                    pass
            
            # 2. Delete __pycache__ directories
            import shutil
            cache_dirs = []
            
            # Find all __pycache__ directories
            for root, dirs, files in os.walk('.'):
                if '__pycache__' in dirs:
                    cache_dir = os.path.join(root, '__pycache__')
                    cache_dirs.append(cache_dir)
            
            # Delete them
            for cache_dir in cache_dirs:
                try:
                    shutil.rmtree(cache_dir)
                    deleted_count += 1
                    print(f"[STORAGE TAB] Deleted {cache_dir}")
                except Exception as e:
                    print(f"[STORAGE TAB] Failed to delete {cache_dir}: {e}")
            
            # 3. Clear cache directory if it exists
            cache_dir = Path(self.cache_dir_edit.text())
            if cache_dir.exists() and cache_dir.is_dir():
                try:
                    for item in cache_dir.iterdir():
                        if item.is_file():
                            item.unlink()
                            deleted_count += 1
                        elif item.is_dir():
                            shutil.rmtree(item)
                            deleted_count += 1
                    print(f"[STORAGE TAB] Cleared cache directory: {cache_dir}")
                except Exception as e:
                    print(f"[STORAGE TAB] Failed to clear cache directory: {e}")
            
            QMessageBox.information(
                self,
                "All Caches Cleared",
                f"All caches cleared successfully!\n\n"
                f"Items deleted: {deleted_count}\n"
                f"• Translation cache cleared\n"
                f"• Python bytecode cache deleted\n"
                f"• Temporary files removed"
            )
                
        except Exception as e:
            QMessageBox.critical(
                self,
                "Error",
                f"Failed to clear all caches:\n{str(e)}"
            )
            import traceback
            traceback.print_exc()
