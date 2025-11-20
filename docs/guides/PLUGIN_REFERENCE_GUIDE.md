# Complete Plugin Reference Guide

## Table of Contents

### Capture Plugins
1. [DirectX Capture (GPU)](#1-directx-capture-gpu)
2. [Screenshot Capture (CPU)](#2-screenshot-capture-cpu)

### OCR Plugins
3. [EasyOCR](#3-easyocr)
4. [Tesseract](#4-tesseract)
5. [PaddleOCR](#5-paddleocr)
6. [Manga OCR](#6-manga-ocr)
7. [Hybrid OCR](#7-hybrid-ocr)

### Optimizer Plugins
8. [Async Pipeline](#8-async-pipeline)
9. [Batch Processing](#9-batch-processing)
10. [Frame Skip](#10-frame-skip)
11. [Learning Dictionary](#11-learning-dictionary)
12. [Motion Tracker](#12-motion-tracker)
13. [OCR per Region](#13-ocr-per-region)
14. [Parallel Capture](#14-parallel-capture)
15. [Parallel OCR](#15-parallel-ocr)
16. [Parallel Translation](#16-parallel-translation)
17. [Priority Queue](#17-priority-queue)
18. [Text Block Merger](#18-text-block-merger)
19. [Text Validator](#19-text-validator)
20. [Translation Cache](#20-translation-cache)
21. [Translation Chain](#21-translation-chain)
22. [Work Stealing](#22-work-stealing)

### Text Processor Plugins
23. [Regex Processor](#23-regex-processor)
24. [Spell Corrector](#24-spell-corrector)

### Translation Plugins
25. [MarianMT (GPU)](#25-marianmt-gpu)
26. [LibreTranslate](#26-libretranslate)

---

## Capture Plugins

### 1. DirectX Capture (GPU)

**Type**: Capture  
**File**: `plugins/capture/dxcam_capture_gpu/`  
**Status**: ✅ Implemented  
**Default**: Yes (if GPU available)

#### What It Does
Captures screen content using DirectX GPU acceleration. Fastest capture method available.

#### How It Works
```
1. Initialize DirectX capture device
2. Lock GPU frame buffer
3. Copy frame data (GPU → CPU)
4. Convert to RGB format
5. Return frame object
```

#### Performance
- **Speed**: ~8ms per frame
- **CPU Usage**: Very low (5-10%)
- **GPU Usage**: Low (10-15%)
- **Memory**: Minimal

#### When to Use
✅ **Use when**:
- You have a dedicated GPU
- You want maximum performance
- You're capturing games or GPU-accelerated apps

❌ **Don't use when**:
- No GPU available
- GPU is busy with other tasks
- Compatibility issues with specific apps

#### Configuration
```json
{
  "device_idx": 0,
  "output_idx": 0,
  "output_color": "RGB"
}
```

#### Settings
- **device_idx**: GPU device index (0 = primary GPU)
- **output_idx**: Monitor index (0 = primary monitor)
- **output_color**: Color format (RGB, BGR, GRAY)

#### Troubleshooting
**Problem**: Black screen captured  
**Solution**: Try different output_idx or use CPU capture

**Problem**: Capture fails  
**Solution**: Update GPU drivers, check DirectX version

---

### 2. Screenshot Capture (CPU)

**Type**: Capture  
**File**: `plugins/capture/screenshot_capture_cpu/`  
**Status**: ✅ Implemented  
**Default**: Fallback if GPU unavailable

#### What It Does
Captures screen content using CPU-based screenshot method. Universal compatibility.

#### How It Works
```
1. Use system screenshot API
2. Capture specified region
3. Convert to numpy array
4. Return frame object
```

#### Performance
- **Speed**: ~15-20ms per frame
- **CPU Usage**: Moderate (20-30%)
- **GPU Usage**: None
- **Memory**: Minimal

#### When to Use
✅ **Use when**:
- No GPU available
- GPU capture not working
- Maximum compatibility needed
- Capturing desktop apps

❌ **Don't use when**:
- GPU capture is working
- You need maximum performance

#### Configuration
```json
{
  "method": "mss",
  "compression": false
}
```

#### Settings
- **method**: Screenshot method (mss, pillow, win32)
- **compression**: Enable compression (slower but less memory)

#### Troubleshooting
**Problem**: Slow capture  
**Solution**: Use GPU capture if available

**Problem**: High CPU usage  
**Solution**: Reduce capture frequency, enable frame skip

---

## OCR Plugins

### 3. EasyOCR

**Type**: OCR Engine  
**File**: `plugins/ocr/easyocr/`  
**Status**: ✅ Implemented  
**Default**: Yes

#### What It Does
General-purpose OCR engine with good accuracy for multiple languages. Best all-around choice.

#### How It Works
```
1. Load pre-trained neural network model
2. Detect text regions in image
3. Extract text from each region
4. Calculate confidence scores
5. Return text blocks with positions
```

#### Performance
- **Speed**: ~50ms per frame
- **Accuracy**: High (90-95%)
- **Languages**: 80+ languages
- **GPU**: Supported (recommended)

#### When to Use
✅ **Use when**:
- General text recognition
- Multiple languages needed
- Good balance of speed/accuracy
- Default choice for most cases

❌ **Don't use when**:
- Only English text (Tesseract faster)
- Japanese manga (Manga OCR better)
- Need maximum speed

#### Supported Languages
English, Japanese, Korean, Chinese, German, French, Spanish, Russian, Arabic, Thai, Vietnamese, and 70+ more

#### Configuration
```json
{
  "languages": ["en", "ja"],
  "gpu": true,
  "detector": true,
  "recognizer": true,
  "paragraph": false
}
```

#### Settings
- **languages**: List of language codes
- **gpu**: Use GPU acceleration
- **detector**: Enable text detection
- **recognizer**: Enable text recognition
- **paragraph**: Group text into paragraphs

#### Tips
💡 **For best results**:
- Use GPU if available (5x faster)
- Limit languages to what you need
- Enable paragraph mode for documents
- Adjust confidence threshold

#### Troubleshooting
**Problem**: Slow processing  
**Solution**: Enable GPU, reduce languages

**Problem**: Low accuracy  
**Solution**: Check image quality, adjust confidence threshold

**Problem**: Missing text  
**Solution**: Enable detector, check text size

---

### 4. Tesseract

**Type**: OCR Engine  
**File**: `plugins/ocr/tesseract/`  
**Status**: ✅ Implemented  
**Default**: No

#### What It Does
Fast OCR engine optimized for clean, printed text. Best for documents and UI text.

#### How It Works
```
1. Preprocess image (binarization)
2. Detect text layout
3. Recognize characters
4. Apply language model
5. Return text with confidence
```

#### Performance
- **Speed**: ~30ms per frame (faster than EasyOCR)
- **Accuracy**: High for clean text (95%+)
- **Languages**: 100+ languages
- **GPU**: Not supported (CPU only)

#### When to Use
✅ **Use when**:
- Clean, printed text
- UI elements, menus
- Documents, PDFs
- Need maximum speed
- English text primarily

❌ **Don't use when**:
- Handwritten text
- Stylized fonts
- Low-quality images
- Japanese manga

#### Supported Languages
English, German, French, Spanish, Italian, Portuguese, Russian, Chinese, Japanese, Korean, and 90+ more

#### Configuration
```json
{
  "lang": "eng",
  "oem": 3,
  "psm": 3,
  "config": "--oem 3 --psm 3"
}
```

#### Settings
- **lang**: Language code (eng, deu, fra, etc.)
- **oem**: OCR Engine Mode (0-3, 3=default)
- **psm**: Page Segmentation Mode (0-13, 3=auto)
- **config**: Additional Tesseract config

#### OEM (OCR Engine Mode)
- 0 = Legacy engine only
- 1 = Neural nets LSTM engine only
- 2 = Legacy + LSTM engines
- 3 = Default (based on what's available)

#### PSM (Page Segmentation Mode)
- 3 = Fully automatic page segmentation (default)
- 6 = Assume a single uniform block of text
- 7 = Treat the image as a single text line
- 11 = Sparse text. Find as much text as possible

#### Tips
💡 **For best results**:
- Use PSM 6 for single blocks
- Use PSM 7 for single lines
- Use PSM 11 for scattered text
- Preprocess images (contrast, denoise)

#### Troubleshooting
**Problem**: Poor accuracy  
**Solution**: Adjust PSM mode, improve image quality

**Problem**: Missing text  
**Solution**: Try PSM 11 (sparse text mode)

---

### 5. PaddleOCR

**Type**: OCR Engine  
**File**: `plugins/ocr/paddleocr/`  
**Status**: ✅ Implemented  
**Default**: No

#### What It Does
OCR engine optimized for Asian languages (Chinese, Japanese, Korean). Excellent for CJK text.

#### How It Works
```
1. Text detection (find text regions)
2. Text direction classification
3. Text recognition
4. Post-processing
5. Return structured results
```

#### Performance
- **Speed**: ~40ms per frame
- **Accuracy**: Very high for CJK (95%+)
- **Languages**: 80+ languages, optimized for Asian
- **GPU**: Supported

#### When to Use
✅ **Use when**:
- Chinese text
- Japanese text (alternative to Manga OCR)
- Korean text
- Mixed CJK and English
- Vertical text

❌ **Don't use when**:
- Only English text (Tesseract faster)
- Japanese manga (Manga OCR better)
- Need maximum speed

#### Supported Languages
Chinese (Simplified/Traditional), Japanese, Korean, English, and 75+ more

#### Configuration
```json
{
  "lang": "ch",
  "use_angle_cls": true,
  "use_gpu": true,
  "det": true,
  "rec": true
}
```

#### Settings
- **lang**: Language (ch, japan, korean, en, etc.)
- **use_angle_cls**: Detect text direction
- **use_gpu**: GPU acceleration
- **det**: Enable detection
- **rec**: Enable recognition

#### Tips
💡 **For best results**:
- Use GPU for speed
- Enable angle classification for rotated text
- Use 'japan' lang for Japanese
- Use 'korean' lang for Korean

#### Troubleshooting
**Problem**: Slow processing  
**Solution**: Enable GPU, disable angle classification

**Problem**: Vertical text not detected  
**Solution**: Enable angle classification

---

### 6. Manga OCR

**Type**: OCR Engine  
**File**: `plugins/ocr/manga_ocr/`  
**Status**: ✅ Implemented  
**Default**: No

#### What It Does
Specialized OCR engine for Japanese manga and comics. Best accuracy for manga text.

#### How It Works
```
1. Load manga-specific model
2. Detect text in speech bubbles
3. Handle vertical text
4. Recognize stylized fonts
5. Return Japanese text
```

#### Performance
- **Speed**: ~45ms per frame
- **Accuracy**: Excellent for manga (98%+)
- **Languages**: Japanese only
- **GPU**: Supported

#### When to Use
✅ **Use when**:
- Reading Japanese manga
- Japanese comics
- Stylized Japanese text
- Vertical Japanese text
- Speech bubbles

❌ **Don't use when**:
- Non-Japanese text
- Regular documents
- UI text
- Need multiple languages

#### Configuration
```json
{
  "model": "manga-ocr-base",
  "use_gpu": true,
  "force_cpu": false
}
```

#### Settings
- **model**: Model variant (base, large)
- **use_gpu**: GPU acceleration
- **force_cpu**: Force CPU mode

#### Tips
💡 **For best results**:
- Use with motion_tracker for smooth scrolling
- Combine with text_block_merger
- Enable GPU for speed
- Use ocr_per_region to assign to manga regions

#### Troubleshooting
**Problem**: English text not recognized  
**Solution**: Use hybrid_ocr or ocr_per_region

**Problem**: Slow processing  
**Solution**: Enable GPU

---

### 7. Hybrid OCR

**Type**: OCR Engine  
**File**: `plugins/ocr/hybrid_ocr/`  
**Status**: ✅ Implemented  
**Default**: No

#### What It Does
Combines EasyOCR and Tesseract for maximum accuracy. Uses best result from both engines.

#### How It Works
```
1. Run EasyOCR on image
2. Run Tesseract on image
3. Compare results
4. Select best based on strategy:
   - best_confidence: Highest confidence
   - longest_text: Most complete text
   - consensus: Both engines agree
   - easyocr_primary: EasyOCR with Tesseract fallback
5. Return combined results
```

#### Performance
- **Speed**: ~80ms per frame (2x slower)
- **Accuracy**: Highest (96-98%)
- **Languages**: All supported by both engines
- **GPU**: Supported (for EasyOCR)

#### When to Use
✅ **Use when**:
- Maximum accuracy needed
- Critical text (legal, medical)
- Mixed text types
- Speed not critical
- Difficult text

❌ **Don't use when**:
- Need maximum speed
- Simple, clean text
- Real-time processing
- Limited CPU/GPU

#### Strategies

**best_confidence** (default):
- Picks result with highest confidence
- Best for general use
- Balanced accuracy

**longest_text**:
- Picks longer/more complete text
- Good for partial OCR failures
- May include noise

**consensus**:
- Only returns text both engines agree on
- Highest accuracy
- May miss some text

**easyocr_primary**:
- Uses EasyOCR primarily
- Falls back to Tesseract if confidence < threshold
- Good balance of speed/accuracy

#### Configuration
```json
{
  "strategy": "best_confidence",
  "confidence_threshold": 0.7,
  "use_gpu": true,
  "enable_easyocr": true,
  "enable_tesseract": true
}
```

#### Settings
- **strategy**: Selection strategy
- **confidence_threshold**: Minimum confidence
- **use_gpu**: GPU for EasyOCR
- **enable_easyocr**: Enable EasyOCR
- **enable_tesseract**: Enable Tesseract

#### Tips
💡 **For best results**:
- Use best_confidence for general use
- Use consensus for critical text
- Enable GPU for speed
- Adjust confidence threshold based on needs

#### Troubleshooting
**Problem**: Too slow  
**Solution**: Use single engine or reduce resolution

**Problem**: Conflicting results  
**Solution**: Use consensus strategy

---

## Optimizer Plugins

### 8. Async Pipeline

**Type**: Optimizer (Global)  
**File**: `plugins/optimizers/async_pipeline/`  
**Status**: ✅ Implemented  
**Essential**: No  
**Default**: Disabled

#### What It Does
Enables asynchronous pipeline processing with multiple frames in flight simultaneously. Massive performance boost.

#### How It Works
```
Sequential:
Frame 1: [Capture][OCR][Translation][Overlay] → 96ms
Frame 2: [Capture][OCR][Translation][Overlay] → 96ms
Result: 10.4 FPS

Async:
Frame 1: [Capture][OCR][Translation][Overlay]
Frame 2:       [Capture][OCR][Translation][Overlay]
Frame 3:             [Capture][OCR][Translation][Overlay]
... (8-10 frames in flight)
Result: 18.0 FPS (73% faster!)
```

#### Performance
- **Speed**: 50-80% throughput improvement
- **Latency**: Same as sequential (96ms)
- **CPU Usage**: +15-25%
- **Memory**: +300-500MB
- **Frames in Flight**: 8-10

#### When to Use
✅ **Use when**:
- Need maximum FPS
- Have spare CPU/memory
- Production use
- Stable setup

❌ **Don't use when**:
- Debugging issues
- Limited memory
- Unstable plugins
- Testing new features

#### Configuration
```json
{
  "max_concurrent_stages": 4,
  "queue_size": 10,
  "enable_backpressure": true
}
```

#### Settings
- **max_concurrent_stages**: Max parallel stages (2-8)
- **queue_size**: Buffer size (5-20)
- **enable_backpressure**: Prevent queue overflow

#### Tips
💡 **For best results**:
- Start with 4 concurrent stages
- Monitor memory usage
- Increase queue_size if dropping frames
- Disable for debugging

#### Troubleshooting
**Problem**: High memory usage  
**Solution**: Reduce max_concurrent_stages or queue_size

**Problem**: Frames dropped  
**Solution**: Increase queue_size, enable backpressure

**Problem**: Unstable  
**Solution**: Disable and use sequential

---

### 9. Batch Processing

**Type**: Optimizer (Translation - Pre)  
**File**: `plugins/optimizers/batch_processing/`  
**Status**: ✅ Implemented  
**Essential**: No  
**Default**: Disabled

#### What It Does
Batches multiple frames together for GPU processing. Improves GPU utilization by 30-50%.

#### How It Works
```
Without batching:
Frame 1 → GPU (30ms, 40% utilization)
Frame 2 → GPU (30ms, 40% utilization)
Frame 3 → GPU (30ms, 40% utilization)

With batching:
Frames 1-3 → GPU (35ms, 90% utilization)
Result: 3 frames in 35ms vs 90ms (2.5x faster!)
```

#### Performance
- **Speed**: 30-50% faster translation
- **GPU Utilization**: +50-100%
- **Latency**: +10ms max (wait time)
- **Memory**: +50-100MB (batch buffer)

#### When to Use
✅ **Use when**:
- Using GPU translation
- Multiple text blocks per frame
- High frame rate
- GPU underutilized

❌ **Don't use when**:
- CPU translation
- Single text per frame
- Need minimum latency
- GPU already maxed

#### Configuration
```json
{
  "max_batch_size": 8,
  "max_wait_time_ms": 10.0,
  "min_batch_size": 2,
  "adaptive": true
}
```

#### Settings
- **max_batch_size**: Max frames per batch (2-32)
- **max_wait_time_ms**: Max wait to form batch (1-100ms)
- **min_batch_size**: Min frames to batch (1-16)
- **adaptive**: Adjust batch size dynamically

#### Tips
💡 **For best results**:
- Start with batch_size=8, wait=10ms
- Enable adaptive mode
- Monitor GPU utilization
- Increase batch_size if GPU underutilized

#### Troubleshooting
**Problem**: Added latency  
**Solution**: Reduce max_wait_time_ms

**Problem**: Small batches  
**Solution**: Increase max_wait_time_ms

**Problem**: No improvement  
**Solution**: Check if GPU is bottleneck

---

### 10. Frame Skip

**Type**: Optimizer (Capture - Post)  
**File**: `plugins/optimizers/frame_skip/`  
**Status**: ✅ Implemented  
**Essential**: ⭐ Yes  
**Default**: Enabled

#### What It Does
Skips processing of unchanged frames. Reduces CPU usage by 50-70% for static scenes.

#### How It Works
```
Frame 1: [Capture] → Hash: ABC123 → Process (new)
Frame 2: [Capture] → Hash: ABC123 → Skip (same)
Frame 3: [Capture] → Hash: ABC123 → Skip (same)
Frame 4: [Capture] → Hash: DEF456 → Process (changed)

Result: 75% frames skipped, 75% CPU saved!
```

#### Performance
- **CPU Saved**: 50-70% for static scenes
- **Overhead**: 0.5-2ms per frame (comparison)
- **Memory**: Minimal (1 previous frame)

#### When to Use
✅ **Always use** (essential plugin)
- Automatic optimization
- No downsides
- Works with all content

#### Comparison Methods

**hash** (default):
- Fastest (0.5ms)
- Perceptual hash
- Good for most cases

**mse** (Mean Squared Error):
- Medium speed (1ms)
- Pixel-by-pixel comparison
- More accurate

**ssim** (Structural Similarity):
- Slower (2ms)
- Structural comparison
- Most accurate

#### Configuration
```json
{
  "similarity_threshold": 0.98,
  "min_skip_frames": 3,
  "max_skip_frames": 30,
  "comparison_method": "hash"
}
```

#### Settings
- **similarity_threshold**: How similar to skip (0.8-0.99)
- **min_skip_frames**: Min similar frames before skipping
- **max_skip_frames**: Max consecutive skips
- **comparison_method**: hash/mse/ssim

#### Tips
💡 **For best results**:
- Use hash for speed
- Use ssim for accuracy
- Adjust threshold: 0.95 (sensitive) to 0.99 (strict)
- Increase max_skip_frames for very static content

#### Troubleshooting
**Problem**: Skipping too much  
**Solution**: Lower similarity_threshold (0.95)

**Problem**: Not skipping enough  
**Solution**: Raise similarity_threshold (0.99)

**Problem**: Slow comparison  
**Solution**: Use hash method

---

