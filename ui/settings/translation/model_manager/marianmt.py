"""
MarianMT model management — download pairs, optimize, delete, add language pairs.
"""

from PyQt6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel, QPushButton, QListWidget,
    QComboBox, QMessageBox, QTreeWidget, QTreeWidgetItem, QWidget,
    QProgressDialog, QApplication, QListWidgetItem
)
from PyQt6.QtCore import Qt, QTimer
import threading
import json
from pathlib import Path
from datetime import datetime


class MarianMTMixin:
    """MarianMT pair download / optimize / delete / add logic."""

    def _create_available_models_tab(self, manager_ref, refresh_models_func=None):
        """Create the available models tab.

        Args:
            manager_ref: List containing the manager (allows updating the reference)
            refresh_models_func: List to store the refresh function
        """
        available_tab = QWidget()
        manager = manager_ref[0]
        available_layout = QVBoxLayout(available_tab)
        available_layout.setContentsMargins(10, 10, 10, 10)
        available_layout.setSpacing(10)

        # Filter controls
        filter_layout = QHBoxLayout()
        filter_layout.setSpacing(10)

        filter_layout.addWidget(QLabel("Source:"))
        source_combo = QComboBox()
        source_combo.addItems(["All", "en", "es", "fr", "de", "it", "ja", "zh", "ru"])
        filter_layout.addWidget(source_combo)

        filter_layout.addWidget(QLabel("Target:"))
        target_combo = QComboBox()
        target_combo.addItems(["All", "en", "es", "fr", "de", "it", "ja", "zh", "ru"])
        filter_layout.addWidget(target_combo)

        refresh_btn = QPushButton("🔄 Refresh")
        refresh_btn.setProperty("class", "action")
        filter_layout.addWidget(refresh_btn)

        filter_layout.addStretch()
        available_layout.addLayout(filter_layout)

        # Models tree
        models_tree = QTreeWidget()
        models_tree.setHeaderLabels(["Languages", "Model Name", "Size", "BLEU Score", "Status", "Optimized"])
        models_tree.setColumnWidth(0, 120)
        models_tree.setColumnWidth(1, 250)
        models_tree.setColumnWidth(2, 80)
        models_tree.setColumnWidth(3, 80)
        models_tree.setColumnWidth(4, 120)
        models_tree.setColumnWidth(5, 80)
        models_tree.setAlternatingRowColors(True)
        available_layout.addWidget(models_tree)
        optimize_btn_ref = [None]

        def refresh_models():
            """Refresh the models tree."""
            models_tree.clear()

            current_manager = manager_ref[0]

            src = None if source_combo.currentText() == "All" else source_combo.currentText()
            tgt = None if target_combo.currentText() == "All" else target_combo.currentText()
            models = current_manager.get_available_models(source_lang=src, target_lang=tgt)

            for model in models:
                status = "✓ Downloaded" if model.is_downloaded else "Available"
                optimized = "✓" if model.is_optimized else ""

                if model.source_language == "multilingual":
                    lang_display = f"Multilingual ({model.languages_count} languages)"
                else:
                    lang_display = f"{model.source_language.upper()} → {model.target_language.upper()}"

                item = QTreeWidgetItem([
                    lang_display,
                    model.model_name,
                    f"{model.size_mb} MB",
                    f"{model.accuracy_bleu:.1f}",
                    status,
                    optimized
                ])
                models_tree.addTopLevelItem(item)

            # Qwen3 models are causal LLMs; disable seq2seq-only optimization action.
            if optimize_btn_ref[0] is not None:
                optimize_btn_ref[0].setEnabled(current_manager.get_model_type() != "qwen3")

        refresh_btn.clicked.connect(refresh_models)
        source_combo.currentTextChanged.connect(refresh_models)
        target_combo.currentTextChanged.connect(refresh_models)

        if refresh_models_func is not None:
            refresh_models_func[0] = refresh_models
            refresh_models()

        # Action buttons
        action_layout = QHBoxLayout()
        action_layout.setSpacing(10)

        download_pairs_btn = QPushButton("📦 Download Model")
        download_pairs_btn.setProperty("class", "action")

        def on_download_click():
            """Handle download button click based on model type."""
            current = manager_ref[0]
            if current.get_model_type() == "marianmt":
                self._download_language_pairs(self.parent, current, refresh_models)
            elif current.get_model_type() in {"nllb", "m2m100", "mbart"}:
                self.show_multilingual_model_downloader(current, current.get_model_type())
                refresh_models()
            else:
                # For model types like Qwen3, download the selected row directly.
                self._download_selected_model(self.parent, current, models_tree, refresh_models)

        download_pairs_btn.clicked.connect(on_download_click)
        action_layout.addWidget(download_pairs_btn)

        download_selected_btn = QPushButton("⬇ Download Selected")
        download_selected_btn.setProperty("class", "action")
        download_selected_btn.clicked.connect(lambda: self._download_selected_model(self.parent, manager_ref[0], models_tree, refresh_models))
        action_layout.addWidget(download_selected_btn)

        optimize_btn = QPushButton("⚡ Optimize")
        optimize_btn.setProperty("class", "action")
        optimize_btn.clicked.connect(lambda: self._optimize_selected_model(self.parent, manager_ref[0], models_tree, refresh_models))
        action_layout.addWidget(optimize_btn)
        optimize_btn_ref[0] = optimize_btn

        delete_btn = QPushButton("🗑 Delete")
        delete_btn.setProperty("class", "action")
        delete_btn.clicked.connect(lambda: self._delete_selected_model(self.parent, manager_ref[0], models_tree, refresh_models))
        action_layout.addWidget(delete_btn)

        action_layout.addStretch()

        discover_btn = QPushButton("🔍 Discover Custom Models")
        discover_btn.setProperty("class", "action")
        discover_btn.setToolTip("Scan models folder for custom models and create plugins")
        discover_btn.clicked.connect(lambda: self._discover_custom_models(self.parent, manager_ref[0], refresh_models))
        action_layout.addWidget(discover_btn)

        available_layout.addLayout(action_layout)

        refresh_models()

        return available_tab

    # ------------------------------------------------------------------
    # MarianMT-specific download / batch download
    # ------------------------------------------------------------------

    def _download_language_pairs(self, parent_dialog, manager, refresh_callback):
        """Show dialog to select and download specific language pairs."""
        dialog = QDialog(parent_dialog)
        dialog.setWindowTitle("📦 Download Language Pairs")
        dialog.setMinimumSize(700, 600)

        layout = QVBoxLayout(dialog)
        layout.setContentsMargins(20, 20, 20, 20)
        layout.setSpacing(15)

        title = QLabel("Select Language Pairs to Download")
        title.setStyleSheet("font-size: 12pt; font-weight: bold;")
        layout.addWidget(title)

        desc = QLabel(
            "Select one or more language pairs to download from HuggingFace.\n"
            "Each model is approximately 280-330 MB."
        )
        desc.setWordWrap(True)
        desc.setStyleSheet("color: #666666; font-size: 9pt; margin-bottom: 10px;")
        layout.addWidget(desc)

        # Filter controls
        filter_layout = QHBoxLayout()
        filter_layout.addWidget(QLabel("Filter by source:"))
        source_filter = QComboBox()
        source_filter.addItems(["All", "en", "es", "fr", "de", "it", "ja", "zh", "ru", "ar", "nl", "pl", "tr", "ko", "pt"])
        filter_layout.addWidget(source_filter)

        filter_layout.addWidget(QLabel("Filter by target:"))
        target_filter = QComboBox()
        target_filter.addItems(["All", "en", "es", "fr", "de", "it", "ja", "zh", "ru", "ar", "nl", "pl", "tr", "ko", "pt"])
        filter_layout.addWidget(target_filter)

        filter_layout.addStretch()
        layout.addLayout(filter_layout)

        pairs_list = QListWidget()
        pairs_list.setSelectionMode(QListWidget.SelectionMode.MultiSelection)

        def populate_pairs():
            """Populate the pairs list based on filters."""
            pairs_list.clear()

            src_filter = None if source_filter.currentText() == "All" else source_filter.currentText()
            tgt_filter = None if target_filter.currentText() == "All" else target_filter.currentText()

            all_pairs = manager.get_language_pairs()

            for src, tgt, pair_desc in sorted(all_pairs, key=lambda x: x[2]):
                if src_filter and src != src_filter:
                    continue
                if tgt_filter and tgt != tgt_filter:
                    continue

                lang_pair = f"{src}-{tgt}"
                model_name = manager.AVAILABLE_MODELS.get(lang_pair, {}).get("name", "")
                is_downloaded = manager.is_model_downloaded(model_name)

                status = "✓ Downloaded" if is_downloaded else "Available"
                item_text = f"{pair_desc} ({src} → {tgt}) - {status}"

                item = QListWidgetItem(item_text)
                item.setData(Qt.ItemDataRole.UserRole, (src, tgt))

                if is_downloaded:
                    item.setForeground(Qt.GlobalColor.darkGray)

                pairs_list.addItem(item)

        source_filter.currentTextChanged.connect(populate_pairs)
        target_filter.currentTextChanged.connect(populate_pairs)

        layout.addWidget(pairs_list)

        info_label = QLabel("💡 Select multiple pairs and download them in batch")
        info_label.setStyleSheet("color: #666666; font-size: 8pt;")
        layout.addWidget(info_label)

        button_layout = QHBoxLayout()

        select_all_btn = QPushButton("Select All")
        select_all_btn.clicked.connect(pairs_list.selectAll)
        button_layout.addWidget(select_all_btn)

        deselect_all_btn = QPushButton("Deselect All")
        deselect_all_btn.clicked.connect(pairs_list.clearSelection)
        button_layout.addWidget(deselect_all_btn)

        button_layout.addStretch()

        cancel_btn = QPushButton("Cancel")
        cancel_btn.clicked.connect(dialog.reject)
        button_layout.addWidget(cancel_btn)

        download_btn = QPushButton("Download Selected")
        download_btn.setProperty("class", "action")
        download_btn.setDefault(True)
        download_btn.clicked.connect(lambda: self._start_batch_download(dialog, pairs_list, manager, refresh_callback))
        button_layout.addWidget(download_btn)

        layout.addLayout(button_layout)

        populate_pairs()

        dialog.exec()

    def _start_batch_download(self, dialog, pairs_list, manager, refresh_callback):
        """Start batch download of selected language pairs."""
        selected_items = pairs_list.selectedItems()

        if not selected_items:
            QMessageBox.warning(dialog, "No Selection", "Please select at least one language pair to download.")
            return

        pairs = []
        for item in selected_items:
            src, tgt = item.data(Qt.ItemDataRole.UserRole)
            pairs.append((src, tgt))

        total_size = len(pairs) * 300
        reply = QMessageBox.question(
            dialog,
            "Confirm Download",
            f"Download {len(pairs)} language pair(s)?\n\n"
            f"Approximate total size: {total_size} MB\n"
            f"This may take several minutes depending on your connection.\n\n"
            f"Continue?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
        )

        if reply != QMessageBox.StandardButton.Yes:
            return

        progress = QProgressDialog(
            "Downloading language pairs...",
            "Cancel",
            0,
            len(pairs),
            dialog
        )
        progress.setWindowTitle("Batch Download")
        progress.setWindowModality(Qt.WindowModality.WindowModal)
        progress.setMinimumDuration(0)
        progress.setValue(0)
        progress.show()
        QApplication.processEvents()

        def do_batch_download():
            try:
                results = {}
                for idx, (src, tgt) in enumerate(pairs):
                    cancelled = [False]
                    def check_cancel():
                        cancelled[0] = progress.wasCanceled()
                    QTimer.singleShot(0, check_cancel)
                    import time; time.sleep(0.05)
                    if cancelled[0]:
                        break

                    QTimer.singleShot(0, lambda s=src, t=tgt, i=idx: (
                        progress.setLabelText(f"Downloading {s} → {t}..."),
                        progress.setValue(i),
                    ))

                    lang_pair = f"{src}-{tgt}"
                    model_name = manager.AVAILABLE_MODELS.get(lang_pair, {}).get("name", "")

                    if model_name:
                        success = manager.download_model(model_name)
                        results[lang_pair] = success

                successful = sum(1 for v in results.values() if v)
                failed = len(results) - successful

                msg = f"Download complete!\n\n"
                msg += f"✓ Successful: {successful}\n"
                if failed > 0:
                    msg += f"✗ Failed: {failed}\n"

                def on_finished():
                    progress.setValue(len(pairs))
                    progress.close()
                    QMessageBox.information(dialog, "Download Complete", msg)
                    if refresh_callback:
                        refresh_callback()
                    dialog.accept()

                QTimer.singleShot(0, on_finished)

            except Exception as e:
                error_msg = str(e)
                QTimer.singleShot(0, lambda: (progress.close(), QMessageBox.critical(dialog, "Error", f"Batch download failed:\n{error_msg}")))

        threading.Thread(target=do_batch_download, daemon=True).start()

    # ------------------------------------------------------------------
    # Single model download / optimize / delete
    # ------------------------------------------------------------------

    def _download_selected_model(self, parent_dialog, manager, models_tree, refresh_callback):
        """Download the selected model."""
        selected_items = models_tree.selectedItems()
        if not selected_items:
            QMessageBox.warning(parent_dialog, "No Selection", "Please select a model to download.")
            return

        model_name = selected_items[0].text(1)

        progress = QProgressDialog(
            f"Downloading {model_name}...",
            None,
            0,
            0,
            parent_dialog
        )
        progress.setWindowTitle("Downloading Model")
        progress.setWindowModality(Qt.WindowModality.WindowModal)
        progress.setMinimumDuration(0)
        progress.setValue(0)
        progress.show()
        QApplication.processEvents()

        def do_download():
            try:
                success = manager.download_model(model_name)

                def on_finished():
                    progress.close()
                    if success:
                        QMessageBox.information(parent_dialog, "Success", f"Model {model_name} downloaded successfully!")
                        refresh_callback()
                    else:
                        QMessageBox.critical(parent_dialog, "Error", f"Failed to download model {model_name}")

                QTimer.singleShot(0, on_finished)
            except Exception as e:
                error_msg = str(e)
                QTimer.singleShot(0, lambda: (progress.close(), QMessageBox.critical(parent_dialog, "Error", f"Download failed:\n{error_msg}")))

        threading.Thread(target=do_download, daemon=True).start()

    def _optimize_selected_model(self, parent_dialog, manager, models_tree, refresh_callback):
        """Optimize the selected model."""
        selected_items = models_tree.selectedItems()
        if not selected_items:
            QMessageBox.warning(parent_dialog, "No Selection", "Please select a model to optimize.")
            return

        model_name = selected_items[0].text(1)

        if not manager.is_model_downloaded(model_name):
            QMessageBox.warning(parent_dialog, "Not Downloaded", "Please download the model first.")
            return

        progress = QProgressDialog(
            f"Optimizing {model_name}...",
            None,
            0,
            0,
            parent_dialog
        )
        progress.setWindowTitle("Optimizing Model")
        progress.setWindowModality(Qt.WindowModality.WindowModal)
        progress.setMinimumDuration(0)
        progress.setValue(0)
        progress.show()
        QApplication.processEvents()

        def do_optimize():
            try:
                result = manager.optimize_model(model_name)

                def on_finished():
                    progress.close()
                    if result.success:
                        msg = f"Model optimized successfully!\n\n"
                        msg += f"Size reduction: {result.original_size_mb:.1f}MB → {result.optimized_size_mb:.1f}MB\n"
                        msg += f"Speed improvement: {result.speed_improvement:.1f}x\n"
                        msg += f"Memory saved: {result.memory_reduction_mb:.1f}MB"
                        QMessageBox.information(parent_dialog, "Success", msg)
                        refresh_callback()
                    else:
                        QMessageBox.critical(parent_dialog, "Error", f"Optimization failed:\n{result.error_message}")

                QTimer.singleShot(0, on_finished)
            except Exception as e:
                error_msg = str(e)
                QTimer.singleShot(0, lambda: (progress.close(), QMessageBox.critical(parent_dialog, "Error", f"Optimization failed:\n{error_msg}")))

        threading.Thread(target=do_optimize, daemon=True).start()

    def _delete_selected_model(self, parent_dialog, manager, models_tree, refresh_callback):
        """Delete the selected model."""
        selected_items = models_tree.selectedItems()
        if not selected_items:
            QMessageBox.warning(parent_dialog, "No Selection", "Please select a model to delete.")
            return

        model_name = selected_items[0].text(1)

        if not manager.is_model_downloaded(model_name):
            QMessageBox.information(parent_dialog, "Not Downloaded", "This model is not downloaded.")
            return

        reply = QMessageBox.question(
            parent_dialog,
            "Confirm Delete",
            f"Delete model {model_name}?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            QMessageBox.StandardButton.No
        )

        if reply == QMessageBox.StandardButton.Yes:
            try:
                if manager.delete_model(model_name):
                    QMessageBox.information(parent_dialog, "Success", f"Model {model_name} deleted successfully!")
                    refresh_callback()
                else:
                    QMessageBox.critical(parent_dialog, "Error", "Failed to delete model")
            except Exception as e:
                QMessageBox.critical(parent_dialog, "Error", f"Delete failed:\n{str(e)}")

    # ------------------------------------------------------------------
    # Add language pair to configuration
    # ------------------------------------------------------------------

    def add_marianmt_language_pair(self, model_list_widget):
        """Show dialog to add a new MarianMT language pair."""
        dialog = QDialog(self.parent)
        dialog.setWindowTitle("➕ Add MarianMT Language Pair")
        dialog.setMinimumSize(600, 500)
        dialog.resize(600, 500)

        layout = QVBoxLayout(dialog)
        layout.setContentsMargins(20, 20, 20, 20)
        layout.setSpacing(15)

        title = QLabel("Select Language Pairs to Add")
        title.setStyleSheet("font-size: 12pt; font-weight: bold;")
        layout.addWidget(title)

        desc = QLabel(
            "Select one or more language pairs to add to your configuration.\n"
            "Only available MarianMT models are shown."
        )
        desc.setWordWrap(True)
        desc.setStyleSheet("color: #666666; font-size: 9pt; margin-bottom: 10px;")
        layout.addWidget(desc)

        current_pairs = set()
        for i in range(model_list_widget.count()):
            item_text = model_list_widget.item(i).text()
            if "(" in item_text and ")" in item_text:
                lang_code = item_text.split("(")[1].split(")")[0]
                current_pairs.add(lang_code)

        all_available_pairs = self._get_available_marianmt_pairs()

        available_pairs = {k: v for k, v in all_available_pairs.items() if k not in current_pairs}

        if not available_pairs:
            QMessageBox.information(
                dialog,
                "All Pairs Added",
                "All available MarianMT language pairs are already in your configuration!"
            )
            dialog.reject()
            return

        pair_list = QListWidget()
        pair_list.setSelectionMode(QListWidget.SelectionMode.MultiSelection)

        for lang_code, lang_name in sorted(available_pairs.items(), key=lambda x: x[1]):
            item_text = f"{lang_name} ({lang_code})"
            pair_list.addItem(item_text)

        layout.addWidget(pair_list)

        info_label = QLabel(f"💡 {len(available_pairs)} language pairs available to add")
        info_label.setStyleSheet("color: #666666; font-size: 8pt;")
        layout.addWidget(info_label)

        button_layout = QHBoxLayout()
        button_layout.addStretch()

        cancel_btn = QPushButton("Cancel")
        cancel_btn.clicked.connect(dialog.reject)
        button_layout.addWidget(cancel_btn)

        add_btn = QPushButton("Add Selected")
        add_btn.setProperty("class", "action")
        add_btn.setDefault(True)
        add_btn.clicked.connect(lambda: self._confirm_add_language_pairs(dialog, pair_list, available_pairs, model_list_widget))
        button_layout.addWidget(add_btn)

        layout.addLayout(button_layout)

        dialog.exec()

    def _confirm_add_language_pairs(self, dialog, pair_list, available_pairs, model_list_widget):
        """Confirm and add selected language pairs."""
        selected_items = pair_list.selectedItems()

        if not selected_items:
            QMessageBox.warning(dialog, "No Selection", "Please select at least one language pair to add.")
            return

        added_pairs = []
        for item in selected_items:
            item_text = item.text()
            if "(" in item_text and ")" in item_text:
                lang_code = item_text.split("(")[1].split(")")[0]
                lang_name = item_text.split(" (")[0]
                added_pairs.append((lang_code, lang_name))

        for lang_code, lang_name in added_pairs:
            model_list_widget.addItem(f"{lang_name} ({lang_code})")

        self._update_translation_config_with_new_pairs(added_pairs)

        QMessageBox.information(
            dialog,
            "Language Pairs Added",
            f"✅ Successfully added {len(added_pairs)} language pair(s)!"
        )

        dialog.accept()

    def _update_translation_config_with_new_pairs(self, new_pairs):
        """Update translation_config.json with new language pairs."""
        try:
            config_path = Path(__file__).parent.parent.parent.parent / 'config' / 'translation_config.json'

            if config_path.exists():
                with open(config_path, 'r', encoding='utf-8') as f:
                    config = json.load(f)

                if 'marianmt' not in config:
                    config['marianmt'] = {}
                if 'models' not in config['marianmt']:
                    config['marianmt']['models'] = {}

                for lang_code, lang_name in new_pairs:
                    config['marianmt']['models'][lang_code] = {
                        "model_name": f"opus-mt-{lang_code}",
                        "downloaded": False,
                        "optimized": False
                    }

                config['last_updated'] = datetime.now().isoformat()

                with open(config_path, 'w', encoding='utf-8') as f:
                    json.dump(config, f, indent=2, ensure_ascii=False)

                import logging
                logging.getLogger(__name__).info("Added %d language pairs to translation_config.json", len(new_pairs))
        except Exception as e:
            import logging
            logging.getLogger(__name__).error("Failed to update translation config: %s", e)

    def _get_available_marianmt_pairs(self):
        """Get all available MarianMT language pairs from the model catalog."""
        from app.core.model_catalog_metadata import BUILTIN_MODELS

        _names = {
            "en": "English", "de": "German", "es": "Spanish", "fr": "French",
            "it": "Italian", "pt": "Portuguese", "ja": "Japanese", "zh": "Chinese",
            "ko": "Korean", "ru": "Russian", "ar": "Arabic", "nl": "Dutch",
            "pl": "Polish", "tr": "Turkish",
        }

        pairs = {}
        for model_id, meta in BUILTIN_MODELS.items():
            if meta.family != "MarianMT":
                continue
            if len(meta.languages) >= 2:
                src, tgt = meta.languages[0], meta.languages[1]
                src_name = _names.get(src, src.upper())
                tgt_name = _names.get(tgt, tgt.upper())
                pairs[f"{src}-{tgt}"] = f"{src_name} \u2192 {tgt_name}"
        return pairs
