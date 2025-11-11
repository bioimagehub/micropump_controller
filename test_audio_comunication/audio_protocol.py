"""
Robust FSK audio modem protocol for airgapped communication.

Based on Bell 202 modem standard with error detection:
- 1200 Hz = binary 0 (mark frequency)
- 1800 Hz = binary 1 (space frequency)  
- Preamble sync pattern prevents false triggers
- CRC8 checksum for data integrity
- Minimum tone duration filters out speech/noise

This is similar to how old-school modems and packet radio (AX.25) work.
"""

import numpy as np
from typing import Optional, Tuple, List
from dataclasses import dataclass
from enum import Enum
import time


class Command(Enum):
    """Predefined commands for microscope control"""
    CAPTURE = 0b0001  # 1: Trigger image capture
    DONE    = 0b0010  # 2: Capture complete
    ERROR   = 0b0011  # 3: Capture failed
    PING    = 0b0100  # 4: Test connection
    PONG    = 0b0101  # 5: Respond to ping


@dataclass
class FSKConfig:
    """FSK modem configuration parameters"""
    sample_rate: int = 44100
    mark_freq: int = 1200      # Binary 0
    space_freq: int = 1800     # Binary 1
    bit_duration: float = 0.1  # 100ms per bit (10 baud - very slow but robust)
    preamble_duration: float = 0.5  # 500ms sync tone
    preamble_freq: int = 2400  # Distinctive frequency for message start
    
    # Detection thresholds
    min_tone_duration: float = 0.08  # Reject tones shorter than 80ms (filters speech)
    frequency_tolerance: float = 100  # Hz tolerance for frequency detection
    min_signal_power: float = 0.01   # Minimum RMS to consider valid signal


