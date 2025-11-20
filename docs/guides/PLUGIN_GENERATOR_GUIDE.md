# Plugin Generator Guide

**How to create plugins quickly using the OptikR Plugin Generator**

---

## Overview

The Plugin Generator is a CLI tool that creates plugin boilerplate automatically. It generates:
- `plugin.json` - Plugin metadata
- `worker.py` - Worker script template
- `README.md` - Documentation template

**No manual file creation needed!**

---

## Quick Start

### Run the Generator

```bash
cd dev
python -m src.workflow.plugin_generator
```

### Follow the Prompts

The generator will ask you:

1. **Plugin Type** - Choose from:
   - Capture - Screen capture method
   - OCR - Text recognition engine
   - Translation - Translation engine
   - Optimizer - Performance optimization

2. **Plugin Name** - Lowercase, no spaces (e.g., `my_capture`)

3. **Display Name** - Human-readable name (e.g., `My Custom Capture`)

4. **Author** - Your name

5. **Description** - What your plugin does

6. **Version** - Default: `1.0.0`

7. **Settings** (optional) - Configurable options for your plugin

8. **Dependencies** (optional) - Python packages required

### Example Session

```
============================================================
OPTIKR PLUGIN GENERATOR
============================================================

Plugin Type:
  1. Capture
  2. OCR
  3. Translation
  4. Optimizer

Select type (1-4): 1

Plugin name (lowercase, no spaces): obs_capture

Display name [Obs Capture]: OBS Studio Capture

Author name: John Doe

Description: Captures from OBS Studio virtual camera

Version [1.0.0]: 1.0.0

------------------------------------------------------------
Plugin Settings (optional)
------------------------------------------------------------

Setting name (or Enter to finish): device_id
  Type: 1=string, 2=int, 3=float, 4=bool
  Select type (1-4): 2
  Default value: 0
  Description: OBS virtual camera device ID
  ✓ Added setting: device_id

Setting name (or Enter to finish): 

------------------------------------------------------------
Dependencies (optional)
------------------------------------------------------------

Package name (or Enter to finish): opencv-python
  ✓ Added: opencv-python

Package name (or Enter to finish): 

============================================================
PLUGIN SUMMARY
============================================================
Type:         capture
Name:         obs_capture
Display Name: OBS Studio Capture
Author:       John Doe
Description:  Captures from OBS Studio virtual camera
Version:      1.0.0

Settings: 1
  - device_id (int): 0

Dependencies: opencv-python
============================================================

Generate this plugin? (y/n): y

✓ Plugin generated successfully!

Location: plugins\capture\obs_capture

Next steps:
1. Edit worker.py to implement your plugin logic
2. Test your plugin in OptikR
3. Share your plugin with others!
```

---

## Generated Files

### plugin.json

Complete metadata file with all your settings:

```json
{
  "name": "obs_capture",
  "display_name": "OBS Studio Capture",
  "version": "1.0.0",
  "author": "John Doe",
  "description": "Captures from OBS Studio virtual camera",
  "type": "capture",
  "worker_script": "worker.py",
  "enabled_by_default": true,
  "settings": {
    "device_id": {
      "type": "int",
      "default": 0,
      "description": "OBS virtual camera device ID"
    }
  },
  "dependencies": [
    "opencv-python"
  ]
}
```

### worker.py

Template with TODO comments showing where to add your code:

```python
"""
OBS Studio Capture - Captures from OBS Studio virtual camera

Capture plugin worker script.
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent.parent.parent))

from src.workflow.base.base_worker import BaseWorker


class CaptureWorker(BaseWorker):
    """Worker for OBS Studio Capture."""
    
    def initialize(self, config: dict) -> bool:
        """Initialize capture system."""
        try:
            # TODO: Initialize your capture method here
            # Example: self.capture_device = cv2.VideoCapture(device_id)
            
            self.log("OBS Studio Capture initialized")
            return True
            
        except Exception as e:
            self.log(f"Failed to initialize: {e}")
            return False
    
    def process(self, data: dict) -> dict:
        """Capture a frame."""
        try:
            # TODO: Implement frame capture
            # See template for full example
            
            return {'error': 'Capture not implemented yet'}
            
        except Exception as e:
            return {'error': f'Capture failed: {e}'}
    
    def cleanup(self):
        """Clean up resources."""
        self.log("OBS Studio Capture cleanup")


if __name__ == '__main__':
    worker = CaptureWorker(name="obs_capture")
    worker.run()
```

