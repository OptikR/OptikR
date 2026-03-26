#!/bin/bash

# Configuration
VENV_DIR=".venv"
SETUP_MARKER="${VENV_DIR}/setup_done.marker"

echo "===================================================="
echo "          OptikR Environment Manager"
echo "===================================================="

# Helper function to emulate Windows 'pause'
pause() {
    read -n 1 -s -r -p "Press any key to continue..."
    echo ""
}

# 1. Check for Python
if ! command -v python3 >/dev/null 2>&1; then
    echo "[ERROR] Python not found. Please install Python 3.10+ and add it to your PATH."
    pause
    exit 1
fi

# 2. Create Virtual Environment (Supports 3.12 > 3.11 > 3.10)
P=""
# Try explicit version binaries first
for py in python3.12 python3.11 python3.10; do
    if command -v "$py" >/dev/null 2>&1; then
        P="$py"
        break
    fi
done

# Fallback to default python3 if explicit binaries aren't mapped
if [ -z "$P" ]; then
    PY_VER=$(python3 -c 'import sys; print(f"{sys.version_info.major}.{sys.version_info.minor}")' 2>/dev/null)
    if [[ "$PY_VER" == "3.10" || "$PY_VER" == "3.11" || "$PY_VER" == "3.12" ]]; then
        P="python3"
    fi
fi

if [ -z "$P" ]; then
    echo "[ERROR] Python 3.10-3.12 required!"
    pause
    exit 1
fi

if [ ! -d "$VENV_DIR" ]; then
    echo "[INFO] Creating virtual environment using $P..."
    if ! $P -m venv "$VENV_DIR"; then
        echo "[ERROR] Failed to create venv."
        pause
        exit 1
    fi
fi

# 3. Activate Virtual Environment
source "${VENV_DIR}/bin/activate"

# 4. Check if installation is needed
if [ -f "$SETUP_MARKER" ]; then
    echo "[INFO] Dependencies already installed. Skipping setup..."
else
    # 5. Ask user for GPU or CPU preference
    echo ""
    echo "Select your installation type:"
    echo "[1] GPU (NVIDIA CUDA 12.4)"
    echo "[2] CPU (No GPU acceleration)"
    echo ""
    read -p "Enter choice [1-2]: " choice

    echo "[INFO] Updating pip..."
    python -m pip install --upgrade pip

    # Step 1: Install core requirements
    echo "[INFO] Installing core requirements..."
    pip install -r requirements.txt
    pip install -r requirements-linux.txt

    # Step 2: Install PyTorch variant
    if [ "$choice" == "1" ]; then
        echo "[INFO] Installing GPU version (PyTorch with CUDA 12.4)..."
        pip install -r requirements-gpu.txt
    else
        echo "[INFO] Installing CPU version..."
        pip install -r requirements-cpu.txt
    fi

    # Step 3: Install Audio dependencies
    echo "[INFO] Installing audio dependencies..."
    pip install -r requirements-audio.txt

    # Step 4: Install special packages with --no-deps
    echo "[INFO] Installing protected dependency packages..."
    pip install openai-whisper --no-deps
    pip install mokuro --no-deps
    pip install qwen-vl-utils --no-deps
    pip install accelerate --no-deps

    # Create marker file
    echo "Installation successful" > "$SETUP_MARKER"
    echo "[SUCCESS] Environment setup complete."
fi

# Run the app
echo ""
echo "[INFO] Starting OptikR (run.py)..."
echo "----------------------------------------------------"
python run.py

if [ $? -ne 0 ]; then
    echo ""
    echo "[ERROR] Application exited with an error."
    pause
fi

deactivate
