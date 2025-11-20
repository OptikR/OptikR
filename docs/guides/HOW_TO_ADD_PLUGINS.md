# How to Add New Optimizer Plugins

**Complete guide for creating and integrating new optimizer plugins**

---

## Plugin Structure

Every optimizer plugin consists of 3 files in `plugins/optimizers/[plugin_name]/`:

```
plugins/optimizers/my_new_plugin/
├── plugin.json          # Metadata and settings
├── optimizer.py         # Implementation
└── README.md            # Documentation
```

---

## Step-by-Step Guide

### Step 1: Create Plugin Directory

```bash
mkdir plugins/optimizers/my_new_plugin
```

### Step 2: Create plugin.json

**File:** `plugins/optimizers/my_new_plugin/plugin.json`

```json
{
  "name": "my_new_plugin",
  "display_name": "My New Optimizer",
  "version": "1.0.0",
  "type": "optimizer",
  "target_stage": "translation",
  "stage": "pre",
  "description": "Brief description of what this optimizer does",
  "author": "Your Name",
  "enabled": true,
  "settings": {
    "setting_name": {
      "type": "int",
      "default": 100,
      "min": 10,
      "max": 1000,
      "description": "Description of this setting"
    },
    "another_setting": {
      "type": "float",
      "default": 0.5,
      "min": 0.0,
      "max": 1.0,
      "description": "Another setting description"
    },
    "enable_feature": {
      "type": "bool",
      "default": true,
      "description": "Enable/disable a feature"
    },
    "mode": {
      "type": "string",
      "default": "auto",
      "options": ["auto", "manual", "advanced"],
      "description": "Operation mode"
    }
  },
  "performance": {
    "benefit": "Expected performance improvement",
    "overhead": "Expected overhead",
    "memory": "Memory usage"
  }
}
```

**Field Descriptions:**

- **name**: Unique identifier (lowercase, underscores)
- **display_name**: Human-readable name
- **type**: Always "optimizer"
- **target_stage**: Which stage to optimize (capture, ocr, translation, pipeline)
- **stage**: When to run (pre, post, global)
- **enabled**: Default enabled state
- **settings**: Configurable parameters

**Setting Types:**
- `int`: Integer with min/max range
- `float`: Floating point with min/max range
- `bool`: True/false toggle
- `string`: Text with optional predefined options

### Step 3: Create optimizer.py

**File:** `plugins/optimizers/my_new_plugin/optimizer.py`

```python
"""
My New Optimizer Plugin
Brief description of what it does
"""

from typing import Dict, Any


class MyNewOptimizer:
    """
    Optimizer class that implements the optimization logic.
    """
    
    def __init__(self, config: Dict[str, Any]):
        """
        Initialize the optimizer with configuration.
        
        Args:
            config: Dictionary with settings from plugin.json
        """
        self.config = config
        
        # Load settings
        self.setting_name = config.get('setting_name', 100)
        self.another_setting = config.get('another_setting', 0.5)
        self.enable_feature = config.get('enable_feature', True)
        self.mode = config.get('mode', 'auto')
        
        # Initialize state
        self.total_processed = 0
        self.optimizations_applied = 0
        
        print(f"[MY_NEW_PLUGIN] Initialized with setting_name={self.setting_name}")
    
    def process(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Process data through the optimizer.
        
        This is the main method called by the pipeline.
        
        Args:
            data: Input data dictionary
            
        Returns:
            Modified data dictionary
        """
        self.total_processed += 1
        
        # Your optimization logic here
        if self.enable_feature:
            # Apply optimization
            data = self._apply_optimization(data)
            self.optimizations_applied += 1
        
        return data
    
    def _apply_optimization(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Apply the actual optimization logic.
        
        Args:
            data: Input data
            
        Returns:
            Optimized data
        """
        # Example: Modify data based on settings
        if self.mode == 'auto':
            # Automatic optimization
            pass
        elif self.mode == 'manual':
            # Manual optimization
            pass
        
        return data
    
    def get_stats(self) -> Dict[str, Any]:
        """
        Get optimizer statistics.
        
        Returns:
            Dictionary with statistics
        """
        optimization_rate = (self.optimizations_applied / self.total_processed * 100) if self.total_processed > 0 else 0
        
        return {
            'total_processed': self.total_processed,
            'optimizations_applied': self.optimizations_applied,
            'optimization_rate': f"{optimization_rate:.1f}%"
        }
    
    def reset(self):
        """Reset optimizer state."""
        self.total_processed = 0
        self.optimizations_applied = 0


# Plugin interface - REQUIRED
def initialize(config: Dict[str, Any]) -> MyNewOptimizer:
    """
    Initialize the optimizer plugin.
    
    This function is called by the plugin loader.
    
    Args:
        config: Configuration dictionary from plugin.json
        
    Returns:
        Initialized optimizer instance
    """
    return MyNewOptimizer(config)
```

