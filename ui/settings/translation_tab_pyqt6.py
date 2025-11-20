"""
Translation Settings Tab - PyQt6 Implementation (Refactored)
Translation engine selection, API keys, model management, and cache settings.
Uses modular manager classes for better organization.
"""

from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QFormLayout, QGroupBox,
    QLabel, QComboBox, QRadioButton, QCheckBox, QPushButton,
    QButtonGroup, QMessageBox,
    QListWidget, QSlider, QSpinBox, QLineEdit
)
from PyQt6.QtCore import Qt, pyqtSignal
from ui.custom_spinbox import CustomSpinBox, CustomDoubleSpinBox

# Import custom scroll area
from .scroll_area_no_wheel import ScrollAreaNoWheel
import sys
import os
from pathlib import Path

# Add parent directories to path for imports
current_dir = Path(__file__).parent
v01_dir = current_dir.parent.parent
if str(v01_dir) not in sys.path:
    sys.path.insert(0, str(v01_dir))

# Import manager classes
from .translation_api_manager import TranslationAPIManager
from .translation_cache_manager import TranslationCacheManager
from .translation_dictionary_manager import TranslationDictionaryManager
from .translation_model_manager import TranslationModelManager

# Import translation system
from app.translations import TranslatableMixin

# Import encryption utilities
try:
    from app.utils.encryption import encrypt_api_key, decrypt_api_key
    ENCRYPTION_AVAILABLE = True
    print("[INFO] Encryption module loaded successfully - API keys will be encrypted")
except ImportError as e:
    print(f"[WARNING] Encryption module not available ({e}), API keys will be stored in plaintext")
    ENCRYPTION_AVAILABLE = False
    
    def encrypt_api_key(key):
        return key
    
    def decrypt_api_key(key):
        return key


