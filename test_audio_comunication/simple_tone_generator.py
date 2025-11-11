"""
Simple Signal Generator - Play test tones at different frequencies

Run this on SENDER computer. 
Use monitor_audio_levels.py on RECEIVER computer to see what gets through.

This helps find the best frequencies for your specific setup.
"""

import numpy as np
import sounddevice as sd
import time


def play_beep(frequency: float, duration: float) -> None:
    """Generate and play a simple sine wave tone"""
    sample_rate = 44100
    t = np.linspace(0, duration, int(sample_rate * duration))
    
    # Generate sine wave
    signal = np.sin(2 * np.pi * frequency * t)
    
    # Add fade in/out to prevent clicks
    fade_len = int(0.01 * sample_rate)  # 10ms
    if len(signal) > 2 * fade_len:
        signal[:fade_len] *= np.linspace(0, 1, fade_len)
        signal[-fade_len:] *= np.linspace(1, 0, fade_len)
    
    # Play
    sd.play(signal, sample_rate)
    sd.wait()


def main() -> None:
    """Play various test frequencies"""
    print("=" * 70)
    print("SIMPLE AUDIO SIGNAL GENERATOR")
    print("=" * 70)
    print("\nThis will play tones at different frequencies and durations.")
    print("Run monitor_audio_levels.py on the RECEIVER to see what's detected.\n")
    
    input("Press Enter to start...")
    
    # Test different frequencies
    test_frequencies = [
        (300, "Very Low - 300 Hz"),
        (500, "Low - 500 Hz"),
        (700, "Mid-Low - 700 Hz"),
        (1000, "Mid - 1000 Hz"),
        (1200, "FSK Mark - 1200 Hz"),
        (1500, "Mid-High - 1500 Hz"),
        (1800, "FSK Space - 1800 Hz"),
        (2000, "High - 2000 Hz"),
        (2400, "FSK Preamble - 2400 Hz"),
        (3000, "Very High - 3000 Hz"),
        (4000, "Ultra High - 4000 Hz"),
    ]
    
    print("\n" + "=" * 70)
    print("FREQUENCY SWEEP TEST (1 second each)")
    print("=" * 70)
    
    for freq, label in test_frequencies:
        print(f"\n🔊 {label}")
        print(f"   Playing {freq} Hz for 1 second...")
        play_beep(freq, 1.0)
        print(f"   ✓ Done")
        time.sleep(0.5)  # Brief pause between tones
    
    # Test different durations
    print("\n" + "=" * 70)
    print("DURATION TEST (1500 Hz at different lengths)")
    print("=" * 70)
    
    test_durations = [
        (0.1, "Very Short - 100ms"),
        (0.25, "Short - 250ms"),
        (0.5, "Medium - 500ms"),
        (1.0, "Long - 1 second"),
        (2.0, "Very Long - 2 seconds"),
    ]
    
    for duration, label in test_durations:
        print(f"\n🔊 {label}")
        print(f"   Playing 1500 Hz for {duration} seconds...")
        play_beep(1500, duration)
        print(f"   ✓ Done")
        time.sleep(0.5)
    
    # Test pattern (like FSK data)
    print("\n" + "=" * 70)
    print("FSK PATTERN TEST (Alternating 1200/1800 Hz)")
    print("=" * 70)
    print("\n🔊 Playing alternating pattern (simulates data transmission)...")
    
    pattern = [1200, 1800, 1200, 1800, 1200, 1800, 1200, 1800]
    for i, freq in enumerate(pattern):
        print(f"   Bit {i}: {freq} Hz")
        play_beep(freq, 0.15)
    
    print("   ✓ Pattern complete")
    
    # Continuous tone test
    print("\n" + "=" * 70)
    print("LONG TONE TEST (for manual alignment)")
    print("=" * 70)
    print("\n🔊 Playing 1500 Hz for 5 seconds...")
    print("   Use this to position speaker/microphone optimally.")
    
    play_beep(1500, 5.0)
    print("   ✓ Done")
    
    # Summary
    print("\n" + "=" * 70)
    print("TEST COMPLETE")
    print("=" * 70)
    print("\nCheck the RECEIVER computer output.")
    print("\nLook for:")
    print("  - Which frequencies were detected most clearly")
    print("  - What the peak frequency readings were")
    print("  - If any frequencies were completely missed")
    print("\nNext steps:")
    print("  1. Note which frequencies worked best")
    print("  2. If 2400 Hz didn't work, try lower frequencies (1000-1500 Hz)")
    print("  3. Adjust FSK protocol to use successful frequencies")
    print("=" * 70)


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\n\nInterrupted by user")
    except Exception as e:
        print(f"\n✗ Error: {e}")
        print("\nMake sure dependencies are installed:")
        print("  pip install sounddevice numpy")
