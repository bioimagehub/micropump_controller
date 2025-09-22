#!/usr/bin/env python3
"""
Troubleshooting script for COM4 connection issues
"""

import serial
import serial.tools.list_ports
import time

def test_com4_step_by_step():
    print("🔧 COM4 Troubleshooting")
    print("=" * 30)
    
    # Step 1: Check if COM4 exists
    print("1. Checking if COM4 exists...")
    ports = list(serial.tools.list_ports.comports())
    com4_port = None
    for port in ports:
        if port.device == 'COM4':
            com4_port = port
            print(f"   ✅ Found: {port.device} - {port.description}")
            print(f"   Hardware ID: {port.hwid}")
            break
    
    if not com4_port:
        print("   ❌ COM4 not found!")
        return False
    
    # Step 2: Try different serial settings
    print("\n2. Testing different serial configurations...")
    
    settings_to_try = [
        {'baudrate': 9600, 'timeout': 1},
        {'baudrate': 115200, 'timeout': 1},
        {'baudrate': 9600, 'timeout': 5, 'xonxoff': True},
        {'baudrate': 9600, 'timeout': 1, 'rtscts': True},
        {'baudrate': 9600, 'timeout': 1, 'dsrdtr': True},
    ]
    
    for i, settings in enumerate(settings_to_try):
        print(f"   Trying configuration {i+1}: {settings}")
        try:
            ser = serial.Serial('COM4', **settings)
            print(f"   ✅ Success with configuration {i+1}!")
            ser.close()
            return settings
        except Exception as e:
            print(f"   ❌ Failed: {e}")
    
    # Step 3: Check if device manager shows errors
    print("\n3. Device may need reset. Try:")
    print("   - Unplug and replug USB cable")
    print("   - Check Device Manager for errors")
    print("   - Restart the pump if it has a power switch")
    
    return False

def test_pybartelslabtronix_with_settings(settings):
    """Test pybartelslabtronix with specific settings"""
    print(f"\n🧪 Testing pybartelslabtronix with settings: {settings}")
    
    try:
        # Try to modify the connection
        from pybartelslabtronix import BartelsLabtronix
        
        # Unfortunately, pybartelslabtronix hardcodes some settings
        # Let's try the default first
        blt = BartelsLabtronix(port='COM4')
        print("✅ pybartelslabtronix connected successfully!")
        
        # Quick test
        if hasattr(blt, 'setfrequency'):
            blt.setfrequency(50)
            print("✅ Set frequency command sent")
        
        if hasattr(blt, 'ser') and hasattr(blt.ser, 'close'):
            blt.ser.close()
        
        return True
        
    except Exception as e:
        print(f"❌ pybartelslabtronix failed: {e}")
        return False

if __name__ == "__main__":
    working_settings = test_com4_step_by_step()
    
    if working_settings:
        print(f"\n✅ Found working serial settings: {working_settings}")
        test_pybartelslabtronix_with_settings(working_settings)
    else:
        print("\n❌ No working serial configuration found.")
        print("\n🔧 TROUBLESHOOTING STEPS:")
        print("1. Unplug the USB cable from the pump")
        print("2. Wait 5 seconds")
        print("3. Plug it back in")
        print("4. Check Device Manager for any error icons")
        print("5. Make sure the pump is powered on")
        print("6. Try running this script again")
        print("\nIf the problem persists, the pump hardware or")
        print("USB cable might have an issue.")
