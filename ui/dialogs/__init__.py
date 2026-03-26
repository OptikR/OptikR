"""
Dialogs Module

Various dialog windows for the translation system.

Exports are loaded lazily (PEP 562) so importing ``ui.dialogs.<submodule>`` does not
execute every dialog module at startup.
"""

from __future__ import annotations

import importlib
from typing import Any

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

# name -> (relative submodule, attribute)
_LAZY_IMPORTS: dict[str, tuple[str, str]] = {
    'UserConsentDialog': ('.consent_dialog', 'UserConsentDialog'),
    'check_user_consent': ('.consent_dialog', 'check_user_consent'),
    'save_user_consent': ('.consent_dialog', 'save_user_consent'),
    'show_consent_dialog': ('.consent_dialog', 'show_consent_dialog'),
    'HelpDialog': ('.help_dialog', 'HelpDialog'),
    'show_help_dialog': ('.help_dialog', 'show_help_dialog'),
    'QuickOCRSwitchDialog': ('.quick_ocr_switch_dialog', 'QuickOCRSwitchDialog'),
    'show_quick_ocr_switch_dialog': (
        '.quick_ocr_switch_dialog',
        'show_quick_ocr_switch_dialog',
    ),
    'AudioTranslationDialog': (
        '.audio_translation_dialog',
        'AudioTranslationDialog',
    ),
    'DictionaryEditorDialog': (
        '.dictionary_editor_dialog',
        'DictionaryEditorDialog',
    ),
    'DictionaryEntryEditDialog': (
        '.dictionary_editor_dialog',
        'DictionaryEntryEditDialog',
    ),
    'FirstRunWizard': ('.first_run', 'FirstRunWizard'),
    'show_first_run_wizard': ('.first_run', 'show_first_run_wizard'),
    'LocalizationManager': (
        '.localization_manager',
        'LocalizationManager',
    ),
    'show_localization_manager': (
        '.localization_manager',
        'show_localization_manager',
    ),
    'PluginSettingsDialog': (
        '.plugin_settings_dialog',
        'PluginSettingsDialog',
    ),
    'FullPipelineTestDialog': (
        '.full_pipeline_test_dialog',
        'FullPipelineTestDialog',
    ),
    'show_full_pipeline_test': (
        '.full_pipeline_test_dialog',
        'show_full_pipeline_test',
    ),
    'DictionarySaveDialog': (
        '.dictionary_save_dialog',
        'DictionarySaveDialog',
    ),
    'show_dictionary_save_dialog': (
        '.dictionary_save_dialog',
        'show_dictionary_save_dialog',
    ),
}


def __getattr__(name: str) -> Any:
    if name in _LAZY_IMPORTS:
        mod_rel, attr = _LAZY_IMPORTS[name]
        module = importlib.import_module(mod_rel, __name__)
        obj = getattr(module, attr)
        globals()[name] = obj
        return obj
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")


def __dir__() -> list[str]:
    return sorted(__all__)
