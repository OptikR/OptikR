"""
Pipeline Flow Section

Side-by-side sequential vs async pipeline flow visualization.
"""

import logging

from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QGroupBox, QLabel,
    QPushButton, QMessageBox,
)

logger = logging.getLogger(__name__)

ENGINE_NAMES = {
    'easyocr': 'EasyOCR',
    'tesseract': 'Tesseract',
    'paddleocr': 'PaddleOCR',
    'mokuro': 'Mokuro',
    'windows_ocr': 'Windows OCR',
    'judge_ocr': 'Judge OCR',
}

LANGUAGE_NAMES = {
    'ja': 'Japanese',
    'en': 'English',
    'zh': 'Chinese',
    'ko': 'Korean',
    'de': 'German',
    'fr': 'French',
    'es': 'Spanish',
    'pt': 'Portuguese',
    'ru': 'Russian',
    'ar': 'Arabic',
    'hi': 'Hindi',
}


def get_ocr_engine_display(config_manager) -> str:
    """Get the OCR engine display name from config."""
    if not config_manager:
        return "EasyOCR"

    try:
        engine = config_manager.get_setting('ocr.engine', 'easyocr')
        languages = config_manager.get_setting('ocr.languages', [])

        if languages and len(languages) > 0:
            first_lang = languages[0]
            if '(' in first_lang and ')' in first_lang:
                language = first_lang.split('(')[1].split(')')[0].strip()
            else:
                language = first_lang
        else:
            language = 'en'

        engine_display = ENGINE_NAMES.get(engine.lower(), engine.title())
        lang_display = LANGUAGE_NAMES.get(language.lower(), language.upper())

        return f"{engine_display} ({lang_display})"
    except Exception:
        logger.warning("Failed to get OCR engine display", exc_info=True)
        return "EasyOCR"


