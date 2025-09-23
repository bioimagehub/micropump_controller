#!/usr/bin/env python3
"""
Audio device discovery and compatibility testing utility.
"""

import numpy as np
import sounddevice as sd
import sys
import time
from pathlib import Path

class AudioDiscovery:
    """Discover and test audio devices for compatibility."""
    
    def __init__(self):
        self.working_devices = []
        self.sample_rates = [44100, 48000, 22050]
        self.formats = [np.int16, np.float32]
    
    def query_all_devices(self):
        """Get information about all audio devices."""
        try:
            devices = sd.query_devices()
            print("🔍 AUDIO DEVICE DISCOVERY")
            print("=" * 60)
            
            if not devices:
                print("❌ No audio devices found")
                return []
            
            input_devices = []
            output_devices = []
            
            for i, device in enumerate(devices):
                if isinstance(device, dict):
                    device_info = {
                        'id': i,
                        'name': device.get('name', f'Device {i}'),
                        'hostapi': device.get('hostapi', 0),
                        'max_input_channels': device.get('max_input_channels', 0),
                        'max_output_channels': device.get('max_output_channels', 0),
                        'default_low_input_latency': device.get('default_low_input_latency', 0),
                        'default_low_output_latency': device.get('default_low_output_latency', 0),
                        'default_high_input_latency': device.get('default_high_input_latency', 0),
                        'default_high_output_latency': device.get('default_high_output_latency', 0),
                        'default_samplerate': device.get('default_samplerate', 44100)
                    }
                    
                    print(f"Device {i}: {device_info['name']}")
                    print(f"   Input channels: {device_info['max_input_channels']}")
                    print(f"   Output channels: {device_info['max_output_channels']}")
                    print(f"   Default sample rate: {device_info['default_samplerate']}")
                    print(f"   Input latency: {device_info['default_low_input_latency']:.3f}s")
                    print()
                    
                    if device_info['max_input_channels'] > 0:
                        input_devices.append(device_info)
                    if device_info['max_output_channels'] > 0:
                        output_devices.append(device_info)
            
            print(f"📊 Summary: {len(input_devices)} input devices, {len(output_devices)} output devices")
            return input_devices
            
        except Exception as e:
            print(f"❌ Error querying devices: {e}")
            return []
    
    def test_device_formats(self, device_id, device_name):
        """Test different sample rates and formats for a device."""
        print(f"\\n🧪 Testing device {device_id}: {device_name}")
        
        working_configs = []
        
        for sample_rate in self.sample_rates:
            for fmt in self.formats:
                try:
                    print(f"   Testing {sample_rate}Hz, {fmt.__name__}... ", end="")
                    
                    # Test with very short recording
                    audio = sd.rec(
                        int(0.1 * sample_rate),  # 0.1 second
                        samplerate=sample_rate,
                        channels=1,
                        dtype=fmt,
                        device=device_id
                    )
                    sd.wait()
                    
                    # Check if we got valid audio
                    if audio is not None and len(audio) > 0:
                        working_configs.append({
                            'device_id': device_id,
                            'device_name': device_name,
                            'sample_rate': sample_rate,
                            'format': fmt,
                            'channels': 1
                        })
                        print("✅ Works!")
                    else:
                        print("❌ No data")
                        
                except Exception as e:
                    print(f"❌ Failed: {str(e)[:30]}")
        
        return working_configs
    
    def test_all_input_devices(self):
        """Test all input devices for compatibility."""
        input_devices = self.query_all_devices()
        
        if not input_devices:
            print("❌ No input devices to test")
            return []
        
        print("\\n🧪 COMPATIBILITY TESTING")
        print("=" * 60)
        
        all_working_configs = []
        
        for device in input_devices:
            device_id = device['id']
            device_name = device['name']
            
            configs = self.test_device_formats(device_id, device_name)
            all_working_configs.extend(configs)
        
        self.working_devices = all_working_configs
        
        print(f"\\n📊 RESULTS: {len(all_working_configs)} working configurations found")
        
        return all_working_configs
    
    def display_working_devices(self):
        """Display all working device configurations."""
        if not self.working_devices:
            print("❌ No working devices found")
            return
        
        print("\\n✅ WORKING CONFIGURATIONS:")
        print("=" * 60)
        
        # Group by device
        device_groups = {}
        for config in self.working_devices:
            device_id = config['device_id']
            if device_id not in device_groups:
                device_groups[device_id] = {
                    'name': config['device_name'],
                    'configs': []
                }
            device_groups[device_id]['configs'].append(config)
        
        for device_id, group in device_groups.items():
            print(f"🎤 Device {device_id}: {group['name']}")
            for config in group['configs']:
                print(f"   • {config['sample_rate']}Hz, {config['format'].__name__}")
            print()
    
    def recommend_best_device(self):
        """Recommend the best device configuration."""
        if not self.working_devices:
            print("❌ No working devices to recommend")
            return None
        
        print("\\n🏆 RECOMMENDATION:")
        print("=" * 60)
        
        # Scoring criteria:
        # 1. Prefer 44100Hz (standard)
        # 2. Prefer int16 (common format)
        # 3. Prefer devices with "Stereo Mix" in name (usually reliable)
        
        scored_configs = []
        
        for config in self.working_devices:
            score = 0
            
            # Sample rate preference
            if config['sample_rate'] == 44100:
                score += 10
            elif config['sample_rate'] == 48000:
                score += 8
            
            # Format preference
            if config['format'] == np.int16:
                score += 5
            elif config['format'] == np.float32:
                score += 3
            
            # Device name preference
            device_name_lower = config['device_name'].lower()
            if 'stereo mix' in device_name_lower:
                score += 15
            elif 'microphone' in device_name_lower:
                score += 10
            elif 'line in' in device_name_lower:
                score += 8
            
            scored_configs.append((score, config))
        
        # Sort by score (highest first)
        scored_configs.sort(key=lambda x: x[0], reverse=True)
        
        best_config = scored_configs[0][1]
        
        print(f"🥇 BEST CHOICE:")
        print(f"   Device: {best_config['device_name']} (ID: {best_config['device_id']})")
        print(f"   Sample Rate: {best_config['sample_rate']} Hz")
        print(f"   Format: {best_config['format'].__name__}")
        print(f"   Channels: {best_config['channels']}")
        
        # Show top 3
        if len(scored_configs) > 1:
            print(f"\\n📋 ALTERNATIVES:")
            for i, (score, config) in enumerate(scored_configs[1:4], 2):
                print(f"   {i}. {config['device_name']} - {config['sample_rate']}Hz, {config['format'].__name__}")
        
        return best_config
    
    def test_recommended_device(self, config=None):
        """Test the recommended device with actual recording."""
        if config is None:
            config = self.recommend_best_device()
        
        if config is None:
            print("❌ No device to test")
            return False
        
        print(f"\\n🎯 TESTING RECOMMENDED DEVICE:")
        print("=" * 60)
        
        try:
            device_id = config['device_id']
            sample_rate = config['sample_rate']
            fmt = config['format']
            
            print(f"Device: {config['device_name']}")
            print(f"Recording 2 seconds of audio...")
            
            # Record 2 seconds
            audio = sd.rec(
                int(2 * sample_rate),
                samplerate=sample_rate,
                channels=1,
                dtype=fmt,
                device=device_id
            )
            sd.wait()
            
            if audio is None or len(audio) == 0:
                print("❌ No audio data recorded")
                return False
            
            # Analyze the audio
            if fmt == np.int16:
                audio_float = audio.astype(np.float32) / 32768.0
            else:
                audio_float = audio.astype(np.float32)
            
            audio_flat = audio_float.flatten()
            
            rms = np.sqrt(np.mean(audio_flat**2))
            peak = np.max(np.abs(audio_flat))
            mean_abs = np.mean(np.abs(audio_flat))
            
            print(f"✅ Recording successful!")
            print(f"   Duration: 2.00s")
            print(f"   Samples: {len(audio_flat)}")
            print(f"   RMS Level: {rms:.6f}")
            print(f"   Peak Level: {peak:.6f}")
            print(f"   Mean Level: {mean_abs:.6f}")
            
            if rms > 0.001:
                print(f"🔊 Active audio detected (RMS > 0.001)")
            else:
                print(f"🤫 Very quiet environment (RMS ≤ 0.001)")
            
            return True
            
        except Exception as e:
            print(f"❌ Test failed: {e}")
            return False

