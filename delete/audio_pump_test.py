"""
Audio-based pump detection test.
Records microphone audio while pump is running to detect pump sounds.
"""

import numpy as np
import sounddevice as sd
import time
import logging
from scipy import signal
import sys
import os

# Add src directory to path for imports
sys.path.append(os.path.join(os.path.dirname(__file__), 'src'))

from device_control.pump import PumpController
from device_control.resolve_ports import find_pump_port

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s [%(levelname)s] %(message)s')

class AudioPumpDetector:
    """Detects pump operation using microphone audio analysis."""
    
    def __init__(self, sample_rate=44100, duration=5.0):
        self.sample_rate = sample_rate
        self.duration = duration
        self.baseline_audio = None
        self.pump_audio = None
        
    def record_audio(self, duration=None):
        """Record audio from the default microphone."""
        if duration is None:
            duration = self.duration
            
        print(f"🎤 Recording audio for {duration} seconds...")
        try:
            # Record audio
            audio_data = sd.rec(int(duration * self.sample_rate), 
                              samplerate=self.sample_rate, 
                              channels=1, 
                              dtype=np.float64)
            sd.wait()  # Wait for recording to complete
            return audio_data.flatten()
        except Exception as e:
            print(f"❌ Error recording audio: {e}")
            return None
    
    def analyze_frequency_spectrum(self, audio_data, label=""):
        """Analyze the frequency spectrum of audio data."""
        if audio_data is None:
            return None
            
        # Compute FFT
        fft = np.fft.fft(audio_data)
        freqs = np.fft.fftfreq(len(fft), 1/self.sample_rate)
        
        # Get magnitude spectrum (positive frequencies only)
        magnitude = np.abs(fft[:len(fft)//2])
        freqs = freqs[:len(freqs)//2]
        
        # Find dominant frequencies
        peak_indices = signal.find_peaks(magnitude, height=np.max(magnitude)*0.1)[0]
        dominant_freqs = freqs[peak_indices]
        peak_magnitudes = magnitude[peak_indices]
        
        # Sort by magnitude
        sorted_indices = np.argsort(peak_magnitudes)[::-1]
        top_freqs = dominant_freqs[sorted_indices[:5]]  # Top 5 frequencies
        top_magnitudes = peak_magnitudes[sorted_indices[:5]]
        
        print(f"📊 {label} Analysis:")
        print(f"   RMS Level: {np.sqrt(np.mean(audio_data**2)):.6f}")
        print(f"   Peak Level: {np.max(np.abs(audio_data)):.6f}")
        print(f"   Top frequencies: {top_freqs[:3]:.1f} Hz")
        
        return {
            'rms': np.sqrt(np.mean(audio_data**2)),
            'peak': np.max(np.abs(audio_data)),
            'frequencies': top_freqs,
            'magnitudes': top_magnitudes,
            'spectrum': (freqs, magnitude)
        }
    
    def compare_audio(self, baseline, pump_audio):
        """Compare baseline and pump audio to detect differences."""
        if baseline is None or pump_audio is None:
            return False
            
        baseline_rms = baseline['rms']
        pump_rms = pump_audio['rms']
        
        # Calculate relative increase
        rms_increase = pump_rms / baseline_rms if baseline_rms > 0 else float('inf')
        
        print(f"\n🔍 PUMP DETECTION ANALYSIS:")
        print(f"   Baseline RMS: {baseline_rms:.6f}")
        print(f"   Pump RMS: {pump_rms:.6f}")
        print(f"   RMS Increase: {rms_increase:.2f}x")
        
        # Detection criteria
        significant_increase = rms_increase > 1.5  # 50% increase in sound level
        
        if significant_increase:
            print("✅ PUMP DETECTED: Significant audio increase detected!")
            return True
        else:
            print("❌ NO PUMP DETECTED: No significant audio change")
            return False

def main():
    """Main audio pump detection test."""
    print("🔬 AUDIO-BASED PUMP DETECTION TEST")
    print("=" * 50)
    
    # Initialize audio detector
    detector = AudioPumpDetector(duration=3.0)
    
    # Find and initialize pump
    print("🔍 Finding pump...")
    pump_port = find_pump_port()
    if not pump_port:
        print("❌ No pump found!")
        return
    
    print(f"✅ Found pump on {pump_port}")
    
    try:
        pump = PumpController(pump_port)
        print("✅ Pump connected successfully")
        
        # Test microphone
        print("\n🎤 Testing microphone access...")
        test_audio = detector.record_audio(1.0)
        if test_audio is None:
            print("❌ Cannot access microphone!")
            return
        print("✅ Microphone working")
        
        # Record baseline (quiet) audio
        print("\n📴 Recording baseline audio (pump OFF)...")
        input("Press Enter when ready to record baseline...")
        baseline_audio = detector.record_audio()
        baseline_analysis = detector.analyze_frequency_spectrum(baseline_audio, "BASELINE")
        
        # Configure pump
        print("\n⚙️ Configuring pump...")
        pump.set_frequency(100)  # 100 Hz
        pump.set_voltage(50)     # 50V
        time.sleep(0.5)
        
        # Record pump audio
        print("\n🔊 Recording audio with PUMP ON...")
        input("Press Enter when ready to record with pump ON...")
        
        print("Starting pump...")
        pump.start()
        time.sleep(0.5)  # Let pump stabilize
        
        pump_audio = detector.record_audio()
        pump_analysis = detector.analyze_frequency_spectrum(pump_audio, "PUMP ON")
        
        print("Stopping pump...")
        pump.stop()
        
        # Compare and detect
        pump_detected = detector.compare_audio(baseline_analysis, pump_analysis)
        
        # Results summary
        print(f"\n🎯 FINAL RESULT:")
        if pump_detected:
            print("🎉 SUCCESS: Pump operation detected via audio!")
        else:
            print("😐 INCONCLUSIVE: No clear pump signature detected")
            
    except Exception as e:
        print(f"❌ Error during test: {e}")
        
    finally:
        try:
            pump.close()
            print("🧹 Pump connection closed")
        except:
            pass

if __name__ == "__main__":
    main()