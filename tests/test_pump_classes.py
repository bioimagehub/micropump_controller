#!/usr/bin/env python3
"""Quick test of pump classes."""

import sys
from pathlib import Path

# Add src directory to path
src_path = Path(__file__).parent.parent / "src"
sys.path.insert(0, str(src_path))

def test_pump_win(freq=100, amplitude=100, waveform="RECT", duration=2.0):
    """Test Windows pump class with actual pump commands."""
    print("=== Testing Pump_win ===")
    try:
        import pump_win
        pump = pump_win.Pump_win()
        
        result = pump.initialize()
        print(f"Initialize result: {result}")
        
        if not result:
            print(f"Error: {pump.get_error_details()}")
            print(f"Suggested fix: {pump.get_suggested_fix()}")
            return False
        
        print("✅ Pump initialized!")
        
        # Send test commands
        print(f"🔧 Configuring pump: {freq}Hz, {amplitude}Vpp, {waveform}")
        if not pump.set_frequency(freq):
            print(f"❌ Failed to set frequency: {pump.get_error_details()}")
            return False
        
        if not pump.set_voltage(amplitude):
            print(f"❌ Failed to set voltage: {pump.get_error_details()}")
            return False
            
        if not pump.set_waveform(waveform):
            print(f"❌ Failed to set waveform: {pump.get_error_details()}")
            return False
        
        # Run test pulse
        print(f"🚀 Running test pulse for {duration} seconds...")
        if pump.pulse(duration):
            print("✅ Test pulse completed successfully!")
        else:
            print(f"❌ Test pulse failed: {pump.get_error_details()}")
            return False
            
        pump.close()
        return True
        
    except Exception as e:
        print(f"❌ Pump_win error: {e}")
        return False

def test_pump_wsl(freq=100, amplitude=100, waveform="RECT", duration=2.0):
    """Test WSL pump class with actual pump commands."""
    print("\n=== Testing Pump_wsl ===")
    try:
        import pump_wsl
        pump = pump_wsl.Pump_wsl()
        
        result = pump.initialize()
        print(f"Initialize result: {result}")
        
        if not result:
            print(f"Error: {pump.get_error_details()}")
            print(f"Suggested fix: {pump.get_suggested_fix()}")
            return False
        
        print("✅ WSL pump initialized!")
        
        # Send test commands
        print(f"🔧 Configuring pump via WSL: {freq}Hz, {amplitude}Vpp, {waveform}")
        if not pump.set_frequency(freq):
            print(f"❌ Failed to set frequency: {pump.get_error_details()}")
            return False
        
        if not pump.set_voltage(amplitude):
            print(f"❌ Failed to set voltage: {pump.get_error_details()}")
            return False
            
        if not pump.set_waveform(waveform):
            print(f"❌ Failed to set waveform: {pump.get_error_details()}")
            return False
        
        # Run test pulse
        print(f"🚀 Running WSL test pulse for {duration} seconds...")
        if pump.pulse(duration):
            print("✅ WSL test pulse completed successfully!")
        else:
            print(f"❌ WSL test pulse failed: {pump.get_error_details()}")
            return False
            
        pump.close()
        return True
        
    except Exception as e:
        print(f"❌ Pump_wsl error: {e}")
        return False

if __name__ == "__main__":
    print("🧪 Quick Pump Test")
    print("=" * 50)
    
    # Test parameters
    test_freq = 100
    test_amp = 100
    test_shape = "RECT"  # Changed from "Rectangular" to match pump API
    test_duration = 2  # seconds
    
    print(f"Test parameters: {test_freq}Hz, {test_amp}Vpp, {test_shape}, {test_duration}s pulse")
    print("=" * 50)

    # Run tests with parameters
    win_ok = test_pump_win(test_freq, test_amp, test_shape, test_duration)
    wsl_ok = test_pump_wsl(test_freq, test_amp, test_shape, test_duration)
    
    print("=" * 50)
    print(f"📊 Test Results:")
    print(f"Windows pump: {'✅ PASS' if win_ok else '❌ FAIL'}")
    print(f"WSL pump: {'✅ PASS' if wsl_ok else '❌ FAIL'}")
    
    if win_ok or wsl_ok:
        print("\n🎉 At least one pump method is working!")
        if win_ok and wsl_ok:
            print("💪 Both pump methods are functional - excellent!")
        elif win_ok:
            print("💡 Windows pump working - you have native hardware control")
        else:
            print("💡 WSL pump working - cross-platform solution functional")
    else:
        print("\n⚠️  Both pump methods failed")
        print("💡 This is expected if no hardware is connected")
        print("💡 Connect pump hardware and ensure drivers are installed to test functionality")