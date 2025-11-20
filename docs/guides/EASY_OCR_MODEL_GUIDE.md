# E
asy OCR Model Addition Guide

**Add your own OCR models without code changes**

---

## Overview

OptikR's OCR plugin system makes it easy to:
- ✅ Download new OCR models
- ✅ Create custom OCR engines
- ✅ Add without modifying core code
- ✅ Switch between models easily

---

## Quick Start: Add New OCR Engine

### Step 1: Create Plugin Directory

```bash
mkdir src/ocr/engines/my_ocr
```

### Step 2: Create plugin.json

```json
{
  "name": "my_ocr",
  "version": "1.0.0",
  "description": "My custom OCR engine",
  "author": "Your Name",
  "engine_type": "my_ocr",
  "entry_point": "__init__.py",
  "supported_platforms": ["windows", "linux", "macos"],
  "dependencies": ["your-ocr-library"],
  "config_schema": {
    "model_path": {
      "type": "string",
      "default": "models/my_ocr",
      "description": "Path to OCR model files"
    },
    "language": {
      "type": "string",
      "default": "en",
      "description": "OCR language"
    },
    "confidence_threshold": {
      "type": "float",
      "default": 0.5,
      "description": "Minimum confidence score"
    }
  }
}
```

### Step 3: Create __init__.py

```python
"""My Custom OCR Engine"""

from typing import List, Dict, Any
import sys
import os

# Add parent directory to path
sys.path.append(os.path.join(os.path.dirname(__file__), '../..'))

try:
    from src.models import TextBlock, Rectangle
    from src.ocr.ocr_engine_interface import IOCREngine
except ImportError:
    from models import TextBlock, Rectangle
    from ocr_engine_interface import IOCREngine


class MyOCREngine(IOCREngine):
    """Custom OCR engine implementation."""
    
    def __init__(self, config: Dict[str, Any]):
        """Initialize OCR engine with config."""
        self.config = config
        self.model_path = config.get('model_path', 'models/my_ocr')
        self.language = config.get('language', 'en')
        self.confidence_threshold = config.get('confidence_threshold', 0.5)
        
        # Load your model here
        self.model = self._load_model()
        
        print(f"[MY_OCR] Initialized with language: {self.language}")
    
    def _load_model(self):
        """Load OCR model from disk."""
        # Your model loading code here
        # Example:
        # return YourOCRLibrary.load(self.model_path)
        pass
    
    def extract_text(self, image, language: str = None) -> List[TextBlock]:
        """
        Extract text from image.
        
        Args:
            image: PIL Image or numpy array
            language: Language code (optional, uses config if not provided)
            
        Returns:
            List of TextBlock objects with text and positions
        """
        if language is None:
            language = self.language
        
        # Your OCR logic here
        # Example:
        # results = self.model.detect_text(image, language)
        
        # Convert to TextBlock format
        text_blocks = []
        
        # Example conversion:
        # for result in results:
        #     text = result['text']
        #     bbox = result['bbox']  # [x, y, width, height]
        #     confidence = result['confidence']
        #     
        #     if confidence >= self.confidence_threshold:
        #         rectangle = Rectangle(
        #             x=bbox[0],
        #             y=bbox[1],
        #             width=bbox[2],
        #             height=bbox[3]
        #         )
        #         
        #         text_block = TextBlock(
        #             text=text,
        #             bbox=rectangle,
        #             confidence=confidence,
        #             language=language
        #         )
        #         
        #         text_blocks.append(text_block)
        
        return text_blocks
    
    def get_supported_languages(self) -> List[str]:
        """Get list of supported language codes."""
        # Return languages your model supports
        return ['en', 'ja', 'zh', 'ko', 'de', 'fr', 'es']
    
    def get_engine_info(self) -> Dict[str, Any]:
        """Get engine information."""
        return {
            'name': 'My OCR Engine',
            'version': '1.0.0',
            'type': 'my_ocr',
            'languages': self.get_supported_languages(),
            'model_path': self.model_path
        }
    
    def cleanup(self):
        """Clean up resources."""
        # Release model, free memory, etc.
        if hasattr(self, 'model') and self.model:
            del self.model
        print("[MY_OCR] Cleaned up")


# Plugin interface - REQUIRED
def create_engine(config: Dict[str, Any]) -> MyOCREngine:
    """
    Create OCR engine instance.
    
    This function is called by the OCR plugin manager.
    
    Args:
        config: Configuration dictionary from plugin.json
        
    Returns:
        Initialized OCR engine instance
    """
    return MyOCREngine(config)
```

