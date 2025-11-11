"""
Audio device configuration - saves working device IDs per computer
"""
import os
from pathlib import Path
from typing import Optional

# Use .env file in project root
ENV_FILE = Path(__file__).parent.parent / ".env"


def save_audio_config(input_device: Optional[int] = None, output_device: Optional[int] = None) -> None:
    """Save audio device configuration to .env file"""
    lines = []
    
    # Read existing .env file
    if ENV_FILE.exists():
        with open(ENV_FILE, 'r') as f:
            lines = f.readlines()
    
    # Remove old audio config lines
    lines = [line for line in lines if not line.startswith('AUDIO_INPUT_DEVICE=') 
             and not line.startswith('AUDIO_OUTPUT_DEVICE=')]
    
    # Add new audio config
    if input_device is not None:
        lines.append(f'AUDIO_INPUT_DEVICE={input_device}\n')
    if output_device is not None:
        lines.append(f'AUDIO_OUTPUT_DEVICE={output_device}\n')
    
    # Write back
    with open(ENV_FILE, 'w') as f:
        f.writelines(lines)
    
    print(f"✓ Saved audio config to {ENV_FILE}")


def load_audio_config() -> dict:
    """Load audio device configuration from .env file"""
    config = {}
    
    if ENV_FILE.exists():
        with open(ENV_FILE, 'r') as f:
            for line in f:
                line = line.strip()
                if line.startswith('AUDIO_INPUT_DEVICE='):
                    config['input_device'] = int(line.split('=')[1])
                elif line.startswith('AUDIO_OUTPUT_DEVICE='):
                    config['output_device'] = int(line.split('=')[1])
    
    if config:
        print(f"✓ Loaded audio config: input={config.get('input_device')}, output={config.get('output_device')}")
    
    return config


def get_input_device() -> Optional[int]:
    """Get saved input device ID"""
    config = load_audio_config()
    return config.get('input_device')


def get_output_device() -> Optional[int]:
    """Get saved output device ID"""
    config = load_audio_config()
    return config.get('output_device')
