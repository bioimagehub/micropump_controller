#!/usr/bin/env python3
"""
TARGETED RADICAL DRIVER-FREE TESTS
==================================
Starting with the most promising methods that can be automated immediately.
"""

import time
import sys
import os
import subprocess
import ctypes
import logging
import numpy as np
import sounddevice as sd

# Add src directory for imports
sys.path.append(os.path.join(os.path.dirname(__file__), 'src'))

from pump import PumpController
from resolve_ports import find_pump_port_by_vid_pid

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s [%(levelname)s] %(message)s')

class TargetedRadicalTester:
    """Run the most promising radical tests first."""
    
    def __init__(self):
        self.successful_methods = []
        self.vid = 0x0403  # FTDI
        self.pid = 0xB4C0  # Bartels specific
        self.pump_port = None
        self.baseline_rms = None
        
    def establish_audio_baseline(self):
        """Record baseline audio."""
        print("📊 Establishing audio baseline...")
        time.sleep(1)
        
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
            
            detected = ratio > 1.05 and rms > 0.020
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

    def test_method(self, test_num: int, description: str, test_func) -> bool:
        """Test a method with automatic audio detection."""
        print(f"\\n🧪 TEST {test_num:2d}: {description}")
        print("-" * 60)
        
        try:
            result = test_func()
            
            if result:
                print("✅ Method executed successfully")
                time.sleep(0.5)
                pump_detected = self.detect_pump_sound()
                
                if pump_detected:
                    self.successful_methods.append((test_num, description))
                    print(f"🎉 SUCCESS: {description}")
                    return True
                else:
                    print("❌ No pump sound detected")
                    return False
            else:
                print("❌ Method failed to execute")
                return False
                
        except Exception as e:
            print(f"❌ Exception: {e}")
            return False

    # IMMEDIATELY TESTABLE METHODS
    
    def test_pyusb_direct(self) -> bool:
        """PyUSB direct USB communication."""
        try:
            import usb.core
            import usb.util
            
            # Find the pump device
            dev = usb.core.find(idVendor=self.vid, idProduct=self.pid)
            if dev is None:
                print("   Device not found via PyUSB")
                return False
            
            print(f"   Found device: {dev}")
            print(f"   Manufacturer: {usb.util.get_string(dev, dev.iManufacturer)}")
            print(f"   Product: {usb.util.get_string(dev, dev.iProduct)}")
            
            # Try to send control transfer
            try:
                # Set configuration
                dev.set_configuration()
                
                # Send pump commands via control transfer
                commands = [b'F100\\r', b'A100\\r', b'bon\\r']
                for cmd in commands:
                    dev.ctrl_transfer(0x40, 0x01, 0, 0, cmd)
                    time.sleep(0.2)
                
                print("   Sent pump commands via USB control transfer")
                return True
                
            except Exception as e:
                print(f"   USB communication error: {e}")
                return False
                
        except ImportError:
            print("   PyUSB not available")
            return False
        except Exception as e:
            print(f"   PyUSB error: {e}")
            return False

    def test_kernel32_deviceiocontrol(self) -> bool:
        """Direct DeviceIoControl Windows API calls."""
        try:
            import ctypes
            from ctypes import wintypes
            
            kernel32 = ctypes.windll.kernel32
            GENERIC_READ = 0x80000000
            GENERIC_WRITE = 0x40000000
            OPEN_EXISTING = 3
            
            # Open device handle
            device_path = f"\\\\.\\{self.pump_port}"
            handle = kernel32.CreateFileW(
                device_path,
                GENERIC_READ | GENERIC_WRITE,
                0, None, OPEN_EXISTING, 0, None
            )
            
            if handle == -1:
                print(f"   Could not open device handle for {device_path}")
                return False
            
            print(f"   Opened device handle: {handle}")
            
            # Try to write data directly
            data = b'F100\\rA100\\rbon\\r'
            bytes_written = wintypes.DWORD(0)
            
            success = kernel32.WriteFile(
                handle, data, len(data),
                ctypes.byref(bytes_written), None
            )
            
            if success:
                print(f"   Wrote {bytes_written.value} bytes via WriteFile")
                kernel32.CloseHandle(handle)
                return True
            else:
                error = kernel32.GetLastError()
                print(f"   WriteFile failed with error: {error}")
                kernel32.CloseHandle(handle)
                return False
                
        except Exception as e:
            print(f"   DeviceIoControl error: {e}")
            return False

    def test_wsl_direct_access(self) -> bool:
        """WSL direct COM port access."""
        try:
            # Map Windows COM port to WSL path
            wsl_device = f"/dev/ttyS{int(self.pump_port[3:]) - 1}"  # COM4 -> /dev/ttyS3
            
            cmd = [
                "wsl", "bash", "-c", 
                f"stty -F {wsl_device} 9600 raw -echo; " +
                f"echo -e 'F100\\rA100\\rbon\\r' > {wsl_device}"
            ]
            
            result = subprocess.run(cmd, timeout=10, capture_output=True, text=True)
            
            if result.returncode == 0:
                print(f"   Successfully sent commands via WSL to {wsl_device}")
                return True
            else:
                print(f"   WSL error: {result.stderr}")
                return False
                
        except Exception as e:
            print(f"   WSL access error: {e}")
            return False

    def test_setupapi_direct(self) -> bool:
        """SetupAPI for direct device access."""
        try:
            import ctypes
            from ctypes import wintypes
            
            setupapi = ctypes.windll.setupapi
            kernel32 = ctypes.windll.kernel32
            
            # GUID for serial ports
            GUID_DEVINTERFACE_COMPORT = "{86E0D1E0-8089-11D0-9CE4-08003E301F73}"
            
            # Get device information set
            guid = ctypes.create_string_buffer(GUID_DEVINTERFACE_COMPORT.encode())
            dev_info = setupapi.SetupDiGetClassDevsA(
                None, None, None, 0x00000012  # DIGCF_DEVICEINTERFACE | DIGCF_PRESENT
            )
            
            if dev_info != -1:
                print("   Enumerated devices via SetupAPI")
                setupapi.SetupDiDestroyDeviceInfoList(dev_info)
                return True
            else:
                print("   SetupAPI enumeration failed")
                return False
                
        except Exception as e:
            print(f"   SetupAPI error: {e}")
            return False

    def test_powershell_direct(self) -> bool:
        """PowerShell direct serial communication."""
        try:
            ps_script = f'''
$port = New-Object System.IO.Ports.SerialPort "{self.pump_port}", 9600
$port.Open()
$port.WriteLine("F100")
Start-Sleep -Milliseconds 200
$port.WriteLine("A100") 
Start-Sleep -Milliseconds 200
$port.WriteLine("bon")
Start-Sleep -Milliseconds 500
$port.Close()
Write-Host "Commands sent via PowerShell SerialPort"
'''
            
            cmd = ["powershell", "-Command", ps_script]
            result = subprocess.run(cmd, timeout=10, capture_output=True, text=True)
            
            if result.returncode == 0:
                print("   Successfully sent commands via PowerShell")
                return True
            else:
                print(f"   PowerShell error: {result.stderr}")
                return False
                
        except Exception as e:
            print(f"   PowerShell error: {e}")
            return False

    def run_immediate_tests(self):
        """Run tests that can be executed immediately."""
        print("🚀 TARGETED RADICAL DRIVER-FREE TESTS")
        print("=" * 60)
        print("Starting with methods that can be tested immediately...")
        print("=" * 60)
        
        if not self.find_pump_device():
            return
        
        if not self.establish_audio_baseline():
            print("⚠️ Warning: Could not establish audio baseline!")
        
        # Test positive control first
        print("\\n📍 POSITIVE CONTROL: Testing driver-based pump...")
        try:
            pump = PumpController(self.pump_port)
            pump.set_waveform("rectangle")
            pump.set_frequency(100)
            pump.set_voltage(100)
            pump.start()
            time.sleep(1)
            pump_detected = self.detect_pump_sound()
            pump.stop()
            pump.close()
            
            if pump_detected:
                print("✅ Positive control: Pump working with drivers")
            else:
                print("⚠️ WARNING: Positive control failed!")
                
        except Exception as e:
            print(f"❌ Positive control error: {e}")
        
        print("\\n" + "="*60)
        print("IMMEDIATE RADICAL TESTS")
        print("="*60)
        
        # Run immediate tests
        tests = [
            (1, "PyUSB direct USB communication", self.test_pyusb_direct),
            (2, "Kernel32 DeviceIoControl API", self.test_kernel32_deviceiocontrol),
            (3, "WSL direct COM port access", self.test_wsl_direct_access),
            (4, "SetupAPI direct device access", self.test_setupapi_direct),
            (5, "PowerShell SerialPort class", self.test_powershell_direct),
        ]
        
        for test_num, description, test_func in tests:
            success = self.test_method(test_num, description, test_func)
            time.sleep(1)  # Brief pause between tests
        
        # Print results
        self.print_results()
        
        # Next steps guidance
        self.print_next_steps()

    def print_results(self):
        """Print test results."""
        print("\\n\\n🎯 IMMEDIATE TEST RESULTS")
        print("=" * 50)
        
        if self.successful_methods:
            print(f"🎉 SUCCESSFUL METHODS: {len(self.successful_methods)}")
            for test_num, description in self.successful_methods:
                print(f"   ✅ Test {test_num}: {description}")
            
            print("\\n🔧 BREAKTHROUGH:")
            print("   🎉 Found working driver-free methods!")
            print("   📝 You can control pump without drivers!")
            
        else:
            print("❌ No immediate methods succeeded")
            print("\\n💡 NEXT STEPS:")
            print("   • Try Zadig driver replacement")
            print("   • Install additional tools (usbipd, Docker)")
            print("   • Test advanced hardware access methods")

    def print_next_steps(self):
        """Print guidance for next steps."""
        print("\\n\\n📋 NEXT STEPS FOR MANUAL INTERVENTION")
        print("=" * 60)
        
        print("\\n🔧 ZADIG DRIVER REPLACEMENT (Most Promising):")
        print("   1. Run: .\\delete\\utils\\zadig-2.9.exe")
        print("   2. Select your Bartels pump device")
        print("   3. Choose driver: WinUSB, libusb-win32, or libusbK")
        print("   4. Click 'Replace Driver'")
        print("   5. Re-run tests with new driver")
        
        print("\\n🐧 WSL2 + USBIPD SETUP:")
        print("   1. Install: winget install --interactive --exact dorssel.usbipd-win")
        print("   2. Run: usbipd wsl list")
        print("   3. Run: usbipd wsl attach --busid <your-device-id>")
        print("   4. Test in WSL: echo 'bon' > /dev/ttyUSB0")
        
        print("\\n🐳 DOCKER SETUP:")
        print("   1. Install Docker Desktop")
        print("   2. Enable WSL2 integration")
        print("   3. Test USB passthrough to containers")
        
        print("\\n💡 Let me know when you've completed any of these steps!")


def main():
    """Main test execution."""
    tester = TargetedRadicalTester()
    tester.run_immediate_tests()


if __name__ == "__main__":
    main()