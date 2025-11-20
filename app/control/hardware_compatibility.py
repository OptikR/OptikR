"""
Hardware Compatibility Engine

Provides hardware detection, profiling, compatibility assessment, and model recommendation
functionality for the Real-Time Translation Overlay System.
"""

import platform
import subprocess
import json
import os
import psutil
import logging
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Tuple, Any, Callable
from enum import Enum
from pathlib import Path
import requests
import hashlib
from datetime import datetime

try:
    from ..models import PerformanceProfile, RuntimeMode
    from ..interfaces import ILogger
except ImportError:
    from models import PerformanceProfile, RuntimeMode
    from interfaces import ILogger


class HardwareType(Enum):
    """Hardware component types."""
    CPU = "cpu"
    GPU = "gpu"
    MEMORY = "memory"
    STORAGE = "storage"


class CompatibilityLevel(Enum):
    """Compatibility assessment levels."""
    EXCELLENT = "excellent"
    GOOD = "good"
    FAIR = "fair"
    POOR = "poor"
    INCOMPATIBLE = "incompatible"


class ModelType(Enum):
    """AI model types."""
    OCR = "ocr"
    TRANSLATION = "translation"
    PREPROCESSING = "preprocessing"


class VerificationStatus(Enum):
    """Model verification status."""
    VERIFIED = "verified"
    PENDING = "pending"
    FAILED = "failed"
    NOT_VERIFIED = "not_verified"


@dataclass
class HardwareRequirements:
    """Hardware requirements for AI models."""
    min_ram_mb: int
    min_vram_mb: int = 0
    requires_gpu: bool = False
    supported_architectures: List[str] = field(default_factory=lambda: ["x86_64"])
    cuda_compute_capability: Optional[str] = None
    supported_os: List[str] = field(default_factory=lambda: ["Windows", "Linux", "Darwin"])
    min_cpu_cores: int = 2
    min_cpu_frequency_ghz: float = 2.0
    
    def __post_init__(self):
        """Validate hardware requirements."""
        if self.min_ram_mb <= 0:
            raise ValueError("Minimum RAM must be positive")
        if self.min_vram_mb < 0:
            raise ValueError("Minimum VRAM cannot be negative")
        if self.min_cpu_cores <= 0:
            raise ValueError("Minimum CPU cores must be positive")
        if self.min_cpu_frequency_ghz <= 0:
            raise ValueError("Minimum CPU frequency must be positive")


@dataclass
class AIModelInfo:
    """Information about an AI model."""
    model_id: str
    name: str
    description: str
    model_type: ModelType
    size_mb: int
    download_url: str
    checksum: str
    signature: str
    hardware_requirements: HardwareRequirements
    supported_languages: List[str] = field(default_factory=list)
    accuracy_metrics: Dict[str, float] = field(default_factory=dict)
    license: str = "Unknown"
    version: str = "1.0.0"
    
    def __post_init__(self):
        """Validate model information."""
        if not self.model_id.strip():
            raise ValueError("Model ID cannot be empty")
        if not self.name.strip():
            raise ValueError("Model name cannot be empty")
        if self.size_mb <= 0:
            raise ValueError("Model size must be positive")
        if not self.download_url.strip():
            raise ValueError("Download URL cannot be empty")


@dataclass
class InstalledModel:
    """Information about an installed AI model."""
    model_info: AIModelInfo
    installation_path: str
    installation_date: datetime
    verification_status: VerificationStatus
    performance_metrics: Dict[str, float] = field(default_factory=dict)
    last_used: Optional[datetime] = None
    
    def __post_init__(self):
        """Validate installed model information."""
        if not self.installation_path.strip():
            raise ValueError("Installation path cannot be empty")


@dataclass
class HardwareProfile:
    """System hardware profile."""
    cpu_info: Dict[str, Any]
    gpu_info: List[Dict[str, Any]]
    memory_info: Dict[str, Any]
    storage_info: Dict[str, Any]
    os_info: Dict[str, Any]
    architecture: str
    
    @property
    def total_ram_gb(self) -> float:
        """Get total RAM in GB."""
        return self.memory_info.get("total_mb", 0) / 1024.0
    
    @property
    def has_gpu(self) -> bool:
        """Check if system has dedicated GPU."""
        return len(self.gpu_info) > 0 and any(
            gpu.get("dedicated", False) for gpu in self.gpu_info
        )
    
    @property
    def has_cuda_gpu(self) -> bool:
        """Check if system has CUDA-capable GPU."""
        return any(
            gpu.get("vendor", "").lower() == "nvidia" and gpu.get("cuda_capable", False)
            for gpu in self.gpu_info
        )
    
    @property
    def cpu_cores(self) -> int:
        """Get number of CPU cores."""
        return self.cpu_info.get("cores", 1)
    
    @property
    def cpu_frequency_ghz(self) -> float:
        """Get CPU frequency in GHz."""
        return self.cpu_info.get("frequency_mhz", 2000) / 1000.0


