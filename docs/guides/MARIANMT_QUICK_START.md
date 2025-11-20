# MarianMT Model Manager - Quick Start Guide

## 🚀 Getting Started in 3 Steps

### Step 1: Open the Model Manager
1. Launch your application
2. Go to **Settings** (gear icon)
3. Click on **Translation** tab
4. Select **"MarianMT (Neural MT - Recommended)"** from the dropdown
5. Click the **"Manage Models"** button

### Step 2: Download Models
You have two options:

#### Option A: Download Single Model
1. Go to **"Available Models"** tab
2. Use filters to find your language pair (e.g., Source: en, Target: de)
3. Select the model from the list
4. Click **"Download Selected"**
5. Wait for download to complete (~300 MB, 2-5 minutes)

#### Option B: Batch Download (Recommended)
1. Click **"Download Language Pairs"** button
2. Select multiple language pairs you need
3. Click **"Download Selected"**
4. All models download automatically

### Step 3: Use Your Models
1. Close the Model Manager
2. Your downloaded models are now available
3. Start translating!

## 📦 Recommended Language Pairs

### For Manga/Anime Translation
- Japanese → English (ja-en)
- English → Japanese (en-ja)

### For European Content
- German ↔ English (de-en, en-de)
- Spanish ↔ English (es-en, en-es)
- French ↔ English (fr-en, en-fr)

### For Asian Content
- Chinese ↔ English (zh-en, en-zh)
- Korean ↔ English (ko-en, en-ko)

## ⚡ Performance Tips

### 1. Optimize Your Models (GPU Users)
After downloading:
1. Select a downloaded model
2. Click **"Optimize"**
3. Model converts to FP16 (faster, smaller)
4. Enjoy 1.5x speed boost!

### 2. Manage Your Cache
Keep your cache clean:
1. Go to **"Cache Management"** tab
2. Set max age (e.g., 30 days)
3. Set max size (e.g., 10 GB)
4. Click **"Clean Cache"** periodically

## 🎯 Common Use Cases

### Use Case 1: Japanese Game Translation
**What you need:**
- Japanese → English (ja-en)

**Steps:**
1. Open Model Manager
2. Filter: Source = ja, Target = en
3. Download "opus-mt-jap-en"
4. Done! (~315 MB)

### Use Case 2: Multi-Language Support
**What you need:**
- Multiple language pairs

**Steps:**
1. Click "Download Language Pairs"
2. Select all needed pairs:
   - ☑ English → German
   - ☑ English → Spanish
   - ☑ English → French
3. Download all at once
4. Done! (~900 MB for 3 pairs)

### Use Case 3: Bidirectional Translation
**What you need:**
- Both directions (e.g., EN↔DE)

**Steps:**
1. Download both models:
   - opus-mt-en-de (English → German)
   - opus-mt-de-en (German → English)
2. Optimize both for best performance
3. Done!

## 💡 Pro Tips

### Tip 1: Download During Off-Hours
Models are large (~300 MB each). Download when you have:
- Good internet connection
- Time to wait (2-5 minutes per model)
- Sufficient disk space (check before downloading)

### Tip 2: Use Filters Effectively
Don't scroll through all 26 models:
- Filter by source language
- Filter by target language
- Find exactly what you need

### Tip 3: Optimize After Downloading
If you have a CUDA GPU:
1. Always optimize after downloading
2. Reduces size by ~50%
3. Speeds up translation by ~1.5x
4. No quality loss!

### Tip 4: Batch Download Related Pairs
Downloading multiple pairs? Do it in one batch:
- Faster than one-by-one
- Single progress dialog
- Automatic retry on failure

### Tip 5: Monitor Your Cache
Check cache regularly:
- View total size
- See which models are downloaded
- Clean up unused models
- Free up disk space

## 🔧 Troubleshooting

### Problem: Download Failed
**Solutions:**
1. Check internet connection
2. Verify HuggingFace is accessible
3. Check disk space (need ~300 MB per model)
4. Try downloading again
5. Try a different model first

### Problem: Model Not Showing in UI
**Solutions:**
1. Click "Refresh List" button
2. Close and reopen Model Manager
3. Check if model is in models/marianmt/ folder
4. Verify model_registry.json exists

### Problem: Optimization Failed
**Solutions:**
1. Ensure model is downloaded first
2. Check if CUDA is available (GPU users)
3. Verify sufficient disk space
4. Try optimizing a different model first

### Problem: Out of Disk Space
**Solutions:**
1. Go to "Cache Management" tab
2. Delete unused models
3. Run "Clean Cache" with lower size limit
4. Free up space on your drive

## 📊 Model Information

### Model Sizes
- Small: ~280-290 MB (Dutch, Italian, Turkish)
- Medium: ~295-310 MB (Most European languages)
- Large: ~315-330 MB (Asian languages)

### BLEU Scores (Quality)
- Excellent: 40+ (EN↔ES, EN↔DE, EN↔FR)
- Good: 30-40 (EN↔RU, EN↔IT, EN↔PT)
- Fair: 24-30 (EN↔JA, EN↔ZH, EN↔KO)

Higher BLEU = Better translation quality

### Download Times (Approximate)
- Fast connection (100 Mbps): 30-60 seconds
- Medium connection (50 Mbps): 1-2 minutes
- Slow connection (10 Mbps): 5-10 minutes

## 🎓 Advanced Usage

### Programmatic Access
```python
from src.translation.marianmt_model_manager import create_marianmt_model_manager

# Create manager
manager = create_marianmt_model_manager()

# Download specific model
manager.download_model("opus-mt-en-de")

# Batch download
pairs = [("en", "de"), ("en", "es"), ("en", "fr")]
results = manager.download_language_pairs(pairs)

# Get info
info = manager.get_cache_info()
print(f"Downloaded: {info['downloaded_models']}/{info['total_models']}")
```

### Custom Cache Location
```python
from pathlib import Path

# Use custom cache directory
custom_cache = Path("D:/MyModels/marianmt")
manager = create_marianmt_model_manager(cache_dir=custom_cache)
```

## 📚 Additional Resources

- **Full Guide**: See `MARIANMT_MODEL_MANAGER_GUIDE.md`
- **Implementation Details**: See `MARIANMT_MODEL_MANAGER_IMPLEMENTATION.md`
- **Flow Diagrams**: See `MARIANMT_MODEL_MANAGER_FLOW.md`
- **Test Script**: Run `python test_marianmt_model_manager.py`

## ✅ Checklist

Before you start translating:
- [ ] Model Manager opens successfully
- [ ] Can see list of 26 available models
- [ ] Downloaded at least one language pair
- [ ] Model shows as "✓ Downloaded" in list
- [ ] (Optional) Optimized model for GPU
- [ ] Model appears in translation settings
- [ ] Translation works with downloaded model

## 🎉 You're Ready!

Once you've downloaded your models, you're all set to:
- Translate text in real-time
- Use high-quality neural translation
- Support multiple language pairs
- Enjoy fast, offline translation

Happy translating! 🌐
