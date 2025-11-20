# Preset System Guide

## Overview
The preset system allows you to save and load complete application configurations, making it easy to switch between different setups for various use cases.

## Location
The preset controls are located in the **sidebar** under the "● Presets" section, right below the System Status.

## Features

### What Gets Saved in a Preset?
When you save a preset, it captures:

- **OCR Settings**
  - Selected OCR engine (EasyOCR, Tesseract, PaddleOCR, etc.)
  - Source language for OCR detection
  - Available languages list

- **Translation Settings**
  - Target language
  - Translation engine

- **Multi-Monitor Capture Settings**
  - All defined capture regions
  - Active region IDs
  - Capture mode (continuous/manual)
  - Capture interval

- **Overlay Settings**
  - Enabled/disabled state
  - Style configuration
  - Font size
  - Opacity

- **Plugin Settings**
  - Enabled plugins list
  - Individual plugin configurations

- **Advanced Settings**
  - GPU acceleration on/off
  - Batch size
  - Thread count

- **UI Settings**
  - Language
  - Theme

## How to Use

### Saving a Preset

1. Configure your application settings as desired (OCR engine, languages, capture regions, etc.)
2. Click the **"Save"** button in the Presets section
3. Enter a descriptive name for your preset (e.g., "Gaming Setup", "Work Monitor", "Japanese Manga")
4. Click OK

Your preset is now saved and will appear in the dropdown list.

### Loading a Preset

1. Select a preset from the dropdown menu
2. Click the **"Load"** button
3. Confirm that you want to load the preset (this will overwrite current settings)
4. The application will reload with all the preset settings applied

### Deleting a Preset

1. Select the preset you want to delete from the dropdown
2. Click the **"Del"** button (red)
3. Confirm the deletion

## Use Cases

### Example 1: Gaming Setup
Save a preset with:
- Full-screen capture region on your gaming monitor
- Japanese → English translation
- EasyOCR engine
- Overlay enabled with high opacity

### Example 2: Work Documents
Save a preset with:
- Specific window region capture
- German → English translation
- Tesseract engine (faster, lighter)
- Overlay disabled

### Example 3: Multi-Monitor Streaming
Save a preset with:
- Multiple capture regions across monitors
- Korean → English translation
- PaddleOCR engine
- Custom overlay style

## Technical Details

### Storage
Presets are stored in your configuration file under the `presets` key:
```
user_data/config/config.json
```

### Format
Each preset contains:
- `description`: Timestamp and metadata
- `settings`: Complete configuration snapshot

### Backup
It's recommended to export your settings (File menu) periodically to back up your presets.

## Tips

- **Descriptive Names**: Use clear names that describe the use case (e.g., "Dual Monitor - Gaming" instead of "Preset 1")
- **Test Before Saving**: Make sure your configuration works as expected before saving it as a preset
- **Regular Backups**: Export your settings occasionally to preserve your presets
- **Quick Switching**: Use presets to quickly switch between different gaming sessions, work setups, or language pairs

## Troubleshooting

**Preset doesn't appear after saving**
- Check that you entered a valid name
- Try refreshing by switching to another tab and back

**Settings don't apply after loading**
- Some settings may require restarting the translation pipeline
- Click "Start Translation" to apply capture region changes

**Lost presets after update**
- Presets are stored in your config file, which persists across updates
- If lost, restore from a settings export backup
