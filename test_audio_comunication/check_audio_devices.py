"""
Check available audio devices and test microphone input.

This script helps diagnose audio setup issues.
"""

import sys
from typing import Optional


def check_sounddevice() -> bool:
    """Check if sounddevice is installed"""
    try:
        import sounddevice as sd
        import numpy as np
        print("✓ sounddevice library installed")
        print(f"  Version: {sd.__version__}")
        return True
    except ImportError as e:
        print("✗ sounddevice not installed")
        print("\nTo install:")
        print("  uv pip install sounddevice numpy")
        print("  OR: pip install sounddevice numpy")
        return False


def list_devices() -> None:
    """List all available audio devices"""
    try:
        import sounddevice as sd
        
        print("\n" + "=" * 60)
        print("AVAILABLE AUDIO DEVICES")
        print("=" * 60)
        
        devices = sd.query_devices()
        
        if isinstance(devices, list):
            for i, device in enumerate(devices):
                print(f"\n[{i}] {device['name']}")
                print(f"    Channels: {device['max_input_channels']} in, {device['max_output_channels']} out")
                print(f"    Sample Rate: {device['default_samplerate']} Hz")
                if device['max_input_channels'] > 0:
                    print("    ✓ Has microphone/input")
                if device['max_output_channels'] > 0:
                    print("    ✓ Has speaker/output")
        else:
            print(devices)
        
        # Show default devices
        print("\n" + "=" * 60)
        print("DEFAULT DEVICES")
        print("=" * 60)
        
        try:
            default_input = sd.query_devices(kind='input')
            print(f"\nDefault INPUT:  {default_input['name']}")
            print(f"  Channels: {default_input['max_input_channels']}")
        except Exception as e:
            print(f"\n✗ No default input device: {e}")
        
        try:
            default_output = sd.query_devices(kind='output')
            print(f"\nDefault OUTPUT: {default_output['name']}")
            print(f"  Channels: {default_output['max_output_channels']}")
        except Exception as e:
            print(f"\n✗ No default output device: {e}")
            
    except Exception as e:
        print(f"\n✗ Error listing devices: {e}")


def test_microphone(duration: float = 3.0) -> bool:
    """Test if microphone is receiving audio"""
    try:
        import sounddevice as sd
        import numpy as np
        
        print("\n" + "=" * 60)
        print("MICROPHONE TEST")
        print("=" * 60)
        
        sample_rate = 44100
        
        # Check if there's an input device
        try:
            input_device = sd.query_devices(kind='input')
            print(f"\nUsing input: {input_device['name']}")
        except Exception as e:
            print(f"\n✗ No input device available: {e}")
            print("\nThis computer may not have a microphone connected.")
            return False
        
        print(f"\n🎤 Recording for {duration} seconds...")
        print("   Please make some noise (clap, speak, tap keyboard)...")
        
        recording = sd.rec(
            int(duration * sample_rate),
            samplerate=sample_rate,
            channels=1,
            dtype='float32'
        )
        sd.wait()
        
        # Analyze recording
        audio_data = recording[:, 0]
        max_amplitude = np.max(np.abs(audio_data))
        rms = np.sqrt(np.mean(audio_data ** 2))
        
        print("\n" + "=" * 60)
        print("RESULTS")
        print("=" * 60)
        print(f"\nMax amplitude: {max_amplitude:.4f}")
        print(f"RMS level:     {rms:.4f}")
        
        if max_amplitude < 0.001:
            print("\n✗ NO AUDIO DETECTED")
            print("  Possible issues:")
            print("  - No microphone connected")
            print("  - Microphone muted in Windows settings")
            print("  - Wrong input device selected")
            print("  - Microphone permissions disabled")
            return False
        elif max_amplitude < 0.01:
            print("\n⚠ VERY WEAK SIGNAL")
            print("  Audio detected but very quiet")
            print("  Check microphone volume/gain settings")
            return False
        else:
            print("\n✓ MICROPHONE WORKING!")
            print("  Audio input is functional")
            return True
            
    except Exception as e:
        print(f"\n✗ Test failed: {e}")
        return False


def test_speaker(duration: float = 2.0) -> bool:
    """Test if speakers are working"""
    try:
        import sounddevice as sd
        import numpy as np
        
        print("\n" + "=" * 60)
        print("SPEAKER TEST")
        print("=" * 60)
        
        # Check if there's an output device
        try:
            output_device = sd.query_devices(kind='output')
            print(f"\nUsing output: {output_device['name']}")
        except Exception as e:
            print(f"\n✗ No output device available: {e}")
            return False
        
        print(f"\n🔊 Playing test tone ({duration} seconds)...")
        print("   Listen for a beep...")
        
        sample_rate = 44100
        frequency = 1000  # 1 kHz test tone
        
        t = np.linspace(0, duration, int(sample_rate * duration))
        tone = 0.3 * np.sin(2 * np.pi * frequency * t)
        
        sd.play(tone, sample_rate)
        sd.wait()
        
        print("\n✓ Test tone played")
        print("  Did you hear a beep? If not, check speaker volume.")
        return True
        
    except Exception as e:
        print(f"\n✗ Test failed: {e}")
        return False


def check_windows_permissions() -> None:
    """Show instructions for checking Windows microphone permissions"""
    print("\n" + "=" * 60)
    print("WINDOWS MICROPHONE PERMISSIONS")
    print("=" * 60)
    print("\nTo check if Python has microphone access:")
    print("\n1. Open Windows Settings")
    print("2. Go to Privacy & Security > Microphone")
    print("3. Ensure 'Microphone access' is ON")
    print("4. Ensure 'Let apps access your microphone' is ON")
    print("5. Check that Python/PowerShell is allowed")
    print("\nAlternatively, run this command in PowerShell:")
    print("  Start-Process ms-settings:privacy-microphone")


def main() -> None:
    """Main diagnostic routine"""
    print("=" * 60)
    print("AUDIO SYSTEM DIAGNOSTIC")
    print("=" * 60)
    
    # Step 1: Check library
    if not check_sounddevice():
        return
    
    # Step 2: List devices
    list_devices()
    
    # Step 3: Test speaker
    print("\n")
    input("Press Enter to test speakers...")
    test_speaker()
    
    # Step 4: Test microphone
    print("\n")
    input("Press Enter to test microphone...")
    has_mic = test_microphone()
    
    # Step 5: Show troubleshooting
    if not has_mic:
        check_windows_permissions()
    
    print("\n" + "=" * 60)
    print("DIAGNOSTIC COMPLETE")
    print("=" * 60)


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\n\nDiagnostic interrupted.")
        sys.exit(0)
