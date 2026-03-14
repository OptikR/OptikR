"""
Translation Settings Tab — main tab container.

Composes the EngineSection (engine selection, API keys, local models) with
quality settings and advanced settings into a single scrollable tab.
"""

from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QGroupBox,
    QLabel, QCheckBox, QSlider, QLineEdit, QTextEdit,
)
from PyQt6.QtCore import Qt, pyqtSignal

from ui.common.widgets.scroll_area_no_wheel import ScrollAreaNoWheel
from .engine_section import EngineSection
from .cache_manager import TranslationCacheManager
import logging
from app.localization import TranslatableMixin, tr

logger = logging.getLogger(__name__)

_LEGACY_QWEN_PROMPT = (
    "Extract all visible text from this image and translate it from "
    "{source_lang} to {target_lang}. For each text region, return the "
    'translated text and its approximate bounding box as JSON: '
    '[{"text": "...", "bbox": [x, y, w, h]}]. Only return the JSON array, no other text.'
)

_NEW_QWEN_PROMPT = (
    "You are a translation engine. Translate the user text from "
    "{source_lang} to {target_lang}. Only return the translated text, "
    "with no explanations or additional formatting."
)


def _migrate_qwen_prompt(tpl: str) -> str:
    """Replace legacy (bbox/JSON) prompt with text-only prompt for text-mode pipeline."""
    if not tpl or not tpl.strip():
        return _NEW_QWEN_PROMPT
    if tpl.strip() == _LEGACY_QWEN_PROMPT:
        return _NEW_QWEN_PROMPT
    # Catch variants: e.g. (source_lang), [[{..., or "bounding box" + "bbox" + "JSON"
    if "bounding box" in tpl and "bbox" in tpl and "JSON" in tpl:
        return _NEW_QWEN_PROMPT
    return tpl


