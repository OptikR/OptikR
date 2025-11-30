"""
Capture Plugin Manager with Auto-Generation

Manages capture plugins and auto-generates plugins for installed capture libraries.
"""

import logging
import importlib.util
import json
from pathlib import Path
from typing import List, Dict, Optional

# Import PluginMetadata for proper plugin representation
from app.workflow.base.plugin_interface import PluginMetadata


class CapturePluginManager:
    """Manages capture plugins with auto-generation support."""
    
    def __init__(self, plugin_directories: Optional[List[str]] = None):
        """Initialize capture plugin manager."""
        self.logger = logging.getLogger(__name__)
        self._plugin_directories = plugin_directories or []
        self._add_default_plugin_directories()
        self.discovered_plugins = []
        self._active_plugin = None
        self._active_worker = None
        self._loaded_plugins = []
    
    def _add_default_plugin_directories(self):
        """Add default plugin search directories."""
        current_dir = Path(__file__).parent
        
        # Main plugins directory
        self._plugin_directories.extend([
            str(current_dir.parent.parent / "plugins" / "capture"),
        ])
        
        # User plugins directory
        user_plugins = Path.home() / ".translation_system" / "plugins" / "capture"
        self._plugin_directories.append(str(user_plugins))
    
    def discover_plugins(self) -> List[PluginMetadata]:
        """
        Discover available capture plugins.
        Auto-generates plugins for installed capture libraries.
        
        Returns:
            List of discovered plugin metadata objects
        """
        # DISABLED: Auto-generation causes conflicts with existing plugins
        # Use pre-built plugins instead (screenshot_capture_cpu, dxcam_capture_gpu)
        # self._auto_generate_missing_plugins()
        
        discovered = []
        
        for directory in self._plugin_directories:
            dir_path = Path(directory)
            if not dir_path.exists():
                continue
            
            self.logger.info(f"Scanning for capture plugins in: {directory}")
            
            for item in dir_path.iterdir():
                if item.is_dir():
                    plugin_json = item / "plugin.json"
                    if plugin_json.exists():
                        try:
                            with open(plugin_json, 'r', encoding='utf-8') as f:
                                plugin_data = json.load(f)
                            
                            # Check if dependencies are installed
                            if self._check_dependencies(plugin_data.get('dependencies', [])):
                                # Convert dict to PluginMetadata object
                                plugin_info = PluginMetadata.from_dict(plugin_data)
                                discovered.append(plugin_info)
                                self.logger.info(f"Discovered capture plugin: {plugin_info.name}")
                            else:
                                self.logger.debug(f"Skipping {plugin_data.get('name')} - dependencies not installed")
                        except Exception as e:
                            self.logger.error(f"Failed to load plugin {plugin_json}: {e}")
        
        self.discovered_plugins = discovered
        self.logger.info(f"Discovered {len(discovered)} capture plugins")
        return discovered
    
    def _auto_generate_missing_plugins(self):
        """
        Auto-generate capture plugins for installed packages.
        Uses the universal plugin generator to create the necessary files.
        """
        try:
            from app.workflow.universal_plugin_generator import PluginGenerator
            
            generator = PluginGenerator(output_dir="plugins")
            
            # Check for installed capture libraries
            capture_libraries = {
                'mss': {
                    'display_name': 'MSS Screen Capture',
                    'description': 'Fast cross-platform screen capture using MSS'
                },
                'pyautogui': {
                    'display_name': 'PyAutoGUI Screen Capture',
                    'description': 'Simple screen capture using PyAutoGUI'
                },
                'pyscreenshot': {
                    'display_name': 'PyScreenshot',
                    'description': 'Cross-platform screenshot library'
                },
            }
            
            main_plugin_dir = None
            for directory in self._plugin_directories:
                if 'plugins' in directory and 'capture' in directory and '.translation_system' not in directory:
                    main_plugin_dir = Path(directory)
                    break
            
            if not main_plugin_dir:
                return
            
            # Scan existing plugins to avoid duplicates
            existing_packages = set()
            if main_plugin_dir.exists():
                for item in main_plugin_dir.iterdir():
                    if item.is_dir():
                        plugin_json = item / "plugin.json"
                        if plugin_json.exists():
                            try:
                                with open(plugin_json, 'r', encoding='utf-8') as f:
                                    data = json.load(f)
                                    deps = data.get('dependencies', [])
                                    existing_packages.update(deps)
                            except:
                                pass
            
            for package_name, info in capture_libraries.items():
                # Skip if already exists
                if package_name in existing_packages:
                    continue
                
                # Check if package is installed
                spec = importlib.util.find_spec(package_name)
                if spec is not None:
                    plugin_folder = main_plugin_dir / package_name
                    if not (plugin_folder / "plugin.json").exists():
                        self.logger.info(f"Auto-generating capture plugin for {package_name}")
                        
                        # Use universal generator
                        success = generator.create_plugin_programmatically(
                            plugin_type='capture',
                            name=package_name,
                            display_name=info['display_name'],
                            description=info['description'],
                            dependencies=[package_name],
                            settings={
                                'capture_mode': {
                                    'type': 'string',
                                    'default': 'fullscreen',
                                    'description': 'Capture mode (fullscreen/region)'
                                }
                            }
                        )
                        
                        if success:
                            self.logger.info(f"✓ Auto-generated plugin for {package_name}")
                        else:
                            self.logger.warning(f"Failed to auto-generate plugin for {package_name}")
        
        except Exception as e:
            self.logger.warning(f"Failed to auto-generate plugins: {e}")
    
    def _check_dependencies(self, dependencies: List[str]) -> bool:
        """Check if all dependencies are installed."""
        if not dependencies:
            return True
        
        for dep in dependencies:
            spec = importlib.util.find_spec(dep)
            if spec is None:
                return False
        return True
    
    def set_active_plugin(self, plugin_name: str, config: Optional[Dict] = None) -> bool:
        """
        Set the active capture plugin.
        
        Args:
            plugin_name: Name of the plugin to activate
            config: Optional configuration for the plugin
            
        Returns:
            True if plugin was successfully activated
        """
        try:
            # Find the plugin in discovered plugins
            plugin_metadata = None
            for plugin in self.discovered_plugins:
                if plugin.name == plugin_name:
                    plugin_metadata = plugin
                    break
            
            if not plugin_metadata:
                self.logger.error(f"Plugin '{plugin_name}' not found in discovered plugins")
                return False
            
            # For dxcam, just set it as active - we'll initialize on first capture
            self._active_plugin = plugin_name
            if plugin_name not in self._loaded_plugins:
                self._loaded_plugins.append(plugin_name)
            
            self.logger.info(f"Activated capture plugin: {plugin_name}")
            return True
            
        except Exception as e:
            self.logger.error(f"Failed to activate plugin '{plugin_name}': {e}")
            import traceback
            traceback.print_exc()
            return False
    
    def capture_frame(self, region_data: Dict) -> Optional[Dict]:
        """
        Capture a frame using the active plugin.
        
        Args:
            region_data: Dictionary with x, y, width, height, monitor_id
            
        Returns:
            Dictionary with frame data or None if capture failed
        """
        try:
            # Use dxcam directly (in-process, no subprocess for now)
            if self._active_plugin == 'dxcam_capture_gpu':
                # Initialize dxcam camera if not already done
                if not hasattr(self, '_dxcam_camera'):
                    try:
                        import dxcam
                        self._dxcam_camera = dxcam.create()
                        if self._dxcam_camera:
                            self.logger.info("DXCam camera initialized successfully")
                        else:
                            self.logger.error("DXCam camera initialization returned None")
                            self._dxcam_camera = None
                    except Exception as e:
                        self.logger.error(f"Failed to initialize DXCam: {e}")
                        self._dxcam_camera = None
                
                # Try to capture with dxcam
                if self._dxcam_camera:
                    try:
                        import numpy as np
                        import base64
                        
                        x = region_data['x']
                        y = region_data['y']
                        w = region_data['width']
                        h = region_data['height']
                        
                        # Capture frame with dxcam
                        frame = self._dxcam_camera.grab(region=(x, y, x + w, y + h))
                        
                        if frame is not None:
                            # Encode frame as base64
                            frame_bytes = frame.tobytes()
                            frame_b64 = base64.b64encode(frame_bytes).decode('utf-8')
                            
                            return {
                                'frame': frame_b64,
                                'shape': list(frame.shape),
                                'dtype': str(frame.dtype)
                            }
                        else:
                            self.logger.warning("DXCam returned None, trying full screen capture")
                            # Try full screen
                            frame = self._dxcam_camera.grab()
                            if frame is not None:
                                # Crop to region
                                frame = frame[y:y+h, x:x+w]
                                frame_bytes = frame.tobytes()
                                frame_b64 = base64.b64encode(frame_bytes).decode('utf-8')
                                
                                return {
                                    'frame': frame_b64,
                                    'shape': list(frame.shape),
                                    'dtype': str(frame.dtype)
                                }
                    except Exception as e:
                        self.logger.error(f"DXCam capture error: {e}")
            
            # If we get here, dxcam failed or isn't active - use PIL fallback
            self.logger.warning("Using PIL fallback capture")
            try:
                from PIL import ImageGrab
                import numpy as np
                import base64
                
                x = region_data['x']
                y = region_data['y']
                w = region_data['width']
                h = region_data['height']
                
                # Capture with PIL
                screenshot = ImageGrab.grab(bbox=(x, y, x + w, y + h))
                
                # Convert to numpy array
                frame = np.array(screenshot)
                
                # Convert RGB to BGR (if needed for consistency)
                if len(frame.shape) == 3 and frame.shape[2] == 3:
                    frame = frame[:, :, ::-1]  # RGB to BGR
                
                # Encode frame as base64
                frame_bytes = frame.tobytes()
                frame_b64 = base64.b64encode(frame_bytes).decode('utf-8')
                
                return {
                    'frame': frame_b64,
                    'shape': list(frame.shape),
                    'dtype': str(frame.dtype)
                }
                
            except Exception as pil_error:
                self.logger.error(f"PIL fallback also failed: {pil_error}")
                return {'error': f'All capture methods failed. DXCam and PIL both unavailable.'}
                
        except Exception as e:
            self.logger.error(f"Frame capture failed: {e}")
            import traceback
            traceback.print_exc()
            return {'error': str(e)}
    
    def get_available_plugins(self, config_manager=None) -> List[str]:
        """
        Get list of available plugin names, filtered by runtime mode.
        GPU-only plugins (like dxcam) are hidden in CPU mode.
        
        Args:
            config_manager: Optional config manager to check runtime mode
            
        Returns:
            List of available plugin names
        """
        all_plugins = [p.name for p in self.discovered_plugins]
        
        # If no config manager, return all plugins
        if not config_manager:
            return all_plugins
        
        # Check runtime mode
        runtime_mode = config_manager.get_runtime_mode()
        
        # GPU-only plugins that require CUDA/DirectX
        gpu_only_plugins = ['dxcam_capture_gpu', 'directx_capture']
        
        # Filter out GPU plugins in CPU mode
        if runtime_mode == 'cpu':
            filtered = [p for p in all_plugins if p not in gpu_only_plugins]
            if len(filtered) < len(all_plugins):
                self.logger.info(f"[CPU Mode] Filtered out GPU-only capture methods: {set(all_plugins) - set(filtered)}")
            return filtered
        
        return all_plugins
    
    def get_active_plugin(self) -> Optional[str]:
        """Get name of currently active plugin."""
        return self._active_plugin
    
    def get_loaded_plugins(self) -> List[str]:
        """Get list of loaded plugin names."""
        return self._loaded_plugins.copy()
    
    def cleanup(self) -> None:
        """Clean up plugin resources."""
        # Clean up dxcam camera
        if hasattr(self, '_dxcam_camera') and self._dxcam_camera:
            try:
                del self._dxcam_camera
                self._dxcam_camera = None
            except Exception as e:
                self.logger.error(f"Error cleaning up dxcam camera: {e}")
        
        # Clean up worker if exists
        if self._active_worker:
            try:
                # Send shutdown message
                import json
                shutdown_msg = {'type': 'shutdown'}
                self._active_worker.stdin.write(json.dumps(shutdown_msg) + '\n')
                self._active_worker.stdin.flush()
                
                # Wait for process to terminate
                self._active_worker.wait(timeout=2)
            except Exception as e:
                self.logger.error(f"Error stopping worker: {e}")
                # Force terminate if graceful shutdown failed
                try:
                    self._active_worker.terminate()
                    self._active_worker.wait(timeout=1)
                except:
                    self._active_worker.kill()
            finally:
                self._active_worker = None
        self._active_plugin = None
