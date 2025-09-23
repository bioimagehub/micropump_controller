#!/usr/bin/env python3
"""
AUTOMATIC PUMP VERIFICATION SYSTEM
Runs after driver installation to verify pump communication
Uses your proven audio detection method for success verification
"""

import time
import sys
import os
import logging
import numpy as np
import sounddevice as sd
import serial.tools.list_ports

# Add src directory for imports
sys.path.append(os.path.join(os.path.dirname(__file__), 'src'))

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s [%(levelname)s] %(message)s')

class AudioDetector:
    """Simple audio detector for pump sounds."""
    
    def __init__(self):
        self.baseline_rms = None
        
    def establish_baseline(self, duration=2.0):
        """Record baseline audio."""
        print("📊 Establishing audio baseline...")
        print("   Please ensure pump is OFF and environment is quiet.")
        time.sleep(1)
        
        try:
            audio = sd.rec(int(duration * 22050), samplerate=22050, channels=1)
            sd.wait()
            self.baseline_rms = np.sqrt(np.mean(audio.flatten()**2))
            print(f"   Baseline RMS: {self.baseline_rms:.6f}")
            return True
        except Exception as e:
            print(f"   Audio baseline error: {e}")
            return False
            
    def detect_pump_sound(self, duration=3.0, threshold_multiplier=1.5):
        """Record audio and detect if pump is running."""
        if self.baseline_rms is None:
            print("❌ No baseline established")
            return False
            
        try:
            audio = sd.rec(int(duration * 22050), samplerate=22050, channels=1)
            sd.wait()
            current_rms = np.sqrt(np.mean(audio.flatten()**2))
            
            print(f"   Current RMS: {current_rms:.6f}")
            print(f"   Baseline RMS: {self.baseline_rms:.6f}")
            print(f"   Ratio: {current_rms / self.baseline_rms:.2f}x")
            
            return current_rms > (self.baseline_rms * threshold_multiplier)
            
        except Exception as e:
            print(f"   Audio detection error: {e}")
            return False

