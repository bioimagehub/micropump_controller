#!/usr/bin/env python3
"""
DIAGNOSTIC TOOL: Why Windows API isn't working
==============================================
Compare working driver vs Windows API approach to identify the issue.
"""

import ctypes
from ctypes import wintypes
import time
import sys
import os
import logging

# Add src directory for imports
sys.path.append(os.path.join(os.path.dirname(__file__), 'src'))

from pump import PumpController
from resolve_ports import find_pump_port_by_vid_pid

logging.basicConfig(level=logging.INFO, format='%(asctime)s [%(levelname)s] %(message)s')

class PumpDiagnostic:
    """Diagnose why Windows API approach isn't working."""
    
    def __init__(self):
        self.pump_port = None
        
    def find_pump(self):
        """Find pump device."""
        try:
            self.pump_port = find_pump_port_by_vid_pid(0x0403, 0xB4C0)
            print(f"🔍 Found pump on: {self.pump_port}")
            return True
        except Exception as e:
            print(f"❌ Pump not found: {e}")
            return False
    
    def test_working_driver(self):
        """Test with known working driver approach."""
        print("\\n📍 TEST 1: WORKING DRIVER APPROACH")
        print("=" * 45)
        
        try:
            pump = PumpController(self.pump_port)
            
            print("🔧 Configuring with working driver...")
            pump.set_waveform("rectangle")
            time.sleep(0.5)
            pump.set_frequency(100)
            time.sleep(0.5)
            pump.set_voltage(100)
            time.sleep(0.5)
            
            print("▶️  Starting pump with working driver...")
            pump.start()
            
            print("🎧 Listen now - pump should be audible!")
            input("Press Enter when you confirm pump is running...")
            
            pump.stop()
            pump.close()
            
            return True
            
        except Exception as e:
            print(f"❌ Working driver failed: {e}")
            return False
    
    def test_windows_api_detailed(self):
        """Test Windows API with detailed diagnostics."""
        print("\\n📍 TEST 2: WINDOWS API DETAILED ANALYSIS")
        print("=" * 50)
        
        kernel32 = ctypes.windll.kernel32
        GENERIC_READ = 0x80000000
        GENERIC_WRITE = 0x40000000
        OPEN_EXISTING = 3
        
        device_path = f"\\\\.\\{self.pump_port}"
        print(f"🔗 Opening device: {device_path}")
        
        # Open device
        handle = kernel32.CreateFileW(
            device_path,
            GENERIC_READ | GENERIC_WRITE,
            0, None, OPEN_EXISTING, 0, None
        )
        
        if handle == -1:
            error = kernel32.GetLastError()
            print(f"❌ Failed to open device, error: {error}")
            return False
        
        print(f"✅ Device opened, handle: {handle}")
        
        # Test different command formats and timings
        commands_to_test = [
            # Format 1: Just carriage return
            ("MR\\r", "Reset with \\r"),
            ("F100\\r", "Frequency with \\r"),
            ("A100\\r", "Amplitude with \\r"), 
            ("bon\\r", "Start with \\r"),
            
            # Format 2: Carriage return + line feed
            ("MR\\r\\n", "Reset with \\r\\n"),
            ("F100\\r\\n", "Frequency with \\r\\n"),
            ("A100\\r\\n", "Amplitude with \\r\\n"),
            ("bon\\r\\n", "Start with \\r\\n"),
            
            # Format 3: No terminator
            ("MR", "Reset no terminator"),
            ("F100", "Frequency no terminator"),
            ("A100", "Amplitude no terminator"),
            ("bon", "Start no terminator"),
        ]
        
        print("\\n🧪 Testing different command formats...")
        
        for cmd_str, description in commands_to_test:
            print(f"\\n   Testing: {description}")
            
            # Convert command to bytes
            data = cmd_str.encode('utf-8')
            bytes_written = wintypes.DWORD(0)
            
            # Write command
            success = kernel32.WriteFile(
                handle, data, len(data),
                ctypes.byref(bytes_written), None
            )
            
            if success:
                print(f"   ✅ Wrote {bytes_written.value} bytes")
                
                # Flush the buffer
                kernel32.FlushFileBuffers(handle)
                
                # Wait for processing
                time.sleep(0.3)
                
                # Try to read response
                read_buffer = ctypes.create_string_buffer(256)
                bytes_read = wintypes.DWORD(0)
                
                read_success = kernel32.ReadFile(
                    handle, read_buffer, 256,
                    ctypes.byref(bytes_read), None
                )
                
                if read_success and bytes_read.value > 0:
                    response = read_buffer.value[:bytes_read.value]
                    print(f"   📥 Response: {response}")
                else:
                    print("   📥 No response")
                
                # Ask user if pump is working
                if "bon" in cmd_str:
                    user_input = input("   🎧 Do you hear pump running? (y/n): ").lower().strip()
                    if user_input in ['y', 'yes']:
                        print("   🎉 SUCCESS! This format works!")
                        
                        # Stop pump
                        stop_data = b'boff\\r'
                        kernel32.WriteFile(handle, stop_data, len(stop_data), ctypes.byref(bytes_written), None)
                        
                        kernel32.CloseHandle(handle)
                        return True
                    else:
                        print("   ❌ No pump sound detected")
            else:
                error = kernel32.GetLastError()
                print(f"   ❌ Write failed, error: {error}")
        
        # Close handle
        kernel32.CloseHandle(handle)
        return False
    
    def test_serial_port_settings(self):
        """Test different serial port settings."""
        print("\\n📍 TEST 3: SERIAL PORT CONFIGURATION")
        print("=" * 45)
        
        kernel32 = ctypes.windll.kernel32
        device_path = f"\\\\.\\{self.pump_port}"
        
        # Open device
        handle = kernel32.CreateFileW(
            device_path,
            0x80000000 | 0x40000000,  # GENERIC_READ | GENERIC_WRITE
            0, None, 3, 0, None  # OPEN_EXISTING
        )
        
        if handle == -1:
            print("❌ Could not open device for configuration")
            return False
        
        print("🔧 Testing different serial configurations...")
        
        # Try to get current DCB (Device Control Block)
        import ctypes.wintypes as wintypes
        
        class DCB(ctypes.Structure):
            _fields_ = [
                ("DCBlength", wintypes.DWORD),
                ("BaudRate", wintypes.DWORD),
                ("fBinary", wintypes.DWORD, 1),
                ("fParity", wintypes.DWORD, 1),
                ("fOutxCtsFlow", wintypes.DWORD, 1),
                ("fOutxDsrFlow", wintypes.DWORD, 1),
                ("fDtrControl", wintypes.DWORD, 2),
                ("fDsrSensitivity", wintypes.DWORD, 1),
                ("fTXContinueOnXoff", wintypes.DWORD, 1),
                ("fOutX", wintypes.DWORD, 1),
                ("fInX", wintypes.DWORD, 1),
                ("fErrorChar", wintypes.DWORD, 1),
                ("fNull", wintypes.DWORD, 1),
                ("fRtsControl", wintypes.DWORD, 2),
                ("fAbortOnError", wintypes.DWORD, 1),
                ("fDummy2", wintypes.DWORD, 17),
                ("wReserved", wintypes.WORD),
                ("XonLim", wintypes.WORD),
                ("XoffLim", wintypes.WORD),
                ("ByteSize", ctypes.c_ubyte),
                ("Parity", ctypes.c_ubyte),
                ("StopBits", ctypes.c_ubyte),
                ("XonChar", ctypes.c_char),
                ("XoffChar", ctypes.c_char),
                ("ErrorChar", ctypes.c_char),
                ("EofChar", ctypes.c_char),
                ("EvtChar", ctypes.c_char),
                ("wReserved1", wintypes.WORD),
            ]
        
        dcb = DCB()
        dcb.DCBlength = ctypes.sizeof(DCB)
        
        if kernel32.GetCommState(handle, ctypes.byref(dcb)):
            print(f"   Current settings:")
            print(f"   Baud Rate: {dcb.BaudRate}")
            print(f"   Data Bits: {dcb.ByteSize}")
            print(f"   Parity: {dcb.Parity}")
            print(f"   Stop Bits: {dcb.StopBits}")
            
            # Try setting to known pump settings
            dcb.BaudRate = 9600
            dcb.ByteSize = 8
            dcb.Parity = 0  # No parity
            dcb.StopBits = 0  # 1 stop bit
            dcb.fOutxCtsFlow = 0
            dcb.fOutxDsrFlow = 0
            dcb.fDtrControl = 1  # DTR_CONTROL_ENABLE
            dcb.fRtsControl = 1  # RTS_CONTROL_ENABLE
            
            if kernel32.SetCommState(handle, ctypes.byref(dcb)):
                print("   ✅ Serial settings configured")
            else:
                print("   ❌ Failed to set serial settings")
        else:
            print("   ❌ Could not get current serial settings")
        
        kernel32.CloseHandle(handle)
        return True
    
    def compare_approaches(self):
        """Compare working vs non-working approaches."""
        print("\\n📊 COMPARISON ANALYSIS")
        print("=" * 30)
        
        print("🤔 POTENTIAL ISSUES:")
        print("1. Serial port configuration (baud, parity, flow control)")
        print("2. Command termination (\\r vs \\r\\n vs none)")
        print("3. Timing between commands")
        print("4. DTR/RTS control signals")
        print("5. Buffer flushing")
        print("6. Device initialization sequence")
        
        print("\\n💡 NEXT DEBUGGING STEPS:")
        print("1. Compare exact serial settings used by working driver")
        print("2. Monitor actual serial traffic with working driver")
        print("3. Test manual serial communication tools")
        print("4. Check if device needs specific initialization")
    
    def run_diagnostic(self):
        """Run complete diagnostic."""
        print("🔬 PUMP COMMUNICATION DIAGNOSTIC")
        print("=" * 40)
        print("Investigating why Windows API approach isn't working")
        print("=" * 40)
        
        if not self.find_pump():
            return
        
        # Test 1: Confirm working driver
        print("\\nFirst, let's confirm the working approach...")
        if not self.test_working_driver():
            print("❌ Even the working driver failed! Check connections.")
            return
        
        # Test 2: Detailed Windows API analysis
        if self.test_windows_api_detailed():
            print("\\n🎉 Found working Windows API format!")
            return
        
        # Test 3: Serial port configuration
        self.test_serial_port_settings()
        
        # Test 4: Analysis
        self.compare_approaches()
        
        print("\\n📋 RECOMMENDATION:")
        print("The Windows API writes are succeeding but the pump isn't responding.")
        print("This suggests a serial configuration or protocol issue.")
        print("We need to capture and compare the exact traffic from the working driver.")

def main():
    """Main diagnostic execution."""
    diagnostic = PumpDiagnostic()
    diagnostic.run_diagnostic()

if __name__ == "__main__":
    main()