@dataclass
class CompatibilityResult:
    """Result of compatibility assessment."""
    is_compatible: bool
    compatibility_level: CompatibilityLevel
    missing_requirements: List[str]
    warnings: List[str]
    recommended_alternatives: List[AIModelInfo] = field(default_factory=list)
    performance_estimate: Optional[Dict[str, float]] = None
    
    @property
    def compatibility_score(self) -> float:
        """Get compatibility score (0.0 to 1.0)."""
        score_map = {
            CompatibilityLevel.EXCELLENT: 1.0,
            CompatibilityLevel.GOOD: 0.8,
            CompatibilityLevel.FAIR: 0.6,
            CompatibilityLevel.POOR: 0.4,
            CompatibilityLevel.INCOMPATIBLE: 0.0
        }
        return score_map.get(self.compatibility_level, 0.0)


@dataclass
class InstallationResult:
    """Result of model installation."""
    success: bool
    model_id: str
    installation_path: Optional[str] = None
    error_message: Optional[str] = None
    verification_result: Optional[bool] = None
    download_time_seconds: float = 0.0
    installation_time_seconds: float = 0.0


@dataclass
class PerformanceEstimate:
    """Performance estimate for a model on specific hardware."""
    estimated_fps: float
    estimated_latency_ms: float
    estimated_memory_usage_mb: float
    estimated_vram_usage_mb: float
    confidence: float  # 0.0 to 1.0
    
    def __post_init__(self):
        """Validate performance estimate."""
        if not 0.0 <= self.confidence <= 1.0:
            raise ValueError("Confidence must be between 0.0 and 1.0")


