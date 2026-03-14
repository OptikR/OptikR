"""
Multilingual model download — NLLB, M2M-100, mBART.
"""

from PyQt6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QComboBox, QMessageBox, QGroupBox, QFormLayout, QProgressDialog
)
from PyQt6.QtCore import Qt, QTimer
import threading


class MultilingualMixin:
    """NLLB / M2M-100 / mBART download logic."""

    def show_multilingual_model_downloader(self, manager, model_type="nllb"):
        """Show dialog to download multilingual models (NLLB, M2M-100, mBART).

        Args:
            manager: UniversalModelManager instance
            model_type: Type of model ("nllb", "m2m100", "mbart")
        """
        dialog = QDialog(self.parent)
        dialog.setWindowTitle(f"📦 Download {model_type.upper()} Model")
        dialog.setMinimumSize(600, 500)

        layout = QVBoxLayout(dialog)
        layout.setContentsMargins(20, 20, 20, 20)
        layout.setSpacing(15)

        model_names = {
            "nllb": "NLLB-200 (Meta AI)",
            "m2m100": "M2M-100 (Facebook)",
            "mbart": "mBART (Facebook)"
        }
        title = QLabel(f"Download {model_names.get(model_type, model_type.upper())} Model")
        title.setStyleSheet("font-size: 12pt; font-weight: bold;")
        layout.addWidget(title)

        descriptions = {
            "nllb": "No Language Left Behind supports 200+ languages with high quality translation.",
            "m2m100": "Many-to-Many translation supports 100 languages with direct translation.",
            "mbart": "Multilingual BART supports 50 languages with excellent quality."
        }
        desc = QLabel(descriptions.get(model_type, "Multilingual translation model."))
        desc.setWordWrap(True)
        desc.setStyleSheet("color: #666666; font-size: 9pt; margin-bottom: 10px;")
        layout.addWidget(desc)

        # Model size selector
        if model_type == "nllb":
            size_group = QGroupBox("Model Size")
            size_layout = QVBoxLayout()

            size_combo = QComboBox()
            size_combo.addItem("600MB - Distilled (Fast, Good Quality)", "nllb-200-distilled-600M")
            size_combo.addItem("1.3GB - Standard (Balanced)", "nllb-200-1.3B")
            size_combo.addItem("3.3GB - Large (Best Quality)", "nllb-200-3.3B")
            size_layout.addWidget(size_combo)

            size_group.setLayout(size_layout)
            layout.addWidget(size_group)
        elif model_type == "m2m100":
            size_group = QGroupBox("Model Size")
            size_layout = QVBoxLayout()

            size_combo = QComboBox()
            size_combo.addItem("418MB - Small (Fast)", "m2m100_418M")
            size_combo.addItem("1.2GB - Large (Better Quality)", "m2m100_1.2B")
            size_layout.addWidget(size_combo)

            size_group.setLayout(size_layout)
            layout.addWidget(size_group)
        else:  # mbart
            size_combo = QComboBox()
            size_combo.addItem("2.4GB - Large (Excellent Quality)", "mbart-large-50-many-to-many-mmt")
            size_combo.setVisible(False)

        # Language pair selector
        lang_group = QGroupBox("Language Pair")
        lang_layout = QFormLayout()

        languages = manager.get_supported_languages(model_type)

        source_combo = QComboBox()
        for code, name in languages:
            source_combo.addItem(f"{name} ({code})", code)

        target_combo = QComboBox()
        for code, name in languages:
            target_combo.addItem(f"{name} ({code})", code)

        source_combo.setCurrentIndex(0)
        target_combo.setCurrentIndex(1 if len(languages) > 1 else 0)

        # Try to default to the user's current config language pair
        config_mgr = getattr(self, 'config_manager', None) or getattr(self, 'parent', lambda: None)
        if hasattr(config_mgr, 'config_manager'):
            config_mgr = config_mgr.config_manager
        if config_mgr and hasattr(config_mgr, 'get_setting'):
            cfg_src = config_mgr.get_setting('translation.source_language', '')
            cfg_tgt = config_mgr.get_setting('translation.target_language', '')
            for i in range(source_combo.count()):
                if source_combo.itemData(i) == cfg_src:
                    source_combo.setCurrentIndex(i)
                    break
            for i in range(target_combo.count()):
                if target_combo.itemData(i) == cfg_tgt:
                    target_combo.setCurrentIndex(i)
                    break

        lang_layout.addRow("Source Language:", source_combo)
        lang_layout.addRow("Target Language:", target_combo)

        lang_group.setLayout(lang_layout)
        layout.addWidget(lang_group)

        info_label = QLabel("ℹ️ The model will be downloaded from HuggingFace and a plugin will be auto-generated.")
        info_label.setWordWrap(True)
        info_label.setStyleSheet("color: #4A9EFF; font-size: 9pt; padding: 10px; background-color: rgba(74, 158, 255, 0.1); border-radius: 5px;")
        layout.addWidget(info_label)

        button_layout = QHBoxLayout()
        button_layout.addStretch()

        cancel_btn = QPushButton("Cancel")
        cancel_btn.clicked.connect(dialog.reject)
        button_layout.addWidget(cancel_btn)

        download_btn = QPushButton("📦 Download Model + Generate Plugin")
        download_btn.setProperty("class", "action")
        download_btn.clicked.connect(lambda: self._start_multilingual_download(
            dialog, manager, model_type, size_combo, source_combo, target_combo
        ))
        button_layout.addWidget(download_btn)

        layout.addLayout(button_layout)

        dialog.exec()

    def _start_multilingual_download(self, dialog, manager, model_type, size_combo, source_combo, target_combo):
        """Start downloading a multilingual model."""
        model_name = size_combo.currentData()
        source_lang = source_combo.currentData()
        target_lang = target_combo.currentData()

        if source_lang == target_lang:
            QMessageBox.warning(
                dialog,
                "Invalid Selection",
                "Source and target languages must be different!"
            )
            return

        reply = QMessageBox.question(
            dialog,
            "Confirm Download",
            f"Download {model_name}?\n\n"
            f"Language Pair: {source_combo.currentText()} → {target_combo.currentText()}\n"
            f"Size: {size_combo.currentText().split(' - ')[0]}\n\n"
            f"This will download the model from HuggingFace and auto-generate a plugin.",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
        )

        if reply != QMessageBox.StandardButton.Yes:
            return

        progress = QProgressDialog(
            f"Downloading {model_name}...",
            "Cancel",
            0,
            100,
            dialog
        )
        progress.setWindowTitle("Downloading Model")
        progress.setWindowModality(Qt.WindowModality.WindowModal)
        progress.setMinimumDuration(0)
        progress.setValue(0)

        def progress_callback(value, message):
            """Update progress on main thread."""
            def _update():
                progress.setValue(int(value * 100))
                progress.setLabelText(message)
            QTimer.singleShot(0, _update)

        def download_thread():
            """Download in background thread."""
            try:
                success = manager.download_model(
                    model_name,
                    source_lang=source_lang,
                    target_lang=target_lang,
                    progress_callback=progress_callback,
                    auto_generate_plugin=True
                )

                def on_finished():
                    progress.close()
                    if success:
                        # Determine the plugin name (multilingual models use
                        # family-only names, not language-pair suffixes).
                        _MULTILINGUAL = {"nllb": "nllb200", "m2m100": "m2m100", "mbart": "mbart"}
                        plugin_name = _MULTILINGUAL.get(model_type, f"{model_type}_{source_lang}_{target_lang}")

                        # Update config so the app uses this engine + language pair
                        config_mgr = getattr(self, 'config_manager', None) or getattr(self, 'parent', lambda: None)
                        if hasattr(config_mgr, 'config_manager'):
                            config_mgr = config_mgr.config_manager
                        if config_mgr and hasattr(config_mgr, 'set_setting'):
                            config_mgr.set_setting('translation.engine', plugin_name)
                            config_mgr.set_setting('translation.source_language', source_lang)
                            config_mgr.set_setting('translation.target_language', target_lang)
                            # Store the HF repo so the plugin loads the right variant
                            hf_repo = f"facebook/{model_name}"
                            config_mgr.set_setting('translation.multilingual_model_name', hf_repo)
                            config_mgr.save_config()

                        QMessageBox.information(
                            dialog,
                            "Download Complete",
                            f"✅ Successfully downloaded {model_name}!\n\n"
                            f"Plugin: {plugin_name}\n"
                            f"Language pair set to: {source_lang} → {target_lang}\n\n"
                            f"Restart the app to use this engine."
                        )
                        dialog.accept()
                    else:
                        QMessageBox.critical(
                            dialog,
                            "Download Failed",
                            f"❌ Failed to download {model_name}.\n\nCheck logs for details."
                        )

                QTimer.singleShot(0, on_finished)
            except Exception as e:
                error_msg = str(e)
                QTimer.singleShot(0, lambda: (
                    progress.close(),
                    QMessageBox.critical(dialog, "Download Error", f"❌ Error downloading model:\n\n{error_msg}")
                ))

        thread = threading.Thread(target=download_thread, daemon=True)
        thread.start()