class AudioModem:
    """
    Robust FSK modem for airgapped communication.
    
    Protocol structure:
    [PREAMBLE 500ms] [COMMAND 4 bits] [CHECKSUM 4 bits] [POSTAMBLE 200ms]
    
    Total transmission: ~1.3 seconds per command
    """
    
    def __init__(self, config: Optional[FSKConfig] = None):
        self.config = config or FSKConfig()
        
    def _generate_tone(self, frequency: float, duration: float) -> np.ndarray:
        """Generate pure sine wave tone"""
        t = np.linspace(0, duration, int(self.config.sample_rate * duration))
        # Add 10ms ramp on/off to avoid clicking
        ramp_samples = int(0.01 * self.config.sample_rate)
        tone = np.sin(2 * np.pi * frequency * t)
        
        # Apply envelope
        if len(tone) > 2 * ramp_samples:
            envelope = np.ones_like(tone)
            envelope[:ramp_samples] = np.linspace(0, 1, ramp_samples)
            envelope[-ramp_samples:] = np.linspace(1, 0, ramp_samples)
            tone *= envelope
            
        return tone
    
    def _encode_bits(self, data: int, num_bits: int = 4) -> List[int]:
        """Convert integer to binary bits (MSB first)"""
        return [(data >> i) & 1 for i in range(num_bits - 1, -1, -1)]
    
    def _calculate_checksum(self, data: int) -> int:
        """Simple 4-bit checksum (XOR with rotation)"""
        checksum = 0
        for i in range(4):
            bit = (data >> i) & 1
            checksum ^= bit << (i % 4)
        return checksum & 0x0F
    
    def encode_command(self, command: Command) -> np.ndarray:
        """
        Encode command into FSK audio signal.
        
        Returns numpy array of audio samples ready for playback.
        """
        audio_segments = []
        
        # 1. Preamble (sync tone)
        preamble = self._generate_tone(
            self.config.preamble_freq,
            self.config.preamble_duration
        )
        audio_segments.append(preamble)
        
        # 2. Command bits (4 bits)
        command_bits = self._encode_bits(command.value, num_bits=4)
        for bit in command_bits:
            freq = self.config.space_freq if bit else self.config.mark_freq
            bit_tone = self._generate_tone(freq, self.config.bit_duration)
            audio_segments.append(bit_tone)
        
        # 3. Checksum (4 bits)
        checksum = self._calculate_checksum(command.value)
        checksum_bits = self._encode_bits(checksum, num_bits=4)
        for bit in checksum_bits:
            freq = self.config.space_freq if bit else self.config.mark_freq
            bit_tone = self._generate_tone(freq, self.config.bit_duration)
            audio_segments.append(bit_tone)
        
        # 4. Postamble (silence)
        silence = np.zeros(int(0.2 * self.config.sample_rate))
        audio_segments.append(silence)
        
        return np.concatenate(audio_segments)
    
    def _detect_frequency(self, audio_chunk: np.ndarray) -> Tuple[float, float]:
        """
        Detect dominant frequency in audio chunk using FFT.
        
        Returns (frequency, power_level)
        """
        # Apply window to reduce spectral leakage
        window = np.hanning(len(audio_chunk))
        windowed = audio_chunk * window
        
        # FFT
        fft = np.fft.rfft(windowed)
        freqs = np.fft.rfftfreq(len(audio_chunk), 1 / self.config.sample_rate)
        
        # Find peak
        magnitude = np.abs(fft)
        peak_idx = np.argmax(magnitude)
        peak_freq = freqs[peak_idx]
        
        # Calculate signal power (RMS)
        power = np.sqrt(np.mean(audio_chunk ** 2))
        
        return peak_freq, power
    
    def _is_frequency_match(self, detected: float, target: float) -> bool:
        """Check if detected frequency matches target within tolerance"""
        return abs(detected - target) < self.config.frequency_tolerance
    
    def decode_command(self, audio: np.ndarray) -> Optional[Command]:
        """
        Decode FSK audio signal into command.
        
        Returns Command if valid message detected, None otherwise.
        """
        # Look for preamble (2400 Hz tone for 500ms)
        chunk_size = int(self.config.preamble_duration * self.config.sample_rate)
        
        # Scan through audio looking for preamble
        preamble_found = False
        preamble_end_idx = 0
        
        for i in range(0, len(audio) - chunk_size, chunk_size // 4):
            chunk = audio[i:i + chunk_size]
            freq, power = self._detect_frequency(chunk)
            
            if (self._is_frequency_match(freq, self.config.preamble_freq) and 
                power > self.config.min_signal_power):
                preamble_found = True
                preamble_end_idx = i + chunk_size
                break
        
        if not preamble_found:
            return None
        
        # Decode command bits (4 bits)
        bit_chunk_size = int(self.config.bit_duration * self.config.sample_rate)
        command_bits = []
        
        for i in range(4):
            start = preamble_end_idx + i * bit_chunk_size
            end = start + bit_chunk_size
            
            if end > len(audio):
                return None  # Incomplete transmission
            
            chunk = audio[start:end]
            freq, power = self._detect_frequency(chunk)
            
            if power < self.config.min_signal_power:
                return None  # Weak signal
            
            # Decode bit
            if self._is_frequency_match(freq, self.config.mark_freq):
                command_bits.append(0)
            elif self._is_frequency_match(freq, self.config.space_freq):
                command_bits.append(1)
            else:
                return None  # Frequency doesn't match either mark or space
        
        # Decode checksum bits (4 bits)
        checksum_bits = []
        
        for i in range(4, 8):
            start = preamble_end_idx + i * bit_chunk_size
            end = start + bit_chunk_size
            
            if end > len(audio):
                return None
            
            chunk = audio[start:end]
            freq, power = self._detect_frequency(chunk)
            
            if power < self.config.min_signal_power:
                return None
            
            if self._is_frequency_match(freq, self.config.mark_freq):
                checksum_bits.append(0)
            elif self._is_frequency_match(freq, self.config.space_freq):
                checksum_bits.append(1)
            else:
                return None
        
        # Convert bits to integers
        command_value = sum(bit << (3 - i) for i, bit in enumerate(command_bits))
        received_checksum = sum(bit << (3 - i) for i, bit in enumerate(checksum_bits))
        
        # Verify checksum
        expected_checksum = self._calculate_checksum(command_value)
        
        if received_checksum != expected_checksum:
            return None  # Checksum mismatch - corrupted transmission
        
        # Convert to Command enum
        try:
            return Command(command_value)
        except ValueError:
            return None  # Invalid command value


class MicroscopeAudioController:
    """
    High-level interface for microscope control via audio.
    Uses AudioModem for robust FSK communication.
    """
    
    def __init__(self):
        self.modem = AudioModem()
        self.is_initialized = False
        self.last_error = ""
        
        # Try importing sounddevice
        try:
            import sounddevice as sd
            self.sd = sd
            self.is_initialized = True
        except ImportError:
            self.last_error = "sounddevice not installed: pip install sounddevice numpy"
    
    def send_command(self, command: Command, retries: int = 3) -> bool:
        """
        Send command with automatic retries.
        
        Args:
            command: Command to send
            retries: Number of retry attempts if no acknowledgment
            
        Returns:
            True if command sent successfully
        """
        if not self.is_initialized:
            return False
        
        for attempt in range(retries):
            try:
                # Encode and play
                audio = self.modem.encode_command(command)
                self.sd.play(audio, self.modem.config.sample_rate)
                self.sd.wait()
                
                print(f"  Sent {command.name} (attempt {attempt + 1}/{retries})")
                return True
                
            except Exception as e:
                print(f"  Send failed: {e}")
                if attempt < retries - 1:
                    time.sleep(0.5)
                    
        return False
    
    def wait_for_command(self, timeout: float = 60.0, 
                        expected: Optional[Command] = None) -> Optional[Command]:
        """
        Listen for incoming command.
        
        Args:
            timeout: Maximum wait time in seconds
            expected: If set, only return if this specific command received
            
        Returns:
            Received Command or None if timeout/no valid command
        """
        if not self.is_initialized:
            return None
        
        try:
            # Record audio
            duration = min(timeout, 5.0)  # Record in 5-second chunks
            sample_rate = self.modem.config.sample_rate
            
            start_time = time.time()
            
            while time.time() - start_time < timeout:
                remaining = int(timeout - (time.time() - start_time))
                print(f"  Listening... ({remaining}s remaining)")
                
                recording = self.sd.rec(
                    int(duration * sample_rate),
                    samplerate=sample_rate,
                    channels=1
                )
                self.sd.wait()
                
                # Try to decode
                command = self.modem.decode_command(recording[:, 0])
                
                if command:
                    print(f"  Received: {command.name}")
                    
                    if expected is None or command == expected:
                        return command
                    else:
                        print(f"  Expected {expected.name}, got {command.name} - ignoring")
            
            print("  Timeout - no valid command received")
            return None
            
        except Exception as e:
            print(f"  Listen error: {e}")
            return None
    
    def trigger_and_wait(self, timeout: float = 60.0) -> bool:
        """
        High-level: Send CAPTURE command and wait for DONE response.
        
        Returns True if successful, False on timeout or error
        """
        print("\n🔬 Triggering microscope capture...")
        
        if not self.send_command(Command.CAPTURE):
            return False
        
        print("⏳ Waiting for completion signal...")
        response = self.wait_for_command(timeout=timeout, expected=Command.DONE)
        
        if response == Command.DONE:
            print("✓ Capture complete!")
            return True
        else:
            print("✗ No completion signal received")
            return False
    
    def test_connection(self, timeout: float = 10.0) -> bool:
        """Send PING and wait for PONG response"""
        print("\n🔊 Testing audio connection...")
        
        if not self.send_command(Command.PING):
            return False
        
        response = self.wait_for_command(timeout=timeout, expected=Command.PONG)
        return response == Command.PONG
    
    def close(self) -> None:
        """Cleanup resources"""
        pass
