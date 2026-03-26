@echo off
setlocal enabledelayedexpansion

:: Configuration
set VENV_DIR=.venv
set SETUP_MARKER=%VENV_DIR%\setup_done.marker

echo ====================================================
echo           OptikR Environment Manager
echo ====================================================

:: 1. Check for Python
python --version >nul 2>&1
if %errorlevel% neq 0 (
    echo [ERROR] Python not found. Please install Python 3.10+ and add it to PATH.
    pause
    exit /b
)

:: 2. Create Virtual Environment (Supports 3.12 > 3.11 > 3.10)
py -3.12 -V >nul 2>&1 && set "P=py -3.12" || py -3.11 -V >nul 2>&1 && set "P=py -3.11" || py -3.10 -V >nul 2>&1 && set "P=py -3.10" || (echo [ERROR] Python 3.10-3.12 required! & exit /b)

if not exist %VENV_DIR% (
    echo [INFO] Creating virtual environment using %P%...
    %P% -m venv %VENV_DIR% || (echo [ERROR] Failed to create venv. & pause & exit /b)
)

:: 3. Activate Virtual Environment
call %VENV_DIR%\Scripts\activate

:: 4. Check if installation is needed
if exist %SETUP_MARKER% (
    echo [INFO] Dependencies already installed. Skipping setup...
    goto :run_app
)

:: 5. Ask user for GPU or CPU preference
echo.
echo Select your installation type:
echo [1] GPU (NVIDIA CUDA 12.4)
echo [2] CPU (No GPU acceleration)
echo.
set /p choice="Enter choice [1-2]: "

echo [INFO] Updating pip...
python -m pip install --upgrade pip

:: Step 1: Install core requirements
echo [INFO] Installing core requirements...
pip install -r requirements.txt
pip install -r requirements-windows.txt

:: Step 2: Install PyTorch variant
if "%choice%"=="1" goto :install_gpu
if "%choice%"=="2" goto :install_cpu
goto :install_cpu

:install_gpu
echo [INFO] Installing GPU version (PyTorch with CUDA 12.4)...
pip install -r requirements-gpu.txt
goto :install_audio

:install_cpu
echo [INFO] Installing CPU version...
pip install -r requirements-cpu.txt
goto :install_audio

:install_audio
:: Step 3: Install Audio dependencies
echo [INFO] Installing audio dependencies...
pip install -r requirements-audio.txt

:: Step 4: Install special packages with --no-deps 
echo [INFO] Installing protected dependency packages...
pip install openai-whisper --no-deps
pip install mokuro --no-deps
pip install qwen-vl-utils --no-deps
pip install accelerate --no-deps

:: Create marker file
echo Installation successful > %SETUP_MARKER%
echo [SUCCESS] Environment setup complete.

:run_app
echo.
echo [INFO] Starting OptikR (run.py)...
echo ----------------------------------------------------
python run.py
if %errorlevel% neq 0 (
    echo.
    echo [ERROR] Application exited with an error.
    pause
)
goto :exit_ok

:exit_err
pause
:exit_ok
deactivate
popd