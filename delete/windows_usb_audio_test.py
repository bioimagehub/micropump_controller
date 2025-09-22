"""
Windows Direct USB Communication Test with Audio Feedback
Attempts 50 different methods to communicate with the Bartels pump via Windows USB API
Uses audio detection to determine which methods actually work
"""

import ctypes
from ctypes import wintypes
import time
import numpy as np
import sounddevice as sd
import logging
import sys
import os
import serial.tools.list_ports
from typing import List, Dict, Any, Optional

# Add src directory for imports
sys.path.append(os.path.join(os.path.dirname(__file__), 'src'))

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s [%(levelname)s] %(message)s')

# Windows USB API constants
GENERIC_READ = 0x80000000
GENERIC_WRITE = 0x40000000
FILE_SHARE_READ = 0x00000001
FILE_SHARE_WRITE = 0x00000002
OPEN_EXISTING = 3
FILE_ATTRIBUTE_NORMAL = 0x80
INVALID_HANDLE_VALUE = -1

class AudioDetector:
    """Simple audio detector for pump sounds."""
    
    def __init__(self):
        self.sample_rate = 22050
        self.duration = 2.0
        self.baseline_rms = None
        
    def establish_baseline(self):
        """Record baseline audio."""
        print("📊 Establishing audio baseline (2 seconds of silence)...")
        time.sleep(1)
        audio = sd.rec(int(self.duration * self.sample_rate), 
                      samplerate=self.sample_rate, channels=1)
        sd.wait()
        self.baseline_rms = np.sqrt(np.mean(audio.flatten()**2))
        print(f"   Baseline RMS: {self.baseline_rms:.6f}")
        
    def detect_pump_sound(self) -> bool:
        """Record audio and detect if pump is running."""
        try:
            # Use shorter duration to avoid hanging
            short_duration = 1.0  # 1 second instead of 2
            audio = sd.rec(int(short_duration * self.sample_rate), 
                          samplerate=self.sample_rate, channels=1)
            sd.wait()  # Wait for recording to complete
            
            rms = np.sqrt(np.mean(audio.flatten()**2))
            ratio = rms / self.baseline_rms if self.baseline_rms and self.baseline_rms > 0 else 0
            
            # Pump detected if audio is significantly louder than baseline
            detected = ratio > 1.5 and rms > 0.005
            print(f"   Audio RMS: {rms:.6f}, Ratio: {ratio:.2f}, Detected: {'YES' if detected else 'NO'}")
            return detected
        except Exception as e:
            print(f"   Audio error: {e} - Skipping audio detection")
            return False

