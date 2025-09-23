#!/usr/bin/env python3
"""
Audio package for micropump controller.

This package provides audio monitoring capabilities to detect and analyze
sound changes during micropump operations.
"""

from .monitor import SimpleAudioCommandMonitor
from .discovery import AudioDiscovery

__version__ = "1.0.0"
__all__ = ["SimpleAudioCommandMonitor", "AudioDiscovery"]

# Package-level convenience functions
def quick_audio_test(command, baseline_duration=2.0):
    """Quick audio test with a command."""
    monitor = SimpleAudioCommandMonitor(baseline_duration=baseline_duration)
    return monitor.run_full_test(command)

def discover_audio_devices():
    """Discover and test audio devices."""
    discovery = AudioDiscovery()
    working_devices = discovery.test_all_input_devices()
    discovery.display_working_devices()
    return discovery.recommend_best_device()