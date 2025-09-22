"""Simple serial-only pump controller for Bartels micropump unit."""

import time
import serial
import logging


class PumpController:
    """Bartels micropump controller using serial communication only."""
    
    def __init__(self, port: str, baudrate: int = 9600):
        self.port = port
        self.baudrate = baudrate
        self.ser = None
        self._initialize()
    
    def _initialize(self):
        """Initialize serial connection to pump."""
        try:
            self.ser = serial.Serial(
                port=self.port,
                baudrate=self.baudrate,
                timeout=2,
                xonxoff=True  # XON/XOFF flow control often needed for Bartels
            )
            logging.info(f'Pump connection established on {self.port}')
        except serial.SerialException as e:
            logging.error(f'No pump found on {self.port}: {e}')
            self.ser = None
    
    def close(self):
        """Close serial connection."""
        if self.ser is not None:
            try:
                self.ser.close()
                logging.info("Pump connection closed")
            except Exception:
                pass
    
    def _send_command(self, command: str):
        """Send command to pump with carriage return terminator."""
        if self.ser is None:
            logging.error("Pump is not initialized.")
            return False
        try:
            full_command = command + "\r"
            self.ser.write(full_command.encode("utf-8"))
            self.ser.flush()
            logging.info(f"Sent command: '{command}'")
            return True
        except Exception as e:
            logging.error(f"Failed to send command '{command}': {e}")
            return False
    
    def set_frequency(self, freq: int):
        """Set pump frequency in Hz (1-300)."""
        if 1 <= freq <= 300:
            self._send_command(f"F{freq}")
            time.sleep(0.15)  # Allow processing time
        else:
            logging.error(f"Invalid frequency: {freq} (must be 1-300)")
    
    def set_voltage(self, voltage: int):
        """Set pump voltage/amplitude (1-250 Vpp).""" 
        if 1 <= voltage <= 250:
            self._send_command(f"A{voltage}")
            time.sleep(0.15)
        else:
            logging.error(f"Invalid voltage: {voltage} (must be 1-250)")
    
    def set_waveform(self, waveform: str):
        """Set pump waveform (RECT, SINE, etc)."""
        waveform_map = {
            "RECT": "MR",
            "RECTANGLE": "MR", 
            "SINE": "MS",
            "SIN": "MS"
        }
        cmd = waveform_map.get(waveform.upper(), waveform.upper())
        self._send_command(cmd)
        time.sleep(0.15)
    
    def start(self):
        """Start the pump."""
        self._send_command("bon")
        logging.info("Pump started")
    
    def stop(self):
        """Stop the pump.""" 
        self._send_command("boff")
        logging.info("Pump stopped")
    
    def pulse(self, duration: float):
        """Run pump for specified duration then stop."""
        self.start()
        time.sleep(duration)
        self.stop()
    
    # Legacy method names for compatibility
    def bartels_set_freq(self, freq: int):
        """Legacy compatibility method."""
        self.set_frequency(freq)
    
    def bartels_set_voltage(self, voltage: int):
        """Legacy compatibility method."""
        self.set_voltage(voltage)
    
    def bartels_set_waveform(self, waveform: str):
        """Legacy compatibility method."""
        self.set_waveform(waveform)
    
    def bartels_start(self):
        """Legacy compatibility method."""
        self.start()
    
    def bartels_stop(self):
        """Legacy compatibility method.""" 
        self.stop()
    
    def pump_cycle(self, run_time: float):
        """Legacy compatibility method."""
        self.pulse(run_time)