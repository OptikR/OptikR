"""
Backward-compatible re-export shim.

The first_run_wizard module has been split into:
- ui.dialogs.first_run.setup_worker (SetupWorker)
- ui.dialogs.first_run.wizard (FirstRunWizard, show_first_run_wizard)

This file re-exports the full public surface so existing imports and
unittest.mock.patch() targets continue to work unchanged.
"""

# Re-export everything from wizard.py (includes FirstRunWizard,
# show_first_run_wizard, and all imported names like DependencyChecker,
# HealthCheck, ModelCatalog, HardwareDetector, QDialog, sys, etc.
# that tests patch via "ui.dialogs.first_run_wizard.<name>").
from .first_run.wizard import *  # noqa: F401,F403
from .first_run.setup_worker import SetupWorker  # noqa: F401
