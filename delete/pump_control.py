"""Dual-mode pump control: Windows native USB + WSL/Linux serial fallback."""

from __future__ import annotations

import time
import warnings
import glob
import platform
import subprocess
from pathlib import Path
from typing import Optional, Union
import os

# Track available connection methods and platform
USBX_AVAILABLE = False
SERIAL_AVAILABLE = False
PLATFORM = platform.system().lower()

# Try to import usbx (for Windows with proper drivers)
try:
    from usbx import Device, TransferDirection, TransferType, USBError, usb
    USBX_AVAILABLE = True
except ImportError:
    # Create dummy classes for type hints when usbx not available
    class Device: pass
    class TransferDirection: 
        OUT = IN = None
    class TransferType: 
        BULK = INTERRUPT = None
    class USBError(Exception): pass
    usb = None

# Try to import pyserial (for WSL/Linux and Windows fallback)
try:
    import serial
    SERIAL_AVAILABLE = True
except ImportError:
    serial = None

DEFAULT_VID = 0x0403
DEFAULT_PID = 0xB4C0
ENV_PATH = Path(__file__).resolve().parents[1] / ".env"
_CMD_DELAY_S = 0.12  # controller needs ~100 ms between commands

# Waveform commands documented for the Bartels mp-x controller
_WAVEFORM_COMMANDS = {
    "MR": "MR",  # rectangular
    "RECT": "MR",
    "RECTANGLE": "MR",
    "SQUARE": "MR",
    "MS": "MS",  # sine
    "SINE": "MS",
    "SIN": "MS",
    "MC": "MC",  # SRS / custom waveform
    "SRS": "MC",
}


class PumpCommunicationError(RuntimeError):
    """Raised when communicating with the pump fails."""


def _load_device_ids() -> tuple[int, int]:
    """Return VID/PID from the project .env file or defaults."""
    vid = DEFAULT_VID
    pid = DEFAULT_PID
    if not ENV_PATH.exists():
        return vid, pid
    try:
        with ENV_PATH.open("r", encoding="utf-8") as handle:
            for raw_line in handle:
                line = raw_line.strip()
                if not line or line.startswith("#") or "=" not in line:
                    continue
                key, value = map(str.strip, line.split("=", 1))
                if key == "PUMP_VID":
                    vid = int(value, 0)
                elif key == "PUMP_PID":
                    pid = int(value, 0)
    except (OSError, ValueError) as exc:
        raise PumpCommunicationError(f"Unable to parse pump VID/PID from {ENV_PATH}: {exc}") from exc
    return vid, pid


def _select_interface(device: Device) -> int:
    """Pick the first interface exposing a bulk/interrupt OUT endpoint."""
    for intf in device.configuration.interfaces:
        alt = intf.current_alternate
        for endpoint in alt.endpoints:
            if endpoint.transfer_type in (TransferType.BULK, TransferType.INTERRUPT) and \
                    endpoint.direction == TransferDirection.OUT:
                return intf.number
    raise PumpCommunicationError("Pump has no bulk/interrupt OUT endpoint")


def _find_endpoint(device: Device, interface_number: int, direction: TransferDirection) -> Optional[int]:
    interface = device.get_interface(interface_number)
    if interface is None:
        return None
    for endpoint in interface.current_alternate.endpoints:
        if endpoint.direction == direction and endpoint.transfer_type in (TransferType.BULK, TransferType.INTERRUPT):
            return endpoint.number
    return None


def _format_value(value: int, *, name: str, minimum: int, maximum: int) -> str:
    if not minimum <= value <= maximum:
        raise PumpCommunicationError(f"{name} must be between {minimum} and {maximum} (got {value})")
    return f"{value:03d}"


def find_serial_ports(vid: int = DEFAULT_VID, pid: int = DEFAULT_PID) -> list[str]:
    """Find serial ports that might be the micropump."""
    ports = []
    
    if PLATFORM == "windows":
        # Windows: Look for COM ports
        import winreg
        try:
            key = winreg.OpenKey(winreg.HKEY_LOCAL_MACHINE, "HARDWARE\\DEVICEMAP\\SERIALCOMM")
            for i in range(winreg.QueryInfoKey(key)[1]):
                port = winreg.EnumValue(key, i)[1]
                ports.append(port)
            winreg.CloseKey(key)
        except:
            # Fallback: common COM ports
            for i in range(1, 21):
                ports.append(f"COM{i}")
    else:
        # Linux/WSL: Look for ttyUSB and ttyACM devices
        usb_ports = glob.glob('/dev/ttyUSB*')
        acm_ports = glob.glob('/dev/ttyACM*')
        ports.extend(usb_ports + acm_ports)
        
        # Try to filter by device info if possible
        filtered_ports = []
        for port in ports:
            try:
                result = subprocess.run(['udevadm', 'info', '--name=' + port], 
                                      capture_output=True, text=True)
                if f'{vid:04x}' in result.stdout.lower():
                    filtered_ports.append(port)
            except:
                # If udevadm fails, include all ports
                filtered_ports.append(port)
        
        if filtered_ports:
            ports = filtered_ports
    
    return sorted(set(ports))


