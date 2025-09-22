#!/usr/bin/env python3
"""
Simple serial test for USB Serial (CDC) driver.
Tests basic connectivity before trying the full pump protocol.
"""

import serial
import serial.tools.list_ports
import time

def test_basic_serial_connection():
    """Test basic serial connection to COM3."""
    print("=== Basic Serial Connection Test ===")
    
    # Find the COM port
    ports = serial.tools.list_ports.comports()
    com_port = None
    
    for port in ports:
        if 'micropump' in port.description.lower():
            com_port = port.device
            print(f"Found Bartels device on {com_port}: {port.description}")
            break
    
    if not com_port:
        print("No Bartels COM port found")
        return False
    
    # Try different serial configurations
    configs = [
        {"baudrate": 9600, "timeout": 1, "xonxoff": True},
        {"baudrate": 9600, "timeout": 1, "xonxoff": False},
        {"baudrate": 115200, "timeout": 1, "xonxoff": False},
        {"baudrate": 19200, "timeout": 1, "xonxoff": False},
    ]
    
    for i, config in enumerate(configs):
        try:
            print(f"\nTesting configuration {i+1}: {config}")
            
            with serial.Serial(com_port, **config) as ser:
                print(f"✓ Successfully opened {com_port}")
                
                # Wait for connection to stabilize
                time.sleep(0.5)
                
                # Try to send a simple command
                print("Sending status request...")
                ser.write(b"\r")
                ser.flush()
                
                # Try to read response
                time.sleep(0.5)
                if ser.in_waiting > 0:
                    data = ser.read(ser.in_waiting)
                    print(f"✓ Received data: {data}")
                    print(f"✓ As text: {repr(data.decode('utf-8', errors='ignore'))}")
                    return True
                else:
                    print("No response received")
                
        except Exception as e:
            print(f"✗ Failed: {e}")
            continue
    
    return False

def test_pump_commands():
    """Test actual pump commands if basic connection works."""
    print("\n=== Pump Commands Test ===")
    
    com_port = "COM3"  # We know it's COM3
    
    try:
        # Use the working configuration from pybartelslabtronix
        with serial.Serial(com_port, 9600, timeout=1, xonxoff=True) as ser:
            print(f"Connected to {com_port}")
            
            # Send pump commands like pybartelslabtronix
            commands = [
                ("", "Get Status"),
                ("F100", "Set Frequency 100Hz"),
                ("A100", "Set Amplitude 100Vpp"),
                ("MR", "Set Rectangular Wave"),
            ]
            
            for command, description in commands:
                print(f"\n{description}: '{command}'")
                
                # Send command with \r like pybartelslabtronix
                full_cmd = command + "\r"
                ser.write(full_cmd.encode('utf-8'))
                ser.flush()
                
                # Wait for response
                time.sleep(0.5)
                
                if ser.in_waiting > 0:
                    response = ser.read(ser.in_waiting)
                    text = response.decode('utf-8', errors='ignore')
                    print(f"Response: {repr(text)}")
                else:
                    print("No response")
            
            return True
            
    except Exception as e:
        print(f"Pump commands test failed: {e}")
        return False

def main():
    """Main test function."""
    print("=== USB Serial (CDC) Driver Test ===")
    
    # Test basic connection first
    if test_basic_serial_connection():
        print("\n✓ Basic serial connection working!")
        
        # Try pump commands
        if test_pump_commands():
            print("\n✓ Pump commands working!")
            print("\nReady to test full pump operation!")
            print("Run: python test_pump_serial_native.py")
        else:
            print("\n⚠ Basic connection works but pump commands need work")
    else:
        print("\n✗ Basic serial connection failed")
        print("Try different driver in Zadig (libusb or WinUSB)")

if __name__ == "__main__":
    main()
