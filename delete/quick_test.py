#!/usr/bin/env python3
"""
Quick libusb test with timeouts to avoid hanging.
"""

import usb.core
import usb.util
import time

def quick_libusb_test():
    """Quick test with short timeouts to avoid hanging."""
    print("=== Quick libusb Test (with timeouts) ===")
    
    try:
        # Find device with short timeout
        print("1. Looking for device...")
        device = usb.core.find(idVendor=0x0403, idProduct=0xb4c0)
        
        if not device:
            print("✗ Device not found")
            return False
        
        print(f"✓ Found device: VID:{hex(device.idVendor)} PID:{hex(device.idProduct)}")
        
        # Try configuration with timeout
        print("2. Setting configuration...")
        try:
            device.set_configuration()
            print("✓ Configuration set")
        except Exception as e:
            print(f"⚠ Configuration failed: {e}")
        
        # Quick endpoint test
        print("3. Testing one simple command...")
        try:
            # Send just one command with short timeout
            data = b"F100\r"
            result = device.write(0x02, data, timeout=500)  # 500ms timeout
            print(f"✓ Sent {result} bytes")
            
            # Try to read with very short timeout
            try:
                response = device.read(0x81, 64, timeout=500)  # 500ms timeout
                print(f"✓ Got response: {bytes(response).hex()}")
            except usb.core.USBTimeoutError:
                print("⚠ No response (timeout)")
            except Exception as e:
                print(f"⚠ Read error: {e}")
                
        except Exception as e:
            print(f"✗ Write failed: {e}")
            return False
        
        print("✓ Basic communication working")
        return True
        
    except Exception as e:
        print(f"✗ Test failed: {e}")
        return False

if __name__ == "__main__":
    quick_libusb_test()
    print("\nTest completed (no hanging)")
