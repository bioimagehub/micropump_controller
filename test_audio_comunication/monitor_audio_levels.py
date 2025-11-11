"""
Simple audio level monitor to verify microphone is picking up sound.
Run this on the receiving PC while sending audio from another PC.
"""

import sounddevice as sd
import numpy as np
import time
from typing import Optional


def monitor_audio_levels(device_id: Optional[int] = None, duration: float = 30.0) -> None:
    """
    Monitor incoming audio levels in real-time.
    
    Args:
        device_id: Input device to monitor (None = default)
        duration: How long to monitor
    """
    print("=" * 60)
    print("AUDIO LEVEL MONITOR")
    print("=" * 60)
    
    if device_id is not None:
        device = sd.query_devices(device_id)
        print(f"\nMonitoring device {device_id}: {device['name']}")
    else:
        try:
            device = sd.query_devices(kind='input')
            print(f"\nMonitoring default input: {device['name']}")
        except:
            print("\n⚠ No default input device - will try anyway")
    
    print(f"\nListening for {duration} seconds...")
    print("Play audio on the other computer and watch for level changes.\n")
    print("Time  | Max Level | RMS Level | Status")
    print("-" * 60)
    
    sample_rate = 44100
    chunk_duration = 0.5  # Check every 0.5 seconds
    chunk_samples = int(sample_rate * chunk_duration)
    
    start_time = time.time()
    
    try:
        while time.time() - start_time < duration:
            # Record short chunk
            recording = sd.rec(
                chunk_samples,
                samplerate=sample_rate,
                channels=1,
                device=device_id,
                dtype='float32'
            )
            sd.wait()
            
            # Analyze
            audio_data = recording[:, 0]
            max_amp = np.max(np.abs(audio_data))
            rms = np.sqrt(np.mean(audio_data ** 2))
            
            # Determine status
            if max_amp < 0.001:
                status = "Silence"
                bar = ""
            elif max_amp < 0.01:
                status = "Very quiet"
                bar = "▁"
            elif max_amp < 0.05:
                status = "Quiet"
                bar = "▂▃"
            elif max_amp < 0.1:
                status = "Moderate"
                bar = "▄▅"
            elif max_amp < 0.3:
                status = "Loud"
                bar = "▆▇"
            else:
                status = "VERY LOUD"
                bar = "█████"
            
            elapsed = int(time.time() - start_time)
            print(f"{elapsed:4d}s | {max_amp:9.4f} | {rms:9.4f} | {status:12s} {bar}")
            
    except KeyboardInterrupt:
        print("\n\nMonitoring stopped.")
    except Exception as e:
        print(f"\n\nError: {e}")
    
    print("\n" + "=" * 60)
    print("Monitoring complete")
    print("=" * 60)


def list_input_devices() -> None:
    """List available input devices"""
    print("\nAvailable input devices:")
    print("-" * 60)
    
    devices = sd.query_devices()
    for i, device in enumerate(devices):
        if device['max_input_channels'] > 0:
            print(f"  [{i}] {device['name']}")


def main() -> None:
    """Main entry point"""
    import sys
    
    list_input_devices()
    
    device_id = None
    if len(sys.argv) > 1:
        try:
            device_id = int(sys.argv[1])
            print(f"\nUsing device {device_id}")
        except ValueError:
            print(f"\nInvalid device ID: {sys.argv[1]}")
            print("Usage: python monitor_audio_levels.py [device_id]")
            return
    else:
        print("\nUsing default input device")
        print("To specify device: python monitor_audio_levels.py <device_id>")
    
    input("\nPress Enter to start monitoring...")
    monitor_audio_levels(device_id, duration=60.0)


if __name__ == "__main__":
    main()
