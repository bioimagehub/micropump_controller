#!/usr/bin/env python3
"""
Windows-native Bartels micropump control using pyserial
Based on the working pybartelslabtronix implementation.

This script uses serial communication instead of direct USB to control the Bartels micropump.
Requires FTDI VCP drivers to create a COM port.
"""

import serial
import serial.tools.list_ports
import threading
import time
import logging

class BartelsPumpSerial:
    """
    Bartels micropump controller using serial communication.
    Based on pybartelslabtronix implementation.
    """
    
    def __init__(self, port=None, baud=9600, timeout=1):
        self.port = port
        self.baud = baud
        self.timeout = timeout
        self.ser = None
        self.buffer = ""
        self.reading = False
        
        # Setup logging
        logging.basicConfig(level=logging.INFO, format='%(asctime)s [%(levelname)s] %(message)s')
        self.log = logging.getLogger(__name__)
        
        # Auto-detect port if not specified
        if not self.port:
            self.port = self._find_bartels_port()
        
        if self.port:
            self._connect()
        else:
            self.log.error("No Bartels device found. Please install FTDI VCP drivers.")
    
    def _find_bartels_port(self):
        """Find the Bartels micropump COM port."""
        self.log.info("Scanning for Bartels micropump...")
        
        ports = serial.tools.list_ports.comports()
        for port in ports:
            self.log.info(f"Found COM port: {port.device} - {port.description}")
            # Look for FTDI devices with Bartels identifiers
            if any(keyword in str(port).lower() for keyword in ['ftdi', 'bartels', 'micropump', 'bami']):
                self.log.info(f"Potential Bartels device found on {port.device}")
                return port.device
        
        # If no obvious match, try common ports
        for port_name in ['COM3', 'COM4', 'COM5', 'COM6']:
            try:
                test_ser = serial.Serial(port_name, self.baud, timeout=0.5)
                test_ser.close()
                self.log.info(f"Accessible COM port found: {port_name}")
                return port_name
            except:
                continue
        
        return None
    
    def _connect(self):
        """Connect to the serial port."""
        try:
            # Use same settings as pybartelslabtronix
            self.ser = serial.Serial(
                port=self.port,
                baudrate=self.baud,
                timeout=self.timeout,
                xonxoff=True  # XON/XOFF flow control - critical for Bartels!
            )
            
            # Wait for connection
            while not self.ser.is_open:
                time.sleep(0.1)
            
            self.log.info(f"Connected to Bartels micropump on {self.port}")
            
            # Start background reading thread
            self.reading_thread = threading.Thread(target=self._read_continuously, daemon=True)
            self.reading_thread.start()
            
        except Exception as e:
            self.log.error(f"Failed to connect to {self.port}: {e}")
            self.ser = None
    
    def _read_continuously(self):
        """Continuously read from serial port (background thread)."""
        while self.ser and self.ser.is_open:
            try:
                time.sleep(0.05)  # 50ms polling like pybartelslabtronix
                if self.ser.in_waiting > 0:
                    self.reading = True
                    data = self.ser.read(self.ser.in_waiting).decode('utf-8', errors='ignore')
                    self.buffer += data
                else:
                    self.reading = False
            except Exception as e:
                self.log.error(f"Error reading from serial: {e}")
                break
    
    def _send_command(self, command):
        """Send a command to the pump."""
        if not self.ser or not self.ser.is_open:
            self.log.error("No serial connection")
            return False
        
        try:
            # Add carriage return like pybartelslabtronix
            full_command = command + "\r"
            self.ser.write(full_command.encode('utf-8'))
            self.ser.flush()
            self.log.info(f"Sent command: '{command}'")
            return True
        except Exception as e:
            self.log.error(f"Failed to send command '{command}': {e}")
            return False
    
    def get_status(self):
        """Get pump status by sending empty command."""
        self.buffer = ""  # Clear buffer
        self._send_command("")  # Empty command requests status
        
        # Wait for response
        timeout = time.time() + 2.0
        while (len(self.buffer) < 1 or self.reading) and time.time() < timeout:
            time.sleep(0.01)
        
        if self.buffer:
            self.log.info(f"Status response: {repr(self.buffer)}")
            return self.buffer
        else:
            self.log.warning("No status response received")
            return None
    
    def turn_on(self):
        """Turn pump on."""
        return self._send_command("bon")
    
    def turn_off(self):
        """Turn pump off."""
        return self._send_command("boff")
    
    def set_frequency(self, freq):
        """Set frequency (1-300 Hz)."""
        if 1 <= freq <= 300:
            return self._send_command(f"F{freq}")
        else:
            self.log.error(f"Invalid frequency: {freq} (must be 1-300)")
            return False
    
    def set_amplitude(self, amp):
        """Set amplitude (1-250 Vpp)."""
        if 1 <= amp <= 250:
            return self._send_command(f"A{amp}")
        else:
            self.log.error(f"Invalid amplitude: {amp} (must be 1-250)")
            return False
    
    def set_waveform_rectangular(self):
        """Set rectangular waveform."""
        return self._send_command("MR")
    
    def set_waveform_sine(self):
        """Set sine waveform."""
        return self._send_command("MS")
    
    def set_waveform_srs(self):
        """Set SRS waveform."""
        return self._send_command("MC")
    
    def close(self):
        """Close the serial connection."""
        if self.ser:
            self.ser.close()
            self.log.info("Serial connection closed")


def main():
    """Test the Bartels pump communication."""
    print("=== Bartels Micropump Serial Control Test ===")
    
    # Create pump controller
    pump = BartelsPumpSerial()
    
    if not pump.ser:
        print("ERROR: Could not connect to pump")
        print("Please ensure:")
        print("1. FTDI VCP drivers are installed")
        print("2. Pump is connected via USB")
        print("3. Device appears in Device Manager as COM port")
        return
    
    try:
        print("\n1. Getting initial status...")
        status = pump.get_status()
        if status:
            print(f"Initial status: {status}")
        
        print("\n2. Setting up pump parameters...")
        pump.set_frequency(100)
        time.sleep(0.2)
        pump.set_amplitude(100)
        time.sleep(0.2)
        pump.set_waveform_rectangular()
        time.sleep(0.2)
        
        print("\n3. Getting updated status...")
        status = pump.get_status()
        if status:
            print(f"Updated status: {status}")
        
        print("\n4. Turning pump ON for 10 seconds...")
        pump.turn_on()
        print("*** PUMP SHOULD BE MAKING SOUND NOW ***")
        print("Listen for pump operation...")
        
        # Run for 10 seconds
        for i in range(10):
            print(f"Running... {10-i} seconds remaining")
            time.sleep(1)
        
        print("\n5. Turning pump OFF...")
        pump.turn_off()
        print("*** PUMP SHOULD BE QUIET NOW ***")
        
        print("\n6. Getting final status...")
        status = pump.get_status()
        if status:
            print(f"Final status: {status}")
        
        print("\nTest completed successfully!")
        
    except KeyboardInterrupt:
        print("\nTest interrupted by user")
    except Exception as e:
        print(f"Test failed with error: {e}")
    finally:
        pump.close()


if __name__ == "__main__":
    main()