**Key Points:**

1. **Class name** can be anything, but should be descriptive
2. **`__init__()`** receives config from plugin.json
3. **`process()`** is the main method called by pipeline
4. **`get_stats()`** returns statistics (optional but recommended)
5. **`initialize()`** function is REQUIRED - this is the plugin entry point

### Step 4: Create README.md

**File:** `plugins/optimizers/my_new_plugin/README.md`

```markdown
# My New Optimizer

Brief description of what this optimizer does.

## Benefits

- Benefit 1
- Benefit 2
- Benefit 3

## How It Works

Explain the optimization technique:
1. Step 1
2. Step 2
3. Step 3

## Configuration

```json
{
  "setting_name": 100,
  "another_setting": 0.5,
  "enable_feature": true,
  "mode": "auto"
}
```

### Settings

- **setting_name**: Description (range: 10-1000)
- **another_setting**: Description (range: 0.0-1.0)
- **enable_feature**: Enable/disable feature
- **mode**: Operation mode (auto, manual, advanced)

## Use Cases

- Use case 1
- Use case 2
- Use case 3

## Performance

- **Benefit**: Expected improvement
- **Overhead**: Expected overhead
- **Memory**: Memory usage

## Statistics

The optimizer tracks:
- Total items processed
- Optimizations applied
- Optimization rate
```

---

## Integration Points

### Where Plugins Run

Plugins can run at different stages:

**1. Pre-processing (stage: "pre")**
- Runs BEFORE the target stage
- Can modify input data
- Can skip processing

**2. Post-processing (stage: "post")**
- Runs AFTER the target stage
- Can modify output data
- Can store results

**3. Global (stage: "global")**
- Runs at pipeline level
- Can affect entire pipeline
- Used for cross-stage optimizations

### Target Stages

**capture**: Screen capture stage
- Pre: Modify capture settings
- Post: Process captured frame

**ocr**: Text recognition stage
- Pre: Preprocess image
- Post: Validate/filter text

**translation**: Translation stage
- Pre: Cache lookup, batch formation
- Post: Store results, validation

**pipeline**: Entire pipeline
- Global: Async execution, scheduling

---

## Adding Plugin to UI

To add your plugin to the Pipeline Management UI:

**File:** `dev/components/settings/pipeline_management_tab_pyqt6.py`

Add a new group in `_create_plugins_tab()` method:

```python
# Plugin X: My New Plugin
my_plugin_group = QGroupBox("🎨 My New Optimizer")
my_plugin_layout = QFormLayout(my_plugin_group)

self.my_plugin_enabled = QCheckBox("Enabled")
self.my_plugin_enabled.setChecked(False)
my_plugin_layout.addRow("Status:", self.my_plugin_enabled)

my_plugin_desc = QLabel("Brief description of what it does")
my_plugin_desc.setWordWrap(True)
my_plugin_desc.setStyleSheet("color: #666666; font-size: 8pt;")
my_plugin_layout.addRow("", my_plugin_desc)

# Add settings controls
self.my_setting_spin = QSpinBox()
self.my_setting_spin.setRange(10, 1000)
self.my_setting_spin.setValue(100)
my_plugin_layout.addRow("Setting Name:", self.my_setting_spin)

layout.addWidget(my_plugin_group)
```

Then update `_apply_plugin_settings()` method:

```python
# My New Plugin
my_plugin_json = plugins_dir / "my_new_plugin" / "plugin.json"
if my_plugin_json.exists():
    with open(my_plugin_json, 'r') as f:
        my_config = json.load(f)
    my_config['enabled'] = self.my_plugin_enabled.isChecked()
    my_config['settings']['setting_name']['default'] = self.my_setting_spin.value()
    with open(my_plugin_json, 'w') as f:
        json.dump(my_config, f, indent=2)
```

---

## Testing Your Plugin

### 1. Test Plugin Loading

```python
from src.workflow.runtime_pipeline_optimized import OptimizerPluginLoader

loader = OptimizerPluginLoader("plugins/optimizers")
plugins = loader.load_plugins()

if 'my_new_plugin' in plugins:
    print("✓ Plugin loaded successfully")
    optimizer = plugins['my_new_plugin']['optimizer']
    print(f"Config: {plugins['my_new_plugin']['config']}")
else:
    print("✗ Plugin not found")
```

### 2. Test Plugin Functionality

```python
# Initialize plugin
from plugins.optimizers.my_new_plugin.optimizer import initialize

config = {
    'setting_name': 100,
    'another_setting': 0.5,
    'enable_feature': True,
    'mode': 'auto'
}

optimizer = initialize(config)

# Test processing
test_data = {'text': 'Hello World'}
result = optimizer.process(test_data)
print(f"Result: {result}")

# Check statistics
stats = optimizer.get_stats()
print(f"Stats: {stats}")
```

