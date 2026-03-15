"""
First-Run Setup Wizard for OptikR

Automated setup wizard that guides users through initial configuration:
1. Python version check
2. Dependency verification
3. GPU detection
4. Model downloads
5. Default configuration
6. Health check

Requirements: 4.1, 4.2, 4.3, 4.4, 4.5, 4.6, 4.7, 4.8, 4.9, 4.10, 4.11
"""

import json
import shutil
import subprocess
import sys
import logging
import re
from pathlib import Path
from datetime import datetime

from PyQt6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QProgressBar, QTextEdit, QWidget, QStackedWidget, QGroupBox,
    QMessageBox, QRadioButton, QCheckBox, QButtonGroup, QComboBox
)
from PyQt6.QtCore import Qt
from PyQt6.QtGui import QCloseEvent, QFont

from app.utils.dependency_checker import DependencyChecker
from app.utils.health_check import HealthCheck
from app.core.model_catalog import ModelCatalog
from app.utils.hardware_detection import HardwareDetector, GPUBackend
from app.workflow.plugin_manager import PluginManager
from app.localization import tr, get_available_languages, set_language, get_current_language
from app.utils.path_utils import get_config_dir

from .component_selector import ComponentSelectorPage
from .setup_worker import SetupWorker

logger = logging.getLogger(__name__)


