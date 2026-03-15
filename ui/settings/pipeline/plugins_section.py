"""
Pipeline Plugins-by-Stage Section

Plugin settings organized by pipeline stage (Capture, OCR, Translation,
Overlay, Global) with detailed configuration controls.
"""

import logging

from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QGroupBox, QLabel, QPushButton,
    QCheckBox, QFormLayout, QComboBox, QLineEdit,
)
from PyQt6.QtCore import pyqtSignal
from ui.common.widgets.custom_spinbox import CustomSpinBox, CustomDoubleSpinBox

from app.localization import TranslatableMixin, tr

logger = logging.getLogger(__name__)


class PluginsByStageSection(TranslatableMixin, QWidget):
    """Plugins organized by pipeline stage with detailed configuration."""

    settingChanged = pyqtSignal()

    def __init__(self, parent=None):
        super().__init__(parent)
        self._init_ui()
        self._connect_change_signals()

    def _connect_change_signals(self):
        """Auto-connect all interactive widgets to settingChanged so the save button activates."""
        for w in self.findChildren(QCheckBox):
            w.stateChanged.connect(self.settingChanged.emit)
        for w in self.findChildren(CustomSpinBox):
            w.valueChanged.connect(self.settingChanged.emit)
        for w in self.findChildren(CustomDoubleSpinBox):
            w.valueChanged.connect(self.settingChanged.emit)
        for w in self.findChildren(QComboBox):
            w.currentIndexChanged.connect(self.settingChanged.emit)
        for w in self.findChildren(QLineEdit):
            w.textChanged.connect(self.settingChanged.emit)

    def _init_ui(self):
        layout = QVBoxLayout(self)
        layout.setSpacing(15)

        # Header
        header_label = QLabel()
        self.set_translatable_text(header_label, "plugins_section_title")
        header_label.setStyleSheet("font-size: 14pt; font-weight: bold;")
        layout.addWidget(header_label)

        # Essential plugins info banner
        essential_info = QLabel()
        self.set_translatable_text(essential_info, "plugins_essential_info")
        essential_info.setWordWrap(True)
        essential_info.setStyleSheet(
            "background-color: #FFF3CD; color: #856404; padding: 10px; "
            "border: 1px solid #FFE69C; border-radius: 5px; "
            "font-size: 9pt; font-weight: bold;"
        )
        layout.addWidget(essential_info)

        # Master toggle
        self.plugins_enabled_check = QCheckBox()
        self.set_translatable_text(
            self.plugins_enabled_check,
            "pipeline_management_enable_optional_optimizer_plugins_check")
        self.plugins_enabled_check.setChecked(True)
        self.plugins_enabled_check.setStyleSheet(
            "font-weight: bold; font-size: 11pt;")
        self.set_translatable_text(
            self.plugins_enabled_check,
            "plugins_master_toggle_tooltip", method="setToolTip")
        layout.addWidget(self.plugins_enabled_check)

        # CAPTURE STAGE
        capture_stage = self._create_capture_stage_section()
        layout.addWidget(capture_stage)

        # OCR STAGE
        ocr_stage = self._create_ocr_stage_section()
        layout.addWidget(ocr_stage)

        # TRANSLATION STAGE
        translation_stage = self._create_translation_stage_section()
        layout.addWidget(translation_stage)

        # OVERLAY STAGE
        overlay_stage = self._create_overlay_stage_section()
        layout.addWidget(overlay_stage)

        # GLOBAL PLUGINS
        global_stage = self._create_global_stage_section()
        layout.addWidget(global_stage)

        # Apply button
        self.apply_btn = QPushButton()
        self.set_translatable_text(
            self.apply_btn,
            "pipeline_management_apply_all_changes_button")
        self.apply_btn.setProperty("class", "action")
        layout.addWidget(self.apply_btn)

        # Performance summary
        perf_label = QLabel()
        self.set_translatable_text(perf_label, "plugins_perf_summary")
        perf_label.setWordWrap(True)
        perf_label.setStyleSheet(
            "color: #0066CC; font-size: 9pt; padding: 10px; "
            "background-color: #E6F2FF; border-radius: 5px;")
        layout.addWidget(perf_label)

        layout.addStretch()

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------

    @staticmethod
    def _create_pipeline_badge(audio_compatible: bool) -> QLabel:
        """Create a small styled label indicating pipeline compatibility."""
        badge = QLabel()
        if audio_compatible:
            badge.setText("\U0001f50a Visual + Audio")
            badge.setStyleSheet(
                "color: #2e7d32; background-color: #e8f5e9; "
                "border: 1px solid #a5d6a7; border-radius: 3px; "
                "padding: 1px 6px; font-size: 7pt; font-weight: bold;"
            )
            badge.setToolTip(
                "This plugin works with both the visual and audio pipelines")
        else:
            badge.setText("\U0001f5bc Visual only")
            badge.setStyleSheet(
                "color: #616161; background-color: #f5f5f5; "
                "border: 1px solid #e0e0e0; border-radius: 3px; "
                "padding: 1px 6px; font-size: 7pt; font-weight: bold;"
            )
            badge.setToolTip(
                "This plugin only works with the visual translation pipeline")
        badge.setFixedHeight(18)
        return badge

    # ------------------------------------------------------------------
    # Stage section builders
    # ------------------------------------------------------------------

    def _create_capture_stage_section(self) -> QGroupBox:
        """Create capture stage plugins section."""
        group = QGroupBox()
        self.set_translatable_text(
            group, "pipeline_management_capture_stage_section")
        layout = QVBoxLayout(group)

        # Frame Skip Plugin (ESSENTIAL)
        skip_group = QGroupBox()
        self.set_translatable_text(
            skip_group,
            "pipeline_management_frame_skip_optimizer_essential_section")
        skip_layout = QFormLayout(skip_group)

        self.skip_plugin_enabled = QCheckBox()
        self.set_translatable_text(
            self.skip_plugin_enabled,
            "pipeline_management_enabled_check")
        self.skip_plugin_enabled.setChecked(True)
        self.set_translatable_text(
            self.skip_plugin_enabled,
            "plugins_essential_bypass_tooltip", method="setToolTip")
        skip_layout.addRow(tr("plugins_status_label"), self.skip_plugin_enabled)

        skip_desc = QLabel()
        self.set_translatable_text(skip_desc, "plugins_frame_skip_desc")
        skip_desc.setStyleSheet("color: #666666; font-size: 8pt;")
        skip_layout.addRow("", skip_desc)
        skip_layout.addRow("", self._create_pipeline_badge(audio_compatible=False))

        self.skip_threshold_spin = CustomDoubleSpinBox()
        self.skip_threshold_spin.setDecimals(2)
        self.skip_threshold_spin.setRange(0.80, 0.99)
        self.skip_threshold_spin.setSingleStep(0.01)
        self.skip_threshold_spin.setValue(0.95)
        skip_layout.addRow(
            tr("plugins_similarity_threshold_label"),
            self.skip_threshold_spin)

        self.skip_method_combo = QComboBox()
        self.skip_method_combo.addItems(["hash", "mse", "ssim"])
        skip_layout.addRow(
            tr("plugins_comparison_method_label"), self.skip_method_combo)

        self.skip_max_frames_spin = CustomSpinBox()
        self.skip_max_frames_spin.setRange(10, 1000)
        self.skip_max_frames_spin.setValue(300)
        self.set_translatable_text(
            self.skip_max_frames_spin,
            "plugins_skip_max_frames_tooltip", method="setToolTip")
        skip_layout.addRow(
            tr("plugins_skip_max_frames_label"),
            self.skip_max_frames_spin)

        self.skip_adaptive_check = QCheckBox()
        self.set_translatable_text(
            self.skip_adaptive_check,
            "plugins_skip_adaptive_check")
        self.skip_adaptive_check.setChecked(True)
        self.set_translatable_text(
            self.skip_adaptive_check,
            "plugins_skip_adaptive_tooltip", method="setToolTip")
        skip_layout.addRow("", self.skip_adaptive_check)

        self.skip_content_mode_combo = QComboBox()
        self.skip_content_mode_combo.addItems(["static", "dynamic"])
        self.set_translatable_text(
            self.skip_content_mode_combo,
            "plugins_skip_content_mode_tooltip", method="setToolTip")
        skip_layout.addRow(
            tr("plugins_skip_content_mode_label"),
            self.skip_content_mode_combo)

        layout.addWidget(skip_group)

        # Motion Tracker Plugin
        motion_group = QGroupBox()
        self.set_translatable_text(
            motion_group, "pipeline_management_motion_tracker_section")
        motion_layout = QFormLayout(motion_group)

        self.motion_plugin_enabled = QCheckBox()
        self.set_translatable_text(
            self.motion_plugin_enabled,
            "pipeline_management_enabled_check_1")
        self.motion_plugin_enabled.setChecked(True)
        motion_layout.addRow(
            tr("plugins_status_label"), self.motion_plugin_enabled)

        motion_desc = QLabel()
        self.set_translatable_text(
            motion_desc, "plugins_motion_tracker_desc")
        motion_desc.setStyleSheet("color: #666666; font-size: 8pt;")
        motion_layout.addRow("", motion_desc)
        motion_layout.addRow("", self._create_pipeline_badge(audio_compatible=False))

        self.motion_threshold_spin = CustomDoubleSpinBox()
        self.motion_threshold_spin.setRange(0.01, 0.2)
        self.motion_threshold_spin.setSingleStep(0.01)
        self.motion_threshold_spin.setDecimals(2)
        self.motion_threshold_spin.setValue(0.05)
        motion_layout.addRow(
            tr("plugins_motion_threshold_label"),
            self.motion_threshold_spin)

        self.motion_smoothing_spin = CustomDoubleSpinBox()
        self.motion_smoothing_spin.setRange(0.0, 1.0)
        self.motion_smoothing_spin.setSingleStep(0.1)
        self.motion_smoothing_spin.setValue(0.3)
        motion_layout.addRow(
            tr("plugins_smoothing_factor_label"),
            self.motion_smoothing_spin)

        self.motion_max_distance_spin = CustomSpinBox()
        self.motion_max_distance_spin.setRange(50, 500)
        self.motion_max_distance_spin.setValue(200)
        self.motion_max_distance_spin.setSuffix("px")
        self.set_translatable_text(
            self.motion_max_distance_spin,
            "plugins_motion_max_distance_tooltip", method="setToolTip")
        motion_layout.addRow(
            tr("plugins_motion_max_distance_label"),
            self.motion_max_distance_spin)

        self.motion_skip_ocr_check = QCheckBox()
        self.set_translatable_text(
            self.motion_skip_ocr_check,
            "plugins_motion_skip_ocr_check")
        self.motion_skip_ocr_check.setChecked(True)
        self.set_translatable_text(
            self.motion_skip_ocr_check,
            "plugins_motion_skip_ocr_tooltip", method="setToolTip")
        motion_layout.addRow("", self.motion_skip_ocr_check)

        self.motion_update_overlay_check = QCheckBox()
        self.set_translatable_text(
            self.motion_update_overlay_check,
            "plugins_motion_update_overlay_check")
        self.motion_update_overlay_check.setChecked(True)
        self.set_translatable_text(
            self.motion_update_overlay_check,
            "plugins_motion_update_overlay_tooltip", method="setToolTip")
        motion_layout.addRow("", self.motion_update_overlay_check)

        self.motion_reocr_check = QCheckBox()
        self.set_translatable_text(
            self.motion_reocr_check,
            "plugins_motion_reocr_check")
        self.motion_reocr_check.setChecked(True)
        self.set_translatable_text(
            self.motion_reocr_check,
            "plugins_motion_reocr_tooltip", method="setToolTip")
        motion_layout.addRow("", self.motion_reocr_check)

        self.motion_stop_threshold_spin = CustomDoubleSpinBox()
        self.motion_stop_threshold_spin.setRange(0.1, 2.0)
        self.motion_stop_threshold_spin.setSingleStep(0.1)
        self.motion_stop_threshold_spin.setValue(0.5)
        self.motion_stop_threshold_spin.setSuffix("s")
        self.set_translatable_text(
            self.motion_stop_threshold_spin,
            "plugins_motion_stop_threshold_tooltip", method="setToolTip")
        motion_layout.addRow(
            tr("plugins_motion_stop_threshold_label"),
            self.motion_stop_threshold_spin)

        layout.addWidget(motion_group)

        # Parallel Capture Plugin
        parallel_capture_group = QGroupBox()
        self.set_translatable_text(
            parallel_capture_group,
            "pipeline_management_parallel_capture_section")
        parallel_capture_layout = QFormLayout(parallel_capture_group)

        self.parallel_capture_enabled = QCheckBox()
        self.set_translatable_text(
            self.parallel_capture_enabled,
            "pipeline_management_enabled_check_2")
        self.parallel_capture_enabled.setChecked(False)
        parallel_capture_layout.addRow(
            tr("plugins_status_label"), self.parallel_capture_enabled)

        parallel_capture_desc = QLabel()
        self.set_translatable_text(
            parallel_capture_desc, "plugins_parallel_regions_desc")
        parallel_capture_desc.setStyleSheet("color: #666666; font-size: 8pt;")
        parallel_capture_layout.addRow("", parallel_capture_desc)
        parallel_capture_layout.addRow("", self._create_pipeline_badge(audio_compatible=False))

        self.parallel_capture_workers_spin = CustomSpinBox()
        self.parallel_capture_workers_spin.setRange(2, 8)
        self.parallel_capture_workers_spin.setValue(4)
        parallel_capture_layout.addRow(
            tr("plugins_worker_threads_label"),
            self.parallel_capture_workers_spin)

        layout.addWidget(parallel_capture_group)

        return group

    def _create_ocr_stage_section(self) -> QGroupBox:
        """Create OCR stage plugins section."""
        group = QGroupBox()
        self.set_translatable_text(
            group, "pipeline_management_ocr_stage_section")
        layout = QVBoxLayout(group)

        # Current Engine Display
        engine_display_layout = QHBoxLayout()
        current_engine_lbl = QLabel()
        self.set_translatable_text(
            current_engine_lbl, "plugins_current_engine_label")
        engine_display_layout.addWidget(current_engine_lbl)

        self.current_ocr_engine_label = QLabel()
        self.set_translatable_text(
            self.current_ocr_engine_label, "plugins_loading")
        self.current_ocr_engine_label.setStyleSheet(
            "font-weight: bold; color: #0066CC; font-size: 11pt;")
        engine_display_layout.addWidget(self.current_ocr_engine_label)

        change_engine_btn = QPushButton()
        self.set_translatable_text(
            change_engine_btn,
            "pipeline_management_change_engine_button")
        change_engine_btn.clicked.connect(self._open_ocr_tab)
        engine_display_layout.addWidget(change_engine_btn)

        engine_display_layout.addStretch()
        layout.addLayout(engine_display_layout)

        # OCR Stability Cache threshold
        stability_group = QGroupBox()
        self.set_translatable_text(
            stability_group, "plugins_ocr_stability_cache_section")
        stability_layout = QFormLayout(stability_group)

        stability_desc = QLabel()
        self.set_translatable_text(
            stability_desc, "plugins_ocr_stability_desc")
        stability_desc.setWordWrap(True)
        stability_desc.setStyleSheet("color: #666666; font-size: 8pt;")
        stability_layout.addRow("", stability_desc)

        self.ocr_stability_threshold_spin = CustomDoubleSpinBox()
        self.ocr_stability_threshold_spin.setRange(0.50, 0.99)
        self.ocr_stability_threshold_spin.setSingleStep(0.01)
        self.ocr_stability_threshold_spin.setDecimals(2)
        self.ocr_stability_threshold_spin.setValue(0.80)
        self.set_translatable_text(
            self.ocr_stability_threshold_spin,
            "plugins_ocr_stability_tooltip", method="setToolTip")
        stability_layout.addRow(
            tr("plugins_ocr_stability_threshold_label"),
            self.ocr_stability_threshold_spin)

        layout.addWidget(stability_group)

        # Intelligent Text Processor Plugin (ESSENTIAL)
        intelligent_group = QGroupBox()
        self.set_translatable_text(
            intelligent_group,
            "pipeline_management_intelligent_text_processor_essential_section")
        intelligent_layout = QFormLayout(intelligent_group)

        self.intelligent_plugin_enabled = QCheckBox()
        self.set_translatable_text(
            self.intelligent_plugin_enabled,
            "pipeline_management_enabled_check_3")
        self.intelligent_plugin_enabled.setChecked(True)
        self.set_translatable_text(
            self.intelligent_plugin_enabled,
            "plugins_essential_bypass_tooltip", method="setToolTip")
        intelligent_layout.addRow(
            tr("plugins_status_label"), self.intelligent_plugin_enabled)

        intelligent_desc = QLabel()
        self.set_translatable_text(
            intelligent_desc, "plugins_intelligent_text_desc")
        intelligent_desc.setStyleSheet("color: #666666; font-size: 8pt;")
        intelligent_layout.addRow("", intelligent_desc)
        intelligent_layout.addRow("", self._create_pipeline_badge(audio_compatible=False))

        self.intelligent_corrections_check = QCheckBox()
        self.set_translatable_text(
            self.intelligent_corrections_check,
            "pipeline_management_enable_ocr_corrections_check")
        self.intelligent_corrections_check.setChecked(True)
        self.set_translatable_text(
            self.intelligent_corrections_check,
            "plugins_ocr_corrections_tooltip", method="setToolTip")
        intelligent_layout.addRow(
            tr("plugins_ocr_corrections_label"),
            self.intelligent_corrections_check)

        self.intelligent_context_check = QCheckBox()
        self.set_translatable_text(
            self.intelligent_context_check,
            "pipeline_management_enable_context_aware_check")
        self.intelligent_context_check.setChecked(True)
        self.set_translatable_text(
            self.intelligent_context_check,
            "plugins_context_aware_tooltip", method="setToolTip")
        intelligent_layout.addRow(
            tr("plugins_context_aware_label"),
            self.intelligent_context_check)

        self.intelligent_validation_check = QCheckBox()
        self.set_translatable_text(
            self.intelligent_validation_check,
            "pipeline_management_enable_text_validation_check")
        self.intelligent_validation_check.setChecked(True)
        self.set_translatable_text(
            self.intelligent_validation_check,
            "plugins_filter_tooltip", method="setToolTip")
        intelligent_layout.addRow(
            tr("plugins_text_validation_label"),
            self.intelligent_validation_check)

        self.intelligent_min_confidence_spin = CustomDoubleSpinBox()
        self.intelligent_min_confidence_spin.setRange(0.1, 0.9)
        self.intelligent_min_confidence_spin.setSingleStep(0.1)
        self.intelligent_min_confidence_spin.setValue(0.3)
        self.set_translatable_text(
            self.intelligent_min_confidence_spin,
            "plugins_min_confidence_tooltip", method="setToolTip")
        intelligent_layout.addRow(
            tr("plugins_min_confidence_label"),
            self.intelligent_min_confidence_spin)

        self.intelligent_min_word_length_spin = CustomSpinBox()
        self.intelligent_min_word_length_spin.setRange(1, 10)
        self.intelligent_min_word_length_spin.setSingleStep(1)
        self.intelligent_min_word_length_spin.setValue(2)
        self.set_translatable_text(
            self.intelligent_min_word_length_spin,
            "plugins_min_word_length_tooltip", method="setToolTip")
        intelligent_layout.addRow(
            tr("plugins_min_word_length_label"),
            self.intelligent_min_word_length_spin)

        self.intelligent_auto_learn_check = QCheckBox()
        self.set_translatable_text(
            self.intelligent_auto_learn_check,
            "pipeline_management_auto_learn_check")
        self.intelligent_auto_learn_check.setChecked(True)
        self.set_translatable_text(
            self.intelligent_auto_learn_check,
            "plugins_auto_learn_tooltip", method="setToolTip")
        intelligent_layout.addRow(
            tr("plugins_auto_learn_label"),
            self.intelligent_auto_learn_check)

        correction_hint = QLabel()
        self.set_translatable_text(
            correction_hint, "plugins_correction_hint")
        correction_hint.setStyleSheet(
            "color: #0066CC; font-size: 8pt; font-style: italic;")
        intelligent_layout.addRow("", correction_hint)

        layout.addWidget(intelligent_group)

        # Spell Corrector Plugin
        spell_group = QGroupBox()
        self.set_translatable_text(
            spell_group, "pipeline_management_spell_corrector_section")
        spell_layout = QFormLayout(spell_group)

        self.spell_plugin_enabled = QCheckBox()
        self.set_translatable_text(
            self.spell_plugin_enabled,
            "pipeline_management_enabled_check_4")
        self.spell_plugin_enabled.setChecked(True)
        spell_layout.addRow(
            tr("plugins_status_label"), self.spell_plugin_enabled)

        spell_desc = QLabel()
        self.set_translatable_text(
            spell_desc, "plugins_spell_corrector_desc")
        spell_desc.setStyleSheet("color: #666666; font-size: 8pt;")
        spell_layout.addRow("", spell_desc)
        spell_layout.addRow("", self._create_pipeline_badge(audio_compatible=False))

        self.spell_aggressive_check = QCheckBox()
        self.set_translatable_text(
            self.spell_aggressive_check,
            "pipeline_management_aggressive_mode_check")
        self.spell_aggressive_check.setChecked(False)
        self.set_translatable_text(
            self.spell_aggressive_check,
            "plugins_aggressive_tooltip", method="setToolTip")
        spell_layout.addRow("", self.spell_aggressive_check)

        self.spell_fix_caps_check = QCheckBox()
        self.set_translatable_text(
            self.spell_fix_caps_check,
            "pipeline_management_fix_capitalization_check")
        self.spell_fix_caps_check.setChecked(True)
        self.set_translatable_text(
            self.spell_fix_caps_check,
            "plugins_fix_caps_tooltip", method="setToolTip")
        spell_layout.addRow("", self.spell_fix_caps_check)

        self.spell_confidence_spin = CustomDoubleSpinBox()
        self.spell_confidence_spin.setRange(0.1, 1.0)
        self.spell_confidence_spin.setSingleStep(0.1)
        self.spell_confidence_spin.setValue(0.5)
        spell_layout.addRow(
            tr("plugins_min_confidence_label"), self.spell_confidence_spin)

        self.spell_use_dict_check = QCheckBox()
        self.set_translatable_text(
            self.spell_use_dict_check,
            "plugins_spell_use_dict_check")
        self.spell_use_dict_check.setChecked(True)
        self.set_translatable_text(
            self.spell_use_dict_check,
            "plugins_spell_use_dict_tooltip", method="setToolTip")
        spell_layout.addRow("", self.spell_use_dict_check)

        self.spell_language_combo = QComboBox()
        self.spell_language_combo.addItems(
            ["en", "de", "es", "fr", "it", "pt", "nl", "ru", "ja", "ko",
             "zh"])
        self.set_translatable_text(
            self.spell_language_combo,
            "plugins_spell_language_tooltip", method="setToolTip")
        spell_layout.addRow(
            tr("plugins_spell_language_label"),
            self.spell_language_combo)

        layout.addWidget(spell_group)

        # Text Block Merger Plugin (ESSENTIAL)
        merger_group = QGroupBox()
        self.set_translatable_text(
            merger_group,
            "pipeline_management_text_block_merger_essential_section")
        merger_layout = QFormLayout(merger_group)

        self.merger_plugin_enabled = QCheckBox()
        self.set_translatable_text(
            self.merger_plugin_enabled,
            "pipeline_management_enabled_check")
        self.merger_plugin_enabled.setChecked(True)
        self.set_translatable_text(
            self.merger_plugin_enabled,
            "plugins_essential_bypass_tooltip", method="setToolTip")
        merger_layout.addRow(
            tr("plugins_status_label"), self.merger_plugin_enabled)

        merger_desc = QLabel()
        self.set_translatable_text(
            merger_desc, "plugins_text_block_merger_desc")
        merger_desc.setWordWrap(True)
        merger_desc.setStyleSheet("color: #666666; font-size: 8pt;")
        merger_layout.addRow("", merger_desc)
        merger_layout.addRow("", self._create_pipeline_badge(audio_compatible=False))

        self.merger_h_threshold_spin = CustomSpinBox()
        self.merger_h_threshold_spin.setRange(5, 200)
        self.merger_h_threshold_spin.setValue(50)
        self.merger_h_threshold_spin.setSuffix("px")
        self.set_translatable_text(
            self.merger_h_threshold_spin,
            "plugins_merger_h_threshold_tooltip", method="setToolTip")
        merger_layout.addRow(
            tr("plugins_merger_h_threshold_label"),
            self.merger_h_threshold_spin)

        self.merger_v_threshold_spin = CustomSpinBox()
        self.merger_v_threshold_spin.setRange(3, 100)
        self.merger_v_threshold_spin.setValue(30)
        self.merger_v_threshold_spin.setSuffix("px")
        self.set_translatable_text(
            self.merger_v_threshold_spin,
            "plugins_merger_v_threshold_tooltip", method="setToolTip")
        merger_layout.addRow(
            tr("plugins_merger_v_threshold_label"),
            self.merger_v_threshold_spin)

        self.merger_line_height_spin = CustomDoubleSpinBox()
        self.merger_line_height_spin.setRange(1.0, 3.0)
        self.merger_line_height_spin.setSingleStep(0.1)
        self.merger_line_height_spin.setValue(1.5)
        self.merger_line_height_spin.setSuffix("×")
        merger_layout.addRow(
            tr("plugins_merger_line_height_label"),
            self.merger_line_height_spin)

        self.merger_strategy_combo = QComboBox()
        self.merger_strategy_combo.addItems(
            ["smart", "horizontal", "vertical", "aggressive"])
        self.set_translatable_text(
            self.merger_strategy_combo,
            "plugins_merger_strategy_tooltip", method="setToolTip")
        merger_layout.addRow(
            tr("plugins_merger_strategy_label"),
            self.merger_strategy_combo)

        self.merger_respect_punct_check = QCheckBox()
        self.set_translatable_text(
            self.merger_respect_punct_check,
            "plugins_merger_respect_punctuation_check")
        self.merger_respect_punct_check.setChecked(True)
        merger_layout.addRow("", self.merger_respect_punct_check)

        self.merger_min_confidence_spin = CustomDoubleSpinBox()
        self.merger_min_confidence_spin.setRange(0.0, 1.0)
        self.merger_min_confidence_spin.setSingleStep(0.1)
        self.merger_min_confidence_spin.setValue(0.3)
        merger_layout.addRow(
            tr("plugins_min_confidence_label"),
            self.merger_min_confidence_spin)

        layout.addWidget(merger_group)

        # OCR per Region Plugin
        ocr_region_group = QGroupBox()
        self.set_translatable_text(
            ocr_region_group,
            "pipeline_management_ocr_per_region_section")
        ocr_region_layout = QFormLayout(ocr_region_group)

        self.ocr_per_region_enabled = QCheckBox()
        self.set_translatable_text(
            self.ocr_per_region_enabled,
            "pipeline_management_enabled_check")
        self.ocr_per_region_enabled.setChecked(False)
        ocr_region_layout.addRow(
            tr("plugins_status_label"), self.ocr_per_region_enabled)

        ocr_region_desc = QLabel()
        self.set_translatable_text(
            ocr_region_desc, "plugins_ocr_per_region_desc")
        ocr_region_desc.setWordWrap(True)
        ocr_region_desc.setStyleSheet("color: #666666; font-size: 8pt;")
        ocr_region_layout.addRow("", ocr_region_desc)
        ocr_region_layout.addRow("", self._create_pipeline_badge(audio_compatible=False))

        self.ocr_per_region_default_combo = QComboBox()
        self.ocr_per_region_default_combo.addItems(
            ["easyocr", "mokuro", "paddleocr", "tesseract", "windows_ocr"])
        ocr_region_layout.addRow(
            tr("plugins_ocr_per_region_default_label"),
            self.ocr_per_region_default_combo)

        self.ocr_per_region_parallel_check = QCheckBox()
        self.set_translatable_text(
            self.ocr_per_region_parallel_check,
            "plugins_ocr_per_region_parallel_check")
        self.ocr_per_region_parallel_check.setChecked(True)
        self.set_translatable_text(
            self.ocr_per_region_parallel_check,
            "plugins_ocr_per_region_parallel_tooltip", method="setToolTip")
        ocr_region_layout.addRow("", self.ocr_per_region_parallel_check)

        self.ocr_per_region_cache_check = QCheckBox()
        self.set_translatable_text(
            self.ocr_per_region_cache_check,
            "plugins_ocr_per_region_cache_check")
        self.ocr_per_region_cache_check.setChecked(True)
        self.set_translatable_text(
            self.ocr_per_region_cache_check,
            "plugins_ocr_per_region_cache_tooltip", method="setToolTip")
        ocr_region_layout.addRow("", self.ocr_per_region_cache_check)

        layout.addWidget(ocr_region_group)

        # Regex Text Processor Plugin
        regex_group = QGroupBox()
        self.set_translatable_text(
            regex_group,
            "pipeline_management_regex_text_processor_section")
        regex_layout = QFormLayout(regex_group)

        self.regex_plugin_enabled = QCheckBox()
        self.set_translatable_text(
            self.regex_plugin_enabled,
            "pipeline_management_enabled_check")
        self.regex_plugin_enabled.setChecked(False)
        regex_layout.addRow(
            tr("plugins_status_label"), self.regex_plugin_enabled)

        regex_desc = QLabel()
        self.set_translatable_text(
            regex_desc, "plugins_regex_desc")
        regex_desc.setWordWrap(True)
        regex_desc.setStyleSheet("color: #666666; font-size: 8pt;")
        regex_layout.addRow("", regex_desc)
        regex_layout.addRow("", self._create_pipeline_badge(audio_compatible=False))

        self.regex_filter_mode_combo = QComboBox()
        self.regex_filter_mode_combo.addItems(
            ["basic", "aggressive", "normalize",
             "ocr_cleanup", "japanese", "url_email"])
        self.set_translatable_text(
            self.regex_filter_mode_combo,
            "plugins_regex_filter_mode_tooltip", method="setToolTip")
        regex_layout.addRow(
            tr("plugins_regex_filter_mode_label"),
            self.regex_filter_mode_combo)

        self.regex_min_length_spin = CustomSpinBox()
        self.regex_min_length_spin.setRange(0, 100)
        self.regex_min_length_spin.setValue(1)
        regex_layout.addRow(
            tr("plugins_regex_min_length_label"),
            self.regex_min_length_spin)

        self.regex_max_length_spin = CustomSpinBox()
        self.regex_max_length_spin.setRange(100, 100000)
        self.regex_max_length_spin.setValue(10000)
        regex_layout.addRow(
            tr("plugins_regex_max_length_label"),
            self.regex_max_length_spin)

        layout.addWidget(regex_group)

        # Parallel OCR Plugin
        parallel_group = QGroupBox()
        self.set_translatable_text(
            parallel_group, "pipeline_management_parallel_ocr_section")
        parallel_layout = QFormLayout(parallel_group)

        self.parallel_plugin_enabled = QCheckBox()
        self.set_translatable_text(
            self.parallel_plugin_enabled,
            "pipeline_management_enabled_check_5")
        self.parallel_plugin_enabled.setChecked(False)
        parallel_layout.addRow(
            tr("plugins_status_label"), self.parallel_plugin_enabled)

        parallel_desc = QLabel()
        self.set_translatable_text(
            parallel_desc, "plugins_parallel_regions_desc")
        parallel_desc.setStyleSheet("color: #666666; font-size: 8pt;")
        parallel_layout.addRow("", parallel_desc)
        parallel_layout.addRow("", self._create_pipeline_badge(audio_compatible=False))

        self.parallel_workers_spin = CustomSpinBox()
        self.parallel_workers_spin.setRange(2, 8)
        self.parallel_workers_spin.setValue(4)
        parallel_layout.addRow(
            tr("plugins_worker_threads_label"), self.parallel_workers_spin)

        layout.addWidget(parallel_group)

        return group

    def _create_translation_stage_section(self) -> QGroupBox:
        """Create translation stage plugins section."""
        group = QGroupBox()
        self.set_translatable_text(
            group, "pipeline_management_translation_stage_section")
        layout = QVBoxLayout(group)

        # Translation Cache (ESSENTIAL)
        cache_group = QGroupBox()
        self.set_translatable_text(
            cache_group,
            "pipeline_management_translation_cache_essential_section")
        cache_layout = QFormLayout(cache_group)

        self.cache_plugin_enabled = QCheckBox()
        self.set_translatable_text(
            self.cache_plugin_enabled,
            "pipeline_management_enabled_check_6")
        self.cache_plugin_enabled.setChecked(True)
        self.set_translatable_text(
            self.cache_plugin_enabled,
            "plugins_essential_bypass_tooltip", method="setToolTip")
        cache_layout.addRow(
            tr("plugins_status_label"), self.cache_plugin_enabled)

        cache_desc = QLabel()
        self.set_translatable_text(cache_desc, "plugins_cache_desc")
        cache_desc.setStyleSheet("color: #666666; font-size: 8pt;")
        cache_layout.addRow("", cache_desc)
        cache_layout.addRow("", self._create_pipeline_badge(audio_compatible=True))

        self.cache_size_spin = CustomSpinBox()
        self.cache_size_spin.setRange(100, 100000)
        self.cache_size_spin.setValue(10000)
        self.set_translatable_text(
            self.cache_size_spin, "plugins_suffix_entries",
            method="setSuffix")
        cache_layout.addRow(
            tr("plugins_cache_size_label"), self.cache_size_spin)

        self.cache_ttl_spin = CustomSpinBox()
        self.cache_ttl_spin.setRange(60, 86400)
        self.cache_ttl_spin.setValue(3600)
        self.set_translatable_text(
            self.cache_ttl_spin, "plugins_suffix_seconds",
            method="setSuffix")
        cache_layout.addRow(tr("plugins_ttl_label"), self.cache_ttl_spin)

        self.cache_fuzzy_check = QCheckBox()
        self.set_translatable_text(
            self.cache_fuzzy_check,
            "plugins_cache_fuzzy_check")
        self.cache_fuzzy_check.setChecked(False)
        self.set_translatable_text(
            self.cache_fuzzy_check,
            "plugins_cache_fuzzy_tooltip", method="setToolTip")
        cache_layout.addRow("", self.cache_fuzzy_check)

        layout.addWidget(cache_group)

        # Learning Dictionary (ESSENTIAL)
        dict_group = QGroupBox()
        self.set_translatable_text(
            dict_group,
            "pipeline_management_learning_dictionary_essential_section")
        dict_layout = QFormLayout(dict_group)

        self.dict_plugin_enabled = QCheckBox()
        self.set_translatable_text(
            self.dict_plugin_enabled,
            "pipeline_management_enabled_check_7")
        self.dict_plugin_enabled.setChecked(True)
        self.set_translatable_text(
            self.dict_plugin_enabled,
            "plugins_essential_bypass_tooltip", method="setToolTip")
        dict_layout.addRow(
            tr("plugins_status_label"), self.dict_plugin_enabled)

        dict_desc = QLabel()
        self.set_translatable_text(dict_desc, "plugins_dict_desc")
        dict_desc.setStyleSheet("color: #666666; font-size: 8pt;")
        dict_layout.addRow("", dict_desc)
        dict_layout.addRow("", self._create_pipeline_badge(audio_compatible=True))

        self.dict_auto_save_check = QCheckBox()
        self.set_translatable_text(
            self.dict_auto_save_check,
            "plugins_dict_auto_save_check")
        self.dict_auto_save_check.setChecked(True)
        self.set_translatable_text(
            self.dict_auto_save_check,
            "plugins_dict_auto_save_tooltip", method="setToolTip")
        dict_layout.addRow("", self.dict_auto_save_check)

        self.dict_min_confidence_spin = CustomDoubleSpinBox()
        self.dict_min_confidence_spin.setRange(0.5, 1.0)
        self.dict_min_confidence_spin.setSingleStep(0.05)
        self.dict_min_confidence_spin.setValue(0.8)
        self.set_translatable_text(
            self.dict_min_confidence_spin,
            "plugins_dict_min_confidence_tooltip", method="setToolTip")
        dict_layout.addRow(
            tr("plugins_dict_min_confidence_label"),
            self.dict_min_confidence_spin)

        self.dict_validate_check = QCheckBox()
        self.set_translatable_text(
            self.dict_validate_check,
            "plugins_dict_validate_check")
        self.dict_validate_check.setChecked(True)
        self.set_translatable_text(
            self.dict_validate_check,
            "plugins_dict_validate_tooltip", method="setToolTip")
        dict_layout.addRow("", self.dict_validate_check)

        layout.addWidget(dict_group)

        # Batch Processing
        batch_group = QGroupBox()
        self.set_translatable_text(
            batch_group, "pipeline_management_batch_processing_section")
        batch_layout = QFormLayout(batch_group)

        self.batch_plugin_enabled = QCheckBox()
        self.set_translatable_text(
            self.batch_plugin_enabled,
            "pipeline_management_enabled_check_8")
        self.batch_plugin_enabled.setChecked(False)
        batch_layout.addRow(
            tr("plugins_status_label"), self.batch_plugin_enabled)

        batch_desc = QLabel()
        self.set_translatable_text(batch_desc, "plugins_batch_desc")
        batch_desc.setStyleSheet("color: #666666; font-size: 8pt;")
        batch_layout.addRow("", batch_desc)
        batch_layout.addRow("", self._create_pipeline_badge(audio_compatible=True))

        self.batch_size_spin = CustomSpinBox()
        self.batch_size_spin.setRange(2, 32)
        self.batch_size_spin.setValue(8)
        self.set_translatable_text(
            self.batch_size_spin, "plugins_suffix_frames",
            method="setSuffix")
        batch_layout.addRow(
            tr("plugins_max_batch_size_label"), self.batch_size_spin)

        self.batch_wait_spin = CustomDoubleSpinBox()
        self.batch_wait_spin.setRange(1.0, 100.0)
        self.batch_wait_spin.setSingleStep(1.0)
        self.batch_wait_spin.setValue(10.0)
        self.batch_wait_spin.setSuffix("ms")
        batch_layout.addRow(
            tr("plugins_max_wait_time_label"), self.batch_wait_spin)

        self.batch_min_size_spin = CustomSpinBox()
        self.batch_min_size_spin.setRange(1, 16)
        self.batch_min_size_spin.setValue(2)
        self.set_translatable_text(
            self.batch_min_size_spin, "plugins_suffix_frames",
            method="setSuffix")
        self.set_translatable_text(
            self.batch_min_size_spin,
            "plugins_batch_min_size_tooltip", method="setToolTip")
        batch_layout.addRow(
            tr("plugins_batch_min_size_label"),
            self.batch_min_size_spin)

        self.batch_adaptive_check = QCheckBox()
        self.set_translatable_text(
            self.batch_adaptive_check,
            "plugins_batch_adaptive_check")
        self.batch_adaptive_check.setChecked(True)
        self.set_translatable_text(
            self.batch_adaptive_check,
            "plugins_batch_adaptive_tooltip", method="setToolTip")
        batch_layout.addRow("", self.batch_adaptive_check)

        layout.addWidget(batch_group)

        # Parallel Translation Plugin
        parallel_trans_group = QGroupBox()
        self.set_translatable_text(
            parallel_trans_group,
            "pipeline_management_parallel_translation_section")
        parallel_trans_layout = QFormLayout(parallel_trans_group)

        self.parallel_trans_enabled = QCheckBox()
        self.set_translatable_text(
            self.parallel_trans_enabled,
            "pipeline_management_enabled_check")
        self.parallel_trans_enabled.setChecked(False)
        parallel_trans_layout.addRow(
            tr("plugins_status_label"), self.parallel_trans_enabled)

        parallel_trans_desc = QLabel()
        self.set_translatable_text(
            parallel_trans_desc, "plugins_parallel_translation_desc")
        parallel_trans_desc.setWordWrap(True)
        parallel_trans_desc.setStyleSheet("color: #666666; font-size: 8pt;")
        parallel_trans_layout.addRow("", parallel_trans_desc)
        parallel_trans_layout.addRow("", self._create_pipeline_badge(audio_compatible=True))

        self.parallel_trans_workers_spin = CustomSpinBox()
        self.parallel_trans_workers_spin.setRange(1, 8)
        self.parallel_trans_workers_spin.setValue(2)
        parallel_trans_layout.addRow(
            tr("plugins_worker_threads_label"),
            self.parallel_trans_workers_spin)

        self.parallel_trans_batch_spin = CustomSpinBox()
        self.parallel_trans_batch_spin.setRange(2, 64)
        self.parallel_trans_batch_spin.setValue(8)
        parallel_trans_layout.addRow(
            tr("plugins_parallel_trans_batch_label"),
            self.parallel_trans_batch_spin)

        self.parallel_trans_timeout_spin = CustomDoubleSpinBox()
        self.parallel_trans_timeout_spin.setRange(5.0, 120.0)
        self.parallel_trans_timeout_spin.setSingleStep(5.0)
        self.parallel_trans_timeout_spin.setValue(30.0)
        self.set_translatable_text(
            self.parallel_trans_timeout_spin,
            "plugins_suffix_seconds", method="setSuffix")
        parallel_trans_layout.addRow(
            tr("plugins_parallel_trans_timeout_label"),
            self.parallel_trans_timeout_spin)

        self.parallel_trans_gpu_check = QCheckBox()
        self.set_translatable_text(
            self.parallel_trans_gpu_check,
            "plugins_parallel_trans_gpu_check")
        self.parallel_trans_gpu_check.setChecked(True)
        parallel_trans_layout.addRow("", self.parallel_trans_gpu_check)

        self.parallel_trans_warm_start_check = QCheckBox()
        self.set_translatable_text(
            self.parallel_trans_warm_start_check,
            "plugins_parallel_trans_warm_start_check")
        self.parallel_trans_warm_start_check.setChecked(True)
        self.set_translatable_text(
            self.parallel_trans_warm_start_check,
            "plugins_parallel_trans_warm_start_tooltip", method="setToolTip")
        parallel_trans_layout.addRow("", self.parallel_trans_warm_start_check)

        self.parallel_trans_fallback_check = QCheckBox()
        self.set_translatable_text(
            self.parallel_trans_fallback_check,
            "plugins_parallel_trans_fallback_check")
        self.parallel_trans_fallback_check.setChecked(True)
        parallel_trans_layout.addRow("", self.parallel_trans_fallback_check)

        parallel_trans_perf = QLabel()
        self.set_translatable_text(
            parallel_trans_perf, "plugins_parallel_trans_perf")
        parallel_trans_perf.setStyleSheet(
            "color: #66bb6a; font-size: 8pt; font-style: italic;")
        parallel_trans_layout.addRow("", parallel_trans_perf)

        layout.addWidget(parallel_trans_group)

        # Translation Chain Plugin
        chain_group = QGroupBox()
        self.set_translatable_text(
            chain_group,
            "pipeline_management_translation_chain_best_for_rare_language_section")
        chain_layout = QFormLayout(chain_group)

        self.chain_plugin_enabled = QCheckBox()
        self.set_translatable_text(
            self.chain_plugin_enabled,
            "pipeline_management_enabled_check_9")
        self.chain_plugin_enabled.setChecked(False)
        self.chain_plugin_enabled.stateChanged.connect(
            self.settingChanged.emit)
        chain_layout.addRow(
            tr("plugins_status_label"), self.chain_plugin_enabled)

        chain_desc = QLabel()
        self.set_translatable_text(chain_desc, "plugins_chain_desc")
        chain_desc.setWordWrap(True)
        chain_desc.setStyleSheet("color: #666666; font-size: 8pt;")
        chain_layout.addRow("", chain_desc)
        chain_layout.addRow("", self._create_pipeline_badge(audio_compatible=True))

        self.chain_enable_chaining_check = QCheckBox()
        self.set_translatable_text(
            self.chain_enable_chaining_check,
            "plugins_chain_enable_chaining_check")
        self.chain_enable_chaining_check.setChecked(False)
        self.set_translatable_text(
            self.chain_enable_chaining_check,
            "plugins_chain_enable_chaining_tooltip", method="setToolTip")
        chain_layout.addRow("", self.chain_enable_chaining_check)

        self.chain_intermediate_lang_combo = QComboBox()
        self.chain_intermediate_lang_combo.addItems(
            ["en", "zh", "es", "fr", "de"])
        self.chain_intermediate_lang_combo.setCurrentText("en")
        self.chain_intermediate_lang_combo.currentTextChanged.connect(
            self.settingChanged.emit)
        chain_layout.addRow(
            tr("plugins_intermediate_language_label"),
            self.chain_intermediate_lang_combo)

        self.chain_quality_threshold_spin = CustomDoubleSpinBox()
        self.chain_quality_threshold_spin.setRange(0.0, 1.0)
        self.chain_quality_threshold_spin.setSingleStep(0.1)
        self.chain_quality_threshold_spin.setValue(0.7)
        self.chain_quality_threshold_spin.valueChanged.connect(
            self.settingChanged.emit)
        chain_layout.addRow(
            tr("plugins_quality_threshold_label"),
            self.chain_quality_threshold_spin)

        self.chain_save_all_check = QCheckBox()
        self.set_translatable_text(
            self.chain_save_all_check,
            "pipeline_management_save_all_intermediate_translations_to_di_check")
        self.chain_save_all_check.setChecked(True)
        self.chain_save_all_check.stateChanged.connect(
            self.settingChanged.emit)
        chain_layout.addRow("", self.chain_save_all_check)

        self.chain_cache_intermediate_check = QCheckBox()
        self.set_translatable_text(
            self.chain_cache_intermediate_check,
            "plugins_chain_cache_intermediate_check")
        self.chain_cache_intermediate_check.setChecked(True)
        self.set_translatable_text(
            self.chain_cache_intermediate_check,
            "plugins_chain_cache_intermediate_tooltip", method="setToolTip")
        self.chain_cache_intermediate_check.stateChanged.connect(
            self.settingChanged.emit)
        chain_layout.addRow("", self.chain_cache_intermediate_check)

        chain_note = QLabel()
        self.set_translatable_text(chain_note, "plugins_chain_note")
        chain_note.setStyleSheet(
            "color: #2196F3; font-size: 8pt; font-style: italic;")
        chain_layout.addRow("", chain_note)

        chain_performance = QLabel()
        self.set_translatable_text(
            chain_performance, "plugins_chain_performance")
        chain_performance.setStyleSheet(
            "color: #FF9800; font-size: 8pt; font-style: italic;")
        chain_layout.addRow("", chain_performance)

        layout.addWidget(chain_group)

        return group

    def _create_overlay_stage_section(self) -> QGroupBox:
        """Create overlay stage plugins section."""
        group = QGroupBox()
        self.set_translatable_text(group, "plugins_overlay_stage")
        layout = QVBoxLayout(group)

        # Color Contrast Plugin
        cc_group = QGroupBox()
        self.set_translatable_text(
            cc_group, "plugins_color_contrast_optimizer")
        cc_layout = QFormLayout(cc_group)

        self.color_contrast_enabled = QCheckBox()
        self.set_translatable_text(
            self.color_contrast_enabled, "plugins_enabled")
        self.color_contrast_enabled.setChecked(False)
        cc_layout.addRow(
            tr("plugins_status_label"), self.color_contrast_enabled)

        cc_desc = QLabel()
        self.set_translatable_text(
            cc_desc, "plugins_color_contrast_desc")
        cc_desc.setWordWrap(True)
        cc_desc.setStyleSheet("color: #666666; font-size: 8pt;")
        cc_layout.addRow("", cc_desc)
        cc_layout.addRow("", self._create_pipeline_badge(audio_compatible=False))

        self.color_contrast_mode_combo = QComboBox()
        self.color_contrast_mode_combo.addItems(
            ["auto_contrast", "seamless"])
        self.set_translatable_text(
            self.color_contrast_mode_combo,
            "plugins_cc_mode_tooltip", method="setToolTip")
        cc_layout.addRow(
            tr("plugins_mode_label"), self.color_contrast_mode_combo)

        self.color_contrast_ratio_spin = CustomDoubleSpinBox()
        self.color_contrast_ratio_spin.setRange(3.0, 7.0)
        self.color_contrast_ratio_spin.setSingleStep(0.5)
        self.color_contrast_ratio_spin.setValue(4.5)
        self.set_translatable_text(
            self.color_contrast_ratio_spin,
            "plugins_cc_ratio_tooltip", method="setToolTip")
        cc_layout.addRow(
            tr("plugins_min_contrast_ratio_label"),
            self.color_contrast_ratio_spin)

        self.color_contrast_sample_spin = CustomSpinBox()
        self.color_contrast_sample_spin.setRange(5, 50)
        self.color_contrast_sample_spin.setValue(20)
        self.color_contrast_sample_spin.setSuffix("px")
        cc_layout.addRow(
            tr("plugins_sample_size_label"),
            self.color_contrast_sample_spin)

        self.cc_fallback_light_edit = QLineEdit("#ffffff")
        self.cc_fallback_light_edit.setMaxLength(7)
        self.cc_fallback_light_edit.setFixedWidth(90)
        self.set_translatable_text(
            self.cc_fallback_light_edit,
            "plugins_cc_fallback_light_tooltip", method="setToolTip")
        cc_layout.addRow(
            tr("plugins_cc_fallback_light_label"),
            self.cc_fallback_light_edit)

        self.cc_fallback_dark_edit = QLineEdit("#000000")
        self.cc_fallback_dark_edit.setMaxLength(7)
        self.cc_fallback_dark_edit.setFixedWidth(90)
        self.set_translatable_text(
            self.cc_fallback_dark_edit,
            "plugins_cc_fallback_dark_tooltip", method="setToolTip")
        cc_layout.addRow(
            tr("plugins_cc_fallback_dark_label"),
            self.cc_fallback_dark_edit)

        cc_perf = QLabel()
        self.set_translatable_text(cc_perf, "plugins_cc_perf")
        cc_perf.setStyleSheet(
            "color: #66bb6a; font-size: 8pt; font-style: italic;")
        cc_layout.addRow("", cc_perf)

        layout.addWidget(cc_group)
        return group

    def _create_global_stage_section(self) -> QGroupBox:
        """Create global plugins section."""
        group = QGroupBox()
        self.set_translatable_text(
            group, "pipeline_management_global_pipeline-level_section")
        layout = QVBoxLayout(group)

        # Pipeline Mode
        mode_group = QGroupBox()
        self.set_translatable_text(
            mode_group, "plugins_pipeline_execution_mode")
        mode_layout = QFormLayout(mode_group)

        self.detailed_pipeline_mode_combo = QComboBox()
        self.detailed_pipeline_mode_combo.addItems(
            [tr("plugins_sequential"), tr("plugins_parallel_async"),
             tr("plugins_custom_per_stage"), "Subprocess (Isolated)"])
        self.set_translatable_text(
            self.detailed_pipeline_mode_combo,
            "plugins_pipeline_mode_tooltip", method="setToolTip")
        mode_layout.addRow(
            tr("plugins_mode_label"),
            self.detailed_pipeline_mode_combo)

        mode_desc = QLabel()
        self.set_translatable_text(mode_desc, "plugins_mode_desc")
        mode_desc.setWordWrap(True)
        mode_desc.setStyleSheet("color: #666666; font-size: 8pt;")
        mode_layout.addRow("", mode_desc)

        # Hidden state holder for backward compatibility
        self.async_plugin_enabled = QCheckBox()
        self.async_plugin_enabled.setChecked(False)
        self.async_plugin_enabled.setVisible(False)
        mode_layout.addRow(self.async_plugin_enabled)

        self.async_stages_spin = CustomSpinBox()
        self.async_stages_spin.setRange(2, 8)
        self.async_stages_spin.setValue(4)
        mode_layout.addRow(
            tr("plugins_max_concurrent_stages_label"),
            self.async_stages_spin)

        # Per-stage mode selectors (visible only in Custom mode)
        self._custom_mode_widget = QWidget()
        custom_layout = QFormLayout(self._custom_mode_widget)
        custom_layout.setContentsMargins(0, 4, 0, 0)

        custom_hint = QLabel()
        self.set_translatable_text(
            custom_hint, "plugins_custom_mode_hint")
        custom_hint.setWordWrap(True)
        custom_hint.setStyleSheet(
            "color: #0066CC; font-size: 8pt; font-style: italic;")
        custom_layout.addRow("", custom_hint)

        stage_options = [tr("plugins_sequential"), tr("plugins_parallel_async")]

        self.custom_capture_combo = QComboBox()
        self.custom_capture_combo.addItems(stage_options)
        custom_layout.addRow(
            tr("plugins_custom_capture_label"), self.custom_capture_combo)

        self.custom_ocr_combo = QComboBox()
        self.custom_ocr_combo.addItems(stage_options)
        custom_layout.addRow(
            tr("plugins_custom_ocr_label"), self.custom_ocr_combo)

        self.custom_translation_combo = QComboBox()
        self.custom_translation_combo.addItems(stage_options)
        custom_layout.addRow(
            tr("plugins_custom_translation_label"),
            self.custom_translation_combo)

        self.custom_overlay_combo = QComboBox()
        self.custom_overlay_combo.addItems(stage_options)
        custom_layout.addRow(
            tr("plugins_custom_overlay_label"), self.custom_overlay_combo)

        self._custom_mode_widget.setVisible(False)
        mode_layout.addRow(self._custom_mode_widget)

        def _on_mode_changed(idx):
            self.async_plugin_enabled.setChecked(idx == 1)
            self._custom_mode_widget.setVisible(idx == 2)

        self.detailed_pipeline_mode_combo.currentIndexChanged.connect(
            _on_mode_changed
        )

        layout.addWidget(mode_group)

        # Priority Queue
        priority_group = QGroupBox()
        self.set_translatable_text(
            priority_group,
            "pipeline_management_priority_queue_section")
        priority_layout = QFormLayout(priority_group)

        self.priority_plugin_enabled = QCheckBox()
        self.set_translatable_text(
            self.priority_plugin_enabled,
            "pipeline_management_enabled_check_11")
        self.priority_plugin_enabled.setChecked(False)
        priority_layout.addRow(
            tr("plugins_status_label"), self.priority_plugin_enabled)

        priority_desc = QLabel()
        self.set_translatable_text(
            priority_desc, "plugins_priority_desc")
        priority_desc.setStyleSheet("color: #666666; font-size: 8pt;")
        priority_layout.addRow("", priority_desc)
        priority_layout.addRow("", self._create_pipeline_badge(audio_compatible=True))

        self.priority_max_queue_spin = CustomSpinBox()
        self.priority_max_queue_spin.setRange(10, 1000)
        self.priority_max_queue_spin.setValue(100)
        self.set_translatable_text(
            self.priority_max_queue_spin,
            "plugins_priority_max_queue_tooltip", method="setToolTip")
        priority_layout.addRow(
            tr("plugins_priority_max_queue_label"),
            self.priority_max_queue_spin)

        self.priority_starvation_check = QCheckBox()
        self.set_translatable_text(
            self.priority_starvation_check,
            "plugins_priority_starvation_check")
        self.priority_starvation_check.setChecked(True)
        self.set_translatable_text(
            self.priority_starvation_check,
            "plugins_priority_starvation_tooltip", method="setToolTip")
        priority_layout.addRow("", self.priority_starvation_check)

        layout.addWidget(priority_group)

        # Work-Stealing Pool
        work_group = QGroupBox()
        self.set_translatable_text(
            work_group,
            "pipeline_management_work-stealing_pool_section")
        work_layout = QFormLayout(work_group)

        self.work_plugin_enabled = QCheckBox()
        self.set_translatable_text(
            self.work_plugin_enabled,
            "pipeline_management_enabled_check_12")
        self.work_plugin_enabled.setChecked(False)
        work_layout.addRow(
            tr("plugins_status_label"), self.work_plugin_enabled)

        work_desc = QLabel()
        self.set_translatable_text(
            work_desc, "plugins_work_stealing_desc")
        work_desc.setStyleSheet("color: #666666; font-size: 8pt;")
        work_layout.addRow("", work_desc)
        work_layout.addRow("", self._create_pipeline_badge(audio_compatible=True))

        self.work_workers_spin = CustomSpinBox()
        self.work_workers_spin.setRange(2, 16)
        self.work_workers_spin.setValue(4)
        work_layout.addRow(
            tr("plugins_number_of_workers_label"),
            self.work_workers_spin)

        self.work_steal_threshold_spin = CustomSpinBox()
        self.work_steal_threshold_spin.setRange(1, 10)
        self.work_steal_threshold_spin.setValue(2)
        self.set_translatable_text(
            self.work_steal_threshold_spin,
            "plugins_work_steal_threshold_tooltip", method="setToolTip")
        work_layout.addRow(
            tr("plugins_work_steal_threshold_label"),
            self.work_steal_threshold_spin)

        self.work_affinity_check = QCheckBox()
        self.set_translatable_text(
            self.work_affinity_check,
            "plugins_work_affinity_check")
        self.work_affinity_check.setChecked(False)
        self.set_translatable_text(
            self.work_affinity_check,
            "plugins_work_affinity_tooltip", method="setToolTip")
        work_layout.addRow("", self.work_affinity_check)

        layout.addWidget(work_group)

        return group

    def _open_ocr_tab(self):
        """Open the OCR settings tab."""
        parent = self.parent()
        while parent and not hasattr(parent, 'tab_widget'):
            parent = parent.parent()

        if parent and hasattr(parent, 'tab_widget'):
            for i in range(parent.tab_widget.count()):
                if "OCR" in parent.tab_widget.tabText(i):
                    parent.tab_widget.setCurrentIndex(i)
                    break
