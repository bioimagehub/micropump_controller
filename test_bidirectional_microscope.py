"""
Test bidirectional communication between sender and receiver

This script demonstrates the full communication cycle:
1. Sender sends CAPTURE command
2. Receiver responds with DONE command

Run this on the SENDER (controller) PC to test communication with microscope PC.

Usage:
    python test_bidirectional_microscope.py
"""

import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent / "test_audio_comunication"))

from audio_protocol import AudioModem, Command, FSKConfig
import sounddevice as sd
import numpy as np
import time
from audio_config import load_audio_config

def main():
    print("=" * 70)
    print("BIDIRECTIONAL MICROSCOPE COMMUNICATION TEST")
    print("=" * 70)
    
    # Load audio devices
    config = load_audio_config()
    output_device = config.get('output_device')
    input_device = config.get('input_device')
    
    if output_device is None or input_device is None:
        print("\n✗ Audio devices not configured!")
        print("  Please run microscope_listener.py first to configure devices")
        return
    
    print(f"\nUsing devices:")
    print(f"  Output: {output_device}")
    print(f"  Input: {input_device}")
    
    # Initialize modem
    modem = AudioModem(FSKConfig())
    sample_rate = modem.config.sample_rate
    
    # Test 1: Send CAPTURE command
    print("\n" + "=" * 70)
    print("TEST 1: Send CAPTURE Command")
    print("=" * 70)
    print("\nMake sure microscope_listener.py is running on the microscope PC!")
    input("Press Enter to send CAPTURE command...")
    
    print("\n🔊 Sending CAPTURE...")
    audio = modem.encode_command(Command.CAPTURE)
    sd.play(audio, sample_rate, device=output_device)
    sd.wait()
    print("✓ CAPTURE sent")
    
    # Test 2: Wait for DONE response
    print("\n" + "=" * 70)
    print("TEST 2: Wait for DONE Response")
    print("=" * 70)
    print("\nListening for DONE command...")
    print("(Timeout: 60 seconds)\n")
    
    timeout = 60.0
    chunk_duration = 5.0
    start_time = time.time()
    chunk_num = 0
    
    while time.time() - start_time < timeout:
        chunk_num += 1
        remaining = int(timeout - (time.time() - start_time))
        
        print(f"  Listening... ({remaining}s remaining, chunk #{chunk_num})")
        
        # Record audio
        recording = sd.rec(
            int(chunk_duration * sample_rate),
            samplerate=sample_rate,
            channels=1,
            device=input_device,
            dtype='float32'
        )
        sd.wait()
        
        # Check audio levels
        audio_data = recording[:, 0]
        max_amp = np.max(np.abs(audio_data))
        rms = np.sqrt(np.mean(audio_data ** 2))
        
        debug_mode = False
        if max_amp > 0.01:
            print(f"    🔊 Sound detected! max={max_amp:.4f}, rms={rms:.4f}")
            debug_mode = True
        elif max_amp > 0.001:
            print(f"    ~ Weak audio: max={max_amp:.4f}")
        
        # Try to decode
        command = modem.decode_command(audio_data, debug=debug_mode)
        
        if command == Command.DONE:
            print("\n✅ SUCCESS! Received DONE command")
            print("\n" + "=" * 70)
            print("BIDIRECTIONAL COMMUNICATION WORKING!")
            print("=" * 70)
            return
        elif command is not None:
            print(f"    ⚠ Unexpected command: {command.name}")
    
    print("\n✗ TIMEOUT - No DONE received")
    print("\nTroubleshooting:")
    print("  1. Is microscope_listener.py running on microscope PC?")
    print("  2. Is audio cable connected?")
    print("  3. Check audio device configuration")
    

if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\n\nInterrupted by user")
    except Exception as e:
        print(f"\n✗ ERROR: {e}")
        import traceback
        traceback.print_exc()
