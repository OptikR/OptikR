# New Plugins Usage Guide

## Plugin 24: Regex Text Processor

### What It Does
Cleans and normalizes text using regex patterns. Perfect for:
- Removing noise from OCR output
- Normalizing punctuation and quotes
- Fixing common OCR errors
- Removing URLs and emails
- Japanese text spacing

### How to Enable
1. Go to Settings → Plugins
2. Find "Regex Text Processor"
3. Enable it
4. Select filter mode

### Filter Modes

#### 1. Basic (Default)
- Removes excessive whitespace
- Trims leading/trailing spaces
- **Use for**: General cleanup

#### 2. Aggressive
- Removes special characters
- Normalizes punctuation
- Removes excessive whitespace
- **Use for**: Noisy OCR output

#### 3. Normalize
- Fixes quotes (" " ' → " ')
- Fixes dashes (— – → -)
- Fixes ellipsis (... → ...)
- Removes zero-width characters
- **Use for**: Text formatting issues

#### 4. OCR Cleanup
- Fixes l → I (standalone)
- Fixes 0 → O (standalone)
- Removes random single characters
- Fixes spacing around punctuation
- **Use for**: OCR error correction

#### 5. Japanese
- Removes spaces between Japanese characters
- Normalizes Japanese punctuation
- **Use for**: Japanese text from OCR

#### 6. URL/Email
- Removes URLs
- Removes email addresses
- **Use for**: Web content cleanup

### Custom Patterns

You can add custom regex patterns in the config:

```json
{
  "filter_mode": "basic",
  "custom_patterns": [
    {
      "pattern": "\\d+",
      "replacement": "#"
    },
    {
      "pattern": "test",
      "replacement": "TEST"
    }
  ]
}
```

### Examples

**Before**: `Th1s  1s   a    test.`
**After (basic)**: `Th1s 1s a test.`
**After (ocr_cleanup)**: `This is a test.`

**Before**: `"Hello"  —  World...`
**After (normalize)**: `"Hello" - World...`

**Before**: `これ は テスト です` (with spaces)
**After (japanese)**: `これはテストです` (no spaces)

---

## Plugin 26: LibreTranslate

### What It Does
Free online translation using LibreTranslate API. Supports:
- 30+ languages
- Self-hosted instances
- No API key required (for public API)
- Language detection

### How to Enable
1. Go to Settings → Translation
2. Select "LibreTranslate" as translation engine
3. Configure API URL (optional)
4. Add API key (optional)

### Configuration

#### Public API (Free)
```json
{
  "api_url": "https://libretranslate.com/translate",
  "api_key": "",
  "timeout": 30,
  "max_retries": 3
}
```

**Note**: Public API has rate limits. Good for testing, not for heavy use.

#### Self-Hosted (Recommended for Production)

**Step 1: Install LibreTranslate**
```bash
docker run -ti --rm -p 5000:5000 libretranslate/libretranslate
```

**Step 2: Configure Plugin**
```json
{
  "api_url": "http://localhost:5000/translate",
  "api_key": "",
  "timeout": 30,
  "max_retries": 3
}
```

**Benefits**:
- No rate limits
- Faster (local network)
- Privacy (no data sent to external servers)
- Free unlimited translations

### Supported Languages

**30+ languages**: English, Arabic, Azerbaijani, Chinese, Czech, Danish, Dutch, Esperanto, Finnish, French, German, Greek, Hebrew, Hindi, Hungarian, Indonesian, Irish, Italian, Japanese, Korean, Persian, Polish, Portuguese, Russian, Slovak, Spanish, Swedish, Turkish, Ukrainian, Vietnamese

### Language Codes

| Language | Code | Language | Code |
|----------|------|----------|------|
| English | en | Japanese | ja |
| German | de | Korean | ko |
| French | fr | Chinese | zh |
| Spanish | es | Arabic | ar |
| Italian | it | Russian | ru |
| Portuguese | pt | Turkish | tr |
| Dutch | nl | Polish | pl |
| Swedish | sv | Czech | cs |
| Danish | da | Finnish | fi |
| Greek | el | Hebrew | he |
| Hindi | hi | Hungarian | hu |
| Indonesian | id | Irish | ga |
| Persian | fa | Slovak | sk |
| Ukrainian | uk | Vietnamese | vi |
| Azerbaijani | az | Esperanto | eo |

### Features

#### Automatic Retry
- Retries failed requests up to 3 times
- Exponential backoff (2s, 4s, 8s)
- Handles rate limits automatically

#### Language Detection
```python
# Automatically detect source language
detected = engine.detect_language("Hello world")
# Returns: "en"
```

#### Batch Translation
```python
# Translate multiple texts at once
texts = ["Hello", "World", "Test"]
results = engine.translate_batch(texts, "en", "de")
# Returns: ["Hallo", "Welt", "Test"]
```

#### Statistics
```python
stats = engine.get_stats()
# {
#   'total_requests': 100,
#   'total_errors': 2,
#   'error_rate': '2.0%',
#   'total_chars_translated': 5000,
#   'api_url': 'https://libretranslate.com/translate',
#   'has_api_key': False
# }
```

### Troubleshooting

#### Rate Limit Error (429)
- **Problem**: Too many requests to public API
- **Solution**: 
  1. Wait a few minutes
  2. Get free API key from libretranslate.com
  3. Self-host LibreTranslate

#### Timeout Error
- **Problem**: Request taking too long
- **Solution**: Increase timeout in settings (30s → 60s)

#### Connection Error
- **Problem**: Can't reach API
- **Solution**: 
  1. Check internet connection
  2. Verify API URL is correct
  3. Check firewall settings

#### API Key Required (403)
- **Problem**: Instance requires API key
- **Solution**: Get API key from libretranslate.com or your self-hosted instance

### Performance Tips

1. **Self-host for production**: No rate limits, faster, private
2. **Use batch translation**: More efficient for multiple texts
3. **Enable translation cache**: Avoid re-translating same text
4. **Increase timeout for long texts**: 30s may not be enough for very long texts

### Comparison with MarianMT

| Feature | LibreTranslate | MarianMT GPU |
|---------|----------------|--------------|
| **Speed** | 100-500ms (network) | 10-50ms (local) |
| **Quality** | Good | Excellent |
| **Languages** | 30+ | Limited pairs |
| **Setup** | Easy (API) | Complex (models) |
| **Cost** | Free | Free |
| **Internet** | Required | Not required |
| **Privacy** | Data sent to API | Fully local |
| **Best For** | Testing, variety | Production, speed |

### When to Use LibreTranslate

✅ **Use LibreTranslate when**:
- Testing OCR vs translation issues
- Need many language pairs
- Don't have GPU
- Want easy setup
- Self-hosting for production

❌ **Use MarianMT when**:
- Need maximum speed
- Have GPU available
- Want offline translation
- Need best quality
- Privacy is critical

---

## Testing the New Plugins

### Test Regex Processor

1. Enable "Regex Text Processor"
2. Set mode to "ocr_cleanup"
3. Capture text with OCR errors
4. Verify errors are fixed

**Test Cases**:
- `l` → `I` (standalone)
- `0` → `O` (standalone)
- Multiple spaces → single space
- Punctuation spacing fixed

### Test LibreTranslate

1. Enable "LibreTranslate" translation engine
2. Use public API (no key needed)
3. Translate simple text
4. Check logs for API calls

**Test Cases**:
- English → German
- Japanese → English
- Long text (test timeout)
- Multiple texts (test batch)

---

## 🎉 Both Plugins Ready!

All 27 plugins are now fully implemented and ready for comprehensive testing!
