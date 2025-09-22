#!/usr/bin/env python3
"""
Windows-native Bartels micropump controller.
Attempts multiple communication methods:
1. Serial via COM port (if drivers installed)
2. Direct USB communication via pyusb
3. WinUSB/libusb approach

VID: 0x0403 (FTDI)
PID: 0xB4C0 (Bartels custom)
"""

import sys
import time
import serial
import serial.tools.list_ports
from typing import Optional, List

# Optional USB imports
try:
    import usb.core  # type: ignore
    import usb.util  # type: ignore
    HAS_USB = True
except ImportError:
    HAS_USB = False
    usb = None  # type: ignore
    print("Note: pyusb not available. Install with: pip install pyusb")

BARTELS_VID = 0x0403
BARTELS_PID = 0xB4C0
BAUDRATE = 9600
TIMEOUT = 1.0
CMD_DELAY = 0.2  # 200ms delay between commands as per manual


class BartelsPumpController:
    def __init__(self):
        self.device = None
        self.interface = None
        self.connection_type = None
        
    def find_com_port(self) -> Optional[str]:
        """Find Bartels pump on COM ports."""
        ports = serial.tools.list_ports.comports()
        for port in ports:
            if (port.vid == BARTELS_VID and port.pid == BARTELS_PID):
                print(f"Found Bartels pump on {port.device}")
                return port.device
        return None
    
    def find_usb_device(self):
        """Find Bartels pump via USB direct access."""
        if not HAS_USB:
            return None
            
        try:
            dev = usb.core.find(idVendor=BARTELS_VID, idProduct=BARTELS_PID)
            if dev is None:
                return None
            print(f"Found USB device: VID={dev.idVendor:04x}, PID={dev.idProduct:04x}")
            return dev
        except Exception as e:
            print(f"USB search failed: {e}")
            return None
    
    def connect_serial(self, port: str) -> bool:
        """Connect via serial/COM port."""
        try:
            self.device = serial.Serial(
                port=port,
                baudrate=BAUDRATE,
                timeout=TIMEOUT,
                bytesize=8,
                parity='N',
                stopbits=1
            )
            self.connection_type = "serial"
            print(f"Connected via serial on {port}")
            return True
        except Exception as e:
            print(f"Serial connection failed: {e}")
            return False
    
    def connect_usb(self, dev) -> bool:
        """Connect via direct USB access."""
        if not dev:
            return False
            
        try:
            # Try to detach kernel driver if active
            try:
                if dev.is_kernel_driver_active(0):
                    dev.detach_kernel_driver(0)
            except:
                pass  # Windows doesn't have kernel drivers like Linux
            
            # Set configuration
            dev.set_configuration()
            
            # Get the first interface
            cfg = dev.get_active_configuration()
            intf = cfg[(0,0)]
            
            # Find endpoints
            ep_out = usb.util.find_descriptor(
                intf,
                custom_match=lambda e: usb.util.endpoint_direction(e.bEndpointAddress) == usb.util.ENDPOINT_OUT
            )
            ep_in = usb.util.find_descriptor(
                intf,
                custom_match=lambda e: usb.util.endpoint_direction(e.bEndpointAddress) == usb.util.ENDPOINT_IN
            )
            
            if ep_out is None or ep_in is None:
                print("Could not find USB endpoints")
                return False
            
            self.device = dev
            self.ep_out = ep_out
            self.ep_in = ep_in
            self.connection_type = "usb"
            print("Connected via direct USB")
            return True
            
        except Exception as e:
            print(f"USB connection failed: {e}")
            return False
    
    def connect(self) -> bool:
        """Try all connection methods."""
        # Method 1: Serial/COM port
        com_port = self.find_com_port()
        if com_port and self.connect_serial(com_port):
            return True
        
        # Method 2: Direct USB
        if HAS_USB:
            usb_dev = self.find_usb_device()
            if usb_dev and self.connect_usb(usb_dev):
                return True
        
        print("Failed to connect via any method")
        return False
    
    def send_command(self, cmd: str) -> bool:
        """Send command to pump with proper timing and response handling."""
        if not self.device:
            print("Not connected")
            return False
        
        try:
            # Ensure command ends with carriage return as per Bartels protocol
            cmd_bytes = (cmd + '\r').encode('ascii')
            
            if self.connection_type == "serial":
                self.device.write(cmd_bytes)
                self.device.flush()
                
            elif self.connection_type == "usb":
                self.ep_out.write(cmd_bytes)
            
            print(f"Sent: {cmd}")
            
            # Wait for response (200ms as per manual)
            time.sleep(CMD_DELAY)
            
            # Try to read response
            try:
                if self.connection_type == "serial":
                    response = self.device.read(100)
                    if response:
                        print(f"Response: {response.decode('ascii', errors='ignore').strip()}")
            except Exception:
                pass  # No response expected for some commands
            
            return True
            
        except Exception as e:
            print(f"Send failed: {e}")
            return False
    
    def send_pulse(self, duration_seconds: int = 10) -> bool:
        """Send a pulse command for specified duration with correct stop command."""
        commands = [
            "F100",    # 100 Hz frequency
            "A150",    # 150 Vpp amplitude  
            "MR",      # Rectangular waveform
            "bon"      # Turn on
        ]
        
        print(f"Starting {duration_seconds}s pulse...")
        
        # Send setup commands with proper delays
        for cmd in commands:
            if not self.send_command(cmd):
                return False
            # Additional delay after each command for pump to process
            time.sleep(CMD_DELAY)
        
        # Wait for pulse duration
        time.sleep(duration_seconds)
        
        # Turn off using correct command
        if not self.send_command("boff"):  # Correct stop command
            print("Warning: failed to turn off pump")
            return False
        
        print("Pulse complete")
        return True
    
    def disconnect(self):
        """Close connection."""
        if self.device:
            try:
                if self.connection_type == "serial":
                    self.device.close()
                elif self.connection_type == "usb":
                    usb.util.dispose_resources(self.device)
            except:
                pass
            self.device = None
            self.connection_type = None


def list_all_devices():
    """List all available devices for debugging."""
    print("\n=== Available Serial Ports ===")
    ports = serial.tools.list_ports.comports()
    for port in ports:
        print(f"{port.device}: {port.description} (VID={port.vid:04x if port.vid else 'None'}, PID={port.pid:04x if port.pid else 'None'})")
    
    if HAS_USB:
        print("\n=== USB Devices ===")
        try:
            devices = usb.core.find(find_all=True)
            for dev in devices:
                print(f"VID={dev.idVendor:04x}, PID={dev.idProduct:04x}")
        except Exception as e:
            print(f"USB enumeration failed: {e}")


def main():
    print("Bartels Micropump Controller - Windows Native")
    print("=" * 50)
    
    # List devices for debugging
    list_all_devices()
    
    # Try to connect and send pulse
    pump = BartelsPumpController()
    
    try:
        if pump.connect():
            print("\nConnection successful!")
            pump.send_pulse(duration_seconds=10)
        else:
            print("\nConnection failed. Trying manual interventions...")
            
            # Manual driver suggestions
            print("\nTo resolve connection issues:")
            print("1. Install Bartels FTDI drivers (run as admin):")
            print("   hardware\\drivers\\install_unsigned_bartels_drivers.bat")
            print("2. Or install generic FTDI drivers from ftdichip.com")
            print("3. Or use Windows Device Manager to update driver")
            
    finally:
        pump.disconnect()


if __name__ == "__main__":
    main()
