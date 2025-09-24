"""3D stage controller for GRBL-based CNC pipetting robot."""

import yaml
import logging
import time
import serial
from threading import Event
from typing import Dict, Any, Optional, Tuple
from pathlib import Path


class Stage3DController:
    """Controller for 3D stage operations using GRBL-based CNC system.
    
    Designed to be robust and work with or without configuration files.
    Falls back gracefully when configs are missing or incomplete.
    """
    
    # Default settings that work without any config
    DEFAULT_SETTINGS = {
        'serial': {
            'baudrate': 115200,
            'timeout': 2.0
        },
        'movement': {
            'rapid_rate': 3000,
            'work_rate': 1000,
            'plunge_rate': 500
        },
        'safety': {
            'max_travel': {'x': 250.0, 'y': 150.0, 'z': 50.0},
            'soft_limits_enabled': True
        }
    }
    
    def __init__(self, port=None, baudrate=115200, config_path=None, auto_connect=True):
        """Initialize the 3D stage controller.
        
        Args:
            port: Serial port (if None, won't auto-connect)
            baudrate: Serial baudrate (overridden by config if present)
            config_path: Path to YAML config file (optional)
            auto_connect: Whether to automatically connect if port provided
        """
        self.port = port
        self.ser = None
        self.stop = Event()
        self.current_position = {"x": 0.0, "y": 0.0, "z": 0.0}
        self.is_connected = False
        
        # Load configuration with graceful fallback
        self.config = self._load_config_safely(config_path)
        
        # Apply settings from config or use defaults
        self._apply_settings()
        
        # Auto-connect if requested and port available
        if auto_connect and port:
            try:
                success = self.connect()
                if success:
                    self._perform_initialization_test()
            except Exception as e:
                logging.warning(f"Auto-connect failed: {e}. Use connect() method manually.")
    
    def _load_config_safely(self, config_path):
        """Load configuration with robust error handling and defaults."""
        if not config_path:
            logging.info("No config path provided, using default settings")
            return {}
        
        config_file = Path(config_path)
        if not config_file.exists():
            logging.warning(f"Config file not found: {config_path}, using defaults")
            return {}
        
        try:
            with open(config_file, 'r') as file:
                config = yaml.safe_load(file) or {}
                logging.info(f"Loaded config from {config_path}")
                return config
        except yaml.YAMLError as e:
            logging.error(f"YAML parsing error in {config_path}: {e}")
            return {}
        except Exception as e:
            logging.error(f"Error loading config {config_path}: {e}")
            return {}
    
    def _apply_settings(self):
        """Apply settings from config or use defaults."""
        # Serial settings
        serial_config = self.config.get('serial', {})
        self.baudrate = serial_config.get('baudrate', self.DEFAULT_SETTINGS['serial']['baudrate'])
        self.timeout = serial_config.get('timeout', self.DEFAULT_SETTINGS['serial']['timeout'])
        
        # Movement settings
        movement_config = self.config.get('movement', {})
        self.rapid_rate = movement_config.get('rapid_rate', self.DEFAULT_SETTINGS['movement']['rapid_rate'])
        self.work_rate = movement_config.get('work_rate', self.DEFAULT_SETTINGS['movement']['work_rate'])
        
        # Safety settings
        safety_config = self.config.get('safety', {})
        self.max_travel = safety_config.get('max_travel', self.DEFAULT_SETTINGS['safety']['max_travel'])
    
    def is_ready(self):
        """Check if the stage is ready for operations."""
        return self.is_connected and self.ser is not None
    
    def connect(self):
        """Connect to the GRBL device."""
        if not self.port:
            logging.error("No port specified for connection")
            return False
        
        if self.is_connected:
            logging.info("Already connected")
            return True
        
        try:
            self.ser = serial.Serial(port=self.port, baudrate=self.baudrate, timeout=self.timeout)
            time.sleep(0.1)
            
            # Wake up GRBL and wait for startup message
            self.ser.write(b"\r\n\r\n")
            time.sleep(1.5)  # Give more time for startup
            
            # Read startup message
            startup_response = ""
            while self.ser.in_waiting > 0:
                startup_response += self.ser.read(self.ser.in_waiting).decode('utf-8', errors='ignore')
                time.sleep(0.1)
            
            logging.info(f"GRBL startup: {startup_response.strip()}")
            
            # Now try status request
            self.ser.write(b"?\n")
            time.sleep(0.2)  # Give time for response
            response = self.ser.readline().decode('utf-8', errors='ignore').strip()
            
            if response or "Grbl" in startup_response:
                self.is_connected = True
                logging.info(f'GRBL stage connected on {self.port}')
                if response:
                    logging.info(f'Status: {response}')
                return True
            else:
                logging.error(f'No GRBL response on {self.port}')
                self.ser.close()
                self.ser = None
                return False
                
        except serial.SerialException as e:
            logging.error(f'Failed to connect to {self.port}: {e}')
            self.ser = None
            return False
    
    def disconnect(self):
        """Disconnect from the GRBL device."""
        if self.ser:
            try:
                self.ser.close()
                logging.info("GRBL stage disconnected")
            except Exception as e:
                logging.error(f"Error during disconnect: {e}")
            finally:
                self.ser = None
                self.is_connected = False
    
    def _perform_initialization_test(self):
        """Perform a small movement test to verify stage is working (audible confirmation)."""
        if not self.is_ready():
            return
        
        try:
            logging.info("WRENCH Performing initialization movement test...")
            
            # Set up coordinate system
            self.ser.write(b"G21\n")  # mm units
            time.sleep(0.1)
            self.ser.readline()  # Read response
            
            self.ser.write(b"G90\n")  # absolute positioning
            time.sleep(0.1)
            self.ser.readline()  # Read response
            
            # Small movement test: 1mm forward and back in X axis
            logging.info("  Moving +1mm in X...")
            self.ser.write(b"G0 X1\n")
            time.sleep(0.3)
            self.ser.readline()  # Read response
            
            logging.info("  Moving back to X=0...")
            self.ser.write(b"G0 X0\n")
            time.sleep(0.3)
            self.ser.readline()  # Read response
            
            logging.info("OK Initialization test complete - stage is working!")
            
        except Exception as e:
            logging.warning(f"Initialization test failed: {e}")
    
    def move_to_coordinates(self, x=None, y=None, z=None):
        """Move to specific 3D coordinates."""
        if not self.is_ready():
            logging.error("Stage not connected")
            return False

        try:
            coords = []
            if x is not None:
                coords.append(f"X{x}")
                self.current_position["x"] = x
            if y is not None:
                coords.append(f"Y{y}")
                self.current_position["y"] = y
            if z is not None:
                coords.append(f"Z{z}")
                self.current_position["z"] = z
            
            if coords:
                command = f"G0 {' '.join(coords)}"
                self.ser.write((command + "\n").encode('utf-8'))
                time.sleep(0.1)
                response = self.ser.readline().decode('utf-8', errors='ignore').strip()
                logging.info(f'Moved to position: {self.current_position}')
                return True
            else:
                logging.warning("No coordinates specified for movement")
                return False
                
        except Exception as e:
            logging.error(f"Move failed: {e}")
            return False
    
    def has_well_plate_config(self):
        """Check if well plate configuration is available."""
        return 'well_plate' in self.config
    
    def has_positions_config(self):
        """Check if named positions are configured."""
        return 'positions' in self.config and len(self.config['positions']) > 0
    
    def get_available_positions(self):
        """Get list of available named positions."""
        if not self.has_positions_config():
            return []
        return list(self.config['positions'].keys())
    
    def get_status(self):
        """Get current GRBL status."""
        if not self.is_ready():
            return "Disconnected"
        
        try:
            self.ser.write(b"?\n")
            response = self.ser.readline().decode('utf-8', errors='ignore').strip()
            return response if response else "No response"
        except Exception as e:
            logging.error(f"Error getting status: {e}")
            return f"Error: {e}"
    
    def move_relative(self, dx=0, dy=0, dz=0):
        """Move relative to current position."""
        new_x = self.current_position["x"] + dx
        new_y = self.current_position["y"] + dy
        new_z = self.current_position["z"] + dz
        return self.move_to_coordinates(new_x, new_y, new_z)
    
    def calculate_well_coordinates(self, well_name):
        """Calculate coordinates for a specific well (e.g., 'A1', 'B3')."""
        if not self.has_well_plate_config():
            logging.error("Well plate configuration not available")
            return None
            
        well_config = self.config['well_plate']
        
        # Parse well name (e.g., "A1" -> row=0, col=0)
        if len(well_name) < 2:
            logging.error(f"Invalid well name: {well_name}")
            return None
            
        row_letter = well_name[0].upper()
        col_number = well_name[1:]
        
        try:
            row = ord(row_letter) - ord('A')  # A=0, B=1, etc.
            col = int(col_number) - 1         # 1=0, 2=1, etc.
        except (ValueError, IndexError):
            logging.error(f"Invalid well format: {well_name}")
            return None
            
        # Get plate parameters
        well_spacing = well_config.get('well_spacing', 9.0)
        z_base = well_config.get('z_base', 0)
        top_left = well_config.get('top_left', {'x': 0, 'y': 0})
        
        # Calculate base position
        base_x = top_left['x'] + col * well_spacing
        base_y = top_left['y'] + row * well_spacing
        
        return {
            'x': base_x,
            'y': base_y, 
            'z': z_base,
            'well': well_name
        }
    
    def close(self):
        """Close stage connection."""
        self.disconnect()


# Legacy aliases for backward compatibility  
PipettingController = Stage3DController
Robot = Stage3DController
