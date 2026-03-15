"""
Pipeline Management Tab — Central Pipeline Hub

Main container that composes all pipeline-related settings into a single
tabbed interface with 8 sub-tabs: Overview, Capture, OCR Engines,
Translation, AI Processing, Vision, Audio, and Plugins.

Previously standalone top-level tabs (Capture, OCR, Translation, LLM,
Overlay) are embedded here as sub-tabs.  Handles cross-section
synchronisation and config load/save.
"""

import json
import logging
from pathlib import Path

from app.utils.path_utils import get_plugin_enhancers_dir

from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QTabWidget, QMessageBox,
)
from PyQt6.QtCore import Qt, pyqtSignal, QTimer

from ui.common.widgets.scroll_area_no_wheel import ScrollAreaNoWheel
from app.localization import TranslatableMixin, tr

from .overview_section import OverviewSection
from .flow_section import ENGINE_NAMES, LANGUAGE_NAMES, get_ocr_engine_display
from .plugins_section import PluginsByStageSection
from .audio_translation_section import AudioTranslationSection
from .vision_section import VisionSettingsSection

logger = logging.getLogger(__name__)


class PipelineManagementTab(TranslatableMixin, QWidget):
    """Central pipeline hub with 8 sub-tabs covering every pipeline stage."""

    settingChanged = pyqtSignal()

    def __init__(self, config_manager=None, pipeline=None, parent=None):
        super().__init__(parent)

        self.config_manager = config_manager
        self.pipeline = None
        self._original_state = {}

        self._init_ui()

        self._stats_timer = QTimer(self)
        self._stats_timer.setInterval(500)
        self._stats_timer.timeout.connect(self._poll_stats)

        if pipeline is not None:
            self.set_pipeline(pipeline)

        QTimer.singleShot(100, self._update_metrics)

    # ------------------------------------------------------------------
    # UI construction
    # ------------------------------------------------------------------

    def _init_ui(self):
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.setSpacing(0)

        tab_widget = QTabWidget()

        # -- Internal sections (always created) --
        self.overview = OverviewSection()
        self.plugins = PluginsByStageSection()
        self.audio = AudioTranslationSection()
        self.vision = VisionSettingsSection(
            config_manager=self.config_manager, parent=self)

        # -- Embedded stage tabs (lazy-created on first access) --
        self._capture_tab = None
        self._ocr_tab = None
        self._translation_tab = None
        self._llm_tab = None

        # Tab 1: Overview
        overview_tab = self._create_scrollable_tab(self.overview)
        tab_widget.addTab(overview_tab, tr("pipeline_overview"))

        # Tab 2: Capture  (placeholder — filled lazily)
        self._capture_placeholder = QWidget()
        tab_widget.addTab(self._capture_placeholder, tr("capture"))

        # Tab 3: OCR Engines  (placeholder)
        self._ocr_placeholder = QWidget()
        tab_widget.addTab(self._ocr_placeholder, tr("ocr_engines"))

        # Tab 4: Translation  (placeholder)
        self._translation_placeholder = QWidget()
        tab_widget.addTab(self._translation_placeholder, tr("translation"))

        # Tab 5: AI Processing  (placeholder)
        self._llm_placeholder = QWidget()
        tab_widget.addTab(self._llm_placeholder, tr("ai_processing"))

        # Tab 6: Vision (has its own internal scroll area)
        tab_widget.addTab(self.vision, tr("vision"))

        # Tab 7: Audio Translation
        audio_tab = self._create_scrollable_tab(self.audio)
        tab_widget.addTab(audio_tab, tr("audio_translation"))

        # Tab 8: Plugins by Stage
        plugins_tab = self._create_scrollable_tab(self.plugins)
        tab_widget.addTab(plugins_tab, tr("pipeline_plugins"))

        self._sub_tab_widget = tab_widget
        main_layout.addWidget(tab_widget)

        # Lazy-load embedded tabs when their sub-tab is first selected
        tab_widget.currentChanged.connect(self._on_sub_tab_changed)

        self._connect_signals()

    def _create_scrollable_tab(self, content_widget):
        """Wrap a tab's content in a scroll area."""
        scroll_area = ScrollAreaNoWheel()
        scroll_area.setWidgetResizable(True)
        scroll_area.setFrameShape(ScrollAreaNoWheel.Shape.NoFrame)
        scroll_area.setHorizontalScrollBarPolicy(
            Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        scroll_area.setVerticalScrollBarPolicy(
            Qt.ScrollBarPolicy.ScrollBarAsNeeded)
        scroll_area.setWidget(content_widget)
        return scroll_area

    # ------------------------------------------------------------------
    # Lazy loading for embedded stage tabs
    # ------------------------------------------------------------------

    # Sub-tab indices for the embedded tabs (must match _init_ui order)
    _CAPTURE_IDX = 1
    _OCR_IDX = 2
    _TRANSLATION_IDX = 3
    _LLM_IDX = 4

    def _on_sub_tab_changed(self, index: int):
        """Lazily create embedded tab widgets on first visit."""
        if index == self._CAPTURE_IDX and self._capture_tab is None:
            self._load_capture_tab()
        elif index == self._OCR_IDX and self._ocr_tab is None:
            self._load_ocr_tab()
        elif index == self._TRANSLATION_IDX and self._translation_tab is None:
            self._load_translation_tab()
        elif index == self._LLM_IDX and self._llm_tab is None:
            self._load_llm_tab()

    def _replace_placeholder(self, index: int, widget):
        """Swap a placeholder tab with the real widget."""
        tw = self._sub_tab_widget
        label = tw.tabText(index)
        tw.blockSignals(True)
        old = tw.widget(index)
        tw.removeTab(index)
        tw.insertTab(index, widget, label)
        tw.setCurrentIndex(index)
        tw.blockSignals(False)
        if old:
            old.deleteLater()

    def _load_capture_tab(self):
        from ui.settings.capture_tab import CaptureSettingsTab

        tab = CaptureSettingsTab(
            config_manager=self.config_manager, parent=self)
        tab.load_config()
        tab.settingChanged.connect(self.settingChanged)
        self._capture_tab = tab
        self._replace_placeholder(self._CAPTURE_IDX, tab)
        logger.debug("Pipeline hub: loaded Capture sub-tab")

    def _load_ocr_tab(self):
        from ui.settings.ocr.ocr_tab import OCRSettingsTab

        tab = OCRSettingsTab(
            config_manager=self.config_manager, parent=self)
        if self.pipeline:
            tab.pipeline = self.pipeline
        tab.load_config()
        tab.settingChanged.connect(self.settingChanged)
        self._ocr_tab = tab
        self._replace_placeholder(self._OCR_IDX, tab)
        logger.debug("Pipeline hub: loaded OCR sub-tab")

    def _load_translation_tab(self):
        from ui.settings.translation.translation_tab import TranslationSettingsTab

        tab = TranslationSettingsTab(
            config_manager=self.config_manager,
            pipeline=self.pipeline,
            parent=self)
        tab.load_config()
        tab.settingChanged.connect(self.settingChanged)
        self._translation_tab = tab
        self._replace_placeholder(self._TRANSLATION_IDX, tab)
        logger.debug("Pipeline hub: loaded Translation sub-tab")

    def _load_llm_tab(self):
        from ui.settings.llm.llm_tab import LLMSettingsTab

        tab = LLMSettingsTab(
            config_manager=self.config_manager,
            pipeline=self.pipeline,
            parent=self)
        tab.load_config()
        tab.settingChanged.connect(self.settingChanged)
        self._llm_tab = tab
        self._replace_placeholder(self._LLM_IDX, tab)
        logger.debug("Pipeline hub: loaded AI Processing sub-tab")

    # -- Public accessors for embedded tabs (used by ui_manager wiring) --

    @property
    def capture_tab(self):
        if self._capture_tab is None:
            self._load_capture_tab()
        return self._capture_tab

    @property
    def ocr_tab(self):
        if self._ocr_tab is None:
            self._load_ocr_tab()
        return self._ocr_tab

    @property
    def translation_tab(self):
        if self._translation_tab is None:
            self._load_translation_tab()
        return self._translation_tab

    @property
    def llm_tab(self):
        if self._llm_tab is None:
            self._load_llm_tab()
        return self._llm_tab

    # ------------------------------------------------------------------
    # Signal wiring (cross-section sync)
    # ------------------------------------------------------------------

    def _connect_signals(self):
        ov = self.overview
        pl = self.plugins

        # Pipeline lifecycle buttons
        ov.new_start_btn.clicked.connect(self._on_start_clicked)
        ov.new_pause_btn.clicked.connect(self._on_pause_clicked)
        ov.new_stop_btn.clicked.connect(self._on_stop_clicked)

        # Overview → main tab handlers
        ov.new_context_check.stateChanged.connect(
            self._on_overview_context_changed)
        ov.new_master_check.stateChanged.connect(
            self._on_overview_master_changed)
        ov.pipeline_mode_combo.currentIndexChanged.connect(
            self._on_pipeline_mode_changed)
        ov.apply_btn.clicked.connect(self._apply_overview_plugin_changes)

        # Overview plugin checkboxes → sync to detailed tab
        overview_plugin_map = {
            'new_skip_check': 'skip',
            'new_dict_check': 'dict',
            'new_cache_check': 'cache',
            'new_intelligent_check': 'intelligent',
            'new_batch_check': 'batch',
            'new_color_contrast_check': 'color_contrast',
            'new_motion_check': 'motion',
            'new_parallel_capture_check': 'parallel_capture',
            'new_parallel_ocr_check': 'parallel_ocr',
            'new_priority_check': 'priority',
            'new_spell_check': 'spell',
            'new_chain_check': 'chain',
            'new_work_check': 'work',
            'new_merger_check': 'merger',
            'new_parallel_trans_check': 'parallel_trans',
            'new_ocr_per_region_check': 'ocr_per_region',
            'new_regex_check': 'regex',
        }
        for attr_name, plugin_name in overview_plugin_map.items():
            checkbox = getattr(ov, attr_name)
            checkbox.stateChanged.connect(
                lambda state, pn=plugin_name: self._sync_plugin_checkbox(pn)
            )

        # Plugins section → main tab
        pl.plugins_enabled_check.stateChanged.connect(
            self._on_plugins_enabled_changed)
        pl.apply_btn.clicked.connect(self._apply_plugin_settings)
        pl.settingChanged.connect(self.settingChanged.emit)

        # Live threshold updates → push to running pipeline
        pl.skip_threshold_spin.valueChanged.connect(
            self._push_frame_skip_threshold)
        pl.ocr_stability_threshold_spin.valueChanged.connect(
            self._push_ocr_stability_threshold)

        # Detailed pipeline mode combo → overview sync
        pl.detailed_pipeline_mode_combo.currentIndexChanged.connect(
            self._sync_detailed_pipeline_mode_to_overview)

        # Audio Translation
        self.audio.settingChanged.connect(self.settingChanged.emit)
        self.audio.start_audio_btn.clicked.connect(
            self._open_audio_translation_dialog)

        # Vision
        self.vision.settingChanged.connect(self.settingChanged.emit)

    # ------------------------------------------------------------------
    # Cross-section synchronisation helpers
    # ------------------------------------------------------------------

    # ------------------------------------------------------------------
    # Pipeline lifecycle button handlers
    # ------------------------------------------------------------------

    def _on_start_clicked(self):
        """Start the translation pipeline."""
        if not self.pipeline:
            QMessageBox.warning(
                self, tr("pipeline_not_ready"),
                tr("pipeline_not_initialized_message"))
            return

        if self.pipeline.is_running():
            return

        success = self.pipeline.start_translation()
        if not success:
            QMessageBox.warning(
                self, tr("pipeline_start_failed"),
                tr("pipeline_start_failed_message"))

    def _on_pause_clicked(self):
        """Toggle pause/resume on the pipeline."""
        if not self.pipeline or not self.pipeline.pipeline:
            return

        inner = self.pipeline.pipeline
        from app.workflow.pipeline.types import PipelineState
        if inner._state == PipelineState.PAUSED:
            inner.resume()
            self.overview.update_pipeline_state(running=True, paused=False)
        elif inner._state == PipelineState.RUNNING:
            inner.pause()
            self.overview.update_pipeline_state(running=False, paused=True)

    def _on_stop_clicked(self):
        """Stop the translation pipeline."""
        if not self.pipeline:
            return
        self.pipeline.stop_translation()

    def _on_pipeline_started(self):
        """React to pipeline_started signal."""
        self.overview.update_pipeline_state(running=True, paused=False)
        self._stats_timer.start()

    def _on_pipeline_stopped(self):
        """React to pipeline_stopped signal."""
        self.overview.update_pipeline_state(running=False, paused=False)
        self._stats_timer.stop()

    def _on_pipeline_error(self, message: str):
        """React to pipeline_error signal."""
        self.overview.update_pipeline_state(running=False, paused=False)
        self._stats_timer.stop()
        logger.error("Pipeline error: %s", message)

    def _poll_stats(self):
        """Periodically poll pipeline metrics and update overview labels."""
        if not self.pipeline:
            return
        try:
            stats = self.pipeline.get_metrics()
            self.overview.update_stats(stats)
        except Exception:
            logger.debug("Failed to poll pipeline stats", exc_info=True)

    def _on_plugins_enabled_changed(self, state):
        """Handle master plugin enable/disable."""
        if isinstance(state, int):
            enabled = (state == Qt.CheckState.Checked.value)
        else:
            enabled = (state == Qt.CheckState.Checked)

        # Sync with overview master switch
        self.overview.new_master_check.blockSignals(True)
        self.overview.new_master_check.setChecked(enabled)
        self.overview.new_master_check.blockSignals(False)

        # Enable/disable OPTIONAL plugin checkboxes (plugins section)
        pl = self.plugins
        for attr in ('motion_plugin_enabled', 'parallel_capture_enabled',
                     'parallel_plugin_enabled', 'batch_plugin_enabled',
                     'chain_plugin_enabled', 'async_plugin_enabled',
                     'priority_plugin_enabled', 'work_plugin_enabled',
                     'spell_plugin_enabled', 'color_contrast_enabled',
                     'parallel_trans_enabled', 'ocr_per_region_enabled',
                     'regex_plugin_enabled'):
            widget = getattr(pl, attr, None)
            if widget is not None:
                widget.setEnabled(enabled)

        # Enable/disable overview optional checkboxes
        overview_optional = [
            'new_motion_check', 'new_parallel_capture_check',
            'new_spell_check', 'new_parallel_ocr_check',
            'new_batch_check', 'new_chain_check',
            'new_priority_check', 'new_work_check',
            'new_color_contrast_check', 'new_parallel_trans_check',
            'new_ocr_per_region_check', 'new_regex_check',
        ]
        for name in overview_optional:
            widget = getattr(self.overview, name, None)
            if widget is not None:
                widget.setEnabled(enabled)

        if self.config_manager:
            self.config_manager.set_setting(
                'pipeline.enable_optimizer_plugins', enabled)
            self.settingChanged.emit()

        logger.info("Master plugin switch: %s",
                     'ENABLED' if enabled else 'DISABLED')

    # ------------------------------------------------------------------
    # Live threshold push to running pipeline
    # ------------------------------------------------------------------

    def _push_frame_skip_threshold(self, value: float) -> None:
        """Push FrameSkipOptimizer threshold change to the running pipeline."""
        if self.pipeline and self.pipeline.is_running():
            self.pipeline.update_runtime_config(
                "FrameSkipOptimizer",
                {"similarity_threshold": value},
            )
        if self.config_manager:
            self.config_manager.set_setting(
                'ocr.frame_skip_threshold', value)

    def _push_ocr_stability_threshold(self, value: float) -> None:
        """Push OCRStage stability threshold change to the running pipeline."""
        if self.pipeline and self.pipeline.is_running():
            high = min(0.99, value + 0.04)
            self.pipeline.update_runtime_config(
                "OCRStage",
                {
                    "_STABILITY_THRESHOLD": value,
                    "_HIGH_SIMILARITY_THRESHOLD": high,
                },
                stage_attr=True,
            )
        if self.config_manager:
            self.config_manager.set_setting(
                'ocr.stability_threshold', value)

    def _on_overview_master_changed(self, state):
        """Handle overview tab master switch change."""
        enabled = (state == Qt.CheckState.Checked.value)

        self.plugins.plugins_enabled_check.blockSignals(True)
        self.plugins.plugins_enabled_check.setChecked(enabled)
        self.plugins.plugins_enabled_check.blockSignals(False)

        self._on_plugins_enabled_changed(state)

    def _sync_plugin_checkbox(self, plugin_name):
        """Sync plugin checkbox between overview and detailed tabs."""
        checkbox_map = {
            'skip': ('new_skip_check', 'skip_plugin_enabled'),
            'intelligent': ('new_intelligent_check',
                            'intelligent_plugin_enabled'),
            'cache': ('new_cache_check', 'cache_plugin_enabled'),
            'dict': ('new_dict_check', 'dict_plugin_enabled'),
            'motion': ('new_motion_check', 'motion_plugin_enabled'),
            'parallel_capture': ('new_parallel_capture_check',
                                 'parallel_capture_enabled'),
            'spell': ('new_spell_check', 'spell_plugin_enabled'),
            'parallel_ocr': ('new_parallel_ocr_check',
                             'parallel_plugin_enabled'),
            'batch': ('new_batch_check', 'batch_plugin_enabled'),
            'chain': ('new_chain_check', 'chain_plugin_enabled'),
            'priority': ('new_priority_check', 'priority_plugin_enabled'),
            'work': ('new_work_check', 'work_plugin_enabled'),
            'color_contrast': ('new_color_contrast_check',
                               'color_contrast_enabled'),
            'merger': ('new_merger_check', 'merger_plugin_enabled'),
            'parallel_trans': ('new_parallel_trans_check',
                               'parallel_trans_enabled'),
            'ocr_per_region': ('new_ocr_per_region_check',
                               'ocr_per_region_enabled'),
            'regex': ('new_regex_check', 'regex_plugin_enabled'),
        }

        entry = checkbox_map.get(plugin_name)
        if not entry:
            return

        overview_name, detailed_name = entry

        overview_checkbox = getattr(self.overview, overview_name, None)
        if overview_checkbox is None:
            return

        detailed_checkbox = getattr(self.plugins, detailed_name, None)
        if detailed_checkbox is not None:
            detailed_checkbox.blockSignals(True)
            detailed_checkbox.setChecked(overview_checkbox.isChecked())
            detailed_checkbox.blockSignals(False)

        self.settingChanged.emit()

    def _sync_overview_checkboxes_from_detailed(self):
        """Sync overview checkboxes from detailed tab on load."""
        checkbox_map = {
            'new_skip_check': 'skip_plugin_enabled',
            'new_intelligent_check': 'intelligent_plugin_enabled',
            'new_cache_check': 'cache_plugin_enabled',
            'new_dict_check': 'dict_plugin_enabled',
            'new_motion_check': 'motion_plugin_enabled',
            'new_parallel_capture_check': 'parallel_capture_enabled',
            'new_spell_check': 'spell_plugin_enabled',
            'new_parallel_ocr_check': 'parallel_plugin_enabled',
            'new_batch_check': 'batch_plugin_enabled',
            'new_chain_check': 'chain_plugin_enabled',
            'new_priority_check': 'priority_plugin_enabled',
            'new_work_check': 'work_plugin_enabled',
            'new_color_contrast_check': 'color_contrast_enabled',
            'new_merger_check': 'merger_plugin_enabled',
            'new_parallel_trans_check': 'parallel_trans_enabled',
            'new_ocr_per_region_check': 'ocr_per_region_enabled',
            'new_regex_check': 'regex_plugin_enabled',
        }

        for overview_name, detailed_name in checkbox_map.items():
            ov_cb = getattr(self.overview, overview_name, None)
            det_cb = getattr(self.plugins, detailed_name, None)
            if ov_cb is not None and det_cb is not None:
                ov_cb.blockSignals(True)
                ov_cb.setChecked(det_cb.isChecked())
                ov_cb.blockSignals(False)

        # Sync pipeline mode combo
        if hasattr(self.plugins, 'detailed_pipeline_mode_combo'):
            mode_index = self.plugins.detailed_pipeline_mode_combo.currentIndex()
            self.overview.pipeline_mode_combo.blockSignals(True)
            self.overview.pipeline_mode_combo.setCurrentIndex(mode_index)
            self.overview.pipeline_mode_combo.blockSignals(False)
            self.plugins._custom_mode_widget.setVisible(mode_index == 2)

    def _on_pipeline_mode_changed(self, index):
        """Handle pipeline mode dropdown change in overview tab."""
        is_parallel = (index == 1)
        self.plugins.async_plugin_enabled.blockSignals(True)
        self.plugins.async_plugin_enabled.setChecked(is_parallel)
        self.plugins.async_plugin_enabled.blockSignals(False)

        self.plugins.detailed_pipeline_mode_combo.blockSignals(True)
        self.plugins.detailed_pipeline_mode_combo.setCurrentIndex(index)
        self.plugins.detailed_pipeline_mode_combo.blockSignals(False)

        self.plugins._custom_mode_widget.setVisible(index == 2)
        self.settingChanged.emit()

    def _sync_detailed_pipeline_mode_to_overview(self, index):
        """Sync detailed tab pipeline mode to overview tab."""
        self.overview.pipeline_mode_combo.blockSignals(True)
        self.overview.pipeline_mode_combo.setCurrentIndex(index)
        self.overview.pipeline_mode_combo.blockSignals(False)

        self.plugins._custom_mode_widget.setVisible(index == 2)
        self.settingChanged.emit()

    def _on_overview_context_changed(self, state):
        """Handle context plugin checkbox change on overview tab."""
        enabled = (state == 2)
        if self.config_manager:
            self.config_manager.set_setting(
                'plugins.context_manager.enabled', enabled)
            self.config_manager.save_config()
        try:
            main_window = self.window()
            if (hasattr(main_window, 'settings_coordinator')
                    and main_window.settings_coordinator):
                main_window.settings_coordinator.notify_setting_changed(
                    'plugins.context_manager.enabled', enabled,
                    source_tab='pipeline')
        except Exception:
            pass

    def _apply_overview_plugin_changes(self):
        """Apply plugin changes from the overview tab."""
        if not self.config_manager:
            return

        # Sync pipeline mode
        is_parallel = self.overview.pipeline_mode_combo.currentIndex() == 1
        self.plugins.async_plugin_enabled.blockSignals(True)
        self.plugins.async_plugin_enabled.setChecked(is_parallel)
        self.plugins.async_plugin_enabled.blockSignals(False)

        # Sync all overview checkboxes to detailed tab
        plugin_names = [
            'skip', 'dict', 'cache', 'intelligent', 'motion',
            'parallel_capture', 'spell', 'parallel_ocr', 'batch',
            'chain', 'priority', 'work', 'color_contrast',
            'merger', 'parallel_trans', 'ocr_per_region', 'regex',
        ]
        for pn in plugin_names:
            self._sync_plugin_checkbox(pn)

        # Save context plugin state
        self.config_manager.set_setting(
            'plugins.context_manager.enabled',
            self.overview.new_context_check.isChecked())

        self._apply_plugin_settings()

        try:
            main_window = self.window()
            if (hasattr(main_window, 'settings_coordinator')
                    and main_window.settings_coordinator):
                main_window.settings_coordinator.notify_setting_changed(
                    'plugins.context_manager.enabled',
                    self.overview.new_context_check.isChecked(),
                    source_tab='pipeline')
        except Exception:
            pass

    def on_setting_changed(self, key: str, value):
        """Handle setting changes from other tabs (cross-tab sync)."""
        if key == 'plugins.context_manager.enabled':
            self.overview.new_context_check.blockSignals(True)
            self.overview.new_context_check.setChecked(value)
            self.overview.new_context_check.blockSignals(False)
        elif key == 'pipeline.mode':
            self.set_pipeline_mode(str(value) == "vision")

    # ------------------------------------------------------------------
    # Vision-mode awareness
    # ------------------------------------------------------------------

    def set_pipeline_mode(self, is_vision: bool) -> None:
        """
        Enable/disable text-pipeline-only controls when vision mode is active.

        In vision mode the runtime preset is forced to the dedicated
        ``vision`` pipeline in StartupPipeline, so the execution-mode
        comboboxes in this tab no longer apply. Optimizer plugins and
        the Vision sub-tab remain fully configurable.
        """
        # Execution-mode widgets in Overview/Plugins
        try:
            if hasattr(self.overview, "pipeline_mode_combo"):
                self.overview.pipeline_mode_combo.setEnabled(not is_vision)
        except Exception:
            pass

        try:
            if hasattr(self.plugins, "detailed_pipeline_mode_combo"):
                self.plugins.detailed_pipeline_mode_combo.setEnabled(not is_vision)
            if hasattr(self.plugins, "async_plugin_enabled"):
                self.plugins.async_plugin_enabled.setEnabled(not is_vision)
        except Exception:
            pass

        # User-facing hint so it's clear why controls are disabled.
        try:
            hint = tr("vision_mode_disabled_setting_hint") if is_vision else ""
        except Exception:
            hint = ""

        try:
            if hasattr(self.overview, "pipeline_mode_combo"):
                self.overview.pipeline_mode_combo.setToolTip(hint)
        except Exception:
            pass

        try:
            if hasattr(self.plugins, "detailed_pipeline_mode_combo"):
                self.plugins.detailed_pipeline_mode_combo.setToolTip(hint)
            if hasattr(self.plugins, "async_plugin_enabled"):
                self.plugins.async_plugin_enabled.setToolTip(hint)
        except Exception:
            pass

        # Forward mode to embedded OCR / Translation sub-tabs (pipeline hub
        # variants are not registered with SettingsCoordinator directly).
        try:
            if self._ocr_tab is not None and hasattr(self._ocr_tab, "set_pipeline_mode"):
                self._ocr_tab.set_pipeline_mode(is_vision)
        except Exception:
            pass

        try:
            if self._translation_tab is not None and hasattr(self._translation_tab, "set_pipeline_mode"):
                self._translation_tab.set_pipeline_mode(is_vision)
        except Exception:
            pass

    # ------------------------------------------------------------------
    # Plugin JSON persistence
    # ------------------------------------------------------------------

    def _read_plugin_json(self, json_path: Path) -> dict | None:
        """Read a plugin.json and return enabled state + flattened settings.

        Returns a dict like ``{"enabled": True, "similarity_threshold": 0.97}``
        or *None* when the file is missing / unreadable.  Values come from
        ``settings.<key>.default`` (standard schema) and ``config.<key>``
        (non-standard schema used by intelligent_text_processor).
        """
        if not json_path.exists():
            return None
        try:
            with open(json_path, 'r', encoding='utf-8') as f:
                data = json.load(f)

            result: dict = {'enabled': data.get('enabled', False)}

            for key, schema in data.get('settings', {}).items():
                if isinstance(schema, dict) and 'default' in schema:
                    result[key] = schema['default']

            for key, value in data.get('config', {}).items():
                if key not in result:
                    result[key] = value

            return result
        except Exception:
            logger.warning("Failed to read plugin config: %s",
                           json_path, exc_info=True)
            return None

    def _update_plugin_json(self, json_path: Path, enabled: bool,
                            settings_map: dict = None):
        """Update a plugin.json file with enabled state and settings."""
        if not json_path.exists():
            return

        with open(json_path, 'r', encoding='utf-8') as f:
            config = json.load(f)

        config['enabled'] = enabled

        if settings_map:
            if 'settings' not in config:
                config['settings'] = {}
            for key, value in settings_map.items():
                if key not in config['settings']:
                    if isinstance(value, bool):
                        config['settings'][key] = {
                            'type': 'bool', 'default': value}
                    elif isinstance(value, int):
                        config['settings'][key] = {
                            'type': 'int', 'default': value}
                    elif isinstance(value, float):
                        config['settings'][key] = {
                            'type': 'float', 'default': value}
                    else:
                        config['settings'][key] = {
                            'type': 'string', 'default': value}
                else:
                    config['settings'][key]['default'] = value

        with open(json_path, 'w', encoding='utf-8') as f:
            json.dump(config, f, indent=2)

    def _save_all_plugin_json_files(self):
        """Write current plugin settings to their respective plugin.json files."""
        plugins_dir = get_plugin_enhancers_dir("optimizers")
        pl = self.plugins

        self._update_plugin_json(
            plugins_dir / "frame_skip" / "plugin.json",
            pl.skip_plugin_enabled.isChecked(),
            {'similarity_threshold': pl.skip_threshold_spin.value(),
             'comparison_method': pl.skip_method_combo.currentText(),
             'max_skip_frames': pl.skip_max_frames_spin.value(),
             'adaptive_backoff': pl.skip_adaptive_check.isChecked(),
             'content_mode':
             pl.skip_content_mode_combo.currentText()})

        self._update_plugin_json(
            plugins_dir / "motion_tracker" / "plugin.json",
            pl.motion_plugin_enabled.isChecked(),
            {'motion_threshold': pl.motion_threshold_spin.value(),
             'motion_smoothing': pl.motion_smoothing_spin.value(),
             'max_motion_distance':
             pl.motion_max_distance_spin.value(),
             'skip_ocr_on_motion':
             pl.motion_skip_ocr_check.isChecked(),
             'update_overlay_positions':
             pl.motion_update_overlay_check.isChecked(),
             'reocr_after_stop':
             pl.motion_reocr_check.isChecked(),
             'stop_threshold_seconds':
             pl.motion_stop_threshold_spin.value()})

        self._update_plugin_json(
            plugins_dir / "parallel_capture" / "plugin.json",
            pl.parallel_capture_enabled.isChecked(),
            {'worker_threads':
             pl.parallel_capture_workers_spin.value()})

        self._update_plugin_json(
            plugins_dir / "text_block_merger" / "plugin.json",
            pl.merger_plugin_enabled.isChecked(),
            {'horizontal_threshold':
             pl.merger_h_threshold_spin.value(),
             'vertical_threshold':
             pl.merger_v_threshold_spin.value(),
             'line_height_tolerance':
             pl.merger_line_height_spin.value(),
             'merge_strategy':
             pl.merger_strategy_combo.currentText(),
             'respect_punctuation':
             pl.merger_respect_punct_check.isChecked(),
             'min_confidence':
             pl.merger_min_confidence_spin.value()})

        self._update_plugin_json(
            plugins_dir / "ocr_per_region" / "plugin.json",
            pl.ocr_per_region_enabled.isChecked(),
            {'default_ocr':
             pl.ocr_per_region_default_combo.currentText(),
             'parallel_regions':
             pl.ocr_per_region_parallel_check.isChecked(),
             'cache_engines':
             pl.ocr_per_region_cache_check.isChecked()})

        self._update_plugin_json(
            plugins_dir / "parallel_ocr" / "plugin.json",
            pl.parallel_plugin_enabled.isChecked(),
            {'worker_threads': pl.parallel_workers_spin.value()})

        self._update_plugin_json(
            get_plugin_enhancers_dir("text_processors") / "spell_corrector" / "plugin.json",
            pl.spell_plugin_enabled.isChecked(),
            {'aggressive_mode': pl.spell_aggressive_check.isChecked(),
             'fix_capitalization': pl.spell_fix_caps_check.isChecked(),
             'min_confidence': pl.spell_confidence_spin.value(),
             'use_learning_dict':
             pl.spell_use_dict_check.isChecked(),
             'language':
             pl.spell_language_combo.currentText()})

        self._update_plugin_json(
            get_plugin_enhancers_dir("text_processors") / "regex" / "plugin.json",
            pl.regex_plugin_enabled.isChecked(),
            {'filter_mode':
             pl.regex_filter_mode_combo.currentText(),
             'min_text_length':
             pl.regex_min_length_spin.value(),
             'max_text_length':
             pl.regex_max_length_spin.value()})

        self._update_plugin_json(
            plugins_dir / "translation_cache" / "plugin.json",
            pl.cache_plugin_enabled.isChecked(),
            {'max_cache_size': pl.cache_size_spin.value(),
             'ttl_seconds': pl.cache_ttl_spin.value(),
             'enable_fuzzy_match':
             pl.cache_fuzzy_check.isChecked()})

        self._update_plugin_json(
            plugins_dir / "learning_dictionary" / "plugin.json",
            pl.dict_plugin_enabled.isChecked(),
            {'auto_save': pl.dict_auto_save_check.isChecked(),
             'min_confidence':
             pl.dict_min_confidence_spin.value(),
             'validate_sentences':
             pl.dict_validate_check.isChecked()})

        self._update_plugin_json(
            plugins_dir / "batch_processing" / "plugin.json",
            pl.batch_plugin_enabled.isChecked(),
            {'max_batch_size': pl.batch_size_spin.value(),
             'max_wait_time_ms': pl.batch_wait_spin.value(),
             'min_batch_size': pl.batch_min_size_spin.value(),
             'adaptive': pl.batch_adaptive_check.isChecked()})

        self._update_plugin_json(
            plugins_dir / "parallel_translation" / "plugin.json",
            pl.parallel_trans_enabled.isChecked(),
            {'worker_threads':
             pl.parallel_trans_workers_spin.value(),
             'batch_size':
             pl.parallel_trans_batch_spin.value(),
             'timeout_seconds':
             pl.parallel_trans_timeout_spin.value(),
             'use_gpu':
             pl.parallel_trans_gpu_check.isChecked(),
             'enable_warm_start':
             pl.parallel_trans_warm_start_check.isChecked(),
             'fallback_on_error':
             pl.parallel_trans_fallback_check.isChecked()})

        self._update_plugin_json(
            plugins_dir / "translation_chain" / "plugin.json",
            pl.chain_plugin_enabled.isChecked(),
            {'enable_chaining':
             pl.chain_enable_chaining_check.isChecked(),
             'intermediate_language':
             pl.chain_intermediate_lang_combo.currentText(),
             'quality_threshold':
             pl.chain_quality_threshold_spin.value(),
             'save_all_mappings':
             pl.chain_save_all_check.isChecked(),
             'cache_intermediate':
             pl.chain_cache_intermediate_check.isChecked()})

        self._update_plugin_json(
            plugins_dir / "priority_queue" / "plugin.json",
            pl.priority_plugin_enabled.isChecked(),
            {'max_queue_size':
             pl.priority_max_queue_spin.value(),
             'starvation_prevention':
             pl.priority_starvation_check.isChecked()})

        self._update_plugin_json(
            plugins_dir / "work_stealing" / "plugin.json",
            pl.work_plugin_enabled.isChecked(),
            {'num_workers': pl.work_workers_spin.value(),
             'steal_threshold':
             pl.work_steal_threshold_spin.value(),
             'enable_affinity':
             pl.work_affinity_check.isChecked()})

        self._update_plugin_json(
            plugins_dir / "color_contrast" / "plugin.json",
            self.overview.new_color_contrast_check.isChecked(),
            {'mode': pl.color_contrast_mode_combo.currentText(),
             'min_contrast_ratio':
             pl.color_contrast_ratio_spin.value(),
             'sample_size':
             pl.color_contrast_sample_spin.value(),
             'fallback_text_light':
             pl.cc_fallback_light_edit.text(),
             'fallback_text_dark':
             pl.cc_fallback_dark_edit.text()}
            if hasattr(pl, 'color_contrast_mode_combo') else None)

    def _apply_plugin_settings(self):
        """Apply optimizer plugin settings to plugin.json files and config."""
        plugins_dir = get_plugin_enhancers_dir("optimizers")
        pl = self.plugins

        try:
            # Capture stage
            self._update_plugin_json(
                plugins_dir / "frame_skip" / "plugin.json",
                pl.skip_plugin_enabled.isChecked(),
                {'similarity_threshold': pl.skip_threshold_spin.value(),
                 'comparison_method': pl.skip_method_combo.currentText(),
                 'max_skip_frames': pl.skip_max_frames_spin.value(),
                 'adaptive_backoff': pl.skip_adaptive_check.isChecked(),
                 'content_mode':
                 pl.skip_content_mode_combo.currentText()})

            self._update_plugin_json(
                plugins_dir / "motion_tracker" / "plugin.json",
                pl.motion_plugin_enabled.isChecked(),
                {'motion_threshold': pl.motion_threshold_spin.value(),
                 'motion_smoothing': pl.motion_smoothing_spin.value(),
                 'max_motion_distance':
                 pl.motion_max_distance_spin.value(),
                 'skip_ocr_on_motion':
                 pl.motion_skip_ocr_check.isChecked(),
                 'update_overlay_positions':
                 pl.motion_update_overlay_check.isChecked(),
                 'reocr_after_stop':
                 pl.motion_reocr_check.isChecked(),
                 'stop_threshold_seconds':
                 pl.motion_stop_threshold_spin.value()})

            self._update_plugin_json(
                plugins_dir / "parallel_capture" / "plugin.json",
                pl.parallel_capture_enabled.isChecked(),
                {'worker_threads':
                 pl.parallel_capture_workers_spin.value()})

            # OCR stage
            self._update_plugin_json(
                plugins_dir / "text_block_merger" / "plugin.json",
                pl.merger_plugin_enabled.isChecked(),
                {'horizontal_threshold':
                 pl.merger_h_threshold_spin.value(),
                 'vertical_threshold':
                 pl.merger_v_threshold_spin.value(),
                 'line_height_tolerance':
                 pl.merger_line_height_spin.value(),
                 'merge_strategy':
                 pl.merger_strategy_combo.currentText(),
                 'respect_punctuation':
                 pl.merger_respect_punct_check.isChecked(),
                 'min_confidence':
                 pl.merger_min_confidence_spin.value()})

            self._update_plugin_json(
                plugins_dir / "ocr_per_region" / "plugin.json",
                pl.ocr_per_region_enabled.isChecked(),
                {'default_ocr':
                 pl.ocr_per_region_default_combo.currentText(),
                 'parallel_regions':
                 pl.ocr_per_region_parallel_check.isChecked(),
                 'cache_engines':
                 pl.ocr_per_region_cache_check.isChecked()})

            self._update_plugin_json(
                plugins_dir / "parallel_ocr" / "plugin.json",
                pl.parallel_plugin_enabled.isChecked(),
                {'worker_threads': pl.parallel_workers_spin.value()})

            self._update_plugin_json(
                get_plugin_enhancers_dir("text_processors") / "spell_corrector" / "plugin.json",
                pl.spell_plugin_enabled.isChecked(),
                {'aggressive_mode': pl.spell_aggressive_check.isChecked(),
                 'fix_capitalization': pl.spell_fix_caps_check.isChecked(),
                 'min_confidence': pl.spell_confidence_spin.value(),
                 'use_learning_dict':
                 pl.spell_use_dict_check.isChecked(),
                 'language':
                 pl.spell_language_combo.currentText()})

            self._update_plugin_json(
                get_plugin_enhancers_dir("text_processors") / "regex" / "plugin.json",
                pl.regex_plugin_enabled.isChecked(),
                {'filter_mode':
                 pl.regex_filter_mode_combo.currentText(),
                 'min_text_length':
                 pl.regex_min_length_spin.value(),
                 'max_text_length':
                 pl.regex_max_length_spin.value()})

            # Translation stage
            self._update_plugin_json(
                plugins_dir / "translation_cache" / "plugin.json",
                pl.cache_plugin_enabled.isChecked(),
                {'max_cache_size': pl.cache_size_spin.value(),
                 'ttl_seconds': pl.cache_ttl_spin.value(),
                 'enable_fuzzy_match':
                 pl.cache_fuzzy_check.isChecked()})

            self._update_plugin_json(
                plugins_dir / "learning_dictionary" / "plugin.json",
                pl.dict_plugin_enabled.isChecked(),
                {'auto_save': pl.dict_auto_save_check.isChecked(),
                 'min_confidence':
                 pl.dict_min_confidence_spin.value(),
                 'validate_sentences':
                 pl.dict_validate_check.isChecked()})

            self._update_plugin_json(
                plugins_dir / "batch_processing" / "plugin.json",
                pl.batch_plugin_enabled.isChecked(),
                {'max_batch_size': pl.batch_size_spin.value(),
                 'max_wait_time_ms': pl.batch_wait_spin.value(),
                 'min_batch_size': pl.batch_min_size_spin.value(),
                 'adaptive': pl.batch_adaptive_check.isChecked()})

            self._update_plugin_json(
                plugins_dir / "parallel_translation" / "plugin.json",
                pl.parallel_trans_enabled.isChecked(),
                {'worker_threads':
                 pl.parallel_trans_workers_spin.value(),
                 'batch_size':
                 pl.parallel_trans_batch_spin.value(),
                 'timeout_seconds':
                 pl.parallel_trans_timeout_spin.value(),
                 'use_gpu':
                 pl.parallel_trans_gpu_check.isChecked(),
                 'enable_warm_start':
                 pl.parallel_trans_warm_start_check.isChecked(),
                 'fallback_on_error':
                 pl.parallel_trans_fallback_check.isChecked()})

            self._update_plugin_json(
                plugins_dir / "translation_chain" / "plugin.json",
                pl.chain_plugin_enabled.isChecked(),
                {'enable_chaining':
                 pl.chain_enable_chaining_check.isChecked(),
                 'intermediate_language':
                 pl.chain_intermediate_lang_combo.currentText(),
                 'quality_threshold':
                 pl.chain_quality_threshold_spin.value(),
                 'save_all_mappings':
                 pl.chain_save_all_check.isChecked(),
                 'cache_intermediate':
                 pl.chain_cache_intermediate_check.isChecked()})

            # Global
            self._update_plugin_json(
                plugins_dir / "priority_queue" / "plugin.json",
                pl.priority_plugin_enabled.isChecked(),
                {'max_queue_size':
                 pl.priority_max_queue_spin.value(),
                 'starvation_prevention':
                 pl.priority_starvation_check.isChecked()})

            self._update_plugin_json(
                plugins_dir / "work_stealing" / "plugin.json",
                pl.work_plugin_enabled.isChecked(),
                {'num_workers': pl.work_workers_spin.value(),
                 'steal_threshold':
                 pl.work_steal_threshold_spin.value(),
                 'enable_affinity':
                 pl.work_affinity_check.isChecked()})

            # Overlay stage
            self._update_plugin_json(
                plugins_dir / "color_contrast" / "plugin.json",
                self.overview.new_color_contrast_check.isChecked(),
                {'mode': pl.color_contrast_mode_combo.currentText(),
                 'min_contrast_ratio':
                 pl.color_contrast_ratio_spin.value(),
                 'sample_size':
                 pl.color_contrast_sample_spin.value(),
                 'fallback_text_light':
                 pl.cc_fallback_light_edit.text(),
                 'fallback_text_dark':
                 pl.cc_fallback_dark_edit.text()}
                if hasattr(pl, 'color_contrast_mode_combo') else None)

            # Save master setting + config
            if self.config_manager:
                self.config_manager.set_setting(
                    'pipeline.enable_optimizer_plugins',
                    pl.plugins_enabled_check.isChecked())
                self.config_manager.set_setting(
                    'ocr.stability_threshold',
                    pl.ocr_stability_threshold_spin.value())
                self.save_config()

            QMessageBox.information(
                self,
                tr("plugin_settings_applied"),
                tr("plugin_settings_applied_message")
            )

            self.settingChanged.emit()

        except Exception as e:
            QMessageBox.warning(
                self,
                tr("error"),
                tr("plugin_settings_save_failed_message", error=str(e))
            )

    # ------------------------------------------------------------------
    # Metrics / display helpers
    # ------------------------------------------------------------------

    def _update_metrics(self):
        """Update dynamic displays."""
        self._update_ocr_engine_display()
        self._update_active_components()

    def set_pipeline(self, pipeline):
        """Set or update the pipeline reference."""
        old = self.pipeline
        if old is not None:
            try:
                old.pipeline_started.disconnect(self._on_pipeline_started)
                old.pipeline_stopped.disconnect(self._on_pipeline_stopped)
                old.pipeline_error.disconnect(self._on_pipeline_error)
            except (TypeError, RuntimeError):
                pass

        self.pipeline = pipeline

        if pipeline is not None:
            pipeline.pipeline_started.connect(self._on_pipeline_started)
            pipeline.pipeline_stopped.connect(self._on_pipeline_stopped)
            pipeline.pipeline_error.connect(self._on_pipeline_error)

            is_running = pipeline.is_running()
            is_paused = False
            if is_running is False and pipeline.pipeline:
                from app.workflow.pipeline.types import PipelineState
                is_paused = (pipeline.pipeline._state == PipelineState.PAUSED)
            self.overview.update_pipeline_state(
                running=is_running, paused=is_paused)

            if is_running or is_paused:
                self._stats_timer.start()
            else:
                self._stats_timer.stop()
        else:
            self.overview.update_pipeline_state(
                running=False, paused=False)
            self._stats_timer.stop()
            self.overview.reset_stats()

        # Forward pipeline to embedded stage tabs
        if self._ocr_tab is not None:
            self._ocr_tab.pipeline = pipeline
            if pipeline is not None:
                self._ocr_tab.refresh_engine_list()
        if self._translation_tab is not None:
            self._translation_tab.pipeline = pipeline
        if self._llm_tab is not None:
            self._llm_tab.pipeline = pipeline

        logger.info(
            "Pipeline Management tab: pipeline reference updated "
            "(pipeline=%s)",
            'available' if pipeline else 'None')
        self._update_metrics()

    def _update_ocr_engine_display(self):
        """Update OCR engine display in all tabs."""
        if not self.config_manager:
            return

        try:
            engine = self.config_manager.get_setting('ocr.engine', 'easyocr')
            language = self.config_manager.get_setting(
                'translation.source_language', 'en')

            engine_display = ENGINE_NAMES.get(engine.lower(), engine)
            lang_display = LANGUAGE_NAMES.get(language, language)

            display_text = f"{engine_display} ({lang_display})"

            if hasattr(self.plugins, 'current_ocr_engine_label'):
                self.plugins.current_ocr_engine_label.setText(display_text)

        except Exception:
            logger.warning("Failed to update OCR engine display",
                           exc_info=True)

    def _update_active_components(self):
        """Update active components display."""
        try:
            capture_method = (
                self.config_manager.get_setting('capture.method', 'directx')
                if self.config_manager else 'directx')
            capture_text = (
                f"{capture_method.upper()} (GPU)"
                if capture_method == 'directx' else "Screenshot")

            source_lang = (
                self.config_manager.get_setting(
                    'translation.source_language', 'en')
                if self.config_manager else 'en')
            target_lang = (
                self.config_manager.get_setting(
                    'translation.target_language', 'de')
                if self.config_manager else 'de')
            translation_text = f"MarianMT ({source_lang}→{target_lang})"

            ocr_text = get_ocr_engine_display(self.config_manager)
            overlay_text = "PyQt6 (GPU-accelerated)"

            ov = self.overview
            ov.new_capture_label.setText(capture_text)
            ov.new_ocr_label.setText(ocr_text)
            ov.new_translation_label.setText(translation_text)
            ov.new_overlay_label.setText(overlay_text)

        except Exception:
            logger.warning("Failed to update active components",
                           exc_info=True)

    # ------------------------------------------------------------------
    # Config load / save / validate
    # ------------------------------------------------------------------

    def load_config(self):
        """Load configuration."""
        if not self.config_manager:
            return

        pl = self.plugins
        ov = self.overview

        # Master enable/disable
        plugins_enabled = self.config_manager.get_setting(
            'pipeline.enable_optimizer_plugins', False)
        pl.plugins_enabled_check.setChecked(plugins_enabled)
        self._on_plugins_enabled_changed(
            Qt.CheckState.Checked.value
            if plugins_enabled
            else Qt.CheckState.Unchecked.value)

        ov.new_master_check.blockSignals(True)
        ov.new_master_check.setChecked(plugins_enabled)
        ov.new_master_check.blockSignals(False)

        # ---- Read all plugin settings from plugin.json (source of truth) ----
        optimizers_dir = get_plugin_enhancers_dir("optimizers")
        text_proc_dir = get_plugin_enhancers_dir("text_processors")

        # Capture stage: Frame Skip
        cfg = self._read_plugin_json(
            optimizers_dir / "frame_skip" / "plugin.json")
        if cfg:
            pl.skip_plugin_enabled.setChecked(cfg.get('enabled', True))
            pl.skip_threshold_spin.setValue(
                cfg.get('similarity_threshold', 0.95))
            idx = pl.skip_method_combo.findText(
                cfg.get('comparison_method', 'hash'))
            if idx >= 0:
                pl.skip_method_combo.setCurrentIndex(idx)
            pl.skip_max_frames_spin.setValue(
                cfg.get('max_skip_frames', 300))
            pl.skip_adaptive_check.setChecked(
                cfg.get('adaptive_backoff', True))
            idx = pl.skip_content_mode_combo.findText(
                cfg.get('content_mode', 'static'))
            if idx >= 0:
                pl.skip_content_mode_combo.setCurrentIndex(idx)

        # Capture stage: Motion Tracker
        cfg = self._read_plugin_json(
            optimizers_dir / "motion_tracker" / "plugin.json")
        if cfg:
            pl.motion_plugin_enabled.setChecked(cfg.get('enabled', True))
            pl.motion_threshold_spin.setValue(
                cfg.get('motion_threshold', 0.05))
            pl.motion_smoothing_spin.setValue(
                cfg.get('motion_smoothing', 0.3))
            pl.motion_max_distance_spin.setValue(
                cfg.get('max_motion_distance', 200))
            pl.motion_skip_ocr_check.setChecked(
                cfg.get('skip_ocr_on_motion', True))
            pl.motion_update_overlay_check.setChecked(
                cfg.get('update_overlay_positions', True))
            pl.motion_reocr_check.setChecked(
                cfg.get('reocr_after_stop', True))
            pl.motion_stop_threshold_spin.setValue(
                cfg.get('stop_threshold_seconds', 0.5))

        # Capture stage: Parallel Capture
        cfg = self._read_plugin_json(
            optimizers_dir / "parallel_capture" / "plugin.json")
        if cfg:
            pl.parallel_capture_enabled.setChecked(
                cfg.get('enabled', False))
            pl.parallel_capture_workers_spin.setValue(
                cfg.get('worker_threads', 4))

        # OCR stage: stability threshold (from config, not plugin.json)
        pl.ocr_stability_threshold_spin.setValue(
            self.config_manager.get_setting('ocr.stability_threshold', 0.80))

        # OCR stage: Intelligent Text Processor (non-standard 'config' key)
        cfg = self._read_plugin_json(
            optimizers_dir / "intelligent_text_processor" / "plugin.json")
        if cfg:
            pl.intelligent_plugin_enabled.setChecked(
                cfg.get('enabled', True))
            pl.intelligent_corrections_check.setChecked(
                cfg.get('enable_corrections', True))
            pl.intelligent_context_check.setChecked(
                cfg.get('enable_context', True))
            pl.intelligent_validation_check.setChecked(
                cfg.get('enable_validation', True))
            pl.intelligent_min_confidence_spin.setValue(
                cfg.get('min_confidence', 0.3))
            pl.intelligent_auto_learn_check.setChecked(
                cfg.get('auto_learn', True))
        # min_word_length is only in user_config.json (not in plugin.json)
        pl.intelligent_min_word_length_spin.setValue(
            self.config_manager.get_setting(
                'pipeline.plugins.intelligent_text_processor.'
                'min_word_length', 2))

        # OCR stage: Spell Corrector
        cfg = self._read_plugin_json(
            text_proc_dir / "spell_corrector" / "plugin.json")
        if cfg:
            pl.spell_plugin_enabled.setChecked(cfg.get('enabled', True))
            pl.spell_aggressive_check.setChecked(
                cfg.get('aggressive_mode', False))
            pl.spell_fix_caps_check.setChecked(
                cfg.get('fix_capitalization', True))
            pl.spell_confidence_spin.setValue(
                cfg.get('min_confidence', 0.5))
            pl.spell_use_dict_check.setChecked(
                cfg.get('use_learning_dict', True))
            idx = pl.spell_language_combo.findText(
                cfg.get('language', 'en'))
            if idx >= 0:
                pl.spell_language_combo.setCurrentIndex(idx)

        # OCR stage: Text Block Merger
        cfg = self._read_plugin_json(
            optimizers_dir / "text_block_merger" / "plugin.json")
        if cfg:
            pl.merger_plugin_enabled.setChecked(cfg.get('enabled', True))
            pl.merger_h_threshold_spin.setValue(
                cfg.get('horizontal_threshold', 50))
            pl.merger_v_threshold_spin.setValue(
                cfg.get('vertical_threshold', 30))
            pl.merger_line_height_spin.setValue(
                cfg.get('line_height_tolerance', 1.5))
            idx = pl.merger_strategy_combo.findText(
                cfg.get('merge_strategy', 'smart'))
            if idx >= 0:
                pl.merger_strategy_combo.setCurrentIndex(idx)
            pl.merger_respect_punct_check.setChecked(
                cfg.get('respect_punctuation', True))
            pl.merger_min_confidence_spin.setValue(
                cfg.get('min_confidence', 0.3))

        # OCR stage: OCR per Region
        cfg = self._read_plugin_json(
            optimizers_dir / "ocr_per_region" / "plugin.json")
        if cfg:
            pl.ocr_per_region_enabled.setChecked(
                cfg.get('enabled', False))
            idx = pl.ocr_per_region_default_combo.findText(
                cfg.get('default_ocr', 'easyocr'))
            if idx >= 0:
                pl.ocr_per_region_default_combo.setCurrentIndex(idx)
            pl.ocr_per_region_parallel_check.setChecked(
                cfg.get('parallel_regions', True))
            pl.ocr_per_region_cache_check.setChecked(
                cfg.get('cache_engines', True))

        # OCR stage: Regex Text Processor
        cfg = self._read_plugin_json(
            text_proc_dir / "regex" / "plugin.json")
        if cfg:
            pl.regex_plugin_enabled.setChecked(cfg.get('enabled', False))
            idx = pl.regex_filter_mode_combo.findText(
                cfg.get('filter_mode', 'basic'))
            if idx >= 0:
                pl.regex_filter_mode_combo.setCurrentIndex(idx)
            pl.regex_min_length_spin.setValue(
                cfg.get('min_text_length', 1))
            pl.regex_max_length_spin.setValue(
                cfg.get('max_text_length', 10000))

        # OCR stage: Parallel OCR
        cfg = self._read_plugin_json(
            optimizers_dir / "parallel_ocr" / "plugin.json")
        if cfg:
            pl.parallel_plugin_enabled.setChecked(
                cfg.get('enabled', False))
            pl.parallel_workers_spin.setValue(
                cfg.get('worker_threads', 4))

        # Translation stage: Translation Cache
        cfg = self._read_plugin_json(
            optimizers_dir / "translation_cache" / "plugin.json")
        if cfg:
            pl.cache_plugin_enabled.setChecked(cfg.get('enabled', True))
            pl.cache_size_spin.setValue(
                cfg.get('max_cache_size', 10000))
            pl.cache_ttl_spin.setValue(cfg.get('ttl_seconds', 3600))
            pl.cache_fuzzy_check.setChecked(
                cfg.get('enable_fuzzy_match', False))

        # Translation stage: Learning Dictionary
        cfg = self._read_plugin_json(
            optimizers_dir / "learning_dictionary" / "plugin.json")
        if cfg:
            pl.dict_plugin_enabled.setChecked(cfg.get('enabled', True))
            pl.dict_auto_save_check.setChecked(
                cfg.get('auto_save', True))
            pl.dict_min_confidence_spin.setValue(
                cfg.get('min_confidence', 0.8))
            pl.dict_validate_check.setChecked(
                cfg.get('validate_sentences', True))

        # Translation stage: Batch Processing
        cfg = self._read_plugin_json(
            optimizers_dir / "batch_processing" / "plugin.json")
        if cfg:
            pl.batch_plugin_enabled.setChecked(cfg.get('enabled', False))
            pl.batch_size_spin.setValue(cfg.get('max_batch_size', 8))
            pl.batch_wait_spin.setValue(
                cfg.get('max_wait_time_ms', 10.0))
            pl.batch_min_size_spin.setValue(
                cfg.get('min_batch_size', 2))
            pl.batch_adaptive_check.setChecked(
                cfg.get('adaptive', True))

        # Translation stage: Parallel Translation
        cfg = self._read_plugin_json(
            optimizers_dir / "parallel_translation" / "plugin.json")
        if cfg:
            pl.parallel_trans_enabled.setChecked(
                cfg.get('enabled', False))
            pl.parallel_trans_workers_spin.setValue(
                cfg.get('worker_threads', 2))
            pl.parallel_trans_batch_spin.setValue(
                cfg.get('batch_size', 8))
            pl.parallel_trans_timeout_spin.setValue(
                cfg.get('timeout_seconds', 30.0))
            pl.parallel_trans_gpu_check.setChecked(
                cfg.get('use_gpu', True))
            pl.parallel_trans_warm_start_check.setChecked(
                cfg.get('enable_warm_start', True))
            pl.parallel_trans_fallback_check.setChecked(
                cfg.get('fallback_on_error', True))

        # Translation stage: Translation Chain
        cfg = self._read_plugin_json(
            optimizers_dir / "translation_chain" / "plugin.json")
        if cfg:
            pl.chain_plugin_enabled.setChecked(cfg.get('enabled', False))
            pl.chain_enable_chaining_check.setChecked(
                cfg.get('enable_chaining', False))
            idx = pl.chain_intermediate_lang_combo.findText(
                cfg.get('intermediate_language', 'en'))
            if idx >= 0:
                pl.chain_intermediate_lang_combo.setCurrentIndex(idx)
            pl.chain_quality_threshold_spin.setValue(
                cfg.get('quality_threshold', 0.7))
            pl.chain_save_all_check.setChecked(
                cfg.get('save_all_mappings', True))
            pl.chain_cache_intermediate_check.setChecked(
                cfg.get('cache_intermediate', True))

        # Overlay stage: Color Contrast
        cfg = self._read_plugin_json(
            optimizers_dir / "color_contrast" / "plugin.json")
        if cfg:
            pl.color_contrast_enabled.setChecked(
                cfg.get('enabled', False))
            idx = pl.color_contrast_mode_combo.findText(
                cfg.get('mode', 'auto_contrast'))
            if idx >= 0:
                pl.color_contrast_mode_combo.setCurrentIndex(idx)
            pl.color_contrast_ratio_spin.setValue(
                cfg.get('min_contrast_ratio', 4.5))
            pl.color_contrast_sample_spin.setValue(
                cfg.get('sample_size', 20))
            pl.cc_fallback_light_edit.setText(
                cfg.get('fallback_text_light', '#ffffff'))
            pl.cc_fallback_dark_edit.setText(
                cfg.get('fallback_text_dark', '#000000'))

        # Global: Priority Queue
        cfg = self._read_plugin_json(
            optimizers_dir / "priority_queue" / "plugin.json")
        if cfg:
            pl.priority_plugin_enabled.setChecked(
                cfg.get('enabled', False))
            pl.priority_max_queue_spin.setValue(
                cfg.get('max_queue_size', 100))
            pl.priority_starvation_check.setChecked(
                cfg.get('starvation_prevention', True))

        # Global: Work Stealing
        cfg = self._read_plugin_json(
            optimizers_dir / "work_stealing" / "plugin.json")
        if cfg:
            pl.work_plugin_enabled.setChecked(cfg.get('enabled', False))
            pl.work_workers_spin.setValue(cfg.get('num_workers', 4))
            pl.work_steal_threshold_spin.setValue(
                cfg.get('steal_threshold', 2))
            pl.work_affinity_check.setChecked(
                cfg.get('enable_affinity', False))

        # OCR engine display
        self._update_ocr_engine_display()

        # Pipeline execution mode
        exec_mode = self.config_manager.get_setting(
            'pipeline.execution_mode', 'sequential')
        mode_map = {'sequential': 0, 'async': 1, 'custom': 2, 'subprocess': 3}
        mode_index = mode_map.get(exec_mode, 0)
        ov.pipeline_mode_combo.blockSignals(True)
        ov.pipeline_mode_combo.setCurrentIndex(mode_index)
        ov.pipeline_mode_combo.blockSignals(False)
        pl.detailed_pipeline_mode_combo.blockSignals(True)
        pl.detailed_pipeline_mode_combo.setCurrentIndex(mode_index)
        pl.detailed_pipeline_mode_combo.blockSignals(False)
        pl.async_plugin_enabled.blockSignals(True)
        pl.async_plugin_enabled.setChecked(mode_index == 1)
        pl.async_plugin_enabled.blockSignals(False)
        pl._custom_mode_widget.setVisible(mode_index == 2)

        # Per-stage modes (for Custom mode)
        stage_modes = self.config_manager.get_setting(
            'pipeline.stage_modes', {})
        stage_map = {'sequential': 0, 'async': 1}
        for stage_name, combo_attr in [
            ('capture', 'custom_capture_combo'),
            ('ocr', 'custom_ocr_combo'),
            ('translation', 'custom_translation_combo'),
            ('overlay', 'custom_overlay_combo'),
        ]:
            combo = getattr(pl, combo_attr, None)
            if combo is not None:
                idx = stage_map.get(stage_modes.get(stage_name, 'sequential'), 0)
                combo.blockSignals(True)
                combo.setCurrentIndex(idx)
                combo.blockSignals(False)

        # Context plugin → overview checkbox
        context_enabled = self.config_manager.get_setting(
            'plugins.context_manager.enabled', True)
        ov.new_context_check.blockSignals(True)
        ov.new_context_check.setChecked(context_enabled)
        ov.new_context_check.blockSignals(False)

        # Audio Translation
        au = self.audio
        au.audio_plugin_enabled.setChecked(
            self.config_manager.get_setting(
                'plugins.audio_translation.enabled', False))
        au.audio_mode.setChecked(
            self.config_manager.get_setting(
                'plugins.audio_translation.audio_mode', False))

        whisper_model = self.config_manager.get_setting(
            'plugins.audio_translation.whisper_model', 'base')
        idx = au.audio_whisper_model.findText(whisper_model)
        if idx >= 0:
            au.audio_whisper_model.setCurrentIndex(idx)

        tts_engine = self.config_manager.get_setting(
            'plugins.audio_translation.tts_engine', 'coqui')
        idx = au.audio_tts_engine.findText(tts_engine)
        if idx >= 0:
            au.audio_tts_engine.setCurrentIndex(idx)

        au.audio_auto_play.setChecked(
            self.config_manager.get_setting(
                'plugins.audio_translation.auto_play', True))
        au.audio_voice_speed.setValue(
            self.config_manager.get_setting(
                'plugins.audio_translation.voice_speed', 1.0))
        au.audio_mic_device.setValue(
            self.config_manager.get_setting(
                'plugins.audio_translation.mic_device', -1))
        au.audio_speaker_device.setValue(
            self.config_manager.get_setting(
                'plugins.audio_translation.speaker_device', -1))
        au.audio_vad_sensitivity.setValue(
            self.config_manager.get_setting(
                'plugins.audio_translation.vad_sensitivity', 2))
        au.audio_use_gpu.setChecked(
            self.config_manager.get_setting(
                'plugins.audio_translation.use_gpu', True))

        self._sync_overview_checkboxes_from_detailed()
        self._update_active_components()

        # Vision section
        self.vision.load_config()

        # Apply pipeline-mode specific enabling/disabling for execution-mode
        # controls and embedded text tabs on initial load.
        try:
            mode = self.config_manager.get_setting('pipeline.mode', 'text')
            self.set_pipeline_mode(mode == "vision")
        except Exception:
            # If anything goes wrong, leave controls enabled.
            pass

        # Embedded stage tabs (only if already created)
        for tab in (self._capture_tab, self._ocr_tab,
                    self._translation_tab, self._llm_tab):
            if tab is not None:
                tab.load_config()

        self._original_state = self._get_current_state()

    def save_config(self):
        """Save configuration."""
        if not self.config_manager:
            return True, ""

        pl = self.plugins

        self.config_manager.set_setting(
            'pipeline.enable_optimizer_plugins',
            pl.plugins_enabled_check.isChecked())

        # OCR stability threshold
        self.config_manager.set_setting(
            'ocr.stability_threshold',
            pl.ocr_stability_threshold_spin.value())

        # Parallel Capture
        self.config_manager.set_setting(
            'pipeline.parallel_capture.enabled',
            pl.parallel_capture_enabled.isChecked())
        self.config_manager.set_setting(
            'pipeline.parallel_capture.workers',
            pl.parallel_capture_workers_spin.value())

        # Motion Tracker
        self.config_manager.set_setting(
            'pipeline.plugins.motion_tracker.enabled',
            pl.motion_plugin_enabled.isChecked())
        self.config_manager.set_setting(
            'pipeline.plugins.motion_tracker.threshold',
            pl.motion_threshold_spin.value())
        self.config_manager.set_setting(
            'pipeline.plugins.motion_tracker.smoothing',
            pl.motion_smoothing_spin.value())
        self.config_manager.set_setting(
            'pipeline.plugins.motion_tracker.max_motion_distance',
            pl.motion_max_distance_spin.value())
        self.config_manager.set_setting(
            'pipeline.plugins.motion_tracker.skip_ocr_on_motion',
            pl.motion_skip_ocr_check.isChecked())
        self.config_manager.set_setting(
            'pipeline.plugins.motion_tracker.update_overlay_positions',
            pl.motion_update_overlay_check.isChecked())
        self.config_manager.set_setting(
            'pipeline.plugins.motion_tracker.reocr_after_stop',
            pl.motion_reocr_check.isChecked())
        self.config_manager.set_setting(
            'pipeline.plugins.motion_tracker.stop_threshold_seconds',
            pl.motion_stop_threshold_spin.value())

        # Spell Corrector
        self.config_manager.set_setting(
            'pipeline.plugins.spell_corrector.enabled',
            pl.spell_plugin_enabled.isChecked())
        self.config_manager.set_setting(
            'pipeline.plugins.spell_corrector.aggressive_mode',
            pl.spell_aggressive_check.isChecked())
        self.config_manager.set_setting(
            'pipeline.plugins.spell_corrector.fix_capitalization',
            pl.spell_fix_caps_check.isChecked())
        self.config_manager.set_setting(
            'pipeline.plugins.spell_corrector.min_confidence',
            pl.spell_confidence_spin.value())
        self.config_manager.set_setting(
            'pipeline.plugins.spell_corrector.use_learning_dict',
            pl.spell_use_dict_check.isChecked())
        self.config_manager.set_setting(
            'pipeline.plugins.spell_corrector.language',
            pl.spell_language_combo.currentText())

        # Intelligent Text Processor
        self.config_manager.set_setting(
            'pipeline.plugins.intelligent_text_processor.enabled',
            pl.intelligent_plugin_enabled.isChecked())
        self.config_manager.set_setting(
            'pipeline.plugins.intelligent_text_processor.enable_corrections',
            pl.intelligent_corrections_check.isChecked())
        self.config_manager.set_setting(
            'pipeline.plugins.intelligent_text_processor.enable_context',
            pl.intelligent_context_check.isChecked())
        self.config_manager.set_setting(
            'pipeline.plugins.intelligent_text_processor.enable_validation',
            pl.intelligent_validation_check.isChecked())
        self.config_manager.set_setting(
            'pipeline.plugins.intelligent_text_processor.min_confidence',
            pl.intelligent_min_confidence_spin.value())
        self.config_manager.set_setting(
            'pipeline.plugins.intelligent_text_processor.min_word_length',
            pl.intelligent_min_word_length_spin.value())
        self.config_manager.set_setting(
            'pipeline.plugins.intelligent_text_processor.auto_learn',
            pl.intelligent_auto_learn_check.isChecked())

        # Translation Chain
        self.config_manager.set_setting(
            'pipeline.plugins.translation_chain.enabled',
            pl.chain_plugin_enabled.isChecked())
        self.config_manager.set_setting(
            'pipeline.plugins.translation_chain.intermediate_language',
            pl.chain_intermediate_lang_combo.currentText())
        self.config_manager.set_setting(
            'pipeline.plugins.translation_chain.quality_threshold',
            pl.chain_quality_threshold_spin.value())
        self.config_manager.set_setting(
            'pipeline.plugins.translation_chain.save_all_mappings',
            pl.chain_save_all_check.isChecked())
        self.config_manager.set_setting(
            'pipeline.plugins.translation_chain.enable_chaining',
            pl.chain_enable_chaining_check.isChecked())
        self.config_manager.set_setting(
            'pipeline.plugins.translation_chain.cache_intermediate',
            pl.chain_cache_intermediate_check.isChecked())

        # Text Block Merger
        self.config_manager.set_setting(
            'pipeline.plugins.text_block_merger.enabled',
            pl.merger_plugin_enabled.isChecked())
        self.config_manager.set_setting(
            'pipeline.plugins.text_block_merger.horizontal_threshold',
            pl.merger_h_threshold_spin.value())
        self.config_manager.set_setting(
            'pipeline.plugins.text_block_merger.vertical_threshold',
            pl.merger_v_threshold_spin.value())
        self.config_manager.set_setting(
            'pipeline.plugins.text_block_merger.merge_strategy',
            pl.merger_strategy_combo.currentText())

        # Parallel Translation
        self.config_manager.set_setting(
            'pipeline.plugins.parallel_translation.enabled',
            pl.parallel_trans_enabled.isChecked())
        self.config_manager.set_setting(
            'pipeline.plugins.parallel_translation.worker_threads',
            pl.parallel_trans_workers_spin.value())
        self.config_manager.set_setting(
            'pipeline.plugins.parallel_translation.batch_size',
            pl.parallel_trans_batch_spin.value())

        # OCR per Region
        self.config_manager.set_setting(
            'pipeline.plugins.ocr_per_region.enabled',
            pl.ocr_per_region_enabled.isChecked())
        self.config_manager.set_setting(
            'pipeline.plugins.ocr_per_region.default_ocr',
            pl.ocr_per_region_default_combo.currentText())

        # Regex Text Processor
        self.config_manager.set_setting(
            'pipeline.plugins.regex.enabled',
            pl.regex_plugin_enabled.isChecked())
        self.config_manager.set_setting(
            'pipeline.plugins.regex.filter_mode',
            pl.regex_filter_mode_combo.currentText())

        # Frame Skip
        self.config_manager.set_setting(
            'pipeline.plugins.frame_skip.max_skip_frames',
            pl.skip_max_frames_spin.value())
        self.config_manager.set_setting(
            'pipeline.plugins.frame_skip.adaptive_backoff',
            pl.skip_adaptive_check.isChecked())
        self.config_manager.set_setting(
            'pipeline.plugins.frame_skip.content_mode',
            pl.skip_content_mode_combo.currentText())

        # Translation Cache
        self.config_manager.set_setting(
            'pipeline.plugins.translation_cache.enable_fuzzy_match',
            pl.cache_fuzzy_check.isChecked())

        # Learning Dictionary
        self.config_manager.set_setting(
            'pipeline.plugins.learning_dictionary.auto_save',
            pl.dict_auto_save_check.isChecked())
        self.config_manager.set_setting(
            'pipeline.plugins.learning_dictionary.min_confidence',
            pl.dict_min_confidence_spin.value())
        self.config_manager.set_setting(
            'pipeline.plugins.learning_dictionary.validate_sentences',
            pl.dict_validate_check.isChecked())

        # Batch Processing
        self.config_manager.set_setting(
            'pipeline.plugins.batch_processing.min_batch_size',
            pl.batch_min_size_spin.value())
        self.config_manager.set_setting(
            'pipeline.plugins.batch_processing.adaptive',
            pl.batch_adaptive_check.isChecked())

        # Color Contrast
        self.config_manager.set_setting(
            'pipeline.plugins.color_contrast.fallback_text_light',
            pl.cc_fallback_light_edit.text())
        self.config_manager.set_setting(
            'pipeline.plugins.color_contrast.fallback_text_dark',
            pl.cc_fallback_dark_edit.text())

        # Priority Queue
        self.config_manager.set_setting(
            'pipeline.plugins.priority_queue.max_queue_size',
            pl.priority_max_queue_spin.value())
        self.config_manager.set_setting(
            'pipeline.plugins.priority_queue.starvation_prevention',
            pl.priority_starvation_check.isChecked())

        # Work Stealing
        self.config_manager.set_setting(
            'pipeline.plugins.work_stealing.steal_threshold',
            pl.work_steal_threshold_spin.value())
        self.config_manager.set_setting(
            'pipeline.plugins.work_stealing.enable_affinity',
            pl.work_affinity_check.isChecked())

        # Pipeline execution mode
        mode_index = self.overview.pipeline_mode_combo.currentIndex()
        mode_names = {0: "sequential", 1: "async", 2: "custom", 3: "subprocess"}
        mode = mode_names.get(mode_index, "sequential")
        self.config_manager.set_setting('pipeline.execution_mode', mode)

        # Per-stage modes (saved regardless; only used when mode == "custom")
        stage_idx_to_name = {0: "sequential", 1: "async"}
        stage_modes = {}
        for stage_name, combo_attr in [
            ('capture', 'custom_capture_combo'),
            ('ocr', 'custom_ocr_combo'),
            ('translation', 'custom_translation_combo'),
            ('overlay', 'custom_overlay_combo'),
        ]:
            combo = getattr(pl, combo_attr, None)
            if combo is not None:
                stage_modes[stage_name] = stage_idx_to_name.get(
                    combo.currentIndex(), "sequential")
        self.config_manager.set_setting('pipeline.stage_modes', stage_modes)

        # Audio Translation
        au = self.audio
        self.config_manager.set_setting(
            'plugins.audio_translation.enabled',
            au.audio_plugin_enabled.isChecked())
        self.config_manager.set_setting(
            'plugins.audio_translation.audio_mode',
            au.audio_mode.isChecked())
        self.config_manager.set_setting(
            'plugins.audio_translation.whisper_model',
            au.audio_whisper_model.currentText())
        self.config_manager.set_setting(
            'plugins.audio_translation.tts_engine',
            au.audio_tts_engine.currentText())
        self.config_manager.set_setting(
            'plugins.audio_translation.auto_play',
            au.audio_auto_play.isChecked())
        self.config_manager.set_setting(
            'plugins.audio_translation.voice_speed',
            au.audio_voice_speed.value())
        self.config_manager.set_setting(
            'plugins.audio_translation.mic_device',
            au.audio_mic_device.value())
        self.config_manager.set_setting(
            'plugins.audio_translation.speaker_device',
            au.audio_speaker_device.value())
        self.config_manager.set_setting(
            'plugins.audio_translation.vad_sensitivity',
            au.audio_vad_sensitivity.value())
        self.config_manager.set_setting(
            'plugins.audio_translation.use_gpu',
            au.audio_use_gpu.isChecked())

        try:
            self._save_all_plugin_json_files()
        except Exception:
            logger.warning("Failed to write plugin.json files", exc_info=True)

        # Vision section
        self.vision.save_config()

        # Embedded stage tabs (only if already created)
        for tab in (self._capture_tab, self._ocr_tab,
                    self._translation_tab, self._llm_tab):
            if tab is not None:
                tab.save_config()

        self.config_manager.save_config()

        self._original_state = self._get_current_state()
        return True, ""

    def validate(self) -> bool:
        """Validate settings."""
        return True

    def _get_current_state(self):
        """Get current state of all settings for change detection."""
        state = {}
        pl = self.plugins
        ov = self.overview
        au = self.audio

        state['plugins_enabled'] = pl.plugins_enabled_check.isChecked()
        state['execution_mode'] = ov.pipeline_mode_combo.currentIndex()

        for attr in ('custom_capture_combo', 'custom_ocr_combo',
                     'custom_translation_combo', 'custom_overlay_combo'):
            combo = getattr(pl, attr, None)
            if combo is not None:
                state[attr] = combo.currentIndex()

        for attr in ('skip_plugin_enabled', 'motion_plugin_enabled',
                     'parallel_capture_enabled', 'intelligent_plugin_enabled',
                     'spell_plugin_enabled', 'merger_plugin_enabled',
                     'ocr_per_region_enabled', 'parallel_plugin_enabled',
                     'regex_plugin_enabled', 'cache_plugin_enabled',
                     'dict_plugin_enabled', 'batch_plugin_enabled',
                     'parallel_trans_enabled', 'chain_plugin_enabled',
                     'color_contrast_enabled', 'priority_plugin_enabled',
                     'work_plugin_enabled', 'async_plugin_enabled'):
            widget = getattr(pl, attr, None)
            if widget is not None:
                state[attr] = widget.isChecked()

        state['skip_threshold'] = pl.skip_threshold_spin.value()
        state['skip_method'] = pl.skip_method_combo.currentIndex()
        state['skip_max_frames'] = pl.skip_max_frames_spin.value()
        state['skip_adaptive'] = pl.skip_adaptive_check.isChecked()
        state['skip_content_mode'] = pl.skip_content_mode_combo.currentIndex()
        state['ocr_stability_threshold'] = pl.ocr_stability_threshold_spin.value()

        state['motion_threshold'] = pl.motion_threshold_spin.value()
        state['motion_smoothing'] = pl.motion_smoothing_spin.value()
        state['motion_max_distance'] = pl.motion_max_distance_spin.value()
        state['motion_skip_ocr'] = pl.motion_skip_ocr_check.isChecked()
        state['motion_update_overlay'] = pl.motion_update_overlay_check.isChecked()
        state['motion_reocr'] = pl.motion_reocr_check.isChecked()
        state['motion_stop_threshold'] = pl.motion_stop_threshold_spin.value()

        state['parallel_capture_workers'] = pl.parallel_capture_workers_spin.value()

        state['intelligent_corrections'] = pl.intelligent_corrections_check.isChecked()
        state['intelligent_context'] = pl.intelligent_context_check.isChecked()
        state['intelligent_validation'] = pl.intelligent_validation_check.isChecked()
        state['intelligent_min_confidence'] = pl.intelligent_min_confidence_spin.value()
        state['intelligent_min_word_length'] = pl.intelligent_min_word_length_spin.value()
        state['intelligent_auto_learn'] = pl.intelligent_auto_learn_check.isChecked()

        state['spell_aggressive'] = pl.spell_aggressive_check.isChecked()
        state['spell_fix_caps'] = pl.spell_fix_caps_check.isChecked()
        state['spell_confidence'] = pl.spell_confidence_spin.value()
        state['spell_use_dict'] = pl.spell_use_dict_check.isChecked()
        state['spell_language'] = pl.spell_language_combo.currentIndex()

        state['merger_h_threshold'] = pl.merger_h_threshold_spin.value()
        state['merger_v_threshold'] = pl.merger_v_threshold_spin.value()
        state['merger_line_height'] = pl.merger_line_height_spin.value()
        state['merger_strategy'] = pl.merger_strategy_combo.currentIndex()
        state['merger_respect_punct'] = pl.merger_respect_punct_check.isChecked()
        state['merger_min_confidence'] = pl.merger_min_confidence_spin.value()

        state['ocr_per_region_default'] = pl.ocr_per_region_default_combo.currentIndex()
        state['ocr_per_region_parallel'] = pl.ocr_per_region_parallel_check.isChecked()
        state['ocr_per_region_cache'] = pl.ocr_per_region_cache_check.isChecked()

        state['regex_filter_mode'] = pl.regex_filter_mode_combo.currentIndex()
        state['regex_min_length'] = pl.regex_min_length_spin.value()
        state['regex_max_length'] = pl.regex_max_length_spin.value()

        state['parallel_workers'] = pl.parallel_workers_spin.value()

        state['cache_size'] = pl.cache_size_spin.value()
        state['cache_ttl'] = pl.cache_ttl_spin.value()
        state['cache_fuzzy'] = pl.cache_fuzzy_check.isChecked()

        state['dict_auto_save'] = pl.dict_auto_save_check.isChecked()
        state['dict_min_confidence'] = pl.dict_min_confidence_spin.value()
        state['dict_validate'] = pl.dict_validate_check.isChecked()

        state['batch_size'] = pl.batch_size_spin.value()
        state['batch_wait'] = pl.batch_wait_spin.value()
        state['batch_min_size'] = pl.batch_min_size_spin.value()
        state['batch_adaptive'] = pl.batch_adaptive_check.isChecked()

        state['parallel_trans_workers'] = pl.parallel_trans_workers_spin.value()
        state['parallel_trans_batch'] = pl.parallel_trans_batch_spin.value()
        state['parallel_trans_timeout'] = pl.parallel_trans_timeout_spin.value()
        state['parallel_trans_gpu'] = pl.parallel_trans_gpu_check.isChecked()
        state['parallel_trans_warm_start'] = pl.parallel_trans_warm_start_check.isChecked()
        state['parallel_trans_fallback'] = pl.parallel_trans_fallback_check.isChecked()

        state['chain_enable_chaining'] = pl.chain_enable_chaining_check.isChecked()
        state['chain_intermediate_lang'] = pl.chain_intermediate_lang_combo.currentIndex()
        state['chain_quality_threshold'] = pl.chain_quality_threshold_spin.value()
        state['chain_save_all'] = pl.chain_save_all_check.isChecked()
        state['chain_cache_intermediate'] = pl.chain_cache_intermediate_check.isChecked()

        if hasattr(pl, 'color_contrast_mode_combo'):
            state['cc_mode'] = pl.color_contrast_mode_combo.currentIndex()
            state['cc_ratio'] = pl.color_contrast_ratio_spin.value()
            state['cc_sample'] = pl.color_contrast_sample_spin.value()
            state['cc_fallback_light'] = pl.cc_fallback_light_edit.text()
            state['cc_fallback_dark'] = pl.cc_fallback_dark_edit.text()

        state['priority_max_queue'] = pl.priority_max_queue_spin.value()
        state['priority_starvation'] = pl.priority_starvation_check.isChecked()

        state['work_workers'] = pl.work_workers_spin.value()
        state['work_steal_threshold'] = pl.work_steal_threshold_spin.value()
        state['work_affinity'] = pl.work_affinity_check.isChecked()

        state['context_enabled'] = ov.new_context_check.isChecked()

        state['audio_enabled'] = au.audio_plugin_enabled.isChecked()
        state['audio_mode'] = au.audio_mode.isChecked()
        state['audio_whisper_model'] = au.audio_whisper_model.currentIndex()
        state['audio_tts_engine'] = au.audio_tts_engine.currentIndex()
        state['audio_auto_play'] = au.audio_auto_play.isChecked()
        state['audio_voice_speed'] = au.audio_voice_speed.value()
        state['audio_mic_device'] = au.audio_mic_device.value()
        state['audio_speaker_device'] = au.audio_speaker_device.value()
        state['audio_vad_sensitivity'] = au.audio_vad_sensitivity.value()
        state['audio_use_gpu'] = au.audio_use_gpu.isChecked()

        return state

    def get_state(self) -> dict:
        """Get the current state of the tab (SettingsTab protocol)."""
        return self._get_current_state()

    # ------------------------------------------------------------------
    # Audio Translation
    # ------------------------------------------------------------------

    def _open_audio_translation_dialog(self):
        """Open the audio translation dialog using PipelineFactory."""
        try:
            from ui.dialogs.audio_translation_dialog import (
                AudioTranslationDialog)
            from app.workflow.pipeline_factory import PipelineFactory

            factory = PipelineFactory(config_manager=self.config_manager)

            translation_layer = None
            try:
                if self.pipeline and hasattr(self.pipeline, 'translation_layer'):
                    translation_layer = self.pipeline.translation_layer
            except Exception as e:
                logger.warning(
                    "Could not retrieve translation layer: %s", e)

            dialog = AudioTranslationDialog(
                self.config_manager, factory, translation_layer, self)
            dialog.translationStarted.connect(
                self._on_audio_translation_started)
            dialog.translationStopped.connect(
                self._on_audio_translation_stopped)
            dialog.exec()

        except Exception as e:
            QMessageBox.critical(
                self,
                tr("error"),
                tr("audio_dialog_open_failed_message", error=str(e))
            )

    def _on_audio_translation_started(self) -> None:
        """Handle audio translation started event."""
        logger.info("Audio translation started")

    def _on_audio_translation_stopped(self) -> None:
        """Handle audio translation stopped event."""
        logger.info("Audio translation stopped")
