#!/usr/bin/env python3
"""
Check if Bartels USB device is still visible after uninstalling WinUSB driver.
"""

import usb.core

def check_usb_devices():
    """Check for USB devices, especially FTDI/Bartels ones."""
    print("=== USB Device Scanner ===")
    
    try:
        devices = usb.core.find(find_all=True)
        
        ftdi_devices = []
        for device in devices:
            if device.idVendor == 0x0403:  # FTDI vendor ID
                ftdi_devices.append(device)
        
        if not ftdi_devices:
            print("No FTDI devices found via USB")
            print("Device may need drivers or may not be recognized")
        else:
            print(f"Found {len(ftdi_devices)} FTDI device(s):")
            for device in ftdi_devices:
                print(f"  VID:PID {hex(device.idVendor)}:{hex(device.idProduct)}")
                try:
                    manufacturer = usb.util.get_string(device, device.iManufacturer)
                    product = usb.util.get_string(device, device.iProduct)
                    print(f"  Manufacturer: {manufacturer}")
                    print(f"  Product: {product}")
                except:
                    print("  (Unable to read device strings - may need drivers)")
                
                if device.idProduct == 0xb4c0:
                    print("  >>> THIS IS THE BARTELS MICROPUMP <<<")
                print()
        
    except Exception as e:
        print(f"Error scanning USB devices: {e}")
        print("This usually means:")
        print("1. No libusb backend available")
        print("2. Device needs proper drivers")
        print("3. Access permissions issue")

if __name__ == "__main__":
    check_usb_devices()