class HardwareDetector:
    """Hardware detection and profiling system."""
    
    def __init__(self, logger: Optional[ILogger] = None):
        """Initialize hardware detector.
        
        Args:
            logger: Optional logger for debugging
        """
        self.logger = logger or logging.getLogger(__name__)
    
    def detect_hardware_profile(self) -> HardwareProfile:
        """Detect and create comprehensive hardware profile.
        
        Returns:
            HardwareProfile with detected system information
        """
        try:
            cpu_info = self._detect_cpu_info()
            gpu_info = self._detect_gpu_info()
            memory_info = self._detect_memory_info()
            storage_info = self._detect_storage_info()
            os_info = self._detect_os_info()
            architecture = platform.machine()
            
            profile = HardwareProfile(
                cpu_info=cpu_info,
                gpu_info=gpu_info,
                memory_info=memory_info,
                storage_info=storage_info,
                os_info=os_info,
                architecture=architecture
            )
            
            self.logger.info(f"Hardware profile detected: {cpu_info['name']}, "
                           f"{len(gpu_info)} GPU(s), {profile.total_ram_gb:.1f}GB RAM")
            
            return profile
            
        except Exception as e:
            self.logger.error(f"Error detecting hardware profile: {e}")
            # Return minimal profile on error
            return HardwareProfile(
                cpu_info={"name": "Unknown", "cores": 2, "frequency_mhz": 2000},
                gpu_info=[],
                memory_info={"total_mb": 4096, "available_mb": 2048},
                storage_info={"total_gb": 100, "available_gb": 50},
                os_info={"name": platform.system(), "version": platform.version()},
                architecture=platform.machine()
            )
    
    def _detect_cpu_info(self) -> Dict[str, Any]:
        """Detect CPU information.
        
        Returns:
            Dictionary with CPU details
        """
        try:
            cpu_info = {
                "name": platform.processor() or "Unknown CPU",
                "cores": psutil.cpu_count(logical=False) or 2,
                "logical_cores": psutil.cpu_count(logical=True) or 4,
                "frequency_mhz": 2000,  # Default fallback
                "architecture": platform.machine(),
                "vendor": "Unknown"
            }
            
            # Try to get CPU frequency
            try:
                freq_info = psutil.cpu_freq()
                if freq_info:
                    cpu_info["frequency_mhz"] = freq_info.current or freq_info.max or 2000
            except Exception:
                pass
            
            # Try to detect CPU vendor and features
            try:
                if platform.system() == "Windows":
                    result = subprocess.run(
                        ["wmic", "cpu", "get", "Name,Manufacturer", "/format:csv"],
                        capture_output=True, text=True, timeout=10
                    )
                    if result.returncode == 0:
                        lines = result.stdout.strip().split('\n')
                        for line in lines[1:]:  # Skip header
                            parts = line.split(',')
                            if len(parts) >= 3:
                                cpu_info["vendor"] = parts[1].strip()
                                cpu_info["name"] = parts[2].strip()
                                break
                elif platform.system() == "Linux":
                    with open("/proc/cpuinfo", "r") as f:
                        for line in f:
                            if line.startswith("model name"):
                                cpu_info["name"] = line.split(":", 1)[1].strip()
                            elif line.startswith("vendor_id"):
                                cpu_info["vendor"] = line.split(":", 1)[1].strip()
            except Exception:
                pass
            
            return cpu_info
            
        except Exception as e:
            self.logger.error(f"Error detecting CPU info: {e}")
            return {
                "name": "Unknown CPU",
                "cores": 2,
                "logical_cores": 4,
                "frequency_mhz": 2000,
                "architecture": platform.machine(),
                "vendor": "Unknown"
            }
    
    def _detect_gpu_info(self) -> List[Dict[str, Any]]:
        """Detect GPU information.
        
        Returns:
            List of GPU information dictionaries
        """
        gpus = []
        
        try:
            # Try NVIDIA GPUs first
            nvidia_gpus = self._detect_nvidia_gpus()
            gpus.extend(nvidia_gpus)
            
            # Try to detect other GPUs (AMD, Intel)
            if platform.system() == "Windows":
                try:
                    result = subprocess.run(
                        ["wmic", "path", "win32_VideoController", "get", 
                         "Name,AdapterRAM,DriverVersion", "/format:csv"],
                        capture_output=True, text=True, timeout=15
                    )
                    if result.returncode == 0:
                        lines = result.stdout.strip().split('\n')
                        for line in lines[1:]:  # Skip header
                            parts = line.split(',')
                            if len(parts) >= 4 and parts[2].strip():
                                name = parts[3].strip()
                                # Skip if already detected by NVIDIA detection
                                if any(gpu["name"].lower() in name.lower() for gpu in gpus):
                                    continue
                                
                                gpu_info = {
                                    "name": name,
                                    "vendor": self._detect_gpu_vendor(name),
                                    "memory_mb": 0,
                                    "dedicated": True,
                                    "cuda_capable": False,
                                    "driver_version": parts[2].strip() if len(parts) > 2 else "Unknown"
                                }
                                
                                # Try to parse memory
                                try:
                                    if parts[1].strip():
                                        memory_bytes = int(parts[1].strip())
                                        gpu_info["memory_mb"] = memory_bytes // (1024 * 1024)
                                except (ValueError, IndexError):
                                    pass
                                
                                gpus.append(gpu_info)
                except Exception as e:
                    self.logger.warning(f"Error detecting Windows GPUs: {e}")
            
            # If no GPUs detected, add integrated graphics placeholder
            if not gpus:
                gpus.append({
                    "name": "Integrated Graphics",
                    "vendor": "Unknown",
                    "memory_mb": 0,
                    "dedicated": False,
                    "cuda_capable": False,
                    "driver_version": "Unknown"
                })
            
            return gpus
            
        except Exception as e:
            self.logger.error(f"Error detecting GPU info: {e}")
            return [{
                "name": "Unknown GPU",
                "vendor": "Unknown",
                "memory_mb": 0,
                "dedicated": False,
                "cuda_capable": False,
                "driver_version": "Unknown"
            }]
    
    def _detect_nvidia_gpus(self) -> List[Dict[str, Any]]:
        """Detect NVIDIA GPUs using nvidia-smi.
        
        Returns:
            List of NVIDIA GPU information
        """
        gpus = []
        
        try:
            result = subprocess.run(
                ["nvidia-smi", "--query-gpu=name,memory.total,driver_version,compute_cap",
                 "--format=csv,noheader,nounits"],
                capture_output=True, text=True, timeout=10
            )
            
            if result.returncode == 0:
                lines = result.stdout.strip().split('\n')
                for line in lines:
                    parts = [p.strip() for p in line.split(',')]
                    if len(parts) >= 3:
                        gpu_info = {
                            "name": parts[0],
                            "vendor": "NVIDIA",
                            "memory_mb": int(parts[1]) if parts[1].isdigit() else 0,
                            "dedicated": True,
                            "cuda_capable": True,
                            "driver_version": parts[2] if len(parts) > 2 else "Unknown",
                            "compute_capability": parts[3] if len(parts) > 3 else "Unknown"
                        }
                        gpus.append(gpu_info)
                        
        except (subprocess.TimeoutExpired, FileNotFoundError, subprocess.CalledProcessError):
            # nvidia-smi not available or failed
            pass
        except Exception as e:
            self.logger.warning(f"Error detecting NVIDIA GPUs: {e}")
        
        return gpus
    
    def _detect_gpu_vendor(self, gpu_name: str) -> str:
        """Detect GPU vendor from name.
        
        Args:
            gpu_name: GPU name string
            
        Returns:
            Vendor name
        """
        name_lower = gpu_name.lower()
        if "nvidia" in name_lower or "geforce" in name_lower or "quadro" in name_lower:
            return "NVIDIA"
        elif "amd" in name_lower or "radeon" in name_lower:
            return "AMD"
        elif "intel" in name_lower:
            return "Intel"
        else:
            return "Unknown"
    
    def _detect_memory_info(self) -> Dict[str, Any]:
        """Detect memory information.
        
        Returns:
            Dictionary with memory details
        """
        try:
            memory = psutil.virtual_memory()
            swap = psutil.swap_memory()
            
            return {
                "total_mb": memory.total // (1024 * 1024),
                "available_mb": memory.available // (1024 * 1024),
                "used_mb": memory.used // (1024 * 1024),
                "percent_used": memory.percent,
                "swap_total_mb": swap.total // (1024 * 1024),
                "swap_used_mb": swap.used // (1024 * 1024)
            }
            
        except Exception as e:
            self.logger.error(f"Error detecting memory info: {e}")
            return {
                "total_mb": 4096,
                "available_mb": 2048,
                "used_mb": 2048,
                "percent_used": 50.0,
                "swap_total_mb": 0,
                "swap_used_mb": 0
            }
    
    def _detect_storage_info(self) -> Dict[str, Any]:
        """Detect storage information.
        
        Returns:
            Dictionary with storage details
        """
        try:
            # Get disk usage for current drive
            disk_usage = psutil.disk_usage('/')
            
            return {
                "total_gb": disk_usage.total // (1024 * 1024 * 1024),
                "available_gb": disk_usage.free // (1024 * 1024 * 1024),
                "used_gb": disk_usage.used // (1024 * 1024 * 1024),
                "percent_used": (disk_usage.used / disk_usage.total) * 100
            }
            
        except Exception as e:
            self.logger.error(f"Error detecting storage info: {e}")
            return {
                "total_gb": 100,
                "available_gb": 50,
                "used_gb": 50,
                "percent_used": 50.0
            }
    
    def _detect_os_info(self) -> Dict[str, Any]:
        """Detect operating system information.
        
        Returns:
            Dictionary with OS details
        """
        try:
            return {
                "name": platform.system(),
                "version": platform.version(),
                "release": platform.release(),
                "architecture": platform.architecture()[0],
                "machine": platform.machine(),
                "python_version": platform.python_version()
            }
            
        except Exception as e:
            self.logger.error(f"Error detecting OS info: {e}")
            return {
                "name": "Unknown",
                "version": "Unknown",
                "release": "Unknown",
                "architecture": "Unknown",
                "machine": "Unknown",
                "python_version": platform.python_version()
            }


