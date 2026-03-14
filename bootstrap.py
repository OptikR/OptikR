"""
OptikR — Bootstrap module.

Runs all environment setup that must happen before the application starts:
  1. EXE stdout/stderr fix
  2. Warning suppression & environment variables
  3. Logging configuration
  4. sys.path setup
  5. PyTorch auto-installation (may restart process)
  6. Application directory creation
  7. Config manager initialization
  8. Installation info / CUDA path loading

After this module is imported, the following are available:
  - bootstrap.logger          — pre-configured logger for optikr
  - bootstrap.config_manager  — SimpleConfigManager instance (ready to use)
  - bootstrap.INSTALLATION_INFO — hardware/CUDA detection dict
"""

import sys
import os
import warnings
import re
import shutil
import site
from pathlib import Path

# ============================================================================
# EXE FIX: Redirect stdout/stderr for windowed applications
# ============================================================================
# When running as a windowed EXE (console=False), sys.stdout and sys.stderr
# are None, which causes crashes when code tries to use print() or flush().
if getattr(sys, 'frozen', False):
    _devnull_handles = []
    if sys.stdout is None:
        sys.stdout = open(os.devnull, 'w', encoding='utf-8', errors='ignore')
        _devnull_handles.append(sys.stdout)
    if sys.stderr is None:
        sys.stderr = open(os.devnull, 'w', encoding='utf-8', errors='ignore')
        _devnull_handles.append(sys.stderr)
    if _devnull_handles:
        import atexit

        def _close_devnull():
            for h in _devnull_handles:
                try:
                    h.close()
                except Exception:
                    pass

        atexit.register(_close_devnull)
# ============================================================================

# Suppress common warnings for cleaner console output
warnings.filterwarnings('ignore', category=FutureWarning)
warnings.filterwarnings('ignore', category=UserWarning, module='paddle')
warnings.filterwarnings('ignore', category=UserWarning, module='transformers')
warnings.filterwarnings('ignore', message='.*resume_download.*')
warnings.filterwarnings('ignore', message='.*torch.load.*')
warnings.filterwarnings('ignore', message='.*_pytree.*')

# Suppress paddle verbose output
os.environ['GLOG_minloglevel'] = '3'
os.environ['FLAGS_pir_apply_shape_optimization_pass'] = '0'
os.environ['PPOCR_SHOW_LOG'] = '0'
os.environ['PADDLEOCR_VERBOSE'] = '0'

# Suppress Qt DPI awareness warning on Windows (harmless — already set by another component)
os.environ.setdefault('QT_LOGGING_RULES', 'qt.qpa.window=false')

import logging

# Configure logging to suppress verbose library output
logging.getLogger('mokuro').setLevel(logging.CRITICAL)
logging.getLogger('transformers').setLevel(logging.CRITICAL)
logging.getLogger('huggingface_hub').setLevel(logging.CRITICAL)
logging.getLogger('paddleocr').setLevel(logging.CRITICAL)

# Suppress root logger warnings
logging.getLogger().setLevel(logging.ERROR)

# Logging format constants
_STANDARD_FORMAT = '[%(levelname)s] [%(asctime)s] [%(name)s] [%(threadName)s] %(message)s'
_STANDARD_DATEFMT = '%H:%M:%S'
_DEBUG_FORMAT = (
    '[%(levelname)s] [%(asctime)s.%(msecs)03d] '
    '[%(name)s:%(funcName)s:%(lineno)d] [%(threadName)s] %(message)s'
)

# Module logger — shared across bootstrap and run.py
logger = logging.getLogger('optikr')
logger.setLevel(logging.INFO)
if not logger.handlers:
    _handler = logging.StreamHandler()
    _handler.setFormatter(logging.Formatter(_STANDARD_FORMAT, datefmt=_STANDARD_DATEFMT))
    logger.addHandler(_handler)
    logger.propagate = False

