"""Fixed Windows API pump controller with proper serial configuration."""

import ctypes
import ctypes.wintypes
import time
from ctypes import Structure, byref, c_ulong, c_ubyte, c_ushort

# Windows API constants
GENERIC_READ = 0x80000000
GENERIC_WRITE = 0x40000000
OPEN_EXISTING = 3
FILE_ATTRIBUTE_NORMAL = 0x80

# DCB (Device Control Block) structure for serial port configuration
class DCB(Structure):
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
        ("fOutX", c_ulong, 1),          # XON/XOFF output flow control
        ("fInX", c_ulong, 1),           # XON/XOFF input flow control
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
        ("XonChar", c_ubyte),           # XON character (usually 0x11)
        ("XoffChar", c_ubyte),          # XOFF character (usually 0x13)
        ("ErrorChar", c_ubyte),
        ("EofChar", c_ubyte),
        ("EvtChar", c_ubyte),
        ("wReserved1", c_ushort),
    ]

class WindowsAPIPumpController:
    """Bartels micropump controller using direct Windows API calls."""
    
    def __init__(self, port="COM4", baudrate=9600):
        self.port = port
        self.baudrate = baudrate
        self.handle = None
        self._initialize()
    
    def _initialize(self):
        """Initialize serial connection using Windows API."""
        kernel32 = ctypes.windll.kernel32
        
        # Open the serial port
        self.handle = kernel32.CreateFileW(
            f"\\\\.\\{self.port}",
            GENERIC_READ | GENERIC_WRITE,
            0,  # No sharing
            None,  # Default security
            OPEN_EXISTING,
            FILE_ATTRIBUTE_NORMAL,
            None
        )
        
        if self.handle == -1:
            print(f"Failed to open {self.port}")
            return False
        
        # Configure serial port with XON/XOFF flow control
        dcb = DCB()
        dcb.DCBlength = ctypes.sizeof(DCB)
        
        # Get current DCB settings
        if not kernel32.GetCommState(self.handle, byref(dcb)):
            print("Failed to get comm state")
            return False
        
        # Configure DCB for Bartels pump (matching PumpController settings)
        dcb.BaudRate = self.baudrate
        dcb.ByteSize = 8
        dcb.StopBits = 0  # 1 stop bit
        dcb.Parity = 0    # No parity
        dcb.fBinary = 1   # Binary mode
        dcb.fParity = 0   # No parity checking
        
        # CRITICAL: Enable XON/XOFF flow control (like PumpController xonxoff=True)
        dcb.fOutX = 1     # Enable XON/XOFF output flow control
        dcb.fInX = 1      # Enable XON/XOFF input flow control
        dcb.XonChar = 0x11    # Standard XON character
        dcb.XoffChar = 0x13   # Standard XOFF character
        dcb.XonLim = 2048     # When to send XON
        dcb.XoffLim = 512     # When to send XOFF
        
        # Set flow control settings
        dcb.fOutxCtsFlow = 0  # No CTS flow control
        dcb.fOutxDsrFlow = 0  # No DSR flow control
        dcb.fDtrControl = 1   # DTR_CONTROL_ENABLE
        dcb.fRtsControl = 1   # RTS_CONTROL_ENABLE
        dcb.fDsrSensitivity = 0
        dcb.fTXContinueOnXoff = 1
        dcb.fErrorChar = 0
        dcb.fNull = 0
        dcb.fAbortOnError = 0
        
        # Apply the configuration
        if not kernel32.SetCommState(self.handle, byref(dcb)):
            print("Failed to set comm state")
            return False
        
        print(f"Successfully opened and configured {self.port} with XON/XOFF flow control")
        return True
    
    def _send_command(self, command):
        """Send command to pump with proper termination."""
        if self.handle is None or self.handle == -1:
            print("Port not open")
            return False
        
        kernel32 = ctypes.windll.kernel32
        
        # Add carriage return terminator (like PumpController)
        full_command = command + "\r"
        command_bytes = full_command.encode('utf-8')
        
        # Write to the port
        bytes_written = ctypes.wintypes.DWORD(0)
        success = kernel32.WriteFile(
            self.handle,
            command_bytes,
            len(command_bytes),
            byref(bytes_written),
            None
        )
        
        if success:
            # Force flush (like PumpController ser.flush())
            kernel32.FlushFileBuffers(self.handle)
            print(f"Sent command '{command}' ({bytes_written.value} bytes written)")
            return True
        else:
            print(f"Failed to send command '{command}'")
            return False
    
    def set_frequency(self, freq):
        """Set pump frequency in Hz (1-300)."""
        if 1 <= freq <= 300:
            success = self._send_command(f"F{freq}")
            if success:
                time.sleep(0.15)  # Same delay as PumpController
            return success
        else:
            print(f"Frequency {freq} out of range (1-300 Hz)")
            return False
    
    def set_amplitude(self, amp):
        """Set pump amplitude (1-300)."""
        if 1 <= amp <= 300:
            success = self._send_command(f"A{amp}")
            if success:
                time.sleep(0.15)
            return success
        else:
            print(f"Amplitude {amp} out of range (1-300)")
            return False
    
    def start_pump(self):
        """Start pumping."""
        success = self._send_command("bon")
        if success:
            time.sleep(0.15)
        return success
    
    def stop_pump(self):
        """Stop pumping."""
        success = self._send_command("boff")
        if success:
            time.sleep(0.15)
        return success
    
    def close(self):
        """Close the serial port."""
        if self.handle and self.handle != -1:
            kernel32 = ctypes.windll.kernel32
            kernel32.CloseHandle(self.handle)
            self.handle = None
            print("Port closed")

def test_fixed_pump_controller():
    """Test the fixed Windows API pump controller with XON/XOFF flow control."""
    print("Testing Fixed Windows API Pump Controller with XON/XOFF Flow Control")
    print("=" * 70)
    
    # Initialize controller
    controller = WindowsAPIPumpController("COM4", 9600)
    
    if controller.handle is None or controller.handle == -1:
        print("Failed to initialize pump controller")
        return
    
    try:
        # Test sequence
        print("\n1. Setting frequency to 100 Hz...")
        controller.set_frequency(100)
        
        print("2. Setting amplitude to 100...")
        controller.set_amplitude(100)
        
        print("3. Starting pump (should hear sound now)...")
        controller.start_pump()
        
        print("4. Pumping for 3 seconds...")
        time.sleep(3)
        
        print("5. Stopping pump...")
        controller.stop_pump()
        
        print("\nTest completed! Did you hear the pump sound this time?")
        
    except Exception as e:
        print(f"Error during test: {e}")
    finally:
        controller.close()

if __name__ == "__main__":
    test_fixed_pump_controller()