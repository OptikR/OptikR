"""
Universal Plugin Generator - Modern Version

Creates plugins for the current OptikR plugin system:
- Capture plugins: worker.py
- OCR plugins: worker.py  
- Translation plugins: worker.py
- Optimizer plugins: optimizer.py
- Text Processor plugins: processor.py

Usage:
    from app.workflow.universal_plugin_generator import PluginGenerator
    
    generator = PluginGenerator(output_dir="plugins")
    success = generator.create_plugin_programmatically(
        plugin_type='optimizer',
        name='my_optimizer',
        display_name='My Optimizer',
        description='Does something cool'
    )
"""

import json
import logging
from pathlib import Path
from typing import Dict, List, Optional, Any


class PluginGenerator:
    """Modern plugin generator for current OptikR system."""
    
    # Plugin type to script file mapping
    SCRIPT_FILES = {
        'capture': 'worker.py',
        'ocr': 'worker.py',
        'translation': 'worker.py',
        'optimizers': 'optimizer.py',
        'text_processors': 'processor.py'
    }
    
    def __init__(self, output_dir: str = "plugins"):
        """
        Initialize plugin generator.
        
        Args:
            output_dir: Base directory for plugins (default: "plugins")
        """
        self.output_dir = Path(output_dir)
        self.logger = logging.getLogger(__name__)
    
    def create_plugin_programmatically(self, 
                                      plugin_type: str,
                                      name: str,
                                      display_name: str = None,
                                      description: str = None,
                                      author: str = "OptikR Auto-Generator",
                                      version: str = "1.0.0",
                                      dependencies: List[str] = None,
                                      settings: Dict[str, Any] = None,
                                      **kwargs) -> bool:
        """
        Create a plugin programmatically.
        
        Args:
            plugin_type: Type of plugin ('capture', 'ocr', 'translation', 'optimizers', 'text_processors')
            name: Plugin name (folder name)
            display_name: Display name (optional, defaults to name)
            description: Plugin description
            author: Plugin author
            version: Plugin version
            dependencies: List of Python package dependencies
            settings: Plugin settings dictionary
            **kwargs: Additional plugin.json fields
            
        Returns:
            True if plugin created successfully
        """
        try:
            # Validate plugin type
            if plugin_type not in self.SCRIPT_FILES:
                self.logger.error(f"Invalid plugin type: {plugin_type}")
                return False
            
            # Create plugin folder
            plugin_path = self.output_dir / plugin_type / name
            if plugin_path.exists():
                self.logger.info(f"Plugin already exists: {plugin_path}")
                return True
            
            plugin_path.mkdir(parents=True, exist_ok=True)
            self.logger.info(f"Creating plugin: {plugin_path}")
            
            # Create plugin.json
            plugin_json = self._create_plugin_json(
                plugin_type=plugin_type,
                name=name,
                display_name=display_name or name.replace('_', ' ').title(),
                description=description or f"Auto-generated {plugin_type} plugin",
                author=author,
                version=version,
                dependencies=dependencies or [],
                settings=settings or {},
                **kwargs
            )
            
            json_path = plugin_path / "plugin.json"
            with open(json_path, 'w', encoding='utf-8') as f:
                json.dump(plugin_json, f, indent=2, ensure_ascii=False)
            
            self.logger.info(f"Created plugin.json: {json_path}")
            
            # Create script file
            script_file = self.SCRIPT_FILES[plugin_type]
            script_path = plugin_path / script_file
            script_content = self._create_script_template(plugin_type, name, plugin_json)
            
            with open(script_path, 'w', encoding='utf-8') as f:
                f.write(script_content)
            
            self.logger.info(f"Created {script_file}: {script_path}")
            
            # Create README.md
            readme_path = plugin_path / "README.md"
            readme_content = self._create_readme(plugin_type, name, display_name or name, description)
            
            with open(readme_path, 'w', encoding='utf-8') as f:
                f.write(readme_content)
            
            self.logger.info(f"✓ Plugin created successfully: {name}")
            return True
            
        except Exception as e:
            self.logger.error(f"Failed to create plugin: {e}", exc_info=True)
            return False
    
    def _create_plugin_json(self, plugin_type: str, name: str, display_name: str,
                           description: str, author: str, version: str,
                           dependencies: List[str], settings: Dict[str, Any],
                           **kwargs) -> Dict[str, Any]:
        """Create plugin.json content."""
        plugin_json = {
            "name": name,
            "display_name": display_name,
            "version": version,
            "author": author,
            "description": description,
            "type": plugin_type.rstrip('s'),  # Remove trailing 's' for type
            "enabled_by_default": kwargs.get('enabled_by_default', True)
        }
        
        # Add script file reference
        script_file = self.SCRIPT_FILES[plugin_type]
        if plugin_type in ['capture', 'ocr', 'translation']:
            plugin_json["worker_script"] = script_file
        
        # Add type-specific fields
        if plugin_type == 'optimizers':
            plugin_json["target_stage"] = kwargs.get('target_stage', 'capture')
            plugin_json["stage"] = kwargs.get('stage', 'post')
        
        if plugin_type == 'ocr':
            plugin_json["engine_type"] = kwargs.get('engine_type', name)
            plugin_json["entry_point"] = "__init__.py"
        
        # Add settings
        if settings:
            plugin_json["settings"] = settings
        
        # Add dependencies
        if dependencies:
            plugin_json["dependencies"] = dependencies
        
        # Add any additional kwargs
        for key, value in kwargs.items():
            if key not in plugin_json and key not in ['enabled_by_default', 'target_stage', 'stage', 'engine_type']:
                plugin_json[key] = value
        
        return plugin_json
    
    def _create_script_template(self, plugin_type: str, name: str, plugin_json: Dict) -> str:
        """Create script file template based on plugin type."""
        if plugin_type == 'optimizers':
            return self._create_optimizer_template(name, plugin_json)
        elif plugin_type == 'text_processors':
            return self._create_processor_template(name, plugin_json)
        elif plugin_type == 'translation':
            return self._create_translation_worker_template(name, plugin_json)
        elif plugin_type == 'ocr':
            return self._create_ocr_worker_template(name, plugin_json)
        elif plugin_type == 'capture':
            return self._create_capture_worker_template(name, plugin_json)
        else:
            return self._create_generic_worker_template(name, plugin_json)
    
    def _create_optimizer_template(self, name: str, plugin_json: Dict) -> str:
        """Create optimizer.py template."""
        return f'''"""
{plugin_json['display_name']} - Optimizer Plugin

{plugin_json['description']}

Auto-generated by OptikR Plugin Generator
"""

import logging
from typing import Dict, Any, Optional


def initialize(config: Optional[Dict[str, Any]] = None) -> bool:
    """
    Initialize the optimizer plugin.
    
    Args:
        config: Configuration dictionary from plugin.json settings
        
    Returns:
        True if initialization successful
    """
    global logger
    logger = logging.getLogger(__name__)
    logger.info("Initializing {plugin_json['display_name']}")
    
    # TODO: Add your initialization code here
    
    return True


class {name.replace('_', ' ').title().replace(' ', '')}Optimizer:
    """Main optimizer class."""
    
    def __init__(self, config: Optional[Dict[str, Any]] = None):
        """Initialize optimizer with configuration."""
        self.config = config or {{}}
        self.logger = logging.getLogger(__name__)
        
        # TODO: Initialize your optimizer state here
    
    def process(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Process data through the optimizer.
        
        Args:
            data: Input data dictionary
            
        Returns:
            Modified data dictionary
        """
        # TODO: Implement your optimization logic here
        
        # Example: Add metadata
        data['optimized_by'] = '{name}'
        
        return data
    
    def cleanup(self):
        """Clean up resources."""
        # TODO: Add cleanup code if needed
        pass
'''
    
    def _create_processor_template(self, name: str, plugin_json: Dict) -> str:
        """Create processor.py template."""
        return f'''"""
{plugin_json['display_name']} - Text Processor Plugin

{plugin_json['description']}

Auto-generated by OptikR Plugin Generator
"""

import logging
from typing import Dict, Any, Optional, List


def initialize(config: Optional[Dict[str, Any]] = None) -> bool:
    """
    Initialize the text processor plugin.
    
    Args:
        config: Configuration dictionary from plugin.json settings
        
    Returns:
        True if initialization successful
    """
    global logger
    logger = logging.getLogger(__name__)
    logger.info("Initializing {plugin_json['display_name']}")
    
    # TODO: Add your initialization code here
    
    return True


class {name.replace('_', ' ').title().replace(' ', '')}Processor:
    """Main text processor class."""
    
    def __init__(self, config: Optional[Dict[str, Any]] = None):
        """Initialize processor with configuration."""
        self.config = config or {{}}
        self.logger = logging.getLogger(__name__)
        
        # TODO: Initialize your processor state here
    
    def process(self, text: str, metadata: Optional[Dict[str, Any]] = None) -> str:
        """
        Process text.
        
        Args:
            text: Input text to process
            metadata: Optional metadata dictionary
            
        Returns:
            Processed text
        """
        # TODO: Implement your text processing logic here
        
        # Example: Return text unchanged
        return text
    
    def process_batch(self, texts: List[str]) -> List[str]:
        """
        Process multiple texts in batch.
        
        Args:
            texts: List of texts to process
            
        Returns:
            List of processed texts
        """
        return [self.process(text) for text in texts]
    
    def cleanup(self):
        """Clean up resources."""
        # TODO: Add cleanup code if needed
        pass
'''
    
    def _create_translation_worker_template(self, name: str, plugin_json: Dict) -> str:
        """Create worker.py template for translation plugins."""
        model_name = plugin_json.get('settings', {}).get('model_name', {}).get('default', 'model-name')
        
        return f'''"""
{plugin_json['display_name']} - Translation Worker

{plugin_json['description']}

Auto-generated by OptikR Plugin Generator
"""

import logging
from typing import Optional, Dict, Any

try:
    from transformers import AutoModelForSeq2SeqLM, AutoTokenizer
    TRANSFORMERS_AVAILABLE = True
except ImportError:
    TRANSFORMERS_AVAILABLE = False


class TranslationEngine:
    """Translation engine for {plugin_json['display_name']}."""
    
    def __init__(self):
        """Initialize translation engine."""
        self.logger = logging.getLogger(__name__)
        self.model = None
        self.tokenizer = None
        self.model_name = "{model_name}"
    
    def initialize(self, config: Dict[str, Any]) -> bool:
        """
        Initialize the translation engine.
        
        Args:
            config: Configuration dictionary
            
        Returns:
            True if initialization successful
        """
        if not TRANSFORMERS_AVAILABLE:
            self.logger.error("transformers library not available")
            return False
        
        try:
            self.model_name = config.get('model_name', self.model_name)
            
            self.logger.info(f"Loading model: {{self.model_name}}")
            self.tokenizer = AutoTokenizer.from_pretrained(self.model_name)
            self.model = AutoModelForSeq2SeqLM.from_pretrained(self.model_name)
            
            self.logger.info("Model loaded successfully")
            return True
            
        except Exception as e:
            self.logger.error(f"Failed to initialize: {{e}}")
            return False
    
    def translate_text(self, text: str, src_lang: str, tgt_lang: str,
                      options: Optional[Dict] = None):
        """
        Translate text.
        
        Args:
            text: Text to translate
            src_lang: Source language code
            tgt_lang: Target language code
            options: Translation options
            
        Returns:
            Translated text
        """
        try:
            inputs = self.tokenizer(text, return_tensors="pt", padding=True)
            outputs = self.model.generate(**inputs)
            translated = self.tokenizer.decode(outputs[0], skip_special_tokens=True)
            return translated
            
        except Exception as e:
            self.logger.error(f"Translation failed: {{e}}")
            return text
    
    def is_available(self) -> bool:
        """Check if engine is available."""
        return self.model is not None and self.tokenizer is not None
'''
    
    def _create_ocr_worker_template(self, name: str, plugin_json: Dict) -> str:
        """Create worker.py template for OCR plugins."""
        return f'''"""
{plugin_json['display_name']} - OCR Worker

{plugin_json['description']}

Auto-generated by OptikR Plugin Generator
"""

import logging
from typing import List, Dict, Any, Optional
import numpy as np


class OCREngine:
    """OCR engine for {plugin_json['display_name']}."""
    
    def __init__(self):
        """Initialize OCR engine."""
        self.logger = logging.getLogger(__name__)
        self.reader = None
    
    def initialize(self, config: Dict[str, Any]) -> bool:
        """
        Initialize the OCR engine.
        
        Args:
            config: Configuration dictionary
            
        Returns:
            True if initialization successful
        """
        try:
            # TODO: Initialize your OCR engine here
            self.logger.info("Initializing {plugin_json['display_name']}")
            return True
            
        except Exception as e:
            self.logger.error(f"Failed to initialize: {{e}}")
            return False
    
    def process_frame(self, frame: np.ndarray, languages: List[str] = None) -> List[Dict[str, Any]]:
        """
        Process frame and extract text.
        
        Args:
            frame: Image frame as numpy array
            languages: List of language codes
            
        Returns:
            List of text blocks with bounding boxes
        """
        try:
            # TODO: Implement OCR logic here
            
            # Example return format:
            results = []
            # results.append({{
            #     'text': 'detected text',
            #     'confidence': 0.95,
            #     'bbox': [x, y, width, height]
            # }})
            
            return results
            
        except Exception as e:
            self.logger.error(f"OCR processing failed: {{e}}")
            return []
    
    def is_available(self) -> bool:
        """Check if engine is available."""
        return self.reader is not None
'''
    
    def _create_capture_worker_template(self, name: str, plugin_json: Dict) -> str:
        """Create worker.py template for capture plugins."""
        return f'''"""
{plugin_json['display_name']} - Capture Worker

{plugin_json['description']}

Auto-generated by OptikR Plugin Generator
"""

import logging
from typing import Dict, Any, Optional, Tuple
import numpy as np


class CaptureEngine:
    """Capture engine for {plugin_json['display_name']}."""
    
    def __init__(self):
        """Initialize capture engine."""
        self.logger = logging.getLogger(__name__)
    
    def initialize(self, config: Dict[str, Any]) -> bool:
        """
        Initialize the capture engine.
        
        Args:
            config: Configuration dictionary
            
        Returns:
            True if initialization successful
        """
        try:
            # TODO: Initialize your capture engine here
            self.logger.info("Initializing {plugin_json['display_name']}")
            return True
            
        except Exception as e:
            self.logger.error(f"Failed to initialize: {{e}}")
            return False
    
    def capture(self, region: Optional[Tuple[int, int, int, int]] = None) -> Optional[np.ndarray]:
        """
        Capture screen region.
        
        Args:
            region: (x, y, width, height) or None for full screen
            
        Returns:
            Captured frame as numpy array (BGR format) or None on failure
        """
        try:
            # TODO: Implement capture logic here
            
            # Example: Return None if not implemented
            return None
            
        except Exception as e:
            self.logger.error(f"Capture failed: {{e}}")
            return None
    
    def is_available(self) -> bool:
        """Check if capture engine is available."""
        return True
'''
    
    def _create_generic_worker_template(self, name: str, plugin_json: Dict) -> str:
        """Create generic worker.py template."""
        return f'''"""
{plugin_json['display_name']} - Worker

{plugin_json['description']}

Auto-generated by OptikR Plugin Generator
"""

import logging
from typing import Dict, Any, Optional


def initialize(config: Optional[Dict[str, Any]] = None) -> bool:
    """
    Initialize the plugin.
    
    Args:
        config: Configuration dictionary from plugin.json settings
        
    Returns:
        True if initialization successful
    """
    global logger
    logger = logging.getLogger(__name__)
    logger.info("Initializing {plugin_json['display_name']}")
    
    # TODO: Add your initialization code here
    
    return True


# TODO: Implement your plugin logic here
'''
    
    def _create_readme(self, plugin_type: str, name: str, display_name: str, description: str) -> str:
        """Create README.md content."""
        return f'''# {display_name}

{description}

## Plugin Information

- **Type**: {plugin_type}
- **Name**: {name}
- **Auto-generated**: Yes

## Installation

This plugin is auto-generated and should work out of the box.

## Configuration

Edit `plugin.json` to configure plugin settings.

## Development

To customize this plugin:
1. Edit the script file ({self.SCRIPT_FILES.get(plugin_type, 'worker.py')})
2. Implement the TODO sections
3. Test your changes
4. Update this README

## Support

For help, see: docs/PLUGIN_DEVELOPMENT.md
'''
    
    def create_plugin_json(self, name: str, **kwargs) -> bool:
        """
        Create only plugin.json file (for backward compatibility).
        
        Args:
            name: Plugin name
            **kwargs: Plugin configuration
            
        Returns:
            True if created successfully
        """
        plugin_type = kwargs.get('type', 'optimizer')
        return self.create_plugin_programmatically(
            plugin_type=plugin_type,
            name=name,
            **kwargs
        )
    
    def run_interactive(self):
        """
        Run interactive CLI to generate a plugin.
        
        Note: This is a simplified version. For full customization,
        use create_plugin_programmatically() directly.
        """
        print("=" * 70)
        print("OPTIKR PLUGIN GENERATOR")
        print("=" * 70)
        print("\nThis tool will help you create a new plugin.\n")
        
        # Get plugin type
        print("Plugin Type:")
        print("  1. Capture - Screen capture method")
        print("  2. OCR - Text recognition engine")
        print("  3. Translation - Translation engine")
        print("  4. Optimizer - Performance optimization")
        print("  5. Text Processor - Text processing/filtering")
        
        type_map = {
            '1': 'capture',
            '2': 'ocr',
            '3': 'translation',
            '4': 'optimizers',
            '5': 'text_processors'
        }
        
        choice = input("\nSelect type (1-5): ").strip()
        plugin_type = type_map.get(choice)
        
        if not plugin_type:
            print("Invalid choice. Exiting.")
            return False
        
        # Get basic info
        name = input("\nPlugin name (e.g., my_plugin): ").strip()
        if not name:
            print("Name is required. Exiting.")
            return False
        
        display_name = input(f"Display name (default: {name.replace('_', ' ').title()}): ").strip()
        if not display_name:
            display_name = name.replace('_', ' ').title()
        
        description = input("Description: ").strip()
        if not description:
            description = f"Auto-generated {plugin_type} plugin"
        
        # Create plugin
        print(f"\nCreating plugin '{name}'...")
        success = self.create_plugin_programmatically(
            plugin_type=plugin_type,
            name=name,
            display_name=display_name,
            description=description
        )
        
        if success:
            print(f"\n✓ Plugin created successfully!")
            print(f"\nLocation: {self.output_dir / plugin_type / name}")
            print("\nNext steps:")
            print(f"1. Edit {self.SCRIPT_FILES[plugin_type]} to implement your logic")
            print("2. Test your plugin in OptikR")
            print("3. Restart OptikR to load the plugin")
        else:
            print("\n✗ Plugin creation failed. Check logs for details.")
        
        return success


# For backward compatibility
def main():
    """CLI entry point."""
    generator = PluginGenerator()
    generator.run_interactive()


if __name__ == '__main__':
    main()
