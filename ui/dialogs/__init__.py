"""
Dialogs Module

Various dialog windows for the Real-Time Translation System.
"""

from .consent_dialog import (
    UserConsentDialog,
    check_user_consent,
    save_user_consent,
    show_consent_dialog
)
from .help_dialog import HelpDialog, show_help_dialog
from .quick_ocr_switch_dialog import QuickOCRSwitchDialog, show_quick_ocr_switch_dialog

__all__ = [
    'UserConsentDialog',
    'check_user_consent',
    'save_user_consent',
    'show_consent_dialog',
    'HelpDialog',
    'show_help_dialog',
    'QuickOCRSwitchDialog',
    'show_quick_ocr_switch_dialog'
]
