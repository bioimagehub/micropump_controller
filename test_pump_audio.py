#!/usr/bin/env python3
"""
Quick pump audibility test - try different frequencies to hear if pump is working.
Some frequencies are more audible than others.
"""

import time
from test_pump_windows_native import BartelsPumpController

def test_frequencies():
    """Test different frequencies to find audible ones."""
    pump = BartelsPumpController()
    
    try:
        if not pump.connect():
            print("❌ Failed to connect to pump")
            return
        
        print("✅ Connected! Testing different frequencies...")
        
        # Test frequencies that should be more audible
        test_freqs = [50, 100, 150, 200, 250]  # Hz
        
        for freq in test_freqs:
            print(f"\n🔊 Testing {freq} Hz (listen for sound)...")
            
            # Set parameters
            pump.send_command(f"F{freq:03d}")
            time.sleep(0.2)
            pump.send_command("A200")  # Higher amplitude for more noise
            time.sleep(0.2)
            pump.send_command("MR")  # Rectangular (more audible than sine)
            time.sleep(0.2)
            
            # Short pulse
            pump.send_command("bon")
            print(f"🔛 ON at {freq} Hz...")
            time.sleep(3)  # 3 seconds per test
            
            pump.send_command("boff")
            print("🔴 OFF")
            time.sleep(1)  # Pause between tests
        
        print("\n✅ Frequency test complete!")
        print("If you heard clicking/buzzing sounds, the pump is working!")
        
    except Exception as e:
        print(f"❌ Error: {e}")
    finally:
        pump.disconnect()

if __name__ == "__main__":
    test_frequencies()
