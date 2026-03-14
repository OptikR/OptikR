"""
Custom model discovery, registration, and plugin creation.
"""

from PyQt6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QComboBox, QMessageBox, QTreeWidget, QTreeWidgetItem,
    QGroupBox, QFormLayout, QInputDialog
)
from PyQt6.QtCore import Qt
from ui.common.widgets.custom_spinbox import CustomSpinBox, CustomDoubleSpinBox


class CustomModelsMixin:
    """Custom model discovery / registration / plugin generation."""

    def _discover_custom_models(self, parent_dialog, manager, refresh_callback):
        """Discover custom models in the models folder and create plugins for them."""
        dialog = QDialog(parent_dialog)
        dialog.setWindowTitle("🔍 Discover Custom Models")
        dialog.setMinimumSize(800, 600)

        layout = QVBoxLayout(dialog)
        layout.setContentsMargins(20, 20, 20, 20)
        layout.setSpacing(15)

        title = QLabel("Discover Custom Translation Models")
        title.setStyleSheet("font-size: 12pt; font-weight: bold;")
        layout.addWidget(title)

        current_type = manager.get_model_type()

        desc = QLabel(
            "This tool scans your models folder for custom translation models and creates plugins for them.\n\n"
            f"📁 Models folder: {manager.cache_dir}\n"
            f"📁 Current model type: {current_type.upper()}\n\n"
            "To add a custom model:\n"
            f"1. Place your model folder in: {manager.cache_dir}/your-model-name/\n"
            "2. Model folder must contain: config.json, pytorch_model.bin (or model.safetensors)\n"
            "3. Click 'Scan for Models' below\n"
            "4. Select the model and provide language pair information\n"
            "5. Plugin will be auto-generated!"
        )
        desc.setWordWrap(True)
        desc.setStyleSheet("color: #666666; font-size: 9pt; padding: 10px; background-color: rgba(100, 100, 100, 0.1); border-radius: 5px;")
        layout.addWidget(desc)

        scan_btn = QPushButton("🔍 Scan for Models")
        scan_btn.setProperty("class", "action")
        layout.addWidget(scan_btn)

        models_tree = QTreeWidget()
        models_tree.setHeaderLabels(["Model Folder", "Has Config", "Has Weights", "Status"])
        models_tree.setColumnWidth(0, 300)
        models_tree.setColumnWidth(1, 100)
        models_tree.setColumnWidth(2, 100)
        models_tree.setColumnWidth(3, 200)
        models_tree.setAlternatingRowColors(True)
        layout.addWidget(models_tree)

        def scan_for_models():
            """Scan the models folder for custom models using discover_models()."""
            models_tree.clear()

            if not manager.cache_dir.exists():
                QMessageBox.warning(
                    dialog,
                    "Folder Not Found",
                    f"Models folder not found:\n{manager.cache_dir}\n\n"
                    f"You can manually add models to this folder."
                )
                return

            try:
                unregistered_models = manager.discover_models()
                registered_models = list(manager.registry.get("models", {}).keys())

                discovered = []

                for model_name in unregistered_models:
                    model_path = manager.cache_dir / model_name
                    has_config = (model_path / "config.json").exists()
                    has_weights = (
                        (model_path / "pytorch_model.bin").exists() or
                        (model_path / "model.safetensors").exists()
                    )
                    discovered.append((model_name, has_config, has_weights, "⚠️ Not Registered", False))

                for model_name in registered_models:
                    model_path = manager.cache_dir / model_name
                    if model_path.exists():
                        has_config = (model_path / "config.json").exists()
                        has_weights = (
                            (model_path / "pytorch_model.bin").exists() or
                            (model_path / "model.safetensors").exists()
                        )
                        discovered.append((model_name, has_config, has_weights, "✓ Registered", True))

                if not discovered:
                    item = QTreeWidgetItem(["No models found", "", "", ""])
                    item.setForeground(0, Qt.GlobalColor.darkGray)
                    models_tree.addTopLevelItem(item)

                    QMessageBox.information(
                        dialog,
                        "No Models Found",
                        f"No models found in:\n{manager.cache_dir}\n\n"
                        f"To add models manually:\n"
                        f"1. Download a HuggingFace model\n"
                        f"2. Place it in the models folder\n"
                        f"3. Click 'Scan for Models' again\n"
                        f"4. Register and create plugin"
                    )
                else:
                    for model_name, has_config, has_weights, status, is_registered in discovered:
                        item = QTreeWidgetItem([
                            model_name,
                            "✓" if has_config else "✗",
                            "✓" if has_weights else "✗",
                            status
                        ])

                        if is_registered:
                            item.setForeground(0, Qt.GlobalColor.darkGray)
                        else:
                            item.setForeground(3, Qt.GlobalColor.red)

                        models_tree.addTopLevelItem(item)

                    unregistered_count = len(unregistered_models)
                    if unregistered_count > 0:
                        QMessageBox.information(
                            dialog,
                            "Models Found",
                            f"Found {len(discovered)} total model(s):\n"
                            f"• {len(registered_models)} registered\n"
                            f"• {unregistered_count} unregistered\n\n"
                            f"Select an unregistered model and click 'Register Model' to add it."
                        )
                    else:
                        QMessageBox.information(
                            dialog,
                            "Scan Complete",
                            f"Found {len(discovered)} model(s) - all registered.\n\n"
                            f"You can create plugins for registered models."
                        )

            except Exception as e:
                QMessageBox.critical(
                    dialog,
                    "Scan Failed",
                    f"Failed to scan for models:\n{str(e)}"
                )

        scan_btn.clicked.connect(scan_for_models)

        # Action buttons
        button_layout = QHBoxLayout()

        register_btn = QPushButton("📝 Register Selected Model")
        register_btn.setProperty("class", "action")
        register_btn.setToolTip("Register an unregistered model in the registry")
        register_btn.clicked.connect(lambda: self._register_custom_model(
            dialog, manager, models_tree, scan_for_models
        ))
        button_layout.addWidget(register_btn)

        create_plugin_btn = QPushButton("🔌 Create Plugin for Selected")
        create_plugin_btn.setProperty("class", "action")
        create_plugin_btn.setToolTip("Generate a plugin for a registered model")
        create_plugin_btn.clicked.connect(lambda: self._create_plugin_for_custom_model(
            dialog, manager, models_tree, refresh_callback
        ))
        button_layout.addWidget(create_plugin_btn)

        button_layout.addStretch()

        close_btn = QPushButton("Close")
        close_btn.clicked.connect(dialog.accept)
        button_layout.addWidget(close_btn)

        layout.addLayout(button_layout)

        dialog.exec()

    def _register_custom_model(self, parent_dialog, manager, models_tree, refresh_callback):
        """Register a discovered but unregistered model."""
        selected_items = models_tree.selectedItems()
        if not selected_items:
            QMessageBox.warning(
                parent_dialog,
                "No Selection",
                "Please select an unregistered model from the list first."
            )
            return

        model_name = selected_items[0].text(0)
        status = selected_items[0].text(3)

        if model_name == "No models found":
            return

        if "✓ Registered" in status:
            QMessageBox.information(
                parent_dialog,
                "Already Registered",
                f"Model '{model_name}' is already registered.\n\n"
                f"You can create a plugin for it using 'Create Plugin' button."
            )
            return

        language_pair, ok = QInputDialog.getText(
            parent_dialog,
            "Language Pair",
            f"Enter language pair for model '{model_name}':\n\n"
            f"Examples:\n"
            f"  • en-de (English to German)\n"
            f"  • ja-en (Japanese to English)\n"
            f"  • zh-en (Chinese to English)\n\n"
            f"Leave empty if multilingual model:",
            text=""
        )

        if not ok:
            return

        description, ok = QInputDialog.getText(
            parent_dialog,
            "Description (Optional)",
            f"Enter a description for this model:\n\n"
            f"(Leave empty for auto-generated description)",
            text=""
        )

        if not ok:
            return

        try:
            success = manager.register_discovered_model(
                model_name,
                language_pair=language_pair if language_pair else None,
                description=description if description else None
            )

            if success:
                QMessageBox.information(
                    parent_dialog,
                    "Registration Successful",
                    f"Model '{model_name}' has been registered!\n\n"
                    f"Language pair: {language_pair if language_pair else 'Multilingual'}\n\n"
                    f"You can now create a plugin for this model."
                )
                if refresh_callback:
                    refresh_callback()
            else:
                QMessageBox.critical(
                    parent_dialog,
                    "Registration Failed",
                    f"Failed to register model '{model_name}'.\n\n"
                    f"Check the console for error details."
                )

        except Exception as e:
            QMessageBox.critical(
                parent_dialog,
                "Registration Error",
                f"Error registering model:\n{str(e)}"
            )

    def _create_plugin_for_custom_model(self, parent_dialog, manager, models_tree, refresh_callback):
        """Create a plugin for a selected custom model."""
        selected_items = models_tree.selectedItems()
        if not selected_items:
            QMessageBox.warning(
                parent_dialog,
                "No Selection",
                "Please select a model from the list first."
            )
            return

        model_name = selected_items[0].text(0)

        if model_name == "No custom models found":
            return

        if "✓ Registered" not in selected_items[0].text(3):
            QMessageBox.warning(
                parent_dialog,
                "Not Registered",
                f"Model '{model_name}' must be registered first.\n\n"
                f"Use 'Register Selected Model' to register it before creating a plugin."
            )
            return

        lang_dialog = QDialog(parent_dialog)
        lang_dialog.setWindowTitle(f"Configure Plugin for {model_name}")
        lang_dialog.setMinimumSize(500, 400)

        layout = QVBoxLayout(lang_dialog)
        layout.setContentsMargins(20, 20, 20, 20)
        layout.setSpacing(15)

        title = QLabel(f"Configure Plugin for: {model_name}")
        title.setStyleSheet("font-size: 11pt; font-weight: bold;")
        layout.addWidget(title)

        type_group = QGroupBox("Model Type")
        type_layout = QVBoxLayout()

        type_combo = QComboBox()
        type_combo.addItem("MarianMT (Bilingual)", "marianmt")
        type_combo.addItem("NLLB (Multilingual)", "nllb")
        type_combo.addItem("M2M-100 (Multilingual)", "m2m100")
        type_combo.addItem("mBART (Multilingual)", "mbart")
        type_combo.addItem("Custom (Other)", "custom")
        type_layout.addWidget(type_combo)

        type_group.setLayout(type_layout)
        layout.addWidget(type_group)

        lang_group = QGroupBox("Language Pair")
        lang_layout = QFormLayout()

        source_input = QComboBox()
        source_input.setEditable(True)
        source_input.addItems(["en", "de", "es", "fr", "it", "pt", "ja", "zh", "ko", "ru", "ar"])

        target_input = QComboBox()
        target_input.setEditable(True)
        target_input.addItems(["en", "de", "es", "fr", "it", "pt", "ja", "zh", "ko", "ru", "ar"])

        lang_layout.addRow("Source Language:", source_input)
        lang_layout.addRow("Target Language:", target_input)

        lang_group.setLayout(lang_layout)
        layout.addWidget(lang_group)

        info_group = QGroupBox("Model Information (Optional)")
        info_layout = QFormLayout()

        size_input = CustomSpinBox()
        size_input.setRange(1, 10000)
        size_input.setValue(300)
        size_input.setSuffix("MB")

        bleu_input = CustomDoubleSpinBox()
        bleu_input.setRange(0, 100)
        bleu_input.setValue(40.0)
        bleu_input.setDecimals(1)

        info_layout.addRow("Model Size:", size_input)
        info_layout.addRow("BLEU Score:", bleu_input)

        info_group.setLayout(info_layout)
        layout.addWidget(info_group)

        info_label = QLabel(
            "ℹ️ This will create a plugin that can be used for translation.\n"
            "The plugin will be named: {model_type}_{source}_{target}"
        )
        info_label.setWordWrap(True)
        info_label.setStyleSheet("color: #4A9EFF; font-size: 9pt; padding: 10px; background-color: rgba(74, 158, 255, 0.1); border-radius: 5px;")
        layout.addWidget(info_label)

        button_layout = QHBoxLayout()
        button_layout.addStretch()

        cancel_btn = QPushButton("Cancel")
        cancel_btn.clicked.connect(lang_dialog.reject)
        button_layout.addWidget(cancel_btn)

        create_btn = QPushButton("🔌 Create Plugin")
        create_btn.setProperty("class", "action")
        create_btn.clicked.connect(lambda: self._finalize_custom_plugin(
            lang_dialog, manager, model_name, type_combo, source_input, target_input,
            size_input, bleu_input, refresh_callback
        ))
        button_layout.addWidget(create_btn)

        layout.addLayout(button_layout)

        lang_dialog.exec()

    def _finalize_custom_plugin(self, dialog, manager, model_name, type_combo, source_input,
                                target_input, size_input, bleu_input, refresh_callback):
        """Finalize and create the plugin for custom model."""
        model_type = type_combo.currentData()
        source_lang = source_input.currentText().strip()
        target_lang = target_input.currentText().strip()
        size_mb = size_input.value()
        bleu_score = bleu_input.value()

        if not source_lang or not target_lang:
            QMessageBox.warning(
                dialog,
                "Invalid Input",
                "Please provide both source and target languages."
            )
            return

        if source_lang == target_lang:
            QMessageBox.warning(
                dialog,
                "Invalid Input",
                "Source and target languages must be different."
            )
            return

        model_info = {
            "name": model_name,
            "size": size_mb,
            "bleu": bleu_score,
            "desc": f"Custom {model_type} model: {source_lang} → {target_lang}"
        }

        try:
            success = manager._generate_plugin_for_model(
                model_name, source_lang, target_lang, model_info
            )

            if success:
                QMessageBox.information(
                    dialog,
                    "Plugin Created",
                    f"✅ Successfully created plugin for {model_name}!\n\n"
                    f"Plugin name: {model_type}_{source_lang}_{target_lang}\n"
                    f"Language pair: {source_lang} → {target_lang}\n\n"
                    f"You can now use this model for translation."
                )

                dialog.accept()

                if refresh_callback:
                    refresh_callback()
            else:
                QMessageBox.critical(
                    dialog,
                    "Plugin Creation Failed",
                    f"❌ Failed to create plugin for {model_name}.\n\n"
                    f"Check logs for details."
                )
        except Exception as e:
            QMessageBox.critical(
                dialog,
                "Error",
                f"❌ Error creating plugin:\n\n{str(e)}"
            )
