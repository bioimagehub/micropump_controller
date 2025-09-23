"""
Manual pump audio test - for troubleshooting driver issues.
This test records audio while you manually operate the pump.
"""

import time
import sys
import os

# Add project root to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

try:
    import sounddevice as sd
    AUDIO_AVAILABLE = True
except ImportError:
    AUDIO_AVAILABLE = False
    print("❌ sounddevice not available")

def record_audio_level(duration=3.0, sample_rate=22050):
    """Record audio and calculate simple volume level."""
    if not AUDIO_AVAILABLE:
        print("❌ Audio recording not available")
        return 0.0
    
    try:
        print(f"   🎧 Recording for {duration} seconds...")
        recording = sd.rec(int(duration * sample_rate), samplerate=sample_rate, channels=1, dtype='float64')
        sd.wait()
        
        # Simple volume calculation without numpy
        total = 0.0
        max_val = 0.0
        samples = len(recording)
        
        for sample in recording:
            val = abs(float(sample[0]))
            total += val
            if val > max_val:
                max_val = val
        
        avg_level = total / samples if samples > 0 else 0.0
        print(f"   📊 Average level: {avg_level:.6f}, Peak: {max_val:.6f}")
        
        return avg_level
        
    except Exception as e:
        print(f"   ❌ Recording failed: {e}")
        return 0.0

def wait_for_user_input(message):
    """Wait for user to press Enter."""
    input(f"\n⏸️  {message}\n   Press Enter when ready...")

def manual_pump_audio_test():
    """Manual pump audio test with user interaction."""
    print("🚀 MANUAL PUMP AUDIO TEST")
    print("=" * 40)
    print("This test records audio while you manually operate the pump.")
    print("Use this to verify audio monitoring works before testing drivers.")
    
    if not AUDIO_AVAILABLE:
        print("❌ Audio monitoring not available")
        print("Install sounddevice: pip install sounddevice")
        return False
    
    try:
        # Show available audio devices
        print("\n📱 Available audio devices:")
        devices = sd.query_devices()
        input_devices = []
        for i, device in enumerate(devices):
            try:
                if hasattr(device, 'max_input_channels') and device['max_input_channels'] > 0:
                    input_devices.append((i, device['name']))
                    marker = " ← DEFAULT" if i == sd.default.device[0] else ""
                    print(f"   {i}: {device['name']}{marker}")
            except:
                pass
        
        print(f"\n🎤 Using default microphone for monitoring")
        
        # Step 1: Baseline
        print("\n📍 STEP 1: Baseline measurement (pump OFF)")
        print("   Make sure the pump is OFF and environment is quiet")
        wait_for_user_input("Ready to record baseline?")
        baseline = record_audio_level(3.0)
        
        # Step 2: Manual pump operation
        print("\n📍 STEP 2: Manual pump operation")
        print("   🔧 Now MANUALLY turn on your pump using:")
        print("      - Physical switch on the pump")
        print("      - External controller") 
        print("      - Any method that makes the pump run")
        print("   💡 The pump should make audible sounds when running")
        
        wait_for_user_input("Turn ON the pump now, then press Enter to start recording")
        
        print("   🎧 Recording pump sounds...")
        pump_level = record_audio_level(5.0)
        
        # Step 3: Stop pump
        print("\n📍 STEP 3: Turn off pump")
        print("   🔧 Now MANUALLY turn OFF your pump")
        
        wait_for_user_input("Turn OFF the pump now, then press Enter to record silence")
        
        final_level = record_audio_level(3.0)
        
        # Analysis
        print("\n📊 AUDIO ANALYSIS:")
        print("=" * 30)
        print(f"   Baseline level (OFF):  {baseline:.6f}")
        print(f"   Pump level (ON):       {pump_level:.6f}")
        print(f"   Final level (OFF):     {final_level:.6f}")
        
        # Determine if pump made sound
        if pump_level > baseline * 1.5:  # Pump should be 1.5x louder than baseline
            ratio = pump_level / baseline
            print(f"\n🎉 SUCCESS! Pump sound detected!")
            print(f"   Pump level is {ratio:.1f}x louder than baseline")
            print(f"   Audio monitoring is working correctly!")
            print(f"   Your pump makes detectable sounds when running.")
            
            # Now test automated control
            print(f"\n🤖 NEXT STEP: Test automated pump control")
            print(f"   Since audio monitoring works, we can now test if")
            print(f"   the libusb driver is sending commands correctly.")
            
            test_auto = input("\n   Test automated pump control now? (y/n): ").lower().startswith('y')
            if test_auto:
                return test_automated_control(baseline, pump_level)
            
            return True
            
        elif pump_level > baseline * 1.1:  # Slight increase
            print(f"\n⚠️  Weak pump signal detected")
            print(f"   Pump level is only {pump_level/baseline:.1f}x baseline")
            print(f"   Either the pump is very quiet or needs adjustment")
            return False
            
        else:
            print(f"\n❌ No pump sound detected")
            print(f"   Possible issues:")
            print(f"   - Pump is not actually running")
            print(f"   - Pump is too quiet for microphone")
            print(f"   - Microphone is not positioned correctly")
            print(f"   - Audio levels are too low")
            return False
        
    except Exception as e:
        print(f"\n❌ Test failed: {e}")
        import traceback
        traceback.print_exc()
        return False