from app.utils.credential_filter import CredentialLoggingFilter
logger.addFilter(CredentialLoggingFilter())

# Add root directory to Python path for imports
_current_dir = Path(__file__).parent
if str(_current_dir) not in sys.path:
    sys.path.insert(0, str(_current_dir))


# ============================================================================
# PYTORCH AUTO-INSTALLATION
# Delegates detection/install to PyTorchManager — restart logic stays here
# because it happens before the app event loop exists.
# ============================================================================
def _check_and_install_pytorch():
    """Check if PyTorch is installed. If not, auto-install via PyTorchManager.

    On first run without PyTorch: detects GPU, installs matching variant,
    then restarts the process.

    Returns:
        tuple: (success, is_gpu, message)
    """
    from app.utils.pytorch_manager import PyTorchManager, PyTorchVersion

    mgr = PyTorchManager()
    info = mgr.get_pytorch_info()

    def _get_missing_core_deps():
        """Return missing packages required to launch the GUI."""
        import importlib.util
        required = ("PyQt6", "packaging")
        return [pkg for pkg in required if importlib.util.find_spec(pkg) is None]

    missing_core = _get_missing_core_deps()

    if info['installed'] and not missing_core:
        version = info['version']
        is_gpu = info['cuda_available']
        if is_gpu and info.get('devices'):
            gpu_name = info['devices'][0]['name']
            logger.info("PyTorch %s detected with GPU: %s", version, gpu_name)
        else:
            logger.info("PyTorch %s detected (CPU mode)", version)
        return True, is_gpu, f"PyTorch {version} ready"
    elif info['installed'] and missing_core:
        logger.warning(
            "PyTorch is installed, but core dependencies are missing: %s. "
            "Running requirements install to repair environment.",
            ", ".join(missing_core),
        )

    # PyTorch not installed — first-run auto-install
    import subprocess

    _req_file = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'requirements.txt')

    cuda_info = mgr.check_cuda_toolkit()
    use_cuda = cuda_info['installed'] or cuda_info['driver_version'] is not None

    variant = "CUDA" if use_cuda else "CPU"
    logger.info("=" * 60)
    logger.info("FIRST RUN: Setting up OptikR (%s)...", variant)
    logger.info("This is a one-time setup and may take a few minutes.")
    logger.info("=" * 60)

    def _normalize_pkg_name(name):
        return re.sub(r"[-_.]+", "-", name.strip().lower())

    def _extract_req_name(req_line):
        """Parse package name from a requirements line."""
        line = req_line.strip()
        if not line or line.startswith('#'):
            return None
        if line.startswith(('-r', '--requirement', '-e', '--editable', '--index-url',
                           '--extra-index-url', '--find-links', '--trusted-host',
                           '--constraint', '-c')):
            return None
        if ' #' in line:
            line = line.split(' #', 1)[0].strip()
        # Keep only the package token before version/extras/markers.
        token = re.split(r'[<>=!~;\[\s]', line, maxsplit=1)[0].strip()
        if not token or token.startswith(('.', '/', '\\')) or '://' in token:
            return None
        return _normalize_pkg_name(token)

    def _extract_pkg_from_pip_line(pip_line):
        """Extract package name from common pip output lines."""
        text = pip_line.strip()
        if text.startswith("Collecting "):
            pkg = text[len("Collecting "):].split()[0]
            return _normalize_pkg_name(pkg)
        if text.startswith("Requirement already satisfied: "):
            pkg = text[len("Requirement already satisfied: "):].split()[0]
            return _normalize_pkg_name(pkg)
        if text.startswith("Processing "):
            pkg = Path(text[len("Processing "):].split()[0]).stem.split('-')[0]
            return _normalize_pkg_name(pkg)
        return None

    def _cleanup_stale_torch_artifacts():
        """Remove broken pip leftovers like '~orch*' in site-packages."""
        try:
            candidates = set()
            for sp in getattr(site, "getsitepackages", lambda: [])() or []:
                if sp:
                    candidates.add(Path(sp))
            user_site = getattr(site, "getusersitepackages", lambda: "")()
            if user_site:
                candidates.add(Path(user_site))

            stale_prefixes = ("~orch", "~unctorch")
            removed = 0
            for sp in candidates:
                if not sp.exists() or not sp.is_dir():
                    continue
                for entry in sp.iterdir():
                    name = entry.name.lower()
                    if not name.startswith(stale_prefixes):
                        continue
                    try:
                        if entry.is_dir():
                            shutil.rmtree(entry, ignore_errors=False)
                        else:
                            entry.unlink(missing_ok=True)
                        removed += 1
                        logger.warning("Removed stale package artifact: %s", entry)
                    except Exception as e:
                        logger.warning("Could not remove stale artifact %s: %s", entry, e)
            if removed:
                logger.info("Cleaned %d stale torch artifact(s) before install", removed)
        except Exception as e:
            logger.debug("Stale artifact cleanup skipped: %s", e)

    def _restart_current_process():
        """Restart the current script with robust Windows path handling."""
        argv = [sys.executable]
        if sys.argv:
            argv.extend(sys.argv)
        try:
            # subprocess handles quoting on Windows better than os.execv when
            # executable paths/usernames contain spaces.
            import subprocess as _subprocess
            _subprocess.Popen(argv, close_fds=True)
            os._exit(0)
        except Exception as restart_error:
            logger.error("Failed to restart automatically: %s", restart_error)
            return False

    try:
        _cleanup_stale_torch_artifacts()

        # Step 1: Install all requirements from requirements.txt
        if os.path.exists(_req_file):
            direct_reqs = []
            with open(_req_file, 'r', encoding='utf-8') as req_handle:
                for line in req_handle:
                    parsed = _extract_req_name(line)
                    if parsed:
                        direct_reqs.append(parsed)
            direct_req_set = set(direct_reqs)
            total_direct = len(direct_req_set)
            logger.info(
                "Step 1/2: Installing dependencies from requirements.txt (%d direct deps)...",
                total_direct,
            )

            req_cmd = [
                sys.executable, '-m', 'pip', 'install', '-r', _req_file,
                '--disable-pip-version-check', '--progress-bar', 'off',
            ]
            req_proc = subprocess.Popen(
                req_cmd,
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                text=True,
                bufsize=1,
            )

            completed_direct = set()
            last_remaining = total_direct
            assert req_proc.stdout is not None
            for raw_line in req_proc.stdout:
                line = raw_line.rstrip()
                if not line:
                    continue
                pkg_name = _extract_pkg_from_pip_line(line)
                if pkg_name:
                    if pkg_name in direct_req_set:
                        completed_direct.add(pkg_name)
                        remaining = total_direct - len(completed_direct)
                        if remaining != last_remaining:
                            logger.info(
                                "Dependency progress: %d/%d direct deps checked (remaining: %d)",
                                len(completed_direct), total_direct, remaining,
                            )
                            last_remaining = remaining
                logger.info("[pip] %s", line)

            # Do not force a hard timeout by default: first-run installs can
            # legitimately take >10 minutes on slower machines/networks.
            # Optional override: set OPTIKR_PIP_INSTALL_TIMEOUT (seconds).
            timeout_raw = os.environ.get("OPTIKR_PIP_INSTALL_TIMEOUT", "").strip()
            timeout_seconds = int(timeout_raw) if timeout_raw.isdigit() else 0
            if timeout_seconds > 0:
                req_proc.wait(timeout=timeout_seconds)
            else:
                req_proc.wait()
            if req_proc.returncode != 0:
                logger.warning(
                    "Some dependencies may have failed (exit code %s). "
                    "Direct deps checked: %d/%d, remaining: %d",
                    req_proc.returncode,
                    len(completed_direct),
                    total_direct,
                    max(total_direct - len(completed_direct), 0),
                )
            else:
                logger.info(
                    "Dependencies installed successfully. Direct deps checked: %d/%d.",
                    len(completed_direct),
                    total_direct,
                )
        else:
            logger.warning("requirements.txt not found, skipping dependency install.")

        # Re-check PyTorch after requirements install.
        # On some systems, torch may already be pulled in as a transitive
        # dependency (e.g. easyocr). Re-installing in the same process can
        # trigger WinError 32 file-lock issues on Windows.
        post_req_info = mgr.get_pytorch_info()
        if post_req_info.get('installed'):
            post_version = post_req_info.get('version', 'unknown')
            post_cuda = bool(post_req_info.get('cuda_available'))
            if not use_cuda or post_cuda:
                logger.info(
                    "PyTorch %s already available after Step 1 (cuda=%s); "
                    "skipping Step 2 installation.",
                    post_version, post_cuda,
                )
                return True, post_cuda, f"PyTorch {post_version} ready"

        # Step 2: Install PyTorch via PyTorchManager
        version_type = PyTorchVersion.CUDA_124 if use_cuda else PyTorchVersion.CPU
        logger.info("Step 2/2: Installing PyTorch (%s)... Please wait...", variant)

        success, msg = mgr.install_pytorch(version_type)

        if success:
            logger.info("PyTorch %s installed successfully! Restarting application...", variant)
            if _restart_current_process() is False:
                return True, use_cuda, "PyTorch installed. Please restart the app manually."
        else:
            logger.error("PyTorch installation failed: %s", msg)
            return False, False, f"Installation failed: {msg}"

    except Exception as e:
        logger.error("PyTorch installation error: %s", e)
        return False, False, f"Installation error: {e}"


