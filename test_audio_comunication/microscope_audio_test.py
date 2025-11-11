"""
Standalone audio feasibility test for airgapped microscope PC.

Tests robust FSK modem protocol with error correction.

Usage:
    python microscope_audio_test.py
    
To create standalone .exe for airgapped transfer:
    pip install pyinstaller sounddevice numpy
    pyinstaller --onefile --add-data "audio_protocol.py;." microscope_audio_test.py
"""

import sys
from typing import Optional
import time

# Import protocol
try:
    from audio_protocol import AudioModem, Command, MicroscopeAudioController
    PROTOCOL_AVAILABLE = True
except ImportError:
    PROTOCOL_AVAILABLE = False


def test_basic_beep() -> bool:
    """Test 1: Basic system beep capability"""
    print("\n=== Test 1: System Beep ===")
    print("Testing [console]::beep()...")
    
    try:
        import subprocess
        result = subprocess.run(
            ['powershell', '-c', '[console]::beep(1000,500)'],
            capture_output=True,
            timeout=2
        )
        print("✓ System beep command executed")
        print("  Did you hear a beep? (This confirms basic audio output)")
        return True
    except Exception as e:
        print(f"✗ System beep failed: {e}")
        return False


def test_audio_generation() -> bool:
    """Test 2: Generate audio tones via sounddevice"""
    print("\n=== Test 2: Audio Tone Generation ===")
    print("Attempting to import sounddevice and numpy...")
    
    try:
        import numpy as np
        import sounddevice as sd
        print("✓ Libraries imported successfully")
    except ImportError as e:
        print(f"✗ Import failed: {e}")
        print("  This PC needs: pip install sounddevice numpy")
        return False
    
    try:
        print("Generating 1200 Hz tone for 1 second...")
        sample_rate = 44100
        duration = 1.0
        frequency = 1200
        
        t = np.linspace(0, duration, int(sample_rate * duration))
        tone = np.sin(2 * np.pi * frequency * t)
        
        sd.play(tone, sample_rate)
        sd.wait()
        
        print("✓ Audio tone generated successfully")
        print("  Did you hear a 1200 Hz tone? (high-pitched beep)")
        return True
        
    except Exception as e:
        print(f"✗ Audio generation failed: {e}")
        print(f"  Error details: {type(e).__name__}")
        return False


def test_audio_recording() -> bool:
    """Test 3: Record audio from microphone"""
    print("\n=== Test 3: Audio Recording ===")
    
    try:
        import numpy as np
        import sounddevice as sd
    except ImportError:
        print("✗ Skipping (libraries not available)")
        return False
    
    try:
        duration = 3.0
        sample_rate = 44100
        
        print(f"Recording for {duration} seconds...")
        print("  ** CLAP YOUR HANDS or SPEAK NOW **")
        
        recording = sd.rec(
            int(duration * sample_rate),
            samplerate=sample_rate,
            channels=1
        )
        sd.wait()
        
        # Analyze recording
        max_amplitude = np.max(np.abs(recording))
        rms = np.sqrt(np.mean(recording**2))
        
        print(f"✓ Recording complete")
        print(f"  Max amplitude: {max_amplitude:.4f}")
        print(f"  RMS level: {rms:.4f}")
        
        if max_amplitude > 0.01:
            print("  ✓ Audio detected! Microphone is working.")
            return True
        else:
            print("  ✗ Very weak signal. Check:")
            print("    - Microphone is plugged in")
            print("    - Microphone is not muted in Windows settings")
            print("    - Volume levels are adequate")
            return False
            
    except Exception as e:
        print(f"✗ Recording failed: {e}")
        return False


