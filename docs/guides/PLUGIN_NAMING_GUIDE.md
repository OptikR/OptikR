# Plugin Naming and Organization Guide

## Overview

This guide explains the plugin naming convention and folder structure for OptikR plugins, specifically regarding GPU/CPU compatibility.

---

## Naming Convention

### Pattern

Plugins are named to clearly indicate their hardware requirements:

- **GPU-dependent plugins**: `{plugin_name}_gpu`
- **CPU-compatible plugins**: `{plugin_name}_cpu`
- **Hybrid plugins** (GPU-accelerated but CPU-capable): `{plugin_name}_gpu` with metadata indicating CPU support

### Examples

```
plugins/
├── capture/
│   ├── dxcam_capture_gpu/          # Requires GPU (DirectX)
│   └── screenshot_capture_cpu/     # CPU-compatible
├── ocr/
│   └── easyocr_gpu/                # GPU-accelerated, CPU-capable
└── translation/
    └── marianmt_gpu/               # GPU-accelerated, CPU-capable
```

---

## Plugin Metadata

### Required Fields in plugin.json

Every plugin must include `runtime_requirements` section:

```json
{
  "name": "plugin_name_gpu",
  "display_name": "Plugin Name (GPU)",
  "runtime_requirements": {
    "gpu": {
      "required": false,
      "recommended": true,
      "libraries": ["torch+cu121", "..."],
      "performance_note": "5-10x faster on GPU"
    },
    "cpu": {
      "supported": true,
      "performance_note": "Slower but functional on CPU",
      "libraries": ["torch-cpu", "..."]
    }
  },
  "exe_compatibility": {
    "cpu_build": true,
    "gpu_build": true,
    "auto_disable_on_cpu": false
  }
}
```

### Field Descriptions

#### runtime_requirements.gpu
- `required` (bool): If true, plugin will not work without GPU
- `recommended` (bool): If true, GPU is recommended for best performance
- `libraries` (array): List of GPU-specific dependencies
- `performance_note` (string): Description of GPU performance benefits
- `gpu_features` (array): Required GPU features (e.g., "DirectX 11+")

#### runtime_requirements.cpu
- `supported` (bool): If true, plugin can run on CPU
- `performance_note` (string): Description of CPU performance
- `libraries` (array): List of CPU-specific dependencies
- `fallback_plugin` (string): Name of CPU-compatible alternative plugin
- `reason` (string): Why CPU is not supported (if applicable)

#### exe_compatibility
- `cpu_build` (bool): Include in CPU-only builds
- `gpu_build` (bool): Include in GPU builds
- `auto_disable_on_cpu` (bool): Automatically disable when runtime_mode is 'cpu'

---

## Plugin Categories

### 1. GPU-Only Plugins

**Characteristics**:
- Cannot run without GPU
- Should fail gracefully in CPU mode
- Must provide fallback plugin recommendation

**Example**: `dxcam_capture_gpu`

```json
{
  "name": "dxcam_capture_gpu",
  "runtime_requirements": {
    "gpu": {
      "required": true,
      "gpu_features": ["DirectX 11+"]
    },
    "cpu": {
      "supported": false,
      "fallback_plugin": "screenshot_capture_cpu",
      "reason": "DXCam requires DirectX GPU acceleration"
    }
  },
  "exe_compatibility": {
    "cpu_build": false,
    "gpu_build": true,
    "auto_disable_on_cpu": true
  }
}
```

### 2. CPU-Only Plugins

**Characteristics**:
- Designed for CPU execution
- No GPU dependencies
- Should be included in all builds

**Example**: `screenshot_capture_cpu`

```json
{
  "name": "screenshot_capture_cpu",
  "runtime_requirements": {
    "gpu": {
      "required": false,
      "recommended": false
    },
    "cpu": {
      "supported": true,
      "performance_note": "Fully functional on CPU"
    }
  },
  "exe_compatibility": {
    "cpu_build": true,
    "gpu_build": true,
    "auto_disable_on_cpu": false
  }
}
```

### 3. Hybrid Plugins (GPU-Accelerated, CPU-Capable)

**Characteristics**:
- Can run on both GPU and CPU
- Significantly faster on GPU
- Should detect and adapt to available hardware

**Example**: `easyocr_gpu`, `marianmt_gpu`

```json
{
  "name": "easyocr_gpu",
  "runtime_requirements": {
    "gpu": {
      "required": false,
      "recommended": true,
      "performance_note": "2-5x faster on GPU"
    },
    "cpu": {
      "supported": true,
      "performance_note": "Significantly slower on CPU"
    }
  },
  "exe_compatibility": {
    "cpu_build": true,
    "gpu_build": true,
    "auto_disable_on_cpu": false
  }
}
```

---

## Implementation Requirements

### Plugin Worker/Engine Code

Plugins must check `runtime_mode` and `gpu` config parameters:

```python
def initialize(self, config: dict) -> bool:
    """Initialize plugin with runtime mode awareness."""
    runtime_mode = config.get('runtime_mode', 'auto')
    use_gpu = config.get('gpu', True)
    
    # For GPU-only plugins
    if runtime_mode == 'cpu':
        self.log("CPU-only mode: Plugin disabled")
        return False
    
    # For hybrid plugins
    if use_gpu and torch.cuda.is_available():
        self.device = torch.device('cuda')
    else:
        self.device = torch.device('cpu')
    
    # Initialize with appropriate device
    self.model = Model().to(self.device)
    return True
```

### Config Manager Integration

Plugin managers must propagate runtime_mode:

```python
def load_plugin(self, plugin_name: str, config: Optional[Dict] = None):
    plugin_config = config or {}
    
    if self.config_manager:
        runtime_mode = self.config_manager.get_setting('performance.runtime_mode', 'auto')
        plugin_config.setdefault('runtime_mode', runtime_mode)
        
        # Determine GPU usage
        use_gpu = (runtime_mode == 'gpu') or (runtime_mode == 'auto' and torch.cuda.is_available())
        plugin_config.setdefault('gpu', use_gpu)
    
    # Load plugin with config
    return self._load_plugin_internal(plugin_name, plugin_config)
```

---

## Display Names

### Convention

Display names should clearly indicate hardware requirements:

- GPU-only: "Plugin Name (GPU Required)"
- GPU-accelerated: "Plugin Name (GPU)"
- CPU-only: "Plugin Name (CPU)"
- Hybrid: "Plugin Name (GPU)" with note in description

### Examples

```json
{
  "name": "dxcam_capture_gpu",
  "display_name": "DXCam Screen Capture (GPU)",
  "description": "High-performance screen capture using DXCam (DirectX-based) - Requires GPU"
}
```

```json
{
  "name": "easyocr_gpu",
  "display_name": "EasyOCR Text Recognition (GPU)",
  "description": "Multi-language OCR using EasyOCR (supports 80+ languages) - GPU accelerated"
}
```

---

## Migration Guide

### Renaming Existing Plugins

When renaming plugins to follow the new convention:

1. **Rename folder**: `old_name` → `old_name_gpu` or `old_name_cpu`
2. **Update plugin.json**: Change `name` field to match folder
3. **Update display_name**: Add (GPU) or (CPU) suffix
4. **Add runtime_requirements**: Include full metadata
5. **Update code references**: Search and replace old plugin name
6. **Update config defaults**: Change default plugin names in config

### Example Migration

**Before**:
```
plugins/ocr/easyocr/
  plugin.json: {"name": "easyocr"}
```

**After**:
```
plugins/ocr/easyocr_gpu/
  plugin.json: {"name": "easyocr_gpu", "display_name": "EasyOCR (GPU)"}
```

**Code Updates**:
```python
# Before
ocr_engine = 'easyocr'

# After
ocr_engine = 'easyocr_gpu'
```

---

## Best Practices

### 1. Clear Naming
- Always use `_gpu` or `_cpu` suffix
- Match folder name with plugin name in plugin.json
- Use descriptive display names

### 2. Complete Metadata
- Always include `runtime_requirements` section
- Document performance differences
- Specify fallback plugins for GPU-only plugins

### 3. Graceful Degradation
- GPU-only plugins should fail with clear error messages
- Hybrid plugins should detect and adapt to available hardware
- Provide fallback recommendations

### 4. Testing
- Test plugins in both CPU and GPU modes
- Verify fallback behavior
- Check error messages are helpful

### 5. Documentation
- Document hardware requirements in README
- Explain performance differences
- Provide troubleshooting guide

---

## Folder Structure

### Complete Example

```
plugins/
├── capture/
│   ├── dxcam_capture_gpu/
│   │   ├── plugin.json          # GPU-only metadata
│   │   ├── worker.py            # Checks runtime_mode
│   │   └── README.md            # Documents GPU requirement
│   └── screenshot_capture_cpu/
│       ├── plugin.json          # CPU-compatible metadata
│       ├── worker.py            # Works on CPU
│       └── README.md            # Documents CPU compatibility
├── ocr/
│   └── easyocr_gpu/
│       ├── plugin.json          # Hybrid metadata
│       ├── worker.py            # Adapts to GPU/CPU
│       └── README.md            # Documents both modes
└── translation/
    └── marianmt_gpu/
        ├── plugin.json          # Hybrid metadata
        ├── marianmt_engine.py   # Device selection logic
        └── README.md            # Documents performance
```

---

## Checklist for New Plugins

When creating a new plugin:

- [ ] Choose appropriate suffix (`_gpu` or `_cpu`)
- [ ] Create folder with correct name
- [ ] Add complete `runtime_requirements` to plugin.json
- [ ] Add `exe_compatibility` section
- [ ] Implement runtime_mode checking in code
- [ ] Add device selection for hybrid plugins
- [ ] Test in both CPU and GPU modes
- [ ] Document hardware requirements
- [ ] Add performance notes
- [ ] Specify fallback plugins (if GPU-only)

---

## Summary

The plugin naming convention ensures:
- ✅ Clear hardware requirements at a glance
- ✅ Proper runtime mode handling
- ✅ Graceful fallback behavior
- ✅ Correct EXE build inclusion
- ✅ Better user experience

Follow this guide when creating or migrating plugins to maintain consistency across the OptikR plugin ecosystem.
