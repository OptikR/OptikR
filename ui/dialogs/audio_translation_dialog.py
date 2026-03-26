"""
Real-Time Audio Translation Dialog

Tabbed UI for managing real-time audio translation.
Sub-tabs: Source, Language, Voice & TTS, Subtitles, Game Mode, Advanced.
Persistent control bar at bottom with status, stats, and Start/Pause/Stop/Close.

Uses ``PipelineFactory.create("audio")`` and ``BasePipeline`` lifecycle.
"""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING

from PyQt6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QGroupBox, QLabel,
    QPushButton, QComboBox, QCheckBox, QTextEdit, QMessageBox,
    QGridLayout, QSlider, QFileDialog, QStackedWidget, QLineEdit,
    QWidget, QTabWidget, QFrame, QSizePolicy,
)
from PyQt6.QtCore import Qt, pyqtSignal, QTimer
from PyQt6.QtGui import QFont
from app.localization import TranslatableMixin, tr

if TYPE_CHECKING:
    from ui.widgets.subtitle_overlay import SubtitleOverlay
    from ui.widgets.subtitle_window import SubtitleWindow

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Preset definitions
# ---------------------------------------------------------------------------

PRESETS = {
    "default": {
        "label": "audio_dlg_preset_default",
        "whisper_model": "base",
        "use_gpu": True,
        "auto_detect": True,
        "parallel": False,
        "subtitle_display_mode": "overlay",
        "source_mode": None,
        "vad_enabled": True,
        "echo_cancellation": False,
        "echo_cancel_mode": "gate",
        "ptt_enabled": False,
        "auto_virtual_device": False,
    },
    "gaming": {
        "label": "audio_dlg_preset_gaming",
        "whisper_model": "tiny",
        "use_gpu": True,
        "auto_detect": True,
        "parallel": True,
        "subtitle_display_mode": "overlay",
        "source_mode": "process",
        "vad_enabled": True,
        "echo_cancellation": True,
        "echo_cancel_mode": "gate",
        "ptt_enabled": False,
        "auto_virtual_device": True,
    },
    "meeting": {
        "label": "audio_dlg_preset_meeting",
        "whisper_model": "base",
        "use_gpu": True,
        "auto_detect": True,
        "parallel": False,
        "subtitle_display_mode": "overlay",
        "source_mode": "system",
        "vad_enabled": True,
        "echo_cancellation": False,
        "echo_cancel_mode": "gate",
        "ptt_enabled": False,
        "auto_virtual_device": False,
    },
    "streaming": {
        "label": "audio_dlg_preset_streaming",
        "whisper_model": "small",
        "use_gpu": True,
        "auto_detect": True,
        "parallel": False,
        "subtitle_display_mode": "window",
        "source_mode": "system",
        "vad_enabled": True,
        "echo_cancellation": False,
        "echo_cancel_mode": "gate",
        "ptt_enabled": False,
        "auto_virtual_device": False,
    },
}


