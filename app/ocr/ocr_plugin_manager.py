"""
OCR Plugin Management System

This module provides comprehensive plugin management for OCR engines,
including plugin discovery, loading, registration, and lifecycle management.
"""

import os
import sys
import json
import importlib
import importlib.util
from pathlib import Path
from typing import Dict, Any, List, Optional, Set, Callable
import threading
import logging
from dataclasses import dataclass, field
from enum import Enum

from .ocr_engine_interface import (
    IOCREngine, OCREnginePlugin, OCREngineType, OCREngineStatus,
    OCRBenchmarkResult, OCREngineBenchmarker, OCRProcessingOptions
)
import sys
import os
sys.path.append(os.path.join(os.path.dirname(__file__), '..'))

try:
    from app.models import Frame, TextBlock, PerformanceProfile
    from app.interfaces import IPluginManager
except ImportError:
    from app.models import Frame, TextBlock, PerformanceProfile
    from app.interfaces import IPluginManager


class PluginLoadStatus(Enum):
    """Plugin loading status enumeration."""
    NOT_LOADED = "not_loaded"
    LOADING = "loading"
    LOADED = "loaded"
    FAILED = "failed"
    DISABLED = "disabled"


@dataclass
class PluginInfo:
    """Plugin information and metadata."""
    name: str
    version: str
    description: str
    author: str
    engine_type: OCREngineType
    plugin_path: str
    config_schema: Dict[str, Any] = field(default_factory=dict)
    dependencies: List[str] = field(default_factory=list)
    supported_platforms: List[str] = field(default_factory=lambda: ["windows", "linux", "macos"])
    min_python_version: str = "3.8"
    load_status: PluginLoadStatus = PluginLoadStatus.NOT_LOADED
    load_error: Optional[str] = None


class OCRPluginRegistry:
    """Registry for managing OCR engine plugins."""
    
    def __init__(self):
        """Initialize plugin registry."""
        self._plugins: Dict[str, PluginInfo] = {}
        self._loaded_engines: Dict[str, IOCREngine] = {}
        self._plugin_instances: Dict[str, OCREnginePlugin] = {}
        self._lock = threading.RLock()
        self._logger = logging.getLogger("ocr.plugin_registry")
        self._event_handlers: Dict[str, List[Callable]] = {
            "plugin_loaded": [],
            "plugin_unloaded": [],
            "plugin_failed": [],
            "engine_registered": [],
            "engine_unregistered": []
        }
    
    def register_plugin_info(self, plugin_info: PluginInfo) -> bool:
        """
        Register plugin information in the registry.
        
        Args:
            plugin_info: Plugin information to register
            
        Returns:
            True if registration successful
        """
        with self._lock:
            if plugin_info.name in self._plugins:
                self._logger.warning(f"Plugin {plugin_info.name} already registered, updating info")
            
            self._plugins[plugin_info.name] = plugin_info
            self._logger.info(f"Registered plugin info: {plugin_info.name} v{plugin_info.version}")
            return True
    
    def get_plugin_info(self, plugin_name: str) -> Optional[PluginInfo]:
        """Get plugin information by name."""
        with self._lock:
            return self._plugins.get(plugin_name)
    
    def get_all_plugins(self) -> Dict[str, PluginInfo]:
        """Get all registered plugin information."""
        with self._lock:
            return self._plugins.copy()
    
    def get_loaded_plugins(self) -> Dict[str, PluginInfo]:
        """Get information for loaded plugins only."""
        with self._lock:
            return {name: info for name, info in self._plugins.items() 
                   if info.load_status == PluginLoadStatus.LOADED}
    
    def get_available_engines(self) -> Dict[str, IOCREngine]:
        """Get all loaded and ready OCR engines."""
        with self._lock:
            return {name: engine for name, engine in self._loaded_engines.items() 
                   if engine.is_ready()}
    
    def get_engine(self, engine_name: str) -> Optional[IOCREngine]:
        """Get specific OCR engine by name."""
        with self._lock:
            return self._loaded_engines.get(engine_name)
    
    def is_engine_loaded(self, engine_name: str) -> bool:
        """
        Check if an OCR engine is loaded and ready.
        
        Args:
            engine_name: Name of engine to check
            
        Returns:
            True if engine is loaded and ready
        """
        with self._lock:
            plugin_info = self._plugins.get(engine_name)
            if not plugin_info:
                return False
            return plugin_info.load_status == PluginLoadStatus.LOADED
    
    def register_engine(self, engine: IOCREngine) -> bool:
        """
        Register a loaded OCR engine.
        
        Args:
            engine: OCR engine instance to register
            
        Returns:
            True if registration successful
        """
        with self._lock:
            if engine.engine_name in self._loaded_engines:
                self._logger.warning(f"Engine {engine.engine_name} already registered, replacing")
            
            self._loaded_engines[engine.engine_name] = engine
            self._logger.info(f"Registered OCR engine: {engine.engine_name}")
            self._trigger_event("engine_registered", engine.engine_name, engine)
            return True
    
    def unregister_engine(self, engine_name: str) -> bool:
        """
        Unregister an OCR engine.
        
        Args:
            engine_name: Name of engine to unregister
            
        Returns:
            True if unregistration successful
        """
        with self._lock:
            if engine_name in self._loaded_engines:
                engine = self._loaded_engines.pop(engine_name)
                self._logger.info(f"Unregistered OCR engine: {engine_name}")
                self._trigger_event("engine_unregistered", engine_name, engine)
                return True
            return False
    
    def add_event_handler(self, event_type: str, handler: Callable) -> None:
        """Add event handler for plugin/engine events."""
        if event_type in self._event_handlers:
            self._event_handlers[event_type].append(handler)
    
    def remove_event_handler(self, event_type: str, handler: Callable) -> None:
        """Remove event handler."""
        if event_type in self._event_handlers and handler in self._event_handlers[event_type]:
            self._event_handlers[event_type].remove(handler)
    
    def _trigger_event(self, event_type: str, *args, **kwargs) -> None:
        """Trigger event handlers."""
        for handler in self._event_handlers.get(event_type, []):
            try:
                handler(*args, **kwargs)
            except Exception as e:
                self._logger.error(f"Error in event handler for {event_type}: {e}")


