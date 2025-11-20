# Smart Dictionary Tab - Integration Guide

## Quick Integration Steps

### Step 1: Add Import to Main Settings Dialog

Find your main settings dialog file (the one that creates all tabs) and add:

```python
from ui.settings.smart_dictionary_tab_pyqt6 import SmartDictionaryTab
```

### Step 2: Add Tab in create_tabs() Method

Add this code where you create the other tabs:

```python
# Smart Dictionary tab (NEW!)
smart_dict_tab = SmartDictionaryTab(
    config_manager=self.config_manager,
    pipeline=self.pipeline,  # Pass pipeline reference
    parent=self
)
self.add_tab(smart_dict_tab, "Smart Dictionary")
```

### Step 3: Update Pipeline Management Tab

In `ui/settings/pipeline_management_tab_pyqt6.py`, find the Learning Dictionary section and add a note:

```python
# In _create_translation_stage_section() method
# Find the Learning Dictionary group and add:

dict_settings_note = QLabel(
    "💡 <b>For dictionary settings:</b> See the <b>Smart Dictionary</b> tab"
)
dict_settings_note.setWordWrap(True)
dict_settings_note.setStyleSheet(
    "color: #2196F3; font-size: 8pt; font-style: italic; "
    "padding: 5px; background-color: rgba(33, 150, 243, 0.1); "
    "border-radius: 3px; margin-top: 5px;"
)
dict_layout.addRow("", dict_settings_note)
```

### Step 4: Remove Dictionary Section from Storage Tab (Optional)

If you want to fully move dictionary management to the new tab:

In `ui/settings/storage_tab_pyqt6.py`, find `_create_dictionary_section()` and either:
- **Option A:** Remove it completely
- **Option B:** Replace with a note directing to Smart Dictionary tab

```python
def _create_dictionary_redirect_note(self, parent_layout):
    """Create note directing to Smart Dictionary tab."""
    group = QGroupBox("📚 Smart Dictionary")
    layout = QVBoxLayout(group)
    layout.setContentsMargins(15, 20, 15, 15)
    
    note = QLabel(
        "Dictionary management has moved to the dedicated <b>Smart Dictionary</b> tab.<br><br>"
        "Go to <b>Settings → Smart Dictionary</b> to:<br>"
        "• View and edit dictionary entries<br>"
        "• Export/Import dictionaries<br>"
        "• Configure auto-learning<br>"
        "• Manage language pairs"
    )
    note.setWordWrap(True)
    note.setStyleSheet(
        "color: #2196F3; font-size: 9pt; padding: 15px; "
        "background-color: rgba(33, 150, 243, 0.1); border-radius: 4px; "
        "border-left: 4px solid #2196F3;"
    )
    layout.addWidget(note)
    
    parent_layout.addWidget(group)
```

---

## Recommended Tab Order

```
1. General              (Language, runtime, startup)
2. Capture              (Capture method, FPS, quality)
3. OCR                  (OCR engine, languages)
4. Translation          (Translation engine, API keys)
5. Overlay              (Font, colors, positioning)
6. Smart Dictionary     ← NEW TAB
7. Advanced             (Logging, performance, debug)
8. Pipeline Management  (Plugin configuration)
9. Storage              (Cache, models, storage)
```

---

## What Each Tab Now Handles

### Smart Dictionary Tab (NEW):
- ✅ View all language pair dictionaries
- ✅ Dictionary statistics
- ✅ Edit/Export/Import dictionaries
- ✅ Auto-learn settings
- ✅ Confidence thresholds
- ✅ Max entries limits

### Pipeline Management Tab:
- ✅ Enable/Disable dictionary plugin
- ✅ Note directing to Smart Dictionary tab
- ✅ Other plugin settings

### Storage Tab:
- ✅ Cache management
- ✅ Model management
- ✅ Storage locations
- ❌ Dictionary management (moved to Smart Dictionary tab)

---

## Testing After Integration

1. **Start app**
2. **Open Settings**
3. **Verify new tab appears** between Overlay and Advanced
4. **Click Smart Dictionary tab**
5. **Verify all sections render**
6. **Change a setting**
7. **Click Apply**
8. **Restart app**
9. **Verify setting saved**

---

## Troubleshooting

### Tab doesn't appear:
- Check import statement
- Check add_tab() call
- Check for errors in console

### Settings don't save:
- Verify config_manager passed to tab
- Check save_config() is called
- Check config file permissions

### Pipeline reference missing:
- Pass pipeline to tab constructor
- Check pipeline is not None
- Verify pipeline has dictionary methods

---

## Complete Example

Here's a complete example of integrating the tab:

```python
# In your main settings dialog file (e.g., main_settings_dialog.py)

from ui.settings.base_settings_dialog import BaseSettingsDialog
from ui.settings.general_tab_pyqt6 import GeneralSettingsTab
from ui.settings.capture_tab_pyqt6 import CaptureSettingsTab
from ui.settings.ocr_tab_pyqt6 import OCRSettingsTab
from ui.settings.translation_tab_pyqt6 import TranslationSettingsTab
from ui.settings.overlay_tab_pyqt6 import OverlaySettingsTab
from ui.settings.smart_dictionary_tab_pyqt6 import SmartDictionaryTab  # NEW!
from ui.settings.advanced_tab_pyqt6 import AdvancedSettingsTab
from ui.settings.pipeline_management_tab_pyqt6 import PipelineManagementTab
from ui.settings.storage_tab_pyqt6 import StorageSettingsTab


class MainSettingsDialog(BaseSettingsDialog):
    """Main settings dialog with all tabs."""
    
    def __init__(self, config_manager, pipeline, parent=None):
        self.pipeline = pipeline
        super().__init__(parent, config_manager)
    
    def create_tabs(self):
        """Create all settings tabs."""
        # General tab
        general_tab = GeneralSettingsTab(self.config_manager, self)
        self.add_tab(general_tab, "General")
        
        # Capture tab
        capture_tab = CaptureSettingsTab(self.config_manager, self)
        self.add_tab(capture_tab, "Capture")
        
        # OCR tab
        ocr_tab = OCRSettingsTab(self.config_manager, self)
        ocr_tab.pipeline = self.pipeline
        self.add_tab(ocr_tab, "OCR")
        
        # Translation tab
        translation_tab = TranslationSettingsTab(self.config_manager, self.pipeline, self)
        self.add_tab(translation_tab, "Translation")
        
        # Overlay tab
        overlay_tab = OverlaySettingsTab(self.config_manager, self)
        self.add_tab(overlay_tab, "Overlay")
        
        # Smart Dictionary tab (NEW!)
        smart_dict_tab = SmartDictionaryTab(self.config_manager, self.pipeline, self)
        self.add_tab(smart_dict_tab, "Smart Dictionary")
        
        # Advanced tab
        advanced_tab = AdvancedSettingsTab(self.config_manager, self)
        self.add_tab(advanced_tab, "Advanced")
        
        # Pipeline Management tab
        pipeline_tab = PipelineManagementTab(self.config_manager, self.pipeline, self)
        self.add_tab(pipeline_tab, "Pipeline")
        
        # Storage tab
        storage_tab = StorageSettingsTab(self.config_manager, self.pipeline, self)
        self.add_tab(storage_tab, "Storage")
```

---

**That's it!** The Smart Dictionary tab is now integrated and ready to use.