### README.md

Documentation template with your plugin info:

```markdown
# OBS Studio Capture

Captures from OBS Studio virtual camera

## Information

- **Type:** capture
- **Version:** 1.0.0
- **Author:** John Doe

## Requirements

Python packages:
- `opencv-python`

Install with:
\`\`\`bash
pip install opencv-python
\`\`\`

## Settings

- **device_id** (int): OBS virtual camera device ID
  - Default: `0`

## Usage

1. Enable the plugin in OptikR's Pipeline Management tab
2. Configure settings if needed
3. Start translation

## Development

To modify this plugin:

1. Edit `worker.py` to implement your logic
2. Edit `plugin.json` to add/modify settings
3. Reload plugin in OptikR (no restart needed)
```

---

## Next Steps After Generation

### 1. Implement Your Logic

Edit `worker.py` and replace the TODO comments with your implementation:

**For Capture plugins:**
- Initialize your capture device in `initialize()`
- Capture frames in `process()`
- Return base64-encoded frame data

**For OCR plugins:**
- Initialize your OCR engine in `initialize()`
- Perform text recognition in `process()`
- Return text blocks with bounding boxes

**For Translation plugins:**
- Initialize your translation engine in `initialize()`
- Translate text in `process()`
- Return translations with original text

**For Optimizer plugins:**
- Initialize your optimizer in `initialize()`
- Optimize data in `process()`
- Return optimized data

### 2. Install Dependencies

If you added dependencies:

```bash
cd plugins/{type}/{name}
pip install -r requirements.txt
```

Or install manually:
```bash
pip install package1 package2
```

### 3. Test Your Plugin

1. Open OptikR
2. Go to Pipeline Management tab
3. Click "Rescan Plugins"
4. Enable your plugin
5. Configure settings
6. Test with translation

### 4. Debug Issues

Check logs for errors:
- Worker script errors appear in console
- Plugin validation errors shown in UI
- Subprocess errors logged separately

### 5. Share Your Plugin

Once working:

1. Zip the plugin folder
2. Share on GitHub or your website
3. Include installation instructions
4. Document any special requirements

---

## Plugin Templates

### Capture Plugin Template

**What to implement:**
- Frame capture from your source
- Convert to numpy array
- Encode as base64
- Return with shape info

**Example libraries:**
- `dxcam` - DirectX capture
- `opencv-python` - Camera/video capture
- `mss` - Cross-platform screenshot
- `pyautogui` - Simple screenshots

### OCR Plugin Template

**What to implement:**
- Decode base64 frame to numpy array
- Run OCR on frame
- Extract text and bounding boxes
- Return text blocks with confidence

**Example libraries:**
- `easyocr` - Multi-language OCR
- `pytesseract` - Tesseract wrapper
- `paddleocr` - PaddlePaddle OCR
- `keras-ocr` - Keras-based OCR

### Translation Plugin Template

**What to implement:**
- Extract text from text blocks
- Translate to target language
- Return translations with original text

**Example libraries:**
- `transformers` - Hugging Face models
- `googletrans` - Google Translate API
- `deep-translator` - Multiple translation APIs
- `argostranslate` - Offline translation

### Optimizer Plugin Template

**What to implement:**
- Analyze input data
- Apply optimization
- Return optimized data

**Example optimizations:**
- Frame skipping
- Batch processing
- Caching
- Parallel processing

---

## Tips & Best Practices

### Naming

