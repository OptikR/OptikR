# How to Change Overlay Positioning

## Quick Guide

### Step 1: Open Settings
Click the **Settings** button in OptikR (usually a gear icon ⚙️)

### Step 2: Go to Overlay Tab
Click on the **Overlay** tab in the settings window

### Step 3: Find Positioning Strategy
Scroll down to the **📍 Positioning Strategy** section

### Step 4: Choose Your Mode

You'll see a dropdown with three options:

#### 🎯 Simple (OCR Coordinates)
- **What it does**: Places overlays exactly where OCR detected text
- **Best for**: Manga, comics, images where you want precise positioning
- **Pros**: Predictable, no surprises
- **Cons**: May overlap with original text

#### 🧠 Intelligent (Recommended)
- **What it does**: Smart positioning with collision avoidance
- **Best for**: Dense text, multiple overlays, general use
- **Pros**: Avoids collisions, stays on screen
- **Cons**: May move overlays slightly from original position

#### 📖 Flow-Based
- **What it does**: Follows text reading direction
- **Best for**: Manga, comics with specific reading patterns
- **Pros**: Respects text flow
- **Cons**: Currently similar to Intelligent mode (can be enhanced)

### Step 5: Save
Click the **Save** button at the bottom of the settings window

### Step 6: Test
Start translating and see how overlays appear!

## Recommendations by Use Case

### For Manga/Comics Translation
**Use: Simple (OCR Coordinates)**
- Overlays appear exactly where text bubbles are
- Most predictable for static images
- You can see exactly what OCR detected

### For Game Translation
**Use: Intelligent (Recommended)**
- Handles dynamic UI elements
- Avoids overlapping with game UI
- Better for moving content

### For Video/Subtitle Translation
**Use: Intelligent (Recommended)**
- Handles multiple overlays
- Avoids collisions
- Better for dense text

### For Document Translation
**Use: Simple (OCR Coordinates)**
- Preserves document layout
- Exact positioning
- No unexpected movement

## Troubleshooting

### Problem: Overlays appear far from original text

**Solution**: Switch to **Simple** mode
- This uses exact OCR coordinates
- No repositioning logic applied

### Problem: Overlays overlap each other

**Solution**: Switch to **Intelligent** mode
- Automatic collision avoidance
- Finds best position for each overlay

### Problem: Overlays go off-screen

**Solution**: Both modes handle this
- Overlays are automatically clamped to screen boundaries
- Check your screen margin settings if needed

### Problem: Can't see the setting

**Solution**: 
1. Make sure you're on the **Overlay** tab (not OCR or Translation)
2. Scroll down - it's in the middle of the page
3. Look for **📍 Positioning Strategy** section

## Advanced: Testing Modes

Want to test all modes quickly?

Run this command:
```bash
python test_positioning_fix.py
```

This will show you sample overlays in each mode so you can compare.

## Configuration File

If you prefer editing config files directly:

**Location**: `config.json` (or your config file)

**Setting**:
```json
{
  "overlay": {
    "positioning_mode": "simple"
  }
}
```

**Valid values**: 
- `"simple"` - OCR coordinates
- `"intelligent"` - Smart positioning (default)
- `"flow_based"` - Text flow

## What Changed?

Previously, overlays were automatically repositioned above/below text, causing them to appear "way off" from OCR coordinates.

Now you have full control:
- **Simple mode**: No repositioning (exact OCR coords)
- **Intelligent mode**: Smart repositioning with collision avoidance
- **Flow-based mode**: Follows text patterns

## Need Help?

1. Try **Simple** mode first - it's the most predictable
2. If overlays overlap, try **Intelligent** mode
3. Check the console for any error messages
4. Report issues with screenshots showing the problem

## Summary

1. Settings → Overlay → Positioning Strategy
2. Choose: Simple, Intelligent, or Flow-Based
3. Save and test
4. Adjust as needed

That's it! Enjoy properly positioned overlays! 🎉
