"""
Simple audio-based pump detection test.
Records microphone audio while pump is running to detect pump sounds.
Uses basic audio analysis without requiring scipy.
"""

import numpy as np
import sounddevice as sd
import time
import logging
import sys
import os

# Add src directory to path for imports
sys.path.append(os.path.join(os.path.dirname(__file__), 'src'))

from pump import PumpController
from resolve_ports import find_pump_port_by_vid_pid

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s [%(levelname)s] %(message)s')

class AudioPumpDetector:
    def __init__(self, sample_rate=44100, duration=2.0):
        """Initialize audio detector with basic parameters."""
        self.sample_rate = sample_rate
        self.duration = duration
        self.baseline_rms = None
        
    def record_audio(self, duration=None):
        """Record audio from microphone."""
        if duration is None:
            duration = self.duration
            
        print(f"🎤 Recording audio for {duration:.1f} seconds...")
        try:
            # Record audio
            audio_data = sd.rec(int(duration * self.sample_rate), 
                              samplerate=self.sample_rate, 
                              channels=1, 
                              dtype='float64')
            sd.wait()  # Wait for recording to complete
            return audio_data.flatten()
        except Exception as e:
            print(f"❌ Audio recording failed: {e}")
            return None
    
    def analyze_audio(self, audio_data):
        """Analyze audio data for pump-like sounds using basic methods."""
        if audio_data is None or len(audio_data) == 0:
            return {"rms": 0, "peak": 0, "energy": 0}
        
        # Calculate basic audio metrics
        rms = np.sqrt(np.mean(audio_data**2))  # Root Mean Square (overall volume)
        peak = np.max(np.abs(audio_data))      # Peak amplitude
        energy = np.sum(audio_data**2)         # Total energy
        
        # Calculate frequency content using basic FFT
        fft = np.fft.fft(audio_data)
        freqs = np.fft.fftfreq(len(audio_data), 1/self.sample_rate)
        magnitude = np.abs(fft)
        
        # Find dominant frequency (simple peak detection)
        positive_freqs = freqs[:len(freqs)//2]
        positive_magnitude = magnitude[:len(magnitude)//2]
        dominant_freq_idx = np.argmax(positive_magnitude)
        dominant_freq = positive_freqs[dominant_freq_idx]
        
        return {
            "rms": rms,
            "peak": peak, 
            "energy": energy,
            "dominant_freq": abs(dominant_freq),
            "magnitude_at_dominant": positive_magnitude[dominant_freq_idx]
        }
    
    def establish_baseline(self):
        """Record baseline audio (silence) to compare against."""
        print("📊 Establishing baseline audio level...")
        print("   Please ensure pump is OFF and environment is quiet.")
        time.sleep(2)
        
        baseline_audio = self.record_audio(3.0)  # 3 second baseline
        if baseline_audio is not None:
            self.baseline_metrics = self.analyze_audio(baseline_audio)
            print(f"   Baseline RMS: {self.baseline_metrics['rms']:.6f}")
            print(f"   Baseline Peak: {self.baseline_metrics['peak']:.6f}")
            return True
        return False
    
    def detect_pump_sound(self, test_audio_metrics):
        """Compare test audio against baseline to detect pump operation."""
        if not hasattr(self, 'baseline_metrics'):
            print("❌ No baseline established!")
            return False
        
        baseline = self.baseline_metrics
        test = test_audio_metrics
        
        # Calculate ratios
        rms_ratio = test['rms'] / baseline['rms'] if baseline['rms'] > 0 else float('inf')
        energy_ratio = test['energy'] / baseline['energy'] if baseline['energy'] > 0 else float('inf')
        
        # Detection thresholds (adjustable based on your environment)
        rms_threshold = 2.0      # Pump should be at least 2x louder than baseline
        energy_threshold = 4.0   # Energy should be at least 4x higher
        min_rms = 0.001         # Minimum absolute RMS to avoid noise
        
        pump_detected = (
            rms_ratio > rms_threshold and 
            energy_ratio > energy_threshold and 
            test['rms'] > min_rms
        )
        
        print(f"📈 Audio Analysis:")
        print(f"   RMS Ratio: {rms_ratio:.2f} (threshold: {rms_threshold})")
        print(f"   Energy Ratio: {energy_ratio:.2f} (threshold: {energy_threshold})")
        print(f"   Test RMS: {test['rms']:.6f}")
        print(f"   Dominant Frequency: {test['dominant_freq']:.1f} Hz")
        
        return pump_detected


def main():
    """Main test function."""
    print("🔊 AUDIO-BASED PUMP DETECTION TEST")
    print("=" * 50)
    
    # Initialize audio detector
    detector = AudioPumpDetector(sample_rate=22050, duration=3.0)  # Lower sample rate for simplicity
    
    # Check if microphone is available
    try:
        devices = sd.query_devices()
        print(f"🎤 Available audio devices: {len(devices)} found")
        default_input = sd.query_devices(kind='input')
        print(f"   Default input: {default_input['name']}")
    except Exception as e:
        print(f"❌ Audio device error: {e}")
        return
    
    # Establish baseline
    if not detector.establish_baseline():
        print("❌ Failed to establish baseline. Exiting.")
        return
    
    # Find and connect to pump
    print("\n🔍 Finding pump...")
    try:
        pump_port = find_pump_port_by_vid_pid(0x0403, 0xB4C0)  # Bartels pump VID/PID
    except Exception as e:
        print(f"❌ No pump found: {e}")
        return
    
    print(f"✓ Found pump on: {pump_port}")
    
    try:
        pump = PumpController(port=pump_port)
        print("✓ Pump connected successfully")
        
        # Test 1: Record audio with pump OFF
        print("\n🧪 TEST 1: Pump OFF")
        print("Recording audio with pump OFF...")
        off_audio = detector.record_audio()
        off_metrics = detector.analyze_audio(off_audio)
        pump_detected_off = detector.detect_pump_sound(off_metrics)
        
        print(f"🔇 Pump OFF - Detected: {'YES' if pump_detected_off else 'NO'}")
        
        # Test 2: Record audio with pump ON
        print("\n🧪 TEST 2: Pump ON")
        print("Starting pump...")
        pump.set_frequency(100)  # 100 Hz
        pump.set_voltage(50)     # 50V
        pump.start()
        
        time.sleep(1)  # Let pump stabilize
        
        print("Recording audio with pump ON...")
        on_audio = detector.record_audio()
        on_metrics = detector.analyze_audio(on_audio)
        pump_detected_on = detector.detect_pump_sound(on_metrics)
        
        print(f"🔊 Pump ON - Detected: {'YES' if pump_detected_on else 'NO'}")
        
        # Stop pump
        pump.stop()
        print("✓ Pump stopped")
        
        # Results
        print("\n📊 FINAL RESULTS")
        print("=" * 30)
        success = not pump_detected_off and pump_detected_on
        print(f"🎯 Audio detection {'SUCCESS' if success else 'FAILED'}")
        print(f"   Pump OFF detected: {'❌ BAD' if pump_detected_off else '✅ GOOD'}")
        print(f"   Pump ON detected: {'✅ GOOD' if pump_detected_on else '❌ BAD'}")
        
        if success:
            print("\n🎉 Congratulations! Audio-based pump detection is working!")
            print("   You can now detect pump operation using microphone audio.")
        else:
            print("\n🔧 Detection needs tuning. Try adjusting:")
            print("   - Microphone position (closer to pump)")
            print("   - Detection thresholds in the code")
            print("   - Background noise level")
        
    except Exception as e:
        print(f"❌ Pump control error: {e}")
    
    finally:
        try:
            if 'pump' in locals():
                pump.close()
        except:
            pass


if __name__ == "__main__":
    main()