# Copy Minimal Files Script - Usage Guide

## Overview
The updated `copy_minimal_files.py` script creates a clean distribution of OptikR with only essential runtime files.

## What Gets Included ✅

### Root Files (3 files)
- `run.py` - Main application entry point
- `requirements.txt` - Python dependencies
- `LICENSE` - License information

### Essential Folders
- `app/` - Core application logic (~200 .py files)
- `ui/` - User interface (~70 .py files)
- `plugins/` - Plugin system (~50 plugin folders)
- `dictionary/` - Learned translation dictionaries (.json.gz)
- `system_data/` - Runtime data structure (README.md + empty folders)
- `user_data/` - User config structure (README.md + .migrated + empty folders)
- `models/` - AI models structure (empty, populated at runtime)

## What Gets Excluded ❌

### Development Scripts (~60 files)
All root-level .py scripts except run.py:
- `add_*.py` - Translation utilities
- `auto_*.py` - Auto-translation scripts
- `check_*.py` - Validation scripts
- `cleanup_*.py` - Cleanup utilities
- `consolidate_*.py` - Documentation tools
- `copy_minimal_files.py` - This script itself
- `create_*.py` - Creation utilities
- `delete_*.py` - Deletion utilities
- `extract_*.py` - Extraction tools
- `find_*.py` - Search utilities
- `fix_*.py` - Fix scripts
- `identify_*.py` - Identification tools
- `implement_*.py` - Implementation utilities
- `merge_*.py` - Merge utilities
- `migrate_*.py` - Migration scripts
- `organize_*.py` - Organization tools
- `phase*.py` - Phase implementation scripts
- `regenerate_*.py` - Regeneration utilities
- `remove_*.py` - Removal scripts
- `split_*.py` - Split utilities
- `test_*.py` - Test scripts
- `update_*.py` - Update utilities
- `verify_*.py` - Verification scripts

### Documentation
- All `.md` files (except system_data/README.md, user_data/README.md)
- All `.txt` files (except requirements.txt)
- Entire `docs/` folder

### Test Files
- `test_*.py` files
- `*_test.py` files

### Other
- `__pycache__/` folders
- `.pyc`, `.pyo`, `.pyd` files
- `.log` files
- `.git/` folder

## Usage

### 1. Configure Paths
Edit the script to set your source and destination:
```python
SOURCE_DIR = Path(r"D:\OptikR\release")
DEST_DIR = Path(r"D:\OptikR\backup")
```

### 2. Run the Script
```bash
python copy_minimal_files.py
```

### 3. Confirm
The script will show what will be copied and ask for confirmation:
```
This will copy only essential files for distribution:
  ✓ Root: run.py, requirements.txt, LICENSE
  ✓ Folders: app/, ui/, plugins/, dictionary/, system_data/, user_data/, models/
  ✗ Excluded: All dev scripts, docs/, test files, __pycache__/

Continue? (y/n):
```

### 4. Review Output
The script will:
- Show progress as it copies files
- Display skipped folders and root files
- Verify critical files exist
- Show summary statistics

## Verification

After copying, the script verifies these critical items:
- ✓ run.py
- ✓ requirements.txt
- ✓ LICENSE
- ✓ app/__init__.py
- ✓ app/models.py
- ✓ app/core/config_manager.py
- ✓ app/translations/locales/en.json
- ✓ app/styles/ folder
- ✓ ui/__init__.py
- ✓ ui/dialogs/language_pack_manager.py
- ✓ plugins/ folder
- ✓ dictionary/ folder
- ✓ system_data/README.md
- ✓ user_data/README.md
- ✓ models/ folder

## Testing the Distribution

After copying, test the minimal distribution:

```bash
cd D:\OptikR\backup
python run.py
```

Verify:
1. Application starts without errors
2. All settings tabs load
3. Pipeline can start/stop
4. Language Pack Manager works (Sidebar button)
5. All UI features are accessible

## Why This Works

All utility functions are **built into the application**:

### Language Pack Management
- **Location**: `ui/dialogs/language_pack_manager.py`
- **Access**: Sidebar → "Language Pack Manager" button
- **Features**:
  - Export English template
  - Export split (8 parts for ChatGPT)
  - Import language pack
  - Import merged split files
  - Reload languages

### Translation System
- **Location**: `app/translations/json_translator.py`
- **Functions**: `export_template()`, `import_language_pack()`

### Plugin Translation
- **Location**: `app/translations/plugin_translations.py`
- **Functions**: `export_plugin_template()`, `import_plugin_translation()`

### Auto-Updater
- **Location**: `app/utils/auto_updater.py`
- **Features**: Check for updates, download, self-repair

### Performance Monitoring
- **Location**: `app/utils/performance_monitor.py`
- **Features**: Export metrics data

## File Count Estimate

- **Root**: 3 files
- **app/**: ~200 .py files + .qss + .json
- **ui/**: ~70 .py files
- **plugins/**: ~50 plugin folders
- **dictionary/**: 1 .json.gz file
- **system_data/**: 1 README.md + empty folders
- **user_data/**: 1 README.md + 1 .migrated + empty folders
- **models/**: Empty folder structure

**Total**: ~325 essential files

## Distribution Checklist

- [ ] Run copy_minimal_files.py
- [ ] Verify all critical files exist
- [ ] Test run.py in destination
- [ ] Test all major features
- [ ] Test Language Pack Manager
- [ ] Create installer or zip archive
- [ ] Include requirements.txt
- [ ] Test on clean system
- [ ] Document installation steps

## Notes

- The `models/` folder is included empty - AI models are downloaded at runtime
- `system_data/` and `user_data/` folders are mostly empty on fresh install
- The application creates necessary folders at runtime if missing
- All ~60 development scripts in root are excluded - they're not needed for runtime
- The application is completely self-contained with all utilities built-in
