# Plugin Testing Guide - Baseline & Individual Testing

**Purpose:** Test base system first, then add plugins one by one to find optimal settings

---

## Current Plugin Status

### ✅ GOOD NEWS: Plugins are ALREADY DISABLED by default!

Looking at your `config/system_config.json`:

```json
{
  "pipeline": {
    "enable_optimizer_plugins": false,  // ← DISABLED
    "plugins_comment": "DISABLED - Testing base system performance first"
  },
  "plugins": {
    "optimizers": {
      "translation_cache": {"enabled": false},
      "frame_skip": {"enabled": false},
      "batch_processing": {"enabled": false},
      "async_pipeline": {"enabled": false},
      "priority_queue": {"enabled": false},
      "work_stealing": {"enabled": false},
      "translation_chain": {"enabled": false}
    }
  }
}
```

**All optimizer plugins are DISABLED!** ✅

---

## Plugin Categories & Status

### 1. Capture Plugins (ALWAYS ACTIVE - Required)

| Plugin | Status | Can Disable? | Purpose |
|--------|--------|--------------|---------|
| `dxcam_capture` | ✅ Active | ❌ No | Screen capture (required for app to work) |

**Note:** Capture plugins are required - the app won't work without them. But you can switch between different capture methods (DirectX, Screenshot, etc.)

### 2. OCR Plugins (ONE ACTIVE - Required)

| Plugin | Status | Can Disable? | Purpose |
|--------|--------|--------------|---------|
| `easyocr` | ✅ Active | ❌ No | Text recognition (required) |
| `tesseract` | ⚪ Available | ✅ Yes | Alternative OCR |
| `paddleocr` | ⚪ Available | ✅ Yes | Alternative OCR |
| `manga_ocr` | ⚪ Available | ✅ Yes | Alternative OCR |

**Note:** You need at least ONE OCR engine active. You can switch between them.

### 3. Text Processor Plugins (OPTIONAL)

| Plugin | Status | Can Disable? | Purpose |
|--------|--------|--------------|---------|
| `spell_corrector` | ❓ Unknown | ✅ Yes | Fix OCR errors |

**Status:** Need to check if this is enabled by default.

### 4. Optimizer Plugins (ALL DISABLED ✅)

| Plugin | Status | Purpose | Performance Gain |
|--------|--------|---------|------------------|
| `translation_cache` | ❌ Disabled | Cache translations | 100x for repeated text |
| `frame_skip` | ❌ Disabled | Skip unchanged frames | 50-70% CPU reduction |
| `batch_processing` | ❌ Disabled | Batch multiple frames | 30-50% faster |
| `async_pipeline` | ❌ Disabled | Async execution | 50-80% throughput |
| `priority_queue` | ❌ Disabled | Priority scheduling | 20-30% responsiveness |
| `work_stealing` | ❌ Disabled | Load balancing | 15-25% CPU utilization |
| `translation_chain` | ❌ Disabled | Multi-language chaining | 25-35% quality |

**All optimizer plugins are DISABLED by default!** ✅

---

## Testing Strategy

### Phase 1: Baseline Testing (Current State)

**Goal:** Measure base system performance without any optimizations

**Current Config:**
```json
{
  "pipeline": {
    "enable_optimizer_plugins": false
  }
}
```

**What to measure:**
- FPS (frames per second)
- CPU usage (%)
- Memory usage (MB)
- Translation latency (ms)
- OCR accuracy (%)
- Startup time (seconds)

**How to test:**
1. Start the app
2. Start translation
3. Let it run for 5 minutes
4. Record metrics from Performance Monitor
5. Save baseline results

**Expected baseline (no optimizations):**
- FPS: 10-15
- CPU: 40-60%
- Memory: 500-600MB
- Latency: 100-200ms
- Startup: 5-10 seconds

---

### Phase 2: Individual Plugin Testing

**Goal:** Test each plugin individually to see its impact

#### Test 1: Translation Cache

