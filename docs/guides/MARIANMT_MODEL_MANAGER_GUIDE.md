# MarianMT Model Manager - Complete Guide

## Overview

The MarianMT Model Manager provides a comprehensive UI for downloading, managing, and optimizing translation models from HuggingFace. It's similar to the OCR model manager but with additional features for language pair management.

## Features

### 1. **Model Browsing**
- View all available MarianMT models from Helsinki-NLP
- Filter by source and target language
- See model size, BLEU scores, and download status
- Real-time status updates

### 2. **Batch Language Pair Download**
- Download multiple language pairs at once
- Filter available pairs by source/target language
- Progress tracking for batch downloads
- Automatic retry on failure

### 3. **Model Optimization**
- FP16 optimization for GPU models (CUDA)
- Reduces model size by ~50%
- Improves inference speed by ~1.5x
- Automatic optimization status tracking

### 4. **Cache Management**
- View cache statistics (size, models, disk space)
- Clean up old models based on age
- Limit cache size with automatic cleanup
- Detailed storage information

## Architecture

```
dev/
├── src/
│   └── translation/
│       └── marianmt_model_manager.py    # Backend manager
└── components/
    └── settings/
        └── translation_model_manager.py  # UI integration
```

### Backend (`marianmt_model_manager.py`)

**Key Classes:**
- `MarianMTModel`: Data class for model information
- `OptimizationResult`: Result of model optimization
- `MarianMTModelManager`: Main manager class

**Key Methods:**
```python
# Get available models (with optional filtering)
get_available_models(source_lang=None, target_lang=None) -> List[MarianMTModel]

# Download a single model
download_model(model_name: str, progress_callback=None) -> bool

# Download multiple language pairs
download_language_pairs(pairs: List[Tuple[str, str]], progress_callback=None) -> Dict[str, bool]

# Optimize a model for faster inference
optimize_model(model_name: str) -> OptimizationResult

# Delete a model
delete_model(model_name: str) -> bool

# Get cache statistics
get_cache_info() -> Dict

# Clean up old models
cleanup_cache(max_age_days: int, max_size_gb: float) -> Dict
```

### UI Integration (`translation_model_manager.py`)

**Key Methods:**
- `show_marianmt_manager()`: Main entry point
- `_create_available_models_tab()`: Browse and download models
- `_create_cache_management_tab()`: Manage cache
- `_download_language_pairs()`: Batch download dialog
- `_download_selected_model()`: Download single model
- `_optimize_selected_model()`: Optimize model
- `_delete_selected_model()`: Delete model

## Available Models

The manager includes 26 language pairs:

### European Languages
- English ↔ German (en-de, de-en)
- English ↔ Spanish (en-es, es-en)
- English ↔ French (en-fr, fr-en)
- English ↔ Italian (en-it, it-en)
- English ↔ Portuguese (en-pt, pt-en)
- English ↔ Russian (en-ru, ru-en)
- English ↔ Dutch (en-nl, nl-en)
- English ↔ Polish (en-pl, pl-en)
- English ↔ Turkish (en-tr, tr-en)

### Asian Languages
- English ↔ Japanese (en-ja, ja-en)
- English ↔ Chinese (en-zh, zh-en)
- English ↔ Korean (en-ko, ko-en)

### Other Languages
- English ↔ Arabic (en-ar, ar-en)

Each model:
- Size: ~280-330 MB
- BLEU scores: 24-44 (higher is better)
- Source: Helsinki-NLP on HuggingFace

## Usage

### From the UI

1. **Open Settings** → **Translation Tab**
2. Click **"Manage Models"** button next to MarianMT
3. The Model Manager dialog opens with two tabs:

#### Available Models Tab
- Browse all available models
- Filter by source/target language
- Select a model and click:
  - **"Download Selected"**: Download the model
  - **"Optimize"**: Optimize for faster inference
  - **"Delete"**: Remove the model
- Click **"Download Language Pairs"** for batch download

#### Cache Management Tab
- View cache statistics
- Set cleanup criteria:
  - Maximum age (days)
  - Maximum cache size (GB)
- Click **"Clean Cache"** to remove old models

### Programmatic Usage

```python
from src.translation.marianmt_model_manager import create_marianmt_model_manager

# Create manager
manager = create_marianmt_model_manager()

# Get available models
models = manager.get_available_models(source_lang="en", target_lang="de")

# Download a model
success = manager.download_model("opus-mt-en-de")

# Batch download
pairs = [("en", "de"), ("en", "es"), ("en", "fr")]
results = manager.download_language_pairs(pairs)

# Optimize a model
result = manager.optimize_model("opus-mt-en-de")
if result.success:
    print(f"Speed improvement: {result.speed_improvement}x")
    print(f"Size reduction: {result.memory_reduction_mb} MB")

# Get cache info
info = manager.get_cache_info()
print(f"Downloaded: {info['downloaded_models']}/{info['total_models']}")
print(f"Cache size: {info['total_size_mb']:.1f} MB")

# Cleanup old models
result = manager.cleanup_cache(max_age_days=30, max_size_gb=10.0)
print(f"Deleted {len(result['deleted_models'])} models")
print(f"Freed {result['freed_space_mb']:.1f} MB")
```

