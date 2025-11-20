# TextValidator Configuration Guide

## Quick Answers

### ✅ YES - TextValidator has confidence settings!

**Where to configure:**
1. Open Settings → Pipeline tab
2. Click "🔌 Plugins by Stage" sub-tab
3. Find "✓ Text Validator" in OCR STAGE section
4. Adjust "Min Confidence" slider (0.1-0.9)

**Default:** 0.3 (30% confidence threshold)

### ✅ YES - TextValidator is context-aware!

It analyzes multiple aspects of text to determine validity.

---

## Confidence System Explained

### How Confidence is Calculated

TextValidator builds a confidence score from **multiple signals**:

```
Total Confidence = Sum of:
├─ Common Words (30% weight)
├─ Dictionary Words (40% weight) ← Learns from your translations!
├─ Valid Patterns (30% weight)
├─ Proper Capitalization (10% bonus)
├─ Punctuation (10% bonus)
├─ Hyphenation (15% bonus)
└─ Word Length Distribution (10% bonus)

Maximum possible: ~1.15 (115%)
Typical valid text: 0.4-0.8 (40-80%)
```

### Confidence Weights Breakdown

| Signal | Weight | Example |
|--------|--------|---------|
| **Common Words** | 30% | "the", "a", "is", "are" |
| **Dictionary Words** | 40% | Words you've translated before |
| **Valid Patterns** | 30% | "the cat", "is running" |
| **Capitalization** | 10% | "Hello World" or "MANGA STYLE" |
| **Punctuation** | 10% | "Hello, world!" |
| **Hyphenation** | 15% | "contin-" (word continues) |
| **Word Lengths** | 10% | Average 3-8 chars per word |

### Min Confidence Threshold

**What it means:**
- **0.1 (10%)** - Very permissive, accepts almost anything
- **0.3 (30%)** - Default, balanced filtering
- **0.5 (50%)** - Stricter, only clear text
- **0.7 (70%)** - Very strict, may reject valid text
- **0.9 (90%)** - Extremely strict, only perfect text

**Recommendation:** Start with 0.3, adjust based on results.

---

## Context Awareness Features

### 1. **Manga-Style Text Detection**

```python
# Recognizes ALL CAPS as valid manga style
if text.isupper() and len(words) >= 2:
    confidence += 0.15
    reasons.append("manga-style caps")
```

**Example:**
- ✅ "AN AXE, A SPEAR, A SWORD," → Valid (manga style)
- ✅ "A HAMMER, A FLAIL, A BOW," → Valid (manga style)

### 2. **Hyphenated Word Detection**

```python
# Detects words split across lines
if text.endswith('-') or text.endswith('—'):
    confidence += 0.15
    reasons.append("hyphenated (continues)")
```

**Example:**
- ✅ "AN INSTRU-" → Valid (continues on next line)
- ✅ "MENT..." → Valid (continuation)

### 3. **Word Fragment Recognition**

```python
# Allows short text if it looks like a word fragment
if len(text) <= 8 and re.search(r'[a-zA-Z]{3,}', text):
    # Has at least 3 consecutive letters - likely a word fragment
    pass  # Continue validation
```

**Example:**
- ✅ "sup reme" → Valid (OCR split word)
- ✅ "contin" → Valid (fragment)

### 4. **Dictionary Learning**

```python
# Checks if words exist in your translation dictionary
dict_word_count = 0
if self.dict_engine and words:
    for word in words:
        if self._is_in_dictionary(word_clean):
            dict_word_count += 1
```

**How it learns:**
1. You translate "sword" → "Schwert"
2. TextValidator remembers "sword" is valid
3. Next time "sword" appears, confidence increases
4. Over time, validation gets smarter!

### 5. **Pattern Recognition**

```python
valid_patterns = [
    r'\b(the|a|an)\s+\w+',  # Article + word
    r'\w+\s+(is|are|was|were)\s+\w+',  # Verb patterns
    r'\w+,\s*\w+',  # Comma-separated words
]
```

**Example:**
- ✅ "the quick brown fox" → Valid (article + words)
- ✅ "cat is running" → Valid (verb pattern)
- ✅ "red, blue, green" → Valid (comma-separated)

### 6. **Garbage Detection**

```python
garbage_patterns = [
    r'^[^a-zA-Z0-9\s]{3,}',  # Only special characters
    r'^[0-9\s\-_\.]{5,}',  # Only numbers and punctuation
    r'(.)\1{4,}',  # Same character repeated 5+ times
]
```

**Example:**
- ❌ "!!!###$$" → Invalid (only special chars)
- ❌ "12345678" → Invalid (only numbers)
- ❌ "aaaaaaaaaa" → Invalid (repeated chars)

---

## Current Configuration in Code

### Complete Pipeline (`complete_pipeline.py`)

```python
# Line 899-902
is_valid, confidence, reason = self.text_validator.is_valid_text(
    block.text,
    min_confidence=0.3  # Lower threshold to allow more text through
)
```

**Hardcoded:** 0.3 (30%)

### Runtime Pipeline Optimized (`runtime_pipeline_optimized.py`)

```python
# Line 555
is_valid, confidence, reason = self.text_validator.is_valid_text(block.text)
```

**Uses default:** 0.3 (30%)

### Validation Stage (`validation_stage.py`)

