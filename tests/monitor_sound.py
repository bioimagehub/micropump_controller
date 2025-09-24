#!/usr/bin/env python3
"""
Standalone Audio Command Monitor for micropump controller.

A single-file solution for recording baseline audio, executing commands
while monitoring sound changes, and comparing the results.

Usage:
    # Command line
    python monitor_sound.py "python cli.py config.yaml"
    
    # As module
    import monitor_sound
    result = monitor_sound.monitor_command("echo test")
    
    # With function call
    monitor_sound.monitor_sound(lambda: print("Hello"))
"""

import argparse
import numpy as np
import sounddevice as sd
import subprocess
import sys
import time
from datetime import datetime
from typing import Callable, Optional, Union, Dict, Any


class AudioCommandMonitor:
    """Standalone audio monitor for detecting sound changes during command execution."""
    
    def __init__(self, baseline_duration: float = 2.0, device_id: Optional[int] = None):
        """
        Initialize the audio monitor.
        
        Args:
            baseline_duration: Duration in seconds to record baseline audio
            device_id: Specific audio device ID to use (None for auto-detection)
        """
        self.baseline_duration = baseline_duration
        self.baseline_audio = None
        self.command_audio = None
        self.device_id = device_id
        self.sample_rate = 44100
        self.audio_dtype = np.int16
        self.baseline_analysis = None
        self.command_analysis = None
        
    def find_working_device(self) -> bool:
        """Find a working audio input device."""
        if self.device_id is not None:
            # Test the specified device
            try:
                audio = sd.rec(
                    int(0.1 * self.sample_rate),
                    samplerate=self.sample_rate,
                    channels=1,
                    dtype=self.audio_dtype,
                    device=self.device_id
                )
                sd.wait()
                print(f"MIC Using specified device ID: {self.device_id}")
                return True
            except Exception as e:
                print(f"FAIL Specified device {self.device_id} failed: {e}")
                return False
        
        try:
            devices = sd.query_devices()
            input_devices = []
            
            # Find input devices
            for i, device in enumerate(devices):
                if isinstance(device, dict) and device.get('max_input_channels', 0) > 0:
                    input_devices.append((i, device))
            
            if not input_devices:
                print("FAIL No input devices found")
                return False
            
            print(f"SEARCH Testing {len(input_devices)} input devices...")
            
            # Test each device to find one that works
            for device_id, device_info in input_devices:
                device_name = device_info.get('name', f'Device {device_id}')
                print(f"   Testing: {device_name}...", end="")
                
                try:
                    # Test with a very short recording
                    audio = sd.rec(
                        int(0.1 * self.sample_rate),
                        samplerate=self.sample_rate,
                        channels=1,
                        dtype=self.audio_dtype,
                        device=device_id
                    )
                    sd.wait()
                    print(" OK")
                    
                    self.device_id = device_id
                    print(f"MIC Using: {device_name} (ID: {device_id})")
                    return True
                    
                except Exception as e:
                    print(f" FAIL {str(e)[:30]}")
                    continue
            
            print("FAIL No working audio devices found")
            return False
            
        except Exception as e:
            print(f"FAIL Error finding audio device: {e}")
            return False
    
    def record_audio(self, duration: float, label: str = "") -> Optional[np.ndarray]:
        """Record audio for specified duration."""
        try:
            if label:
                print(f"MIC  Recording {label.lower()} for {duration:.1f}s...")
            
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
            print(f"FAIL Recording failed: {e}")
            return None
    
    def analyze_audio(self, audio_data: np.ndarray, label: str = "") -> Optional[Dict[str, float]]:
        """Analyze audio data and return statistics."""
        if audio_data is None or len(audio_data) == 0:
            return None
        
        # Convert to float for analysis
        if audio_data.dtype == np.int16:
            audio_float = audio_data.astype(np.float32) / 32768.0
        else:
            audio_float = audio_data.astype(np.float32)
        
        # Calculate statistics
        rms = float(np.sqrt(np.mean(audio_float**2)))
        peak = float(np.max(np.abs(audio_float)))
        mean_abs = float(np.mean(np.abs(audio_float)))
        
        analysis = {
            'rms': rms,
            'peak': peak,
            'mean_abs': mean_abs,
            'duration': len(audio_data) / self.sample_rate,
            'samples': len(audio_data)
        }
        
        if label:
            print(f"STATS {label} Analysis:")
            print(f"   Duration: {analysis['duration']:.2f}s")
            print(f"   RMS Level: {analysis['rms']:.6f}")
            print(f"   Peak Level: {analysis['peak']:.6f}")
            print(f"   Mean Level: {analysis['mean_abs']:.6f}")
        
        return analysis
    
    def record_baseline(self) -> bool:
        """Record baseline audio."""
        print(f"\nOFF Recording baseline audio...")
        print(f"SHH Please keep environment quiet for {self.baseline_duration} seconds")
        
        # Countdown
        for i in range(3, 0, -1):
            print(f"   Starting in {i}...")
            time.sleep(1)
        
        self.baseline_audio = self.record_audio(self.baseline_duration, "baseline")
        
        if self.baseline_audio is not None:
            self.baseline_analysis = self.analyze_audio(self.baseline_audio, "BASELINE")
            return True
        else:
            print("FAIL Failed to record baseline")
            return False
    
    def execute_command_with_audio(self, command: Union[str, list], shell: bool = True) -> tuple:
        """Execute command while recording audio."""
        print(f"\nROCKET Executing command while recording audio...")
        print(f"Command: {command}")
        
        start_time = time.time()
        
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
            audio_chunks = []
            chunk_duration = 0.5  # Record in 0.5-second chunks
            recording_duration = 0
            
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
            
            print(f"STOPWATCH  Command completed in {execution_time:.2f}s")
            print(f"STOPWATCH  Audio recorded for {recording_duration:.2f}s")
            
            return result, execution_time
            
        except Exception as e:
            print(f"FAIL Error during command execution: {e}")
            return None, 0
    
    def execute_function_with_audio(self, func: Callable, *args, **kwargs) -> tuple:
        """Execute a Python function while recording audio."""
        print(f"\nROCKET Executing function while recording audio...")
        print(f"Function: {func.__name__}")
        
        start_time = time.time()
        
        try:
            # Start recording
            audio_chunks = []
            chunk_duration = 0.1  # Smaller chunks for better responsiveness
            recording_duration = 0
            
            # Execute function while recording audio
            import threading
            import queue
            
            function_result_queue = queue.Queue()
            recording_active = threading.Event()
            recording_active.set()
            
            def execute_function():
                """Execute the function in a separate thread."""
                try:
                    result = func(*args, **kwargs)
                    function_result_queue.put(("success", result))
                except Exception as e:
                    function_result_queue.put(("error", str(e)))
                finally:
                    recording_active.clear()
            
            # Start function execution thread
            func_thread = threading.Thread(target=execute_function, daemon=True)
            func_thread.start()
            
            # Record while function is running
            while recording_active.is_set() and func_thread.is_alive():
                chunk = self.record_audio(chunk_duration)
                if chunk is not None:
                    audio_chunks.append(chunk)
                    recording_duration += chunk_duration
                
                # Safety limit - don't record more than 30 seconds
                if recording_duration > 30:
                    recording_active.clear()
                    break
            
            # Wait for function to complete
            func_thread.join(timeout=5)
            
            execution_time = time.time() - start_time
            
            # Get function result
            try:
                result_type, result_value = function_result_queue.get_nowait()
                function_success = (result_type == "success")
                result = result_value
            except queue.Empty:
                function_success = False
                result = "Function timeout or no result"
            
            # Combine audio chunks
            if audio_chunks:
                self.command_audio = np.concatenate(audio_chunks)
            else:
                self.command_audio = None
            
            # Create result object
            class FunctionResult:
                def __init__(self, result, success):
                    self.result = result
                    self.success = success
                    self.returncode = 0 if success else 1
                    self.stdout = str(result) if success else ""
                    self.stderr = str(result) if not success else ""
            
            func_result = FunctionResult(result, function_success)
            
            print(f"STOPWATCH  Function completed in {execution_time:.2f}s")
            print(f"STOPWATCH  Audio recorded for {recording_duration:.2f}s")
            
            return func_result, execution_time
            
        except Exception as e:
            print(f"FAIL Error during function execution: {e}")
            return None, 0
    
    def compare_audio(self) -> Optional[Dict[str, Any]]:
        """Compare baseline and command audio."""
        if self.baseline_analysis is None or self.command_analysis is None:
            print("FAIL Cannot compare - missing audio analysis")
            return None
        
        baseline_rms = self.baseline_analysis['rms']
        command_rms = self.command_analysis['rms']
        baseline_peak = self.baseline_analysis['peak']
        command_peak = self.command_analysis['peak']
        
        # Calculate ratios (avoid division by zero)
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
        
        print(f"\nSEARCH AUDIO COMPARISON:")
        print(f"   Baseline RMS:  {baseline_rms:.6f}")
        print(f"   Command RMS:   {command_rms:.6f}")
        print(f"   RMS Change:    {rms_change_pct:+.1f}% ({rms_ratio:.2f}x)")
        print(f"")
        print(f"   Baseline Peak: {baseline_peak:.6f}")
        print(f"   Command Peak:  {command_peak:.6f}")
        print(f"   Peak Change:   {peak_change_pct:+.1f}% ({peak_ratio:.2f}x)")
        
        return comparison
    
    def interpret_results(self, comparison: Dict[str, Any]) -> str:
        """Interpret the comparison results."""
        if comparison is None:
            return "UNKNOWN"
        
        rms_ratio = comparison['rms_ratio']
        
        print(f"\nTARGET INTERPRETATION:")
        
        if rms_ratio > 2.0:
            interpretation = "SIGNIFICANT_INCREASE"
            print(f"SPEAKER SIGNIFICANT AUDIO INCREASE detected!")
            print(f"   Sound levels more than doubled during execution.")
        elif rms_ratio > 1.5:
            interpretation = "MODERATE_INCREASE"
            print(f"UP MODERATE AUDIO INCREASE detected")
            print(f"   Command caused noticeable sound level changes.")
        elif rms_ratio > 1.2:
            interpretation = "SLIGHT_INCREASE"
            print(f"STATS SLIGHT AUDIO INCREASE detected")
            print(f"   Small but measurable sound level increase.")
        elif rms_ratio > 0.8:
            interpretation = "NO_SIGNIFICANT_CHANGE"
            print(f"- NO SIGNIFICANT CHANGE in audio levels")
            print(f"   Execution was relatively quiet.")
        else:
            interpretation = "DECREASE"
            print(f"DOWN AUDIO DECREASE detected")
            print(f"   Sound levels decreased during execution.")
        
        return interpretation


