"""
LLM Settings Tab — main tab container.

Configures the optional LLM pipeline stage that sits between Translation
and Overlay.  Supports engine selection, processing mode, model variant,
generation parameters, and a conflict warning when the same Qwen3 model
is used for both translation and LLM.
"""

import logging

from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QGroupBox,
    QLabel, QComboBox, QCheckBox, QPushButton,
    QSlider, QSpinBox, QTextEdit, QDoubleSpinBox,
    QFrame,
)
from PyQt6.QtCore import Qt, pyqtSignal

from ui.common.widgets.scroll_area_no_wheel import ScrollAreaNoWheel
from app.localization import TranslatableMixin, tr

logger = logging.getLogger(__name__)

_MODE_OPTIONS = [
    ("refine",    "llm_mode_refine",    "llm_mode_refine_desc"),
    ("translate", "llm_mode_translate", "llm_mode_translate_desc"),
    ("custom",    "llm_mode_custom",    "llm_mode_custom_desc"),
]

_MODEL_VARIANTS = [
    ("Qwen/Qwen3-0.6B", "llm_model_0_6b_desc", "llm_model_0_6b_size"),
    ("Qwen/Qwen3-1.7B", "llm_model_1_7b_desc", "llm_model_1_7b_size"),
    ("Qwen/Qwen3-4B",   "llm_model_4b_desc",   "llm_model_4b_size"),
    ("Qwen/Qwen3-8B",   "llm_model_8b_desc",   "llm_model_8b_size"),
]

# Default system prompts (must match plugin defaults for preview accuracy)
_DEFAULT_REFINE_PROMPT = (
    "You are a professional editor. Refine the following translated text "
    "so it reads naturally in the target language. Preserve the original "
    "meaning. Output ONLY the refined text, nothing else."
)
_DEFAULT_TRANSLATE_PROMPT = (
    "You are a professional translator. Translate the following "
    "{src_lang} text into {tgt_lang}. Output ONLY the translation, "
    "nothing else."
)
_LLM_LANG_NAMES: dict[str, str] = {
    "ja": "Japanese", "en": "English", "de": "German", "fr": "French",
    "es": "Spanish", "it": "Italian", "pt": "Portuguese", "ru": "Russian",
    "zh": "Chinese", "ko": "Korean", "ar": "Arabic", "nl": "Dutch",
    "pl": "Polish", "tr": "Turkish",
}


