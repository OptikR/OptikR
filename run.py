"""
OptikR — Application entry point.

Thin launcher: imports bootstrap for environment setup, then runs
the GUI startup flow or CLI subcommands.
"""

import sys
import atexit
import signal
import platform
import threading
from pathlib import Path
from datetime import datetime

# Bootstrap handles: EXE fix, warnings, env vars, logging, sys.path,
# PyTorch auto-install, directory creation, config manager, CUDA setup.
from bootstrap import logger, config_manager

from PyQt6.QtWidgets import QApplication, QMessageBox


# ============================================================================
# Crash logger
# ============================================================================

def _install_crash_logger():
    """Install a global exception hook that logs unhandled crashes to system_data/logs/."""
    from app.utils.path_utils import ensure_dir
    import traceback as _tb

    crash_log_dir = ensure_dir('logs')
    _original_hook = sys.excepthook

    def _crash_hook(exc_type, exc_value, exc_traceback):
        if exc_type is KeyboardInterrupt:
            _original_hook(exc_type, exc_value, exc_traceback)
            return
        try:
            timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
            crash_file = crash_log_dir / f'crash_{timestamp}.log'
            with open(crash_file, 'w', encoding='utf-8') as f:
                f.write(f"OptikR Crash Report — {datetime.now().isoformat()}\n")
                f.write("=" * 60 + "\n\n")
                f.write(f"Exception: {exc_type.__name__}: {exc_value}\n\n")
                f.write("Traceback:\n")
                _tb.print_exception(exc_type, exc_value, exc_traceback, file=f)
                f.write(f"\nPython: {sys.version}\n")
                f.write(f"Platform: {platform.platform()}\n")
            logger.critical("Crash log saved to: %s", crash_file)
        except Exception:
            pass  # Last resort — don't mask the original crash
        _original_hook(exc_type, exc_value, exc_traceback)

    sys.excepthook = _crash_hook

    # Also catch unhandled thread exceptions (Python 3.10+)
    if hasattr(threading, 'excepthook'):
        _original_thread_hook = threading.excepthook

        def _thread_crash_hook(args):
            _crash_hook(args.exc_type, args.exc_value, args.exc_traceback)
            _original_thread_hook(args)

        threading.excepthook = _thread_crash_hook


# ============================================================================
# Main application
# ============================================================================

def main():
    """Launch the OptikR application."""
    logger.info("")
    logger.info("=" * 60)
    logger.info("OPTIKR")
    logger.info("=" * 60)
    logger.info("Starting application...")
    logger.info("")

    _install_crash_logger()

    app = QApplication(sys.argv)

    # Load UI language from config
    try:
        from app.localization import get_language_manager
        ui_lang = config_manager.get_setting('ui.language', 'en')
        language_manager = get_language_manager()
        language_manager.set_language(ui_lang)
        logger.info("UI language set to: %s", ui_lang)
    except Exception as e:
        logger.warning("Failed to load UI language: %s", e)

    # Load stylesheet (dark default, base fallback)
    stylesheet_path = Path(__file__).parent / "app" / "styles" / "dark.qss"
    if stylesheet_path.exists():
        with open(stylesheet_path, 'r', encoding='utf-8') as f:
            app.setStyleSheet(f.read())
        logger.info("Loaded dark mode stylesheet")
    else:
        stylesheet_path = Path(__file__).parent / "app" / "styles" / "base.qss"
        if stylesheet_path.exists():
            with open(stylesheet_path, 'r', encoding='utf-8') as f:
                app.setStyleSheet(f.read())
            logger.info("Loaded base stylesheet")
        else:
            logger.warning("No stylesheet found")
            return 1

    # Check for user consent
    from ui.dialogs.consent_dialog import check_user_consent, show_consent_dialog

    consent_result = None
    if not check_user_consent(config_manager):
        logger.info("FIRST TIME LAUNCH - USER CONSENT REQUIRED")
        consent_result = show_consent_dialog(parent=None, config_manager=config_manager)
        if not consent_result:
            logger.info("User declined consent. Exiting application.")
            return 0
        logger.info("User consent obtained. Continuing...")

    # Check for first-run setup
    from ui.dialogs.first_run import FirstRunWizard, show_first_run_wizard

    show_wizard = config_manager.get_setting('startup.show_setup_wizard', True)
    force_setup_wizard = isinstance(consent_result, dict) and consent_result.get('mode') == 'online'
    if force_setup_wizard or (show_wizard and not FirstRunWizard.is_setup_complete()):
        logger.info("First run detected — launching setup wizard")
        wizard_result = show_first_run_wizard(
            config_manager=config_manager,
            force=force_setup_wizard,
        )
        if not wizard_result:
            logger.warning("Setup wizard was cancelled or failed")
            logger.info("You can re-run the wizard from Settings later")
    else:
        logger.info("First-run setup already completed, skipping wizard")

    # Show loading overlay
    from ui.common.widgets.loading_overlay import LoadingOverlay
    splash = LoadingOverlay()
    splash.show()
    splash.set_progress(10, "Initializing...")
    QApplication.processEvents()

    splash.set_progress(30, "Loading configuration...")

    # Periodic cache clear (runs only when enabled in config and retention elapsed)
    try:
        from app.utils.periodic_cache_cleaner import run_periodic_clear
        run_periodic_clear(config_manager)
    except Exception as e:
        logger.warning("Periodic cache clear failed: %s", e)

    # Create main window
    from app.core.main_window import MainWindow

    splash.set_progress(50, "Building UI...")
    window = MainWindow(config_manager=config_manager)

    # Register atexit and signal handlers for cleanup fallback (Bug 1.12)
    _cleanup_called = False

    def _cleanup_handler(*args):
        nonlocal _cleanup_called
        if not _cleanup_called:
            _cleanup_called = True
            try:
                window._cleanup_on_exit()
            except Exception:
                pass

    atexit.register(_cleanup_handler)
    signal.signal(signal.SIGTERM, lambda sig, frame: (_cleanup_handler(), sys.exit(0)))
    signal.signal(signal.SIGINT, lambda sig, frame: (_cleanup_handler(), sys.exit(0)))

    splash.set_progress(80, "Loading pipeline...")
    QApplication.processEvents()

    splash.set_progress(100, "Ready!")

    window.show()
    splash.finish_with_delay(window, delay_ms=600)

    logger.info("OptikR started successfully")
    logger.info("Ready for translation")

    return app.exec()


