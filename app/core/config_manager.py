"""
Configuration Manager Module

Simple configuration manager that persists settings to JSON file.
Handles loading, saving, and merging of configuration data.

Author: Real-Time Translation System
Date: 2024
"""

import json
from pathlib import Path

# Import path utilities for EXE compatibility
from app.utils.path_utils import get_app_path, ensure_app_directory


class SimpleConfigManager:
    """Simple configuration manager that persists to JSON file."""
    
    def __init__(self, config_file=None):
        """
        Initialize configuration manager.
        
        Args:
            config_file: Path to config file (default: config/user_config.json)
        """
        # Use config file from settings or default (EXE-compatible)
        if config_file is None:
            # Use new structure: user_data/config/
            from app.utils.path_utils import get_config_path
            config_file = get_config_path()
        else:
            config_file = Path(config_file)
        self.config_file = config_file
        self.config = self._load_config()
    
    def _load_config(self):
        """Load configuration from file."""
        defaults = self._get_default_config()
        
        if self.config_file.exists():
            try:
                with open(self.config_file, 'r', encoding='utf-8') as f:
                    existing = json.load(f)
                # Merge existing config with defaults (existing takes precedence)
                return self._merge_configs(defaults, existing)
            except Exception as e:
                print(f"[WARNING] Failed to load config: {e}")
                return defaults
        else:
            return defaults
    
    def _get_default_config(self):
        """Get default configuration."""
        import os
        # Return minimal defaults - will be merged with existing config
        return {
            '_metadata': {
                'version': '2.0.0',
                'description': 'Consolidated configuration - all settings in one place'
            },
            'performance': {
                'runtime_mode': 'auto',
                'worker_threads': max(1, os.cpu_count() - 1) if os.cpu_count() else 4,
                'queue_size': 16,
                'ocr_batch_size': 8,
                'translation_batch_size': 16,
                'batch_wait_time_ms': 20.0,
                'enable_parallel_processing': True
            },
            'timeouts': {
                'model_loading': 30.0,
                'process_operation': 2.0,
                'subprocess_communication': 5.0,
                'translation_request': 10.0,
                'ocr_processing': 5.0
            },
            'quality': {
                'ocr_confidence_threshold': 0.3,
                'translation_confidence_threshold': 0.5,
                'dictionary_learning_threshold': 0.8,
                'high_confidence_threshold': 0.85,
                'enable_quality_filter': True
            },
            'cache': {
                'translation_cache_size': 10000,
                'translation_cache_ttl': 3600,
                'dictionary_cache_size': 1000,
                'frame_cache_size': 100,
                'frame_cache_memory_mb': 50.0,
                'ocr_cache_size': 500,
                'ocr_cache_memory_mb': 20.0,
                'translation_cache_memory_mb': 10.0
            },
            'retry': {
                'max_retries': 3,
                'retry_delay_ms': 100
            },
            'monitoring': {
                'memory_warning_threshold': 75,
                'memory_critical_threshold': 90,
                'enable_performance_monitoring': True,
                'metrics_history_size': 60
            },
            'translation': {'source_language': 'en', 'target_language': 'de'},
            'startup': {
                'start_with_windows': False,
                'minimize_to_tray': True,
                'show_setup_wizard': True
            },
            'overlay': {'interactive_on_hover': False},
            'capture': {
                'mode': 'directx',
                'region': 'full_screen',
                'fps': 30,
                'quality': 'high',
                'monitor': 'primary',
                'adaptive': True,
                'fallback_enabled': True
            },
            'ui': {
                'sidebar_width': 220,
                'window_x': 100,
                'window_y': 100,
                'window_width': 1400,
                'window_height': 950,
                'window_min_width': 1300,
                'window_min_height': 850,
                'version': '1.0.0'
            },
            'paths': {
                'config_dir': 'user_data/config',
                'config_file': 'user_data/config/user_config.json',
                'consent_file': None,  # Consolidated into main config
                'installation_info': None,  # Consolidated into main config
                'models_dir': 'system_data/ai_models',
                'cache_dir': 'system_data/cache',
                'logs_dir': 'system_data/logs',
                'data_dir': 'user_data',
                'dictionary_dir': 'user_data/learned/translations',
                'styles_dir': 'app/styles',
                'plugins_dir': 'plugins'
            },
            'consent': {
                'consent_given': False,
                'consent_date': None,
                'version': '1.0.0'
            },
            'installation': {
                'created': None,
                'version': '1.0.0',
                'cuda': {
                    'installed': False,
                    'path': ''
                },
                'pytorch': {
                    'version': '',
                    'cuda_available': False,
                    'device_name': 'CPU'
                }
            },
            'presets': {
                'regions': {}
            }
        }
    
    def _merge_configs(self, base, updates):
        """Recursively merge two config dictionaries."""
        result = base.copy()
        for key, value in updates.items():
            if key in result and isinstance(result[key], dict) and isinstance(value, dict):
                result[key] = self._merge_configs(result[key], value)
            else:
                result[key] = value
        return result
    
    def get_setting(self, key, default=None):
        """
        Get a setting value using dot notation.
        
        Args:
            key: Setting key in dot notation (e.g., 'ui.window_width')
            default: Default value if key not found
            
        Returns:
            Setting value or default
        """
        keys = key.split('.')
        value = self.config
        for k in keys:
            if isinstance(value, dict) and k in value:
                value = value[k]
            else:
                return default
        return value
    
    def set_setting(self, key, value):
        """
        Set a setting value using dot notation.
        
        Args:
            key: Setting key in dot notation (e.g., 'ui.window_width')
            value: Value to set
        """
        keys = key.split('.')
        config = self.config
        for k in keys[:-1]:
            if k not in config:
                config[k] = {}
            config = config[k]
        config[keys[-1]] = value
    
    def save_config(self):
        """
        Save configuration to file.
        
        Returns:
            bool: True if save successful, False otherwise
        """
        try:
            # Ensure directory exists
            self.config_file.parent.mkdir(parents=True, exist_ok=True)
            
            # Write to file
            with open(self.config_file, 'w', encoding='utf-8') as f:
                json.dump(self.config, f, indent=2, ensure_ascii=False)
            
            print(f"[INFO] Configuration saved to {self.config_file}")
            return True
        except Exception as e:
            print(f"[ERROR] Failed to save config: {e}")
            return False
    
    def save_configuration(self, config_dict):
        """
        Save configuration (alternative method name for compatibility).
        
        Args:
            config_dict: Configuration dictionary to save
            
        Returns:
            bool: True if save successful, False otherwise
        """
        self.config = config_dict
        return self.save_config()
    
    # Convenience methods for consolidated sections
    
    def get_consent_info(self):
        """Get user consent information."""
        return self.config.get('consent', {})
    
    def set_consent_info(self, consent_given, version='1.0.0'):
        """
        Set user consent information.
        
        Args:
            consent_given: Boolean indicating if consent was given
            version: Consent version string
        """
        from datetime import datetime
        self.config['consent'] = {
            'consent_given': consent_given,
            'consent_date': datetime.now().isoformat() if consent_given else None,
            'version': version
        }
    
    def get_installation_info(self):
        """Get installation information."""
        return self.config.get('installation', {})
    
    def set_installation_info(self, install_info):
        """
        Set installation information.
        
        Args:
            install_info: Dictionary with installation details
        """
        self.config['installation'] = install_info
    
    def get_region_presets(self):
        """Get region presets."""
        return self.config.get('presets', {}).get('regions', {})
    
    def set_region_preset(self, preset_name, preset_data):
        """
        Set a region preset.
        
        Args:
            preset_name: Name of the preset
            preset_data: Preset configuration dictionary
        """
        if 'presets' not in self.config:
            self.config['presets'] = {'regions': {}}
        if 'regions' not in self.config['presets']:
            self.config['presets']['regions'] = {}
        
        self.config['presets']['regions'][preset_name] = preset_data
    
    def delete_region_preset(self, preset_name):
        """
        Delete a region preset.
        
        Args:
            preset_name: Name of the preset to delete
            
        Returns:
            bool: True if deleted, False if not found
        """
        presets = self.config.get('presets', {}).get('regions', {})
        if preset_name in presets:
            del presets[preset_name]
            return True
        return False
