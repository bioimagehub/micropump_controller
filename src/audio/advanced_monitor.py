#!/usr/bin/env python3
"""
Advanced Audio Command Monitor with continuous recording.
Note: This version has known compatibility issues with Windows audio devices.
Use monitor.py for reliable audio monitoring.
"""

import argparse
import numpy as np
import sounddevice as sd
import subprocess
import sys
import threading
import time
from datetime import datetime
from pathlib import Path
import queue

class AudioCommandMonitor:
    """Advanced audio monitor with continuous recording capability."""
    
    def __init__(self, baseline_duration=2.0, device_id=None, sample_rate=44100):
        self.baseline_duration = baseline_duration
        self.device_id = device_id
        self.sample_rate = sample_rate
        self.audio_dtype = np.int16
        
        # Audio storage
        self.baseline_audio = None
        self.command_audio = []
        self.recording = False
        
        # Threading
        self.audio_queue = queue.Queue()
        self.recording_thread = None
        
        # Analysis results
        self.baseline_analysis = None
        self.command_analysis = None
    
    def find_working_device(self):
        """Find a working audio input device."""
        try:
            devices = sd.query_devices()
            input_devices = []
            
            # Find input devices
            for i, device in enumerate(devices):
                if isinstance(device, dict) and device.get('max_input_channels', 0) > 0:
                    input_devices.append((i, device))
            
            if not input_devices:
                print("❌ No input devices found")
                return False
            
            print(f"🔍 Testing {len(input_devices)} input devices...")
            
            # Test each device to find one that works with InputStream
            for device_id, device_info in input_devices:
                device_name = device_info.get('name', f'Device {device_id}')
                print(f"   Testing: {device_name}...", end="")
                
                try:
                    # Test with InputStream (this is what we'll use for continuous recording)
                    test_stream = sd.InputStream(
                        device=device_id,
                        channels=1,
                        samplerate=self.sample_rate,
                        dtype=self.audio_dtype,
                        blocksize=1024,
                        callback=self._test_callback
                    )
                    
                    with test_stream:
                        time.sleep(0.1)  # Test for 0.1 seconds
                    
                    print(" ✅ Works!")
                    
                    self.device_id = device_id
                    print(f"🎤 Using: {device_name}")
                    print(f"   Device ID: {device_id}")
                    print(f"   Sample rate: {self.sample_rate} Hz")
                    print(f"   Format: {self.audio_dtype.__name__}")
                    return True
                    
                except Exception as e:
                    print(f" ❌ Failed: {str(e)[:30]}")
                    continue
            
            print("❌ No working audio devices found")
            print("💡 Try using monitor.py instead (uses different recording method)")
            return False
            
        except Exception as e:
            print(f"❌ Error finding audio device: {e}")
            return False
    
    def _test_callback(self, indata, frames, time, status):
        """Callback for testing device compatibility."""
        if status:
            print(f"Stream status: {status}")
        # Just discard data during test
        pass
    
    def _audio_callback(self, indata, frames, time, status):
        """Callback for continuous audio recording."""
        if status:
            print(f"Stream status: {status}")
        
        if self.recording:
            # Copy data to avoid issues with the callback buffer
            audio_chunk = indata.copy()
            try:
                self.audio_queue.put_nowait(audio_chunk)
            except queue.Full:
                print("⚠️ Audio queue full, dropping frames")
    
    def record_baseline(self):
        """Record baseline audio using sd.rec method."""
        print(f"\\n📴 Recording baseline audio...")
        print(f"🤫 Please keep environment quiet for {self.baseline_duration} seconds")
        
        # Countdown
        for i in range(3, 0, -1):
            print(f"   Starting in {i}...")
            time.sleep(1)
        
        try:
            self.baseline_audio = sd.rec(
                int(self.baseline_duration * self.sample_rate),
                samplerate=self.sample_rate,
                channels=1,
                dtype=self.audio_dtype,
                device=self.device_id
            )
            sd.wait()
            
            if self.baseline_audio is not None:
                self.baseline_analysis = self.analyze_audio(self.baseline_audio.flatten(), "BASELINE")
                return True
            else:
                print("❌ Failed to record baseline")
                return False
                
        except Exception as e:
            print(f"❌ Baseline recording failed: {e}")
            return False
    
    def start_continuous_recording(self):
        """Start continuous audio recording in background."""
        try:
            print("🎙️  Starting continuous recording...")
            
            self.recording = True
            self.command_audio = []
            
            # Clear the queue
            while not self.audio_queue.empty():
                try:
                    self.audio_queue.get_nowait()
                except queue.Empty:
                    break
            
            # Start the input stream
            self.stream = sd.InputStream(
                device=self.device_id,
                channels=1,
                samplerate=self.sample_rate,
                dtype=self.audio_dtype,
                blocksize=1024,
                callback=self._audio_callback
            )
            
            self.stream.start()
            print("✅ Continuous recording started")
            return True
            
        except Exception as e:
            print(f"❌ Failed to start recording: {e}")
            self.recording = False
            return False
    
    def stop_continuous_recording(self):
        """Stop continuous recording and collect audio data."""
        if not self.recording:
            return
        
        print("⏹️  Stopping continuous recording...")
        self.recording = False
        
        try:
            if hasattr(self, 'stream'):
                self.stream.stop()
                self.stream.close()
            
            # Collect all audio chunks from the queue
            audio_chunks = []
            while not self.audio_queue.empty():
                try:
                    chunk = self.audio_queue.get_nowait()
                    audio_chunks.append(chunk.flatten())
                except queue.Empty:
                    break
            
            if audio_chunks:
                self.command_audio = np.concatenate(audio_chunks)
                print(f"✅ Collected {len(self.command_audio)} audio samples")
            else:
                print("⚠️ No audio data collected")
                self.command_audio = np.array([])
                
        except Exception as e:
            print(f"❌ Error stopping recording: {e}")
    
    def execute_command_with_continuous_audio(self, command, shell=True):
        """Execute command while recording audio continuously."""
        print(f"\\n🚀 Executing command with continuous audio monitoring...")
        print(f"Command: {command}")
        
        # Start continuous recording
        if not self.start_continuous_recording():
            return None, 0
        
        start_time = time.time()
        
        try:
            # Execute the command
            if isinstance(command, str) and shell:
                process = subprocess.Popen(
                    command,
                    shell=True,
                    stdout=subprocess.PIPE,
                    stderr=subprocess.PIPE,
                    text=True
                )
            else:
                process = subprocess.Popen(
                    command,
                    stdout=subprocess.PIPE,
                    stderr=subprocess.PIPE,
                    text=True
                )
            
            # Wait for command to complete (with timeout)
            try:
                stdout, stderr = process.communicate(timeout=30)
                return_code = process.returncode
            except subprocess.TimeoutExpired:
                process.kill()
                stdout, stderr = process.communicate()
                return_code = -1
                print("⚠️ Command timed out after 30 seconds")
            
            execution_time = time.time() - start_time
            
            # Stop recording
            self.stop_continuous_recording()
            
            # Create result object
            class CommandResult:
                def __init__(self, returncode, stdout, stderr):
                    self.returncode = returncode
                    self.stdout = stdout
                    self.stderr = stderr
            
            result = CommandResult(return_code, stdout, stderr)
            
            print(f"⏱️  Command completed in {execution_time:.2f}s")
            
            return result, execution_time
            
        except Exception as e:
            print(f"❌ Error during command execution: {e}")
            self.stop_continuous_recording()
            return None, 0
    
    def analyze_audio(self, audio_data, label=""):
        """Analyze audio data."""
        if audio_data is None or len(audio_data) == 0:
            print(f"⚠️ No audio data to analyze for {label}")
            return None
        
        # Convert to float for analysis
        if audio_data.dtype == np.int16:
            audio_float = audio_data.astype(np.float32) / 32768.0
        else:
            audio_float = audio_data.astype(np.float32)
        
        # Calculate statistics
        rms = np.sqrt(np.mean(audio_float**2))
        peak = np.max(np.abs(audio_float))
        mean_abs = np.mean(np.abs(audio_float))
        
        analysis = {
            'rms': rms,
            'peak': peak,
            'mean_abs': mean_abs,
            'duration': len(audio_data) / self.sample_rate,
            'samples': len(audio_data)
        }
        
        if label:
            print(f"📊 {label} Analysis:")
            print(f"   Duration: {analysis['duration']:.2f}s")
            print(f"   RMS Level: {analysis['rms']:.6f}")
            print(f"   Peak Level: {analysis['peak']:.6f}")
            print(f"   Mean Level: {analysis['mean_abs']:.6f}")
        
        return analysis
    
    def compare_audio(self):
        """Compare baseline and command audio."""
        if self.baseline_analysis is None:
            print("❌ No baseline analysis available")
            return None
        
        if self.command_analysis is None:
            print("❌ No command analysis available")
            return None
        
        baseline_rms = self.baseline_analysis['rms']
        command_rms = self.command_analysis['rms']
        
        baseline_peak = self.baseline_analysis['peak']
        command_peak = self.command_analysis['peak']
        
        # Calculate ratios
        rms_ratio = command_rms / baseline_rms if baseline_rms > 0 else float('inf')
        peak_ratio = command_peak / baseline_peak if baseline_peak > 0 else float('inf')
        
        # Calculate percentage changes
        rms_change_pct = (rms_ratio - 1) * 100
        peak_change_pct = (peak_ratio - 1) * 100
        
        comparison = {
            'rms_ratio': rms_ratio,
            'peak_ratio': peak_ratio,
            'rms_change_pct': rms_change_pct,
            'peak_change_pct': peak_change_pct,
            'baseline': self.baseline_analysis,
            'command': self.command_analysis
        }
        
        print(f"\\n🔍 AUDIO COMPARISON:")
        print(f"   Baseline RMS: {baseline_rms:.6f}")
        print(f"   Command RMS:  {command_rms:.6f}")
        print(f"   RMS Change:   {rms_change_pct:+.1f}% ({rms_ratio:.2f}x)")
        print(f"")
        print(f"   Baseline Peak: {baseline_peak:.6f}")
        print(f"   Command Peak:  {command_peak:.6f}")
        print(f"   Peak Change:   {peak_change_pct:+.1f}% ({peak_ratio:.2f}x)")
        
        return comparison
    
    def interpret_results(self, comparison):
        """Interpret the comparison results."""
        if comparison is None:
            return "UNKNOWN"
        
        rms_ratio = comparison['rms_ratio']
        rms_change_pct = comparison['rms_change_pct']
        
        print(f"\\n🎯 INTERPRETATION:")
        
        if rms_ratio > 2.0:
            interpretation = "SIGNIFICANT_INCREASE"
            print(f"🔊 SIGNIFICANT AUDIO INCREASE detected!")
            print(f"   Sound levels more than doubled during command execution.")
        elif rms_ratio > 1.5:
            interpretation = "MODERATE_INCREASE"
            print(f"📈 MODERATE AUDIO INCREASE detected")
            print(f"   Command caused noticeable sound level changes.")
        elif rms_ratio > 1.2:
            interpretation = "SLIGHT_INCREASE"
            print(f"📊 SLIGHT AUDIO INCREASE detected")
            print(f"   Small but measurable sound level increase.")
        elif rms_ratio > 0.8:
            interpretation = "NO_SIGNIFICANT_CHANGE"
            print(f"➖ NO SIGNIFICANT CHANGE in audio levels")
            print(f"   Command was relatively quiet.")
        else:
            interpretation = "DECREASE"
            print(f"📉 AUDIO DECREASE detected")
            print(f"   Sound levels decreased during command execution.")
        
        return interpretation
    
    def run_full_test(self, command, shell=True):
        """Run the complete audio monitoring test."""
        print("⚠️  WARNING: This is the advanced audio monitor with known compatibility issues.")
        print("   If you experience problems, use monitor.py instead.")
        print()
        
        # Find working device
        if not self.find_working_device():
            return False
        
        # Record baseline using simple method
        if not self.record_baseline():
            return False
        
        # Execute command with continuous audio monitoring
        result, exec_time = self.execute_command_with_continuous_audio(command, shell)
        
        if result is not None:
            print(f"\\n📋 COMMAND RESULTS:")
            print(f"   Return code: {result.returncode}")
            if result.stdout.strip():
                print(f"   stdout: {result.stdout.strip()}")
            if result.stderr.strip():
                print(f"   stderr: {result.stderr.strip()}")
        
        # Analyze command audio
        if len(self.command_audio) > 0:
            self.command_analysis = self.analyze_audio(self.command_audio, "COMMAND")
            
            # Compare audio
            comparison = self.compare_audio()
            interpretation = self.interpret_results(comparison)
            
            print(f"\\n📊 SUMMARY:")
            print(f"   Command: {command}")
            print(f"   Execution time: {exec_time:.2f}s")
            print(f"   Audio interpretation: {interpretation}")
            if comparison:
                print(f"   RMS change: {comparison['rms_change_pct']:+.1f}%")
                print(f"   Peak change: {comparison['peak_change_pct']:+.1f}%")
            
            return True
        else:
            print("❌ No audio recorded during command execution")
            print("💡 Try using monitor.py instead")
            return False

