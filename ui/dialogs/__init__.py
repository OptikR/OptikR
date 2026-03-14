"""
Dialogs Module

Various dialog windows for the translation system.
"""

from .consent_dialog import (
    UserConsentDialog,
    check_user_consent,
    save_user_consent,
    show_consent_dialog
)
from .help_dialog import HelpDialog, show_help_dialog
from .quick_ocr_switch_dialog import QuickOCRSwitchDialog, show_quick_ocr_switch_dialog
from .audio_translation_dialog import AudioTranslationDialog
from .dictionary_editor_dialog import DictionaryEditorDialog, DictionaryEntryEditDialog
from .first_run import FirstRunWizard, show_first_run_wizard
from .localization_manager import LocalizationManager, show_localization_manager
from .plugin_settings_dialog import PluginSettingsDialog
from .full_pipeline_test_dialog import FullPipelineTestDialog, show_full_pipeline_test
from .dictionary_save_dialog import DictionarySaveDialog, show_dictionary_save_dialog

__all__ = [
    'UserConsentDialog',
    'check_user_consent',
    'save_user_consent',
    'show_consent_dialog',
    'HelpDialog',
    'show_help_dialog',
    'QuickOCRSwitchDialog',
    'show_quick_ocr_switch_dialog',
    'AudioTranslationDialog',
    'DictionaryEditorDialog',
    'DictionaryEntryEditDialog',
    'FirstRunWizard',
    'show_first_run_wizard',
    'LocalizationManager',
    'show_localization_manager',
    'PluginSettingsDialog',
    'FullPipelineTestDialog',
    'show_full_pipeline_test',
    'DictionarySaveDialog',
    'show_dictionary_save_dialog',
]
