"""
Debug script to test if audio signals are being transmitted and received properly.
This helps diagnose FSK communication issues.
"""

import numpy as np
import sounddevice as sd
import matplotlib.pyplot as plt
from audio_protocol import AudioModem, Command
import time


def plot_audio_signal(audio_data: np.ndarray, title: str, sample_rate: int = 44100) -> None:
    """Plot audio waveform and frequency spectrum"""
    fig, (ax1, ax2) = plt.subplots(2, 1, figsize=(12, 8))
    
    # Time domain
    duration = len(audio_data) / sample_rate
    time_axis = np.linspace(0, duration, len(audio_data))
    ax1.plot(time_axis, audio_data)
    ax1.set_xlabel('Time (s)')
    ax1.set_ylabel('Amplitude')
    ax1.set_title(f'{title} - Time Domain')
    ax1.grid(True)
    
    # Frequency domain
    fft = np.fft.rfft(audio_data)
    freqs = np.fft.rfftfreq(len(audio_data), 1/sample_rate)
    magnitude = np.abs(fft)
    
    ax2.plot(freqs, magnitude)
    ax2.set_xlabel('Frequency (Hz)')
    ax2.set_ylabel('Magnitude')
    ax2.set_title(f'{title} - Frequency Domain')
    ax2.set_xlim([0, 5000])
    ax2.grid(True)
    
    # Mark expected frequencies
    ax2.axvline(1200, color='r', linestyle='--', label='1200 Hz (mark)')
    ax2.axvline(1800, color='g', linestyle='--', label='1800 Hz (space)')
    ax2.axvline(2400, color='b', linestyle='--', label='2400 Hz (preamble)')
    ax2.legend()
    
    plt.tight_layout()
    plt.show()


def test_encode_decode() -> None:
    """Test encoding and decoding without actual audio I/O"""
    print("=" * 60)
    print("TEST 1: ENCODE/DECODE (No Audio I/O)")
    print("=" * 60)
    
    modem = AudioModem()
    
    for command in [Command.PING, Command.PONG, Command.CAPTURE, Command.DONE]:
        print(f"\nTesting {command.name}...")
        
        # Encode
        audio = modem.encode_command(command)
        print(f"  Encoded signal: {len(audio)} samples, {len(audio)/44100:.2f}s")
        
        # Decode
        decoded = modem.decode_command(audio)
        
        if decoded == command:
            print(f"  ✓ Decoded correctly: {decoded.name}")
        else:
            print(f"  ✗ Decode failed! Expected {command.name}, got {decoded}")
    
    print("\n✓ Encode/decode test complete")


def test_loopback(input_device: int = None, output_device: int = None) -> None:
    """Test audio loopback: play signal and immediately record it"""
    print("\n" + "=" * 60)
    print("TEST 2: AUDIO LOOPBACK")
    print("=" * 60)
    
    modem = AudioModem()
    
    # Generate PING signal
    print("\nGenerating PING signal...")
    audio = modem.encode_command(Command.PING)
    
    print(f"Playing and recording simultaneously...")
    print(f"  Output device: {output_device}")
    print(f"  Input device: {input_device}")
    
    # Record while playing
    sample_rate = modem.config.sample_rate
    duration = len(audio) / sample_rate + 0.5  # Add buffer
    
    recording = sd.playrec(
        audio,
        samplerate=sample_rate,
        channels=1,
        input_mapping=[1],
        output_mapping=[1, 2],
        device=(input_device, output_device)
    )
    sd.wait()
    
    print(f"\nRecorded {len(recording)} samples")
    
    # Analyze recording
    max_amp = np.max(np.abs(recording))
    rms = np.sqrt(np.mean(recording ** 2))
    print(f"  Max amplitude: {max_amp:.4f}")
    print(f"  RMS level: {rms:.4f}")
    
    # Try to decode
    print("\nAttempting to decode...")
    decoded = modem.decode_command(recording[:, 0])
    
    if decoded == Command.PING:
        print("  ✓ LOOPBACK SUCCESSFUL! Decoded PING correctly")
    else:
        print(f"  ✗ Loopback failed. Decoded: {decoded}")
        
        # Show plots for debugging
        response = input("\nShow signal plots for debugging? (y/n): ").strip().lower()
        if response == 'y':
            plot_audio_signal(audio, "Transmitted Signal", sample_rate)
            plot_audio_signal(recording[:, 0], "Received Signal", sample_rate)


def test_manual_send_receive() -> None:
    """Manual test: send from one PC, receive on another"""
    print("\n" + "=" * 60)
    print("TEST 3: MANUAL SEND/RECEIVE")
    print("=" * 60)
    
    mode = input("\nMode (send/receive): ").strip().lower()
    
    modem = AudioModem()
    
    if mode == 'send':
        print("\nSending PING signal...")
        audio = modem.encode_command(Command.PING)
        
        print(f"Signal length: {len(audio)/44100:.2f}s")
        print("Playing in 3 seconds...")
        time.sleep(3)
        
        sd.play(audio, modem.config.sample_rate)
        sd.wait()
        
        print("✓ Signal sent")
        
    elif mode == 'receive':
        duration = 10.0
        print(f"\nListening for {duration} seconds...")
        print("Start the SENDER now!")
        
        recording = sd.rec(
            int(duration * modem.config.sample_rate),
            samplerate=modem.config.sample_rate,
            channels=1
        )
        sd.wait()
        
        print("\nRecording complete")
        max_amp = np.max(np.abs(recording))
        rms = np.sqrt(np.mean(recording ** 2))
        print(f"  Max amplitude: {max_amp:.4f}")
        print(f"  RMS level: {rms:.4f}")
        
        print("\nAttempting to decode...")
        decoded = modem.decode_command(recording[:, 0])
        
        if decoded:
            print(f"  ✓ Received: {decoded.name}")
        else:
            print(f"  ✗ No valid signal detected")
            
            response = input("\nShow recording plot? (y/n): ").strip().lower()
            if response == 'y':
                plot_audio_signal(recording[:, 0], "Received Signal", modem.config.sample_rate)


def main() -> None:
    """Main entry point"""
    print("=" * 60)
    print("AUDIO SIGNAL DEBUG TOOL")
    print("=" * 60)
    
    # Test 1: Basic encode/decode
    test_encode_decode()
    
    # Test 2: Loopback (if possible)
    response = input("\nRun loopback test? (requires audio cable or stereo mix) (y/n): ").strip().lower()
    if response == 'y':
        test_loopback()
    
    # Test 3: Manual send/receive
    response = input("\nRun manual send/receive test? (y/n): ").strip().lower()
    if response == 'y':
        test_manual_send_receive()


if __name__ == "__main__":
    main()
