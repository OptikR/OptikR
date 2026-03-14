# OptikR - Real-Time Screen Translation System

<div align="center">

**Translate anything on your screen in real-time**

Version preview-1.0.0 


</div>

---

## Project Motivation

This is a **proof of concept** and a **one-person community project**.

**Built by someone with minimal coding experience** — I can understand code but can't write it from scratch. This project proves that with the right tools, determination, and community support, anyone can create something meaningful.

**Why I Built This:**
- Make translation accessible to everyone
- No paywalls, no subscriptions, no limits
- Community-driven development
- Learn by doing (and sharing what I learned)
- Give back to the community that helped me

**What This Means:**
- This is a proof of concept — expect rough edges
- Bugs exist but will be fixed
- Extensive documentation to help you understand and improve it
- Community contributions are welcome and encouraged
- It works, and it works well for what it does

---

## What is OptikR?

### A Modular Framework

OptikR is not just a screen translator — it's a **modular framework built on extensibility and plugins**. This is a proof of concept demonstrating what's possible when you combine:

- **Stage-Based Pipeline Architecture** — Every processing stage (Capture, OCR, Translation, Overlay) is plugin-based
- **Universal Plugin System** — Everything can be enhanced, replaced, or extended
- **Built-In Plugin Generator** — CLI tool creates correctly structured plugins for any type
- **Zero Limits Philosophy** — The only limit is your hardware, not the software

### Built for Everyone

**Accessibility First:**
- **Custom UI Languages** — Import your own language translations via Sidebar > Language Packs
- **Highly Customizable** — Every setting is user-configurable
- **No Artificial Limits** — You control everything
- **Community-Driven** — Share plugins, dictionaries, and translations

### Everything is a Plugin

**You Can Add:**
- New OCR engines (Mokuro, Windows OCR, custom models)
- New capture methods (DirectX, Screenshot, custom implementations)
- New translation engines (local AI, cloud APIs, custom models)
- New optimizer plugins (frame skip, caching, preprocessing)
- New text processors (spell check, regex filters)

**Plugin Generator Helps You:**

```bash
python run.py --create-plugin
```

Interactive CLI that generates the correct folder structure, `plugin.json`, entry script with template code, and a README for any plugin type. See [Plugins and Engines](docs/PLUGINS_AND_ENGINES.md) for full details.

### Real-Time Translation

OptikR provides a powerful real-time screen translation and OCR system. Whether you're reading manga, playing games, watching videos, or browsing the web, OptikR provides seamless translation with minimal performance impact.

### Key Features

- **Real-Time Translation** — High FPS with low latency
- **Multiple AI Engines** — EasyOCR, PaddleOCR, Tesseract, Mokuro, Surya, and more
- **Offline Capable** — Works without internet using local AI models (MarianMT, NLLB-200)
- **GPU Accelerated** — 3-6x faster with NVIDIA CUDA support
- **Smart Dictionary** — Personal translation database that learns over time
- **Context-Aware** — Presets for manga, games, videos, formal text, and more
- **100+ Languages** — Supports all major language pairs
- **50+ Plugins** — Highly extensible with optimizers, processors, and engines

---

## Screenshots

### Main Interface

---

## Quick Start

### Prerequisites

1. **Python 3.10+** — Download from https://www.python.org/downloads/
   - During installation, check **"Add Python to PATH"**