def main():
    parser = argparse.ArgumentParser(
        description="Advanced audio command monitor (with known compatibility issues)",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
⚠️  WARNING: This is the advanced audio monitor that may have compatibility issues
   with Windows audio devices. If you experience problems, use monitor.py instead.

Examples:
  # Test with echo command
  python advanced_monitor.py "echo Hello World"
  
  # Test with micropump
  python advanced_monitor.py "python ../pump.py --test"
  
  # Test with longer baseline
  python advanced_monitor.py --baseline 3.0 "your_command"
        """
    )
    
    parser.add_argument("command", help="Command to execute while monitoring audio")
    parser.add_argument("--baseline", type=float, default=2.0,
                       help="Baseline duration in seconds (default: 2.0)")
    parser.add_argument("--device", type=int,
                       help="Audio device ID to use")
    parser.add_argument("--sample-rate", type=int, default=44100,
                       help="Sample rate in Hz (default: 44100)")
    parser.add_argument("--no-shell", action="store_true",
                       help="Don't use shell for command execution")
    
    args = parser.parse_args()
    
    print("🎤 ADVANCED AUDIO COMMAND MONITOR")
    print("=" * 50)
    print("⚠️  This version has known compatibility issues!")
    print("   Consider using monitor.py for reliable operation.")
    print("=" * 50)
    print(f"Command: {args.command}")
    print(f"Baseline duration: {args.baseline}s")
    print("=" * 50)
    
    try:
        monitor = AudioCommandMonitor(
            baseline_duration=args.baseline,
            device_id=args.device,
            sample_rate=args.sample_rate
        )
        
        command = args.command if not args.no_shell else args.command.split()
        success = monitor.run_full_test(command, shell=not args.no_shell)
        
        if success:
            print("\\n✅ Audio monitoring completed successfully!")
            sys.exit(0)
        else:
            print("\\n❌ Audio monitoring failed!")
            print("💡 Try using monitor.py instead")
            sys.exit(1)
            
    except KeyboardInterrupt:
        print("\\n❌ Interrupted by user")
        sys.exit(1)
    except Exception as e:
        print(f"\\n❌ Error: {e}")
        import traceback
        traceback.print_exc()
        print("\\n💡 Try using monitor.py instead")
        sys.exit(1)

if __name__ == "__main__":
    main()