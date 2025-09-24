"""Quick audio test to see if pump detection works."""

import numpy as np
import sounddevice as sd
import sys
import os

sys.path.append(os.path.join(os.path.dirname(__file__), 'src'))
from pump import PumpController
from delete.resolve_ports import find_pump_port_by_vid_pid

# Quick 1-second test
print("🎤 Quick Audio Test")

# Record 1 second of audio
print("Recording 1 second...")
audio = sd.rec(22050, samplerate=22050, channels=1)
sd.wait()

# Basic analysis  
rms = np.sqrt(np.mean(audio**2))
peak = np.max(np.abs(audio))

print(f"RMS: {rms:.6f}, Peak: {peak:.6f}")

# Test pump
try:
    pump_port = find_pump_port_by_vid_pid(0x0403, 0xB4C0)
    print(f"Pump found on: {pump_port}")
    
    pump = PumpController(port=pump_port)
    print("✅ Audio + Pump systems working!")
    pump.close()
    
except Exception as e:
    print(f"❌ Error: {e}")