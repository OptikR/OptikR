# Plugin Quick Start Guide

**Create a new optimizer plugin in 5 minutes!**

---

## Quick Steps

### 1. Create Directory
```bash
mkdir plugins/optimizers/my_plugin
```

### 2. Create plugin.json
```json
{
  "name": "my_plugin",
  "display_name": "My Plugin",
  "version": "1.0.0",
  "type": "optimizer",
  "target_stage": "translation",
  "stage": "pre",
  "description": "What it does",
  "author": "Your Name",
  "enabled": true,
  "settings": {
    "threshold": {
      "type": "float",
      "default": 0.5,
      "min": 0.0,
      "max": 1.0
    }
  }
}
```

### 3. Create optimizer.py
```python
"""My Plugin"""

class MyOptimizer:
    def __init__(self, config):
        self.threshold = config.get('threshold', 0.5)
        self.count = 0
    
    def process(self, data):
        self.count += 1
        # Your logic here
        return data
    
    def get_stats(self):
        return {'processed': self.count}

def initialize(config):
    return MyOptimizer(config)
```

### 4. Create README.md
```markdown
# My Plugin

What it does and why it's useful.

## Settings
- threshold: Controls sensitivity (0.0-1.0)

## Performance
- Benefit: What improvement to expect
```

### 5. Test It
```python
python dev/run.py
# Check console for: "Loaded optimizer plugin: My Plugin"
```

---

## Plugin Template

Copy this template to get started quickly:

**plugins/optimizers/template/plugin.json:**
```json
{
  "name": "template",
  "display_name": "Template Plugin",
  "version": "1.0.0",
  "type": "optimizer",
  "target_stage": "translation",
  "stage": "pre",
  "description": "Template for new plugins",
  "author": "Your Name",
  "enabled": false,
  "settings": {}
}
```

**plugins/optimizers/template/optimizer.py:**
```python
"""Template Plugin"""

from typing import Dict, Any

class TemplateOptimizer:
    def __init__(self, config: Dict[str, Any]):
        self.config = config
        self.processed = 0
    
    def process(self, data: Dict[str, Any]) -> Dict[str, Any]:
        self.processed += 1
        # TODO: Add your optimization logic here
        return data
    
    def get_stats(self) -> Dict[str, Any]:
        return {'processed': self.processed}

def initialize(config: Dict[str, Any]) -> TemplateOptimizer:
    return TemplateOptimizer(config)
```

---

## Common Patterns

### Skip Processing
```python
def process(self, data):
    if should_skip(data):
        data['skip_processing'] = True
    return data
```

### Modify Data
```python
def process(self, data):
    data['optimized'] = True
    data['value'] = data['value'] * 2
    return data
```

### Track Statistics
```python
def __init__(self, config):
    self.hits = 0
    self.misses = 0

def process(self, data):
    if condition:
        self.hits += 1
    else:
        self.misses += 1
    return data

def get_stats(self):
    return {
        'hits': self.hits,
        'misses': self.misses,
        'hit_rate': f"{self.hits/(self.hits+self.misses)*100:.1f}%"
    }
```

---

## Target Stages

- **capture**: Screen capture
- **ocr**: Text recognition
- **translation**: Translation
- **pipeline**: Entire pipeline

## Stage Types

- **pre**: Before stage execution
- **post**: After stage execution
- **global**: Pipeline-level

---

## Testing

### 1. Check Loading
```bash
python dev/run.py
# Look for: "Loaded optimizer plugin: [Your Plugin]"
```

### 2. Check Processing
```python
# Add print statements in process()
def process(self, data):
    print(f"[MY_PLUGIN] Processing: {data}")
    return data
```

### 3. Check Statistics
```python
# Pipeline will log stats on stop
# Look for: "My Plugin: {'processed': 100}"
```

---

## Common Issues

### Plugin Not Loading
- Check `plugin.json` is valid JSON
- Check `enabled: true`
- Check `initialize()` function exists

### Plugin Not Working
- Check `process()` method exists
- Check method returns data
- Check for exceptions in console

### Settings Not Applying
- Restart translation after changes
- Check config is passed to `__init__()`

---

## Examples

See existing plugins for examples:
- `plugins/optimizers/translation_cache/` - Caching
- `plugins/optimizers/frame_skip/` - Frame comparison
- `plugins/optimizers/batch_processing/` - Batching

---

## Full Documentation

See `HOW_TO_ADD_PLUGINS.md` for complete guide.

---

**That's it!** Your plugin will be automatically loaded and used by the pipeline. 🚀
