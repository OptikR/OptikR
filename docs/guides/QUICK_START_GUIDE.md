# Quick Start Guide - OCR per Region

## 🎯 What You Can Do Now

You can now assign **different OCR engines** to **different screen regions**!

Example use cases:
- Region 1 (manga): Use `manga_ocr` for Japanese text
- Region 2 (subtitles): Use `tesseract` for fast English text
- Region 3 (UI): Use `paddleocr` for mixed languages

---

## 🚀 Quick Setup (5 Steps)

### Step 1: Open Region Selector
Click the **"Select Capture Region"** button in the toolbar

### Step 2: Add Regions
1. Click **"+ Add Region"**
2. Select your monitor
3. Click **"Draw Region"**
4. Draw a rectangle around the area
5. Click **"Apply"**
6. Give it a name (e.g., "Manga Panel", "Subtitles")
7. Repeat for more regions

### Step 3: Assign OCR Engines
For each region in the list:
- Find the **"OCR Engine"** dropdown
- Select the best engine for that region:
  - `default` - System default
  - `easyocr` - General purpose, good accuracy
  - `tesseract` - Fast, good for clean text
  - `paddleocr` - Great for Asian languages
  - `manga_ocr` - Specialized for manga/Japanese
  - `hybrid_ocr` - Combines multiple engines

### Step 4: Save
Click **"Save Configuration"** button

### Step 5: Visualize (Optional)
Click **"Region Overlay"** button in toolbar
- All your regions appear in **GREEN**
- Press **ESC** to close

---

## 🎨 Visual Guide

```
┌─────────────────────────────────────────┐
│  Multi-Region Capture Configuration    │
├─────────────────────────────────────────┤
│                                         │
│  ☑ Manga Panel                          │
│     Monitor 0 | 800×600 | (100, 100)    │
│     OCR Engine: [manga_ocr ▼]           │
│     [Edit] [×]                          │
│                                         │
│  ☑ Subtitles                            │
│     Monitor 0 | 1920×100 | (0, 980)     │
│     OCR Engine: [tesseract ▼]           │
│     [Edit] [×]                          │
│                                         │
│  ☑ UI Text                              │
│     Monitor 1 | 400×300 | (50, 50)      │
│     OCR Engine: [easyocr ▼]             │
│     [Edit] [×]                          │
│                                         │
│  [+ Add Region]                         │
│                                         │
│  [Save Configuration] [Cancel]          │
└─────────────────────────────────────────┘
```

---

## 🔍 How to Verify It's Working

### Check Logs:
When translation runs, you'll see:
```
[OCR_PER_REGION] Region 'Manga Panel' → manga_ocr
[OCR_PER_REGION] Region 'Subtitles' → tesseract
[OCR_PER_REGION] Region 'UI Text' → easyocr
```

### Check Region Overlay:
Press "Region Overlay" button:
- All regions appear in **GREEN**
- Each shows its name and monitor
- Press ESC to close

---

## 🎮 Available OCR Engines

| Engine | Best For | Speed | Accuracy |
|--------|----------|-------|----------|
| **default** | Uses system default | - | - |
| **easyocr** | General text, multiple languages | Medium | High |
| **tesseract** | Clean text, documents | Fast | Medium-High |
| **paddleocr** | Asian languages (Chinese, Japanese, Korean) | Medium | High |
| **manga_ocr** | Manga, Japanese comics | Medium | Very High (Japanese) |
| **hybrid_ocr** | Combines multiple engines | Slow | Very High |

---

## 💡 Tips

### For Manga:
- Use `manga_ocr` for speech bubbles
- Use `easyocr` for sound effects (if mixed languages)

### For Games:
- Use `tesseract` for UI text (fast)
- Use `easyocr` for dialogue (better accuracy)

### For Videos:
- Use `tesseract` for subtitles (fast, clean text)
- Use `paddleocr` for Asian language subtitles

### For Multi-Monitor:
- Define regions on each monitor
- Assign appropriate engines per monitor
- Use "Region Overlay" to verify positions

---

## 🐛 Troubleshooting

### Regions not showing in green?
- Make sure regions are **enabled** (checkbox checked)
- Make sure you clicked **"Save Configuration"**
- Try closing and reopening the region overlay

### OCR engine not being used?
- Check logs for `[OCR_PER_REGION]` messages
- Verify plugin is enabled in settings
- Make sure you saved the configuration

### Dropdown not showing?
- Update to latest version
- Check that `ui/region_list_widget.py` was modified
- Restart the application

---

## 📚 Documentation

- **Full Testing Plan**: `PLUGIN_TESTING_PLAN.md`
- **Implementation Details**: `IMPLEMENTATION_COMPLETE_SUMMARY.md`
- **Technical Plan**: `OCR_PER_REGION_IMPLEMENTATION_PLAN.md`

---

## ✅ Ready to Test!

Everything is implemented and ready. Start by:
1. Opening the region selector
2. Adding 2-3 regions
3. Assigning different OCR engines
4. Pressing "Region Overlay" to see them in green
5. Running translation and checking the logs

Enjoy your multi-region OCR setup! 🎉