def test_automated_control(baseline, expected_pump_level):
    """Test automated pump control after manual test succeeds."""
    print("\n🤖 AUTOMATED PUMP CONTROL TEST")
    print("=" * 40)
    
    try:
        from src.pump_libusb import PumpController
        
        print("   Connecting to pump via libusb...")
        pump = PumpController()
        
        if pump.device is None:
            print("❌ Failed to connect to pump via libusb")
            print("   The driver installation may not be working")
            return False
        
        print("✅ Pump connected via libusb")
        
        # Test automated control
        print("\n   Testing automated pump control...")
        print("   Configuring: 100 Hz, 80V")
        pump.set_frequency(100)
        pump.set_voltage(80)
        
        print("   Starting pump via software...")
        pump.start()
        
        print("   Recording automated pump sounds...")
        auto_level = record_audio_level(5.0)
        
        pump.stop()
        pump.close()
        
        print(f"\n📊 AUTOMATED CONTROL RESULTS:")
        print(f"   Manual pump level:    {expected_pump_level:.6f}")
        print(f"   Automated pump level: {auto_level:.6f}")
        print(f"   Baseline level:       {baseline:.6f}")
        
        if auto_level > baseline * 1.5:
            print(f"\n🎉 COMPLETE SUCCESS!")
            print(f"   Both manual and automated pump control work!")
            print(f"   Your libusb driver setup is fully functional!")
            return True
        else:
            print(f"\n❌ Automated control failed")
            print(f"   Manual pump works but automated control doesn't")
            print(f"   The libusb driver may not be communicating properly")
            return False
            
    except ImportError:
        print("❌ LibUSB pump controller not available")
        return False
    except Exception as e:
        print(f"❌ Automated test failed: {e}")
        return False

if __name__ == "__main__":
    print("🔬 Manual Pump Audio Test")
    print("=========================")
    print("This test helps verify audio monitoring and pump operation")
    print("before testing automated driver control.")
    print()
    
    success = manual_pump_audio_test()
    
    if success:
        print("\n✅ Manual test completed successfully!")
    else:
        print("\n❌ Manual test indicates issues with pump or audio setup")
        print("\nTroubleshooting:")
        print("1. Ensure pump is physically connected and powered")
        print("2. Check microphone is working and positioned near pump")
        print("3. Verify pump makes audible sounds when manually operated")
        print("4. Try adjusting pump settings (frequency, voltage)")
