#!/usr/bin/env python3
"""
Simplified Audio Command Monitor using the working recording approach.
"""

import argparse
import numpy as np
import sounddevice as sd
import subprocess
import sys
import time
from datetime import datetime
from pathlib import Path

class SimpleAudioCommandMonitor:
    """Simple audio monitor using sd.rec approach that we know works."""
    
    def __init__(self, baseline_duration=2.0):
        self.baseline_duration = baseline_duration
        self.baseline_audio = None
        self.command_audio = None
        self.device_id = None
        self.sample_rate = 44100
        self.audio_dtype = np.int16
        
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
            
            # Test each device to find one that works
            for device_id, device_info in input_devices:
                device_name = device_info.get('name', f'Device {device_id}')
                print(f"   Testing: {device_name}...", end="")
                
                try:
                    # Test with a very short recording
                    audio = sd.rec(
                        int(0.1 * self.sample_rate),  # 0.1 second test
                        samplerate=self.sample_rate,
                        channels=1,
                        dtype=self.audio_dtype,
                        device=device_id
                    )
                    sd.wait()
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
            return False
            
        except Exception as e:
            print(f"❌ Error finding audio device: {e}")
            return False
    
    def record_audio(self, duration, label=""):
        """Record audio for specified duration."""
        try:
            if label:
                print(f"🎙️  Recording {label.lower()} for {duration:.1f}s...")
            
            audio_data = sd.rec(
                int(duration * self.sample_rate),
                samplerate=self.sample_rate,
                channels=1,
                dtype=self.audio_dtype,
                device=self.device_id
            )
            sd.wait()
            
            return audio_data.flatten()
            
        except Exception as e:
            print(f"❌ Recording failed: {e}")
            return None
    
    def analyze_audio(self, audio_data, label=""):
        """Analyze audio data."""
        if audio_data is None or len(audio_data) == 0:
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
    
    def record_baseline(self):
        """Record baseline audio."""
        print(f"\\n📴 Recording baseline audio...")
        print(f"🤫 Please keep environment quiet for {self.baseline_duration} seconds")
        
        # Countdown
        for i in range(3, 0, -1):
            print(f"   Starting in {i}...")
            time.sleep(1)
        
        self.baseline_audio = self.record_audio(self.baseline_duration, "baseline")
        
        if self.baseline_audio is not None:
            self.baseline_analysis = self.analyze_audio(self.baseline_audio, "BASELINE")
            return True
        else:
            print("❌ Failed to record baseline")
            return False
    
    def execute_command_with_audio(self, command, shell=True):
        """Execute command while recording audio."""
        print(f"\\n🚀 Executing command while recording audio...")
        print(f"Command: {command}")
        
        # Start recording before command execution
        start_time = time.time()
        
        # Run command in background and record audio simultaneously
        try:
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
            
            # Record for at least 1 second, or until command finishes
            recording_duration = 0
            audio_chunks = []
            chunk_duration = 0.5  # Record in 0.5-second chunks
            
            while process.poll() is None:  # While command is running
                chunk = self.record_audio(chunk_duration)
                if chunk is not None:
                    audio_chunks.append(chunk)
                    recording_duration += chunk_duration
                
                # Safety limit - don't record more than 30 seconds
                if recording_duration > 30:
                    break
            
            # Get command result
            stdout, stderr = process.communicate(timeout=5)
            return_code = process.returncode
            execution_time = time.time() - start_time
            
            # Combine audio chunks
            if audio_chunks:
                self.command_audio = np.concatenate(audio_chunks)
            else:
                self.command_audio = None
            
            # Create result object
            class CommandResult:
                def __init__(self, returncode, stdout, stderr):
                    self.returncode = returncode
                    self.stdout = stdout
                    self.stderr = stderr
            
            result = CommandResult(return_code, stdout, stderr)
            
            print(f"⏱️  Command completed in {execution_time:.2f}s")
            print(f"⏱️  Audio recorded for {recording_duration:.2f}s")
            
            return result, execution_time
            
        except Exception as e:
            print(f"❌ Error during command execution: {e}")
            return None, 0
    
    def compare_audio(self):
        """Compare baseline and command audio."""
        if self.baseline_analysis is None or self.command_analysis is None:
            print("❌ Cannot compare - missing audio analysis")
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
        # Find working device
        if not self.find_working_device():
            return False
        
        # Record baseline
        if not self.record_baseline():
            return False
        
        # Execute command with audio monitoring
        result, exec_time = self.execute_command_with_audio(command, shell)
        
        if result is not None:
            print(f"\\n📋 COMMAND RESULTS:")
            print(f"   Return code: {result.returncode}")
            if result.stdout.strip():
                print(f"   stdout: {result.stdout.strip()}")
            if result.stderr.strip():
                print(f"   stderr: {result.stderr.strip()}")
        
        # Analyze command audio
        if self.command_audio is not None and len(self.command_audio) > 0:
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
            return False

def main():
    parser = argparse.ArgumentParser(
        description="Simple audio command monitor",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Test with echo command
  python monitor.py "echo Hello World"
  
  # Test with micropump
  python monitor.py "python ../pump.py --test"
  
  # Test with longer baseline
  python monitor.py --baseline 3.0 "your_command"
        """
    )
    
    parser.add_argument("command", help="Command to execute while monitoring audio")
    parser.add_argument("--baseline", type=float, default=2.0,
                       help="Baseline duration in seconds (default: 2.0)")
    parser.add_argument("--no-shell", action="store_true",
                       help="Don't use shell for command execution")
    
    args = parser.parse_args()
    
    print("🎤 SIMPLE AUDIO COMMAND MONITOR")
    print("=" * 50)
    print(f"Command: {args.command}")
    print(f"Baseline duration: {args.baseline}s")
    print("=" * 50)
    
    try:
        monitor = SimpleAudioCommandMonitor(baseline_duration=args.baseline)
        
        command = args.command if not args.no_shell else args.command.split()
        success = monitor.run_full_test(command, shell=not args.no_shell)
        
        if success:
            print("\\n✅ Audio monitoring completed successfully!")
            sys.exit(0)
        else:
            print("\\n❌ Audio monitoring failed!")
            sys.exit(1)
            
    except KeyboardInterrupt:
        print("\\n❌ Interrupted by user")
        sys.exit(1)
    except Exception as e:
        print(f"\\n❌ Error: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)

if __name__ == "__main__":
    main()