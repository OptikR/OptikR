# Visual Guide - New Features

## 1. First-Run Dialog Flow

```
┌─────────────────────────────────────────────────────────┐
│  Welcome to OptikR!                                     │
│  Please read and understand the following...            │
├─────────────────────────────────────────────────────────┤
│                                                         │
│  ┌───────────────────────────────────────────────────┐ │
│  │ What This Application Does:                       │ │
│  │                                                   │ │
│  │ 1. Screen Capture                                │ │
│  │    • Captures selected screen region             │ │
│  │    • Only when you click "Start"                 │ │
│  │                                                   │ │
│  │ 2. Data Processing                               │ │
│  │    • OCR extracts text from images               │ │
│  │    • Translation engines translate text          │ │
│  │                                                   │ │
│  │ [... more consent text ...]                      │ │
│  └───────────────────────────────────────────────────┘ │
│                                                         │
│  ☑ I have read and understand the above...             │
│                                                         │
│                    [Decline & Exit]  [Accept & Continue →] │
└─────────────────────────────────────────────────────────┘
                            ↓
                    User clicks "Accept & Continue"
                            ↓
┌─────────────────────────────────────────────────────────┐
│  Model Setup                                            │
│  Choose how you want to set up OCR and translation...  │
├─────────────────────────────────────────────────────────┤
│                                                         │
│  ⦿ 🌐 Online Mode (Recommended)                         │
│     • Models download automatically when needed         │
│     • First run: ~500MB download (2-3 minutes)         │
│     • All future runs: Instant (uses cached models)    │
│     • Requires internet connection for first run       │
│                                                         │
│  ○ 📦 Offline Mode (Advanced)                           │
│     • Select your pre-downloaded model files           │
│     • Files will be copied to correct locations        │
│     • Plugins will be generated automatically          │
│     • No internet required after setup                 │
│                                                         │
│     ┌─────────────────────────────────────────────┐   │
│     │ Select Model Files                          │   │
│     │                                             │   │
│     │ OCR Files: [No files selected...]          │   │
│     │            [Select Files...]                │   │
│     │                                             │   │
│     │ Translation: [No folder selected...]       │   │
│     │              [Select Folder...]            │   │
│     └─────────────────────────────────────────────┘   │
│                                                         │
│  ○ ⏭️ Skip Setup                                        │
│     • Configure models later in Settings               │
│     • OCR and translation disabled until configured    │
│                                                         │
│                         [← Back]      [Finish Setup]    │
└─────────────────────────────────────────────────────────┘
```

## 2. Offline Mode File Selection

```
User clicks "Select Files..." for OCR
         ↓
┌─────────────────────────────────────────┐
│  Select OCR Model Files                 │
├─────────────────────────────────────────┤
│  Look in: E:\MyModels\                  │
│                                         │
│  📁 ..                                  │
│  📄 craft_mlt_25k.pth        83 MB     │ ← Select
│  📄 english_g2.pth           15 MB     │ ← Select
│  📄 japanese_g2.pth          17 MB     │
│  📄 korean_g2.pth            16 MB     │
│                                         │
│  File type: Model Files (*.pth *.pt)   │
│                                         │
│                    [Open]    [Cancel]   │
└─────────────────────────────────────────┘
         ↓
Shows: "2 file(s): craft_mlt_25k.pth, english_g2.pth"

User clicks "Select Folder..." for Translation
         ↓
┌─────────────────────────────────────────┐
│  Select Translation Model Folder        │
├─────────────────────────────────────────┤
│  Look in: E:\MyModels\                  │
│                                         │
│  📁 ..                                  │
│  📁 opus-mt-en-de                       │ ← Select
│  📁 opus-mt-en-ja                       │
│  📁 opus-mt-en-es                       │
│                                         │
│                    [Select]  [Cancel]   │
└─────────────────────────────────────────┘
         ↓
Shows: "opus-mt-en-de"

User clicks "Finish Setup"
         ↓
┌─────────────────────────────────────────┐
│  Setting up offline models...           │
├─────────────────────────────────────────┤
│  ████████████████░░░░░░░░░░░  60%      │
│                                         │
│  Copying OCR model files...             │
│                                         │
│                           [Cancel]      │
└─────────────────────────────────────────┘
         ↓
┌─────────────────────────────────────────┐
│  Setup Complete                         │
├─────────────────────────────────────────┤
│  Offline models have been installed     │
│  successfully!                          │
│                                         │
│  Models copied to:                      │
│  • OCR: models/ocr/                     │
│  • Translation: models/language/        │
│                                         │
│  Plugins have been generated            │
│  automatically.                         │
│                                         │
│                              [OK]       │
└─────────────────────────────────────────┘
```

## 3. Fullscreen Performance Warning

