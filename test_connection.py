#!/usr/bin/env python3
"""Test script to diagnose micropump connection issues."""

import sys
import time
from pathlib import Path

# Add the src directory to the path
sys.path.insert(0, str(Path(__file__).parent / "src"))

try:
    import usbx
    print("✓ usbx library imported successfully")
except ImportError as e:
    print(f"✗ Failed to import usbx: {e}")
    sys.exit(1)

try:
    from controllers.pump_control import UsbPumpController, PumpCommunicationError
    print("✓ UsbPumpController imported successfully")
except ImportError as e:
    print(f"✗ Failed to import UsbPumpController: {e}")
    sys.exit(1)

def test_usb_devices():
    """List all USB devices and look for the micropump."""
    print("\n=== USB Device Scan ===")
    
    # Check if we're in WSL
    is_wsl = False
    try:
        with open('/proc/version', 'r') as f:
            if 'microsoft' in f.read().lower():
                is_wsl = True
                print("✓ Running in WSL environment")
    except:
        pass
    
    try:
        devices = usbx.usb.find_devices()
        print(f"Found {len(devices)} USB devices:")
        
        bartels_found = False
        for device in devices:
            vid = device.vid
            pid = device.pid
            print(f"  VID:PID = 0x{vid:04x}:0x{pid:04x}")
            
            # Check for Bartels micropump (default VID/PID)
            if vid == 0x0403 and pid == 0xb4c0:
                print("  ↳ ✓ Bartels micropump detected!")
                bartels_found = True
            # Check for FTDI devices (common for the pump)
            elif vid == 0x0403:
                print(f"  ↳ FTDI device (PID: 0x{pid:04x})")
                
        if not bartels_found:
            print("  ✗ No Bartels micropump found with default VID:PID (0403:b4c0)")
            print("  → Check if the device is connected and powered on")
            print("  → Try a different USB port or cable")
            
            if is_wsl:
                print("  → WSL detected: USB forwarding likely needed")
                print_wsl_instructions()
                
        return bartels_found
        
    except Exception as e:
        print(f"✗ Error scanning USB devices: {e}")
        return False

def print_wsl_instructions():
    """Print detailed WSL USB forwarding instructions."""
    print("\n" + "="*60)
    print("WSL USB FORWARDING SETUP")
    print("="*60)
    print("\nYour micropump is not detected in WSL. To fix this:")
    print("\nSTEP 1 - Install usbipd-win on Windows (as Administrator):")
    print("  winget install usbipd")
    print("\nSTEP 2 - Find your device in Windows Command Prompt/PowerShell:")
    print("  usbipd list")
    print("  ")
    print("  Look for a device with:")
    print("  - Name containing \"FTDI\" or \"Serial\"")
    print("  - VID 0403 (this is FTDI vendor)")
    print("  ")
    print("STEP 3 - Share the device (replace X-X with actual bus-device ID):")
    print("  usbipd bind --busid X-X")
    print("  ")
    print("STEP 4 - Attach to WSL:")
    print("  usbipd attach --wsl --busid X-X")
    print("\nSTEP 5 - Verify in WSL:")
    print("  lsusb | grep 0403")
    print("\nSTEP 6 - Set USB permissions in WSL:")
    print("  sudo usermod -a -G dialout $USER")
    print("  echo 'SUBSYSTEM==\"usb\", ATTR{idVendor}==\"0403\", ATTR{idProduct}==\"b4c0\", MODE=\"0666\"' | sudo tee /etc/udev/rules.d/99-micropump.rules")
    print("  sudo udevadm control --reload-rules")
    print("  ")
    print("STEP 7 - Logout and login to WSL, then run this test again.")
    print("\nAlternative quick test (temporary):")
    print("  sudo chmod 666 /dev/bus/usb/*/*")
    print("  (This gives broad USB permissions - use only for testing)")

def test_pump_connection():
    """Test direct connection to the micropump."""
    print("\n=== Pump Connection Test ===")
    
    try:
        # Try with auto_connect=False first to avoid immediate connection
        pump = UsbPumpController(auto_connect=False)
        print("✓ UsbPumpController created")
        
        # Now try to connect manually
        print("Attempting to connect...")
        pump.connect()
        print("✓ Successfully connected to micropump!")
        
        # Test if we can send a simple command
        print("Testing basic communication...")
        response = pump.send_command("F050")  # Set frequency to 50 Hz
        print(f"✓ Command sent successfully, response: {response}")
        
        pump.disconnect()
        print("✓ Disconnected successfully")
        return True
        
    except PumpCommunicationError as e:
        print(f"✗ Pump communication error: {e}")
        return False
    except Exception as e:
        print(f"✗ Unexpected error: {e}")
        return False

def print_wsl_setup_instructions():
    """Print WSL USB forwarding setup instructions."""
    print("\n" + "="*60)
    print("WSL USB FORWARDING SETUP")
    print("="*60)
    print("""
Your micropump is not detected in WSL. To fix this:

STEP 1 - Install usbipd-win on Windows (as Administrator):
  winget install usbipd

STEP 2 - Find your device in Windows Command Prompt/PowerShell:
  usbipd list
  
  Look for a device with:
  - Name containing "FTDI" or "Serial"
  - VID 0403 (this is FTDI vendor)
  
STEP 3 - Share the device (replace X-X with actual bus-device ID):
  usbipd bind --busid X-X
  
STEP 4 - Attach to WSL:
  usbipd attach --wsl --busid X-X

STEP 5 - Verify in WSL:
  lsusb | grep 0403

STEP 6 - Set USB permissions in WSL:
  sudo usermod -a -G dialout $USER
  echo 'SUBSYSTEM=="usb", ATTR{idVendor}=="0403", ATTR{idProduct}=="b4c0", MODE="0666"' | sudo tee /etc/udev/rules.d/99-micropump.rules
  sudo udevadm control --reload-rules
  
STEP 7 - Logout and login to WSL, then run this test again.

Alternative quick test (temporary):
  sudo chmod 666 /dev/bus/usb/*/*
  (This gives broad USB permissions - use only for testing)
""")

def main():
    """Run all diagnostic tests."""
    print("Micropump Connection Diagnostic Tool")
    print("=" * 40)
    
    # Check if we're in WSL
    try:
        with open('/proc/version', 'r') as f:
            is_wsl = 'microsoft' in f.read().lower()
    except:
        is_wsl = False
    
    if is_wsl:
        print("✓ Running in WSL environment")
    
    # Test 1: USB device scan
    usb_ok = test_usb_devices()
    
    # Test 2: Connection test (only if USB device found)
    if usb_ok:
        connection_ok = test_pump_connection()
    else:
        print("\n=== Pump Connection Test ===")
        print("✗ Skipping connection test - no micropump detected")
        connection_ok = False
    
    # Summary
    print("\n=== Summary ===")
    if usb_ok and connection_ok:
        print("✓ All tests passed! Micropump is ready to use.")
    elif usb_ok:
        print("⚠ Device detected but connection failed.")
        print("  → Check permissions (try running with sudo)")
        print("  → Verify the device is not in use by another process")
    else:
        print("✗ No micropump detected.")
        if is_wsl:
            print("  → WSL detected: USB forwarding likely needed")
            print_wsl_setup_instructions()
        else:
            print("  → Check physical connection")
            print("  → Verify device is powered on") 
            print("  → Try different USB port/cable")

if __name__ == "__main__":
    main()