def monitor_sound(target: Union[str, Callable], baseline_duration: float = 2.0, 
                  device_id: Optional[int] = None, shell: bool = True, 
                  *args, **kwargs) -> Dict[str, Any]:
    """
    Monitor audio changes while executing a command or function.
    
    Args:
        target: Command string or Python function to execute
        baseline_duration: Duration in seconds to record baseline audio
        device_id: Specific audio device ID to use (None for auto-detection)
        shell: Whether to use shell for command execution (ignored for functions)
        *args, **kwargs: Arguments to pass to function (ignored for commands)
    
    Returns:
        Dictionary containing results and audio analysis
    """
    monitor = AudioCommandMonitor(baseline_duration=baseline_duration, device_id=device_id)
    
    # Find working device
    if not monitor.find_working_device():
        return {"success": False, "error": "No working audio device found"}
    
    # Record baseline
    if not monitor.record_baseline():
        return {"success": False, "error": "Failed to record baseline"}
    
    # Execute target with audio monitoring
    if callable(target):
        result, exec_time = monitor.execute_function_with_audio(target, *args, **kwargs)
    else:
        result, exec_time = monitor.execute_command_with_audio(target, shell=shell)
    
    if result is None:
        return {"success": False, "error": "Execution failed"}
    
    # Analyze command audio
    if monitor.command_audio is not None and len(monitor.command_audio) > 0:
        monitor.command_analysis = monitor.analyze_audio(monitor.command_audio, "COMMAND")
        
        # Compare audio
        comparison = monitor.compare_audio()
        interpretation = monitor.interpret_results(comparison)
        
        return {
            "success": True,
            "execution_time": exec_time,
            "audio_interpretation": interpretation,
            "comparison": comparison,
            "result": result,
            "baseline_analysis": monitor.baseline_analysis,
            "command_analysis": monitor.command_analysis
        }
    else:
        return {
            "success": False, 
            "error": "No audio recorded during execution",
            "result": result
        }


