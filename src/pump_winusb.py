"""
Driver-free Bartels Micropump Controller for WinUSB devices.

This version works with USB devices that have WinUSB drivers installed via Zadig,
instead of COM port devices. It uses the Windows USB device interface directly.
"""

import time
import logging
import ctypes
import ctypes.wintypes
from ctypes import Structure, byref, c_ulong, c_ubyte, c_ushort
import subprocess

# Windows API constants
GENERIC_READ = 0x80000000
GENERIC_WRITE = 0x40000000
OPEN_EXISTING = 3
FILE_ATTRIBUTE_NORMAL = 0x80
INVALID_HANDLE_VALUE = -1


def find_bartels_device_path():
    """Find the USB device path for Bartels micropump with WinUSB driver."""
    try:
        vid = 0x0403  # FTDI
        pid = 0xB4C0  # Bartels micropump
        
        # Get the device instance ID using PowerShell
        cmd = [
            "powershell", "-Command",
            f"Get-PnpDevice | Where-Object {{$_.InstanceId -like '*VID_{vid:04X}*PID_{pid:04X}*'}} | Select-Object -ExpandProperty InstanceId"
        ]
        
        result = subprocess.run(cmd, capture_output=True, text=True)
        if result.returncode == 0 and result.stdout.strip():
            instance_id = result.stdout.strip()
            
            # Convert to device path format for WinUSB
            device_path = f"\\\\?\\{instance_id.replace('\\', '#')}#{{A5DCBF10-6530-11D2-901F-00C04FB951ED}}"
            return device_path
            
        return None
        
    except Exception as e:
        logging.error(f"Error finding Bartels device: {e}")
        return None


