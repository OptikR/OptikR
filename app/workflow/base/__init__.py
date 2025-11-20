"""
Base classes for subprocess-based pipeline system.

This module provides the foundation for running pipeline stages
as isolated subprocesses with crash protection and automatic restart.
"""

from .base_subprocess import BaseSubprocess
from .base_worker import BaseWorker
from .plugin_interface import PluginMetadata, PluginSettings

__all__ = [
    'BaseSubprocess',
    'BaseWorker',
    'PluginMetadata',
    'PluginSettings',
]
