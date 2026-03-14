"""
Engine Selection Section for the Translation Settings Tab.

Runtime status, translation engine selection (plugin-based and cloud-based),
API key management, and local AI model management.
"""

from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QGroupBox,
    QLabel, QComboBox, QRadioButton, QPushButton,
    QButtonGroup, QMessageBox,
    QListWidget, QLineEdit
)
from PyQt6.QtCore import pyqtSignal, Qt

import logging
from pathlib import Path

from .api_manager import TranslationAPIManager
from .model_manager import TranslationModelManager
from app.localization import TranslatableMixin, tr

logger = logging.getLogger(__name__)


class EngineSection(TranslatableMixin, QWidget):
    """Translation engine selection, API key management, and local model management."""

    settingChanged = pyqtSignal()

    def __init__(self, config_manager=None, pipeline=None, parent=None):
        super().__init__(parent)

        self.config_manager = config_manager
        self.pipeline = pipeline

        # Managers
        self.api_manager = TranslationAPIManager(parent=self)
        self.model_manager = TranslationModelManager(parent=self, config_manager=config_manager)

        from .test_manager import TranslationTestManager
        self.test_manager = TranslationTestManager(parent=self)

        # Plugin discovery
        self.translation_layer = None
        self.available_plugins = []
        self.plugin_radios = {}

        if pipeline and hasattr(pipeline, 'translation_layer'):
            self.translation_layer = pipeline.translation_layer
            self._discover_translation_plugins()

        self.engine_button_group = None

        # API key widgets
        self.google_api_key_edit = None
        self.deepl_api_key_edit = None
        self.azure_api_key_edit = None

        # Model management widgets
        self.ai_model_combo = None
        self.model_list = None
        self.model_info_label = None
        self.help_label = None
        self.add_language_btn = None
        self.download_models_btn = None
        self.manage_models_btn = None

        self._init_ui()

    def _init_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(10)

        self._create_engine_selection_section(layout)
        self._create_cloud_services_section(layout)
        self._create_local_engines_section(layout)

    def on_change(self):
        """Called when any setting changes."""
        self.settingChanged.emit()

    def _create_label(self, text: str, bold: bool = False) -> QLabel:
        """Create a label with consistent styling."""
        label = QLabel(text)
        if bold:
            label.setStyleSheet("font-weight: 600; font-size: 9pt;")
        else:
            label.setStyleSheet("font-size: 9pt;")
        return label

    def _set_placeholder_text(self, line_edit, key):
        """Helper to set placeholder text from translation key."""
        from app.localization import tr
        line_edit.setPlaceholderText(tr(key))

    @staticmethod
    def _make_whitespace_stripper(line_edit: QLineEdit):
        """Return a slot that strips all whitespace from a QLineEdit on every change."""
        def _strip(text: str) -> None:
            cleaned = ''.join(text.split())
            if cleaned != text:
                line_edit.blockSignals(True)
                pos = line_edit.cursorPosition()
                line_edit.setText(cleaned)
                line_edit.setCursorPosition(min(pos, len(cleaned)))
                line_edit.blockSignals(False)
        return _strip

    def _get_effective_runtime_mode(self) -> str:
        """
        Resolve runtime mode against actual hardware.

        If config says GPU but CUDA is not available, this returns CPU so
        labels and badges stay accurate on CPU-only systems.
        """
        configured = self.config_manager.get_setting('performance.runtime_mode', 'auto') if self.config_manager else 'auto'
        cuda_available = False
        try:
            import torch
            cuda_available = bool(torch.cuda.is_available())
        except Exception:
            cuda_available = False

        if configured == 'gpu' and not cuda_available:
            return 'cpu'
        if configured == 'auto':
            return 'gpu' if cuda_available else 'cpu'
        return configured

    # ── Plugin discovery ─────────────────────────────────────────────

    def _discover_translation_plugins(self):
        """Discover available translation plugins (Phase 2)."""
        if not self.translation_layer:
            logger.debug("No translation layer available for plugin discovery")
            return

        try:
            plugin_manager = self.translation_layer.plugin_manager
            self.available_plugins = []

            discovered = plugin_manager.discover_plugins()

            for plugin_metadata in discovered:
                raw_data = plugin_manager.registry.get_plugin_raw_data(plugin_metadata.name)

                plugin_info = {
                    'name': plugin_metadata.name,
                    'display_name': plugin_metadata.display_name,
                    'description': plugin_metadata.description,
                    'version': plugin_metadata.version,
                    'metadata': raw_data if raw_data else plugin_metadata.to_dict(),
                    'loaded': self._is_translation_plugin_loaded(plugin_manager, plugin_metadata.name)
                }
                self.available_plugins.append(plugin_info)

            self.available_plugins = [
                p for p in self.available_plugins
                if not p.get('metadata', {}).get('hidden', False)
            ]

            logger.info("Discovered %d translation plugins (after hiding internal)", len(self.available_plugins))
            for plugin in self.available_plugins:
                logger.debug("  - %s (loaded: %s)", plugin['display_name'], plugin['loaded'])

        except Exception as e:
            logger.error("Failed to discover plugins: %s", e, exc_info=True)

    def _is_translation_plugin_loaded(self, plugin_manager, plugin_name: str) -> bool:
        """
        Return whether a translation plugin is loaded at runtime.

        MarianMT is frequently registered under the base engine name
        (``marianmt``) even when the plugin id is ``marianmt_gpu``.
        """
        candidates = [plugin_name]
        if plugin_name.endswith("_gpu") or plugin_name.endswith("_cpu"):
            candidates.append(plugin_name.rsplit("_", 1)[0])

        try:
            for candidate in candidates:
                if plugin_manager.registry.is_engine_loaded(candidate):
                    return True
        except Exception:
            pass

        # TranslationFacade runtime registry check (covers direct registration
        # path used by MarianMT in startup pipeline).
        try:
            engine_mgr = getattr(self.translation_layer, "_engine_mgr", None)
            if engine_mgr is not None:
                for candidate in candidates:
                    engine = engine_mgr.get_engine(candidate)
                    if engine and engine.is_available():
                        return True
        except Exception:
            pass

        return False

    def _add_plugin_engine_option(self, layout, plugin_info, button_id):
        """Add a plugin engine option with GPU/CPU indicator (Phase 2)."""
        plugin_layout = QHBoxLayout()
        plugin_layout.setSpacing(10)

        # Radio button
        display_name = plugin_info['display_name']
        if plugin_info.get('name') == 'marianmt_gpu' and self._get_effective_runtime_mode() == 'cpu':
            display_name = display_name.replace("GPU/CPU", "CPU").replace("GPU / CPU", "CPU")
        radio = QRadioButton(display_name)
        radio.toggled.connect(self.on_change)
        self.engine_button_group.addButton(radio, button_id)
        self.plugin_radios[plugin_info['name']] = radio
        plugin_layout.addWidget(radio)

        metadata = plugin_info.get('metadata', {})
        runtime_req = metadata.get('runtime_requirements', {})
        internet_req = runtime_req.get('internet', {})
        api_key_required = metadata.get('api_key_required', False)

        if internet_req.get('required', False):
            if api_key_required:
                indicator = QLabel("🌐🔑")
                indicator.setStyleSheet("font-size: 12pt;")
                indicator.setToolTip(tr("engine_indicator_internet_api_tooltip"))
            else:
                indicator = QLabel("🌐")
                indicator.setStyleSheet("font-size: 12pt;")
                indicator.setToolTip(tr("engine_indicator_internet_tooltip"))
            plugin_layout.addWidget(indicator)
        elif runtime_req:
            gpu_req = runtime_req.get('gpu', {})
            cpu_req = runtime_req.get('cpu', {})

            if gpu_req.get('required'):
                indicator = QLabel(tr("engine_indicator_gpu_only"))
                indicator.setStyleSheet("color: #FF9800; font-weight: bold; font-size: 9pt;")
                indicator.setToolTip(tr("engine_indicator_gpu_only_tooltip"))
            elif gpu_req.get('recommended') and cpu_req.get('supported'):
                runtime_mode = self._get_effective_runtime_mode()
                if runtime_mode == 'gpu':
                    indicator = QLabel(tr("engine_indicator_gpu"))
                    indicator.setStyleSheet("color: #4CAF50; font-weight: bold; font-size: 9pt;")
                    indicator.setToolTip(tr("engine_indicator_gpu_tooltip"))
                elif runtime_mode == 'cpu':
                    indicator = QLabel(tr("engine_indicator_cpu"))
                    indicator.setStyleSheet("color: #FF9800; font-weight: bold; font-size: 9pt;")
                    indicator.setToolTip(tr("engine_indicator_cpu_slower_tooltip"))
                else:
                    indicator = QLabel(tr("engine_indicator_gpu_cpu"))
                    indicator.setStyleSheet("color: #4CAF50; font-weight: bold; font-size: 9pt;")
                    indicator.setToolTip(tr("engine_indicator_gpu_cpu_tooltip"))
            else:
                indicator = QLabel(tr("engine_indicator_cpu"))
                indicator.setStyleSheet("color: #2196F3; font-weight: bold; font-size: 9pt;")
                indicator.setToolTip(tr("engine_indicator_cpu_only_tooltip"))

            plugin_layout.addWidget(indicator)

        # Loaded status
        if plugin_info['loaded']:
            status_label = QLabel(tr("engine_plugin_loaded"))
            status_label.setStyleSheet("color: #4CAF50; font-size: 8pt;")
            status_label.setToolTip(tr("engine_plugin_loaded_tooltip"))
        else:
            status_label = QLabel(tr("engine_plugin_not_loaded"))
            status_label.setStyleSheet("color: #666666; font-size: 8pt;")
            status_label.setToolTip(tr("engine_plugin_not_loaded_tooltip"))
        plugin_layout.addWidget(status_label)

        # Test button
        test_btn = self._create_test_button()
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

    _TEST_BTN_STYLE = (
        "QPushButton { background: transparent; color: #4FC3F7; border: 1px solid #4FC3F7;"
        " border-radius: 3px; padding: 2px 10px; font-size: 8pt; }"
        "QPushButton:hover { background: #4FC3F7; color: #1a1a2e; }"
        "QPushButton:pressed { background: #0288D1; border-color: #0288D1; color: #ffffff; }"
    )

    def _create_test_button(self) -> QPushButton:
        """Create a compact, styled test button."""
        btn = QPushButton()
        self.set_translatable_text(btn, "engine_test_btn")
        btn.setMaximumWidth(70)
        btn.setCursor(Qt.CursorShape.PointingHandCursor)
        btn.setStyleSheet(self._TEST_BTN_STYLE)
        return btn

    def _test_plugin_engine(self, plugin_name):
        """Test a plugin-based translation engine."""
        try:
            self.test_manager.test_translation_engine(plugin_name)
        except Exception as e:
            QMessageBox.warning(
                self,
                tr("engine_test_failed_title"),
                f"{tr('engine_test_failed_msg')} '{plugin_name}':\n\n{str(e)}"
            )

    # ── MarianMT model utilities ─────────────────────────────────────

    def _get_downloaded_marianmt_models(self):
        """Get list of actually downloaded MarianMT models (Phase 3)."""
        try:
            cache_dir = Path.home() / '.cache' / 'huggingface' / 'hub'

            if not cache_dir.exists():
                return []

            models = []

            for model_dir in cache_dir.iterdir():
                if model_dir.is_dir() and 'opus-mt-' in model_dir.name:
                    try:
                        parts = model_dir.name.split('--')
                        if len(parts) >= 3 and parts[1] == 'Helsinki-NLP':
                            model_name = parts[2]
                            lang_pair = model_name.replace('opus-mt-', '')

                            if '-' in lang_pair:
                                src, tgt = lang_pair.split('-', 1)

                                try:
                                    total_size = sum(
                                        f.stat().st_size
                                        for f in model_dir.rglob('*')
                                        if f.is_file()
                                    )
                                    size_mb = total_size / (1024 * 1024)
                                    size_str = f"{size_mb:.0f} MB"
                                except Exception as e:
                                    logger.debug("Could not calculate model size for %s: %s", model_dir, e)
                                    size_str = "Unknown size"

                                models.append({
                                    'name': f"{src.upper()} → {tgt.upper()}",
                                    'size': size_str,
                                    'src': src,
                                    'tgt': tgt
                                })
                    except Exception as e:
                        logger.debug("Error scanning model directory %s: %s", model_dir, e)
                        continue

            return models

        except Exception as e:
            logger.error("Failed to get downloaded models: %s", e, exc_info=True)
            return []

    def _is_model_downloaded(self, src_lang, tgt_lang):
        """Check if a specific model is downloaded (Phase 3)."""
        try:
            cache_dir = Path.home() / '.cache' / 'huggingface' / 'hub'

            if not cache_dir.exists():
                return False

            model_name = f"opus-mt-{src_lang}-{tgt_lang}"

            for model_dir in cache_dir.iterdir():
                if model_dir.is_dir() and model_name in model_dir.name:
                    snapshots_dir = model_dir / 'snapshots'
                    if snapshots_dir.exists():
                        for snapshot in snapshots_dir.iterdir():
                            if snapshot.is_dir() and any(snapshot.iterdir()):
                                return True

            return False
        except Exception as e:
            logger.error("Failed to check model download status: %s", e)
            return False

    def _get_available_marianmt_models(self):
        """Get list of available MarianMT models to download (Phase 3)."""
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

    # ── UI section builders ──────────────────────────────────────────

    def _create_runtime_status_section(self, parent_layout):
        """Create runtime status section showing GPU/CPU mode (Phase 1)."""
        runtime_group = QGroupBox()
        self.set_translatable_text(runtime_group, "translation_runtime_status_section")
        layout = QVBoxLayout(runtime_group)
        layout.setSpacing(8)
        layout.setContentsMargins(15, 20, 15, 15)

        runtime_mode = self._get_effective_runtime_mode()

        if runtime_mode == 'gpu':
            status_text = tr("engine_runtime_gpu")
            color = "#4CAF50"
            icon = "⚡"
        elif runtime_mode == 'cpu':
            status_text = tr("engine_runtime_cpu")
            color = "#FF9800"
            icon = "💻"
        else:
            status_text = tr("engine_runtime_auto")
            color = "#2196F3"
            icon = "🔄"

        status_label = QLabel(f"{icon} {status_text}")
        status_label.setStyleSheet(f"color: {color}; font-size: 10pt; font-weight: bold;")
        layout.addWidget(status_label)

        try:
            import torch
            if torch.cuda.is_available():
                gpu_name = torch.cuda.get_device_name(0)
                gpu_label = QLabel(tr("engine_gpu_available").format(gpu_name=gpu_name))
                gpu_label.setStyleSheet("color: #4CAF50; font-size: 9pt;")
                layout.addWidget(gpu_label)

                cuda_version = torch.version.cuda
                cuda_label = QLabel(tr("engine_cuda_version").format(cuda_version=cuda_version))
                cuda_label.setStyleSheet("color: #666666; font-size: 8pt;")
                layout.addWidget(cuda_label)
            else:
                gpu_label = QLabel(tr("engine_no_gpu_detected"))
                gpu_label.setStyleSheet("color: #FF9800; font-size: 9pt;")
                layout.addWidget(gpu_label)
        except Exception as e:
            error_label = QLabel(tr("engine_gpu_detect_error").format(error=str(e)))
            error_label.setStyleSheet("color: #FF9800; font-size: 8pt;")
            layout.addWidget(error_label)

        link_label = QLabel(tr("engine_runtime_change_hint"))
        link_label.setWordWrap(True)
        link_label.setStyleSheet(
            "color: #2196F3; font-size: 8pt; margin-top: 8px; padding: 8px; "
            "background-color: rgba(33, 150, 243, 0.1); border-radius: 4px;"
        )
        layout.addWidget(link_label)

        parent_layout.addWidget(runtime_group)

    def _create_engine_selection_section(self, parent_layout):
        """Create translation engine selection section."""
        self._create_runtime_status_section(parent_layout)

        engine_group = QGroupBox()
        self.set_translatable_text(engine_group, "translation_engine_section")
        layout = QVBoxLayout(engine_group)
        layout.setSpacing(12)
        layout.setContentsMargins(15, 20, 15, 15)

        engine_label = self._create_label("", bold=True)
        self.set_translatable_text(engine_label, "translation_select_engine_label")
        layout.addWidget(engine_label)

        self.engine_button_group = QButtonGroup()

        if not self.available_plugins:
            error_label = QLabel(tr("engine_no_plugins_found"))
            error_label.setStyleSheet("color: #FF5252; font-size: 10pt; font-weight: bold;")
            layout.addWidget(error_label)

            error_desc = QLabel(tr("engine_no_plugins_desc"))
            error_desc.setWordWrap(True)
            error_desc.setStyleSheet("color: #FF5252; font-size: 9pt; margin-top: 5px;")
            layout.addWidget(error_desc)
        else:
            offline_plugins = []
            cloud_free_plugins = []
            premium_plugins = []

            for plugin in self.available_plugins:
                metadata = plugin.get('metadata', {})
                runtime_req = metadata.get('runtime_requirements', {})
                internet_req = runtime_req.get('internet', {})
                api_key_required = metadata.get('api_key_required', False)

                if internet_req.get('required', False):
                    if api_key_required:
                        premium_plugins.append(plugin)
                    else:
                        cloud_free_plugins.append(plugin)
                else:
                    offline_plugins.append(plugin)

            if offline_plugins:
                plugin_section_label = QLabel()
                self.set_translatable_text(plugin_section_label, "engine_local_ai_section")
                plugin_section_label.setStyleSheet("color: #4CAF50; font-size: 10pt; margin-top: 5px;")
                layout.addWidget(plugin_section_label)

                button_id = 0
                for plugin in offline_plugins:
                    self._add_plugin_engine_option(layout, plugin, button_id)
                    button_id += 1
            else:
                button_id = 0

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

            separator = QLabel("─" * 80)
            separator.setStyleSheet("color: #666666; margin-top: 10px; margin-bottom: 10px;")
            layout.addWidget(separator)

            cloud_label = QLabel()
            self.set_translatable_text(cloud_label, "engine_cloud_services_label")
            cloud_label.setStyleSheet("color: #2196F3; font-size: 10pt;")
            layout.addWidget(cloud_label)

            internet_disclaimer = QLabel()
            self.set_translatable_text(internet_disclaimer, "translation_internet_disclaimer")
            internet_disclaimer.setWordWrap(True)
            internet_disclaimer.setStyleSheet(
                "color: #FF9800; font-size: 9pt; margin-top: 5px; margin-bottom: 10px; "
                "padding: 8px; background-color: rgba(255, 152, 0, 0.1); border-radius: 4px; "
                "border-left: 3px solid #FF9800;"
            )
            layout.addWidget(internet_disclaimer)

            for plugin in cloud_free_plugins:
                self._add_plugin_engine_option(layout, plugin, button_id)
                button_id += 1

            if premium_plugins:
                separator2 = QLabel("─" * 80)
                separator2.setStyleSheet("color: #666666; margin-top: 10px; margin-bottom: 5px;")
                layout.addWidget(separator2)

                premium_label = QLabel()
                self.set_translatable_text(premium_label, "engine_premium_services_label")
                premium_label.setStyleSheet("color: #9C27B0; font-size: 10pt;")
                layout.addWidget(premium_label)

                premium_disclaimer = QLabel()
                self.set_translatable_text(premium_disclaimer, "translation_premium_disclaimer")
                premium_disclaimer.setWordWrap(True)
                premium_disclaimer.setStyleSheet(
                    "color: #9C27B0; font-size: 9pt; margin-top: 5px; margin-bottom: 10px; "
                    "padding: 8px; background-color: rgba(156, 39, 176, 0.1); border-radius: 4px; "
                    "border-left: 3px solid #9C27B0;"
                )
                layout.addWidget(premium_disclaimer)

                for plugin in premium_plugins:
                    self._add_plugin_engine_option(layout, plugin, button_id)
                    button_id += 1

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
        self.google_api_key_edit.textChanged.connect(self._make_whitespace_stripper(self.google_api_key_edit))
        self.google_api_key_edit.textChanged.connect(self.on_change)
        google_layout.addWidget(self.google_api_key_edit)

        google_test_btn = self._create_test_button()
        google_test_btn.clicked.connect(lambda: self.api_manager.test_api_key("google_api", self.google_api_key_edit.text().strip()))
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
        self.deepl_api_key_edit.textChanged.connect(self._make_whitespace_stripper(self.deepl_api_key_edit))
        self.deepl_api_key_edit.textChanged.connect(self.on_change)
        deepl_layout.addWidget(self.deepl_api_key_edit)

        deepl_test_btn = self._create_test_button()
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
        self.azure_api_key_edit.textChanged.connect(self._make_whitespace_stripper(self.azure_api_key_edit))
        self.azure_api_key_edit.textChanged.connect(self.on_change)
        azure_layout.addWidget(self.azure_api_key_edit)

        azure_test_btn = self._create_test_button()
        azure_test_btn.clicked.connect(lambda: self.api_manager.test_api_key("azure", self.azure_api_key_edit.text().strip()))
        azure_layout.addWidget(azure_test_btn)

        layout.addLayout(azure_layout)

        azure_help = QLabel()
        self.set_translatable_text(azure_help, "translation_azure_help")
        azure_help.setStyleSheet("color: #666666; font-size: 8pt; margin-left: 5px;")
        azure_help.setWordWrap(True)
        layout.addWidget(azure_help)

        parent_layout.addWidget(cloud_group)

    def _create_local_engines_section(self, parent_layout):
        """Create local translation engines section with REAL model status (Phase 3)."""
        marianmt_group = QGroupBox()
        self.set_translatable_text(marianmt_group, "translation_marianmt_section")
        layout = QVBoxLayout(marianmt_group)
        layout.setSpacing(12)
        layout.setContentsMargins(15, 20, 15, 15)

        downloaded_models = self._get_downloaded_marianmt_models()

        if downloaded_models:
            downloaded_label = QLabel(tr("engine_downloaded_models_count").format(count=len(downloaded_models)))
            downloaded_label.setStyleSheet("color: #4CAF50; font-size: 10pt;")
            layout.addWidget(downloaded_label)

            for model in downloaded_models:
                model_item = QLabel(f"  • {model['name']} - {model['size']}")
                model_item.setStyleSheet("color: #4CAF50; font-size: 9pt; margin-left: 10px;")
                layout.addWidget(model_item)

            separator = QLabel("─" * 80)
            separator.setStyleSheet("color: #666666; margin-top: 10px; margin-bottom: 10px;")
            layout.addWidget(separator)
        else:
            no_models_label = QLabel(tr("engine_no_models_downloaded"))
            no_models_label.setStyleSheet("color: #FF9800; font-size: 10pt; font-weight: bold;")
            layout.addWidget(no_models_label)

            help_text = QLabel(tr("engine_models_auto_download_help"))
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
            tr("engine_model_marianmt"),
            tr("engine_model_nllb"),
            tr("engine_model_m2m100"),
            tr("engine_model_mbart")
        ])
        self.ai_model_combo.setMinimumWidth(300)
        self.ai_model_combo.currentIndexChanged.connect(self._on_ai_model_changed)
        model_select_layout.addWidget(self.ai_model_combo)

        model_select_layout.addStretch()
        layout.addLayout(model_select_layout)

        self.model_info_label = QLabel()
        self.model_info_label.setWordWrap(True)
        self.model_info_label.setStyleSheet("color: #666666; font-size: 8pt; margin-top: 5px; margin-bottom: 10px;")
        layout.addWidget(self.model_info_label)

        # Available language pairs
        lang_pairs_label = self._create_label("", bold=True)
        self.set_translatable_text(lang_pairs_label, "translation_available_models_label")
        layout.addWidget(lang_pairs_label)

        lang_pairs_help = QLabel()
        self.set_translatable_text(lang_pairs_help, "translation_lang_pairs_help")
        lang_pairs_help.setWordWrap(True)
        lang_pairs_help.setStyleSheet("color: #666666; font-size: 8pt; margin-bottom: 5px;")
        layout.addWidget(lang_pairs_help)

        # Model list with download status
        self.model_list = QListWidget()
        self.model_list.setMaximumHeight(150)
        self.model_list.setSelectionMode(QListWidget.SelectionMode.SingleSelection)

        available_models = self._get_available_marianmt_models()
        for model in available_models:
            status_icon = "✅" if model['downloaded'] else "⬇️"
            status_text = f" ({tr('engine_model_downloaded')})" if model['downloaded'] else f" ({tr('engine_model_not_downloaded')})"
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

        self.help_label = QLabel()
        self.help_label.setWordWrap(True)
        self.help_label.setStyleSheet("color: #666666; font-size: 9pt; margin-top: 5px;")
        layout.addWidget(self.help_label)

        explanation_box = QLabel()
        self.set_translatable_text(explanation_box, "translation_how_it_works")
        explanation_box.setWordWrap(True)
        explanation_box.setStyleSheet(
            "color: #2196F3; font-size: 8pt; margin-top: 10px; padding: 10px; "
            "background-color: rgba(33, 150, 243, 0.1); border-radius: 4px; border-left: 3px solid #2196F3;"
        )
        layout.addWidget(explanation_box)

        self._on_ai_model_changed(0)

        parent_layout.addWidget(marianmt_group)

    # ── Model management event handlers ──────────────────────────────

    def _on_ai_model_changed(self, index):
        """Handle AI model selection change."""
        model_info = {
            0: {
                "name": "MarianMT",
                "info": tr("engine_marianmt_info"),
                "models": [
                    tr("engine_marianmt_model_en_de"),
                    tr("engine_marianmt_model_en_es"),
                    tr("engine_marianmt_model_en_fr"),
                    tr("engine_marianmt_model_en_ja"),
                    tr("engine_marianmt_model_de_en"),
                    tr("engine_marianmt_model_ja_en")
                ],
                "help": tr("engine_marianmt_help"),
                "available": True
            },
            1: {
                "name": "NLLB",
                "info": tr("engine_nllb_info"),
                "models": [tr("engine_nllb_model_600m"), tr("engine_nllb_model_1_3b"), tr("engine_nllb_model_3_3b")],
                "help": tr("engine_nllb_help"),
                "available": True
            },
            2: {
                "name": "M2M-100",
                "info": tr("engine_m2m100_info"),
                "models": [tr("engine_m2m100_model_418m"), tr("engine_m2m100_model_1_2b")],
                "help": tr("engine_m2m100_help"),
                "available": True
            },
            3: {
                "name": "mBART",
                "info": tr("engine_mbart_info"),
                "models": [tr("engine_mbart_model_large_50")],
                "help": tr("engine_mbart_help"),
                "available": True
            }
        }

        info = model_info.get(index, model_info[0])

        self.model_info_label.setText(info["info"])

        self.model_list.clear()
        for model in info["models"]:
            self.model_list.addItem(model)

        self.help_label.setText(info["help"])

        self.add_language_btn.setEnabled(info["available"])
        self.download_models_btn.setEnabled(info["available"])
        self.manage_models_btn.setEnabled(info["available"])

    def _add_language_pair(self):
        """Add a new language pair for the selected AI model."""
        selected_index = self.ai_model_combo.currentIndex()

        if selected_index == 0:  # MarianMT
            self.model_manager.add_marianmt_language_pair(self.model_list)
        else:
            model_name = self.ai_model_combo.currentText().split(" (")[0]
            QMessageBox.information(
                self,
                tr("engine_use_manage_models_title"),
                tr("engine_use_manage_models_msg").format(model_name=model_name)
            )

    def _download_selected_ai_model(self):
        """Download the selected AI model."""
        selected_index = self.ai_model_combo.currentIndex()

        if selected_index == 0:  # MarianMT
            selected_items = self.model_list.selectedItems()
            if not selected_items:
                QMessageBox.warning(self, tr("engine_no_selection_title"), tr("engine_no_selection_msg"))
                return
            self.model_manager.show_marianmt_manager()
        else:
            self.model_manager.show_marianmt_manager()

    def _manage_selected_ai_model(self):
        """Manage models for the selected AI model."""
        self.model_manager.show_marianmt_manager()

    # ── Public API for the parent tab ────────────────────────────────

    def get_selected_engine(self) -> str:
        """Return the name of the currently selected engine."""
        for plugin_name, radio in self.plugin_radios.items():
            if radio.isChecked():
                return plugin_name

        return 'marianmt_gpu'

    def get_current_state(self) -> dict:
        """Return current engine-related state for change tracking."""
        state = {}
        for plugin_name, radio in self.plugin_radios.items():
            if radio.isChecked():
                state['translation_engine'] = plugin_name
                break
        return state

    def load_config(self, config_manager):
        """Load engine selection and API keys from config."""
        if not config_manager:
            return

        try:
            engine = config_manager.get_setting('translation.engine', 'marianmt_gpu')

            plugin_radio = self.plugin_radios.get(engine)
            if plugin_radio:
                plugin_radio.setChecked(True)
            elif self.plugin_radios:
                # Prefer the schema default (marianmt_gpu) over alphabetical
                # first plugin to avoid accidentally selecting a cloud API.
                _FALLBACK_ORDER = [
                    'marianmt_gpu', 'google_free', 'libretranslate',
                ]
                fallback = None
                for name in _FALLBACK_ORDER:
                    if name in self.plugin_radios:
                        fallback = self.plugin_radios[name]
                        break
                if fallback is None:
                    fallback = next(iter(self.plugin_radios.values()), None)
                if fallback:
                    fallback.setChecked(True)
                    logger.warning(
                        "Configured engine '%s' not found in available plugins, "
                        "falling back to '%s'",
                        engine,
                        next(
                            (n for n, r in self.plugin_radios.items() if r is fallback),
                            '?',
                        ),
                    )

            # Load API keys
            google_key = config_manager.get_setting('translation.google_api_key', '')
            deepl_key = config_manager.get_setting('translation.deepl_api_key', '')
            azure_key = config_manager.get_setting('translation.azure_api_key', '')

            # One-time migration: decrypt any Fernet-encrypted keys left from
            # the removed encryption.py module (tokens start with 'gAAAAA')
            migrated = False
            try:
                from cryptography.fernet import Fernet as _MigFernet
                for key_name, key_val in [
                    ('translation.google_api_key', google_key),
                    ('translation.deepl_api_key', deepl_key),
                    ('translation.azure_api_key', azure_key),
                ]:
                    if key_val and key_val.startswith('gAAAAA'):
                        key_file = Path.home() / '.cache' / 'live_translator' / 'encryption.key'
                        if key_file.exists():
                            cipher = _MigFernet(key_file.read_bytes())
                            plaintext = cipher.decrypt(key_val.encode('utf-8')).decode('utf-8')
                            config_manager.set_setting(key_name, plaintext)
                            if key_name.endswith('google_api_key'):
                                google_key = plaintext
                            elif key_name.endswith('deepl_api_key'):
                                deepl_key = plaintext
                            elif key_name.endswith('azure_api_key'):
                                azure_key = plaintext
                            migrated = True
                if migrated:
                    config_manager.save_config()
                    logger.info("Migrated Fernet-encrypted API keys to plaintext")
            except Exception as e:
                logger.debug("Fernet key migration skipped (expected if cryptography not installed): %s", e)

            self.google_api_key_edit.setText(google_key)
            self.deepl_api_key_edit.setText(deepl_key)
            self.azure_api_key_edit.setText(azure_key)

        except Exception as e:
            logger.error("Failed to load engine settings: %s", e, exc_info=True)

    def save_config(self, config_manager):
        """Save engine selection and API keys to config (does not flush to disk)."""
        if not config_manager:
            return

        engine = self.get_selected_engine()
        logger.debug("Saving engine: %s", engine)

        google_key = self.google_api_key_edit.text().strip()
        deepl_key = self.deepl_api_key_edit.text().strip()
        azure_key = self.azure_api_key_edit.text().strip()

        config_manager.set_setting('translation.engine', engine)
        config_manager.set_setting('translation.google_api_key', google_key)
        config_manager.set_setting('translation.deepl_api_key', deepl_key)
        config_manager.set_setting('translation.azure_api_key', azure_key)

    def validate(self) -> bool:
        """Validate engine selection and API key requirements."""
        engine = self.get_selected_engine()

        if engine == 'google_api':
            if not self.google_api_key_edit.text().strip():
                QMessageBox.warning(
                    self,
                    tr("engine_missing_api_key_title"),
                    tr("engine_missing_google_api_key_msg")
                )
                return False
        elif engine == 'deepl':
            if not self.deepl_api_key_edit.text().strip():
                QMessageBox.warning(
                    self,
                    tr("engine_missing_api_key_title"),
                    tr("engine_missing_deepl_api_key_msg")
                )
                return False
        elif engine == 'azure':
            if not self.azure_api_key_edit.text().strip():
                QMessageBox.warning(
                    self,
                    tr("engine_missing_api_key_title"),
                    tr("engine_missing_azure_api_key_msg")
                )
                return False

        return True