class LLMSettingsTab(TranslatableMixin, QWidget):
    """LLM stage settings: engine, mode, model variant, parameters, and test."""

    settingChanged = pyqtSignal()
    llmEngineChanged = pyqtSignal(str)

    def __init__(self, config_manager=None, pipeline=None, parent=None):
        super().__init__(parent)

        self.config_manager = config_manager
        self.pipeline = pipeline

        self._original_state: dict = {}

        # Widgets populated during _init_ui
        self.enabled_check: QCheckBox | None = None
        self.engine_combo: QComboBox | None = None
        self.mode_combo: QComboBox | None = None
        self.model_combo: QComboBox | None = None
        self.temperature_slider: QSlider | None = None
        self.temperature_spinbox: QDoubleSpinBox | None = None
        self.max_tokens_spin: QSpinBox | None = None
        self.system_prompt_edit: QTextEdit | None = None
        self.prompt_preview_edit: QTextEdit | None = None
        self._custom_prompt_container: QWidget | None = None
        self._conflict_banner: QFrame | None = None
        self._conflict_label: QLabel | None = None
        self._custom_prompt_group: QGroupBox | None = None

        self._init_ui()

    # ------------------------------------------------------------------
    # UI construction
    # ------------------------------------------------------------------

    def _init_ui(self):
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.setSpacing(0)

        scroll_area = ScrollAreaNoWheel()
        scroll_area.setWidgetResizable(True)
        scroll_area.setFrameShape(ScrollAreaNoWheel.Shape.NoFrame)
        scroll_area.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        scroll_area.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAsNeeded)

        content_widget = QWidget()
        content_layout = QVBoxLayout(content_widget)
        content_layout.setContentsMargins(5, 5, 5, 5)
        content_layout.setSpacing(10)

        self._create_conflict_banner(content_layout)
        self._create_enable_section(content_layout)
        self._create_engine_section(content_layout)
        self._create_mode_section(content_layout)
        self._create_model_section(content_layout)
        self._create_parameters_section(content_layout)
        self._create_custom_prompt_section(content_layout)
        self._create_test_section(content_layout)
        self._create_model_management_section(content_layout)

        content_layout.addStretch()

        scroll_area.setWidget(content_widget)
        self._update_prompt_preview()
        self._update_prompt_visibility()
        main_layout.addWidget(scroll_area)

    # ── helpers ────────────────────────────────────────────────────────

    def _create_label(self, text: str, bold: bool = False) -> QLabel:
        label = QLabel(text)
        if bold:
            label.setStyleSheet("font-weight: 600; font-size: 9pt;")
        else:
            label.setStyleSheet("font-size: 9pt;")
        return label

    def _desc_label(self, text: str) -> QLabel:
        lbl = QLabel(text)
        lbl.setWordWrap(True)
        lbl.setStyleSheet("color: #666666; font-size: 8pt; margin-left: 20px; margin-bottom: 5px;")
        return lbl

    # ── conflict banner ───────────────────────────────────────────────

    def _create_conflict_banner(self, parent_layout):
        self._conflict_banner = QFrame()
        self._conflict_banner.setStyleSheet(
            "QFrame { background-color: #1e3a4f; border: 1px solid #4A9EFF; "
            "border-radius: 4px; padding: 10px; margin-bottom: 5px; }"
        )
        banner_layout = QVBoxLayout(self._conflict_banner)
        banner_layout.setContentsMargins(12, 8, 12, 8)

        self._conflict_label = QLabel(tr("llm_conflict_shared"))
        self._conflict_label.setWordWrap(True)
        self._conflict_label.setStyleSheet(
            "color: #90CAF9; font-size: 9pt; font-weight: 500;"
        )
        banner_layout.addWidget(self._conflict_label)

        self._conflict_banner.setVisible(False)
        parent_layout.addWidget(self._conflict_banner)

    # ── enable / disable ──────────────────────────────────────────────

    def _create_enable_section(self, parent_layout):
        group = QGroupBox(tr("llm_stage_group"))
        layout = QVBoxLayout(group)
        layout.setSpacing(8)
        layout.setContentsMargins(15, 20, 15, 15)

        self.enabled_check = QCheckBox(tr("llm_enable_check"))
        self.enabled_check.setStyleSheet("font-weight: bold;")
        self.enabled_check.stateChanged.connect(self._on_enabled_changed)
        layout.addWidget(self.enabled_check)

        layout.addWidget(self._desc_label(tr("llm_enable_description")))

        parent_layout.addWidget(group)

    # ── engine selection ──────────────────────────────────────────────

    def _create_engine_section(self, parent_layout):
        group = QGroupBox(tr("llm_engine_selection_group"))
        layout = QVBoxLayout(group)
        layout.setSpacing(8)
        layout.setContentsMargins(15, 20, 15, 15)

        layout.addWidget(self._create_label(tr("llm_engine_label"), bold=True))

        self.engine_combo = QComboBox()
        self.engine_combo.addItem(tr("llm_engine_qwen3"), "qwen3")
        self.engine_combo.setMaximumWidth(300)
        self.engine_combo.currentIndexChanged.connect(self._on_engine_changed)
        layout.addWidget(self.engine_combo)

        layout.addWidget(self._desc_label(tr("llm_engine_description")))

        parent_layout.addWidget(group)
        self._engine_group = group

    # ── mode selection ────────────────────────────────────────────────

    def _create_mode_section(self, parent_layout):
        group = QGroupBox(tr("llm_mode_group"))
        layout = QVBoxLayout(group)
        layout.setSpacing(8)
        layout.setContentsMargins(15, 20, 15, 15)

        layout.addWidget(self._create_label(tr("llm_mode_label"), bold=True))

        self.mode_combo = QComboBox()
        for mode_id, label_key, desc_key in _MODE_OPTIONS:
            self.mode_combo.addItem(f"{tr(label_key)} — {tr(desc_key)}", mode_id)
        self.mode_combo.setMaximumWidth(550)
        self.mode_combo.currentIndexChanged.connect(self._on_mode_changed)
        layout.addWidget(self.mode_combo)

        layout.addWidget(self._desc_label(tr("llm_mode_explanation")))

        parent_layout.addWidget(group)

    # ── model variant ─────────────────────────────────────────────────

    def _create_model_section(self, parent_layout):
        group = QGroupBox(tr("llm_model_variant_group"))
        layout = QVBoxLayout(group)
        layout.setSpacing(8)
        layout.setContentsMargins(15, 20, 15, 15)

        layout.addWidget(self._create_label(tr("llm_model_size_label"), bold=True))

        self.model_combo = QComboBox()
        for model_name, desc_key, size_key in _MODEL_VARIANTS:
            self.model_combo.addItem(f"{tr(desc_key)}  [{tr(size_key)}]", model_name)
        self.model_combo.setMaximumWidth(550)
        self.model_combo.currentIndexChanged.connect(self._on_setting_changed)
        layout.addWidget(self.model_combo)

        layout.addWidget(self._desc_label(tr("llm_model_description")))

        parent_layout.addWidget(group)

    # ── generation parameters ─────────────────────────────────────────

    def _create_parameters_section(self, parent_layout):
        group = QGroupBox(tr("llm_generation_params_group"))
        layout = QVBoxLayout(group)
        layout.setSpacing(10)
        layout.setContentsMargins(15, 20, 15, 15)

        # Temperature
        layout.addWidget(self._create_label(tr("llm_temp_label"), bold=True))

        temp_row = QHBoxLayout()
        temp_row.setSpacing(10)

        self.temperature_slider = QSlider(Qt.Orientation.Horizontal)
        self.temperature_slider.setRange(0, 200)  # 0.00 – 2.00
        self.temperature_slider.setValue(70)
        self.temperature_slider.setSingleStep(5)
        self.temperature_slider.setPageStep(10)
        self.temperature_slider.setTickPosition(QSlider.TickPosition.TicksBelow)
        self.temperature_slider.setTickInterval(20)
        self.temperature_slider.setMaximumWidth(220)
        self.temperature_slider.valueChanged.connect(self._on_temp_slider_changed)
        self.temperature_slider.sliderReleased.connect(self._on_setting_changed)
        temp_row.addWidget(self.temperature_slider)

        self.temperature_spinbox = QDoubleSpinBox()
        self.temperature_spinbox.setRange(0.00, 2.00)
        self.temperature_spinbox.setSingleStep(0.05)
        self.temperature_spinbox.setDecimals(2)
        self.temperature_spinbox.setValue(0.70)
        self.temperature_spinbox.setFixedWidth(70)
        self.temperature_spinbox.setStyleSheet("font-weight: 600; font-size: 9pt;")
        self.temperature_spinbox.valueChanged.connect(self._on_temp_spinbox_changed)
        temp_row.addWidget(self.temperature_spinbox)

        temp_row.addStretch()
        layout.addLayout(temp_row)

        layout.addWidget(self._desc_label(tr("llm_temp_description")))

        # Max tokens
        layout.addWidget(self._create_label(tr("llm_max_tokens_label"), bold=True))

        tokens_row = QHBoxLayout()
        tokens_row.setSpacing(10)

        self.max_tokens_spin = QSpinBox()
        self.max_tokens_spin.setRange(32, 4096)
        self.max_tokens_spin.setSingleStep(32)
        self.max_tokens_spin.setValue(256)
        self.max_tokens_spin.setFixedWidth(100)
        self.max_tokens_spin.setStyleSheet("font-weight: 600; font-size: 9pt;")
        self.max_tokens_spin.valueChanged.connect(self._on_setting_changed)
        tokens_row.addWidget(self.max_tokens_spin)

        tokens_row.addStretch()
        layout.addLayout(tokens_row)

        layout.addWidget(self._desc_label(tr("llm_max_tokens_description")))

        parent_layout.addWidget(group)

    # ── system prompt (visible for all modes; preview for Refine/Translate, edit for Custom)
    def _create_custom_prompt_section(self, parent_layout):
        self._custom_prompt_group = QGroupBox(tr("llm_prompt_section_title"))
        layout = QVBoxLayout(self._custom_prompt_group)
        layout.setSpacing(8)
        layout.setContentsMargins(15, 20, 15, 15)

        # Read-only preview for Refine / Translate (default prompts)
        self.prompt_preview_edit = QTextEdit()
        self.prompt_preview_edit.setReadOnly(True)
        self.prompt_preview_edit.setMaximumHeight(100)
        self.prompt_preview_edit.setStyleSheet(
            "font-size: 9pt; background-color: #252525; color: #c0c0c0;"
        )
        self.prompt_preview_edit.setPlaceholderText(tr("llm_prompt_using_default"))
        layout.addWidget(self.prompt_preview_edit)

        # Editable custom prompt (shown only in Custom mode)
        self._custom_prompt_container = QWidget()
        custom_layout = QVBoxLayout(self._custom_prompt_container)
        custom_layout.setContentsMargins(0, 8, 0, 0)
        custom_layout.setSpacing(4)
        custom_layout.addWidget(self._desc_label(tr("llm_custom_how_to_use")))
        self.system_prompt_edit = QTextEdit()
        self.system_prompt_edit.setPlaceholderText(tr("llm_custom_placeholder"))
        self.system_prompt_edit.setMaximumHeight(120)
        self.system_prompt_edit.setStyleSheet("font-size: 9pt;")
        self.system_prompt_edit.setToolTip(tr("llm_custom_speed_hint"))
        self.system_prompt_edit.textChanged.connect(self._on_setting_changed)
        custom_layout.addWidget(self.system_prompt_edit)
        custom_layout.addWidget(self._desc_label(tr("llm_custom_speed_hint")))
        layout.addWidget(self._custom_prompt_container)

        # Section always visible; preview vs edit visibility set in _update_prompt_visibility
        parent_layout.addWidget(self._custom_prompt_group)

    # ── test ──────────────────────────────────────────────────────────

    def _create_test_section(self, parent_layout):
        group = QGroupBox(tr("llm_test_group"))
        layout = QVBoxLayout(group)
        layout.setSpacing(10)
        layout.setContentsMargins(15, 20, 15, 15)

        layout.addWidget(self._desc_label(tr("llm_test_description")))

        btn_row = QHBoxLayout()
        test_btn = QPushButton(tr("llm_test_button"))
        test_btn.setProperty("class", "action")
        test_btn.setMinimumWidth(150)
        test_btn.clicked.connect(self._run_test)
        btn_row.addWidget(test_btn)
        btn_row.addStretch()
        layout.addLayout(btn_row)

        self._test_output = QLabel("")
        self._test_output.setWordWrap(True)
        self._test_output.setStyleSheet(
            "color: #B0B0B0; font-size: 9pt; padding: 8px; "
            "background-color: #1E1E1E; border-radius: 3px;"
        )
        self._test_output.setVisible(False)
        layout.addWidget(self._test_output)

        parent_layout.addWidget(group)

    # ── model management ──────────────────────────────────────────────

    def _create_model_management_section(self, parent_layout):
        group = QGroupBox(tr("llm_manage_group"))
        layout = QVBoxLayout(group)
        layout.setSpacing(10)
        layout.setContentsMargins(15, 20, 15, 15)

        layout.addWidget(self._desc_label(tr("llm_manage_description")))

        btn_row = QHBoxLayout()
        manage_btn = QPushButton(tr("llm_manage_button"))
        manage_btn.setProperty("class", "action")
        manage_btn.setToolTip(tr("llm_manage_tooltip"))
        manage_btn.clicked.connect(self._show_model_manager)
        btn_row.addWidget(manage_btn)
        btn_row.addStretch()
        layout.addLayout(btn_row)

        parent_layout.addWidget(group)

    # ------------------------------------------------------------------
    # Slot handlers
    # ------------------------------------------------------------------

    def _on_setting_changed(self):
        self.settingChanged.emit()

    def _on_enabled_changed(self, state):
        enabled = state == Qt.CheckState.Checked.value
        self._update_section_enabled_state(enabled)
        self._update_conflict_banner()
        self.settingChanged.emit()

    def _on_engine_changed(self, _index):
        engine = self.engine_combo.currentData()
        if engine:
            self.llmEngineChanged.emit(engine)
        self._update_conflict_banner()
        self.settingChanged.emit()

    def _on_mode_changed(self, _index):
        mode = self.mode_combo.currentData()
        self._update_prompt_preview()
        self._update_prompt_visibility()
        self._update_conflict_banner()
        self.settingChanged.emit()

    def _update_prompt_preview(self):
        """Set the read-only prompt preview text from mode and config (source/target lang)."""
        if not self.prompt_preview_edit or not self.mode_combo:
            return
        mode = self.mode_combo.currentData()
        if mode == "refine":
            self.prompt_preview_edit.setPlainText(_DEFAULT_REFINE_PROMPT)
        elif mode == "translate":
            src_code = "en"
            tgt_code = "en"
            if self.config_manager:
                src_code = self.config_manager.get_setting("translation.source_language", "en")
                tgt_code = self.config_manager.get_setting("translation.target_language", "en")
            src = _LLM_LANG_NAMES.get(src_code, src_code)
            tgt = _LLM_LANG_NAMES.get(tgt_code, tgt_code)
            self.prompt_preview_edit.setPlainText(
                _DEFAULT_TRANSLATE_PROMPT.format(src_lang=src, tgt_lang=tgt)
            )
        else:
            self.prompt_preview_edit.setPlainText("")

    def _update_prompt_visibility(self):
        """Show prompt preview for Refine/Translate, custom edit for Custom mode."""
        if not self.mode_combo:
            return
        mode = self.mode_combo.currentData()
        show_preview = mode in ("refine", "translate")
        if self.prompt_preview_edit is not None:
            self.prompt_preview_edit.setVisible(show_preview)
        if self._custom_prompt_container is not None:
            self._custom_prompt_container.setVisible(mode == "custom")

    def _on_temp_slider_changed(self, value):
        self.temperature_spinbox.blockSignals(True)
        self.temperature_spinbox.setValue(value / 100.0)
        self.temperature_spinbox.blockSignals(False)

    def _on_temp_spinbox_changed(self, value):
        self.temperature_slider.blockSignals(True)
        self.temperature_slider.setValue(int(round(value * 100)))
        self.temperature_slider.blockSignals(False)
        self._on_setting_changed()

    def _update_section_enabled_state(self, enabled: bool):
        """Enable or disable all config sections based on the master toggle."""
        for widget in (
            self.engine_combo, self.mode_combo, self.model_combo,
            self.temperature_slider, self.temperature_spinbox,
            self.max_tokens_spin, self.system_prompt_edit,
        ):
            if widget is not None:
                widget.setEnabled(enabled)

    # ── conflict detection ────────────────────────────────────────────

    def _update_conflict_banner(self):
        """Show or hide the shared-model information banner."""
        if not self._conflict_banner or not self.config_manager:
            return

        llm_enabled = self.enabled_check and self.enabled_check.isChecked()
        llm_engine = self.engine_combo.currentData() if self.engine_combo else ""
        llm_model = self.model_combo.currentData() if self.model_combo else ""

        trans_engine = self.config_manager.get_setting("translation.engine", "")
        trans_model = self.config_manager.get_setting("translation.model_name", "")

        is_conflict = (
            llm_enabled
            and llm_engine == "qwen3"
            and str(trans_engine).lower() == "qwen3"
        )
        same_variant = is_conflict and llm_model and llm_model == trans_model

        if is_conflict:
            mode = self.mode_combo.currentData() if self.mode_combo else "refine"
            if same_variant:
                msg = tr("llm_conflict_same_variant")
            else:
                msg = tr("llm_conflict_different_variant")
            if mode == "translate":
                msg += tr("llm_conflict_translate_mode")
            self._conflict_label.setText(msg)

        self._conflict_banner.setVisible(is_conflict)

    # ── test ──────────────────────────────────────────────────────────

    def _run_test(self):
        """Send sample text through the LLM engine."""
        self._test_output.setVisible(True)
        self._test_output.setText(tr("llm_test_running"))

        pipeline = self._get_pipeline()
        if not pipeline or not hasattr(pipeline, 'llm_layer') or pipeline.llm_layer is None:
            self._test_output.setText(tr("llm_test_layer_unavailable"))
            self._test_output.setStyleSheet(
                "color: #FF9800; font-size: 9pt; padding: 8px; "
                "background-color: #3a2a00; border-radius: 3px;"
            )
            return

        try:
            sample = "The quick brown fox jumps over the lazy dog."
            result = pipeline.llm_layer.process_text(sample)
            self._test_output.setText(f"Input:  {sample}\nOutput: {result}")
            self._test_output.setStyleSheet(
                "color: #66bb6a; font-size: 9pt; padding: 8px; "
                "background-color: #1e3a1e; border-radius: 3px;"
            )
        except Exception as exc:
            self._test_output.setText(tr("llm_test_failed", exc=str(exc)))
            self._test_output.setStyleSheet(
                "color: #F44336; font-size: 9pt; padding: 8px; "
                "background-color: #3a1e1e; border-radius: 3px;"
            )

    def _get_pipeline(self):
        parent = self.parent()
        while parent:
            if hasattr(parent, 'pipeline') and parent.pipeline:
                return parent.pipeline
            parent = parent.parent()
        return None

    # ── model manager ─────────────────────────────────────────────────

    def _show_model_manager(self):
        try:
            from .model_manager import LLMModelManager
            manager = LLMModelManager(parent=self, config_manager=self.config_manager)
            manager.show_llm_model_manager()
        except ImportError as exc:
            from PyQt6.QtWidgets import QMessageBox
            QMessageBox.warning(
                self,
                tr("llm_feature_not_available"),
                tr("llm_manager_load_error", exc=str(exc)),
            )

    # ------------------------------------------------------------------
    # Config load / save / validate
    # ------------------------------------------------------------------

    def _get_current_state(self) -> dict:
        state: dict = {}
        if self.enabled_check:
            state["enabled"] = self.enabled_check.isChecked()
        if self.engine_combo:
            state["engine"] = self.engine_combo.currentData()
        if self.mode_combo:
            state["mode"] = self.mode_combo.currentData()
        if self.model_combo:
            state["model_name"] = self.model_combo.currentData()
        if self.temperature_spinbox:
            state["temperature"] = self.temperature_spinbox.value()
        if self.max_tokens_spin:
            state["max_tokens"] = self.max_tokens_spin.value()
        if self.system_prompt_edit:
            state["system_prompt"] = self.system_prompt_edit.toPlainText()
        return state

    def on_change(self):
        self.settingChanged.emit()

    def load_config(self):
        """Load LLM settings from config manager."""
        if not self.config_manager:
            return

        try:
            enabled = self.config_manager.get_setting("llm.enabled", False)
            self.enabled_check.setChecked(enabled)

            # Engine
            engine = self.config_manager.get_setting("llm.engine", "qwen3")
            idx = self.engine_combo.findData(engine)
            if idx >= 0:
                self.engine_combo.setCurrentIndex(idx)

            # Mode
            mode = self.config_manager.get_setting("llm.mode", "refine")
            idx = self.mode_combo.findData(mode)
            if idx >= 0:
                self.mode_combo.setCurrentIndex(idx)
            if self._custom_prompt_group:
                self._custom_prompt_group.setVisible(mode == "custom")

            # Model variant
            model_name = self.config_manager.get_setting("llm.model_name", "Qwen/Qwen3-1.7B")
            idx = self.model_combo.findData(model_name)
            if idx >= 0:
                self.model_combo.setCurrentIndex(idx)

            # Temperature
            temp = self.config_manager.get_setting("llm.temperature", 0.7)
            self.temperature_spinbox.setValue(temp)
            self.temperature_slider.setValue(int(round(temp * 100)))

            # Max tokens
            max_tokens = self.config_manager.get_setting("llm.max_tokens", 256)
            self.max_tokens_spin.setValue(max_tokens)

            # Custom system prompt
            system_prompt = self.config_manager.get_setting("llm.system_prompt", "")
            self.system_prompt_edit.setPlainText(system_prompt)

            self._update_prompt_preview()
            self._update_prompt_visibility()
            self._update_section_enabled_state(enabled)
            self._update_conflict_banner()
            self._original_state = self._get_current_state()

        except Exception as exc:
            logger.error("Failed to load LLM settings: %s", exc, exc_info=True)

    def save_config(self):
        """Save LLM settings to config manager.

        Returns:
            tuple: (success: bool, error_message: str)
        """
        if not self.config_manager:
            return False, "Configuration manager not available"

        try:
            self.config_manager.set_setting("llm.enabled", self.enabled_check.isChecked())
            self.config_manager.set_setting("llm.engine", self.engine_combo.currentData())
            self.config_manager.set_setting("llm.mode", self.mode_combo.currentData())
            self.config_manager.set_setting("llm.model_name", self.model_combo.currentData())
            self.config_manager.set_setting("llm.temperature", self.temperature_spinbox.value())
            self.config_manager.set_setting("llm.max_tokens", self.max_tokens_spin.value())
            self.config_manager.set_setting("llm.system_prompt", self.system_prompt_edit.toPlainText())

            success, error_msg = self.config_manager.save_config()
            if not success:
                return False, error_msg

            self._original_state = self._get_current_state()
            logger.info("LLM settings saved to disk")
            return True, ""

        except Exception as exc:
            error_msg = f"Failed to save LLM settings: {exc}"
            logger.error(error_msg, exc_info=True)
            return False, error_msg

    def validate(self) -> bool:
        """Validate LLM settings."""
        if not self.enabled_check or not self.enabled_check.isChecked():
            return True

        if self.mode_combo and self.mode_combo.currentData() == "custom":
            prompt = self.system_prompt_edit.toPlainText().strip() if self.system_prompt_edit else ""
            if not prompt:
                logger.warning("Custom mode selected but system prompt is empty")
                return False

        return True
