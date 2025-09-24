"""
Driver vs Driver-Free USB Communication Test with Automatic Audio Detection
1. First tests with working driver-based pump controller (positive control)
2. Then tests driver-free methods using automatic audio detection
Uses sounddevice and numpy for automatic pump sound detection
"""

import time
import sys
import os
import logging
import numpy as np
import sounddevice as sd

# Add src directory for imports
sys.path.append(os.path.join(os.path.dirname(__file__), 'src'))

# Import our working pump controller
from pump import PumpController
from delete.resolve_ports import find_pump_port_by_vid_pid

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s [%(levelname)s] %(message)s')

class SimpleDriverFreeTester:
    """Test driver vs driver-free methods with automatic audio detection."""
    
    def __init__(self):
        self.successful_methods = []
        self.vid = 0x0403  # FTDI
        self.pid = 0xB4C0  # Bartels specific
        self.pump_port = None
        self.baseline_rms = None
        
    def establish_audio_baseline(self):
        """Record baseline audio."""
        print("📊 Establishing audio baseline (2 seconds of silence)...")
        print("   Please ensure pump is OFF and environment is quiet.")
        time.sleep(2)
        
        try:
            audio = sd.rec(int(1.5 * 22050), samplerate=22050, channels=1)
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
            print("   🎧 Listening for pump sounds (3 seconds)...")
            audio = sd.rec(int(3.0 * 22050), samplerate=22050, channels=1)
            sd.wait()
            
            rms = np.sqrt(np.mean(audio.flatten()**2))
            ratio = rms / self.baseline_rms if self.baseline_rms and self.baseline_rms > 0 else 0
            
            # Pump detected if audio is slightly louder than baseline (pump is quite quiet)
            detected = ratio > 1.05 and rms > 0.020  # Very sensitive thresholds for quiet pump
            print(f"   Audio RMS: {rms:.6f}, Ratio: {ratio:.2f}, Detected: {'YES' if detected else 'NO'}")
            return detected
        except Exception as e:
            print(f"   Audio detection error: {e}")
            return False
        
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
            pump_detected = self.detect_pump_sound()
            print(f"   Result: Pump OFF - Audio detected: {'BAD' if pump_detected else 'GOOD'}")
            
            # Test 2: Driver-based pump ON (should make sound)
            print("\\n📍 Test 2: Driver-based pump ON")
            if not self.pump_port:
                print("❌ No pump port available")
                return False
                
            pump = PumpController(port=self.pump_port)
            
            # Configure pump with proper settings for audible operation
            print("   Resetting pump...")
            time.sleep(0.5)
            print("   Setting waveform to RECTANGLE...")
            pump.set_waveform("RECT")
            time.sleep(0.5)
            print("   Setting frequency to 100 Hz...")
            pump.set_frequency(100)
            time.sleep(0.5)  # Longer delay
            print("   Setting voltage to 100V...")
            pump.set_voltage(100) 
            time.sleep(0.5)  # Longer delay
            print("   Starting pump...")
            pump.start()
            
            # Detect pump sound automatically
            pump_detected = self.detect_pump_sound()
            
            pump.stop()
            pump.close()
            
            print(f"   Result: Pump ON - Audio detected: {'GOOD' if pump_detected else 'BAD'}")
            
            if pump_detected:
                print("\\n✅ POSITIVE CONTROL PASSED: Audio detection is working!")
                return True
            else:
                print("\\n❌ POSITIVE CONTROL FAILED: Audio detection not working properly")
                return False
                
        except Exception as e:
            print(f"\\n❌ Positive control error: {e}")
            return False
    
    def test_driver_free_method(self, method_num: int, description: str, test_func) -> bool:
        """Test a driver-free communication method with automatic audio detection."""
        print(f"\\n🧪 DRIVER-FREE TEST {method_num:2d}: {description}")
        print("-" * 50)
        
        try:
            result = test_func()
            
            if result:
                print("✅ Command sent successfully")
                
                # Wait a moment then automatically detect audio
                time.sleep(0.5)
                pump_detected = self.detect_pump_sound()
                
                if pump_detected:
                    self.successful_methods.append((method_num, description))
                    print(f"🎉 SUCCESS: {description}")
                    return True
                else:
                    print("❌ No pump sound detected")
                    return False
            else:
                print("❌ Command failed to send")
                return False
                
        except Exception as e:
            print(f"❌ Exception: {e}")
            return False
    
    def run_key_tests(self):
        """Run key driver-free tests."""
        print("🚀 DRIVER vs DRIVER-FREE COMMUNICATION TEST")
        print("=" * 60)
        
        if not self.find_pump_device():
            return
        
        # Establish audio baseline first
        if not self.establish_audio_baseline():
            print("⚠️ Warning: Could not establish audio baseline!")
            
        # Phase 1: Test driver-based control
        print("\\n" + "="*60)
        print("PHASE 1: POSITIVE CONTROL WITH WORKING DRIVER")
        print("="*60)
        
        if not self.test_driver_based_positive_control():
            print("⚠️ Warning: Driver-based control failed!")
            return
        
        # Phase 2: Test key driver-free methods
        print("\\n" + "="*60)  
        print("PHASE 2: KEY DRIVER-FREE TESTS")
        print("="*60)
        print("Testing critical driver-free methods...")
        print("Listen carefully and respond y/n for each test.")
        
        print("\\nStarting driver-free tests automatically...")
        
        # Test most likely to work methods
        self.test_driver_free_method(1, "Direct serial bon command", 
                                   lambda: self.direct_serial_command(b'bon\\n'))
        
        self.test_driver_free_method(2, "Direct F100+A100+bon sequence", 
                                   lambda: self.direct_command_sequence())
        
        self.test_driver_free_method(3, "Direct bon with DTR/RTS control", 
                                   lambda: self.direct_dtr_rts_control())
        
        self.test_driver_free_method(4, "Direct bon with buffer flush", 
                                   lambda: self.direct_buffer_flush())
        
        self.test_driver_free_method(5, "Direct long duration bon", 
                                   lambda: self.direct_long_duration())
        
        self.test_driver_free_method(6, "Direct bon at 57600 baud", 
                                   lambda: self.direct_serial_command(b'bon\\n', baudrate=57600))
        
        self.test_driver_free_method(7, "Direct bon with CRLF", 
                                   lambda: self.direct_serial_command(b'bon\\r\\n'))
        
        self.test_driver_free_method(8, "Direct repeated bon commands", 
                                   lambda: self.direct_serial_command(b'bon\\nbon\\nbon\\n'))
        
        self.test_driver_free_method(9, "Direct slow character sending", 
                                   lambda: self.direct_slow_char_sending())
        
        self.test_driver_free_method(10, "Direct ultimate sequence", 
                                    lambda: self.direct_ultimate_sequence())
        
        # Print results
        self.print_results()
    
    def direct_serial_command(self, command: bytes, baudrate: int = 115200, timeout: float = 1.0) -> bool:
        """Send command via direct serial interface (no pump driver)."""
        try:
            import serial
            with serial.Serial(self.pump_port, baudrate=baudrate, timeout=timeout) as ser:
                ser.write(command)
                print(f"   Sent: {command} at {baudrate} baud")
                time.sleep(0.5)  # Give pump time to respond
                return True
        except Exception as e:
            print(f"   Error: {e}")
            return False
    
    def direct_command_sequence(self) -> bool:
        """Direct F100, A100, bon sequence."""
        try:
            import serial
            with serial.Serial(self.pump_port, 115200, timeout=1) as ser:
                commands = [b'F100\\n', b'A100\\n', b'bon\\n']
                for cmd in commands:
                    ser.write(cmd)
                    time.sleep(0.2)
                print("   Sent: F100 -> A100 -> bon sequence")
                return True
        except Exception as e:
            print(f"   Error: {e}")
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
                print("   Sent: bon with DTR/RTS enabled")
                time.sleep(0.5)
                return True
        except Exception as e:
            print(f"   Error: {e}")
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
                print("   Sent: bon with buffer flush")
                time.sleep(0.5)
                return True
        except Exception as e:
            print(f"   Error: {e}")
            return False
    
    def direct_long_duration(self) -> bool:
        """Direct long duration test."""
        try:
            import serial
            with serial.Serial(self.pump_port, 115200, timeout=1) as ser:
                ser.write(b'bon\\n')
                print("   Sent: bon (listen for 3 seconds)")
                time.sleep(3)  # Extra time to hear pump
                return True
        except Exception as e:
            print(f"   Error: {e}")
            return False
    
    def direct_slow_char_sending(self) -> bool:
        """Direct slow character sending."""
        try:
            import serial
            with serial.Serial(self.pump_port, 115200, timeout=1) as ser:
                for char in b'bon\\n':
                    ser.write(bytes([char]))
                    time.sleep(0.1)
                print("   Sent: bon with 100ms delays between characters")
                time.sleep(0.5)
                return True
        except Exception as e:
            print(f"   Error: {e}")
            return False
    
    def direct_ultimate_sequence(self) -> bool:
        """Direct ultimate sequence."""
        try:
            import serial
            with serial.Serial(self.pump_port, 115200, timeout=1) as ser:
                # Complete pump activation sequence
                ser.reset_input_buffer()
                ser.reset_output_buffer()
                ser.dtr = True
                ser.rts = True
                time.sleep(0.1)
                
                commands = [b'F100\\n', b'A100\\n', b'W1\\n', b'bon\\n']
                for cmd in commands:
                    ser.write(cmd)
                    time.sleep(0.3)
                
                print("   Sent: Ultimate activation sequence")
                time.sleep(1)  # Extra listening time
                return True
        except Exception as e:
            print(f"   Error: {e}")
            return False
    
    def print_results(self):
        """Print test results."""
        print("\\n\\n🎯 FINAL TEST RESULTS")
        print("=" * 60)
        
        if self.successful_methods:
            print(f"🎉 SUCCESSFUL DRIVER-FREE METHODS: {len(self.successful_methods)}")
            print("-" * 40)
            for method_num, description in self.successful_methods:
                print(f"   ✅ Test {method_num:2d}: {description}")
                
            print("\\n🔧 IMPLICATIONS:")
            print("   🎉 SUCCESS! You can communicate with pump WITHOUT drivers!")
            print("   📝 The successful methods use direct USB/serial communication")
            print("   🚀 You can create a driver-free pump controller using these methods")
            print("   💡 Consider implementing the successful methods in your main code")
            
        else:
            print("❌ No successful driver-free methods found")
            print("\\n💡 ANALYSIS:")
            print("   • The pump likely requires the Bartels driver for communication")
            print("   • Direct USB/serial protocols may not work with this pump model")
            print("   • Continue using the current driver-based approach")
            print("   • The working driver approach is still the best solution")
        
        print(f"\\n📊 STATISTICS:")
        print(f"   Driver-free tests: 10")
        print(f"   Successful: {len(self.successful_methods)}")
        print(f"   Success rate: {len(self.successful_methods)/10*100:.1f}%")


def main():
    """Main test execution."""
    tester = SimpleDriverFreeTester()
    tester.run_key_tests()


if __name__ == "__main__":
    main()