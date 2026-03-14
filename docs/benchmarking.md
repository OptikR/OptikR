## Benchmark pipeline overview

This document summarizes how the OptiKr benchmark flow is wired end to end, from the UI dialog down to the individual engines. It focuses on the components involved in the benchmark dialog and how they interact with the shared pipeline and engine infrastructure.

### High-level flow

- **User action**: From the main window, the user opens the benchmark dialog (`BenchmarkDialog`) and configures:
  - Modes: text, vision, or both
  - Execution: sequential / async
  - Scope: fast / full / custom (engines)
  - Image set: default test images or a single user-selected image
- **Benchmark worker**: When the user clicks **Run**, `BenchmarkDialog`:
  - Resolves the image list (either all defaults or the selected file)
  - Reads the `benchmark.allow_vision_async` flag from the config manager
  - Instantiates a `BenchmarkWorker` (a `QThread`) with the chosen scope
  - Connects the worker’s `progress`, `finished`, and `error` signals back to the dialog
  - Starts the worker thread so the UI remains responsive
- **Combination matrix**: Inside `BenchmarkWorker.run`:
  - `build_default_combinations` (in `benchmark_runner`) constructs a (mode, execution, plugins, engines) matrix according to:
    - `include_vision` / `include_text`
    - `fast` scope vs full
    - Optional custom text translation / OCR engine selections
  - `guard_vision_async_combinations` post-processes the matrix:
    - If `allow_vision_async` is `False`, any `("vision", "async", ...)` entries are downgraded to sequential
    - Duplicate combinations are removed
    - If downgrades occurred, the worker emits a log message explaining that async vision combinations were disabled or downgraded
- **Benchmark core**: The worker then calls `run_benchmark` with:
  - The concrete image paths
  - The guarded combination matrix
  - A progress callback that forwards messages to the UI

### Core benchmark runner

The core benchmark implementation lives in `app/benchmark/benchmark_runner.py`:

- **Entry point (`run_benchmark`)**
  - Normalizes the image list into `Path` objects and drops non-existent files
  - If no explicit combinations are provided, generates defaults via `build_default_combinations` and `guard_vision_async_combinations`
  - Creates a shared `MockCaptureLayer` that serves frames to pipelines
  - Delegates to `_run_benchmark_with_reuse` to execute all combinations

- **Engine reuse (`_run_benchmark_with_reuse`)**
  - Splits the combination list into:
    - `vision_combos`: entries where `mode == "vision"`
    - `text_combos`: entries where `mode == "text"`
  - For **vision**:
    - Lazily imports `VisionTranslationEngine` from `plugins.stages.vision.qwen3_vl.worker`
    - Initializes a single shared `VisionTranslationEngine` instance with the Qwen3-VL configuration
    - For each image and vision combination:
      - Logs progress (including a `[current/total]` counter parsed by the UI)
      - Delegates to `_run_combination`, passing the shared vision engine
    - After all runs, calls `engine.cleanup()` if available and logs unload
    - If import or initialization fails, produces synthetic failed `BenchmarkResult` rows for the affected combinations
  - For **text**:
    - Computes the unique OCR and translation engine IDs referenced by text combinations
    - For each OCR engine ID:
      - Creates and initializes an engine instance via `_create_ocr_engine`
      - Caches successful instances in a small map
    - For each translation engine ID:
      - Creates and initializes an engine instance via `_create_translation_engine`
      - For each image and matching text combination:
        - Looks up the appropriate OCR engine instance
        - Logs progress and calls `_run_combination`, passing the shared OCR and translation engines
      - Cleans up the translation engine instance when finished
    - Finally, cleans up all OCR engine instances

- **Per-combination runner (`_run_combination`)**
  - Starts a per-run timer
  - Dispatches based on `mode`:
    - `"vision"` → `_run_single_frame_vision`
    - `"text"` → `_run_single_frame_text`
  - Wraps the boolean success flag, elapsed time, block count, and error string into a `BenchmarkResult`

### Vision benchmark path

For vision benchmarks, `_run_single_frame_vision` builds and runs a single-frame vision pipeline:

- **Frame preparation**
  - Calls `_load_image_as_frame`:
    - Uses `PIL.Image` and `numpy` to load the image file into an RGB array
    - Wraps it into an `app.models.Frame` with a matching `CaptureRegion` rectangle
  - Sets this frame on the shared `MockCaptureLayer`, which implements `capture_frame` for the pipeline