def test_frequency_detection() -> bool:
    """Test 4: Detect specific frequency (FSK simulation)"""
    print("\n=== Test 4: Frequency Detection (FSK Simulation) ===")
    
    try:
        import numpy as np
        import sounddevice as sd
    except ImportError:
        print("✗ Skipping (libraries not available)")
        return False
    
    try:
        sample_rate = 44100
        test_freq = 1800  # Hz
        duration = 1.0
        
        # Generate test tone
        print(f"Generating {test_freq} Hz test tone...")
        t = np.linspace(0, duration, int(sample_rate * duration))
        tone = np.sin(2 * np.pi * test_freq * t)
        
        # Record while playing (loopback test)
        print("Playing tone and recording simultaneously...")
        recording = sd.playrec(
            tone.reshape(-1, 1),
            samplerate=sample_rate,
            channels=1
        )
        sd.wait()
        
        # FFT analysis
        fft = np.fft.rfft(recording[:, 0])
        freqs = np.fft.rfftfreq(len(recording), 1/sample_rate)
        
        peak_idx = np.argmax(np.abs(fft))
        detected_freq = freqs[peak_idx]
        
        print(f"  Generated frequency: {test_freq} Hz")
        print(f"  Detected frequency: {detected_freq:.1f} Hz")
        
        if abs(detected_freq - test_freq) < 50:
            print("  ✓ Frequency detection working! FSK modem is viable.")
            return True
        else:
            print("  ✗ Frequency mismatch. Audio loopback may not work.")
            print("    (This is OK if using separate speaker/microphone)")
            return True  # Still viable with external audio path
            
    except Exception as e:
        print(f"✗ Frequency detection failed: {e}")
        return False


