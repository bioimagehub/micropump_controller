"""
Helper script to select and test specific audio devices.
Useful when Windows doesn't have a default input device set.
"""

import sounddevice as sd
import numpy as np
from typing import Optional


def list_input_devices() -> list:
    """List all available input devices"""
    devices = sd.query_devices()
    input_devices = []
    
    print("\n" + "=" * 60)
    print("AVAILABLE INPUT DEVICES")
    print("=" * 60)
    
    for i, device in enumerate(devices):
        if device['max_input_channels'] > 0:
            input_devices.append((i, device))
            print(f"\n[{len(input_devices)-1}] Device ID: {i}")
            print(f"    Name: {device['name']}")
            print(f"    Channels: {device['max_input_channels']}")
            print(f"    Sample Rate: {device['default_samplerate']} Hz")
    
    return input_devices


def test_device(device_id: int) -> bool:
    """Test if a specific device can record audio"""
    print(f"\n🎤 Testing device {device_id}...")
    print("   Recording 3 seconds - please make some noise!")
    
    try:
        sample_rate = 44100
        duration = 3.0
        
        recording = sd.rec(
            int(duration * sample_rate),
            samplerate=sample_rate,
            channels=1,
            device=device_id,
            dtype='float32'
        )
        sd.wait()
        
        # Analyze
        audio_data = recording[:, 0]
        max_amplitude = np.max(np.abs(audio_data))
        rms = np.sqrt(np.mean(audio_data ** 2))
        
        print(f"\n   Max amplitude: {max_amplitude:.4f}")
        print(f"   RMS level:     {rms:.4f}")
        
        if max_amplitude < 0.001:
            print("   ✗ No audio detected")
            return False
        else:
            print("   ✓ Audio detected!")
            return True
            
    except Exception as e:
        print(f"   ✗ Error: {e}")
        return False


def main() -> None:
    """Main entry point"""
    print("=" * 60)
    print("AUDIO DEVICE SELECTOR")
    print("=" * 60)
    
    input_devices = list_input_devices()
    
    if not input_devices:
        print("\n✗ No input devices found!")
        print("  Make sure your headphones/microphone are connected.")
        return
    
    print("\n" + "=" * 60)
    
    # Let user select device
    while True:
        try:
            choice = input(f"\nSelect device [0-{len(input_devices)-1}] or 'q' to quit: ").strip()
            
            if choice.lower() == 'q':
                return
            
            idx = int(choice)
            if 0 <= idx < len(input_devices):
                device_id, device = input_devices[idx]
                print(f"\nSelected: {device['name']}")
                
                if test_device(device_id):
                    print(f"\n✓ Device {device_id} is working!")
                    print(f"\nTo use this device in audio_protocol.py:")
                    print(f"  Set device={device_id} in sd.rec() and sd.play() calls")
                    
                    # Save to config file
                    with open('audio_device_config.txt', 'w') as f:
                        f.write(f"input_device={device_id}\n")
                        f.write(f"device_name={device['name']}\n")
                    
                    print(f"\n✓ Configuration saved to audio_device_config.txt")
                else:
                    print(f"\n✗ Device {device_id} is not working properly")
                
                break
            else:
                print(f"Invalid choice. Please enter 0-{len(input_devices)-1}")
                
        except ValueError:
            print("Invalid input. Please enter a number.")
        except KeyboardInterrupt:
            print("\n\nCancelled.")
            return


if __name__ == "__main__":
    main()
