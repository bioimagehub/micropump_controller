#!/usr/bin/env python3
"""Test script to run a 10-second pulse at 100 Hz, 100 VPP rectangle wave."""

import sys
import traceback
from pathlib import Path

# Add src to path
src_path = Path(__file__).parent / "src"
sys.path.insert(0, str(src_path))

from controllers.pump_control import UsbPumpController, PumpCommunicationError


def main():
    """Run a 10-second pulse with specified parameters."""
    print("=== Bartels Micropump Pulse Test ===")
    print("Testing 10-second pulse: 100 Hz, 100 VPP, Rectangle wave")
    print()
    
    try:
        # Create controller - it will auto-detect connection method
        print("Initializing pump controller...")
        pump = UsbPumpController()
        
        print(f"Connected! Active mode: {pump._active_mode}")
        print()
        
        # Test basic communication
        print("Testing communication...")
        try:
            response = pump.send_command("?", expect_response=True, timeout=2.0)
            print(f"Pump response to '?': {response}")
        except Exception as e:
            print(f"Communication test failed (this may be normal): {e}")
        print()
        
        # Set pump parameters
        print("Setting pump parameters...")
        print("- Frequency: 100 Hz")
        pump.set_frequency(100)
        
        print("- Amplitude: 100 VPP")
        pump.set_amplitude(100)
        
        print("- Waveform: Rectangle")
        pump.set_waveform("RECTANGLE")
        print()
        
        # Run pulse
        print("Starting 10-second pulse...")
        pump.pulse(duration_s=10.0)
        print("Pulse completed!")
        
    except PumpCommunicationError as e:
        print(f"Pump communication error: {e}")
        return 1
    except Exception as e:
        print(f"Unexpected error: {e}")
        traceback.print_exc()
        return 1
    finally:
        try:
            if 'pump' in locals():
                pump.disconnect()
                print("Pump disconnected.")
        except:
            pass
    
    return 0


if __name__ == "__main__":
    exit(main())