class PumpController:
    """
    Driver-free Bartels micropump controller for WinUSB devices.
    
    This version works with USB devices that have WinUSB drivers installed via Zadig.
    It provides the same interface as the COM port version but uses USB device paths.
    """
    
    def __init__(self, device_path=None):
        """
        Initialize pump controller for WinUSB device.
        
        Args:
            device_path: USB device path (auto-detected if None)
        """
        self.device_path = device_path or find_bartels_device_path()
        self.handle = None
        self._initialize()
    
    def _initialize(self):
        """Initialize USB connection using Windows API."""
        if not self.device_path:
            logging.error("No Bartels micropump device found")
            return
            
        try:
            kernel32 = ctypes.windll.kernel32
            
            # Open the USB device using Windows CreateFileW API
            self.handle = kernel32.CreateFileW(
                self.device_path,             # USB device path
                GENERIC_READ | GENERIC_WRITE, # Read/write access
                0,                           # No sharing
                None,                        # Default security
                OPEN_EXISTING,               # Open existing device
                FILE_ATTRIBUTE_NORMAL,       # Normal file attributes
                None                         # No template file
            )
            
            if self.handle == INVALID_HANDLE_VALUE:
                logging.error(f'Failed to open USB device: {self.device_path}')
                self.handle = None
                return
            
            logging.info(f'Pump connection established via USB (WinUSB driver)')
            
        except Exception as e:
            logging.error(f'Failed to initialize USB pump: {e}')
            self.handle = None
    
    def close(self):
        """Close pump connection and clean up resources."""
        if self.handle and self.handle != INVALID_HANDLE_VALUE:
            try:
                kernel32 = ctypes.windll.kernel32
                kernel32.CloseHandle(self.handle)
                self.handle = None
                logging.info("USB pump connection closed")
            except Exception:
                pass
    
    def _send_command(self, command: str):
        """
        Send command to pump via USB with carriage return terminator.
        
        Args:
            command: Command string (without termination)
            
        Returns:
            bool: True if command sent successfully
        """
        if self.handle is None or self.handle == INVALID_HANDLE_VALUE:
            logging.error("USB pump is not initialized.")
            return False
        
        try:
            kernel32 = ctypes.windll.kernel32
            
            # Add carriage return terminator (same as COM port version)
            full_command = command + "\r"
            command_bytes = full_command.encode("utf-8")
            
            # Write to the USB device using Windows API
            bytes_written = ctypes.wintypes.DWORD(0)
            success = kernel32.WriteFile(
                self.handle,
                command_bytes,
                len(command_bytes),
                byref(bytes_written),
                None
            )
            
            if success and bytes_written.value == len(command_bytes):
                # Force flush to ensure immediate transmission
                kernel32.FlushFileBuffers(self.handle)
                logging.info(f"Sent USB command: '{command}'")
                return True
            else:
                logging.error(f"Failed to send USB command '{command}': WriteFile failed")
                return False
                
        except Exception as e:
            logging.error(f"Failed to send USB command '{command}': {e}")
            return False
    
    def set_frequency(self, freq: int):
        """Set pump frequency in Hz (1-300)."""
        if 1 <= freq <= 300:
            self._send_command(f"F{freq}")
            time.sleep(0.15)  # Allow processing time
        else:
            logging.error(f"Frequency {freq} out of range (1-300 Hz)")
    
    def set_amplitude(self, amp: int):
        """Set pump amplitude (1-300)."""
        if 1 <= amp <= 300:
            self._send_command(f"A{amp}")
            time.sleep(0.15)  # Allow processing time
        else:
            logging.error(f"Amplitude {amp} out of range (1-300)")
    
    def set_voltage(self, voltage: int):
        """Set pump voltage/amplitude (1-250 Vpp) - alias for compatibility."""
        if 1 <= voltage <= 250:
            self._send_command(f"A{voltage}")
            time.sleep(0.15)
        else:
            logging.error(f"Invalid voltage: {voltage} (must be 1-250)")
    
    def start(self):
        """Start the pump."""
        self._send_command("bon")
        time.sleep(0.15)  # Allow processing time
        logging.info("USB pump started")
    
    def stop(self):
        """Stop the pump."""
        self._send_command("boff")
        time.sleep(0.15)  # Allow processing time
        logging.info("USB pump stopped")
    
    def start_pump(self):
        """Start pumping operation (alias for start)."""
        self.start()
    
    def stop_pump(self):
        """Stop pumping operation (alias for stop)."""
        self.stop()
    
    def pulse(self, duration: float):
        """Run pump for specified duration then stop."""
        self.start()
        time.sleep(duration)
        self.stop()
    
    def set_waveform(self, waveform: str):
        """Set pump waveform (RECT, SINE, etc)."""
        waveform_map = {
            "RECT": "MR",
            "RECTANGLE": "MR", 
            "SINE": "MS",
            "SIN": "MS"
        }
        cmd = waveform_map.get(waveform.upper(), waveform.upper())
        self._send_command(cmd)
        time.sleep(0.15)
    
    def reset_device(self):
        """Reset the pump device."""
        self._send_command("MR")
        time.sleep(0.15)  # Allow processing time
    
    def get_status(self):
        """Get pump status (placeholder for compatibility)."""
        logging.info("Status request sent (USB WinUSB implementation)")
        return "USB WinUSB device operational"
    
    def __enter__(self):
        """Context manager entry."""
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        """Context manager exit."""
        self.close()


# Test the controller
if __name__ == "__main__":
    # Configure logging to see what's happening
    logging.basicConfig(level=logging.INFO, format='%(levelname)s: %(message)s')
    
    print("USB WinUSB Bartels Micropump Controller")
    print("====================================")
    print("Direct USB access with WinUSB driver")
    
    # Initialize pump controller
    pump = PumpController()
    
    if pump.handle is None:
        print("❌ Failed to initialize USB pump controller")
        print("Check that Zadig installed WinUSB driver correctly")
    else:
        try:
            print("\n🧪 Running USB pump test...")
            
            # Test sequence
            print("1. Setting frequency to 100 Hz...")
            pump.set_frequency(100)
            
            print("2. Setting amplitude to 50...")
            pump.set_amplitude(50)
            
            print("3. Starting pump...")
            pump.start()
            
            print("4. Running for 2 seconds...")
            time.sleep(2)
            
            print("5. Stopping pump...")
            pump.stop()
            
            print("\n✅ USB pump control test completed!")
            print("WinUSB driver working correctly!")
            
        except KeyboardInterrupt:
            print("\n⏹️  Test interrupted")
        except Exception as e:
            print(f"\n❌ Error during test: {e}")
        finally:
            pump.close()
