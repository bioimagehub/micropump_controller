#!/usr/bin/env python3
"""
ZADIG DRIVER-FREE PUMP CONTROLLER
Alternative solution using WinUSB/libusb drivers via Zadig
No signed drivers required - uses generic USB communication
"""

import os
import sys
import time
import subprocess
import tempfile

def check_zadig_available():
    """Check if Zadig is available."""
    zadig_path = r"c:\git\micropump_controller\zadig-2.9.exe"
    if os.path.exists(zadig_path):
        return zadig_path
    
    # Check if zadig is in PATH
    try:
        subprocess.run(["zadig", "--help"], capture_output=True, timeout=5)
        return "zadig"
    except:
        pass
        
    return None

def launch_zadig_gui():
    """Launch Zadig with instructions for manual driver replacement."""
    print("🔧 LAUNCHING ZADIG FOR DRIVER-FREE SOLUTION")
    print("="*50)
    print()
    print("ZADIG INSTRUCTIONS:")
    print("1. Zadig will open - wait for it to load")
    print("2. Click 'Options' → 'List All Devices'")
    print("3. Find 'USB Micropump Control' or device with VID_0403 PID_B4C0")
    print("4. Select target driver: WinUSB (recommended)")
    print("5. Click 'Replace Driver' and wait for completion")
    print("6. Close Zadig when done")
    print()
    
    zadig_path = check_zadig_available()
    if not zadig_path:
        print("❌ Zadig not found!")
        print("Please download zadig-2.9.exe from https://zadig.akeo.ie/")
        return False
        
    print(f"Starting Zadig from: {zadig_path}")
    print("Press any key when ready...")
    try:
        input()
    except:
        pass
        
    try:
        # Launch Zadig
        if zadig_path.endswith(".exe"):
            subprocess.Popen([zadig_path])
        else:
            subprocess.Popen(["zadig"])
            
        print("✅ Zadig launched!")
        print("Complete the driver replacement, then press any key...")
        try:
            input()
        except:
            pass
            
        return True
        
    except Exception as e:
        print(f"❌ Failed to launch Zadig: {e}")
        return False

def test_driver_free_communication():
    """Test communication after driver replacement."""
    print("\n🧪 Testing driver-free communication...")
    
    try:
        import usb.core
        import usb.util
        
        # Find device
        device = usb.core.find(idVendor=0x0403, idProduct=0xB4C0)
        
        if device is None:
            print("❌ Device not found via PyUSB")
            print("Driver replacement may not have completed successfully")
            return False
            
        print(f"✅ Device found: {device}")
        
        try:
            # Try to get device information
            manufacturer = usb.util.get_string(device, device.iManufacturer) if device.iManufacturer else "Unknown"
            product = usb.util.get_string(device, device.iProduct) if device.iProduct else "Unknown"
            
            print(f"   Manufacturer: {manufacturer}")
            print(f"   Product: {product}")
            
        except Exception as e:
            print(f"   Device info access failed: {e}")
            
        try:
            # Try to set configuration
            device.set_configuration()
            print("✅ Device configuration successful")
            
            # Find endpoints
            cfg = device.get_active_configuration()
            intf = cfg[(0,0)]
            
            # Look for OUT endpoint
            ep_out = usb.util.find_descriptor(
                intf, 
                custom_match=lambda e: usb.util.endpoint_direction(e.bEndpointAddress) == usb.util.ENDPOINT_OUT
            )
            
            if ep_out is not None:
                print(f"✅ Found output endpoint: {hex(ep_out.bEndpointAddress)}")
                
                # Try to send commands
                print("💨 Testing pump commands...")
                
                commands = [b'F100\r', b'A100\r', b'bon\r']
                for cmd in commands:
                    try:
                        ep_out.write(cmd)
                        time.sleep(0.2)
                        print(f"   Sent: {cmd}")
                    except Exception as e:
                        print(f"   Failed to send {cmd}: {e}")
                        
                # Wait then turn off
                time.sleep(2)
                try:
                    ep_out.write(b'boff\r')
                    print("   Sent: boff (pump off)")
                except:
                    pass
                    
                print("🎉 Driver-free communication successful!")
                return True
                
            else:
                print("⚠️  No output endpoint found")
                return False
                
        except Exception as e:
            print(f"❌ Device configuration failed: {e}")
            return False
            
    except ImportError:
        print("❌ PyUSB not available")
        print("Install with: pip install pyusb")
        return False
    except Exception as e:
        print(f"❌ Communication test failed: {e}")
        return False

def install_pyusb_if_needed():
    """Install PyUSB if not available."""
    try:
        import usb.core
        print("✅ PyUSB already available")
        return True
    except ImportError:
        print("📦 Installing PyUSB...")
        try:
            subprocess.check_call([sys.executable, "-m", "pip", "install", "pyusb"])
            print("✅ PyUSB installed successfully")
            return True
        except Exception as e:
            print(f"❌ Failed to install PyUSB: {e}")
            return False

def main():
    """Main Zadig-based installation process."""
    print("="*60)
    print("🚀 ZADIG DRIVER-FREE PUMP SOLUTION")
    print("="*60)
    print()
    print("This method replaces FTDI drivers with generic USB drivers")
    print("Advantages:")
    print("  ✅ No signed drivers required")
    print("  ✅ No certificate installation needed")
    print("  ✅ Works with PyUSB for direct USB communication")
    print()
    
    # Step 1: Install PyUSB
    if not install_pyusb_if_needed():
        return False
        
    # Step 2: Launch Zadig for driver replacement
    if not launch_zadig_gui():
        return False
        
    # Step 3: Test communication
    success = test_driver_free_communication()
    
    print("\n" + "="*60)
    if success:
        print("🎉 DRIVER-FREE SOLUTION SUCCESSFUL!")
        print("✅ Generic USB driver installed")
        print("✅ PyUSB communication working")
        print("✅ Pump control ready")
        print()
        print("Your pump is now controlled via direct USB without signed drivers!")
    else:
        print("❌ DRIVER-FREE SOLUTION FAILED")
        print("💡 Try different driver in Zadig (libusb-win32 or libusbK)")
        print("💡 Or use the certificate-based solution instead")
        
    return success

if __name__ == "__main__":
    success = main()
    print(f"\nPress any key to exit...")
    try:
        input()
    except:
        pass
    sys.exit(0 if success else 1)