**Enable in config:**
```json
{
  "pipeline": {
    "enable_optimizer_plugins": true
  },
  "plugins": {
    "optimizers": {
      "translation_cache": {"enabled": true}
    }
  }
}
```

**Expected improvement:**
- FPS: No change
- CPU: No change
- Latency: <1ms for repeated text (100x faster)
- Memory: +10MB (cache storage)

**Test procedure:**
1. Restart app
2. Translate same text multiple times
3. Measure cache hit rate
4. Compare latency (first vs repeated)

---

#### Test 2: Frame Skip

**Enable in config:**
```json
{
  "plugins": {
    "optimizers": {
      "translation_cache": {"enabled": false},  // Disable previous
      "frame_skip": {"enabled": true}
    }
  }
}
```

**Expected improvement:**
- FPS: +50-100% (15-30 FPS)
- CPU: -50-70% (20-30%)
- Latency: No change
- Memory: No change

**Test procedure:**
1. Restart app
2. Capture static content (no changes)
3. Measure skip rate
4. Compare CPU usage

---

#### Test 3: Batch Processing

**Enable in config:**
```json
{
  "plugins": {
    "optimizers": {
      "frame_skip": {"enabled": false},
      "batch_processing": {"enabled": true}
    }
  }
}
```

**Expected improvement:**
- FPS: +30-50%
- CPU: -20-30%
- Latency: +10-20ms (batching delay)
- Throughput: +30-50%

---

#### Test 4-7: Repeat for other plugins

Continue testing each plugin individually:
- `async_pipeline`
- `priority_queue`
- `work_stealing`
- `translation_chain`

---

### Phase 3: Combination Testing

**Goal:** Test plugins together to find optimal combinations

#### Combination 1: Cache + Frame Skip

```json
{
  "plugins": {
    "optimizers": {
      "translation_cache": {"enabled": true},
      "frame_skip": {"enabled": true}
    }
  }
}
```

**Expected:** Additive benefits (both improvements)

---

#### Combination 2: All Performance Plugins

```json
{
  "plugins": {
    "optimizers": {
      "translation_cache": {"enabled": true},
      "frame_skip": {"enabled": true},
      "batch_processing": {"enabled": true},
      "async_pipeline": {"enabled": true}
    }
  }
}
```

**Expected:** 3-5x overall improvement

---

#### Combination 3: All Plugins

```json
{
  "plugins": {
    "optimizers": {
      "translation_cache": {"enabled": true},
      "frame_skip": {"enabled": true},
      "batch_processing": {"enabled": true},
      "async_pipeline": {"enabled": true},
      "priority_queue": {"enabled": true},
      "work_stealing": {"enabled": true},
      "translation_chain": {"enabled": true}
    }
  }
}
```

**Expected:** Maximum performance (but check for conflicts)

---

### Phase 4: Conflict Detection

**Goal:** Identify any plugin conflicts or negative interactions

**What to watch for:**
- Crashes or errors
- Performance degradation
- Memory leaks
- Incorrect translations
- UI freezes

**Common conflicts:**
- `batch_processing` + `async_pipeline` (may compete for resources)
- `priority_queue` + `work_stealing` (scheduling conflicts)
- `translation_chain` + `translation_cache` (cache invalidation)

---

## Overlay Tracker (Region Visualizer)

**Location:** `dev/components/region_visualizer_pyqt6.py`

**What it does:**
- Shows red overlay for capture region
- Shows blue overlay for translation region
- Helps visualize what's being captured/translated

**How to use:**

### Option 1: Via Toolbar Button

1. Look for "Show Region Overlay" button in toolbar
2. Click to toggle overlay on/off
3. Red box = capture region
4. Blue box = translation region

### Option 2: Via Code

```python
from components.region_visualizer_pyqt6 import RegionVisualizer

# Create visualizer
visualizer = RegionVisualizer()

# Show capture region (red)
visualizer.show_capture_region(x, y, width, height, monitor_id)

# Show translation region (blue)
visualizer.show_translation_region(x, y, width, height, monitor_id)

# Hide overlays
visualizer.hide_overlays()
```

