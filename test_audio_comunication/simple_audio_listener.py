"""
Simple Audio Listener - Records audio and shows detected frequencies

Run this on RECEIVER computer.
Use simple_tone_generator.py on SENDER computer.

This shows exactly what frequencies are being received with NO filtering.
"""

import numpy as np
import sounddevice as sd
import time


def analyze_audio_chunk(audio: np.ndarray, sample_rate: int = 44100) -> None:
    """Analyze audio chunk and display frequency information"""
    # Calculate RMS (volume level)
    rms = np.sqrt(np.mean(audio ** 2))
    max_amp = np.max(np.abs(audio))
    
    # FFT to find dominant frequencies
    fft = np.fft.rfft(audio)
    freqs = np.fft.rfftfreq(len(audio), 1 / sample_rate)
    magnitude = np.abs(fft)
    
    # Find top 5 frequencies
    top_indices = np.argsort(magnitude)[-5:][::-1]
    
    # Display results
    print(f"  RMS: {rms:.4f}  |  Max: {max_amp:.4f}")
    print(f"  Top frequencies detected:")
    
    for i, idx in enumerate(top_indices):
        freq = freqs[idx]
        mag = magnitude[idx]
        if mag > 100:  # Only show significant peaks
            print(f"    {i+1}. {freq:7.1f} Hz  (magnitude: {mag:10.0f})")
    
    print()


def main() -> None:
    """Continuously listen and analyze audio"""
    print("=" * 70)
    print("SIMPLE AUDIO LISTENER (NO FILTERING)")
    print("=" * 70)
    print("\nThis will record audio and show detected frequencies in real-time.")
    print("Run simple_tone_generator.py on the SENDER computer.\n")
    
    # Get available audio devices
    print("Available audio input devices:")
    devices = sd.query_devices()
    for i, device in enumerate(devices):
        if device['max_input_channels'] > 0:
            print(f"  [{i}] {device['name']}")
    
    print()
    device_id = input("Select input device (press Enter for default): ").strip()
    device_id = int(device_id) if device_id else None
    
    sample_rate = 44100
    chunk_duration = 1.0  # Analyze 1-second chunks
    
    print("\n" + "=" * 70)
    print("LISTENING... (Press Ctrl+C to stop)")
    print("=" * 70)
    print()
    
    try:
        chunk_num = 0
        while True:
            chunk_num += 1
            print(f"[Chunk {chunk_num}] Recording {chunk_duration}s...")
            
            # Record chunk
            recording = sd.rec(
                int(chunk_duration * sample_rate),
                samplerate=sample_rate,
                channels=1,
                device=device_id
            )
            sd.wait()
            
            # Analyze and display
            analyze_audio_chunk(recording[:, 0], sample_rate)
            
            time.sleep(0.1)  # Brief pause before next chunk
            
    except KeyboardInterrupt:
        print("\n\n" + "=" * 70)
        print("STOPPED")
        print("=" * 70)
        print("\nReview the frequencies detected above.")
        print("\nLook for:")
        print("  - Did you see the expected frequencies (300, 500, 1200, 1800, 2400 Hz)?")
        print("  - Were some frequencies clearer than others?")
        print("  - Was there a lot of background noise?")
        print("\nIf specific frequencies were NOT detected:")
        print("  1. Move speaker closer to microphone")
        print("  2. Increase volume on sender")
        print("  3. Try those frequencies might not work well in your setup")
        print("=" * 70)


if __name__ == "__main__":
    try:
        main()
    except Exception as e:
        print(f"\n✗ Error: {e}")
        print("\nMake sure dependencies are installed:")
        print("  pip install sounddevice numpy")
