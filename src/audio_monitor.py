#!/usr/bin/env python3
"""Simple audio monitoring to verify pump sounds."""

import sounddevice as sd
import numpy as np
import time
import sys
import os

# Add the project root to the path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

try:
    from src.pump_libusb import PumpController as LibUSBPumpController
    LIBUSB_AVAILABLE = True
except ImportError:
    LIBUSB_AVAILABLE = False
    print("❌ LibUSB pump controller not available")

try:
    from src.pump import PumpController
    SERIAL_AVAILABLE = True
except ImportError:
    SERIAL_AVAILABLE = False
    print("❌ Serial pump controller not available")

def monitor_audio(duration=5.0, sample_rate=22050):
    """Monitor audio levels in real-time."""
    print(f"🎧 Monitoring audio for {duration} seconds...")
    print("   Watch the RMS values - they should increase when pump starts")
    
    # Record and analyze in chunks
    chunk_duration = 0.5
    chunk_samples = int(chunk_duration * sample_rate)
    
    for i in range(int(duration / chunk_duration)):
        recording = sd.rec(chunk_samples, samplerate=sample_rate, channels=1, dtype='float64')
        sd.wait()
        
        rms = np.sqrt(np.mean(recording**2))
        print(f"   Chunk {i+1:2d}: RMS = {rms:.6f}")
        
    print("✅ Audio monitoring complete")

def test_pump_audio():
    """Test pump audio detection using the working libusb controller."""
    print("🚀 PUMP AUDIO DETECTION TEST (LibUSB)")
    print("=" * 50)
    
    if not LIBUSB_AVAILABLE:
        print("❌ LibUSB pump controller not available")
        print("Make sure libusb-win32 driver is installed via Zadig")
        return
    
    # Baseline measurement
    print("\n📍 STEP 1: Baseline (pump OFF)")
    monitor_audio(3.0)
    
    # Start pump and measure
    print("\n📍 STEP 2: Starting pump...")
    try:
        # Use libusb controller (works with our current setup)
        pump = LibUSBPumpController()
        
        if pump.device is None:
            print("❌ Failed to initialize libusb pump")
            return
        
        print("✅ LibUSB pump connected")
        
        # Configure pump
        print("   Configuring pump (100Hz, 100V)...")
        pump.set_frequency(100)
        pump.set_voltage(100)
        
        print("   Starting pump...")
        pump.start()
        
        print("\n📍 STEP 3: Monitoring with pump ON")
        monitor_audio(5.0)
        
        print("\n📍 STEP 4: Stopping pump...")
        pump.stop()
        pump.close()
        
        print("\n📍 STEP 5: Final silence check")
        monitor_audio(2.0)
        
        print("\n🎉 Audio test completed!")
        
    except Exception as e:
        print(f"❌ Pump control error: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    test_pump_audio()