### Option 3: Via Settings

1. Open Settings → Capture tab
2. Click "Show Region Overlay" button
3. Overlay appears on screen

**Note:** The overlay tracker was fixed in Phase 14 to read from multi-region config correctly.

---

## Performance Monitoring Tools

### 1. Performance Monitor Dashboard

**Location:** Sidebar → "Performance" button

**Shows:**
- FPS (real-time)
- CPU usage
- GPU usage
- Memory usage
- Translation latency
- OCR accuracy
- Translation count
- Error count

### 2. Performance Overlay (On-Screen)

**Location:** Performance Monitor → "Show Performance Overlay" button

**Features:**
- Draggable on-screen display
- Configurable metrics (right-click)
- Color-coded status
- Always on top
- Semi-transparent

**How to use:**
1. Open Performance Monitor
2. Click "Show Performance Overlay"
3. Drag to desired position
4. Right-click to configure metrics
5. Position persists across sessions

### 3. Log Viewer

**Location:** Sidebar → "View Logs" button

**Features:**
- Browse all log files
- Automatic error detection
- Quick navigation to errors/warnings
- Search functionality
- Export analysis reports

---

## Testing Checklist

### Baseline Testing ✅

- [ ] Start app with all plugins disabled
- [ ] Record FPS for 5 minutes
- [ ] Record CPU usage average
- [ ] Record memory usage
- [ ] Record translation latency
- [ ] Save baseline metrics

### Individual Plugin Testing

- [ ] Test `translation_cache` alone
- [ ] Test `frame_skip` alone
- [ ] Test `batch_processing` alone
- [ ] Test `async_pipeline` alone
- [ ] Test `priority_queue` alone
- [ ] Test `work_stealing` alone
- [ ] Test `translation_chain` alone

### Combination Testing

- [ ] Test cache + frame_skip
- [ ] Test all performance plugins
- [ ] Test all plugins together

### Conflict Detection

- [ ] Check for crashes
- [ ] Check for memory leaks
- [ ] Check for incorrect translations
- [ ] Check for UI freezes

### Use Case Testing

- [ ] Static content (manga pages)
- [ ] Dynamic content (video subtitles)
- [ ] High-frequency updates (games)
- [ ] Low-frequency updates (documents)

---

## Recommended Plugin Combinations

### For Static Content (Manga, Documents)

```json
{
  "translation_cache": {"enabled": true},
  "frame_skip": {"enabled": true}
}
```

**Why:** Static content doesn't change, so cache and frame skip are very effective.

### For Dynamic Content (Videos, Games)

```json
{
  "translation_cache": {"enabled": true},
  "batch_processing": {"enabled": true},
  "async_pipeline": {"enabled": true}
}
```

**Why:** Dynamic content needs fast processing, batching and async help throughput.

### For Maximum Performance

```json
{
  "translation_cache": {"enabled": true},
  "frame_skip": {"enabled": true},
  "batch_processing": {"enabled": true},
  "async_pipeline": {"enabled": true}
}
```

**Why:** Combines caching, skipping, batching, and async for best overall performance.

### For Maximum Quality

```json
{
  "translation_cache": {"enabled": true},
  "translation_chain": {"enabled": true}
}
```

**Why:** Chaining improves translation quality, cache speeds up repeated text.

---

## Summary

**Current Status:**
- ✅ All optimizer plugins are DISABLED by default
- ✅ Base system is ready for baseline testing
- ✅ Performance monitoring tools are available
- ✅ Overlay tracker (region visualizer) is working

**Next Steps:**
1. Run baseline test (no plugins)
2. Test each plugin individually
3. Test combinations
4. Find optimal settings for your use case

**Tools Available:**
- Performance Monitor Dashboard
- Performance Overlay (on-screen)
- Log Viewer
- Region Visualizer (overlay tracker)

**You're all set for systematic plugin testing!** 🚀
