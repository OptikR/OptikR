# Translation Engine Setup with Translation Chain

**How to use different translation engines with the translation chain plugin**

---

## Quick Answer

**No, the translation_chain plugin does NOT handle translation engines directly.**

The plugin uses whatever translation engine is currently selected in OptikR settings.

---

## How It Works

### Current System

```
OptikR Settings:
├─ Translation Engine: MarianMT (selected)
└─ Translation Chain Plugin: Enabled

Result:
├─ All translations use MarianMT
├─ Chain: ja→en (MarianMT) → en→de (MarianMT)
└─ Same engine for all steps
```

### Translation Chain Flow

```python
# In translation_chain plugin
def post_process(self, data):
    # Uses the translation_layer passed from pipeline
    translation_layer = data.get('translation_layer')  # This is MarianMT
    
    # Step 1: ja→en
    english = translation_layer.translate(japanese_text, 'ja', 'en')
    
    # Step 2: en→de  
    german = translation_layer.translate(english, 'en', 'de')
```

**Key Point:** Plugin uses the same engine for all steps!

---

## Using Different Engines Per Step

### Option 1: Modify Plugin (Advanced)

**Add engine selection to plugin.json:**

```json
{
  "settings": {
    "engine_per_step": {
      "type": "object",
      "default": {
        "ja->en": "easyocr",
        "en->de": "marianmt",
        "zh->en": "paddleocr"
      },
      "description": "Translation engine per language pair"
    }
  }
}
```

**Modify optimizer.py:**

```python
class TranslationChainOptimizer:
    def __init__(self, config):
        self.engine_per_step = config.get('engine_per_step', {})
    
    def post_process(self, data):
        for i in range(len(chain_languages) - 1):
            source = chain_languages[i]
            target = chain_languages[i + 1]
            
            # Get specific engine for this step
            step_key = f"{source}->{target}"
            engine_name = self.engine_per_step.get(step_key, 'default')
            
            # Load specific engine
            if engine_name != 'default':
                engine = self._load_translation_engine(engine_name)
                translated = engine.translate(current_text, source, target)
            else:
                # Use default engine
                translated = translation_layer.translate(current_text, source, target)
```

### Option 2: Multiple Translation Layers (Recommended)

**Create enhanced translation layer:**

```python
# In src/translation/multi_engine_layer.py
class MultiEngineTranslationLayer:
    def __init__(self):
        self.engines = {
            'marianmt': MarianMTEngine(),
            'google': GoogleTranslateEngine(),
            'azure': AzureTranslateEngine()
        }
        self.engine_mapping = {
            'ja->en': 'marianmt',  # Best for Japanese
            'en->de': 'google',    # Best for German
            'zh->en': 'marianmt',  # Best for Chinese
        }
    
    def translate(self, text, source_lang, target_lang):
        # Select best engine for this language pair
        pair_key = f"{source_lang}->{target_lang}"
        engine_name = self.engine_mapping.get(pair_key, 'marianmt')
        
        engine = self.engines[engine_name]
        return engine.translate(text, source_lang, target_lang)
```

**Use in pipeline:**

```python
# In startup_pipeline.py
self.translation_layer = MultiEngineTranslationLayer()
```

**Result:** Automatic engine selection per language pair!

---

## Recommended Setup

### For Best Quality

**Engine Selection by Language Pair:**

```python
engine_mapping = {
    # Japanese pairs
    'ja->en': 'easyocr',      # Good Japanese support
    'ja->de': 'marianmt',     # General purpose
    
    # English pairs  
    'en->de': 'google',       # Excellent English→German
    'en->fr': 'google',       # Excellent English→French
    'en->es': 'google',       # Excellent English→Spanish
    
    # Chinese pairs
    'zh->en': 'baidu',        # Best for Chinese
    'zh->ja': 'marianmt',     # Good cross-Asian
    
    # Default
    'default': 'marianmt'     # Fallback
}
```

### Configuration Example

**For Japanese→German chain:**

```json
{
  "chain_pairs": {
    "ja->de": "ja->en->de"
  },
  "engine_mapping": {
    "ja->en": "easyocr",     // Best for Japanese
    "en->de": "google"       // Best for German
  }
}
```

**Result:**
```
Japanese: "こんにちは世界"
    ↓ (EasyOCR: ja→en)
English: "Hello World"
    ↓ (Google: en→de)
German: "Hallo Welt"
```

---

## Implementation Guide

### Step 1: Create Multi-Engine Layer

**File:** `src/translation/multi_engine_layer.py`

