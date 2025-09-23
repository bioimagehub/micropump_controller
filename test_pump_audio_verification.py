#!/usr/bin/env python3
"""
Comprehensive pump audio verification test.
1. Records baseline audio
2. Asks user to manually start pump for reference
3. Sends automatic commands while monitoring audio
4. Confirms if pump is actually making sound
"""

import time
import sys
import os
import usb.core
import usb.util

# Add project root to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

try:
    import sounddevice as sd
    AUDIO_AVAILABLE = True
    print("✅ Audio recording available")
except ImportError:
    AUDIO_AVAILABLE = False
    print("❌ sounddevice not available - install with: pip install sounddevice")

def record_audio_level(duration=3.0, sample_rate=22050, description="", device=8):
    """Record audio and calculate volume level."""
    if not AUDIO_AVAILABLE:
        print("❌ Audio recording not available")
        return 0.0
    
    try:
        print(f"   🎧 {description} - Recording for {duration} seconds...")
        recording = sd.rec(int(duration * sample_rate), samplerate=sample_rate, channels=1, dtype='float64', device=device)
        sd.wait()
        
        # Calculate volume without numpy
        total = 0.0
        max_val = 0.0
        samples = len(recording)
        
        for sample in recording:
            val = abs(float(sample[0]))
            total += val
            if val > max_val:
                max_val = val
        
        avg_level = total / samples if samples > 0 else 0.0
        rms_level = (total * total / samples) ** 0.5 if samples > 0 else 0.0
        
        print(f"   📊 Average: {avg_level:.6f}, Peak: {max_val:.6f}, RMS: {rms_level:.6f}")
        
        return avg_level
        
    except Exception as e:
        print(f"   ❌ Recording failed: {e}")
        return 0.0

def send_pump_command(command, description):
    """Send command to pump via USB."""
    try:
        device = usb.core.find(idVendor=0x0403, idProduct=0xb4c0)
        if device is None:
            print(f"   ❌ Pump not found for command: {command}")
            return False
        
        full_command = command + "\r"
        data = full_command.encode('utf-8')
        
        print(f"   📤 {description}: '{command}'")
        bytes_sent = device.write(0x02, data, timeout=1000)
        
        # Try to read response
        try:
            response = device.read(0x81, 64, timeout=500)
            resp_bytes = bytes(response)
            print(f"   ✅ Response: {resp_bytes.hex()}")
        except:
            print(f"   ✅ Command sent ({bytes_sent} bytes)")
        
        usb.util.dispose_resources(device)
        time.sleep(0.2)  # Protocol timing
        return True
        
    except Exception as e:
        print(f"   ❌ Command failed: {e}")
        return False

