"""
Simple audio monitoring test without numpy dependency.
Tests pump audio using basic audio recording.
"""

import time
import sys
import os

# Add project root to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

try:
    import sounddevice as sd
    AUDIO_AVAILABLE = True
except ImportError:
    AUDIO_AVAILABLE = False
    print("❌ sounddevice not available")

try:
    from src.pump_libusb import PumpController
    PUMP_AVAILABLE = True
except ImportError:
    PUMP_AVAILABLE = False
    print("❌ LibUSB pump controller not available")

def record_audio_level(duration=2.0, sample_rate=22050):
    """Record audio and calculate simple volume level."""
    if not AUDIO_AVAILABLE:
        print("❌ Audio recording not available")
        return 0.0
    
    try:
        print(f"   🎧 Recording for {duration} seconds...")
        recording = sd.rec(int(duration * sample_rate), samplerate=sample_rate, channels=1, dtype='float64')
        sd.wait()
        
        # Simple volume calculation without numpy
        total = 0.0
        max_val = 0.0
        samples = len(recording)
        
        for sample in recording:
            val = abs(float(sample[0]))
            total += val
            if val > max_val:
                max_val = val
        
        avg_level = total / samples if samples > 0 else 0.0
        print(f"   📊 Average level: {avg_level:.6f}, Peak: {max_val:.6f}")
        
        return avg_level
        
    except Exception as e:
        print(f"   ❌ Recording failed: {e}")
        return 0.0

def test_pump_with_audio():
    """Test pump operation with audio monitoring."""
    print("🚀 PUMP AUDIO MONITORING TEST")
    print("=" * 50)
    
    if not AUDIO_AVAILABLE:
        print("❌ Audio monitoring not available")
        return False
    
    if not PUMP_AVAILABLE:
        print("❌ Pump control not available")
        return False
    
    try:
        # Show available audio devices
        print("\n📱 Available audio devices:")
        devices = sd.query_devices()
        for i, device in enumerate(devices):
            if device['max_input_channels'] > 0:  # Input devices only
                marker = " ← DEFAULT" if i == sd.default.device[0] else ""
                print(f"   {i}: {device['name']}{marker}")
        
        # Baseline measurement
        print("\n📍 STEP 1: Baseline (pump OFF)")
        baseline = record_audio_level(3.0)
        
        # Initialize pump
        print("\n📍 STEP 2: Connecting to pump...")
        pump = PumpController()
        
        if pump.device is None:
            print("❌ Failed to connect to pump")
            return False
        
        print("✅ Pump connected successfully")
        
        # Configure pump
        print("\n📍 STEP 3: Configuring pump...")
        pump.set_frequency(100)
        pump.set_voltage(80)
        print("   Frequency: 100 Hz, Voltage: 80V")
        
        # Start pump and monitor
        print("\n📍 STEP 4: Starting pump and monitoring audio...")
        pump.start()
        
        pump_level = record_audio_level(5.0)
        
        # Stop pump
        print("\n📍 STEP 5: Stopping pump...")
        pump.stop()
        pump.close()
        
        # Final check
        print("\n📍 STEP 6: Final silence check...")
        final_level = record_audio_level(2.0)
        
        # Analysis
        print("\n📊 AUDIO ANALYSIS:")
        print(f"   Baseline level:  {baseline:.6f}")
        print(f"   Pump ON level:   {pump_level:.6f}")
        print(f"   Final level:     {final_level:.6f}")
        
        # Determine if pump made sound
        threshold = baseline * 2.0  # Pump should be at least 2x louder than baseline
        if pump_level > threshold:
            print(f"\n🎉 SUCCESS! Pump sound detected!")
            print(f"   Pump level ({pump_level:.6f}) is {pump_level/baseline:.1f}x louder than baseline")
            print("   The pump is working correctly!")
            return True
        else:
            print(f"\n⚠️  No significant pump sound detected")
            print(f"   Pump level ({pump_level:.6f}) is similar to baseline ({baseline:.6f})")
            print("   Either the pump is very quiet or not working properly")
            return False
        
    except Exception as e:
        print(f"\n❌ Test failed: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    print("🔬 Simple Audio Monitoring - Bartels Micropump")
    print("===============================================")
    
    if not AUDIO_AVAILABLE:
        print("Install sounddevice: pip install sounddevice")
    elif not PUMP_AVAILABLE:
        print("Ensure libusb-win32 driver is installed via Zadig")
    else:
        test_pump_with_audio()
