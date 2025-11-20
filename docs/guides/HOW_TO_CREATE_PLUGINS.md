# How to Create Plugins for OptikR

## Quick Start

Want to add a new plugin? Here's how:

### Option 1: Auto-Generation (Easiest!)

Just install the package you want to use:

```bash
pip install easyocr  # For OCR
pip install mss      # For screen capture
pip install numba    # For optimization
pip install nltk     # For text processing
```

OptikR will automatically create plugins during startup! ✨

Or manually trigger auto-generation:

```bash
python run.py --auto-generate-missing
```

### Option 2: Use the Plugin Generator

```bash
python run.py --create-plugin
```

Follow the interactive prompts to create your plugin!

### Option 3: Manual Creation

Create a folder in the appropriate directory with the required files.

---

## Plugin Types

OptikR supports 5 types of plugins:

### 1. Capture Plugins
**Location**: `plugins/capture/`
**Purpose**: Screen capture methods
**Auto-generation**: ✅ Yes! (automatically creates plugins for installed packages)
**Supported packages**: mss, pyautogui, pyscreenshot

### 2. OCR Plugins
**Location**: `plugins/ocr/`
**Purpose**: Text recognition engines
**Auto-generation**: ✅ Yes! (automatically creates plugins for installed packages)
**Supported packages**: easyocr, paddleocr, tesseract, manga_ocr

### 3. Translation Plugins
**Location**: `plugins/translation/`
**Purpose**: Translation engines
**Auto-generation**: ✅ Yes! (when downloading models)

### 4. Optimizer Plugins
**Location**: `plugins/optimizers/`
**Purpose**: Performance optimization
**Auto-generation**: ✅ Yes! (automatically creates plugins for installed packages)
**Supported packages**: numba, cython

### 5. Text Processor Plugins
**Location**: `plugins/text_processors/`
**Purpose**: Text processing/filtering
**Auto-generation**: ✅ Yes! (automatically creates plugins for installed packages)
**Supported packages**: nltk, spacy, textblob, regex

---

## Method 1: Using the Generator (Recommended)

### Step 1: Run the Generator

```bash
python create_plugin.py
```

### Step 2: Answer the Questions

The generator will ask you:
- Plugin type (capture, ocr, translation, optimizer, text_processor)
- Plugin name (e.g., "my_ocr_engine")
- Display name (e.g., "My OCR Engine")
- Author name
- Description
- Version
- Settings (optional)
- Dependencies (optional)

### Step 3: Implement Your Plugin

The generator creates:
- `plugin.json` - Metadata
- `worker.py` - Your implementation goes here
- `README.md` - Documentation

Edit `worker.py` to implement your plugin logic!

---

## Method 2: Manual Creation

### For OCR Plugins (Auto-Generated)

Just install the Python package:

```bash
pip install your-ocr-package
```

The system will automatically create the plugin! ✨

### For Other Plugins (Manual)

#### Step 1: Create Folder Structure

```
plugins/[type]/[your_plugin_name]/
├── plugin.json          # Required
├── __init__.py          # Required (or worker.py)
└── README.md            # Optional
```

#### Step 2: Create plugin.json

```json
{
  "name": "your_plugin_name",
  "display_name": "Your Plugin Name",
  "version": "1.0.0",
  "author": "Your Name",
  "description": "What your plugin does",
  "type": "capture",
  "enabled_by_default": true,
  "settings": {
    "setting_name": {
      "type": "string",
      "default": "value",
      "description": "Setting description"
    }
  },
  "dependencies": [
    "required-package"
  ]
}
```

#### Step 3: Create Implementation

**For OCR plugins** - Create `__init__.py`:

```python
from src.ocr.ocr_engine_interface import IOCREngine

class OCREngine(IOCREngine):
    def __init__(self, engine_name: str = "your_engine", engine_type=None):
        super().__init__(engine_name, engine_type)
    
    def initialize(self, config: dict) -> bool:
        # Initialize your engine
        return True
    
    def extract_text(self, frame, options):
        # Extract text from image
        return []
```

**For Translation plugins** - Create `worker.py`:

```python
from src.translation.translation_engine_interface import AbstractTranslationEngine

class TranslationEngine(AbstractTranslationEngine):
    def __init__(self, engine_name: str = "your_engine"):
        super().__init__(engine_name)
    
    def initialize(self, config: dict) -> bool:
        # Initialize your engine
        return True
    
    def translate_text(self, text: str, src_lang: str, tgt_lang: str, options=None):
        # Translate text
        return text
```

