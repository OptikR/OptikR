# Quick Start: Translation System

## For Users

### Change UI Language
1. Open OptikR
2. Click **Settings** button
3. Go to **General** tab
4. Find **"Interface Language"** dropdown
5. Select: **English**, **Deutsch**, **Français**, or **Italiano**
6. Click **"Save Configuration"**
7. **Restart OptikR**

Done! The entire UI is now in your language.

## For Developers

### Regenerate All Translations
```bash
python dev/generate_translations.py
```

This will:
- Extract all UI strings from Python files (546 found)
- Translate using MarianMT neural translation
- Generate new translations.py file
- Takes 10-30 minutes first run

### Add Turkish & Japanese
Edit `dev/generate_translations.py` line 127:
```python
self.languages = {
    'de': 'German',
    'fr': 'French', 
    'it': 'Italian',
    'tr': 'Turkish',  # Uncomment this
    'ja': 'Japanese'  # Uncomment this
}
```

Then run:
```bash
python dev/generate_translations.py
```

### Use Translations in Code
```python
from translations.translations import tr

# Instead of:
label = QLabel("Settings")

# Use:
label = QLabel(tr("settings"))
```

## Files

- **`dev/generate_translations.py`** - Generator script
- **`dev/translations/translations.py`** - 546 translations
- **`dev/translations/extracted_strings.json`** - All UI strings
- **`docs/AUTO_TRANSLATION_COMPLETE.md`** - Full docs

## Status

✅ 546 UI strings extracted
✅ German, French, Italian translated
✅ Turkish, Japanese placeholders ready
✅ System working and tested

## That's It!

The system is fully automatic. Just run the generator script whenever you add new UI strings.
