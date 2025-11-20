# Parallel Pipelines - Complete Guide

## How Many Parallel Pipelines Can You Have?

### 🎯 Short Answer: **As Many As Your Hardware Can Handle!**

**Practical Limits:**
- **CPU-bound:** 4-8 pipelines (depends on CPU cores)
- **GPU-bound:** 2-4 pipelines (depends on GPU memory)
- **Memory-bound:** Depends on RAM (each pipeline ~500MB-2GB)

---

## Part 1: Technical Limits

### Hardware Constraints:

#### CPU Cores
```
Your CPU: 8 cores (example)

Pipeline Resource Usage:
├─ Screen Pipeline: 2-3 cores
│  ├─ Capture: 0.5 core
│  ├─ OCR: 1 core
│  └─ Translation: 1 core
│
├─ Audio Pipeline: 2-3 cores
│  ├─ Audio Capture: 0.5 core
│  ├─ Speech-to-Text: 1.5 cores
│  └─ Translation: 1 core
│
└─ Available: 2-3 cores for OS/GUI

Maximum: ~3-4 pipelines before CPU bottleneck
```

#### GPU Memory
```
Your GPU: 8GB VRAM (example)

Model Memory Usage:
├─ EasyOCR: ~2GB
├─ Whisper (STT): ~1.5GB
├─ MarianMT: ~1GB
└─ Available: 3.5GB

Maximum: 2-3 GPU-heavy pipelines
```

#### RAM
```
Your RAM: 16GB (example)

Pipeline Memory:
├─ Screen Pipeline: ~1GB
├─ Audio Pipeline: ~1.5GB
├─ OS + GUI: ~4GB
└─ Available: 9.5GB

Maximum: 6-8 pipelines before RAM bottleneck
```

### Realistic Limits:

| Hardware | Light Pipelines | Heavy Pipelines |
|----------|----------------|-----------------|
| **Low-end** (4 cores, 8GB RAM) | 2-3 | 1-2 |
| **Mid-range** (8 cores, 16GB RAM) | 4-6 | 2-4 |
| **High-end** (16 cores, 32GB RAM) | 8-12 | 4-6 |
| **Workstation** (32 cores, 64GB RAM) | 16-24 | 8-12 |

---

## Part 2: Pipeline Types & Use Cases

### Built-in Pipelines (Bundled with OptikR):

#### 1. Screen Translation Pipeline
```python
screen_pipeline = ScreenTranslationPipeline(
    capture_method="dxcam",
    ocr_engine="easyocr",
    translation_engine="marianmt",
    overlay_style="default"
)
```
**Resource:** ~1GB RAM, 1-2 CPU cores, 2GB GPU

#### 2. Audio Translation Pipeline
```python
audio_pipeline = AudioTranslationPipeline(
    audio_source="system",
    stt_engine="whisper",
    translation_engine="marianmt",
    output_mode="tts"  # or "subtitle"
)
```
**Resource:** ~1.5GB RAM, 2-3 CPU cores, 1.5GB GPU

#### 3. Subtitle Translation Pipeline
```python
subtitle_pipeline = SubtitleTranslationPipeline(
    subtitle_source="file",  # or "stream"
    translation_engine="marianmt",
    output_format="srt"
)
```
**Resource:** ~500MB RAM, 1 CPU core, 1GB GPU

#### 4. Document Translation Pipeline
```python
document_pipeline = DocumentTranslationPipeline(
    input_format="pdf",
    ocr_engine="tesseract",
    translation_engine="marianmt",
    output_format="pdf"
)
```
**Resource:** ~800MB RAM, 1-2 CPU cores, 2GB GPU

#### 5. Chat Translation Pipeline
```python
chat_pipeline = ChatTranslationPipeline(
    chat_source="clipboard",  # or "window"
    translation_engine="marianmt",
    output_mode="overlay"
)
```
**Resource:** ~300MB RAM, 0.5 CPU core, 1GB GPU

---

## Part 3: User-Created Pipelines

### ✅ YES! Users Can Create Custom Pipelines (Even in EXE)

### Method 1: Pipeline Configuration Files

