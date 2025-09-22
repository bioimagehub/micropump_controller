"""Drop-in replacement for pump.py using driver-free Windows API implementation.

This module provides the same interface as the original pump.py but uses pure Windows API
calls with XON/XOFF flow control instead of relying on proprietary FTDI drivers.

BREAKTHROUGH: Successfully achieved September 22, 2025
"""

import time
import logging
import ctypes
import ctypes.wintypes
from ctypes import Structure, byref, c_ulong, c_ubyte, c_ushort

# Windows API constants
GENERIC_READ = 0x80000000
GENERIC_WRITE = 0x40000000
OPEN_EXISTING = 3
FILE_ATTRIBUTE_NORMAL = 0x80

# DCB (Device Control Block) structure for serial port configuration
class DCB(Structure):
    """Complete DCB structure matching Windows API documentation."""
    _fields_ = [
        ("DCBlength", c_ulong),
        ("BaudRate", c_ulong),
        ("fBinary", c_ulong, 1),
        ("fParity", c_ulong, 1),
        ("fOutxCtsFlow", c_ulong, 1),
        ("fOutxDsrFlow", c_ulong, 1),
        ("fDtrControl", c_ulong, 2),
        ("fDsrSensitivity", c_ulong, 1),
        ("fTXContinueOnXoff", c_ulong, 1),
        ("fOutX", c_ulong, 1),          # XON/XOFF output flow control - CRITICAL!
        ("fInX", c_ulong, 1),           # XON/XOFF input flow control - CRITICAL!
        ("fErrorChar", c_ulong, 1),
        ("fNull", c_ulong, 1),
        ("fRtsControl", c_ulong, 2),
        ("fAbortOnError", c_ulong, 1),
        ("fDummy2", c_ulong, 17),
        ("wReserved", c_ushort),
        ("XonLim", c_ushort),
        ("XoffLim", c_ushort),
        ("ByteSize", c_ubyte),
        ("Parity", c_ubyte),
        ("StopBits", c_ubyte),
        ("XonChar", c_ubyte),           # XON character (0x11) - CRITICAL!
        ("XoffChar", c_ubyte),          # XOFF character (0x13) - CRITICAL!
        ("ErrorChar", c_ubyte),
        ("EofChar", c_ubyte),
        ("EvtChar", c_ubyte),
        ("wReserved1", c_ushort),
    ]


