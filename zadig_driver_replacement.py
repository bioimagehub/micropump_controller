#!/usr/bin/env python3
"""
ZADIG DRIVER REPLACEMENT GUIDE
==============================
Step-by-step guide for replacing FTDI driver with libusb/WinUSB for driver-free pump control.
"""

import subprocess
import sys
import os
import time

def check_current_driver():
    """Check current driver for the pump device."""
    print("🔍 CHECKING CURRENT DRIVER STATUS")
    print("=" * 50)
    
    try:
        # Check device manager
        cmd = ['powershell', '-Command', '''
Get-PnpDevice | Where-Object {$_.InstanceId -like "*VID_0403&PID_B4C0*"} | 
Select-Object FriendlyName, Status, InstanceId, Service | Format-Table -AutoSize
''']
        result = subprocess.run(cmd, capture_output=True, text=True)
        print("Current device status:")
        print(result.stdout)
        
        return True
    except Exception as e:
        print(f"Error checking driver: {e}")
        return False

def launch_zadig():
    """Launch Zadig for driver replacement."""
    print("\\n🔧 LAUNCHING ZADIG FOR DRIVER REPLACEMENT")
    print("=" * 50)
    
    zadig_path = r"c:\\git\\micropump_controller\\delete\\utils\\zadig-2.9.exe"
    
    if not os.path.exists(zadig_path):
        print(f"❌ Zadig not found at: {zadig_path}")
        return False
    
    print("📋 ZADIG INSTRUCTIONS:")
    print("1. Zadig will open in a new window")
    print("2. In Zadig menu: Options → List All Devices")
    print("3. Find your Bartels pump device (VID_0403, PID_B4C0)")
    print("4. Current driver should show 'usbser' or 'FTDIBUS'")
    print("5. Select replacement driver: WinUSB, libusb-win32, or libusbK")
    print("6. Click 'Replace Driver' button")
    print("7. Wait for installation to complete")
    print("8. Close Zadig")
    print()
    print("⚠️  WARNING: This will replace the current driver!")
    print("   You can revert using Device Manager later if needed.")
    print()
    
    choice = input("Ready to launch Zadig? (y/n): ").lower().strip()
    if choice not in ['y', 'yes']:
        print("❌ Driver replacement cancelled")
        return False
    
    print("🚀 Launching Zadig...")
    
    try:
        # Launch Zadig (non-blocking)
        subprocess.Popen([zadig_path])
        
        print("✅ Zadig launched!")
        print("\\n⏳ Follow the instructions above in the Zadig window")
        print("   Come back here when driver replacement is complete...")
        
        return True
        
    except Exception as e:
        print(f"❌ Failed to launch Zadig: {e}")
        return False

def test_new_driver():
    """Test communication with new driver."""
    print("\\n🧪 TESTING NEW DRIVER")
    print("=" * 30)
    
    choice = input("Have you completed the driver replacement? (y/n): ").lower().strip()
    if choice not in ['y', 'yes']:
        print("❌ Testing cancelled - complete driver replacement first")
        return False
    
    print("🔄 Testing new driver configuration...")
    
    # Test PyUSB (should work now)
    print("\\n📍 Testing PyUSB with new driver...")
    try:
        import usb.core
        import usb.util
        
        # Find device
        dev = usb.core.find(idVendor=0x0403, idProduct=0xB4C0)
        if dev is None:
            print("❌ Device not found via PyUSB")
            return False
        
        print(f"✅ Device found: {dev}")
        
        try:
            # Get device info
            manufacturer = usb.util.get_string(dev, dev.iManufacturer)
            product = usb.util.get_string(dev, dev.iProduct)
            print(f"   Manufacturer: {manufacturer}")
            print(f"   Product: {product}")
            
            # Set configuration
            dev.set_configuration()
            print("   Configuration set successfully")
            
            # Try bulk transfer
            cfg = dev.get_active_configuration()
            intf = cfg[(0,0)]
            
            # Find endpoints
            ep_out = usb.util.find_descriptor(
                intf, custom_match=lambda e: usb.util.endpoint_direction(e.bEndpointAddress) == usb.util.ENDPOINT_OUT
            )
            
            if ep_out is not None:
                # Send pump commands
                commands = [b'F100\\r', b'A100\\r', b'bon\\r']
                for cmd in commands:
                    ep_out.write(cmd)
                    time.sleep(0.2)
                
                print("✅ Commands sent via PyUSB bulk transfer!")
                
                # Wait then turn off
                time.sleep(2)
                ep_out.write(b'boff\\r')
                print("✅ Pump turned off")
                
                return True
            else:
                print("❌ No output endpoint found")
                return False
                
        except Exception as e:
            print(f"❌ PyUSB communication error: {e}")
            return False
            
    except ImportError:
        print("❌ PyUSB not available")
        return False
    except Exception as e:
        print(f"❌ PyUSB test error: {e}")
        return False

def revert_driver():
    """Guide for reverting driver if needed."""
    print("\\n🔄 DRIVER REVERT INSTRUCTIONS")
    print("=" * 40)
    print("If you need to revert to the original driver:")
    print("1. Open Device Manager (devmgmt.msc)")
    print("2. Find your device under 'Universal Serial Bus devices' or 'libusb devices'")
    print("3. Right-click → Update driver")
    print("4. Browse my computer for drivers")
    print("5. Let me pick from a list")
    print("6. Select 'USB Serial Converter' or 'FTDI' driver")
    print("7. Click Next to install")

def main():
    """Main driver replacement workflow."""
    print("🚀 ZADIG DRIVER REPLACEMENT FOR PUMP CONTROL")
    print("=" * 60)
    print("This will replace the FTDI driver with libusb/WinUSB for direct access")
    print("=" * 60)
    
    # Step 1: Check current status
    check_current_driver()
    
    # Step 2: Launch Zadig
    if not launch_zadig():
        return
    
    # Step 3: Wait for user to complete replacement
    input("\\nPress Enter when you've completed the driver replacement...")
    
    # Step 4: Test new driver
    if test_new_driver():
        print("\\n🎉 SUCCESS! Driver-free pump control working!")
        print("🔧 You can now control the pump without proprietary drivers!")
    else:
        print("\\n❌ Driver replacement didn't enable PyUSB communication")
        print("💡 Try different driver (WinUSB vs libusb-win32 vs libusbK)")
        revert_driver()

if __name__ == "__main__":
    main()