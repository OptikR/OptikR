"""
Setup Worker Thread for First-Run Wizard

Background worker that executes the 7-step setup sequence without blocking the UI.
All GUI interactions happen on the main thread via Qt signals.
"""

import logging

from PyQt6.QtCore import QThread, pyqtSignal

logger = logging.getLogger(__name__)


class SetupWorker(QThread):
    """Worker thread for running setup steps without blocking UI.

    IMPORTANT: This thread must NEVER create or interact with Qt widgets.
    All GUI interactions (QMessageBox, QDialog, etc.) must happen on the
    main thread via signals.
    """

    # Signals
    progress_updated = pyqtSignal(float, str)  # progress_percent (0.0-100.0), status_message
    step_completed = pyqtSignal(bool, str, str)  # success, message, details
    all_completed = pyqtSignal(bool)  # overall_success
    log_message = pyqtSignal(str)  # log line to append to UI

    def __init__(self, wizard, parent=None):
        super().__init__(parent)
        self.wizard = wizard
        self.should_stop = False

    def run(self):
        """Run all setup steps sequentially.

        No Qt GUI calls are made here — only signals are emitted.
        Failed steps are logged and reported via step_completed signal,
        but non-critical failures don't block the setup.

        Step order:
        1. Python version check
        2. Mode-aware dependency installation
        3. Model download
        4. Register model plugins
        5. Configure defaults (with mode info)
        6. Validate plugin state
        7. Health check
        """
        try:
            # Step 1: Check Python version (unchanged)
            self.progress_updated.emit(2.0, "Checking Python version...")
            success, message = self.wizard.check_python_version()
            self.step_completed.emit(success, "Python Version", message)
            if not success or self.should_stop:
                self.all_completed.emit(False)
                return

            # Step 2: Mode-aware dependency installation (3% - 32%)
            #
            # Defence-in-depth against CUDA-torch being replaced by CPU-only:
            #
            #  a) requirements.txt no longer lists packages whose transitive
            #     deps include torch (mokuro, accelerate).
            #  b) _collect_plugin_dependencies() strips torch/torchvision/
            #     torchaudio from plugin dep lists.
            #  c) _install_dependencies() installs known heavy packages
            #     (mokuro, accelerate) with --no-deps, then installs their
            #     lightweight sub-deps separately.
            #  d) PyTorch is force-reinstalled from the CUDA index LAST so
            #     that even if a CPU-only build slipped through, it is
            #     replaced deterministically.
            #  e) _verify_pytorch_build() validates CUDA and can force-
            #     reinstall again as a last resort.
            self.progress_updated.emit(3.0, "Installing base dependencies...")
            try:
                req_file = self.wizard._get_requirements_file()
                self.wizard._install_requirements_file("requirements.txt", progress_range=(3.0, 17.0))
                plugin_deps = self.wizard._collect_plugin_dependencies()
                if plugin_deps:
                    self.wizard._install_dependencies(plugin_deps, progress_range=(17.0, 22.0))

                self.progress_updated.emit(22.0, "Installing PyTorch (ensuring correct build)...")
                if self.wizard.selected_mode == "gpu":
                    success = self.wizard._force_reinstall_pytorch_cuda()
                else:
                    success = self.wizard._install_requirements_file(req_file, progress_range=(22.0, 30.0))

                if success:
                    torch_ok = self.wizard._verify_pytorch_build()
                    if torch_ok:
                        self.step_completed.emit(True, "Dependencies", f"Dependencies installed — PyTorch verified from {req_file}")
                    else:
                        self.step_completed.emit(True, "Dependencies", f"Dependencies installed from {req_file} (PyTorch CUDA verification skipped or N/A)")
                else:
                    self.step_completed.emit(False, "Dependencies", f"Failed to install from {req_file} (can install later)")
            except Exception as e:
                self.step_completed.emit(False, "Dependencies", f"Dependency install error: {e}")
            if self.should_stop:
                self.all_completed.emit(False)
                return

            # Step 3: Download selected components (33% - 65%)
            components = self.wizard.selected_components
            if not components:
                self.progress_updated.emit(65.0, "No components selected for download.")
                self.step_completed.emit(True, "Model Download", "No components selected — skipped")
            else:
                self.progress_updated.emit(33.0, "Downloading AI models...")
                per_component_range = 32.0 / len(components)
                successes = []
                failures = []
                for i, model_id in enumerate(components):
                    if self.should_stop:
                        break
                    base = 33.0 + i * per_component_range
                    try:
                        # Bind loop variables via default args to avoid late-binding closure issue
                        def _make_cb(b=base, r=per_component_range, mid=model_id):
                            return lambda p, m: self.progress_updated.emit(
                                b + p * r, f"Downloading {mid}..."
                            )
                        success = self.wizard.download_component(
                            model_id,
                            progress_callback=_make_cb(),
                        )
                        if success:
                            successes.append(model_id)
                            self.step_completed.emit(True, f"Download: {model_id}", f"{model_id} downloaded successfully")
                        else:
                            failures.append(model_id)
                            self.step_completed.emit(False, f"Download: {model_id}", f"{model_id} download failed (can be done later in Settings)")
                    except Exception as e:
                        logger.error("Download error for %s: %s", model_id, e, exc_info=True)
                        failures.append(model_id)
                        self.step_completed.emit(False, f"Download: {model_id}", f"{model_id}: {e}")

                # Emit summary
                overall_success = len(failures) == 0 and len(successes) > 0
                if failures:
                    summary = f"Downloads: {len(successes)} succeeded, {len(failures)} failed ({', '.join(failures)})"
                else:
                    summary = f"All {len(successes)} component(s) downloaded successfully"
                self.step_completed.emit(overall_success, "Model Download Summary", summary)

            if self.should_stop:
                self.all_completed.emit(False)
                return

            # Step 4: Register model plugins
            self.progress_updated.emit(66.0, "Registering model plugins...")
            try:
                registered = self.wizard._register_model_plugins()
                if registered:
                    message = f"Registered plugins: {', '.join(registered)}"
                else:
                    message = "No new plugins to register"
                self.step_completed.emit(True, "Plugin Registration", message)
            except Exception as e:
                self.step_completed.emit(False, "Plugin Registration", f"Plugin registration error: {e}")
            if self.should_stop:
                self.all_completed.emit(False)
                return

            # Step 5: Configure defaults
            self.progress_updated.emit(75.0, "Configuring default settings...")
            try:
                self.wizard.gpu_detected = (self.wizard.selected_mode == "gpu")
                success = self.wizard.configure_defaults()
                message = "Default configuration applied" if success else "Configuration failed"
            except Exception as e:
                success = False
                message = f"Configuration error: {e}"
            self.step_completed.emit(success, "Configuration", message)
            if self.should_stop:
                self.all_completed.emit(False)
                return

            # Step 6: Validate plugin state
            self.progress_updated.emit(85.0, "Validating plugin state...")
            try:
                issues = self.wizard._validate_plugin_state()
                if not issues:
                    self.step_completed.emit(True, "Plugin Validation", "All plugins validated successfully")
                else:
                    self.step_completed.emit(False, "Plugin Validation", f"Issues: {'; '.join(issues)}")
            except Exception as e:
                self.step_completed.emit(False, "Plugin Validation", f"Validation error: {e}")
            if self.should_stop:
                self.all_completed.emit(False)
                return

            # Step 7: Run health check (unchanged)
            self.progress_updated.emit(92.0, "Running health check...")
            try:
                success, failures = self.wizard.run_health_check()
                message = "All systems operational" if success else f"Issues: {', '.join(failures)}"
            except Exception as e:
                success = False
                message = f"Health check error: {e}"
            self.step_completed.emit(success, "Health Check", message)

            # Complete
            self.progress_updated.emit(100.0, "Setup complete!")
            self.all_completed.emit(True)

        except Exception as e:
            logger.error(f"Setup worker error: {e}", exc_info=True)
            self.step_completed.emit(False, "Error", str(e))
            self.all_completed.emit(False)

    def stop(self):
        """Request worker to stop."""
        self.should_stop = True