**User creates:** `~/.optikr/pipelines/my_custom_pipeline.json`

```json
{
  "name": "my_custom_pipeline",
  "display_name": "My Custom Pipeline",
  "version": "1.0.0",
  "author": "User Name",
  "description": "Custom pipeline for specific use case",
  "type": "custom",
  "enabled": true,
  
  "stages": [
    {
      "name": "capture",
      "plugin": "screenshot_capture",
      "settings": {
        "region": "custom",
        "x": 100,
        "y": 100,
        "width": 800,
        "height": 600
      }
    },
    {
      "name": "ocr",
      "plugin": "easyocr",
      "settings": {
        "language": "ja",
        "gpu": true
      }
    },
    {
      "name": "translation",
      "plugin": "marianmt",
      "settings": {
        "source_language": "ja",
        "target_language": "en"
      }
    },
    {
      "name": "output",
      "plugin": "overlay",
      "settings": {
        "style": "minimal"
      }
    }
  ],
  
  "settings": {
    "fps": 5,
    "priority": "normal",
    "auto_start": false
  }
}
```

**OptikR loads this automatically!**

### Method 2: Pipeline Plugins

**User creates:** `~/.optikr/plugins/pipelines/my_pipeline/`

```
my_pipeline/
├── pipeline.json       ← Pipeline definition
├── stages/             ← Custom stages (optional)
│   ├── custom_stage_1/
│   │   ├── plugin.json
│   │   └── worker.py
│   └── custom_stage_2/
│       ├── plugin.json
│       └── worker.py
└── README.md
```

**`pipeline.json`:**
```json
{
  "name": "my_pipeline",
  "display_name": "My Custom Pipeline",
  "type": "pipeline_plugin",
  "version": "1.0.0",
  "author": "User Name",
  
  "stages": [
    {
      "name": "custom_capture",
      "type": "custom",
      "plugin_path": "./stages/custom_stage_1"
    },
    {
      "name": "ocr",
      "type": "builtin",
      "plugin": "easyocr"
    },
    {
      "name": "translation",
      "type": "builtin",
      "plugin": "marianmt"
    },
    {
      "name": "custom_output",
      "type": "custom",
      "plugin_path": "./stages/custom_stage_2"
    }
  ]
}
```

---

## Part 4: Pipeline Manager Architecture

### Pipeline Discovery & Loading:

```python
class PipelineManager:
    """Manages multiple parallel pipelines."""
    
    def __init__(self, config_manager):
        self.config_manager = config_manager
        self.pipelines: Dict[str, BasePipeline] = {}
        self.pipeline_threads: Dict[str, threading.Thread] = {}
        
        # Built-in pipeline types
        self.pipeline_types = {
            'screen': ScreenTranslationPipeline,
            'audio': AudioTranslationPipeline,
            'subtitle': SubtitleTranslationPipeline,
            'document': DocumentTranslationPipeline,
            'chat': ChatTranslationPipeline
        }
    
    def discover_pipelines(self) -> List[PipelineMetadata]:
        """Discover all available pipelines."""
        pipelines = []
        
        # 1. Built-in pipelines
        for name, pipeline_class in self.pipeline_types.items():
            pipelines.append(pipeline_class.get_metadata())
        
        # 2. User configuration files
        user_config_dir = Path.home() / ".optikr" / "pipelines"
        if user_config_dir.exists():
            for config_file in user_config_dir.glob("*.json"):
                metadata = self._load_pipeline_config(config_file)
                if metadata:
                    pipelines.append(metadata)
        
        # 3. User pipeline plugins
        user_plugin_dir = Path.home() / ".optikr" / "plugins" / "pipelines"
        if user_plugin_dir.exists():
            for plugin_dir in user_plugin_dir.iterdir():
                if plugin_dir.is_dir():
                    metadata = self._load_pipeline_plugin(plugin_dir)
                    if metadata:
                        pipelines.append(metadata)
        
        return pipelines
    
    def create_pipeline(self, pipeline_name: str, config: dict) -> bool:
        """Create and initialize a pipeline."""
        try:
            # Check if pipeline already exists
            if pipeline_name in self.pipelines:
                return False
            
            # Get pipeline metadata
            metadata = self.get_pipeline_metadata(pipeline_name)
            if not metadata:
                return False
            
            # Create pipeline instance
            if metadata.type == 'builtin':
                pipeline_class = self.pipeline_types[metadata.name]
                pipeline = pipeline_class(config)
            else:
                # User-defined pipeline
                pipeline = self._create_custom_pipeline(metadata, config)
            
            # Store pipeline
            self.pipelines[pipeline_name] = pipeline
            return True
            
        except Exception as e:
            print(f"Failed to create pipeline {pipeline_name}: {e}")
            return False
    
    def start_pipeline(self, pipeline_name: str) -> bool:
        """Start a pipeline in a separate thread."""
        if pipeline_name not in self.pipelines:
            return False
        
        pipeline = self.pipelines[pipeline_name]
        
        # Create thread for pipeline
        thread = threading.Thread(
            target=pipeline.run,
            name=f"Pipeline-{pipeline_name}",
            daemon=True
        )
        
        self.pipeline_threads[pipeline_name] = thread
        thread.start()
        
        return True
    
    def stop_pipeline(self, pipeline_name: str) -> bool:
        """Stop a running pipeline."""
        if pipeline_name not in self.pipelines:
            return False
        
        pipeline = self.pipelines[pipeline_name]
        pipeline.stop()
        
        # Wait for thread to finish
        if pipeline_name in self.pipeline_threads:
            thread = self.pipeline_threads[pipeline_name]
            thread.join(timeout=5.0)
            del self.pipeline_threads[pipeline_name]
        
        return True
    
    def get_running_pipelines(self) -> List[str]:
        """Get list of currently running pipelines."""
        return [
            name for name, pipeline in self.pipelines.items()
            if pipeline.is_running
        ]
    
    def get_pipeline_stats(self, pipeline_name: str) -> dict:
        """Get statistics for a pipeline."""
        if pipeline_name not in self.pipelines:
            return {}
        
        pipeline = self.pipelines[pipeline_name]
        return pipeline.get_stats()
```

---

## Part 5: User Interface for Pipeline Management

### Pipeline Manager UI:

```python
class PipelineManagerTab(QWidget):
    """UI for managing multiple pipelines."""
    
    def __init__(self, pipeline_manager):
        super().__init__()
        self.pipeline_manager = pipeline_manager
        self._init_ui()
    
    def _init_ui(self):
        layout = QVBoxLayout(self)
        
        # Available Pipelines
        available_group = QGroupBox("Available Pipelines")
        available_layout = QVBoxLayout(available_group)
        
        self.pipeline_list = QListWidget()
        self._load_available_pipelines()
        available_layout.addWidget(self.pipeline_list)
        
        # Buttons
        button_layout = QHBoxLayout()
        
        add_btn = QPushButton("➕ Add Pipeline")
        add_btn.clicked.connect(self._add_pipeline)
        button_layout.addWidget(add_btn)
        
        create_btn = QPushButton("🔧 Create Custom")
        create_btn.clicked.connect(self._create_custom_pipeline)
        button_layout.addWidget(create_btn)
        
        import_btn = QPushButton("📥 Import")
        import_btn.clicked.connect(self._import_pipeline)
        button_layout.addWidget(import_btn)
        
        available_layout.addLayout(button_layout)
        layout.addWidget(available_group)
        
        # Active Pipelines
        active_group = QGroupBox("Active Pipelines")
        active_layout = QVBoxLayout(active_group)
        
        self.active_table = QTableWidget()
        self.active_table.setColumnCount(5)
        self.active_table.setHorizontalHeaderLabels([
            "Name", "Status", "FPS", "CPU", "Actions"
        ])
        active_layout.addWidget(self.active_table)
        
        layout.addWidget(active_group)
        
        # Update timer
        self.update_timer = QTimer()
        self.update_timer.timeout.connect(self._update_active_pipelines)
        self.update_timer.start(1000)
    
    def _load_available_pipelines(self):
        """Load available pipelines."""
        pipelines = self.pipeline_manager.discover_pipelines()
        
        for pipeline in pipelines:
            item = QListWidgetItem(
                f"{pipeline.display_name} ({pipeline.type})"
            )
            item.setData(Qt.ItemDataRole.UserRole, pipeline)
            self.pipeline_list.addItem(item)
    
    def _add_pipeline(self):
        """Add selected pipeline to active pipelines."""
        current_item = self.pipeline_list.currentItem()
        if not current_item:
            return
        
        pipeline_metadata = current_item.data(Qt.ItemDataRole.UserRole)
        
        # Show configuration dialog
        dialog = PipelineConfigDialog(pipeline_metadata, self)
        if dialog.exec():
            config = dialog.get_config()
            
            # Create and start pipeline
            success = self.pipeline_manager.create_pipeline(
                pipeline_metadata.name,
                config
            )
            
            if success:
                self.pipeline_manager.start_pipeline(pipeline_metadata.name)
                self._update_active_pipelines()
    
    def _create_custom_pipeline(self):
        """Open custom pipeline creator."""
        dialog = CustomPipelineCreator(self)
        if dialog.exec():
            pipeline_config = dialog.get_pipeline_config()
            
            # Save to user pipelines directory
            user_dir = Path.home() / ".optikr" / "pipelines"
            user_dir.mkdir(parents=True, exist_ok=True)
            
            config_file = user_dir / f"{pipeline_config['name']}.json"
            with open(config_file, 'w') as f:
                json.dump(pipeline_config, f, indent=2)
            
            # Reload available pipelines
            self._load_available_pipelines()
    
    def _import_pipeline(self):
        """Import pipeline from file."""
        file_path, _ = QFileDialog.getOpenFileName(
            self,
            "Import Pipeline",
            "",
            "Pipeline Files (*.json *.zip)"
        )
        
        if file_path:
            # Import pipeline
            self.pipeline_manager.import_pipeline(file_path)
            self._load_available_pipelines()
    
    def _update_active_pipelines(self):
        """Update active pipelines table."""
        running = self.pipeline_manager.get_running_pipelines()
        
        self.active_table.setRowCount(len(running))
        
        for i, pipeline_name in enumerate(running):
            stats = self.pipeline_manager.get_pipeline_stats(pipeline_name)
            
            # Name
            self.active_table.setItem(i, 0, QTableWidgetItem(pipeline_name))
            
            # Status
            status = "Running" if stats.get('is_running') else "Stopped"
            self.active_table.setItem(i, 1, QTableWidgetItem(status))
            
            # FPS
            fps = stats.get('fps', 0)
            self.active_table.setItem(i, 2, QTableWidgetItem(f"{fps:.1f}"))
            
            # CPU
            cpu = stats.get('cpu_usage', 0)
            self.active_table.setItem(i, 3, QTableWidgetItem(f"{cpu:.1f}%"))
            
            # Actions
            actions_widget = QWidget()
            actions_layout = QHBoxLayout(actions_widget)
            actions_layout.setContentsMargins(0, 0, 0, 0)
            
            stop_btn = QPushButton("⏹️")
            stop_btn.clicked.connect(
                lambda checked, name=pipeline_name: self._stop_pipeline(name)
            )
            actions_layout.addWidget(stop_btn)
            
            config_btn = QPushButton("⚙️")
            config_btn.clicked.connect(
                lambda checked, name=pipeline_name: self._configure_pipeline(name)
            )
            actions_layout.addWidget(config_btn)
            
            self.active_table.setCellWidget(i, 4, actions_widget)
```

---

## Part 6: Custom Pipeline Creator

### Visual Pipeline Builder:

```python
class CustomPipelineCreator(QDialog):
    """Visual pipeline builder for users."""
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Create Custom Pipeline")
        self.setMinimumSize(800, 600)
        
        self.stages = []
        self._init_ui()
    
    def _init_ui(self):
        layout = QVBoxLayout(self)
        
        # Pipeline Info
        info_group = QGroupBox("Pipeline Information")
        info_layout = QFormLayout(info_group)
        
        self.name_input = QLineEdit()
        info_layout.addRow("Name:", self.name_input)
        
        self.display_name_input = QLineEdit()
        info_layout.addRow("Display Name:", self.display_name_input)
        
        self.description_input = QTextEdit()
        self.description_input.setMaximumHeight(60)
        info_layout.addRow("Description:", self.description_input)
        
        layout.addWidget(info_group)
        
        # Pipeline Stages
        stages_group = QGroupBox("Pipeline Stages")
        stages_layout = QVBoxLayout(stages_group)
        
        # Stage list
        self.stages_list = QListWidget()
        self.stages_list.setDragDropMode(QListWidget.DragDropMode.InternalMove)
        stages_layout.addWidget(self.stages_list)
        
        # Stage buttons
        stage_buttons = QHBoxLayout()
        
        add_stage_btn = QPushButton("➕ Add Stage")
        add_stage_btn.clicked.connect(self._add_stage)
        stage_buttons.addWidget(add_stage_btn)
        
        remove_stage_btn = QPushButton("➖ Remove Stage")
        remove_stage_btn.clicked.connect(self._remove_stage)
        stage_buttons.addWidget(remove_stage_btn)
        
        edit_stage_btn = QPushButton("✏️ Edit Stage")
        edit_stage_btn.clicked.connect(self._edit_stage)
        stage_buttons.addWidget(edit_stage_btn)
        
        stages_layout.addLayout(stage_buttons)
        layout.addWidget(stages_group)
        
        # Pipeline Settings
        settings_group = QGroupBox("Pipeline Settings")
        settings_layout = QFormLayout(settings_group)
        
        self.fps_spin = QSpinBox()
        self.fps_spin.setRange(1, 60)
        self.fps_spin.setValue(10)
        settings_layout.addRow("FPS:", self.fps_spin)
        
        self.priority_combo = QComboBox()
        self.priority_combo.addItems(["Low", "Normal", "High"])
        self.priority_combo.setCurrentText("Normal")
        settings_layout.addRow("Priority:", self.priority_combo)
        
        self.auto_start_check = QCheckBox()
        settings_layout.addRow("Auto Start:", self.auto_start_check)
        
        layout.addWidget(settings_group)
        
        # Buttons
        button_box = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Ok | 
            QDialogButtonBox.StandardButton.Cancel
        )
        button_box.accepted.connect(self.accept)
        button_box.rejected.connect(self.reject)
        layout.addWidget(button_box)
    
    def _add_stage(self):
        """Add a stage to the pipeline."""
        dialog = StageSelectionDialog(self)
        if dialog.exec():
            stage_info = dialog.get_stage_info()
            self.stages.append(stage_info)
            
            # Add to list
            item = QListWidgetItem(
                f"{stage_info['name']} ({stage_info['plugin']})"
            )
            item.setData(Qt.ItemDataRole.UserRole, stage_info)
            self.stages_list.addItem(item)
    
    def get_pipeline_config(self) -> dict:
        """Get pipeline configuration."""
        return {
            'name': self.name_input.text(),
            'display_name': self.display_name_input.text(),
            'description': self.description_input.toPlainText(),
            'type': 'custom',
            'version': '1.0.0',
            'author': 'User',
            'stages': self.stages,
            'settings': {
                'fps': self.fps_spin.value(),
                'priority': self.priority_combo.currentText().lower(),
                'auto_start': self.auto_start_check.isChecked()
            }
        }
```

---

## Part 7: Example Use Cases

### Use Case 1: Multi-Game Translation
```python
# User plays 3 games simultaneously (streamer setup)
pipeline_manager.create_pipeline("game1_screen", {
    'capture_region': {'x': 0, 'y': 0, 'width': 1920, 'height': 1080},
    'monitor': 0
})

pipeline_manager.create_pipeline("game2_screen", {
    'capture_region': {'x': 0, 'y': 0, 'width': 1920, 'height': 1080},
    'monitor': 1
})

pipeline_manager.create_pipeline("game3_screen", {
    'capture_region': {'x': 0, 'y': 0, 'width': 1920, 'height': 1080},
    'monitor': 2
})

# Start all 3
pipeline_manager.start_pipeline("game1_screen")
pipeline_manager.start_pipeline("game2_screen")
pipeline_manager.start_pipeline("game3_screen")
```

