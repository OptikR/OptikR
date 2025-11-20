# OptikR Plugin System - Deployment Guide

**Complete guide for deploying the plugin system**

---

## Table of Contents

1. [Prerequisites](#prerequisites)
2. [Development Setup](#development-setup)
3. [Building for Production](#building-for-production)
4. [EXE Distribution](#exe-distribution)
5. [Plugin Distribution](#plugin-distribution)
6. [Configuration](#configuration)
7. [Troubleshooting](#troubleshooting)

---

## Prerequisites

### System Requirements

**Minimum:**
- Windows 10/11
- Python 3.7+
- 4 GB RAM
- 2 GB disk space

**Recommended:**
- Windows 10/11
- Python 3.10+
- 8 GB RAM
- 5 GB disk space
- CUDA-capable GPU (optional)

### Required Software

```bash
# Python 3.10+
python --version

# pip (latest)
python -m pip install --upgrade pip

# Git (for cloning)
git --version
```

---

## Development Setup

### 1. Clone Repository

```bash
git clone https://github.com/your-org/OptikR.git
cd OptikR/dev
```

### 2. Install Dependencies

```bash
# Core dependencies
pip install PyQt6 numpy opencv-python

# Subprocess system
pip install psutil

# Plugin system (built-in plugins)
pip install dxcam easyocr transformers torch

# Optional: GPU support
pip install torch torchvision --index-url https://download.pytorch.org/whl/cu118
```

### 3. Verify Installation

```bash
# Run tests
python tests/run_all_tests.py

# Test plugin manager
python test_plugin_manager.py

# Test UI
python test_plugin_ui.py
```

### 4. Run Application

```bash
python run.py
```

---

## Building for Production

### 1. Install PyInstaller

```bash
pip install pyinstaller
```

### 2. Create Spec File

Create `optikr.spec`:

```python
# -*- mode: python ; coding: utf-8 -*-

block_cipher = None

a = Analysis(
    ['run.py'],
    pathex=[],
    binaries=[],
    datas=[
        # Include plugins
        ('plugins', 'plugins'),
        
        # Include worker scripts
        ('src/workflow/workers', 'src/workflow/workers'),
        ('src/workflow/base', 'src/workflow/base'),
        
        # Include styles
        ('styles', 'styles'),
        
        # Include translations
        ('translations', 'translations'),
        
        # Include config
        ('config', 'config'),
    ],
    hiddenimports=[
        # Subprocess system
        'src.workflow.base.base_subprocess',
        'src.workflow.base.base_worker',
        'src.workflow.base.plugin_interface',
        'src.workflow.subprocess_manager',
        'src.workflow.plugin_manager',
        
        # Subprocesses
        'src.workflow.subprocesses.capture_subprocess',
        'src.workflow.subprocesses.ocr_subprocess',
        'src.workflow.subprocesses.translation_subprocess',
        
        # Workers
        'src.workflow.workers.capture_worker',
        'src.workflow.workers.ocr_worker',
        'src.workflow.workers.translation_worker',
        
        # Built-in plugin dependencies
        'dxcam',
        'easyocr',
        'transformers',
        'torch',
        
        # PyQt6
        'PyQt6.QtCore',
        'PyQt6.QtGui',
        'PyQt6.QtWidgets',
    ],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[],
    win_no_prefer_redirects=False,
    win_private_assemblies=False,
    cipher=block_cipher,
    noarchive=False,
)

pyz = PYZ(a.pure, a.zipped_data, cipher=block_cipher)

exe = EXE(
    pyz,
    a.scripts,
    a.binaries,
    a.zipfiles,
    a.datas,
    [],
    name='OptikR',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    upx_exclude=[],
    runtime_tmpdir=None,
    console=False,  # GUI application
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
    icon='icon.ico',  # Add your icon
    # IMPORTANT: Enable multiprocessing for subprocesses
    multiprocessing=True,
)
```

### 3. Build EXE

```bash
# Build
pyinstaller optikr.spec

# Output will be in dist/OptikR
```

### 4. Test EXE

```bash
cd dist
OptikR
```

---

## EXE Distribution

### Directory Structure

```
OptikR-v1.0/
├── OptikR              # Main executable
├── plugins/                # External plugins folder
│   ├── capture/
│   ├── ocr/
│   ├── translation/
│   └── optimizer/
├── config/                 # Configuration files
│   └── settings.json
├── logs/                   # Log files
├── README.txt             # User instructions
└── LICENSE.txt            # License
```

### Creating Installer

**Option 1: Inno Setup**

```iss
[Setup]
AppName=OptikR
AppVersion=1.0
DefaultDirName={pf}\OptikR
DefaultGroupName=OptikR
OutputDir=installer
OutputBaseFilename=OptikR-Setup-v1.0

[Files]
Source: "dist\OptikR"; DestDir: "{app}"
Source: "plugins\*"; DestDir: "{app}\plugins"; Flags: recursesubdirs
Source: "config\*"; DestDir: "{app}\config"; Flags: recursesubdirs
Source: "README.txt"; DestDir: "{app}"
Source: "LICENSE.txt"; DestDir: "{app}"

[Icons]
Name: "{group}\OptikR"; Filename: "{app}\OptikR"
Name: "{commondesktop}\OptikR"; Filename: "{app}\OptikR"

[Run]
Filename: "{app}\OptikR"; Description: "Launch OptikR"; Flags: postinstall nowait skipifsilent
```

**Option 2: ZIP Distribution**

```bash
# Create ZIP
7z a OptikR-v1.0.zip OptikR-v1.0/

# Or use PowerShell
Compress-Archive -Path OptikR-v1.0 -DestinationPath OptikR-v1.0.zip
```

---

## Plugin Distribution

### Built-in Plugins

**Included in EXE:**
- DXCam Capture
- EasyOCR
- MarianMT Translation

**Location:** Bundled in EXE temp folder

### External Plugins

**Location:** `plugins/` folder next to EXE

**Distribution:**
1. Create plugin folder
2. Include plugin.json, worker.py, README.md
3. ZIP the folder
4. Share on GitHub/website

**Installation:**
1. Download plugin ZIP
2. Extract to `OptikR/plugins/{type}/`
3. Restart OptikR or click "Rescan Plugins"

---

## Configuration

### Application Settings

**Location:** `config/settings.json`

```json
{
  "ui": {
    "language": "en",
    "theme": "dark"
  },
  "pipeline": {
    "fps": 10,
    "source_language": "en",
    "target_language": "de"
  },
  "plugins": {
    "directories": ["plugins/"],
    "auto_enable": true
  }
}
```

### Plugin Settings

**Location:** `config/plugin_settings.json`

```json
{
  "dxcam_capture": {
    "enabled": true,
    "settings": {
      "target_fps": 60,
      "color_mode": "BGR"
    }
  },
  "easyocr": {
    "enabled": true,
    "settings": {
      "language": "en",
      "gpu": true,
      "min_confidence": 0.5
    }
  }
}
```

---

## Troubleshooting

### Build Issues

**"Module not found"**
```bash
# Add to hiddenimports in spec file
hiddenimports=['missing_module']
```

**"DLL load failed"**
```bash
# Include DLL in binaries
binaries=[('path/to/dll', '.')]
```

**"Multiprocessing not working"**
```python
# Ensure in spec file:
exe = EXE(..., multiprocessing=True)
```

### Runtime Issues

**"Plugins not found"**
- Check `plugins/` folder exists
- Check plugin.json is valid
- Click "Rescan Plugins"

**"Subprocess failed to start"**
- Check worker script exists
- Check Python dependencies installed
- Check logs for errors

**"Out of memory"**
- Close other applications
- Reduce FPS
- Disable unused plugins

---

## Performance Optimization

### Build Optimization

```bash
# Use UPX compression
upx=True

# Exclude unnecessary modules
excludes=['tkinter', 'matplotlib']

# One-file mode (slower startup)
onefile=True
```

### Runtime Optimization

```python
# In config
{
  "pipeline": {
    "fps": 10,  # Lower = less CPU
    "batch_size": 8  # Higher = more throughput
  }
}
```

---

## Security

### Code Signing

```bash
# Sign EXE (Windows)
signtool sign /f certificate.pfx /p password OptikR
```

### Plugin Verification

- Only install plugins from trusted sources
- Review plugin code before enabling
- Check plugin author and reviews

---

## Updates

### Application Updates

1. Build new version
2. Increment version number
3. Create changelog
4. Distribute new EXE

### Plugin Updates

1. Update plugin files
2. Increment version in plugin.json
3. Redistribute plugin folder
4. Users replace old folder

---

## Monitoring

### Logs

**Location:** `logs/`

```
logs/
├── app.log          # Application logs
├── subprocess.log   # Subprocess logs
└── plugin.log       # Plugin logs
```

### Metrics

```python
# Get metrics
metrics = pipeline.get_metrics()

# Metrics include:
- frames_processed
- translations_count
- errors_count
- subprocess_status
```

---

## Backup & Recovery

### Backup

```bash
# Backup configuration
copy config\*.json backup\

# Backup plugins
xcopy plugins backup\plugins\ /E /I
```

### Recovery

```bash
# Restore configuration
copy backup\*.json config\

# Restore plugins
xcopy backup\plugins plugins\ /E /I
```

---

## Support

### Getting Help

- Documentation: `docs/`
- Issues: GitHub Issues
- Email: support@optikr.com

### Reporting Bugs

Include:
- OptikR version
- Windows version
- Error message
- Steps to reproduce
- Log files

---

## Checklist

### Pre-Release

- [ ] All tests passing
- [ ] Documentation complete
- [ ] Version number updated
- [ ] Changelog created
- [ ] EXE built and tested
- [ ] Installer created
- [ ] Code signed (optional)

### Release

- [ ] Upload to website
- [ ] Create GitHub release
- [ ] Announce on social media
- [ ] Update documentation
- [ ] Monitor for issues

### Post-Release

- [ ] Collect feedback
- [ ] Fix critical bugs
- [ ] Plan next version
- [ ] Update roadmap

---

## Conclusion

The OptikR Plugin System is ready for production deployment with:
- ✅ Complete build process
- ✅ EXE distribution
- ✅ Plugin system
- ✅ Documentation
- ✅ Testing

**Status:** Production Ready 🚀

---

**For more information:**
- Architecture: `SYSTEM_ARCHITECTURE.md`
- User Manual: `USER_MANUAL.md`
- Developer Guide: `DEVELOPER_GUIDE.md`
