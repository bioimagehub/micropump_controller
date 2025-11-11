"""
Microscope control via audio communication

Sends 1000 Hz trigger signal to airgapped microscope PC.
The microscope_listener.py running on the microscope PC will click the Run button.
"""

import sounddevice as sd
import numpy as np
import time
from pathlib import Path
from typing import Optional
import logging

# Add test_audio_comunication to path for imports
import sys
sys.path.insert(0, str(Path(__file__).parent.parent / "test_audio_comunication"))
from audio_config import load_audio_config, save_audio_config


class Microscope:
    """
    Simple microscope controller that triggers image acquisition via audio signal.
    
    Sends 1000 Hz tone to trigger microscope_listener.py on the airgapped microscope PC.
    """
    
    TRIGGER_FREQ = 1000  # Hz - frequency to send
    TRIGGER_DURATION = 2.0  # seconds - how long to send signal
    SAMPLE_RATE = 44100
    
    def __init__(self, output_device: Optional[int] = None):
        """
        Initialize microscope controller.
        
        Args:
            output_device: Audio output device ID. If None, uses saved or default device.
        """
        self.is_initialized = False
        self.last_error = ""
        self.output_device = output_device
        
        # Load saved output device if not specified
        if self.output_device is None:
            config = load_audio_config()
            self.output_device = config.get('output_device')
            
            if self.output_device is None:
                # Use default output device
                try:
                    self.output_device = sd.default.device[1]
                    save_audio_config(output_device=self.output_device)
                except Exception as e:
                    self.last_error = f"Failed to get default output device: {e}"
                    logging.error(self.last_error)
                    return
        
        # Generate trigger tone (1000 Hz)
        t = np.linspace(0, self.TRIGGER_DURATION, int(self.SAMPLE_RATE * self.TRIGGER_DURATION))
        self.trigger_tone = 0.5 * np.sin(2 * np.pi * self.TRIGGER_FREQ * t)
        
        self.is_initialized = True
        logging.info(f"Microscope controller initialized (audio device {self.output_device})")
    
    def acquire(self) -> bool:
        """
        Trigger image acquisition on microscope.
        
        Sends 1000 Hz audio signal that microscope_listener.py will detect
        and respond to by clicking the Run button.
        
        Returns:
            True if signal sent successfully, False otherwise
        """
        if not self.is_initialized:
            print(f"✗ Microscope not initialized: {self.last_error}")
            return False
        
        try:
            print(f"🔊 Sending microscope trigger ({self.TRIGGER_FREQ} Hz for {self.TRIGGER_DURATION}s)...")
            
            # Play trigger tone
            sd.play(self.trigger_tone, self.SAMPLE_RATE, device=self.output_device)
            sd.wait()
            
            print("✓ Microscope trigger sent")
            logging.info("Microscope trigger sent successfully")
            return True
            
        except Exception as e:
            self.last_error = f"Failed to send trigger: {e}"
            print(f"✗ {self.last_error}")
            logging.error(self.last_error)
            return False
    
    def close(self) -> None:
        """Cleanup (nothing to do for audio-based controller)"""
        logging.info("Microscope controller closed")


# Backwards compatibility alias
MicroscopeController = Microscope


# For testing
if __name__ == "__main__":
    print("=" * 70)
    print("MICROSCOPE CONTROLLER TEST")
    print("=" * 70)
    
    microscope = Microscope()
    
    if not microscope.is_initialized:
        print(f"✗ Failed to initialize: {microscope.last_error}")
    else:
        print("✓ Microscope controller initialized")
        print(f"  Using output device: {microscope.output_device}")
        
        input("\nPress Enter to send trigger signal...")
        
        if microscope.acquire():
            print("\n✓ Success!")
        else:
            print("\n✗ Failed!")
        
        microscope.close()