class PumpController:
    """
    Driver-free Bartels micropump controller - DROP-IN REPLACEMENT for pump.py
    
    This class provides the exact same interface as the original PumpController
    but uses pure Windows API calls instead of pySerial and FTDI drivers.
    
    CRITICAL SUCCESS FACTOR: XON/XOFF flow control configuration in DCB structure.
    
    Usage:
        # Exactly the same as original pump.py
        pump = PumpController(port="COM4", baudrate=9600)
        pump.set_frequency(100)
        pump.set_amplitude(100)
        pump.start_pump()
        time.sleep(3)
        pump.stop_pump()
        pump.close()
    """
    
    def __init__(self, port: str, baudrate: int = 9600):
        """
        Initialize pump controller with driver-free Windows API.
        
        Args:
            port: COM port string (e.g., "COM4")
            baudrate: Communication speed (default 9600)
        """
        self.port = port
        self.baudrate = baudrate
        self.handle = None
        self._initialize()
    
    def _initialize(self):
        """Initialize serial connection using Windows API with XON/XOFF flow control."""
        try:
            kernel32 = ctypes.windll.kernel32
            
            # Open the serial port using Windows CreateFileW API
            self.handle = kernel32.CreateFileW(
                f"\\\\.\\{self.port}",        # Port name format for Windows
                GENERIC_READ | GENERIC_WRITE,  # Read/write access
                0,                            # No sharing
                None,                         # Default security
                OPEN_EXISTING,                # Open existing device
                FILE_ATTRIBUTE_NORMAL,        # Normal file attributes
                None                          # No template file
            )
            
            if self.handle == -1:
                logging.error(f'No pump found on {self.port}: CreateFileW failed')
                self.handle = None
                return
            
            # Configure serial port with XON/XOFF flow control
            dcb = DCB()
            dcb.DCBlength = ctypes.sizeof(DCB)
            
            # Get current DCB settings
            if not kernel32.GetCommState(self.handle, byref(dcb)):
                logging.error(f'Failed to get comm state on {self.port}')
                self._cleanup()
                return
            
            # Configure DCB for Bartels pump - BREAKTHROUGH CONFIGURATION!
            dcb.BaudRate = self.baudrate
            dcb.ByteSize = 8              # 8 data bits
            dcb.StopBits = 0              # 1 stop bit (0 = ONESTOPBIT)
            dcb.Parity = 0                # No parity (0 = NOPARITY)
            dcb.fBinary = 1               # Binary mode (required)
            dcb.fParity = 0               # No parity checking
            
            # ⭐ CRITICAL: Enable XON/XOFF flow control (equivalent to xonxoff=True)
            dcb.fOutX = 1                 # Enable XON/XOFF output flow control
            dcb.fInX = 1                  # Enable XON/XOFF input flow control
            dcb.XonChar = 0x11            # Standard XON character (DC1)
            dcb.XoffChar = 0x13           # Standard XOFF character (DC3)
            dcb.XonLim = 2048             # Buffer level to send XON
            dcb.XoffLim = 512             # Buffer level to send XOFF
            
            # Additional flow control settings
            dcb.fOutxCtsFlow = 0          # Disable CTS flow control
            dcb.fOutxDsrFlow = 0          # Disable DSR flow control
            dcb.fDtrControl = 1           # DTR_CONTROL_ENABLE
            dcb.fRtsControl = 1           # RTS_CONTROL_ENABLE
            dcb.fDsrSensitivity = 0       # Not sensitive to DSR
            dcb.fTXContinueOnXoff = 1     # Continue transmission after XOFF
            dcb.fErrorChar = 0            # Don't replace error characters
            dcb.fNull = 0                 # Don't discard null characters
            dcb.fAbortOnError = 0         # Don't abort on errors
            
            # Apply the configuration
            if not kernel32.SetCommState(self.handle, byref(dcb)):
                logging.error(f'Failed to set comm state on {self.port}')
                self._cleanup()
                return
            
            logging.info(f'Pump connection established on {self.port} (driver-free)')
            
        except Exception as e:
            logging.error(f'Failed to initialize pump on {self.port}: {e}')
            self.handle = None
    
    def _cleanup(self):
        """Clean up handle if initialization fails."""
        if self.handle and self.handle != -1:
            kernel32 = ctypes.windll.kernel32
            kernel32.CloseHandle(self.handle)
            self.handle = None
    
    def close(self):
        """Close pump connection and clean up resources."""
        if self.handle and self.handle != -1:
            try:
                kernel32 = ctypes.windll.kernel32
                kernel32.CloseHandle(self.handle)
                self.handle = None
                logging.info("Pump connection closed (driver-free)")
            except Exception:
                pass
    
    def _send_command(self, command: str):
        """
        Send command to pump with carriage return terminator.
        
        Args:
            command: Command string (without termination)
            
        Returns:
            bool: True if command sent successfully
        """
        if self.handle is None or self.handle == -1:
            logging.error("Pump is not initialized.")
            return False
        
        try:
            kernel32 = ctypes.windll.kernel32
            
            # Add carriage return terminator (same as original pump.py)
            full_command = command + "\r"
            command_bytes = full_command.encode("utf-8")
            
            # Write to the port using Windows API
            bytes_written = ctypes.wintypes.DWORD(0)
            success = kernel32.WriteFile(
                self.handle,
                command_bytes,
                len(command_bytes),
                byref(bytes_written),
                None
            )
            
            if success:
                # Force flush to ensure immediate transmission (equivalent to ser.flush())
                kernel32.FlushFileBuffers(self.handle)
                logging.info(f"Sent command: '{command}'")
                return True
            else:
                logging.error(f"Failed to send command '{command}': WriteFile failed")
                return False
                
        except Exception as e:
            logging.error(f"Failed to send command '{command}': {e}")
            return False
    
    def set_frequency(self, freq: int):
        """
        Set pump frequency in Hz (1-300).
        
        Args:
            freq: Frequency in Hz (1-300)
        """
        if 1 <= freq <= 300:
            self._send_command(f"F{freq}")
            time.sleep(0.15)  # Allow processing time (same as original)
        else:
            logging.error(f"Frequency {freq} out of range (1-300 Hz)")
    
    def set_amplitude(self, amp: int):
        """
        Set pump amplitude (1-300).
        
        Args:
            amp: Amplitude value (1-300)
        """
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
        """Start the pump (original interface)."""
        self._send_command("bon")
        time.sleep(0.15)  # Allow processing time
        logging.info("Pump started")
    
    def stop(self):
        """Stop the pump (original interface)."""
        self._send_command("boff")
        time.sleep(0.15)  # Allow processing time
        logging.info("Pump stopped")
    
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
        """
        Get pump status (placeholder - original doesn't read responses).
        
        Note: Original pump.py doesn't implement response reading,
        so this maintains the same interface for compatibility.
        """
        # Original pump.py doesn't read responses, so we maintain compatibility
        logging.info("Status request sent (driver-free implementation)")
        return "Status reading not implemented (maintains original interface)"
    
    def __enter__(self):
        """Context manager entry."""
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        """Context manager exit."""
        self.close()


# For backwards compatibility, provide the same interface as original pump.py
def create_pump_controller(port: str, baudrate: int = 9600) -> PumpController:
    """
    Factory function to create a driver-free pump controller.
    
    Args:
        port: COM port string
        baudrate: Communication speed
        
    Returns:
        PumpController: Initialized pump controller instance
    """
    return PumpController(port, baudrate)


# Example usage (same as original pump.py)
if __name__ == "__main__":
    # Configure logging to see what's happening
    logging.basicConfig(level=logging.INFO, format='%(levelname)s: %(message)s')
    
    print("Driver-Free Bartels Micropump Controller")
    print("======================================")
    print("Drop-in replacement for pump.py using Windows API")
    
    # Initialize pump controller (same interface as original)
    pump = PumpController("COM4", 9600)
    
    if pump.handle is None:
        print("❌ Failed to initialize pump controller")
        print("Check COM port and ensure pump is connected")
    else:
        try:
            print("\n🧪 Running compatibility test...")
            
            # Test sequence (same as original pump.py usage)
            print("1. Resetting device...")
            pump.reset_device()
            
            print("2. Setting frequency to 100 Hz...")
            pump.set_frequency(100)
            
            print("3. Setting amplitude to 100...")
            pump.set_amplitude(100)
            
            print("4. Starting pump...")
            pump.start()
            
            print("5. Running for 3 seconds...")
            time.sleep(3)
            
            print("6. Stopping pump...")
            pump.stop()
            
            print("\n✅ Driver-free pump control test completed!")
            print("Same interface as original pump.py but no drivers needed!")
            
        except KeyboardInterrupt:
            print("\n⏹️  Test interrupted")
        except Exception as e:
            print(f"\n❌ Error during test: {e}")
        finally:
            pump.close()