- **Pipeline construction**
  - Chooses execution mode:
    - `ExecutionMode.ASYNC` when `execution == "async"`
    - `ExecutionMode.SEQUENTIAL` otherwise
  - Builds a `PipelineConfig` with source/target languages and the selected execution mode
  - Uses `PipelineFactory.create("vision", ...)` to construct a `BasePipeline` with:
    - `capture_layer` wired to the shared `MockCaptureLayer`
    - `vision_layer` wired to the (shared) `VisionTranslationEngine`
    - Any configured plugins enabled or disabled via `enable_all_plugins`

- **Execution and results**
  - Installs an `on_translation` callback on the pipeline to capture the first translation result into a holder list and set a synchronization event
  - Starts the pipeline and waits (up to a timeout) for the event indicating a translation callback
  - Stops and cleans up the pipeline (and, if the engine is not shared, the vision engine itself)
  - Extracts the block count from the returned `translations` list and returns:
    - `success`: whether a translation callback was received before timeout
    - `block_count`: number of translated blocks
    - `error`: a human-readable error such as `"No translation callback (timeout or failure)"` when unsuccessful

### Text benchmark path

For text benchmarks, `_run_single_frame_text` builds a pipeline that composes OCR and text translation engines:

- **Engine adapters**
  - Wraps the chosen OCR engine in `_OCRLayerAdapter`, which:
    - Accepts frames from the capture layer
    - Forwards to the underlying OCR engine with `OCRProcessingOptions`
    - Cleans up the engine when appropriate
  - Wraps the chosen translation engine in `_TranslationLayerAdapter`, which:
    - Provides a `translate_batch` API that translates a list of texts
    - Extracts `translated_text` strings from engine-specific result objects
    - Cleans up the engine when appropriate

- **Pipeline construction and execution**
  - Loads the image into a `Frame` and sets it on `MockCaptureLayer`
  - Selects:
    - `preset = "async"` or `"sequential"` based on the requested execution
    - `ExecutionMode.ASYNC` or `ExecutionMode.SEQUENTIAL` for the pipeline config
  - Uses `PipelineFactory.create(preset, ...)` to construct a `BasePipeline` wired with:
    - `capture_layer` → `MockCaptureLayer`
    - `ocr_layer` → OCR adapter
    - `translation_layer` → translation adapter
  - Installs an `on_translation` callback, starts the pipeline, waits for the callback or timeout, then stops and cleans up
  - Returns success, block count, and error in the same shape as the vision helper

### Result aggregation and JSON export

- **Aggregation in the dialog**
  - After `BenchmarkWorker` emits `finished(results)`, `BenchmarkDialog`:
    - Stores the `BenchmarkResult` list
    - Populates the results table with:
      - Mode, execution, plugins, engines, image name, success flag, time, block count, and error snippet
    - Builds a grouped textual summary via `_build_summary`, which:
      - Groups by `(mode, execution, plugins, translation_engine, ocr_engine)`
      - Computes success counts and average times per combination
- **Automatic JSON persistence**
  - `_auto_save_json` is called with the results and summary text:
    - Resolves the benchmarks directory via `get_benchmarks_dir` (under `user_data/benchmarks`)
    - Writes a JSON file named `benchmark_YYYYMMDD_HHMMSS.json` containing:
      - `metadata`: timestamp, mode flags, and configuration-derived details such as source/target language, active engines, pipeline mode, execution mode, and benchmark scope (when a config manager is present)
      - `results`: a full list of serialized `BenchmarkResult` rows
      - `summary_by_combination`: a compact table of per-combination statistics for quick comparison
      - `summary_text`: the same human-readable summary shown in the UI
  - The dialog refreshes its “previous runs” dropdown from this directory so past JSON files can be reloaded and inspected.

### Architecture diagram

Below is a simplified view of the main control flow when running benchmarks from the UI:

```mermaid
flowchart TD
    A[Main Window] --> B[BenchmarkDialog]
    B --> C[BenchmarkWorker (QThread)]
    C --> D[build_default_combinations]
    D --> E[guard_vision_async_combinations]
    E --> F[run_benchmark]
    F --> G[_run_benchmark_with_reuse]

    G --> H[_run_single_frame_vision]
    G --> I[_run_single_frame_text]

    H --> J[PipelineFactory.create('vision', ...)]
    I --> K[PipelineFactory.create(preset, ...)]

    J --> L[BasePipeline + ExecutionStrategy]
    K --> L

    L --> M[VisionTranslationEngine (Qwen3-VL)]
    L --> N[OCR Engines (easyocr, tesseract, mokuro)]
    L --> O[Text Translation Engines (marianmt, qwen3, nllb200)]

    L --> P[on_translation callback]
    P --> Q[BenchmarkResult rows]
    Q --> R[BenchmarkDialog table + summary]
    R --> S[_auto_save_json → benchmark_*.json]
```