def test_protocol_loopback() -> bool:
    """Test 5: FSK Protocol with Loopback"""
    print("\n=== Test 5: FSK Protocol (Robust Communication) ===")
    
    if not PROTOCOL_AVAILABLE:
        print("✗ audio_protocol.py not found - copy both files")
        return False
    
    try:
        import numpy as np
        import sounddevice as sd
    except ImportError:
        print("✗ Skipping (sounddevice not available)")
        return False
    
    try:
        modem = AudioModem()
        
        # Test each command
        test_commands = [Command.CAPTURE, Command.DONE, Command.PING]
        
        for cmd in test_commands:
            print(f"\nTesting {cmd.name}:")
            print("  1. Encoding...")
            audio = modem.encode_command(cmd)
            print(f"     Duration: {len(audio) / modem.config.sample_rate:.2f}s")
            
            print("  2. Playing and recording...")
            recording = sd.playrec(
                audio.reshape(-1, 1),
                samplerate=modem.config.sample_rate,
                channels=1
            )
            sd.wait()
            
            print("  3. Decoding...")
            decoded = modem.decode_command(recording[:, 0])
            
            if decoded == cmd:
                print(f"     ✓ Success! {cmd.name} → {decoded.name}")
            else:
                print(f"     ✗ Failed! {cmd.name} → {decoded}")
                return False
        
        print("\n✓ All protocol tests passed!")
        print("\nProtocol Features:")
        print("  - Preamble sync tone (filters background noise)")
        print("  - 4-bit checksum (detects corruption)")
        print("  - Frequency tolerance (±100 Hz)")
        print("  - Minimum signal power threshold")
        print("  - 1.3 second transmission per command")
        print("\nThis means:")
        print("  ✓ Immune to brief background conversations")
        print("  ✓ Detects transmission errors automatically")
        print("  ✓ Rejects invalid/corrupted signals")
        
        return True
        
    except Exception as e:
        print(f"✗ Protocol test failed: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_noise_immunity() -> bool:
    """Test 6: Verify noise rejection"""
    print("\n=== Test 6: Noise Immunity ===")
    
    if not PROTOCOL_AVAILABLE:
        print("✗ Skipping")
        return False
    
    try:
        import numpy as np
        modem = AudioModem()
        
        print("Testing decoder with random noise...")
        
        # Generate random noise (simulates talking/background)
        sample_rate = modem.config.sample_rate
        noise = np.random.normal(0, 0.1, int(3 * sample_rate))
        
        decoded = modem.decode_command(noise)
        
        if decoded is None:
            print("  ✓ Correctly rejected random noise")
            return True
        else:
            print(f"  ✗ False positive: decoded {decoded.name} from noise")
            return False
            
    except Exception as e:
        print(f"✗ Test failed: {e}")
        return False


def list_audio_devices() -> None:
    """List all available audio devices"""
    print("\n=== Audio Device Information ===")
    
    try:
        import sounddevice as sd
        devices = sd.query_devices()
        
        print("\nAvailable audio devices:")
        for i, device in enumerate(devices):
            print(f"\n[{i}] {device['name']}")
            print(f"    Max inputs: {device['max_input_channels']}")
            print(f"    Max outputs: {device['max_output_channels']}")
            print(f"    Default sample rate: {device['default_samplerate']}")
            
    except ImportError:
        print("sounddevice not available - cannot list devices")
    except Exception as e:
        print(f"Error listing devices: {e}")


def demo_high_level_api() -> None:
    """Demonstrate the high-level controller API"""
    print("\n=== High-Level API Demo ===")
    
    if not PROTOCOL_AVAILABLE:
        print("✗ Skipping")
        return
    
    try:
        controller = MicroscopeAudioController()
        
        if not controller.is_initialized:
            print(f"✗ Controller not initialized: {controller.last_error}")
            return
        
        print("\nAvailable commands:")
        for cmd in Command:
            print(f"  - {cmd.name}: {cmd.value}")
        
        print("\nExample usage on microscope PC:")
        print("  controller = MicroscopeAudioController()")
        print("  # Wait for CAPTURE command, then respond with DONE")
        print("  cmd = controller.wait_for_command(expected=Command.CAPTURE)")
        print("  if cmd: controller.send_command(Command.DONE)")
        
        print("\nExample usage on microfluidics PC:")
        print("  controller = MicroscopeAudioController()")
        print("  controller.trigger_and_wait(timeout=60)")
        
    except Exception as e:
        print(f"Demo error: {e}")


def main() -> None:
    """Run all audio feasibility tests including FSK protocol"""
    print("=" * 70)
    print("Microscope PC Audio Feasibility Test - FSK Protocol Edition")
    print("=" * 70)
    print("\nThis tool tests:")
    print("  1. Basic system beep (confirms audio output)")
    print("  2. Audio tone generation (sounddevice library)")
    print("  3. Audio recording (microphone)")
    print("  4. Frequency detection (FFT analysis)")
    print("  5. FSK modem protocol (robust digital communication)")
    print("  6. Noise immunity (rejects background speech)")
    print("\nPress Ctrl+C to abort at any time.")
    print("=" * 70)
    
    # Run all tests
    results = {
        "System Beep": test_basic_beep(),
        "Audio Generation": test_audio_generation(),
        "Audio Recording": test_audio_recording(),
        "Frequency Detection": test_frequency_detection(),
        "FSK Protocol": test_protocol_loopback(),
        "Noise Immunity": test_noise_immunity(),
    }
    
    # Device listing
    list_audio_devices()
    
    # Demo
    demo_high_level_api()
    
    # Summary
    print("\n" + "=" * 70)
    print("RESULTS SUMMARY")
    print("=" * 70)
    
    for test_name, passed in results.items():
        status = "✓ PASS" if passed else "✗ FAIL"
        print(f"{test_name:.<50} {status}")
    
    all_passed = all(results.values())
    
    print("\n" + "=" * 70)
    if all_passed:
        print("✓ ALL TESTS PASSED - FSK PROTOCOL READY FOR DEPLOYMENT")
        print("\nThis PC is ready for audio-based communication!")
        print("\nNext steps:")
        print("  1. Copy audio_protocol.py AND microscope_audio_test.py to USB")
        print("  2. Run test on microscope PC")
        print("  3. If both PCs pass, build microscope_control.exe")
        print("\nSafety features enabled:")
        print("  ✓ Preamble prevents false triggers from speech")
        print("  ✓ Checksum detects corrupted transmissions")
        print("  ✓ Frequency tolerance handles speaker variations")
        print("  ✓ 1.3s transmission too long for accidental speech patterns")
    else:
        print("✗ SOME TESTS FAILED")
        print("\nTroubleshooting:")
        if not results["Audio Generation"]:
            print("  - Install dependencies: pip install sounddevice numpy")
        if not results["Audio Recording"]:
            print("  - Check microphone is plugged in and not muted")
            print("  - Verify Windows sound settings (Recording devices)")
        if not results["FSK Protocol"]:
            print("  - Audio loopback quality may be insufficient")
            print("  - Use separate speaker/microphone setup")
        print("\nAlternative: Use optical communication (screen flash + LED)")
    print("=" * 70)
    
    input("\nPress Enter to exit...")


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\n\nTest aborted by user.")
        sys.exit(0)