### 3. Test in Pipeline

Enable your plugin in `plugin.json`:
```json
{
  "enabled": true
}
```

Run the app and check console output:
```
[OPTIMIZED] Pipeline loop started with 3 plugins
Loaded optimizer plugin: My New Optimizer
```

---

## Example Plugins

### Example 1: Simple Counter

**Purpose:** Count processed items

```python
class CounterOptimizer:
    def __init__(self, config):
        self.count = 0
    
    def process(self, data):
        self.count += 1
        data['item_number'] = self.count
        return data
    
    def get_stats(self):
        return {'total_count': self.count}

def initialize(config):
    return CounterOptimizer(config)
```

### Example 2: Text Filter

**Purpose:** Filter out short text

```python
class TextFilterOptimizer:
    def __init__(self, config):
        self.min_length = config.get('min_length', 3)
        self.filtered = 0
    
    def process(self, data):
        text = data.get('text', '')
        if len(text) < self.min_length:
            data['skip_processing'] = True
            self.filtered += 1
        return data
    
    def get_stats(self):
        return {'filtered_count': self.filtered}

def initialize(config):
    return TextFilterOptimizer(config)
```

### Example 3: Performance Monitor

**Purpose:** Track processing times

```python
import time

class PerformanceMonitorOptimizer:
    def __init__(self, config):
        self.times = []
    
    def process(self, data):
        start = time.time()
        # Processing happens in pipeline
        data['start_time'] = start
        return data
    
    def post_process(self, data):
        if 'start_time' in data:
            elapsed = time.time() - data['start_time']
            self.times.append(elapsed)
        return data
    
    def get_stats(self):
        if self.times:
            avg = sum(self.times) / len(self.times)
            return {'avg_time': f"{avg*1000:.1f}ms"}
        return {'avg_time': '0ms'}

def initialize(config):
    return PerformanceMonitorOptimizer(config)
```

---

## Best Practices

### 1. Error Handling

Always wrap your logic in try-except:

```python
def process(self, data):
    try:
        # Your logic here
        return data
    except Exception as e:
        print(f"[MY_PLUGIN] Error: {e}")
        return data  # Return original data on error
```

### 2. Performance

- Keep `process()` fast (<1ms if possible)
- Use caching for expensive operations
- Avoid blocking operations

### 3. Statistics

Track useful metrics:
- Items processed
- Optimizations applied
- Time saved
- Memory used

### 4. Configuration

Provide sensible defaults:
- Settings should work out of the box
- Document valid ranges
- Validate input values

### 5. Documentation

Write clear documentation:
- What the plugin does
- How it works
- When to use it
- Expected performance impact

---

## Troubleshooting

### Plugin Not Loading

**Check:**
1. Directory structure is correct
2. `plugin.json` is valid JSON
3. `optimizer.py` has `initialize()` function
4. Plugin is enabled in `plugin.json`

### Plugin Not Working

**Check:**
1. `process()` method exists
2. Method returns modified data
3. No exceptions in console
4. Plugin is actually being called

### Settings Not Applying

**Check:**
1. Settings are in `plugin.json`
2. UI is reading/writing correct file
3. Pipeline is restarted after changes
4. Config is passed to `__init__()`

---

## Advanced Topics

### Multi-Stage Plugins

A plugin can run at multiple stages:

```python
class MultiStageOptimizer:
    def __init__(self, config):
        self.stage = config.get('stage', 'pre')
    
    def process(self, data):
        if self.stage == 'pre':
            return self.pre_process(data)
        else:
            return self.post_process(data)
    
    def pre_process(self, data):
        # Pre-processing logic
        return data
    
    def post_process(self, data):
        # Post-processing logic
        return data
```

### Stateful Plugins

Plugins can maintain state across calls:

```python
class StatefulOptimizer:
    def __init__(self, config):
        self.history = []
        self.max_history = config.get('max_history', 10)
    
    def process(self, data):
        # Use history
        if self.history:
            data['previous'] = self.history[-1]
        
        # Update history
        self.history.append(data)
        if len(self.history) > self.max_history:
            self.history.pop(0)
        
        return data
```

### Plugin Dependencies

Plugins can depend on other plugins:

```python
class DependentOptimizer:
    def __init__(self, config):
        self.requires = ['translation_cache']
    
    def process(self, data):
        # Check if cache was used
        if data.get('cache_hit', False):
            # Do something special
            pass
        return data
```

---

## Conclusion

Creating optimizer plugins is straightforward:

1. **Create 3 files** (plugin.json, optimizer.py, README.md)
2. **Implement `initialize()` function** and optimizer class
3. **Add to UI** (optional)
4. **Test** and iterate

The plugin system automatically loads and applies your optimizations!

---

**Need help?** Check existing plugins in `plugins/optimizers/` for examples.
