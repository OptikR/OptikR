# Full Pipeline Test - User Guide

## What is the Full Pipeline Test?

The **Full Pipeline Test** is a comprehensive testing feature that verifies all pipeline components work together **without starting continuous capture**. It's the perfect way to verify your system is working before clicking "Start Translation".

## What It Tests

The test runs through the complete workflow:

1. **📸 Image Acquisition** - Captures a single frame or loads test image
2. **🔍 OCR Text Detection** - Detects text using your configured OCR engine
3. **🌐 Translation** - Translates detected text using your translation engine
4. **🎨 Overlay System Check** - Verifies overlay system is available

## How to Access

### Option 1: Pipeline Management Tab (Recommended)
1. Open the application
2. Go to **Pipeline** tab
3. Click **🧪 Run Full Pipeline Test** button

### Option 2: Direct Import (For Developers)
```python
from components.dialogs.full_pipeline_test_dialog import show_full_pipeline_test

show_full_pipeline_test(
    parent=main_window,
    pipeline=pipeline,
    config_manager=config_manager
)
```

## How to Use

### Step 1: Choose Test Image Source

**Option A: Capture from Screen (Default)**
- Uses your configured capture region
- Takes a single screenshot
- Best for testing real-world scenarios

**Option B: Upload Test Image**
- Click "📁 Select Image..."
- Choose a PNG, JPG, or BMP file
- Best for testing specific images

### Step 2: Run the Test

1. Click **▶️ Run Full Pipeline Test**
2. Watch the progress bar and results
3. Review detailed output for each stage

### Step 3: Interpret Results

**✓ Success** - All stages passed:
```
✓ Image acquired: (1920, 1080, 3)
✓ OCR complete: 3 text block(s) detected
✓ Translation complete: 3 translation(s)
✓ Overlay system available and ready
```

**✗ Failure** - Shows which stage failed:
```
✗ FAILED: OCR processing failed
Error: No OCR engine available
```

## What Each Stage Tests

### Stage 1: Image Acquisition
- **Tests**: Capture layer, screen capture, image loading
- **Success**: Image data acquired with valid dimensions
- **Failure**: Capture region not set, capture layer unavailable

### Stage 2: OCR Text Detection
- **Tests**: OCR layer, plugin system, current OCR engine
- **Success**: Text blocks detected (or none if image is blank)
- **Failure**: OCR layer not initialized, engine not loaded

### Stage 3: Translation
- **Tests**: Translation layer, translation engines, language pairs
- **Success**: Text translated successfully
- **Failure**: Translation layer unavailable, unsupported language pair

### Stage 4: Overlay System Check
- **Tests**: Overlay system availability
- **Success**: Overlay system found and ready
- **Failure**: Non-critical - overlay may not be needed

## Benefits

✅ **Safe Testing** - No continuous capture, no threading issues
✅ **Detailed Feedback** - See exactly which component fails
✅ **Repeatable** - Run multiple times without restarting
✅ **Pre-Start Verification** - Confirm everything works before going live
✅ **Debugging Aid** - Detailed logs help identify issues

## Troubleshooting

### "Pipeline Not Ready"
- **Cause**: Pipeline still initializing
- **Solution**: Wait for "● System Ready" in status bar

### "OCR layer not available"
- **Cause**: No OCR engine installed
- **Solution**: Install an OCR engine in OCR Engines tab

### "No text detected"
- **Cause**: Image is blank or text too small
- **Solution**: Try a different image with clear text

### "Translation layer not available"
- **Cause**: Translation system not initialized
- **Solution**: Check Translation tab settings

## Recommended Testing Workflow

Before clicking "▶ Start Translation", run these tests in order:

1. ✅ **OCR Quick Test** (OCR Engines tab)
2. ✅ **Translation Test** (Translation tab)
3. ✅ **Capture Test** (Capture tab)
4. ✅ **Full Pipeline Test** (Pipeline tab) ← **This test!**
5. ✅ **Start Translation** (Main toolbar)

If the Full Pipeline Test passes, you have **~95% confidence** the system will work!

## Example Output

```
======================================================================
🧪 FULL PIPELINE TEST - Starting...
======================================================================

📸 Stage 1/4: Image Acquisition
  Capturing region: (0, 0) 1920x1080 on monitor 0
  Captured frame: (1080, 1920, 3)
✓ Image acquired: (1080, 1920, 3)

🔍 Stage 2/4: OCR Text Detection
  Using OCR engine: easyocr
  Processing time: 1234.56 ms
✓ OCR complete: 3 text block(s) detected
  Block 1: "Hello World" (confidence: 0.95)
  Block 2: "Test Text" (confidence: 0.89)
  Block 3: "Sample" (confidence: 0.92)

🌐 Stage 3/4: Translation
  Translating: en → es
  Processing time: 234.56 ms
✓ Translation complete: 3 translation(s)
  Translation 1:
    Original:   "Hello World"
    Translated: "Hola Mundo"
  Translation 2:
    Original:   "Test Text"
    Translated: "Texto de Prueba"
  Translation 3:
    Original:   "Sample"
    Translated: "Muestra"

🎨 Stage 4/4: Overlay System Check
✓ Overlay system available and ready

======================================================================
✓ FULL PIPELINE TEST PASSED!
======================================================================

Summary:
  • Image Acquisition: ✓ Success
  • OCR Detection: ✓ 3 blocks detected
  • Translation: ✓ 3 translations
  • Overlay System: ✓ Available

🎉 All pipeline components are working correctly!
You can now safely use the 'Start Translation' feature.
```

## Technical Details

### What It Does NOT Test
- Continuous capture loop (only single frame)
- Threading/concurrency under load
- Performance over time
- Memory management during sustained operation

These are only tested when you click "Start Translation".

### Integration with Existing Tests
- Complements individual component tests (OCR Test, Translation Test, Capture Test)
- Provides integration testing without full system activation
- Safe to run repeatedly without side effects

## For Developers

### Adding Custom Test Stages

Edit `dev/components/dialogs/full_pipeline_test_dialog.py`:

```python
def _execute_test(self):
    # Add your custom stage here
    self._log("🔧 Stage X/Y: Custom Test")
    success, result = self._test_custom_component()
    if not success:
        self._log("✗ FAILED: Custom test failed")
        return
    self._log("✓ Custom test passed")
```

### Accessing Test Results Programmatically

```python
dialog = FullPipelineTestDialog(parent, pipeline, config_manager)
result = dialog.exec()
# Check dialog.results_text for output
```

## Version History

- **v1.0** (2024-11-15) - Initial implementation
  - Full pipeline testing (Capture → OCR → Translation → Overlay)
  - Support for screen capture and image upload
  - Detailed stage-by-stage reporting
  - Integration with Pipeline Management Tab
