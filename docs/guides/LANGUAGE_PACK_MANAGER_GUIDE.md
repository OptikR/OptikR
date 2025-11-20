# Language Pack Manager - ChatGPT Translation Guide

## New Features Added ✨

The Language Pack Manager now includes built-in support for splitting large translation files for ChatGPT!

---

## Features

### 1. 📤 Export Split (8 Parts for ChatGPT)
**Purpose:** Splits the English template into 8 smaller files that ChatGPT can handle

**How it works:**
- Splits 1034 keys into 8 files (~130 keys each)
- Each file is small enough for ChatGPT to process
- First file includes metadata (language_code, language_name, etc.)
- Files named: `en_part_1_of_8.json` through `en_part_8_of_8.json`

**Usage:**
1. Click "📤 Export Split (8 Parts for ChatGPT)"
2. Select a folder to save the files
3. 8 JSON files will be created

### 2. 📥 Import Merged Split Files
**Purpose:** Automatically merges 8 translated files back into one language pack

**How it works:**
- Reads all 8 translated files from a folder
- Merges translations into single file
- Validates metadata
- Saves to `app/translations/locales/`
- Automatically reloads languages

**Usage:**
1. Click "📥 Import Merged Split Files"
2. Select folder containing translated files
3. Files are merged and imported automatically

---

## Complete Workflow for ChatGPT Translation

### Step 1: Export Split Files
1. Open Language Pack Manager
2. Click **"📤 Export Split (8 Parts for ChatGPT)"**
3. Choose a folder (e.g., `translation_work/`)
4. 8 files are created: `en_part_1_of_8.json` to `en_part_8_of_8.json`

### Step 2: Translate with ChatGPT
For each file (1 through 8):

1. **Upload file to ChatGPT**
2. **Use this prompt:**
   ```
   Translate this JSON file to German. 
   Keep all keys unchanged, only translate the values.
   Preserve all emojis, formatting, and special characters.
   Return the complete translated JSON.
   ```
3. **Copy the response**
4. **Save as:** `de_part_1_of_8.json` (change number for each file)
5. **Repeat for all 8 files**

### Step 3: Update Metadata (First File Only)
Open `de_part_1_of_8.json` and update the metadata:
```json
"_metadata": {
  "language_code": "de",
  "language_name": "German (Deutsch)",
  "author": "Your Name",
  "last_updated": "2025-11-18"
}
```

### Step 4: Import Merged Files
1. Open Language Pack Manager
2. Click **"📥 Import Merged Split Files"**
3. Select the folder with your translated files
4. Confirm the import
5. Done! German language is now available

---

## File Naming Patterns

The import function recognizes these patterns:
- `de_part_1_of_8.json` (recommended)
- `part_1_of_8.json`
- `translated_part_1.json`
- `part1.json`

**Tip:** Use the recommended pattern for clarity!

---

## Troubleshooting

### "No Files Found"
- Check file names match the pattern
- Ensure files are in the selected folder
- Files should be named `de_part_X_of_8.json`

### "Incomplete Set"
- You have less than 8 files
- You can continue with partial import
- Or cancel and add missing files

### "Missing Metadata"
- First file must contain `_metadata` section
- Check `de_part_1_of_8.json` has metadata
- Update language_code and language_name

### Import Failed
- Check JSON syntax is valid
- Ensure all files are properly formatted
- Look at error message for details

---

## Tips for Best Results

### ChatGPT Translation
1. **One file at a time** - Don't try to translate multiple files in one prompt
2. **Check the output** - Verify JSON is valid before saving
3. **Preserve formatting** - Make sure emojis and special characters are intact
4. **Use consistent naming** - Name files sequentially (1, 2, 3, etc.)

### Quality Check
After importing:
1. Switch to the new language
2. Check a few tabs to verify translations
3. Look for any untranslated text
4. Fix any issues and re-import if needed

---

## Example ChatGPT Conversation

**You:**
```
Translate this JSON file to German. 
Keep all keys unchanged, only translate the values.
Preserve all emojis, formatting, and special characters.
Return the complete translated JSON.

[paste en_part_1_of_8.json content]
```

**ChatGPT:**
```json
{
  "_metadata": {
    "language_code": "de",
    "language_name": "German (Deutsch)",
    ...
  },
  "translations": {
    "general": "Allgemein",
    "capture": "Erfassung",
    ...
  }
}
```

**You:**
```
[Copy the response and save as de_part_1_of_8.json]
[Repeat for parts 2-8]
```

---

## Benefits

✅ **No file size limits** - Each part is small enough for ChatGPT
✅ **Automatic merging** - No manual JSON editing needed
✅ **Error checking** - Validates files before import
✅ **Flexible naming** - Recognizes multiple file patterns
✅ **Progress tracking** - Shows how many files were merged
✅ **Safe import** - Confirms before saving

---

## Technical Details

### Split Export
- **Total keys:** 1034
- **Keys per file:** ~130
- **File size:** 7-11 KB each
- **Format:** Standard JSON with UTF-8 encoding

### Merge Import
- **Reads:** All matching files in folder
- **Validates:** Metadata and translations structure
- **Merges:** Combines all translations into one
- **Saves:** To `app/translations/locales/{lang_code}.json`
- **Reloads:** Automatically refreshes language list

---

## Summary

The Language Pack Manager now makes it easy to translate OptikR into any language using ChatGPT:

1. **Export Split** → 8 small files
2. **Translate** → Upload each to ChatGPT
3. **Import Merged** → Automatic combination
4. **Done!** → New language ready to use

No more manual JSON editing or file size issues! 🎉