def main():
    """Main function to run audio discovery."""
    import argparse
    
    parser = argparse.ArgumentParser(
        description="Discover and test audio devices",
        formatter_class=argparse.RawDescriptionHelpFormatter
    )
    
    parser.add_argument("--test-only", action="store_true",
                       help="Only test the recommended device")
    parser.add_argument("--quiet", action="store_true",
                       help="Reduce output verbosity")
    
    args = parser.parse_args()
    
    try:
        discovery = AudioDiscovery()
        
        if args.test_only:
            # Just test the recommended device without full discovery
            print("🎯 Quick device test mode")
            discovery.working_devices = []
            
            # Get default input device
            try:
                default_device = sd.query_devices(kind='input')
                if default_device:
                    default_config = {
                        'device_id': None,  # Use default
                        'device_name': default_device['name'],
                        'sample_rate': 44100,
                        'format': np.int16,
                        'channels': 1
                    }
                    discovery.test_recommended_device(default_config)
                else:
                    print("❌ No default input device found")
            except Exception as e:
                print(f"❌ Error with default device: {e}")
        else:
            # Full discovery and testing
            discovery.test_all_input_devices()
            discovery.display_working_devices()
            
            recommended = discovery.recommend_best_device()
            
            if recommended:
                print("\\n" + "="*60)
                test_success = discovery.test_recommended_device(recommended)
                
                if test_success:
                    print("\\n✅ Audio system is ready for monitoring!")
                else:
                    print("\\n❌ Recommended device test failed")
            else:
                print("\\n❌ No suitable audio devices found")
    
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