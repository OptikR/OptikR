# System Architecture - Complete Reference

**Version:** 0.1  
**Status:** ✅ Production Architecture

---

## 📋 Table of Contents

- [Introduction](#introduction)
- [Part 1: Pipeline Architecture](#part-1-pipeline-architecture)
- [Part 2: Plugin System Architecture](#part-2-plugin-system-architecture)
- [Part 3: Process & Threading Model](#part-3-process--threading-model)
- [Part 4: Component Architecture](#part-4-component-architecture)
- [Part 5: System Design Patterns](#part-5-system-design-patterns)
- [Part 6: Configuration Architecture](#part-6-configuration-architecture)
- [Part 7: Performance Architecture](#part-7-performance-architecture)
- [Part 8: Deployment Architecture](#part-8-deployment-architecture)
- [Part 9: Architecture Decisions](#part-9-architecture-decisions)
- [Part 10: Pipeline Flowcharts](#part-10-pipeline-flowcharts)

---

## Introduction

This document provides comprehensive technical documentation of the OptikR system architecture. It covers all major architectural decisions, design patterns, component interactions, and implementation details.

**Target Audience:** Software architects, senior developers, system designers  
**Prerequisites:** Strong understanding of Python, Qt, multiprocessing, and real-time systems  
**Related Docs:**
- Features: `docs/features/FEATURES_COMPLETE.md`
- Current Status: `docs/current/CURRENT_COMPLETE.md`

### Architecture Overview

OptikR is built on a **modular, plugin-based architecture** with several key architectural principles:

1. **Two-Pipeline System** - Separation of initialization (Startup) and processing (Runtime)
2. **Four Plugin Systems** - Extensible architecture for OCR, Capture, Optimizers, and Text Processors
3. **Process Isolation** - Critical components run in separate processes for stability
4. **Real-Time Performance** - Optimized for 10 FPS target with sub-100ms latency
5. **Offline-First Design** - All processing can happen locally without internet

**Key Design Principles:**
- **Modularity** - Components are loosely coupled and independently replaceable
- **Extensibility** - Plugin system allows adding new functionality without core changes
- **Stability** - Process isolation prevents crashes from affecting the entire system
- **Performance** - Optimized for real-time processing with minimal latency
- **Privacy** - Offline-first design ensures user data stays local

---

## Part 1: Pipeline Architecture

### 1.1 Overview

**Status:** ✅ IMPLEMENTED

OptikR uses a modular pipeline architecture for real-time screen translation. The system consists of two main pipeline types and a plugin system for performance optimization.

#### Pipeline Types

**1. StartupPipeline (Initialization)**
- Runs once at application startup
- Loads AI models (OCR, Translation)
- Initializes components
- Creates RuntimePipeline
- Warm up for faster first translation
- Duration: 20-30 seconds

**2. RuntimePipeline (Continuous Processing)**
- Runs continuously during translation
- Captures screen regions
- Extracts text via OCR
- Translates text
- Displays overlay
- Target: 10 FPS (100ms per frame)

#### Architecture Diagram

```
┌─────────────────────────────────────────────────────────┐
│                   APPLICATION STARTUP                    │
└─────────────────────────────────────────────────────────┘
                          │
                          ▼
┌─────────────────────────────────────────────────────────┐
│                   STARTUP PIPELINE                       │
│  (Runs once - 20-30 seconds)                            │
├─────────────────────────────────────────────────────────┤
│ 1. Load Configuration                                   │
│ 2. Initialize OCR Engines (15-20s)                      │
│ 3. Initialize Translation Engines (3-5s)                │
│ 4. Initialize Overlay System                            │
│ 5. Scan and Load Plugins                                │
│ 6. Create RuntimePipeline                               │
│ 7. Warm Up Components                                   │
└─────────────────────────────────────────────────────────┘
                          │
                          ▼
┌─────────────────────────────────────────────────────────┐
│                   RUNTIME PIPELINE                       │
│  (Runs continuously - 10 FPS target)                    │
├─────────────────────────────────────────────────────────┤
│ Loop (every 100ms):                                     │
│   1. CAPTURE STAGE                                      │
│      ├─ Capture screen region                           │
│      └─ Apply capture plugins (frame_skip, motion)      │
│   2. OCR STAGE                                          │
│      ├─ Extract text from image                         │
│      └─ Apply OCR plugins (validator, merger)           │
│   3. TRANSLATION STAGE                                  │
│      ├─ Translate text                                  │
│      └─ Apply translation plugins (cache, dictionary)   │
│   4. OVERLAY STAGE                                      │
│      ├─ Position overlay                                │
│      └─ Display translation                             │
│   5. PERFORMANCE MONITORING                             │
│      └─ Track FPS, latency, cache hits                  │
└─────────────────────────────────────────────────────────┘
```


---

### 1.2 StartupPipeline (Initialization)

**Purpose:** Initialize all components at application startup

**Location:** `src/workflow/startup_pipeline.py`

**Responsibilities:**
1. Load OCR engines (EasyOCR, Tesseract, PaddleOCR, Manga OCR)
2. Load translation engines (MarianMT, Dictionary)
3. Initialize overlay system (PyQt6)
4. Scan and load plugins
5. Create RuntimePipeline for continuous translation
6. Warm up components for faster first translation

**Lifecycle:**
```python
# Application Startup
app = QApplication(sys.argv)

# Create StartupPipeline
startup_pipeline = StartupPipeline(config_manager)

# Initialize components (20-30 seconds)
success = startup_pipeline.initialize_components()

# Warm up for faster first translation
startup_pipeline.warm_up_components()

# Create RuntimePipeline (ready for use)
runtime_pipeline = startup_pipeline.create_runtime_pipeline()

# Show main window
main_window.show()
```

**Timing Breakdown:**
- Configuration loading: <1s
- OCR engine loading: 15-20s (largest component)
  - EasyOCR: 10-15s
  - Tesseract: 2-3s
  - PaddleOCR: 2-3s
  - Manga OCR: 1-2s
- Translation engine loading: 3-5s
  - MarianMT: 2-4s
  - Dictionary: <1s
- Plugin scanning: 1-2s
- Pipeline creation: 1-2s
- Warm up: 1-2s
- **Total: 20-30 seconds**

**Optimization Strategies:**
- Lazy loading: Load models only when needed
- Parallel loading: Load multiple models simultaneously
- Model caching: Keep models in memory
- Warmstart: Pre-load models during startup

**Code Example:**
```python
class StartupPipeline:
    def __init__(self, config_manager):
        self.config_manager = config_manager
        self.ocr_layer = None
        self.translation_layer = None
        self.overlay_manager = None
        self.plugin_manager = None
        self.runtime_pipeline = None
    
    def initialize_components(self):
        """Initialize all components."""
        try:
            # 1. Initialize OCR Layer (15-20s)
            self.ocr_layer = OCRLayer(self.config_manager)
            self.ocr_layer.initialize()
            
            # 2. Initialize Translation Layer (3-5s)
            self.translation_layer = TranslationLayer(self.config_manager)
            self.translation_layer.initialize()
            
            # 3. Initialize Overlay Manager (<1s)
            self.overlay_manager = OverlayManager(self.config_manager)
            
            # 4. Initialize Plugin Manager (1-2s)
            self.plugin_manager = PluginManager()
            self.plugin_manager.scan_plugins()
            
            return True
        except Exception as e:
            logger.error(f"Initialization failed: {e}")
            return False
    
    def warm_up_components(self):
        """Warm up components for faster first translation."""
        # Warm up OCR
        dummy_image = np.zeros((100, 100, 3), dtype=np.uint8)
        self.ocr_layer.recognize(dummy_image)
        
        # Warm up Translation
        dummy_text = "Hello"
        self.translation_layer.translate(dummy_text)
    
    def create_runtime_pipeline(self):
        """Create RuntimePipeline for continuous processing."""
        self.runtime_pipeline = RuntimePipeline(
            config_manager=self.config_manager,
            ocr_layer=self.ocr_layer,
            translation_layer=self.translation_layer,
            overlay_manager=self.overlay_manager,
            plugin_manager=self.plugin_manager
        )
        return self.runtime_pipeline
```

---

### 1.3 RuntimePipeline (Continuous Processing)

**Purpose:** Process frames continuously during translation

**Location:** `src/workflow/runtime_pipeline_optimized.py`

**Responsibilities:**
1. Capture screen regions (10 FPS target)
2. Extract text via OCR
3. Translate text
4. Display overlay
5. Apply optimizer plugins
6. Manage performance

**Lifecycle:**
```python
# User clicks "Start Translation"
runtime_pipeline.start()

# Continuous loop (10 FPS)
while running:
    # 1. Capture Stage (1-5ms)
    frame = capture_subprocess.get_frame()
    
    # Apply capture plugins
    frame = apply_capture_plugins(frame)  # frame_skip, motion_tracker
    
    if frame is None:  # Frame skipped
        continue
    
    # 2. OCR Stage (50-200ms)
    text_blocks = ocr_layer.recognize(frame)
    
    # Apply OCR plugins
    text_blocks = apply_ocr_plugins(text_blocks)  # text_validator, text_block_merger
    
    # 3. Translation Stage (1-100ms)
    for block in text_blocks:
        # Apply translation plugins
        translation = apply_translation_plugins(block)  # cache, dictionary, chain
        
        if not translation:
            # Call translation engine
            translation = translation_layer.translate(block.text)
    
    # 4. Overlay Stage (5-10ms)
    overlay_manager.update(translations)
    
    # 5. Performance Monitoring
    track_performance_metrics()
    
    # Sleep to maintain target FPS
    sleep_until_next_frame()

# User clicks "Stop Translation"
runtime_pipeline.stop()
```

**Performance Target:**
- Target FPS: 10
- Frame time budget: 100ms
- Breakdown:
  - Capture: 1-5ms (5%)
  - OCR: 50-200ms (50-200%)
  - Translation: 1-100ms (1-100%)
  - Overlay: 5-10ms (5-10%)
  - Overhead: 5-10ms (5-10%)

**Actual Performance:**
- Without optimizations: 1-3 FPS
- With essential plugins: 7-10 FPS
- With all optimizations: 10-15 FPS

**Code Example:**
```python
class RuntimePipeline:
    def __init__(self, config_manager, ocr_layer, translation_layer, overlay_manager, plugin_manager):
        self.config_manager = config_manager
        self.ocr_layer = ocr_layer
        self.translation_layer = translation_layer
        self.overlay_manager = overlay_manager
        self.plugin_manager = plugin_manager
        
        self.running = False
        self.capture_subprocess = None
        self.plugins = {}
    
    def start(self):
        """Start continuous translation."""
        self.running = True
        
        # Start capture subprocess
        self.capture_subprocess = CaptureSubprocess(worker_script='plugins/capture/dxcam_capture/worker.py')
        self.capture_subprocess.start(self.config_manager.get_capture_config())
        
        # Load optimizer plugins
        self.plugins = self.plugin_manager.load_optimizer_plugins()
        
        # Start processing loop
        self.process_loop()
    
    def process_loop(self):
        """Main processing loop."""
        while self.running:
            start_time = time.time()
            
            # 1. Capture Stage
            frame = self.capture_subprocess.get_frame()
            
            # Apply capture plugins
            frame = self.apply_capture_plugins(frame)
            
            if frame is None:
                continue
            
            # 2. OCR Stage
            text_blocks = self.ocr_layer.recognize(frame)
            
            # Apply OCR plugins
            text_blocks = self.apply_ocr_plugins(text_blocks)
            
            # 3. Translation Stage
            translations = []
            for block in text_blocks:
                translation = self.translate_with_plugins(block)
                translations.append(translation)
            
            # 4. Overlay Stage
            self.overlay_manager.update(translations)
            
            # 5. Performance Monitoring
            elapsed = time.time() - start_time
            self.track_performance(elapsed)
            
            # Sleep to maintain target FPS
            target_frame_time = 1.0 / 10  # 10 FPS
            sleep_time = max(0, target_frame_time - elapsed)
            time.sleep(sleep_time)
    
    def stop(self):
        """Stop continuous translation."""
        self.running = False
        self.capture_subprocess.stop()
        self.overlay_manager.hide()
```

---

### 1.4 Pipeline Flow Diagram

**Complete Pipeline Flow:**

```
┌─────────────────────────────────────────────────────────┐
│                    USER INTERACTION                      │
└─────────────────────────────────────────────────────────┘
                          │
                          ▼
                  [Start Translation]
                          │
                          ▼
┌─────────────────────────────────────────────────────────┐
│                   CAPTURE STAGE                          │
├─────────────────────────────────────────────────────────┤
│ 1. Capture Subprocess (DXCam/Screenshot)                │
│    └─ Capture screen region (1-5ms)                     │
│                                                          │
│ 2. Frame Skip Plugin (Essential)                        │
│    ├─ Compare with previous frame                       │
│    ├─ If similar (>95%) → SKIP                         │
│    └─ If different → CONTINUE                           │
│                                                          │
│ 3. Motion Tracker Plugin (Optional)                     │
│    ├─ Detect motion in region                           │
│    ├─ If rapid motion → SKIP                           │
│    └─ If static → CONTINUE                              │
└─────────────────────────────────────────────────────────┘
                          │
                          ▼
┌─────────────────────────────────────────────────────────┐
│                     OCR STAGE                            │
├─────────────────────────────────────────────────────────┤
│ 1. OCR Engine (EasyOCR/Tesseract/PaddleOCR/Manga OCR)  │
│    └─ Extract text from image (50-200ms)                │
│                                                          │
│ 2. Text Validator Plugin (Essential)                    │
│    ├─ Check confidence score                            │
│    ├─ Filter garbage text                               │
│    └─ Validate character patterns                       │
│                                                          │
│ 3. Text Block Merger Plugin (Essential)                 │
│    ├─ Analyze text block positions                      │
│    ├─ Merge nearby blocks                               │
│    └─ Create complete sentences                         │
│                                                          │
│ 4. Intelligent OCR Processor                            │
│    ├─ Text orientation detection                        │
│    ├─ Multi-line handling                               │
│    └─ Quality scoring                                   │
└─────────────────────────────────────────────────────────┘
                          │
                          ▼
┌─────────────────────────────────────────────────────────┐
│                  TRANSLATION STAGE                       │
├─────────────────────────────────────────────────────────┤
│ 1. Translation Cache Plugin (Essential)                 │
│    ├─ Check in-memory cache                             │
│    ├─ If found → RETURN (100x faster)                  │
│    └─ If not found → CONTINUE                           │
│                                                          │
│ 2. Learning Dictionary Plugin (Essential)               │
│    ├─ Check persistent dictionary                       │
│    ├─ If found → RETURN (20x faster)                   │
│    └─ If not found → CONTINUE                           │
│                                                          │
│ 3. User Dictionary                                      │
│    ├─ Check custom translations                         │
│    ├─ If found → RETURN (instant)                      │
│    └─ If not found → CONTINUE                           │
│                                                          │
│ 4. Translation Chain Plugin (Optional)                  │
│    ├─ Check if chaining needed                          │
│    ├─ If yes → Execute multi-hop translation           │
│    └─ If no → CONTINUE                                  │
│                                                          │
│ 5. Translation Engine (MarianMT/Google/LibreTranslate)  │
│    ├─ Execute translation (30-100ms)                    │
│    ├─ Save to cache                                     │
│    └─ Save to learning dictionary                       │
└─────────────────────────────────────────────────────────┘
                          │
                          ▼
┌─────────────────────────────────────────────────────────┐
│                 POST-PROCESSING STAGE                    │
├─────────────────────────────────────────────────────────┤
│ 1. Quality Filter                                       │
│    ├─ Check translation confidence                      │
│    ├─ Validate output quality                           │
│    └─ Filter low-quality results                        │
│                                                          │
│ 2. Smart Grammar Mode (Optional)                        │
│    ├─ Basic grammar validation                          │
│    ├─ Sentence structure check                          │
│    └─ Punctuation validation                            │
│                                                          │
│ 3. Smart Positioning                                    │
│    ├─ Calculate overlay position                        │
│    ├─ Avoid overlapping text                            │
│    └─ Adjust for screen boundaries                      │
└─────────────────────────────────────────────────────────┘
                          │
                          ▼
┌─────────────────────────────────────────────────────────┐
│                   OVERLAY STAGE                          │
├─────────────────────────────────────────────────────────┤
│ 1. Overlay Rendering (PyQt6)                            │
│    ├─ Create transparent overlay window                 │
│    ├─ Render translated text                            │
│    ├─ Apply styling (font, color, background)          │
│    └─ Update at 10 FPS                                  │
└─────────────────────────────────────────────────────────┘
                          │
                          ▼
                  [Display Translation]
                          │
                          ▼
                  [Loop back to Capture]
```

---

### 1.5 Pipeline Configuration

**Configuration Hierarchy:**

```
config/system_config.json
├── pipeline
│   ├── target_fps: 10
│   ├── enable_optimizer_plugins: false
│   └── performance_mode: "balanced"
├── capture
│   ├── method: "dxcam"
│   ├── region: [x, y, width, height]
│   └── fps: 10
├── ocr
│   ├── engine: "easyocr"
│   ├── languages: ["ja", "en"]
│   └── gpu_enabled: true
├── translation
│   ├── engine: "marianmt"
│   ├── source_language: "ja"
│   ├── target_language: "en"
│   └── gpu_enabled: true
└── overlay
    ├── position: "below"
    ├── font_size: 16
    └── opacity: 0.8
```

**Plugin Configuration:**

```
plugins/optimizers/frame_skip/plugin.json
{
  "name": "frame_skip",
  "enabled": true,
  "essential": true,
  "settings": {
    "similarity_threshold": 0.95,
    "min_skip_frames": 3,
    "max_skip_frames": 30
  }
}
```

---

### 1.6 Performance Metrics

**Pipeline Statistics:**

```python
{
  "fps": 8.5,
  "target_fps": 10,
  "frame_time": {
    "capture": 2.5,      # ms
    "ocr": 85.3,         # ms
    "translation": 12.7, # ms
    "overlay": 8.2,      # ms
    "total": 108.7       # ms
  },
  "cache_stats": {
    "translation_cache_hit_rate": 0.853,
    "learning_dictionary_hit_rate": 0.602,
    "frame_skip_rate": 0.672
  },
  "resource_usage": {
    "cpu_percent": 28.5,
    "memory_mb": 756,
    "gpu_memory_mb": 1024
  }
}
```

**Performance Tracking:**

```python
class PerformanceMonitor:
    def __init__(self):
        self.frame_times = []
        self.cache_hits = 0
        self.cache_misses = 0
        self.frames_processed = 0
        self.frames_skipped = 0
    
    def track_frame(self, frame_time, cache_hit, frame_skipped):
        self.frame_times.append(frame_time)
        if cache_hit:
            self.cache_hits += 1
        else:
            self.cache_misses += 1
        if frame_skipped:
            self.frames_skipped += 1
        else:
            self.frames_processed += 1
    
    def get_stats(self):
        return {
            'fps': 1000 / np.mean(self.frame_times),
            'avg_frame_time': np.mean(self.frame_times),
            'cache_hit_rate': self.cache_hits / (self.cache_hits + self.cache_misses),
            'frame_skip_rate': self.frames_skipped / (self.frames_processed + self.frames_skipped)
        }
```



---

## Part 9: Architecture Decisions

### 9.1 user_data/ Folder - Empty in Distribution ✅

**Decision:** Include only empty structure in distribution

**Reasoning:**
1. **First-Run Experience** - User needs to see consent dialog on first run
2. **Clean State** - Config is created by the app after user accepts consent
3. **No Pre-Configuration** - Avoids shipping with developer's personal settings
4. **Privacy** - No user-specific data in distribution

**What Gets Included:**
```
user_data/
├── README.md                    ✅ Keep (explains folder purpose)
├── backups/                     ✅ Empty folder
├── config/                      ✅ Empty folder (no system_config.json!)
├── custom_plugins/              ✅ Empty folder
├── exports/                     ✅ Empty folder
└── learned/                     ✅ Empty folder
```

**What Gets Excluded:**
```
❌ user_data/config/system_config.json    # User-specific config
❌ user_data/.migrated                     # Migration marker
❌ Any other user-specific files
```

**Result:**
- User gets clean first-run experience
- Consent dialog shows properly
- Config is created with proper defaults
- No developer settings leak into distribution

---

### 9.2 ui/ Folder - Keep in Root ✅

**Decision:** Keep ui/ in root instead of moving to app/ui/

**Reasoning:**

**1. Import Compatibility**
Current imports throughout codebase:
```python
from ui.dialogs.consent_dialog import show_consent_dialog
from ui.sidebar.sidebar_widget import SidebarWidget
from ui.settings.general_tab_pyqt6 import GeneralSettingsTab
```

Moving to `app/ui/` would require updating hundreds of import statements.

**2. Separation of Concerns**
```
app/        → Business Logic (models, engines, workflows)
ui/         → Presentation Layer (PyQt6 widgets, dialogs)
plugins/    → Extensibility (plugin system)
```

This is a **clean architectural pattern**:
- `app/` = Core logic, no UI dependencies
- `ui/` = Presentation, depends on app/
- Clear separation makes testing easier

**3. Common Pattern**
Many Python applications use this structure:
```
myapp/
├── core/          # Business logic
├── ui/            # User interface
├── plugins/       # Extensions
└── run.py         # Entry point
```

**4. Refactoring Cost vs Benefit**
- **Cost:** Update ~200+ import statements, test every UI component, risk breaking imports
- **Benefit:** Slightly "cleaner" folder structure
- **Verdict:** Not worth the refactoring cost

**Current Structure (Keep This):**
```
OptikR/
├── run.py
├── app/                    # Core logic
│   ├── capture/
│   ├── ocr/
│   ├── translation/
│   ├── workflow/
│   └── ...
├── ui/                     # Presentation (separate from logic)
│   ├── dialogs/
│   ├── settings/
│   ├── sidebar/
│   └── ...
├── plugins/                # Extensions
└── ...
```

---

### 9.3 Final Distribution Structure

```
OptikR_Distribution/
├── run.py                          ✅ Entry point
├── requirements.txt                ✅ Dependencies
├── LICENSE                         ✅ License
│
├── app/                            ✅ Core logic (~200 files)
│   ├── capture/
│   ├── ocr/
│   ├── translation/
│   ├── workflow/
│   └── ...
│
├── ui/                             ✅ Presentation (~70 files)
│   ├── dialogs/                    [Kept in root for imports]
│   ├── settings/
│   ├── sidebar/
│   └── ...
│
├── plugins/                        ✅ Plugin system (~50 plugins)
│   ├── capture/
│   ├── ocr/
│   ├── optimizers/
│   └── ...
│
├── dictionary/                     ✅ Learned data
│   └── learned_dictionary_en_de.json.gz
│
├── system_data/                    ✅ Runtime data (empty)
│   ├── README.md
│   ├── ai_models/
│   ├── cache/
│   ├── logs/
│   └── temp/
│
├── user_data/                      ✅ User config (EMPTY!)
│   ├── README.md                   [Only README included]
│   ├── backups/                    [Empty]
│   ├── config/                     [Empty - no system_config.json!]
│   ├── custom_plugins/             [Empty]
│   ├── exports/                    [Empty]
│   └── learned/                    [Empty]
│
└── models/                         ✅ AI models (empty)
    └── marianmt/                   [Empty - populated at runtime]
```

**Key Points:**
1. ✅ `user_data/` is empty - config created on first run
2. ✅ `ui/` stays in root - import compatibility
3. ✅ Clean separation: app/ (logic) + ui/ (presentation)
4. ✅ All development scripts excluded
5. ✅ User gets proper first-run experience with consent dialog

**First Run Behavior:**
1. User extracts distribution
2. Runs `python run.py`
3. App detects empty `user_data/config/`
4. Shows consent dialog
5. Creates `system_config.json` with defaults
6. User has clean, proper first-run experience

---

## Part 10: Pipeline Flowcharts

### 10.1 Sequential Pipeline (Default Mode)

```
┌─────────────────────────────────────────────────────────────────────────┐
│                         FRAME 1 PROCESSING                              │
└─────────────────────────────────────────────────────────────────────────┘

    ┌──────────────────────────────────────────────────────────────┐
    │  START: New Frame Captured                                   │
    └────────────────────┬─────────────────────────────────────────┘
                         │
                         ▼
    ┌────────────────────────────────────────────────────────────┐
    │  STAGE 1: CAPTURE (~8ms)                                   │
    │  ┌──────────────────────────────────────────────────────┐  │
    │  │ • DirectX GPU Capture / Screenshot                   │  │
    │  │ • Capture Region: X, Y, Width, Height                │  │
    │  └──────────────────────────────────────────────────────┘  │
    │                                                            │
    │  🔌 PLUGINS:                                               │
    │  ⭐ Frame Skip (50-70% frames skipped)                     │
    │     ├─ Compare with previous frame                         │
    │     ├─ Similarity > 95%? → SKIP entire pipeline ✓          │
    │     └─ Different? → Continue ↓                             │
    │                                                            │
    │  ⚙️  Motion Tracker (optional)                            │
    │     └─ Scrolling detected? → SKIP OCR                      │
    │                                                            │
    │  ⚙️  Parallel Capture (optional, multi-region)            │
    │     └─ Process 4 regions simultaneously                    │
    └────────────────────┬───────────────────────────────────────┘
                         │
                         ▼
    ┌────────────────────────────────────────────────────────────┐
    │  STAGE 2: OCR (~50ms baseline, ~70ms with preprocessing)   │
    │  ┌──────────────────────────────────────────────────────┐  │
    │  │ 2A: IMAGE PREPROCESSING (Optional, +20ms)           │  │
    │  │ ┌────────────────────────────────────────────────┐  │  │
    │  │ │ 🔍 Intelligent Preprocessing (QoL Feature)    │  │  │
    │  │ │ 1. Quick OCR → Find text regions              │  │  │
    │  │ │ 2. Enhance ONLY text areas (2x, sharpen)      │  │  │
    │  │ │ 3. Re-OCR enhanced regions                    │  │  │
    │  │ │ Result: Better accuracy, 80% faster than full │  │  │
    │  │ └────────────────────────────────────────────────┘ │  │
    │  └─────────────────────────────────────────────────────┘  │
    │                                                           │
    │  ┌─────────────────────────────────────────────────────┐  │
    │  │ 2B: OCR EXECUTION                                   │  │
    │  │ • Engine: EasyOCR/Tesseract/PaddleOCR/Manga OCR     │  │
    │  │ • Languages: [en, ja, de, ...]                      │  │
    │  │ • Confidence threshold: 0.5                         │  │
    │  │                                                     │  │
    │  │ Raw Output:                                         │  │
    │  │ ┌─────────────────────────────────────────────────┐ │  │
    │  │ │ Block 1: "STR"      (x:100, y:50)               │ │  │
    │  │ │ Block 2: "ONG HUMAN" (x:100, y:85)              │ │  │
    │  │ │                                                 │ │  │
    │  │ └─────────────────────────────────────────────────┘ │  │
    │  └──────────────────────────────────────────────────────┘  │
    │                                                              │
    │  ┌──────────────────────────────────────────────────────┐  │
    │  │ 2C: TEXT BLOCK MERGING ⭐ ESSENTIAL                 │  │
    │  │ (intelligent_ocr_processor.py)                      │  │
    │  │                                                     │  │
    │  │ Step 1: Horizontal Merge (same line)                │  │
    │  │ ├─ Detect blocks on same Y coordinate               │  │
    │  │ ├─ Check horizontal proximity                       │  │
    │  │ └─ Merge with space (or remove hyphen)              │  │
    │  │                                                     │  │
    │  │ Step 2: Vertical Merge (multi-line text)            │  │
    │  │ ├─ Detect vertically close lines                    │  │
    │  │ ├─ Check horizontal alignment                       │  │
    │  │ └─ Merge lines (handle line-break hyphens)          │  │
    │  │                                                     │  │
    │  │ 🔧 Hyphen Handling:                                 │  │
    │  │ "VUL-" + "GAR HUMAN" → "VULGAR HUMAN" ✓             │  │
    │  │                                                     │  │
    │  │ Merged Output:                                      │  │
    │  │ ┌─────────────────────────────────────────────────┐ │  │
    │  │ │ Block 1: "VULGAR HUMAN INFERIORS"               │ │  │
    │  │ │          (x:100, y:50, merged from 3 blocks)    │ │  │
    │  │ └─────────────────────────────────────────────────┘ │  │
    │  └──────────────────────────────────────────────────────┘  │
    │                                                            │
    │  🔌 PLUGINS:                                              │
    │  ⭐ Text Validator (30-50% noise removed)                 │
    │     ├─ Check min confidence (0.3)                          │
    │     ├─ Check alphanumeric content                          │
    │     ├─ Smart grammar check (optional)                      │
    │     └─ Filter garbage text                                 │
    │                                                            │
    │  ⚙️  Spell Corrector (10-20% accuracy boost)               │
    │     ├─ Fix: | → I, l → I, 0 → O, rn → m                    │
    │     ├─ Fix capitalization                                  │
    │     └─ Dictionary validation                               │
    │                                                            │
    │  ⚙️  Parallel OCR (optional, multi-region)                 │
    │     └─ Process 4 regions simultaneously                    │
    └────────────────────┬───────────────────────────────────────┘
                         │
                         ▼
    ┌────────────────────────────────────────────────────────────┐
    │  STAGE 3: TRANSLATION (~30ms baseline, ~3ms with cache)    │
    │  ┌──────────────────────────────────────────────────────┐  │
    │  │ Input: "VULGAR HUMAN INFERIORS"                      │  │
    │  └──────────────────────────────────────────────────────┘  │
    │                                                              │
    │  🔌 PLUGINS (Check in order):                               │
    │                                                              │
    │  ⭐ Translation Cache (100x speedup)                         │
    │     ├─ Check cache for exact match                          │
    │     ├─ HIT? → Return instantly (0.1ms) ✓                   │
    │     └─ MISS? → Continue ↓                                   │
    │                                                              │
    │  ⭐ Smart Dictionary (20x speedup)                           │
    │     ├─ Check learned translations                           │
    │     ├─ HIT? → Return fast (1ms) ✓                          │
    │     └─ MISS? → Continue ↓                                   │
    │                                                              │
    │  🌐 Translation Engine (30ms)                               │
    │     ├─ Engine: MarianMT/Google/DeepL                        │
    │     ├─ Source: ja → Target: de                              │
    │     ├─ Translate text                                       │
    │     └─ Save to Cache + Dictionary                           │
    │                                                              │
    │  ⚙️  Batch Processing (optional, 30-50% faster)            │
    │     └─ Batch 8 texts into single API call                   │
    │                                                              │
    │  ⚙️  Translation Chain (optional, rare pairs)               │
    │     └─ Multi-hop: JA→EN→DE (2-3x slower, better quality)   │
    │                                                              │
    │  ┌──────────────────────────────────────────────────────┐  │
    │  │ Output: "VULGÄRE MENSCHLICHE UNTERLEGENE"           │  │
    │  └──────────────────────────────────────────────────────┘  │
    └────────────────────┬───────────────────────────────────────┘
                         │
                         ▼
    ┌────────────────────────────────────────────────────────────┐
    │  STAGE 4: POSITIONING (~5ms)                               │
    │  ┌──────────────────────────────────────────────────────┐  │
    │  │ • Strategy: Smart/Above/Below/Fixed/Cursor           │  │
    │  │ • Input: Text bounding box from OCR                  │  │
    │  │ • Calculate preferred position                        │  │
    │  │ • Check collision with existing overlays             │  │
    │  │ • Adjust if needed                                    │  │
    │  │                                                       │  │
    │  │ 🔧 Collision Detection (built-in)                    │  │
    │  │ └─ Avoid overlapping overlays                        │  │
    │  │                                                       │  │
    │  │ Output: Position (x: 150, y: 200)                    │  │
    │  └──────────────────────────────────────────────────────┘  │
    └────────────────────┬───────────────────────────────────────┘
                         │
                         ▼
    ┌────────────────────────────────────────────────────────────┐
    │  STAGE 5: OVERLAY (~1ms, +2-3ms with seamless)            │
    │  ┌──────────────────────────────────────────────────────┐  │
    │  │ 🎨 Seamless Background (QoL Feature, optional)       │  │
    │  │ ├─ Sample background color from OCR region           │  │
    │  │ ├─ Match overlay background (e.g., white for manga)  │  │
    │  │ ├─ Auto-adjust text color for readability            │  │
    │  │ └─ Result: Seamless integration (+2-3ms)             │  │
    │  └──────────────────────────────────────────────────────┘  │
    │                                                            │
    │  ┌──────────────────────────────────────────────────────┐  │
    │  │ • Create PyQt6 overlay window                        │  │
    │  │ • Apply styling (font, colors, borders, rounded)     │  │
    │  │ • Position at calculated coordinates                 │  │
    │  │ • Apply animation (fade-in/slide)                    │  │
    │  │ • Show overlay                                        │  │
    │  │ • Start auto-hide timer                              │  │
    │  │                                                       │  │
    │  │ ┌────────────────────────────────────────────────┐   │  │
    │  │ │  ╔════════════════════════════════════════╗   │   │  │
    │  │ │  ║ VULGÄRE MENSCHLICHE UNTERLEGENE        ║   │   │  │
    │  │ │  ╚════════════════════════════════════════╝   │   │  │
    │  │ └────────────────────────────────────────────────┘   │  │
    │  └──────────────────────────────────────────────────────┘  │
    └────────────────────┬───────────────────────────────────────┘
                         │
                         ▼
    ┌────────────────────────────────────────────────────────────┐
    │  END: Overlay Displayed                                    │
    │  Total Time: ~94ms baseline (10.6 FPS)                     │
    │              ~35ms with cache (28 FPS)                      │
    └────────────────────────────────────────────────────────────┘

    ⏱️  WAIT for next frame...
    
    Then process FRAME 2 (same flow) →
```

---

### 10.2 Async Pipeline (Advanced Mode)

```
┌─────────────────────────────────────────────────────────────────────────┐
│              PARALLEL PROCESSING - MULTIPLE FRAMES                      │
└─────────────────────────────────────────────────────────────────────────┘

    FRAME 1:  [CAPTURE] → [OCR] → [TRANS] → [POS] → [OVERLAY]
                            ↓
    FRAME 2:            [CAPTURE] → [OCR] → [TRANS] → [POS] → [OVERLAY]
                                      ↓
    FRAME 3:                      [CAPTURE] → [OCR] → [TRANS] → [POS] → [OVERLAY]
                                                ↓
    FRAME 4:                                [CAPTURE] → [OCR] → [TRANS] → [POS]

    ⏱️  Timeline:
    ├─────────────────────────────────────────────────────────────────────┤
    0ms    20ms   40ms   60ms   80ms   100ms  120ms  140ms  160ms  180ms

    Frame 1: ████████████████████████████████████████████ (94ms total)
    Frame 2:         ████████████████████████████████████████████ (starts at 20ms)
    Frame 3:                 ████████████████████████████████████████████ (starts at 40ms)
    Frame 4:                         ████████████████████████████████████████████

    🚀 Result: 4 frames processed in ~180ms
              Sequential would take: 4 × 94ms = 376ms
              Speedup: 2.1x faster!
```

---

### 10.3 Performance Comparison

```
┌─────────────────────────────────────────────────────────────────────────┐
│                    SEQUENTIAL vs ASYNC                                  │
└─────────────────────────────────────────────────────────────────────────┘

SEQUENTIAL (Default):
═══════════════════════════════════════════════════════════════════════════
Frame 1: [████████████████████████████████████████████] 94ms
         Wait...
Frame 2:                                                  [████████████████████████████████████████████] 94ms
         Wait...
Frame 3:                                                                                                   [████████████████████████████████████████████] 94ms

Total: 282ms for 3 frames = 10.6 FPS


ASYNC (Advanced):
═══════════════════════════════════════════════════════════════════════════
Frame 1: [████████████████████████████████████████████] 94ms
Frame 2:         [████████████████████████████████████████████] 94ms
Frame 3:                 [████████████████████████████████████████████] 94ms

Total: 154ms for 3 frames = 19.5 FPS

SPEEDUP: 1.8x faster! 🚀


WITH OPTIMIZATIONS:
═══════════════════════════════════════════════════════════════════════════
Sequential + Cache:
Frame 1: [████████] 35ms (cache hit)
Frame 2:          [████████] 35ms
Frame 3:                   [████████] 35ms
Total: 105ms = 28 FPS

Async + Cache:
Frame 1: [████████] 35ms
Frame 2:     [████████] 35ms
Frame 3:         [████████] 35ms
Total: 55ms = 54 FPS (theoretical max)

SPEEDUP: 5x faster than baseline! 🚀🚀🚀
```

---

### 10.4 Plugin Activation Map

```
┌─────────────────────────────────────────────────────────────────────────┐
│                    WHERE EACH PLUGIN IS APPLIED                         │
└─────────────────────────────────────────────────────────────────────────┘

CAPTURE STAGE:
├─ ⭐ Frame Skip (ESSENTIAL)
│   └─ BEFORE capture processing
├─ ⚙️  Motion Tracker
│   └─ DURING capture
└─ ⚙️  Parallel Capture
    └─ REPLACES single-threaded capture

OCR STAGE:
├─ 🔍 Intelligent Preprocessing (QoL)
│   └─ BEFORE OCR execution
├─ ⭐ Text Block Merger (ESSENTIAL)
│   └─ IMMEDIATELY after OCR
├─ ⭐ Text Validator (ESSENTIAL)
│   └─ AFTER text block merging
├─ ⚙️  Spell Corrector
│   └─ AFTER validation
└─ ⚙️  Parallel OCR
    └─ REPLACES single-threaded OCR

TRANSLATION STAGE:
├─ ⭐ Translation Cache (ESSENTIAL)
│   └─ BEFORE translation (check first)
├─ ⭐ Smart Dictionary (ESSENTIAL)
│   └─ BEFORE translation (check second)
├─ ⚙️  Batch Processing
│   └─ GROUPS multiple texts
└─ ⚙️  Translation Chain
    └─ REPLACES direct translation

POSITIONING STAGE:
└─ 🔧 Collision Detection (built-in)
    └─ DURING position calculation

OVERLAY STAGE:
└─ 🎨 Seamless Background (QoL)
    └─ BEFORE overlay rendering

GLOBAL (ALL STAGES):
├─ ⚙️  Async Pipeline
│   └─ COORDINATES all stages
├─ ⚙️  Priority Queue
│   └─ MANAGES task ordering
└─ ⚙️  Work-Stealing Pool
    └─ BALANCES worker load

LEGEND:
⭐ = Essential (always active, bypass master switch)
⚙️  = Optional (controlled by master switch)
🔍 = QoL Feature (quality of life improvement)
🎨 = QoL Feature (visual enhancement)
🔧 = Built-in (not a plugin)
```

---

**Document Version:** 2.1  
**Last Updated:** November 20, 2025  
**Status:** ✅ Production Architecture with Latest Updates
