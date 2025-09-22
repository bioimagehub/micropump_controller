"""
Driver vs Driver-Free USB Communication Test with Audio Detection
1. First tests with working driver-based pump controller (positive control)
2. Then tests 50 driver-free methods using only USB/serial communication
Uses automatic audio detection to identify successful methods
"""

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

# Import our working pump controller
from pump import PumpController
from resolve_ports import find_pump_port_by_vid_pid

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s [%(levelname)s] %(message)s')

class AudioDetector:
    """Audio detector for pump sounds."""
    
    def __init__(self):
        self.sample_rate = 22050
        self.duration = 1.5  # Shorter duration to avoid hanging
        self.baseline_rms = None
        
    def establish_baseline(self):
        """Record baseline audio."""
        print("📊 Establishing audio baseline (2 seconds of silence)...")
        print("   Please ensure pump is OFF and environment is quiet.")
        time.sleep(2)
        
        try:
            audio = sd.rec(int(self.duration * self.sample_rate), 
                          samplerate=self.sample_rate, channels=1)
            sd.wait()
            self.baseline_rms = np.sqrt(np.mean(audio.flatten()**2))
            print(f"   Baseline RMS: {self.baseline_rms:.6f}")
            return True
        except Exception as e:
            print(f"   Audio baseline error: {e}")
            return False
        
    def detect_pump_sound(self) -> bool:
        """Record audio and detect if pump is running."""
        try:
            audio = sd.rec(int(self.duration * self.sample_rate), 
                          samplerate=self.sample_rate, channels=1)
            sd.wait()
            
            rms = np.sqrt(np.mean(audio.flatten()**2))
            ratio = rms / self.baseline_rms if self.baseline_rms and self.baseline_rms > 0 else 0
            
            # Pump detected if audio is significantly louder than baseline
            detected = ratio > 1.8 and rms > 0.008  # Slightly higher thresholds
            print(f"   Audio RMS: {rms:.6f}, Ratio: {ratio:.2f}, Detected: {'YES' if detected else 'NO'}")
            return detected
        except Exception as e:
            print(f"   Audio detection error: {e}")
            return False

