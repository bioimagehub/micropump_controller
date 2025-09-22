#!/usr/bin/env python3
"""
Linux-focused micropump test script.
Tests both direct USB and serial port detection without Windows dependencies.
"""

import sys
import time
import glob
import subprocess
from pathlib import Path

def check_linux_usb_support():
    """Check if Linux has proper USB/FTDI support."""
    print("=== Linux USB Support Check ===")
    
    # Check kernel modules
    try:
        result = subprocess.run(['lsmod'], capture_output=True, text=True)
        modules = result.stdout
        
        ftdi_loaded = 'ftdi_sio' in modules
        usbserial_loaded = 'usbserial' in modules
        
        print(f"FTDI module loaded: {'✓' if ftdi_loaded else '✗'}")
        print(f"USB Serial module loaded: {'✓' if usbserial_loaded else '✗'}")
        
        if not ftdi_loaded:
            print("Loading FTDI module...")
            subprocess.run(['sudo', 'modprobe', 'ftdi_sio'], check=True)
            print("✓ FTDI module loaded")
        
        if not usbserial_loaded:
            print("Loading USB Serial module...")
            subprocess.run(['sudo', 'modprobe', 'usbserial'], check=True)
            print("✓ USB Serial module loaded")
            
        return True
        
    except Exception as e:
        print(f"✗ Error checking USB support: {e}")
        return False

def scan_for_usb_devices():
    """Scan for USB devices that might be the micropump."""
    print("\n=== USB Device Scan ===")
    
    try:
        # Use lsusb to find devices
        result = subprocess.run(['lsusb'], capture_output=True, text=True)
        print("All USB devices:")
        for line in result.stdout.strip().split('\n'):
            print(f"  {line}")
            
        # Look for FTDI devices (VID 0403)
        ftdi_devices = [line for line in result.stdout.split('\n') if '0403:' in line]
        if ftdi_devices:
            print("\nFTDI devices found:")
            for device in ftdi_devices:
                print(f"  {device}")
                if 'b4c0' in device.lower():
                    print("    ↳ ✓ This looks like the Bartels micropump!")
        else:
            print("✗ No FTDI devices found")
            
        return len(ftdi_devices) > 0
        
    except Exception as e:
        print(f"✗ Error scanning USB devices: {e}")
        return False

def scan_for_serial_ports():
    """Scan for serial ports that might be the micropump."""
    print("\n=== Serial Port Scan ===")
    
    # Look for ttyUSB devices
    usb_ports = glob.glob('/dev/ttyUSB*')
    acm_ports = glob.glob('/dev/ttyACM*')
    all_ports = usb_ports + acm_ports
    
    print(f"Found {len(all_ports)} serial ports:")
    for port in all_ports:
        print(f"  {port}")
        
        # Try to get device info
        try:
            result = subprocess.run(['udevadm', 'info', '--name=' + port], 
                                  capture_output=True, text=True)
            if '0403' in result.stdout:
                print(f"    ↳ ✓ FTDI device detected")
                if 'b4c0' in result.stdout.lower():
                    print(f"    ↳ ✓ Bartels micropump detected!")
        except:
            print(f"    ↳ Could not get device info")
    
    return all_ports

def test_serial_communication(ports):
    """Test serial communication with detected ports."""
    print("\n=== Serial Communication Test ===")
    
    if not ports:
        print("No serial ports to test")
        return False
    
    # Try to import serial
    try:
        import serial
    except ImportError:
        print("✗ pyserial not available")
        return False
    
    for port in ports:
        print(f"Testing {port}...")
        try:
            # Try to open the port
            ser = serial.Serial(
                port=port,
                baudrate=9600,
                timeout=1.0,
                bytesize=serial.EIGHTBITS,
                parity=serial.PARITY_NONE,
                stopbits=serial.STOPBITS_ONE
            )
            
            print(f"  ✓ Port opened successfully")
            
            # Try to send a test command
            ser.write(b"F050\r")  # Set frequency to 50 Hz
            time.sleep(0.2)
            
            # Try to read response
            response = ser.read(100)
            print(f"  Response: {response}")
            
            if response:
                print(f"  ✓ Communication successful on {port}!")
                ser.close()
                return True
            else:
                print(f"  ⚠ No response from {port}")
                
            ser.close()
            
        except Exception as e:
            print(f"  ✗ Error testing {port}: {e}")
            
    return False

def test_usbx_library():
    """Test if usbx library can find the device."""
    print("\n=== USBX Library Test ===")
    
    try:
        import usbx
        print("✓ usbx library imported")
        
        devices = usbx.usb.find_devices()
        print(f"Found {len(devices)} USB devices via usbx:")
        
        micropump_found = False
        for device in devices:
            vid = device.vid
            pid = device.pid
            print(f"  VID=0x{vid:04x} PID=0x{pid:04x}")
            
            if vid == 0x0403 and pid == 0xb4c0:
                print("    ↳ ✓ Bartels micropump found!")
                micropump_found = True
            elif vid == 0x0403:
                print("    ↳ FTDI device (might be micropump with different PID)")
        
        return micropump_found
        
    except ImportError:
        print("✗ usbx library not available")
        return False
    except Exception as e:
        print(f"✗ Error using usbx: {e}")
        return False

def create_device_binding_instructions():
    """Create instructions for manually binding the device."""
    print("\n=== Manual Device Binding Instructions ===")
    print("""
If your micropump is physically connected but not detected:

1. Check if it appears in Windows Device Manager (if using WSL)
2. If using native Linux, try:
   
   # Add device manually to ftdi_sio driver
   echo "0403 b4c0" | sudo tee /sys/bus/usb-serial/drivers/ftdi_sio/new_id
   
   # Or try generic USB-serial
   echo "0403 b4c0" | sudo tee /sys/bus/usb-serial/drivers/generic/new_id

3. Check dmesg for USB device messages:
   dmesg | tail -20

4. Set permissions for the device:
   sudo chmod 666 /dev/ttyUSB*
   
5. If still not working, the device might need specific drivers
   or have a different VID/PID than expected.
""")

def main():
    """Main test function."""
    print("Linux Micropump Detection Tool")
    print("=" * 40)
    
    # Check USB support
    usb_support_ok = check_linux_usb_support()
    
    # Scan for USB devices
    usb_devices_found = scan_for_usb_devices()
    
    # Scan for serial ports
    serial_ports = scan_for_serial_ports()
    
    # Test serial communication
    serial_ok = test_serial_communication(serial_ports)
    
    # Test usbx library
    usbx_ok = test_usbx_library()
    
    # Summary
    print("\n=== Summary ===")
    if serial_ok:
        print("✓ Device found and responding via serial port!")
        print("You can use the pump with serial communication.")
    elif usbx_ok:
        print("✓ Device found via USB!")
        print("You can use the pump with USB communication.")
    elif usb_devices_found or serial_ports:
        print("⚠ Device hardware detected but communication failed")
        print("Check permissions and driver setup")
    else:
        print("✗ No micropump detected")
        print("Check physical connection and power")
        if not usb_support_ok:
            print("Also check USB driver support")
        
        create_device_binding_instructions()

if __name__ == "__main__":
    main()
