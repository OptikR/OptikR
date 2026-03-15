"""
Capture Plugin Manager

Discovers, registers, and activates capture plugins.
Delegates actual frame capture to the active backend.
"""

import logging
import importlib.util
import json
from pathlib import Path

import numpy as np

from app.workflow.base.plugin_interface import PluginMetadata
from app.workflow.plugins.manager import UnifiedPluginManager


class CapturePluginManager:
    """Discovers and manages capture plugins.

    Each plugin is identified by a ``plugin.json`` on disk.  At capture time
    the manager delegates to the currently active backend (bettercam or PIL
    screenshot fallback).
    """

    def __init__(self, plugin_directories: list[str] | None = None):
        self.logger = logging.getLogger(__name__)
        self._plugin_directories = list(plugin_directories or [])
        self._add_default_plugin_directories()
        self.discovered_plugins: list[PluginMetadata] = []
        self._active_plugin: str | None = None
        self._unified = UnifiedPluginManager(self._plugin_directories)

        # BetterCam backend (streaming mode for fresh DXGI frames)
        self._bettercam_camera = None
        self._bettercam_streaming = False
        self._bettercam_region: tuple[int, ...] | None = None

    # ------------------------------------------------------------------
    # Plugin directories
    # ------------------------------------------------------------------

    def _add_default_plugin_directories(self) -> None:
        current_dir = Path(__file__).parent
        self._plugin_directories.append(
            str(current_dir.parent.parent / "plugins" / "stages" / "capture"),
        )
        user_plugins = Path.home() / ".translation_system" / "plugins" / "stages" / "capture"
        self._plugin_directories.append(str(user_plugins))

    # ------------------------------------------------------------------
    # Discovery
    # ------------------------------------------------------------------

    def discover_plugins(self) -> list[PluginMetadata]:
        """Scan plugin directories and return metadata for available plugins."""
        discovered: list[PluginMetadata] = []

        for directory in self._plugin_directories:
            dir_path = Path(directory)
            if not dir_path.exists():
                continue

            self.logger.info("Scanning for capture plugins in: %s", directory)

            for item in dir_path.iterdir():
                if not item.is_dir():
                    continue
                plugin_json = item / "plugin.json"
                if not plugin_json.exists():
                    continue
                try:
                    with open(plugin_json, "r", encoding="utf-8") as f:
                        plugin_data = json.load(f)

                    if not self._check_dependencies(plugin_data.get("dependencies", [])):
                        self.logger.debug(
                            "Skipping %s — dependencies not installed",
                            plugin_data.get("name"),
                        )
                        continue

                    plugin_info = PluginMetadata.from_dict(plugin_data)
                    discovered.append(plugin_info)
                    self.logger.info("Discovered capture plugin: %s", plugin_info.name)
                except Exception as e:
                    self.logger.error("Failed to load plugin %s: %s", plugin_json, e)

        self.discovered_plugins = discovered

        for p in discovered:
            self._unified.registry.register(p)

        self.logger.info("Discovered %d capture plugins", len(discovered))
        return discovered

    _PIP_TO_IMPORT: dict[str, str] = {
        "opencv-python": "cv2",
        "opencv-python-headless": "cv2",
        "pillow": "PIL",
        "pywin32": "win32api",
        "scikit-learn": "sklearn",
        "beautifulsoup4": "bs4",
    }

    @classmethod
    def _check_dependencies(cls, dependencies: list[str]) -> bool:
        for dep in dependencies:
            if "optional" in dep.lower():
                continue
            dep_name = dep.split("(")[0].strip()
            import_name = cls._PIP_TO_IMPORT.get(dep_name, dep_name)
            if importlib.util.find_spec(import_name) is None:
                return False
        return True

    # ------------------------------------------------------------------
    # Activation
    # ------------------------------------------------------------------

    def set_active_plugin(self, plugin_name: str, config: dict | None = None) -> bool:
        """Activate a discovered plugin by name."""
        if not any(p.name == plugin_name for p in self.discovered_plugins):
            self.logger.error("Plugin '%s' not found in discovered plugins", plugin_name)
            return False

        self._active_plugin = plugin_name
        self.logger.info("Activated capture plugin: %s", plugin_name)
        return True

    # ------------------------------------------------------------------
    # Frame capture
    # ------------------------------------------------------------------

    def capture_frame(self, region_data: dict) -> np.ndarray | None:
        """Capture a frame using the active backend.

        Returns a numpy array (BGR, uint8) or *None* on failure.
        Falls back to PIL screenshot if the GPU backend fails or is inactive.
        """
        frame: np.ndarray | None = None

        if self._active_plugin in ("bettercam_capture_gpu", "dxcam_capture_gpu"):
            frame = self._capture_bettercam(region_data)

        # PIL fallback — always available
        if frame is None:
            frame = self._capture_pil(region_data)

        return frame

    # -- backend helpers ------------------------------------------------

    def _capture_bettercam(self, region_data: dict) -> np.ndarray | None:
        x, y = region_data['x'], region_data['y']
        w, h = region_data['width'], region_data['height']
        monitor_id = region_data.get('monitor_id', 0)
        target_region = (x, y, x + w, y + h)

        if not self._bettercam_streaming:
            self._start_bettercam_stream(monitor_id, target_region)
            if not self._bettercam_streaming:
                return None

        if self._bettercam_region != target_region:
            self._start_bettercam_stream(monitor_id, target_region)

        try:
            frame = self._bettercam_camera.get_latest_frame()
            if frame is not None:
                return frame
        except Exception as e:
            self.logger.warning("BetterCam get_latest_frame failed: %s", e)
            self._stop_bettercam_stream()

        return None

    def _start_bettercam_stream(self, monitor_id: int, region: tuple[int, ...]) -> None:
        """Start (or restart) BetterCam in continuous-capture mode."""
        import time

        self._stop_bettercam_stream()

        try:
            import bettercam

            if self._bettercam_camera is None:
                self._bettercam_camera = bettercam.create(
                    output_idx=monitor_id, output_color="BGR",
                )
                if self._bettercam_camera is None:
                    self.logger.error("BetterCam camera creation returned None")
                    return

            self._bettercam_camera.start(region=region, target_fps=60)
            self._bettercam_streaming = True
            self._bettercam_region = region

            time.sleep(0.15)
            for _ in range(3):
                self._bettercam_camera.get_latest_frame()
                time.sleep(0.03)

            self.logger.info(
                "BetterCam streaming started (monitor=%d, region=%s)",
                monitor_id, region,
            )
        except Exception as e:
            self.logger.error("Failed to start BetterCam stream: %s", e)
            self._bettercam_streaming = False

    def _stop_bettercam_stream(self) -> None:
        """Stop the BetterCam streaming capture."""
        if self._bettercam_camera is not None and self._bettercam_streaming:
            try:
                self._bettercam_camera.stop()
            except Exception:
                pass
        self._bettercam_streaming = False
        self._bettercam_region = None

    def force_refresh(self, monitor_id: int = 0) -> None:
        """Stop the BetterCam stream so the next capture starts a fresh one.

        Does NOT release the camera -- BetterCam uses a global singleton
        registry, so ``release()`` + ``create()`` returns the same stale
        instance.  Stopping and restarting the stream is sufficient to
        get fresh DXGI frames.
        """
        self.logger.info("Force-refreshing BetterCam capture (monitor=%d)", monitor_id)
        self._stop_bettercam_stream()

    @staticmethod
    def _capture_pil(region_data: dict) -> np.ndarray | None:
        from app.capture.pil_screenshot import capture_screenshot
        return capture_screenshot(region_data)

    # ------------------------------------------------------------------
    # Queries
    # ------------------------------------------------------------------

    def get_available_plugins(self, config_manager=None) -> list[str]:
        """Return plugin names, filtering GPU-only plugins in CPU mode."""
        all_plugins = [p.name for p in self.discovered_plugins]

        if not config_manager:
            return all_plugins

        runtime_mode = config_manager.get_runtime_mode()
        gpu_only = {"directx_capture", "bettercam_capture_gpu"}

        if runtime_mode == "cpu":
            filtered = [p for p in all_plugins if p not in gpu_only]
            if len(filtered) < len(all_plugins):
                self.logger.info(
                    "[CPU Mode] Filtered out GPU-only capture methods: %s",
                    set(all_plugins) - set(filtered),
                )
            return filtered

        return all_plugins

    def get_active_plugin(self) -> str | None:
        return self._active_plugin

    # ------------------------------------------------------------------
    # Cleanup
    # ------------------------------------------------------------------

    def cleanup(self) -> None:
        """Release backend resources."""
        self._stop_bettercam_stream()
        if self._bettercam_camera is not None:
            try:
                self._bettercam_camera.release()
            except Exception as e:
                self.logger.error("Error cleaning up BetterCam: %s", e)
            self._bettercam_camera = None

        self._active_plugin = None
