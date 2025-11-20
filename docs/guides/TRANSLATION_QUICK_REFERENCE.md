# Translation System - Quick Reference Card

## ✅ Status: COMPLETE & WORKING

## 🚀 Quick Start

### Test It Now:
```bash
python test_translation_system.py
```

### Use in Code:
```python
from app.translations import tr

label = QLabel(tr("general"))  # Translates "general" key
```

### Switch Language:
```python
from app.translations import set_language

set_language("de")  # German
set_language("fr")  # French
set_language("en")  # English
```

## 📦 Available Languages

| Code | Language | Status |
|------|----------|--------|
| en | English | ✅ 100% |
| de | German | ✅ 96% |
| fr | French | ✅ 97% |
| it | Italian | ✅ 96% |
| tr | Turkish | ⏳ Needs translation |
| ja | Japanese | ⏳ Needs translation |

## 🎯 For Users: Add a Language

### 1. Export Template
```python
from app.translations import export_template
export_template("english_template.json")
```

### 2. Translate
- Upload to ChatGPT: "Translate this JSON to Spanish"
- Or edit manually

### 3. Update Metadata
```json
{
  "_metadata": {
    "language_code": "es",
    "language_name": "Español"
  }
}
```

### 4. Import
```python
from app.translations import import_language_pack
import_language_pack("spanish.json")
```

## 🛠️ For Developers: Wrap Strings

### Before:
```python
button = QPushButton("Save Settings")
label = QLabel("General")
```

### After:
```python
from app.translations import tr

button = QPushButton(tr("save_settings"))
label = QLabel(tr("general"))
```

### Add to JSON:
```json
{
  "translations": {
    "save_settings": "Save Settings",
    "general": "General"
  }
}
```

## 📁 File Locations

### Translation Files:
- `app/translations/locales/en.json` - English
- `app/translations/locales/de.json` - German
- `app/translations/locales/fr.json` - French
- `app/translations/locales/it.json` - Italian
- `app/translations/locales/tr.json` - Turkish
- `app/translations/locales/ja.json` - Japanese
- `app/translations/locales/custom/` - User languages

### Core Files:
- `app/translations/json_translator.py` - Translator engine
- `app/translations/__init__.py` - Public API
- `ui/dialogs/language_pack_manager.py` - UI tool

## 🎨 Language Pack Manager UI

### Show the Dialog:
```python
from ui.dialogs.language_pack_manager import show_language_pack_manager

show_language_pack_manager(parent_widget)
```

### Features:
- View installed languages
- Export English template
- Import custom language packs
- Reload languages

## 🧪 API Reference

### Import:
```python
from app.translations import (
    tr,                      # Translate a key
    set_language,            # Change language
    get_current_language,    # Get current language code
    get_available_languages, # Get all languages
    export_template,         # Export English template
    import_language_pack,    # Import language pack
    reload_languages         # Reload all languages
)
```

### Functions:

#### `tr(key, **kwargs)`
Translate a key with optional parameters.
```python
tr("general")  # Simple
tr("error_msg", error="File not found")  # With params
```

#### `set_language(lang_code)`
Change the current language.
```python
set_language("de")  # German
```

#### `get_current_language()`
Get current language code.
```python
lang = get_current_language()  # Returns "en", "de", etc.
```

#### `get_available_languages()`
Get all available languages.
```python
langs = get_available_languages()
# Returns: {"en": "English", "de": "German", ...}
```

#### `export_template(output_file, lang_code="en")`
Export language template.
```python
export_template("template.json")
```

#### `import_language_pack(json_file, custom=True)`
Import a language pack.
```python
import_language_pack("spanish.json", custom=True)
```

#### `reload_languages()`
Reload all language packs from disk.
```python
reload_languages()
```

## 📊 JSON File Format

```json
{
  "_metadata": {
    "language_code": "es",
    "language_name": "Español",
    "version": "1.0.0",
    "author": "Your Name",
    "last_updated": "2025-11-18",
    "total_keys": 554
  },
  "translations": {
    "general": "General",
    "save": "Guardar",
    "cancel": "Cancelar"
  }
}
```

## ⚡ Quick Tips

### Tip 1: Fallback Works Automatically
If a translation is missing, English is used automatically.

### Tip 2: Can't Break the App
Invalid translations just show the key name.

### Tip 3: Hot Reload
Call `reload_languages()` to reload without restart.

### Tip 4: Thread-Safe
Safe to use from any thread.

### Tip 5: Gradual Migration
Don't need to wrap all strings at once!

## 🎯 Common Tasks

### Task: Add Spanish
1. Export: `export_template("en.json")`
2. Translate with ChatGPT
3. Import: `import_language_pack("es.json")`

### Task: Update Translation
1. Edit JSON file in `app/translations/locales/`
2. Call `reload_languages()` or restart app

### Task: Wrap UI String
1. Import: `from app.translations import tr`
2. Replace: `"Text"` → `tr("text")`
3. Add to JSON if missing

### Task: Test Translation
1. Run: `python test_translation_system.py`
2. Or change language in app settings

## 🐛 Troubleshooting

### Problem: Translation not showing
- Check key exists in JSON
- Check language is loaded
- Check `tr()` is called correctly

### Problem: Language not available
- Check JSON file exists
- Check metadata is correct
- Call `reload_languages()`

### Problem: Import fails
- Check JSON is valid
- Check metadata section exists
- Check translations section exists

## 📞 Support

### Test Script:
```bash
python test_translation_system.py
```

### Check Logs:
Look for `[INFO]`, `[WARNING]`, `[ERROR]` messages in console.

### Validate JSON:
Use online JSON validator or:
```python
import json
with open("file.json") as f:
    json.load(f)  # Will error if invalid
```

## 🎉 Success!

The system is:
- ✅ Working
- ✅ Tested
- ✅ Ready to use
- ✅ User-friendly
- ✅ Production-ready

**Start using it today!** 🚀
