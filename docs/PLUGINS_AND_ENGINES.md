# Plugins and Engines

OptikR is built on a plugin architecture. Every major processing component — capture, OCR, translation, vision, and optimization — is a plugin that can be replaced, extended, or created from scratch.

---

## Plugin Directory Layout

All plugins live under the `plugins/` directory, organized by role:

```
plugins/
├── stages/                        # Core pipeline stages
│   ├── capture/                   # Screen capture methods
│   │   ├── bettercam_capture_gpu/ # GPU-accelerated (DirectX)
│   │   └── screenshot_capture_cpu/# CPU fallback (mss/PIL)
│   ├── ocr/                       # Text recognition engines
│   │   ├── easyocr/               # Multi-language, GPU-accelerated
│   │   ├── paddleocr/             # Strong on Asian languages
│   │   ├── tesseract/             # Fast, CPU-based
│   │   ├── mokuro/                # Manga-specialized (Japanese)
│   │   ├── surya_ocr/             # Vision-transformer OCR
│   │   ├── rapidocr/              # Lightweight ONNX Runtime
│   │   ├── doctr/                 # Transformer-based (Mindee)
│   │   ├── windows_ocr/           # Windows built-in OCR
│   │   ├── hybrid_ocr/            # Combines multiple engines
│   │   └── judge_ocr/             # Selects best engine per frame
│   ├── translation/               # Translation engines
│   │   ├── marianmt_gpu/          # MarianMT neural translation
│   │   ├── marianmt_en_es/        # MarianMT English→Spanish
│   │   ├── marianmt_en_fr/        # MarianMT English→French
│   │   ├── marianmt_en_it/        # MarianMT English→Italian
│   │   ├── marianmt_en_ja/        # MarianMT English→Japanese
│   │   ├── nllb200/               # NLLB-200 (200 languages)
│   │   ├── qwen3/                 # Qwen3 LLM translation
│   │   ├── google_free/           # Google Translate (free)
│   │   ├── google_api/            # Google Cloud Translation
│   │   ├── deepl/                 # DeepL API
│   │   ├── azure/                 # Azure Translator
│   │   └── libretranslate/        # LibreTranslate (self-hosted)
│   ├── vision/                    # Vision-language models
│   │   └── qwen3_vl/              # Qwen3-VL (image→text)
│   └── llm/                       # Large language models
│       └── qwen3/                 # Qwen3 general LLM
└── enhancers/                     # Pipeline enhancers
    ├── optimizers/                # Performance optimizers
    │   ├── translation_cache/     # Cache repeated translations
    │   ├── frame_skip/            # Skip unchanged frames
    │   ├── motion_tracker/        # Pause OCR during scrolling
    │   ├── batch_processing/      # Process frames in batches
    │   ├── parallel_ocr/          # Multi-region parallel OCR
    │   ├── parallel_capture/      # Multi-region parallel capture
    │   ├── parallel_translation/  # Parallel translation threads
    │   ├── translation_chain/     # Chain multiple engines
    │   ├── text_block_merger/     # Merge fragmented text
    │   ├── ocr_per_region/        # Per-region engine assignment
    │   ├── priority_queue/        # Task prioritization
    │   ├── work_stealing/         # Load balancing
    │   ├── intelligent_text_processor/ # Context-aware processing
    │   ├── color_contrast/        # Image contrast enhancement
    │   ├── context_manager/       # Content-type presets
    │   └── learning_dictionary/   # Learns translations over time
    ├── text_processors/           # Post-OCR text processing
    │   ├── text_validator/        # Filter garbage text
    │   ├── spell_corrector/       # Fix OCR spelling errors
    │   └── regex/                 # Regex-based text filtering
    └── audio_translation/         # Audio translation (standalone)
```

---

## How a Plugin Works

Every plugin is a folder containing at minimum:

1. **`plugin.json`** — Metadata, settings, dependencies, and type declaration
2. **A Python entry script** — The actual implementation

The entry script name depends on the plugin type:

| Plugin Type | Entry Script | Location |
|---|---|---|
| Capture | `worker.py` | `plugins/stages/capture/<name>/` |
| OCR | `__init__.py` | `plugins/stages/ocr/<name>/` |
| Translation | `worker.py` | `plugins/stages/translation/<name>/` |
| Optimizer | `optimizer.py` | `plugins/enhancers/optimizers/<name>/` |
| Text Processor | `processor.py` | `plugins/enhancers/text_processors/<name>/` |

### plugin.json Example (OCR)

```json
{
  "name": "easyocr",
  "display_name": "EasyOCR",
  "version": "pre-realese-1.0.0",
  "author": "OptikR Team",
  "description": "Multi-language OCR using EasyOCR — GPU accelerated with CPU fallback",
  "type": "ocr",
  "engine_type": "easyocr",
  "entry_point": "__init__.py",
  "worker_script": "worker.py",
  "enabled_by_default": true,
  "settings": {
    "language": {
      "type": "string",
      "default": "en",
      "options": ["en", "ja", "ko", "zh_sim", "de", "fr", "es", "ru"]
    },
    "gpu": {
      "type": "bool",
      "default": true
    },
    "min_confidence": {
      "type": "float",
      "default": 0.5,
      "min": 0.0,
      "max": 1.0
    }
  },
  "dependencies": ["easyocr", "opencv-python", "numpy"],
  "supported_languages": ["en", "ja", "ko", "zh", "de", "fr", "es", "ru"]
}
```

### plugin.json Example (Optimizer)

```json
{
  "name": "translation_cache",
  "display_name": "Translation Cache Optimizer",
  "type": "optimizer",
  "target_stage": "translation",
  "stage": "pre",
  "description": "Caches translations for instant lookup of repeated text.",
  "enabled": true,
  "essential": true,
  "settings": {
    "max_cache_size": { "type": "int", "default": 10000 },
    "ttl_seconds": { "type": "int", "default": 3600 },
    "enable_fuzzy_match": { "type": "bool", "default": false }
  }
}
```

---

## Plugin Discovery and Loading

Plugin management is handled by `app/workflow/plugin_manager.py`:

1. Scans all directories under `plugins/` for `plugin.json` files
2. Parses metadata into `PluginMetadata` objects
3. Infers missing `type` field from the folder path when needed (e.g., a plugin under `plugins/enhancers/optimizers/` is inferred as `optimizer`)
4. Resolves the worker script with type-aware fallbacks
5. Registers valid plugins into the unified plugin manager

Plugins with validation errors or missing worker scripts are silently skipped. Disabled plugins log a note but do not block startup.

---

## Creating Plugins

### Option 1: Built-In Plugin Generator (CLI)

OptikR includes a built-in plugin generator that creates the correct folder structure, `plugin.json`, entry script with template code, and a README for any plugin type.

**Interactive mode:**

```bash
python run.py --create-plugin
```

This launches a CLI wizard that asks for:
- Plugin type (Capture, OCR, Translation, Optimizer, Text Processor)
- Plugin name (used as the folder name)
- Display name
- Description

The generator creates all files in the correct location automatically.

**Programmatic mode (from Python):**

```python
from app.workflow.universal_plugin_generator import PluginGenerator

generator = PluginGenerator(output_dir="plugins")
generator.create_plugin_programmatically(
    plugin_type='translation',
    name='my_custom_engine',
    display_name='My Custom Engine',
    description='Translates using my custom model',
    dependencies=['transformers', 'torch'],
    settings={
        "model_name": {
            "type": "string",
            "default": "my-org/my-model",
            "description": "HuggingFace model name"
        }
    }
)
```

The generator maps plugin types to the correct subdirectory:

| `plugin_type` argument | Created under |
|---|---|
| `capture` | `plugins/stages/capture/` |
| `ocr` | `plugins/stages/ocr/` |
| `translation` | `plugins/stages/translation/` |
| `optimizers` | `plugins/enhancers/optimizers/` |
| `text_processors` | `plugins/enhancers/text_processors/` |

### Option 2: Automatic Plugin Registration (Model Catalog)

When you download a translation model through the UI (First-Run Wizard or Model Manager), OptikR's `ModelCatalog` automatically generates a translation plugin for it using the same `PluginGenerator`.

