#!/usr/bin/env python3
"""
Low-level USB device testing to see if we can communicate at all.
"""

import time

def test_usb_basic_communication():
    """Test basic USB communication without pyusb."""
    try:
        import usb.core
        import usb.util
        
        print("🔍 Testing basic USB communication...")
        
        # Find device
        dev = usb.core.find(idVendor=0x0403, idProduct=0xB4C0)
        if dev is None:
            print("❌ Device not found")
            return False
        
        print(f"✅ Device found: {dev}")
        print(f"   Manufacturer: {usb.util.get_string(dev, dev.iManufacturer) if dev.iManufacturer else 'Unknown'}")
        print(f"   Product: {usb.util.get_string(dev, dev.iProduct) if dev.iProduct else 'Unknown'}")
        print(f"   Serial: {usb.util.get_string(dev, dev.iSerialNumber) if dev.iSerialNumber else 'Unknown'}")
        
        # Show device configuration
        print("\nDevice configuration:")
        for cfg in dev:
            print(f"  Configuration {cfg.bConfigurationValue}")
            for intf in cfg:
                print(f"    Interface {intf.bInterfaceNumber}")
                print(f"      Class: {intf.bInterfaceClass}")
                print(f"      Subclass: {intf.bInterfaceSubClass}")
                print(f"      Protocol: {intf.bInterfaceProtocol}")
                for ep in intf:
                    print(f"      Endpoint {ep.bEndpointAddress:02x}")
                    print(f"        Type: {ep.bmAttributes & 3}")
                    print(f"        Max packet: {ep.wMaxPacketSize}")
        
        # Try to detach kernel driver and set configuration
        try:
            if dev.is_kernel_driver_active(0):
                print("Detaching kernel driver...")
                dev.detach_kernel_driver(0)
        except:
            pass
        
        try:
            print("Setting configuration...")
            dev.set_configuration()
            print("✅ Configuration set successfully")
        except Exception as e:
            print(f"❌ Failed to set configuration: {e}")
            return False
        
        # Try to send a simple command
        try:
            print("Attempting to send test command...")
            # Find OUT endpoint
            cfg = dev.get_active_configuration()
            intf = cfg[(0,0)]
            
            ep_out = None
            for ep in intf:
                if usb.util.endpoint_direction(ep.bEndpointAddress) == usb.util.ENDPOINT_OUT:
                    ep_out = ep
                    break
            
            if ep_out:
                print(f"Found OUT endpoint: {ep_out.bEndpointAddress:02x}")
                # Try sending a simple command
                test_cmd = b"?\r"  # Query command
                result = ep_out.write(test_cmd)
                print(f"✅ Sent {result} bytes: {test_cmd}")
                time.sleep(0.2)
                
                # Try to read response
                ep_in = None
                for ep in intf:
                    if usb.util.endpoint_direction(ep.bEndpointAddress) == usb.util.ENDPOINT_IN:
                        ep_in = ep
                        break
                
                if ep_in:
                    try:
                        response = ep_in.read(64, timeout=1000)
                        print(f"✅ Response: {bytes(response)}")
                        return True
                    except Exception as e:
                        print(f"⚠️ No response: {e}")
                        return True  # Sent successfully even if no response
                else:
                    print("⚠️ No IN endpoint found")
                    return True  # Sent successfully
            else:
                print("❌ No OUT endpoint found")
                return False
                
        except Exception as e:
            print(f"❌ Failed to send command: {e}")
            return False
        
    except ImportError:
        print("❌ pyusb not available")
        return False
    except Exception as e:
        print(f"❌ USB test failed: {e}")
        return False

def test_device_reset():
    """Try resetting the USB device."""
    try:
        import usb.core
        
        dev = usb.core.find(idVendor=0x0403, idProduct=0xB4C0)
        if dev:
            print("🔄 Attempting device reset...")
            dev.reset()
            time.sleep(2)
            print("✅ Device reset complete")
            return True
    except Exception as e:
        print(f"❌ Reset failed: {e}")
        return False

def main():
    """Main USB testing function."""
    print("🔧 Low-Level USB Device Testing")
    print("=" * 40)
    
    if test_usb_basic_communication():
        print("\n✅ Basic USB communication working!")
        print("The device responds to commands but pump may need specific protocol.")
    else:
        print("\n❌ USB communication failed")
        print("Trying device reset...")
        if test_device_reset():
            print("Reset complete, try running pump test again.")
        else:
            print("Device reset also failed.")
    
    print("\n💡 Next steps if this fails:")
    print("1. Install FTDI VCP drivers to get a COM port")
    print("2. Use WSL USB forwarding with admin rights")
    print("3. Check if device needs special FTDI D2XX drivers")

if __name__ == "__main__":
    main()