class AudioTranslationDialog(TranslatableMixin, QDialog):
    """Dialog for real-time audio translation powered by BasePipeline."""

    translationStarted = pyqtSignal()
    translationStopped = pyqtSignal()

    _translationReceived = pyqtSignal(object)
    _errorReceived = pyqtSignal(str)
    _pipelineStateChanged = pyqtSignal(str)

    def __init__(self, config_manager, pipeline_factory=None,
                 translation_layer=None, parent=None):
        super().__init__(parent)
        self.config_manager = config_manager
        self.pipeline_factory = pipeline_factory
        self.translation_layer = translation_layer
        self._pipeline = None
        self.is_active = False
        self._accumulated_segments = []
        self._subtitle_overlay: SubtitleOverlay | None = None
        self._subtitle_window: SubtitleWindow | None = None

        self._audio_stats = {
            "transcriptions": 0,
            "translations": 0,
            "speeches": 0,
        }

        self._game_mode_enabled = False
        self._process_pid: int | None = None
        self._echo_cancellation_enabled = True
        self._echo_cancel_mode = "gate"
        self._ptt_enabled = False
        self._ptt_key = ""

        self.setWindowTitle(tr("real_time_audio_translation"))
        self.setMinimumSize(740, 660)

        self.init_ui()
        self.load_settings()

        self._translationReceived.connect(self._handle_translation)
        self._errorReceived.connect(self._handle_error)
        self._pipelineStateChanged.connect(self._handle_state_change)

        self.update_timer = QTimer()
        self.update_timer.timeout.connect(self.update_statistics)
        self.update_timer.start(1000)

    # ==================================================================
    # UI construction
    # ==================================================================

    def init_ui(self):
        layout = QVBoxLayout(self)
        layout.setSpacing(8)
        layout.setContentsMargins(12, 10, 12, 10)

        # -- Preset bar (top) --
        layout.addLayout(self._build_preset_bar())

        # -- Tab widget --
        self._tabs = QTabWidget()
        self._tabs.addTab(self._create_source_tab(), tr("audio_dlg_tab_source"))
        self._tabs.addTab(self._create_language_tab(), tr("audio_dlg_tab_language"))
        self._tabs.addTab(self._create_voice_tab(), tr("audio_dlg_tab_voice"))
        self._tabs.addTab(self._create_subtitles_tab(), tr("audio_dlg_tab_subtitles"))
        self._tabs.addTab(self._create_game_mode_tab(), tr("audio_dlg_tab_game_mode"))
        self._tabs.addTab(self._create_advanced_tab(), tr("audio_dlg_tab_advanced"))
        layout.addWidget(self._tabs, 1)

        # -- Transcript panel (collapsible) --
        layout.addWidget(self._build_transcript_panel())

        # -- Control bar (bottom) --
        layout.addWidget(self._build_control_bar())

    # ------------------------------------------------------------------
    # Preset bar
    # ------------------------------------------------------------------

    def _build_preset_bar(self) -> QHBoxLayout:
        bar = QHBoxLayout()
        bar.addWidget(QLabel(tr("audio_dlg_preset_label")))
        self.preset_combo = QComboBox()
        self.preset_combo.addItem(tr("audio_dlg_preset_default"), "default")
        self.preset_combo.addItem(tr("audio_dlg_preset_gaming"), "gaming")
        self.preset_combo.addItem(tr("audio_dlg_preset_meeting"), "meeting")
        self.preset_combo.addItem(tr("audio_dlg_preset_streaming"), "streaming")
        self.preset_combo.currentIndexChanged.connect(self._on_preset_changed)
        bar.addWidget(self.preset_combo)

        save_btn = QPushButton(tr("audio_dlg_save_custom_preset"))
        save_btn.setToolTip(tr("audio_dlg_save_custom_preset_tooltip"))
        save_btn.clicked.connect(self._save_custom_preset)
        bar.addWidget(save_btn)
        bar.addStretch()
        return bar

    def _on_preset_changed(self, _index: int):
        key = self.preset_combo.currentData()
        preset = PRESETS.get(key)
        if not preset:
            return
        self.whisper_model_combo.setCurrentText(preset["whisper_model"])
        self.gpu_check.setChecked(preset["use_gpu"])
        self.auto_detect_check.setChecked(preset["auto_detect"])
        self.parallel_check.setChecked(preset["parallel"])
        self.vad_check.setChecked(preset.get("vad_enabled", True))
        idx = self.display_mode_combo.findData(
            preset["subtitle_display_mode"])
        if idx >= 0:
            self.display_mode_combo.setCurrentIndex(idx)

        # Source mode
        source_mode = preset.get("source_mode")
        if source_mode is not None:
            sm_idx = self.source_mode_combo.findData(source_mode)
            if sm_idx >= 0:
                self.source_mode_combo.setCurrentIndex(sm_idx)

        # Echo cancellation
        self._echo_cancellation_enabled = preset.get(
            "echo_cancellation", False)
        self._echo_cancel_mode = preset.get("echo_cancel_mode", "gate")

        # PTT
        self._ptt_enabled = preset.get("ptt_enabled", False)

        # Auto-detect and configure virtual audio device for TTS output
        if preset.get("auto_virtual_device", False):
            self._auto_configure_virtual_device()

    def _save_custom_preset(self):
        QMessageBox.information(
            self,
            tr("audio_dlg_save_custom_preset"),
            tr("audio_dlg_custom_preset_saved_msg"),
        )

    def _auto_configure_virtual_device(self):
        """Detect a virtual audio cable and select it as TTS output."""
        try:
            from plugins.enhancers.audio_translation.virtual_device_helper import (
                detect_virtual_devices,
            )
            pairs = detect_virtual_devices()
            for pair in pairs:
                if pair.output_device is not None:
                    dev_idx = pair.output_device.index
                    combo_idx = self.output_device_combo.findData(dev_idx)
                    if combo_idx >= 0:
                        self.output_device_combo.setCurrentIndex(combo_idx)
                        logger.info(
                            "[Preset] Auto-selected virtual device '%s' "
                            "(idx=%d) for TTS output",
                            pair.output_device.name, dev_idx,
                        )
                        return
            logger.info(
                "[Preset] No virtual audio device found — "
                "TTS output remains on default device"
            )
        except Exception as exc:
            logger.debug(
                "[Preset] Virtual device auto-config failed: %s", exc
            )

    # ------------------------------------------------------------------
    # Tab: Source
    # ------------------------------------------------------------------

    def _create_source_tab(self) -> QWidget:
        page = QWidget()
        layout = QVBoxLayout(page)

        # Source mode
        mode_layout = QHBoxLayout()
        mode_layout.addWidget(QLabel(tr("audio_dlg_source_mode")))
        self.source_mode_combo = QComboBox()
        self.source_mode_combo.addItem(
            tr("audio_dlg_mode_microphone"), "microphone")
        self.source_mode_combo.addItem(
            tr("audio_dlg_mode_system_audio"), "system")
        self.source_mode_combo.addItem(
            tr("audio_dlg_mode_game_app"), "process")
        self.source_mode_combo.addItem(
            tr("audio_dlg_mode_youtube"), "youtube")
        mode_layout.addWidget(self.source_mode_combo, 1)
        layout.addLayout(mode_layout)

        # Source stack
        self.source_stack = QStackedWidget()

        # Page 0: Microphone
        mic_page = QWidget()
        mic_lay = QGridLayout(mic_page)
        mic_lay.setContentsMargins(0, 0, 0, 0)
        mic_lay.addWidget(QLabel(tr("input_microphone")), 0, 0)
        self.input_device_combo = QComboBox()
        self.input_device_combo.addItem(
            tr("audio_dlg_default_microphone"), None)
        mic_lay.addWidget(self.input_device_combo, 0, 1)
        refresh_input_btn = QPushButton("\U0001f504")
        refresh_input_btn.setMaximumWidth(40)
        refresh_input_btn.clicked.connect(self.refresh_devices)
        mic_lay.addWidget(refresh_input_btn, 0, 2)
        self.source_stack.addWidget(mic_page)

        # Page 1: System Audio (WASAPI Loopback)
        sys_page = QWidget()
        sys_lay = QGridLayout(sys_page)
        sys_lay.setContentsMargins(0, 0, 0, 0)
        sys_lay.addWidget(QLabel(tr("audio_dlg_loopback_device")), 0, 0)
        self.loopback_device_combo = QComboBox()
        self.loopback_device_combo.addItem(
            tr("audio_dlg_default_output"), None)
        sys_lay.addWidget(self.loopback_device_combo, 0, 1)
        refresh_loopback_btn = QPushButton("\U0001f504")
        refresh_loopback_btn.setMaximumWidth(40)
        refresh_loopback_btn.clicked.connect(self.refresh_loopback_devices)
        sys_lay.addWidget(refresh_loopback_btn, 0, 2)
        self.source_stack.addWidget(sys_page)

        # Page 2: Game / Application (per-process capture)
        proc_page = QWidget()
        proc_lay = QGridLayout(proc_page)
        proc_lay.setContentsMargins(0, 0, 0, 0)
        proc_lay.addWidget(
            QLabel(tr("audio_dlg_target_process")), 0, 0)
        self.process_combo = QComboBox()
        self.process_combo.setSizePolicy(
            QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Preferred)
        proc_lay.addWidget(self.process_combo, 0, 1)
        refresh_proc_btn = QPushButton("\U0001f504")
        refresh_proc_btn.setMaximumWidth(40)
        refresh_proc_btn.setToolTip(tr("audio_dlg_refresh_processes"))
        refresh_proc_btn.clicked.connect(self._refresh_audio_processes)
        proc_lay.addWidget(refresh_proc_btn, 0, 2)
        self._process_info_label = QLabel(
            tr("audio_dlg_process_capture_info"))
        self._process_info_label.setStyleSheet(
            "color: #FF9800; font-size: 9pt; font-style: italic;")
        self._process_info_label.setWordWrap(True)
        proc_lay.addWidget(self._process_info_label, 1, 0, 1, 3)
        self.source_stack.addWidget(proc_page)

        # Page 3: YouTube Transcript
        yt_page = QWidget()
        yt_lay = QGridLayout(yt_page)
        yt_lay.setContentsMargins(0, 0, 0, 0)
        yt_lay.addWidget(QLabel(tr("audio_dlg_youtube_url")), 0, 0)
        self.youtube_url_input = QLineEdit()
        self.youtube_url_input.setPlaceholderText(
            "https://www.youtube.com/watch?v=...")
        yt_lay.addWidget(self.youtube_url_input, 0, 1)
        self.fetch_transcript_btn = QPushButton(
            tr("audio_dlg_fetch_transcript"))
        self.fetch_transcript_btn.clicked.connect(
            self._fetch_youtube_transcript)
        yt_lay.addWidget(self.fetch_transcript_btn, 0, 2)
        self.yt_language_label = QLabel("")
        self.yt_language_label.setStyleSheet(
            "color: #666; font-size: 9pt; font-style: italic;")
        yt_lay.addWidget(self.yt_language_label, 1, 0, 1, 3)
        self.source_stack.addWidget(yt_page)

        layout.addWidget(self.source_stack)

        # Source volume
        self.source_volume_widget = QWidget()
        sv_layout = QHBoxLayout(self.source_volume_widget)
        sv_layout.setContentsMargins(0, 0, 0, 0)
        sv_layout.addWidget(QLabel(tr("audio_dlg_source_volume")))
        self.input_volume_slider = QSlider(Qt.Orientation.Horizontal)
        self.input_volume_slider.setRange(0, 200)
        self.input_volume_slider.setValue(100)
        self.input_volume_label = QLabel("100%")
        self.input_volume_label.setMinimumWidth(40)
        self.input_volume_slider.valueChanged.connect(
            lambda v: self.input_volume_label.setText(f"{v}%"))
        sv_layout.addWidget(self.input_volume_slider, 1)
        sv_layout.addWidget(self.input_volume_label)
        layout.addWidget(self.source_volume_widget)

        # Output device
        out_grid = QGridLayout()
        out_grid.addWidget(QLabel(tr("output_speaker")), 0, 0)
        self.output_device_combo = QComboBox()
        self.output_device_combo.addItem(
            tr("audio_dlg_default_speaker"), None)
        out_grid.addWidget(self.output_device_combo, 0, 1)
        refresh_output_btn = QPushButton("\U0001f504")
        refresh_output_btn.setMaximumWidth(40)
        refresh_output_btn.clicked.connect(self.refresh_devices)
        out_grid.addWidget(refresh_output_btn, 0, 2)
        layout.addLayout(out_grid)

        # Translation voice volume
        tv_layout = QHBoxLayout()
        tv_layout.addWidget(QLabel(tr("audio_dlg_translation_volume")))
        self.output_volume_slider = QSlider(Qt.Orientation.Horizontal)
        self.output_volume_slider.setRange(0, 200)
        self.output_volume_slider.setValue(100)
        self.output_volume_label = QLabel("100%")
        self.output_volume_label.setMinimumWidth(40)
        self.output_volume_slider.valueChanged.connect(
            lambda v: self.output_volume_label.setText(f"{v}%"))
        tv_layout.addWidget(self.output_volume_slider, 1)
        tv_layout.addWidget(self.output_volume_label)
        layout.addLayout(tv_layout)

        # Volume ducking
        self.duck_widget = QWidget()
        duck_main = QVBoxLayout(self.duck_widget)
        duck_main.setContentsMargins(0, 5, 0, 0)
        self.duck_check = QCheckBox(tr("audio_dlg_enable_ducking"))
        self.duck_check.setChecked(True)
        self.duck_check.setToolTip(tr("audio_dlg_ducking_tooltip"))
        duck_main.addWidget(self.duck_check)
        dl_layout = QHBoxLayout()
        dl_layout.addWidget(QLabel(tr("audio_dlg_duck_level")))
        self.duck_level_slider = QSlider(Qt.Orientation.Horizontal)
        self.duck_level_slider.setRange(0, 100)
        self.duck_level_slider.setValue(20)
        self.duck_level_label = QLabel("20%")
        self.duck_level_label.setMinimumWidth(40)
        self.duck_level_slider.valueChanged.connect(
            lambda v: self.duck_level_label.setText(f"{v}%"))
        dl_layout.addWidget(self.duck_level_slider, 1)
        dl_layout.addWidget(self.duck_level_label)
        duck_main.addLayout(dl_layout)
        layout.addWidget(self.duck_widget)
        self.duck_widget.setVisible(False)

        self.source_mode_combo.currentIndexChanged.connect(
            self._on_source_mode_changed)

        info = QLabel(tr("audio_dlg_device_tip"))
        info.setStyleSheet(
            "color: #2196F3; font-size: 9pt; font-style: italic;")
        layout.addWidget(info)
        layout.addStretch()
        return page

    def _on_source_mode_changed(self, index: int):
        mode = self.source_mode_combo.currentData()
        self.source_stack.setCurrentIndex(index)
        self.source_volume_widget.setVisible(mode != "youtube")
        self.duck_widget.setVisible(mode not in ("microphone",))
        if hasattr(self, 'bidirectional_check'):
            self.bidirectional_check.setVisible(mode == "microphone")
        if mode == "process":
            self._refresh_audio_processes()

    # ------------------------------------------------------------------
    # Tab: Language
    # ------------------------------------------------------------------

    def _create_language_tab(self) -> QWidget:
        page = QWidget()
        layout = QVBoxLayout(page)

        languages = [
            ("English", "en"), ("Japanese", "ja"), ("German", "de"),
            ("Spanish", "es"), ("French", "fr"), ("Chinese", "zh"),
            ("Korean", "ko"), ("Russian", "ru"), ("Italian", "it"),
            ("Portuguese", "pt"),
        ]

        grid = QGridLayout()

        grid.addWidget(QLabel(tr("your_language")), 0, 0)
        self.source_lang_combo = QComboBox()
        for name, code in languages:
            self.source_lang_combo.addItem(f"{name} ({code})", code)
        grid.addWidget(self.source_lang_combo, 0, 1)

        grid.addWidget(QLabel(tr("target_language")), 1, 0)
        self.target_lang_combo = QComboBox()
        for name, code in [languages[1]] + [languages[0]] + languages[2:]:
            self.target_lang_combo.addItem(f"{name} ({code})", code)
        grid.addWidget(self.target_lang_combo, 1, 1)

        layout.addLayout(grid)

        self.auto_detect_check = QCheckBox(
            tr("audio_dlg_auto_detect_language"))
        self.auto_detect_check.setChecked(True)
        self.auto_detect_check.setToolTip(tr("audio_dlg_auto_detect_tooltip"))
        self.auto_detect_check.toggled.connect(self._on_auto_detect_toggled)
        layout.addWidget(self.auto_detect_check)

        self._auto_detect_hint = QLabel(
            tr("audio_dlg_auto_detect_hint"))
        self._auto_detect_hint.setStyleSheet(
            "color: #66BB6A; font-size: 9pt; font-style: italic; "
            "margin-left: 20px;")
        self._auto_detect_hint.setWordWrap(True)
        layout.addWidget(self._auto_detect_hint)

        self.bidirectional_check = QCheckBox(tr("audio_dlg_bidirectional"))
        self.bidirectional_check.setChecked(True)
        layout.addWidget(self.bidirectional_check)

        layout.addStretch()
        return page

    def _on_auto_detect_toggled(self, checked: bool):
        self.source_lang_combo.setEnabled(not checked)
        self._auto_detect_hint.setVisible(checked)

    # ------------------------------------------------------------------
    # Tab: Voice & TTS
    # ------------------------------------------------------------------

    def _create_voice_tab(self) -> QWidget:
        page = QWidget()
        layout = QVBoxLayout(page)

        selector_layout = QHBoxLayout()
        selector_layout.addWidget(QLabel(tr("audio_dlg_voice_label")))
        self.voice_combo = QComboBox()
        self.voice_combo.setMinimumWidth(300)
        selector_layout.addWidget(self.voice_combo, 1)
        refresh_voices_btn = QPushButton("\U0001f504")
        refresh_voices_btn.setMaximumWidth(40)
        refresh_voices_btn.setToolTip(tr("audio_dlg_refresh_voices"))
        refresh_voices_btn.clicked.connect(self._refresh_voices)
        selector_layout.addWidget(refresh_voices_btn)
        layout.addLayout(selector_layout)

        speed_layout = QHBoxLayout()
        speed_layout.addWidget(QLabel(tr("audio_dlg_speed_label")))
        self.speed_slider = QSlider(Qt.Orientation.Horizontal)
        self.speed_slider.setRange(80, 300)
        self.speed_slider.setValue(170)
        self.speed_slider.setTickInterval(20)
        self.speed_slider.setTickPosition(
            QSlider.TickPosition.TicksBelow)
        speed_layout.addWidget(self.speed_slider, 1)
        self.speed_label = QLabel("170")
        self.speed_label.setMinimumWidth(30)
        self.speed_slider.valueChanged.connect(
            lambda v: self.speed_label.setText(str(v)))
        speed_layout.addWidget(self.speed_label)
        layout.addLayout(speed_layout)

        import_layout = QHBoxLayout()
        import_voice_btn = QPushButton(tr("audio_dlg_import_voice_file"))
        import_voice_btn.setToolTip(tr("audio_dlg_import_voice_tooltip"))
        import_voice_btn.clicked.connect(self._import_custom_voice)
        import_layout.addWidget(import_voice_btn)
        import_pack_btn = QPushButton(tr("audio_dlg_import_voice_pack"))
        import_pack_btn.setToolTip(tr("audio_dlg_import_pack_tooltip"))
        import_pack_btn.clicked.connect(self._import_voice_pack)
        import_layout.addWidget(import_pack_btn)
        remove_btn = QPushButton(tr("audio_dlg_remove_selected"))
        remove_btn.setToolTip(tr("audio_dlg_remove_tooltip"))
        remove_btn.clicked.connect(self._remove_selected_voice)
        import_layout.addWidget(remove_btn)
        import_layout.addStretch()
        layout.addLayout(import_layout)

        info = QLabel(tr("audio_dlg_voice_info"))
        info.setStyleSheet(
            "color: #2196F3; font-size: 9pt; font-style: italic;")
        info.setWordWrap(True)
        layout.addWidget(info)
        layout.addStretch()

        self._refresh_voices()
        return page

    # ------------------------------------------------------------------
    # Tab: Subtitles
    # ------------------------------------------------------------------

    def _create_subtitles_tab(self) -> QWidget:
        page = QWidget()
        layout = QVBoxLayout(page)

        # Display mode
        dm_layout = QHBoxLayout()
        dm_layout.addWidget(QLabel(tr("audio_dlg_display_mode")))
        self.display_mode_combo = QComboBox()
        self.display_mode_combo.addItem(
            tr("audio_dlg_display_overlay"), "overlay")
        self.display_mode_combo.addItem(
            tr("audio_dlg_display_window"), "window")
        self.display_mode_combo.addItem(
            tr("audio_dlg_display_both"), "both")
        self.display_mode_combo.currentIndexChanged.connect(
            self._on_display_mode_changed)
        dm_layout.addWidget(self.display_mode_combo, 1)
        layout.addLayout(dm_layout)

        self.overlay_check = QCheckBox(
            tr("audio_dlg_show_subtitle_overlay"))
        self.overlay_check.setChecked(False)
        self.overlay_check.setToolTip(tr("audio_dlg_overlay_tooltip"))
        self.overlay_check.toggled.connect(self._on_overlay_toggled)
        layout.addWidget(self.overlay_check)

        # Font size
        font_layout = QHBoxLayout()
        font_layout.addWidget(QLabel(tr("audio_dlg_subtitle_font_size")))
        self.subtitle_font_slider = QSlider(Qt.Orientation.Horizontal)
        self.subtitle_font_slider.setRange(12, 48)
        self.subtitle_font_slider.setValue(24)
        self.subtitle_font_label = QLabel("24px")
        self.subtitle_font_label.setMinimumWidth(40)
        self.subtitle_font_slider.valueChanged.connect(
            self._on_subtitle_font_changed)
        font_layout.addWidget(self.subtitle_font_slider, 1)
        font_layout.addWidget(self.subtitle_font_label)
        layout.addLayout(font_layout)

        # Bilingual
        self.bilingual_overlay_check = QCheckBox(
            tr("audio_dlg_bilingual_subtitles"))
        self.bilingual_overlay_check.setChecked(False)
        self.bilingual_overlay_check.setToolTip(
            tr("audio_dlg_bilingual_tooltip"))
        self.bilingual_overlay_check.toggled.connect(
            self._on_bilingual_toggled)
        layout.addWidget(self.bilingual_overlay_check)

        # Export
        export_layout = QHBoxLayout()
        self.export_transcript_btn = QPushButton(
            tr("audio_dlg_export_transcript"))
        self.export_transcript_btn.setToolTip(
            tr("audio_dlg_export_tooltip"))
        self.export_transcript_btn.clicked.connect(self._export_transcript)
        export_layout.addWidget(self.export_transcript_btn)
        export_layout.addStretch()
        layout.addLayout(export_layout)

        layout.addStretch()
        return page

    # ------------------------------------------------------------------
    # Tab: Game Mode
    # ------------------------------------------------------------------

    def _create_game_mode_tab(self) -> QWidget:
        page = QWidget()
        layout = QVBoxLayout(page)
        layout.setSpacing(10)

        # --- Virtual audio device section ---
        vdev_group = QGroupBox(tr("audio_dlg_game_virtual_device_title"))
        vdev_layout = QVBoxLayout(vdev_group)
        vdev_layout.setSpacing(6)

        vdev_desc = QLabel(tr("audio_dlg_game_virtual_device_desc"))
        vdev_desc.setWordWrap(True)
        vdev_desc.setStyleSheet("color: #666; font-size: 9pt;")
        vdev_layout.addWidget(vdev_desc)

        self._vdev_status_label = QLabel(
            tr("audio_dlg_game_virtual_device_status_none"))
        self._vdev_status_label.setWordWrap(True)
        self._vdev_status_label.setStyleSheet("font-size: 9pt;")
        vdev_layout.addWidget(self._vdev_status_label)

        vdev_btn_row = QHBoxLayout()
        self._vdev_setup_btn = QPushButton(
            tr("audio_dlg_game_virtual_device_setup"))
        self._vdev_setup_btn.setStyleSheet(
            "QPushButton { background: #2980B9; color: white; "
            "padding: 6px 14px; border-radius: 4px; }"
            "QPushButton:hover { background: #3498DB; }")
        self._vdev_setup_btn.clicked.connect(self._open_virtual_device_setup)
        vdev_btn_row.addWidget(self._vdev_setup_btn)
        vdev_btn_row.addStretch()
        vdev_layout.addLayout(vdev_btn_row)

        layout.addWidget(vdev_group)

        self._refresh_virtual_device_status()

        # --- Remaining game mode features placeholder ---
        placeholder = QLabel(tr("audio_dlg_game_mode_placeholder"))
        placeholder.setWordWrap(True)
        placeholder.setAlignment(Qt.AlignmentFlag.AlignTop)
        placeholder.setStyleSheet(
            "color: #78909C; font-size: 10pt; padding: 20px;")
        layout.addWidget(placeholder)
        layout.addStretch()
        return page

    def _open_virtual_device_setup(self) -> None:
        from ui.dialogs.virtual_device_setup_dialog import (
            VirtualDeviceSetupDialog,
        )
        dlg = VirtualDeviceSetupDialog(self)
        dlg.deviceConfigured.connect(self._on_virtual_device_configured)
        dlg.exec()

    def _on_virtual_device_configured(self, index: int, name: str) -> None:
        """Apply virtual device as the TTS output device."""
        for i in range(self.output_device_combo.count()):
            if self.output_device_combo.itemData(i) == index:
                self.output_device_combo.setCurrentIndex(i)
                break
        self._refresh_virtual_device_status()

    def _refresh_virtual_device_status(self) -> None:
        try:
            from plugins.enhancers.audio_translation.virtual_device_helper import (
                detect_virtual_devices,
            )
            pairs = detect_virtual_devices()
            if pairs:
                name = pairs[0].family
                self._vdev_status_label.setText(
                    tr("audio_dlg_game_virtual_device_status_ok").format(
                        name=name))
                self._vdev_status_label.setStyleSheet(
                    "color: #27AE60; font-size: 9pt;")
            else:
                self._vdev_status_label.setText(
                    tr("audio_dlg_game_virtual_device_status_none"))
                self._vdev_status_label.setStyleSheet(
                    "color: #E67E22; font-size: 9pt;")
        except Exception:
            self._vdev_status_label.setText(
                tr("audio_dlg_game_virtual_device_status_none"))
            self._vdev_status_label.setStyleSheet(
                "color: #E67E22; font-size: 9pt;")

    # ------------------------------------------------------------------
    # Tab: Advanced
    # ------------------------------------------------------------------

    def _create_advanced_tab(self) -> QWidget:
        page = QWidget()
        layout = QGridLayout(page)
        layout.setSpacing(8)

        layout.addWidget(QLabel(tr("whisper_model")), 0, 0)
        self.whisper_model_combo = QComboBox()
        self.whisper_model_combo.addItems(
            ["tiny", "base", "small", "medium", "large"])
        self.whisper_model_combo.setCurrentText("base")
        layout.addWidget(self.whisper_model_combo, 0, 1)
        model_info = QLabel(tr("audio_dlg_model_size_hint"))
        model_info.setStyleSheet("color: #666; font-size: 8pt;")
        layout.addWidget(model_info, 0, 2)

        self.gpu_check = QCheckBox(tr("audio_dlg_use_gpu"))
        self.gpu_check.setChecked(True)
        layout.addWidget(self.gpu_check, 1, 0, 1, 3)

        self.gpu_warning_label = QLabel(
            tr("audio_dlg_no_nvidia_gpu_warning"))
        self.gpu_warning_label.setWordWrap(True)
        self.gpu_warning_label.setStyleSheet(
            "color: #E67E22; font-size: 8pt; font-style: italic; "
            "margin-left: 20px;")
        self.gpu_warning_label.setVisible(False)
        layout.addWidget(self.gpu_warning_label, 2, 0, 1, 3)

        has_nvidia = self._detect_nvidia_gpu()
        if not has_nvidia:
            self.gpu_check.setChecked(False)
            self.gpu_check.setEnabled(False)
            self.gpu_warning_label.setVisible(True)

        self.vad_check = QCheckBox(tr("audio_dlg_enable_vad"))
        self.vad_check.setChecked(True)
        layout.addWidget(self.vad_check, 3, 0, 1, 3)

        layout.addWidget(QLabel(tr("audio_dlg_silence_threshold")), 4, 0)
        self.silence_threshold_spin = QSlider(Qt.Orientation.Horizontal)
        self.silence_threshold_spin.setRange(2, 30)  # 0.2s to 3.0s in 0.1 steps
        self.silence_threshold_spin.setValue(8)  # 0.8s default
        self.silence_threshold_spin.setToolTip(
            tr("audio_dlg_silence_threshold_tooltip"))
        layout.addWidget(self.silence_threshold_spin, 4, 1)
        self.silence_threshold_label = QLabel("0.8 s")
        layout.addWidget(self.silence_threshold_label, 4, 2)
        self.silence_threshold_spin.valueChanged.connect(
            lambda v: self.silence_threshold_label.setText(f"{v/10:.1f} s"))

        layout.addWidget(QLabel(tr("audio_dlg_max_recording")), 5, 0)
        self.max_buffer_spin = QSlider(Qt.Orientation.Horizontal)
        self.max_buffer_spin.setRange(5, 120)  # 5s to 120s
        self.max_buffer_spin.setValue(30)
        self.max_buffer_spin.setToolTip(
            tr("audio_dlg_max_recording_tooltip"))
        layout.addWidget(self.max_buffer_spin, 5, 1)
        self.max_buffer_label = QLabel("30 s")
        layout.addWidget(self.max_buffer_label, 5, 2)
        self.max_buffer_spin.valueChanged.connect(
            lambda v: self.max_buffer_label.setText(f"{v} s"))

        self.parallel_check = QCheckBox(
            tr("audio_dlg_parallel_processing"))
        self.parallel_check.setChecked(False)
        self.parallel_check.setToolTip(
            tr("audio_dlg_parallel_processing_tooltip"))
        layout.addWidget(self.parallel_check, 6, 0, 1, 3)

        # Spacer at bottom
        spacer = QWidget()
        spacer.setSizePolicy(
            QSizePolicy.Policy.Preferred, QSizePolicy.Policy.Expanding)
        layout.addWidget(spacer, 7, 0)

        return page

    @staticmethod
    def _detect_nvidia_gpu() -> bool:
        try:
            import torch
            if torch.cuda.is_available() and torch.cuda.device_count() > 0:
                name = torch.cuda.get_device_name(0).upper()
                if any(k in name for k in ("NVIDIA", "GEFORCE", "RTX", "GTX")):
                    return True
        except Exception:
            pass
        return False

    # ------------------------------------------------------------------
    # Transcript panel (collapsible)
    # ------------------------------------------------------------------

    def _build_transcript_panel(self) -> QGroupBox:
        group = QGroupBox(tr("audio_dlg_live_transcript"))
        group.setCheckable(True)
        group.setChecked(True)
        layout = QVBoxLayout(group)

        self.transcript_display = QTextEdit()
        self.transcript_display.setReadOnly(True)
        self.transcript_display.setMaximumHeight(140)
        self.transcript_display.setPlaceholderText(
            tr("transcriptions_and_translations_will_appear_here"))
        layout.addWidget(self.transcript_display)
        return group

    # ------------------------------------------------------------------
    # Control bar (bottom)
    # ------------------------------------------------------------------

    def _build_control_bar(self) -> QFrame:
        bar = QFrame()
        bar.setStyleSheet("""
            QFrame {
                background-color: #263238;
                border-radius: 6px;
                padding: 4px;
            }
        """)
        outer = QVBoxLayout(bar)
        outer.setContentsMargins(10, 6, 10, 6)
        outer.setSpacing(4)

        # Stats row
        stats_row = QHBoxLayout()
        self.status_label = QLabel(tr("audio_dlg_idle"))
        self.status_label.setStyleSheet(
            "font-weight: bold; color: #90A4AE; font-size: 10pt;")
        stats_row.addWidget(self.status_label)
        stats_row.addStretch()

        for key, attr_name in [
            (tr("transcriptions"), "transcriptions_label"),
            (tr("translations"), "translations_label"),
            (tr("speeches"), "speeches_label"),
        ]:
            stats_row.addWidget(self._stat_label(key))
            lbl = QLabel("0")
            lbl.setStyleSheet("color: #CFD8DC; font-weight: bold;")
            setattr(self, attr_name, lbl)
            stats_row.addWidget(lbl)

        outer.addLayout(stats_row)

        # Button row
        btn_row = QHBoxLayout()
        btn_row.addStretch()

        self.start_btn = QPushButton(tr("audio_dlg_start_translation"))
        self.start_btn.clicked.connect(self.start_translation)
        self.start_btn.setMinimumWidth(150)
        self.start_btn.setStyleSheet(
            "background-color: #4CAF50; color: white; "
            "font-weight: bold; padding: 8px; border-radius: 4px;")
        btn_row.addWidget(self.start_btn)

        self.pause_btn = QPushButton(tr("audio_dlg_pause"))
        self.pause_btn.clicked.connect(self.pause_translation)
        self.pause_btn.setEnabled(False)
        self.pause_btn.setMinimumWidth(100)
        self.pause_btn.setStyleSheet(
            "background-color: #FF9800; color: white; "
            "font-weight: bold; padding: 8px; border-radius: 4px;")
        btn_row.addWidget(self.pause_btn)

        self.stop_btn = QPushButton(tr("audio_dlg_stop"))
        self.stop_btn.clicked.connect(self.stop_translation)
        self.stop_btn.setEnabled(False)
        self.stop_btn.setMinimumWidth(150)
        self.stop_btn.setStyleSheet(
            "background-color: #f44336; color: white; "
            "font-weight: bold; padding: 8px; border-radius: 4px;")
        btn_row.addWidget(self.stop_btn)

        close_btn = QPushButton(tr("close"))
        close_btn.clicked.connect(self.close)
        close_btn.setMinimumWidth(100)
        btn_row.addWidget(close_btn)

        outer.addLayout(btn_row)
        return bar

    @staticmethod
    def _stat_label(text: str) -> QLabel:
        lbl = QLabel(text)
        lbl.setStyleSheet("color: #78909C; font-size: 9pt;")
        return lbl

    # ==================================================================
    # Subtitle overlay / window controls
    # ==================================================================

    def _on_overlay_toggled(self, checked: bool):
        if checked:
            self._ensure_subtitle_overlay()
        else:
            self._destroy_subtitle_overlay()

    def _on_subtitle_font_changed(self, value: int):
        self.subtitle_font_label.setText(f"{value}px")
        if self._subtitle_overlay is not None:
            self._subtitle_overlay.set_font_size(value)
        if self._subtitle_window is not None:
            self._subtitle_window.set_font_size(value)

    def _on_bilingual_toggled(self, checked: bool):
        if self._subtitle_overlay is not None:
            self._subtitle_overlay.set_bilingual(checked)
        if self._subtitle_window is not None:
            self._subtitle_window.set_bilingual(checked)

    def _ensure_subtitle_overlay(self):
        if self._subtitle_overlay is None:
            from ui.widgets.subtitle_overlay import SubtitleOverlay

            self._subtitle_overlay = SubtitleOverlay(
                font_size=self.subtitle_font_slider.value(),
                bilingual=self.bilingual_overlay_check.isChecked(),
            )

    def _destroy_subtitle_overlay(self):
        if self._subtitle_overlay is not None:
            self._subtitle_overlay.hide_subtitle()
            self._subtitle_overlay.close()
            self._subtitle_overlay.deleteLater()
            self._subtitle_overlay = None

    def _ensure_subtitle_window(self):
        if self._subtitle_window is None:
            from ui.widgets.subtitle_window import SubtitleWindow

            self._subtitle_window = SubtitleWindow(
                font_size=self.subtitle_font_slider.value(),
                bilingual=self.bilingual_overlay_check.isChecked(),
            )
            self._subtitle_window.show()

    def _destroy_subtitle_window(self):
        if self._subtitle_window is not None:
            self._subtitle_window.close()
            self._subtitle_window.deleteLater()
            self._subtitle_window = None

    def _get_display_mode(self) -> str:
        return self.display_mode_combo.currentData() or "overlay"

    def _apply_display_mode(self):
        """Create or destroy subtitle displays based on selected mode."""
        mode = self._get_display_mode()
        if mode in ("overlay", "both"):
            self._ensure_subtitle_overlay()
        else:
            self._destroy_subtitle_overlay()

        if mode in ("window", "both"):
            self._ensure_subtitle_window()
        else:
            self._destroy_subtitle_window()

    def _on_display_mode_changed(self, _index: int):
        """Re-apply display mode when the user changes the combo mid-session."""
        if self.is_active:
            self._apply_display_mode()

    # ==================================================================
    # Device helpers
    # ==================================================================

    def refresh_loopback_devices(self):
        self.loopback_device_combo.clear()
        self.loopback_device_combo.addItem(
            tr("audio_dlg_default_output"), None)
        try:
            from plugins.enhancers.audio_translation.system_audio_capture import (
                SystemAudioCapture,
            )
            for dev in SystemAudioCapture.enumerate_loopback_devices():
                self.loopback_device_combo.addItem(
                    f"{dev['name']} (#{dev['index']})", dev["index"])
        except Exception as e:
            logger.debug("Cannot enumerate loopback devices: %s", e)

    def _refresh_audio_processes(self):
        """Populate the process picker combo with audio-producing processes."""
        self.process_combo.clear()
        try:
            from plugins.enhancers.audio_translation.process_audio_capture import (
                enumerate_audio_processes,
            )
            processes = enumerate_audio_processes()
            if not processes:
                self.process_combo.addItem(
                    tr("audio_dlg_no_audio_processes"), None)
                return
            for proc in processes:
                label = proc.name
                if proc.title:
                    label = f"{proc.name} — {proc.title}"
                label = f"{label} (PID {proc.pid})"
                self.process_combo.addItem(label, proc.pid)

            if self._process_pid is not None:
                idx = self.process_combo.findData(self._process_pid)
                if idx >= 0:
                    self.process_combo.setCurrentIndex(idx)
        except ImportError:
            self.process_combo.addItem(
                tr("audio_dlg_process_capture_unavailable"), None)
            logger.debug("process_audio_capture module not available")
        except Exception as e:
            logger.warning("Failed to enumerate audio processes: %s", e)

    def _fetch_youtube_transcript(self):
        url = self.youtube_url_input.text().strip()
        if not url:
            QMessageBox.warning(
                self, tr("audio_dlg_error"),
                tr("audio_dlg_enter_youtube_url"))
            return

        self.fetch_transcript_btn.setEnabled(False)
        self.yt_language_label.setText(tr("audio_dlg_fetching_transcript"))
        self.yt_language_label.setStyleSheet(
            "color: #666; font-size: 9pt; font-style: italic;")

        try:
            from plugins.enhancers.audio_translation.youtube_transcript import (
                YouTubeTranscriptSource,
            )
            languages = YouTubeTranscriptSource.get_available_languages(url)
            if languages:
                self.yt_language_label.setText(
                    tr("audio_dlg_transcript_available").format(
                        langs=", ".join(languages)))
                self.yt_language_label.setStyleSheet(
                    "color: #4CAF50; font-size: 9pt; font-style: italic;")
            else:
                self.yt_language_label.setText(
                    tr("audio_dlg_no_transcript"))
                self.yt_language_label.setStyleSheet(
                    "color: #f44336; font-size: 9pt; font-style: italic;")
        except ImportError:
            self.yt_language_label.setText(
                tr("audio_dlg_youtube_api_missing"))
            self.yt_language_label.setStyleSheet(
                "color: #f44336; font-size: 9pt; font-style: italic;")
        except Exception as e:
            self.yt_language_label.setText(
                f"{tr('audio_dlg_fetch_failed')}: {e}")
            self.yt_language_label.setStyleSheet(
                "color: #f44336; font-size: 9pt; font-style: italic;")
        finally:
            self.fetch_transcript_btn.setEnabled(True)

    def refresh_devices(self):
        try:
            import pyaudiowpatch as pyaudio
        except ImportError:
            try:
                import pyaudio
            except ImportError:
                logger.debug(
                    "pyaudio not installed, cannot enumerate audio devices")
                return

        pa = None
        try:
            pa = pyaudio.PyAudio()
            self.input_device_combo.clear()
            self.input_device_combo.addItem(
                tr("audio_dlg_default_microphone"), None)
            self.output_device_combo.clear()
            self.output_device_combo.addItem(
                tr("audio_dlg_default_speaker"), None)

            for i in range(pa.get_device_count()):
                info = pa.get_device_info_by_index(i)
                if info['maxInputChannels'] > 0:
                    self.input_device_combo.addItem(
                        f"{info['name']} (#{i})", i)
                if info['maxOutputChannels'] > 0:
                    self.output_device_combo.addItem(
                        f"{info['name']} (#{i})", i)
        except Exception as e:
            logger.warning("Failed to refresh audio devices: %s", e)
        finally:
            if pa is not None:
                try:
                    pa.terminate()
                except Exception:
                    pass

    # ==================================================================
    # Voice management
    # ==================================================================

    def _refresh_voices(self):
        self.voice_combo.clear()
        self.voice_combo.addItem(tr("audio_dlg_default_voice"), None)
        try:
            from plugins.enhancers.audio_translation.voice_manager import (
                get_system_voices, get_coqui_models, get_custom_voices,
                get_voice_packs,
            )
            coqui = get_coqui_models()
            if coqui:
                self.voice_combo.insertSeparator(self.voice_combo.count())
                for v in coqui:
                    self.voice_combo.addItem(
                        f"\U0001f9e0 {v['name']} ({v['language']})",
                        v["id"])
            custom = get_custom_voices()
            if custom:
                self.voice_combo.insertSeparator(self.voice_combo.count())
                for v in custom:
                    self.voice_combo.addItem(
                        f"\U0001f399\ufe0f {v['name']} (custom clone)",
                        v["id"])
            packs = get_voice_packs()
            if packs:
                self.voice_combo.insertSeparator(self.voice_combo.count())
                for p in packs:
                    self.voice_combo.addItem(
                        f"\U0001f4e6 {p['name']} ({p.get('language', '?')})",
                        p["id"])
            system = get_system_voices()
            if system:
                self.voice_combo.insertSeparator(self.voice_combo.count())
                for v in system:
                    self.voice_combo.addItem(
                        f"\U0001f4bb {v['name']}", v["id"])
        except Exception as e:
            logger.debug("Voice manager unavailable: %s", e)

    def _import_custom_voice(self):
        file_path, _ = QFileDialog.getOpenFileName(
            self, tr("audio_dlg_select_voice_audio"), "",
            "Audio Files (*.wav *.mp3 *.ogg *.flac);;All Files (*)")
        if not file_path:
            return
        from PyQt6.QtWidgets import QInputDialog
        name, ok = QInputDialog.getText(
            self, tr("audio_dlg_voice_name_title"),
            tr("audio_dlg_voice_name_prompt"))
        if not ok or not name.strip():
            return
        try:
            from plugins.enhancers.audio_translation.voice_manager import (
                import_custom_voice,
            )
            result = import_custom_voice(file_path, name.strip())
            if result:
                QMessageBox.information(
                    self, tr("audio_dlg_voice_imported"),
                    tr("audio_dlg_voice_imported_msg").format(name=name))
                self._refresh_voices()
                for i in range(self.voice_combo.count()):
                    if self.voice_combo.itemData(i) == result["id"]:
                        self.voice_combo.setCurrentIndex(i)
                        break
            else:
                QMessageBox.warning(
                    self, tr("audio_dlg_import_failed"),
                    tr("audio_dlg_voice_import_failed_msg"))
        except Exception as e:
            QMessageBox.critical(
                self, tr("audio_dlg_error"),
                f"{tr('audio_dlg_import_error')}: {e}")

    def _import_voice_pack(self):
        file_path, _ = QFileDialog.getOpenFileName(
            self, tr("audio_dlg_select_voice_pack"), "",
            "Voice Packs (*.zip);;All Files (*)")
        if not file_path:
            return
        try:
            from plugins.enhancers.audio_translation.voice_manager import (
                import_voice_pack,
            )
            result = import_voice_pack(file_path)
            if result:
                QMessageBox.information(
                    self, tr("audio_dlg_voice_pack_installed"),
                    tr("audio_dlg_voice_pack_installed_msg").format(
                        name=result['name']))
                self._refresh_voices()
                for i in range(self.voice_combo.count()):
                    if self.voice_combo.itemData(i) == result["id"]:
                        self.voice_combo.setCurrentIndex(i)
                        break
            else:
                QMessageBox.warning(
                    self, tr("audio_dlg_import_failed"),
                    tr("audio_dlg_voice_pack_import_failed_msg"))
        except Exception as e:
            QMessageBox.critical(
                self, tr("audio_dlg_error"),
                f"{tr('audio_dlg_import_error')}: {e}")

    def _remove_selected_voice(self):
        voice_id = self.voice_combo.currentData()
        if not voice_id:
            QMessageBox.information(
                self, tr("audio_dlg_nothing_to_remove"),
                tr("audio_dlg_nothing_to_remove_msg"))
            return
        if not (voice_id.startswith("custom:") or
                voice_id.startswith("pack:")):
            QMessageBox.information(
                self, tr("audio_dlg_cannot_remove"),
                tr("audio_dlg_cannot_remove_msg"))
            return
        reply = QMessageBox.question(
            self, tr("audio_dlg_confirm_removal"),
            tr("audio_dlg_confirm_removal_msg").format(
                name=self.voice_combo.currentText()),
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No)
        if reply != QMessageBox.StandardButton.Yes:
            return
        try:
            from plugins.enhancers.audio_translation.voice_manager import (
                remove_custom_voice, remove_voice_pack,
            )
            if voice_id.startswith("custom:"):
                remove_custom_voice(voice_id)
            else:
                remove_voice_pack(voice_id)
            self._refresh_voices()
        except Exception as e:
            QMessageBox.critical(
                self, tr("audio_dlg_error"),
                f"{tr('audio_dlg_removal_failed')}: {e}")

    # ==================================================================
    # Settings persistence
    # ==================================================================

    def load_settings(self):
        config = self.config_manager.get_setting(
            'plugins.audio_translation', {})

        source_mode = config.get('audio_source_mode', 'microphone')
        mode_idx = self.source_mode_combo.findData(source_mode)
        if mode_idx >= 0:
            self.source_mode_combo.setCurrentIndex(mode_idx)

        source_lang = config.get('source_language', 'en')
        target_lang = config.get('target_language', 'ja')
        source_idx = self.source_lang_combo.findData(source_lang)
        if source_idx >= 0:
            self.source_lang_combo.setCurrentIndex(source_idx)
        target_idx = self.target_lang_combo.findData(target_lang)
        if target_idx >= 0:
            self.target_lang_combo.setCurrentIndex(target_idx)

        self.bidirectional_check.setChecked(
            config.get('bidirectional', True))
        self.whisper_model_combo.setCurrentText(
            config.get('whisper_model', 'base'))
        self.gpu_check.setChecked(config.get('use_gpu', True))
        self.vad_check.setChecked(config.get('vad_enabled', True))
        self.silence_threshold_spin.setValue(
            int(config.get('silence_threshold', 0.8) * 10))
        self.max_buffer_spin.setValue(
            int(config.get('max_buffer_duration', 30)))
        self.parallel_check.setChecked(
            config.get('parallel_processing', False))
        self.auto_detect_check.setChecked(
            config.get('auto_detect_language', True))
        self._on_auto_detect_toggled(self.auto_detect_check.isChecked())

        voice_id = config.get('voice_id', None)
        if voice_id:
            for i in range(self.voice_combo.count()):
                if self.voice_combo.itemData(i) == voice_id:
                    self.voice_combo.setCurrentIndex(i)
                    break
        self.speed_slider.setValue(config.get('tts_speed', 170))

        self.input_volume_slider.setValue(
            config.get('input_volume', 100))
        self.output_volume_slider.setValue(
            config.get('output_volume', 100))
        self.duck_check.setChecked(config.get('duck_enabled', True))
        self.duck_level_slider.setValue(config.get('duck_level', 20))
        self.youtube_url_input.setText(config.get('youtube_url', ''))

        self.overlay_check.setChecked(
            config.get('show_subtitle_overlay', False))
        self.subtitle_font_slider.setValue(
            config.get('subtitle_font_size', 24))
        self.bilingual_overlay_check.setChecked(
            config.get('bilingual_subtitles', False))

        display_mode = config.get('subtitle_display_mode', 'overlay')
        dm_idx = self.display_mode_combo.findData(display_mode)
        if dm_idx >= 0:
            self.display_mode_combo.setCurrentIndex(dm_idx)

        active_preset = config.get('active_preset', 'default')
        preset_idx = self.preset_combo.findData(active_preset)
        if preset_idx >= 0:
            self.preset_combo.blockSignals(True)
            self.preset_combo.setCurrentIndex(preset_idx)
            self.preset_combo.blockSignals(False)

        self._game_mode_enabled = config.get('game_mode_enabled', False)
        self._process_pid = config.get('process_pid', None)
        self._echo_cancellation_enabled = config.get(
            'echo_cancellation_enabled', True)
        self._echo_cancel_mode = config.get('echo_cancel_mode', 'gate')
        self._ptt_enabled = config.get('ptt_enabled', False)
        self._ptt_key = config.get('ptt_key', '')

        loopback_dev = config.get('loopback_device', None)
        self.refresh_devices()
        self.refresh_loopback_devices()
        if loopback_dev is not None:
            idx = self.loopback_device_combo.findData(loopback_dev)
            if idx >= 0:
                self.loopback_device_combo.setCurrentIndex(idx)

    def save_settings(self):
        # Capture current process PID from combo if in process mode
        if self.source_mode_combo.currentData() == "process":
            pid = self.process_combo.currentData()
            if pid is not None:
                self._process_pid = pid

        config = {
            'enabled': True,
            'audio_source_mode': self.source_mode_combo.currentData(),
            'input_device': self.input_device_combo.currentData(),
            'loopback_device': self.loopback_device_combo.currentData(),
            'output_device': self.output_device_combo.currentData(),
            'source_language': self.source_lang_combo.currentData(),
            'target_language': self.target_lang_combo.currentData(),
            'bidirectional': self.bidirectional_check.isChecked(),
            'whisper_model': self.whisper_model_combo.currentText(),
            'use_gpu': self.gpu_check.isChecked(),
            'vad_enabled': self.vad_check.isChecked(),
            'vad_sensitivity': 2,
            'silence_threshold': self.silence_threshold_spin.value() / 10.0,
            'max_buffer_duration': float(self.max_buffer_spin.value()),
            'voice_id': self.voice_combo.currentData(),
            'tts_speed': self.speed_slider.value(),
            'input_volume': self.input_volume_slider.value(),
            'output_volume': self.output_volume_slider.value(),
            'parallel_processing': self.parallel_check.isChecked(),
            'auto_detect_language': self.auto_detect_check.isChecked(),
            'duck_enabled': self.duck_check.isChecked(),
            'duck_level': self.duck_level_slider.value(),
            'youtube_url': self.youtube_url_input.text().strip(),
            'show_subtitle_overlay': self.overlay_check.isChecked(),
            'subtitle_font_size': self.subtitle_font_slider.value(),
            'bilingual_subtitles':
                self.bilingual_overlay_check.isChecked(),
            'subtitle_display_mode':
                self.display_mode_combo.currentData() or 'overlay',
            'active_preset':
                self.preset_combo.currentData() or 'default',
            'game_mode_enabled': self._game_mode_enabled,
            'process_pid': self._process_pid,
            'echo_cancellation_enabled': self._echo_cancellation_enabled,
            'echo_cancel_mode': self._echo_cancel_mode,
            'ptt_enabled': self._ptt_enabled,
            'ptt_key': self._ptt_key,
        }
        self.config_manager.set_setting(
            'plugins.audio_translation', config)
        self.config_manager.save_config()

    # ==================================================================
    # Pipeline lifecycle
    # ==================================================================

    def _build_audio_config(self) -> dict:
        source_mode = self.source_mode_combo.currentData()

        # Resolve process PID from the combo when in process mode
        process_pid = None
        if source_mode == "process":
            process_pid = self.process_combo.currentData()
            self._process_pid = process_pid

        return {
            'enabled': True,
            'audio_source_mode': source_mode,
            'input_device': self.input_device_combo.currentData(),
            'loopback_device': self.loopback_device_combo.currentData(),
            'output_device': self.output_device_combo.currentData(),
            'source_language': self.source_lang_combo.currentData(),
            'target_language': self.target_lang_combo.currentData(),
            'bidirectional': self.bidirectional_check.isChecked(),
            'whisper_model': self.whisper_model_combo.currentText(),
            'use_gpu': self.gpu_check.isChecked(),
            'vad_enabled': self.vad_check.isChecked(),
            'vad_sensitivity': 2,
            'silence_threshold': self.silence_threshold_spin.value() / 10.0,
            'max_buffer_duration': float(self.max_buffer_spin.value()),
            'voice_id': self.voice_combo.currentData(),
            'tts_speed': self.speed_slider.value(),
            'input_volume': self.input_volume_slider.value(),
            'output_volume': self.output_volume_slider.value(),
            'parallel_processing': self.parallel_check.isChecked(),
            'auto_detect_language': self.auto_detect_check.isChecked(),
            'duck_enabled': self.duck_check.isChecked(),
            'duck_level': self.duck_level_slider.value(),
            'youtube_url': self.youtube_url_input.text().strip(),
            'show_subtitle_overlay': self.overlay_check.isChecked(),
            'subtitle_font_size': self.subtitle_font_slider.value(),
            'bilingual_subtitles':
                self.bilingual_overlay_check.isChecked(),
            'subtitle_display_mode':
                self.display_mode_combo.currentData() or 'overlay',
            'process_pid': process_pid,
            'echo_cancellation_enabled': self._echo_cancellation_enabled,
            'echo_cancel_mode': self._echo_cancel_mode,
            'ptt_enabled': self._ptt_enabled,
            'ptt_key': self._ptt_key,
        }

    def start_translation(self):
        if not self.pipeline_factory:
            QMessageBox.warning(
                self, tr("audio_dlg_factory_not_available"),
                tr("audio_dlg_factory_not_initialized"))
            return

        self.save_settings()
        audio_config = self._build_audio_config()

        if not self.translation_layer:
            QMessageBox.warning(
                self, tr("audio_dlg_error"),
                tr("audio_dlg_no_translation_layer"))
            return

        avail = getattr(self.translation_layer, "get_available_engines", lambda: [])()
        if not avail:
            QMessageBox.warning(
                self, tr("audio_dlg_error"),
                tr("audio_dlg_no_translation_engine"))
            return

        if audio_config.get('audio_source_mode') == 'youtube':
            if not audio_config.get('youtube_url'):
                QMessageBox.warning(
                    self, tr("audio_dlg_error"),
                    tr("audio_dlg_enter_youtube_url"))
                return

        self._accumulated_segments = []

        try:
            self._pipeline = self.pipeline_factory.create(
                "audio",
                translation_layer=self.translation_layer,
                audio_config=audio_config,
            )
            self._pipeline.on_translation = (
                lambda data: self._translationReceived.emit(data))
            self._pipeline.on_error = (
                lambda msg: self._errorReceived.emit(msg))
            self._pipeline.on_state_change = (
                lambda _old, new: self._pipelineStateChanged.emit(
                    new.value))

            self._audio_stats = {
                "transcriptions": 0,
                "translations": 0,
                "speeches": 0,
            }

            if self._pipeline.start():
                self.is_active = True
                self.start_btn.setEnabled(False)
                self.pause_btn.setEnabled(True)
                self.stop_btn.setEnabled(True)
                self.status_label.setText(tr("active_listening"))
                self.status_label.setStyleSheet(
                    "font-weight: bold; color: #4CAF50; font-size: 10pt;")
                self.transcript_display.append(
                    tr("audio_dlg_translation_started"))

                self._apply_display_mode()
                self.translationStarted.emit()
            else:
                QMessageBox.critical(
                    self, tr("audio_dlg_start_failed"),
                    tr("audio_dlg_start_failed_msg"))
        except Exception as e:
            logger.error(
                "Failed to create audio pipeline: %s", e, exc_info=True)
            QMessageBox.critical(
                self, tr("audio_dlg_pipeline_error"),
                tr("audio_dlg_pipeline_error_msg").format(error=e))

    def stop_translation(self):
        self._destroy_subtitle_overlay()
        self._destroy_subtitle_window()

        if self._pipeline is not None:
            self._pipeline.cleanup()
            self._pipeline = None

        self.is_active = False
        self.start_btn.setEnabled(True)
        self.pause_btn.setEnabled(False)
        self.pause_btn.setText(tr("audio_dlg_pause"))
        self.stop_btn.setEnabled(False)
        self.status_label.setText(tr("idle"))
        self.status_label.setStyleSheet(
            "font-weight: bold; color: #90A4AE; font-size: 10pt;")

        self.transcript_display.append(tr("audio_dlg_translation_stopped"))
        self.translationStopped.emit()

    def pause_translation(self):
        if self._pipeline is None:
            return
        from app.workflow.pipeline.types import PipelineState

        if self._pipeline.state == PipelineState.RUNNING:
            self._pipeline.pause()
            self.pause_btn.setText(tr("audio_dlg_resume"))
            self.status_label.setText(tr("audio_dlg_paused_status"))
            self.status_label.setStyleSheet(
                "font-weight: bold; color: #FF9800; font-size: 10pt;")
            self.transcript_display.append(tr("audio_dlg_paused_msg"))
        elif self._pipeline.state == PipelineState.PAUSED:
            self._pipeline.resume()
            self.pause_btn.setText(tr("audio_dlg_pause"))
            self.status_label.setText(tr("active_listening"))
            self.status_label.setStyleSheet(
                "font-weight: bold; color: #4CAF50; font-size: 10pt;")
            self.transcript_display.append(tr("audio_dlg_resumed_msg"))

    # ==================================================================
    # Pipeline callbacks
    # ==================================================================

    def _handle_translation(self, data: dict):
        transcribed = data.get("transcribed_text", "")
        translated = data.get("translated_text", "")
        translations = data.get("translations", [])
        spoken = data.get("spoken", False)

        if transcribed:
            self._audio_stats["transcriptions"] += 1
        if translations:
            self._audio_stats["translations"] += 1
        if spoken:
            self._audio_stats["speeches"] += 1

        if transcribed or translated:
            self._accumulated_segments.append(data)

        if transcribed:
            detected = data.get("detected_language", "?")
            self.transcript_display.append(
                f"\U0001f3a4 [{detected}] {transcribed}")
        if translated:
            target = data.get("target_language", "?")
            self.transcript_display.append(
                f"\U0001f30d [{target}] {translated}")

        if translated:
            detected_lang = data.get("detected_language", "")
            if self._subtitle_overlay is not None:
                self._subtitle_overlay.show_subtitle(
                    translated, transcribed, detected_lang)
            if self._subtitle_window is not None:
                self._subtitle_window.show_subtitle(
                    translated, transcribed, detected_lang)

    def _handle_error(self, message: str):
        self.transcript_display.append(f"\u26a0\ufe0f {message}")

    def _handle_state_change(self, state_str: str):
        if state_str == "error":
            self.is_active = False
            self.start_btn.setEnabled(True)
            self.pause_btn.setEnabled(False)
            self.pause_btn.setText(tr("audio_dlg_pause"))
            self.stop_btn.setEnabled(False)
            self.status_label.setText(tr("audio_dlg_error_stopped"))
            self.status_label.setStyleSheet(
                "font-weight: bold; color: #f44336; font-size: 10pt;")
            self.transcript_display.append(
                tr("audio_dlg_error_stopped_msg"))

    # ==================================================================
    # Statistics
    # ==================================================================

    def update_statistics(self):
        self.transcriptions_label.setText(
            str(self._audio_stats.get("transcriptions", 0)))
        self.translations_label.setText(
            str(self._audio_stats.get("translations", 0)))
        self.speeches_label.setText(
            str(self._audio_stats.get("speeches", 0)))

    # ==================================================================
    # Transcript export
    # ==================================================================

    def _export_transcript(self):
        if not self._accumulated_segments:
            QMessageBox.information(
                self, tr("audio_dlg_no_transcript_data"),
                tr("audio_dlg_no_transcript_data_msg"))
            return

        file_path, _ = QFileDialog.getSaveFileName(
            self, tr("audio_dlg_export_transcript"), "",
            "SRT Subtitle (*.srt);;Text File (*.txt);;All Files (*)")
        if not file_path:
            return

        try:
            from plugins.enhancers.audio_translation.transcript_exporter import (
                TranscriptExporter,
            )
            exporter = TranscriptExporter()
            if file_path.endswith(".srt"):
                exporter.export_dual_srt(
                    self._accumulated_segments, file_path)
            else:
                exporter.export_text(
                    self._accumulated_segments, file_path)
            QMessageBox.information(
                self, tr("audio_dlg_export_success"),
                tr("audio_dlg_export_success_msg").format(path=file_path))
        except ImportError:
            self._export_transcript_fallback(file_path)
        except Exception as e:
            QMessageBox.critical(self, tr("audio_dlg_error"), str(e))

    def _export_transcript_fallback(self, file_path: str):
        try:
            with open(file_path, "w", encoding="utf-8") as f:
                for seg in self._accumulated_segments:
                    original = seg.get("transcribed_text", "")
                    translated = seg.get("translated_text", "")
                    if original:
                        f.write(f"{original}\n")
                    if translated:
                        f.write(f"  \u2192 {translated}\n")
                    f.write("\n")
            QMessageBox.information(
                self, tr("audio_dlg_export_success"),
                tr("audio_dlg_export_success_msg").format(path=file_path))
        except Exception as e:
            QMessageBox.critical(self, tr("audio_dlg_error"), str(e))

    # ==================================================================
    # Cleanup
    # ==================================================================

    def closeEvent(self, event):
        self.update_timer.stop()
        self.save_settings()
        if self.is_active:
            reply = QMessageBox.question(
                self, tr("audio_dlg_translation_active"),
                tr("audio_dlg_stop_and_close"),
                QMessageBox.StandardButton.Yes
                | QMessageBox.StandardButton.No)
            if reply == QMessageBox.StandardButton.Yes:
                self.stop_translation()
                event.accept()
            else:
                event.ignore()
        else:
            self._destroy_subtitle_overlay()
            self._destroy_subtitle_window()
            if self._pipeline is not None:
                self._pipeline.cleanup()
                self._pipeline = None
            event.accept()
