"""
Microscope control via audio communication

Uses FSK audio modem for bidirectional communication with airgapped microscope PC.
Sends CAPTURE command and waits for DONE response.
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
from audio_protocol import AudioModem, Command, FSKConfig


class Microscope:
    """
    Bidirectional microscope controller using FSK audio modem.
    
    Sends CAPTURE command to trigger acquisition, waits for DONE response.
    """
    
    def __init__(self, output_device: Optional[int] = None, input_device: Optional[int] = None):
        """
        Initialize microscope controller.
        
        Args:
            output_device: Audio output device ID. If None, uses saved or default device.
            input_device: Audio input device ID. If None, uses saved or default device.
        """
        self.is_initialized = False
        self.last_error = ""
        self.output_device = output_device
        self.input_device = input_device
        
        # Load saved devices if not specified
        config = load_audio_config()
        
        if self.output_device is None:
            self.output_device = config.get('output_device')
            if self.output_device is None:
                try:
                    self.output_device = sd.default.device[1]
                    save_audio_config(output_device=self.output_device)
                except Exception as e:
                    self.last_error = f"Failed to get default output device: {e}"
                    logging.error(self.last_error)
                    return
        
        if self.input_device is None:
            self.input_device = config.get('input_device')
            if self.input_device is None:
                try:
                    self.input_device = sd.default.device[0]
                    save_audio_config(input_device=self.input_device)
                except Exception as e:
                    self.last_error = f"Failed to get default input device: {e}"
                    logging.error(self.last_error)
                    return
        
        # Initialize FSK modem
        self.modem = AudioModem(FSKConfig())
        
        self.is_initialized = True
        logging.info(f"Microscope controller initialized (output: {self.output_device}, input: {self.input_device})")
    
    def acquire(self, timeout: float = 300.0) -> bool:
        """
        Trigger image acquisition on microscope and wait for completion.
        
        Sends CAPTURE command via audio, waits for DONE response from microscope.
        
        Args:
            timeout: Maximum time to wait for acquisition completion (default: 5 minutes)
        
        Returns:
            True if acquisition completed successfully, False on timeout or error
        """
        if not self.is_initialized:
            print(f"✗ Microscope not initialized: {self.last_error}")
            return False
        
        try:
            print("� Triggering microscope acquisition...")
            
            # Send CAPTURE command
            audio = self.modem.encode_command(Command.CAPTURE)
            sd.play(audio, self.modem.config.sample_rate, device=self.output_device)
            sd.wait()
            
            print("✓ CAPTURE command sent")
            logging.info("CAPTURE command sent to microscope")
            
            # Wait for DONE response
            print(f"⏳ Waiting for acquisition to complete (timeout: {timeout}s)...")
            done_received = self._wait_for_done(timeout)
            
            if done_received:
                print("✓ Microscope acquisition complete!")
                logging.info("Received DONE signal from microscope")
                return True
            else:
                print("✗ Timeout waiting for microscope completion")
                logging.warning(f"No DONE signal received within {timeout}s")
                return False
            
        except Exception as e:
            self.last_error = f"Acquisition failed: {e}"
            print(f"✗ {self.last_error}")
            logging.error(self.last_error)
            return False
    
    def _wait_for_done(self, timeout: float) -> bool:
        """
        Listen for DONE command from microscope.
        
        Args:
            timeout: Maximum time to wait in seconds
        
        Returns:
            True if DONE received, False on timeout
        """
        sample_rate = self.modem.config.sample_rate
        start_time = time.time()
        chunk_duration = 5.0  # Record in 5-second chunks
        chunk_num = 0
        
        while time.time() - start_time < timeout:
            elapsed = time.time() - start_time
            remaining = int(timeout - elapsed)
            chunk_num += 1
            
            print(f"  Listening for DONE... ({remaining}s remaining, chunk #{chunk_num})")
            
            # Record audio chunk
            recording = sd.rec(
                int(chunk_duration * sample_rate),
                samplerate=sample_rate,
                channels=1,
                device=self.input_device,
                dtype='float32'
            )
            sd.wait()
            
            # Check audio levels for debugging
            audio_data = recording[:, 0]
            max_amp = np.max(np.abs(audio_data))
            rms = np.sqrt(np.mean(audio_data ** 2))
            
            if max_amp > 0.01:
                print(f"    🔊 Sound detected! max={max_amp:.4f}, rms={rms:.4f}")
                debug_mode = True
            elif max_amp > 0.001:
                print(f"    ~ Weak audio: max={max_amp:.4f}, rms={rms:.4f}")
                debug_mode = False
            else:
                print(f"    - Silence: max={max_amp:.4f}")
                debug_mode = False
            
            # Try to decode
            command = self.modem.decode_command(audio_data, debug=debug_mode)
            
            if command == Command.DONE:
                print("    ✓ DONE command received!")
                return True
            elif command is not None:
                print(f"    ⚠ Unexpected command: {command.name} (expecting DONE)")
        
        return False
    
    def close(self) -> None:
        """Cleanup resources"""
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