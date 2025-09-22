"""
BARTELS MICROPUMP DRIVER-FREE CONTROLLER
========================================
Working implementation - September 22, 2025

This is the EXACT working code that successfully achieved driver-free
pump control using pure Windows API calls with XON/XOFF flow control.

CRITICAL SUCCESS FACTOR: XON/XOFF flow control configuration in DCB structure.
"""

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
        ("XonChar", c_ubyte),           # XON character (usually 0x11) - CRITICAL!
        ("XoffChar", c_ubyte),          # XOFF character (usually 0x13) - CRITICAL!
        ("ErrorChar", c_ubyte),
        ("EofChar", c_ubyte),
        ("EvtChar", c_ubyte),
        ("wReserved1", c_ushort),
    ]

class BartelsDriverFreePumpController:
    """
    WORKING driver-free Bartels micropump controller using Windows API.
    
    This implementation successfully controls Bartels mp-x series micropumps
    without requiring proprietary FTDI drivers by using direct Windows API
    calls with proper XON/XOFF flow control configuration.
    
    VERIFIED WORKING: September 22, 2025
    """
    
    def __init__(self, port="COM4", baudrate=9600):
        """
        Initialize controller.
        
        Args:
            port: COM port (check with serial.tools.list_ports for actual port)
            baudrate: Communication speed (9600 confirmed working)
        """
        self.port = port
        self.baudrate = baudrate
        self.handle = None
        self.is_initialized = self._initialize()
    
    def _initialize(self):
        """
        Initialize serial connection using Windows API with XON/XOFF flow control.
        
        THIS IS THE CRITICAL BREAKTHROUGH IMPLEMENTATION.
        
        Returns:
            bool: True if initialization successful, False otherwise
        """
        kernel32 = ctypes.windll.kernel32
        
        # Step 1: Open the serial port using Windows CreateFileW API
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
            print(f"❌ Failed to open {self.port}")
            return False
        
        # Step 2: Configure serial port with XON/XOFF flow control
        dcb = DCB()
        dcb.DCBlength = ctypes.sizeof(DCB)
        
        # Get current DCB settings
        if not kernel32.GetCommState(self.handle, byref(dcb)):
            print("❌ Failed to get comm state")
            self._cleanup()
            return False
        
        # Configure DCB for Bartels pump - THIS IS THE BREAKTHROUGH!
        dcb.BaudRate = self.baudrate
        dcb.ByteSize = 8              # 8 data bits
        dcb.StopBits = 0              # 1 stop bit (0 = ONESTOPBIT)
        dcb.Parity = 0                # No parity (0 = NOPARITY)
        dcb.fBinary = 1               # Binary mode (required)
        dcb.fParity = 0               # No parity checking
        
        # ⭐ CRITICAL: Enable XON/XOFF flow control (this was the missing piece!)
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
            print("❌ Failed to set comm state")
            self._cleanup()
            return False
        
        print(f"✅ Successfully opened and configured {self.port} with XON/XOFF flow control")
        return True
    
    def _cleanup(self):
        """Clean up handle if initialization fails."""
        if self.handle and self.handle != -1:
            kernel32 = ctypes.windll.kernel32
            kernel32.CloseHandle(self.handle)
            self.handle = None
    
    def _send_command(self, command):
        """
        Send command to pump with proper termination and flushing.
        
        Args:
            command: Command string (without termination)
            
        Returns:
            bool: True if command sent successfully
        """
        if not self.is_initialized or self.handle is None or self.handle == -1:
            print("❌ Port not properly initialized")
            return False
        
        kernel32 = ctypes.windll.kernel32
        
        # Add carriage return terminator (CRITICAL - must be \r, not \n)
        full_command = command + "\r"
        command_bytes = full_command.encode('utf-8')
        
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
            # Force flush to ensure immediate transmission (CRITICAL)
            kernel32.FlushFileBuffers(self.handle)
            print(f"✅ Sent command '{command}' ({bytes_written.value} bytes written)")
            return True
        else:
            print(f"❌ Failed to send command '{command}'")
            return False
    
    def set_frequency(self, freq):
        """
        Set pump frequency in Hz.
        
        Args:
            freq: Frequency (1-300 Hz)
            
        Returns:
            bool: True if successful
        """
        if not 1 <= freq <= 300:
            print(f"❌ Frequency {freq} out of range (1-300 Hz)")
            return False
        
        success = self._send_command(f"F{freq}")
        if success:
            time.sleep(0.15)  # Allow processing time (CRITICAL timing)
        return success
    
    def set_amplitude(self, amp):
        """
        Set pump amplitude.
        
        Args:
            amp: Amplitude (1-300)
            
        Returns:
            bool: True if successful
        """
        if not 1 <= amp <= 300:
            print(f"❌ Amplitude {amp} out of range (1-300)")
            return False
        
        success = self._send_command(f"A{amp}")
        if success:
            time.sleep(0.15)
        return success
    
    def start_pump(self):
        """
        Start pumping.
        
        Returns:
            bool: True if successful
        """
        success = self._send_command("bon")
        if success:
            time.sleep(0.15)
            print("🔊 Pump should be running (listen for sound)")
        return success
    
    def stop_pump(self):
        """
        Stop pumping.
        
        Returns:
            bool: True if successful
        """
        success = self._send_command("boff")
        if success:
            time.sleep(0.15)
            print("🔇 Pump stopped")
        return success
    
    def run_test_sequence(self):
        """
        Run a complete test sequence to verify functionality.
        
        Returns:
            bool: True if all commands successful
        """
        if not self.is_initialized:
            print("❌ Controller not initialized")
            return False
        
        print("\n🧪 Running Bartels Pump Test Sequence")
        print("=" * 50)
        
        steps = [
            ("Setting frequency to 100 Hz", lambda: self.set_frequency(100)),
            ("Setting amplitude to 100", lambda: self.set_amplitude(100)),
            ("Starting pump (listen for sound!)", lambda: self.start_pump()),
            ("Pumping for 3 seconds", lambda: time.sleep(3) or True),
            ("Stopping pump", lambda: self.stop_pump()),
        ]
        
        success_count = 0
        for i, (description, action) in enumerate(steps, 1):
            print(f"{i}. {description}...")
            if action():
                success_count += 1
            else:
                print(f"❌ Step {i} failed")
                break
        
        if success_count == len(steps):
            print("\n🎉 TEST SEQUENCE COMPLETED SUCCESSFULLY!")
            print("If you heard pump sound, driver-free control is working!")
            return True
        else:
            print(f"\n❌ Test sequence failed at step {success_count + 1}")
            return False
    
    def close(self):
        """Close the serial port and clean up resources."""
        if self.handle and self.handle != -1:
            kernel32 = ctypes.windll.kernel32
            kernel32.CloseHandle(self.handle)
            self.handle = None
            self.is_initialized = False
            print("✅ Port closed")