class OCRPluginManager(IPluginManager):
    """Comprehensive OCR plugin management system."""
    
    def __init__(self, plugin_directories: Optional[List[str]] = None, config_manager=None):
        """
        Initialize OCR plugin manager.
        
        Args:
            plugin_directories: List of directories to search for plugins
            config_manager: Configuration manager for runtime settings
        """
        self.registry = OCRPluginRegistry()
        self.benchmarker = OCREngineBenchmarker()
        self._plugin_directories = plugin_directories or []
        self._default_config: Dict[str, Any] = {}
        self.config_manager = config_manager
        self._lock = threading.RLock()
        self._logger = logging.getLogger("ocr.plugin_manager")
        
        # Add default plugin directories
        self._add_default_plugin_directories()
    
    def _add_default_plugin_directories(self) -> None:
        """Add default plugin search directories."""
        # Current directory is dev/src/ocr
        current_dir = Path(__file__).parent
        
        # NEW PLUGIN SYSTEM: dev/plugins/ocr
        # Go up two levels: dev/src/ocr -> dev/src -> dev, then down to plugins/ocr
        self._plugin_directories.extend([
            str(current_dir.parent.parent / "plugins" / "ocr"),  # dev/plugins/ocr (NEW)
            str(current_dir / "plugins"),  # dev/src/ocr/plugins (legacy, if exists)
            str(current_dir / "engines"),  # dev/src/ocr/engines (old system, deprecated)
        ])
        
        # User plugins directory
        user_plugins = Path.home() / ".translation_system" / "plugins" / "ocr"
        self._plugin_directories.append(str(user_plugins))
    
    def discover_plugins(self) -> List[PluginInfo]:
        """
        Discover available plugins in configured directories.
        Only includes plugins whose dependencies are actually installed.
        Auto-generates missing plugin folders for installed packages.
        
        Returns:
            List of discovered plugin information
        """
        discovered_plugins = []
        
        # First, auto-generate missing plugins for installed packages
        self._auto_generate_missing_plugins()
        
        for directory in self._plugin_directories:
            if not os.path.exists(directory):
                continue
            
            self._logger.info(f"Scanning for plugins in: {directory}")
            
            for item in os.listdir(directory):
                item_path = os.path.join(directory, item)
                
                # Check for plugin manifest file
                manifest_path = os.path.join(item_path, "plugin.json")
                if os.path.isdir(item_path) and os.path.exists(manifest_path):
                    try:
                        plugin_info = self._load_plugin_manifest(manifest_path, item_path)
                        if plugin_info:
                            # Check if plugin dependencies are actually installed
                            if self._check_plugin_dependencies(plugin_info):
                                discovered_plugins.append(plugin_info)
                                self.registry.register_plugin_info(plugin_info)
                            else:
                                self._logger.info(f"Skipping plugin {plugin_info.name} - dependencies not installed")
                    except Exception as e:
                        self._logger.error(f"Failed to load plugin manifest {manifest_path}: {e}")
        
        self._logger.info(f"Discovered {len(discovered_plugins)} OCR plugins with installed dependencies")
        return discovered_plugins
    
    def _auto_generate_missing_plugins(self):
        """
        Auto-generate plugin folders for installed OCR packages that don't have plugins yet.
        Uses the universal plugin generator to create the necessary files.
        Skips packages that already have a plugin (even with different names).
        """
        try:
            # Use the universal plugin generator from workflow
            from app.workflow.universal_plugin_generator import PluginGenerator
            import importlib.util
            
            generator = PluginGenerator(output_dir="plugins")
            
            # Check which OCR packages are installed
            installed_engines = []
            
            # Check for each known engine
            engine_checks = {
                'manga_ocr': 'manga_ocr',
                'paddleocr': 'paddleocr',
                'tesseract': 'pytesseract',
                'easyocr': 'easyocr'
            }
            
            for engine_name, import_name in engine_checks.items():
                spec = importlib.util.find_spec(import_name)
                if spec is not None:
                    installed_engines.append((engine_name, import_name))
            
            # Get the main plugins directory (dev/plugins/ocr)
            main_plugin_dir = None
            for directory in self._plugin_directories:
                if 'plugins' in directory and 'ocr' in directory and 'src' not in directory:
                    main_plugin_dir = Path(directory)
                    break
            
            if not main_plugin_dir:
                return
            
            # First, scan existing plugins to see which packages they use
            existing_packages = set()
            if main_plugin_dir.exists():
                for item in main_plugin_dir.iterdir():
                    if item.is_dir():
                        plugin_json = item / "plugin.json"
                        if plugin_json.exists():
                            try:
                                with open(plugin_json, 'r', encoding='utf-8') as f:
                                    data = json.load(f)
                                    # Track which packages are used by existing plugins
                                    deps = data.get('dependencies', [])
                                    for dep in deps:
                                        # Normalize package names
                                        if dep in ['easyocr', 'torch', 'torchvision']:
                                            existing_packages.add('easyocr')
                                        elif dep in ['manga-ocr', 'manga_ocr']:
                                            existing_packages.add('manga_ocr')
                                        elif dep in ['paddleocr', 'paddlepaddle']:
                                            existing_packages.add('paddleocr')
                                        elif dep in ['pytesseract', 'tesseract-ocr']:
                                            existing_packages.add('tesseract')
                            except:
                                pass
            
            # For each installed engine, check if we should create a plugin
            for engine_name, import_name in installed_engines:
                # Skip if a plugin already exists for this package
                if engine_name in existing_packages:
                    self._logger.debug(f"Skipping {engine_name} - plugin already exists")
                    continue
                
                plugin_folder = main_plugin_dir / engine_name
                plugin_json_path = plugin_folder / "plugin.json"
                
                # If plugin folder doesn't exist or is incomplete, create it
                if not plugin_json_path.exists():
                    self._logger.info(f"Auto-generating plugin for installed package: {engine_name}")
                    
                    # Use universal generator to create plugin
                    success = generator.create_plugin_programmatically(
                        plugin_type='ocr',
                        name=engine_name,
                        display_name=engine_name.replace('_', ' ').title(),
                        description=f"OCR engine using {engine_name} library",
                        dependencies=[import_name],
                        settings={}
                    )
                    
                    if success:
                        self._logger.info(f"✓ Auto-generated plugin for {engine_name}")
                    else:
                        self._logger.warning(f"Failed to auto-generate plugin for {engine_name}")
        
        except Exception as e:
            self._logger.warning(f"Failed to auto-generate plugins: {e}")
    
    def _check_plugin_dependencies(self, plugin_info: PluginInfo) -> bool:
        """
        Check if all plugin dependencies are installed.
        
        Args:
            plugin_info: Plugin information with dependencies list
            
        Returns:
            True if all dependencies are installed, False otherwise
        """
        if not plugin_info.dependencies:
            return True
        
        import importlib.util
        
        # Map of package names to import names (some packages have different import names)
        package_import_map = {
            'easyocr': 'easyocr',
            'pytesseract': 'pytesseract',
            'tesseract-ocr': 'pytesseract',  # tesseract-ocr is installed separately, check pytesseract
            'paddleocr': 'paddleocr',
            'paddlepaddle': 'paddle',
            'manga-ocr': 'manga_ocr',
            'torch': 'torch',
            'torchvision': 'torchvision',
            'transformers': 'transformers',
            'opencv-python': 'cv2',  # opencv-python imports as cv2
            'numpy': 'numpy'
        }
        
        for dependency in plugin_info.dependencies:
            # Get the import name for this dependency
            import_name = package_import_map.get(dependency, dependency)
            
            # Check if the module can be imported
            spec = importlib.util.find_spec(import_name)
            if spec is None:
                self._logger.debug(f"Dependency {dependency} (import: {import_name}) not found for plugin {plugin_info.name}")
                return False
        
        return True
    
    def _load_plugin_manifest(self, manifest_path: str, plugin_path: str) -> Optional[PluginInfo]:
        """
        Load plugin manifest from JSON file.
        
        Args:
            manifest_path: Path to plugin.json manifest file
            plugin_path: Path to plugin directory
            
        Returns:
            Plugin information or None if invalid
        """
        try:
            with open(manifest_path, 'r', encoding='utf-8') as f:
                manifest_data = json.load(f)
            
            # Validate required fields
            required_fields = ["name", "version", "description", "author", "engine_type", "entry_point"]
            for field in required_fields:
                if field not in manifest_data:
                    raise ValueError(f"Missing required field: {field}")
            
            # Create plugin info
            plugin_info = PluginInfo(
                name=manifest_data["name"],
                version=manifest_data["version"],
                description=manifest_data["description"],
                author=manifest_data["author"],
                engine_type=OCREngineType(manifest_data["engine_type"]),
                plugin_path=plugin_path,
                config_schema=manifest_data.get("config_schema", {}),
                dependencies=manifest_data.get("dependencies", []),
                supported_platforms=manifest_data.get("supported_platforms", ["windows", "linux", "macos"]),
                min_python_version=manifest_data.get("min_python_version", "3.8")
            )
            
            return plugin_info
            
        except Exception as e:
            self._logger.error(f"Failed to parse plugin manifest {manifest_path}: {e}")
            return None
    
    def load_plugin(self, plugin_name: str, config: Optional[Dict[str, Any]] = None) -> bool:
        """
        Load and initialize a plugin.
        
        Args:
            plugin_name: Name of plugin to load
            config: Optional configuration for plugin initialization
            
        Returns:
            True if plugin loaded successfully
        """
        with self._lock:
            plugin_info = self.registry.get_plugin_info(plugin_name)
            if not plugin_info:
                self._logger.error(f"Plugin {plugin_name} not found in registry")
                return False
            
            if plugin_info.load_status == PluginLoadStatus.LOADED:
                self._logger.info(f"Plugin {plugin_name} already loaded")
                return True
            
            try:
                plugin_info.load_status = PluginLoadStatus.LOADING
                
                # Load plugin module
                plugin_module = self._load_plugin_module(plugin_info)
                if not plugin_module:
                    raise ImportError(f"Failed to load plugin module for {plugin_name}")
                
                # Get engine class from module
                engine_class = getattr(plugin_module, "OCREngine", None)
                if not engine_class:
                    raise AttributeError(f"Plugin {plugin_name} does not define OCREngine class")
                
                # Create plugin instance
                plugin_instance = OCREnginePlugin(engine_class, plugin_info.__dict__)
                
                # Initialize plugin with engine-specific config
                plugin_config = config or self._default_config.copy()
                
                # Apply GPU configuration based on runtime mode
                use_gpu = self._should_use_gpu()
                plugin_config['gpu'] = use_gpu
                plugin_config['use_gpu'] = use_gpu  # Some engines use 'use_gpu' instead of 'gpu'
                self._logger.info(f"Configuring {plugin_name} with GPU={use_gpu}")
                
                # Apply engine-specific language code if available
                if hasattr(self, '_engine_languages') and plugin_name in self._engine_languages:
                    plugin_config['language'] = self._engine_languages[plugin_name]
                    self._logger.info(f"Using engine-specific language for {plugin_name}: {plugin_config['language']}")
                
                # Try to initialize with GPU first, fallback to CPU if it fails
                init_success = plugin_instance.initialize(plugin_config)
                
                if not init_success and use_gpu:
                    # GPU initialization failed, try CPU mode
                    self._logger.warning(f"GPU initialization failed for {plugin_name}, falling back to CPU mode")
                    print(f"[STARTUP] ⚠️ GPU initialization failed, retrying with CPU mode...")
                    plugin_config['gpu'] = False
                    plugin_config['use_gpu'] = False
                    init_success = plugin_instance.initialize(plugin_config)
                
                if not init_success:
                    raise RuntimeError(f"Failed to initialize plugin {plugin_name} (tried both GPU and CPU modes)")
                
                # Register plugin and engine
                self.registry._plugin_instances[plugin_name] = plugin_instance
                engine = plugin_instance.get_engine_instance()
                if engine:
                    self.registry.register_engine(engine)
                
                plugin_info.load_status = PluginLoadStatus.LOADED
                plugin_info.load_error = None
                
                self._logger.info(f"Successfully loaded plugin: {plugin_name}")
                self.registry._trigger_event("plugin_loaded", plugin_name, plugin_instance)
                return True
                
            except Exception as e:
                plugin_info.load_status = PluginLoadStatus.FAILED
                plugin_info.load_error = str(e)
                self._logger.error(f"Failed to load plugin {plugin_name}: {e}")
                self.registry._trigger_event("plugin_failed", plugin_name, e)
                return False
    
    def _load_plugin_module(self, plugin_info: PluginInfo):
        """
        Load plugin module from file system.
        
        Args:
            plugin_info: Plugin information
            
        Returns:
            Loaded module or None if failed
        """
        try:
            # Find main plugin file
            main_file = os.path.join(plugin_info.plugin_path, "__init__.py")
            if not os.path.exists(main_file):
                main_file = os.path.join(plugin_info.plugin_path, f"{plugin_info.name}.py")
            
            if not os.path.exists(main_file):
                raise FileNotFoundError(f"Plugin main file not found for {plugin_info.name}")
            
            # Load module
            spec = importlib.util.spec_from_file_location(plugin_info.name, main_file)
            if not spec or not spec.loader:
                raise ImportError(f"Failed to create module spec for {plugin_info.name}")
            
            module = importlib.util.module_from_spec(spec)
            sys.modules[f"ocr_plugin_{plugin_info.name}"] = module
            spec.loader.exec_module(module)
            
            return module
            
        except Exception as e:
            self._logger.error(f"Failed to load module for plugin {plugin_info.name}: {e}")
            return None
    
    def unload_plugin(self, plugin_name: str) -> bool:
        """
        Unload a plugin and clean up resources.
        
        Args:
            plugin_name: Name of plugin to unload
            
        Returns:
            True if plugin unloaded successfully
        """
        with self._lock:
            plugin_info = self.registry.get_plugin_info(plugin_name)
            if not plugin_info or plugin_info.load_status != PluginLoadStatus.LOADED:
                return False
            
            try:
                # Get plugin instance
                plugin_instance = self.registry._plugin_instances.get(plugin_name)
                if plugin_instance:
                    # Unregister engine
                    engine = plugin_instance.get_engine_instance()
                    if engine:
                        self.registry.unregister_engine(engine.engine_name)
                    
                    # Cleanup plugin
                    plugin_instance.cleanup()
                    del self.registry._plugin_instances[plugin_name]
                
                # Update status
                plugin_info.load_status = PluginLoadStatus.NOT_LOADED
                
                # Remove from sys.modules
                module_name = f"ocr_plugin_{plugin_name}"
                if module_name in sys.modules:
                    del sys.modules[module_name]
                
                self._logger.info(f"Successfully unloaded plugin: {plugin_name}")
                self.registry._trigger_event("plugin_unloaded", plugin_name)
                return True
                
            except Exception as e:
                self._logger.error(f"Failed to unload plugin {plugin_name}: {e}")
                return False
    
    def get_loaded_plugins(self) -> List[str]:
        """Get list of loaded plugin names."""
        return [name for name, info in self.registry.get_all_plugins().items() 
                if info.load_status == PluginLoadStatus.LOADED]
    
    def get_plugin_info(self, plugin_name: str) -> Dict[str, Any]:
        """Get plugin information as dictionary."""
        plugin_info = self.registry.get_plugin_info(plugin_name)
        return plugin_info.__dict__ if plugin_info else {}
    
    def get_available_engines(self) -> List[str]:
        """Get list of available OCR engine names."""
        return list(self.registry.get_available_engines().keys())
    
    def get_engine(self, engine_name: str) -> Optional[IOCREngine]:
        """Get OCR engine by name."""
        return self.registry.get_engine(engine_name)
    
    def benchmark_engines(self, test_frames: List[Frame], 
                         options: Optional[OCRProcessingOptions] = None) -> Dict[str, OCRBenchmarkResult]:
        """
        Benchmark all available OCR engines.
        
        Args:
            test_frames: Test frames for benchmarking
            options: Processing options for benchmarking
            
        Returns:
            Dictionary mapping engine names to benchmark results
        """
        if not options:
            options = OCRProcessingOptions()
        
        available_engines = list(self.registry.get_available_engines().values())
        return self.benchmarker.compare_engines(available_engines, test_frames, options)
    
    def get_best_engine(self, benchmark_results: Optional[Dict[str, OCRBenchmarkResult]] = None,
                       criteria: str = "balanced") -> Optional[str]:
        """
        Get the best performing engine.
        
        Args:
            benchmark_results: Optional pre-computed benchmark results
            criteria: Selection criteria ("speed", "accuracy", "balanced")
            
        Returns:
            Name of best performing engine
        """
        if benchmark_results is None:
            # Need to run benchmark first
            self._logger.warning("No benchmark results provided, cannot determine best engine")
            return None
        
        return self.benchmarker.get_best_engine(benchmark_results, criteria)
    
    def set_default_config(self, config: Dict[str, Any]) -> None:
        """Set default configuration for plugin initialization."""
        self._default_config = config.copy()
    
    def _should_use_gpu(self) -> bool:
        """
        Determine if GPU should be used based on runtime mode configuration.
        
        Returns:
            True if GPU should be used, False otherwise
        """
        if not self.config_manager:
            # No config manager, default to auto-detect
            try:
                import torch
                gpu_available = torch.cuda.is_available()
                self._logger.info(f"No config manager, auto-detecting GPU: {gpu_available}")
                return gpu_available
            except:
                self._logger.info("No config manager and PyTorch not available, using CPU")
                return False
        
        runtime_mode = self.config_manager.get_setting('performance.runtime_mode', 'auto')
        self._logger.info(f"Runtime mode from config: {runtime_mode}")
        
        if runtime_mode == 'cpu':
            self._logger.info("Runtime mode set to CPU only")
            return False
        elif runtime_mode == 'gpu':
            self._logger.info("Runtime mode set to GPU acceleration")
            return True
        else:  # 'auto'
            # Auto-detect GPU availability
            try:
                import torch
                gpu_available = torch.cuda.is_available()
                self._logger.info(f"Runtime mode set to Auto, GPU available: {gpu_available}")
                return gpu_available
            except:
                self._logger.info("Runtime mode set to Auto, PyTorch not available, using CPU")
                return False
    
    def reload_plugin(self, plugin_name: str, config: Optional[Dict[str, Any]] = None) -> bool:
        """
        Reload a plugin (unload then load).
        
        Args:
            plugin_name: Name of plugin to reload
            config: Optional new configuration
            
        Returns:
            True if reload successful
        """
        self.unload_plugin(plugin_name)
        return self.load_plugin(plugin_name, config)
    
    def load_all_plugins(self, config: Optional[Dict[str, Any]] = None) -> Dict[str, bool]:
        """
        Load all discovered plugins.
        
        Args:
            config: Optional configuration for all plugins
            
        Returns:
            Dictionary mapping plugin names to load success status
        """
        results = {}
        for plugin_name in self.registry.get_all_plugins().keys():
            results[plugin_name] = self.load_plugin(plugin_name, config)
        return results
    
    def get_plugin_statistics(self) -> Dict[str, Any]:
        """Get comprehensive plugin system statistics."""
        all_plugins = self.registry.get_all_plugins()
        loaded_engines = self.registry.get_available_engines()
        
        stats = {
            "total_plugins": len(all_plugins),
            "loaded_plugins": len([p for p in all_plugins.values() 
                                 if p.load_status == PluginLoadStatus.LOADED]),
            "failed_plugins": len([p for p in all_plugins.values() 
                                 if p.load_status == PluginLoadStatus.FAILED]),
            "available_engines": len(loaded_engines),
            "engine_types": list(set(engine.engine_type.value for engine in loaded_engines.values())),
            "plugin_directories": self._plugin_directories.copy()
        }
        
        return stats