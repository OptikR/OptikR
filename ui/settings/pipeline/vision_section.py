"""
Vision Settings Section

Configures the Qwen3-VL vision-language pipeline stage that replaces
separate OCR + Translation with a single vision model.  Includes model
variant selection, quantization, generation parameters, prompt template,
download management, and a quick test button.
"""

import logging
import threading
from pathlib import Path

from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QGroupBox, QFormLayout,
    QLabel, QComboBox, QCheckBox, QPushButton, QSlider,
    QSpinBox, QDoubleSpinBox, QTextEdit, QLineEdit, QProgressBar, QMessageBox,
)
from PyQt6.QtCore import Qt, pyqtSignal, QTimer

from ui.common.widgets.scroll_area_no_wheel import ScrollAreaNoWheel
from app.localization import TranslatableMixin, tr

logger = logging.getLogger(__name__)

_VISION_MODELS = [
    ("Qwen/Qwen3-VL-2B-Instruct", "Qwen3-VL 2B  — Fastest, lower quality",  "~4 GB",  "qwen3-vl-2B"),
    ("Qwen/Qwen3-VL-4B-Instruct", "Qwen3-VL 4B  — Balanced (recommended)", "~8 GB",  "qwen3-vl-4B"),
    ("Qwen/Qwen3-VL-8B-Instruct", "Qwen3-VL 8B  — Best quality, slowest",  "~16 GB", "qwen3-vl-8B"),
]

_QUANTIZATION_OPTIONS = [
    ("none", "None (FP16)"),
    ("4bit", "4-bit (GPTQ/AWQ)"),
    ("8bit", "8-bit (bitsandbytes)"),
]

_DEFAULT_PROMPT = (
    "Extract all visible text from this image, then translate it "
    "from {source_lang} to {target_lang}. Return each text block "
    "with its bounding box coordinates and the translated text."
)