class CompatibilityEngine:
    """Hardware compatibility assessment engine."""
    
    def __init__(self, hardware_detector: HardwareDetector, logger: Optional[ILogger] = None):
        """Initialize compatibility engine.
        
        Args:
            hardware_detector: Hardware detection system
            logger: Optional logger for debugging
        """
        self.hardware_detector = hardware_detector
        self.logger = logger or logging.getLogger(__name__)
        self._hardware_profile = None
    
    def assess_hardware(self) -> HardwareProfile:
        """Assess current hardware and return profile.
        
        Returns:
            HardwareProfile with current system information
        """
        if self._hardware_profile is None:
            self._hardware_profile = self.hardware_detector.detect_hardware_profile()
        return self._hardware_profile
    
    def check_model_compatibility(self, model: AIModelInfo, 
                                hardware: Optional[HardwareProfile] = None) -> CompatibilityResult:
        """Check compatibility of model with hardware.
        
        Args:
            model: AI model to check compatibility for
            hardware: Hardware profile (uses current if None)
            
        Returns:
            CompatibilityResult with assessment details
        """
        if hardware is None:
            hardware = self.assess_hardware()
        
        try:
            missing_requirements = []
            warnings = []
            
            # Check RAM requirements
            required_ram_gb = model.hardware_requirements.min_ram_mb / 1024.0
            if hardware.total_ram_gb < required_ram_gb:
                missing_requirements.append(
                    f"Insufficient RAM: {required_ram_gb:.1f}GB required, "
                    f"{hardware.total_ram_gb:.1f}GB available"
                )
            elif hardware.total_ram_gb < required_ram_gb * 1.5:
                warnings.append(
                    f"Low RAM: {required_ram_gb:.1f}GB required, "
                    f"{hardware.total_ram_gb:.1f}GB available (recommended: {required_ram_gb * 1.5:.1f}GB)"
                )
            
            # Check GPU requirements
            if model.hardware_requirements.requires_gpu:
                if not hardware.has_gpu:
                    missing_requirements.append("Dedicated GPU required but not found")
                elif model.hardware_requirements.min_vram_mb > 0:
                    max_vram = max((gpu.get("memory_mb", 0) for gpu in hardware.gpu_info), default=0)
                    if max_vram < model.hardware_requirements.min_vram_mb:
                        missing_requirements.append(
                            f"Insufficient VRAM: {model.hardware_requirements.min_vram_mb}MB required, "
                            f"{max_vram}MB available"
                        )
            
            # Check CUDA requirements
            if model.hardware_requirements.cuda_compute_capability:
                if not hardware.has_cuda_gpu:
                    missing_requirements.append("CUDA-capable GPU required but not found")
            
            # Check CPU requirements
            if hardware.cpu_cores < model.hardware_requirements.min_cpu_cores:
                missing_requirements.append(
                    f"Insufficient CPU cores: {model.hardware_requirements.min_cpu_cores} required, "
                    f"{hardware.cpu_cores} available"
                )
            
            if hardware.cpu_frequency_ghz < model.hardware_requirements.min_cpu_frequency_ghz:
                warnings.append(
                    f"Low CPU frequency: {model.hardware_requirements.min_cpu_frequency_ghz:.1f}GHz recommended, "
                    f"{hardware.cpu_frequency_ghz:.1f}GHz available"
                )
            
            # Check OS compatibility
            current_os = hardware.os_info.get("name", "Unknown")
            if current_os not in model.hardware_requirements.supported_os:
                missing_requirements.append(
                    f"Unsupported OS: {current_os} (supported: {', '.join(model.hardware_requirements.supported_os)})"
                )
            
            # Check architecture compatibility
            if hardware.architecture not in model.hardware_requirements.supported_architectures:
                missing_requirements.append(
                    f"Unsupported architecture: {hardware.architecture} "
                    f"(supported: {', '.join(model.hardware_requirements.supported_architectures)})"
                )
            
            # Determine compatibility level
            is_compatible = len(missing_requirements) == 0
            
            if not is_compatible:
                compatibility_level = CompatibilityLevel.INCOMPATIBLE
            elif len(warnings) == 0:
                compatibility_level = CompatibilityLevel.EXCELLENT
            elif len(warnings) <= 2:
                compatibility_level = CompatibilityLevel.GOOD
            else:
                compatibility_level = CompatibilityLevel.FAIR
            
            # Generate performance estimate
            performance_estimate = self._estimate_performance(model, hardware) if is_compatible else None
            
            result = CompatibilityResult(
                is_compatible=is_compatible,
                compatibility_level=compatibility_level,
                missing_requirements=missing_requirements,
                warnings=warnings,
                performance_estimate=performance_estimate
            )
            
            self.logger.info(f"Compatibility check for {model.name}: {compatibility_level.value}")
            
            return result
            
        except Exception as e:
            self.logger.error(f"Error checking model compatibility: {e}")
            return CompatibilityResult(
                is_compatible=False,
                compatibility_level=CompatibilityLevel.INCOMPATIBLE,
                missing_requirements=[f"Error during compatibility check: {e}"],
                warnings=[]
            )
    
    def recommend_optimal_models(self, model_type: ModelType, 
                               available_models: List[AIModelInfo],
                               hardware: Optional[HardwareProfile] = None) -> List[Tuple[AIModelInfo, CompatibilityResult]]:
        """Recommend optimal models for given hardware.
        
        Args:
            model_type: Type of models to recommend
            available_models: List of available models to choose from
            hardware: Hardware profile (uses current if None)
            
        Returns:
            List of (model, compatibility_result) tuples sorted by compatibility
        """
        if hardware is None:
            hardware = self.assess_hardware()
        
        try:
            # Filter models by type
            filtered_models = [m for m in available_models if m.model_type == model_type]
            
            # Check compatibility for each model
            model_results = []
            for model in filtered_models:
                compatibility = self.check_model_compatibility(model, hardware)
                if compatibility.is_compatible:
                    model_results.append((model, compatibility))
            
            # Sort by compatibility score (descending) and model size (ascending)
            model_results.sort(key=lambda x: (x[1].compatibility_score, -x[0].size_mb), reverse=True)
            
            self.logger.info(f"Recommended {len(model_results)} compatible {model_type.value} models")
            
            return model_results
            
        except Exception as e:
            self.logger.error(f"Error recommending models: {e}")
            return []
    
    def estimate_performance(self, model: AIModelInfo, 
                           hardware: Optional[HardwareProfile] = None) -> PerformanceEstimate:
        """Estimate performance for model on hardware.
        
        Args:
            model: AI model to estimate performance for
            hardware: Hardware profile (uses current if None)
            
        Returns:
            PerformanceEstimate with predicted metrics
        """
        if hardware is None:
            hardware = self.assess_hardware()
        
        return self._estimate_performance(model, hardware)
    
    def _estimate_performance(self, model: AIModelInfo, hardware: HardwareProfile) -> Dict[str, float]:
        """Internal performance estimation logic.
        
        Args:
            model: AI model
            hardware: Hardware profile
            
        Returns:
            Dictionary with performance estimates
        """
        try:
            # Base performance factors
            base_fps = 30.0
            base_latency = 100.0  # ms
            base_memory = model.hardware_requirements.min_ram_mb
            base_vram = model.hardware_requirements.min_vram_mb
            
            # CPU performance factor
            cpu_factor = min(hardware.cpu_cores / model.hardware_requirements.min_cpu_cores, 2.0)
            cpu_freq_factor = min(hardware.cpu_frequency_ghz / model.hardware_requirements.min_cpu_frequency_ghz, 1.5)
            
            # Memory factor
            memory_factor = min(hardware.total_ram_gb * 1024 / model.hardware_requirements.min_ram_mb, 2.0)
            
            # GPU factor
            gpu_factor = 1.0
            if model.hardware_requirements.requires_gpu and hardware.has_gpu:
                if hardware.has_cuda_gpu:
                    gpu_factor = 2.0  # CUDA acceleration
                else:
                    gpu_factor = 1.5  # GPU acceleration
            
            # Model size factor (larger models are slower)
            size_factor = max(0.5, 1.0 - (model.size_mb - 100) / 1000.0)
            
            # Calculate estimates
            performance_factor = cpu_factor * cpu_freq_factor * memory_factor * gpu_factor * size_factor
            
            estimated_fps = base_fps * performance_factor
            estimated_latency = base_latency / performance_factor
            estimated_memory = base_memory * (1.0 + (performance_factor - 1.0) * 0.2)  # Slight memory increase for better performance
            estimated_vram = base_vram * gpu_factor if model.hardware_requirements.requires_gpu else 0
            
            # Confidence based on how well hardware exceeds requirements
            confidence = min(1.0, performance_factor / 2.0)
            
            return {
                "estimated_fps": max(1.0, estimated_fps),
                "estimated_latency_ms": max(10.0, estimated_latency),
                "estimated_memory_usage_mb": estimated_memory,
                "estimated_vram_usage_mb": estimated_vram,
                "confidence": confidence
            }
            
        except Exception as e:
            self.logger.error(f"Error estimating performance: {e}")
            return {
                "estimated_fps": 10.0,
                "estimated_latency_ms": 200.0,
                "estimated_memory_usage_mb": float(model.hardware_requirements.min_ram_mb),
                "estimated_vram_usage_mb": float(model.hardware_requirements.min_vram_mb),
                "confidence": 0.5
            }


