# How To Run OptikR

## Quick Answer

```bash
python run.py
```

That is usually all you need. On first launch, OptikR automatically installs all dependencies (including PyTorch) and restarts itself. No manual `pip install` step is required under normal conditions.

## What Happens On First Launch

When you run `python run.py` for the first time, the bootstrap module performs a two-step setup:

1. **Step 1/2 — Core dependencies**: Installs everything listed in `requirements.txt` via pip (OCR engines, translation libraries, UI framework, image processing, etc.).
2. **Step 2/2 — PyTorch**: Detects whether you have an NVIDIA GPU with CUDA. If yes, installs the CUDA-enabled PyTorch build. If no, installs the CPU-only build. After PyTorch installs, the application restarts itself automatically.

On subsequent launches, both steps are skipped because the packages are already present.

## When Auto-Install Works

The automatic setup succeeds when:

- Python 3.10 or later is installed
- `pip` is available in the active Python environment
- Internet access is available for package downloads
- No corporate proxy or firewall blocks PyPI or the PyTorch package index
- The user has permission to install packages (not in a locked-down system Python)

## When Manual Installation Is Required

If automatic setup fails (network restrictions, permission issues, or pip errors), install manually:

**CPU-only systems:**

```bash
pip install -r requirements.txt
pip install -r requirements-cpu.txt
```

**NVIDIA GPU systems (CUDA 12.4):**

```bash
pip install -r requirements.txt
pip install -r requirements-gpu.txt
```

Then run:

```bash
python run.py
```

---

## CUDA Toolkit — What It Is and Why You Should Install It

### What is the CUDA Toolkit?

The CUDA Toolkit is NVIDIA's GPU programming platform. It allows PyTorch (and therefore OptikR's OCR and translation engines) to run computations on your GPU instead of your CPU.

### Why install it?

GPU acceleration provides a **3-6x speedup** across the entire pipeline:

| Component | CPU | GPU (CUDA) |
|-----------|-----|------------|
| OCR (EasyOCR) | ~200ms per frame | ~50ms per frame |
| Translation (MarianMT) | ~100ms per batch | ~30ms per batch |
| Overall pipeline | ~10 FPS | ~30-50 FPS |

Without CUDA, OptikR still works — it falls back to CPU mode automatically. But if you have an NVIDIA GPU, installing CUDA unlocks significantly better performance.

### How OptikR detects CUDA

During bootstrap, OptikR's `PyTorchManager` checks:

1. Whether the CUDA toolkit is installed in standard locations (`C:\Program Files\NVIDIA GPU Computing Toolkit\CUDA` on Windows, `/usr/local/cuda` on Linux)
2. Whether an NVIDIA driver is available (via `nvidia-smi`)
3. If either is found, it installs PyTorch with CUDA support; otherwise it installs the CPU-only build

### How to install the CUDA Toolkit

**Prerequisites:**
- An NVIDIA GPU (GeForce, RTX, Quadro, etc.)
- Up-to-date NVIDIA drivers

**Steps:**

1. Download the CUDA Toolkit from https://developer.nvidia.com/cuda-downloads
2. Select your operating system and architecture
3. Download CUDA Toolkit 12.x (recommended: 12.4 for best compatibility with current PyTorch builds)
4. Run the installer and choose "Express Installation"
5. **Restart your computer** after installation (required for driver paths to load)

**Verification:**

```bash
nvcc --version
```

This should print the CUDA compiler version. If it does, CUDA is correctly installed.

### Do I need CUDA?

| Situation | Recommendation |
|-----------|---------------|
| NVIDIA GPU available | Install CUDA — significant speedup |
| AMD GPU only | Skip — CUDA is NVIDIA-only; OptikR runs on CPU |
| No dedicated GPU | Skip — CPU mode works fine |
| Laptop with integrated graphics | Skip unless it has an NVIDIA GPU |

### Visual C++ Redistributable

Some CUDA and PyTorch libraries depend on the Visual C++ Redistributable. If you see "DLL load failed" errors on Windows:

1. Download from https://aka.ms/vs/17/release/vc_redist.x64.exe
2. Install and restart your computer

---

## System Requirements

### Minimum

- **OS**: Windows 10/11 (primary), Linux (supported)
- **CPU**: Dual-core 2.0 GHz
- **RAM**: 4 GB
- **Storage**: 2 GB free
- **Python**: 3.10+

### Recommended

- **OS**: Windows 10/11
- **CPU**: Quad-core 3.0 GHz
- **RAM**: 8 GB
- **GPU**: NVIDIA GPU with CUDA support
- **Storage**: 5 GB free (for AI models)
- **Python**: 3.10 or 3.11

---

## CLI Options

OptikR supports several command-line flags:

```bash
python run.py                        # Normal launch
python run.py --create-plugin        # Interactive plugin generator
python run.py --auto-generate-missing # Scan and generate missing plugins
python run.py --health-check         # Run system health check
```
