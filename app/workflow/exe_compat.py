"""
EXE Compatibility - Helpers for running as Windows EXE.

Handles:
- Worker script path resolution
- Plugin directory location
- Subprocess spawning in frozen state
"""

import sys
from pathlib import Path
from typing import Optional


def is_frozen() -> bool:
    """Check if running as frozen EXE (PyInstaller/cx_Freeze)."""
    return getattr(sys, 'frozen', False)


def get_base_path() -> Path:
    """
    Get base path for the application.
    
    Returns:
        Path to application root (EXE dir or project root)
    """
    if is_frozen():
        # Running as EXE - use EXE directory
        return Path(sys.executable).parent
    else:
        # Running as script - use project root
        return Path(__file__).parent.parent.parent


def get_temp_path() -> Optional[Path]:
    """
    Get temporary extraction path (PyInstaller only).
    
    Returns:
        Path to PyInstaller temp folder or None
    """
    if is_frozen() and hasattr(sys, '_MEIPASS'):
        return Path(sys._MEIPASS)
    return None


def get_worker_script_path(worker_script: str) -> str:
    """
    Get correct path for worker script.
    
    Works in both development and frozen EXE.
    
    Args:
        worker_script: Relative path to worker script (e.g., "plugins/capture/worker.py")
        
    Returns:
        Absolute path to worker script
    """
    if is_frozen():
        # In EXE, worker scripts are in temp extraction folder
        temp_path = get_temp_path()
        if temp_path:
            # Try temp folder first (bundled scripts)
            bundled_path = temp_path / worker_script
            if bundled_path.exists():
                return str(bundled_path)
        
        # Try relative to EXE (external plugins)
        exe_path = get_base_path() / worker_script
        if exe_path.exists():
            return str(exe_path)
        
        # Fallback to relative path
        return worker_script
    else:
        # In development, use project root
        return str(get_base_path() / worker_script)


def get_plugin_directory() -> Path:
    """
    Get plugin directory path.
    
    Returns:
        Path to plugins directory
    """
    base = get_base_path()
    return base / "plugins"


def get_executable() -> str:
    """
    Get path to Python executable or EXE.
    
    Returns:
        Path to executable that can spawn subprocesses
    """
    return sys.executable


def get_subprocess_args(worker_script: str) -> list:
    """
    Get subprocess arguments for spawning worker.
    
    Args:
        worker_script: Relative path to worker script
        
    Returns:
        List of arguments for subprocess.Popen
    """
    executable = get_executable()
    script_path = get_worker_script_path(worker_script)
    
    if is_frozen():
        # When frozen, EXE can run Python scripts directly
        # PyInstaller includes Python interpreter
        return [executable, script_path]
    else:
        # In development, use Python interpreter
        return [executable, script_path]


# PyInstaller spec file configuration
PYINSTALLER_SPEC_NOTES = """
# Add to your .spec file for proper subprocess support:

a = Analysis(
    ['run.py'],
    pathex=[],
    binaries=[],
    datas=[
        # Include worker scripts
        ('app/workflow/workers', 'app/workflow/workers'),
        ('plugins', 'plugins'),  # Include plugins
    ],
    hiddenimports=[
        'src.workflow.base.base_worker',
        'src.workflow.subprocesses',
        # Add all worker modules
    ],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[],
    win_no_prefer_redirects=False,
    win_private_assemblies=False,
    cipher=None,
    noarchive=False,
)

# Important: Enable multiprocessing support
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
    console=False,  # Set to True for debugging
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
    # IMPORTANT: Enable multiprocessing
    multiprocessing=True,
)
"""


def print_debug_info():
    """Print debug information about execution environment."""
    print("=" * 60)
    print("EXECUTION ENVIRONMENT")
    print("=" * 60)
    print(f"Frozen: {is_frozen()}")
    print(f"Executable: {get_executable()}")
    print(f"Base Path: {get_base_path()}")
    print(f"Temp Path: {get_temp_path()}")
    print(f"Plugin Dir: {get_plugin_directory()}")
    print("=" * 60)


if __name__ == '__main__':
    # Test the compatibility helpers
    print_debug_info()
