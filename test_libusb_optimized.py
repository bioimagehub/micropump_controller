#!/usr/bin/env python3
"""
Optimized libusb test for Bartels micropump.
This should work better than the CDC driver.
"""

import usb.core
import usb.util
import time

def test_libusb_connection():
    """Test libusb connection with optimized approach."""
    print("=== libusb Driver Test ===")
    
    try:
        # Find device
        device = usb.core.find(idVendor=0x0403, idProduct=0xb4c0)
        
        if device is None:
            print("✗ Device not found")
            return False
        
        print(f"✓ Found device: VID:{hex(device.idVendor)} PID:{hex(device.idProduct)}")
        
        # Try to detach kernel driver (Linux/Mac) - will fail on Windows, that's OK
        try:
            if device.is_kernel_driver_active(0):
                device.detach_kernel_driver(0)
        except:
            pass  # Expected on Windows
        
        # Try to claim the interface
        try:
            usb.util.claim_interface(device, 0)
            print("✓ Interface claimed successfully")
        except Exception as e:
            print(f"Interface claim warning: {e}")
        
        # Find endpoints without setting configuration
        try:
            # Look for endpoints in current configuration
            for cfg in device:
                for intf in cfg:
                    for ep in intf:
                        direction = usb.util.endpoint_direction(ep.bEndpointAddress)
                        if direction == usb.util.ENDPOINT_OUT:
                            ep_out = ep.bEndpointAddress
                            print(f"✓ Found OUT endpoint: 0x{ep_out:02x}")
                        elif direction == usb.util.ENDPOINT_IN:
                            ep_in = ep.bEndpointAddress
                            print(f"✓ Found IN endpoint: 0x{ep_in:02x}")
            
            return device, ep_out, ep_in
            
        except Exception as e:
            print(f"Endpoint discovery failed: {e}")
            return False
        
    except Exception as e:
        print(f"libusb test failed: {e}")
        return False

def test_pump_communication(device, ep_out, ep_in):
    """Test pump communication with known good endpoints."""
    print("\n=== Testing Pump Communication ===")
    
    # Test commands from pybartelslabtronix
    commands = [
        ("", "Get Status"),
        ("F100", "Set Frequency 100Hz"),
        ("A100", "Set Amplitude 100Vpp"),
        ("MR", "Set Rectangular Wave"),
        ("bon", "Turn Pump ON"),
        ("boff", "Turn Pump OFF"),
    ]
    
    for command, description in commands:
        try:
            print(f"\n{description}: '{command}'")
            
            # Format command like pybartelslabtronix
            full_command = command + "\r"
            data = full_command.encode('utf-8')
            
            # Send command
            bytes_written = device.write(ep_out, data, 2000)
            print(f"  Sent {bytes_written} bytes")
            
            # Try to read response
            time.sleep(0.2)
            try:
                response = device.read(ep_in, 64, 1000)
                if response:
                    text = bytes(response).decode('utf-8', errors='ignore')
                    print(f"  Response: {repr(text)}")
                else:
                    print("  No response")
            except usb.core.USBTimeoutError:
                print("  No response (timeout)")
            except Exception as e:
                print(f"  Read error: {e}")
            
            time.sleep(0.5)  # Wait between commands
            
        except Exception as e:
            print(f"  Command failed: {e}")

def main():
    """Main test function."""
    print("=== Bartels Micropump libusb Test ===")
    
    result = test_libusb_connection()
    
    if result and len(result) == 3:
        device, ep_out, ep_in = result
        print("\n✓ libusb connection successful!")
        
        # Test pump communication
        test_pump_communication(device, ep_out, ep_in)
        
        # Cleanup
        try:
            usb.util.release_interface(device, 0)
            usb.util.dispose_resources(device)
        except:
            pass
        
        print("\n✓ Test completed!")
        
    else:
        print("\n✗ libusb connection failed")
        print("Make sure you installed libusb driver in Zadig")

if __name__ == "__main__":
    main()
