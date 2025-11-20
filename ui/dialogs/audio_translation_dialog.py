"""
Real-Time Audio Translation Dialog

Simple UI for managing real-time audio translation for video calls.
Single PC setup: Microphone → Translation → Speaker

Author: Niklas Verhasselt
Date: 2025-11-18
"""

from PyQt6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QGroupBox, QLabel,
    QPushButton, QComboBox, QCheckBox, QTextEdit, QMessageBox,
    QGridLayout, QFrame
)
from PyQt6.QtCore import Qt, pyqtSignal, QTimer
from PyQt6.QtGui import QFont
from typing import Optional, Dict, Any


class AudioTranslationDialog(QDialog):
    """Dialog for real-time audio translation"""
    
    # Signals
    translationStarted = pyqtSignal()
    translationStopped = pyqtSignal()
    
    def __init__(self, config_manager, plugin_instance=None, parent=None):
        super().__init__(parent)
        self.config_manager = config_manager
        self.plugin = plugin_instance
        self.is_active = False
        
        self.setWindowTitle("Real-Time Audio Translation")
        self.setMinimumSize(700, 600)
        
        self.init_ui()
        self.load_settings()
        
        # Update timer for statistics
        self.update_timer = QTimer()
        self.update_timer.timeout.connect(self.update_statistics)
        self.update_timer.start(1000)
    
    def init_ui(self):
        """Initialize the user interface"""
        layout = QVBoxLayout(self)
        layout.setSpacing(15)
        
        # Title
        title = QLabel("🎤 Real-Time Audio Translation")
        title_font = QFont()
        title_font.setPointSize(14)
        title_font.setBold(True)
        title.setFont(title_font)
        layout.addWidget(title)
        
        # Description
        desc = QLabel(
            "Translate your voice in real-time for video calls (Zoom, Skype, Teams, etc.). "
            "Speak in your language, and the system will translate and output in the target language."
        )
        desc.setWordWrap(True)
        desc.setStyleSheet("color: #666; margin-bottom: 10px;")
        layout.addWidget(desc)
        
        # Device selection
        device_group = self._create_device_section()
        layout.addWidget(device_group)
        
        # Language settings
        lang_group = self._create_language_section()
        layout.addWidget(lang_group)
        
        # Advanced settings
        advanced_group = self._create_advanced_section()
        layout.addWidget(advanced_group)
        
        # Live transcript
        transcript_group = self._create_transcript_section()
        layout.addWidget(transcript_group)
        
        # Statistics
        stats_group = self._create_statistics_section()
        layout.addWidget(stats_group)
        
        # Control buttons
        button_layout = QHBoxLayout()
        button_layout.addStretch()
        
        self.start_btn = QPushButton("🎤 Start Translation")
        self.start_btn.clicked.connect(self.start_translation)
        self.start_btn.setMinimumWidth(150)
        self.start_btn.setStyleSheet("background-color: #4CAF50; color: white; font-weight: bold; padding: 8px;")
        button_layout.addWidget(self.start_btn)
        
        self.stop_btn = QPushButton("⏸️ Stop")
        self.stop_btn.clicked.connect(self.stop_translation)
        self.stop_btn.setEnabled(False)
        self.stop_btn.setMinimumWidth(150)
        self.stop_btn.setStyleSheet("background-color: #f44336; color: white; font-weight: bold; padding: 8px;")
        button_layout.addWidget(self.stop_btn)
        
        close_btn = QPushButton("Close")
        close_btn.clicked.connect(self.close)
        close_btn.setMinimumWidth(100)
        button_layout.addWidget(close_btn)
        
        layout.addLayout(button_layout)
    
    def _create_device_section(self) -> QGroupBox:
        """Create device selection section"""
        group = QGroupBox("🎧 Audio Devices")
        layout = QGridLayout(group)
        
        # Input device
        layout.addWidget(QLabel("Input (Microphone):"), 0, 0)
        self.input_device_combo = QComboBox()
        self.input_device_combo.addItem("Default Microphone", None)
        layout.addWidget(self.input_device_combo, 0, 1)
        
        refresh_input_btn = QPushButton("🔄")
        refresh_input_btn.setMaximumWidth(40)
        refresh_input_btn.clicked.connect(self.refresh_devices)
        layout.addWidget(refresh_input_btn, 0, 2)
        
        # Output device
        layout.addWidget(QLabel("Output (Speaker):"), 1, 0)
        self.output_device_combo = QComboBox()
        self.output_device_combo.addItem("Default Speaker", None)
        layout.addWidget(self.output_device_combo, 1, 1)
        
        refresh_output_btn = QPushButton("🔄")
        refresh_output_btn.setMaximumWidth(40)
        refresh_output_btn.clicked.connect(self.refresh_devices)
        layout.addWidget(refresh_output_btn, 1, 2)
        
        # Info
        info = QLabel("💡 Use the same device for calls (e.g., headset with mic)")
        info.setStyleSheet("color: #2196F3; font-size: 9pt; font-style: italic;")
        layout.addWidget(info, 2, 0, 1, 3)
        
        return group
    
    def _create_language_section(self) -> QGroupBox:
        """Create language settings section"""
        group = QGroupBox("🌍 Languages")
        layout = QGridLayout(group)
        
        # Source language
        layout.addWidget(QLabel("Your Language:"), 0, 0)
        self.source_lang_combo = QComboBox()
        self.source_lang_combo.addItems([
            "English (en)", "Japanese (ja)", "German (de)", "Spanish (es)",
            "French (fr)", "Chinese (zh)", "Korean (ko)", "Russian (ru)",
            "Italian (it)", "Portuguese (pt)"
        ])
        layout.addWidget(self.source_lang_combo, 0, 1)
        
        # Target language
        layout.addWidget(QLabel("Target Language:"), 1, 0)
        self.target_lang_combo = QComboBox()
        self.target_lang_combo.addItems([
            "Japanese (ja)", "English (en)", "German (de)", "Spanish (es)",
            "French (fr)", "Chinese (zh)", "Korean (ko)", "Russian (ru)",
            "Italian (it)", "Portuguese (pt)"
        ])
        layout.addWidget(self.target_lang_combo, 1, 1)
        
        # Bidirectional
        self.bidirectional_check = QCheckBox("Enable bidirectional translation (auto-detect both languages)")
        self.bidirectional_check.setChecked(True)
        layout.addWidget(self.bidirectional_check, 2, 0, 1, 2)
        
        return group
    
    def _create_advanced_section(self) -> QGroupBox:
        """Create advanced settings section"""
        group = QGroupBox("⚙️ Advanced Settings")
        layout = QGridLayout(group)
        
        # Whisper model
        layout.addWidget(QLabel("Whisper Model:"), 0, 0)
        self.whisper_model_combo = QComboBox()
        self.whisper_model_combo.addItems(["tiny", "base", "small", "medium", "large"])
        self.whisper_model_combo.setCurrentText("base")
        layout.addWidget(self.whisper_model_combo, 0, 1)
        
        model_info = QLabel("(larger = more accurate but slower)")
        model_info.setStyleSheet("color: #666; font-size: 8pt;")
        layout.addWidget(model_info, 0, 2)
        
        # GPU acceleration
        self.gpu_check = QCheckBox("Use GPU acceleration (3-5x faster)")
        self.gpu_check.setChecked(True)
        layout.addWidget(self.gpu_check, 1, 0, 1, 3)
        
        # VAD
        self.vad_check = QCheckBox("Enable Voice Activity Detection (reduces false transcriptions)")
        self.vad_check.setChecked(True)
        layout.addWidget(self.vad_check, 2, 0, 1, 3)
        
        return group
    
    def _create_transcript_section(self) -> QGroupBox:
        """Create live transcript section"""
        group = QGroupBox("📝 Live Transcript")
        layout = QVBoxLayout(group)
        
        self.transcript_display = QTextEdit()
        self.transcript_display.setReadOnly(True)
        self.transcript_display.setMaximumHeight(150)
        self.transcript_display.setPlaceholderText("Transcriptions and translations will appear here...")
        layout.addWidget(self.transcript_display)
        
        return group
    
    def _create_statistics_section(self) -> QGroupBox:
        """Create statistics section"""
        group = QGroupBox("📊 Statistics")
        layout = QGridLayout(group)
        
        layout.addWidget(QLabel("Transcriptions:"), 0, 0)
        self.transcriptions_label = QLabel("0")
        layout.addWidget(self.transcriptions_label, 0, 1)
        
        layout.addWidget(QLabel("Translations:"), 0, 2)
        self.translations_label = QLabel("0")
        layout.addWidget(self.translations_label, 0, 3)
        
        layout.addWidget(QLabel("Speeches:"), 0, 4)
        self.speeches_label = QLabel("0")
        layout.addWidget(self.speeches_label, 0, 5)
        
        layout.addWidget(QLabel("Status:"), 1, 0)
        self.status_label = QLabel("⚪ Idle")
        self.status_label.setStyleSheet("font-weight: bold;")
        layout.addWidget(self.status_label, 1, 1, 1, 5)
        
        return group
    
    def load_settings(self):
        """Load settings from config"""
        config = self.config_manager.get_setting('plugins.system_diagnostics', {})
        
        # Load language settings
        source_lang = config.get('source_language', 'en')
        target_lang = config.get('target_language', 'ja')
        
        # Set combo boxes
        for i in range(self.source_lang_combo.count()):
            if source_lang in self.source_lang_combo.itemText(i):
                self.source_lang_combo.setCurrentIndex(i)
                break
        
        for i in range(self.target_lang_combo.count()):
            if target_lang in self.target_lang_combo.itemText(i):
                self.target_lang_combo.setCurrentIndex(i)
                break
        
        # Load other settings
        self.bidirectional_check.setChecked(config.get('bidirectional', True))
        self.whisper_model_combo.setCurrentText(config.get('whisper_model', 'base'))
        self.gpu_check.setChecked(config.get('use_gpu', True))
        self.vad_check.setChecked(config.get('vad_enabled', True))
        
        # Refresh devices
        self.refresh_devices()
    
    def save_settings(self):
        """Save settings to config"""
        # Extract language codes from combo box text
        source_text = self.source_lang_combo.currentText()
        target_text = self.target_lang_combo.currentText()
        
        source_lang = source_text.split('(')[1].split(')')[0]
        target_lang = target_text.split('(')[1].split(')')[0]
        
        config = {
            'enabled': True,
            'input_device': self.input_device_combo.currentData(),
            'output_device': self.output_device_combo.currentData(),
            'source_language': source_lang,
            'target_language': target_lang,
            'bidirectional': self.bidirectional_check.isChecked(),
            'whisper_model': self.whisper_model_combo.currentText(),
            'use_gpu': self.gpu_check.isChecked(),
            'vad_enabled': self.vad_check.isChecked(),
            'vad_sensitivity': 2
        }
        
        self.config_manager.set_setting('plugins.system_diagnostics', config)
        self.config_manager.save_config()
    
    def refresh_devices(self):
        """Refresh audio device list"""
        if not self.plugin:
            return
        
        try:
            devices = self.plugin.list_audio_devices()
            
            # Clear and repopulate input devices
            self.input_device_combo.clear()
            self.input_device_combo.addItem("Default Microphone", None)
            
            for device in devices:
                if device['max_input_channels'] > 0:
                    self.input_device_combo.addItem(
                        f"{device['name']} (#{device['index']})",
                        device['index']
                    )
            
            # Clear and repopulate output devices
            self.output_device_combo.clear()
            self.output_device_combo.addItem("Default Speaker", None)
            
            for device in devices:
                if device['max_output_channels'] > 0:
                    self.output_device_combo.addItem(
                        f"{device['name']} (#{device['index']})",
                        device['index']
                    )
        
        except Exception as e:
            print(f"[AUDIO_TRANSLATION_UI] Failed to refresh devices: {e}")
    
    def start_translation(self):
        """Start real-time translation"""
        if not self.plugin:
            QMessageBox.warning(
                self,
                "Plugin Not Available",
                "Audio translation plugin is not initialized."
            )
            return
        
        # Save settings
        self.save_settings()
        
        # Start plugin
        if self.plugin.start():
            self.is_active = True
            self.start_btn.setEnabled(False)
            self.stop_btn.setEnabled(True)
            self.status_label.setText("🟢 Active - Listening...")
            self.status_label.setStyleSheet("font-weight: bold; color: #4CAF50;")
            
            self.transcript_display.append("🎤 Translation started. Speak into your microphone...\n")
            
            self.translationStarted.emit()
        else:
            QMessageBox.critical(
                self,
                "Start Failed",
                "Failed to start audio translation. Check console for errors."
            )
    
    def stop_translation(self):
        """Stop real-time translation"""
        if self.plugin:
            self.plugin.stop()
        
        self.is_active = False
        self.start_btn.setEnabled(True)
        self.stop_btn.setEnabled(False)
        self.status_label.setText("⚪ Idle")
        self.status_label.setStyleSheet("font-weight: bold; color: #666;")
        
        self.transcript_display.append("\n⏸️ Translation stopped.\n")
        
        self.translationStopped.emit()
    
    def update_statistics(self):
        """Update statistics display"""
        if not self.plugin:
            return
        
        try:
            stats = self.plugin.get_stats()
            
            self.transcriptions_label.setText(str(stats.get('transcriptions', 0)))
            self.translations_label.setText(str(stats.get('translations', 0)))
            self.speeches_label.setText(str(stats.get('speeches', 0)))
            
        except Exception as e:
            pass  # Silently fail
    
    def closeEvent(self, event):
        """Handle dialog close"""
        if self.is_active:
            reply = QMessageBox.question(
                self,
                "Translation Active",
                "Audio translation is still active. Stop and close?",
                QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
            )
            
            if reply == QMessageBox.StandardButton.Yes:
                self.stop_translation()
                event.accept()
            else:
                event.ignore()
        else:
            event.accept()


def show_audio_translation_dialog(config_manager, plugin_instance=None, parent=None):
    """Show the audio translation dialog"""
    dialog = AudioTranslationDialog(config_manager, plugin_instance, parent)
    dialog.exec()
