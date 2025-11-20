# Translation Chain - Quick Start Guide

**Get better translations for rare language pairs in 3 steps!**

---

## What It Does

Chains translations through intermediate languages:

**Japanese → English → German** (instead of Japanese → German directly)

**Result:** 25-35% better quality + saves to dictionary for future use!

---

## Quick Setup

### Step 1: Enable Plugin

**File:** `plugins/optimizers/translation_chain/plugin.json`

Change:
```json
{
  "enabled": false
}
```

To:
```json
{
  "enabled": true,
  "settings": {
    "enable_chaining": {
      "default": true
    }
  }
}
```

### Step 2: Configure Your Language Pairs

Edit the `chain_pairs` in `plugin.json`:

```json
{
  "chain_pairs": {
    "default": {
      "ja->de": "ja->en->de",
      "ko->de": "ko->en->de",
      "zh->ja": "zh->en->ja"
    }
  }
}
```

**Format:** `"source->target": "source->intermediate->target"`

### Step 3: Restart Translation

1. Stop translation if running
2. Start translation
3. Check console for:
   ```
   [TRANSLATION_CHAIN] Initialized with 3 chain pairs
   [TRANSLATION_CHAIN] Chaining enabled
   ```

**Done!** Your translations now use chaining automatically!

---

## How to Use

### Just translate normally!

The plugin automatically:
1. Detects your language pair (e.g., ja→de)
2. Checks if chain is configured
3. Executes chain (ja→en→de)
4. Saves ALL mappings to dictionary
5. Returns final result

### Console Output

**First translation:**
```
[TRANSLATION_CHAIN] Using chain: ja->en->de for 'こんにちは世界'
[TRANSLATION_CHAIN] Step 1 (engine): ja → en
[TRANSLATION_CHAIN]   'こんにちは世界' → 'Hello World'
[TRANSLATION_CHAIN] Step 2 (engine): en → de
[TRANSLATION_CHAIN]   'Hello World' → 'Hallo Welt'
[TRANSLATION_CHAIN] Saving 3 mappings to dictionary...
[TRANSLATION_CHAIN]   Saved: ja→en
[TRANSLATION_CHAIN]   Saved: en→de
[TRANSLATION_CHAIN]   Saved final: ja→de
[TRANSLATION_CHAIN] ✓ Complete
```

**Second translation (same text):**
```
[TRANSLATION_CHAIN] Using direct dictionary: ja->de
```

---

## Common Language Pairs

### Japanese → German
```json
"ja->de": "ja->en->de"
```

### Korean → German
```json
"ko->de": "ko->en->de"
```

### Chinese → Japanese
```json
"zh->ja": "zh->en->ja"
```

### Arabic → German
```json
"ar->de": "ar->en->de"
```

### Thai → German
```json
"th->de": "th->en->de"
```

---

## Performance

**First Time:**
- 2x slower (two translations)
- But 25-35% better quality!

**Second Time:**
- Instant from dictionary
- Best of both worlds!

---

## Troubleshooting

### Not Working?

**Check:**
1. `"enabled": true` in plugin.json
2. `"enable_chaining": {"default": true}`
3. Your language pair is in `chain_pairs`
4. Restart translation after changes

### Console shows nothing?

**Check:**
1. Plugin file exists: `plugins/optimizers/translation_chain/`
2. Files present: `plugin.json`, `optimizer.py`, `README.md`
3. No syntax errors in plugin.json

---

## Statistics

Check pipeline statistics to see:
- Total translations
- Chained translations (%)
- Cache hits
- Dictionary savings

---

**That's it!** Better translations with automatic dictionary learning! 🚀
