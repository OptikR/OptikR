"""
DiagnosticsWorker - Background thread for collecting system diagnostics.
"""

import logging
import sys
import platform
from pathlib import Path

from PyQt6.QtCore import QThread, pyqtSignal

logger = logging.getLogger(__name__)


class DiagnosticsWorker(QThread):
    """Worker thread for collecting system diagnostics in the background."""
    
    # Signals (diagnostics_ready avoids shadowing QThread.finished)
    diagnostics_ready = pyqtSignal(str)  # Emits diagnostics text when complete
    error = pyqtSignal(str)              # Emits error message if collection fails
    
    def __init__(self, config_manager: object | None = None, parent: object | None = None):
        """
        Initialize the diagnostics worker.
        
        Args:
            config_manager: Configuration manager instance for reading settings
            parent: Parent QObject
        """
        super().__init__(parent)
        self.config_manager = config_manager
    
    def run(self):
        """Collect diagnostics in background thread."""
        try:
            diagnostics_text = self._collect_diagnostics()
            self.diagnostics_ready.emit(diagnostics_text)
        except Exception as e:
            self.error.emit(str(e))
    
    def _collect_diagnostics(self) -> str:
        """
        Collect all system diagnostics information.
        
        Returns:
            str: Formatted diagnostics text
        """
        diagnostics = []
        
        # System information
        diagnostics.append("=== SYSTEM INFORMATION ===")
        diagnostics.append(f"Operating System: {platform.system()} {platform.release()}")
        diagnostics.append(f"Platform: {platform.platform()}")
        diagnostics.append(f"Architecture: {platform.machine()}")
        diagnostics.append(f"Processor: {platform.processor()}")
        diagnostics.append(f"Python Version: {sys.version.split()[0]}")
        diagnostics.append("")
        
        # PyQt6 information
        diagnostics.append("=== PYQT6 INFORMATION ===")
        try:
            from PyQt6.QtCore import QT_VERSION_STR, PYQT_VERSION_STR
            diagnostics.append(f"Qt Version: {QT_VERSION_STR}")
            diagnostics.append(f"PyQt6 Version: {PYQT_VERSION_STR}")
        except Exception:
            diagnostics.append("PyQt6 version information unavailable")
        diagnostics.append("")
        
        # PyTorch information
        diagnostics.append("=== PYTORCH INFORMATION ===")
        try:
            import torch
            diagnostics.append(f"PyTorch Version: {torch.__version__}")
            diagnostics.append(f"CUDA Available: {torch.cuda.is_available()}")
            if torch.cuda.is_available():
                diagnostics.append(f"CUDA Version: {torch.version.cuda}")
                diagnostics.append(f"GPU Count: {torch.cuda.device_count()}")
                if torch.cuda.device_count() > 0:
                    diagnostics.append(f"GPU 0: {torch.cuda.get_device_name(0)}")
                    diagnostics.append(f"GPU Memory: {torch.cuda.get_device_properties(0).total_memory / 1024**3:.1f} GB")
        except ImportError:
            diagnostics.append("PyTorch not installed")
        except Exception as e:
            logger.warning("Failed to get PyTorch info: %s", e)
            diagnostics.append(f"Error getting PyTorch info: {e}")
        diagnostics.append("")
        
        # Application paths (EXE-compatible)
        diagnostics.append("=== APPLICATION PATHS ===")
        try:
            from app.utils.path_utils import get_models_dir, get_cache_dir, get_logs_dir, get_dictionary_dir, get_config_file
            diagnostics.append(f"Working Directory: {Path.cwd()}")
            diagnostics.append(f"Config File: {get_config_file()}")
            diagnostics.append(f"Models Directory: {get_models_dir()}")
            diagnostics.append(f"Cache Directory: {get_cache_dir()}")
            diagnostics.append(f"Logs Directory: {get_logs_dir()}")
            diagnostics.append(f"Dictionary Directory: {get_dictionary_dir()}")
        except Exception as e:
            logger.warning("Failed to get application paths: %s", e)
            diagnostics.append(f"Error getting application paths: {e}")
        diagnostics.append("")
        
        # Configuration status
        diagnostics.append("=== CONFIGURATION STATUS ===")
        if self.config_manager:
            try:
                runtime_mode = self.config_manager.get_setting('performance.runtime_mode', 'unknown')
                diagnostics.append(f"Runtime Mode: {runtime_mode}")
                
                source_lang = self.config_manager.get_setting('translation.source_language', 'unknown')
                target_lang = self.config_manager.get_setting('translation.target_language', 'unknown')
                diagnostics.append(f"Languages: {source_lang} → {target_lang}")
                
                cache_enabled = self.config_manager.get_setting('storage.cache_enabled', True)
                diagnostics.append(f"Cache Enabled: {cache_enabled}")
            except Exception as e:
                logger.warning("Failed to read configuration: %s", e)
                diagnostics.append(f"Error reading configuration: {e}")
        else:
            diagnostics.append("Configuration manager not available")
        diagnostics.append("")
        
        # AMD Hardware information
        diagnostics.append("=== AMD HARDWARE INFORMATION ===")
        try:
            from app.utils.hardware_detection import HardwareDetector
            detector = HardwareDetector()
            
            # AMD CPU diagnostics
            amd_cpu = detector.get_amd_cpu_diagnostics()
            if amd_cpu:
                diagnostics.append(f"AMD CPU Detected: Yes")
                diagnostics.append(f"  Model: {amd_cpu['model']}")
                diagnostics.append(f"  Zen Generation: {amd_cpu['zen_generation']}")
                diagnostics.append(f"  Cores: {amd_cpu['cores']}")
                simd_str = ', '.join(amd_cpu['simd_support'])
                diagnostics.append(f"  SIMD Support: {simd_str}")
            else:
                diagnostics.append("AMD CPU Detected: No")
            
            # AMD GPU diagnostics
            amd_gpu = detector.get_amd_gpu_diagnostics()
            if amd_gpu:
                diagnostics.append(f"AMD GPU Detected: Yes")
                diagnostics.append(f"  Model: {amd_gpu['model']}")
                diagnostics.append(f"  Memory: {amd_gpu['memory_mb'] / 1024:.1f} GB")
                diagnostics.append(f"  Device Count: {amd_gpu['device_count']}")
                diagnostics.append(f"  ROCm Available: {'Yes' if amd_gpu.get('rocm_available', False) else 'No'}")
                if 'opencl_version' in amd_gpu:
                    diagnostics.append(f"  OpenCL Version: {amd_gpu['opencl_version']}")
            else:
                diagnostics.append("AMD GPU Detected: No")
            
            # GPU Backend
            backend = detector.get_active_gpu_backend()
            diagnostics.append(f"Active GPU Backend: {backend}")
            
            # SIMD Instructions
            simd_instructions = detector.get_enabled_simd_instructions()
            if simd_instructions:
                simd_str = ', '.join(simd_instructions)
                diagnostics.append(f"Enabled SIMD Instructions: {simd_str}")
            
        except ImportError:
            diagnostics.append("Hardware detection module not available")
        except Exception as e:
            logger.warning("Failed to get AMD hardware info: %s", e)
            diagnostics.append(f"Error getting AMD hardware info: {e}")
        diagnostics.append("")
        
        # Memory information
        diagnostics.append("=== MEMORY INFORMATION ===")
        try:
            import psutil
            memory = psutil.virtual_memory()
            diagnostics.append(f"Total Memory: {memory.total / 1024**3:.1f} GB")
            diagnostics.append(f"Available Memory: {memory.available / 1024**3:.1f} GB")
            diagnostics.append(f"Memory Usage: {memory.percent}%")
        except ImportError:
            diagnostics.append("psutil not installed (memory info unavailable)")
        except Exception as e:
            logger.warning("Failed to get memory info: %s", e)
            diagnostics.append(f"Error getting memory info: {e}")
        
        return "\n".join(diagnostics)
