"""
Windows Startup Utility
Manages Windows startup registry entries for auto-start functionality.
"""

import sys
import os
from pathlib import Path


def get_executable_path() -> str:
    """
    Get the path to the current executable or script.
    
    Returns:
        Full path to the executable or Python script
    """
    if getattr(sys, 'frozen', False):
        # Running as compiled executable
        return sys.executable
    else:
        # Running as Python script - return path to run.py
        script_path = Path(__file__).parent.parent.parent / "run.py"
        return str(script_path.absolute())


def is_windows_startup_enabled() -> bool:
    """
    Check if application is set to start with Windows.
    
    Returns:
        True if startup entry exists, False otherwise
    """
    if sys.platform != 'win32':
        return False
    
    try:
        import winreg
        
        key = winreg.OpenKey(
            winreg.HKEY_CURRENT_USER,
            r"Software\Microsoft\Windows\CurrentVersion\Run",
            0,
            winreg.KEY_READ
        )
        
        try:
            value, _ = winreg.QueryValueEx(key, "OptikR")
            winreg.CloseKey(key)
            return True
        except FileNotFoundError:
            winreg.CloseKey(key)
            return False
            
    except Exception as e:
        print(f"[WARNING] Failed to check Windows startup status: {e}")
        return False


def set_windows_startup(enable: bool) -> bool:
    """
    Enable or disable application startup with Windows.
    
    Args:
        enable: True to enable startup, False to disable
        
    Returns:
        True if successful, False otherwise
    """
    if sys.platform != 'win32':
        print("[WARNING] Windows startup is only supported on Windows")
        return False
    
    try:
        import winreg
        
        key = winreg.OpenKey(
            winreg.HKEY_CURRENT_USER,
            r"Software\Microsoft\Windows\CurrentVersion\Run",
            0,
            winreg.KEY_SET_VALUE
        )
        
        if enable:
            # Add startup entry
            app_path = get_executable_path()
            
            # If running as Python script, create a command to run with pythonw
            if not getattr(sys, 'frozen', False):
                # Use pythonw to run without console window
                python_exe = sys.executable.replace('python.exe', 'pythonw.exe')
                if not os.path.exists(python_exe):
                    python_exe = sys.executable
                app_path = f'"{python_exe}" "{app_path}"'
            else:
                app_path = f'"{app_path}"'
            
            winreg.SetValueEx(key, "OptikR", 0, winreg.REG_SZ, app_path)
            print(f"[INFO] Windows startup enabled: {app_path}")
            
        else:
            # Remove startup entry
            try:
                winreg.DeleteValue(key, "OptikR")
                print("[INFO] Windows startup disabled")
            except FileNotFoundError:
                # Entry doesn't exist, that's fine
                pass
        
        winreg.CloseKey(key)
        return True
        
    except Exception as e:
        print(f"[ERROR] Failed to set Windows startup: {e}")
        import traceback
        traceback.print_exc()
        return False


def sync_startup_with_config(config_manager) -> bool:
    """
    Synchronize Windows startup state with configuration.
    
    Args:
        config_manager: Configuration manager instance
        
    Returns:
        True if successful, False otherwise
    """
    if not config_manager:
        return False
    
    # Get desired state from config
    should_start = config_manager.get_setting('startup.start_with_windows', False)
    
    # Get current state
    is_enabled = is_windows_startup_enabled()
    
    # Sync if different
    if should_start != is_enabled:
        return set_windows_startup(should_start)
    
    return True