class VisionSettingsSection(TranslatableMixin, QWidget):
    """Vision (Qwen3-VL) pipeline stage settings."""

    settingChanged = pyqtSignal()

    def __init__(self, config_manager=None, parent=None):
        super().__init__(parent)

        self.config_manager = config_manager

        self.model_combo: QComboBox | None = None
        self.quantization_combo: QComboBox | None = None
        self.temperature_slider: QSlider | None = None
        self.temperature_spin: QDoubleSpinBox | None = None
        self.max_tokens_spin: QSpinBox | None = None
        self.prompt_edit: QTextEdit | None = None
        self.context_edit: QLineEdit | None = None
        self.test_btn: QPushButton | None = None

        self._download_bars: dict[str, QProgressBar] = {}
        self._download_status_labels: dict[str, QLabel] = {}
        self._download_buttons: dict[str, QPushButton] = {}
        self._delete_buttons: dict[str, QPushButton] = {}

        self._init_ui()

    # ------------------------------------------------------------------
    # UI construction
    # ------------------------------------------------------------------

    def _init_ui(self):
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.setSpacing(0)

        scroll = ScrollAreaNoWheel()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(ScrollAreaNoWheel.Shape.NoFrame)
        scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        scroll.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAsNeeded)

        content = QWidget()
        layout = QVBoxLayout(content)
        layout.setContentsMargins(5, 5, 5, 5)
        layout.setSpacing(10)

        self._create_description(layout)
        self._create_settings_group(layout)
        self._create_download_group(layout)
        self._create_test_group(layout)

        layout.addStretch()
        scroll.setWidget(content)
        main_layout.addWidget(scroll)

    # -- description banner --

    def _create_description(self, parent_layout):
        desc = QLabel(tr("vision_description"))
        desc.setWordWrap(True)
        desc.setStyleSheet("color: #888; font-size: 9pt; padding: 4px;")
        parent_layout.addWidget(desc)

    # -- settings group --

    def _create_settings_group(self, parent_layout):
        group = QGroupBox(tr("vision"))
        form = QFormLayout(group)

        # Model variant
        self.model_combo = QComboBox()
        for hf_id, label, size, _ in _VISION_MODELS:
            self.model_combo.addItem(f"{label}  ({size})", hf_id)
        self.model_combo.setCurrentIndex(1)
        self.model_combo.currentIndexChanged.connect(self.settingChanged)
        form.addRow(tr("vision_model_variant"), self.model_combo)

        # Quantization
        self.quantization_combo = QComboBox()
        for value, label in _QUANTIZATION_OPTIONS:
            self.quantization_combo.addItem(label, value)
        self.quantization_combo.currentIndexChanged.connect(self.settingChanged)
        form.addRow(tr("vision_quantization"), self.quantization_combo)

        # Use GPU
        self.use_gpu_checkbox = QCheckBox()
        self.use_gpu_checkbox.setChecked(True)
        self.use_gpu_checkbox.setToolTip(
            "Use GPU (CUDA) for the vision model when available. Disable to force CPU (slower)."
        )
        self.use_gpu_checkbox.stateChanged.connect(self.settingChanged)
        form.addRow(tr("vision_use_gpu"), self.use_gpu_checkbox)

        # Temperature
        temp_row = QHBoxLayout()
        self.temperature_slider = QSlider(Qt.Orientation.Horizontal)
        self.temperature_slider.setRange(0, 100)
        self.temperature_slider.setValue(30)

        self.temperature_spin = QDoubleSpinBox()
        self.temperature_spin.setRange(0.0, 1.0)
        self.temperature_spin.setSingleStep(0.05)
        self.temperature_spin.setDecimals(2)
        self.temperature_spin.setValue(0.30)

        self.temperature_slider.valueChanged.connect(
            lambda v: self.temperature_spin.setValue(v / 100.0))
        self.temperature_spin.valueChanged.connect(
            lambda v: self.temperature_slider.setValue(int(v * 100)))
        self.temperature_spin.valueChanged.connect(
            lambda: self.settingChanged.emit())

        temp_row.addWidget(self.temperature_slider)
        temp_row.addWidget(self.temperature_spin)
        form.addRow(tr("vision_temperature"), temp_row)

        # Max tokens
        self.max_tokens_spin = QSpinBox()
        self.max_tokens_spin.setRange(64, 4096)
        self.max_tokens_spin.setSingleStep(64)
        self.max_tokens_spin.setValue(512)
        self.max_tokens_spin.valueChanged.connect(self.settingChanged)
        form.addRow(tr("vision_max_tokens"), self.max_tokens_spin)

        # Exclude SFX (dialogue/narration only)
        self.exclude_sfx_checkbox = QCheckBox()
        self.exclude_sfx_checkbox.setChecked(False)
        self.exclude_sfx_checkbox.setToolTip(
            "Extract and translate only dialogue and narration; skip sound effects (SFX). "
            "Use for manga to measure accuracy without onomatopoeia."
        )
        self.exclude_sfx_checkbox.stateChanged.connect(self.settingChanged)
        form.addRow(tr("vision_exclude_sfx"), self.exclude_sfx_checkbox)

        # Prompt template (editable prompt sent to the vision model)
        self.prompt_edit = QTextEdit()
        self.prompt_edit.setPlaceholderText(_DEFAULT_PROMPT)
        self.prompt_edit.setMaximumHeight(120)
        self.prompt_edit.setToolTip(
            "Instruction sent to the vision model. Use {source_lang} and {target_lang} "
            "as placeholders (e.g. \"Japanese\", \"English\"). Leave empty to use the default prompt."
        )
        self.prompt_edit.textChanged.connect(self.settingChanged)
        prompt_reset_btn = QPushButton(tr("vision_prompt_reset_default"))
        prompt_reset_btn.setToolTip("Clear the custom prompt and use the default again.")
        prompt_reset_btn.clicked.connect(lambda: self.prompt_edit.setPlainText(""))
        prompt_row = QHBoxLayout()
        prompt_row.addWidget(self.prompt_edit, 1)
        prompt_row.addWidget(prompt_reset_btn, 0)
        form.addRow(tr("vision_prompt_template"), prompt_row)

        hint = QLabel(tr("vision_prompt_context_hint"))
        hint.setWordWrap(True)
        hint.setStyleSheet("color: #666; font-size: 8pt; margin-top: 2px;")
        form.addRow(hint)

        # Optional context (prepended to the prompt sent to the model)
        self.context_edit = QLineEdit()
        self.context_edit.setPlaceholderText("e.g. This is manga dialogue. / Technical document.")
        self.context_edit.textChanged.connect(self.settingChanged)
        form.addRow(tr("vision_context_optional"), self.context_edit)

        parent_layout.addWidget(group)

    # -- download manager group --

    def _create_download_group(self, parent_layout):
        group = QGroupBox(tr("vision_download_model"))
        layout = QVBoxLayout(group)

        vram_label = QLabel()
        vram_label.setWordWrap(True)
        vram_label.setStyleSheet("color: #c57600; font-size: 8pt;")
        self._vram_label = vram_label
        layout.addWidget(vram_label)
        self._update_vram_warning()

        for hf_id, label, size, catalog_id in _VISION_MODELS:
            row = QHBoxLayout()

            name_lbl = QLabel(f"<b>{label}</b>")
            name_lbl.setMinimumWidth(260)
            row.addWidget(name_lbl)

            status_lbl = QLabel(tr("vision_model_status_not_downloaded"))
            status_lbl.setStyleSheet("color: #888;")
            status_lbl.setMinimumWidth(140)
            self._download_status_labels[catalog_id] = status_lbl
            row.addWidget(status_lbl)

            progress = QProgressBar()
            progress.setVisible(False)
            progress.setMaximumWidth(150)
            self._download_bars[catalog_id] = progress
            row.addWidget(progress)

            dl_btn = QPushButton(tr("vision_download_model"))
            dl_btn.setProperty("catalog_id", catalog_id)
            dl_btn.setProperty("hf_id", hf_id)
            dl_btn.clicked.connect(
                lambda checked, cid=catalog_id, hid=hf_id: self._start_download(cid, hid))
            self._download_buttons[catalog_id] = dl_btn
            row.addWidget(dl_btn)

            del_btn = QPushButton(tr("vision_delete_model"))
            del_btn.setEnabled(False)
            del_btn.clicked.connect(
                lambda checked, cid=catalog_id: self._delete_model(cid))
            self._delete_buttons[catalog_id] = del_btn
            row.addWidget(del_btn)

            layout.addLayout(row)

        parent_layout.addWidget(group)

    # -- test group --

    def _create_test_group(self, parent_layout):
        group = QGroupBox(tr("vision_test_button"))
        layout = QVBoxLayout(group)

        desc = QLabel(
            "Capture a single frame, run the vision model, and display "
            "the detected + translated text blocks.")
        desc.setWordWrap(True)
        desc.setStyleSheet("color: #888; font-size: 8pt;")
        layout.addWidget(desc)

        self.test_btn = QPushButton(tr("vision_test_button"))
        self.test_btn.clicked.connect(self._run_test)
        layout.addWidget(self.test_btn)

        self._test_result_label = QLabel("")
        self._test_result_label.setWordWrap(True)
        layout.addWidget(self._test_result_label)

        parent_layout.addWidget(group)

    # ------------------------------------------------------------------
    # VRAM warning
    # ------------------------------------------------------------------

    def _update_vram_warning(self):
        try:
            from app.utils.hardware_detector import HardwareDetector
            detector = HardwareDetector()
            info = detector.detect()
            gpu_vram = getattr(info, 'gpu_vram_gb', None)
            if gpu_vram is not None and gpu_vram < 8:
                self._vram_label.setText(
                    tr("vision_vram_warning").format(
                        required="8", available=f"{gpu_vram:.1f}"))
                self._vram_label.setVisible(True)
            else:
                self._vram_label.setVisible(False)
        except Exception:
            self._vram_label.setVisible(False)

    # ------------------------------------------------------------------
    # Download management
    # ------------------------------------------------------------------

    def _start_download(self, catalog_id: str, hf_id: str):
        bar = self._download_bars.get(catalog_id)
        btn = self._download_buttons.get(catalog_id)
        status = self._download_status_labels.get(catalog_id)
        if not bar or not btn:
            return

        btn.setEnabled(False)
        bar.setVisible(True)
        bar.setValue(0)
        if status:
            status.setText(tr("vision_downloading").format(model=catalog_id))

        def _progress(pct):
            QTimer.singleShot(0, lambda: bar.setValue(int(pct)))

        def _worker():
            try:
                from app.core.model_catalog import ModelCatalog
                catalog = ModelCatalog.instance()
                catalog.download(catalog_id, progress_callback=_progress)
                QTimer.singleShot(0, lambda: self._on_download_complete(catalog_id))
            except Exception as exc:
                QTimer.singleShot(
                    0, lambda: self._on_download_failed(catalog_id, str(exc)))

        threading.Thread(target=_worker, daemon=True).start()

    def _on_download_complete(self, catalog_id: str):
        bar = self._download_bars.get(catalog_id)
        btn = self._download_buttons.get(catalog_id)
        status = self._download_status_labels.get(catalog_id)
        del_btn = self._delete_buttons.get(catalog_id)

        if bar:
            bar.setValue(100)
            bar.setVisible(False)
        if btn:
            btn.setEnabled(True)
        if status:
            status.setText(tr("vision_download_complete"))
            status.setStyleSheet("color: #2a2;")
        if del_btn:
            del_btn.setEnabled(True)

        self._refresh_model_statuses()

    def _on_download_failed(self, catalog_id: str, error: str):
        bar = self._download_bars.get(catalog_id)
        btn = self._download_buttons.get(catalog_id)
        status = self._download_status_labels.get(catalog_id)

        if bar:
            bar.setVisible(False)
        if btn:
            btn.setEnabled(True)
        if status:
            status.setText(tr("vision_download_failed").format(error=error))
            status.setStyleSheet("color: #c22;")

    def _delete_model(self, catalog_id: str):
        reply = QMessageBox.question(
            self, tr("vision_delete_model"),
            f"Delete downloaded model '{catalog_id}'?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
        )
        if reply != QMessageBox.StandardButton.Yes:
            return

        try:
            from app.core.model_catalog import ModelCatalog
            catalog = ModelCatalog.instance()
            catalog.delete(catalog_id)
        except Exception as exc:
            logger.warning("Failed to delete model %s: %s", catalog_id, exc)

        self._refresh_model_statuses()

    def _refresh_model_statuses(self):
        """Re-check download status for each model variant.

        Re-scans the HuggingFace cache so models already at ~/.cache/huggingface/hub
        (e.g. C:\\Users\\...\\.cache\\huggingface\\hub\\models--Qwen--Qwen3-VL-4B-Instruct)
        are detected, then checks the registry and falls back to direct cache lookup.
        """
        try:
            from app.core.model_catalog import ModelCatalog
            catalog = ModelCatalog.instance()
            catalog._registry.scan_local_models()
            # Resolve canonical hf_repo per catalog_id (may differ from _VISION_MODELS hf_id)
            vision_entries = {e.model_id: e for e in catalog.list_available("vision")}
            def hf_repo_for(catalog_id: str, fallback_hf_id: str) -> str:
                entry = vision_entries.get(catalog_id)
                if entry and getattr(entry.metadata, "hf_repo", None):
                    return entry.metadata.hf_repo
                return fallback_hf_id

            for hf_id, _, size, catalog_id in _VISION_MODELS:
                status_lbl = self._download_status_labels.get(catalog_id)
                del_btn = self._delete_buttons.get(catalog_id)
                if not status_lbl:
                    continue

                downloaded = catalog.is_downloaded(catalog_id)

                if not downloaded:
                    # Prefer catalog's canonical repo (e.g. Qwen/Qwen3-VL-4B-Instruct) so runtime-cached models are found
                    canonical_repo = hf_repo_for(catalog_id, hf_id)
                    hf_path = catalog._find_hf_snapshot(canonical_repo)
                    if hf_path is None and canonical_repo != hf_id:
                        hf_path = catalog._find_hf_snapshot(hf_id)
                    if hf_path is not None and hf_path.is_dir():
                        # Accept either safetensors or PyTorch bin weights (e.g. models in HF cache)
                        has_weights = (
                            any(hf_path.glob("*.safetensors"))
                            or any(hf_path.glob("pytorch_model*.bin"))
                        )
                        has_config = (
                            (hf_path / "config.json").exists()
                            or (hf_path / "preprocessor_config.json").exists()
                        )
                        if has_weights and has_config:
                            downloaded = True
                            self._sync_registry_from_cache(
                                catalog, catalog_id, canonical_repo, str(hf_path))

                if downloaded:
                    status_lbl.setText(
                        tr("vision_model_status_downloaded").format(size=size))
                    status_lbl.setStyleSheet("color: #2a2;")
                    if del_btn:
                        del_btn.setEnabled(True)
                else:
                    status_lbl.setText(tr("vision_model_status_not_downloaded"))
                    status_lbl.setStyleSheet("color: #888;")
                    if del_btn:
                        del_btn.setEnabled(False)
        except Exception:
            logger.debug("Could not refresh vision model statuses", exc_info=True)

    @staticmethod
    def _sync_registry_from_cache(catalog, catalog_id: str, hf_repo: str, local_path: str):
        """Update the model registry to reflect a model found in the HF cache."""
        try:
            from datetime import datetime, timezone
            catalog._registry.update_entry(
                catalog_id,
                downloaded=True,
                download_timestamp=datetime.now(timezone.utc).isoformat(),
                local_path=local_path,
                hf_repo=hf_repo,
            )
            logger.info(
                "Synced registry for %s: found in HF cache at %s",
                catalog_id, local_path)
        except Exception as exc:
            logger.debug("Could not sync registry for %s: %s", catalog_id, exc)

    # ------------------------------------------------------------------
    # Test
    # ------------------------------------------------------------------

    def _run_test(self):
        self._test_result_label.setText("Running vision test...")
        self._test_result_label.setStyleSheet("color: #888;")
        self.test_btn.setEnabled(False)

        def _worker():
            try:
                result = self._execute_vision_test()
                QTimer.singleShot(
                    0, lambda: self._show_test_result(True, result))
            except Exception as exc:
                QTimer.singleShot(
                    0, lambda: self._show_test_result(False, str(exc)))

        threading.Thread(target=_worker, daemon=True).start()

    def _execute_vision_test(self) -> str:
        """Capture a screenshot and run Qwen3-VL inference (runs in background thread)."""
        import time
        from PIL import ImageGrab

        region = None
        if self.config_manager:
            region = self.config_manager.get_setting("capture.custom_region", None)

        if region and isinstance(region, dict):
            bbox = (
                region["x"], region["y"],
                region["x"] + region["width"],
                region["y"] + region["height"],
            )
            screenshot = ImageGrab.grab(bbox=bbox)
        else:
            screenshot = ImageGrab.grab()

        w, h = screenshot.size

        model_id = self.model_combo.currentData() if self.model_combo else "Qwen/Qwen3-VL-4B-Instruct"

        import torch
        from transformers import Qwen3VLForConditionalGeneration, AutoProcessor
        from qwen_vl_utils import process_vision_info

        src_lang = "Japanese"
        tgt_lang = "English"
        if self.config_manager:
            src_lang = self.config_manager.get_setting("translation.source_language", "ja")
            tgt_lang = self.config_manager.get_setting("translation.target_language", "en")

        processor = AutoProcessor.from_pretrained(model_id)
        model = Qwen3VLForConditionalGeneration.from_pretrained(
            model_id, torch_dtype=torch.float16, device_map="auto",
        )

        prompt = self.prompt_edit.toPlainText().strip() if self.prompt_edit else ""
        if not prompt:
            prompt = (
                f"Extract all visible text from this image and translate it "
                f"from {src_lang} to {tgt_lang}. For each text region, return "
                f"the translated text. Only return the translated text, nothing else."
            )
        if self.context_edit and self.context_edit.text().strip():
            prompt = self.context_edit.text().strip() + "\n\n" + prompt

        messages = [{
            "role": "user",
            "content": [
                {"type": "image", "image": screenshot},
                {"type": "text", "text": prompt},
            ],
        }]

        text = processor.apply_chat_template(messages, tokenize=False, add_generation_prompt=True)
        images, videos, video_kwargs = process_vision_info(messages, return_video_kwargs=True)
        inputs = processor(
            text=[text], images=images, videos=videos,
            padding=True, return_tensors="pt", **video_kwargs,
        ).to(model.device)

        t0 = time.perf_counter()
        max_tokens = self.max_tokens_spin.value() if self.max_tokens_spin else 512
        generated = model.generate(**inputs, max_new_tokens=max_tokens)
        elapsed = (time.perf_counter() - t0) * 1000

        trimmed = [out[len(inp):] for inp, out in zip(inputs.input_ids, generated)]
        output_text = processor.batch_decode(trimmed, skip_special_tokens=True)[0].strip()

        del model, processor, inputs, generated
        torch.cuda.empty_cache()

        return (
            f"Frame: {w}x{h} | Model: {model_id.split('/')[-1]} | "
            f"Inference: {elapsed:.0f}ms\n\n{output_text}"
        )

    def _show_test_result(self, success: bool, message: str):
        self.test_btn.setEnabled(True)
        if success:
            self._test_result_label.setText(message)
            self._test_result_label.setStyleSheet("color: #2a2;")
        else:
            self._test_result_label.setText(message)
            self._test_result_label.setStyleSheet("color: #c22;")

    # ------------------------------------------------------------------
    # Config persistence
    # ------------------------------------------------------------------

    def load_config(self):
        if not self.config_manager:
            return

        model = self.config_manager.get_setting(
            'vision.model_name', 'Qwen/Qwen3-VL-4B-Instruct')
        idx = self.model_combo.findData(model)
        if idx >= 0:
            self.model_combo.setCurrentIndex(idx)

        quant = self.config_manager.get_setting('vision.quantization', 'none')
        idx = self.quantization_combo.findData(quant)
        if idx >= 0:
            self.quantization_combo.setCurrentIndex(idx)

        self.use_gpu_checkbox.setChecked(
            self.config_manager.get_setting('vision.use_gpu', True))

        temp = self.config_manager.get_setting('vision.temperature', 0.3)
        self.temperature_spin.setValue(temp)

        max_tok = self.config_manager.get_setting('vision.max_tokens', 512)
        self.max_tokens_spin.setValue(max_tok)

        self.exclude_sfx_checkbox.setChecked(
            self.config_manager.get_setting('vision.exclude_sfx', False))

        prompt = self.config_manager.get_setting('vision.prompt_template', '')
        self.prompt_edit.setPlainText(prompt)

        if self.context_edit:
            self.context_edit.setText(
                self.config_manager.get_setting('vision.context', ''))

        self._refresh_model_statuses()

    def save_config(self):
        if not self.config_manager:
            return True, ""

        self.config_manager.set_setting(
            'vision.model_name', self.model_combo.currentData())
        self.config_manager.set_setting(
            'vision.quantization', self.quantization_combo.currentData())
        self.config_manager.set_setting(
            'vision.use_gpu', self.use_gpu_checkbox.isChecked())
        self.config_manager.set_setting(
            'vision.temperature', self.temperature_spin.value())
        self.config_manager.set_setting(
            'vision.max_tokens', self.max_tokens_spin.value())
        self.config_manager.set_setting(
            'vision.exclude_sfx', self.exclude_sfx_checkbox.isChecked())
        self.config_manager.set_setting(
            'vision.prompt_template', self.prompt_edit.toPlainText())
        if self.context_edit:
            self.config_manager.set_setting(
                'vision.context', self.context_edit.text().strip())

        return True, ""

    def validate(self) -> bool:
        return True