# Run PyTorch check before any imports that depend on it
_pytorch_success, _pytorch_gpu, _pytorch_msg = _check_and_install_pytorch()

if not _pytorch_success:
    logger.critical("PyTorch installation failed!")
    logger.critical("Please install PyTorch manually:")
    logger.critical("  CPU-only:  pip install -r requirements-cpu.txt")
    logger.critical("  GPU:       pip install -r requirements-gpu.txt")

    try:
        from PyQt6.QtWidgets import QApplication, QMessageBox
        app = QApplication(sys.argv)
        QMessageBox.critical(
            None,
            "PyTorch Installation Required",
            "PyTorch could not be installed automatically.\n\n"
            "Please install it manually:\n\n"
            "CPU-only: pip install -r requirements-cpu.txt\n"
            "GPU: pip install -r requirements-gpu.txt\n\n"
            f"Error: {_pytorch_msg}"
        )
    except Exception as e:
        logger.debug("Could not show PyTorch error dialog: %s", e)

    sys.exit(1)


# ============================================================================
# PYTORCH CUDA GUARD
# Detects when a CUDA-enabled PyTorch build has been silently replaced by a
# CPU-only build (e.g. by `pip install surya-ocr` pulling torch from the
# default index).  Warns the user so they can repair it.
# ============================================================================
def _check_pytorch_cuda_integrity():
    """Warn if the installed PyTorch was expected to have CUDA but doesn't.

    Compares the build tag (+cu124 etc.) recorded in installation info
    against the currently importable torch version.  A mismatch means
    something overwrote the CUDA build with a CPU-only one.
    """
    try:
        import torch

        version_tag = torch.__version__  # e.g. "2.6.0+cu124" or "2.6.0+cpu"
        has_cuda = torch.cuda.is_available()

        if has_cuda:
            return  # All good

        if '+cu' not in version_tag:
            # The current build is CPU-only.  Check if the user originally
            # had a CUDA build by looking at the saved installation info.
            from app.utils.path_utils import get_config_file
            _cfg_file = get_config_file()
            if not _cfg_file.exists():
                return

            import json
            with open(_cfg_file, 'r', encoding='utf-8') as f:
                cfg = json.load(f)

            install = cfg.get('installation', {})
            prev_cuda = install.get('pytorch', {}).get('cuda_available', False)

            if prev_cuda:
                logger.warning("=" * 60)
                logger.warning("PYTORCH CUDA BUILD REPLACED")
                logger.warning(
                    "Current torch version %s has no CUDA support, but a "
                    "previous session had CUDA enabled.  A package install "
                    "(e.g. pip install surya-ocr) likely overwrote your GPU "
                    "build with a CPU-only one.",
                    version_tag,
                )
                logger.warning(
                    "To restore GPU acceleration, run:\n"
                    "  pip install torch torchvision torchaudio "
                    "--index-url https://download.pytorch.org/whl/cu124"
                )
                logger.warning("=" * 60)
    except Exception as e:
        logger.debug("PyTorch CUDA integrity check skipped: %s", e)