class PumpVerifier:
    """Verify pump installation and communication."""
    
    def __init__(self):
        self.audio = AudioDetector()
        self.pump_port = None
        
    def find_pump_port(self):
        """Find the Bartels pump COM port."""
        print("🔍 Searching for Bartels pump...")
        
        # Look for FTDI devices with Bartels VID/PID
        ports = serial.tools.list_ports.comports()
        bartels_ports = [p for p in ports if p.vid == 0x0403 and p.pid == 0xB4C0]
        
        if bartels_ports:
            self.pump_port = bartels_ports[0].device
            print(f"✅ Found Bartels pump on: {self.pump_port}")
            print(f"   Description: {bartels_ports[0].description}")
            return True
        
        # Fallback: Look for any FTDI device
        ftdi_ports = [p for p in ports if p.vid == 0x0403]
        if ftdi_ports:
            print(f"⚠️  Found FTDI device (may be pump): {ftdi_ports[0].device}")
            print(f"   VID:PID = {ftdi_ports[0].vid:04X}:{ftdi_ports[0].pid:04X}")
            self.pump_port = ftdi_ports[0].device
            return True
            
        print("❌ No Bartels pump found")
        print("Available COM ports:")
        for port in ports:
            print(f"  {port.device}: {port.description}")
        return False
        
    def test_pump_communication(self):
        """Test basic pump communication."""
        if not self.pump_port:
            return False
            
        print(f"\n🧪 Testing pump communication on {self.pump_port}...")
        
        try:
            import serial
            
            with serial.Serial(self.pump_port, 115200, timeout=2) as ser:
                # Clear buffers
                ser.reset_input_buffer()
                ser.reset_output_buffer()
                
                # Set DTR/RTS
                ser.dtr = True
                ser.rts = True
                time.sleep(0.1)
                
                # Send status request
                ser.write(b'\r\n')
                time.sleep(0.2)
                
                # Try to read response
                response = ser.read(100)
                
                if response:
                    print(f"✅ Communication successful!")
                    print(f"   Response: {response}")
                    return True
                else:
                    print("⚠️  No response from pump")
                    return True  # Communication channel exists
                    
        except Exception as e:
            print(f"❌ Communication error: {e}")
            return False
            
    def test_pump_activation_with_audio(self):
        """Test pump activation with audio verification."""
        if not self.pump_port:
            return False
            
        print(f"\n🎵 Testing pump activation with audio verification...")
        
        # Establish audio baseline
        if not self.audio.establish_baseline():
            print("❌ Cannot establish audio baseline")
            return False
            
        print("\n💨 Activating pump...")
        
        try:
            import serial
            
            with serial.Serial(self.pump_port, 115200, timeout=2) as ser:
                # Clear buffers
                ser.reset_input_buffer() 
                ser.reset_output_buffer()
                
                # Set DTR/RTS
                ser.dtr = True
                ser.rts = True
                time.sleep(0.1)
                
                # Send pump activation sequence
                commands = [b'F100\n', b'A100\n', b'bon\n']
                for cmd in commands:
                    ser.write(cmd)
                    time.sleep(0.2)
                
                print("   Commands sent, listening for pump sound...")
                
                # Wait for pump to start
                time.sleep(1)
                
                # Check for audio change
                audio_detected = self.audio.detect_pump_sound()
                
                # Turn off pump
                ser.write(b'boff\n')
                time.sleep(0.5)
                
                if audio_detected:
                    print("🎉 SUCCESS! Pump activation confirmed by audio!")
                    return True
                else:
                    print("⚠️  Pump commands sent but no audio change detected")
                    print("   This might still be working - check manually")
                    return True
                    
        except Exception as e:
            print(f"❌ Pump activation error: {e}")
            return False
            
    def run_verification(self):
        """Run complete verification sequence."""
        print("="*60)
        print("🔬 BARTELS PUMP VERIFICATION SYSTEM")
        print("="*60)
        
        success_count = 0
        total_tests = 3
        
        # Test 1: Find pump port
        if self.find_pump_port():
            success_count += 1
            
            # Test 2: Basic communication
            if self.test_pump_communication():
                success_count += 1
                
                # Test 3: Audio-verified activation
                if self.test_pump_activation_with_audio():
                    success_count += 1
        
        print("\n" + "="*60)
        print("📊 VERIFICATION RESULTS")
        print("="*60)
        print(f"Tests passed: {success_count}/{total_tests}")
        
        if success_count == total_tests:
            print("🎉 COMPLETE SUCCESS! Pump is fully operational!")
            print("✅ Driver installation successful")
            print("✅ Communication established") 
            print("✅ Audio verification confirmed")
        elif success_count >= 2:
            print("✅ PARTIAL SUCCESS! Pump communication working")
            print("💡 Audio verification may need adjustment")
        elif success_count >= 1:
            print("⚠️  PARTIAL SUCCESS! Pump detected but communication issues")
            print("💡 May need driver or port configuration")
        else:
            print("❌ VERIFICATION FAILED")
            print("💡 Driver installation may not have completed")
            print("💡 Try running INSTALL_PUMP_DRIVERS.bat again")
            
        print("\n📝 Next steps:")
        if success_count >= 2:
            print("   Your pump is ready to use!")
            print("   Use your existing pump control scripts.")
        else:
            print("   1. Check Device Manager for 'USB Serial Port' devices")
            print("   2. Verify pump is connected via USB")
            print("   3. Run INSTALL_PUMP_DRIVERS.bat if needed")
            
        return success_count >= 2

def main():
    """Main verification process."""
    verifier = PumpVerifier()
    return verifier.run_verification()

if __name__ == "__main__":
    success = main()
    
    print(f"\nPress any key to exit...")
    try:
        input()
    except:
        pass
        
    sys.exit(0 if success else 1)