For example, downloading a MarianMT English→Spanish model will:
1. Download the model weights via HuggingFace Hub
2. Call `PluginGenerator.create_plugin_programmatically()` with the correct model name, language pair, and dependencies
3. Create `plugins/stages/translation/marianmt_en_es/` with a ready-to-use `plugin.json` and `worker.py`

For OCR models, the catalog enables the corresponding pre-built plugin (EasyOCR, Tesseract, PaddleOCR, Mokuro) rather than generating a new one, since OCR plugins require engine-specific integration.

### Option 3: Manual Creation

Create a plugin by hand:

1. Create a folder under the correct path (e.g., `plugins/stages/translation/my_engine/`)
2. Create `plugin.json` with required fields (see examples above)
3. Create the entry script (`worker.py` for translation, `__init__.py` for OCR, `optimizer.py` for optimizers, `processor.py` for text processors)
4. Implement the required interface
5. Restart OptikR

---

## Plugin Interfaces

### OCR Engine

An OCR plugin's entry module must expose an `OCREngine` class:

```python
class OCREngine:
    def initialize(self, config: dict) -> bool:
        """Load the model. Return True on success."""
        ...

    def process_frame(self, frame: np.ndarray, languages: list[str] = None) -> list[dict]:
        """
        Run OCR on a frame.
        Return a list of dicts, each with:
          - 'text': detected text string
          - 'confidence': float 0.0–1.0
          - 'bbox': [x, y, width, height]
        """
        ...

    def is_available(self) -> bool:
        """Return True if the engine is ready."""
        ...
```

### Translation Engine

A translation plugin's `worker.py` must expose a `TranslationEngine` class:

```python
class TranslationEngine:
    def initialize(self, config: dict) -> bool:
        """Load the model. Return True on success."""
        ...

    def translate_text(self, text: str, src_lang: str, tgt_lang: str,
                       options: dict | None = None) -> str:
        """Translate text from src_lang to tgt_lang."""
        ...

    def is_available(self) -> bool:
        """Return True if the engine is ready."""
        ...
```

### Optimizer

An optimizer's `optimizer.py` must expose:

```python
def initialize(config: dict | None = None) -> bool:
    """Initialize the optimizer. Return True on success."""
    ...
```

And typically a class with a `process(data: dict) -> dict` method.

### Text Processor

A text processor's `processor.py` must expose:

```python
def initialize(config: dict | None = None) -> bool:
    """Initialize the processor. Return True on success."""
    ...
```

And typically a class with `process(text: str) -> str` and `process_batch(texts: list[str]) -> list[str]` methods.

---

## Available OCR Engines

| Engine | Best For | GPU? | Languages |
|--------|----------|------|-----------|
| EasyOCR | General text, multi-language | Yes | 80+ |
| PaddleOCR | Asian languages (CJK) | Yes | 80+ |
| Tesseract | Clean text, documents | No (CPU) | 100+ |
| Mokuro | Japanese manga | Yes | Japanese only |
| Surya OCR | Vision-transformer OCR | Yes | 90+ |
| RapidOCR | Lightweight ONNX alternative | No (CPU) | Limited |
| DocTR | Transformer-based (Mindee) | Yes | Limited |
| Windows OCR | Windows built-in | No (DirectML) | OS languages |
| Hybrid OCR | Combines multiple engines | Varies | Varies |
| Judge OCR | Auto-selects best engine | Varies | Varies |

## Available Translation Engines

| Engine | Type | Offline? | Languages |
|--------|------|----------|-----------|
| MarianMT | Neural (HuggingFace) | Yes | 100+ pairs |
| NLLB-200 | Neural (Meta) | Yes | 200 |
| Qwen3 | LLM-based | Yes | Many |
| Google Free | Cloud API | No | 100+ |
| Google API | Cloud API (key required) | No | 100+ |
| DeepL | Cloud API (key required) | No | 30+ |
| Azure | Cloud API (key required) | No | 100+ |
| LibreTranslate | Self-hosted | Optional | 30+ |
