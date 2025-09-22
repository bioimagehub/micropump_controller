"""
Simplified Direct USB Communication Test
Tests 50 different methods to communicate with Bartels pump
Uses manual audio confirmation (you listen for pump sounds)
"""

import time
import logging
import sys
import os
import serial.tools.list_ports
from typing import List, Dict, Any, Optional
import ctypes
from ctypes import wintypes

# Add src directory for imports
sys.path.append(os.path.join(os.path.dirname(__file__), 'src'))

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s [%(levelname)s] %(message)s')

class ManualAudioTester:
    """Tests direct USB communication with manual audio confirmation."""
    
    def __init__(self):
        self.successful_methods = []
        self.test_results = []
        
        # Bartels pump identifiers
        self.vid = 0x0403  # FTDI
        self.pid = 0xB4C0  # Bartels specific
        self.pump_port = None
        
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
        """Test a specific communication method."""
        print(f"\\n🧪 TEST {method_num:2d}/50: {description}")
        print("=" * 60)
        
        success = False
        error_msg = ""
        
        try:
            # Execute the test function
            result = test_func()
            if result:
                print(f"✅ Command executed successfully")
                # Ask user for manual confirmation
                print("🎧 LISTEN: Did you hear the pump make a sound? (y/n): ", end="")
                user_input = input().lower().strip()
                if user_input in ['y', 'yes']:
                    success = True
                    self.successful_methods.append((method_num, description))
                    print(f"🎉 SUCCESS: {description}")
                else:
                    print(f"❌ No pump sound detected by user")
            else:
                print(f"❌ Command execution failed")
                
        except Exception as e:
            error_msg = str(e)
            print(f"❌ Exception: {error_msg}")
        
        # Record results
        self.test_results.append({
            'method': method_num,
            'description': description,
            'success': success,
            'executed': result if 'result' in locals() else False,
            'error': error_msg
        })
        
        return success
    
    def run_all_tests(self):
        """Run all 50 direct USB communication tests."""
        print("🚀 MANUAL AUDIO CONFIRMATION USB TEST SUITE")
        print("=" * 60)
        print("Testing 50 different methods to communicate with Bartels pump")
        print("You will manually confirm if you hear pump sounds")
        print("\\n🎧 INSTRUCTIONS:")
        print("   - Listen carefully for pump sounds during each test")
        print("   - Type 'y' if you hear pump sounds, 'n' if you don't")
        print("   - The pump should make a clicking or humming sound when active")
        
        if not self.find_pump_device():
            return
        
        input("\\nPress Enter when ready to start testing...")
        
        # Test 1-10: Basic Serial Commands
        self.test_method(1, "Standard serial F100 command", 
                        lambda: self.serial_command(b'F100\\n'))
        
        self.test_method(2, "Standard serial A50 command", 
                        lambda: self.serial_command(b'A50\\n'))
        
        self.test_method(3, "Standard serial bon command (SHOULD WORK)", 
                        lambda: self.serial_command(b'bon\\n'))
        
        self.test_method(4, "Standard serial boff command", 
                        lambda: self.serial_command(b'boff\\n'))
        
        self.test_method(5, "Serial F100+A50+bon sequence", 
                        lambda: self.multi_command_sequence())
        
        # Test 6-15: Different baudrates
        self.test_method(6, "bon command at 9600 baud", 
                        lambda: self.serial_command(b'bon\\n', baudrate=9600))
        
        self.test_method(7, "bon command at 57600 baud", 
                        lambda: self.serial_command(b'bon\\n', baudrate=57600))
        
        self.test_method(8, "bon command at 230400 baud", 
                        lambda: self.serial_command(b'bon\\n', baudrate=230400))
        
        self.test_method(9, "bon command at 460800 baud", 
                        lambda: self.serial_command(b'bon\\n', baudrate=460800))
        
        self.test_method(10, "bon command at 921600 baud", 
                         lambda: self.serial_command(b'bon\\n', baudrate=921600))
        
        # Test 11-20: Different terminators
        self.test_method(11, "bon with CR terminator", 
                        lambda: self.serial_command(b'bon\\r'))
        
        self.test_method(12, "bon with CRLF terminator", 
                        lambda: self.serial_command(b'bon\\r\\n'))
        
        self.test_method(13, "bon with no terminator", 
                        lambda: self.serial_command(b'bon'))
        
        self.test_method(14, "bon with null terminator", 
                        lambda: self.serial_command(b'bon\\x00'))
        
        self.test_method(15, "BON uppercase", 
                        lambda: self.serial_command(b'BON\\n'))
        
        # Test 16-25: Binary variations
        self.test_method(16, "bon as hex bytes", 
                        lambda: self.serial_command(bytes.fromhex('626F6E0A')))
        
        self.test_method(17, "bon as individual bytes", 
                        lambda: self.serial_command(bytes([98, 111, 110, 10])))
        
        self.test_method(18, "Binary frequency + bon", 
                        lambda: self.binary_freq_bon())
        
        self.test_method(19, "ASCII with STX/ETX", 
                        lambda: self.serial_command(b'\\x02bon\\x03'))
        
        self.test_method(20, "Length-prefixed bon", 
                        lambda: self.serial_command(b'\\x04bon\\n'))
        
        # Test 21-30: FTDI-specific
        self.test_method(21, "DTR/RTS control + bon", 
                        lambda: self.dtr_rts_control())
        
        self.test_method(22, "Flow control disabled + bon", 
                        lambda: self.flow_control_disabled())
        
        self.test_method(23, "Buffer flush + bon", 
                        lambda: self.buffer_flush_bon())
        
        self.test_method(24, "Custom timeout + bon", 
                        lambda: self.custom_timeout_bon())
        
        self.test_method(25, "Parity enabled + bon", 
                        lambda: self.parity_enabled_bon())
        
        # Test 26-35: Timing variations
        self.test_method(26, "Slow character sending", 
                        lambda: self.slow_char_sending())
        
        self.test_method(27, "Fast burst sending", 
                        lambda: self.fast_burst_sending())
        
        self.test_method(28, "Repeated bon commands", 
                        lambda: self.repeated_bon_commands())
        
        self.test_method(29, "Interleaved on/off", 
                        lambda: self.interleaved_on_off())
        
        self.test_method(30, "Long duration bon", 
                        lambda: self.long_duration_bon())
        
        # Test 31-40: Protocol experiments
        self.test_method(31, "Modbus-style command", 
                        lambda: self.modbus_style_command())
        
        self.test_method(32, "Checksum-protected bon", 
                        lambda: self.checksum_protected_bon())
        
        self.test_method(33, "Escape sequence bon", 
                        lambda: self.serial_command(b'\\x1b[bon'))
        
        self.test_method(34, "JSON-style command", 
                        lambda: self.serial_command(b'{"cmd":"bon"}\\n'))
        
        self.test_method(35, "XML-style command", 
                        lambda: self.serial_command(b'<cmd>bon</cmd>\\n'))
        
        # Test 36-45: Multiple attempts
        self.test_method(36, "Double bon command", 
                        lambda: self.serial_command(b'bon\\nbon\\n'))
        
        self.test_method(37, "Triple bon command", 
                        lambda: self.serial_command(b'bon\\nbon\\nbon\\n'))
        
        self.test_method(38, "All ports broadcast", 
                        lambda: self.all_ports_broadcast())
        
        self.test_method(39, "All baudrates rapid test", 
                        lambda: self.all_baudrates_rapid())
        
        self.test_method(40, "All terminators rapid test", 
                        lambda: self.all_terminators_rapid())
        
        # Test 41-50: Creative attempts
        self.test_method(41, "Reverse byte order", 
                        lambda: self.serial_command(b'nob\\n'))
        
        self.test_method(42, "Spaces in command", 
                        lambda: self.serial_command(b'b o n\\n'))
        
        self.test_method(43, "Command with delays", 
                        lambda: self.command_with_delays())
        
        self.test_method(44, "Mixed case variations", 
                        lambda: self.mixed_case_variations())
        
        self.test_method(45, "Numbers and letters", 
                        lambda: self.serial_command(b'b0n\\n'))
        
        self.test_method(46, "AT command style", 
                        lambda: self.serial_command(b'AT+BON\\r\\n'))
        
        self.test_method(47, "Hayes command style", 
                        lambda: self.serial_command(b'+++BON\\r\\n'))
        
        self.test_method(48, "Control characters", 
                        lambda: self.serial_command(b'\\x01bon\\x04\\n'))
        
        self.test_method(49, "Long command line", 
                        lambda: self.serial_command(b'F100\\nA50\\nW1\\nbon\\n'))
        
        self.test_method(50, "Kitchen sink ultimate", 
                        lambda: self.kitchen_sink_ultimate())
        
        # Print final results
        self.print_results()
    
    def serial_command(self, command: bytes, baudrate: int = 115200, timeout: float = 1.0) -> bool:
        """Send command via standard serial interface."""
        try:
            import serial
            with serial.Serial(self.pump_port, baudrate=baudrate, timeout=timeout) as ser:
                ser.write(command)
                time.sleep(0.1)
                print(f"   Sent: {command} at {baudrate} baud")
                return True
        except Exception as e:
            print(f"   Serial error: {e}")
            return False
    
    def multi_command_sequence(self) -> bool:
        """Send F100, A50, then bon."""
        try:
            import serial
            with serial.Serial(self.pump_port, 115200, timeout=1) as ser:
                commands = [b'F100\\n', b'A50\\n', b'bon\\n']
                for cmd in commands:
                    ser.write(cmd)
                    time.sleep(0.1)
                print("   Sent: F100, A50, bon sequence")
                return True
        except Exception as e:
            print(f"   Error: {e}")
            return False
    
    def binary_freq_bon(self) -> bool:
        """Binary frequency command + bon."""
        try:
            import serial
            with serial.Serial(self.pump_port, 115200, timeout=1) as ser:
                # Binary frequency (100 Hz as 16-bit)
                ser.write(bytes([0x64, 0x00]))  # 100 in little endian
                time.sleep(0.1)
                ser.write(b'bon\\n')
                print("   Sent: Binary frequency + bon")
                return True
        except Exception as e:
            print(f"   Error: {e}")
            return False
    
    def dtr_rts_control(self) -> bool:
        """DTR/RTS control + bon."""
        try:
            import serial
            with serial.Serial(self.pump_port, 115200, timeout=1) as ser:
                ser.dtr = True
                ser.rts = True
                time.sleep(0.1)
                ser.write(b'bon\\n')
                print("   Sent: bon with DTR/RTS enabled")
                return True
        except Exception as e:
            print(f"   Error: {e}")
            return False
    
    def flow_control_disabled(self) -> bool:
        """Flow control disabled + bon."""
        try:
            import serial
            with serial.Serial(self.pump_port, 115200, timeout=1, 
                             rtscts=False, dsrdtr=False, xonxoff=False) as ser:
                ser.write(b'bon\\n')
                print("   Sent: bon with flow control disabled")
                return True
        except Exception as e:
            print(f"   Error: {e}")
            return False
    
    def buffer_flush_bon(self) -> bool:
        """Buffer flush + bon."""
        try:
            import serial
            with serial.Serial(self.pump_port, 115200, timeout=1) as ser:
                ser.reset_input_buffer()
                ser.reset_output_buffer()
                ser.write(b'bon\\n')
                ser.flush()
                print("   Sent: bon with buffer flush")
                return True
        except Exception as e:
            print(f"   Error: {e}")
            return False
    
    def custom_timeout_bon(self) -> bool:
        """Custom timeout + bon."""
        return self.serial_command(b'bon\\n', timeout=5.0)
    
    def parity_enabled_bon(self) -> bool:
        """Parity enabled + bon."""
        try:
            import serial
            with serial.Serial(self.pump_port, 115200, timeout=1, parity=serial.PARITY_EVEN) as ser:
                ser.write(b'bon\\n')
                print("   Sent: bon with even parity")
                return True
        except Exception as e:
            print(f"   Error: {e}")
            return False
    
    def slow_char_sending(self) -> bool:
        """Send characters slowly."""
        try:
            import serial
            with serial.Serial(self.pump_port, 115200, timeout=1) as ser:
                for char in b'bon\\n':
                    ser.write(bytes([char]))
                    time.sleep(0.05)  # 50ms between characters
                print("   Sent: bon with 50ms delays between characters")
                return True
        except Exception as e:
            print(f"   Error: {e}")
            return False
    
    def fast_burst_sending(self) -> bool:
        """Send rapid bursts."""
        try:
            import serial
            with serial.Serial(self.pump_port, 115200, timeout=1) as ser:
                for _ in range(5):
                    ser.write(b'bon\\n')
                    time.sleep(0.01)  # 10ms between bursts
                print("   Sent: 5 rapid bon commands")
                return True
        except Exception as e:
            print(f"   Error: {e}")
            return False
    
    def repeated_bon_commands(self) -> bool:
        """Repeated bon commands."""
        return self.serial_command(b'bon\\nbon\\nbon\\nbon\\nbon\\n')
    
    def interleaved_on_off(self) -> bool:
        """Interleaved on/off."""
        return self.serial_command(b'bon\\nboff\\nbon\\nboff\\nbon\\n')
    
    def long_duration_bon(self) -> bool:
        """Long duration bon."""
        try:
            import serial
            with serial.Serial(self.pump_port, 115200, timeout=1) as ser:
                ser.write(b'bon\\n')
                print("   Sent: bon (listening for 3 seconds...)")
                time.sleep(3)  # Give more time to hear pump
                ser.write(b'boff\\n')
                return True
        except Exception as e:
            print(f"   Error: {e}")
            return False
    
    def modbus_style_command(self) -> bool:
        """Modbus-style command."""
        cmd = bytes([0x01, 0x06, 0x00, 0x01, 0x00, 0x01, 0x99, 0x9A])
        return self.serial_command(cmd)
    
    def checksum_protected_bon(self) -> bool:
        """Checksum-protected bon."""
        data = b'bon'
        checksum = sum(data) & 0xFF
        cmd = data + bytes([checksum]) + b'\\n'
        return self.serial_command(cmd)
    
    def all_ports_broadcast(self) -> bool:
        """Broadcast to all ports."""
        ports = ['COM1', 'COM2', 'COM3', 'COM4', 'COM5', 'COM6', 'COM7', 'COM8']
        success = False
        for port in ports:
            try:
                import serial
                with serial.Serial(port, 115200, timeout=0.1) as ser:
                    ser.write(b'bon\\n')
                    success = True
            except:
                continue
        print(f"   Broadcast bon to {len(ports)} ports")
        return success
    
    def all_baudrates_rapid(self) -> bool:
        """All baudrates rapid test."""
        baudrates = [9600, 19200, 38400, 57600, 115200, 230400]
        success = False
        for baud in baudrates:
            try:
                import serial
                with serial.Serial(self.pump_port, baud, timeout=0.1) as ser:
                    ser.write(b'bon\\n')
                    time.sleep(0.1)
                    success = True
            except:
                continue
        print(f"   Tested bon at {len(baudrates)} baudrates")
        return success
    
    def all_terminators_rapid(self) -> bool:
        """All terminators rapid test."""
        terminators = [b'\\n', b'\\r', b'\\r\\n', b'\\x00', b'']
        success = False
        for term in terminators:
            try:
                import serial
                with serial.Serial(self.pump_port, 115200, timeout=0.1) as ser:
                    ser.write(b'bon' + term)
                    time.sleep(0.1)
                    success = True
            except:
                continue
        print(f"   Tested bon with {len(terminators)} terminators")
        return success
    
    def command_with_delays(self) -> bool:
        """Command with delays."""
        try:
            import serial
            with serial.Serial(self.pump_port, 115200, timeout=1) as ser:
                ser.write(b'F')
                time.sleep(0.1)
                ser.write(b'100\\n')
                time.sleep(0.1)
                ser.write(b'A')
                time.sleep(0.1)
                ser.write(b'50\\n')
                time.sleep(0.1)
                ser.write(b'bon\\n')
                print("   Sent: Delayed character sequence")
                return True
        except Exception as e:
            print(f"   Error: {e}")
            return False
    
    def mixed_case_variations(self) -> bool:
        """Mixed case variations."""
        variations = [b'bon\\n', b'BON\\n', b'Bon\\n', b'bOn\\n', b'boN\\n']
        success = False
        for var in variations:
            try:
                import serial
                with serial.Serial(self.pump_port, 115200, timeout=0.1) as ser:
                    ser.write(var)
                    time.sleep(0.1)
                    success = True
            except:
                continue
        print(f"   Tested {len(variations)} case variations")
        return success
    
    def kitchen_sink_ultimate(self) -> bool:
        """Ultimate kitchen sink approach."""
        try:
            # Try multiple approaches rapidly
            approaches = [
                lambda: self.serial_command(b'bon\\n'),
                lambda: self.multi_command_sequence(),
                lambda: self.dtr_rts_control(),
                lambda: self.long_duration_bon(),
                lambda: self.all_baudrates_rapid()
            ]
            
            success = False
            for approach in approaches:
                try:
                    if approach():
                        success = True
                        time.sleep(0.5)
                except:
                    continue
            
            print("   Tried ultimate kitchen sink approach")
            return success
        except Exception as e:
            print(f"   Error: {e}")
            return False
    
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
            print("   1. The successful methods can communicate with the pump!")
            print("   2. Implement these methods in a driver-free pump controller")
            print("   3. Test with automated audio detection system")
            print("   4. Create a robust communication library")


def main():
    """Main test execution."""
    tester = ManualAudioTester()
    tester.run_all_tests()


if __name__ == "__main__":
    main()