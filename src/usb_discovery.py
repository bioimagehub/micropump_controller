"""
USB Device Discovery for Driver-Free Operation

This module provides functions to find USB devices by VID/PID for driver-free
operation after WinUSB driver installation via Zadig.
"""

import ctypes
import ctypes.wintypes
from ctypes import Structure, POINTER, byref, c_char, c_wchar
import re


# Windows API constants
DIGCF_PRESENT = 0x00000002
DIGCF_DEVICEINTERFACE = 0x00000010
GENERIC_READ = 0x80000000
GENERIC_WRITE = 0x40000000
OPEN_EXISTING = 3
FILE_ATTRIBUTE_NORMAL = 0x80
INVALID_HANDLE_VALUE = -1

# Simplified approach - no complex structures needed


def find_usb_device_path(vid, pid):
    """
    Find USB device path for direct Windows API access after WinUSB installation.
    
    Args:
        vid (int): Vendor ID (e.g., 0x0403)
        pid (int): Product ID (e.g., 0xB4C0)
        
    Returns:
        str: Device path for CreateFileW() or None if not found
    """
    try:
        import subprocess
        
        # Get the device instance ID using PowerShell
        cmd = [
            "powershell", "-Command",
            f"Get-PnpDevice | Where-Object {{$_.InstanceId -like '*VID_{vid:04X}*PID_{pid:04X}*'}} | Select-Object -ExpandProperty InstanceId"
        ]
        
        result = subprocess.run(cmd, capture_output=True, text=True)
        if result.returncode == 0 and result.stdout.strip():
            instance_id = result.stdout.strip()
            print(f"Found device instance ID: {instance_id}")
            
            # Convert instance ID to device path format
            # Format: \\?\USB#VID_0403&PID_B4C0#07-22-067#{GUID}
            device_path = f"\\\\?\\{instance_id.replace('\\', '#')}#{{A5DCBF10-6530-11D2-901F-00C04FB951ED}}"
            
            # Test the path
            kernel32 = ctypes.windll.kernel32
            handle = kernel32.CreateFileW(
                device_path,
                GENERIC_READ | GENERIC_WRITE,
                0, None, OPEN_EXISTING,
                FILE_ATTRIBUTE_NORMAL, None
            )
            
            if handle != INVALID_HANDLE_VALUE:
                kernel32.CloseHandle(handle)
                print(f"✅ Successfully opened device: {device_path}")
                return device_path
            else:
                print(f"❌ Could not open device path: {device_path}")
                
                # Try simpler formats
                simple_paths = [
                    f"\\\\?\\{instance_id}",
                    f"\\\\.\\{instance_id}",
                ]
                
                for path in simple_paths:
                    handle = kernel32.CreateFileW(
                        path,
                        GENERIC_READ | GENERIC_WRITE,
                        0, None, OPEN_EXISTING,
                        FILE_ATTRIBUTE_NORMAL, None
                    )
                    
                    if handle != INVALID_HANDLE_VALUE:
                        kernel32.CloseHandle(handle)
                        print(f"✅ Alternative path works: {path}")
                        return path
                
        return None
        
    except Exception as e:
        print(f"Error finding USB device: {e}")
        return None


def find_bartels_pump_device():
    """
    Find Bartels micropump USB device path for driver-free operation.
    
    Returns:
        str: Device path or None if not found
    """
    # Bartels micropump VID/PID
    vid = 0x0403  # FTDI
    pid = 0xB4C0  # Bartels micropump
    
    return find_usb_device_path(vid, pid)


def get_usb_devices_info():
    """
    Get information about USB devices using PowerShell/WMI.
    
    Returns:
        list: List of USB device information
    """
    try:
        import subprocess
        
        # Use PowerShell to get USB device info
        cmd = [
            "powershell", "-Command",
            "Get-PnpDevice | Where-Object {$_.InstanceId -like '*VID_0403*PID_B4C0*'} | Select-Object FriendlyName, Status, InstanceId | Format-List"
        ]
        
        result = subprocess.run(cmd, capture_output=True, text=True)
        return result.stdout
        
    except Exception as e:
        print(f"Error getting USB info: {e}")
        return None


def test_usb_device_access():
    """Test USB device access for troubleshooting."""
    print("🔍 Testing USB Device Access...")
    
    # Get device info
    info = get_usb_devices_info()
    if info:
        print("USB Device Info:")
        print(info)
    else:
        print("❌ Could not retrieve USB device info")
    
    # Try to find device path
    device_path = find_bartels_pump_device()
    if device_path:
        print(f"✅ Found device path: {device_path}")
    else:
        print("❌ Could not find device path")
    
    return device_path


if __name__ == "__main__":
    test_usb_device_access()
