"""
PyTorch Version Manager

Handles switching between CPU and CUDA versions of PyTorch.
"""

import subprocess
import sys
import os
from typing import Tuple, Optional
from enum import Enum


class PyTorchVersion(Enum):
    """PyTorch version types."""
    CPU = "cpu"
    CUDA_118 = "cu118"
    CUDA_121 = "cu121"
    CUDA_124 = "cu124"


class PyTorchManager:
    """Manages PyTorch installation and version switching."""
    
    def __init__(self):
        """Initialize PyTorch manager."""
        self.current_version = self.detect_current_version()
    
    def detect_current_version(self) -> Tuple[str, bool]:
        """Detect currently installed PyTorch version.
        
        Returns:
            Tuple of (version_string, cuda_available)
        """
        try:
            import torch
            version = getattr(torch, '__version__', 'Unknown')
            cuda_available = torch.cuda.is_available() if hasattr(torch.cuda, 'is_available') else False
            return version, cuda_available
        except (ImportError, AttributeError) as e:
            return "Not installed", False
    
    def get_pytorch_info(self) -> dict:
        """Get detailed PyTorch information.
        
        Returns:
            Dictionary with PyTorch details
        """
        try:
            import torch
            
            info = {
                'installed': True,
                'version': torch.__version__,
                'cuda_available': torch.cuda.is_available(),
                'cuda_version': torch.version.cuda if torch.cuda.is_available() else None,
                'device_count': torch.cuda.device_count() if torch.cuda.is_available() else 0,
                'devices': []
            }
            
            if torch.cuda.is_available():
                for i in range(torch.cuda.device_count()):
                    info['devices'].append({
                        'id': i,
                        'name': torch.cuda.get_device_name(i),
                        'capability': torch.cuda.get_device_capability(i)
                    })
            
            # Determine version type
            if '+cpu' in info['version']:
                info['type'] = 'CPU-only'
            elif '+cu' in info['version']:
                cuda_ver = info['version'].split('+cu')[1][:3]
                info['type'] = f'CUDA {cuda_ver}'
            else:
                info['type'] = 'Unknown'
            
            return info
            
        except ImportError:
            return {
                'installed': False,
                'version': None,
                'cuda_available': False,
                'type': 'Not installed'
            }
    
    def check_cuda_toolkit(self) -> dict:
        """Check if CUDA toolkit is installed.
        
        Returns:
            Dictionary with CUDA toolkit information
        """
        cuda_info = {
            'installed': False,
            'versions': [],
            'driver_version': None
        }
        
        # Check for CUDA toolkit
        cuda_paths = [
            r"C:\Program Files\NVIDIA GPU Computing Toolkit\CUDA",
            r"C:\Program Files (x86)\NVIDIA GPU Computing Toolkit\CUDA",
            "/usr/local/cuda"
        ]
        
        for cuda_path in cuda_paths:
            if os.path.exists(cuda_path):
                cuda_info['installed'] = True
                try:
                    versions = [d for d in os.listdir(cuda_path) if os.path.isdir(os.path.join(cuda_path, d))]
                    cuda_info['versions'] = versions
                except:
                    pass
        
        # Check NVIDIA driver
        try:
            result = subprocess.run(['nvidia-smi', '--query-gpu=driver_version', '--format=csv,noheader'],
                                  capture_output=True, text=True, timeout=5)
            if result.returncode == 0:
                cuda_info['driver_version'] = result.stdout.strip()
        except:
            pass
        
        return cuda_info
    
    def get_install_command(self, version_type: PyTorchVersion) -> list:
        """Get pip install command for specified PyTorch version.
        
        Args:
            version_type: PyTorch version to install
            
        Returns:
            List of command arguments
        """
        base_packages = ['torch', 'torchvision', 'torchaudio']
        
        if version_type == PyTorchVersion.CPU:
            return [sys.executable, '-m', 'pip', 'install'] + base_packages + \
                   ['--index-url', 'https://download.pytorch.org/whl/cpu']
        
        elif version_type == PyTorchVersion.CUDA_118:
            return [sys.executable, '-m', 'pip', 'install'] + base_packages + \
                   ['--index-url', 'https://download.pytorch.org/whl/cu118']
        
        elif version_type == PyTorchVersion.CUDA_121:
            return [sys.executable, '-m', 'pip', 'install'] + base_packages + \
                   ['--index-url', 'https://download.pytorch.org/whl/cu121']
        
        elif version_type == PyTorchVersion.CUDA_124:
            return [sys.executable, '-m', 'pip', 'install'] + base_packages + \
                   ['--index-url', 'https://download.pytorch.org/whl/cu124']
        
        return []
    
    def uninstall_pytorch(self, callback=None) -> Tuple[bool, str]:
        """Uninstall current PyTorch installation.
        
        Args:
            callback: Optional callback function for progress updates
            
        Returns:
            Tuple of (success, message)
        """
        try:
            if callback:
                callback("Uninstalling PyTorch...")
            
            packages = ['torch', 'torchvision', 'torchaudio']
            cmd = [sys.executable, '-m', 'pip', 'uninstall', '-y'] + packages
            
            result = subprocess.run(cmd, capture_output=True, text=True, timeout=120)
            
            if result.returncode == 0:
                return True, "PyTorch uninstalled successfully"
            else:
                return False, f"Uninstall failed: {result.stderr}"
                
        except subprocess.TimeoutExpired:
            return False, "Uninstall timed out"
        except Exception as e:
            return False, f"Uninstall error: {str(e)}"
    
    def install_pytorch(self, version_type: PyTorchVersion, callback=None) -> Tuple[bool, str]:
        """Install specified PyTorch version.
        
        Args:
            version_type: PyTorch version to install
            callback: Optional callback function for progress updates
            
        Returns:
            Tuple of (success, message)
        """
        try:
            if callback:
                callback(f"Installing PyTorch ({version_type.value})...")
            
            cmd = self.get_install_command(version_type)
            
            if not cmd:
                return False, "Invalid version type"
            
            # Run with real-time output capture
            process = subprocess.Popen(
                cmd,
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                text=True,
                bufsize=1,
                universal_newlines=True
            )
            
            output_lines = []
            for line in process.stdout:
                output_lines.append(line)
                if callback:
                    # Extract progress information from pip output
                    line_clean = line.strip()
                    if 'Downloading' in line_clean:
                        callback(f"Downloading packages...")
                    elif 'Installing' in line_clean:
                        callback(f"Installing packages...")
                    elif 'Successfully installed' in line_clean:
                        callback(f"Installation complete!")
                    elif '%' in line_clean or 'MB' in line_clean or 'GB' in line_clean:
                        # Show download progress
                        callback(line_clean[:80])  # Limit length
            
            process.wait(timeout=600)
            
            if process.returncode == 0:
                return True, f"PyTorch ({version_type.value}) installed successfully"
            else:
                error_output = '\n'.join(output_lines[-10:])  # Last 10 lines
                return False, f"Install failed:\n{error_output}"
                
        except subprocess.TimeoutExpired:
            return False, "Install timed out (this can take several minutes)"
        except Exception as e:
            return False, f"Install error: {str(e)}"
    
    def switch_version(self, version_type: PyTorchVersion, callback=None) -> Tuple[bool, str]:
        """Switch to specified PyTorch version.
        
        Args:
            version_type: PyTorch version to switch to
            callback: Optional callback function for progress updates
            
        Returns:
            Tuple of (success, message)
        """
        # Step 1: Uninstall current version
        if callback:
            callback("Step 1/2: Uninstalling current PyTorch...")
        
        success, message = self.uninstall_pytorch(callback)
        if not success:
            return False, f"Uninstall failed: {message}"
        
        # Step 2: Install new version
        if callback:
            callback("Step 2/2: Installing new PyTorch version...")
        
        success, message = self.install_pytorch(version_type, callback)
        if not success:
            return False, f"Install failed: {message}"
        
        return True, f"Successfully switched to PyTorch {version_type.value}"
    
    def recommend_version(self) -> PyTorchVersion:
        """Recommend PyTorch version based on system.
        
        Returns:
            Recommended PyTorch version
        """
        cuda_info = self.check_cuda_toolkit()
        
        if not cuda_info['installed']:
            return PyTorchVersion.CPU
        
        # Check CUDA version and recommend matching PyTorch
        versions = cuda_info.get('versions', [])
        
        if any('v13' in v or 'v12.4' in v for v in versions):
            return PyTorchVersion.CUDA_124
        elif any('v12' in v for v in versions):
            return PyTorchVersion.CUDA_121
        elif any('v11.8' in v for v in versions):
            return PyTorchVersion.CUDA_118
        else:
            return PyTorchVersion.CPU


def get_pytorch_manager() -> PyTorchManager:
    """Get PyTorch manager instance.
    
    Returns:
        PyTorchManager instance
    """
    return PyTorchManager()