```
User has fullscreen capture region set
User clicks "▶ Start" button
         ↓
┌─────────────────────────────────────────┐
│  Performance Tip                        │
├─────────────────────────────────────────┤
│  ⚠️ You are capturing the entire        │
│  screen.                                │
│                                         │
│  For better performance, consider       │
│  selecting a smaller capture region     │
│  that only includes the area you want   │
│  to translate.                          │
│                                         │
│  You can change the region using        │
│  'Select Capture Region' button.        │
│                                         │
│  Continue with fullscreen capture?      │
│                                         │
│                      [Yes]    [No]      │
└─────────────────────────────────────────┘
         ↓                    ↓
    Continues            Returns to
    with start           main window
```

## 4. File Structure After Offline Setup

```
OptikR/
├── OptikR
├── models/                    ← Created automatically
│   ├── ocr/                   ← OCR files copied here
│   │   ├── craft_mlt_25k.pth
│   │   └── english_g2.pth
│   └── language/              ← Translation folders copied here
│       └── opus-mt-en-de/
│           ├── config.json
│           ├── pytorch_model.bin
│           └── ...
├── plugins/                   ← Plugins generated here
│   ├── ocr/
│   │   └── custom_offline_ocr/
│   │       └── plugin.json    ← Auto-generated
│   └── translation/
│       └── custom_opus-mt-en-de/
│           └── plugin.json    ← Auto-generated
└── config/
    └── system_config.json     ← Setup saved here
```

## 5. Generated Plugin Example

**File:** `plugins/ocr/custom_offline_ocr/plugin.json`

```json
{
  "name": "custom_offline_ocr",
  "display_name": "Custom Offline OCR",
  "version": "1.0.0",
  "type": "ocr",
  "description": "Custom OCR models installed via offline setup",
  "author": "User",
  "enabled": true,
  "models_path": "D:/OptikR/models/ocr/",
  "settings": {
    "confidence_threshold": {
      "type": "float",
      "default": 0.5,
      "min": 0.0,
      "max": 1.0,
      "description": "Minimum confidence threshold"
    }
  }
}
```

## 6. Main Window with Fullscreen Warning

```
┌────────────────────────────────────────────────────────────┐
│  OptikR                                          [_][□][X]  │
├────────────────────────────────────────────────────────────┤
│ ┌──────┐                                                   │
│ │      │  General  Capture  OCR  Translation  Overlay     │
│ │ 📊   │  ─────────────────────────────────────────────   │
│ │      │                                                   │
│ │ FPS  │  [Settings content here...]                      │
│ │ 0.0  │                                                   │
│ │      │                                                   │
│ │ CPU  │                                                   │
│ │ 15%  │                                                   │
│ │      │                                                   │
│ │ GPU  │                                                   │
│ │ 0%   │                                                   │
│ │      │                                                   │
│ │ MEM  │                                                   │
│ │ 2.1  │                                                   │
│ └──────┘                                                   │
├────────────────────────────────────────────────────────────┤
│ [▶ Start] [🖥 Select Region] [📊 Monitor] [❓ Help] ...   │
└────────────────────────────────────────────────────────────┘
         ↓ User clicks "▶ Start"
         ↓ Fullscreen detected
         ↓
┌─────────────────────────────────────────┐
│  Performance Tip                        │
│  ⚠️ You are capturing the entire screen │
│  ...                                    │
│                      [Yes]    [No]      │
└─────────────────────────────────────────┘
```

## 7. Comparison: Before vs After

### Before (Not EXE-Friendly):
```
User provides folder paths
         ↓
App reads from external locations
         ↓
❌ Doesn't work with EXE
❌ Models must stay in original location
❌ Not portable
```

### After (EXE-Friendly):
```
User selects files
         ↓
App copies to models/
         ↓
App generates plugins/
         ↓
✅ Works with EXE
✅ Self-contained
✅ Portable
✅ Clean uninstall
```

## 8. Decision Tree

```
                    First Run?
                        │
            ┌───────────┴───────────┐
           Yes                      No
            │                        │
    Show Consent Dialog         Skip Dialog
            │                        │
    ┌───────┴───────┐               │
Accept          Decline              │
    │               │                │
Setup Page      Exit App             │
    │                                │
    ├─ Online Mode ──────────────────┤
    ├─ Offline Mode ─────────────────┤
    └─ Skip Setup ───────────────────┤
                                     │
                            Start Application
                                     │
                            User clicks "Start"
                                     │
                            Fullscreen?
                                     │
                        ┌────────────┴────────────┐
                       Yes                       No
                        │                         │
                Show Warning              Start Immediately
                        │
                ┌───────┴───────┐
            Continue        Change Region
                │                 │
        Start Translation    Return to Main
```

