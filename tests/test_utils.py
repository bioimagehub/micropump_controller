#!/usr/bin/env python3
"""
Audio testing utilities for quick verification of audio system functionality.
"""

import numpy as np
import sounddevice as sd
import sys
import time

def quick_audio_test():
    """Quick test to verify audio recording works."""
    print("MIC QUICK AUDIO TEST")
    print("=" * 40)
    
    try:
        # Test default device
        print("Testing default audio device...")
        
        # Get default input device info
        try:
            default_device = sd.query_devices(kind='input')
            print(f"Default device: {default_device}")
        except Exception as e:
            print(f"Error getting default device: {e}")
            return False
        
        # Record 1 second of audio
        print("Recording 1 second of audio...")
        duration = 1.0
        sample_rate = 44100
        
        audio_data = sd.rec(
            int(duration * sample_rate),
            samplerate=sample_rate,
            channels=1,
            dtype=np.int16
        )
        sd.wait()
        
        if audio_data is None or len(audio_data) == 0:
            print("FAIL No audio data recorded")
            return False
        
        # Analyze the recorded audio
        audio_flat = audio_data.flatten().astype(np.float32) / 32768.0
        
        rms = np.sqrt(np.mean(audio_flat**2))
        peak = np.max(np.abs(audio_flat))
        
        print(f"OK Recording successful!")
        print(f"   Duration: {duration}s")
        print(f"   Samples: {len(audio_flat)}")
        print(f"   RMS Level: {rms:.6f}")
        print(f"   Peak Level: {peak:.6f}")
        
        if rms > 0.001:
            print("SPEAKER Active audio detected")
        else:
            print("SHH Very quiet environment")
        
        return True
        
    except Exception as e:
        print(f"FAIL Audio test failed: {e}")
        return False

def test_device_by_id(device_id):
    """Test a specific audio device by ID."""
    print(f"MIC Testing device ID {device_id}")
    
    try:
        # Get device info
        devices = sd.query_devices()
        if device_id >= len(devices):
            print(f"FAIL Device ID {device_id} not found")
            return False
        
        device_info = devices[device_id]
        print(f"Device: {device_info}")
        
        # Test recording
        duration = 1.0
        sample_rate = 44100
        
        audio_data = sd.rec(
            int(duration * sample_rate),
            samplerate=sample_rate,
            channels=1,
            dtype=np.int16,
            device=device_id
        )
        sd.wait()
        
        if audio_data is None or len(audio_data) == 0:
            print(f"FAIL No audio data from device {device_id}")
            return False
        
        audio_flat = audio_data.flatten().astype(np.float32) / 32768.0
        rms = np.sqrt(np.mean(audio_flat**2))
        peak = np.max(np.abs(audio_flat))
        
        print(f"OK Device {device_id} works!")
        print(f"   RMS: {rms:.6f}, Peak: {peak:.6f}")
        
        return True
        
    except Exception as e:
        print(f"FAIL Device {device_id} test failed: {e}")
        return False

def list_audio_devices():
    """List all available audio devices."""
    print("SEARCH AUDIO DEVICES")
    print("=" * 40)
    
    try:
        devices = sd.query_devices()
        
        input_devices = []
        for i, device in enumerate(devices):
            if isinstance(device, dict) and device.get('max_input_channels', 0) > 0:
                input_devices.append((i, device))
        
        if not input_devices:
            print("FAIL No input devices found")
            return []
        
        print(f"Found {len(input_devices)} input devices:")
        for device_id, device_info in input_devices:
            name = device_info.get('name', f'Device {device_id}')
            channels = device_info.get('max_input_channels', 0)
            sample_rate = device_info.get('default_samplerate', 0)
            print(f"  {device_id}: {name} ({channels} ch, {sample_rate} Hz)")
        
        return input_devices
        
    except Exception as e:
        print(f"FAIL Error listing devices: {e}")
        return []

def main():
    """Main function for audio testing utilities."""
    import argparse
    
    parser = argparse.ArgumentParser(
        description="Audio testing utilities",
        formatter_class=argparse.RawDescriptionHelpFormatter
    )
    
    parser.add_argument("--list", action="store_true",
                       help="List all available audio devices")
    parser.add_argument("--test-device", type=int, metavar="ID",
                       help="Test specific device by ID")
    parser.add_argument("--quick", action="store_true",
                       help="Run quick audio test (default)")
    
    args = parser.parse_args()
    
    try:
        if args.list:
            list_audio_devices()
        elif args.test_device is not None:
            if not test_device_by_id(args.test_device):
                sys.exit(1)
        else:
            # Default: quick test
            if not quick_audio_test():
                sys.exit(1)
        
        print("\\nOK Audio testing completed!")
        
    except KeyboardInterrupt:
        print("\\nFAIL Interrupted by user")
        sys.exit(1)
    except Exception as e:
        print(f"\\nFAIL Error: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()