### Use Case 2: Hybrid Translation
```python
# Screen + Audio + Chat translation simultaneously
pipeline_manager.create_pipeline("screen", {
    'type': 'screen',
    'fps': 10
})

pipeline_manager.create_pipeline("audio", {
    'type': 'audio',
    'source': 'system'
})

pipeline_manager.create_pipeline("chat", {
    'type': 'chat',
    'source': 'clipboard'
})

# All running in parallel!
```

### Use Case 3: Multi-Language Translation
```python
# Translate same screen to multiple languages
pipeline_manager.create_pipeline("ja_to_en", {
    'source_lang': 'ja',
    'target_lang': 'en',
    'overlay_position': 'top'
})

pipeline_manager.create_pipeline("ja_to_de", {
    'source_lang': 'ja',
    'target_lang': 'de',
    'overlay_position': 'middle'
})

pipeline_manager.create_pipeline("ja_to_fr", {
    'source_lang': 'ja',
    'target_lang': 'fr',
    'overlay_position': 'bottom'
})
```

---

## Part 8: Resource Management

### Automatic Resource Limiting:

```python
class ResourceManager:
    """Manages resources across multiple pipelines."""
    
    def __init__(self):
        self.max_cpu_usage = 80  # %
        self.max_gpu_memory = 6  # GB
        self.max_ram_usage = 12  # GB
    
    def can_start_pipeline(self, pipeline_metadata) -> bool:
        """Check if resources available for new pipeline."""
        current_usage = self.get_current_usage()
        estimated_usage = self.estimate_pipeline_usage(pipeline_metadata)
        
        # Check CPU
        if current_usage['cpu'] + estimated_usage['cpu'] > self.max_cpu_usage:
            return False
        
        # Check GPU
        if current_usage['gpu'] + estimated_usage['gpu'] > self.max_gpu_memory:
            return False
        
        # Check RAM
        if current_usage['ram'] + estimated_usage['ram'] > self.max_ram_usage:
            return False
        
        return True
    
    def get_recommended_max_pipelines(self) -> int:
        """Get recommended maximum number of pipelines."""
        import psutil
        
        cpu_cores = psutil.cpu_count()
        ram_gb = psutil.virtual_memory().total / (1024**3)
        
        # Conservative estimate: 2 cores per pipeline
        max_by_cpu = cpu_cores // 2
        
        # Conservative estimate: 2GB per pipeline
        max_by_ram = int(ram_gb // 2)
        
        return min(max_by_cpu, max_by_ram)
```

---

## Summary

### How Many Parallel Pipelines?

**Technical Limit:** Unlimited (software-wise)  
**Practical Limit:** 2-8 pipelines (hardware-dependent)  
**Recommended:** 2-4 pipelines for most users

### Can Users Add Pipelines in EXE?

✅ **YES!** Three ways:

1. **Configuration Files** (easiest)
   - Drop JSON file in `~/.optikr/pipelines/`
   - OptikR loads automatically

2. **Pipeline Plugins** (advanced)
   - Create plugin folder with custom stages
   - Full flexibility

3. **Visual Builder** (user-friendly)
   - Drag-and-drop pipeline creator
   - No coding required!

### Example Scenarios:

```
Casual User: 1-2 pipelines
├─ Screen translation
└─ Audio translation (optional)

Power User: 3-4 pipelines
├─ Screen translation (game)
├─ Audio translation (voice chat)
├─ Chat translation (text chat)
└─ Subtitle translation (video)

Streamer: 4-6 pipelines
├─ Game 1 screen
├─ Game 2 screen
├─ Audio (game + voice)
├─ Chat (multiple platforms)
├─ Subtitle (stream overlay)
└─ Document (reference materials)
```

**All user-configurable, even in EXE!** 🚀

---

*Guide Date: November 14, 2025*  
*Parallel pipelines: Unlimited potential, hardware-limited reality*
