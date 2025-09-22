"""
Direct USB Communication Test with Audio Feedback
Attempts 50 different methods to communicate with the Bartels pump via USB
Uses audio detection to determine which methods actually work
"""

import usb.core
import usb.util
import usb.backend.libusb1
import time
import numpy as np
import sounddevice as sd
import logging
import sys
import os
from typing import List, Dict, Any, Optional
import struct

# Add src directory for audio detection
sys.path.append(os.path.join(os.path.dirname(__file__), 'src'))

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s [%(levelname)s] %(message)s')

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
        audio = sd.rec(int(self.duration * self.sample_rate), 
                      samplerate=self.sample_rate, channels=1)
        sd.wait()
        
        rms = np.sqrt(np.mean(audio.flatten()**2))
        ratio = rms / self.baseline_rms if self.baseline_rms > 0 else 0
        
        # Pump detected if audio is significantly louder than baseline
        detected = ratio > 1.5 and rms > 0.005
        print(f"   Audio RMS: {rms:.6f}, Ratio: {ratio:.2f}, Detected: {'YES' if detected else 'NO'}")
        return detected

class DirectUSBTester:
    """Tests direct USB communication with Bartels pump."""
    
    def __init__(self):
        self.audio = AudioDetector()
        self.device = None
        self.successful_methods = []
        self.test_results = []
        
        # Bartels pump identifiers
        self.vid = 0x0403  # FTDI
        self.pid = 0xB4C0  # Bartels specific
        
    def find_pump_device(self) -> bool:
        """Find the Bartels pump USB device."""
        print(f"🔍 Searching for Bartels pump (VID:{self.vid:04X}, PID:{self.pid:04X})...")
        
        try:
            self.device = usb.core.find(idVendor=self.vid, idProduct=self.pid)
            if self.device is None:
                print("❌ Pump device not found")
                return False
                
            print(f"✅ Found pump device: {self.device}")
            print(f"   Manufacturer: {usb.util.get_string(self.device, self.device.iManufacturer)}")
            print(f"   Product: {usb.util.get_string(self.device, self.device.iProduct)}")
            print(f"   Serial: {usb.util.get_string(self.device, self.device.iSerialNumber)}")
            return True
            
        except Exception as e:
            print(f"❌ Error finding device: {e}")
            return False
    
    def test_method(self, method_num: int, description: str, test_func) -> bool:
        """Test a specific communication method with audio feedback."""
        print(f"\n🧪 TEST {method_num:2d}/50: {description}")
        print("=" * 60)
        
        success = False
        error_msg = ""
        
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
            'audio_detected': pump_detected if 'pump_detected' in locals() else False,
            'error': error_msg
        })
        
        # Brief pause between tests
        time.sleep(1)
        return success
    
    def run_all_tests(self):
        """Run all 50 direct USB communication tests."""
        print("🚀 DIRECT USB COMMUNICATION TEST SUITE")
        print("=" * 60)
        print("Testing 50 different methods to communicate with Bartels pump")
        print("Using audio detection to identify successful communication")
        
        if not self.find_pump_device():
            return
            
        # Establish audio baseline
        self.audio.establish_baseline()
        
        # Test 1-10: Basic USB Control Transfers
        self.test_method(1, "Basic control transfer - GET_STATUS", 
                        lambda: self.device.ctrl_transfer(0x80, 0x00, 0, 0, 2))
        
        self.test_method(2, "Control transfer - SET_FEATURE", 
                        lambda: self.device.ctrl_transfer(0x00, 0x03, 1, 0))
        
        self.test_method(3, "Control transfer - CLEAR_FEATURE", 
                        lambda: self.device.ctrl_transfer(0x00, 0x01, 1, 0))
        
        self.test_method(4, "Vendor request - Custom 0x40", 
                        lambda: self.device.ctrl_transfer(0x40, 0x01, 0x0100, 0, b'F100'))
        
        self.test_method(5, "Vendor request - Custom 0x41", 
                        lambda: self.device.ctrl_transfer(0x41, 0x02, 0x0100, 0, b'A50'))
        
        # Test 6-15: FTDI-specific commands
        self.test_method(6, "FTDI Reset", 
                        lambda: self.device.ctrl_transfer(0x40, 0x00, 0, 0))
        
        self.test_method(7, "FTDI Set Baudrate 115200", 
                        lambda: self.device.ctrl_transfer(0x40, 0x03, 0x001A, 0x4138))
        
        self.test_method(8, "FTDI Set Data Characteristics", 
                        lambda: self.device.ctrl_transfer(0x40, 0x04, 0x0008, 0))
        
        self.test_method(9, "FTDI Set Flow Control", 
                        lambda: self.device.ctrl_transfer(0x40, 0x02, 0, 0))
        
        self.test_method(10, "FTDI Set DTR/RTS", 
                         lambda: self.device.ctrl_transfer(0x40, 0x01, 0x0303, 0))
        
        # Test 11-20: Direct endpoint writes
        self.test_method(11, "Bulk write 'F100' to EP1", 
                        lambda: self.write_to_endpoint(0x01, b'F100\\n'))
        
        self.test_method(12, "Bulk write 'A50' to EP1", 
                        lambda: self.write_to_endpoint(0x01, b'A50\\n'))
        
        self.test_method(13, "Bulk write 'bon' to EP1", 
                        lambda: self.write_to_endpoint(0x01, b'bon\\n'))
        
        self.test_method(14, "Interrupt write 'F100' to EP1", 
                        lambda: self.write_to_endpoint(0x01, b'F100\\n', use_interrupt=True))
        
        self.test_method(15, "Bulk write to EP2", 
                        lambda: self.write_to_endpoint(0x02, b'F100\\n'))
        
        # Test 16-25: Different data formats
        self.test_method(16, "Binary frequency command", 
                        lambda: self.write_to_endpoint(0x01, struct.pack('<H', 100)))
        
        self.test_method(17, "ASCII with CR", 
                        lambda: self.write_to_endpoint(0x01, b'F100\\r'))
        
        self.test_method(18, "ASCII with CRLF", 
                        lambda: self.write_to_endpoint(0x01, b'F100\\r\\n'))
        
        self.test_method(19, "Raw bytes [70, 49, 48, 48]", 
                        lambda: self.write_to_endpoint(0x01, bytes([70, 49, 48, 48])))
        
        self.test_method(20, "Hex encoded command", 
                        lambda: self.write_to_endpoint(0x01, bytes.fromhex('463130300A')))
        
        # Test 21-30: Configuration and interface claims
        self.test_method(21, "Set configuration 1", 
                        lambda: self.device.set_configuration(1))
        
        self.test_method(22, "Claim interface 0", 
                        lambda: usb.util.claim_interface(self.device, 0))
        
        self.test_method(23, "Claim interface 1", 
                        lambda: usb.util.claim_interface(self.device, 1))
        
        self.test_method(24, "Set interface alt setting", 
                        lambda: self.device.set_interface_altsetting(0, 0))
        
        self.test_method(25, "Reset device", 
                        lambda: self.device.reset())
        
        # Test 26-35: Advanced FTDI operations
        self.test_method(26, "FTDI Set Latency Timer", 
                        lambda: self.device.ctrl_transfer(0x40, 0x09, 16, 0))
        
        self.test_method(27, "FTDI Set Event Character", 
                        lambda: self.device.ctrl_transfer(0x40, 0x06, 0x0A, 0))
        
        self.test_method(28, "FTDI Set Error Character", 
                        lambda: self.device.ctrl_transfer(0x40, 0x07, 0x00, 0))
        
        self.test_method(29, "FTDI Purge RX Buffer", 
                        lambda: self.device.ctrl_transfer(0x40, 0x00, 1, 0))
        
        self.test_method(30, "FTDI Purge TX Buffer", 
                        lambda: self.device.ctrl_transfer(0x40, 0x00, 2, 0))
        
        # Test 31-40: Multi-step initialization sequences
        self.test_method(31, "Full FTDI init + F100", 
                        self.ftdi_init_sequence)
        
        self.test_method(32, "Reset + Config + Write", 
                        self.reset_config_write_sequence)
        
        self.test_method(33, "Bartels-specific init", 
                        self.bartels_init_sequence)
        
        self.test_method(34, "Serial emulation setup", 
                        self.serial_emulation_sequence)
        
        self.test_method(35, "Low-level UART setup", 
                        self.uart_setup_sequence)
        
        # Test 36-45: Protocol variations
        self.test_method(36, "Command with checksum", 
                        lambda: self.write_with_checksum(b'F100'))
        
        self.test_method(37, "Command with length prefix", 
                        lambda: self.write_with_length_prefix(b'F100'))
        
        self.test_method(38, "Escape sequence command", 
                        lambda: self.write_to_endpoint(0x01, b'\\x1b[F100'))
        
        self.test_method(39, "Binary protocol attempt", 
                        self.binary_protocol_attempt)
        
        self.test_method(40, "Modbus-style command", 
                        self.modbus_style_command)
        
        # Test 41-50: Creative attempts
        self.test_method(41, "Multiple endpoint write", 
                        self.multi_endpoint_write)
        
        self.test_method(42, "Timed sequence write", 
                        self.timed_sequence_write)
        
        self.test_method(43, "Broadcast to all endpoints", 
                        self.broadcast_to_endpoints)
        
        self.test_method(44, "USB descriptor modification", 
                        self.descriptor_modification_attempt)
        
        self.test_method(45, "Raw HID-style communication", 
                        self.hid_style_communication)
        
        self.test_method(46, "Custom USB class driver", 
                        self.custom_class_driver)
        
        self.test_method(47, "LibUSB direct transfer", 
                        self.libusb_direct_transfer)
        
        self.test_method(48, "Interrupt-driven communication", 
                        self.interrupt_driven_comm)
        
        self.test_method(49, "DMA-style bulk transfer", 
                        self.dma_bulk_transfer)
        
        self.test_method(50, "Kitchen sink approach", 
                        self.kitchen_sink_approach)
        
        # Print final results
        self.print_results()
    
    def write_to_endpoint(self, endpoint: int, data: bytes, use_interrupt: bool = False):
        """Write data to specific USB endpoint."""
        if use_interrupt:
            return self.device.write(0x80 | endpoint, data, timeout=1000)
        else:
            return self.device.write(endpoint, data, timeout=1000)
    
    def write_with_checksum(self, data: bytes):
        """Write data with simple checksum."""
        checksum = sum(data) & 0xFF
        return self.write_to_endpoint(0x01, data + bytes([checksum]))
    
    def write_with_length_prefix(self, data: bytes):
        """Write data with length prefix."""
        length = len(data)
        return self.write_to_endpoint(0x01, bytes([length]) + data)
    
    def ftdi_init_sequence(self):
        """Full FTDI initialization sequence."""
        # Reset
        self.device.ctrl_transfer(0x40, 0x00, 0, 0)
        time.sleep(0.1)
        # Set baudrate
        self.device.ctrl_transfer(0x40, 0x03, 0x001A, 0x4138)
        # Set data characteristics  
        self.device.ctrl_transfer(0x40, 0x04, 0x0008, 0)
        # Set flow control
        self.device.ctrl_transfer(0x40, 0x02, 0, 0)
        # Send command
        return self.write_to_endpoint(0x01, b'F100\\n')
    
    def reset_config_write_sequence(self):
        """Reset, configure, then write."""
        self.device.reset()
        time.sleep(0.1)
        self.device.set_configuration()
        return self.write_to_endpoint(0x01, b'bon\\n')
    
    def bartels_init_sequence(self):
        """Bartels-specific initialization."""
        # Custom Bartels initialization
        self.device.ctrl_transfer(0x40, 0x00, 0, 0)  # Reset
        self.device.ctrl_transfer(0x40, 0x03, 0x001A, 0x4138)  # 115200 baud
        self.device.ctrl_transfer(0x40, 0x01, 0x0101, 0)  # Set DTR
        time.sleep(0.1)
        # Send frequency command
        self.write_to_endpoint(0x01, b'F100\\n')
        time.sleep(0.1)
        # Send amplitude command  
        self.write_to_endpoint(0x01, b'A50\\n')
        time.sleep(0.1)
        # Turn on
        return self.write_to_endpoint(0x01, b'bon\\n')
    
    def serial_emulation_sequence(self):
        """Emulate serial port behavior."""
        # FTDI serial port emulation
        self.device.ctrl_transfer(0x40, 0x00, 0, 0)  # Reset
        self.device.ctrl_transfer(0x40, 0x03, 0x001A, 0x4138)  # Baudrate
        self.device.ctrl_transfer(0x40, 0x04, 0x0008, 0)  # 8N1
        self.device.ctrl_transfer(0x40, 0x01, 0x0303, 0)  # DTR+RTS
        return self.write_to_endpoint(0x01, b'bon\\n')
    
    def uart_setup_sequence(self):
        """Low-level UART setup."""
        # UART configuration
        self.device.ctrl_transfer(0x40, 0x00, 0, 0)  # Reset
        self.device.ctrl_transfer(0x40, 0x09, 1, 0)   # Set latency 1ms
        self.device.ctrl_transfer(0x40, 0x0B, 0, 0)   # Set bitmode
        return self.write_to_endpoint(0x01, b'F100\\nA50\\nbon\\n')
    
    def binary_protocol_attempt(self):
        """Try binary protocol."""
        # Binary command structure: [START][CMD][PARAM][END]
        cmd = bytes([0x7E, 0x01, 0x64, 0x00, 0x7F])  # Frequency 100
        return self.write_to_endpoint(0x01, cmd)
    
    def modbus_style_command(self):
        """Modbus-style command."""
        # [ADDR][FUNC][REG][DATA][CRC]
        cmd = bytes([0x01, 0x06, 0x00, 0x01, 0x00, 0x64, 0x99, 0x9E])
        return self.write_to_endpoint(0x01, cmd)
    
    def multi_endpoint_write(self):
        """Write to multiple endpoints."""
        self.write_to_endpoint(0x01, b'F100\\n')
        self.write_to_endpoint(0x02, b'A50\\n')
        return self.write_to_endpoint(0x01, b'bon\\n')
    
    def timed_sequence_write(self):
        """Timed sequence of commands."""
        self.write_to_endpoint(0x01, b'F100\\n')
        time.sleep(0.1)
        self.write_to_endpoint(0x01, b'A50\\n')
        time.sleep(0.1)
        return self.write_to_endpoint(0x01, b'bon\\n')
    
    def broadcast_to_endpoints(self):
        """Broadcast command to all possible endpoints."""
        cmd = b'bon\\n'
        for ep in range(1, 16):
            try:
                self.write_to_endpoint(ep, cmd)
            except:
                pass
        return True
    
    def descriptor_modification_attempt(self):
        """Attempt descriptor modification."""
        try:
            # This probably won't work but worth trying
            self.device.ctrl_transfer(0x00, 0x09, 1, 0)
            return self.write_to_endpoint(0x01, b'bon\\n')
        except:
            return False
    
    def hid_style_communication(self):
        """HID-style communication."""
        # Try HID-style reports
        report = bytes([0x01, 0x46, 0x31, 0x30, 0x30, 0x0A] + [0x00] * 58)  # 64-byte report
        return self.write_to_endpoint(0x01, report)
    
    def custom_class_driver(self):
        """Custom USB class driver attempt."""
        # Try custom class-specific requests
        self.device.ctrl_transfer(0x21, 0x20, 0, 0, b'F100\\nA50\\nbon\\n')
        return True
    
    def libusb_direct_transfer(self):
        """Direct libusb transfer."""
        # Try different transfer types
        try:
            self.device.ctrl_transfer(0x40, 0xFF, 0x0100, 0x0032, timeout=1000)
            return self.write_to_endpoint(0x01, b'bon\\n')
        except:
            return False
    
    def interrupt_driven_comm(self):
        """Interrupt-driven communication."""
        # Setup interrupt transfer
        try:
            self.device.write(0x81, b'bon\\n', timeout=1000)
            return True
        except:
            return False
    
    def dma_bulk_transfer(self):
        """DMA-style bulk transfer."""
        # Large bulk transfer
        data = b'F100\\nA50\\nbon\\n' * 100  # Repeat command many times
        return self.write_to_endpoint(0x01, data)
    
    def kitchen_sink_approach(self):
        """Try everything at once."""
        # Kitchen sink - try multiple approaches
        try:
            # Reset and configure
            self.device.reset()
            time.sleep(0.1)
            self.device.set_configuration()
            
            # FTDI setup
            self.device.ctrl_transfer(0x40, 0x00, 0, 0)
            self.device.ctrl_transfer(0x40, 0x03, 0x001A, 0x4138)
            self.device.ctrl_transfer(0x40, 0x04, 0x0008, 0)
            self.device.ctrl_transfer(0x40, 0x01, 0x0303, 0)
            
            # Multiple command attempts
            commands = [b'F100\\n', b'A50\\n', b'bon\\n']
            for cmd in commands:
                self.write_to_endpoint(0x01, cmd)
                time.sleep(0.1)
                
            return True
        except:
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
            print("   1. Implement the successful method(s) in a driver-free pump controller")
            print("   2. Create a robust USB communication class")
            print("   3. Test with different pump commands and parameters")


def main():
    """Main test execution."""
    tester = DirectUSBTester()
    tester.run_all_tests()


if __name__ == "__main__":
    main()