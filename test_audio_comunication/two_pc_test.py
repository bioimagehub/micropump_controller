"""
Quick two-terminal test for audio communication.

Run this script in two separate terminals to test audio communication
between them on the same PC.

Terminal 1: python two_pc_test.py sender
Terminal 2: python two_pc_test.py receiver

This simulates communication between microfluidics PC and microscope PC.
"""

import sys
from audio_protocol import MicroscopeAudioController, Command
import time
import numpy as np


def test_audio_hardware() -> tuple[bool, int, int]:
    """
    Test that both speakers and microphone are working.
    Automatically tries different input devices until one works.
    
    Returns (success, input_device_id, output_device_id)
    """
    print("=" * 60)
    print("AUDIO HARDWARE TEST")
    print("=" * 60)
    
    try:
        import sounddevice as sd
    except ImportError:
        print("✗ sounddevice not installed")
        return False, None, None
    
    # Test 1: Find and test output device
    print("\n[1/4] Checking audio output (speakers)...")
    output_device_id = None
    try:
        output_device = sd.query_devices(kind='output')
        output_device_id = sd.default.device[1]  # Get default output ID
        print(f"✓ Output device: {output_device['name']}")
    except Exception as e:
        print(f"✗ No output device found: {e}")
        return False, None, None
    
    # Test 2: Test speaker output
    print("\n[2/4] Testing speaker output...")
    print("  Playing 1-second test tone at 1000 Hz...")
    
    try:
        sample_rate = 44100
        duration = 1.0
        frequency = 1000
        
        t = np.linspace(0, duration, int(sample_rate * duration))
        tone = 0.3 * np.sin(2 * np.pi * frequency * t)
        
        sd.play(tone, sample_rate, device=output_device_id)
        sd.wait()
        
        print("✓ Test tone played (should have heard a beep)")
        
    except Exception as e:
        print(f"✗ Speaker test failed: {e}")
        return False, None, None
    
    # Test 3: Find all input devices
    print("\n[3/4] Finding input devices...")
    all_devices = sd.query_devices()
    input_devices = []
    
    for i, device in enumerate(all_devices):
        if device['max_input_channels'] > 0:
            input_devices.append((i, device))
    
    if not input_devices:
        print("✗ No input devices found!")
        print("  Please connect a microphone or headset")
        return False, None, None
    
    print(f"  Found {len(input_devices)} input device(s)")
    
    # Test 4: Try each input device automatically
    print("\n[4/4] Testing microphone input...")
    print("  Auto-testing each device (make noise during tests)...\n")
    
    working_device = None
    
    # Try default first if it exists
    try:
        default_input = sd.query_devices(kind='input')
        default_id = sd.default.device[0]
        print(f"  [Default] Testing: {default_input['name']}")
        
        if test_input_device(sd, default_id, duration=3.0):
            working_device = default_id
            print(f"  ✓ Default device working!")
    except Exception as e:
        print(f"  ⚠ No default input device set")
    
    # If default didn't work, try all available devices
    if working_device is None:
        for idx, (device_id, device) in enumerate(input_devices):
            print(f"\n  [{idx+1}/{len(input_devices)}] Testing device {device_id}: {device['name'][:50]}...")
            
            if test_input_device(sd, device_id, duration=3.0):
                working_device = device_id
                print(f"  ✓ Device {device_id} working!")
                break
            else:
                print(f"  ✗ No audio detected on device {device_id}")
    
    if working_device is not None:
        print("\n" + "=" * 60)
        print("✓ AUDIO HARDWARE TEST PASSED")
        print("=" * 60)
        return True, working_device, output_device_id
    else:
        print("\n" + "=" * 60)
        print("✗ NO WORKING MICROPHONE FOUND")
        print("=" * 60)
        print("\nTried all available input devices but none detected audio.")
        print("Please check:")
        print("  - Microphone is not muted")
        print("  - Headset is properly connected")
        print("  - Windows microphone permissions are enabled")
        print("  - Microphone volume is turned up")
        
        response = input("\nContinue anyway? (y/n): ").strip().lower()
        if response == 'y':
            # Use first available device as fallback
            fallback_id = input_devices[0][0]
            print(f"Using device {fallback_id} as fallback")
            return True, fallback_id, output_device_id
        else:
            return False, None, None


def test_input_device(sd, device_id: int, duration: float = 3.0) -> bool:
    """
    Test if a specific input device can detect audio.
    
    Args:
        sd: sounddevice module
        device_id: Device ID to test
        duration: Recording duration in seconds
        
    Returns:
        True if audio detected, False otherwise
    """
    try:
        sample_rate = 44100
        
        print(f"    Recording {duration}s... (please make noise!)", end='', flush=True)
        
        recording = sd.rec(
            int(duration * sample_rate),
            samplerate=sample_rate,
            channels=1,
            device=device_id,
            dtype='float32'
        )
        sd.wait()
        
        # Analyze recording
        audio_data = recording[:, 0]
        max_amplitude = np.max(np.abs(audio_data))
        rms = np.sqrt(np.mean(audio_data ** 2))
        
        print(f" max={max_amplitude:.4f}, rms={rms:.4f}")
        
        # Consider it working if we detect any reasonable audio
        if max_amplitude > 0.001:
            return True
        else:
            return False
            
    except Exception as e:
        print(f" ERROR: {e}")
        return False