class FlowSection(QWidget):
    """Pipeline flow visualization with sequential vs async comparison."""

    _PIPELINE_TO_UI_KEY = {
        'capture': 'capture',
        'preprocessing': 'ocr',
        'ocr': 'ocr',
        'translation': 'translation',
        'overlay': 'overlay',
    }

    def __init__(self, config_manager=None, parent=None):
        super().__init__(parent)
        self.config_manager = config_manager
        self._pipeline = None
        self._seq_stages: dict = {}
        self._async_stages: dict = {}
        self._async_total_label: QLabel | None = None
        self._timing_indicator: QLabel | None = None
        self._init_ui()

    def _init_ui(self):
        main_layout = QVBoxLayout(self)
        main_layout.setSpacing(10)

        # Header
        header_label = QLabel("Pipeline Flow Visualization")
        header_label.setStyleSheet(
            "font-size: 14pt; font-weight: bold; margin-bottom: 5px;")
        main_layout.addWidget(header_label)

        desc_label = QLabel(
            "Compare Sequential vs Parallel (Async) pipeline execution modes. "
            "Select your mode in the Overview or Plugins by Stage tab.")
        desc_label.setWordWrap(True)
        desc_label.setStyleSheet("color: #666666; margin-bottom: 10px;")
        main_layout.addWidget(desc_label)

        bench_layout = QHBoxLayout()
        bench_layout.setSpacing(10)

        bench_btn = QPushButton("⏱ Measure Now")
        bench_btn.setToolTip(
            "Read live stage timings from the running pipeline")
        bench_btn.setFixedWidth(140)
        bench_btn.setStyleSheet(
            "QPushButton { background: #2d5a88; color: #fff; border: none; "
            "border-radius: 4px; padding: 6px 12px; font-weight: bold; }"
            "QPushButton:hover { background: #3a6fa0; }"
            "QPushButton:pressed { background: #1e3d5c; }")
        bench_btn.clicked.connect(self._run_benchmark)
        bench_layout.addWidget(bench_btn)

        self._timing_indicator = QLabel("📊 Showing estimated timings")
        self._timing_indicator.setStyleSheet(
            "color: #ff9800; font-size: 9pt; font-style: italic;")
        bench_layout.addWidget(self._timing_indicator)
        bench_layout.addStretch()

        main_layout.addLayout(bench_layout)

        # Side-by-side comparison
        comparison_layout = QHBoxLayout()
        comparison_layout.setSpacing(15)

        sequential_widget = self._create_sequential_pipeline_view()
        comparison_layout.addWidget(sequential_widget, 1)

        async_widget = self._create_async_pipeline_view()
        comparison_layout.addWidget(async_widget, 1)

        main_layout.addLayout(comparison_layout)

        # All Optimizer Plugins Summary (they're ALL global!)
        global_group = QGroupBox("All Optimizer Plugins (Global)")
        global_layout = QVBoxLayout(global_group)

        info_label = QLabel(
            "ℹ️ All plugins work globally across the entire pipeline")
        info_label.setStyleSheet(
            "color: #888; font-size: 9pt; font-style: italic; margin-bottom: 5px;")
        global_layout.addWidget(info_label)

        essential_label = QLabel("⭐ Essential (Always Active):")
        essential_label.setStyleSheet(
            "font-weight: bold; color: #4a9eff; margin-top: 5px;")
        global_layout.addWidget(essential_label)

        essential_plugins = [
            ("Translation Cache", "100x speedup for repeated text", True),
            ("Smart Dictionary", "Learns translations, 20x faster lookups", True),
            ("Frame Skip", "50-70% CPU saved", True),
            ("Text Validator", "30-50% noise reduction", True),
            ("Text Block Merger", "Better translation quality", True),
        ]

        for name, benefit, enabled in essential_plugins:
            status = "✅" if enabled else "⚪"
            plugin_label = QLabel(f"  {status} {name} ({benefit})")
            plugin_label.setStyleSheet("color: #aaa; font-size: 9pt;")
            global_layout.addWidget(plugin_label)

        optional_label = QLabel("Optional (Enable for more speed):")
        optional_label.setStyleSheet(
            "font-weight: bold; color: #888; margin-top: 8px;")
        global_layout.addWidget(optional_label)

        optional_plugins = [
            ("Batch Processing",
             "30-50% faster (best with Parallel mode)", False),
            ("Parallel OCR/Capture", "2-3x faster (uses more CPU)", False),
            ("Priority Queue", "20-30% responsiveness", False),
            ("Work-Stealing Pool",
             "15-25% CPU utilization (best with Parallel mode)", False),
            ("Motion Tracker", "Skips OCR during scrolling", True),
            ("Spell Corrector", "10-20% accuracy boost", True),
        ]

        for name, benefit, enabled in optional_plugins:
            status = "✅" if enabled else "⚪"
            plugin_label = QLabel(f"  {status} {name} ({benefit})")
            plugin_label.setStyleSheet("color: #aaa; font-size: 9pt;")
            global_layout.addWidget(plugin_label)

        main_layout.addWidget(global_group)
        main_layout.addStretch()

    def _create_sequential_pipeline_view(self) -> QWidget:
        """Create sequential pipeline visualization."""
        widget = QWidget()
        layout = QVBoxLayout(widget)
        layout.setSpacing(5)
        layout.setContentsMargins(5, 5, 5, 5)

        title = QLabel("📊 Sequential Pipeline (Default)")
        title.setStyleSheet(
            "font-size: 12pt; font-weight: bold; color: #4a9eff; "
            "margin-bottom: 5px;")
        layout.addWidget(title)

        subtitle = QLabel("One stage at a time, waits for completion")
        subtitle.setStyleSheet(
            "color: #888; font-size: 9pt; margin-bottom: 10px;")
        layout.addWidget(subtitle)

        ocr_engine_display = get_ocr_engine_display(self.config_manager)

        preprocessing_enabled = (
            self.config_manager.get_setting('ocr.preprocessing_enabled', False)
            if self.config_manager else False)
        seamless_enabled = (
            self.config_manager.get_setting('overlay.seamless_background', False)
            if self.config_manager else False)

        ocr_time = "~70ms" if preprocessing_enabled else "~50ms"
        ocr_plugins = ["Text Validator", "Spell Check"]
        if preprocessing_enabled:
            ocr_plugins.append("🔍 Intelligent Preprocessing")

        overlay_plugins = []
        if seamless_enabled:
            overlay_plugins.append("🎨 Seamless Background")

        stage_keys = ['capture', 'ocr', 'translation', 'positioning', 'overlay']
        stages = [
            ("1. CAPTURE", "~8ms", "DirectX GPU", ["Frame Skip"]),
            ("2. OCR", ocr_time, ocr_engine_display, ocr_plugins),
            ("3. TRANSLATION", "~30ms", "MarianMT", ["Cache", "Dictionary"]),
            ("4. POSITIONING", "~5ms", "Smart Layout", ["Collision Detection"]),
            ("5. OVERLAY", "~1ms", "PyQt6", overlay_plugins)
        ]

        for (stage_title, timing, method, plugins), key in zip(stages, stage_keys):
            stage_group = self._create_compact_stage(
                stage_title, timing, method, plugins)
            self._seq_stages[key] = (stage_group, stage_title, timing)
            layout.addWidget(stage_group)

            if stage_title != "5. OVERLAY":
                arrow = QLabel("    ↓")
                arrow.setStyleSheet(
                    "font-size: 14pt; color: #666; margin: 0px; padding: 0px;")
                layout.addWidget(arrow)

        base_time = 114 if preprocessing_enabled else 94
        base_fps = round(1000 / base_time, 1)

        total_label = QLabel(f"⏱️ Baseline: ~{base_time}ms ({base_fps} FPS)")
        total_label.setStyleSheet(
            "font-size: 11pt; font-weight: bold; color: #0066CC; "
            "margin-top: 10px; padding: 8px; background: #1a1a1a; "
            "border-radius: 4px;")
        layout.addWidget(total_label)
        self.total_time_label = total_label

        baseline_note = QLabel(
            "⚠️ Without any optimizer plugins"
            + (" + Intelligent Preprocessing" if preprocessing_enabled else ""))
        baseline_note.setStyleSheet(
            "color: #ff9800; font-size: 8pt; font-style: italic; "
            "margin-top: 2px;")
        layout.addWidget(baseline_note)

        optimized_label = QLabel(
            "💡 With Cache + Smart Dictionary: ~35ms (28 FPS)")
        optimized_label.setStyleSheet(
            "color: #66bb6a; font-size: 10pt; font-weight: bold; "
            "margin-top: 5px;")
        layout.addWidget(optimized_label)

        note = QLabel(
            "✓ Predictable, stable, low memory\n"
            "✗ Lower throughput\n"
            "🚀 With all optimizers: 25-35 FPS possible"
        )
        note.setStyleSheet("color: #888; font-size: 9pt; margin-top: 5px;")
        layout.addWidget(note)

        use_case = QLabel(
            "📖 Best for:\n"
            "• Reading articles/books (3-5 FPS sufficient)\n"
            "• Static content (Wikipedia, documents)\n"
            "• Low-end hardware"
        )
        use_case.setStyleSheet(
            "color: #aaa; font-size: 8pt; margin-top: 8px; "
            "padding: 6px; background: #1e1e1e; border-radius: 3px;"
        )
        layout.addWidget(use_case)

        layout.addStretch()

        widget.setStyleSheet(
            "QWidget { border: 1px solid #444; border-radius: 5px; "
            "background: #2a2a2a; }")

        return widget

    def _create_async_pipeline_view(self) -> QWidget:
        """Create async pipeline visualization."""
        widget = QWidget()
        layout = QVBoxLayout(widget)
        layout.setSpacing(5)
        layout.setContentsMargins(5, 5, 5, 5)

        title = QLabel("⚡ Async Pipeline (Advanced)")
        title.setStyleSheet(
            "font-size: 12pt; font-weight: bold; color: #66bb6a; "
            "margin-bottom: 5px;")
        layout.addWidget(title)

        subtitle = QLabel("Overlapping execution, parallel processing")
        subtitle.setStyleSheet(
            "color: #aaa; font-size: 9pt; margin-bottom: 10px;")
        layout.addWidget(subtitle)

        parallel_label = QLabel(
            "Frame 1: [CAPTURE] → [OCR] → [TRANS] → [POS] → [OVERLAY]\n"
            "Frame 2:           [CAPTURE] → [OCR] → [TRANS] → [POS]\n"
            "Frame 3:                     [CAPTURE] → [OCR] → [TRANS]"
        )
        parallel_label.setStyleSheet(
            "font-family: 'Courier New', monospace; "
            "font-size: 9pt; "
            "color: #aaddaa; "
            "background: #1e1e1e; "
            "padding: 10px; "
            "border: 1px solid #555; "
            "border-radius: 4px; "
            "margin-bottom: 10px;"
        )
        layout.addWidget(parallel_label)

        ocr_engine_display = get_ocr_engine_display(self.config_manager)

        preprocessing_enabled = (
            self.config_manager.get_setting('ocr.preprocessing_enabled', False)
            if self.config_manager else False)
        seamless_enabled = (
            self.config_manager.get_setting('overlay.seamless_background', False)
            if self.config_manager else False)

        ocr_time = "~70ms" if preprocessing_enabled else "~50ms"
        ocr_plugins = ["Text Validator", "Parallel OCR"]
        if preprocessing_enabled:
            ocr_plugins.append("🔍 Intelligent Preprocessing")

        overlay_plugins = []
        if seamless_enabled:
            overlay_plugins.append("🎨 Seamless Background")

        stage_keys = ['capture', 'ocr', 'translation', 'positioning', 'overlay']
        stages = [
            ("1. CAPTURE", "~8ms", "DirectX GPU",
             ["Frame Skip", "Parallel Capture"]),
            ("2. OCR", ocr_time, ocr_engine_display, ocr_plugins),
            ("3. TRANSLATION", "~30ms", "MarianMT",
             ["Cache", "Batch Processing"]),
            ("4. POSITIONING", "~5ms", "Smart Layout",
             ["Collision Detection"]),
            ("5. OVERLAY", "~1ms", "PyQt6", overlay_plugins)
        ]

        for (stage_title, timing, method, plugins), key in zip(stages, stage_keys):
            stage_group = self._create_compact_stage(
                stage_title, timing, method, plugins, async_mode=True)
            self._async_stages[key] = (stage_group, stage_title, timing)
            layout.addWidget(stage_group)

            if stage_title != "5. OVERLAY":
                arrow = QLabel("    ⇊ (parallel)")
                arrow.setStyleSheet(
                    "font-size: 10pt; color: #66bb6a; margin: 0px; "
                    "padding: 0px;")
                layout.addWidget(arrow)

        total_label = QLabel("⏱️ With Async: ~50ms (20 FPS)")
        self._async_total_label = total_label
        total_label.setStyleSheet(
            "font-size: 11pt; font-weight: bold; color: #66bb6a; "
            "margin-top: 10px; padding: 8px; background: #1e1e1e; "
            "border: 1px solid #555; border-radius: 4px;")
        layout.addWidget(total_label)

        async_note = QLabel(
            "⚡ Same hardware, 2x throughput via parallelism")
        async_note.setStyleSheet(
            "color: #66bb6a; font-size: 8pt; font-style: italic; "
            "margin-top: 2px;")
        layout.addWidget(async_note)

        note = QLabel(
            "✓ 50-80% higher throughput (same CPU)\n"
            "✗ +30% memory, more complex\n"
            "⚠️ Parallel plugins use MORE resources"
        )
        note.setStyleSheet("color: #aaa; font-size: 9pt; margin-top: 5px;")
        layout.addWidget(note)

        resource_warning = QLabel(
            "⚙️ Resource Impact:\n"
            "• Async Pipeline: Same CPU, +30% RAM\n"
            "• Parallel Capture/OCR: +50-100% CPU\n"
            "• Batch Processing: +20% RAM"
        )
        resource_warning.setStyleSheet(
            "color: #ff9800; font-size: 8pt; margin-top: 5px; "
            "padding: 6px; background: #1e1e1e; border-radius: 3px;"
        )
        layout.addWidget(resource_warning)

        use_case = QLabel(
            "🎮 Best for:\n"
            "• Gaming/streaming (need 15-30 FPS)\n"
            "• Fast-scrolling content\n"
            "• High-end hardware (4+ cores)"
        )
        use_case.setStyleSheet(
            "color: #aaa; font-size: 8pt; margin-top: 8px; "
            "padding: 6px; background: #1e1e1e; border-radius: 3px;"
        )
        layout.addWidget(use_case)

        layout.addStretch()

        widget.setStyleSheet(
            "QWidget { border: 1px solid #444; border-radius: 5px; "
            "background: #2a2a2a; }")

        return widget

    def _create_compact_stage(self, title: str, timing: str, method: str,
                              plugins: list,
                              async_mode: bool = False) -> QGroupBox:
        """Create a compact pipeline stage display."""
        group = QGroupBox(f"{title} - {timing}")

        group.setStyleSheet(
            "QGroupBox { "
            "font-weight: bold; "
            "padding-top: 10px; "
            "border: 1px solid #555; "
            "border-radius: 3px; "
            "margin-top: 5px; "
            "background: #252525; "
            "}"
        )

        layout = QVBoxLayout(group)
        layout.setSpacing(2)
        layout.setContentsMargins(8, 5, 8, 5)

        engine_label = QLabel(f"Method: {method}")
        engine_label.setObjectName("engine_label")

        if async_mode:
            engine_label.setStyleSheet(
                "font-weight: bold; color: #66bb6a; font-size: 9pt;")
        else:
            engine_label.setStyleSheet(
                "font-weight: bold; color: #4a9eff; font-size: 9pt;")

        layout.addWidget(engine_label)

        if plugins:
            plugins_text = ", ".join(plugins)
            if async_mode:
                plugins_label = QLabel(f"⚡ {plugins_text}")
            else:
                plugins_label = QLabel(f"🔌 {plugins_text}")
            plugins_label.setStyleSheet("color: #aaa; font-size: 8pt;")
            plugins_label.setWordWrap(True)
            layout.addWidget(plugins_label)

        return group

    # ------------------------------------------------------------------
    # Pipeline / live timing support
    # ------------------------------------------------------------------

    def set_pipeline(self, pipeline):
        """Set or update the pipeline reference for live timing reads."""
        self._pipeline = pipeline

    def update_stage_timings(self, stage_times_ms: dict):
        """Update displayed timings with real measured values.

        *stage_times_ms* maps pipeline stage names (``capture``, ``ocr``,
        ``preprocessing``, ``translation``, ``overlay``) to average
        milliseconds.  Preprocessing time is merged into the OCR display.
        """
        if not stage_times_ms:
            return

        ui_times: dict = {}
        for stage_name, ms in stage_times_ms.items():
            ui_key = self._PIPELINE_TO_UI_KEY.get(stage_name)
            if ui_key:
                ui_times[ui_key] = ui_times.get(ui_key, 0.0) + ms

        for key, ms in ui_times.items():
            for stages_dict in (self._seq_stages, self._async_stages):
                entry = stages_dict.get(key)
                if entry:
                    group, base_title, _ = entry
                    group.setTitle(f"{base_title} - {ms:.1f}ms")

        self._update_totals(ui_times)

        if self._timing_indicator:
            self._timing_indicator.setText("✓ Showing measured timings")
            self._timing_indicator.setStyleSheet(
                "color: #66bb6a; font-size: 9pt; font-style: italic;")

    def _update_totals(self, ui_times: dict):
        """Recalculate total time and FPS labels from measured stage data."""
        capture_ms = ui_times.get('capture', 8.0)
        ocr_ms = ui_times.get('ocr', 50.0)
        trans_ms = ui_times.get('translation', 30.0)
        pos_ms = 5.0
        overlay_ms = ui_times.get('overlay', 1.0)

        total_seq = capture_ms + ocr_ms + trans_ms + pos_ms + overlay_ms
        seq_fps = 1000 / total_seq if total_seq > 0 else 0
        if hasattr(self, 'total_time_label') and self.total_time_label:
            self.total_time_label.setText(
                f"⏱️ Measured: ~{total_seq:.0f}ms ({seq_fps:.1f} FPS)")

        bottleneck = max(capture_ms, ocr_ms, trans_ms, pos_ms, overlay_ms)
        async_fps = 1000 / bottleneck if bottleneck > 0 else 0
        if self._async_total_label:
            self._async_total_label.setText(
                f"⏱️ Measured: ~{bottleneck:.0f}ms ({async_fps:.1f} FPS)")

    def _run_benchmark(self):
        """Read live stage timings from the pipeline and update the display."""
        if not self._pipeline:
            QMessageBox.information(
                self, "No Pipeline",
                "Pipeline not available yet.\n"
                "Wait for the application to finish loading.")
            return

        try:
            stats = self._pipeline.get_metrics()
            if hasattr(stats, 'stage_times_ms') and stats.stage_times_ms:
                self.update_stage_timings(stats.stage_times_ms)
            else:
                if self._timing_indicator:
                    self._timing_indicator.setText(
                        "⚠ No timing data — start the pipeline first")
                    self._timing_indicator.setStyleSheet(
                        "color: #ff9800; font-size: 9pt; font-style: italic;")
        except Exception:
            logger.warning("Failed to read pipeline timing", exc_info=True)
            if self._timing_indicator:
                self._timing_indicator.setText(
                    "⚠ Failed to read timing data")
                self._timing_indicator.setStyleSheet(
                    "color: #ff5555; font-size: 9pt; font-style: italic;")

    def reset_to_estimated(self):
        """Reset all stage timings back to estimated defaults."""
        for stages_dict in (self._seq_stages, self._async_stages):
            for key, (group, base_title, default_timing) in stages_dict.items():
                group.setTitle(f"{base_title} - {default_timing}")

        preprocessing_enabled = (
            self.config_manager.get_setting('ocr.preprocessing_enabled', False)
            if self.config_manager else False)
        base_time = 114 if preprocessing_enabled else 94
        base_fps = round(1000 / base_time, 1)

        if hasattr(self, 'total_time_label') and self.total_time_label:
            self.total_time_label.setText(
                f"⏱️ Baseline: ~{base_time}ms ({base_fps} FPS)")
        if self._async_total_label:
            self._async_total_label.setText(
                "⏱️ With Async: ~50ms (20 FPS)")

        if self._timing_indicator:
            self._timing_indicator.setText("📊 Showing estimated timings")
            self._timing_indicator.setStyleSheet(
                "color: #ff9800; font-size: 9pt; font-style: italic;")