def main():
    """Main audio verification test."""
    print("🔬 PUMP AUDIO VERIFICATION TEST")
    print("===============================")
    print("This test will verify if the pump actually makes sound")
    print()
    
    if not AUDIO_AVAILABLE:
        print("❌ Cannot proceed without audio recording capability")
        print("Install with: pip install sounddevice")
        return
    
    # Check for pump device
    device = usb.core.find(idVendor=0x0403, idProduct=0xb4c0)
    if device is None:
        print("❌ Pump device not found!")
        print("Check USB connection and driver installation")
        return
    
    print("✅ Pump device detected")
    usb.util.dispose_resources(device)
    
    # Show available audio devices
    print("\n📱 Available audio devices:")
    devices = sd.query_devices()
    default_input = sd.default.device[0]
    
    for i, device in enumerate(devices):
        if device['max_input_channels'] > 0:
            marker = " ← DEFAULT" if i == default_input else ""
            print(f"   {i}: {device['name']}{marker}")
    
    print(f"\nUsing SPECIFIED input device 8: Headset (Lenovo Wireless VoIP Headset)")
    
    # PHASE 1: Baseline recording
    print("\n" + "="*50)
    print("📍 PHASE 1: BASELINE RECORDING")
    print("="*50)
    print("Recording background noise with pump OFF using device 8...")
    
    baseline = record_audio_level(3.0, description="Baseline (pump OFF)", device=8)
    
    # PHASE 2: Manual pump test (for reference)
    print("\n" + "="*50)
    print("📍 PHASE 2: MANUAL PUMP TEST")
    print("="*50)
    print("Now I need you to MANUALLY turn on the pump for reference.")
    print()
    print("Instructions:")
    print("1. Use whatever method you normally use to turn on the pump")
    print("2. Make sure it's making sound")
    print("3. Keep it running during the next recording")
    print()
    
    input("Press Enter when the pump is MANUALLY turned on and making sound...")
    
    manual_level = record_audio_level(4.0, description="Manual pump operation", device=8)
    
    print("\nNow please turn OFF the manual pump...")
    input("Press Enter when manual pump is turned OFF...")
    
    # PHASE 3: Automatic command test
    print("\n" + "="*50)
    print("📍 PHASE 3: AUTOMATIC COMMAND TEST")
    print("="*50)
    print("Now testing if our commands actually work...")
    
    # Send configuration commands
    print("\n🔧 Configuring pump...")
    send_pump_command("", "Get status")
    send_pump_command("F100", "Set frequency 100Hz")
    send_pump_command("A80", "Set amplitude 80V")
    send_pump_command("MR", "Set rectangular wave")
    
    # Send start command and monitor immediately
    print("\n🚀 Sending START command and monitoring audio...")
    send_pump_command("bon", "START PUMP")
    
    # Record while pump should be running
    auto_level = record_audio_level(5.0, description="Automatic pump command", device=8)
    
    # Send stop command
    print("\n🛑 Sending STOP command...")
    send_pump_command("boff", "STOP PUMP")
    
    # Final silence check
    time.sleep(1)
    final_level = record_audio_level(2.0, description="Final silence check", device=8)
    
    # PHASE 4: Analysis
    print("\n" + "="*50)
    print("📍 PHASE 4: ANALYSIS")
    print("="*50)
    
    print(f"📊 AUDIO LEVEL COMPARISON:")
    print(f"   Baseline (pump OFF):     {baseline:.6f}")
    print(f"   Manual pump operation:   {manual_level:.6f}")
    print(f"   Automatic command test:  {auto_level:.6f}")
    print(f"   Final silence:           {final_level:.6f}")
    
    # Calculate ratios
    manual_ratio = manual_level / baseline if baseline > 0 else 0
    auto_ratio = auto_level / baseline if baseline > 0 else 0
    
    print(f"\n📈 SIGNAL RATIOS:")
    print(f"   Manual pump vs baseline:  {manual_ratio:.1f}x")
    print(f"   Auto command vs baseline: {auto_ratio:.1f}x")
    
    # Determine results
    print(f"\n🎯 RESULTS:")
    
    if manual_ratio > 2.0:
        print(f"   ✅ Manual pump operation: WORKING")
        print(f"      (Sound level {manual_ratio:.1f}x higher than baseline)")
    else:
        print(f"   ❌ Manual pump operation: NO SOUND DETECTED")
        print(f"      (Sound level only {manual_ratio:.1f}x baseline)")
    
    if auto_ratio > 2.0:
        print(f"   ✅ Automatic commands: WORKING")
        print(f"      (Sound level {auto_ratio:.1f}x higher than baseline)")
        
        if manual_ratio > 2.0:
            effectiveness = (auto_ratio / manual_ratio) * 100
            print(f"      Command effectiveness: {effectiveness:.1f}% of manual operation")
        
    else:
        print(f"   ❌ Automatic commands: NOT WORKING")
        print(f"      (Sound level only {auto_ratio:.1f}x baseline)")
    
    # Final verdict
    print(f"\n🏁 FINAL VERDICT:")
    if auto_ratio > 2.0:
        print("   🎉 SUCCESS! Driver-free pump control is working!")
        print("   The pump responds to automatic commands and makes sound.")
    elif manual_ratio > 2.0:
        print("   ⚠️  PARTIAL SUCCESS: Pump works manually but not via commands")
        print("   The pump hardware is fine, but command protocol needs work.")
    else:
        print("   ❌ FAILURE: No pump sound detected")
        print("   Either pump is not connected, not powered, or microphone issue.")

if __name__ == "__main__":
    main()
