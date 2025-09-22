#!/usr/bin/env python3
"""
Docker-based Bartels micropump control using the pybartelslabtronix library.
This runs in a Linux container with USB device passthrough.
"""

import sys
import time
import logging

try:
    from pybartelslabtronix import BartelsLabtronix, SignalForm
    print("Successfully imported pybartelslabtronix library")
except ImportError as e:
    print(f"Failed to import pybartelslabtronix: {e}")
    print("Installing pybartelslabtronix...")
    import subprocess
    subprocess.check_call([sys.executable, "-m", "pip", "install", "pybartelslabtronix"])
    from pybartelslabtronix import BartelsLabtronix, SignalForm

def scan_serial_ports():
    """Scan for available serial ports in container."""
    import serial.tools.list_ports
    
    print("=== Serial Port Scanner (Docker) ===")
    ports = serial.tools.list_ports.comports()
    
    if not ports:
        print("No serial ports found in container")
        print("This means:")
        print("1. USB device not passed through to container")
        print("2. Device not creating serial interface")
        print("3. Need to map /dev/ttyUSB* or /dev/ttyACM* devices")
        return []
    
    print(f"Found {len(ports)} serial port(s):")
    for port in ports:
        print(f"  {port.device} - {port.description}")
    
    return [port.device for port in ports]

def test_with_pybartelslabtronix():
    """Test using the pybartelslabtronix library."""
    print("\n=== Testing with pybartelslabtronix Library ===")
    
    # Scan for ports first
    ports = scan_serial_ports()
    
    if not ports:
        print("No serial ports available. Trying common Linux device paths...")
        test_ports = ['/dev/ttyUSB0', '/dev/ttyUSB1', '/dev/ttyACM0', '/dev/ttyACM1']
    else:
        test_ports = ports
    
    for port in test_ports:
        try:
            print(f"\nTrying to connect to {port}...")
            
            # Create pump controller with specific port
            pump = BartelsLabtronix(port=port)
            
            print(f"✓ Connected to Bartels pump on {port}")
            
            # Get initial status
            print("\n1. Getting initial status...")
            state = pump.get_state()
            print(state)
            
            # Set pump parameters like the working example
            print("\n2. Setting pump parameters...")
            pump.setfrequency(100)
            time.sleep(0.2)
            pump.setamplitude(100)
            time.sleep(0.2)
            pump.setsignalform(SignalForm.Rectangular)
            time.sleep(0.2)
            
            # Get updated status
            print("\n3. Getting updated status...")
            state = pump.get_state()
            print(state)
            
            # Turn pump on
            print("\n4. Turning pump ON for 10 seconds...")
            pump.turnon()
            print("*** PUMP SHOULD BE OPERATING NOW ***")
            
            # Run for 10 seconds
            for i in range(10):
                print(f"Running... {10-i} seconds remaining")
                time.sleep(1)
            
            # Turn pump off
            print("\n5. Turning pump OFF...")
            pump.turnoff()
            print("*** PUMP SHOULD BE STOPPED NOW ***")
            
            # Get final status
            print("\n6. Getting final status...")
            state = pump.get_state()
            print(state)
            
            # Cleanup
            pump.disconnect()
            
            print("\n✓ Test completed successfully!")
            return True
            
        except Exception as e:
            print(f"✗ Failed to connect to {port}: {e}")
            continue
    
    print("\n✗ Failed to connect to any port")
    return False

def main():
    """Main test function."""
    print("=== Bartels Micropump Docker Test ===")
    
    # Set up logging
    logging.basicConfig(level=logging.INFO)
    
    # Test with the proven pybartelslabtronix library
    success = test_with_pybartelslabtronix()
    
    if not success:
        print("\nTroubleshooting tips:")
        print("1. Make sure Docker has access to USB device:")
        print("   docker run --device=/dev/ttyUSB0 ...")
        print("2. Or pass through all USB devices:")
        print("   docker run --privileged -v /dev:/dev ...")
        print("3. Check if device appears in container:")
        print("   ls -la /dev/tty*")

if __name__ == "__main__":
    main()
