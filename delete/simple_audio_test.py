"""
Simple audio-based pump detection test using basic Python libraries.
"""

import time
import logging
import sys
import os

# Add src directory to path for imports
sys.path.append(os.path.join(os.path.dirname(__file__), 'src'))

try:
    from pump import PumpController
    from resolve_ports import find_pump_port_by_vid_pid
except ImportError as e:
    print(f"Import error: {e}")
    print("Could not import pump modules. Exiting...")
    sys.exit(1)

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s [%(levelname)s] %(message)s')

def test_basic_audio():
    """Test basic audio functionality without external libraries."""
    print("🎤 BASIC AUDIO TEST")
    print("=" * 30)
    
    try:
        # Try to import audio libraries
        import sounddevice as sd
        import numpy as np
        print("✅ Audio libraries available!")
        
        # Test microphone access
        print("🎤 Testing microphone...")
        
        # Get available audio devices
        devices = sd.query_devices()
        print(f"📱 Found {len(devices)} audio devices:")
        
        input_devices = []
        for i, device in enumerate(devices):
            if device['max_input_channels'] > 0:
                input_devices.append((i, device))
                print(f"   [{i}] {device['name']} - {device['max_input_channels']} input channels")
        
        if not input_devices:
            print("❌ No input devices found!")
            return False
            
        # Test recording
        print(f"\n🎙️ Testing recording with default device...")
        duration = 2.0
        sample_rate = 44100
        
        print(f"Recording {duration} seconds...")
        audio_data = sd.rec(int(duration * sample_rate), 
                          samplerate=sample_rate, 
                          channels=1, 
                          dtype=np.float64)
        sd.wait()
        
        # Analyze the recorded audio
        rms = np.sqrt(np.mean(audio_data**2))
        peak = np.max(np.abs(audio_data))
        
        print(f"📊 Audio Analysis:")
        print(f"   RMS Level: {rms:.6f}")
        print(f"   Peak Level: {peak:.6f}")
        print(f"   Samples: {len(audio_data)}")
        
        if rms > 0.001:  # Some reasonable threshold
            print("✅ Audio detected - microphone is working!")
            return True
        else:
            print("⚠️ Very low audio levels - check microphone")
            return True  # Still working, just quiet
            
    except ImportError as e:
        print(f"❌ Audio libraries not available: {e}")
        print("💡 Need to install: pip install sounddevice numpy")
        return False
    except Exception as e:
        print(f"❌ Audio test failed: {e}")
        return False

def pump_audio_test():
    """Test pump with audio monitoring."""
    print("\n🔬 PUMP + AUDIO TEST")
    print("=" * 30)
    
    # Test audio first
    if not test_basic_audio():
        print("❌ Cannot proceed without working audio")
        return
    
    # Import audio libraries (we know they work now)
    import sounddevice as sd
    import numpy as np
    
    # Find pump
    print("\n🔍 Finding pump...")
    try:
        pump_port = find_pump_port_by_vid_pid(0x0403, 0xB4C0)  # Bartels pump VID/PID
    except Exception:
        pump_port = None
    if not pump_port:
        print("❌ No pump found!")
        return
    
    print(f"✅ Found pump on {pump_port}")
    pump = None
    
    try:
        pump = PumpController(pump_port)
        print("✅ Pump connected successfully")
        
        # Record baseline
        print("\n📴 Recording baseline (pump OFF)...")
        print("🤫 Please be quiet for 3 seconds...")
        time.sleep(1)
        
        baseline_audio = sd.rec(int(3 * 44100), samplerate=44100, channels=1, dtype=np.float64)
        sd.wait()
        baseline_rms = np.sqrt(np.mean(baseline_audio**2))
        print(f"📊 Baseline RMS: {baseline_rms:.6f}")
        
        # Configure pump
        print("\n⚙️ Configuring pump (100Hz, 50V)...")
        pump.set_frequency(100)
        pump.set_voltage(50)
        time.sleep(0.5)
        
        # Record with pump
        print("\n🔊 Recording with PUMP ON...")
        print("🚀 Starting pump and recording for 3 seconds...")
        
        pump.start()
        time.sleep(0.2)  # Let pump stabilize
        
        pump_audio = sd.rec(int(3 * 44100), samplerate=44100, channels=1, dtype=np.float64)
        sd.wait()
        
        pump.stop()
        print("⏹️ Pump stopped")
        
        # Analyze
        pump_rms = np.sqrt(np.mean(pump_audio**2))
        ratio = pump_rms / baseline_rms if baseline_rms > 0 else float('inf')
        
        print(f"\n🔍 AUDIO ANALYSIS:")
        print(f"   Baseline RMS: {baseline_rms:.6f}")
        print(f"   Pump RMS: {pump_rms:.6f}")
        print(f"   Increase: {ratio:.2f}x")
        
        # Detection logic
        if ratio > 1.3:  # 30% increase
            print("🎉 SUCCESS: Pump detected via audio!")
            print("   The pump makes audible sound that was detected!")
        elif ratio > 1.1:  # 10% increase
            print("✅ POSSIBLE: Small audio increase detected")
            print("   Pump might be audible but signal is weak")
        else:
            print("❓ INCONCLUSIVE: No significant audio change")
            print("   Pump might be too quiet or environment too noisy")
            
    except Exception as e:
        print(f"❌ Error during pump test: {e}")
        import traceback
        traceback.print_exc()
        
    finally:
        if pump:
            try:
                pump.close()
                print("🧹 Pump connection closed")
            except:
                pass

if __name__ == "__main__":
    print("🔬 MICROPUMP AUDIO DETECTION EXPERIMENT")
    print("=" * 50)
    print("This script will:")
    print("1. Test microphone access")
    print("2. Record baseline audio")
    print("3. Turn on the pump and record audio")
    print("4. Compare audio levels to detect pump operation")
    print("")
    
    input("Press Enter to start the audio experiment...")
    pump_audio_test()