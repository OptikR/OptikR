# Plugin System - Quick Start Guide

**For:** Developers implementing the plugin system  

---

## 🎯 What We're Building

A **subprocess-based plugin system** where:
- All pipeline stages run as isolated subprocesses (crash-safe)
- Users create plugins with a generator (2-minute setup)
- Plugins stored in `plugins/` folder (easy access)
- Full UI integration (enable/disable/configure from GUI)

---

## 📁 Key Files to Create

### Phase 1: Core (4-5 hours)
```
src/workflow/base/
├─ base_subprocess.py      ← Subprocess wrapper base class
├─ base_worker.py          ← Worker script base class
└─ plugin_interface.py     ← Plugin metadata definitions

src/workflow/subprocesses/
├─ capture_subprocess.py   ← Capture subprocess wrapper
├─ ocr_subprocess.py       ← OCR subprocess wrapper
└─ translation_subprocess.py ← Translation subprocess wrapper

src/workflow/
├─ subprocess_manager.py   ← Manages all subprocesses
└─ runtime_pipeline.py     ← Updated to use subprocesses
```

### Phase 2: Plugins (3-4 hours)
```
src/workflow/
└─ plugin_manager.py       ← Discovers and loads plugins

plugins/
├─ capture/dxcam_capture/  ← Example capture plugin
├─ ocr/easyocr/            ← Example OCR plugin
└─ translation/marianmt/   ← Example translation plugin
```

### Phase 3: Generator (2-3 hours)
```
src/workflow/
└─ plugin_generator.py     ← CLI + GUI plugin generator
```

### Phase 4: UI (3-4 hours)
```
components/settings/
├─ pipeline_management_tab_pyqt6.py  ← Updated with plugin UI
└─ storage_tab_pyqt6.py              ← Plugin path management

components/dialogs/
└─ plugin_settings_dialog.py         ← Plugin configuration dialog
```

### Phase 5: Docs (2-3 hours)
```
docs/
├─ USER_GUIDE_PLUGINS.md
├─ PLUGIN_DEVELOPMENT_GUIDE.md
├─ PLUGIN_API_REFERENCE.md
└─ PLUGIN_EXAMPLES.md
```

---

## 🔧 Implementation Order

### Day 1: Core Infrastructure (4-5 hours)
1. Create `base_subprocess.py` - Foundation for all subprocesses
2. Create `base_worker.py` - Foundation for all workers
3. Create subprocess wrappers (capture, OCR, translation)
4. Create `subprocess_manager.py` - Orchestrates subprocesses
5. Update `runtime_pipeline.py` - Use subprocess manager

**Test:** All stages run as subprocesses, crash isolation works

### Day 2: Plugin System (3-4 hours)
6. Create `plugin_manager.py` - Discovers plugins
7. Create plugin.json schema
8. Create 3 example plugins (capture, OCR, translation)
9. Integrate plugin manager with subprocess manager

**Test:** Plugins load from `plugins/` directory, hot-reload works

### Day 3: Plugin Generator (2-3 hours)
10. Create `plugin_generator.py` CLI
11. Create plugin templates (4 types)
12. Add GUI generator to Pipeline Management Tab

**Test:** Generate plugin in <2 minutes, plugin works immediately

### Day 4: UI Integration (3-4 hours)
13. Update Pipeline Management Tab - plugin list, enable/disable
14. Update Storage Tab - plugin path management
15. Create plugin settings dialog

**Test:** Full UI workflow - install, enable, configure, use plugin

### Day 5: Documentation (2-3 hours)
16. Write user guide
17. Write developer guide
18. Write API reference
19. Write example plugins guide

**Test:** User can follow docs to create and use plugins

### Day 6: Testing & Validation (2-3 hours)
20. Create test suite (subprocess, plugin, generator tests)
21. Integration testing (full pipeline with plugins)
22. Performance testing (measure overhead)
23. User acceptance testing (workflows)

**Test:** All tests pass, performance acceptable, UX validated

### Day 7: Port Optimizations (4-5 hours)
24. Analyze existing optimizations in complete_pipeline.py
25. Create base_optimizer.py
26. Port 8 optimizer plugins:
    - Frame Skip (50-70% less processing)
    - Parallel OCR (2-3x faster)
    - Batch Translation (30-50% faster)
    - Translation Cache (instant repeats)
    - ROI Detection (30-50% faster OCR)
    - Priority Queue (20-30% responsiveness)
    - Work-Stealing (15-25% CPU usage)
    - Async Pipeline (50-80% throughput)
27. Update documentation with optimizers

**Test:** All optimizers work, 3-5x performance improvement achieved

---

## 💡 Key Concepts

### Subprocess Communication
```python
# Parent → Worker (stdin)
{"type": "init", "config": {...}}
{"type": "process", "data": {...}}
{"type": "shutdown"}

# Worker → Parent (stdout)
{"type": "ready"}
{"type": "result", "data": {...}}
{"type": "error", "error": "..."}
```

### Plugin Structure
```
plugins/capture/my_plugin/
├─ plugin.json      ← Metadata (name, version, settings)
├─ worker.py        ← Worker script (runs as subprocess)
├─ README.md        ← User documentation
└─ requirements.txt ← Python dependencies (optional)
```

### Plugin Lifecycle
```
1. Discovery  → PluginManager scans plugins/ folder
2. Loading    → Read plugin.json, validate structure
3. Starting   → Launch worker.py as subprocess
4. Running    → Send/receive messages via stdin/stdout
5. Stopping   → Send shutdown message, wait for exit
6. Restarting → Auto-restart on crash (max 3 attempts)
```

---

## 🎯 Success Metrics

After implementation, verify:

- [ ] All stages run as subprocesses
- [ ] Subprocess crash doesn't kill main app
- [ ] Automatic restart works (max 3 attempts)
- [ ] Plugin generator creates working plugin in <2 minutes
- [ ] Plugins can be enabled/disabled from UI
- [ ] Plugin settings configurable from UI
- [ ] Hot-reload works (no app restart needed)
- [ ] Plugin metrics visible in UI
- [ ] Documentation is complete and clear

---

## 🚀 Quick Commands

```bash
# Generate a plugin (CLI)
python -m src.workflow.plugin_generator

# Test a plugin
python plugins/capture/my_plugin/worker.py

# List all plugins
python -m src.workflow.plugin_manager --list

# Validate plugin
python -m src.workflow.plugin_manager --validate plugins/capture/my_plugin/
```

---

## 📝 Example Plugin (Minimal)

### plugin.json
```json
{
  "name": "simple_capture",
  "display_name": "Simple Capture",
  "version": "1.0.0",
  "type": "capture",
  "worker_script": "worker.py"
}
```

### worker.py
```python
import sys
import json
from src.workflow.base.base_worker import BaseWorker

class SimpleCaptureWorker(BaseWorker):
    def initialize(self, config):
        # Setup capture
        self.send_ready()
    
    def process(self, data):
        # Capture frame
        frame = self.capture_frame(data['region'])
        self.send_result({'frame': frame})

if __name__ == '__main__':
    worker = SimpleCaptureWorker()
    worker.run()
```

---

## 🔗 Related Documents

- **Full Plan:** `SUBPROCESS_PLUGIN_IMPLEMENTATION_PLAN.md`
- **Current Status:** `SESSION_SUMMARY_NOV12.md`
- **Architecture:** `perfect_structure.txt`

---

**Ready to start?** Begin with Phase 1! 🚀