## Model Storage

Models are stored in:
```
dev/models/marianmt/
├── opus-mt-en-de/
│   ├── config.json
│   ├── pytorch_model.bin
│   ├── tokenizer_config.json
│   └── ...
├── opus-mt-en-es/
│   └── ...
└── model_registry.json
```

The `model_registry.json` tracks:
- Downloaded models
- Download dates
- Optimization status
- Model sizes

## Optimization Details

### GPU Optimization (CUDA)
- Converts models to FP16 (half precision)
- Reduces size by ~50%
- Improves speed by ~1.5x
- Requires CUDA-capable GPU

### CPU Optimization
- No actual optimization performed
- Models are marked as "optimized" for tracking
- CPU inference uses FP32 by default

## Error Handling

The manager handles common errors:
- **Network failures**: Retry download
- **Disk space**: Check before download
- **Missing dependencies**: Show clear error message
- **Corrupted models**: Delete and re-download

## Dependencies

Required packages:
```
transformers>=4.30.0
torch>=2.0.0
sentencepiece>=0.1.99
```

Install with:
```bash
pip install transformers torch sentencepiece
```

## Performance Tips

1. **Download in batches**: Use "Download Language Pairs" for multiple models
2. **Optimize GPU models**: Always optimize if using CUDA
3. **Clean cache regularly**: Remove unused models to save space
4. **Filter by language**: Use filters to find models quickly
5. **Check disk space**: Ensure sufficient space before downloading

## Troubleshooting

### "Failed to initialize model manager"
- Check that `marianmt_model_manager.py` exists
- Verify import paths are correct
- Check Python path includes `dev/src`

### "Download failed"
- Check internet connection
- Verify HuggingFace is accessible
- Check disk space
- Try downloading again

### "Optimization failed"
- Ensure model is downloaded first
- Check CUDA availability for GPU optimization
- Verify sufficient disk space

### Models not showing in UI
- Refresh the model list
- Check model registry file
- Verify cache directory exists

## Future Enhancements

Potential improvements:
1. **Resume downloads**: Continue interrupted downloads
2. **Model quantization**: INT8 quantization for smaller models
3. **Custom models**: Add models from custom sources
4. **Model comparison**: Compare BLEU scores and speeds
5. **Automatic updates**: Check for model updates
6. **Multi-language chains**: Download related language pairs
7. **Model testing**: Test models before deployment

## Integration with Translation System

The model manager integrates with:
- **Translation Tab**: "Manage Models" button
- **MarianMT Plugin**: Automatic model loading
- **Translation Pipeline**: Model selection and loading
- **Config System**: Saves model preferences

## API Reference

### MarianMTModelManager

```python
class MarianMTModelManager:
    def __init__(self, cache_dir: Optional[Path] = None, 
                 logger: Optional[logging.Logger] = None)
    
    def get_available_models(self, source_lang: Optional[str] = None,
                           target_lang: Optional[str] = None) -> List[MarianMTModel]
    
    def is_model_downloaded(self, model_name: str) -> bool
    
    def download_model(self, model_name: str, 
                      progress_callback=None) -> bool
    
    def delete_model(self, model_name: str) -> bool
    
    def optimize_model(self, model_name: str) -> OptimizationResult
    
    def get_cache_info(self) -> Dict
    
    def cleanup_cache(self, max_age_days: int = 30,
                     max_size_gb: float = 10.0) -> Dict
    
    def download_language_pairs(self, pairs: List[Tuple[str, str]],
                               progress_callback=None) -> Dict[str, bool]
    
    def get_language_pairs(self) -> List[Tuple[str, str, str]]
```

### Data Classes

```python
@dataclass
class MarianMTModel:
    model_name: str
    source_language: str
    target_language: str
    size_mb: float
    accuracy_bleu: float
    is_downloaded: bool = False
    is_optimized: bool = False
    download_url: str = ""
    description: str = ""

@dataclass
class OptimizationResult:
    success: bool
    original_size_mb: float
    optimized_size_mb: float
    speed_improvement: float
    memory_reduction_mb: float
    error_message: str = ""
```

## Summary

The MarianMT Model Manager provides a complete solution for managing translation models with:
- ✅ Easy model browsing and filtering
- ✅ Batch download capabilities
- ✅ Model optimization for performance
- ✅ Cache management and cleanup
- ✅ Progress tracking and error handling
- ✅ Integration with existing translation system

It's designed to be user-friendly while providing powerful features for advanced users.
