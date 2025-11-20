# Plugin Translation Guide

## Overview

Plugins in OptikR can provide their own translations that integrate seamlessly with the main translation system.

## Requirements

**IMPORTANT:** Plugins MUST provide an English translation file (`en.json`).

This serves two purposes:
1. **Base translation** - The English text for your plugin
2. **Template** - Users can export this to translate to their language

## Plugin Translation Structure

```
plugins/
└── your_plugin/
    ├── __init__.py
    ├── plugin.py
    └── translations/          # Translation folder
        ├── en.json           # REQUIRED - English base
        ├── de.json           # Optional - German
        ├── fr.json           # Optional - French
        └── ...               # Other languages
```

## English Translation File (REQUIRED)

**File:** `plugins/your_plugin/translations/en.json`

```json
{
  "_metadata": {
    "plugin_name": "your_plugin",
    "language_code": "en",
    "language_name": "English",
    "version": "1.0.0",
    "author": "Your Name",
    "description": "English translation for Your Plugin"
  },
  "translations": {
    "plugin_title": "Your Plugin Name",
    "button_start": "Start Processing",
    "button_stop": "Stop",
    "status_ready": "Ready",
    "status_processing": "Processing...",
    "error_no_input": "No input provided",
    "success_message": "Processing complete!"
  }
}
```

## Using Translations in Your Plugin

```python
from app.translations import plugin_tr

class YourPlugin:
    def __init__(self):
        self.plugin_name = "your_plugin"
    
    def show_ui(self):
        # Translate plugin strings
        title = plugin_tr(self.plugin_name, "plugin_title")
        button_text = plugin_tr(self.plugin_name, "button_start")
        
        # Use in UI
        self.setWindowTitle(title)
        self.button.setText(button_text)
```

## Registering Plugin Translations

In your plugin's `__init__.py` or main file:

```python
from pathlib import Path
from app.translations import register_plugin

# Register when plugin loads
plugin_dir = Path(__file__).parent
register_plugin("your_plugin", plugin_dir)
```

## User Translation Workflow

Users can translate your plugin to their language:

1. **Export Template:**
   ```python
   from app.translations import export_plugin_template
   export_plugin_template("your_plugin", "your_plugin_template.json")
   ```

2. **Translate:**
   - User edits JSON file
   - Or uploads to ChatGPT: "Translate this to Spanish"

3. **Import:**
   ```python
   from app.translations import import_plugin_translation
   import_plugin_translation("your_plugin", "your_plugin_es.json")
   ```

## Best Practices

1. **Always provide en.json** - This is mandatory
2. **Use clear key names** - `button_save` not `btn1`
3. **Group related keys** - `error_*`, `status_*`, etc.
4. **Include metadata** - Helps users understand the file
5. **Test fallback** - Ensure English shows if translation missing

## Example: Complete Plugin

```python
# plugins/my_plugin/__init__.py
from pathlib import Path
from app.translations import register_plugin, plugin_tr

class MyPlugin:
    def __init__(self):
        self.name = "my_plugin"
        
        # Register translations
        plugin_dir = Path(__file__).parent
        register_plugin(self.name, plugin_dir)
    
    def get_title(self):
        return plugin_tr(self.name, "plugin_title")
    
    def get_status(self, status_key):
        return plugin_tr(self.name, f"status_{status_key}")
```

## Why English is Required

1. **Universal Base** - English is the common language
2. **Template** - Users can translate from English
3. **Fallback** - If translation missing, show English
4. **Documentation** - Helps others understand your plugin

## Translation Keys Best Practices

### Good Key Names:
- `plugin_title` - Clear purpose
- `button_save` - Descriptive
- `error_file_not_found` - Specific
- `status_processing` - Grouped

### Bad Key Names:
- `title` - Too generic
- `btn1` - Not descriptive
- `msg` - Unclear
- `text` - Too vague

## Advanced: Multiple Languages

If you want to provide multiple languages:

```
translations/
├── en.json  # Required
├── de.json  # German
├── fr.json  # French
├── es.json  # Spanish
└── ja.json  # Japanese
```

Each file has the same structure, just translated values.

## Testing Your Plugin Translations

```python
# Test script
from app.translations import plugin_tr, set_language

# Test English
print(plugin_tr("my_plugin", "plugin_title"))

# Test German
set_language("de")
print(plugin_tr("my_plugin", "plugin_title"))

# Test fallback
print(plugin_tr("my_plugin", "nonexistent_key"))  # Shows key name
```

## Summary

✅ **DO:**
- Provide `en.json` (required)
- Use clear key names
- Include metadata
- Test translations

❌ **DON'T:**
- Skip English translation
- Use generic key names
- Hardcode strings in plugin
- Forget to register plugin

Your plugin will automatically integrate with OptikR's translation system!