2. **CUDA Toolkit (optional, recommended for NVIDIA GPUs)** — Download from https://developer.nvidia.com/cuda-downloads
   - Install CUDA 12.x, then **restart your computer**
   - See [How To Run — CUDA section](docs/HOW_TO_RUN.md#cuda-toolkit--what-it-is-and-why-you-should-install-it) for details
3. **Visual C++ Redistributable (Windows)** — Download from https://aka.ms/vs/17/release/vc_redist.x64.exe

### Install and Run

```bash
cd OptikR
python run.py
```

That's it. On first launch, OptikR automatically:
1. Installs all dependencies from `requirements.txt`
2. Detects your GPU and installs the correct PyTorch build (CUDA or CPU)
3. Restarts itself once setup is complete

No manual `pip install` is required under normal conditions. If auto-install fails (network issues, permissions), see [How To Run](docs/HOW_TO_RUN.md) for manual installation steps.

### First Launch Setup

1. **Consent Dialog** — Accept the terms on first run
2. **Setup Wizard** — Guides you through initial configuration:
   - Select source and target languages
   - Choose OCR engine (EasyOCR recommended)
   - Choose translation engine (MarianMT for offline)
   - Download required AI models
3. **Start Translating**
   - Click "Select Region" to choose the area to translate
   - Click "Start" to begin real-time translation
   - Translations appear as overlays on your screen

### Troubleshooting Installation

| Problem | Solution |
|---------|----------|
| "Python not found" | Reinstall Python with "Add to PATH" checked |
| "CUDA not found" (NVIDIA GPU) | Restart computer after CUDA install |
| "DLL load failed" | Install Visual C++ Redistributable, restart |
| `pip install` fails | Run `python -m pip install --upgrade pip`, retry |

---

## Smart Dictionary

The Smart Dictionary is one of OptikR's most powerful features — a personal translation database that learns, grows, and can be shared.

### How It Works

```
First Time:
  OCR detects "Hello" → AI translates to "Hallo" → Dictionary saves it

Next Time:
  OCR detects "Hello" → Dictionary: "Hallo" (instant, no AI needed)
```

### Key Capabilities

- **Instant Lookup** — Skips AI translation entirely for known text
- **Per Language Pair** — Separate dictionary files (e.g., `en_de.json.gz`, `ja_en.json.gz`)
- **Full Control** — Browse, edit, delete entries in the Dictionary Editor
- **Import/Export** — Share dictionaries with the community (JSON format)
- **Word Extraction** — Optionally breaks sentences into individual words on stop
- **Statistics** — Track entries, lookups, hit rate, and most-used translations
- **Cleaning Tools** — Remove OCR errors and low-confidence entries

### Real Performance Impact

| Scenario | Without Dictionary | With Dictionary (after learning) |
|----------|-------------------|----------------------------------|
| Manga reading | AI processing every frame | 60-80% hit rate, instant lookups |
| Game UI | AI processing every frame | 70-90% hit rate (UI is repetitive) |
| Video subtitles | AI processing every frame | 50-70% hit rate |

### Community Sharing

Export your dictionary from the Smart Dictionary tab and share the JSON file. Others can import it to get instant access to thousands of pre-translated terms. Great for manga communities, game localization groups, and language learners.

---

## Settings Overview

### General
- Interface language (English, German, French, Italian, Japanese)
- Source and target languages
- Runtime mode (Auto, GPU, CPU)
- Startup options

### Capture
- Capture method (DirectX, Screenshot, Auto-detect)
- Frame rate (5–120 FPS)
- Capture quality (Low, Medium, High, Ultra)
- Multi-monitor and multi-region support
- Adaptive capture, fallback mode, small text enhancement

### OCR
- Engine selection (EasyOCR, PaddleOCR, Tesseract, Mokuro, and more)
- Language packs
- Confidence threshold
- Intelligent preprocessing (two-pass OCR)

### Translation
- Local engines: MarianMT, NLLB-200, Qwen3
- Cloud engines: Google Translate, DeepL, Azure, LibreTranslate
- Quality settings, fallback translation, batch processing

### Overlay
- Font family and size
- Text/background/border colors
- Transparency and positioning strategy (Simple, Smart, Flow-Based)
- Animation (Fade, Slide, Scale, None)
- Seamless background mode (auto-matches overlay to original background)

### Pipeline Management
- Pipeline status and statistics
- Active plugin toggles
- Context presets (Manga, Game UI, Subtitles, Novel, Technical, Wikipedia)
- Sequential vs Async pipeline mode
- Plugin-by-stage browser

### Storage
- Translation cache management
- Learning dictionary management
- Export options (translations, screenshots, logs)

### Advanced
- Log level and output
- Thread pool size and process priority
- Developer/debug options

---

## Context Plugin

The Context Plugin adapts OCR, text validation, and translation behavior based on your content type. Provides 10-30% accuracy improvement.

### Available Presets

| Preset | OCR Behavior | Translation Style |
|--------|-------------|-------------------|
| Wikipedia/Formal | High confidence, proper caps | Formal, precise |
| Manga/Comics | ALL CAPS aware, speech bubbles | Casual, emotion-preserving |
| Game UI | Short phrases, buttons | Concise, action-oriented |
| Subtitles/Video | Line break aware | Natural speech |
| Novel/Book | Paragraph-aware | Literary, descriptive |
| Technical Doc | Code/term aware | Precise, technical |

Custom tags can further refine context: `action`, `comedy`, `sci-fi`, `dialogue-heavy`, `technical`.

---

## Pipeline Architecture

### Sequential Pipeline (Default)

Each stage completes before the next starts. Simple, stable, low memory.

```
Frame 1: CAPTURE → OCR → TRANSLATE → POSITION → OVERLAY
Then Frame 2 starts...
```

**Best for:** Most users, lower-end systems, debugging.

### Async Pipeline (Advanced)

Stages run in parallel on different frames simultaneously. Higher throughput.

```
Time 0ms:   Frame 1: CAPTURE
Time 8ms:   Frame 1: OCR        | Frame 2: CAPTURE
Time 16ms:  Frame 1: OCR        | Frame 2: OCR       | Frame 3: CAPTURE
Time 58ms:  Frame 1: TRANSLATE  | Frame 2: OCR       | Frame 3: OCR
Time 88ms:  Frame 1: OVERLAY ✓  | Frame 2: TRANSLATE | Frame 3: OCR
```

**Best for:** Quad-core+ CPUs, 8 GB+ RAM, users who need 30+ FPS.

### Comparison

| Metric | Sequential | Async |
|--------|-----------|-------|
| Throughput | ~10 FPS | ~50 FPS |
| CPU Usage | Medium | High |
| Memory | ~2 GB | ~3-4 GB |
| Stability | Very High | High |
| Recommended | Most users | Power users |

Switch in Pipeline Management > Overview > "Async Pipeline" toggle.

---

## Performance Optimization

### Essential Plugins (Always Active)

| Plugin | Benefit |
|--------|---------|
| Frame Skip | 50-70% CPU reduction — skips unchanged frames |
| Translation Cache | Instant lookup for repeated text |
| Smart Dictionary | Learns translations permanently |
| Text Validator | Filters garbage text, 30-50% noise reduction |
| Text Block Merger | Merges fragmented OCR text |

### Optional Plugins

| Plugin | Benefit |
|--------|---------|
| Async Pipeline | 50-80% throughput boost |
| Batch Processing | 30-50% faster processing |
| Parallel OCR/Capture | 2-3x faster for multi-region |
| Priority Queue | Better interactive responsiveness |
| Work-Stealing Pool | Load balancing across threads |
| Motion Tracker | Skips OCR during scrolling |
| Spell Corrector | Fixes OCR errors |

### Performance Metrics

| Configuration | Frame Time | FPS | CPU Usage |
|--------------|-----------|-----|-----------|
| No optimizations | ~94ms | ~10 | High |
| Essential plugins | ~30-40ms | ~25-33 | Medium |
| All optimizations | ~10-20ms | ~50-100 | Low |

---

## Application Structure

```
OptikR/
├── run.py                     # Entry point
├── bootstrap.py               # Auto-setup (dependencies, PyTorch, config)
├── requirements.txt           # Core dependencies
├── requirements-cpu.txt       # PyTorch CPU variant
├── requirements-gpu.txt       # PyTorch CUDA variant
├── app/                       # Application logic
│   ├── core/                  # Config, main window, model catalog
│   ├── ocr/                   # OCR plugin management
│   ├── text_translation/      # Translation layer
│   ├── workflow/              # Pipeline, plugin manager, plugin generator
│   ├── benchmark/             # Benchmark runner
│   ├── localization/          # UI translations (en, de, fr, it, ja)
│   ├── styles/                # QSS stylesheets (dark/light)
│   └── utils/                 # Path utils, PyTorch manager, CUDA utils
├── ui/                        # User interface (PyQt6)
│   ├── settings/              # Settings tabs
│   ├── dialogs/               # Dialogs (first-run wizard, benchmark, help)
│   ├── overlays/              # Translation overlay rendering
│   └── layout/                # Sidebar, toolbar
├── plugins/                   # Plugin system
│   ├── stages/                # Core pipeline stages
│   │   ├── capture/           # Screen capture plugins
│   │   ├── ocr/               # OCR engine plugins
│   │   ├── translation/       # Translation engine plugins
│   │   ├── vision/            # Vision-language model plugins
│   │   └── llm/               # LLM plugins
│   └── enhancers/             # Pipeline enhancers
│       ├── optimizers/        # Performance optimizer plugins
│       ├── text_processors/   # Text processing plugins
│       └── audio_translation/ # Audio translation plugin
├── user_data/                 # User-owned runtime data
│   ├── config/                # user_config.json
│   ├── learned/translations/  # Smart Dictionary files
│   ├── exports/               # Exported translations, screenshots, logs
│   ├── custom_plugins/        # User-installed plugins
│   └── backups/               # Config backups
└── system_data/               # System-managed runtime data
    ├── ai_models/             # Model registry (model files in HF cache)
    ├── cache/                 # Translation/OCR cache
    ├── logs/                  # Application logs
    └── temp/                  # Temporary processing files
```

---

## Configuration

- **Location**: `user_data/config/user_config.json`
- **Automatic backups** on every save
- **Learning Dictionary**: `user_data/learned/translations/<src>_<tgt>.json.gz`
- **Logs**: `system_data/logs/`

---

## System Requirements

### Minimum
- **OS**: Windows 10/11
- **CPU**: Dual-core 2.0 GHz
- **RAM**: 4 GB
- **Storage**: 2 GB free
- **Python**: 3.10+

### Recommended
- **OS**: Windows 10/11
- **CPU**: Quad-core 3.0 GHz
- **RAM**: 8 GB
- **GPU**: NVIDIA GPU with CUDA support
- **Storage**: 5 GB free (for AI models)
- **Python**: 3.10 or 3.11

---

## CLI Commands

```bash
python run.py                         # Normal launch
python run.py --create-plugin         # Interactive plugin generator
python run.py --auto-generate-missing # Scan and generate missing plugins
python run.py --health-check          # System health check
```

---

## Documentation

Full documentation is in the `docs/` folder:

- [How To Run](docs/HOW_TO_RUN.md) — Installation, CUDA setup, manual install steps
- [Plugins and Engines](docs/PLUGINS_AND_ENGINES.md) — Plugin system, creation guide, engine reference
- [Project Structure and Config](docs/PROJECT_STRUCTURE_AND_CONFIG.md) — Folder layout, config API
- [Benchmark Pipeline](docs/benchmarking.md) — Benchmark system overview

---

## License

See LICENSE file for details.

---

<div align="center">

**Thank you for using OptikR!**

*Translate anything, anywhere, anytime.*

</div>
