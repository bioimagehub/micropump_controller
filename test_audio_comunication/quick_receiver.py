"""
QUICK RECEIVER - Listens for 1000 Hz, responds with 1200 Hz
"""
import sounddevice as sd
import numpy as np
import time
from audio_config import load_audio_config, save_audio_config

sample_rate = 44100
listen_freq = 1000
respond_freq = 1200

print("=" * 60)
print("QUICK RECEIVER - Listening for 1000 Hz")
print("=" * 60)

# Try to load saved config first
config = load_audio_config()
saved_input = config.get('input_device')

if saved_input is not None:
    print(f"\n✓ Found saved input device: {saved_input}")
    print("   Testing saved device first...\n")
else:
    print("\n⚠ No saved device config found")
    print("   Will scan all devices...\n")

# Show input devices
devices = sd.query_devices()
print("\nAvailable input devices:")
for i, device in enumerate(devices):
    if device['max_input_channels'] > 0:
        print(f"  [{i}] {device['name']}")

print("\nTrying each device automatically...\n")

# Generate response tone (1200 Hz for 2 seconds)
response_duration = 2.0
t = np.linspace(0, response_duration, int(sample_rate * response_duration))
response_tone = 0.5 * np.sin(2 * np.pi * respond_freq * t)


def detect_frequency(audio_chunk: np.ndarray) -> tuple[float, float]:
    """Quick FFT frequency detection"""
    fft = np.fft.rfft(audio_chunk)
    freqs = np.fft.rfftfreq(len(audio_chunk), 1/sample_rate)
    magnitudes = np.abs(fft)
    
    peak_idx = np.argmax(magnitudes)
    peak_freq = freqs[peak_idx]
    peak_mag = magnitudes[peak_idx]
    
    return peak_freq, peak_mag


def test_device(device_id: int) -> bool:
    """Test if device hears 1000 Hz"""
    try:
        print(f"  Device [{device_id}]: ", end='', flush=True)
        
        # Record 1 second
        recording = sd.rec(int(1.0 * sample_rate), samplerate=sample_rate, 
                          channels=1, device=device_id, dtype='float32')
        sd.wait()
        
        audio = recording[:, 0]
        freq, mag = detect_frequency(audio)
        
        print(f"detected {freq:.0f} Hz (mag: {mag:.0f})")
        
        # Check if it's 1000 Hz (±50 Hz tolerance)
        if abs(freq - listen_freq) < 50 and mag > 100:
            return True
        
        return False
        
    except Exception as e:
        print(f"ERROR: {e}")
        return False


# Try each input device
working_device = None

# If we have a saved device, try it first
if saved_input is not None:
    print(f"Testing saved device {saved_input}...")
    if test_device(saved_input):
        working_device = saved_input
        print(f"✓ Saved device {saved_input} still works!")

# If saved device didn't work, scan all devices
if working_device is None:
    print("\nScanning all devices...")
    for i, device in enumerate(devices):
        if device['max_input_channels'] > 0:
            if test_device(i):
                working_device = i
                print(f"\n✓ FOUND IT! Device {i} hears {listen_freq} Hz!")
                
                # Save this working device for next time
                save_audio_config(input_device=i)
                break

# If we found a working device, respond
if working_device is not None:
    print(f"\n🔊 Responding with {respond_freq} Hz for {response_duration}s...")
    sd.play(response_tone, sample_rate)
    sd.wait()
    print("✓ Response sent!")
    
    print("\n" + "=" * 60)
    print("SUCCESS! Communication established!")
    print("=" * 60)
else:
    print("\n✗ No device detected 1000 Hz")
    print("   Make sure sender is playing and audio cable is connected")