class FirstRunWizard(QDialog):
    """Automated first-run setup wizard.

    Guides users through initial setup with automated dependency checking,
    GPU detection, model downloads, and health verification.
    """

    # Marker file to track setup completion
    SETUP_MARKER_FILE = get_config_dir() / '.setup_complete'

    def __init__(self, config_manager=None, parent=None):
        super().__init__(parent)
        self.config = config_manager
        self.dependency_checker = DependencyChecker()
        self.health_check = HealthCheck(config_manager)
        self._catalog = ModelCatalog.instance()

        self.setup_worker = None
        self.setup_results = {}
        self.gpu_detected = False
        self.gpu_vendor = None
        self.gpu_backend = None
        self._plugin_manager = None  # Lazy-initialized, reused across setup steps

        # User preference selections (populated by options page)
        self.selected_mode = "cpu"
        self.selected_gpu_vendor = None
        self.tesseract_enabled = False
        self.audio_enabled = False
        self.selected_components: list[str] = []

        self.setWindowTitle(tr("optikr_first_run_setup_wizard"))
        self.setModal(True)
        self.setMinimumWidth(800)
        self.setMinimumHeight(600)

        self.setup_ui()

    def _get_plugin_manager(self) -> PluginManager:
        """Return a shared PluginManager instance, scanning plugins on first call."""
        if self._plugin_manager is None:
            self._plugin_manager = PluginManager()
            self._plugin_manager.scan_plugins()
        return self._plugin_manager

    def _populate_language_combo(self):
        """Fill the language dropdown with available languages."""
        available = get_available_languages()
        current = get_current_language()
        self.lang_combo.blockSignals(True)
        self.lang_combo.clear()
        current_idx = 0
        for i, (code, name) in enumerate(sorted(available.items(), key=lambda x: x[1])):
            self.lang_combo.addItem(name, code)
            if code == current:
                current_idx = i
        self.lang_combo.setCurrentIndex(current_idx)
        self.lang_combo.blockSignals(False)

    def _on_language_changed(self, index: int):
        """Switch UI language when the user picks a different language."""
        code = self.lang_combo.itemData(index)
        if code and code != get_current_language():
            set_language(code)
            self._retranslate_ui()

    def _retranslate_ui(self):
        """Refresh all visible text after a language change."""
        self.setWindowTitle(tr("optikr_first_run_setup_wizard"))
        self.title_label.setText(tr("welcome_to_optikr"))
        self.subtitle_label.setText(tr("wizard_subtitle"))
        self.cancel_btn.setText(tr("cancel"))
        self.finish_btn.setText(tr("finish"))
        # Options page
        self.cpu_radio.setText(tr("wizard_cpu_mode"))
        self.gpu_radio.setText(tr("wizard_gpu_mode"))
        self.nvidia_radio.setText(tr("wizard_nvidia_cuda"))
        self.amd_radio.setText(tr("wizard_amd_rocm"))
        self.auto_detect_radio.setText(tr("wizard_auto_detect"))
        self.tesseract_checkbox.setText(tr("wizard_enable_tesseract"))
        self.audio_checkbox.setText(tr("wizard_enable_audio"))
        self.next_btn.setText(tr("wizard_next"))
        # Group box titles
        self.mode_group_box.setTitle(tr("wizard_compute_mode"))
        self.ocr_group_box.setTitle(tr("wizard_optional_components"))
        self.steps_group_box.setTitle(tr("wizard_setup_steps"))
        self.log_group_box.setTitle(tr("wizard_setup_log"))
        # Re-label step texts on the progress page
        step_tr = {
            "python": tr("wizard_step_python"),
            "dependencies": tr("wizard_step_dependencies"),
            "models": tr("wizard_step_models"),
            "plugins": tr("wizard_step_plugins"),
            "config": tr("wizard_step_config"),
            "plugin_validation": tr("wizard_step_plugin_validation"),
            "health": tr("wizard_step_health"),
        }
        for step_id, new_text in step_tr.items():
            self._step_texts[step_id] = new_text
            if step_id in self.step_labels:
                label = self.step_labels[step_id]
                current_text = label.text()
                icon = current_text[0] if current_text else "\u23f3"
                label.setText(f"{icon} {new_text}")

    def setup_ui(self):
        """Create wizard UI with progress tracking."""
        layout = QVBoxLayout(self)
        layout.setSpacing(20)
        layout.setContentsMargins(30, 30, 30, 30)

        # Language selector row
        lang_row = QHBoxLayout()
        lang_row.addStretch()
        lang_icon = QLabel("\U0001f310")
        lang_icon.setStyleSheet("font-size: 13pt;")
        lang_row.addWidget(lang_icon)
        self.lang_combo = QComboBox()
        self.lang_combo.setMinimumWidth(140)
        self.lang_combo.setStyleSheet("font-size: 9pt; padding: 3px 6px;")
        self._populate_language_combo()
        self.lang_combo.currentIndexChanged.connect(self._on_language_changed)
        lang_row.addWidget(self.lang_combo)
        layout.addLayout(lang_row)

        # Title
        self.title_label = QLabel(tr("welcome_to_optikr"))
        title_font = QFont()
        title_font.setPointSize(20)
        title_font.setBold(True)
        self.title_label.setFont(title_font)
        self.title_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(self.title_label)

        # Subtitle
        self.subtitle_label = QLabel(tr("wizard_subtitle"))
        self.subtitle_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.subtitle_label.setStyleSheet("color: #666; font-size: 11pt;")
        layout.addWidget(self.subtitle_label)

        # Stacked widget for pages
        self.stacked_widget = QStackedWidget()

        # Page 0: Options / preference gathering
        self.options_page = self._create_options_page()
        self.stacked_widget.addWidget(self.options_page)

        # Page 1: Component selection
        try:
            import bootstrap
            installation_info = bootstrap.INSTALLATION_INFO or {}
        except (ImportError, AttributeError):
            installation_info = {}
        self.component_selector_page = ComponentSelectorPage(installation_info)
        # Add navigation buttons to the component selector page
        comp_nav_layout = QHBoxLayout()
        self.component_back_btn = QPushButton(tr("back"))
        self.component_back_btn.setMinimumWidth(100)
        self.component_back_btn.clicked.connect(self._on_component_back_clicked)
        comp_nav_layout.addWidget(self.component_back_btn)
        comp_nav_layout.addStretch()
        self.component_next_btn = QPushButton(tr("wizard_next"))
        self.component_next_btn.setMinimumWidth(120)
        self.component_next_btn.clicked.connect(self._on_component_next_clicked)
        comp_nav_layout.addWidget(self.component_next_btn)
        self.component_selector_page.layout().addLayout(comp_nav_layout)
        self.stacked_widget.addWidget(self.component_selector_page)

        # Page 2: Setup progress
        self.progress_page = self._create_progress_page()
        self.stacked_widget.addWidget(self.progress_page)

        # Page 3: Results summary
        self.results_page = self._create_results_page()
        self.stacked_widget.addWidget(self.results_page)

        layout.addWidget(self.stacked_widget)

        # Buttons
        button_layout = QHBoxLayout()
        button_layout.addStretch()

        self.cancel_btn = QPushButton(tr("cancel"))
        self.cancel_btn.setMinimumWidth(100)
        self.cancel_btn.clicked.connect(self._on_cancel)
        button_layout.addWidget(self.cancel_btn)

        self.finish_btn = QPushButton(tr("finish"))
        self.finish_btn.setMinimumWidth(100)
        self.finish_btn.setVisible(False)
        self.finish_btn.clicked.connect(self.accept)
        button_layout.addWidget(self.finish_btn)

        layout.addLayout(button_layout)

    def _create_options_page(self) -> QWidget:
        """Create the preference-gathering options page.

        Presents CPU/GPU mode selection, GPU vendor selection (conditional),
        and optional Tesseract OCR checkbox before setup begins.
        """
        page = QWidget()
        layout = QVBoxLayout(page)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(15)

        # --- Mode selection ---
        self.mode_group_box = QGroupBox(tr("wizard_compute_mode"))
        mode_group = self.mode_group_box
        mode_layout = QVBoxLayout(mode_group)

        mode_description = QLabel(tr("wizard_compute_mode_desc"))
        mode_description.setWordWrap(True)
        mode_description.setStyleSheet("color: #666; font-size: 10pt;")
        mode_layout.addWidget(mode_description)

        self.mode_button_group = QButtonGroup(page)
        self.cpu_radio = QRadioButton(tr("wizard_cpu_mode"))
        self.gpu_radio = QRadioButton(tr("wizard_gpu_mode"))
        self.cpu_radio.setChecked(True)
        self.mode_button_group.addButton(self.cpu_radio)
        self.mode_button_group.addButton(self.gpu_radio)
        mode_layout.addWidget(self.cpu_radio)
        mode_layout.addWidget(self.gpu_radio)

        # --- GPU vendor selection (conditional) ---
        self.gpu_vendor_widget = QWidget()
        gpu_vendor_layout = QVBoxLayout(self.gpu_vendor_widget)
        gpu_vendor_layout.setContentsMargins(20, 5, 0, 0)

        vendor_label = QLabel(tr("wizard_gpu_vendor"))
        vendor_label.setStyleSheet("font-weight: bold; font-size: 10pt;")
        gpu_vendor_layout.addWidget(vendor_label)

        self.gpu_vendor_button_group = QButtonGroup(page)
        self.nvidia_radio = QRadioButton(tr("wizard_nvidia_cuda"))
        self.amd_radio = QRadioButton(tr("wizard_amd_rocm"))
        self.auto_detect_radio = QRadioButton(tr("wizard_auto_detect"))
        self.auto_detect_radio.setChecked(True)
        self.gpu_vendor_button_group.addButton(self.nvidia_radio)
        self.gpu_vendor_button_group.addButton(self.amd_radio)
        self.gpu_vendor_button_group.addButton(self.auto_detect_radio)
        gpu_vendor_layout.addWidget(self.nvidia_radio)
        gpu_vendor_layout.addWidget(self.amd_radio)
        gpu_vendor_layout.addWidget(self.auto_detect_radio)

        self.gpu_vendor_widget.setVisible(False)
        mode_layout.addWidget(self.gpu_vendor_widget)

        # Toggle GPU vendor visibility based on mode selection
        self.gpu_radio.toggled.connect(self._on_mode_toggled)

        layout.addWidget(mode_group)

        # --- Tesseract OCR option ---
        self.ocr_group_box = QGroupBox(tr("wizard_optional_components"))
        ocr_group = self.ocr_group_box
        ocr_layout = QVBoxLayout(ocr_group)

        self.tesseract_checkbox = QCheckBox(tr("wizard_enable_tesseract"))
        self.tesseract_checkbox.setChecked(False)
        ocr_layout.addWidget(self.tesseract_checkbox)

        ocr_description = QLabel(tr("wizard_tesseract_desc"))
        ocr_description.setWordWrap(True)
        ocr_description.setStyleSheet("color: #666; font-size: 9pt; margin-left: 20px;")
        ocr_layout.addWidget(ocr_description)

        self.ram_recommendation_label = QLabel()
        self.ram_recommendation_label.setWordWrap(True)
        self.ram_recommendation_label.setVisible(False)
        ocr_layout.addWidget(self.ram_recommendation_label)

        try:
            import psutil
            total_ram_gb = psutil.virtual_memory().total / (1024 ** 3)
            if total_ram_gb <= 8.0:
                self.tesseract_checkbox.setChecked(True)
                ram_str = f"{total_ram_gb:.1f}"
                self.ram_recommendation_label.setText(
                    tr("wizard_low_ram_recommendation", ram_gb=ram_str)
                )
                self.ram_recommendation_label.setStyleSheet(
                    "color: #E67E22; font-size: 9pt; margin-left: 20px; "
                    "font-style: italic;"
                )
                self.ram_recommendation_label.setVisible(True)
        except Exception:
            pass

        # --- Audio Translation option ---
        separator = QLabel("")
        separator.setFixedHeight(4)
        ocr_layout.addWidget(separator)

        self.audio_checkbox = QCheckBox(tr("wizard_enable_audio"))
        self.audio_checkbox.setChecked(False)
        ocr_layout.addWidget(self.audio_checkbox)

        audio_description = QLabel(tr("wizard_audio_desc"))
        audio_description.setWordWrap(True)
        audio_description.setStyleSheet(
            "color: #666; font-size: 9pt; margin-left: 20px;")
        ocr_layout.addWidget(audio_description)

        self.audio_deps_label = QLabel(tr("wizard_audio_deps_note"))
        self.audio_deps_label.setWordWrap(True)
        self.audio_deps_label.setStyleSheet(
            "color: #2196F3; font-size: 9pt; margin-left: 20px; "
            "font-style: italic;")
        ocr_layout.addWidget(self.audio_deps_label)

        layout.addWidget(ocr_group)

        layout.addStretch()

        # --- Next button ---
        next_layout = QHBoxLayout()
        next_layout.addStretch()
        self.next_btn = QPushButton(tr("wizard_next"))
        self.next_btn.setMinimumWidth(120)
        self.next_btn.clicked.connect(self._on_next_clicked)
        next_layout.addWidget(self.next_btn)
        layout.addLayout(next_layout)

        return page

    def _on_mode_toggled(self, gpu_selected: bool):
        """Show or hide GPU vendor selection based on mode radio buttons."""
        self.gpu_vendor_widget.setVisible(gpu_selected)

    def _on_next_clicked(self):
        """Handle Next button click on options page.

        Stores user selections, validates prerequisites if available,
        then switches to the progress page and starts setup.
        """
        # Store user selections
        self.selected_mode = "gpu" if self.gpu_radio.isChecked() else "cpu"

        if self.selected_mode == "gpu":
            if self.nvidia_radio.isChecked():
                self.selected_gpu_vendor = "nvidia"
            elif self.amd_radio.isChecked():
                self.selected_gpu_vendor = "amd"
            else:
                self.selected_gpu_vendor = "auto"
        else:
            self.selected_gpu_vendor = None

        self.tesseract_enabled = self.tesseract_checkbox.isChecked()
        self.audio_enabled = self.audio_checkbox.isChecked()

        # Resolve auto-detect GPU vendor before proceeding
        if self.selected_gpu_vendor == "auto":
            detected = self._auto_detect_gpu_vendor()
            if detected:
                self.selected_gpu_vendor = detected
            else:
                msg = QMessageBox(self)
                msg.setWindowTitle(tr("wizard_gpu_vendor_selection"))
                msg.setText(tr("wizard_auto_detect_failed"))
                nvidia_btn = msg.addButton(tr("wizard_nvidia_btn"), QMessageBox.ButtonRole.AcceptRole)
                amd_btn = msg.addButton(tr("wizard_amd_btn"), QMessageBox.ButtonRole.AcceptRole)
                msg.addButton(QMessageBox.StandardButton.Cancel)
                msg.exec()

                clicked = msg.clickedButton()
                if clicked == nvidia_btn:
                    self.selected_gpu_vendor = "nvidia"
                elif clicked == amd_btn:
                    self.selected_gpu_vendor = "amd"
                else:
                    return  # User cancelled, stay on options page

        # Validate prerequisites before proceeding
        if not self._validate_prerequisites():
            return  # User chose to go back or cancel

        # Switch to component selector page
        self.stacked_widget.setCurrentIndex(1)

    def _on_component_next_clicked(self):
        """Handle Next on the component selector page.

        Stores selected component IDs and advances to the progress page.
        """
        self.selected_components = self.component_selector_page.get_selected_ids()
        self.stacked_widget.setCurrentIndex(2)
        self._start_setup()

    def _on_component_back_clicked(self):
        """Handle Back on the component selector page.

        Returns to the options page; selections on the component selector
        are preserved automatically since the page widget stays in place.
        """
        self.stacked_widget.setCurrentIndex(0)

    def _validate_prerequisites(self) -> bool:
        """Validate prerequisites (CUDA, ROCm, Tesseract) before setup.

        Checks for required external tools based on user selections and shows
        a warning dialog if any are missing, giving the user options to continue
        anyway, go back, or cancel.

        Returns:
            True if all prerequisites are met or user chose to continue anyway,
            False if user chose to go back or cancel.
        """
        missing = []

        if self.selected_mode == "gpu":
            if self.selected_gpu_vendor == "nvidia":
                nvidia_smi = shutil.which('nvidia-smi')
                nvcc = shutil.which('nvcc')
                if not nvidia_smi and not nvcc:
                    missing.append(tr("wizard_cuda_not_found"))
            elif self.selected_gpu_vendor == "amd":
                rocm_smi = shutil.which('rocm-smi')
                rocm_path = sys.platform != 'win32' and Path('/opt/rocm').exists()
                if not rocm_smi and not rocm_path:
                    missing.append(tr("wizard_rocm_not_found"))

        if self.tesseract_enabled:
            tesseract_path = shutil.which('tesseract')
            if not tesseract_path:
                missing.append(tr("wizard_tesseract_not_found"))

        if not missing:
            return True

        msg = QMessageBox(self)
        msg.setWindowTitle(tr("wizard_missing_prerequisites"))
        msg.setIcon(QMessageBox.Icon.Warning)
        msg.setText(tr("wizard_prerequisites_not_found"))
        msg.setDetailedText("\n\n".join(missing))

        continue_btn = msg.addButton(tr("wizard_continue_anyway"), QMessageBox.ButtonRole.AcceptRole)
        back_btn = msg.addButton(tr("wizard_go_back"), QMessageBox.ButtonRole.RejectRole)
        cancel_btn = msg.addButton(tr("cancel"), QMessageBox.ButtonRole.DestructiveRole)

        msg.exec()
        clicked = msg.clickedButton()

        if clicked == continue_btn:
            return True
        elif clicked == cancel_btn:
            self.reject()
            return False
        else:  # back_btn or dialog closed
            return False

    def _auto_detect_gpu_vendor(self) -> str | None:
        """Auto-detect GPU vendor using HardwareDetector.

        Integrated GPUs (APUs) with less than 1 GB VRAM are filtered out
        because they lack the memory needed for AI model inference.

        Returns:
            "nvidia", "amd", or None if detection is inconclusive.
        """
        try:
            detector = HardwareDetector()
            caps = detector.detect_capabilities()
            backend = caps.gpu_backend

            if caps.gpu_memory_mb > 0 and caps.gpu_memory_mb < 1024:
                logger.info(
                    "GPU detected with %d MB VRAM (< 1 GB) — treating as "
                    "integrated/APU, skipping GPU acceleration",
                    caps.gpu_memory_mb,
                )
                return None

            if backend == GPUBackend.CUDA:
                return "nvidia"
            elif backend == GPUBackend.ROCM:
                return "amd"
            elif backend == GPUBackend.OPENCL:
                try:
                    import pyopencl as cl_mod
                    for plat in cl_mod.get_platforms():
                        for device in plat.get_devices(device_type=cl_mod.device_type.GPU):
                            vram_mb = device.global_mem_size // (1024 * 1024)
                            if vram_mb < 1024:
                                logger.info(
                                    "OpenCL device '%s' has %d MB VRAM "
                                    "(< 1 GB) — skipping as APU",
                                    device.name, vram_mb,
                                )
                                continue
                            name = device.name.upper()
                            if "AMD" in name or "RADEON" in name:
                                return "amd"
                            elif "NVIDIA" in name or "GEFORCE" in name:
                                return "nvidia"
                except Exception:
                    pass

            return None
        except Exception:
            return None

    def _get_requirements_file(self) -> str:
        """Get the correct requirements file path based on user's mode and GPU vendor.

        Returns:
            Path to the appropriate requirements file.
        """
        if self.selected_mode == "gpu":
            if self.selected_gpu_vendor == "amd":
                return "requirements-gpu-rocm.txt"
            else:
                return "requirements-gpu.txt"
        else:
            return "requirements-cpu.txt"

    # Packages managed by requirements-gpu.txt / requirements-cpu.txt.
    # Never install these via the plugin dependency path — doing so would
    # pull CPU-only wheels from PyPI and silently clobber the CUDA build.
    _PYTORCH_MANAGED: set[str] = {"torch", "torchvision", "torchaudio"}

    # Packages whose transitive dependency trees include torch.
    # Install with ``--no-deps`` and then install their lightweight
    # sub-dependencies separately so torch is never touched.
    _NODEPS_PACKAGES: dict[str, list[str]] = {
        "mokuro": ["fire", "loguru", "natsort", "pyclipper", "shapely", "torchsummary", "yattag"],
        "accelerate": ["pyyaml", "safetensors"],
        "openai-whisper": ["more-itertools", "tiktoken", "numba"],
    }

    @staticmethod
    def _normalize_package_name(name: str) -> str:
        """Normalize package names for dedupe/filtering."""
        return re.sub(r"[-_.]+", "-", name.strip().lower())

    def _normalize_dependency_spec(self, spec: str) -> str | None:
        """Normalize legacy dependency aliases from plugin manifests."""
        text = (spec or "").strip()
        if not text:
            return None

        token = re.split(r"[<>=!~;\[\s]", text, maxsplit=1)[0].strip()
        normalized = self._normalize_package_name(token)
        alias_map = {
            "manga-ocr": "manga-ocr",
            "manga_ocr": "manga-ocr",
            "torch-cpu": "torch",
            "torch-cu121": "torch",
            "torch+cu121": "torch",
            "torch-cu124": "torch",
            "torch+cu124": "torch",
        }
        mapped = alias_map.get(normalized, normalized)
        if mapped in self._PYTORCH_MANAGED:
            return None
        return mapped

    def _collect_plugin_dependencies(self) -> list[str]:
        """Collect dependencies from enabled plugin manifests.

        Reads plugin.json files for all discovered plugins and collects
        their dependencies, selecting mode-appropriate libraries when
        runtime_requirements are specified.

        Packages in ``_PYTORCH_MANAGED`` are always filtered out because
        they are handled by the dedicated GPU/CPU requirements files.

        Returns:
            Deduplicated list of package names to install.
        """
        all_deps = set()

        try:
            plugin_manager = self._get_plugin_manager()

            for plugin_meta in plugin_manager.get_all_plugins():
                plugin_path = plugin_manager.get_plugin_path(plugin_meta.name)
                if not plugin_path:
                    continue

                plugin_json_path = plugin_path / 'plugin.json'
                if not plugin_json_path.exists():
                    continue

                try:
                    with open(plugin_json_path, 'r', encoding='utf-8') as f:
                        manifest = json.load(f)

                    runtime_reqs = manifest.get('runtime_requirements', {})
                    mode_key = self.selected_mode  # "cpu" or "gpu"

                    if mode_key in runtime_reqs:
                        libraries = runtime_reqs[mode_key].get('libraries', [])
                        all_deps.update(libraries)
                    elif 'dependencies' in manifest:
                        all_deps.update(manifest['dependencies'])

                except Exception as e:
                    logger.warning(f"Failed to read plugin manifest {plugin_json_path}: {e}")

        except Exception as e:
            logger.warning(f"Failed to collect plugin dependencies: {e}")

        normalized: set[str] = set()
        removed: set[str] = set()
        for dep in all_deps:
            norm = self._normalize_dependency_spec(dep)
            if norm is None:
                if dep:
                    removed.add(dep)
                continue
            normalized.add(norm)

        if removed:
            logger.info("Filtered/normalized plugin deps (PyTorch-managed or aliases): %s", removed)

        return sorted(normalized)

    def _register_model_plugins(self) -> list[str]:
        """Register downloaded models with their corresponding plugins via ModelCatalog.

        Iterates translation and vision models that are downloaded but lack a
        registered plugin and calls ``ModelCatalog.register_plugin()`` for each.

        Returns:
            List of model IDs that were registered.
        """
        registered = []

        try:
            catalog = self._catalog
            for category in ("translation", "vision"):
                entries = catalog.list_available(category)
                for entry in entries:
                    if entry.status.downloaded and not entry.status.plugin_registered:
                        if catalog.register_plugin(entry.model_id):
                            registered.append(entry.model_id)
                            logger.info("Registered plugin for model: %s", entry.model_id)

        except Exception as e:
            logger.error("Failed to register model plugins: %s", e, exc_info=True)

        return registered

    def _validate_plugin_state(self) -> list[str]:
        """Validate that downloaded models have registered plugins.

        Checks all translation and vision models tracked by ``ModelCatalog``.
        Models that are downloaded but whose plugins are not yet registered are
        reported as informational notes (not failures).

        Returns:
            List of issue descriptions (empty if all plugins are valid).
        """
        issues = []

        try:
            catalog = self._catalog
            for category in ("translation", "vision"):
                entries = catalog.list_available(category)
                for entry in entries:
                    if entry.status.downloaded and not entry.status.plugin_registered:
                        self._log(tr("wizard_model_not_registered", model_id=entry.model_id))

            if not issues:
                self._log(tr("wizard_plugin_state_validated"))

        except Exception as e:
            issue = tr("wizard_plugin_validation_failed", error=str(e))
            issues.append(issue)
            logger.error(issue, exc_info=True)

        return issues

    def _create_progress_page(self) -> QWidget:
        """Create the setup progress page."""
        page = QWidget()
        layout = QVBoxLayout(page)
        layout.setContentsMargins(0, 0, 0, 0)

        # Progress bar
        self.progress_bar = QProgressBar()
        self.progress_bar.setMinimum(0)
        self.progress_bar.setMaximum(1000)
        self.progress_bar.setValue(0)
        self.progress_bar.setTextVisible(True)
        self.progress_bar.setFormat("%.1f%%" % 0.0)
        layout.addWidget(self.progress_bar)

        # Status label
        self.status_label = QLabel(tr("ready_to_begin_setup"))
        self.status_label.setStyleSheet("font-size: 10pt; color: #333;")
        layout.addWidget(self.status_label)

        # Setup steps group
        self.steps_group_box = QGroupBox(tr("wizard_setup_steps"))
        steps_group = self.steps_group_box
        steps_layout = QVBoxLayout(steps_group)

        self.step_labels = {}
        self._step_texts = {}  # Store original text for safe emoji replacement
        steps = [
            ("python", tr("wizard_step_python")),
            ("dependencies", tr("wizard_step_dependencies")),
            ("models", tr("wizard_step_models")),
            ("plugins", tr("wizard_step_plugins")),
            ("config", tr("wizard_step_config")),
            ("plugin_validation", tr("wizard_step_plugin_validation")),
            ("health", tr("wizard_step_health")),
        ]

        for step_id, step_text in steps:
            label = QLabel(f"\u23f3 {step_text}")
            label.setStyleSheet("font-size: 10pt; padding: 5px;")
            self.step_labels[step_id] = label
            self._step_texts[step_id] = step_text
            steps_layout.addWidget(label)

        layout.addWidget(steps_group)

        # Log output
        self.log_group_box = QGroupBox(tr("wizard_setup_log"))
        log_group = self.log_group_box
        log_layout = QVBoxLayout(log_group)

        self.log_output = QTextEdit()
        self.log_output.setReadOnly(True)
        self.log_output.setMaximumHeight(150)
        self.log_output.setStyleSheet("font-family: monospace; font-size: 9pt;")
        log_layout.addWidget(self.log_output)

        layout.addWidget(log_group)

        return page

    def _create_results_page(self) -> QWidget:
        """Create the results summary page."""
        page = QWidget()
        layout = QVBoxLayout(page)
        layout.setContentsMargins(0, 0, 0, 0)

        # Results title
        self.results_title = QLabel(tr("setup_complete"))
        title_font = QFont()
        title_font.setPointSize(16)
        title_font.setBold(True)
        self.results_title.setFont(title_font)
        self.results_title.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(self.results_title)

        # Results summary
        self.results_summary = QTextEdit()
        self.results_summary.setReadOnly(True)
        self.results_summary.setStyleSheet("font-size: 10pt;")
        layout.addWidget(self.results_summary)

        return page

    def _start_setup(self):
        """Start the automated setup process."""
        self.cancel_btn.setText(tr("stop_3"))

        self._log(tr("wizard_starting_setup"))
        self._log(tr("wizard_timestamp", timestamp=datetime.now().strftime('%Y-%m-%d %H:%M:%S')))
        self._log("-" * 60)

        # Create and start worker thread
        self.setup_worker = SetupWorker(self)
        self.setup_worker.progress_updated.connect(self._on_progress_updated)
        self.setup_worker.step_completed.connect(self._on_step_completed)
        self.setup_worker.all_completed.connect(self._on_setup_completed)
        self.setup_worker.log_message.connect(self._on_log_message)
        self.setup_worker.start()

    def closeEvent(self, event: QCloseEvent):
        """Intercept window-close to confirm if setup is in progress."""
        if self.setup_worker and self.setup_worker.isRunning():
            reply = QMessageBox.question(
                self,
                tr("wizard_close_title"),
                tr("wizard_close_running_msg"),
                QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
                QMessageBox.StandardButton.No,
            )
            if reply == QMessageBox.StandardButton.Yes:
                self._catalog.cancel()
                self.setup_worker.stop()
                if not self.setup_worker.wait(5000):
                    self.setup_worker.terminate()
                    self.setup_worker.wait(2000)
                event.accept()
            else:
                event.ignore()
            return

        if self.stacked_widget.currentIndex() in (0, 1):
            reply = QMessageBox.question(
                self,
                tr("wizard_close_title"),
                tr("wizard_close_confirm_msg"),
                QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
                QMessageBox.StandardButton.No,
            )
            if reply == QMessageBox.StandardButton.Yes:
                event.accept()
            else:
                event.ignore()
            return

        event.accept()

    def _on_cancel(self):
        """Handle cancel/stop button click."""
        if self.setup_worker and self.setup_worker.isRunning():
            self._log(tr("wizard_stopping_setup"))
            self._catalog.cancel()
            self.setup_worker.stop()
            if not self.setup_worker.wait(5000):
                self._log(tr("wizard_worker_terminating"))
                self.setup_worker.terminate()
                self.setup_worker.wait(2000)
            self._log(tr("wizard_setup_cancelled"))
            self.reject()
        else:
            self.reject()

    def _on_progress_updated(self, percent: float, message: str):
        """Handle progress update from worker."""
        self.progress_bar.setValue(int(percent * 10))
        self.progress_bar.setFormat(f"{percent:.1f}%")
        self.status_label.setText(message)

    def _on_step_completed(self, success: bool, step_name: str, message: str):
        """Handle step completion from worker."""
        step_map = {
            "Python Version": "python",
            "Dependencies": "dependencies",
            "Model Download": "models",
            "Plugin Registration": "plugins",
            "Configuration": "config",
            "Plugin Validation": "plugin_validation",
            "Health Check": "health",
        }

        step_id = step_map.get(step_name)
        if step_id and step_id in self.step_labels:
            icon = "\u2705" if success else "\u274c"
            self.step_labels[step_id].setText(f"{icon} {self._step_texts[step_id]}")

        status = tr("wizard_log_success") if success else tr("wizard_log_failed")
        self._log(f"[{status}] {step_name}: {message}")

        self.setup_results[step_name] = (success, message)

    def _on_setup_completed(self, overall_success: bool):
        """Handle setup completion."""
        self.cancel_btn.setVisible(False)
        self.finish_btn.setVisible(True)

        # Always mark setup as complete so the wizard doesn't keep re-appearing.
        # Non-critical failures can be resolved later from Settings.
        self._mark_setup_complete()

        if overall_success:
            self._log("-" * 60)
            self._log(tr("wizard_setup_completed_success"))
            self._show_results(True)
        else:
            self._log("-" * 60)
            self._log(tr("wizard_setup_completed_issues_log"))
            self._show_results(False)

    def _show_results(self, success: bool):
        """Show results summary page."""
        self.stacked_widget.setCurrentIndex(3)

        if success:
            self.results_title.setText(tr("setup_complete_2"))
            self.results_title.setStyleSheet("color: #27AE60;")
            summary = f"<h3>{tr('wizard_ready_to_use')}</h3>"
            summary += f"<p>{tr('wizard_all_steps_completed')}</p><ul>"
        else:
            self.results_title.setText(tr("setup_incomplete"))
            self.results_title.setStyleSheet("color: #E67E22;")
            summary = f"<h3>{tr('wizard_completed_with_issues')}</h3>"
            summary += f"<p>{tr('wizard_steps_failed_or_skipped')}</p><ul>"

        for step_name, (step_success, message) in self.setup_results.items():
            icon = "\u2705" if step_success else "\u274c"
            summary += f"<li>{icon} <b>{step_name}:</b> {message}</li>"

        summary += "</ul>"

        if not success:
            summary += f"<p><b>{tr('wizard_what_to_do_next')}</b></p>"
            summary += "<ul>"
            summary += f"<li>{tr('wizard_review_log')}</li>"
            summary += f"<li>{tr('wizard_install_deps_manually')}</li>"
            summary += f"<li>{tr('wizard_rerun_from_settings')}</li>"
            summary += f"<li>{tr('wizard_contact_support')}</li>"
            summary += "</ul>"

        self.results_summary.setHtml(summary)

    def _log(self, message: str):
        """Add message to log output (thread-safe via signal)."""
        if self.setup_worker and self.setup_worker.isRunning():
            self.setup_worker.log_message.emit(message)
        else:
            self.log_output.append(message)
        logger.info(message)

    def _on_log_message(self, message: str):
        """Handle log message from worker thread (runs on main thread)."""
        self.log_output.append(message)

    def _mark_setup_complete(self):
        """Mark installation as complete to prevent re-running."""
        try:
            self.SETUP_MARKER_FILE.parent.mkdir(parents=True, exist_ok=True)

            marker_data = {
                'completed': True,
                'timestamp': datetime.now().isoformat(),
                'version': 'pre-realese-1.0.0'
            }

            with open(self.SETUP_MARKER_FILE, 'w') as f:
                json.dump(marker_data, f, indent=2)

            logger.info(f"Setup marker created: {self.SETUP_MARKER_FILE}")

        except Exception as e:
            logger.error(f"Failed to create setup marker: {e}")

        try:
            if self.config:
                self.config.set_setting('startup.show_setup_wizard', False)
                self.config.save_config()
                logger.info("Set startup.show_setup_wizard = False in config")
        except Exception as e:
            logger.error(f"Failed to update show_setup_wizard in config: {e}")

    @staticmethod
    def is_setup_complete() -> bool:
        """Check if setup has been completed."""
        marker_file = FirstRunWizard.SETUP_MARKER_FILE

        if not marker_file.exists():
            return False

        try:
            with open(marker_file, 'r') as f:
                data = json.load(f)
            return data.get('completed', False)
        except Exception as e:
            logger.warning(f"Failed to read setup marker: {e}")
            return False

    # Setup step implementations

    def check_python_version(self) -> tuple[bool, str]:
        """
        Verify Python 3.10 or 3.11.

        Requirements: 4.2

        Returns:
            Tuple of (success, message)
        """
        version_info = sys.version_info
        major, minor = version_info.major, version_info.minor
        version_str = f"{major}.{minor}.{version_info.micro}"

        if major == 3 and minor in (10, 11):
            return True, tr("wizard_python_supported", version=version_str)
        elif major == 3 and minor >= 12:
            return True, tr("wizard_python_newer", version=version_str)
        else:
            return False, tr("wizard_python_unsupported", version=version_str)

    def download_models(self, progress_callback) -> bool:
        """Download the default translation model via ModelCatalog.

        Requirements: 4.6, 4.7

        Args:
            progress_callback: Called with ``(model_name, progress_float)``
                where *progress_float* is 0.0 – 1.0.

        Returns:
            True if download successful.
        """
        default_model_id = "marianmt-en-de"

        try:
            def _adapted(progress: float, message: str):
                if progress_callback:
                    progress_callback(default_model_id, progress)

            return self._catalog.download(default_model_id, progress_callback=_adapted)
        except Exception as e:
            logger.error("Model download error: %s", e, exc_info=True)
            return False

    def download_component(self, model_id: str, progress_callback=None) -> bool:
        """
        Download/install a wizard-selected component.

        OCR components do not have HF downloads; they rely on Python package
        dependencies from plugin manifests. Ensure those dependencies exist
        so component selection actually results in a usable engine.
        """
        try:
            success = self._catalog.download(model_id, progress_callback=progress_callback)
            if not success:
                return False

            # OCR components need dependency installation even when the catalog
            # reports "no model download required".
            try:
                from app.core.model_catalog_metadata import BUILTIN_MODELS
                meta = BUILTIN_MODELS.get(model_id)
                if meta and meta.category == "ocr":
                    return self._ensure_ocr_component_dependencies(model_id)
            except Exception as meta_error:
                logger.warning("Could not inspect metadata for %s: %s", model_id, meta_error)

            return True
        except Exception as e:
            logger.error("Component download/install error for %s: %s", model_id, e, exc_info=True)
            return False

    def _ensure_ocr_component_dependencies(self, engine_name: str) -> bool:
        """Install missing required dependencies for an OCR engine plugin."""
        try:
            from app.ocr.ocr_plugin_manager import inspect_ocr_plugin_dependencies
        except Exception as import_error:
            logger.warning(
                "Could not import OCR dependency inspector; skipping dependency install for %s: %s",
                engine_name,
                import_error,
            )
            return True

        try:
            exists_on_disk, missing = inspect_ocr_plugin_dependencies(engine_name)
            if not exists_on_disk:
                logger.warning("OCR plugin '%s' not found on disk", engine_name)
                return False

            if not missing:
                logger.info("OCR plugin '%s' dependencies already satisfied", engine_name)
                return True

            self._log(
                f"OCR component '{engine_name}' is missing dependencies: {', '.join(missing)}"
            )
            installed = self._install_dependencies(missing)
            if not installed:
                self._log(f"Failed to install dependencies for OCR component '{engine_name}'")
                return False

            # Verify again after installation
            _, missing_after = inspect_ocr_plugin_dependencies(engine_name)
            if missing_after:
                self._log(
                    f"OCR component '{engine_name}' still missing dependencies after install: "
                    f"{', '.join(missing_after)}"
                )
                return False

            self._log(f"OCR component '{engine_name}' dependencies installed successfully")
            return True
        except Exception as e:
            logger.error("Failed to ensure OCR dependencies for %s: %s", engine_name, e, exc_info=True)
            return False

    def install_audio_dependencies(self, progress_range: tuple = None) -> bool:
        """Install audio translation dependencies from requirements-audio.txt.

        Installs safe packages via the requirements file, then installs
        openai-whisper with ``--no-deps`` to protect the existing torch
        build (CUDA or CPU).

        Returns:
            True if all audio dependencies installed successfully.
        """
        p_start, p_end = progress_range or (0, 0)
        p_mid = p_start + (p_end - p_start) * 0.6

        self._log("Installing audio translation dependencies...")

        # Step 1: Install safe packages from requirements-audio.txt
        req_file = "requirements-audio.txt"
        if not Path(req_file).exists():
            self._log(f"WARNING: {req_file} not found — skipping safe audio deps")
        else:
            success = self._install_requirements_file(
                req_file, progress_range=(p_start, p_mid),
            )
            if not success:
                self._log(f"WARNING: Some audio deps from {req_file} failed to install")

        # Step 2: Install openai-whisper with --no-deps (protects CUDA torch)
        self._log("Installing openai-whisper (with --no-deps to protect PyTorch)...")
        whisper_packages = ["openai-whisper>=20231117"]
        success = self._install_dependencies(
            whisper_packages, progress_range=(p_mid, p_end),
        )

        if success:
            self._log("Audio translation dependencies installed successfully")
        else:
            self._log(
                "WARNING: openai-whisper installation failed — "
                "you can install it manually later: "
                "pip install openai-whisper --no-deps"
            )

        return success

    def configure_defaults(self) -> bool:
        """
        Set up default configuration.

        Requirements: 4.8

        Returns:
            True if configuration successful
        """
        try:
            if not self.config:
                logger.warning("No config manager provided, skipping default configuration")
                return True

            # Set default capture settings
            self.config.set_setting('capture.fps', 30)
            self.config.set_setting('capture.quality', 'high')
            self.config.set_setting('capture.method', 'auto')

            # Set default OCR settings (always EasyOCR on first run).
            self.config.set_setting('ocr.engine', 'easyocr')
            self.config.set_setting('ocr.confidence_threshold', 0.5)
            self.config.set_setting('ocr.languages', ['en'])

            # Set default translation settings
            self.config.set_setting('translation.engine', 'marianmt')
            self.config.set_setting('translation.source_language', 'en')
            self.config.set_setting('translation.target_language', 'de')

            # Set default performance settings
            self.config.set_setting('performance.enable_frame_skip', True)
            self.config.set_setting('performance.enable_translation_cache', True)
            self.config.set_setting('performance.enable_smart_dictionary', True)

            # If a vision model was selected, default to vision pipeline mode
            _VISION_IDS = {"qwen3-vl-2B", "qwen3-vl-4B", "qwen3-vl-8B"}
            if _VISION_IDS & set(self.selected_components):
                self.config.set_setting('pipeline.mode', 'vision')
                self.config.set_setting('vision.enabled', True)

            # Store audio translation enabled state
            if self.audio_enabled:
                self.config.set_setting(
                    'plugins.audio_translation.enabled', True)
                self.config.set_setting(
                    'plugins.audio_translation.auto_detect_language', True)

            # Apply hardware-based feature gating
            from app.utils.hardware_capability_gate import get_hardware_gate
            gate = get_hardware_gate(self.config)
            gate.configure_defaults(self.gpu_detected)

            # Save configuration
            success, error_msg = self.config.save_config()
            return success

        except Exception as e:
            logger.error(f"Configuration error: {e}", exc_info=True)
            return False

    def run_health_check(self) -> tuple[bool, list[str]]:
        """
        Verify all components functional.

        Requirements: 4.9, 4.10

        Returns:
            Tuple of (all_passed, failed_components)
        """
        try:
            system_health = self.health_check.run_all_checks()
            failed = system_health.get_failed_components()
            return system_health.is_healthy, failed
        except Exception as e:
            logger.error(f"Health check error: {e}", exc_info=True)
            return False, ["Health check failed with exception"]

    def _verify_pytorch_build(self) -> bool:
        """Verify that PyTorch has the expected CUDA support after installation.

        When the user selected GPU mode, this checks that torch.cuda.is_available()
        returns True.  If not, it force-reinstalls PyTorch from the correct
        CUDA index using ``--force-reinstall --no-deps`` so that a CPU-only
        build that satisfies the version spec is actually replaced.

        Returns:
            True if verification passed (or mode is CPU), False on failure.
        """
        if self.selected_mode != "gpu":
            return True

        try:
            import importlib
            import torch
            importlib.reload(torch)

            if torch.cuda.is_available():
                cuda_tag = getattr(torch.version, 'cuda', 'unknown')
                self._log(f"PyTorch CUDA verification passed (CUDA {cuda_tag})")
                return True

            build_tag = getattr(torch, '__version__', 'unknown')
            self._log(f"WARNING: PyTorch {build_tag} lost CUDA support — attempting repair...")

            success = self._force_reinstall_pytorch_cuda()

            if success:
                importlib.reload(torch)
                if torch.cuda.is_available():
                    self._log("PyTorch CUDA support restored successfully")
                    return True

            self._log("WARNING: Could not restore PyTorch CUDA support. "
                       "You may need to reinstall manually: "
                       "pip install torch torchvision torchaudio --index-url "
                       "https://download.pytorch.org/whl/cu124")
            return False

        except ImportError:
            self._log("WARNING: PyTorch not importable after installation")
            return False
        except Exception as e:
            self._log(f"PyTorch verification error: {e}")
            return False

    def _force_reinstall_pytorch_cuda(self) -> bool:
        """Force-reinstall PyTorch from the GPU-specific index.

        Uses ``--index-url`` (NOT ``--extra-index-url``) so pip can ONLY
        see the CUDA/ROCm wheels and cannot accidentally prefer a higher-
        versioned CPU-only wheel from PyPI.  Combined with
        ``--force-reinstall --no-deps`` this guarantees the GPU build is
        installed without touching any other packages.
        """
        index_url = self._get_pytorch_index_url()
        cmd = [
            sys.executable, '-m', 'pip', 'install',
            '--force-reinstall', '--no-deps',
            '--index-url', index_url,
            'torch>=2.0.0', 'torchvision>=0.15.0', 'torchaudio>=2.0.0',
        ]
        self._log(f"Force-reinstalling PyTorch from {index_url}")
        try:
            process = subprocess.Popen(
                cmd,
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                text=True,
                bufsize=1,
            )
            for line in process.stdout:
                line = line.strip()
                if line:
                    self._log(f"  {line}")
            process.wait(timeout=600)
            return process.returncode == 0
        except Exception as e:
            self._log(f"PyTorch force-reinstall failed: {e}")
            return False

    def _get_pytorch_index_url(self) -> str:
        """Return the PyTorch wheel index URL for the selected GPU vendor."""
        req_file = self._get_requirements_file()
        try:
            with open(req_file, 'r') as f:
                for line in f:
                    line = line.strip()
                    if line.startswith('--extra-index-url'):
                        return line.split(None, 1)[1]
        except Exception:
            pass
        return "https://download.pytorch.org/whl/cu124"

    def _install_dependencies(self, packages: list[str], progress_range: tuple = None) -> bool:
        """
        Attempt to install missing dependencies using pip.

        Packages listed in ``_NODEPS_PACKAGES`` are installed with
        ``--no-deps`` to prevent torch from being dragged in
        transitively, and their lightweight sub-dependencies are
        installed separately afterwards.

        Args:
            packages: List of package specifications to install
            progress_range: Optional (start, end) float tuple for progress reporting

        Returns:
            True if installation successful, False otherwise
        """
        self._log(tr("wizard_installing_plugin_deps"))
        p_start, p_end = progress_range or (0, 0)

        nodeps_queue: list[str] = []
        normal_queue: list[str] = []
        for pkg in packages:
            base_name = pkg.split(">=")[0].split("<=")[0].split("==")[0].split("[")[0].strip().lower()
            if base_name in self._NODEPS_PACKAGES:
                nodeps_queue.append(pkg)
            else:
                normal_queue.append(pkg)

        all_packages = normal_queue + nodeps_queue
        total = len(all_packages)

        try:
            idx = 0
            for package in normal_queue:
                if not self._pip_install_one(package, idx, total, p_start, p_end):
                    return False
                idx += 1

            for package in nodeps_queue:
                base_name = package.split(">=")[0].split("<=")[0].split("==")[0].split("[")[0].strip().lower()
                sub_deps = self._NODEPS_PACKAGES.get(base_name, [])

                self._log(f"Installing {package} with --no-deps (torch protection)")
                if not self._pip_install_one(package, idx, total, p_start, p_end, extra_args=["--no-deps"]):
                    return False
                idx += 1

                if sub_deps:
                    self._log(f"Installing lightweight sub-dependencies for {base_name}: {', '.join(sub_deps)}")
                    for dep in sub_deps:
                        if not self._pip_install_one(dep, idx, total, p_start, p_end):
                            self._log(f"  Warning: optional sub-dep {dep} failed (non-fatal)")
                        idx += 1

            return True

        except subprocess.TimeoutExpired:
            self._log(tr("wizard_install_timed_out"))
            return False
        except Exception as e:
            self._log(tr("wizard_install_error", error=str(e)))
            logger.error(f"Dependency installation error: {e}", exc_info=True)
            return False

    def _pip_install_one(
        self,
        package: str,
        idx: int,
        total: int,
        p_start: float,
        p_end: float,
        extra_args: list[str] | None = None,
    ) -> bool:
        """Run ``pip install <package>`` with optional extra arguments.

        Returns True on success, False on failure.
        """
        self._log(tr("wizard_installing_package", package=package))
        if p_end > p_start and self.setup_worker:
            pct = p_start + (p_end - p_start) * (idx / max(total, 1))
            self.setup_worker.progress_updated.emit(pct, tr("wizard_installing_package", package=package))

        cmd = [sys.executable, '-m', 'pip', 'install']
        if extra_args:
            cmd.extend(extra_args)
        cmd.append(package)

        process = subprocess.Popen(
            cmd,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True,
            bufsize=1,
        )

        for line in process.stdout:
            line = line.strip()
            if line and line.startswith(("Collecting", "Installing", "Successfully", "Downloading", "Requirement already")):
                self._log(f"  {line}")

        process.wait(timeout=300)

        if process.returncode == 0:
            self._log(tr("wizard_package_installed", package=package))
            return True
        else:
            self._log(tr("wizard_package_failed", package=package))
            return False

    def _install_requirements_file(self, requirements_file: str, progress_range: tuple = None) -> bool:
        """Install dependencies from a requirements file.

        Args:
            requirements_file: Path to the requirements file
            progress_range: Optional (start, end) float tuple for progress reporting

        Returns:
            True if installation successful, False otherwise
        """
        self._log(tr("wizard_installing_from_file", file=requirements_file))
        p_start, p_end = progress_range or (0, 0)
        line_count = 0

        expected_packages = 0
        try:
            with open(requirements_file, 'r') as f:
                for l in f:
                    l = l.strip()
                    if l and not l.startswith(('#', '-')):
                        expected_packages += 1
        except Exception:
            expected_packages = 30  # fallback estimate

        try:
            process = subprocess.Popen(
                [sys.executable, '-m', 'pip', 'install', '-r', requirements_file],
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                text=True,
                bufsize=1,
            )

            for line in process.stdout:
                line = line.strip()
                if line:
                    if line.startswith(("Collecting", "Installing", "Successfully", "Downloading", "Requirement already")):
                        self._log(f"  {line}")
                    if line.startswith(("Collecting", "Requirement already")):
                        line_count += 1
                        if progress_range and self.setup_worker:
                            ratio = min(line_count / max(expected_packages, 1), 0.95)
                            pct = p_start + (p_end - p_start) * ratio
                            short_name = line.split()[1] if len(line.split()) > 1 else requirements_file
                            self.setup_worker.progress_updated.emit(pct, tr("wizard_installing_package", package=short_name))

            process.wait(timeout=600)

            if process.returncode == 0:
                self._log(tr("wizard_file_installed", file=requirements_file))
                if progress_range and self.setup_worker:
                    self.setup_worker.progress_updated.emit(p_end, tr("wizard_finished_file", file=requirements_file))
                return True
            else:
                self._log(tr("wizard_file_install_failed", file=requirements_file))
                return False

        except subprocess.TimeoutExpired:
            process.kill()
            self._log(tr("wizard_file_install_timed_out", file=requirements_file))
            return False
        except Exception as e:
            self._log(tr("wizard_install_error", error=str(e)))
            logger.error(f"Requirements file installation error: {e}", exc_info=True)
            return False


def show_first_run_wizard(config_manager=None, parent=None, force: bool = False) -> bool:
    """
    Show first-run wizard if not already completed.

    Args:
        config_manager: Configuration manager instance
        parent: Parent widget

    Returns:
        True if setup completed successfully or already done, False if cancelled
    """
    if not force and FirstRunWizard.is_setup_complete():
        logger.info("First-run setup already completed, skipping wizard")
        return True

    wizard = FirstRunWizard(config_manager, parent)
    result = wizard.exec()

    return result == QDialog.DialogCode.Accepted
