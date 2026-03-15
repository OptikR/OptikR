"""
Centralized hardware-based feature gating system.

Provides a single source of truth for which features require GPU hardware,
automatically disabling GPU-only features when running in CPU mode.
"""

import json
import logging
from dataclasses import dataclass
from enum import Enum
from typing import Any

logger = logging.getLogger(__name__)


class GatedFeature(Enum):
    """Enumerates all features subject to hardware gating."""
    GPU_MEMORY_OPTIMIZATION = "gpu_memory_optimization"
    BETTERCAM_CAPTURE = "bettercam_capture"
    EASYOCR = "easyocr"
    PADDLEOCR = "paddleocr"
    MOKURO = "mokuro"
    MARIANMT_GPU = "marianmt_gpu"
    QWEN3_VL = "qwen3_vl"


class HardwareRequirement(Enum):
    """Classifies the hardware requirement level for each feature."""
    GPU = "gpu"
    CUDA = "cuda"
    CPU = "cpu"


@dataclass
class FeatureGateEntry:
    """Stores the metadata for a single gated feature."""
    feature: GatedFeature
    requirement: HardwareRequirement
    config_key: str
    description: str


class HardwareCapabilityGate:
    """Central gating logic for hardware-dependent features."""

    def __init__(self, config_manager):
        """Initialize with config manager. Builds the feature registry."""
        self._config_manager = config_manager
        self._registry: dict[GatedFeature, FeatureGateEntry] = self._build_registry()

    def _build_registry(self) -> dict[GatedFeature, FeatureGateEntry]:
        """Build the feature-to-requirements mapping."""
        return {
            GatedFeature.GPU_MEMORY_OPTIMIZATION: FeatureGateEntry(
                feature=GatedFeature.GPU_MEMORY_OPTIMIZATION,
                requirement=HardwareRequirement.CUDA,
                config_key="experimental.gpu_memory_optimization",
                description="GPU Memory Optimization (requires CUDA)",
            ),
            GatedFeature.BETTERCAM_CAPTURE: FeatureGateEntry(
                feature=GatedFeature.BETTERCAM_CAPTURE,
                requirement=HardwareRequirement.GPU,
                config_key="capture.method",
                description="BetterCam GPU capture (DXGI Desktop Duplication)",
            ),
            GatedFeature.EASYOCR: FeatureGateEntry(
                feature=GatedFeature.EASYOCR,
                requirement=HardwareRequirement.GPU,
                config_key="ocr.engine",
                description="EasyOCR engine (GPU-accelerated)",
            ),
            GatedFeature.PADDLEOCR: FeatureGateEntry(
                feature=GatedFeature.PADDLEOCR,
                requirement=HardwareRequirement.GPU,
                config_key="ocr.engine",
                description="PaddleOCR engine (GPU-accelerated)",
            ),
            GatedFeature.MOKURO: FeatureGateEntry(
                feature=GatedFeature.MOKURO,
                requirement=HardwareRequirement.GPU,
                config_key="ocr.engine",
                description="Mokuro OCR engine (GPU-accelerated)",
            ),
            GatedFeature.MARIANMT_GPU: FeatureGateEntry(
                feature=GatedFeature.MARIANMT_GPU,
                requirement=HardwareRequirement.GPU,
                config_key="translation.gpu_enabled",
                description="MarianMT GPU translation variant",
            ),
            GatedFeature.QWEN3_VL: FeatureGateEntry(
                feature=GatedFeature.QWEN3_VL,
                requirement=HardwareRequirement.CUDA,
                config_key="vision.enabled",
                description="Qwen3-VL vision-language model (requires CUDA GPU)",
            ),
        }

    def get_effective_mode(self) -> str:
        """Return 'cpu' or 'gpu' - resolves 'auto' via config_manager.get_runtime_mode()."""
        return self._config_manager.get_runtime_mode()

    def is_available(self, feature: GatedFeature) -> bool:
        """Return True if the feature is available under the current effective mode."""
        if not isinstance(feature, GatedFeature):
            raise ValueError(f"Unknown feature: {feature}")
        entry = self._registry[feature]
        if entry.requirement == HardwareRequirement.CPU:
            return True
        effective = self.get_effective_mode()
        # GPU mode satisfies both GPU and CUDA requirements
        return effective == "gpu"

    def on_runtime_mode_changed(self, new_mode: str) -> list[GatedFeature]:
        """Called when runtime mode changes. If effective mode is 'cpu',
        disables all GPU features in config. Returns list of affected features."""
        # Resolve effective mode: if 'auto', delegate to config_manager
        if new_mode == "auto":
            effective = self._config_manager.detect_runtime_mode()
        elif new_mode in ("cpu", "gpu"):
            effective = new_mode
        else:
            effective = "cpu"

        affected: list[GatedFeature] = []
        if effective == "cpu":
            for feature, entry in self._registry.items():
                if entry.requirement in (HardwareRequirement.GPU, HardwareRequirement.CUDA):
                    self._disable_feature_in_config(entry)
                    affected.append(feature)
        return affected

    def _disable_feature_in_config(self, entry: FeatureGateEntry) -> None:
        """Disable a single feature in the config manager."""
        # For boolean config keys, set to False
        # For choice-based keys (ocr.engine, capture.method), set to a safe CPU default
        if entry.config_key == "ocr.engine":
            current = self._config_manager.get_setting(entry.config_key, "")
            feature_value_map = {
                GatedFeature.EASYOCR: "easyocr",
                GatedFeature.PADDLEOCR: "paddleocr",
                GatedFeature.MOKURO: "mokuro",
            }
            if current == feature_value_map.get(entry.feature):
                self._config_manager.set_setting(entry.config_key, "tesseract")
        elif entry.config_key == "capture.method":
            current = self._config_manager.get_setting(entry.config_key, "")
            if current in ("directx", "bettercam", "auto"):
                self._config_manager.set_setting(entry.config_key, "screenshot")
        elif entry.feature == GatedFeature.QWEN3_VL:
            self._config_manager.set_setting(entry.config_key, False)
            if self._config_manager.get_setting("pipeline.mode", "text") == "vision":
                self._config_manager.set_setting("pipeline.mode", "text")
        else:
            self._config_manager.set_setting(entry.config_key, False)

    def get_unavailable_features(self) -> list[GatedFeature]:
        """Return all features currently unavailable."""
        return [f for f in self._registry if not self.is_available(f)]

    def get_availability_map(self) -> dict[str, bool]:
        """Return {feature_id: is_available} for all gated features."""
        return {f.value: self.is_available(f) for f in self._registry}

    def get_gate_status(self) -> dict[str, Any]:
        """Return full serializable status including runtime_mode and per-feature availability."""
        mode_setting = self._config_manager.get_setting("performance.runtime_mode", "auto")
        features: dict[str, Any] = {}
        for feature, entry in self._registry.items():
            features[feature.value] = {
                "available": self.is_available(feature),
                "requirement": entry.requirement.value,
                "config_key": entry.config_key,
            }
        return {
            "runtime_mode": mode_setting,
            "effective_mode": self.get_effective_mode(),
            "features": features,
        }

    def configure_defaults(self, gpu_detected: bool) -> None:
        """Called by FirstRunWizard. If no GPU, disables all GPU features."""
        if not gpu_detected:
            for feature, entry in self._registry.items():
                if entry.requirement in (HardwareRequirement.GPU, HardwareRequirement.CUDA):
                    self._disable_feature_in_config(entry)


# Module-level singleton
_gate_instance: HardwareCapabilityGate | None = None


def get_hardware_gate(config_manager=None) -> HardwareCapabilityGate:
    """Get or create the singleton gate instance."""
    global _gate_instance
    if _gate_instance is None:
        if config_manager is None:
            from app.core.config import SimpleConfigManager
            config_manager = SimpleConfigManager()
        _gate_instance = HardwareCapabilityGate(config_manager)
    return _gate_instance


def reset_hardware_gate() -> None:
    """Reset singleton for testing."""
    global _gate_instance
    _gate_instance = None
