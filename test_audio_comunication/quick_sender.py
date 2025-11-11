"""
QUICK SENDER - Just sends 1000 Hz continuously
"""
import sounddevice as sd
import numpy as np
import time

sample_rate = 44100
frequency = 1000

print("=" * 60)
print("QUICK SENDER - Broadcasting 1000 Hz")
print("=" * 60)

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
        sd.play(tone, sample_rate)
        sd.wait()
        print("✓")
        time.sleep(0.5)  # Brief pause between transmissions
except KeyboardInterrupt:
    print("\n\nStopped")