_check_pytorch_cuda_integrity()


# ============================================================================
# Installation info & config manager
# ============================================================================

def _create_installation_info():
    """Detect hardware and create installation info dict."""
    import torch
    from datetime import datetime

    return {
        'created': datetime.now().isoformat(),
        'version': 'pre-realese-1.0.0',
        'cuda': {
            'installed': torch.cuda.is_available(),
            'path': os.environ.get('CUDA_HOME', os.environ.get('CUDA_PATH', '')),
        },
        'pytorch': {
            'version': torch.__version__,
            'cuda_available': torch.cuda.is_available(),
            'device_name': torch.cuda.get_device_name(0) if torch.cuda.is_available() else 'CPU',
        }
    }


def _load_installation_info(cfg_manager):
    """Load or create installation info, configure CUDA environment.

    If a CUDA path is saved, it is validated (must exist and contain nvcc or
    cudart DLL). If invalid (e.g. after moving to another PC), the path is
    cleared and we try env vars (CUDA_HOME/CUDA_PATH); valid path is saved.
    """
    from app.utils.cuda_path_utils import validate_cuda_installation

    install_info = cfg_manager.get_installation_info()
    if install_info and install_info.get('created'):
        logger.info("Loaded installation info from consolidated config")

    if not install_info or not install_info.get('created'):
        logger.info("Creating installation info automatically...")
        install_info = _create_installation_info()
        cfg_manager.set_installation_info(install_info)
        cfg_manager.save_config()
        logger.info("Installation info saved to consolidated config")

        if install_info['pytorch']['cuda_available']:
            logger.info("GPU detected: %s", install_info['pytorch']['device_name'])
        else:
            logger.info("No GPU detected - running in CPU mode")

    # Validate saved CUDA path (portability: path may be from another machine)
    if install_info:
        cuda_info = install_info.get('cuda', {}) or {}
        saved_path = (cuda_info.get('path') or '').strip()
        cuda_path = None
        if saved_path:
            valid, msg = validate_cuda_installation(saved_path)
            if valid:
                cuda_path = saved_path
            else:
                logger.warning("Saved CUDA path invalid or missing: %s — clearing", msg)
                cuda_info = dict(cuda_info)
                cuda_info['path'] = ''
                install_info = dict(install_info)
                install_info['cuda'] = cuda_info
                cfg_manager.set_installation_info(install_info)
                cfg_manager.save_config()
        if not cuda_path:
            # Try environment (e.g. user set CUDA_HOME on new PC)
            for env_key in ('CUDA_HOME', 'CUDA_PATH'):
                candidate = os.environ.get(env_key, '').strip()
                if candidate and validate_cuda_installation(candidate)[0]:
                    cuda_path = candidate
                    cuda_info = install_info.get('cuda', {}) or {}
                    cuda_info = dict(cuda_info)
                    cuda_info['path'] = cuda_path
                    install_info = dict(install_info)
                    install_info['cuda'] = cuda_info
                    cfg_manager.set_installation_info(install_info)
                    cfg_manager.save_config()
                    logger.info("Using CUDA path from %s: %s", env_key, cuda_path)
                    break

    # Set CUDA environment variables from validated path
    if install_info:
        cuda_info = install_info.get('cuda', {})
        cuda_path = (cuda_info.get('path') or '').strip()
        if cuda_path:
            valid, _ = validate_cuda_installation(cuda_path)
            if valid:
                os.environ['CUDA_HOME'] = cuda_path
                os.environ['CUDA_PATH'] = cuda_path
                logger.info("CUDA path loaded: %s", cuda_path)

                cuda_bin = str(Path(cuda_path) / 'bin')
                if cuda_bin not in os.environ.get('PATH', ''):
                    os.environ['PATH'] = cuda_bin + os.pathsep + os.environ.get('PATH', '')
                    logger.info("Added CUDA bin to PATH: %s", cuda_bin)

        pytorch_info = install_info.get('pytorch', {})
        if pytorch_info.get('cuda_available'):
            logger.info("GPU acceleration available: %s", pytorch_info.get('device_name', 'Unknown GPU'))
        else:
            logger.info("Running in CPU mode")

        ocr_engine = install_info.get('ocr_engine', {}).get('name')
        if ocr_engine:
            logger.info("OCR engine: %s", ocr_engine)

        translation_engine = install_info.get('translation_engine', {}).get('name')
        if translation_engine:
            logger.info("Translation engine: %s", translation_engine)

    return install_info