def run_sender() -> None:
    """Simulate microfluidics PC sending commands"""
    print("=" * 60)
    print("SENDER MODE (Simulating Microfluidics PC)")
    print("=" * 60)
    print("\nThis terminal will send audio commands.")
    print("Make sure the RECEIVER terminal is running first!\n")
    
    # Test audio hardware first
    success, input_device, output_device = test_audio_hardware()
    if not success:
        print("\n✗ Audio hardware test failed!")
        print("  Cannot proceed without working audio devices.")
        return
    
    print("\n" + "=" * 60)
    print("✓ Audio hardware test passed!")
    print(f"  Using input device: {input_device}")
    print(f"  Using output device: {output_device}")
    print("=" * 60)
    
    input("\nPress Enter when receiver is ready...")
    
    controller = MicroscopeAudioController(input_device=input_device, output_device=output_device)
    
    if not controller.is_initialized:
        print(f"✗ Error: {controller.last_error}")
        return
    
    print("\n" + "=" * 60)
    print("Test 1: PING/PONG")
    print("=" * 60)
    
    print("\nSending PING command...")
    if controller.send_command(Command.PING):
        print("✓ PING sent successfully")
        print("\nListening for PONG response...")
        response = controller.wait_for_command(timeout=30, expected=Command.PONG)
        
        if response == Command.PONG:
            print("✓ PONG received! Audio communication working!")
        else:
            print("✗ No PONG received - check audio setup")
    
    print("\n" + "=" * 60)
    print("Test 2: CAPTURE/DONE (Simulating Microscope Trigger)")
    print("=" * 60)
    
    input("\nPress Enter to trigger microscope capture...")
    
    if controller.trigger_and_wait(timeout=60):
        print("\n✓ SUCCESS! Full microscope capture cycle completed.")
    else:
        print("\n✗ FAILED! Microscope did not respond.")
    
    print("\n" + "=" * 60)
    print("Sender test complete!")
    print("=" * 60)


def run_receiver() -> None:
    """Simulate microscope PC receiving commands"""
    print("=" * 60)
    print("RECEIVER MODE (Simulating Microscope PC)")
    print("=" * 60)
    print("\nThis terminal will listen for audio commands.")
    print("Start the SENDER terminal to begin testing.\n")
    
    # Test audio hardware first
    success, input_device, output_device = test_audio_hardware()
    if not success:
        print("\n✗ Audio hardware test failed!")
        print("  Cannot proceed without working audio devices.")
        return
    
    print("\n" + "=" * 60)
    print("✓ Audio hardware test passed!")
    print(f"  Using input device: {input_device}")
    print(f"  Using output device: {output_device}")
    print("=" * 60)
    
    controller = MicroscopeAudioController(input_device=input_device, output_device=output_device)
    
    if not controller.is_initialized:
        print(f"✗ Error: {controller.last_error}")
        return
    
    print("🎧 Listening for commands...")
    print("   (Waiting up to 60 seconds)\n")
    
    # Test 1: Wait for PING, respond with PONG
    print("Waiting for PING...")
    print("(Make sure sender PC audio is playing through speakers)")
    print("(and this PC's microphone can hear it)\n")
    
    cmd = controller.wait_for_command(timeout=60, expected=Command.PING)
    
    if cmd == Command.PING:
        print("✓ PING received!")
        print("\nSending PONG response...")
        time.sleep(1)  # Brief delay
        controller.send_command(Command.PONG)
        print("✓ PONG sent!")
    else:
        print("✗ No PING received")
        return
    
    # Test 2: Wait for CAPTURE, respond with DONE
    print("\n" + "=" * 60)
    print("Waiting for CAPTURE command...")
    cmd = controller.wait_for_command(timeout=60, expected=Command.CAPTURE)
    
    if cmd == Command.CAPTURE:
        print("✓ CAPTURE received!")
        print("\n🔬 Simulating microscope image capture...")
        print("   (In production, this would trigger actual microscope)")
        time.sleep(3)  # Simulate capture time
        print("   Image saved!")
        
        print("\nSending DONE response...")
        time.sleep(1)
        controller.send_command(Command.DONE)
        print("✓ DONE sent!")
    else:
        print("✗ No CAPTURE received")
    
    print("\n" + "=" * 60)
    print("Receiver test complete!")
    print("=" * 60)


def main() -> None:
    """Main entry point"""
    if len(sys.argv) != 2 or sys.argv[1] not in ['sender', 'receiver']:
        print("Usage:")
        print("  Terminal 1: python two_pc_test.py receiver")
        print("  Terminal 2: python two_pc_test.py sender")
        print()
        print("Run receiver first, then sender.")
        sys.exit(1)
    
    mode = sys.argv[1]
    
    if mode == 'sender':
        run_sender()
    else:
        run_receiver()


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\n\nTest interrupted by user.")
        sys.exit(0)