class DriverVsDriverFreeTester:
    """Tests driver-based vs driver-free communication."""
    
    def __init__(self):
        self.audio = AudioDetector()
        self.successful_methods = []
        self.test_results = []
        
        # Bartels pump identifiers
        self.vid = 0x0403  # FTDI
        self.pid = 0xB4C0  # Bartels specific
        self.pump_port = None
        
    def find_pump_device(self) -> bool:
        """Find the Bartels pump device."""
        print(f"🔍 Searching for Bartels pump (VID:{self.vid:04X}, PID:{self.pid:04X})...")
        
        try:
            self.pump_port = find_pump_port_by_vid_pid(self.vid, self.pid)
            print(f"✅ Found pump on: {self.pump_port}")
            return True
        except Exception as e:
            print(f"❌ Pump device not found: {e}")
            return False
    
    def test_driver_based_positive_control(self):
        """Test with our working driver-based pump controller."""
        print("\\n🧪 POSITIVE CONTROL: Testing with working driver-based pump")
        print("=" * 70)
        
        try:
            # Test 1: Driver-based pump OFF (should be quiet)
            print("\\n📍 Test 1: Driver-based pump OFF")
            pump_detected = self.audio.detect_pump_sound()
            print(f"   Result: Pump OFF - Audio detected: {'BAD' if pump_detected else 'GOOD'}")
            
            # Test 2: Driver-based pump ON (should make sound)
            print("\\n📍 Test 2: Driver-based pump ON")
            pump = PumpController(port=self.pump_port)
            
            # Configure and start pump
            pump.set_frequency(100)
            pump.set_voltage(50)
            pump.start()
            
            time.sleep(1)  # Let pump run briefly
            pump_detected = self.audio.detect_pump_sound()
            pump.stop()
            pump.close()
            
            print(f"   Result: Pump ON - Audio detected: {'GOOD' if pump_detected else 'BAD'}")
            
            if pump_detected:
                print("\\n✅ POSITIVE CONTROL PASSED: Audio detection is working!")
                print("   We can detect pump sounds with the driver-based controller.")
                return True
            else:
                print("\\n❌ POSITIVE CONTROL FAILED: Audio detection not working properly")
                print("   Check microphone, pump connection, or audio thresholds.")
                return False
                
        except Exception as e:
            print(f"\\n❌ Positive control error: {e}")
            return False
    
    def test_driver_free_method(self, method_num: int, description: str, test_func) -> bool:
        """Test a driver-free communication method."""
        print(f"\\n🧪 DRIVER-FREE TEST {method_num:2d}/50: {description}")
        print("-" * 60)
        
        success = False
        error_msg = ""
        pump_detected = False
        
        try:
            # Execute the test function
            result = test_func()
            
            if result:
                # Wait a moment then check for audio
                time.sleep(0.8)
                pump_detected = self.audio.detect_pump_sound()
                
                if pump_detected:
                    success = True
                    self.successful_methods.append((method_num, description))
                    print(f"🎉 SUCCESS: {description}")
                else:
                    print(f"❌ No pump sound detected")
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
            'audio_detected': pump_detected,
            'command_sent': result if 'result' in locals() else False,
            'error': error_msg
        })
        
        # Brief pause between tests
        time.sleep(0.5)
        return success
    
    def run_all_tests(self):
        """Run complete test suite."""
        print("🚀 DRIVER vs DRIVER-FREE USB COMMUNICATION TEST")
        print("=" * 70)
        print("Phase 1: Test with working driver (positive control)")
        print("Phase 2: Test 50 driver-free methods")
        print("Uses automatic audio detection to identify successful methods")
        
        if not self.find_pump_device():
            return
            
        # Establish audio baseline
        if not self.audio.establish_baseline():
            print("❌ Failed to establish audio baseline. Exiting.")
            return
        
        # Phase 1: Positive control with driver
        print("\\n" + "="*70)
        print("PHASE 1: POSITIVE CONTROL WITH WORKING DRIVER")
        print("="*70)
        
        if not self.test_driver_based_positive_control():
            print("\\n⚠️  Warning: Positive control failed!")
            print("   Audio detection may not be working properly.")
            print("   Continuing with driver-free tests anyway...")
        
        # Phase 2: Driver-free tests
        print("\\n" + "="*70)
        print("PHASE 2: DRIVER-FREE USB COMMUNICATION TESTS")
        print("="*70)
        print("Testing 50 different driver-free methods...")
        
        # Test 1-10: Basic direct serial commands
        self.test_driver_free_method(1, "Direct serial F100 command", 
                                   lambda: self.direct_serial_command(b'F100\\n'))
        
        self.test_driver_free_method(2, "Direct serial A50 command", 
                                   lambda: self.direct_serial_command(b'A50\\n'))
        
        self.test_driver_free_method(3, "Direct serial bon command", 
                                   lambda: self.direct_serial_command(b'bon\\n'))
        
        self.test_driver_free_method(4, "Direct serial boff command", 
                                   lambda: self.direct_serial_command(b'boff\\n'))
        
        self.test_driver_free_method(5, "Direct F100+A50+bon sequence", 
                                   lambda: self.direct_command_sequence())
        
        # Test 6-15: Different baudrates
        self.test_driver_free_method(6, "Direct bon at 9600 baud", 
                                   lambda: self.direct_serial_command(b'bon\\n', baudrate=9600))
        
        self.test_driver_free_method(7, "Direct bon at 57600 baud", 
                                   lambda: self.direct_serial_command(b'bon\\n', baudrate=57600))
        
        self.test_driver_free_method(8, "Direct bon at 230400 baud", 
                                   lambda: self.direct_serial_command(b'bon\\n', baudrate=230400))
        
        self.test_driver_free_method(9, "Direct bon at 460800 baud", 
                                   lambda: self.direct_serial_command(b'bon\\n', baudrate=460800))
        
        self.test_driver_free_method(10, "Direct bon at 921600 baud", 
                                    lambda: self.direct_serial_command(b'bon\\n', baudrate=921600))
        
        # Test 11-20: Different terminators  
        self.test_driver_free_method(11, "Direct bon with CR", 
                                   lambda: self.direct_serial_command(b'bon\\r'))
        
        self.test_driver_free_method(12, "Direct bon with CRLF", 
                                   lambda: self.direct_serial_command(b'bon\\r\\n'))
        
        self.test_driver_free_method(13, "Direct bon no terminator", 
                                   lambda: self.direct_serial_command(b'bon'))
        
        self.test_driver_free_method(14, "Direct bon null terminator", 
                                   lambda: self.direct_serial_command(b'bon\\x00'))
        
        self.test_driver_free_method(15, "Direct BON uppercase", 
                                   lambda: self.direct_serial_command(b'BON\\n'))
        
        # Test 16-25: Binary and protocol variations
        self.test_driver_free_method(16, "Direct bon as hex bytes", 
                                   lambda: self.direct_serial_command(bytes.fromhex('626F6E0A')))
        
        self.test_driver_free_method(17, "Direct bon individual bytes", 
                                   lambda: self.direct_serial_command(bytes([98, 111, 110, 10])))
        
        self.test_driver_free_method(18, "Direct binary frequency + bon", 
                                   lambda: self.direct_binary_freq_bon())
        
        self.test_driver_free_method(19, "Direct ASCII STX/ETX", 
                                   lambda: self.direct_serial_command(b'\\x02bon\\x03'))
        
        self.test_driver_free_method(20, "Direct length-prefixed bon", 
                                   lambda: self.direct_serial_command(b'\\x04bon\\n'))
        
        # Test 21-30: Hardware control variations
        self.test_driver_free_method(21, "Direct DTR/RTS control + bon", 
                                   lambda: self.direct_dtr_rts_control())
        
        self.test_driver_free_method(22, "Direct flow control disabled", 
                                   lambda: self.direct_flow_control_disabled())
        
        self.test_driver_free_method(23, "Direct buffer flush + bon", 
                                   lambda: self.direct_buffer_flush())
        
        self.test_driver_free_method(24, "Direct custom timeout", 
                                   lambda: self.direct_serial_command(b'bon\\n', timeout=5.0))
        
        self.test_driver_free_method(25, "Direct parity enabled", 
                                   lambda: self.direct_parity_enabled())
        
        # Test 26-35: Timing experiments
        self.test_driver_free_method(26, "Direct slow character sending", 
                                   lambda: self.direct_slow_char_sending())
        
        self.test_driver_free_method(27, "Direct fast burst sending", 
                                   lambda: self.direct_fast_burst())
        
        self.test_driver_free_method(28, "Direct repeated bon commands", 
                                   lambda: self.direct_serial_command(b'bon\\nbon\\nbon\\n'))
        
        self.test_driver_free_method(29, "Direct interleaved on/off", 
                                   lambda: self.direct_serial_command(b'bon\\nboff\\nbon\\n'))
        
        self.test_driver_free_method(30, "Direct long duration test", 
                                   lambda: self.direct_long_duration())
        
        # Test 31-40: Protocol experiments
        self.test_driver_free_method(31, "Direct modbus-style", 
                                   lambda: self.direct_modbus_style())
        
        self.test_driver_free_method(32, "Direct checksum protected", 
                                   lambda: self.direct_checksum_protected())
        
        self.test_driver_free_method(33, "Direct escape sequence", 
                                   lambda: self.direct_serial_command(b'\\x1b[bon'))
        
        self.test_driver_free_method(34, "Direct JSON-style", 
                                   lambda: self.direct_serial_command(b'{"cmd":"bon"}\\n'))
        
        self.test_driver_free_method(35, "Direct XML-style", 
                                   lambda: self.direct_serial_command(b'<cmd>bon</cmd>\\n'))
        
        # Test 36-45: Multiple approaches
        self.test_driver_free_method(36, "Direct double bon", 
                                   lambda: self.direct_serial_command(b'bon\\nbon\\n'))
        
        self.test_driver_free_method(37, "Direct triple bon", 
                                   lambda: self.direct_serial_command(b'bon\\nbon\\nbon\\n'))
        
        self.test_driver_free_method(38, "Direct all baudrates rapid", 
                                   lambda: self.direct_all_baudrates())
        
        self.test_driver_free_method(39, "Direct all terminators rapid", 
                                   lambda: self.direct_all_terminators())
        
        self.test_driver_free_method(40, "Direct mixed case variations", 
                                   lambda: self.direct_mixed_case())
        
        # Test 41-50: Creative attempts
        self.test_driver_free_method(41, "Direct reverse byte order", 
                                   lambda: self.direct_serial_command(b'nob\\n'))
        
        self.test_driver_free_method(42, "Direct spaces in command", 
                                   lambda: self.direct_serial_command(b'b o n\\n'))
        
        self.test_driver_free_method(43, "Direct AT command style", 
                                   lambda: self.direct_serial_command(b'AT+BON\\r\\n'))
        
        self.test_driver_free_method(44, "Direct Hayes command style", 
                                   lambda: self.direct_serial_command(b'+++BON\\r\\n'))
        
        self.test_driver_free_method(45, "Direct control characters", 
                                   lambda: self.direct_serial_command(b'\\x01bon\\x04\\n'))
        
        self.test_driver_free_method(46, "Direct long command line", 
                                   lambda: self.direct_serial_command(b'F100\\nA50\\nW1\\nbon\\n'))
        
        self.test_driver_free_method(47, "Direct command with delays", 
                                   lambda: self.direct_command_with_delays())
        
        self.test_driver_free_method(48, "Direct numbers and letters", 
                                   lambda: self.direct_serial_command(b'b0n\\n'))
        
        self.test_driver_free_method(49, "Direct ultimate sequence", 
                                   lambda: self.direct_ultimate_sequence())
        
        self.test_driver_free_method(50, "Direct kitchen sink", 
                                   lambda: self.direct_kitchen_sink())
        
        # Print final results
        self.print_results()
    
    def direct_serial_command(self, command: bytes, baudrate: int = 115200, timeout: float = 1.0) -> bool:
        """Send command via direct serial interface (no pump driver)."""
        try:
            import serial
            with serial.Serial(self.pump_port, baudrate=baudrate, timeout=timeout) as ser:
                ser.write(command)
                print(f"     Sent: {command} at {baudrate} baud")
                return True
        except Exception as e:
            print(f"     Error: {e}")
            return False
    
    def direct_command_sequence(self) -> bool:
        """Direct F100, A50, bon sequence."""
        try:
            import serial
            with serial.Serial(self.pump_port, 115200, timeout=1) as ser:
                commands = [b'F100\\n', b'A50\\n', b'bon\\n']
                for cmd in commands:
                    ser.write(cmd)
                    time.sleep(0.1)
                print("     Sent: F100 -> A50 -> bon sequence")
                return True
        except Exception as e:
            print(f"     Error: {e}")
            return False
    
    def direct_binary_freq_bon(self) -> bool:
        """Direct binary frequency + bon."""
        try:
            import serial
            with serial.Serial(self.pump_port, 115200, timeout=1) as ser:
                ser.write(bytes([0x64, 0x00]))  # 100 Hz as binary
                time.sleep(0.1)
                ser.write(b'bon\\n')
                print("     Sent: Binary 100Hz + bon")
                return True
        except Exception as e:
            print(f"     Error: {e}")
            return False
    
    def direct_dtr_rts_control(self) -> bool:
        """Direct DTR/RTS control."""
        try:
            import serial
            with serial.Serial(self.pump_port, 115200, timeout=1) as ser:
                ser.dtr = True
                ser.rts = True
                time.sleep(0.1)
                ser.write(b'bon\\n')
                print("     Sent: bon with DTR/RTS enabled")
                return True
        except Exception as e:
            print(f"     Error: {e}")
            return False
    
    def direct_flow_control_disabled(self) -> bool:
        """Direct flow control disabled."""
        try:
            import serial
            with serial.Serial(self.pump_port, 115200, timeout=1, 
                             rtscts=False, dsrdtr=False, xonxoff=False) as ser:
                ser.write(b'bon\\n')
                print("     Sent: bon with all flow control disabled")
                return True
        except Exception as e:
            print(f"     Error: {e}")
            return False
    
    def direct_buffer_flush(self) -> bool:
        """Direct buffer flush."""
        try:
            import serial
            with serial.Serial(self.pump_port, 115200, timeout=1) as ser:
                ser.reset_input_buffer()
                ser.reset_output_buffer()
                ser.write(b'bon\\n')
                ser.flush()
                print("     Sent: bon with buffer flush")
                return True
        except Exception as e:
            print(f"     Error: {e}")
            return False
    
    def direct_parity_enabled(self) -> bool:
        """Direct parity enabled."""
        try:
            import serial
            with serial.Serial(self.pump_port, 115200, timeout=1, parity=serial.PARITY_EVEN) as ser:
                ser.write(b'bon\\n')
                print("     Sent: bon with even parity")
                return True
        except Exception as e:
            print(f"     Error: {e}")
            return False
    
    def direct_slow_char_sending(self) -> bool:
        """Direct slow character sending."""
        try:
            import serial
            with serial.Serial(self.pump_port, 115200, timeout=1) as ser:
                for char in b'bon\\n':
                    ser.write(bytes([char]))
                    time.sleep(0.05)
                print("     Sent: bon with 50ms delays")
                return True
        except Exception as e:
            print(f"     Error: {e}")
            return False
    
    def direct_fast_burst(self) -> bool:
        """Direct fast burst."""
        try:
            import serial
            with serial.Serial(self.pump_port, 115200, timeout=1) as ser:
                for _ in range(5):
                    ser.write(b'bon\\n')
                    time.sleep(0.01)
                print("     Sent: 5 rapid bon commands")
                return True
        except Exception as e:
            print(f"     Error: {e}")
            return False
    
    def direct_long_duration(self) -> bool:
        """Direct long duration test."""
        try:
            import serial
            with serial.Serial(self.pump_port, 115200, timeout=1) as ser:
                ser.write(b'bon\\n')
                print("     Sent: bon (extended listening time)")
                time.sleep(2)  # Extra time for audio detection
                return True
        except Exception as e:
            print(f"     Error: {e}")
            return False
    
    def direct_modbus_style(self) -> bool:
        """Direct modbus-style."""
        cmd = bytes([0x01, 0x06, 0x00, 0x01, 0x00, 0x01, 0x99, 0x9A])
        print("     Sent: Modbus-style binary command")
        return self.direct_serial_command(cmd)
    
    def direct_checksum_protected(self) -> bool:
        """Direct checksum protected."""
        data = b'bon'
        checksum = sum(data) & 0xFF
        cmd = data + bytes([checksum]) + b'\\n'
        print("     Sent: bon with checksum")
        return self.direct_serial_command(cmd)
    
    def direct_all_baudrates(self) -> bool:
        """Direct all baudrates test."""
        baudrates = [9600, 19200, 38400, 57600, 115200, 230400]
        for baud in baudrates:
            try:
                import serial
                with serial.Serial(self.pump_port, baud, timeout=0.2) as ser:
                    ser.write(b'bon\\n')
                    time.sleep(0.1)
            except:
                continue
        print(f"     Sent: bon at {len(baudrates)} baudrates")
        return True
    
    def direct_all_terminators(self) -> bool:
        """Direct all terminators test."""
        terminators = [b'\\n', b'\\r', b'\\r\\n', b'\\x00', b'']
        for term in terminators:
            try:
                import serial
                with serial.Serial(self.pump_port, 115200, timeout=0.2) as ser:
                    ser.write(b'bon' + term)
                    time.sleep(0.1)
            except:
                continue
        print(f"     Sent: bon with {len(terminators)} terminators")
        return True
    
    def direct_mixed_case(self) -> bool:
        """Direct mixed case."""
        variations = [b'bon\\n', b'BON\\n', b'Bon\\n', b'bOn\\n']
        for var in variations:
            try:
                import serial
                with serial.Serial(self.pump_port, 115200, timeout=0.2) as ser:
                    ser.write(var)
                    time.sleep(0.1)
            except:
                continue
        print("     Sent: Mixed case variations")
        return True
    
    def direct_command_with_delays(self) -> bool:
        """Direct command with delays."""
        try:
            import serial
            with serial.Serial(self.pump_port, 115200, timeout=1) as ser:
                for char in b'F100\\nA50\\nbon\\n':
                    ser.write(bytes([char]))
                    time.sleep(0.02)
                print("     Sent: Full sequence with character delays")
                return True
        except Exception as e:
            print(f"     Error: {e}")
            return False
    
    def direct_ultimate_sequence(self) -> bool:
        """Direct ultimate sequence."""
        try:
            import serial
            with serial.Serial(self.pump_port, 115200, timeout=1) as ser:
                # Try the most complete pump activation sequence
                ser.reset_input_buffer()
                ser.reset_output_buffer()
                ser.dtr = True
                ser.rts = True
                time.sleep(0.1)
                
                commands = [b'F100\\n', b'A50\\n', b'W1\\n', b'bon\\n']
                for cmd in commands:
                    ser.write(cmd)
                    time.sleep(0.2)
                
                print("     Sent: Ultimate activation sequence")
                return True
        except Exception as e:
            print(f"     Error: {e}")
            return False
    
    def direct_kitchen_sink(self) -> bool:
        """Direct kitchen sink."""
        # Try multiple approaches
        success = False
        success |= self.direct_command_sequence()
        success |= self.direct_dtr_rts_control() 
        success |= self.direct_ultimate_sequence()
        print("     Tried: Multiple approaches")
        return success
    
    def print_results(self):
        """Print comprehensive test results."""
        print("\\n\\n🎯 FINAL TEST RESULTS")
        print("=" * 80)
        
        print("\\n📊 DRIVER-FREE METHOD RESULTS:")
        if self.successful_methods:
            print(f"🎉 SUCCESSFUL DRIVER-FREE METHODS: {len(self.successful_methods)}")
            print("-" * 50)
            for method_num, description in self.successful_methods:
                print(f"   ✅ Test {method_num:2d}: {description}")
                
            print("\\n🔧 IMPLICATIONS:")
            print("   🎉 SUCCESS! You can communicate with the pump WITHOUT drivers!")
            print("   📝 The successful methods use direct USB/serial communication")
            print("   🚀 You can create a driver-free pump controller")
            
        else:
            print("❌ No successful driver-free methods found")
            print("\\n💡 ANALYSIS:")
            print("   • The pump requires the Bartels driver for communication")
            print("   • Direct USB/serial protocols don't work")
            print("   • Stick with the current driver-based approach")
        
        print(f"\\n📊 STATISTICS:")
        print(f"   Total driver-free tests: 50")
        print(f"   Successful: {len(self.successful_methods)}")
        print(f"   Failed: {50 - len(self.successful_methods)}")
        print(f"   Success rate: {len(self.successful_methods)/50*100:.1f}%")


def main():
    """Main test execution."""
    tester = DriverVsDriverFreeTester()
    tester.run_all_tests()


if __name__ == "__main__":
    main()