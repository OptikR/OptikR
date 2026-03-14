"""
Audio Translation Section

Real-time audio translation configuration: Speech-to-Text, Translation,
Text-to-Speech.  Displayed as a dedicated tab in the pipeline management UI.
"""

import logging

from PyQt6.QtWidgets import (
    QGroupBox, QLabel, QPushButton, QCheckBox, QFormLayout, QComboBox,
)
from PyQt6.QtCore import pyqtSignal
from ui.common.widgets.custom_spinbox import CustomSpinBox, CustomDoubleSpinBox

from app.localization import TranslatableMixin

logger = logging.getLogger(__name__)


class AudioTranslationSection(TranslatableMixin, QGroupBox):
    """Audio translation configuration section."""

    settingChanged = pyqtSignal()

    def __init__(self, parent=None):
        super().__init__(parent)
        self.set_translatable_text(
            self,
            "pipeline_management_audio_translation_section")
        self._init_ui()

    def _init_ui(self):
        layout = QFormLayout(self)

        # Enabled checkbox
        self.audio_plugin_enabled = QCheckBox()
        self.set_translatable_text(
            self.audio_plugin_enabled,
            "pipeline_management_enabled_check_19")
        self.audio_plugin_enabled.setChecked(False)
        self.audio_plugin_enabled.stateChanged.connect(
            self.settingChanged.emit)
        layout.addRow("Status:", self.audio_plugin_enabled)

        desc = QLabel(
            "Real-time audio translation: "
            "Speech-to-Text \u2192 Translation \u2192 Text-to-Speech")
        desc.setWordWrap(True)
        desc.setStyleSheet("color: #666666; font-size: 8pt;")
        layout.addRow("", desc)

        # Audio mode toggle
        self.audio_mode = QCheckBox()
        self.set_translatable_text(
            self.audio_mode,
            "pipeline_management_enable_audio_translation_mode_check")
        self.audio_mode.setChecked(False)
        self.audio_mode.stateChanged.connect(
            self.settingChanged.emit)
        layout.addRow("", self.audio_mode)

        # Whisper model
        self.audio_whisper_model = QComboBox()
        self.audio_whisper_model.addItems(
            ["tiny", "base", "small", "medium", "large"])
        self.audio_whisper_model.setCurrentText("base")
        self.audio_whisper_model.currentTextChanged.connect(
            self.settingChanged.emit)
        layout.addRow("Whisper Model:", self.audio_whisper_model)

        # TTS engine
        self.audio_tts_engine = QComboBox()
        self.audio_tts_engine.addItems(["coqui", "system"])
        self.audio_tts_engine.setCurrentText("coqui")
        self.audio_tts_engine.currentTextChanged.connect(
            self.settingChanged.emit)
        layout.addRow("TTS Engine:", self.audio_tts_engine)

        # Auto-play
        self.audio_auto_play = QCheckBox()
        self.set_translatable_text(
            self.audio_auto_play,
            "pipeline_management_automatically_play_translated_audio_check")
        self.audio_auto_play.setChecked(True)
        self.audio_auto_play.stateChanged.connect(
            self.settingChanged.emit)
        layout.addRow("", self.audio_auto_play)

        # Voice speed
        self.audio_voice_speed = CustomDoubleSpinBox()
        self.audio_voice_speed.setRange(0.5, 2.0)
        self.audio_voice_speed.setSingleStep(0.1)
        self.audio_voice_speed.setValue(1.0)
        self.audio_voice_speed.valueChanged.connect(
            self.settingChanged.emit)
        layout.addRow("Voice Speed:", self.audio_voice_speed)

        # Microphone device
        self.audio_mic_device = CustomSpinBox()
        self.audio_mic_device.setRange(-1, 10)
        self.audio_mic_device.setValue(-1)
        self.audio_mic_device.setSuffix(" (default)")
        self.audio_mic_device.valueChanged.connect(
            self.settingChanged.emit)
        layout.addRow("Microphone Device:", self.audio_mic_device)

        # Speaker device
        self.audio_speaker_device = CustomSpinBox()
        self.audio_speaker_device.setRange(-1, 10)
        self.audio_speaker_device.setValue(-1)
        self.audio_speaker_device.setSuffix(" (default)")
        self.audio_speaker_device.valueChanged.connect(
            self.settingChanged.emit)
        layout.addRow("Speaker Device:", self.audio_speaker_device)

        # VAD sensitivity
        self.audio_vad_sensitivity = CustomSpinBox()
        self.audio_vad_sensitivity.setRange(0, 3)
        self.audio_vad_sensitivity.setValue(2)
        self.audio_vad_sensitivity.valueChanged.connect(
            self.settingChanged.emit)
        layout.addRow("VAD Sensitivity:", self.audio_vad_sensitivity)

        # GPU toggle
        self.audio_use_gpu = QCheckBox()
        self.set_translatable_text(
            self.audio_use_gpu,
            "pipeline_management_use_gpu_acceleration_3-5x_faster_check")
        self.audio_use_gpu.setChecked(True)
        self.audio_use_gpu.stateChanged.connect(
            self.settingChanged.emit)
        layout.addRow("", self.audio_use_gpu)

        note = QLabel(
            "\U0001f4a1 Perfect for real-time meeting translation "
            "(German \u2194 Japanese)")
        note.setStyleSheet(
            "color: #2196F3; font-size: 8pt; font-style: italic;")
        layout.addRow("", note)

        install_note = QLabel(
            "\U0001f4e6 Requires: pip install openai-whisper TTS pyaudio "
            "webrtcvad sounddevice")
        install_note.setStyleSheet(
            "color: #FF9800; font-size: 8pt; font-style: italic;")
        layout.addRow("", install_note)

        # Start Audio Translation button
        self.start_audio_btn = QPushButton()
        self.set_translatable_text(
            self.start_audio_btn,
            "pipeline_management_open_bidirectional_audio_translation_button")
        self.start_audio_btn.setStyleSheet("""
            QPushButton {
                background-color: #2196F3;
                color: white;
                padding: 8px;
                border-radius: 4px;
                font-weight: bold;
            }
            QPushButton:hover {
                background-color: #1976D2;
            }
        """)
        layout.addRow("", self.start_audio_btn)