class ModelDownloader:
    """Model download and installation system."""
    
    def __init__(self, models_dir: str = "models", logger: Optional[ILogger] = None):
        """Initialize model downloader.
        
        Args:
            models_dir: Directory to store downloaded models
            logger: Optional logger for debugging
        """
        self.models_dir = Path(models_dir)
        self.models_dir.mkdir(parents=True, exist_ok=True)
        self.logger = logger or logging.getLogger(__name__)
    
    def download_model(self, model: AIModelInfo, 
                      progress_callback: Optional[Callable[[float], None]] = None) -> InstallationResult:
        """Download and install a model.
        
        Args:
            model: Model to download
            progress_callback: Optional callback for progress updates (0.0 to 1.0)
            
        Returns:
            InstallationResult with download status
        """
        start_time = datetime.now()
        
        try:
            # Create model directory
            model_dir = self.models_dir / model.model_type.value / model.model_id
            model_dir.mkdir(parents=True, exist_ok=True)
            
            # Download model file
            model_file = model_dir / f"{model.model_id}.model"
            
            self.logger.info(f"Starting download of {model.name} from {model.download_url}")
            
            # Download with progress tracking
            response = requests.get(model.download_url, stream=True, timeout=30)
            response.raise_for_status()
            
            total_size = int(response.headers.get('content-length', 0))
            downloaded_size = 0
            
            with open(model_file, 'wb') as f:
                for chunk in response.iter_content(chunk_size=8192):
                    if chunk:
                        f.write(chunk)
                        downloaded_size += len(chunk)
                        
                        if progress_callback and total_size > 0:
                            progress = downloaded_size / total_size
                            progress_callback(progress)
            
            download_time = (datetime.now() - start_time).total_seconds()
            
            # Verify checksum
            if not self._verify_checksum(model_file, model.checksum):
                model_file.unlink()  # Delete corrupted file
                return InstallationResult(
                    success=False,
                    model_id=model.model_id,
                    error_message="Checksum verification failed",
                    download_time_seconds=download_time
                )
            
            # Create model metadata file
            metadata_file = model_dir / "metadata.json"
            metadata = {
                "model_info": {
                    "model_id": model.model_id,
                    "name": model.name,
                    "version": model.version,
                    "model_type": model.model_type.value,
                    "size_mb": model.size_mb
                },
                "installation": {
                    "installation_date": datetime.now().isoformat(),
                    "installation_path": str(model_dir),
                    "model_file": str(model_file),
                    "verification_status": VerificationStatus.VERIFIED.value
                }
            }
            
            with open(metadata_file, 'w') as f:
                json.dump(metadata, f, indent=2)
            
            total_time = (datetime.now() - start_time).total_seconds()
            
            self.logger.info(f"Successfully downloaded {model.name} in {total_time:.1f}s")
            
            return InstallationResult(
                success=True,
                model_id=model.model_id,
                installation_path=str(model_dir),
                verification_result=True,
                download_time_seconds=download_time,
                installation_time_seconds=total_time
            )
            
        except Exception as e:
            error_msg = f"Error downloading model {model.model_id}: {e}"
            self.logger.error(error_msg)
            
            return InstallationResult(
                success=False,
                model_id=model.model_id,
                error_message=error_msg,
                download_time_seconds=(datetime.now() - start_time).total_seconds()
            )
    
    def _verify_checksum(self, file_path: Path, expected_checksum: str) -> bool:
        """Verify file checksum.
        
        Args:
            file_path: Path to file to verify
            expected_checksum: Expected SHA256 checksum
            
        Returns:
            True if checksum matches, False otherwise
        """
        try:
            sha256_hash = hashlib.sha256()
            with open(file_path, "rb") as f:
                for chunk in iter(lambda: f.read(4096), b""):
                    sha256_hash.update(chunk)
            
            actual_checksum = sha256_hash.hexdigest()
            return actual_checksum.lower() == expected_checksum.lower()
            
        except Exception as e:
            self.logger.error(f"Error verifying checksum: {e}")
            return False
    
    def get_installed_models(self) -> List[InstalledModel]:
        """Get list of installed models.
        
        Returns:
            List of InstalledModel objects
        """
        installed_models = []
        
        try:
            for model_type_dir in self.models_dir.iterdir():
                if not model_type_dir.is_dir():
                    continue
                
                for model_dir in model_type_dir.iterdir():
                    if not model_dir.is_dir():
                        continue
                    
                    metadata_file = model_dir / "metadata.json"
                    if not metadata_file.exists():
                        continue
                    
                    try:
                        with open(metadata_file, 'r') as f:
                            metadata = json.load(f)
                        
                        model_info_data = metadata.get("model_info", {})
                        installation_data = metadata.get("installation", {})
                        
                        # Create minimal AIModelInfo from metadata
                        model_info = AIModelInfo(
                            model_id=model_info_data.get("model_id", "unknown"),
                            name=model_info_data.get("name", "Unknown Model"),
                            description="Installed model",
                            model_type=ModelType(model_info_data.get("model_type", "ocr")),
                            size_mb=model_info_data.get("size_mb", 0),
                            download_url="",
                            checksum="",
                            signature="",
                            hardware_requirements=HardwareRequirements(min_ram_mb=512)
                        )
                        
                        installed_model = InstalledModel(
                            model_info=model_info,
                            installation_path=installation_data.get("installation_path", str(model_dir)),
                            installation_date=datetime.fromisoformat(
                                installation_data.get("installation_date", datetime.now().isoformat())
                            ),
                            verification_status=VerificationStatus(
                                installation_data.get("verification_status", "not_verified")
                            )
                        )
                        
                        installed_models.append(installed_model)
                        
                    except Exception as e:
                        self.logger.warning(f"Error loading model metadata from {metadata_file}: {e}")
                        continue
            
            return installed_models
            
        except Exception as e:
            self.logger.error(f"Error getting installed models: {e}")
            return []


