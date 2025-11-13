"""
Microscope Listener - Bidirectional audio communication for microscope control

This runs on the MICROSCOPE PC (airgapped computer).
1. Listens for CAPTURE command via FSK audio modem
2. Clicks the "Acquire" button
3. Monitors button state (waits for grey, then normal again)
4. Sends DONE command back when acquisition completes

Usage:
    python microscope_listener.py
"""

import sounddevice as sd
import numpy as np
import pyautogui
import time
from pathlib import Path
from typing import Optional, Tuple
from PIL import ImageGrab

# Add test_audio_comunication to path for imports
import sys
sys.path.insert(0, str(Path(__file__).parent / "test_audio_comunication"))
from audio_config import load_audio_config, save_audio_config
from audio_protocol import AudioModem, Command, FSKConfig

# Screen click configuration (to be customized per setup)
BUTTON_X = None  # Will be configured on first run
BUTTON_Y = None
BUTTON_NORMAL_COLOR = None  # RGB color of button when ready (will be calibrated)


def find_audio_devices() -> Tuple[int, int]:
    """
    Find the correct audio input and output devices.
    First tries saved config, then scans all devices.
    
    Returns:
        (input_device_id, output_device_id)
    """
    print("=" * 70)
    print("MICROSCOPE LISTENER - Audio Device Setup")
    print("=" * 70)
    
    # Try saved config first
    config = load_audio_config()
    saved_input = config.get('input_device')
    saved_output = config.get('output_device')
    
    if saved_input is not None and saved_output is not None:
        print(f"\n✓ Found saved devices:")
        print(f"  Input: {saved_input}")
        print(f"  Output: {saved_output}")
        return saved_input, saved_output
    
    # Manual selection
    devices = sd.query_devices()
    print("\nAvailable audio devices:")
    input_devices = []
    output_devices = []
    
    for i, device in enumerate(devices):
        in_channels = device['max_input_channels']
        out_channels = device['max_output_channels']
        if in_channels > 0:
            print(f"  [{i}] {device['name']} (INPUT)")
            input_devices.append(i)
        if out_channels > 0:
            print(f"  [{i}] {device['name']} (OUTPUT)")
            output_devices.append(i)
    
    if not input_devices or not output_devices:
        raise RuntimeError("Need both input and output audio devices!")
    
    print("\n" + "=" * 70)
    print("DEVICE SELECTION")
    print("=" * 70)
    
    input_id = int(input("Enter INPUT device number (for receiving signals): ").strip())
    output_id = int(input("Enter OUTPUT device number (for sending signals): ").strip())
    
    save_audio_config(input_device=input_id, output_device=output_id)
    return input_id, output_id


def setup_button_position() -> Tuple[int, int]:
    """
    Get user to position mouse over Acquire button.
    
    Returns:
        (x, y) coordinates of button
    """
    global BUTTON_X, BUTTON_Y
    
    print("\n" + "=" * 70)
    print("ACQUIRE BUTTON POSITION SETUP")
    print("=" * 70)
    print("\nMove your mouse over the 'Acquire' button.")
    print("You have 5 seconds...")
    
    for i in range(5, 0, -1):
        print(f"  {i}...", flush=True)
        time.sleep(1)
    
    BUTTON_X, BUTTON_Y = pyautogui.position()
    print(f"\n✓ Button position saved: ({BUTTON_X}, {BUTTON_Y})")
    print("=" * 70 + "\n")
    
    return BUTTON_X, BUTTON_Y


def calibrate_button_color(x: int, y: int) -> Tuple[int, int, int]:
    """
    Capture the normal (ready) color of the Acquire button.
    
    Args:
        x, y: Button coordinates
    
    Returns:
        (R, G, B) color tuple
    """
    global BUTTON_NORMAL_COLOR
    
    print("\n" + "=" * 70)
    print("BUTTON COLOR CALIBRATION")
    print("=" * 70)
    print("\nMake sure the Acquire button is in its NORMAL state (not grey/disabled).")
    input("Press Enter when ready...")
    
    # Capture small region around button
    screenshot = ImageGrab.grab(bbox=(x-5, y-5, x+5, y+5))
    pixels = list(screenshot.getdata())
    
    # Average the color (in case of antialiasing)
    r = sum(p[0] for p in pixels) // len(pixels)
    g = sum(p[1] for p in pixels) // len(pixels)
    b = sum(p[2] for p in pixels) // len(pixels)
    
    BUTTON_NORMAL_COLOR = (r, g, b)
    print(f"✓ Normal button color: RGB({r}, {g}, {b})")
    print("=" * 70 + "\n")
    
    return BUTTON_NORMAL_COLOR


def is_button_normal(x: int, y: int, normal_color: Tuple[int, int, int]) -> bool:
    """
    Check if button is back to normal color (acquisition complete).
    
    Args:
        x, y: Button coordinates
        normal_color: RGB color of normal state
    
    Returns:
        True if button appears to be in normal state
    """
    # Capture button region
    screenshot = ImageGrab.grab(bbox=(x-5, y-5, x+5, y+5))
    pixels = list(screenshot.getdata())
    
    # Average current color
    r = sum(p[0] for p in pixels) // len(pixels)
    g = sum(p[1] for p in pixels) // len(pixels)
    b = sum(p[2] for p in pixels) // len(pixels)
    
    # Check if similar to normal color (within tolerance)
    tolerance = 30  # RGB difference tolerance
    r_diff = abs(r - normal_color[0])
    g_diff = abs(g - normal_color[1])
    b_diff = abs(b - normal_color[2])
    
    return r_diff < tolerance and g_diff < tolerance and b_diff < tolerance