class TranslationSettingsTab(TranslatableMixin, QWidget):
    """Translation settings including engine selection, API keys, and configuration."""
    
    # Signal emitted when any setting changes
    settingChanged = pyqtSignal()

    
    def __init__(self, config_manager=None, pipeline=None, parent=None):
        """Initialize the Translation settings tab."""
        super().__init__(parent)
        
        self.config_manager = config_manager
        self.pipeline = pipeline
        
        # Track original loaded state to detect real changes
        self._original_state = {}
        
        # Initialize manager classes
        self.api_manager = TranslationAPIManager(parent=self)
        self.cache_manager = TranslationCacheManager(parent=self, pipeline=pipeline)
        self.dictionary_manager = TranslationDictionaryManager(parent=self, config_manager=config_manager)
        self.model_manager = TranslationModelManager(parent=self, config_manager=config_manager)
        
        # Import test manager
        from .translation_test_manager import TranslationTestManager
        self.test_manager = TranslationTestManager(parent=self)
        
        # NEW: Phase 2 - Plugin Discovery
        self.translation_layer = None
        self.available_plugins = []
        self.plugin_radios = {}  # Store plugin radio buttons
        
        # Get translation layer from pipeline
        if pipeline and hasattr(pipeline, 'translation_layer'):
            self.translation_layer = pipeline.translation_layer
            self._discover_translation_plugins()
        
        # Engine selection widgets
        self.marianmt_radio = None
        self.google_free_radio = None
        self.libretranslate_radio = None
        self.google_radio = None
        self.deepl_radio = None
        self.azure_radio = None
        self.engine_button_group = None
        
        # API key widgets
        self.google_api_key_edit = None
        self.deepl_api_key_edit = None
        self.azure_api_key_edit = None
        
        # Model management widgets
        self.ai_model_combo = None
        self.model_list = None
        
        # Quality/speed widgets
        self.quality_slider = None
        self.quality_value_label = None
        
        # Cache widgets
        self.cache_enabled_check = None
        self.cache_size_spin = None
        
        # Advanced settings widgets
        self.fallback_enabled_check = None
        self.batch_translation_check = None
        self.context_aware_check = None
        self.preserve_formatting_check = None
        
        # Dictionary overview label
        self.dict_overview_label = None
        
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
        self._create_engine_selection_section(content_layout)
        self._create_cloud_services_section(content_layout)
        self._create_local_engines_section(content_layout)
        self._create_quality_settings_section(content_layout)
        # REMOVED: Cache section (moved to Storage tab)
        # REMOVED: Learning Dictionary section (moved to Storage tab)
        # REMOVED: Settings location note (no longer needed)
        self._create_advanced_section(content_layout)
        
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
        
        # Translation engine
        for plugin_name, radio in self.plugin_radios.items():
            if radio.isChecked():
                state['translation_engine'] = plugin_name
                break
        
        # Cache settings (if available)
        if hasattr(self.cache_manager, 'get_cache_settings'):
            state['cache_settings'] = self.cache_manager.get_cache_settings()
        
        return state
    
    def on_change(self):
        """Called when any setting changes - always emits signal for main window to check."""
        self.settingChanged.emit()

    def _discover_translation_plugins(self):
        """Discover available translation plugins (Phase 2)."""
        if not self.translation_layer:
            print("[TRANSLATION TAB] No translation layer available for plugin discovery")
            return
        
        try:
            # Get plugin manager
            plugin_manager = self.translation_layer.plugin_manager
            
            # Discover plugins
            discovered = plugin_manager.discover_plugins()
            
            # Get plugin info for each discovered plugin
            for plugin_metadata in discovered:
                # Get raw plugin.json data (includes runtime_requirements)
                raw_data = plugin_manager.registry.get_plugin_raw_data(plugin_metadata.name)
                
                plugin_info = {
                    'name': plugin_metadata.name,
                    'display_name': plugin_metadata.display_name,
                    'description': plugin_metadata.description,
                    'version': plugin_metadata.version,
                    'metadata': raw_data if raw_data else plugin_metadata.to_dict(),  # Use raw data for runtime_requirements
                    'loaded': plugin_manager.registry.is_engine_loaded(plugin_metadata.name)
                }
                self.available_plugins.append(plugin_info)
            
            print(f"[TRANSLATION TAB] Discovered {len(self.available_plugins)} translation plugins")
            for plugin in self.available_plugins:
                print(f"  - {plugin['display_name']} (loaded: {plugin['loaded']})")
        
        except Exception as e:
            print(f"[TRANSLATION TAB] Failed to discover plugins: {e}")
            import traceback
            traceback.print_exc()
    
    def _add_plugin_engine_option(self, layout, plugin_info, button_id):
        """Add a plugin engine option with GPU/CPU indicator (Phase 2)."""
        plugin_layout = QHBoxLayout()
        plugin_layout.setSpacing(10)
        
        # Radio button
        radio = QRadioButton(plugin_info['display_name'])
        radio.toggled.connect(self.on_change)
        self.engine_button_group.addButton(radio, button_id)
        self.plugin_radios[plugin_info['name']] = radio
        plugin_layout.addWidget(radio)
        
        # GPU/CPU indicator from metadata
        metadata = plugin_info.get('metadata', {})
        runtime_req = metadata.get('runtime_requirements', {})
        
        if runtime_req:
            gpu_req = runtime_req.get('gpu', {})
            cpu_req = runtime_req.get('cpu', {})
            
            if gpu_req.get('required'):
                # GPU-only
                indicator = QLabel("🎮 GPU Only")
                indicator.setStyleSheet("color: #FF9800; font-weight: bold; font-size: 9pt;")
                indicator.setToolTip("Requires GPU - will not work on CPU")
            elif gpu_req.get('recommended') and cpu_req.get('supported'):
                # Hybrid (GPU-accelerated, CPU-capable)
                runtime_mode = self.config_manager.get_setting('performance.runtime_mode', 'auto') if self.config_manager else 'auto'
                if runtime_mode == 'gpu':
                    indicator = QLabel("⚡ GPU")
                    indicator.setStyleSheet("color: #4CAF50; font-weight: bold; font-size: 9pt;")
                    indicator.setToolTip("Using GPU acceleration")
                elif runtime_mode == 'cpu':
                    indicator = QLabel("💻 CPU")
                    indicator.setStyleSheet("color: #FF9800; font-weight: bold; font-size: 9pt;")
                    indicator.setToolTip("Using CPU (slower)")
                else:
                    indicator = QLabel("⚡ GPU/CPU")
                    indicator.setStyleSheet("color: #4CAF50; font-weight: bold; font-size: 9pt;")
                    indicator.setToolTip("Supports both GPU and CPU")
            else:
                # CPU-only
                indicator = QLabel("💻 CPU")
                indicator.setStyleSheet("color: #2196F3; font-weight: bold; font-size: 9pt;")
                indicator.setToolTip("CPU-only engine")
            
            plugin_layout.addWidget(indicator)
        
        # Loaded status
        if plugin_info['loaded']:
            status_label = QLabel("✅ Loaded")
            status_label.setStyleSheet("color: #4CAF50; font-size: 8pt;")
            status_label.setToolTip("Plugin is currently loaded and ready")
        else:
            status_label = QLabel("⏸️ Not Loaded")
            status_label.setStyleSheet("color: #666666; font-size: 8pt;")
            status_label.setToolTip("Plugin will be loaded when selected")
        plugin_layout.addWidget(status_label)
        
        # Test button
        test_btn = QPushButton("⚡ Test")
        test_btn.setProperty("class", "action")
        test_btn.setMaximumWidth(80)
        test_btn.clicked.connect(lambda: self._test_plugin_engine(plugin_info['name']))
        plugin_layout.addWidget(test_btn)
        
        plugin_layout.addStretch()
        layout.addLayout(plugin_layout)
        
        # Description
        desc_text = f"  • {plugin_info['description']}"
        if runtime_req:
            perf_note = runtime_req.get('gpu', {}).get('performance_note', '')
            if perf_note:
                desc_text += f" - {perf_note}"
        
        desc = QLabel(desc_text)
        desc.setStyleSheet("color: #666666; font-size: 8pt; margin-left: 20px; margin-bottom: 5px;")
        desc.setWordWrap(True)
        layout.addWidget(desc)
    
    def _test_plugin_engine(self, plugin_name):
        """Test a plugin-based translation engine (Phase 2)."""
        try:
            # Use existing test manager
            self.test_manager.test_translation_engine(plugin_name)
        except Exception as e:
            QMessageBox.warning(
                self,
                "Test Failed",
                f"Failed to test plugin '{plugin_name}':\n\n{str(e)}"
            )
    
    def _get_downloaded_marianmt_models(self):
        """Get list of actually downloaded MarianMT models (Phase 3)."""
        try:
            from pathlib import Path
            import os
            
            # Check HuggingFace cache directory for downloaded models
            cache_dir = Path.home() / '.cache' / 'huggingface' / 'hub'
            
            if not cache_dir.exists():
                return []
            
            models = []
            
            # Look for MarianMT model directories
            for model_dir in cache_dir.iterdir():
                if model_dir.is_dir() and 'opus-mt-' in model_dir.name:
                    # Extract language pair from model name
                    # Format: models--Helsinki-NLP--opus-mt-en-de
                    try:
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
                                
                                models.append({
                                    'name': f"{src.upper()} → {tgt.upper()}",
                                    'size': size_str,
                                    'src': src,
                                    'tgt': tgt
                                })
                    except Exception as e:
                        continue
            
            return models
        
        except Exception as e:
            print(f"[TRANSLATION TAB] Failed to get downloaded models: {e}")
            import traceback
            traceback.print_exc()
            return []
    
    def _is_model_downloaded(self, src_lang, tgt_lang):
        """Check if a specific model is downloaded (Phase 3)."""
        try:
            from pathlib import Path
            
            # Check HuggingFace cache directory for this specific model
            cache_dir = Path.home() / '.cache' / 'huggingface' / 'hub'
            
            if not cache_dir.exists():
                return False
            
            # Look for the specific model directory
            model_name = f"opus-mt-{src_lang}-{tgt_lang}"
            
            for model_dir in cache_dir.iterdir():
                if model_dir.is_dir() and model_name in model_dir.name:
                    # Check if it has actual model files (not just a snapshot reference)
                    snapshots_dir = model_dir / 'snapshots'
                    if snapshots_dir.exists():
                        # Check if there's at least one snapshot with files
                        for snapshot in snapshots_dir.iterdir():
                            if snapshot.is_dir() and any(snapshot.iterdir()):
                                return True
            
            return False
        except Exception as e:
            print(f"[TRANSLATION TAB] Failed to check model download status: {e}")
            return False
    
    def _get_model_size(self, model):
        """Get approximate size of a model (Phase 3)."""
        try:
            import sys
            size_bytes = sys.getsizeof(model)
            size_mb = size_bytes / (1024 * 1024)
            return f"{size_mb:.0f} MB"
        except:
            return "Unknown"
    
    def _get_available_marianmt_models(self):
        """Get list of available MarianMT models to download (Phase 3)."""
        # Common language pairs for MarianMT
        common_pairs = [
            ('en', 'de', 'English → German'),
            ('en', 'es', 'English → Spanish'),
            ('en', 'fr', 'English → French'),
            ('en', 'ja', 'English → Japanese'),
            ('en', 'ko', 'English → Korean'),
            ('en', 'zh', 'English → Chinese'),
            ('de', 'en', 'German → English'),
            ('es', 'en', 'Spanish → English'),
            ('fr', 'en', 'French → English'),
            ('ja', 'en', 'Japanese → English'),
            ('ko', 'en', 'Korean → English'),
            ('zh', 'en', 'Chinese → English'),
        ]
        
        models = []
        for src, tgt, desc in common_pairs:
            models.append({
                'src': src,
                'tgt': tgt,
                'name': f"{src}-{tgt}",
                'description': desc,
                'downloaded': self._is_model_downloaded(src, tgt)
            })
        
        return models
    
    def _create_runtime_status_section(self, parent_layout):
        """Create runtime status section showing GPU/CPU mode (Phase 1)."""
        runtime_group = QGroupBox()
        self.set_translatable_text(runtime_group, "translation_runtime_status_section")
        layout = QVBoxLayout(runtime_group)
        layout.setSpacing(8)
        layout.setContentsMargins(15, 20, 15, 15)
        
        # Get runtime mode
        runtime_mode = self.config_manager.get_setting('performance.runtime_mode', 'auto') if self.config_manager else 'auto'
        
        # Runtime mode display
        if runtime_mode == 'gpu':
            status_text = "<b>Runtime Mode:</b> GPU (Using GPU acceleration)"
            color = "#4CAF50"
            icon = "⚡"
        elif runtime_mode == 'cpu':
            status_text = "<b>Runtime Mode:</b> CPU (CPU only)"
            color = "#FF9800"
            icon = "💻"
        else:
            status_text = "<b>Runtime Mode:</b> Auto (Auto-detecting hardware)"
            color = "#2196F3"
            icon = "🔄"
        
        status_label = QLabel(f"{icon} {status_text}")
        status_label.setStyleSheet(f"color: {color}; font-size: 10pt; font-weight: bold;")
        layout.addWidget(status_label)
        
        # Check actual GPU availability
        try:
            import torch
            if torch.cuda.is_available():
                gpu_name = torch.cuda.get_device_name(0)
                gpu_label = QLabel(f"✅ GPU Available: {gpu_name}")
                gpu_label.setStyleSheet("color: #4CAF50; font-size: 9pt;")
                layout.addWidget(gpu_label)
                
                # Show CUDA version
                cuda_version = torch.version.cuda
                cuda_label = QLabel(f"   CUDA Version: {cuda_version}")
                cuda_label.setStyleSheet("color: #666666; font-size: 8pt;")
                layout.addWidget(cuda_label)
            else:
                gpu_label = QLabel("⚠️ No GPU detected - Using CPU mode")
                gpu_label.setStyleSheet("color: #FF9800; font-size: 9pt;")
                layout.addWidget(gpu_label)
        except Exception as e:
            error_label = QLabel(f"⚠️ Could not detect GPU: {str(e)}")
            error_label.setStyleSheet("color: #FF9800; font-size: 8pt;")
            layout.addWidget(error_label)
        
        # Link to General tab
        link_label = QLabel(
            "💡 <b>To change runtime mode:</b> Go to <b>General tab → Runtime Configuration</b>"
        )
        link_label.setWordWrap(True)
        link_label.setStyleSheet(
            "color: #2196F3; font-size: 8pt; margin-top: 8px; padding: 8px; "
            "background-color: rgba(33, 150, 243, 0.1); border-radius: 4px;"
        )
        layout.addWidget(link_label)
        
        parent_layout.addWidget(runtime_group)
    
    def _create_engine_selection_section(self, parent_layout):
        """Create translation engine selection section."""
        # NEW: Runtime Status Section (Phase 1)
        self._create_runtime_status_section(parent_layout)
        
        engine_group = QGroupBox()
        self.set_translatable_text(engine_group, "translation_engine_section")
        layout = QVBoxLayout(engine_group)
        layout.setSpacing(12)
        layout.setContentsMargins(15, 20, 15, 15)
        
        # Engine selection label
        engine_label = self._create_label("", bold=True)
        self.set_translatable_text(engine_label, "translation_select_engine_label")
        layout.addWidget(engine_label)
        
        # Create button group for radio buttons
        self.engine_button_group = QButtonGroup()
        
        # Plugin-based engines only
        if not self.available_plugins:
            # No plugins found - show error
            error_label = QLabel("⚠️ <b>No translation plugins found!</b>")
            error_label.setStyleSheet("color: #FF5252; font-size: 10pt; font-weight: bold;")
            layout.addWidget(error_label)
            
            error_desc = QLabel(
                "Translation plugins are required for the app to work. "
                "Please check your installation or contact support."
            )
            error_desc.setWordWrap(True)
            error_desc.setStyleSheet("color: #FF5252; font-size: 9pt; margin-top: 5px;")
            layout.addWidget(error_desc)
        else:
            # Separate plugins into offline and online
            offline_plugins = []
            online_plugins = []
            
            for plugin in self.available_plugins:
                metadata = plugin.get('metadata', {})
                runtime_req = metadata.get('runtime_requirements', {})
                internet_req = runtime_req.get('internet', {})
                
                if internet_req.get('required', False):
                    online_plugins.append(plugin)
                else:
                    offline_plugins.append(plugin)
            
            # Show offline plugin-based engines
            if offline_plugins:
                plugin_section_label = QLabel("<b>🔌 Local AI Engines (Offline)</b>")
                plugin_section_label.setStyleSheet("color: #4CAF50; font-size: 10pt; margin-top: 5px;")
                layout.addWidget(plugin_section_label)
                
                # Add each offline plugin
                button_id = 0
                for plugin in offline_plugins:
                    self._add_plugin_engine_option(layout, plugin, button_id)
                    button_id += 1
            else:
                button_id = 0
            
            # Add note about offline engines
            if offline_plugins:
                offline_note = QLabel()
                self.set_translatable_text(offline_note, "translation_offline_engines_note")
                offline_note.setWordWrap(True)
                offline_note.setStyleSheet(
                    "color: #4CAF50; font-size: 8pt; margin-top: 5px; margin-bottom: 10px; "
                    "padding: 8px; background-color: rgba(76, 175, 80, 0.1); border-radius: 4px; "
                    "border-left: 3px solid #4CAF50;"
                )
                layout.addWidget(offline_note)
            
            # Separator
            separator = QLabel("─" * 80)
            separator.setStyleSheet("color: #666666; margin-top: 10px; margin-bottom: 10px;")
            layout.addWidget(separator)
            
            # Cloud services section
            cloud_label = QLabel("<b>☁️ Cloud Translation Services (Require Internet)</b>")
            cloud_label.setStyleSheet("color: #2196F3; font-size: 10pt;")
            layout.addWidget(cloud_label)
            
            # Internet disclaimer
            internet_disclaimer = QLabel()
            self.set_translatable_text(internet_disclaimer, "translation_internet_disclaimer")
            internet_disclaimer.setWordWrap(True)
            internet_disclaimer.setStyleSheet(
                "color: #FF9800; font-size: 9pt; margin-top: 5px; margin-bottom: 10px; "
                "padding: 8px; background-color: rgba(255, 152, 0, 0.1); border-radius: 4px; "
                "border-left: 3px solid #FF9800;"
            )
            layout.addWidget(internet_disclaimer)
            
            # Start cloud engines from next button ID
            self._cloud_button_id_offset = button_id
            
            # Add online plugins first (if any)
            for plugin in online_plugins:
                self._add_plugin_engine_option(layout, plugin, button_id)
                button_id += 1
            
            # Google Translate Free option (no API key needed)
            google_free_layout = QHBoxLayout()
            self.google_free_radio = QRadioButton("Google Translate Free (No API Key)")
            self.google_free_radio.toggled.connect(self.on_change)
            self.engine_button_group.addButton(self.google_free_radio, button_id)
            google_free_layout.addWidget(self.google_free_radio)
            
            # Internet indicator
            internet_icon = QLabel("🌐")
            internet_icon.setStyleSheet("font-size: 12pt;")
            internet_icon.setToolTip("Requires internet connection")
            google_free_layout.addWidget(internet_icon)
            
            google_free_test_btn = QPushButton("⚡ Test")
            google_free_test_btn.setProperty("class", "action")
            google_free_test_btn.setMaximumWidth(80)
            google_free_test_btn.clicked.connect(lambda: self.test_manager.test_translation_engine('google_free'))
            google_free_layout.addWidget(google_free_test_btn)
            google_free_layout.addStretch()
            layout.addLayout(google_free_layout)
            
            google_free_desc = QLabel("  • Free, no API key required, good quality, 100+ languages")
            google_free_desc.setStyleSheet("color: #666666; font-size: 8pt; margin-left: 20px; margin-bottom: 5px;")
            layout.addWidget(google_free_desc)
            button_id += 1
            
            # LibreTranslate option (free, open-source)
            libretranslate_layout = QHBoxLayout()
            self.libretranslate_radio = QRadioButton("LibreTranslate (Free AI Cloud)")
            self.libretranslate_radio.toggled.connect(self.on_change)
            self.engine_button_group.addButton(self.libretranslate_radio, button_id)
            libretranslate_layout.addWidget(self.libretranslate_radio)
            
            # Internet indicator
            internet_icon2 = QLabel("🌐")
            internet_icon2.setStyleSheet("font-size: 12pt;")
            internet_icon2.setToolTip("Requires internet connection")
            libretranslate_layout.addWidget(internet_icon2)
            
            # Not Loaded status (legacy engine)
            status_label = QLabel("⏸️ Not Loaded")
            status_label.setStyleSheet("color: #666666; font-size: 8pt;")
            status_label.setToolTip("Legacy engine - will be loaded when selected")
            libretranslate_layout.addWidget(status_label)
            
            libretranslate_test_btn = QPushButton("⚡ Test")
            libretranslate_test_btn.setProperty("class", "action")
            libretranslate_test_btn.setMaximumWidth(80)
            libretranslate_test_btn.clicked.connect(lambda: self.test_manager.test_translation_engine('libretranslate'))
            libretranslate_layout.addWidget(libretranslate_test_btn)
            libretranslate_layout.addStretch()
            layout.addLayout(libretranslate_layout)
            
            libretranslate_desc = QLabel("  • Free, open-source AI translation using LibreTranslate API, useful for testing OCR to translation issues.")
            libretranslate_desc.setStyleSheet("color: #666666; font-size: 8pt; margin-left: 20px; margin-bottom: 5px;")
            libretranslate_desc.setWordWrap(True)
            layout.addWidget(libretranslate_desc)
            button_id += 1
            
            # Separator for premium services
            separator2 = QLabel("─" * 80)
            separator2.setStyleSheet("color: #666666; margin-top: 10px; margin-bottom: 5px;")
            layout.addWidget(separator2)
            
            premium_label = QLabel("<b>💳 Premium Cloud Services (API Key Required)</b>")
            premium_label.setStyleSheet("color: #9C27B0; font-size: 10pt;")
            layout.addWidget(premium_label)
            
            # Premium disclaimer
            premium_disclaimer = QLabel()
            self.set_translatable_text(premium_disclaimer, "translation_premium_disclaimer")
            premium_disclaimer.setWordWrap(True)
            premium_disclaimer.setStyleSheet(
                "color: #9C27B0; font-size: 9pt; margin-top: 5px; margin-bottom: 10px; "
                "padding: 8px; background-color: rgba(156, 39, 176, 0.1); border-radius: 4px; "
                "border-left: 3px solid #9C27B0;"
            )
            layout.addWidget(premium_disclaimer)
            
            # Google Translate API option
            google_api_layout = QHBoxLayout()
            self.google_api_radio = QRadioButton("Google Translate API (Premium)")
            self.google_api_radio.toggled.connect(self.on_change)
            self.engine_button_group.addButton(self.google_api_radio, button_id)
            google_api_layout.addWidget(self.google_api_radio)
            button_id += 1
            
            # Internet + Key indicator
            internet_key_icon = QLabel("🌐🔑")
            internet_key_icon.setStyleSheet("font-size: 12pt;")
            internet_key_icon.setToolTip("Requires internet connection and API key")
            google_api_layout.addWidget(internet_key_icon)
            
            google_api_test_btn = QPushButton("⚡ Test")
            google_api_test_btn.setProperty("class", "action")
            google_api_test_btn.setMaximumWidth(80)
            google_api_test_btn.clicked.connect(lambda: self.test_manager.test_translation_engine('google'))
            google_api_layout.addWidget(google_api_test_btn)
            google_api_layout.addStretch()
            layout.addLayout(google_api_layout)
            
            google_api_desc = QLabel("  • Requires API key, excellent quality, 100+ languages, high rate limits")
            google_api_desc.setStyleSheet("color: #666666; font-size: 8pt; margin-left: 20px; margin-bottom: 5px;")
            layout.addWidget(google_api_desc)
            
            # DeepL option
            deepl_layout = QHBoxLayout()
            self.deepl_api_radio = QRadioButton("DeepL (Premium)")
            self.deepl_api_radio.toggled.connect(self.on_change)
            self.engine_button_group.addButton(self.deepl_api_radio, button_id)
            deepl_layout.addWidget(self.deepl_api_radio)
            button_id += 1
            
            # Internet + Key indicator
            internet_key_icon2 = QLabel("🌐🔑")
            internet_key_icon2.setStyleSheet("font-size: 12pt;")
            internet_key_icon2.setToolTip("Requires internet connection and API key")
            deepl_layout.addWidget(internet_key_icon2)
            
            deepl_test_btn = QPushButton("⚡ Test")
            deepl_test_btn.setProperty("class", "action")
            deepl_test_btn.setMaximumWidth(80)
            deepl_test_btn.clicked.connect(lambda: self.test_manager.test_translation_engine('deepl'))
            deepl_layout.addWidget(deepl_test_btn)
            deepl_layout.addStretch()
            layout.addLayout(deepl_layout)
            
            deepl_desc = QLabel("  • Requires API key, best quality for European languages, professional grade")
            deepl_desc.setStyleSheet("color: #666666; font-size: 8pt; margin-left: 20px; margin-bottom: 5px;")
            layout.addWidget(deepl_desc)
            
            # Azure Translator option
            azure_layout = QHBoxLayout()
            self.azure_api_radio = QRadioButton("Azure Translator (Premium)")
            self.azure_api_radio.toggled.connect(self.on_change)
            self.engine_button_group.addButton(self.azure_api_radio, button_id)
            azure_layout.addWidget(self.azure_api_radio)
            button_id += 1
            
            # Internet + Key indicator
            internet_key_icon3 = QLabel("🌐🔑")
            internet_key_icon3.setStyleSheet("font-size: 12pt;")
            internet_key_icon3.setToolTip("Requires internet connection and API key")
            azure_layout.addWidget(internet_key_icon3)
            
            azure_test_btn = QPushButton("⚡ Test")
            azure_test_btn.setProperty("class", "action")
            azure_test_btn.setMaximumWidth(80)
            azure_test_btn.clicked.connect(lambda: self.test_manager.test_translation_engine('azure'))
            azure_layout.addWidget(azure_test_btn)
            azure_layout.addStretch()
            layout.addLayout(azure_layout)
            
            azure_desc = QLabel("  • Requires API key, enterprise-grade translation, Microsoft Azure platform")
            azure_desc.setStyleSheet("color: #666666; font-size: 8pt; margin-left: 20px; margin-bottom: 5px;")
            layout.addWidget(azure_desc)
            
            # Note about offline vs online
            note_label = QLabel()
            self.set_translatable_text(note_label, "translation_offline_tip")
            note_label.setWordWrap(True)
            note_label.setStyleSheet("color: #666666; font-size: 9pt; margin-top: 10px;")
            layout.addWidget(note_label)
        
        parent_layout.addWidget(engine_group)

    
    def _create_cloud_services_section(self, parent_layout):
        """Create cloud translation services API key section."""
        cloud_group = QGroupBox()
        self.set_translatable_text(cloud_group, "translation_cloud_services_section")
        layout = QVBoxLayout(cloud_group)
        layout.setSpacing(12)
        layout.setContentsMargins(15, 20, 15, 15)
        
        # Google Translate API
        google_label = self._create_label("", bold=True)
        self.set_translatable_text(google_label, "translation_google_api_key_label")
        layout.addWidget(google_label)
        
        google_layout = QHBoxLayout()
        google_layout.setSpacing(10)
        
        self.google_api_key_edit = QLineEdit()
        self._set_placeholder_text(self.google_api_key_edit, "translation_google_api_placeholder")
        self.google_api_key_edit.setEchoMode(QLineEdit.EchoMode.Password)
        self.google_api_key_edit.textChanged.connect(self.on_change)
        google_layout.addWidget(self.google_api_key_edit)
        
        google_test_btn = QPushButton("Test")
        google_test_btn.setProperty("class", "action")
        google_test_btn.setMinimumWidth(80)
        google_test_btn.clicked.connect(lambda: self.api_manager.test_api_key("google", self.google_api_key_edit.text().strip()))
        google_layout.addWidget(google_test_btn)
        
        layout.addLayout(google_layout)
        
        google_help = QLabel()
        self.set_translatable_text(google_help, "translation_google_help")
        google_help.setStyleSheet("color: #666666; font-size: 8pt; margin-left: 5px; margin-bottom: 10px;")
        google_help.setWordWrap(True)
        layout.addWidget(google_help)
        
        # DeepL API
        deepl_label = self._create_label("", bold=True)
        self.set_translatable_text(deepl_label, "translation_deepl_api_key_label")
        layout.addWidget(deepl_label)
        
        deepl_layout = QHBoxLayout()
        deepl_layout.setSpacing(10)
        
        self.deepl_api_key_edit = QLineEdit()
        self._set_placeholder_text(self.deepl_api_key_edit, "translation_deepl_api_placeholder")
        self.deepl_api_key_edit.setEchoMode(QLineEdit.EchoMode.Password)
        self.deepl_api_key_edit.textChanged.connect(self.on_change)
        deepl_layout.addWidget(self.deepl_api_key_edit)
        
        deepl_test_btn = QPushButton("Test")
        deepl_test_btn.setProperty("class", "action")
        deepl_test_btn.setMinimumWidth(80)
        deepl_test_btn.clicked.connect(lambda: self.api_manager.test_api_key("deepl", self.deepl_api_key_edit.text().strip()))
        deepl_layout.addWidget(deepl_test_btn)
        
        layout.addLayout(deepl_layout)
        
        deepl_help = QLabel()
        self.set_translatable_text(deepl_help, "translation_deepl_help")
        deepl_help.setStyleSheet("color: #666666; font-size: 8pt; margin-left: 5px; margin-bottom: 10px;")
        deepl_help.setWordWrap(True)
        layout.addWidget(deepl_help)
        
        # Azure Translator API
        azure_label = self._create_label("", bold=True)
        self.set_translatable_text(azure_label, "translation_azure_api_key_label")
        layout.addWidget(azure_label)
        
        azure_layout = QHBoxLayout()
        azure_layout.setSpacing(10)
        
        self.azure_api_key_edit = QLineEdit()
        self._set_placeholder_text(self.azure_api_key_edit, "translation_azure_api_placeholder")
        self.azure_api_key_edit.setEchoMode(QLineEdit.EchoMode.Password)
        self.azure_api_key_edit.textChanged.connect(self.on_change)
        azure_layout.addWidget(self.azure_api_key_edit)
        
        azure_test_btn = QPushButton("Test")
        azure_test_btn.setProperty("class", "action")
        azure_test_btn.setMinimumWidth(80)
        azure_test_btn.clicked.connect(lambda: self.api_manager.test_api_key("azure", self.azure_api_key_edit.text().strip()))
        azure_layout.addWidget(azure_test_btn)
        
        layout.addLayout(azure_layout)
        
        azure_help = QLabel()
        self.set_translatable_text(azure_help, "translation_azure_help")
        azure_help.setStyleSheet("color: #666666; font-size: 8pt; margin-left: 5px;")
        azure_help.setWordWrap(True)
        layout.addWidget(azure_help)
        
        parent_layout.addWidget(cloud_group)
    
    def _set_placeholder_text(self, line_edit, key):
        """Helper to set placeholder text from translation key."""
        from app.translations import tr
        line_edit.setPlaceholderText(tr(key))

    
    def _create_local_engines_section(self, parent_layout):
        """Create local translation engines section with REAL model status (Phase 3)."""
        marianmt_group = QGroupBox()
        self.set_translatable_text(marianmt_group, "translation_marianmt_section")
        layout = QVBoxLayout(marianmt_group)
        layout.setSpacing(12)
        layout.setContentsMargins(15, 20, 15, 15)
        
        # NEW: Phase 3 - Show downloaded models
        downloaded_models = self._get_downloaded_marianmt_models()
        
        if downloaded_models:
            downloaded_label = QLabel(f"<b>✅ Downloaded Models ({len(downloaded_models)}):</b>")
            downloaded_label.setStyleSheet("color: #4CAF50; font-size: 10pt;")
            layout.addWidget(downloaded_label)
            
            for model in downloaded_models:
                model_item = QLabel(f"  • {model['name']} - {model['size']}")
                model_item.setStyleSheet("color: #4CAF50; font-size: 9pt; margin-left: 10px;")
                layout.addWidget(model_item)
            
            # Separator
            separator = QLabel("─" * 80)
            separator.setStyleSheet("color: #666666; margin-top: 10px; margin-bottom: 10px;")
            layout.addWidget(separator)
        else:
            no_models_label = QLabel("⚠️ <b>No models downloaded yet</b>")
            no_models_label.setStyleSheet("color: #FF9800; font-size: 10pt; font-weight: bold;")
            layout.addWidget(no_models_label)
            
            help_text = QLabel(
                "Models will be downloaded automatically when you first use MarianMT translation. "
                "You can also download them manually below."
            )
            help_text.setWordWrap(True)
            help_text.setStyleSheet("color: #666666; font-size: 8pt; margin-bottom: 10px;")
            layout.addWidget(help_text)
        
        # AI Model selection
        model_select_layout = QHBoxLayout()
        model_select_layout.setSpacing(10)
        
        ai_model_label = self._create_label("", bold=True)
        self.set_translatable_text(ai_model_label, "translation_select_ai_model_label")
        model_select_layout.addWidget(ai_model_label)
        
        self.ai_model_combo = QComboBox()
        self.ai_model_combo.addItems([
            "MarianMT (Neural MT - Recommended)",
            "NLLB (200+ Languages)",
            "M2M-100 (Multilingual)",
            "mBART (Multilingual)"
        ])
        self.ai_model_combo.setMinimumWidth(300)
        self.ai_model_combo.currentIndexChanged.connect(self._on_ai_model_changed)
        model_select_layout.addWidget(self.ai_model_combo)
        
        model_select_layout.addStretch()
        layout.addLayout(model_select_layout)
        
        # Model info label
        self.model_info_label = QLabel()
        self.model_info_label.setWordWrap(True)
        self.model_info_label.setStyleSheet("color: #666666; font-size: 8pt; margin-top: 5px; margin-bottom: 10px;")
        layout.addWidget(self.model_info_label)
        
        # Available language pairs label with explanation
        lang_pairs_label = self._create_label("", bold=True)
        self.set_translatable_text(lang_pairs_label, "translation_available_models_label")
        layout.addWidget(lang_pairs_label)
        
        lang_pairs_help = QLabel()
        self.set_translatable_text(lang_pairs_help, "translation_lang_pairs_help")
        lang_pairs_help.setWordWrap(True)
        lang_pairs_help.setStyleSheet("color: #666666; font-size: 8pt; margin-bottom: 5px;")
        layout.addWidget(lang_pairs_help)
        
        # Model list with download status (Phase 3)
        self.model_list = QListWidget()
        self.model_list.setMaximumHeight(150)
        self.model_list.setSelectionMode(QListWidget.SelectionMode.SingleSelection)
        
        # Populate with available models and their status
        available_models = self._get_available_marianmt_models()
        for model in available_models:
            status_icon = "✅" if model['downloaded'] else "⬇️"
            status_text = " (Downloaded)" if model['downloaded'] else " (Not downloaded)"
            item_text = f"{status_icon} {model['description']}{status_text}"
            self.model_list.addItem(item_text)
        
        layout.addWidget(self.model_list)
        
        # Model management buttons
        button_layout = QHBoxLayout()
        button_layout.setSpacing(10)
        
        self.add_language_btn = QPushButton()
        self.set_translatable_text(self.add_language_btn, "translation_add_language_btn")
        self.add_language_btn.setProperty("class", "action")
        self.add_language_btn.setMinimumWidth(140)
        self.add_language_btn.clicked.connect(self._add_language_pair)
        button_layout.addWidget(self.add_language_btn)
        
        self.download_models_btn = QPushButton()
        self.set_translatable_text(self.download_models_btn, "translation_download_selected_btn")
        self.download_models_btn.setProperty("class", "action")
        self.download_models_btn.setMinimumWidth(160)
        self.download_models_btn.clicked.connect(self._download_selected_ai_model)
        button_layout.addWidget(self.download_models_btn)
        
        self.manage_models_btn = QPushButton()
        self.set_translatable_text(self.manage_models_btn, "translation_manage_models_btn")
        self.manage_models_btn.setProperty("class", "action")
        self.manage_models_btn.setMinimumWidth(150)
        self.manage_models_btn.clicked.connect(self._manage_selected_ai_model)
        button_layout.addWidget(self.manage_models_btn)
        
        button_layout.addStretch()
        layout.addLayout(button_layout)
        
        # Help text
        self.help_label = QLabel()
        self.help_label.setWordWrap(True)
        self.help_label.setStyleSheet("color: #666666; font-size: 9pt; margin-top: 5px;")
        layout.addWidget(self.help_label)
        
        # Clear explanation box
        explanation_box = QLabel()
        self.set_translatable_text(explanation_box, "translation_how_it_works")
        explanation_box.setWordWrap(True)
        explanation_box.setStyleSheet(
            "color: #2196F3; font-size: 8pt; margin-top: 10px; padding: 10px; "
            "background-color: rgba(33, 150, 243, 0.1); border-radius: 4px; border-left: 3px solid #2196F3;"
        )
        layout.addWidget(explanation_box)
        
        # Initialize with MarianMT selected
        self._on_ai_model_changed(0)
        
        parent_layout.addWidget(marianmt_group)
    
    def _on_ai_model_changed(self, index):
        """Handle AI model selection change."""
        model_info = {
            0: {
                "name": "MarianMT",
                "info": "Neural Machine Translation from Helsinki-NLP. Fast, efficient, and works completely offline. Each model translates ONE direction (e.g., English→German).",
                "models": [
                    "English → German (en-de) - Translates English text to German",
                    "English → Spanish (en-es) - Translates English text to Spanish", 
                    "English → French (en-fr) - Translates English text to French",
                    "English → Japanese (en-ja) - Translates English text to Japanese",
                    "German → English (de-en) - Translates German text to English",
                    "Japanese → English (ja-en) - Translates Japanese text to English"
                ],
                "help": "💡 Download the model that matches your Source→Target languages from the General tab. Each model is ~300-500 MB and works offline.",
                "available": True
            },
            1: {
                "name": "NLLB",
                "info": "No Language Left Behind by Meta AI. Supports 200+ languages with high quality.",
                "models": ["nllb-200-distilled-600M (600MB)", "nllb-200-1.3B (1.3GB)", "nllb-200-3.3B (3.3GB)"],
                "help": "✅ NLLB models support 200+ languages. Choose model size based on your needs. Use 'Manage Models' to download.",
                "available": True
            },
            2: {
                "name": "M2M-100",
                "info": "Many-to-Many multilingual translation by Facebook. Direct translation between 100 languages.",
                "models": ["m2m100_418M (418MB)", "m2m100_1.2B (1.2GB)"],
                "help": "✅ M2M-100 models support 100 languages with direct translation. No English intermediate needed.",
                "available": True
            },
            3: {
                "name": "mBART",
                "info": "Multilingual BART by Facebook. Good quality for many languages.",
                "models": ["mbart-large-50-many-to-many-mmt (2.4GB)"],
                "help": "✅ mBART supports 50 languages with excellent quality. Larger model but very accurate.",
                "available": True
            }
        }
        
        info = model_info.get(index, model_info[0])
        
        # Update info label
        self.model_info_label.setText(info["info"])
        
        # Update model list
        self.model_list.clear()
        for model in info["models"]:
            self.model_list.addItem(model)
        
        # Update help text
        self.help_label.setText(info["help"])
        
        # Enable/disable buttons
        self.add_language_btn.setEnabled(info["available"])
        self.download_models_btn.setEnabled(info["available"])
        self.manage_models_btn.setEnabled(info["available"])
    
    def _add_language_pair(self):
        """Add a new language pair for the selected AI model."""
        selected_index = self.ai_model_combo.currentIndex()
        
        if selected_index == 0:  # MarianMT
            self.model_manager.add_marianmt_language_pair(self.model_list)
        else:
            # For multilingual models (NLLB, M2M-100, mBART), use Manage Models
            model_name = self.ai_model_combo.currentText().split(" (")[0]
            QMessageBox.information(
                self,
                "Use Manage Models",
                f"📦 {model_name} Model Download\n\n"
                f"For {model_name} models, please use the 'Manage Models' button.\n\n"
                f"You'll be able to:\n"
                f"• Choose model size\n"
                f"• Select language pairs\n"
                f"• Download and manage models"
            )
    
    def _download_selected_ai_model(self):
        """Download the selected AI model."""
        selected_index = self.ai_model_combo.currentIndex()
        
        if selected_index == 0:  # MarianMT
            selected_items = self.model_list.selectedItems()
            if not selected_items:
                QMessageBox.warning(self, "No Selection", "Please select a language pair from the list first.")
                return
            self.model_manager.show_marianmt_manager()
        else:
            # For multilingual models, open the universal model manager
            self.model_manager.show_marianmt_manager()
    
    def _manage_selected_ai_model(self):
        """Manage models for the selected AI model."""
        # All model types now use the universal model manager
        self.model_manager.show_marianmt_manager()

    
    def _create_quality_settings_section(self, parent_layout):
        """Create translation quality settings section."""
        quality_group = QGroupBox()
        self.set_translatable_text(quality_group, "translation_quality_section")
        layout = QVBoxLayout(quality_group)
        layout.setSpacing(12)
        layout.setContentsMargins(15, 20, 15, 15)
        
        # Quality/Speed tradeoff slider
        quality_label = self._create_label("", bold=True)
        self.set_translatable_text(quality_label, "translation_quality_tradeoff_label")
        layout.addWidget(quality_label)
        
        slider_layout = QHBoxLayout()
        slider_layout.setSpacing(10)
        
        speed_label = QLabel("Fast")
        speed_label.setStyleSheet("font-size: 8pt; color: #666666;")
        slider_layout.addWidget(speed_label)
        
        self.quality_slider = QSlider(Qt.Orientation.Horizontal)
        self.quality_slider.setRange(0, 100)
        self.quality_slider.setValue(70)
        self.quality_slider.setTickPosition(QSlider.TickPosition.TicksBelow)
        self.quality_slider.setTickInterval(25)
        self.quality_slider.valueChanged.connect(self._update_quality_label)
        self.quality_slider.sliderReleased.connect(self.on_change)
        slider_layout.addWidget(self.quality_slider)
        
        quality_right_label = QLabel("High Quality")
        quality_right_label.setStyleSheet("font-size: 8pt; color: #666666;")
        slider_layout.addWidget(quality_right_label)
        
        self.quality_value_label = QLabel("High")
        self.quality_value_label.setStyleSheet("font-weight: 600; font-size: 9pt; min-width: 80px;")
        slider_layout.addWidget(self.quality_value_label)
        
        layout.addLayout(slider_layout)
        
        quality_desc = QLabel()
        self.set_translatable_text(quality_desc, "translation_quality_desc")
        quality_desc.setWordWrap(True)
        quality_desc.setStyleSheet("color: #666666; font-size: 8pt; margin-top: 5px;")
        layout.addWidget(quality_desc)
        
        parent_layout.addWidget(quality_group)
    
    def _update_quality_label(self, value):
        """Update quality value label when slider changes."""
        if value < 25:
            quality_text = "Fast"
        elif value < 50:
            quality_text = "Balanced"
        elif value < 75:
            quality_text = "High"
        else:
            quality_text = "Maximum"
        
        self.quality_value_label.setText(quality_text)
    

        
        # Update dictionary overview initially
        self._update_dictionary_overview()
    
    def _update_dictionary_overview(self):
        """Update dictionary overview for current language pair."""
        if self.dict_overview_label is None:
            return
            
        if not self.config_manager:
            self.dict_overview_label.setText(
                "<b>Status:</b> Configuration not available<br>"
                "<i>Dictionary information will be available after configuration loads</i>"
            )
            return
        
        source_lang = self.config_manager.get_setting('translation.source_language', 'en')
        target_lang = self.config_manager.get_setting('translation.target_language', 'de')
        
        overview_text = self.dictionary_manager.get_dictionary_overview(source_lang, target_lang)
        self.dict_overview_label.setText(overview_text)
    
    def _create_advanced_section(self, parent_layout):
        """Create advanced translation settings section."""
        group = QGroupBox("⚙️ Advanced Settings")
        layout = QVBoxLayout(group)
        layout.setSpacing(8)
        layout.setContentsMargins(15, 20, 15, 15)
        
        # Fallback enabled
        self.fallback_enabled_check = QCheckBox("🔄 Enable automatic fallback to other engines")
        self.fallback_enabled_check.setChecked(True)
        self.fallback_enabled_check.stateChanged.connect(self.on_change)
        layout.addWidget(self.fallback_enabled_check)
        
        fallback_desc = QLabel("  • If primary engine fails, automatically try other available engines")
        fallback_desc.setStyleSheet("color: #666666; font-size: 8pt; margin-left: 20px; margin-bottom: 10px;")
        layout.addWidget(fallback_desc)
        
        # Batch translation
        self.batch_translation_check = QCheckBox("⚡ Enable batch translation optimization")
        self.batch_translation_check.setChecked(True)
        self.batch_translation_check.stateChanged.connect(self.on_change)
        layout.addWidget(self.batch_translation_check)
        
        batch_desc = QLabel("  • Process multiple text segments together for better performance")
        batch_desc.setStyleSheet("color: #666666; font-size: 8pt; margin-left: 20px;")
        layout.addWidget(batch_desc)
        
        # Context-aware translation
        self.context_aware_check = QCheckBox("🧠 Enable context-aware translation")
        self.context_aware_check.setChecked(True)
        self.context_aware_check.stateChanged.connect(self.on_change)
        layout.addWidget(self.context_aware_check)
        
        context_desc = QLabel("  • Use surrounding text for better translation accuracy")
        context_desc.setStyleSheet("color: #666666; font-size: 8pt; margin-left: 20px;")
        layout.addWidget(context_desc)
        
        # Preserve formatting
        self.preserve_formatting_check = QCheckBox("📝 Preserve text formatting")
        self.preserve_formatting_check.setChecked(True)
        self.preserve_formatting_check.stateChanged.connect(self.on_change)
        layout.addWidget(self.preserve_formatting_check)
        
        format_desc = QLabel("  • Maintain line breaks, spacing, and special characters")
        format_desc.setStyleSheet("color: #666666; font-size: 8pt; margin-left: 20px;")
        layout.addWidget(format_desc)
        
        parent_layout.addWidget(group)

    
    def load_config(self):
        """Load configuration from config manager (user_config.json only)."""
        if not self.config_manager:
            return
        
        try:
            print("[TRANSLATION TAB] Loading settings from user_config.json")
            
            # Load translation engine from user_config.json
            engine = self.config_manager.get_setting('translation.primary_engine', 'marianmt_gpu')
            
            # NEW: Phase 2 - Check if it's a plugin first
            found = False
            
            # Check plugins
            for idx, plugin in enumerate(self.available_plugins):
                if plugin['name'] == engine:
                    # Select the plugin radio button
                    plugin_radio = self.plugin_radios.get(plugin['name'])
                    if plugin_radio:
                        plugin_radio.setChecked(True)
                        found = True
                    break
            
            # If not a plugin, check cloud engines
            if not found:
                if engine == 'google_free' and hasattr(self, 'google_free_radio'):
                    self.google_free_radio.setChecked(True)
                elif engine == 'libretranslate' and hasattr(self, 'libretranslate_radio'):
                    self.libretranslate_radio.setChecked(True)
                elif engine == 'google' and hasattr(self, 'google_api_radio'):
                    self.google_api_radio.setChecked(True)
                elif engine == 'deepl' and hasattr(self, 'deepl_api_radio'):
                    self.deepl_api_radio.setChecked(True)
                elif engine == 'azure' and hasattr(self, 'azure_api_radio'):
                    self.azure_api_radio.setChecked(True)
                else:
                    # Default to first plugin if available
                    if self.available_plugins and self.plugin_radios:
                        first_plugin = self.available_plugins[0]
                        first_radio = self.plugin_radios.get(first_plugin['name'])
                        if first_radio:
                            first_radio.setChecked(True)
            
            # Load API keys from user_config.json and decrypt them
            google_key = self.config_manager.get_setting('translation.google_api_key', '')
            deepl_key = self.config_manager.get_setting('translation.deepl_api_key', '')
            azure_key = self.config_manager.get_setting('translation.azure_api_key', '')
            
            if ENCRYPTION_AVAILABLE:
                google_key = decrypt_api_key(google_key) if google_key else ''
                deepl_key = decrypt_api_key(deepl_key) if deepl_key else ''
                azure_key = decrypt_api_key(azure_key) if azure_key else ''
            
            self.google_api_key_edit.setText(google_key)
            self.deepl_api_key_edit.setText(deepl_key)
            self.azure_api_key_edit.setText(azure_key)
            
            # Load quality setting
            quality = self.config_manager.get_setting('translation.quality_level', 70)
            self.quality_slider.setValue(quality)
            self._update_quality_label(quality)
            
            # REMOVED: Cache settings now in Storage tab
            # cache_enabled = self.config_manager.get_setting('translation.cache_enabled', True)
            # cache_size = self.config_manager.get_setting('translation.cache_size', 1000)
            # self.cache_enabled_check.setChecked(cache_enabled)
            # self.cache_size_spin.setValue(cache_size)
            
            # Load advanced settings
            self.fallback_enabled_check.setChecked(
                self.config_manager.get_setting('translation.fallback_enabled', True)
            )
            self.batch_translation_check.setChecked(
                self.config_manager.get_setting('translation.batch_translation', True)
            )
            self.context_aware_check.setChecked(
                self.config_manager.get_setting('translation.context_aware', True)
            )
            self.preserve_formatting_check.setChecked(
                self.config_manager.get_setting('translation.preserve_formatting', True)
            )
            
            # Load quality filter settings
            if hasattr(self, 'quality_filter_check'):
                self.quality_filter_check.setChecked(
                    self.config_manager.get_setting('translation.quality_filter_enabled', True)
                )
            if hasattr(self, 'filter_mode_combo'):
                self.filter_mode_combo.setCurrentIndex(
                    self.config_manager.get_setting('translation.quality_filter_mode', 0)
                )
            
            # Update dictionary overview
            self._update_dictionary_overview()
            
            # Save the original state after loading
            self._original_state = self._get_current_state()
            
        except Exception as e:
            print(f"[ERROR] Failed to load translation settings: {e}")
            import traceback
            traceback.print_exc()
    
    def save_config(self):
        """Save configuration to config manager (user_config.json only)."""
        if not self.config_manager:
            return
        
        try:
            
            # Get selected engine
            selected_button_id = self.engine_button_group.checkedId()
            
            # NEW: Phase 2 - Check if it's a plugin
            engine = None
            
            # Determine which engine is selected
            engine = 'marianmt_gpu'  # Default
            
            # Check plugin radios
            for plugin_name, radio in self.plugin_radios.items():
                if radio.isChecked():
                    engine = plugin_name
                    break
            
            # Check cloud engine radios (free)
            if hasattr(self, 'google_free_radio') and self.google_free_radio.isChecked():
                engine = 'google_free'
            elif hasattr(self, 'libretranslate_radio') and self.libretranslate_radio.isChecked():
                engine = 'libretranslate'
            # Check premium cloud engine radios
            elif hasattr(self, 'google_api_radio') and self.google_api_radio.isChecked():
                engine = 'google'
            elif hasattr(self, 'deepl_api_radio') and self.deepl_api_radio.isChecked():
                engine = 'deepl'
            elif hasattr(self, 'azure_api_radio') and self.azure_api_radio.isChecked():
                engine = 'azure'
            
            print(f"[TRANSLATION TAB] Saving engine: {engine} (button_id: {selected_button_id})")
            
            # Get API keys and encrypt them
            google_key = self.google_api_key_edit.text().strip()
            deepl_key = self.deepl_api_key_edit.text().strip()
            azure_key = self.azure_api_key_edit.text().strip()
            
            if ENCRYPTION_AVAILABLE:
                google_key = encrypt_api_key(google_key) if google_key else ''
                deepl_key = encrypt_api_key(deepl_key) if deepl_key else ''
                azure_key = encrypt_api_key(azure_key) if azure_key else ''
            
            # Save to config manager
            self.config_manager.set_setting('translation.primary_engine', engine)
            self.config_manager.set_setting('translation.google_api_key', google_key)
            self.config_manager.set_setting('translation.deepl_api_key', deepl_key)
            self.config_manager.set_setting('translation.azure_api_key', azure_key)
            self.config_manager.set_setting('translation.quality_level', self.quality_slider.value())
            # REMOVED: Cache settings now in Storage tab
            # self.config_manager.set_setting('translation.cache_enabled', self.cache_enabled_check.isChecked())
            # self.config_manager.set_setting('translation.cache_size', self.cache_size_spin.value())
            self.config_manager.set_setting('translation.fallback_enabled', self.fallback_enabled_check.isChecked())
            self.config_manager.set_setting('translation.batch_translation', self.batch_translation_check.isChecked())
            self.config_manager.set_setting('translation.context_aware', self.context_aware_check.isChecked())
            self.config_manager.set_setting('translation.preserve_formatting', self.preserve_formatting_check.isChecked())
            
            # Save quality filter settings
            self.config_manager.set_setting('translation.quality_filter_enabled', self.quality_filter_check.isChecked())
            self.config_manager.set_setting('translation.quality_filter_mode', self.filter_mode_combo.currentIndex())
            
            # Update original state after saving
            self._original_state = self._get_current_state()
            
            # CRITICAL FIX: Save the configuration file to disk!
            if hasattr(self.config_manager, 'save_config'):
                self.config_manager.save_config()
            elif hasattr(self.config_manager, 'save_configuration'):
                config_dict = self.config_manager._config_to_dict(self.config_manager._config)
                self.config_manager.save_configuration(config_dict)
            
            print(f"[INFO] Translation settings saved to disk")
            
        except Exception as e:
            print(f"[ERROR] Failed to save translation settings: {e}")
            import traceback
            traceback.print_exc()
    
    def validate(self) -> bool:
        """Validate settings including API key format validation."""
        # Check if cloud service is selected but no API key provided
        selected_button_id = self.engine_button_group.checkedId()
        
        # Free services (0: MarianMT, 1: Google Free, 2: LibreTranslate) don't need API keys
        if selected_button_id == 3:  # Google API
            if not self.google_api_key_edit.text().strip():
                QMessageBox.warning(
                    self,
                    "Missing API Key",
                    "Google Translate API is selected but no API key is provided.\n\n"
                    "Please enter your Google Translate API key or select a different engine."
                )
                return False
        elif selected_button_id == 4:  # DeepL
            if not self.deepl_api_key_edit.text().strip():
                QMessageBox.warning(
                    self,
                    "Missing API Key",
                    "DeepL is selected but no API key is provided.\n\n"
                    "Please enter your DeepL API key or select a different engine."
                )
                return False
        elif selected_button_id == 5:  # Azure
            if not self.azure_api_key_edit.text().strip():
                QMessageBox.warning(
                    self,
                    "Missing API Key",
                    "Azure Translator is selected but no API key is provided.\n\n"
                    "Please enter your Azure Translator API key or select a different engine."
                )
                return False
        
        return True
