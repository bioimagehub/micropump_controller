"""
Quick diagnostic: Are the two PCs actually "hearing" each other?

Run this to test if audio from one PC can reach the other PC's microphone.
"""

import sounddevice as sd
import numpy as np
import time


def simple_beep_test() -> None:
    """
    Simple test: one PC beeps, other PC listens.
    """
    print("=" * 60)
    print("TWO-PC AUDIO CONNECTION TEST")
    print("=" * 60)
    
    mode = input("\nIs this the SENDER or RECEIVER? (s/r): ").strip().lower()
    
    if mode == 's':
        print("\n" + "=" * 60)
        print("SENDER MODE")
        print("=" * 60)
        print("\nThis PC will play a series of beeps.")
        print("Make sure:")
        print("  1. Volume is turned UP")
        print("  2. Audio output is connected to other PC's input")
        print("     OR speakers are loud enough for other PC to hear")
        
        input("\nPress Enter to start beeping...")
        
        sample_rate = 44100
        for i in range(5):
            print(f"\n🔊 Beep {i+1}/5...")
            
            # Generate 1-second beep at 1000 Hz
            t = np.linspace(0, 1, sample_rate)
            beep = 0.5 * np.sin(2 * np.pi * 1000 * t)
            
            sd.play(beep, sample_rate)
            sd.wait()
            time.sleep(1)
        
        print("\n✓ Beeping complete")
        print("Did the other PC see audio levels change?")
        
    elif mode == 'r':
        print("\n" + "=" * 60)
        print("RECEIVER MODE")
        print("=" * 60)
        print("\nThis PC will listen for audio.")
        print("Start the SENDER PC now.")
        
        input("\nPress Enter to start listening...")
        
        sample_rate = 44100
        duration = 15.0
        chunk_size = int(0.5 * sample_rate)
        
        print(f"\n🎧 Listening for {duration} seconds...")
        print("\nTime | Audio Level | Detected?")
        print("-" * 50)
        
        start_time = time.time()
        any_detected = False
        
        while time.time() - start_time < duration:
            recording = sd.rec(chunk_size, samplerate=sample_rate, channels=1, dtype='float32')
            sd.wait()
            
            max_amp = np.max(np.abs(recording))
            elapsed = int(time.time() - start_time)
            
            if max_amp > 0.01:
                print(f"{elapsed:3d}s | {max_amp:11.4f} | ✓ DETECTED")
                any_detected = True
            elif max_amp > 0.001:
                print(f"{elapsed:3d}s | {max_amp:11.4f} | ~ weak")
            else:
                print(f"{elapsed:3d}s | {max_amp:11.4f} | - silence")
        
        print("\n" + "=" * 60)
        if any_detected:
            print("✓ AUDIO DETECTED!")
            print("The microphone IS picking up sound.")
            print("The FSK decoding issue is likely in the protocol, not the connection.")
        else:
            print("✗ NO AUDIO DETECTED")
            print("\nPossible issues:")
            print("  1. Audio cable not connected properly")
            print("  2. Sender volume too low")
            print("  3. Receiver microphone muted/wrong device")
            print("  4. PCs too far apart (if using acoustic)")
    
    else:
        print("Invalid mode. Enter 's' for sender or 'r' for receiver")


if __name__ == "__main__":
    simple_beep_test()
