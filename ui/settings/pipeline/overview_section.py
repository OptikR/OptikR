"""
Pipeline Overview Section

Compact overview with plugin toggles, pipeline status, and active components.
"""

import logging

from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QGroupBox, QLabel, QPushButton,
    QCheckBox, QFormLayout, QComboBox
)

logger = logging.getLogger(__name__)


class OverviewSection(QWidget):
    """Compact overview tab with plugin toggles and live status."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self._init_ui()

    def _init_ui(self):
        layout = QVBoxLayout(self)
        layout.setSpacing(8)

        # Pipeline Status - Compact
        status_group = QGroupBox("Pipeline Status")
        status_layout = QFormLayout(status_group)
        status_layout.setSpacing(2)
        status_layout.setContentsMargins(10, 8, 10, 8)

        self.new_status_label = QLabel("Idle (Ready to Start)")
        self.new_status_label.setStyleSheet("font-weight: bold; color: #4a9eff;")
        status_layout.addRow("Status:", self.new_status_label)

        self.new_uptime_label = QLabel("--")
        status_layout.addRow("Uptime:", self.new_uptime_label)

        btn_layout = QHBoxLayout()
        btn_layout.setSpacing(4)
        self.new_start_btn = QPushButton("▶ Start")
        self.new_pause_btn = QPushButton("⏸ Pause")
        self.new_stop_btn = QPushButton("⏹ Stop")
        self.new_pause_btn.setEnabled(False)
        self.new_stop_btn.setEnabled(False)
        btn_layout.addWidget(self.new_start_btn)
        btn_layout.addWidget(self.new_pause_btn)
        btn_layout.addWidget(self.new_stop_btn)
        status_layout.addRow("", btn_layout)

        layout.addWidget(status_group)

        # Quick Statistics - Compact
        stats_group = QGroupBox("Quick Statistics")
        stats_layout = QFormLayout(stats_group)
        stats_layout.setSpacing(2)
        stats_layout.setContentsMargins(10, 8, 10, 8)

        self.new_fps_label = QLabel("0.0 FPS")
        stats_layout.addRow("FPS:", self.new_fps_label)

        self.new_latency_label = QLabel("0 ms")
        stats_layout.addRow("Latency:", self.new_latency_label)

        self.new_frames_label = QLabel("0")
        stats_layout.addRow("Frames:", self.new_frames_label)

        self.new_translations_label = QLabel("0")
        stats_layout.addRow("Translations:", self.new_translations_label)

        self.new_cache_label = QLabel("0 (0%)")
        stats_layout.addRow("Cache Hits:", self.new_cache_label)

        layout.addWidget(stats_group)

        # Active Plugins
        plugins_group = QGroupBox("Active Plugins")
        plugins_layout = QVBoxLayout(plugins_group)
        plugins_layout.setSpacing(4)
        plugins_layout.setContentsMargins(10, 8, 10, 8)

        # Master switch
        self.new_master_check = QCheckBox("Enable Optional Optimizer Plugins")
        self.new_master_check.setChecked(True)
        self.new_master_check.setStyleSheet(
            "QCheckBox { margin: 0px; padding: 2px 0px; font-weight: bold; }")
        plugins_layout.addWidget(self.new_master_check)

        def add_plugin(name, info, checked=True, enabled=True):
            row = QHBoxLayout()
            row.setSpacing(8)
            row.setContentsMargins(0, 1, 0, 1)

            check = QCheckBox(name)
            check.setChecked(checked)
            check.setEnabled(enabled)
            check.setStyleSheet(
                "QCheckBox { margin: 0px; padding: 0px; min-width: 150px; }")
            check.setFixedWidth(150)
            row.addWidget(check)

            info_label = QLabel(info)
            info_label.setStyleSheet(
                "color: #888; font-size: 9pt; margin: 0px; padding: 0px;")
            info_label.setWordWrap(False)
            row.addWidget(info_label, 1)

            plugins_layout.addLayout(row)
            return check

        # Pipeline Mode selector
        mode_label = QLabel("Pipeline Mode:")
        mode_label.setStyleSheet("font-weight: bold; margin-top: 4px;")
        plugins_layout.addWidget(mode_label)

        mode_row = QHBoxLayout()
        mode_row.setSpacing(8)
        mode_row.setContentsMargins(0, 1, 0, 1)

        self.pipeline_mode_combo = QComboBox()
        self.pipeline_mode_combo.addItems(
            ["Sequential", "Parallel (Async)", "Custom (Per-Stage)",
             "Subprocess (Isolated)"])
        self.pipeline_mode_combo.setFixedWidth(200)
        self.pipeline_mode_combo.setToolTip(
            "Sequential: Processes one frame at a time (Capture → OCR → Translate → Display).\n"
            "Parallel (Async): Overlaps stages so multiple frames are processed simultaneously.\n"
            "Custom: Configure each stage independently as Sequential or Async.\n"
            "Subprocess (Isolated): Runs OCR in a separate process for crash isolation.\n"
            "If the OCR engine crashes, it auto-restarts without affecting the main app.\n"
            "Parallel mode gives 50-80% higher throughput."
        )
        mode_row.addWidget(self.pipeline_mode_combo)

        mode_info = QLabel("Controls how pipeline stages are executed")
        mode_info.setStyleSheet(
            "color: #888; font-size: 9pt; margin: 0px; padding: 0px;")
        mode_row.addWidget(mode_info, 1)

        plugins_layout.addLayout(mode_row)

        # Essential Plugins (Alphabetical)
        essential_label = QLabel("⭐ Essential Plugins (Always Active):")
        essential_label.setStyleSheet(
            "font-weight: bold; color: #4a9eff; margin-top: 4px;")
        plugins_layout.addWidget(essential_label)

        self.new_context_check = add_plugin(
            "Context Plugin",
            "Adapts OCR/Translation based on content type (Wiki, Manga, Game, etc.)")
        self.new_skip_check = add_plugin(
            "Frame Skip", "Skips unchanged frames → 50-70% CPU saved")
        self.new_dict_check = add_plugin(
            "Learning Dictionary",
            "Smart dictionary learns translations → 40-80% faster")
        self.new_merger_check = add_plugin(
            "Text Block Merger",
            "Merges fragmented text → Better translations", enabled=False)
        self.new_cache_check = add_plugin(
            "Translation Cache",
            "Instant lookup for repeated text → 100x speedup")
        self.new_intelligent_check = add_plugin(
            "Intelligent Text Processor",
            "OCR error correction + text validation → 30-50% noise reduction")

        # Optional Plugins (Alphabetical)
        optional_label = QLabel("Optional Plugins:")
        optional_label.setStyleSheet("font-weight: bold; margin-top: 6px;")
        plugins_layout.addWidget(optional_label)

        self.new_batch_check = add_plugin(
            "Batch Processing",
            "Process multiple frames together → 30-50% faster (best with Parallel mode)",
            False)
        self.new_ocr_per_region_check = add_plugin(
            "OCR per Region",
            "Different OCR engine per capture region", False)
        self.new_color_contrast_check = add_plugin(
            "Color Contrast",
            "Auto-adapt overlay colors to background → WCAG 2.0 readability",
            False)
        self.new_motion_check = add_plugin(
            "Motion Tracker", "Smooth scrolling detection", True)
        self.new_parallel_capture_check = add_plugin(
            "Parallel Capture",
            "Process multiple regions simultaneously", False)
        self.new_parallel_ocr_check = add_plugin(
            "Parallel OCR",
            "Process multiple regions simultaneously", False)
        self.new_parallel_trans_check = add_plugin(
            "Parallel Translation",
            "Translate multiple blocks simultaneously → 2-4x faster", False)
        self.new_priority_check = add_plugin(
            "Priority Queue",
            "User tasks first → 20-30% responsiveness boost", False)
        self.new_regex_check = add_plugin(
            "Regex Text Processor",
            "Pattern-based text filtering and normalization", False)
        self.new_spell_check = add_plugin(
            "Spell Corrector",
            "Fixes OCR errors → 10-20% accuracy boost", True)
        self.new_chain_check = add_plugin(
            "Translation Chain",
            "Multi-language translation (JA→EN→DE)", False)
        self.new_work_check = add_plugin(
            "Work-Stealing Pool",
            "Load balancing → 15-25% better CPU utilization (best with Parallel mode)",
            False)

        # Apply button
        self.apply_btn = QPushButton("💾 Apply Changes")
        self.apply_btn.setProperty("class", "action")
        plugins_layout.addWidget(self.apply_btn)

        layout.addWidget(plugins_group)

        # Active Components - Compact
        components_group = QGroupBox("Active Components")
        components_layout = QFormLayout(components_group)
        components_layout.setSpacing(2)
        components_layout.setContentsMargins(10, 8, 10, 8)

        self.new_capture_label = QLabel("Loading...")
        components_layout.addRow("Capture:", self.new_capture_label)

        self.new_ocr_label = QLabel("Loading...")
        components_layout.addRow("OCR:", self.new_ocr_label)

        self.new_translation_label = QLabel("Loading...")
        components_layout.addRow("Translation:", self.new_translation_label)

        self.new_overlay_label = QLabel("Loading...")
        components_layout.addRow("Overlay:", self.new_overlay_label)

        layout.addWidget(components_group)

        layout.addStretch()

    # ------------------------------------------------------------------
    # Pipeline button state management
    # ------------------------------------------------------------------

    def update_stats(self, stats) -> None:
        """Update Quick Statistics labels from a PipelineStats object."""
        self.new_fps_label.setText(f"{stats.average_fps:.1f} FPS")
        self.new_latency_label.setText(f"{stats.average_latency_ms:.0f} ms")
        self.new_frames_label.setText(str(stats.frames_processed))
        self.new_translations_label.setText(str(stats.total_translations))

        if stats.total_translations > 0:
            hit_pct = (stats.cache_hits / stats.total_translations) * 100
            self.new_cache_label.setText(
                f"{stats.cache_hits} ({hit_pct:.0f}%)")
        else:
            self.new_cache_label.setText(f"{stats.cache_hits} (0%)")

    def reset_stats(self) -> None:
        """Reset Quick Statistics labels to defaults."""
        self.new_fps_label.setText("0.0 FPS")
        self.new_latency_label.setText("0 ms")
        self.new_frames_label.setText("0")
        self.new_translations_label.setText("0")
        self.new_cache_label.setText("0 (0%)")

    def update_pipeline_state(self, running: bool, paused: bool) -> None:
        """Update button states and status label to reflect pipeline state."""
        self.new_start_btn.setEnabled(not running and not paused)
        self.new_pause_btn.setEnabled(running or paused)
        self.new_stop_btn.setEnabled(running or paused)

        if paused:
            self.new_pause_btn.setText("▶ Resume")
            self.new_status_label.setText("Paused")
            self.new_status_label.setStyleSheet(
                "font-weight: bold; color: #f0a030;")
        elif running:
            self.new_pause_btn.setText("⏸ Pause")
            self.new_status_label.setText("Running")
            self.new_status_label.setStyleSheet(
                "font-weight: bold; color: #4caf50;")
        else:
            self.new_pause_btn.setText("⏸ Pause")
            self.new_status_label.setText("Idle (Ready to Start)")
            self.new_status_label.setStyleSheet(
                "font-weight: bold; color: #4a9eff;")