### Step 4: Test Your Engine

```python
# test_my_ocr.py
from PIL import Image
from src.ocr.engines.my_ocr import create_engine

# Create engine
config = {
    'model_path': 'models/my_ocr',
    'language': 'en',
    'confidence_threshold': 0.5
}

engine = create_engine(config)

# Test with image
image = Image.open('test_image.png')
text_blocks = engine.extract_text(image, 'en')

# Print results
for block in text_blocks:
    print(f"Text: {block.text}")
    print(f"Position: ({block.bbox.x}, {block.bbox.y})")
    print(f"Confidence: {block.confidence}")
    print("---")
```

### Step 5: Use in Application

1. **Restart application**
2. **Go to Settings → OCR**
3. **Select "My OCR" from engine list**
4. **Save settings**
5. **Start translation**

Done! Your OCR engine is now integrated! 🎉

---

## Examples

### Example 1: Tesseract with Custom Model

```python
class TesseractCustomEngine(IOCREngine):
    def __init__(self, config):
        import pytesseract
        self.tesseract = pytesseract
        
        # Set custom model path
        custom_model = config.get('model_path')
        if custom_model:
            self.tesseract.pytesseract.tesseract_cmd = custom_model
    
    def extract_text(self, image, language):
        # Use custom Tesseract model
        data = self.tesseract.image_to_data(
            image,
            lang=language,
            output_type=pytesseract.Output.DICT
        )
        
        return self._convert_to_text_blocks(data)
```

### Example 2: Downloaded Model (ONNX)

```python
class ONNXOCREngine(IOCREngine):
    def __init__(self, config):
        import onnxruntime as ort
        
        model_path = config.get('model_path', 'models/ocr_model.onnx')
        self.session = ort.InferenceSession(model_path)
    
    def extract_text(self, image, language):
        # Preprocess image
        input_data = self._preprocess(image)
        
        # Run inference
        outputs = self.session.run(None, {'input': input_data})
        
        # Post-process results
        return self._postprocess(outputs)
```

### Example 3: Cloud API (Google Vision)

```python
class GoogleVisionEngine(IOCREngine):
    def __init__(self, config):
        from google.cloud import vision
        
        self.client = vision.ImageAnnotatorClient()
        self.api_key = config.get('api_key')
    
    def extract_text(self, image, language):
        # Convert to bytes
        image_bytes = self._image_to_bytes(image)
        
        # Call API
        response = self.client.text_detection(
            image={'content': image_bytes}
        )
        
        # Convert response
        return self._convert_response(response)
```

---

## Model Download Integration

### Auto-Download Models

```python
class MyOCREngine(IOCREngine):
    def __init__(self, config):
        self.model_path = config.get('model_path')
        
        # Check if model exists
        if not os.path.exists(self.model_path):
            print(f"[MY_OCR] Model not found, downloading...")
            self._download_model()
        
        self.model = self._load_model()
    
    def _download_model(self):
        """Download model from URL."""
        import urllib.request
        
        model_url = "https://example.com/ocr_model.bin"
        os.makedirs(os.path.dirname(self.model_path), exist_ok=True)
        
        print(f"[MY_OCR] Downloading from {model_url}...")
        urllib.request.urlretrieve(model_url, self.model_path)
        print(f"[MY_OCR] Downloaded to {self.model_path}")
```

### Hugging Face Integration

```python
class HuggingFaceOCREngine(IOCREngine):
    def __init__(self, config):
        from transformers import TrOCRProcessor, VisionEncoderDecoderModel
        
        model_name = config.get('model_name', 'microsoft/trocr-base-printed')
        
        # Auto-download from Hugging Face
        self.processor = TrOCRProcessor.from_pretrained(model_name)
        self.model = VisionEncoderDecoderModel.from_pretrained(model_name)
        
        print(f"[HF_OCR] Loaded model: {model_name}")
    
    def extract_text(self, image, language):
        # Process with Hugging Face model
        pixel_values = self.processor(image, return_tensors="pt").pixel_values
        generated_ids = self.model.generate(pixel_values)
        text = self.processor.batch_decode(generated_ids, skip_special_tokens=True)[0]
        
        # Create TextBlock
        return [TextBlock(text=text, bbox=Rectangle(0, 0, 100, 20), confidence=1.0)]
```

