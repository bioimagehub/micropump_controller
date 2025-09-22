#!/usr/bin/env python3
"""
Pump test with audio monitoring - send USB commands and listen for any audio changes.
Even if we can't record properly, we can detect volume level changes.
"""

import time
import threading
from test_pump_windows_native import BartelsPumpController

def audio_monitor_simple():
    """Simple audio monitoring that doesn't require recording."""
    try:
        import pyaudio
        import numpy as np
        
        p = pyaudio.PyAudio()
        
        # Try to find any working input device
        for device_id in range(p.get_device_count()):
            try:
                info = p.get_device_info_by_index(device_id)
                if info.get('maxInputChannels', 0) > 0:
                    print(f"🎤 Trying to monitor: {info['name']}")
                    
                    # Try minimal settings
                    stream = p.open(
                        format=pyaudio.paInt16,
                        channels=1,
                        rate=8000,  # Very low sample rate
                        input=True,
                        input_device_index=device_id,
                        frames_per_buffer=512
                    )
                    
                    # Quick test
                    data = stream.read(512, exception_on_overflow=False)
                    stream.close()
                    
                    print(f"✅ Audio monitoring ready on: {info['name']}")
                    return device_id, info
                    
            except Exception as e:
                continue
        
        p.terminate()
        return None, None
        
    except Exception as e:
        print(f"Audio monitoring failed: {e}")
        return None, None

def monitor_audio_during_pump_test():
    """Monitor audio levels while testing pump commands."""
    print("🔊 Pump + Audio Test")
    print("=" * 40)
    
    # Set up pump
    pump = BartelsPumpController()
    if not pump.connect():
        print("❌ Could not connect to pump")
        return
    
    print("✅ Pump connected")
    
    # Check audio
    device_id, device_info = audio_monitor_simple()
    if device_id is None:
        print("⚠️ Audio monitoring not available, but continuing with pump test...")
        audio_available = False
    else:
        audio_available = True
    
    try:
        print("\n🧪 Testing pump with different frequencies...")
        print("Listen carefully for any sounds!\n")
        
        # Test different frequencies
        test_frequencies = [50, 100, 150, 200]
        
        for freq in test_frequencies:
            print(f"🔧 Setting frequency to {freq} Hz...")
            
            # Send pump commands
            pump.send_command(f"F{freq:03d}")
            time.sleep(0.2)
            pump.send_command("A150")  # Higher amplitude for more sound
            time.sleep(0.2)
            pump.send_command("MR")    # Rectangular waveform
            time.sleep(0.2)
            
            print(f"🔛 Turning pump ON at {freq} Hz...")
            pump.send_command("bon")
            
            # Monitor for 3 seconds
            if audio_available:
                try:
                    import pyaudio
                    import numpy as np
                    
                    p = pyaudio.PyAudio()
                    stream = p.open(
                        format=pyaudio.paInt16,
                        channels=1,
                        rate=8000,
                        input=True,
                        input_device_index=device_id,
                        frames_per_buffer=512
                    )
                    
                    print("🎧 Monitoring audio: ", end="", flush=True)
                    volumes = []
                    
                    for i in range(24):  # 3 seconds at 8 readings per second
                        try:
                            data = stream.read(512, exception_on_overflow=False)
                            audio_data = np.frombuffer(data, dtype=np.int16)
                            volume = np.abs(audio_data).mean()
                            volumes.append(volume)
                            
                            if volume > 200:
                                print("🔊", end="", flush=True)
                            elif volume > 100:
                                print("▌", end="", flush=True)
                            elif volume > 50:
                                print(".", end="", flush=True)
                            else:
                                print("_", end="", flush=True)
                            
                            time.sleep(0.125)  # 8 times per second
                        except:
                            print("x", end="", flush=True)
                            time.sleep(0.125)
                    
                    stream.close()
                    p.terminate()
                    
                    max_vol = max(volumes) if volumes else 0
                    avg_vol = sum(volumes) / len(volumes) if volumes else 0
                    print(f" [Max: {max_vol:.0f}, Avg: {avg_vol:.0f}]")
                    
                except Exception as e:
                    print(f"Audio error: {e}")
                    time.sleep(3)
            else:
                print("⏱️ Waiting 3 seconds (listen for pump sounds)...")
                time.sleep(3)
            
            print("🔴 Turning pump OFF...")
            pump.send_command("boff")
            time.sleep(1)
            print()
        
        print("✅ Test complete!")
        print("\n📊 Results:")
        print("If the pump is working, you should have heard:")
        print("  • Lower frequency buzz at 50 Hz")
        print("  • Higher pitch whine at 200 Hz") 
        print("  • Volume changes with amplitude")
        
    except KeyboardInterrupt:
        print("\n⏹️ Test interrupted")
    except Exception as e:
        print(f"❌ Test error: {e}")
    finally:
        pump.send_command("boff")  # Ensure pump is off
        pump.disconnect()

if __name__ == "__main__":
    monitor_audio_during_pump_test()
