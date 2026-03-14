"""
First Run Wizard

Setup wizard shown on first application launch.
Split from first_run_wizard.py into:
- setup_worker.py: SetupWorker QThread class
- wizard.py: FirstRunWizard dialog + show_first_run_wizard helper
"""

from .wizard import FirstRunWizard, show_first_run_wizard
from .setup_worker import SetupWorker

__all__ = [
    'FirstRunWizard',
    'SetupWorker',
    'show_first_run_wizard',
]