# Ensure all directories exist
from app.utils.path_utils import ensure_all_directories, get_logs_dir
ensure_all_directories()
logger.info("All application directories verified")

# Activate file logging now that directories exist
from logging.handlers import RotatingFileHandler
_log_file = get_logs_dir() / 'optikr.log'
_file_handler = RotatingFileHandler(
    str(_log_file), maxBytes=5 * 1024 * 1024, backupCount=3, encoding='utf-8',
)
_file_handler.setFormatter(logging.Formatter(_STANDARD_FORMAT, datefmt=_STANDARD_DATEFMT))
_file_handler.addFilter(CredentialLoggingFilter())
logger.addHandler(_file_handler)
logger.info("File logging activated: %s", _log_file)

def _reconfigure_logging(cfg_manager):
    """Apply log_level, debug_mode, and quiet_console from config to the optikr logger.

    Called once after the config manager is ready.  Updates the logger level
    and switches all handlers to the enhanced debug format when debug_mode
    is enabled.  When quiet_console is enabled, the StreamHandler only shows
    WARNING and above while the file handler keeps the full configured level.
    """
    level_name = cfg_manager.get('logging.log_level', 'INFO')
    debug_mode = cfg_manager.get('advanced.debug_mode', False)
    quiet_console = cfg_manager.get('advanced.quiet_console', False)

    numeric_level = getattr(logging, level_name.upper(), logging.INFO)

    if debug_mode:
        numeric_level = min(numeric_level, logging.DEBUG)

    logger.setLevel(numeric_level)

    fmt_str = _DEBUG_FORMAT if debug_mode else _STANDARD_FORMAT
    datefmt = _STANDARD_DATEFMT
    formatter = logging.Formatter(fmt_str, datefmt=datefmt)

    for h in logger.handlers:
        h.setFormatter(formatter)
        if quiet_console and isinstance(h, logging.StreamHandler) and not isinstance(h, logging.FileHandler):
            h.setLevel(logging.WARNING)
        else:
            h.setLevel(logging.NOTSET)

    logger.info(
        "Logging configured: level=%s, debug_mode=%s, quiet_console=%s",
        logging.getLevelName(numeric_level), debug_mode, quiet_console,
    )


# Create config manager and load installation info
from app.core.config import SimpleConfigManager

config_manager = SimpleConfigManager()
_reconfigure_logging(config_manager)
INSTALLATION_INFO = _load_installation_info(config_manager)