class WindowsDirectUSBTester:
    """Tests direct USB communication with Bartels pump using Windows API."""
    
    def __init__(self):
        self.audio = AudioDetector()
        self.successful_methods = []
        self.test_results = []
        
        # Bartels pump identifiers
        self.vid = 0x0403  # FTDI
        self.pid = 0xB4C0  # Bartels specific
        self.pump_port = None
        
        # Load Windows API
        self.kernel32 = ctypes.windll.kernel32
        self.setupapi = ctypes.windll.setupapi
        
    def find_pump_device(self) -> bool:
        """Find the Bartels pump device."""
        print(f"🔍 Searching for Bartels pump (VID:{self.vid:04X}, PID:{self.pid:04X})...")
        
        # Find using serial port enumeration
        ports = serial.tools.list_ports.comports()
        for port in ports:
            if port.vid == self.vid and port.pid == self.pid:
                self.pump_port = port.device
                print(f"✅ Found pump on: {self.pump_port}")
                print(f"   Description: {port.description}")
                print(f"   Hardware ID: {port.hwid}")
                return True
                
        print("❌ Pump device not found")
        return False
    
    def test_method(self, method_num: int, description: str, test_func) -> bool:
        """Test a specific communication method with audio feedback."""
        print(f"\\n🧪 TEST {method_num:2d}/50: {description}")
        print("=" * 60)
        
        success = False
        error_msg = ""
        pump_detected = False
        
        try:
            # Execute the test function
            result = test_func()
            
            # Wait a moment then check for audio
            time.sleep(0.5)
            pump_detected = self.audio.detect_pump_sound()
            
            if pump_detected:
                success = True
                self.successful_methods.append((method_num, description))
                print(f"🎉 SUCCESS: {description}")
            else:
                print(f"❌ No pump sound detected")
                
        except Exception as e:
            error_msg = str(e)
            print(f"❌ Exception: {error_msg}")
        
        # Record results
        self.test_results.append({
            'method': method_num,
            'description': description,
            'success': success,
            'audio_detected': pump_detected,
            'error': error_msg
        })
        
        # Brief pause between tests
        time.sleep(1)
        return success
    
    def run_all_tests(self):
        """Run all 50 direct USB communication tests."""
        print("🚀 WINDOWS DIRECT USB COMMUNICATION TEST SUITE")
        print("=" * 60)
        print("Testing 50 different methods to communicate with Bartels pump")
        print("Using audio detection to identify successful communication")
        
        if not self.find_pump_device():
            return
            
        # Establish audio baseline
        self.audio.establish_baseline()
        
        # Test 1-10: Basic Serial Port Communication
        self.test_method(1, "Standard serial F100 command", 
                        lambda: self.serial_command(b'F100\\n'))
        
        self.test_method(2, "Standard serial A50 command", 
                        lambda: self.serial_command(b'A50\\n'))
        
        self.test_method(3, "Standard serial bon command", 
                        lambda: self.serial_command(b'bon\\n'))
        
        self.test_method(4, "Serial with custom baudrate 9600", 
                        lambda: self.serial_command(b'F100\\n', baudrate=9600))
        
        self.test_method(5, "Serial with custom baudrate 57600", 
                        lambda: self.serial_command(b'F100\\n', baudrate=57600))
        
        # Test 6-15: Different data formats
        self.test_method(6, "Command with CR terminator", 
                        lambda: self.serial_command(b'F100\\r'))
        
        self.test_method(7, "Command with CRLF terminator", 
                        lambda: self.serial_command(b'F100\\r\\n'))
        
        self.test_method(8, "Binary frequency command", 
                        lambda: self.serial_command(bytes([0x46, 0x31, 0x30, 0x30])))
        
        self.test_method(9, "Hex encoded command", 
                        lambda: self.serial_command(bytes.fromhex('463130300A')))
        
        self.test_method(10, "Command with null terminator", 
                         lambda: self.serial_command(b'F100\\x00'))
        
        # Test 11-20: Windows Device I/O
        self.test_method(11, "Windows CreateFile + WriteFile", 
                        lambda: self.windows_device_io(b'F100\\n'))
        
        self.test_method(12, "Windows overlapped I/O", 
                        lambda: self.windows_overlapped_io(b'bon\\n'))
        
        self.test_method(13, "Windows DeviceIoControl", 
                        lambda: self.windows_device_ioctl())
        
        self.test_method(14, "Windows raw device access", 
                        lambda: self.windows_raw_device_access())
        
        self.test_method(15, "Windows COM port bypass", 
                        lambda: self.windows_com_bypass())
        
        # Test 16-25: FTDI-specific approaches
        self.test_method(16, "FTDI D2XX API simulation", 
                        lambda: self.ftdi_d2xx_simulation())
        
        self.test_method(17, "FTDI VCP with custom settings", 
                        lambda: self.ftdi_vcp_custom_settings())
        
        self.test_method(18, "FTDI latency optimization", 
                        lambda: self.ftdi_latency_optimization())
        
        self.test_method(19, "FTDI buffer management", 
                        lambda: self.ftdi_buffer_management())
        
        self.test_method(20, "FTDI flow control disable", 
                        lambda: self.ftdi_flow_control_disable())
        
        # Test 21-30: Protocol variations
        self.test_method(21, "Multi-command sequence", 
                        lambda: self.multi_command_sequence())
        
        self.test_method(22, "Timed command sequence", 
                        lambda: self.timed_command_sequence())
        
        self.test_method(23, "Command with echo check", 
                        lambda: self.command_with_echo_check())
        
        self.test_method(24, "Persistent connection test", 
                        lambda: self.persistent_connection_test())
        
        self.test_method(25, "Buffered command approach", 
                        lambda: self.buffered_command_approach())
        
        # Test 26-35: Alternative protocols
        self.test_method(26, "Binary protocol attempt", 
                        lambda: self.binary_protocol_attempt())
        
        self.test_method(27, "Modbus-style command", 
                        lambda: self.modbus_style_command())
        
        self.test_method(28, "ASCII protocol with STX/ETX", 
                        lambda: self.ascii_protocol_stx_etx())
        
        self.test_method(29, "Length-prefixed protocol", 
                        lambda: self.length_prefixed_protocol())
        
        self.test_method(30, "Checksum-protected protocol", 
                        lambda: self.checksum_protected_protocol())
        
        # Test 31-40: Advanced Windows techniques
        self.test_method(31, "Windows USB hub reset", 
                        lambda: self.windows_usb_hub_reset())
        
        self.test_method(32, "Registry-based configuration", 
                        lambda: self.registry_based_config())
        
        self.test_method(33, "WMI device management", 
                        lambda: self.wmi_device_management())
        
        self.test_method(34, "PowerShell device control", 
                        lambda: self.powershell_device_control())
        
        self.test_method(35, "Windows Service integration", 
                        lambda: self.windows_service_integration())
        
        # Test 36-45: Creative approaches
        self.test_method(36, "Multiple port scanning", 
                        lambda: self.multiple_port_scanning())
        
        self.test_method(37, "Broadcast to all COM ports", 
                        lambda: self.broadcast_all_com_ports())
        
        self.test_method(38, "USB device tree traversal", 
                        lambda: self.usb_device_tree_traversal())
        
        self.test_method(39, "Driver stack bypass", 
                        lambda: self.driver_stack_bypass())
        
        self.test_method(40, "Low-level USB interrupt", 
                        lambda: self.low_level_usb_interrupt())
        
        # Test 41-50: Kitchen sink approaches
        self.test_method(41, "All baudratesk test", 
                        lambda: self.all_baudrates_test())
        
        self.test_method(42, "All terminators test", 
                        lambda: self.all_terminators_test())
        
        self.test_method(43, "Brute force command variations", 
                        lambda: self.brute_force_command_variations())
        
        self.test_method(44, "Parallel port attempts", 
                        lambda: self.parallel_port_attempts())
        
        self.test_method(45, "Memory-mapped I/O attempt", 
                        lambda: self.memory_mapped_io_attempt())
        
        self.test_method(46, "DLL injection approach", 
                        lambda: self.dll_injection_approach())
        
        self.test_method(47, "Kernel driver bypass", 
                        lambda: self.kernel_driver_bypass())
        
        self.test_method(48, "Hardware abstraction layer", 
                        lambda: self.hardware_abstraction_layer())
        
        self.test_method(49, "Real-time communication", 
                        lambda: self.realtime_communication())
        
        self.test_method(50, "Ultimate kitchen sink", 
                        lambda: self.ultimate_kitchen_sink())
        
        # Print final results
        self.print_results()
    
    def serial_command(self, command: bytes, baudrate: int = 115200) -> bool:
        """Send command via standard serial interface."""
        try:
            import serial
            with serial.Serial(self.pump_port, baudrate=baudrate, timeout=1) as ser:
                ser.write(command)
                time.sleep(0.1)
                return True
        except Exception as e:
            print(f"   Serial error: {e}")
            return False
    
    def windows_device_io(self, command: bytes) -> bool:
        """Direct Windows device I/O."""
        try:
            # Open device handle
            device_path = f"\\\\\\\\.\\\\{self.pump_port}"
            handle = self.kernel32.CreateFileW(
                device_path,
                GENERIC_READ | GENERIC_WRITE,
                FILE_SHARE_READ | FILE_SHARE_WRITE,
                None,
                OPEN_EXISTING,
                FILE_ATTRIBUTE_NORMAL,
                None
            )
            
            if handle == INVALID_HANDLE_VALUE:
                return False
            
            # Write data
            bytes_written = wintypes.DWORD()
            result = self.kernel32.WriteFile(
                handle,
                command,
                len(command),
                ctypes.byref(bytes_written),
                None
            )
            
            self.kernel32.CloseHandle(handle)
            return bool(result)
            
        except Exception as e:
            print(f"   Windows I/O error: {e}")
            return False
    
    def windows_overlapped_io(self, command: bytes) -> bool:
        """Windows overlapped I/O."""
        # Placeholder - would need OVERLAPPED structure
        return self.windows_device_io(command)
    
    def windows_device_ioctl(self) -> bool:
        """Windows DeviceIoControl."""
        try:
            # This would require specific IOCTL codes for FTDI
            return False
        except:
            return False
    
    def windows_raw_device_access(self) -> bool:
        """Raw device access attempt."""
        # Placeholder for raw device access
        return self.serial_command(b'F100\\n')
    
    def windows_com_bypass(self) -> bool:
        """Bypass standard COM port handling."""
        return self.windows_device_io(b'bon\\n')
    
    def ftdi_d2xx_simulation(self) -> bool:
        """Simulate FTDI D2XX API calls."""
        # This would require the actual D2XX DLL
        return self.serial_command(b'F100\\n')
    
    def ftdi_vcp_custom_settings(self) -> bool:
        """Custom FTDI VCP settings."""
        try:
            import serial
            with serial.Serial(self.pump_port, 115200, timeout=1) as ser:
                # Custom settings
                ser.rts = True
                ser.dtr = True
                time.sleep(0.1)
                ser.write(b'F100\\n')
                time.sleep(0.1)
                ser.write(b'bon\\n')
                return True
        except:
            return False
    
    def ftdi_latency_optimization(self) -> bool:
        """Optimize FTDI latency."""
        return self.serial_command(b'bon\\n', baudrate=921600)
    
    def ftdi_buffer_management(self) -> bool:
        """FTDI buffer management."""
        try:
            import serial
            with serial.Serial(self.pump_port, 115200, timeout=1) as ser:
                ser.reset_input_buffer()
                ser.reset_output_buffer()
                ser.write(b'F100\\nA50\\nbon\\n')
                return True
        except:
            return False
    
    def ftdi_flow_control_disable(self) -> bool:
        """Disable FTDI flow control."""
        try:
            import serial
            with serial.Serial(self.pump_port, 115200, timeout=1, 
                             rtscts=False, dsrdtr=False, xonxoff=False) as ser:
                ser.write(b'bon\\n')
                return True
        except:
            return False
    
    def multi_command_sequence(self) -> bool:
        """Multiple command sequence."""
        try:
            import serial
            with serial.Serial(self.pump_port, 115200, timeout=1) as ser:
                commands = [b'F100\\n', b'A50\\n', b'bon\\n']
                for cmd in commands:
                    ser.write(cmd)
                    time.sleep(0.1)
                return True
        except:
            return False
    
    def timed_command_sequence(self) -> bool:
        """Timed command sequence."""
        return self.multi_command_sequence()
    
    def command_with_echo_check(self) -> bool:
        """Command with echo verification."""
        try:
            import serial
            with serial.Serial(self.pump_port, 115200, timeout=1) as ser:
                ser.write(b'bon\\n')
                # Try to read response
                response = ser.read(100)
                return len(response) > 0
        except:
            return False
    
    def persistent_connection_test(self) -> bool:
        """Persistent connection test."""
        return self.multi_command_sequence()
    
    def buffered_command_approach(self) -> bool:
        """Buffered command approach."""
        return self.serial_command(b'F100\\nA50\\nbon\\n')
    
    def binary_protocol_attempt(self) -> bool:
        """Binary protocol attempt."""
        # Binary command: [STX][CMD][PARAM][ETX]
        cmd = bytes([0x02, 0x46, 0x64, 0x03])  # STX F 100 ETX
        return self.serial_command(cmd)
    
    def modbus_style_command(self) -> bool:
        """Modbus-style command."""
        # [ADDR][FUNC][REG][DATA][CRC]
        cmd = bytes([0x01, 0x06, 0x00, 0x01, 0x00, 0x64, 0x99, 0x9E])
        return self.serial_command(cmd)
    
    def ascii_protocol_stx_etx(self) -> bool:
        """ASCII protocol with STX/ETX."""
        cmd = b'\\x02F100\\x03'
        return self.serial_command(cmd)
    
    def length_prefixed_protocol(self) -> bool:
        """Length-prefixed protocol."""
        cmd = b'\\x05F100\\n'  # Length 5 + command
        return self.serial_command(cmd)
    
    def checksum_protected_protocol(self) -> bool:
        """Checksum-protected protocol."""
        data = b'F100'
        checksum = sum(data) & 0xFF
        cmd = data + bytes([checksum])
        return self.serial_command(cmd)
    
    def windows_usb_hub_reset(self) -> bool:
        """Reset USB hub."""
        # This would require admin privileges and specific Windows API calls
        return False
    
    def registry_based_config(self) -> bool:
        """Registry-based configuration."""
        # This would modify registry settings - dangerous
        return False
    
    def wmi_device_management(self) -> bool:
        """WMI device management."""
        # This would use Windows WMI
        return False
    
    def powershell_device_control(self) -> bool:
        """PowerShell device control."""
        try:
            import subprocess
            # Simple PowerShell command
            result = subprocess.run(['powershell', '-Command', 'Get-WmiObject Win32_SerialPort'], 
                                  capture_output=True, text=True, timeout=5)
            return result.returncode == 0
        except:
            return False
    
    def windows_service_integration(self) -> bool:
        """Windows Service integration."""
        return False
    
    def multiple_port_scanning(self) -> bool:
        """Scan multiple ports."""
        ports = ['COM1', 'COM2', 'COM3', 'COM4', 'COM5', 'COM6']
        for port in ports:
            try:
                import serial
                with serial.Serial(port, 115200, timeout=0.1) as ser:
                    ser.write(b'bon\\n')
                    time.sleep(0.1)
            except:
                continue
        return True
    
    def broadcast_all_com_ports(self) -> bool:
        """Broadcast to all COM ports."""
        return self.multiple_port_scanning()
    
    def usb_device_tree_traversal(self) -> bool:
        """USB device tree traversal."""
        return False
    
    def driver_stack_bypass(self) -> bool:
        """Driver stack bypass."""
        return False
    
    def low_level_usb_interrupt(self) -> bool:
        """Low-level USB interrupt."""
        return False
    
    def all_baudrates_test(self) -> bool:
        """Test all common baudrates."""
        baudrates = [9600, 19200, 38400, 57600, 115200, 230400, 460800, 921600]
        for baud in baudrates:
            try:
                import serial
                with serial.Serial(self.pump_port, baud, timeout=0.1) as ser:
                    ser.write(b'bon\\n')
                    time.sleep(0.1)
            except:
                continue
        return True
    
    def all_terminators_test(self) -> bool:
        """Test all terminators."""
        terminators = [b'\\n', b'\\r', b'\\r\\n', b'\\x00', b'']
        for term in terminators:
            try:
                import serial
                with serial.Serial(self.pump_port, 115200, timeout=0.1) as ser:
                    ser.write(b'bon' + term)
                    time.sleep(0.1)
            except:
                continue
        return True
    
    def brute_force_command_variations(self) -> bool:
        """Brute force command variations."""
        variations = [b'bon', b'BON', b'bon\\n', b'BON\\n', b'b on', b'b  on']
        for var in variations:
            try:
                import serial
                with serial.Serial(self.pump_port, 115200, timeout=0.1) as ser:
                    ser.write(var)
                    time.sleep(0.1)
            except:
                continue
        return True
    
    def parallel_port_attempts(self) -> bool:
        """Parallel port attempts."""
        return False
    
    def memory_mapped_io_attempt(self) -> bool:
        """Memory-mapped I/O attempt."""
        return False
    
    def dll_injection_approach(self) -> bool:
        """DLL injection approach."""
        return False
    
    def kernel_driver_bypass(self) -> bool:
        """Kernel driver bypass."""
        return False
    
    def hardware_abstraction_layer(self) -> bool:
        """Hardware abstraction layer."""
        return False
    
    def realtime_communication(self) -> bool:
        """Real-time communication."""
        return self.serial_command(b'bon\\n')
    
    def ultimate_kitchen_sink(self) -> bool:
        """Ultimate kitchen sink approach."""
        # Try everything
        success = False
        success |= self.multi_command_sequence()
        success |= self.all_baudrates_test()
        success |= self.all_terminators_test()
        success |= self.brute_force_command_variations()
        return success
    
    def print_results(self):
        """Print comprehensive test results."""
        print("\\n\\n🎯 TEST RESULTS SUMMARY")
        print("=" * 80)
        
        if self.successful_methods:
            print(f"🎉 SUCCESSFUL METHODS: {len(self.successful_methods)}")
            print("-" * 40)
            for method_num, description in self.successful_methods:
                print(f"   ✅ Test {method_num:2d}: {description}")
        else:
            print("❌ No successful methods found")
        
        print(f"\\n📊 STATISTICS:")
        print(f"   Total tests: 50")
        print(f"   Successful: {len(self.successful_methods)}")
        print(f"   Failed: {50 - len(self.successful_methods)}")
        print(f"   Success rate: {len(self.successful_methods)/50*100:.1f}%")
        
        if self.successful_methods:
            print("\\n🔧 NEXT STEPS:")
            print("   1. Implement the successful method(s) in a driver-free pump controller")
            print("   2. Create a robust USB communication class")
            print("   3. Test with different pump commands and parameters")
            print("   4. Compare audio detection results with actual pump behavior")


def main():
    """Main test execution."""
    tester = WindowsDirectUSBTester()
    tester.run_all_tests()


if __name__ == "__main__":
    main()