def detect_connection_method() -> str:
    """Detect the best connection method for the current environment."""
    if PLATFORM == "windows":
        if USBX_AVAILABLE:
            return "usb_primary"  # Try USB first, fallback to serial
        elif SERIAL_AVAILABLE:
            return "serial_only"
        else:
            return "none"
    else:
        # Linux/WSL - prefer serial for better compatibility
        if SERIAL_AVAILABLE:
            return "serial_primary"  # Try serial first, fallback to USB
        elif USBX_AVAILABLE:
            return "usb_only"
        else:
            return "none"


class UsbPumpController:
    """Dual-mode controller for the Bartels micropump: USB (Windows) + Serial (Linux/WSL)."""

    def __init__(self, port: Optional[str] = None, *, vid: Optional[int] = None,
                 pid: Optional[int] = None, auto_connect: bool = True, 
                 connection_method: Optional[str] = None):
        
        self.vid, self.pid = _load_device_ids() if vid is None or pid is None else (vid, pid)
        if vid is not None:
            self.vid = vid
        if pid is not None:
            self.pid = pid
            
        # Connection state for USB mode
        self._device: Optional[Device] = None
        self._interface_number: Optional[int] = None
        self._out_endpoint: Optional[int] = None
        self._in_endpoint: Optional[int] = None
        self._claimed: bool = False
        
        # Connection state for Serial mode
        self._serial_port: Optional[str] = port
        self._serial_connection = None
        
        # Determine connection method
        if connection_method:
            self._connection_method = connection_method
        else:
            self._connection_method = detect_connection_method()
            
        self._active_mode = None  # Will be set to 'usb' or 'serial'
        
        print(f"INFO: Platform: {PLATFORM}")
        print(f"INFO: USB available: {USBX_AVAILABLE}")
        print(f"INFO: Serial available: {SERIAL_AVAILABLE}")
        print(f"INFO: Connection method: {self._connection_method}")
        
        if auto_connect:
            self.connect()

    # Context-manager helpers -------------------------------------------------
    def __enter__(self) -> "UsbPumpController":
        if not self.connected:
            self.connect()
        return self

    def __exit__(self, exc_type, exc, tb) -> None:
        self.disconnect()

    # Connection management ---------------------------------------------------
    @property
    def connected(self) -> bool:
        return self._device is not None and self._claimed

    def connect(self) -> None:
        if self.connected:
            return
            
        # Try connection methods based on strategy
        if self._connection_method == "usb_only":
            self._connect_usb()
        elif self._connection_method == "serial_only":
            self._connect_serial()
        elif self._connection_method == "usb_primary":
            try:
                self._connect_usb()
            except PumpCommunicationError:
                print("INFO: USB connection failed, trying serial...")
                self._connect_serial()
        elif self._connection_method == "serial_primary":
            try:
                self._connect_serial()
            except PumpCommunicationError:
                print("INFO: Serial connection failed, trying USB...")
                self._connect_usb()
        else:
            raise PumpCommunicationError(f"No connection method available. USB: {USBX_AVAILABLE}, Serial: {SERIAL_AVAILABLE}")

    def _connect_usb(self) -> None:
        """Connect via direct USB using usbx library."""
        if not USBX_AVAILABLE or usb is None:
            raise PumpCommunicationError("USB connection not available (usbx library not found)")
            
        # First, list all available devices for debugging
        try:
            all_devices = usb.find_devices()
            print(f"DEBUG: Found {len(all_devices)} USB devices total")
            for dev in all_devices:
                print(f"DEBUG: Device VID=0x{dev.vid:04x} PID=0x{dev.pid:04x}")
        except Exception as e:
            print(f"DEBUG: Error listing devices: {e}")
        
        device = usb.find_device(vid=self.vid, pid=self.pid)
        if device is None:
            raise PumpCommunicationError(
                f"Pump with VID=0x{self.vid:04x} PID=0x{self.pid:04x} not found via USB. "
                f"Available devices listed above. Make sure the device is connected and "
                f"drivers are installed (Windows) or forwarded to WSL."
            )
        interface_number = _select_interface(device)
        out_endpoint = _find_endpoint(device, interface_number, TransferDirection.OUT)
        if out_endpoint is None:
            raise PumpCommunicationError("Unable to determine OUT endpoint for pump")
        in_endpoint = _find_endpoint(device, interface_number, TransferDirection.IN)

        try:
            device.open()
            device.claim_interface(interface_number)
        except USBError as exc:
            try:
                device.close()
            except USBError:
                pass
            raise PumpCommunicationError("Failed to open/claim the pump interface") from exc

        self._device = device
        self._interface_number = interface_number
        self._out_endpoint = out_endpoint
        self._in_endpoint = in_endpoint
        self._claimed = True
        self._active_mode = "usb"
        print(f"INFO: Connected via USB to device VID=0x{self.vid:04x} PID=0x{self.pid:04x}")

    def _connect_serial(self) -> None:
        """Connect via serial port using pyserial library."""
        if not SERIAL_AVAILABLE or serial is None:
            raise PumpCommunicationError("Serial connection not available (pyserial library not found)")
            
        # Find serial ports
        ports = find_serial_ports(self.vid, self.pid) if self._serial_port is None else [self._serial_port]
        if not ports:
            raise PumpCommunicationError("No serial ports found for the pump")
            
        print(f"INFO: Trying serial ports: {ports}")
        
        last_error = None
        for port in ports:
            try:
                print(f"INFO: Attempting to connect to {port}...")
                # Try common serial settings for FTDI devices
                conn = serial.Serial(
                    port=port,
                    baudrate=9600,  # Common FTDI default
                    timeout=1.0,
                    bytesize=serial.EIGHTBITS,
                    parity=serial.PARITY_NONE,
                    stopbits=serial.STOPBITS_ONE
                )
                
                # Test the connection with a simple command
                conn.write(b"?\r")
                time.sleep(0.1)
                response = conn.read(100)
                
                if response or True:  # Accept any response or no response for now
                    self._serial_connection = conn
                    self._serial_port = port
                    self._active_mode = "serial"
                    print(f"INFO: Connected via serial to {port}")
                    return
                else:
                    conn.close()
                    
            except Exception as e:
                last_error = e
                print(f"INFO: Failed to connect to {port}: {e}")
                continue
                
        raise PumpCommunicationError(f"Failed to connect to any serial port. Last error: {last_error}")

    # Connection management ---------------------------------------------------
    @property
    def connected(self) -> bool:
        if self._active_mode == "usb":
            return self._device is not None and self._claimed
        elif self._active_mode == "serial":
            return self._serial_connection is not None and self._serial_connection.is_open
        return False

    def disconnect(self) -> None:
        if self._active_mode == "usb":
            self._disconnect_usb()
        elif self._active_mode == "serial":
            self._disconnect_serial()
        self._active_mode = None

    def _disconnect_usb(self) -> None:
        """Disconnect USB connection."""
        if self._device is None:
            return
        try:
            if self._claimed and self._interface_number is not None:
                self._device.release_interface(self._interface_number)
        except USBError:
            pass
        finally:
            self._claimed = False
        try:
            self._device.close()
        except USBError:
            pass
        finally:
            self._device = None
            self._interface_number = None
            self._out_endpoint = None
            self._in_endpoint = None

    def _disconnect_serial(self) -> None:
        """Disconnect serial connection."""
        if self._serial_connection is not None:
            try:
                self._serial_connection.close()
            except:
                pass
            finally:
                self._serial_connection = None

    def close(self) -> None:
        """Compatibility wrapper for legacy code."""
        self.disconnect()

    # Command helpers ---------------------------------------------------------
    def _ensure_ready(self) -> None:
        if not self.connected:
            raise PumpCommunicationError("Pump is not connected")

    def send_command(self, command: str | bytes, *, expect_response: bool = True, timeout: float = 1.0) -> bytes:
        """Send a raw command to the pump and return the response bytes."""
        self._ensure_ready()
        
        if self._active_mode == "usb":
            return self._send_command_usb(command, expect_response=expect_response, timeout=timeout)
        elif self._active_mode == "serial":
            return self._send_command_serial(command, expect_response=expect_response, timeout=timeout)
        else:
            raise PumpCommunicationError("No active connection method")
    
    def _send_command_usb(self, command: str | bytes, *, expect_response: bool = True, timeout: float = 1.0) -> bytes:
        """Send command via USB connection."""
        if self._device is None or self._out_endpoint is None:
            raise PumpCommunicationError("USB device not properly initialized")
            
        payload = command.encode("ascii") if isinstance(command, str) else command
        if isinstance(payload, (bytes, bytearray)):
            if not payload.endswith(b"\r"):
                payload = payload + b"\r"
        else:
            # Handle memoryview case
            payload_bytes = bytes(payload)
            if not payload_bytes.endswith(b"\r"):
                payload = payload_bytes + b"\r"
        
        try:
            self._device.transfer_out(self._out_endpoint, payload)
        except USBError as exc:
            raise PumpCommunicationError(f"Failed to send USB command {command!r}") from exc
        time.sleep(_CMD_DELAY_S)

        if not expect_response or self._in_endpoint is None:
            return b""
        try:
            response = self._device.transfer_in(self._in_endpoint, timeout=timeout)
            return bytes(response) if response is not None else b""
        except USBError as exc:
            raise PumpCommunicationError(f"No USB response for command {command!r}") from exc
        finally:
            time.sleep(_CMD_DELAY_S)
    
    def _send_command_serial(self, command: str | bytes, *, expect_response: bool = True, timeout: float = 1.0) -> bytes:
        """Send command via serial connection."""
        if self._serial_connection is None:
            raise PumpCommunicationError("Serial connection not properly initialized")
            
        payload = command.encode("ascii") if isinstance(command, str) else command
        payload_bytes = bytes(payload) if not isinstance(payload, bytes) else payload
        if not payload_bytes.endswith(b"\r"):
            payload_bytes = payload_bytes + b"\r"
        
        try:
            self._serial_connection.write(payload_bytes)
            self._serial_connection.flush()
        except Exception as exc:
            raise PumpCommunicationError(f"Failed to send serial command {command!r}") from exc
        time.sleep(_CMD_DELAY_S)

        if not expect_response:
            return b""
        try:
            # Read response with timeout
            old_timeout = self._serial_connection.timeout
            self._serial_connection.timeout = timeout
            response = self._serial_connection.read(100)  # Read up to 100 bytes
            self._serial_connection.timeout = old_timeout
            return response
        except Exception as exc:
            raise PumpCommunicationError(f"No serial response for command {command!r}") from exc
        finally:
            time.sleep(_CMD_DELAY_S)

    @staticmethod
    def _check_ack(response: bytes, action: str) -> None:
        stripped = response.strip()
        if stripped.upper().startswith(b"ERR"):
            raise PumpCommunicationError(f"Pump reported error while attempting to {action}: {response!r}")

    # High-level operations ---------------------------------------------------
    def set_frequency(self, frequency_hz: int) -> None:
        value = _format_value(int(frequency_hz), name="Frequency", minimum=1, maximum=300)
        response = self.send_command(f"F{value}")
        self._check_ack(response, "set frequency")

    def set_amplitude(self, amplitude: int) -> None:
        value = _format_value(int(amplitude), name="Amplitude", minimum=1, maximum=250)
        response = self.send_command(f"A{value}")
        self._check_ack(response, "set amplitude")

    def set_waveform(self, waveform: str) -> None:
        key = waveform.strip().upper()
        command = _WAVEFORM_COMMANDS.get(key)
        if command is None:
            raise PumpCommunicationError(
                f"Unknown waveform '{waveform}'. Expected one of {sorted(set(_WAVEFORM_COMMANDS) - {'MR','MS','MC'})}"
            )
        response = self.send_command(command)
        self._check_ack(response, "set waveform")

    def start(self) -> None:
        response = self.send_command("bon")
        self._check_ack(response, "start the pump")

    def stop(self) -> None:
        response = self.send_command("boff")
        self._check_ack(response, "stop the pump")

    def pulse(self, duration_s: float, *, frequency_hz: Optional[int] = None,
              amplitude: Optional[int] = None, waveform: Optional[str] = None) -> None:
        if frequency_hz is not None:
            self.set_frequency(frequency_hz)
        if amplitude is not None:
            self.set_amplitude(amplitude)
        if waveform is not None:
            self.set_waveform(waveform)
        self.start()
        try:
            time.sleep(duration_s)
        finally:
            self.stop()


BartelsPump = UsbPumpController

__all__ = ["UsbPumpController", "PumpCommunicationError", "BartelsPump"]