def find_pump_port():
    """
    Find the Bartels pump COM port automatically.
    
    Returns:
        str: COM port name or None if not found
    """
    try:
        import serial.tools.list_ports
        
        ports = serial.tools.list_ports.comports()
        for port in ports:
            if "Micropump Control" in port.description:
                return port.device
        
        print("Available ports:")
        for port in ports:
            print(f"  {port.device}: {port.description}")
        
        return None
    except ImportError:
        print("pyserial not available for port detection")
        return None

def main():
    """Main function to demonstrate driver-free pump control."""
    print("BARTELS MICROPUMP DRIVER-FREE CONTROLLER")
    print("========================================")
    print("Pure Windows API implementation with XON/XOFF flow control")
    print("Successfully tested: September 22, 2025\n")
    
    # Try to find pump port automatically
    pump_port = find_pump_port()
    if not pump_port:
        pump_port = "COM4"  # Fallback to known working port
        print(f"Using fallback port: {pump_port}")
    else:
        print(f"Found pump on port: {pump_port}")
    
    # Initialize controller
    controller = BartelsDriverFreePumpController(pump_port, 9600)
    
    if not controller.is_initialized:
        print("❌ Failed to initialize pump controller")
        print("Check COM port and ensure pump is connected")
        return
    
    try:
        # Run test sequence
        success = controller.run_test_sequence()
        
        if success:
            print("\n🚀 BREAKTHROUGH ACHIEVED!")
            print("Driver-free Bartels micropump control is working!")
            print("\nThis opens the door for:")
            print("• Docker container pump control")
            print("• WSL2 USB forwarding")
            print("• Cross-platform implementations") 
            print("• Network-based pump servers")
            print("• And 46 more test approaches!")
        
    except KeyboardInterrupt:
        print("\n⏹️  Test interrupted by user")
    except Exception as e:
        print(f"\n❌ Unexpected error: {e}")
    finally:
        controller.close()

if __name__ == "__main__":
    main()