**For Capture plugins** - Create `worker.py`:

```python
class CapturePlugin:
    def __init__(self):
        pass
    
    def capture(self, region):
        # Capture screen region
        return image
```

---

## Testing Your Plugin

### Step 1: Restart OptikR

Your plugin will be discovered automatically on startup.

### Step 2: Check Settings

Go to Settings → [Plugin Type] and verify your plugin appears in the list.

### Step 3: Test Functionality

Select your plugin and test it!

---

## Examples

### Example 1: Creating a Custom OCR Engine

```bash
python create_plugin.py
```

```
Select type: 2 (OCR)
Plugin name: my_custom_ocr
Display name: My Custom OCR
Author: Your Name
Description: Custom OCR engine for special text
Version: 1.0.0
```

Then edit `plugins/ocr/my_custom_ocr/worker.py` to implement your OCR logic.

### Example 2: Creating a Text Processor

```bash
python create_plugin.py
```

```
Select type: 5 (Text Processor)
Plugin name: emoji_filter
Display name: Emoji Filter
Author: Your Name
Description: Removes emojis from text
Version: 1.0.0
```

Then edit `plugins/text_processors/emoji_filter/worker.py` to implement filtering.

---

## Plugin Requirements

### All Plugins Must Have:
- ✅ `plugin.json` with valid metadata
- ✅ Implementation file (`__init__.py` or `worker.py`)
- ✅ Correct class name (`OCREngine`, `TranslationEngine`, etc.)

### Optional But Recommended:
- 📝 `README.md` with documentation
- 🧪 Tests for your plugin
- 📦 Requirements listed in `plugin.json`

---

## Troubleshooting

### Plugin Not Appearing

1. Check folder location is correct
2. Verify `plugin.json` is valid JSON
3. Ensure dependencies are installed
4. Restart OptikR

### Plugin Shows "Not Loaded"

1. Check implementation file exists
2. Verify class name is correct
3. Check for syntax errors
4. Look at logs for error messages

### Plugin Crashes

1. Check logs in `logs/` folder
2. Verify all dependencies are installed
3. Test your code independently
4. Add error handling

---

## Best Practices

1. **Test thoroughly** - Test your plugin before sharing
2. **Document well** - Add clear README and comments
3. **Handle errors** - Add try/catch blocks
4. **List dependencies** - Include all required packages
5. **Version properly** - Use semantic versioning (1.0.0)
6. **Keep it simple** - Start small, add features later

---

## Sharing Your Plugin

Want to share your plugin with others?

1. Create a GitHub repository
2. Include installation instructions
3. List dependencies clearly
4. Add usage examples
5. Share on OptikR community forums

---

## Command-Line Reference

OptikR provides several command-line options for plugin management:

### Auto-Generate Missing Plugins

Scans for installed packages and creates plugins automatically:

```bash
python run.py --auto-generate-missing
```

This will:
- Check for installed OCR engines (easyocr, paddleocr, tesseract, manga_ocr)
- Check for capture libraries (mss, pyautogui, pyscreenshot)
- Check for optimizers (numba, cython)
- Check for text processors (nltk, spacy, textblob, regex)
- Create plugins for any that are installed but missing

### Interactive Plugin Generator

Launch the interactive plugin creation wizard:

```bash
python run.py --create-plugin
```

### Generate from Template Path

Generate a plugin from a specific template directory:

```bash
python run.py --plugin-generator "path/to/template"
```

### Using Makefile Commands

If you have `make` installed, you can use these shortcuts:

```bash
make create-plugin          # Interactive generator
make auto-generate          # Auto-generate missing plugins
make list-plugins           # List all discovered plugins
make clean-auto-plugins     # Remove auto-generated plugins
make help                   # Show all commands
```

See `PLUGIN_COMMANDS.mk` for the complete list of commands.

### EXE Compatibility

All command-line features work in EXE builds:
- ✅ Plugin generation works (creates in user directory)
- ✅ Auto-generation works (discovers installed packages)
- ✅ Headless mode works (runs without UI)

When using the EXE:
```bash
OptikR --auto-generate-missing
OptikR --create-plugin
```

---

## Need Help?

- Check `docs/GENERATORS_EXPLAINED.md` for generator details
- Look at existing plugins for examples
- Ask in the community forums
- Open an issue on GitHub

---

**Happy plugin creating!** 🎉