```python
from typing import Dict, Any
from .translation_engine_interface import ITranslationEngine

class MultiEngineTranslationLayer:
    def __init__(self, config_manager=None):
        self.config_manager = config_manager
        self.engines = {}
        self.engine_mapping = {}
        
        # Load engines
        self._load_engines()
        self._load_mapping()
    
    def _load_engines(self):
        """Load available translation engines."""
        # Load MarianMT
        try:
            from .marianmt_engine import MarianMTEngine
            self.engines['marianmt'] = MarianMTEngine()
        except ImportError:
            pass
        
        # Load Google Translate (if API key available)
        try:
            from .google_translate_engine import GoogleTranslateEngine
            api_key = self.config_manager.get_setting('translation.google_api_key')
            if api_key:
                self.engines['google'] = GoogleTranslateEngine(api_key)
        except ImportError:
            pass
        
        # Add more engines as needed
    
    def _load_mapping(self):
        """Load engine mapping from config."""
        if self.config_manager:
            self.engine_mapping = self.config_manager.get_setting(
                'translation.engine_mapping', 
                {
                    'ja->en': 'marianmt',
                    'en->de': 'marianmt',
                    'default': 'marianmt'
                }
            )
    
    def translate(self, text: str, source_lang: str, target_lang: str) -> str:
        """Translate using best engine for language pair."""
        # Select engine
        pair_key = f"{source_lang}->{target_lang}"
        engine_name = self.engine_mapping.get(pair_key, 
                     self.engine_mapping.get('default', 'marianmt'))
        
        # Get engine
        engine = self.engines.get(engine_name)
        if not engine:
            # Fallback to first available engine
            engine = next(iter(self.engines.values()))
        
        # Translate
        return engine.translate(text, source_lang, target_lang)
```

### Step 2: Update Configuration

**File:** `config/system_config.json`

```json
{
  "translation": {
    "engine": "multi_engine",
    "engine_mapping": {
      "ja->en": "marianmt",
      "en->de": "marianmt",
      "zh->en": "marianmt",
      "default": "marianmt"
    },
    "google_api_key": "your_api_key_here",
    "azure_api_key": "your_api_key_here"
  }
}
```

### Step 3: Update Startup Pipeline

**File:** `src/workflow/startup_pipeline.py`

```python
def _create_translation_layer(self):
    """Create translation layer."""
    engine_type = self.config_manager.get_setting('translation.engine', 'marianmt')
    
    if engine_type == 'multi_engine':
        from src.translation.multi_engine_layer import MultiEngineTranslationLayer
        return MultiEngineTranslationLayer(self.config_manager)
    else:
        # Single engine (existing code)
        return self._create_single_engine_layer(engine_type)
```

### Step 4: Test

**Test different engines:**

```python
# Test multi-engine layer
layer = MultiEngineTranslationLayer(config_manager)

# Should use different engines
result1 = layer.translate("こんにちは", "ja", "en")  # Uses MarianMT
result2 = layer.translate("Hello", "en", "de")      # Uses Google (if configured)

print(f"ja->en: {result1}")
print(f"en->de: {result2}")
```

---

## UI Integration

### Settings Tab Enhancement

**Add to Translation Settings:**

```python
# In translation_tab_pyqt6.py
def _create_engine_mapping_section(self):
    """Create engine mapping section."""
    group = QGroupBox("🔧 Engine Mapping")
    layout = QFormLayout(group)
    
    # Japanese pairs
    self.ja_en_engine = QComboBox()
    self.ja_en_engine.addItems(["MarianMT", "Google", "Azure"])
    layout.addRow("Japanese → English:", self.ja_en_engine)
    
    # English pairs
    self.en_de_engine = QComboBox()
    self.en_de_engine.addItems(["MarianMT", "Google", "Azure"])
    layout.addRow("English → German:", self.en_de_engine)
    
    # Add more pairs as needed
    
    return group
```

### Pipeline Management Display

**Show active engines:**

```
┌─────────────────────────────────────────────────────┐
│ 🌐 TRANSLATION STAGE                                │
├─────────────────────────────────────────────────────┤
│                                                     │
│ Engine Mapping:                                     │
│ • Japanese → English: MarianMT                     │
│ • English → German: Google Translate               │
│ • Chinese → English: MarianMT                      │
│ • Default: MarianMT                                 │
│                                                     │
│ 🔗 Translation Chain              [✅ Enabled]     │
│ Multi-language chaining with engine selection      │
│                                                     │
│ Chain: ja→en (MarianMT) → en→de (Google)           │
│                                                     │
│ Stats: 50 chains, 30 different engines used        │
└─────────────────────────────────────────────────────┘
```

---

## Summary

### Current Limitation

❌ **Translation chain uses same engine for all steps**

### Solutions

✅ **Option 1:** Modify translation_chain plugin (complex)
✅ **Option 2:** Create MultiEngineTranslationLayer (recommended)

### Recommended Approach

1. **Create MultiEngineTranslationLayer**
2. **Configure engine mapping per language pair**
3. **Translation chain automatically uses best engine per step**
4. **Add UI for engine mapping configuration**

### Result

```
Japanese: "こんにちは世界"
    ↓ (Best engine for ja→en)
English: "Hello World"
    ↓ (Best engine for en→de)
German: "Hallo Welt"

Both steps use optimal engines! 🚀
```

### Configuration

```json
{
  "translation": {
    "engine": "multi_engine",
    "engine_mapping": {
      "ja->en": "marianmt",
      "en->de": "google",
      "zh->en": "baidu"
    }
  }
}
```

**This gives you the best of both worlds: translation chaining + optimal engines per step!** ✅