- Use lowercase with underscores: `my_plugin`
- Be descriptive: `tesseract_ocr` not `ocr1`
- Avoid conflicts with existing plugins

### Settings

- Add settings for configurable options
- Use appropriate types (int, float, bool, string)
- Provide sensible defaults
- Document what each setting does

### Dependencies

- List all required packages
- Use common packages when possible
- Document version requirements if needed
- Test with fresh Python environment

### Error Handling

- Catch exceptions in `process()`
- Return `{'error': 'message'}` on failure
- Log errors with `self.log()`
- Provide helpful error messages

### Performance

- Initialize heavy resources in `initialize()`
- Don't reload models on every frame
- Use efficient data structures
- Profile your code if slow

### Testing

- Test with different inputs
- Test error cases
- Test with different settings
- Test in subprocess environment

---

## Troubleshooting

### "Plugin not found"

**Check:**
- Plugin folder is in correct location
- `plugin.json` exists and is valid
- Folder name matches plugin name

### "Worker script not found"

**Check:**
- `worker.py` exists in plugin folder
- `worker_script` in plugin.json is correct
- File has `.py` extension

### "Import error"

**Check:**
- Dependencies are installed
- Python path is correct
- `src.workflow.base` is accessible

### "Plugin validation failed"

**Check:**
- All required fields in plugin.json
- `type` is valid (capture/ocr/translation/optimizer)
- Settings have valid types
- JSON syntax is correct

### "Worker crashes"

**Check:**
- Exception handling in `process()`
- Resources initialized in `initialize()`
- Cleanup in `cleanup()`
- Test worker script directly

---

## Advanced Features

### Custom Settings Types

Add min/max for numeric settings:

```json
{
  "fps": {
    "type": "int",
    "default": 30,
    "description": "Frames per second",
    "min": 1,
    "max": 144
  }
}
```

Add options for dropdown:

```json
{
  "quality": {
    "type": "string",
    "default": "medium",
    "description": "Quality preset",
    "options": ["low", "medium", "high"]
  }
}
```

### Multiple Settings

Add as many settings as needed:

```python
Setting name: setting1
Setting name: setting2
Setting name: setting3
Setting name: (Enter to finish)
```

### Multiple Dependencies

List all required packages:

```python
Package name: numpy
Package name: opencv-python
Package name: pillow
Package name: (Enter to finish)
```

---

## Examples

### Example 1: Simple Screenshot Plugin

```bash
Plugin Type: 1 (Capture)
Name: simple_screenshot
Display Name: Simple Screenshot
Author: Your Name
Description: Basic screenshot capture
Version: 1.0.0
Settings: (none)
Dependencies: pillow
```

### Example 2: Tesseract OCR Plugin

```bash
Plugin Type: 2 (OCR)
Name: tesseract_ocr
Display Name: Tesseract OCR
Author: Your Name
Description: OCR using Tesseract
Version: 1.0.0
Settings:
  - language (string): OCR language
Dependencies: pytesseract, pillow
```

### Example 3: Google Translate Plugin

```bash
Plugin Type: 3 (Translation)
Name: google_translate
Display Name: Google Translate
Author: Your Name
Description: Translation using Google Translate API
Version: 1.0.0
Settings:
  - api_key (string): Google API key
Dependencies: googletrans
```

---

## Summary

The Plugin Generator makes it easy to create plugins:

1. **Run generator** - `python -m src.workflow.plugin_generator`
2. **Answer prompts** - Type, name, settings, etc.
3. **Get boilerplate** - Complete plugin structure generated
4. **Implement logic** - Fill in TODO sections
5. **Test plugin** - Load in OptikR
6. **Share** - Zip and distribute

**No manual file creation, no template copying, just answer questions and code!**

---

For more information, see:
- `PLUGIN_DEVELOPMENT_GUIDE.md` - Detailed development guide
- `PLUGIN_SYSTEM_FOR_EXE.md` - EXE distribution info
- Example plugins in `plugins/` folder
