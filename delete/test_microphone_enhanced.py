#!/usr/bin/env python3
"""
Enhanced microphone test that can select specific audio devices.
"""

import time
import numpy as np

def test_specific_microphone():
    """Test a specific microphone device."""
    try:
        import pyaudio
        
        p = pyaudio.PyAudio()
        
        # List input devices again
        print("Available input devices:")
        input_devices = []
        for i in range(p.get_device_count()):
            try:
                info = p.get_device_info_by_index(i)
                if info.get('maxInputChannels', 0) > 0:
                    input_devices.append((i, info))
                    print(f"  {len(input_devices)-1}: {info['name']}")
            except:
                continue
        
        if not input_devices:
            print("❌ No input devices found")
            return False
        
        # Use the built-in microphone (usually index 1 in the list)
        device_idx = 1 if len(input_devices) > 1 else 0
        device_id, device_info = input_devices[device_idx]
        
        print(f"\n🎤 Testing: {device_info['name']}")
        print("Make some noise (speak, tap, etc.) for 5 seconds...")
        
        # Test recording
        try:
            stream = p.open(
                format=pyaudio.paInt16,
                channels=1,
                rate=int(device_info['defaultSampleRate']),
                input=True,
                input_device_index=device_id,
                frames_per_buffer=1024
            )
            
            print("Recording... ", end="", flush=True)
            max_volume = 0
            samples = []
            
            # Record for 5 seconds
            for i in range(int(device_info['defaultSampleRate'] / 1024 * 5)):
                try:
                    data = stream.read(1024, exception_on_overflow=False)
                    audio_data = np.frombuffer(data, dtype=np.int16)
                    volume = np.abs(audio_data).mean()
                    max_volume = max(max_volume, volume)
                    samples.extend(audio_data)
                    
                    # Volume indicator
                    if volume > 100:
                        print("📊", end="", flush=True)
                    elif volume > 50:
                        print("▌", end="", flush=True)
                    else:
                        print(".", end="", flush=True)
                        
                except Exception as e:
                    print(f"x", end="", flush=True)
                    continue
            
            stream.stop_stream()
            stream.close()
            
            print(f"\n✅ Test complete!")
            print(f"Max volume detected: {max_volume}")
            print(f"Total samples: {len(samples)}")
            
            if max_volume > 50:
                print("✅ Microphone is working! Good volume detected.")
                return True
            else:
                print("⚠️ Low volume detected. Check microphone settings.")
                return False
                
        except Exception as e:
            print(f"\n❌ Recording failed: {e}")
            return False
        finally:
            p.terminate()
            
    except ImportError:
        print("❌ PyAudio not available")
        return False
    except Exception as e:
        print(f"❌ Error: {e}")
        return False

def quick_volume_test():
    """Quick volume level test."""
    try:
        import pyaudio
        
        p = pyaudio.PyAudio()
        
        # Find any working input device
        for i in range(p.get_device_count()):
            try:
                info = p.get_device_info_by_index(i)
                if info.get('maxInputChannels', 0) > 0:
                    print(f"Testing device: {info['name']}")
                    
                    stream = p.open(
                        format=pyaudio.paInt16,
                        channels=1,
                        rate=22050,  # Lower sample rate
                        input=True,
                        input_device_index=i,
                        frames_per_buffer=1024
                    )
                    
                    # Quick 2-second test
                    print("Quick test (2s): ", end="", flush=True)
                    volumes = []
                    
                    for _ in range(int(22050 / 1024 * 2)):
                        try:
                            data = stream.read(1024, exception_on_overflow=False)
                            audio_data = np.frombuffer(data, dtype=np.int16)
                            volume = np.abs(audio_data).mean()
                            volumes.append(volume)
                            
                            if volume > 100:
                                print("🔊", end="", flush=True)
                            elif volume > 10:
                                print("▌", end="", flush=True)
                            else:
                                print(".", end="", flush=True)
                        except:
                            print("x", end="", flush=True)
                    
                    stream.stop_stream()
                    stream.close()
                    
                    max_vol = max(volumes) if volumes else 0
                    avg_vol = sum(volumes) / len(volumes) if volumes else 0
                    
                    print(f" Max: {max_vol:.0f}, Avg: {avg_vol:.0f}")
                    
                    if max_vol > 50:
                        print(f"✅ Working microphone found: {info['name']}")
                        p.terminate()
                        return True
                        
            except Exception as e:
                print(f"  Failed: {e}")
                continue
        
        p.terminate()
        print("❌ No working microphones found")
        return False
        
    except Exception as e:
        print(f"❌ Quick test failed: {e}")
        return False

if __name__ == "__main__":
    print("🎤 Enhanced Microphone Test")
    print("=" * 30)
    
    # Try numpy import
    try:
        import numpy as np
        print("✅ NumPy available")
        
        # Try specific microphone test
        if test_specific_microphone():
            print("\n🎉 Microphone working perfectly!")
        else:
            print("\n⚠️ Trying alternative test...")
            quick_volume_test()
            
    except ImportError:
        print("❌ NumPy not available, trying basic test...")
        quick_volume_test()
