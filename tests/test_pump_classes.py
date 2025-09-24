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
        
        print("OK Pump initialized!")
        
        # Send test commands
        print(f"WRENCH Configuring pump: {freq}Hz, {amplitude}Vpp, {waveform}")
        if not pump.set_frequency(freq):
            print(f"FAIL Failed to set frequency: {pump.get_error_details()}")
            return False
        
        if not pump.set_voltage(amplitude):
            print(f"FAIL Failed to set voltage: {pump.get_error_details()}")
            return False
            
        if not pump.set_waveform(waveform):
            print(f"FAIL Failed to set waveform: {pump.get_error_details()}")
            return False
        
        # Run test pulse
        print(f"ROCKET Running test pulse for {duration} seconds...")
        if pump.pulse(duration):
            print("OK Test pulse completed successfully!")
        else:
            print(f"FAIL Test pulse failed: {pump.get_error_details()}")
            return False
            
        pump.close()
        return True
        
    except Exception as e:
        print(f"FAIL Pump_win error: {e}")
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
        
        print("OK WSL pump initialized!")
        
        # Send test commands
        print(f"WRENCH Configuring pump via WSL: {freq}Hz, {amplitude}Vpp, {waveform}")
        if not pump.set_frequency(freq):
            print(f"FAIL Failed to set frequency: {pump.get_error_details()}")
            return False
        
        if not pump.set_voltage(amplitude):
            print(f"FAIL Failed to set voltage: {pump.get_error_details()}")
            return False
            
        if not pump.set_waveform(waveform):
            print(f"FAIL Failed to set waveform: {pump.get_error_details()}")
            return False
        
        # Run test pulse
        print(f"ROCKET Running WSL test pulse for {duration} seconds...")
        if pump.pulse(duration):
            print("OK WSL test pulse completed successfully!")
        else:
            print(f"FAIL WSL test pulse failed: {pump.get_error_details()}")
            return False
            
        pump.close()
        return True
        
    except Exception as e:
        print(f"FAIL Pump_wsl error: {e}")
        return False

if __name__ == "__main__":
    print("LAB Quick Pump Test")
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
    print(f"STATS Test Results:")
    print(f"Windows pump: {'OK PASS' if win_ok else 'FAIL FAIL'}")
    print(f"WSL pump: {'OK PASS' if wsl_ok else 'FAIL FAIL'}")
    
    if win_ok or wsl_ok:
        print("\nCELEBRATE At least one pump method is working!")
        if win_ok and wsl_ok:
            print("STRONG Both pump methods are functional - excellent!")
        elif win_ok:
            print("NOTE Windows pump working - you have native hardware control")
        else:
            print("NOTE WSL pump working - cross-platform solution functional")
    else:
        print("\nWARNING  Both pump methods failed")
        print("NOTE This is expected if no hardware is connected")
        print("NOTE Connect pump hardware and ensure drivers are installed to test functionality")