# ============================================================================
# CLI subcommands
# ============================================================================

if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description='OptikR - OCR and Translation Tool')
    parser.add_argument('--create-plugin', action='store_true',
                       help='Launch plugin generator (no UI)')
    parser.add_argument('--plugin-type', type=str,
                       choices=['capture', 'ocr', 'translation', 'optimizer', 'text_processor'],
                       help='Plugin type to generate')
    parser.add_argument('--plugin-generator', type=str, metavar='PATH',
                       help='Generate plugin from template at specified path (no UI)')
    parser.add_argument('--auto-generate-missing', action='store_true',
                       help='Auto-generate missing essential plugins (no UI)')
    parser.add_argument('--health-check', action='store_true',
                       help='Run system health check and display results')

    args = parser.parse_args()

    # Handle plugin generation from path
    if args.plugin_generator:
        from app.workflow.universal_plugin_generator import PluginGenerator

        plugin_path = Path(args.plugin_generator)
        if not plugin_path.exists():
            print(f"[ERROR] Plugin path does not exist: {plugin_path}")
            sys.exit(1)

        print(f"[INFO] Generating plugin from: {plugin_path}")
        generator = PluginGenerator(output_dir="plugins")
        generator.run_interactive()
        sys.exit(0)

    # Handle auto-generation of missing plugins
    if args.auto_generate_missing:
        print("\n" + "="*60)
        print("AUTO-GENERATING MISSING PLUGINS")
        print("="*60)
        print("\nScanning for installed packages and generating plugins...\n")

        from app.ocr.ocr_plugin_manager import OCRPluginManager
        from app.capture.capture_plugin_manager import CapturePluginManager
        from app.text_processors.text_processor_plugin_manager import TextProcessorPluginManager

        success_count = 0
        total_count = 0

        print("[1/3] Checking OCR plugins...")
        try:
            ocr_plugins = OCRPluginManager().discover_plugins()
            print(f"  ✓ Discovered {len(ocr_plugins)} OCR plugins")
            success_count += 1
        except Exception as e:
            print(f"  ✗ Failed: {e}")
        total_count += 1

        print("[2/3] Checking Capture plugins...")
        try:
            capture_plugins = CapturePluginManager().discover_plugins()
            print(f"  ✓ Discovered {len(capture_plugins)} Capture plugins")
            success_count += 1
        except Exception as e:
            print(f"  ✗ Failed: {e}")
        total_count += 1

        print("[3/3] Checking Text Processor plugins...")
        try:
            text_proc_plugins = TextProcessorPluginManager().discover_plugins()
            print(f"  ✓ Discovered {len(text_proc_plugins)} Text Processor plugins")
            success_count += 1
        except Exception as e:
            print(f"  ✗ Failed: {e}")
        total_count += 1

        print("\n" + "="*60)
        print(f"COMPLETE: {success_count}/{total_count} plugin types processed")
        print("="*60 + "\n")

        sys.exit(0 if success_count == total_count else 1)

    # Handle plugin generation
    if args.create_plugin:
        from app.workflow.universal_plugin_generator import PluginGenerator
        generator = PluginGenerator(output_dir="plugins")
        generator.run_interactive()
        sys.exit(0)

    # Handle manual health check
    if args.health_check:
        print("\n" + "="*60)
        print("SYSTEM HEALTH CHECK")
        print("="*60)
        print("\nRunning comprehensive system health check...\n")

        from app.utils.health_check import HealthCheck
        health_check = HealthCheck(config_manager)

        try:
            system_health = health_check.run_all_checks()

            print("="*60)
            print("HEALTH CHECK RESULTS")
            print("="*60)
            print()

            if system_health.is_healthy:
                print("✅ Overall Status: HEALTHY")
                print("All system components are functioning correctly.\n")
            else:
                print("⚠️  Overall Status: ISSUES DETECTED")
                print("Some components have issues that need attention.\n")

            print("Component Status:")
            print("-" * 60)

            for component_name, result in system_health.components.items():
                status_icon = "✅" if result.passed else "❌"
                print(f"{status_icon} {component_name.upper()}")
                print(f"   Status: {result.message}")
                if result.details:
                    print(f"   Details: {result.details}")
                if not result.passed and result.remediation:
                    print(f"   Remediation: {result.remediation}")
                print()

            print("="*60)
            print("SUMMARY")
            print("="*60)

            failed_components = system_health.get_failed_components()
            if failed_components:
                print(f"Failed Components: {', '.join(failed_components)}")
            else:
                print("No issues detected. System is ready to use.")

            print("="*60 + "\n")
            sys.exit(0 if system_health.is_healthy else 1)

        except Exception as e:
            print(f"\n[ERROR] Health check failed with exception: {e}")
            import traceback
            traceback.print_exc()
            sys.exit(1)

    # Normal GUI mode
    sys.exit(main())
