# Plugin Generators Explained

This document explains the different plugin generators in the codebase and when to use them.

## Generator Files

### 1. `src/ocr/DEPRECATED_ocr_plugin_json_generator.py`

**Status**: ⚠️ DEPRECATED - Not used anymore

**Purpose**: Used to create plugin.json files for OCR engines in the OLD plugin system (`src/ocr/engines/`)

**Why deprecated**: 
- The new plugin system auto-generates plugins in `dev/plugins/ocr/`
- Plugin discovery now checks if packages are actually installed
- This generator created empty plugin.json files without implementation

**Do NOT use this file** - It's kept for reference only.

---

### 2. `src/translation/translation_plugin_generator_FOR_MODELS.py`

**Status**: ✅ ACTIVE - Used for translation models

**Purpose**: Automatically generates translation plugins when you download translation models

**What it does**:
- Creates plugin folders in `plugins/translation/`
- Generates `plugin.json` with model metadata
- Creates `worker.py` for the translation engine
- Supports multiple model types:
  - MarianMT (Helsinki-NLP)
  - NLLB (Meta AI)
  - M2M-100 (Facebook)
  - mBART (Facebook)
  - Custom models

**When it's used**:
- When you download a new translation model
- When the universal model manager installs a model
- Automatically creates the plugin structure

**Example**:
```python
from src.translation.translation_plugin_generator_FOR_MODELS import TranslationPluginGenerator

generator = TranslationPluginGenerator()
generator.generate_plugin_for_model(
    model_name="Helsinki-NLP/opus-mt-en-de",
    source_lang="en",
    target_lang="de",
    model_info={...},
    model_type="marianmt"
)
```

---

### 3. `src/workflow/universal_plugin_generator.py`

**Status**: ✅ ACTIVE - Universal plugin creator

**Purpose**: Interactive CLI tool to create plugin boilerplate for ANY plugin type

**What it does**:
- Asks you questions about your plugin
- Creates folder structure
- Generates `plugin.json`, `worker.py`, `README.md`
- Supports ALL 5 plugin types:
  - Capture plugins
  - OCR plugins
  - Translation plugins
  - Optimizer plugins
  - Text Processor plugins

**When to use**:
- When creating a completely new plugin
- When you want to manually create a plugin
- For learning how plugins are structured
- When you need a custom plugin type

**How to use**:
```bash
# Easy way (from project root)
python create_plugin.py

# Or directly
python src/workflow/universal_plugin_generator.py
```

Then follow the interactive prompts.

---

## Built-in Auto-Generation

Some plugin systems have **built-in auto-generation** that doesn't require a separate generator file:

### OCR Auto-Generation

**Location**: `src/ocr/ocr_plugin_manager.py` → `_auto_generate_missing_plugins()`

**How it works**:
- Automatically detects installed OCR packages (easyocr, paddleocr, manga-ocr, pytesseract)
- Creates plugin folders in `plugins/ocr/` if they don't exist
- Generates `plugin.json` and basic `__init__.py` with OCREngine class
- Skips packages that already have plugins

**When it runs**:
- Automatically during plugin discovery at startup
- No user action needed!

**Example**: If you install `manga-ocr` package, the system automatically creates `plugins/ocr/manga_ocr/` with all necessary files.

---

## Current Plugin System

### OCR Plugins

**Location**: `dev/plugins/ocr/`

**How they're created**:
1. **Manual creation** - Create folder with `__init__.py` and `plugin.json`
2. **Auto-discovery** - Plugin manager discovers installed packages and creates plugins automatically

**Example structure**:
```
plugins/ocr/easyocr/
├── __init__.py          # OCREngine class implementation
├── plugin.json          # Metadata
├── worker.py            # Optional worker process
└── README.md            # Documentation
```

### Translation Plugins

**Location**: `dev/plugins/translation/`

**How they're created**:
1. **Auto-generated** - When you download a model, `translation_plugin_generator_FOR_MODELS.py` creates the plugin
2. **Manual creation** - Create folder with required files

**Example structure**:
```
plugins/translation/marianmt_en_de/
├── marianmt_engine.py   # TranslationEngine class
├── plugin.json          # Metadata
├── worker.py            # Worker process
└── README.md            # Documentation
```

---

## Summary

| Generator | Status | Purpose | When to Use |
|-----------|--------|---------|-------------|
| `DEPRECATED_ocr_plugin_json_generator.py` | ⚠️ Deprecated | Old OCR plugin.json creator | Never (kept for reference) |
| `translation_plugin_generator_FOR_MODELS.py` | ✅ Active | Auto-creates translation plugins | Automatic (when downloading models) |
| `universal_plugin_generator.py` | ✅ Active | CLI tool for ALL plugin types | When creating custom plugins |

---

## For Developers

### Creating a New OCR Plugin

**Don't use the generators!** Instead:

1. Create folder in `plugins/ocr/your_engine/`
2. Create `__init__.py` with `OCREngine` class
3. Create `plugin.json` with metadata
4. The plugin manager will discover it automatically

### Creating a New Translation Plugin

**Use the generator!**

The `translation_plugin_generator_FOR_MODELS.py` will automatically create plugins when you download models through the model manager.

### Creating a Custom Plugin Type

Use `old_plugin_generator.py` as a starting point, then customize the generated files.

---

## Questions?

- **Which generator should I use?** - Probably none! The system auto-discovers plugins now.
- **How do I add a new OCR engine?** - Create a folder in `plugins/ocr/` with `__init__.py` and `plugin.json`
- **How do I add a new translation model?** - Use the model manager, it will auto-generate the plugin
- **Can I delete the deprecated generator?** - Yes, but keep it for now as reference

---

**Last Updated**: 2024-11-16
