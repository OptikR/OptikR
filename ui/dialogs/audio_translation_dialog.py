"""
Real-Time Audio Translation Dialog

Simple UI for managing real-time audio translation for video calls.
Single PC setup: Microphone -> Translation -> Speaker

Uses ``PipelineFactory.create("audio")`` and ``BasePipeline`` lifecycle
(start/stop/pause) instead of managing threads and queues directly.
"""

import logging

from PyQt6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QGroupBox, QLabel,
    QPushButton, QComboBox, QCheckBox, QTextEdit, QMessageBox,
    QGridLayout, QSlider, QFileDialog, QStackedWidget, QLineEdit, QWidget
)
from PyQt6.QtCore import Qt, pyqtSignal, QTimer
from PyQt6.QtGui import QFont
from app.localization import TranslatableMixin, tr
from ui.widgets.subtitle_overlay import SubtitleOverlay

logger = logging.getLogger(__name__)


class AudioTranslationDialog(TranslatableMixin, QDialog):
    """Dialog for real-time audio translation powered by BasePipeline."""

    translationStarted = pyqtSignal()
    translationStopped = pyqtSignal()

    _translationReceived = pyqtSignal(object)
    _errorReceived = pyqtSignal(str)
    _pipelineStateChanged = pyqtSignal(str)

    def __init__(self, config_manager, pipeline_factory=None, translation_layer=None, parent=None):
        super().__init__(parent)
        self.config_manager = config_manager
        self.pipeline_factory = pipeline_factory
        self.translation_layer = translation_layer
        self._pipeline = None
        self.is_active = False
        self._accumulated_segments = []
        self._subtitle_overlay: SubtitleOverlay | None = None

        self._audio_stats = {
            "transcriptions": 0,
            "translations": 0,
            "speeches": 0,
        }

        self.setWindowTitle(tr("real_time_audio_translation"))
        self.setMinimumSize(700, 600)

        self.init_ui()
        self.load_settings()

        self._translationReceived.connect(self._handle_translation)
        self._errorReceived.connect(self._handle_error)
        self._pipelineStateChanged.connect(self._handle_state_change)

        self.update_timer = QTimer()
        self.update_timer.timeout.connect(self.update_statistics)
        self.update_timer.start(1000)

    # ------------------------------------------------------------------
    # UI construction
    # ------------------------------------------------------------------

    def init_ui(self):
        """Initialize the user interface"""
        layout = QVBoxLayout(self)
        layout.setSpacing(15)

        title = QLabel(tr("audio_dlg_title"))
        title_font = QFont()
        title_font.setPointSize(14)
        title_font.setBold(True)
        title.setFont(title_font)
        layout.addWidget(title)

        desc = QLabel(tr("audio_dlg_description"))
        desc.setWordWrap(True)
        desc.setStyleSheet("color: #666; margin-bottom: 10px;")
        layout.addWidget(desc)

        device_group = self._create_device_section()
        layout.addWidget(device_group)

        lang_group = self._create_language_section()
        layout.addWidget(lang_group)

        advanced_group = self._create_advanced_section()
        layout.addWidget(advanced_group)

        voice_group = self._create_voice_section()
        layout.addWidget(voice_group)

        output_group = self._create_output_section()
        layout.addWidget(output_group)

        transcript_group = self._create_transcript_section()
        layout.addWidget(transcript_group)

        stats_group = self._create_statistics_section()
        layout.addWidget(stats_group)

        button_layout = QHBoxLayout()
        button_layout.addStretch()

        self.start_btn = QPushButton(tr("audio_dlg_start_translation"))
        self.start_btn.clicked.connect(self.start_translation)
        self.start_btn.setMinimumWidth(150)
        self.start_btn.setStyleSheet("background-color: #4CAF50; color: white; font-weight: bold; padding: 8px;")
        button_layout.addWidget(self.start_btn)

        self.pause_btn = QPushButton(tr("audio_dlg_pause"))
        self.pause_btn.clicked.connect(self.pause_translation)
        self.pause_btn.setEnabled(False)
        self.pause_btn.setMinimumWidth(100)
        self.pause_btn.setStyleSheet("background-color: #FF9800; color: white; font-weight: bold; padding: 8px;")
        button_layout.addWidget(self.pause_btn)

        self.stop_btn = QPushButton(tr("audio_dlg_stop"))
        self.stop_btn.clicked.connect(self.stop_translation)
        self.stop_btn.setEnabled(False)
        self.stop_btn.setMinimumWidth(150)
        self.stop_btn.setStyleSheet("background-color: #f44336; color: white; font-weight: bold; padding: 8px;")
        button_layout.addWidget(self.stop_btn)

        close_btn = QPushButton(tr("close"))
        close_btn.clicked.connect(self.close)
        close_btn.setMinimumWidth(100)
        button_layout.addWidget(close_btn)

        layout.addLayout(button_layout)

    def _create_device_section(self) -> QGroupBox:
        """Create device selection section with source mode, volume, and ducking controls"""
        group = QGroupBox(tr("audio_dlg_audio_devices"))
        layout = QVBoxLayout(group)

        mode_layout = QHBoxLayout()
        mode_layout.addWidget(QLabel(tr("audio_dlg_source_mode")))
        self.source_mode_combo = QComboBox()
        self.source_mode_combo.addItem(tr("audio_dlg_mode_microphone"), "microphone")
        self.source_mode_combo.addItem(tr("audio_dlg_mode_system_audio"), "system")
        self.source_mode_combo.addItem(tr("audio_dlg_mode_youtube"), "youtube")
        mode_layout.addWidget(self.source_mode_combo, 1)
        layout.addLayout(mode_layout)

        self.source_stack = QStackedWidget()

        # Page 0: Microphone
        mic_page = QWidget()
        mic_lay = QGridLayout(mic_page)
        mic_lay.setContentsMargins(0, 0, 0, 0)
        mic_lay.addWidget(QLabel(tr("input_microphone")), 0, 0)
        self.input_device_combo = QComboBox()
        self.input_device_combo.addItem(tr("audio_dlg_default_microphone"), None)
        mic_lay.addWidget(self.input_device_combo, 0, 1)
        refresh_input_btn = QPushButton("🔄")
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
        self.loopback_device_combo.addItem(tr("audio_dlg_default_output"), None)
        sys_lay.addWidget(self.loopback_device_combo, 0, 1)
        refresh_loopback_btn = QPushButton("🔄")
        refresh_loopback_btn.setMaximumWidth(40)
        refresh_loopback_btn.clicked.connect(self.refresh_loopback_devices)
        sys_lay.addWidget(refresh_loopback_btn, 0, 2)
        self.source_stack.addWidget(sys_page)

        # Page 2: YouTube Transcript
        yt_page = QWidget()
        yt_lay = QGridLayout(yt_page)
        yt_lay.setContentsMargins(0, 0, 0, 0)
        yt_lay.addWidget(QLabel(tr("audio_dlg_youtube_url")), 0, 0)
        self.youtube_url_input = QLineEdit()
        self.youtube_url_input.setPlaceholderText("https://www.youtube.com/watch?v=...")
        yt_lay.addWidget(self.youtube_url_input, 0, 1)
        self.fetch_transcript_btn = QPushButton(tr("audio_dlg_fetch_transcript"))
        self.fetch_transcript_btn.clicked.connect(self._fetch_youtube_transcript)
        yt_lay.addWidget(self.fetch_transcript_btn, 0, 2)
        self.yt_language_label = QLabel("")
        self.yt_language_label.setStyleSheet("color: #666; font-size: 9pt; font-style: italic;")
        yt_lay.addWidget(self.yt_language_label, 1, 0, 1, 3)
        self.source_stack.addWidget(yt_page)

        layout.addWidget(self.source_stack)

        # Source volume (hidden in YouTube mode)
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
            lambda v: self.input_volume_label.setText(f"{v}%")
        )
        sv_layout.addWidget(self.input_volume_slider, 1)
        sv_layout.addWidget(self.input_volume_label)
        layout.addWidget(self.source_volume_widget)

        # Output device (always visible)
        out_grid = QGridLayout()
        out_grid.addWidget(QLabel(tr("output_speaker")), 0, 0)
        self.output_device_combo = QComboBox()
        self.output_device_combo.addItem(tr("audio_dlg_default_speaker"), None)
        out_grid.addWidget(self.output_device_combo, 0, 1)
        refresh_output_btn = QPushButton("🔄")
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
            lambda v: self.output_volume_label.setText(f"{v}%")
        )
        tv_layout.addWidget(self.output_volume_slider, 1)
        tv_layout.addWidget(self.output_volume_label)
        layout.addLayout(tv_layout)

        # Volume ducking (hidden in Microphone mode)
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
            lambda v: self.duck_level_label.setText(f"{v}%")
        )
        dl_layout.addWidget(self.duck_level_slider, 1)
        dl_layout.addWidget(self.duck_level_label)
        duck_main.addLayout(dl_layout)
        layout.addWidget(self.duck_widget)
        self.duck_widget.setVisible(False)

        self.source_mode_combo.currentIndexChanged.connect(self._on_source_mode_changed)

        info = QLabel(tr("audio_dlg_device_tip"))
        info.setStyleSheet("color: #2196F3; font-size: 9pt; font-style: italic;")
        layout.addWidget(info)

        return group

    def _on_source_mode_changed(self, index: int):
        """Handle source mode combo change -- show/hide mode-specific controls."""
        mode = self.source_mode_combo.currentData()
        self.source_stack.setCurrentIndex(index)
        self.source_volume_widget.setVisible(mode != "youtube")
        self.duck_widget.setVisible(mode != "microphone")
        if hasattr(self, 'bidirectional_check'):
            self.bidirectional_check.setVisible(mode == "microphone")

    # ------------------------------------------------------------------
    # Subtitle overlay controls
    # ------------------------------------------------------------------

    def _on_overlay_toggled(self, checked: bool):
        """Show or hide the subtitle overlay in response to the checkbox."""
        if checked:
            self._ensure_subtitle_overlay()
        else:
            self._destroy_subtitle_overlay()

    def _on_subtitle_font_changed(self, value: int):
        self.subtitle_font_label.setText(f"{value}px")
        if self._subtitle_overlay is not None:
            self._subtitle_overlay.set_font_size(value)

    def _on_bilingual_toggled(self, checked: bool):
        if self._subtitle_overlay is not None:
            self._subtitle_overlay.set_bilingual(checked)

    def _ensure_subtitle_overlay(self):
        """Create the subtitle overlay if it doesn't already exist."""
        if self._subtitle_overlay is None:
            self._subtitle_overlay = SubtitleOverlay(
                font_size=self.subtitle_font_slider.value(),
                bilingual=self.bilingual_overlay_check.isChecked(),
            )

    def _destroy_subtitle_overlay(self):
        """Hide and destroy the subtitle overlay."""
        if self._subtitle_overlay is not None:
            self._subtitle_overlay.hide_subtitle()
            self._subtitle_overlay.close()
            self._subtitle_overlay.deleteLater()
            self._subtitle_overlay = None

    def refresh_loopback_devices(self):
        """Refresh WASAPI loopback device list for system audio capture."""
        self.loopback_device_combo.clear()
        self.loopback_device_combo.addItem(tr("audio_dlg_default_output"), None)
        try:
            from plugins.enhancers.audio_translation.system_audio_capture import (
                SystemAudioCapture,
            )
            for dev in SystemAudioCapture.enumerate_loopback_devices():
                self.loopback_device_combo.addItem(
                    f"{dev['name']} (#{dev['index']})", dev["index"]
                )
        except Exception as e:
            logger.debug("Cannot enumerate loopback devices: %s", e)

    def _fetch_youtube_transcript(self):
        """Fetch and validate transcript availability for the entered YouTube URL."""
        url = self.youtube_url_input.text().strip()
        if not url:
            QMessageBox.warning(
                self, tr("audio_dlg_error"), tr("audio_dlg_enter_youtube_url")
            )
            return

        self.fetch_transcript_btn.setEnabled(False)
        self.yt_language_label.setText(tr("audio_dlg_fetching_transcript"))
        self.yt_language_label.setStyleSheet(
            "color: #666; font-size: 9pt; font-style: italic;"
        )

        try:
            from plugins.enhancers.audio_translation.youtube_transcript import (
                YouTubeTranscriptSource,
            )
            languages = YouTubeTranscriptSource.get_available_languages(url)
            if languages:
                self.yt_language_label.setText(
                    tr("audio_dlg_transcript_available").format(
                        langs=", ".join(languages)
                    )
                )
                self.yt_language_label.setStyleSheet(
                    "color: #4CAF50; font-size: 9pt; font-style: italic;"
                )
            else:
                self.yt_language_label.setText(tr("audio_dlg_no_transcript"))
                self.yt_language_label.setStyleSheet(
                    "color: #f44336; font-size: 9pt; font-style: italic;"
                )
        except ImportError:
            self.yt_language_label.setText(tr("audio_dlg_youtube_api_missing"))
            self.yt_language_label.setStyleSheet(
                "color: #f44336; font-size: 9pt; font-style: italic;"
            )
        except Exception as e:
            self.yt_language_label.setText(f"{tr('audio_dlg_fetch_failed')}: {e}")
            self.yt_language_label.setStyleSheet(
                "color: #f44336; font-size: 9pt; font-style: italic;"
            )
        finally:
            self.fetch_transcript_btn.setEnabled(True)

    def _create_language_section(self) -> QGroupBox:
        """Create language settings section"""
        group = QGroupBox(tr("audio_dlg_languages"))
        layout = QGridLayout(group)

        languages = [
            ("English", "en"), ("Japanese", "ja"), ("German", "de"), ("Spanish", "es"),
            ("French", "fr"), ("Chinese", "zh"), ("Korean", "ko"), ("Russian", "ru"),
            ("Italian", "it"), ("Portuguese", "pt"),
        ]

        layout.addWidget(QLabel(tr("your_language")), 0, 0)
        self.source_lang_combo = QComboBox()
        for name, code in languages:
            self.source_lang_combo.addItem(f"{name} ({code})", code)
        layout.addWidget(self.source_lang_combo, 0, 1)

        layout.addWidget(QLabel(tr("target_language")), 1, 0)
        self.target_lang_combo = QComboBox()
        for name, code in [languages[1]] + [languages[0]] + languages[2:]:
            self.target_lang_combo.addItem(f"{name} ({code})", code)
        layout.addWidget(self.target_lang_combo, 1, 1)

        self.bidirectional_check = QCheckBox(tr("audio_dlg_bidirectional"))
        self.bidirectional_check.setChecked(True)
        layout.addWidget(self.bidirectional_check, 2, 0, 1, 2)

        return group

    def _create_advanced_section(self) -> QGroupBox:
        """Create advanced settings section"""
        group = QGroupBox(tr("audio_dlg_advanced_settings"))
        layout = QGridLayout(group)

        layout.addWidget(QLabel(tr("whisper_model")), 0, 0)
        self.whisper_model_combo = QComboBox()
        self.whisper_model_combo.addItems(["tiny", "base", "small", "medium", "large"])
        self.whisper_model_combo.setCurrentText("base")
        layout.addWidget(self.whisper_model_combo, 0, 1)

        model_info = QLabel(tr("audio_dlg_model_size_hint"))
        model_info.setStyleSheet("color: #666; font-size: 8pt;")
        layout.addWidget(model_info, 0, 2)

        self.gpu_check = QCheckBox(tr("audio_dlg_use_gpu"))
        self.gpu_check.setChecked(True)
        layout.addWidget(self.gpu_check, 1, 0, 1, 3)

        self.gpu_warning_label = QLabel(tr("audio_dlg_no_nvidia_gpu_warning"))
        self.gpu_warning_label.setWordWrap(True)
        self.gpu_warning_label.setStyleSheet(
            "color: #E67E22; font-size: 8pt; font-style: italic; "
            "margin-left: 20px;"
        )
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

        self.parallel_check = QCheckBox(tr("audio_dlg_parallel_processing"))
        self.parallel_check.setChecked(False)
        self.parallel_check.setToolTip(
            tr("audio_dlg_parallel_processing_tooltip")
        )
        layout.addWidget(self.parallel_check, 4, 0, 1, 3)

        self.auto_detect_check = QCheckBox(tr("audio_dlg_auto_detect_language"))
        self.auto_detect_check.setChecked(False)
        self.auto_detect_check.setToolTip(tr("audio_dlg_auto_detect_tooltip"))
        layout.addWidget(self.auto_detect_check, 5, 0, 1, 3)

        return group

    @staticmethod
    def _detect_nvidia_gpu() -> bool:
        """Return True if a usable NVIDIA GPU is available for Whisper."""
        try:
            import torch
            if torch.cuda.is_available() and torch.cuda.device_count() > 0:
                name = torch.cuda.get_device_name(0).upper()
                if "NVIDIA" in name or "GEFORCE" in name or "RTX" in name or "GTX" in name:
                    return True
        except Exception:
            pass
        return False

    def _create_voice_section(self) -> QGroupBox:
        """Create voice selection and import section"""
        group = QGroupBox(tr("audio_dlg_output_voice"))
        layout = QVBoxLayout(group)

        selector_layout = QHBoxLayout()
        selector_layout.addWidget(QLabel(tr("audio_dlg_voice_label")))
        self.voice_combo = QComboBox()
        self.voice_combo.setMinimumWidth(300)
        selector_layout.addWidget(self.voice_combo, 1)

        refresh_voices_btn = QPushButton("🔄")
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
        self.speed_slider.setTickPosition(QSlider.TickPosition.TicksBelow)
        speed_layout.addWidget(self.speed_slider, 1)
        self.speed_label = QLabel("170")
        self.speed_label.setMinimumWidth(30)
        self.speed_slider.valueChanged.connect(lambda v: self.speed_label.setText(str(v)))
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
        info.setStyleSheet("color: #2196F3; font-size: 9pt; font-style: italic;")
        info.setWordWrap(True)
        layout.addWidget(info)

        self._refresh_voices()

        return group

    def _refresh_voices(self):
        """Populate the voice combo box with all available voices."""
        self.voice_combo.clear()
        self.voice_combo.addItem(tr("audio_dlg_default_voice"), None)

        try:
            from plugins.enhancers.audio_translation.voice_manager import (
                get_system_voices, get_coqui_models, get_custom_voices, get_voice_packs
            )

            coqui = get_coqui_models()
            if coqui:
                self.voice_combo.insertSeparator(self.voice_combo.count())
                for v in coqui:
                    label = f"🧠 {v['name']} ({v['language']})"
                    self.voice_combo.addItem(label, v["id"])

            custom = get_custom_voices()
            if custom:
                self.voice_combo.insertSeparator(self.voice_combo.count())
                for v in custom:
                    label = f"🎙️ {v['name']} (custom clone)"
                    self.voice_combo.addItem(label, v["id"])

            packs = get_voice_packs()
            if packs:
                self.voice_combo.insertSeparator(self.voice_combo.count())
                for p in packs:
                    label = f"📦 {p['name']} ({p.get('language', '?')})"
                    self.voice_combo.addItem(label, p["id"])

            system = get_system_voices()
            if system:
                self.voice_combo.insertSeparator(self.voice_combo.count())
                for v in system:
                    label = f"💻 {v['name']}"
                    self.voice_combo.addItem(label, v["id"])

        except Exception as e:
            logger.debug("Voice manager unavailable: %s", e)

    def _import_custom_voice(self):
        """Let user pick an audio file to use as voice clone reference."""
        file_path, _ = QFileDialog.getOpenFileName(
            self,
            tr("audio_dlg_select_voice_audio"),
            "",
            "Audio Files (*.wav *.mp3 *.ogg *.flac);;All Files (*)"
        )
        if not file_path:
            return

        from PyQt6.QtWidgets import QInputDialog
        name, ok = QInputDialog.getText(
            self, tr("audio_dlg_voice_name_title"), tr("audio_dlg_voice_name_prompt")
        )
        if not ok or not name.strip():
            return

        try:
            from plugins.enhancers.audio_translation.voice_manager import import_custom_voice
            result = import_custom_voice(file_path, name.strip())
            if result:
                QMessageBox.information(self, tr("audio_dlg_voice_imported"),
                    tr("audio_dlg_voice_imported_msg").format(name=name))
                self._refresh_voices()
                for i in range(self.voice_combo.count()):
                    if self.voice_combo.itemData(i) == result["id"]:
                        self.voice_combo.setCurrentIndex(i)
                        break
            else:
                QMessageBox.warning(self, tr("audio_dlg_import_failed"),
                    tr("audio_dlg_voice_import_failed_msg"))
        except Exception as e:
            QMessageBox.critical(self, tr("audio_dlg_error"), f"{tr('audio_dlg_import_error')}: {e}")

    def _import_voice_pack(self):
        """Let user pick a .zip voice pack to install."""
        file_path, _ = QFileDialog.getOpenFileName(
            self,
            tr("audio_dlg_select_voice_pack"),
            "",
            "Voice Packs (*.zip);;All Files (*)"
        )
        if not file_path:
            return

        try:
            from plugins.enhancers.audio_translation.voice_manager import import_voice_pack
            result = import_voice_pack(file_path)
            if result:
                QMessageBox.information(self, tr("audio_dlg_voice_pack_installed"),
                    tr("audio_dlg_voice_pack_installed_msg").format(name=result['name']))
                self._refresh_voices()
                for i in range(self.voice_combo.count()):
                    if self.voice_combo.itemData(i) == result["id"]:
                        self.voice_combo.setCurrentIndex(i)
                        break
            else:
                QMessageBox.warning(self, tr("audio_dlg_import_failed"),
                    tr("audio_dlg_voice_pack_import_failed_msg"))
        except Exception as e:
            QMessageBox.critical(self, tr("audio_dlg_error"), f"{tr('audio_dlg_import_error')}: {e}")

    def _remove_selected_voice(self):
        """Remove the currently selected custom voice or voice pack."""
        voice_id = self.voice_combo.currentData()
        if not voice_id:
            QMessageBox.information(self, tr("audio_dlg_nothing_to_remove"),
                tr("audio_dlg_nothing_to_remove_msg"))
            return

        if not (voice_id.startswith("custom:") or voice_id.startswith("pack:")):
            QMessageBox.information(self, tr("audio_dlg_cannot_remove"),
                tr("audio_dlg_cannot_remove_msg"))
            return

        reply = QMessageBox.question(
            self, tr("audio_dlg_confirm_removal"),
            tr("audio_dlg_confirm_removal_msg").format(name=self.voice_combo.currentText()),
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
        )
        if reply != QMessageBox.StandardButton.Yes:
            return

        try:
            from plugins.enhancers.audio_translation.voice_manager import (
                remove_custom_voice, remove_voice_pack
            )
            if voice_id.startswith("custom:"):
                remove_custom_voice(voice_id)
            else:
                remove_voice_pack(voice_id)
            self._refresh_voices()
        except Exception as e:
            QMessageBox.critical(self, tr("audio_dlg_error"), f"{tr('audio_dlg_removal_failed')}: {e}")

    def _create_output_section(self) -> QGroupBox:
        """Create output options section with overlay toggle and export button"""
        group = QGroupBox(tr("audio_dlg_output_options"))
        layout = QVBoxLayout(group)

        self.overlay_check = QCheckBox(tr("audio_dlg_show_subtitle_overlay"))
        self.overlay_check.setChecked(False)
        self.overlay_check.setToolTip(tr("audio_dlg_overlay_tooltip"))
        self.overlay_check.toggled.connect(self._on_overlay_toggled)
        layout.addWidget(self.overlay_check)

        overlay_opts = QHBoxLayout()
        overlay_opts.addWidget(QLabel(tr("audio_dlg_subtitle_font_size")))
        self.subtitle_font_slider = QSlider(Qt.Orientation.Horizontal)
        self.subtitle_font_slider.setRange(12, 48)
        self.subtitle_font_slider.setValue(24)
        self.subtitle_font_label = QLabel("24px")
        self.subtitle_font_label.setMinimumWidth(40)
        self.subtitle_font_slider.valueChanged.connect(self._on_subtitle_font_changed)
        overlay_opts.addWidget(self.subtitle_font_slider, 1)
        overlay_opts.addWidget(self.subtitle_font_label)
        layout.addLayout(overlay_opts)

        self.bilingual_overlay_check = QCheckBox(tr("audio_dlg_bilingual_subtitles"))
        self.bilingual_overlay_check.setChecked(False)
        self.bilingual_overlay_check.setToolTip(tr("audio_dlg_bilingual_tooltip"))
        self.bilingual_overlay_check.toggled.connect(self._on_bilingual_toggled)
        layout.addWidget(self.bilingual_overlay_check)

        export_layout = QHBoxLayout()
        self.export_transcript_btn = QPushButton(tr("audio_dlg_export_transcript"))
        self.export_transcript_btn.setToolTip(tr("audio_dlg_export_tooltip"))
        self.export_transcript_btn.clicked.connect(self._export_transcript)
        export_layout.addWidget(self.export_transcript_btn)
        export_layout.addStretch()
        layout.addLayout(export_layout)

        return group

    def _create_transcript_section(self) -> QGroupBox:
        """Create live transcript section"""
        group = QGroupBox(tr("audio_dlg_live_transcript"))
        layout = QVBoxLayout(group)

        self.transcript_display = QTextEdit()
        self.transcript_display.setReadOnly(True)
        self.transcript_display.setMaximumHeight(150)
        self.transcript_display.setPlaceholderText(tr("transcriptions_and_translations_will_appear_here"))
        layout.addWidget(self.transcript_display)

        return group

    def _create_statistics_section(self) -> QGroupBox:
        """Create statistics section"""
        group = QGroupBox(tr("audio_dlg_statistics"))
        layout = QGridLayout(group)

        layout.addWidget(QLabel(tr("transcriptions")), 0, 0)
        self.transcriptions_label = QLabel("0")
        layout.addWidget(self.transcriptions_label, 0, 1)

        layout.addWidget(QLabel(tr("translations")), 0, 2)
        self.translations_label = QLabel("0")
        layout.addWidget(self.translations_label, 0, 3)

        layout.addWidget(QLabel(tr("speeches")), 0, 4)
        self.speeches_label = QLabel("0")
        layout.addWidget(self.speeches_label, 0, 5)

        layout.addWidget(QLabel(tr("status")), 1, 0)
        self.status_label = QLabel(tr("audio_dlg_idle"))
        self.status_label.setStyleSheet("font-weight: bold;")
        layout.addWidget(self.status_label, 1, 1, 1, 5)

        return group

    # ------------------------------------------------------------------
    # Settings persistence
    # ------------------------------------------------------------------

    def load_settings(self):
        """Load settings from config"""
        config = self.config_manager.get_setting('plugins.audio_translation', {})

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

        self.bidirectional_check.setChecked(config.get('bidirectional', True))
        self.whisper_model_combo.setCurrentText(config.get('whisper_model', 'base'))
        self.gpu_check.setChecked(config.get('use_gpu', True))
        self.vad_check.setChecked(config.get('vad_enabled', True))
        self.parallel_check.setChecked(config.get('parallel_processing', False))
        self.auto_detect_check.setChecked(config.get('auto_detect_language', False))

        voice_id = config.get('voice_id', None)
        if voice_id:
            for i in range(self.voice_combo.count()):
                if self.voice_combo.itemData(i) == voice_id:
                    self.voice_combo.setCurrentIndex(i)
                    break
        self.speed_slider.setValue(config.get('tts_speed', 170))

        self.input_volume_slider.setValue(config.get('input_volume', 100))
        self.output_volume_slider.setValue(config.get('output_volume', 100))

        self.duck_check.setChecked(config.get('duck_enabled', True))
        self.duck_level_slider.setValue(config.get('duck_level', 20))

        self.youtube_url_input.setText(config.get('youtube_url', ''))
        self.overlay_check.setChecked(config.get('show_subtitle_overlay', False))
        self.subtitle_font_slider.setValue(config.get('subtitle_font_size', 24))
        self.bilingual_overlay_check.setChecked(config.get('bilingual_subtitles', False))

        loopback_dev = config.get('loopback_device', None)

        self.refresh_devices()
        self.refresh_loopback_devices()

        if loopback_dev is not None:
            idx = self.loopback_device_combo.findData(loopback_dev)
            if idx >= 0:
                self.loopback_device_combo.setCurrentIndex(idx)

    def save_settings(self):
        """Save settings to config"""
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
            'bilingual_subtitles': self.bilingual_overlay_check.isChecked(),
        }

        self.config_manager.set_setting('plugins.audio_translation', config)
        self.config_manager.save_config()

    # ------------------------------------------------------------------
    # Device enumeration (standalone, no plugin dependency)
    # ------------------------------------------------------------------

    def refresh_devices(self):
        """Refresh audio device list using PyAudio directly."""
        try:
            import pyaudio
        except ImportError:
            logger.debug("pyaudio not installed, cannot enumerate audio devices")
            return

        pa = None
        try:
            pa = pyaudio.PyAudio()

            self.input_device_combo.clear()
            self.input_device_combo.addItem(tr("audio_dlg_default_microphone"), None)

            self.output_device_combo.clear()
            self.output_device_combo.addItem(tr("audio_dlg_default_speaker"), None)

            for i in range(pa.get_device_count()):
                info = pa.get_device_info_by_index(i)
                if info['maxInputChannels'] > 0:
                    self.input_device_combo.addItem(
                        f"{info['name']} (#{i})", i
                    )
                if info['maxOutputChannels'] > 0:
                    self.output_device_combo.addItem(
                        f"{info['name']} (#{i})", i
                    )
        except Exception as e:
            logger.warning("Failed to refresh audio devices: %s", e)
        finally:
            if pa is not None:
                try:
                    pa.terminate()
                except Exception:
                    pass

    # ------------------------------------------------------------------
    # Pipeline lifecycle
    # ------------------------------------------------------------------

    def _build_audio_config(self) -> dict:
        """Collect current UI settings into a dict for the audio stages."""
        return {
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
            'bilingual_subtitles': self.bilingual_overlay_check.isChecked(),
        }

    def start_translation(self):
        """Create an audio pipeline via PipelineFactory and start it."""
        if not self.pipeline_factory:
            QMessageBox.warning(
                self,
                tr("audio_dlg_factory_not_available"),
                tr("audio_dlg_factory_not_initialized"),
            )
            return

        self.save_settings()
        audio_config = self._build_audio_config()

        if audio_config.get('audio_source_mode') == 'youtube':
            if not audio_config.get('youtube_url'):
                QMessageBox.warning(
                    self, tr("audio_dlg_error"), tr("audio_dlg_enter_youtube_url")
                )
                return

        self._accumulated_segments = []

        try:
            self._pipeline = self.pipeline_factory.create(
                "audio",
                translation_layer=self.translation_layer,
                audio_config=audio_config,
            )

            self._pipeline.on_translation = (
                lambda data: self._translationReceived.emit(data)
            )
            self._pipeline.on_error = (
                lambda msg: self._errorReceived.emit(msg)
            )
            self._pipeline.on_state_change = (
                lambda _old, new: self._pipelineStateChanged.emit(new.value)
            )

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
                self.status_label.setStyleSheet("font-weight: bold; color: #4CAF50;")
                self.transcript_display.append(
                    tr("audio_dlg_translation_started")
                )

                if self.overlay_check.isChecked():
                    self._ensure_subtitle_overlay()

                self.translationStarted.emit()
            else:
                QMessageBox.critical(
                    self,
                    tr("audio_dlg_start_failed"),
                    tr("audio_dlg_start_failed_msg"),
                )
        except Exception as e:
            logger.error("Failed to create audio pipeline: %s", e, exc_info=True)
            QMessageBox.critical(
                self,
                tr("audio_dlg_pipeline_error"),
                tr("audio_dlg_pipeline_error_msg").format(error=e),
            )

    def stop_translation(self):
        """Stop and clean up the audio pipeline."""
        self._destroy_subtitle_overlay()

        if self._pipeline is not None:
            self._pipeline.cleanup()
            self._pipeline = None

        self.is_active = False
        self.start_btn.setEnabled(True)
        self.pause_btn.setEnabled(False)
        self.pause_btn.setText(tr("audio_dlg_pause"))
        self.stop_btn.setEnabled(False)
        self.status_label.setText(tr("idle"))
        self.status_label.setStyleSheet("font-weight: bold; color: #666;")

        self.transcript_display.append(tr("audio_dlg_translation_stopped"))
        self.translationStopped.emit()

    def pause_translation(self):
        """Toggle pause/resume on the audio pipeline."""
        if self._pipeline is None:
            return

        from app.workflow.pipeline.types import PipelineState

        if self._pipeline.state == PipelineState.RUNNING:
            self._pipeline.pause()
            self.pause_btn.setText(tr("audio_dlg_resume"))
            self.status_label.setText(tr("audio_dlg_paused_status"))
            self.status_label.setStyleSheet("font-weight: bold; color: #FF9800;")
            self.transcript_display.append(tr("audio_dlg_paused_msg"))
        elif self._pipeline.state == PipelineState.PAUSED:
            self._pipeline.resume()
            self.pause_btn.setText(tr("audio_dlg_pause"))
            self.status_label.setText(tr("active_listening"))
            self.status_label.setStyleSheet("font-weight: bold; color: #4CAF50;")
            self.transcript_display.append(tr("audio_dlg_resumed_msg"))

    # ------------------------------------------------------------------
    # Pipeline callbacks (marshalled to Qt thread via signals)
    # ------------------------------------------------------------------

    def _handle_translation(self, data: dict):
        """Process a completed pipeline frame result."""
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
            self.transcript_display.append(f"🎤 [{detected}] {transcribed}")
        if translated:
            target = data.get("target_language", "?")
            self.transcript_display.append(f"🌍 [{target}] {translated}")

        if translated and self._subtitle_overlay is not None:
            self._subtitle_overlay.show_subtitle(translated, transcribed)

    def _handle_error(self, message: str):
        """Display a pipeline error in the transcript."""
        self.transcript_display.append(f"⚠️ {message}")

    def _handle_state_change(self, state_str: str):
        """React to pipeline state transitions (e.g. auto-stop on errors)."""
        if state_str == "error":
            self.is_active = False
            self.start_btn.setEnabled(True)
            self.pause_btn.setEnabled(False)
            self.pause_btn.setText(tr("audio_dlg_pause"))
            self.stop_btn.setEnabled(False)
            self.status_label.setText(tr("audio_dlg_error_stopped"))
            self.status_label.setStyleSheet("font-weight: bold; color: #f44336;")
            self.transcript_display.append(tr("audio_dlg_error_stopped_msg"))

    # ------------------------------------------------------------------
    # Statistics
    # ------------------------------------------------------------------

    def update_statistics(self):
        """Update statistics display from locally tracked counters."""
        self.transcriptions_label.setText(str(self._audio_stats.get("transcriptions", 0)))
        self.translations_label.setText(str(self._audio_stats.get("translations", 0)))
        self.speeches_label.setText(str(self._audio_stats.get("speeches", 0)))

    def _export_transcript(self):
        """Export accumulated transcript segments to SRT or text file."""
        if not self._accumulated_segments:
            QMessageBox.information(
                self, tr("audio_dlg_no_transcript_data"),
                tr("audio_dlg_no_transcript_data_msg")
            )
            return

        file_path, _ = QFileDialog.getSaveFileName(
            self,
            tr("audio_dlg_export_transcript"),
            "",
            "SRT Subtitle (*.srt);;Text File (*.txt);;All Files (*)"
        )
        if not file_path:
            return

        try:
            from plugins.enhancers.audio_translation.transcript_exporter import (
                TranscriptExporter,
            )
            exporter = TranscriptExporter()
            if file_path.endswith(".srt"):
                exporter.export_dual_srt(self._accumulated_segments, file_path)
            else:
                exporter.export_text(self._accumulated_segments, file_path)
            QMessageBox.information(
                self, tr("audio_dlg_export_success"),
                tr("audio_dlg_export_success_msg").format(path=file_path)
            )
        except ImportError:
            self._export_transcript_fallback(file_path)
        except Exception as e:
            QMessageBox.critical(self, tr("audio_dlg_error"), str(e))

    def _export_transcript_fallback(self, file_path: str):
        """Plain-text fallback when TranscriptExporter is not available."""
        try:
            with open(file_path, "w", encoding="utf-8") as f:
                for seg in self._accumulated_segments:
                    original = seg.get("transcribed_text", "")
                    translated = seg.get("translated_text", "")
                    if original:
                        f.write(f"{original}\n")
                    if translated:
                        f.write(f"  → {translated}\n")
                    f.write("\n")
            QMessageBox.information(
                self, tr("audio_dlg_export_success"),
                tr("audio_dlg_export_success_msg").format(path=file_path)
            )
        except Exception as e:
            QMessageBox.critical(self, tr("audio_dlg_error"), str(e))

    # ------------------------------------------------------------------
    # Cleanup
    # ------------------------------------------------------------------

    def closeEvent(self, event):
        """Handle dialog close"""
        self.update_timer.stop()
        if self.is_active:
            reply = QMessageBox.question(
                self,
                tr("audio_dlg_translation_active"),
                tr("audio_dlg_stop_and_close"),
                QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
            )

            if reply == QMessageBox.StandardButton.Yes:
                self.stop_translation()
                event.accept()
            else:
                event.ignore()
        else:
            self._destroy_subtitle_overlay()
            if self._pipeline is not None:
                self._pipeline.cleanup()
                self._pipeline = None
            event.accept()