```python
# Line 74
if self.text_validator.is_valid_text(block.text):
    validated_blocks.append(block)
```

**Uses default:** 0.3 (30%)

---

## How to Make It Configurable

### Option 1: Use UI Setting (Recommended)

The UI control I added saves to:
```
pipeline.plugins.text_validator.min_confidence
```

**Update pipelines to read from config:**

```python
# In complete_pipeline.py
min_conf = self.config_manager.get_setting(
    'pipeline.plugins.text_validator.min_confidence', 
    0.3
)
is_valid, confidence, reason = self.text_validator.is_valid_text(
    block.text,
    min_confidence=min_conf
)
```

### Option 2: Pass to TextValidator Constructor

```python
# Initialize with custom threshold
self.text_validator = TextValidator(
    dict_engine=dict_engine,
    default_min_confidence=0.3  # Would need to add this parameter
)
```

---

## Real-World Examples

### Example 1: Manga Text

**Input:** "AN AXE, A SPEAR, A SWORD,"

**Analysis:**
- Common words: 3 ("a", "an") → +0.3 × (3/6) = +0.15
- Dictionary words: 3 ("axe", "spear", "sword") → +0.4 × (3/6) = +0.20
- Manga-style caps: +0.15
- Punctuation: +0.10
- **Total: 0.60 (60%)**

**Result:** ✅ VALID (exceeds 0.3 threshold)

### Example 2: Hyphenated Word

**Input:** "AN INSTRU-"

**Analysis:**
- Common words: 1 ("an") → +0.3 × (1/2) = +0.15
- Hyphenated: +0.15
- Manga-style caps: +0.15
- **Total: 0.45 (45%)**

**Result:** ✅ VALID (exceeds 0.3 threshold)

### Example 3: Garbage Text

**Input:** "!!!###$$"

**Analysis:**
- Garbage pattern detected
- **Total: 0.0 (0%)**

**Result:** ❌ INVALID (garbage pattern)

### Example 4: OCR Error

**Input:** "sup reme"

**Analysis:**
- Words: 2 → +0.2
- Word lengths: reasonable → +0.1
- **Total: 0.30 (30%)**

**Result:** ✅ VALID (exactly at threshold)

---

## Context-Aware Features Summary

| Feature | Context Type | Benefit |
|---------|-------------|---------|
| **Manga Caps** | Visual style | Accepts ALL CAPS text |
| **Hyphenation** | Line breaks | Accepts split words |
| **Word Fragments** | OCR errors | Accepts partial words |
| **Dictionary Learning** | User history | Gets smarter over time |
| **Pattern Recognition** | Grammar | Validates sentence structure |
| **Garbage Detection** | Noise filtering | Rejects nonsense |
| **Punctuation** | Completeness | Prefers complete sentences |
| **Word Lengths** | Natural language | Validates realistic words |

---

## Recommendations

### For Manga/Comics:
- **Min Confidence:** 0.2-0.3 (permissive)
- **Reason:** Lots of short text, ALL CAPS, fragments

### For Books/Novels:
- **Min Confidence:** 0.4-0.5 (balanced)
- **Reason:** Complete sentences, proper grammar

### For Technical Documents:
- **Min Confidence:** 0.3-0.4 (balanced)
- **Reason:** Mix of text and numbers, technical terms

### For Subtitles:
- **Min Confidence:** 0.2-0.3 (permissive)
- **Reason:** Short phrases, incomplete sentences

---

## Making Pipelines Use UI Setting

### Update Required Files:

**1. `complete_pipeline.py`** (Line 899-902):
```python
# OLD
is_valid, confidence, reason = self.text_validator.is_valid_text(
    block.text,
    min_confidence=0.3
)

# NEW
min_conf = self.config_manager.get_setting(
    'pipeline.plugins.text_validator.min_confidence', 0.3
) if self.config_manager else 0.3
is_valid, confidence, reason = self.text_validator.is_valid_text(
    block.text,
    min_confidence=min_conf
)
```

**2. `runtime_pipeline_optimized.py`** (Line 555):
```python
# OLD
is_valid, confidence, reason = self.text_validator.is_valid_text(block.text)

# NEW
min_conf = self.config_manager.get_setting(
    'pipeline.plugins.text_validator.min_confidence', 0.3
)
is_valid, confidence, reason = self.text_validator.is_valid_text(
    block.text, 
    min_confidence=min_conf
)
```

**3. `validation_stage.py`** (Line 74):
```python
# OLD
if self.text_validator.is_valid_text(block.text):

# NEW
min_conf = self.config_manager.get_setting(
    'pipeline.plugins.text_validator.min_confidence', 0.3
) if hasattr(self, 'config_manager') else 0.3
is_valid, confidence, reason = self.text_validator.is_valid_text(
    block.text,
    min_confidence=min_conf
)
if is_valid:
```

---

## Summary

### ✅ TextValidator IS Context-Aware:
- Recognizes manga-style ALL CAPS
- Detects hyphenated words
- Handles word fragments
- Learns from your translations
- Validates grammar patterns
- Filters garbage intelligently

### ✅ Confidence IS Configurable:
- UI control in Pipeline tab
- Saved to config
- Just needs pipeline updates to read it

### 🔧 Next Step:
Update the 3 pipeline files to read `min_confidence` from config instead of using hardcoded 0.3.

Would you like me to implement that update?
