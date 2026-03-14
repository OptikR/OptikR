"""Settings tab for the Image Processing dialog.

Contains OCR/translation overrides, text rendering style options,
text erasure configuration, and preset management.
"""

import logging
from typing import Any

from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QGridLayout, QGroupBox,
    QLabel, QComboBox, QCheckBox, QPushButton, QSlider,
    QColorDialog, QFontComboBox, QInputDialog, QMessageBox,
)
from PyQt6.QtCore import Qt, pyqtSignal
from PyQt6.QtGui import QColor, QFont

from ui.common.widgets.custom_spinbox import CustomSpinBox
from ui.common.widgets.scroll_area_no_wheel import ScrollAreaNoWheel
from app.localization import TranslatableMixin, tr

logger = logging.getLogger(__name__)


class SettingsTab(TranslatableMixin, QWidget):
    """OCR/translation overrides, text rendering, and erasure settings."""

    settingChanged = pyqtSignal()

    def __init__(self, config_manager: Any = None, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.config_manager = config_manager
        self._preset_manager = None

        self.text_color = QColor("#FFFFFF")
        self.bg_color = QColor("#000000")

        self._init_ui()
        self.load_config()

    # ------------------------------------------------------------------
    # UI construction
    # ------------------------------------------------------------------

    def _init_ui(self) -> None:
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.setSpacing(0)

        scroll = ScrollAreaNoWheel()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(ScrollAreaNoWheel.Shape.NoFrame)
        scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        scroll.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAsNeeded)

        content = QWidget()
        content_layout = QVBoxLayout(content)
        content_layout.setContentsMargins(10, 10, 10, 10)
        content_layout.setSpacing(10)

        self._create_presets_section(content_layout)
        self._create_ocr_translation_section(content_layout)
        self._create_text_rendering_section(content_layout)
        self._create_text_erasure_section(content_layout)

        content_layout.addStretch()

        scroll.setWidget(content)
        main_layout.addWidget(scroll)

    # ------------------------------------------------------------------
    # Presets
    # ------------------------------------------------------------------

    def _create_presets_section(self, parent_layout: QVBoxLayout) -> None:
        group = QGroupBox()
        self.set_translatable_text(group, "image_processing_presets")
        layout = QVBoxLayout(group)
        layout.setSpacing(8)
        layout.setContentsMargins(15, 20, 15, 15)

        # Type filter row
        type_row = QHBoxLayout()
        self.preset_content_btn = QPushButton()
        self.set_translatable_text(self.preset_content_btn, "image_processing_preset_content")
        self.preset_content_btn.setCheckable(True)
        self.preset_content_btn.setChecked(True)
        self.preset_content_btn.clicked.connect(lambda: self._on_preset_type_changed("content"))
        type_row.addWidget(self.preset_content_btn)

        self.preset_style_btn = QPushButton()
        self.set_translatable_text(self.preset_style_btn, "image_processing_preset_style")
        self.preset_style_btn.setCheckable(True)
        self.preset_style_btn.clicked.connect(lambda: self._on_preset_type_changed("style"))
        type_row.addWidget(self.preset_style_btn)

        self.preset_custom_btn = QPushButton()
        self.set_translatable_text(self.preset_custom_btn, "image_processing_preset_custom")
        self.preset_custom_btn.setCheckable(True)
        self.preset_custom_btn.clicked.connect(lambda: self._on_preset_type_changed("custom"))
        type_row.addWidget(self.preset_custom_btn)

        type_row.addStretch()
        layout.addLayout(type_row)

        # Preset combo + buttons
        combo_row = QHBoxLayout()
        self.preset_combo = QComboBox()
        self.preset_combo.setMinimumWidth(200)
        combo_row.addWidget(self.preset_combo, 1)

        self.apply_preset_btn = QPushButton()
        self.set_translatable_text(self.apply_preset_btn, "image_processing_preset_apply")
        self.apply_preset_btn.setProperty("class", "action")
        self.apply_preset_btn.clicked.connect(self._on_apply_preset)
        combo_row.addWidget(self.apply_preset_btn)

        self.save_preset_btn = QPushButton()
        self.set_translatable_text(self.save_preset_btn, "image_processing_preset_save")
        self.save_preset_btn.clicked.connect(self._on_save_preset)
        combo_row.addWidget(self.save_preset_btn)

        self.delete_preset_btn = QPushButton()
        self.set_translatable_text(self.delete_preset_btn, "image_processing_preset_delete")
        self.delete_preset_btn.clicked.connect(self._on_delete_preset)
        combo_row.addWidget(self.delete_preset_btn)

        layout.addLayout(combo_row)

        # Description
        self.preset_desc_label = QLabel()
        self.preset_desc_label.setWordWrap(True)
        self.preset_desc_label.setStyleSheet("color: #888888; font-size: 9pt;")
        layout.addWidget(self.preset_desc_label)

        parent_layout.addWidget(group)
        self._populate_preset_combo()

    # ------------------------------------------------------------------
    # OCR & Translation
    # ------------------------------------------------------------------

    def _create_ocr_translation_section(self, parent_layout: QVBoxLayout) -> None:
        group = QGroupBox()
        self.set_translatable_text(group, "image_processing_ocr_translation")
        layout = QVBoxLayout(group)
        layout.setSpacing(8)
        layout.setContentsMargins(15, 20, 15, 15)

        self.use_main_settings_check = QCheckBox()
        self.set_translatable_text(self.use_main_settings_check, "image_processing_use_main_settings")
        self.use_main_settings_check.setChecked(True)
        self.use_main_settings_check.stateChanged.connect(self._on_use_main_settings_changed)
        self.use_main_settings_check.stateChanged.connect(lambda: self.settingChanged.emit())
        layout.addWidget(self.use_main_settings_check)

        # Override controls
        self.overrides_widget = QWidget()
        grid = QGridLayout(self.overrides_widget)
        grid.setContentsMargins(0, 5, 0, 0)
        grid.setSpacing(8)

        row = 0
        src_label = QLabel()
        self.set_translatable_text(src_label, "image_processing_source_language")
        self.source_lang_combo = QComboBox()
        self._populate_language_combo(self.source_lang_combo)
        self.source_lang_combo.currentIndexChanged.connect(lambda: self.settingChanged.emit())
        grid.addWidget(src_label, row, 0)
        grid.addWidget(self.source_lang_combo, row, 1)

        row += 1
        tgt_label = QLabel()
        self.set_translatable_text(tgt_label, "image_processing_target_language")
        self.target_lang_combo = QComboBox()
        self._populate_language_combo(self.target_lang_combo)
        self.target_lang_combo.currentIndexChanged.connect(lambda: self.settingChanged.emit())
        grid.addWidget(tgt_label, row, 0)
        grid.addWidget(self.target_lang_combo, row, 1)

        row += 1
        engine_label = QLabel()
        self.set_translatable_text(engine_label, "image_processing_ocr_engine")
        self.ocr_engine_combo = QComboBox()
        self._populate_ocr_engine_combo()
        self.ocr_engine_combo.currentIndexChanged.connect(lambda: self.settingChanged.emit())
        grid.addWidget(engine_label, row, 0)
        grid.addWidget(self.ocr_engine_combo, row, 1)

        layout.addWidget(self.overrides_widget)
        self.overrides_widget.setEnabled(False)

        parent_layout.addWidget(group)

    # ------------------------------------------------------------------
    # Text Rendering
    # ------------------------------------------------------------------

    def _create_text_rendering_section(self, parent_layout: QVBoxLayout) -> None:
        group = QGroupBox()
        self.set_translatable_text(group, "image_processing_text_rendering")
        layout = QGridLayout(group)
        layout.setSpacing(8)
        layout.setContentsMargins(15, 20, 15, 15)

        row = 0
        font_label = QLabel()
        self.set_translatable_text(font_label, "image_processing_font_family")
        self.font_family_combo = QFontComboBox()
        self.font_family_combo.setCurrentFont(QFont("Segoe UI"))
        self.font_family_combo.currentFontChanged.connect(lambda: self.settingChanged.emit())
        layout.addWidget(font_label, row, 0)
        layout.addWidget(self.font_family_combo, row, 1)

        row += 1
        size_label = QLabel()
        self.set_translatable_text(size_label, "image_processing_font_size")
        size_row = QHBoxLayout()
        self.font_size_spin = CustomSpinBox()
        self.font_size_spin.setRange(8, 72)
        self.font_size_spin.setValue(16)
        self.font_size_spin.valueChanged.connect(lambda: self.settingChanged.emit())
        size_row.addWidget(self.font_size_spin)
        self.auto_font_check = QCheckBox()
        self.set_translatable_text(self.auto_font_check, "image_processing_auto_font_size")
        self.auto_font_check.setChecked(True)
        self.auto_font_check.stateChanged.connect(lambda: self.settingChanged.emit())
        size_row.addWidget(self.auto_font_check)
        layout.addWidget(size_label, row, 0)
        layout.addLayout(size_row, row, 1)

        row += 1
        text_color_label = QLabel()
        self.set_translatable_text(text_color_label, "image_processing_text_color")
        self.text_color_btn = QPushButton()
        self.text_color_btn.clicked.connect(self._on_select_text_color)
        self._update_color_button(self.text_color_btn, self.text_color)
        layout.addWidget(text_color_label, row, 0)
        layout.addWidget(self.text_color_btn, row, 1)

        row += 1
        bg_row = QHBoxLayout()
        self.bg_enabled_check = QCheckBox()
        self.set_translatable_text(self.bg_enabled_check, "image_processing_background_enabled")
        self.bg_enabled_check.setChecked(True)
        self.bg_enabled_check.stateChanged.connect(self._on_bg_enabled_changed)
        bg_row.addWidget(self.bg_enabled_check)
        self.bg_color_btn = QPushButton()
        self.bg_color_btn.clicked.connect(self._on_select_bg_color)
        self._update_color_button(self.bg_color_btn, self.bg_color)
        bg_row.addWidget(self.bg_color_btn)
        layout.addLayout(bg_row, row, 0, 1, 2)

        row += 1
        opacity_label = QLabel()
        self.set_translatable_text(opacity_label, "image_processing_background_opacity")
        opacity_row = QHBoxLayout()
        self.opacity_slider = QSlider(Qt.Orientation.Horizontal)
        self.opacity_slider.setRange(0, 100)
        self.opacity_slider.setValue(85)
        self.opacity_slider.valueChanged.connect(self._on_opacity_slider_changed)
        opacity_row.addWidget(self.opacity_slider)
        self.opacity_value_label = QLabel("85%")
        self.opacity_value_label.setMinimumWidth(40)
        opacity_row.addWidget(self.opacity_value_label)
        layout.addWidget(opacity_label, row, 0)
        layout.addLayout(opacity_row, row, 1)

        row += 1
        self.border_check = QCheckBox()
        self.set_translatable_text(self.border_check, "image_processing_border_enabled")
        self.border_check.setChecked(False)
        self.border_check.stateChanged.connect(lambda: self.settingChanged.emit())
        layout.addWidget(self.border_check, row, 0, 1, 2)

        row += 1
        padding_label = QLabel()
        self.set_translatable_text(padding_label, "image_processing_padding")
        self.padding_spin = CustomSpinBox()
        self.padding_spin.setRange(0, 30)
        self.padding_spin.setValue(6)
        self.padding_spin.setSuffix(" px")
        self.padding_spin.valueChanged.connect(lambda: self.settingChanged.emit())
        layout.addWidget(padding_label, row, 0)
        layout.addWidget(self.padding_spin, row, 1)

        parent_layout.addWidget(group)

    # ------------------------------------------------------------------
    # Text Erasure
    # ------------------------------------------------------------------

    def _create_text_erasure_section(self, parent_layout: QVBoxLayout) -> None:
        group = QGroupBox()
        self.set_translatable_text(group, "image_processing_text_erasure")
        layout = QVBoxLayout(group)
        layout.setSpacing(8)
        layout.setContentsMargins(15, 20, 15, 15)

        self.erase_check = QCheckBox()
        self.set_translatable_text(self.erase_check, "image_processing_erase_original")
        self.erase_check.setChecked(True)
        self.erase_check.stateChanged.connect(self._on_erase_changed)
        layout.addWidget(self.erase_check)

        method_row = QHBoxLayout()
        method_label = QLabel()
        self.set_translatable_text(method_label, "image_processing_inpaint_method")
        self.inpaint_combo = QComboBox()
        self.inpaint_combo.addItem(tr("image_processing_inpaint_solid"), "solid_fill")
        self.inpaint_combo.addItem(tr("image_processing_inpaint_smart"), "inpaint")
        self.inpaint_combo.currentIndexChanged.connect(lambda: self.settingChanged.emit())
        method_row.addWidget(method_label)
        method_row.addWidget(self.inpaint_combo)
        method_row.addStretch()
        layout.addLayout(method_row)

        parent_layout.addWidget(group)

    # ------------------------------------------------------------------
    # Preset logic
    # ------------------------------------------------------------------

    def _get_preset_manager(self):
        if self._preset_manager is None:
            try:
                from app.image_processing.presets import PresetManager
                self._preset_manager = PresetManager()
            except ImportError:
                logger.debug("PresetManager not available yet")
        return self._preset_manager

    def _populate_preset_combo(self) -> None:
        self.preset_combo.clear()
        pm = self._get_preset_manager()
        if pm is None:
            return

        btn_type = "content"
        if self.preset_style_btn.isChecked():
            btn_type = "style"
        elif self.preset_custom_btn.isChecked():
            btn_type = "custom"

        try:
            if btn_type == "content":
                presets = pm.get_content_presets()
            elif btn_type == "style":
                presets = pm.get_style_presets()
            else:
                presets = pm.get_custom_presets()

            for preset in presets:
                self.preset_combo.addItem(preset.name, preset)
        except Exception as e:
            logger.debug("Failed to populate presets: %s", e)

        self.delete_preset_btn.setEnabled(btn_type == "custom")

    def _on_preset_type_changed(self, preset_type: str) -> None:
        for btn, t in [
            (self.preset_content_btn, "content"),
            (self.preset_style_btn, "style"),
            (self.preset_custom_btn, "custom"),
        ]:
            btn.setChecked(t == preset_type)
        self._populate_preset_combo()

    def _on_apply_preset(self) -> None:
        preset = self.preset_combo.currentData()
        if preset is None:
            return
        pm = self._get_preset_manager()
        if pm is None:
            return
        try:
            settings = preset.settings
            self._apply_settings_dict(settings)
            self.preset_desc_label.setText(getattr(preset, "description", ""))
            if self.config_manager:
                self.config_manager.set_setting("image_processing.active_preset", preset.name)
        except Exception as e:
            logger.warning("Failed to apply preset: %s", e)

    def _on_save_preset(self) -> None:
        name, ok = QInputDialog.getText(
            self, tr("image_processing_preset_save"), tr("image_processing_preset_save_name"),
        )
        if not ok or not name.strip():
            return
        pm = self._get_preset_manager()
        if pm is None:
            return
        try:
            settings = self.get_settings_dict()
            pm.save_custom_preset(name.strip(), settings)
            self._on_preset_type_changed("custom")
        except Exception as e:
            logger.warning("Failed to save preset: %s", e)

    def _on_delete_preset(self) -> None:
        preset = self.preset_combo.currentData()
        if preset is None or getattr(preset, "type", "") != "custom":
            return
        pm = self._get_preset_manager()
        if pm is None:
            return
        reply = QMessageBox.question(
            self,
            tr("image_processing_preset_delete"),
            tr("image_processing_preset_delete_confirm"),
        )
        if reply == QMessageBox.StandardButton.Yes:
            try:
                pm.delete_custom_preset(preset.name)
                self._populate_preset_combo()
            except Exception as e:
                logger.warning("Failed to delete preset: %s", e)

    # ------------------------------------------------------------------
    # Settings dict helpers
    # ------------------------------------------------------------------

    def get_settings_dict(self) -> dict[str, Any]:
        """Collect current widget values into a config-compatible dict."""
        return {
            "font_family": self.font_family_combo.currentFont().family(),
            "font_size": self.font_size_spin.value(),
            "auto_font_size": self.auto_font_check.isChecked(),
            "text_color": self.text_color.name(),
            "background_color": self.bg_color.name(),
            "background_enabled": self.bg_enabled_check.isChecked(),
            "background_opacity": self.opacity_slider.value() / 100.0,
            "border_enabled": self.border_check.isChecked(),
            "padding": self.padding_spin.value(),
            "erase_original_text": self.erase_check.isChecked(),
            "inpaint_method": self.inpaint_combo.currentData() or "solid_fill",
        }

    def get_compositor_config(self) -> dict[str, Any]:
        """Return settings formatted for the ImageCompositor."""
        return self.get_settings_dict()

    def get_language_overrides(self) -> tuple[str | None, str | None]:
        """Return (source, target) language overrides, or None if using main settings."""
        if self.use_main_settings_check.isChecked():
            return None, None
        src = self.source_lang_combo.currentData()
        tgt = self.target_lang_combo.currentData()
        return src, tgt

    def _apply_settings_dict(self, settings: dict[str, Any]) -> None:
        """Push settings values into widgets."""
        self.blockSignals(True)
        try:
            if "font_family" in settings:
                self.font_family_combo.setCurrentFont(QFont(settings["font_family"]))
            if "font_size" in settings:
                self.font_size_spin.setValue(settings["font_size"])
            if "auto_font_size" in settings:
                self.auto_font_check.setChecked(settings["auto_font_size"])
            if "text_color" in settings:
                self.text_color = QColor(settings["text_color"])
                self._update_color_button(self.text_color_btn, self.text_color)
            if "background_color" in settings:
                self.bg_color = QColor(settings["background_color"])
                self._update_color_button(self.bg_color_btn, self.bg_color)
            if "background_enabled" in settings:
                self.bg_enabled_check.setChecked(settings["background_enabled"])
            if "background_opacity" in settings:
                self.opacity_slider.setValue(int(settings["background_opacity"] * 100))
            if "border_enabled" in settings:
                self.border_check.setChecked(settings["border_enabled"])
            if "padding" in settings:
                self.padding_spin.setValue(settings["padding"])
            if "erase_original_text" in settings:
                self.erase_check.setChecked(settings["erase_original_text"])
            if "inpaint_method" in settings:
                idx = self.inpaint_combo.findData(settings["inpaint_method"])
                if idx >= 0:
                    self.inpaint_combo.setCurrentIndex(idx)
        finally:
            self.blockSignals(False)
        self.settingChanged.emit()

    # ------------------------------------------------------------------
    # load / save config
    # ------------------------------------------------------------------

    def load_config(self) -> None:
        if not self.config_manager:
            return
        try:
            self.blockSignals(True)
            g = self.config_manager.get_setting

            self.font_family_combo.setCurrentFont(QFont(g("image_processing.font_family", "Segoe UI")))
            self.font_size_spin.setValue(g("image_processing.font_size", 16))
            self.auto_font_check.setChecked(g("image_processing.auto_font_size", True))

            self.text_color = QColor(g("image_processing.text_color", "#FFFFFF"))
            self._update_color_button(self.text_color_btn, self.text_color)
            self.bg_color = QColor(g("image_processing.background_color", "#000000"))
            self._update_color_button(self.bg_color_btn, self.bg_color)
            self.bg_enabled_check.setChecked(g("image_processing.background_enabled", True))
            self.opacity_slider.setValue(int(g("image_processing.background_opacity", 0.85) * 100))
            self.border_check.setChecked(g("image_processing.border_enabled", False))
            self.padding_spin.setValue(g("image_processing.padding", 6))

            self.erase_check.setChecked(g("image_processing.erase_original_text", True))
            inpaint = g("image_processing.inpaint_method", "solid_fill")
            idx = self.inpaint_combo.findData(inpaint)
            if idx >= 0:
                self.inpaint_combo.setCurrentIndex(idx)

            self.use_main_settings_check.setChecked(g("image_processing.use_main_ocr_settings", True))
            self._on_use_main_settings_changed()

            self.blockSignals(False)
        except Exception as e:
            self.blockSignals(False)
            logger.warning("Failed to load settings tab config: %s", e)

    def save_config(self) -> tuple[bool, str]:
        if not self.config_manager:
            return False, "Configuration manager not available"
        try:
            s = self.config_manager.set_setting
            s("image_processing.font_family", self.font_family_combo.currentFont().family())
            s("image_processing.font_size", self.font_size_spin.value())
            s("image_processing.auto_font_size", self.auto_font_check.isChecked())
            s("image_processing.text_color", self.text_color.name())
            s("image_processing.background_color", self.bg_color.name())
            s("image_processing.background_enabled", self.bg_enabled_check.isChecked())
            s("image_processing.background_opacity", self.opacity_slider.value() / 100.0)
            s("image_processing.border_enabled", self.border_check.isChecked())
            s("image_processing.padding", self.padding_spin.value())
            s("image_processing.erase_original_text", self.erase_check.isChecked())
            s("image_processing.inpaint_method", self.inpaint_combo.currentData() or "solid_fill")
            s("image_processing.use_main_ocr_settings", self.use_main_settings_check.isChecked())
            s("image_processing.use_main_translation_settings", self.use_main_settings_check.isChecked())

            success, error_msg = self.config_manager.save_config()
            if not success:
                return False, error_msg
            return True, ""
        except Exception as e:
            return False, str(e)

    # ------------------------------------------------------------------
    # Widget event handlers
    # ------------------------------------------------------------------

    def _on_use_main_settings_changed(self) -> None:
        use_main = self.use_main_settings_check.isChecked()
        self.overrides_widget.setEnabled(not use_main)

    def _on_bg_enabled_changed(self, state: int) -> None:
        enabled = state == Qt.CheckState.Checked.value
        self.bg_color_btn.setEnabled(enabled)
        self.opacity_slider.setEnabled(enabled)
        self.opacity_value_label.setEnabled(enabled)
        self.settingChanged.emit()

    def _on_erase_changed(self, state: int) -> None:
        enabled = state == Qt.CheckState.Checked.value
        self.inpaint_combo.setEnabled(enabled)
        self.settingChanged.emit()

    def _on_opacity_slider_changed(self, value: int) -> None:
        self.opacity_value_label.setText(f"{value}%")
        self.settingChanged.emit()

    def _on_select_text_color(self) -> None:
        color = QColorDialog.getColor(self.text_color, self, tr("image_processing_text_color"))
        if color.isValid():
            self.text_color = color
            self._update_color_button(self.text_color_btn, self.text_color)
            self.settingChanged.emit()

    def _on_select_bg_color(self) -> None:
        color = QColorDialog.getColor(self.bg_color, self, tr("image_processing_background_color"))
        if color.isValid():
            self.bg_color = color
            self._update_color_button(self.bg_color_btn, self.bg_color)
            self.settingChanged.emit()

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------

    @staticmethod
    def _update_color_button(button: QPushButton, color: QColor) -> None:
        button.setText(f"  {color.name().upper()}  ")
        text_clr = "#FFFFFF" if color.lightness() < 128 else "#000000"
        button.setStyleSheet(
            f"QPushButton {{ background-color: {color.name()}; color: {text_clr}; "
            f"border: 2px solid #D0D0D0; border-radius: 3px; padding: 6px 12px; font-weight: 500; }} "
            f"QPushButton:hover {{ border: 2px solid #2196F3; }}"
        )

    def _populate_language_combo(self, combo: QComboBox) -> None:
        languages = [
            ("en", "English"), ("ja", "Japanese"), ("ko", "Korean"),
            ("zh", "Chinese"), ("de", "German"), ("fr", "French"),
            ("es", "Spanish"), ("it", "Italian"), ("pt", "Portuguese"),
            ("ru", "Russian"), ("ar", "Arabic"), ("nl", "Dutch"),
            ("pl", "Polish"), ("tr", "Turkish"), ("vi", "Vietnamese"),
            ("th", "Thai"),
        ]
        current_src = ""
        current_tgt = ""
        if self.config_manager:
            current_src = self.config_manager.get_setting("translation.source_language", "ja")
            current_tgt = self.config_manager.get_setting("translation.target_language", "de")

        for code, name in languages:
            combo.addItem(name, code)

        if combo is self.source_lang_combo:
            idx = combo.findData(current_src)
            if idx >= 0:
                combo.setCurrentIndex(idx)
        elif combo is self.target_lang_combo:
            idx = combo.findData(current_tgt)
            if idx >= 0:
                combo.setCurrentIndex(idx)

    def _populate_ocr_engine_combo(self) -> None:
        engines = [
            ("easyocr", "EasyOCR"),
            ("tesseract", "Tesseract"),
            ("mokuro", "Mokuro"),
            ("windowsocr", "Windows OCR"),
        ]
        current = ""
        if self.config_manager:
            current = self.config_manager.get_setting("ocr.engine", "easyocr")

        for engine_id, label in engines:
            self.ocr_engine_combo.addItem(label, engine_id)

        idx = self.ocr_engine_combo.findData(current)
        if idx >= 0:
            self.ocr_engine_combo.setCurrentIndex(idx)