def wait_for_acquisition_complete(x: int, y: int, normal_color: Tuple[int, int, int], 
                                   max_wait: float = 600.0) -> bool:
    """
    Monitor button state until acquisition completes.
    
    Wait 1 second, then check if button is grey (acquisition running).
    Then wait for it to return to normal (acquisition done).
    
    Args:
        x, y: Button coordinates
        normal_color: RGB color of normal state
        max_wait: Maximum time to wait in seconds
    
    Returns:
        True if acquisition completed, False on timeout
    """
    print("  Waiting 1 second before monitoring...")
    time.sleep(1.0)
    
    # Check if button went grey (acquisition started)
    print("  Checking if acquisition started...")
    if is_button_normal(x, y, normal_color):
        print("  ⚠ Button still normal color - acquisition may not have started")
    else:
        print("  ✓ Button changed (acquisition running)")
    
    # Now wait for it to return to normal
    print(f"  Monitoring button state (max {max_wait}s)...")
    start_time = time.time()
    check_count = 0
    
    while time.time() - start_time < max_wait:
        check_count += 1
        elapsed = time.time() - start_time
        
        if is_button_normal(x, y, normal_color):
            print(f"  ✓ Button returned to normal after {elapsed:.1f}s ({check_count} checks)")
            return True
        
        # Check every 2 seconds
        if check_count % 10 == 0:
            print(f"  ... still waiting ({elapsed:.0f}s elapsed)")
        
        time.sleep(2.0)
    
    print(f"  ✗ Timeout after {max_wait}s")
    return False


def send_done_signal(output_device: int, modem: AudioModem) -> bool:
    """
    Send DONE command back to controller.
    
    Args:
        output_device: Audio output device ID
        modem: AudioModem instance
    
    Returns:
        True if sent successfully
    """
    try:
        print("\n🔊 Sending DONE command...")
        audio = modem.encode_command(Command.DONE)
        sd.play(audio, modem.config.sample_rate, device=output_device)
        sd.wait()
        print("✓ DONE command sent")
        return True
    except Exception as e:
        print(f"✗ Failed to send DONE: {e}")
        return False


def listen_and_respond(input_device: int, output_device: int) -> None:
    """
    Main listening loop - waits for CAPTURE, clicks button, monitors, sends DONE.
    
    Args:
        input_device: Audio input device ID
        output_device: Audio output device ID
    """
    global BUTTON_X, BUTTON_Y, BUTTON_NORMAL_COLOR
    
    # Setup button if not configured
    if BUTTON_X is None or BUTTON_Y is None:
        BUTTON_X, BUTTON_Y = setup_button_position()
    
    if BUTTON_NORMAL_COLOR is None:
        BUTTON_NORMAL_COLOR = calibrate_button_color(BUTTON_X, BUTTON_Y)
    
    # Initialize modem
    modem = AudioModem(FSKConfig())
    sample_rate = modem.config.sample_rate
    
    print("\n" + "=" * 70)
    print("🎧 LISTENING FOR CAPTURE COMMAND")
    print("=" * 70)
    print(f"\nListening on device {input_device}")
    print(f"Will send DONE on device {output_device}")
    print(f"Button position: ({BUTTON_X}, {BUTTON_Y})")
    print("\nPress Ctrl+C to stop\n")
    
    chunk_duration = 5.0  # Record in 5-second chunks
    chunk_count = 0
    
    try:
        while True:
            chunk_count += 1
            timestamp = time.strftime("%H:%M:%S")
            
            print(f"[{timestamp}] Listening for CAPTURE... (chunk #{chunk_count})")
            
            # Record audio chunk
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
                print(f"  🔊 Sound detected! max={max_amp:.4f}, rms={rms:.4f}")
                debug_mode = True
            elif max_amp > 0.001:
                print(f"  ~ Weak audio: max={max_amp:.4f}")
            
            # Try to decode
            command = modem.decode_command(audio_data, debug=debug_mode)
            
            if command == Command.CAPTURE:
                print("  ✓ CAPTURE command received!")
                
                # Click Acquire button
                print(f"  🖱️  Clicking Acquire button at ({BUTTON_X}, {BUTTON_Y})...")
                pyautogui.click(BUTTON_X, BUTTON_Y)
                print("  ✓ Button clicked")
                
                # Wait for acquisition to complete
                print("  ⏳ Monitoring acquisition...")
                if wait_for_acquisition_complete(BUTTON_X, BUTTON_Y, BUTTON_NORMAL_COLOR):
                    print("  ✓ Acquisition complete!")
                    
                    # Send DONE signal
                    send_done_signal(output_device, modem)
                    
                    print("\n✅ Cycle complete - ready for next trigger\n")
                else:
                    print("  ✗ Acquisition monitoring failed")
                    print("\n⚠ Ready for next trigger (despite error)\n")
                
            elif command is not None:
                print(f"  ⚠ Unexpected command: {command.name} (ignoring)")
    
    except KeyboardInterrupt:
        print("\n\n" + "=" * 70)
        print("Stopped listening")
        print("=" * 70)


def main() -> None:
    """Main entry point"""
    print("\n")
    print("=" * 70)
    print("MICROSCOPE LISTENER - BIDIRECTIONAL MODE")
    print("Listens for CAPTURE, clicks Acquire, sends DONE when complete")
    print("=" * 70)
    
    # Find audio devices
    input_device, output_device = find_audio_devices()
    
    # Start listening
    listen_and_respond(input_device, output_device)


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\n\nInterrupted by user")
    except Exception as e:
        print(f"\n✗ ERROR: {e}")
        import traceback
        traceback.print_exc()
