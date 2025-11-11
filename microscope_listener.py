"""
Microscope Listener - Listens for 1000 Hz audio signal and clicks screen button

This runs on the MICROSCOPE PC (airgapped computer).
When it hears 1000 Hz from the microfluidics PC, it clicks the "Run" button.

Usage:
    python microscope_listener.py
"""

import sounddevice as sd
import numpy as np
import pyautogui
import time
from pathlib import Path
from typing import Optional

# Add test_audio_comunication to path for imports
import sys
sys.path.insert(0, str(Path(__file__).parent / "test_audio_comunication"))
from audio_config import load_audio_config, save_audio_config

# Audio configuration
SAMPLE_RATE = 44100
TRIGGER_FREQ = 1000  # Hz - frequency to listen for
FREQ_TOLERANCE = 50  # Hz - how close the frequency needs to be
MIN_MAGNITUDE = 100  # Minimum FFT magnitude to consider valid signal
CHUNK_DURATION = 1.0  # seconds - how long to record each chunk

# Screen click configuration (to be customized per setup)
BUTTON_X = None  # Will be configured on first run
BUTTON_Y = None


def detect_frequency(audio_chunk: np.ndarray) -> tuple[float, float]:
    """
    Detect dominant frequency in audio chunk using FFT.
    
    Returns:
        (frequency, magnitude) - dominant frequency in Hz and its magnitude
    """
    # Apply FFT
    fft = np.fft.rfft(audio_chunk)
    freqs = np.fft.rfftfreq(len(audio_chunk), 1/SAMPLE_RATE)
    magnitudes = np.abs(fft)
    
    # Find peak frequency
    peak_idx = np.argmax(magnitudes)
    peak_freq = freqs[peak_idx]
    peak_mag = magnitudes[peak_idx]
    
    return peak_freq, peak_mag


def find_audio_device() -> int:
    """
    Find the correct audio input device.
    First tries saved config, then scans all devices.
    
    Returns:
        device_id - ID of working input device
    """
    print("=" * 70)
    print("MICROSCOPE LISTENER - Audio Device Setup")
    print("=" * 70)
    
    # Try saved config first
    config = load_audio_config()
    saved_input = config.get('input_device')
    
    if saved_input is not None:
        print(f"\n✓ Found saved input device: {saved_input}")
        
        # Test if it still works
        print("  Testing saved device...")
        try:
            test_recording = sd.rec(int(0.5 * SAMPLE_RATE), samplerate=SAMPLE_RATE,
                                   channels=1, device=saved_input, dtype='float32')
            sd.wait()
            print("  ✓ Saved device works!")
            return saved_input
        except Exception as e:
            print(f"  ✗ Saved device failed: {e}")
            print("  Will scan for new device...\n")
    
    # Show all available input devices
    devices = sd.query_devices()
    print("\nAvailable audio input devices:")
    input_devices = []
    for i, device in enumerate(devices):
        if device['max_input_channels'] > 0:
            print(f"  [{i}] {device['name']}")
            input_devices.append(i)
    
    if not input_devices:
        raise RuntimeError("No audio input devices found!")
    
    # Manual selection
    print("\n" + "=" * 70)
    print("MANUAL DEVICE SELECTION")
    print("=" * 70)
    print(f"\nThe sender PC should be playing {TRIGGER_FREQ} Hz continuously.")
    print("We'll test each device to find which one hears it.\n")
    
    while True:
        device_input = input("Enter device number to test (or 'auto' to scan all): ").strip()
        
        if device_input.lower() == 'auto':
            # Auto-scan all devices
            print("\nScanning all devices...")
            for device_id in input_devices:
                if test_device_for_trigger(device_id):
                    save_audio_config(input_device=device_id)
                    return device_id
            
            print("\n✗ No device detected the trigger signal!")
            print("  Make sure sender is playing and cable is connected.")
            continue
        
        try:
            device_id = int(device_input)
            if device_id in input_devices:
                if test_device_for_trigger(device_id):
                    save_audio_config(input_device=device_id)
                    return device_id
                else:
                    print(f"✗ Device {device_id} didn't hear {TRIGGER_FREQ} Hz")
            else:
                print(f"✗ Invalid device ID: {device_id}")
        except ValueError:
            print("✗ Please enter a number or 'auto'")