---

## UI Integration

### Automatic Discovery

Your OCR engine will automatically appear in:

**1. OCR Settings Tab**
```
OCR Engine Selection:
○ EasyOCR
○ Tesseract
○ PaddleOCR
● My OCR  ← Your engine!
```

**2. Pipeline Management Tab**
```
Current Engine: My OCR (English) ⭐
```

**3. Quick OCR Switch Dialog**
```
Available Engines:
- EasyOCR
- Tesseract
- My OCR  ← Your engine!
```

### Model Manager Integration

Add model management UI:

```python
# In plugin.json
{
  "model_management": {
    "supports_download": true,
    "download_url": "https://example.com/models",
    "model_list_url": "https://example.com/models/list.json",
    "supports_custom_models": true
  }
}
```

---

## Advanced Features

### Multi-Model Support

Support multiple models in one engine:

```python
class MultiModelOCREngine(IOCREngine):
    def __init__(self, config):
        self.models = {}
        
        # Load different models for different languages
        self.models['en'] = self._load_model('models/english.bin')
        self.models['ja'] = self._load_model('models/japanese.bin')
        self.models['zh'] = self._load_model('models/chinese.bin')
    
    def extract_text(self, image, language):
        # Use appropriate model for language
        model = self.models.get(language, self.models['en'])
        return model.detect_text(image)
```

### GPU Acceleration

```python
class GPUOCREngine(IOCREngine):
    def __init__(self, config):
        import torch
        
        self.device = 'cuda' if torch.cuda.is_available() else 'cpu'
        self.model = self._load_model().to(self.device)
        
        print(f"[GPU_OCR] Using device: {self.device}")
    
    def extract_text(self, image, language):
        # Process on GPU
        with torch.no_grad():
            results = self.model(image)
        return self._convert_results(results)
```

### Batch Processing

```python
class BatchOCREngine(IOCREngine):
    def extract_text_batch(self, images: List, language: str) -> List[List[TextBlock]]:
        """Process multiple images at once."""
        # Batch processing for efficiency
        batch_results = self.model.process_batch(images, language)
        
        return [self._convert_to_text_blocks(r) for r in batch_results]
```

---

## Best Practices

### ✅ Do

1. **Implement full interface**
   - `extract_text()`
   - `get_supported_languages()`
   - `get_engine_info()`
   - `cleanup()`

2. **Handle errors gracefully**
   ```python
   try:
       results = self.model.detect(image)
   except Exception as e:
       print(f"[ERROR] OCR failed: {e}")
       return []  # Return empty list
   ```

3. **Provide accurate confidence scores**
   ```python
   confidence = result.get('confidence', 0.0)
   if confidence < self.confidence_threshold:
       continue  # Skip low confidence results
   ```

4. **Clean up resources**
   ```python
   def cleanup(self):
       if self.model:
           del self.model
       torch.cuda.empty_cache()  # Free GPU memory
   ```

5. **Support multiple languages**
   ```python
   def get_supported_languages(self):
       return ['en', 'ja', 'zh', 'ko', 'de', 'fr', 'es']
   ```

### ❌ Don't

1. **Don't modify core code**
   - Keep everything in your plugin directory

2. **Don't assume GPU availability**
   ```python
   # Bad
   self.model.to('cuda')
   
   # Good
   device = 'cuda' if torch.cuda.is_available() else 'cpu'
   self.model.to(device)
   ```

3. **Don't block the UI**
   - OCR runs in background thread
   - Don't use blocking operations

4. **Don't keep models loaded when not selected**
   - Only your selected engine loads
   - Others remain unloaded

---

## Troubleshooting

### Plugin Not Appearing

**Check:**
1. Directory structure correct
2. `plugin.json` exists and valid
3. `__init__.py` exists
4. `create_engine()` function defined

### Model Not Loading

**Check:**
1. Model path correct
2. Model files exist
3. Dependencies installed
4. Check console for errors

### Poor Performance

**Optimize:**
1. Use GPU if available
2. Implement batch processing
3. Cache model in memory
4. Reduce image size before processing

---

## Conclusion

✅ **Easy to add** - Just 3 files
✅ **No code changes** - Plugin system handles everything
✅ **Automatic discovery** - Appears in UI automatically
✅ **Flexible** - Support any OCR library or model
✅ **Downloadable** - Auto-download models
✅ **Switchable** - Easy to switch between engines

Add your own OCR models without touching core code! 🚀
