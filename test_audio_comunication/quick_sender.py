"""
QUICK SENDER - Just sends 1000 Hz continuously
"""
import sounddevice as sd
import numpy as np
import time
from audio_config import load_audio_config, save_audio_config

sample_rate = 44100
frequency = 1000

print("=" * 60)
print("QUICK SENDER - Broadcasting 1000 Hz")
print("=" * 60)

# Try to load saved output device
config = load_audio_config()
output_device = config.get('output_device')

if output_device is not None:
    print(f"\n✓ Using saved output device: {output_device}")
else:
    print("\n⚠ No saved output device, using default")
    # Get default output device
    try:
        default_output = sd.query_devices(kind='output')
        output_device = sd.default.device[1]
        # Save it for next time
        save_audio_config(output_device=output_device)
        print(f"✓ Saved default output device: {output_device}")
    except:
        output_device = None

# Generate 1 second of 1000 Hz tone
duration = 1.0
t = np.linspace(0, duration, int(sample_rate * duration))
tone = 0.5 * np.sin(2 * np.pi * frequency * t)

print(f"\n🔊 Playing {frequency} Hz tone continuously...")
print("   Press Ctrl+C to stop\n")

try:
    count = 0
    while True:
        count += 1
        print(f"[{count}] Playing {frequency} Hz... ", end='', flush=True)
        sd.play(tone, sample_rate, device=output_device)
        sd.wait()
        print("✓")
        time.sleep(0.5)  # Brief pause between transmissions
except KeyboardInterrupt:
    print("\n\nStopped")