def monitor_command(command: str, baseline_duration: float = 2.0, 
                   device_id: Optional[int] = None, shell: bool = True) -> Dict[str, Any]:
    """
    Monitor audio changes while executing a shell command.
    
    Args:
        command: Shell command to execute
        baseline_duration: Duration in seconds to record baseline audio
        device_id: Specific audio device ID to use (None for auto-detection)
        shell: Whether to use shell for command execution
    
    Returns:
        Dictionary containing results and audio analysis
    """
    return monitor_sound(command, baseline_duration=baseline_duration, 
                        device_id=device_id, shell=shell)


def main():
    """Command line interface for the audio monitor."""
    parser = argparse.ArgumentParser(
        description="Monitor audio changes during command execution",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Test with echo command
  python monitor_sound.py "echo Hello World"
  
  # Test with micropump
  python monitor_sound.py "python cli.py config.yaml"
  
  # Test with longer baseline
  python monitor_sound.py --baseline 3.0 "your_command"
  
  # Use specific audio device
  python monitor_sound.py --device 1 "your_command"
        """
    )
    
    parser.add_argument("command", help="Command to execute while monitoring audio")
    parser.add_argument("--baseline", type=float, default=2.0,
                       help="Baseline duration in seconds (default: 2.0)")
    parser.add_argument("--device", type=int, default=None,
                       help="Specific audio device ID to use")
    parser.add_argument("--no-shell", action="store_true",
                       help="Don't use shell for command execution")
    
    args = parser.parse_args()
    
    print("MIC AUDIO COMMAND MONITOR")
    print("=" * 50)
    print(f"Command: {args.command}")
    print(f"Baseline duration: {args.baseline}s")
    if args.device is not None:
        print(f"Audio device: {args.device}")
    print("=" * 50)
    
    try:
        command = args.command if not args.no_shell else args.command.split()
        result = monitor_sound(command, baseline_duration=args.baseline, 
                             device_id=args.device, shell=not args.no_shell)
        
        if result["success"]:
            print("\nOK Audio monitoring completed successfully!")
            print(f"STATS Result: {result['audio_interpretation']}")
            if result.get('comparison'):
                comp = result['comparison']
                print(f"UP RMS change: {comp['rms_change_pct']:+.1f}%")
                print(f"UP Peak change: {comp['peak_change_pct']:+.1f}%")
            sys.exit(0)
        else:
            print(f"\nFAIL Audio monitoring failed: {result.get('error', 'Unknown error')}")
            sys.exit(1)
            
    except KeyboardInterrupt:
        print("\nFAIL Interrupted by user")
        sys.exit(1)
    except Exception as e:
        print(f"\nFAIL Error: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    main()