class TranslationSettingsTab(TranslatableMixin, QWidget):
    """Translation settings including engine selection, API keys, and configuration."""

    settingChanged = pyqtSignal()

    def __init__(self, config_manager=None, pipeline=None, parent=None):
        """Initialize the Translation settings tab."""
        super().__init__(parent)

        self.config_manager = config_manager
        self.pipeline = pipeline

        self._original_state = {}

        self.cache_manager = TranslationCacheManager(parent=self, pipeline=pipeline)

        # Quality/speed widgets
        self.quality_slider = None
        self.quality_value_label = None

        # Advanced settings widgets
        self.fallback_enabled_check = None
        self.preserve_formatting_check = None
        self.context_edit = None
        self.qwen_prompt_preview = None
        self._qwen_prompt_initialized = False

        # Vision-mode awareness
        self._content_widget = None
        self._vision_mode_banner = None

        # Composite engine section (engine selection, API keys, local models)
        self.engine_section = EngineSection(
            config_manager=config_manager,
            pipeline=pipeline,
            parent=self
        )
        self.engine_section.settingChanged.connect(self.on_change)

        self._init_ui()

    def _init_ui(self):
        """Initialize the UI."""
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.setSpacing(0)

        # Banner shown when this tab is partially disabled in vision mode.
        self._vision_mode_banner = QLabel()
        self._vision_mode_banner.setWordWrap(True)
        self._vision_mode_banner.setStyleSheet(
            "color: #999999; font-size: 8pt; padding: 4px 6px;"
        )
        self._vision_mode_banner.setVisible(False)
        self.set_translatable_text(
            self._vision_mode_banner,
            "vision_mode_translation_tab_disabled",
        )
        main_layout.addWidget(self._vision_mode_banner)

        scroll_area = ScrollAreaNoWheel()
        scroll_area.setWidgetResizable(True)
        scroll_area.setFrameShape(ScrollAreaNoWheel.Shape.NoFrame)
        scroll_area.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        scroll_area.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAsNeeded)

        content_widget = QWidget()
        self._content_widget = content_widget
        content_layout = QVBoxLayout(content_widget)
        content_layout.setContentsMargins(5, 5, 5, 5)
        content_layout.setSpacing(10)

        content_layout.addWidget(self.engine_section)
        self._create_quality_settings_section(content_layout)
        self._create_advanced_section(content_layout)

        content_layout.addStretch()

        scroll_area.setWidget(content_widget)
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
        state = self.engine_section.get_current_state()

        if hasattr(self.cache_manager, 'get_cache_settings'):
            state['cache_settings'] = self.cache_manager.get_cache_settings()

        if self.quality_slider:
            state['quality_level'] = self.quality_slider.value()
        if self.fallback_enabled_check:
            state['fallback_enabled'] = self.fallback_enabled_check.isChecked()
        if self.preserve_formatting_check:
            state['preserve_formatting'] = self.preserve_formatting_check.isChecked()
        if self.context_edit is not None:
            state['context'] = self.context_edit.text().strip()

        return state

    def on_change(self):
        """Called when any setting changes — always emits signal for main window to check."""
        # Keep Qwen3 prompt preview in sync with engine + context
        self._update_qwen_prompt_preview()
        self.settingChanged.emit()

    # ── Vision-mode awareness ─────────────────────────────────────────

    def set_pipeline_mode(self, is_vision: bool) -> None:
        """
        Enable/disable text-translation controls based on pipeline mode.

        In vision mode the Qwen3-VL stage handles OCR + translation in one
        pass, so classic translation engine settings become read-only.
        """
        if self._content_widget is not None:
            self._content_widget.setEnabled(not is_vision)
        if self._vision_mode_banner is not None:
            self._vision_mode_banner.setVisible(is_vision)

    def on_setting_changed(self, key: str, value) -> None:
        """React to cross-tab setting changes from SettingsCoordinator."""
        if key == "pipeline.mode":
            self.set_pipeline_mode(str(value) == "vision")

    # ── Quality settings ─────────────────────────────────────────────

    def _create_quality_settings_section(self, parent_layout):
        """Create translation quality settings section."""
        quality_group = QGroupBox()
        self.set_translatable_text(quality_group, "translation_quality_section")
        layout = QVBoxLayout(quality_group)
        layout.setSpacing(12)
        layout.setContentsMargins(15, 20, 15, 15)

        quality_label = self._create_label("", bold=True)
        self.set_translatable_text(quality_label, "translation_quality_tradeoff_label")
        layout.addWidget(quality_label)

        slider_layout = QHBoxLayout()
        slider_layout.setSpacing(10)

        speed_label = QLabel()
        speed_label.setStyleSheet("font-size: 8pt; color: #666666;")
        self.set_translatable_text(speed_label, "translation_quality_fast")
        slider_layout.addWidget(speed_label)

        self.quality_slider = QSlider(Qt.Orientation.Horizontal)
        self.quality_slider.setRange(0, 100)
        self.quality_slider.setValue(70)
        self.quality_slider.setSingleStep(5)
        self.quality_slider.setPageStep(25)
        self.quality_slider.setTickPosition(QSlider.TickPosition.TicksBelow)
        self.quality_slider.setTickInterval(25)
        self.quality_slider.setMaximumWidth(220)
        self.quality_slider.valueChanged.connect(self._update_quality_label)
        self.quality_slider.valueChanged.connect(lambda: self.on_change())
        self.quality_slider.sliderReleased.connect(self.on_change)
        slider_layout.addWidget(self.quality_slider)

        quality_right_label = QLabel()
        quality_right_label.setStyleSheet("font-size: 8pt; color: #666666;")
        self.set_translatable_text(quality_right_label, "translation_quality_high_quality")
        slider_layout.addWidget(quality_right_label)

        self.quality_value_label = QLabel(tr("translation_quality_high"))
        self.quality_value_label.setStyleSheet("font-weight: 600; font-size: 9pt;")
        self.quality_value_label.setFixedWidth(70)
        slider_layout.addWidget(self.quality_value_label)

        slider_layout.addStretch()
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
            quality_text = tr("translation_quality_fast")
        elif value < 50:
            quality_text = tr("translation_quality_balanced")
        elif value < 75:
            quality_text = tr("translation_quality_high")
        else:
            quality_text = tr("translation_quality_maximum")

        self.quality_value_label.setText(quality_text)

    # ── Advanced settings ────────────────────────────────────────────

    def _create_advanced_section(self, parent_layout):
        """Create advanced translation settings section."""
        group = QGroupBox()
        self.set_translatable_text(group, "translation_advanced_settings")
        layout = QVBoxLayout(group)
        layout.setSpacing(8)
        layout.setContentsMargins(15, 20, 15, 15)

        self.fallback_enabled_check = QCheckBox()
        self.set_translatable_text(self.fallback_enabled_check, "translation_fallback_enabled")
        self.fallback_enabled_check.setChecked(True)
        self.fallback_enabled_check.stateChanged.connect(self.on_change)
        layout.addWidget(self.fallback_enabled_check)

        fallback_desc = QLabel()
        self.set_translatable_text(fallback_desc, "translation_fallback_desc")
        fallback_desc.setStyleSheet("color: #666666; font-size: 8pt; margin-left: 20px; margin-bottom: 10px;")
        layout.addWidget(fallback_desc)

        self.preserve_formatting_check = QCheckBox()
        self.set_translatable_text(self.preserve_formatting_check, "translation_preserve_formatting")
        self.preserve_formatting_check.setChecked(True)
        self.preserve_formatting_check.stateChanged.connect(self.on_change)
        layout.addWidget(self.preserve_formatting_check)

        format_desc = QLabel()
        self.set_translatable_text(format_desc, "translation_preserve_formatting_desc")
        format_desc.setStyleSheet("color: #666666; font-size: 8pt; margin-left: 20px;")
        layout.addWidget(format_desc)

        context_label = QLabel()
        self.set_translatable_text(context_label, "translation_context")
        context_label.setStyleSheet("font-size: 9pt;")
        layout.addWidget(context_label)
        self.context_edit = QLineEdit()
        self.context_edit.setPlaceholderText("e.g. Manga dialogue. / Technical document.")
        self.context_edit.setStyleSheet("font-size: 9pt;")
        self.context_edit.textChanged.connect(lambda: self.on_change())
        layout.addWidget(self.context_edit)
        context_hint = QLabel()
        self.set_translatable_text(context_hint, "translation_context_hint")
        context_hint.setWordWrap(True)
        context_hint.setStyleSheet("color: #666666; font-size: 8pt; margin-left: 20px;")
        layout.addWidget(context_hint)

        # Qwen3 prompt preview (helps users see how Context becomes part of the system prompt)
        prompt_label = QLabel()
        self.set_translatable_text(prompt_label, "translation_qwen_prompt_label")
        prompt_label.setStyleSheet("font-size: 9pt; margin-top: 10px;")
        layout.addWidget(prompt_label)

        self.qwen_prompt_preview = QTextEdit()
        self.qwen_prompt_preview.setReadOnly(False)
        self.qwen_prompt_preview.setMaximumHeight(100)
        self.qwen_prompt_preview.setStyleSheet(
            "font-size: 9pt; background-color: #252525; color: #c0c0c0;"
        )
        self.qwen_prompt_preview.textChanged.connect(lambda: self.settingChanged.emit())
        layout.addWidget(self.qwen_prompt_preview)

        prompt_hint = QLabel()
        self.set_translatable_text(prompt_hint, "translation_qwen_prompt_hint")
        prompt_hint.setWordWrap(True)
        prompt_hint.setStyleSheet("color: #666666; font-size: 8pt; margin-left: 20px;")
        layout.addWidget(prompt_hint)

        parent_layout.addWidget(group)

        # Initialize preview once widgets exist
        self._update_qwen_prompt_preview()

    def _update_qwen_prompt_preview(self):
        """Keep the Qwen3 prompt editor in a sensible state."""
        if not self.qwen_prompt_preview:
            return

        engine = None
        try:
            engine = self.engine_section.get_selected_engine()
        except Exception:
            engine = None

        if engine != "qwen3":
            # Only relevant when Qwen3 is selected as the translation engine
            self.qwen_prompt_preview.setReadOnly(True)
            self.qwen_prompt_preview.setPlainText(
                tr("translation_qwen_prompt_engine_hint")
            )
            return

        # When Qwen3 is active, this field becomes an editable template.
        self.qwen_prompt_preview.setReadOnly(False)
        if self._qwen_prompt_initialized:
            return

        # Initialize from config (or schema default) the first time.
        template_text = ""
        if self.config_manager:
            try:
                template_text = self.config_manager.get_setting(
                    "translation.qwen_prompt_template",
                    "",
                )
            except Exception:
                template_text = ""
        template_text = _migrate_qwen_prompt(template_text)
        self.qwen_prompt_preview.setPlainText(template_text)
        self._qwen_prompt_initialized = True

    # ── Config load / save / validate ────────────────────────────────

    def load_config(self):
        """Load configuration from config manager (user_config.json only)."""
        if not self.config_manager:
            return

        try:
            logger.debug("Loading translation settings from user_config.json")

            self.engine_section.load_config(self.config_manager)

            # Quality setting
            quality = self.config_manager.get_setting('translation.quality_level', 70)
            self.quality_slider.setValue(quality)
            self._update_quality_label(quality)

            # Advanced settings
            self.fallback_enabled_check.setChecked(
                self.config_manager.get_setting('translation.fallback_enabled', True)
            )
            self.preserve_formatting_check.setChecked(
                self.config_manager.get_setting('translation.preserve_formatting', True)
            )
            if self.context_edit is not None:
                self.context_edit.setText(
                    self.config_manager.get_setting('translation.context', '')
                )
            if self.qwen_prompt_preview is not None:
                try:
                    tpl = self.config_manager.get_setting(
                        "translation.qwen_prompt_template",
                        "",
                    )
                except Exception:
                    tpl = ""
                tpl = _migrate_qwen_prompt(tpl)
                try:
                    engine = self.engine_section.get_selected_engine()
                except Exception:
                    engine = None
                if engine == "qwen3":
                    self.qwen_prompt_preview.setReadOnly(False)
                    self.qwen_prompt_preview.setPlainText(tpl)
                else:
                    self.qwen_prompt_preview.setReadOnly(True)
                    self.qwen_prompt_preview.setPlainText(
                        tr("translation_qwen_prompt_engine_hint")
                    )
                self._qwen_prompt_initialized = bool(tpl.strip())

            self._original_state = self._get_current_state()

            # Apply pipeline-mode specific enabling/disabling on load
            try:
                mode = self.config_manager.get_setting('pipeline.mode', 'text')
                self.set_pipeline_mode(mode == "vision")
            except Exception:
                # If anything goes wrong, leave controls enabled.
                pass

        except Exception as e:
            logger.error("Failed to load translation settings: %s", e, exc_info=True)

    def save_config(self):
        """
        Save configuration to config manager (user_config.json only).

        Returns:
            tuple: (success: bool, error_message: str)
        """
        if not self.config_manager:
            return False, "Configuration manager not available"

        try:
            old_engine = self.config_manager.get_setting('translation.engine', 'marianmt_gpu')
            old_qwen_tpl = self.config_manager.get_setting(
                "translation.qwen_prompt_template",
                "",
            )
            self.engine_section.save_config(self.config_manager)

            self.config_manager.set_setting('translation.quality_level', self.quality_slider.value())
            self.config_manager.set_setting('translation.fallback_enabled', self.fallback_enabled_check.isChecked())
            self.config_manager.set_setting('translation.preserve_formatting', self.preserve_formatting_check.isChecked())
            if self.context_edit is not None:
                self.config_manager.set_setting(
                    'translation.context', self.context_edit.text().strip()
                )
            if self.qwen_prompt_preview is not None:
                self.config_manager.set_setting(
                    "translation.qwen_prompt_template",
                    self.qwen_prompt_preview.toPlainText().strip(),
                )
            new_qwen_tpl = ""
            if self.qwen_prompt_preview is not None:
                new_qwen_tpl = self.qwen_prompt_preview.toPlainText().strip()

            success, error_msg = self.config_manager.save_config()

            if not success:
                return False, error_msg

            # Apply translation engine switch at runtime so the new engine is used without restart
            new_engine = self.engine_section.get_selected_engine()
            if self.pipeline and new_engine and new_engine != old_engine:
                try:
                    if self.pipeline.set_translation_engine(new_engine):
                        logger.info("Translation engine switched to %s", new_engine)
                    else:
                        logger.warning("Failed to switch translation engine to %s", new_engine)
                except Exception as e:
                    logger.warning("Error switching translation engine: %s", e)
            elif (
                self.pipeline
                and new_engine == "qwen3"
                and old_engine == "qwen3"
                and old_qwen_tpl.strip() != new_qwen_tpl.strip()
            ):
                # Prompt template is consumed at engine init time.
                # Force a lightweight unload/reload so prompt edits apply immediately.
                try:
                    if hasattr(self.pipeline, "translation_layer") and self.pipeline.translation_layer:
                        self.pipeline.translation_layer.unload_engine("qwen3")
                    if self.pipeline.set_translation_engine("qwen3"):
                        logger.info(
                            "Qwen3 translation prompt updated; engine reloaded to apply changes"
                        )
                    else:
                        logger.warning(
                            "Failed to reload Qwen3 after prompt update; restart may be required"
                        )
                except Exception as e:
                    logger.warning(
                        "Error reloading Qwen3 after prompt update: %s", e
                    )

            self._original_state = self._get_current_state()

            logger.info("Translation settings saved to disk")
            return True, ""

        except Exception as e:
            error_msg = f"Failed to save settings: {e}"
            logger.error(error_msg, exc_info=True)
            return False, error_msg

    def validate(self) -> bool:
        """Validate settings including API key format validation."""
        return self.engine_section.validate()
