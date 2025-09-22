#!/usr/bin/env python3
"""
Audio device detection and pump sound monitoring.
Check if microphone is available and optionally record pump sounds.
"""

import subprocess
import time

def check_windows_audio():
    """Check Windows audio devices."""
    print("🔍 Checking Windows audio devices...")
    
    try:
        # Simple PowerShell command to list audio devices
        result = subprocess.run([
            'powershell', '-Command', 
            'Get-CimInstance Win32_SoundDevice | Select-Object Name'
        ], capture_output=True, text=True, timeout=10)
        
        print("Audio devices found:")
        print(result.stdout)
        
    except Exception as e:
        print(f"Error checking Windows audio: {e}")

def check_pyaudio():
    """Check audio devices using PyAudio."""
    try:
        import pyaudio
        
        p = pyaudio.PyAudio()
        print(f"\n🎤 PyAudio found {p.get_device_count()} audio devices:")
        
        input_devices = []
        output_devices = []
        
        for i in range(p.get_device_count()):
            try:
                info = p.get_device_info_by_index(i)
                name = info.get('name', 'Unknown')
                max_in = info.get('maxInputChannels', 0)
                max_out = info.get('maxOutputChannels', 0)
                
                if max_in > 0:
                    input_devices.append(f"  📥 Input {i}: {name} ({max_in} channels)")
                if max_out > 0:
                    output_devices.append(f"  📤 Output {i}: {name} ({max_out} channels)")
                    
            except Exception as e:
                continue
        
        print("\nInput devices (microphones):")
        if input_devices:
            for device in input_devices:
                print(device)
        else:
            print("  ❌ No input devices found")
            
        print("\nOutput devices (speakers):")
        if output_devices:
            for device in output_devices:
                print(device)
        else:
            print("  ❌ No output devices found")
        
        p.terminate()
        return len(input_devices) > 0
        
    except ImportError:
        print("❌ PyAudio not available")
        return False
    except Exception as e:
        print(f"❌ PyAudio error: {e}")
        return False

def test_microphone_basic():
    """Basic microphone test."""
    try:
        import pyaudio
        import numpy as np
        
        print("\n🎤 Testing microphone (5 seconds)...")
        print("Make some noise to test microphone...")
        
        p = pyaudio.PyAudio()
        
        # Find default input device
        default_input = p.get_default_input_device_info()
        print(f"Using: {default_input['name']}")
        
        stream = p.open(
            format=pyaudio.paInt16,
            channels=1,
            rate=44100,
            input=True,
            frames_per_buffer=1024
        )
        
        print("Recording...")
        max_volume = 0
        
        for i in range(int(44100 / 1024 * 5)):  # 5 seconds
            data = stream.read(1024)
            audio_data = np.frombuffer(data, dtype=np.int16)
            volume = np.abs(audio_data).mean()
            max_volume = max(max_volume, volume)
            
            # Simple volume indicator
            if volume > 100:
                print("📊", end="", flush=True)
            else:
                print(".", end="", flush=True)
                
        stream.stop_stream()
        stream.close()
        p.terminate()
        
        print(f"\n✅ Microphone test complete! Max volume: {max_volume}")
        return max_volume > 50
        
    except Exception as e:
        print(f"❌ Microphone test failed: {e}")
        return False

def main():
    """Main audio detection function."""
    print("🔊 Audio System Detection")
    print("=" * 40)
    
    # Check Windows audio
    check_windows_audio()
    
    # Check with PyAudio
    has_microphone = check_pyaudio()
    
    if has_microphone:
        print("\n✅ Microphone detected!")
        
        # Ask if user wants to test
        try:
            test = input("\nTest microphone? (y/n): ").lower().strip()
            if test == 'y':
                try:
                    import numpy
                    test_microphone_basic()
                except ImportError:
                    print("❌ NumPy not available for microphone test")
        except KeyboardInterrupt:
            print("\nSkipped microphone test")
    else:
        print("\n❌ No microphone detected")
    
    print("\n💡 If pump is working, you should hear:")
    print("  - Clicking/buzzing at low frequencies (50-100 Hz)")
    print("  - Higher pitched whining at higher frequencies (200+ Hz)")
    print("  - Volume proportional to amplitude setting")

if __name__ == "__main__":
    main()
