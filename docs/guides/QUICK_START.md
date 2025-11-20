# Testing Utilities - Quick Start Guide

Quick reference for using the testing utilities during UI testing.

---

## 🚀 Quick Commands

### Test All Utilities
```bash
cd dev/tests/utilities
python run_all_utilities.py --quick
```

### Validate Config Save/Load
```bash
cd dev/tests/utilities
python config_validator.py
```

### Capture Bug Screenshot
```bash
cd dev/tests/utilities
python screenshot_utility.py --type window --description "Bug: Save button not working"
```

### Monitor Performance
```bash
cd dev/tests/utilities
python performance_monitor.py --duration 30
```

### Scan for Obsolete Files
```bash
cd dev/tests/utilities
python file_scanner.py
```

---

## 📋 Common Testing Scenarios

### Scenario 1: Testing a Settings Tab

**Before testing:**
```bash
# Establish baseline
python performance_monitor.py --duration 10 --output baseline.json
```

**During testing:**
```bash
# Capture bugs
python screenshot_utility.py --type window --description "Capture tab bug"
```

**After testing:**
```bash
# Validate settings persistence
python config_validator.py
```

---

### Scenario 2: Performance Testing

**Start monitoring:**
```bash
# Monitor for 60 seconds
python performance_monitor.py --duration 60 --output performance_test.json
```

**While monitoring runs:**
- Start the application
- Start the pipeline
- Let it run for the duration
- Stop the pipeline

**Review results:**
- Check console output for real-time metrics
- Open `performance_test.json` for detailed analysis

---

### Scenario 3: Bug Reporting

**Capture screenshot with annotation:**
```bash
python screenshot_utility.py \
  --annotate "Save button doesn't enable after changing settings" \
  --description "Critical: Save button bug"
```

**List all bug screenshots:**
```bash
python screenshot_utility.py --list
```

---

### Scenario 4: Project Cleanup

**Scan for obsolete files:**
```bash
python file_scanner.py --scan-dir ../.. --output cleanup_candidates.txt
```

**Review the report:**
- Open `cleanup_candidates.txt`
- Review each category (backups, duplicates, old tests, old logs)
- Manually verify before deleting

---

## 🔧 Programmatic Usage

### In Python Scripts

```python
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent / "tests" / "utilities"))

from config_validator import ConfigValidator
from screenshot_utility import ScreenshotUtility
from performance_monitor import PerformanceMonitor
from file_scanner import FileScanner

# Validate config
validator = ConfigValidator()
result = validator.test_setting('ui.window_width', 1600)
print(f"Config test passed: {result['values_match']}")

# Capture screenshot
screenshot = ScreenshotUtility()
screenshot.capture_window("Bug description")

# Monitor performance
monitor = PerformanceMonitor()
metrics = monitor.monitor(duration=30, interval=1.0)

# Scan files
scanner = FileScanner()
results = scanner.scan_directory()
```

---

## 📊 Output Files

All utilities save their output to `dev/tests/utilities/`:

| File | Description |
|------|-------------|
| `config_validation_results.json` | Config test results |
| `screenshots/*.png` | Bug screenshots |
| `screenshots/*.json` | Screenshot metadata |
| `performance_results.json` | Performance metrics |
| `obsolete_files_scan.txt` | File scan report (human-readable) |
| `obsolete_files_scan.json` | File scan report (machine-readable) |

---

## 💡 Tips

1. **Config Validator:** Always creates backups - safe to run anytime
2. **Screenshot Utility:** Requires QApplication - run from within app
3. **Performance Monitor:** Use `--duration 0` for indefinite monitoring (Ctrl+C to stop)
4. **File Scanner:** Review reports carefully before deleting files

---

## 🐛 Troubleshooting

**"No QApplication instance found"**
- Screenshot utility needs a running Qt application
- Run from within the application or start QApplication first

**"Process not found"**
- Performance monitor couldn't find the target process
- It will fall back to system-wide monitoring
- Specify correct process name with `--process`

**"Module not found"**
- Make sure you're in the correct directory
- Run from `dev/tests/utilities/` directory

---

## 📚 Full Documentation

See `README.md` for comprehensive documentation including:
- Detailed feature descriptions
- All command-line options
- Programmatic API reference
- Integration examples
