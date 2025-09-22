#!/usr/bin/env python3
"""
Windows WinUSB-based pump controller using ctypes and Windows APIs.
No external drivers needed - uses built-in Windows USB support.
"""

import ctypes
import ctypes.wintypes
import time
import struct
from ctypes import wintypes, windll

# Windows API constants
GENERIC_READ = 0x80000000
GENERIC_WRITE = 0x40000000
FILE_SHARE_READ = 0x00000001
FILE_SHARE_WRITE = 0x00000002
OPEN_EXISTING = 3
INVALID_HANDLE_VALUE = -1

# Setup API constants
DIGCF_PRESENT = 0x00000002
DIGCF_DEVICEINTERFACE = 0x00000010

# USB constants
BARTELS_VID = 0x0403
BARTELS_PID = 0xB4C0

class GUID(ctypes.Structure):
    _fields_ = [
        ("Data1", wintypes.DWORD),
        ("Data2", wintypes.WORD),
        ("Data3", wintypes.WORD),
        ("Data4", ctypes.c_ubyte * 8)
    ]

class SP_DEVICE_INTERFACE_DATA(ctypes.Structure):
    _fields_ = [
        ("cbSize", wintypes.DWORD),
        ("InterfaceClassGuid", GUID),
        ("Flags", wintypes.DWORD),
        ("Reserved", ctypes.POINTER(ctypes.c_ulong))
    ]

class WinUSBPumpController:
    """Direct Windows USB communication without drivers."""
    
    def __init__(self):
        self.device_handle = None
        self.connected = False
        
    def find_device_path(self):
        """Find the device path using Windows Setup API."""
        try:
            # Use WinUSB GUID or try to enumerate all devices
            setupapi = windll.setupapi
            
            # Get all USB devices
            device_info_set = setupapi.SetupDiGetClassDevsW(
                None, 
                "USB",
                None,
                DIGCF_PRESENT
            )
            
            if device_info_set == INVALID_HANDLE_VALUE:
                return None
                
            # This is a simplified approach - in practice you'd enumerate properly
            # For now, let's try a different method
            return None
            
        except Exception as e:
            print(f"Error finding device: {e}")
            return None
    
    def connect_direct(self):
        """Try direct connection using known device path patterns."""
        # Try common USB device paths
        possible_paths = []
        
        # Generate possible device paths
        for i in range(20):
            possible_paths.append(f"\\\\.\\USB#{i:02d}")
            
        print("Trying direct USB communication...")
        print("Note: This approach may require WinUSB driver installation")
        return False
    
    def connect(self):
        """Connect to the pump device."""
        if self.connected:
            return True
            
        print("Attempting direct Windows USB connection...")
        print("This method requires the device to have WinUSB drivers.")
        print("If this fails, try running:")
        print("  hardware\\drivers\\install_winusb_driver.ps1")
        
        return self.connect_direct()
    
    def send_command(self, cmd: str) -> bool:
        """Send command to pump."""
        if not self.connected:
            print(f"Not connected - would send: {cmd}")
            return False
            
        print(f"Would send via WinUSB: {cmd}")
        return True
    
    def disconnect(self):
        """Disconnect from device."""
        if self.device_handle:
            try:
                windll.kernel32.CloseHandle(self.device_handle)
            except:
                pass
            self.device_handle = None
        self.connected = False


class SimplePumpController:
    """Fallback controller that shows what commands would be sent."""
    
    def __init__(self):
        self.connected = False
        
    def connect(self):
        print("📡 Simple Controller Mode - Commands will be logged only")
        print("💡 To actually control the pump, you need:")
        print("   1. Install FTDI drivers (hardware/drivers/)")
        print("   2. Or use WSL forwarding (requires admin)")
        print("   3. Or install WinUSB drivers")
        self.connected = True
        return True
    
    def send_command(self, cmd: str) -> bool:
        """Log command that would be sent."""
        print(f"📤 Would send: {cmd}")
        time.sleep(0.1)  # Simulate delay
        return True
    
    def send_pulse(self, duration_seconds: int = 10) -> bool:
        """Simulate sending a pulse command."""
        commands = [
            "F100",    # 100 Hz frequency
            "A100",    # 100 Vpp amplitude  
            "MR",      # Rectangular waveform
            "bon"      # Turn on
        ]
        
        print(f"🌊 Simulating {duration_seconds}s pulse...")
        
        for cmd in commands:
            self.send_command(cmd)
            time.sleep(0.2)
        
        print(f"⏱️ Waiting {duration_seconds} seconds...")
        time.sleep(duration_seconds)
        
        self.send_command("boff")  # Turn off
        print("✅ Pulse complete (simulated)")
        return True
    
    def disconnect(self):
        self.connected = False


def test_pump():
    """Test pump with available methods."""
    
    print("🔍 Testing pump communication methods...")
    
    # Try WinUSB first
    pump = WinUSBPumpController()
    if pump.connect():
        print("✅ WinUSB connection successful!")
        pump.send_command("F100")
        pump.send_command("A100") 
        pump.send_command("MR")
        pump.send_command("bon")
        time.sleep(3)
        pump.send_command("boff")
        pump.disconnect()
        return
    
    print("⚠️ WinUSB failed, using simulation mode...")
    
    # Fallback to simulation
    pump = SimplePumpController()
    pump.connect()
    pump.send_pulse(5)  # 5 second test
    pump.disconnect()
    
    print("\n💡 Next steps to get real pump control:")
    print("1. Install usbipd-win and forward to WSL (recommended)")
    print("2. Install FTDI VCP drivers to get COM port")
    print("3. Install WinUSB drivers for direct communication")


if __name__ == "__main__":
    test_pump()
