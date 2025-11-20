# Plugin Development Guide

## Table of Contents
1. [Plugin System Overview](#plugin-system-overview)
2. [Plugin Types](#plugin-types)
3. [Creating Plugins](#creating-plugins)
4. [Auto Plugin Discovery](#auto-plugin-discovery)
5. [Universal Plugin Generator](#universal-plugin-generator)
6. [Plugin Best Practices](#plugin-best-practices)
7. [Examples](#examples)
8. [Troubleshooting](#troubleshooting)

---

## Plugin System Overview

OptikR uses a modular plugin system that allows you to extend functionality without modifying core code.

### Plugin Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                    PLUGIN SYSTEM                             │
└─────────────────────────────────────────────────────────────┘

plugins/
├── capture/              ← Screen capture methods
│   ├── dxcam_capture_gpu/
│   │   ├── plugin.json
│   │   └── worker.py
│   └── screenshot_capture_cpu/
│       ├── plugin.json
│       └── worker.py
│
├── ocr/                  ← Text extraction engines
│   ├── easyocr/
│   ├── tesseract/
│   ├── paddleocr/
│   ├── manga_ocr/
│   └── hybrid_ocr/
│
├── optimizers/           ← Performance & quality plugins
│   ├── frame_skip/
│   ├── translation_cache/
│   ├── learning_dictionary/
│   ├── text_block_merger/
│   ├── parallel_ocr/
│   └── ... (15 total)
│
├── text_processors/      ← Text cleaning & processing
│   ├── regex/
│   └── spell_corrector/
│
└── translation/          ← Translation engines
    ├── marianmt_gpu/
    └── libretranslate/
```

### Plugin Components

Every plugin consists of:
1. **plugin.json** - Configuration and metadata
2. **Implementation file** - Python code (worker.py, optimizer.py, etc.)
3. **Optional files** - README.md, requirements.txt, etc.

---

## Plugin Types

### 1. Capture Plugins
**Purpose**: Capture screen content
**File**: `worker.py`
**Interface**: `capture(region) → frame`


**Example**:
```python
def capture(region):
    """Capture screen region."""
    # Your capture logic
    return frame_data
```

### 2. OCR Plugins
**Purpose**: Extract text from images
**File**: `worker.py`
**Interface**: `process_frame(frame) → text_blocks`

**Example**:
```python
def process_frame(frame):
    """Extract text from frame."""
    # Your OCR logic
    return text_blocks
```

### 3. Optimizer Plugins
**Purpose**: Enhance pipeline performance/quality
**File**: `optimizer.py`
**Interface**: `process(data) → modified_data`

**Stages**:
- **pre** - Before main operation
- **post** - After main operation
- **core** - Replace main operation
- **global** - Affect entire pipeline

**Example**:
```python
class MyOptimizer:
    def process(self, data):
        """Process pipeline data."""
        # Your optimization logic
        return data
```

### 4. Text Processor Plugins
**Purpose**: Clean and process text
**File**: `__init__.py` or `processor.py`
**Interface**: `process_text(text) → cleaned_text`

**Example**:
```python
def process_text(text):
    """Process text."""
    # Your processing logic
    return cleaned_text
```

### 5. Translation Plugins
**Purpose**: Translate text
**File**: `worker.py`
**Interface**: `translate(text, source_lang, target_lang) → translated_text`

**Example**:
```python
def translate(text, source_lang, target_lang):
    """Translate text."""
    # Your translation logic
    return translated_text
```

---

## Creating Plugins

### Quick Start: 3 Steps

1. **Create directory**: `plugins/{type}/{name}/`
2. **Create plugin.json**: Configuration file
3. **Create implementation**: Python file with your logic

### Step-by-Step Guide

#### Step 1: Choose Plugin Type

Decide what your plugin will do:
- Capture screen? → `capture`
- Extract text? → `ocr`
- Optimize performance? → `optimizer`
- Clean text? → `text_processor`
- Translate text? → `translation`

#### Step 2: Create Directory

```bash
mkdir -p plugins/{type}/{name}
```

Example:
```bash
mkdir -p plugins/optimizers/my_awesome_optimizer
```

#### Step 3: Create plugin.json

Minimum required fields:
```json
{
  "name": "my_plugin",
  "display_name": "My Awesome Plugin",
  "version": "1.0.0",
  "type": "optimizer",
  "description": "Does something awesome",
  "author": "Your Name",
  "enabled": false
}
```

Full example with settings:
```json
{
  "name": "my_optimizer",
  "display_name": "My Awesome Optimizer",
  "version": "1.0.0",
  "type": "optimizer",
  "target_stage": "translation",
  "stage": "pre",
  "description": "Optimizes translation performance",
  "author": "Your Name",
  "enabled": false,
  "essential": false,
  "settings": {
    "threshold": {
      "type": "float",
      "default": 0.5,
      "min": 0.0,
      "max": 1.0,
      "description": "Optimization threshold"
    },
    "mode": {
      "type": "string",
      "default": "fast",
      "options": ["fast", "accurate", "balanced"],
      "description": "Processing mode"
    },
    "enabled_features": {
      "type": "boolean",
      "default": true,
      "description": "Enable advanced features"
    }
  },
  "performance": {
    "benefit": "20% faster processing",
    "overhead": "< 1ms per frame",
    "memory": "Minimal (< 10MB)"
  },
  "dependencies": ["numpy", "requests"]
}
```

#### Step 4: Create Implementation File

**For Optimizer** (`optimizer.py`):


```python
"""
My Awesome Optimizer Plugin
"""

from typing import Dict, Any
import time


class MyAwesomeOptimizer:
    """Optimizer implementation."""
    
    def __init__(self, config: Dict[str, Any]):
        """Initialize with configuration."""
        self.config = config
        self.threshold = config.get('threshold', 0.5)
        self.mode = config.get('mode', 'fast')
        
        # Statistics
        self.total_processed = 0
        self.total_optimized = 0
        self.total_time = 0.0
        
        print(f"[MY_OPTIMIZER] Initialized (threshold={self.threshold}, mode={self.mode})")
    
    def process(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Process pipeline data.
        
        Args:
            data: Pipeline data dictionary containing:
                - frame: Frame object
                - texts: List of text blocks
                - translations: List of translations
                - etc.
        
        Returns:
            Modified data dictionary
        """
        start_time = time.time()
        self.total_processed += 1
        
        # Your optimization logic here
        if self._should_optimize(data):
            data = self._optimize(data)
            self.total_optimized += 1
        
        self.total_time += time.time() - start_time
        return data
    
    def _should_optimize(self, data: Dict[str, Any]) -> bool:
        """Check if data should be optimized."""
        # Example: Check confidence threshold
        confidence = data.get('confidence', 0.0)
        return confidence >= self.threshold
    
    def _optimize(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """Optimize the data."""
        # Example: Filter low-quality items
        if 'texts' in data:
            data['texts'] = [t for t in data['texts'] 
                           if t.get('confidence', 0) >= self.threshold]
        return data
    
    def get_stats(self) -> Dict[str, Any]:
        """Get optimizer statistics."""
        rate = (self.total_optimized / self.total_processed * 100) if self.total_processed > 0 else 0
        avg_time = (self.total_time / self.total_processed * 1000) if self.total_processed > 0 else 0
        
        return {
            'total_processed': self.total_processed,
            'total_optimized': self.total_optimized,
            'optimization_rate': f"{rate:.1f}%",
            'avg_time_ms': f"{avg_time:.2f}ms"
        }
    
    def reset(self):
        """Reset optimizer state."""
        self.total_processed = 0
        self.total_optimized = 0
        self.total_time = 0.0


# Plugin interface (required)
def initialize(config: Dict[str, Any]):
    """Initialize the optimizer plugin."""
    return MyAwesomeOptimizer(config)
```

#### Step 5: Test Your Plugin

1. **Restart OptikR** - Plugins are discovered at startup
2. **Check logs** - Look for initialization message
3. **Enable plugin** - Go to Settings → Pipeline → Plugins
4. **Run translation** - Start capturing and translating
5. **Check stats** - View plugin statistics

---

## Auto Plugin Discovery

OptikR automatically discovers plugins at startup without any configuration.

### Discovery Process

```
┌────────────────────────────────────────────────────────────────┐
│              AUTO PLUGIN DISCOVERY PROCESS                      │
└────────────────────────────────────────────────────────────────┘

Step 1: Scan Directories
├─ plugins/capture/
├─ plugins/ocr/
├─ plugins/optimizers/
├─ plugins/text_processors/
└─ plugins/translation/
        ↓
Step 2: Find plugin.json Files
├─ plugins/optimizers/my_optimizer/plugin.json ✓
├─ plugins/optimizers/frame_skip/plugin.json ✓
└─ ... (scan all subdirectories)
        ↓
Step 3: Parse Configuration
├─ Read JSON
├─ Validate required fields
└─ Extract metadata
        ↓
Step 4: Validate Structure
├─ Check implementation file exists
├─ Verify required functions
└─ Check dependencies
        ↓
Step 5: Load Implementation
├─ Import Python module
├─ Call initialize() function
└─ Store plugin instance
        ↓
Step 6: Register Plugin
├─ Add to plugin registry
├─ Make available in UI
└─ Ready to use!
        ↓
Step 7: Plugin Available
└─ Appears in Settings → Pipeline → Plugins
```

### Directory Requirements

```
plugins/
└── {type}/                    ← Must match plugin type
    └── {name}/                ← Must match plugin.json "name"
        ├── plugin.json        ← Required
        └── {implementation}   ← Required (see below)
```

### Implementation File Names

| Plugin Type | File Name |
|-------------|-----------|
| Capture | `worker.py` |
| OCR | `worker.py` |
| Optimizer | `optimizer.py` |
| Text Processor | `__init__.py` or `processor.py` |
| Translation | `worker.py` |

### Validation Checks

The system validates:

1. ✅ **plugin.json exists** and is valid JSON
2. ✅ **Required fields** present:
   - `name` (string)
   - `type` (string)
   - `version` (string)
3. ✅ **Implementation file** exists
4. ✅ **Required functions** present:
   - Optimizer: `initialize(config)`
   - Text Processor: `initialize(config)`, `process_text(text)`
   - Translation: `initialize(config)`, `translate(...)`
5. ✅ **Dependencies** available (if specified)

### Hot Reload

Plugins can be reloaded without restarting:

**Option 1: UI Button**
1. Go to Settings → Pipeline
2. Click "Reload Plugins" (if available)

**Option 2: Restart OptikR**
1. Close application
2. Reopen
3. Plugins automatically reloaded

---

## Universal Plugin Generator

OptikR includes a universal plugin generator for quick plugin creation.

### Using the Generator

#### Command Line Mode

```bash
# Basic usage
python generate_plugin.py --type optimizer --name my_optimizer

# With all options
python generate_plugin.py \
  --type optimizer \
  --name my_optimizer \
  --display-name "My Awesome Optimizer" \
  --stage translation \
  --author "Your Name" \
  --description "Does something awesome"
```

#### Interactive Mode

```bash
python generate_plugin.py
```

**Prompts**:
```
Plugin Type? (capture/ocr/optimizer/text_processor/translation): optimizer
Plugin Name? my_optimizer
Display Name? My Awesome Optimizer
Target Stage? (capture/ocr/translation/pipeline): translation
Stage? (pre/post/core/global): pre
Description? Optimizes translation performance
Author? Your Name
```

### Generated Files

```
plugins/optimizers/my_optimizer/
├── plugin.json          ← Configuration
├── optimizer.py         ← Implementation boilerplate
└── README.md           ← Usage instructions
```

### Boilerplate Code

The generator includes:

✅ **Class structure** with __init__
✅ **process() method** with type hints
✅ **get_stats() method** for statistics
✅ **reset() method** for state reset
✅ **Plugin interface** functions
✅ **Logging setup**
✅ **Error handling**
✅ **Docstrings**
✅ **Example logic**

### Customization After Generation

1. **Edit plugin.json** - Add settings, adjust metadata
2. **Implement process()** - Add your logic
3. **Add custom methods** - Extend functionality
4. **Update statistics** - Track what matters
5. **Test thoroughly** - Verify behavior

---

## Plugin Best Practices

### Performance

**DO**:
- ✅ Keep processing fast (< 5ms overhead)
- ✅ Cache expensive operations
- ✅ Use efficient algorithms
- ✅ Profile your code

**DON'T**:
- ❌ Block the pipeline
- ❌ Do heavy I/O in process()
- ❌ Create memory leaks
- ❌ Ignore performance

### Error Handling

**DO**:
- ✅ Catch all exceptions
- ✅ Log errors properly
- ✅ Return original data on error
- ✅ Provide fallbacks

**DON'T**:
- ❌ Let exceptions crash pipeline
- ❌ Silently fail
- ❌ Return None on error
- ❌ Ignore edge cases

### Configuration

**DO**:
- ✅ Provide sensible defaults
- ✅ Validate settings
- ✅ Document all options
- ✅ Use type hints

**DON'T**:
- ❌ Require complex setup
- ❌ Use magic numbers
- ❌ Ignore invalid settings
- ❌ Break on missing config

### Testing

**DO**:
- ✅ Test with real data
- ✅ Test edge cases
- ✅ Measure performance
- ✅ Test compatibility

**DON'T**:
- ❌ Skip testing
- ❌ Test only happy path
- ❌ Ignore warnings
- ❌ Deploy untested code

---

## Examples

### Example 1: Simple Text Filter

```python
def process(self, data: Dict[str, Any]) -> Dict[str, Any]:
    """Filter short texts."""
    if 'texts' in data:
        # Keep only texts with 3+ characters
        data['texts'] = [
            t for t in data['texts'] 
            if len(t.get('text', '')) >= 3
        ]
    return data
```

### Example 2: Performance Tracker

```python
def process(self, data: Dict[str, Any]) -> Dict[str, Any]:
    """Track processing time per stage."""
    import time
    
    stage = data.get('stage', 'unknown')
    start_time = time.time()
    
    # Process data (your logic here)
    
    elapsed = time.time() - start_time
    
    # Track statistics
    if stage not in self.stage_times:
        self.stage_times[stage] = []
    self.stage_times[stage].append(elapsed)
    
    # Add timing to data
    data['processing_time'] = elapsed
    
    return data
```

### Example 3: Conditional Processing

```python
def process(self, data: Dict[str, Any]) -> Dict[str, Any]:
    """Process only high-confidence data."""
    confidence = data.get('confidence', 0.0)
    
    if confidence >= self.threshold:
        # High confidence - apply optimization
        data = self._optimize(data)
        self.optimized_count += 1
    else:
        # Low confidence - skip
        self.skipped_count += 1
    
    return data
```

### Example 4: Caching

```python
def process(self, data: Dict[str, Any]) -> Dict[str, Any]:
    """Cache expensive operations."""
    text = data.get('text', '')
    
    # Check cache
    if text in self.cache:
        data['result'] = self.cache[text]
        self.cache_hits += 1
        return data
    
    # Process (expensive operation)
    result = self._expensive_operation(text)
    
    # Save to cache
    self.cache[text] = result
    data['result'] = result
    self.cache_misses += 1
    
    return data
```

---

## Troubleshooting

### Plugin Not Appearing

**Problem**: Plugin doesn't show up in UI

**Solutions**:
1. Check plugin.json is valid JSON
2. Verify plugin name matches directory name
3. Ensure implementation file exists
4. Check file naming (optimizer.py, worker.py, etc.)
5. Restart OptikR
6. Check logs for errors

### Plugin Not Working

**Problem**: Plugin enabled but not functioning

**Solutions**:
1. Check plugin is actually enabled in settings
2. Verify settings are correct
3. Check logs for errors
4. Add debug logging to your code
5. Test with simple data
6. Verify plugin stage (pre/post/core)

### Performance Issues

**Problem**: Plugin slows down pipeline

**Solutions**:
1. Profile your code
2. Remove blocking operations
3. Reduce logging in hot paths
4. Use caching for expensive operations
5. Consider async operations
6. Optimize algorithms

### Compatibility Issues

**Problem**: Plugin conflicts with others

**Solutions**:
1. Check plugin stage order
2. Verify data format expectations
3. Test with other plugins disabled
4. Check for data modifications
5. Review plugin dependencies
6. Adjust plugin priority

### Import Errors

**Problem**: Module not found errors

**Solutions**:
1. Check dependencies in plugin.json
2. Install required packages
3. Verify Python path
4. Check import statements
5. Use absolute imports
6. Add __init__.py files

---

## Summary

### Key Takeaways

✅ **Plugin System** - Modular, extensible, discoverable
✅ **5 Plugin Types** - Capture, OCR, Optimizer, Text Processor, Translation
✅ **Auto-Discovery** - Drop in folder, it works
✅ **Generator** - Create plugins in seconds
✅ **Best Practices** - Performance, errors, testing
✅ **Examples** - Copy-paste ready code

### Quick Reference

**Create Plugin**:
1. `mkdir plugins/{type}/{name}`
2. Create `plugin.json`
3. Create implementation file
4. Restart OptikR

**Plugin Interface**:
- Optimizer: `initialize(config)`, `process(data)`
- Text Processor: `initialize(config)`, `process_text(text)`
- Translation: `initialize(config)`, `translate(...)`

**File Names**:
- Capture/OCR/Translation: `worker.py`
- Optimizer: `optimizer.py`
- Text Processor: `__init__.py` or `processor.py`

### Next Steps

1. Review existing plugins for examples
2. Create your first plugin using generator
3. Test with real data
4. Share with community
5. Contribute improvements

Happy plugin development! 🚀


---

## Model Discovery and Manual Plugin Creation

### Overview

OptikR supports automatic discovery of manually added AI models. This allows you to:
1. Download models from HuggingFace manually
2. Place them in the models folder
3. Scan and register them
4. Generate plugins automatically

### Supported Model Types

#### OCR Models
- **Location**: `system_data/ai_models/ocr/`
- **Engines**: EasyOCR, Tesseract, PaddleOCR, Manga OCR
- **Discovery**: ✅ Automatic scanning available

#### Translation Models
- **Location**: `models/language/` or `system_data/ai_models/translation/`
- **Types**: MarianMT, NLLB, M2M100, mBART
- **Discovery**: ✅ Automatic scanning available (NEW!)

### How Model Discovery Works

#### Step 1: Add Model Manually

Download a model from HuggingFace and place it in the appropriate folder:

```
models/language/
└── opus-mt-en-de/              ← Your manually added model
    ├── config.json             ← Required
    ├── pytorch_model.bin       ← Required (or model.safetensors)
    ├── tokenizer.json
    └── vocab.json
```

**Requirements**:
- Must have `config.json` (model configuration)
- Must have weights: `pytorch_model.bin` OR `model.safetensors`

#### Step 2: Scan for Models

**For Translation Models**:
1. Open Settings → Translation Tab
2. Click "Model Manager" button
3. Click "Custom Models" tab
4. Click "🔍 Scan for Models" button

**For OCR Models**:
1. Open Settings → OCR Tab
2. Click "Model Manager" button
3. Click "Custom Models" tab
4. Click "🔍 Scan for Models" button

#### Step 3: Register Model

After scanning, unregistered models will be highlighted:

```
Model Name          Config  Weights  Status
opus-mt-en-de       ✓       ✓        ⚠️ Not Registered
```

1. Select the unregistered model
2. Click "📝 Register Selected Model"
3. Enter language pair (e.g., "en-de")
4. Enter description (optional)
5. Click OK

The model is now registered in the system!

#### Step 4: Generate Plugin

After registration:

1. Select the registered model
2. Click "🔌 Create Plugin for Selected"
3. Plugin is automatically generated in `plugins/translation/` or `plugins/ocr/`
4. Restart application (or reload plugins)
5. Plugin appears in available engines!

### Model Discovery API

#### Translation Models

```python
from app.translation.universal_model_manager import UniversalModelManager

# Create manager
manager = UniversalModelManager(model_type="marianmt")

# Discover unregistered models
discovered = manager.discover_models()
# Returns: ['opus-mt-en-de', 'opus-mt-ja-en', ...]

# Register a discovered model
success = manager.register_discovered_model(
    model_name="opus-mt-en-de",
    language_pair="en-de",
    description="English to German translation"
)

# Check registered models
models = manager.get_available_models()
```

#### OCR Models

```python
from app.ocr.ocr_model_manager import OCRModelManager

# Create manager
manager = OCRModelManager()

# Discover unregistered models
discovered = manager.discover_models()
# Returns: [OCRModel(...), OCRModel(...), ...]

# Register a discovered model
success = manager.register_model(
    model_name="custom_easyocr_model",
    engine_type="easyocr",
    language="en"
)
```

### Example: Complete Workflow

#### Adding a MarianMT Model

```bash
# 1. Download model from HuggingFace
git clone https://huggingface.co/Helsinki-NLP/opus-mt-fr-en

# 2. Move to models folder
mv opus-mt-fr-en D:/OptikR/release/models/language/

# 3. Open OptikR
# 4. Settings → Translation → Model Manager → Custom Models
# 5. Click "Scan for Models"
# 6. Select "opus-mt-fr-en"
# 7. Click "Register Selected Model"
#    - Language pair: fr-en
#    - Description: French to English
# 8. Click "Create Plugin for Selected"
# 9. Restart OptikR
# 10. New engine "opus-mt-fr-en" available!
```

### Model Folder Structure

#### Recommended Structure

```
D:/OptikR/release/
├── models/
│   └── language/                    ← Translation models
│       ├── language_registry/       ← Registry (auto-generated)
│       ├── opus-mt-en-de/          ← Downloaded or manual
│       ├── opus-mt-ja-en/          ← Downloaded or manual
│       └── facebook-nllb-200/      ← Downloaded or manual
│
├── system_data/
│   └── ai_models/
│       ├── ocr/                     ← OCR models
│       │   ├── easyocr_en/
│       │   └── tesseract_jpn/
│       └── translation/             ← Alternative location
│           └── marianmt/
│
└── plugins/
    ├── ocr/                         ← Auto-generated OCR plugins
    │   └── custom_easyocr_en/
    └── translation/                 ← Auto-generated translation plugins
        └── custom_opus_mt_en_de/
```

### Benefits of Model Discovery

1. **Flexibility**: Add any HuggingFace model manually
2. **No Code**: Generate plugins without writing code
3. **Version Control**: Use specific model versions
4. **Offline**: Download models once, use offline
5. **Custom Models**: Use fine-tuned or custom models
6. **Easy Sharing**: Share model folders with team

### Troubleshooting

#### Model Not Detected

**Problem**: Model doesn't appear in scan results

**Solutions**:
- ✅ Check folder structure (must have `config.json` + weights)
- ✅ Verify file names: `pytorch_model.bin` or `model.safetensors`
- ✅ Check folder location (correct models directory)
- ✅ Restart scan after adding files

#### Registration Failed

**Problem**: Cannot register discovered model

**Solutions**:
- ✅ Check model is valid HuggingFace format
- ✅ Verify language pair format (e.g., "en-de" not "en_de")
- ✅ Check console for error messages
- ✅ Ensure model folder has correct permissions

#### Plugin Generation Failed

**Problem**: Plugin not created after registration

**Solutions**:
- ✅ Ensure model is registered first
- ✅ Check `plugins/` folder permissions
- ✅ Verify plugin doesn't already exist
- ✅ Check console for error messages

### Advanced: Manual Plugin Creation

If auto-generation doesn't work, you can create plugins manually:

#### 1. Create Plugin Folder

```bash
mkdir plugins/translation/my_custom_model
```

#### 2. Create plugin.json

```json
{
  "name": "my_custom_model",
  "display_name": "My Custom Model",
  "version": "1.0.0",
  "author": "Your Name",
  "description": "Custom translation model",
  "type": "translation",
  "worker_script": "worker.py",
  "enabled_by_default": true,
  "settings": {
    "model_path": {
      "type": "string",
      "default": "models/language/my_custom_model",
      "description": "Path to model folder"
    }
  }
}
```

#### 3. Create worker.py

```python
from transformers import AutoModelForSeq2SeqLM, AutoTokenizer

class TranslationEngine:
    def __init__(self):
        self.model = None
        self.tokenizer = None
    
    def initialize(self, config):
        model_path = config.get('model_path')
        self.tokenizer = AutoTokenizer.from_pretrained(model_path)
        self.model = AutoModelForSeq2SeqLM.from_pretrained(model_path)
        return True
    
    def translate_text(self, text, src_lang, tgt_lang, options=None):
        inputs = self.tokenizer(text, return_tensors="pt")
        outputs = self.model.generate(**inputs)
        translated = self.tokenizer.decode(outputs[0], skip_special_tokens=True)
        return translated
```

#### 4. Restart Application

Your custom plugin will be discovered automatically!

---

## Summary

### Plugin Discovery
- ✅ Plugins auto-discovered from `plugins/` folder
- ✅ Drop plugin folder → Restart → Works!

### Model Discovery (NEW!)
- ✅ Models auto-discovered from models folders
- ✅ Scan → Register → Generate Plugin → Works!

### Workflow
1. **Download** model from HuggingFace
2. **Place** in models folder
3. **Scan** for models in UI
4. **Register** with language pair
5. **Generate** plugin automatically
6. **Restart** and use!

### Next Steps
- Try adding a custom model
- Experiment with different model types
- Share your custom plugins
- Contribute to the community!

---

**Happy plugin development! 🚀**