class HardwareCompatibilityEngine:
    """Main hardware compatibility engine combining all functionality."""
    
    def __init__(self, models_dir: str = "models", logger: Optional[ILogger] = None):
        """Initialize hardware compatibility engine.
        
        Args:
            models_dir: Directory for model storage
            logger: Optional logger for debugging
        """
        self.logger = logger or logging.getLogger(__name__)
        self.hardware_detector = HardwareDetector(logger)
        self.compatibility_engine = CompatibilityEngine(self.hardware_detector, logger)
        self.model_downloader = ModelDownloader(models_dir, logger)
        
        # Cache for hardware profile
        self._hardware_profile = None
    
    def get_hardware_profile(self) -> HardwareProfile:
        """Get current hardware profile.
        
        Returns:
            HardwareProfile with system information
        """
        if self._hardware_profile is None:
            self._hardware_profile = self.compatibility_engine.assess_hardware()
        return self._hardware_profile
    
    def check_model_compatibility(self, model: AIModelInfo) -> CompatibilityResult:
        """Check if model is compatible with current hardware.
        
        Args:
            model: Model to check compatibility for
            
        Returns:
            CompatibilityResult with assessment
        """
        return self.compatibility_engine.check_model_compatibility(model)
    
    def get_recommended_models(self, model_type: ModelType, 
                             available_models: List[AIModelInfo]) -> List[Tuple[AIModelInfo, CompatibilityResult]]:
        """Get recommended models for current hardware.
        
        Args:
            model_type: Type of models to recommend
            available_models: Available models to choose from
            
        Returns:
            List of recommended (model, compatibility) pairs
        """
        return self.compatibility_engine.recommend_optimal_models(model_type, available_models)
    
    def download_model(self, model: AIModelInfo, 
                      progress_callback: Optional[Callable[[float], None]] = None) -> InstallationResult:
        """Download and install a model.
        
        Args:
            model: Model to download
            progress_callback: Optional progress callback
            
        Returns:
            InstallationResult with download status
        """
        return self.model_downloader.download_model(model, progress_callback)
    
    def get_installed_models(self) -> List[InstalledModel]:
        """Get list of installed models.
        
        Returns:
            List of installed models
        """
        return self.model_downloader.get_installed_models()
    
    def estimate_model_performance(self, model: AIModelInfo) -> Dict[str, float]:
        """Estimate performance for model on current hardware.
        
        Args:
            model: Model to estimate performance for
            
        Returns:
            Dictionary with performance estimates
        """
        return self.compatibility_engine.estimate_performance(model)
    
    def refresh_hardware_profile(self) -> HardwareProfile:
        """Refresh hardware profile detection.
        
        Returns:
            Updated HardwareProfile
        """
        self._hardware_profile = None
        return self.get_hardware_profile()