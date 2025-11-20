# Configuration Quick Reference

## Single Config File

All settings are now in: **`config/system_config.json`**

## Structure

```json
{
  "_metadata": { ... },      // Version and consolidation info
  "consent": { ... },         // User consent (was user_consent.json)
  "installation": { ... },    // Hardware info (was installation_info.json)
  "presets": { ... },         // Region presets (was region_presets.json)
  "performance": { ... },     // Performance settings
  "translation": { ... },     // Translation settings
  "startup": { ... },         // Startup behavior
  "overlay": { ... },         // Overlay appearance
  "capture": { ... },         // Screen capture settings
  "ui": { ... },              // UI preferences
  "paths": { ... },           // Directory paths
  "ocr": { ... },             // OCR engine settings
  "storage": { ... },         // Cache and storage
  "advanced": { ... },        // Advanced options
  "roi_detection": { ... },   // ROI detection
  "pipeline": { ... },        // Pipeline configuration
  "plugins": { ... }          // Plugin settings
}
```

## Common Operations

### Load Config
```python
from core.config_manager import SimpleConfigManager

config = SimpleConfigManager()
```

### Get Settings
```python
# Dot notation
value = config.get_setting('translation.source_language', 'en')
window_width = config.get_setting('ui.window_width', 1400)

# Convenience methods
consent = config.get_consent_info()
install = config.get_installation_info()
presets = config.get_region_presets()
```

### Set Settings
```python
# Dot notation
config.set_setting('translation.source_language', 'ja')
config.set_setting('ui.window_width', 1600)

# Convenience methods
config.set_consent_info(consent_given=True, version='1.0.0')
config.set_installation_info(install_dict)
config.set_region_preset('MyPreset', preset_data)
```

### Save Config
```python
config.save_config()
```

## Migration

### Consolidate Old Files
```bash
# With backup (recommended)
python scripts/consolidate_config.py --backup

# Dry run first
python scripts/consolidate_config.py --dry-run
```

### What Gets Consolidated
- `user_consent.json` → `config.consent`
- `installation_info.json` → `config.installation`
- `region_presets.json` → `config.presets.regions`
- `translation_config.json` → Removed (redundant)

## Backward Compatibility

Old separate files are still supported:
- If they exist, they're automatically migrated
- No code changes needed
- Safe to delete after migration

## Benefits

- **Simplicity**: 1 file instead of 5
- **Consistency**: Single source of truth
- **Performance**: Faster I/O
- **Maintainability**: Easier to manage

## Full Documentation

See `docs/CONFIG_CONSOLIDATION.md` for complete details.
