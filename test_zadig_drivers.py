#!/usr/bin/env python3
"""
Zadig Driver Test Plan for Bartels Micropump

This script helps test different driver options installed via Zadig.
Run this after installing each driver type to verify functionality.
"""

import sys
import time

def test_usb_serial_cdc():
    """Test USB Serial (CDC) driver - creates COM port."""
    print("=== Testing USB Serial (CDC) Driver ===")
    print("This driver should create a COM port that works like a real serial port.")
    
    try:
        import serial.tools.list_ports
        
        # Scan for COM ports
        ports = serial.tools.list_ports.comports()
        
        print(f"Found {len(ports)} COM port(s):")
        for port in ports:
            print(f"  {port.device} - {port.description}")
            
            # Check if this might be our device
            if any(keyword in str(port).lower() for keyword in ['ftdi', 'bartels', 'cdc', 'serial']):
                print(f"  >>> POTENTIAL BARTELS DEVICE ON {port.device} <<<")
        
        if ports:
            print("\n✓ COM ports detected - USB Serial (CDC) driver working")
            print("Next: Run 'python test_pump_serial_native.py'")
            return True
        else:
            print("\n✗ No COM ports found")
            return False
            
    except ImportError:
        print("pyserial not available - install with: pip install pyserial")
        return False
    except Exception as e:
        print(f"Error testing USB Serial: {e}")
        return False

def test_winusb():
    """Test WinUSB driver - generic USB access."""
    print("=== Testing WinUSB Driver ===")
    print("This driver provides generic USB access via Windows USB API.")
    
    try:
        import usb.core
        
        # Look for our device
        device = usb.core.find(idVendor=0x0403, idProduct=0xb4c0)
        
        if device:
            print(f"✓ Found Bartels device via WinUSB: VID:{hex(device.idVendor)} PID:{hex(device.idProduct)}")
            
            # Try to access device info
            try:
                manufacturer = usb.util.get_string(device, device.iManufacturer)
                product = usb.util.get_string(device, device.iProduct)
                print(f"  Manufacturer: {manufacturer}")
                print(f"  Product: {product}")
                print("✓ Device strings accessible - WinUSB working well")
            except:
                print("  Device found but strings not accessible")
            
            print("Next: Run 'python test_pump_driver_free.py'")
            return True
        else:
            print("✗ Bartels device not found via WinUSB")
            return False
            
    except ImportError:
        print("pyusb not available - install with: pip install pyusb")
        return False
    except Exception as e:
        print(f"Error testing WinUSB: {e}")
        return False

def test_libusb():
    """Test libusb driver - direct libusb access."""
    print("=== Testing libusb Driver ===")
    print("This driver provides direct libusb access for advanced USB communication.")
    
    try:
        import usb.core
        import usb.backend.libusb1
        
        # Try to use libusb backend specifically
        backend = usb.backend.libusb1.get_backend()
        if backend:
            print("✓ libusb backend available")
        
        # Look for our device
        device = usb.core.find(idVendor=0x0403, idProduct=0xb4c0, backend=backend)
        
        if device:
            print(f"✓ Found Bartels device via libusb: VID:{hex(device.idVendor)} PID:{hex(device.idProduct)}")
            
            # Try more advanced operations
            try:
                # Try to set configuration
                device.set_configuration()
                print("✓ Device configuration successful")
                
                # Try to get interface
                interface = device.get_active_configuration()[(0,0)]
                print("✓ Interface access successful")
                
                print("✓ libusb driver working excellently")
                print("Next: Run 'python test_pump_usb_advanced.py'")
                return True
                
            except Exception as e:
                print(f"Device found but configuration failed: {e}")
                print("Driver may need different approach")
                return False
        else:
            print("✗ Bartels device not found via libusb")
            return False
            
    except ImportError:
        print("pyusb or libusb not available")
        return False
    except Exception as e:
        print(f"Error testing libusb: {e}")
        return False

def main():
    """Main test function."""
    print("=== Zadig Driver Test Plan ===")
    print()
    print("INSTRUCTIONS:")
    print("1. Run Zadig (zadig-2.9.exe)")
    print("2. Select 'USB Micropump Control' device")
    print("3. Choose driver type and install")
    print("4. Run this script to test")
    print()
    print("RECOMMENDED ORDER:")
    print("1. Try USB Serial (CDC) first")
    print("2. If that doesn't work, try libusb")
    print("3. WinUSB as last resort")
    print()
    
    # Test all available drivers
    tests = [
        ("USB Serial (CDC)", test_usb_serial_cdc),
        ("WinUSB", test_winusb),
        ("libusb", test_libusb)
    ]
    
    results = {}
    
    for driver_name, test_func in tests:
        print(f"\n{'='*50}")
        try:
            results[driver_name] = test_func()
        except Exception as e:
            print(f"Test failed: {e}")
            results[driver_name] = False
        
        time.sleep(1)
    
    # Summary
    print(f"\n{'='*50}")
    print("=== TEST RESULTS SUMMARY ===")
    
    for driver_name, success in results.items():
        status = "✓ WORKING" if success else "✗ NOT WORKING"
        print(f"{driver_name:20} {status}")
    
    # Recommendations
    print("\nRECOMMENDATIONS:")
    if results.get("USB Serial (CDC)", False):
        print("✓ Use USB Serial (CDC) - run: python test_pump_serial_native.py")
    elif results.get("libusb", False):
        print("✓ Use libusb - run: python test_pump_usb_advanced.py")
    elif results.get("WinUSB", False):
        print("⚠ Use WinUSB - run: python test_pump_driver_free.py")
    else:
        print("✗ No drivers working - check Zadig installation")

if __name__ == "__main__":
    main()