def test_device_for_trigger(device_id: int) -> bool:
    """
    Test if a device can hear the trigger frequency.
    
    Args:
        device_id: Audio device ID to test
        
    Returns:
        True if device hears trigger frequency
    """
    try:
        device = sd.query_devices(device_id)
        print(f"  Testing [{device_id}] {device['name'][:50]}...", end='', flush=True)
        
        # Record 1 second
        recording = sd.rec(int(CHUNK_DURATION * SAMPLE_RATE), 
                          samplerate=SAMPLE_RATE,
                          channels=1, 
                          device=device_id, 
                          dtype='float32')
        sd.wait()
        
        # Analyze
        audio = recording[:, 0]
        freq, mag = detect_frequency(audio)
        
        print(f" detected {freq:.0f} Hz (mag: {mag:.0f})")
        
        # Check if it's the trigger frequency
        if abs(freq - TRIGGER_FREQ) < FREQ_TOLERANCE and mag > MIN_MAGNITUDE:
            print(f"    ✓ FOUND! This device hears {TRIGGER_FREQ} Hz!")
            return True
        
        return False
        
    except Exception as e:
        print(f" ERROR: {e}")
        return False


def listen_for_trigger(device_id: int) -> None:
    """
    Main listening loop - waits for trigger signal and clicks button.
    
    Args:
        device_id: Audio input device to listen on
    """
    print("\n" + "=" * 70)
    print("🎧 LISTENING FOR TRIGGER SIGNAL")
    print("=" * 70)
    print(f"\nListening on device {device_id}")
    print(f"Trigger frequency: {TRIGGER_FREQ} Hz")
    print(f"Will click screen when signal detected\n")
    print("Press Ctrl+C to stop\n")
    
    chunk_count = 0
    
    try:
        while True:
            chunk_count += 1
            
            # Record audio chunk
            recording = sd.rec(int(CHUNK_DURATION * SAMPLE_RATE),
                             samplerate=SAMPLE_RATE,
                             channels=1,
                             device=device_id,
                             dtype='float32')
            sd.wait()
            
            # Analyze
            audio = recording[:, 0]
            freq, mag = detect_frequency(audio)
            rms = np.sqrt(np.mean(audio ** 2))
            
            # Print status
            timestamp = time.strftime("%H:%M:%S")
            print(f"[{timestamp}] Chunk {chunk_count}: freq={freq:.0f} Hz, mag={mag:.0f}, rms={rms:.4f}", 
                  end='')
            
            # Check for trigger
            if abs(freq - TRIGGER_FREQ) < FREQ_TOLERANCE and mag > MIN_MAGNITUDE:
                print(" ← TRIGGER DETECTED!")
                click_run_button()
            else:
                print()
            
    except KeyboardInterrupt:
        print("\n\n" + "=" * 70)
        print("Stopped listening")
        print("=" * 70)


def click_run_button() -> None:
    """
    Click the 'Run' button on screen.
    On first run, asks user to position mouse over button.
    """
    global BUTTON_X, BUTTON_Y
    
    if BUTTON_X is None or BUTTON_Y is None:
        print("\n" + "=" * 70)
        print("BUTTON POSITION SETUP")
        print("=" * 70)
        print("\nMove your mouse over the 'Run' button on screen.")
        print("You have 5 seconds...")
        
        for i in range(5, 0, -1):
            print(f"  {i}...", flush=True)
            time.sleep(1)
        
        BUTTON_X, BUTTON_Y = pyautogui.position()
        print(f"\n✓ Button position saved: ({BUTTON_X}, {BUTTON_Y})")
        print("=" * 70 + "\n")
    
    # Click the button
    print(f"  🖱️  Clicking button at ({BUTTON_X}, {BUTTON_Y})...")
    pyautogui.click(BUTTON_X, BUTTON_Y)
    print("  ✓ Button clicked!")
    
    # Brief delay to prevent rapid re-triggering
    time.sleep(2)


def main() -> None:
    """Main entry point"""
    print("\n")
    print("=" * 70)
    print("MICROSCOPE LISTENER")
    print("Listens for audio signal and clicks 'Run' button")
    print("=" * 70)
    
    # Find audio device
    device_id = find_audio_device()
    
    # Start listening
    listen_for_trigger(device_id)


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\n\nInterrupted by user")
    except Exception as e:
        print(f"\n✗ ERROR: {e}")
        import traceback
        traceback.print_exc()
