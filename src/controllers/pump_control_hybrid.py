"""Pump control supporting both USB (usbx) and serial (pyserial) connections."""

from __future__ import annotations

import time
import warnings
import glob
from pathlib import Path
from typing import Optional, Union
import os

# Import availability tracking
USBX_AVAILABLE = False
SERIAL_AVAILABLE = False

try:
    from usbx import Device, TransferDirection, TransferType, USBError, usb
    USBX_AVAILABLE = True
except ImportError:
    print("Info: usbx not available, will use serial fallback if device found")
    # Create dummy classes for type hints
    class Device: pass
    class TransferDirection: 
        OUT = IN = None
    class TransferType: 
        BULK = INTERRUPT = None
    class USBError(Exception): pass
    usb = None

try:
    import serial
    SERIAL_AVAILABLE = True
except ImportError:
    print("Warning: pyserial not available")
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


def find_serial_ports(vid: int = DEFAULT_VID, pid: int = DEFAULT_PID) -> list[str]:
    """Find serial ports that might be the micropump."""
    ports = []
    
    # Look for ttyUSB devices (Linux)
    usb_ports = glob.glob('/dev/ttyUSB*')
    for port in usb_ports:
        try:
            # Try to get device info
            import subprocess
            result = subprocess.run(['udevadm', 'info', '--name=' + port], 
                                  capture_output=True, text=True)
            if f'{vid:04x}' in result.stdout.lower() and f'{pid:04x}' in result.stdout.lower():
                ports.append(port)
            elif f'{vid:04x}' in result.stdout.lower():  # FTDI device, might be the pump
                ports.append(port)
        except:
            # If we can't get device info, include all ttyUSB ports
            ports.append(port)
    
    # Look for ttyACM devices (some USB-serial converters)
    acm_ports = glob.glob('/dev/ttyACM*')
    ports.extend(acm_ports)
    
    return sorted(set(ports))


def _select_interface(device: Device) -> int:
    """Pick the first interface exposing a bulk/interrupt OUT endpoint."""
    if not USBX_AVAILABLE:
        raise PumpCommunicationError("USB functionality not available")
    
    for intf in device.configuration.interfaces:
        alt = intf.current_alternate
        for endpoint in alt.endpoints:
            if endpoint.transfer_type in (TransferType.BULK, TransferType.INTERRUPT) and \
                    endpoint.direction == TransferDirection.OUT:
                return intf.number
    raise PumpCommunicationError("Pump has no bulk/interrupt OUT endpoint")


def _find_endpoint(device: Device, interface_number: int, direction) -> Optional[int]:
    """Find endpoint for given direction."""
    if not USBX_AVAILABLE:
        return None
    
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


class PumpController:
    """High-level controller for the Bartels micropump with USB and serial support."""

    def __init__(self, port: Optional[str] = None, *, vid: Optional[int] = None,
                 pid: Optional[int] = None, auto_connect: bool = True, 
                 prefer_serial: bool = False):
        self.vid, self.pid = _load_device_ids() if vid is None or pid is None else (vid, pid)
        if vid is not None:
            self.vid = vid
        if pid is not None:
            self.pid = pid
        
        self.port = port
        self.prefer_serial = prefer_serial
        
        # USB-specific attributes
        self._device: Optional[Device] = None
        self._interface_number: Optional[int] = None
        self._out_endpoint: Optional[int] = None
        self._in_endpoint: Optional[int] = None
        self._claimed: bool = False
        
        # Serial-specific attributes
        self._serial_connection: Optional[serial.Serial] = None
        self._using_serial: bool = False
        
        if auto_connect:
            self.connect()

    # Context-manager helpers -------------------------------------------------
    def __enter__(self) -> "PumpController":
        if not self.connected:
            self.connect()
        return self

    def __exit__(self, exc_type, exc, tb) -> None:
        self.disconnect()

    # Connection management ---------------------------------------------------
    @property
    def connected(self) -> bool:
        if self._using_serial:
            return self._serial_connection is not None and self._serial_connection.is_open
        else:
            return self._device is not None and self._claimed

    def _try_usb_connection(self) -> bool:
        """Try to connect via USB using usbx."""
        if not USBX_AVAILABLE:
            print("DEBUG: usbx not available, skipping USB connection")
            return False
        
        try:
            # First, list all available devices for debugging
            all_devices = usb.find_devices()
            print(f"DEBUG: Found {len(all_devices)} USB devices total")
            for dev in all_devices:
                print(f"DEBUG: Device VID=0x{dev.vid:04x} PID=0x{dev.pid:04x}")
            
            device = usb.find_device(vid=self.vid, pid=self.pid)
            if device is None:
                print(f"DEBUG: No USB device found with VID=0x{self.vid:04x} PID=0x{self.pid:04x}")
                return False
            
            interface_number = _select_interface(device)
            out_endpoint = _find_endpoint(device, interface_number, TransferDirection.OUT)
            if out_endpoint is None:
                print("DEBUG: Unable to determine OUT endpoint for pump")
                return False
            in_endpoint = _find_endpoint(device, interface_number, TransferDirection.IN)

            device.open()
            device.claim_interface(interface_number)

            self._device = device
            self._interface_number = interface_number
            self._out_endpoint = out_endpoint
            self._in_endpoint = in_endpoint
            self._claimed = True
            self._using_serial = False
            
            print("DEBUG: Successfully connected via USB")
            return True
            
        except Exception as e:
            print(f"DEBUG: USB connection failed: {e}")
            try:
                if device:
                    device.close()
            except:
                pass
            return False

    def _try_serial_connection(self) -> bool:
        """Try to connect via serial port."""
        if not SERIAL_AVAILABLE:
            print("DEBUG: pyserial not available, skipping serial connection")
            return False
        
        ports_to_try = []
        
        if self.port:
            # Use specific port if provided
            ports_to_try = [self.port]
        else:
            # Auto-detect ports
            ports_to_try = find_serial_ports(self.vid, self.pid)
            
        if not ports_to_try:
            print("DEBUG: No serial ports found")
            return False
        
        print(f"DEBUG: Trying serial ports: {ports_to_try}")
        
        for port in ports_to_try:
            try:
                print(f"DEBUG: Attempting to connect to {port}")
                ser = serial.Serial(
                    port=port,
                    baudrate=9600,  # Common baudrate for FTDI devices
                    timeout=1.0,
                    bytesize=serial.EIGHTBITS,
                    parity=serial.PARITY_NONE,
                    stopbits=serial.STOPBITS_ONE
                )
                
                # Test communication
                ser.write(b"F050\r")
                time.sleep(0.2)
                response = ser.read(100)
                
                self._serial_connection = ser
                self._using_serial = True
                print(f"DEBUG: Successfully connected via serial port {port}")
                return True
                
            except Exception as e:
                print(f"DEBUG: Serial connection to {port} failed: {e}")
                try:
                    ser.close()
                except:
                    pass
                continue
                
        return False

    def connect(self) -> None:
        """Connect to the pump using USB or serial."""
        if self.connected:
            return
        
        success = False
        
        if self.prefer_serial:
            # Try serial first
            success = self._try_serial_connection()
            if not success:
                success = self._try_usb_connection()
        else:
            # Try USB first  
            success = self._try_usb_connection()
            if not success:
                success = self._try_serial_connection()
        
        if not success:
            available_libs = []
            if USBX_AVAILABLE:
                available_libs.append("usbx")
            if SERIAL_AVAILABLE:
                available_libs.append("pyserial")
            
            raise PumpCommunicationError(
                f"Could not connect to pump with VID=0x{self.vid:04x} PID=0x{self.pid:04x}. "
                f"Available libraries: {available_libs}. "
                f"Make sure device is connected and drivers are installed."
            )

    def disconnect(self) -> None:
        """Disconnect from the pump."""
        if self._using_serial and self._serial_connection:
            try:
                self._serial_connection.close()
            except:
                pass
            self._serial_connection = None
        
        if not self._using_serial and self._device is not None:
            try:
                if self._claimed and self._interface_number is not None:
                    self._device.release_interface(self._interface_number)
            except:
                pass
            finally:
                self._claimed = False
            try:
                self._device.close()
            except:
                pass
            finally:
                self._device = None
                self._interface_number = None
                self._out_endpoint = None
                self._in_endpoint = None
        
        self._using_serial = False

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
        
        payload = command.encode("ascii") if isinstance(command, str) else command
        if not payload.endswith(b"\r"):
            payload = payload + b"\r"
        
        if self._using_serial:
            return self._send_command_serial(payload, expect_response, timeout)
        else:
            return self._send_command_usb(payload, expect_response, timeout)
    
    def _send_command_serial(self, payload: bytes, expect_response: bool, timeout: float) -> bytes:
        """Send command via serial port."""
        if not self._serial_connection:
            raise PumpCommunicationError("Serial connection not established")
        
        try:
            self._serial_connection.write(payload)
            time.sleep(_CMD_DELAY_S)
            
            if not expect_response:
                return b""
            
            # Read response
            self._serial_connection.timeout = timeout
            response = self._serial_connection.read(100)  # Read up to 100 bytes
            time.sleep(_CMD_DELAY_S)
            return response
            
        except Exception as exc:
            raise PumpCommunicationError(f"Failed to send command via serial: {exc}") from exc
    
    def _send_command_usb(self, payload: bytes, expect_response: bool, timeout: float) -> bytes:
        """Send command via USB."""
        if not self._device or not self._out_endpoint:
            raise PumpCommunicationError("USB connection not established")
        
        try:
            self._device.transfer_out(self._out_endpoint, payload)
            time.sleep(_CMD_DELAY_S)

            if not expect_response or self._in_endpoint is None:
                return b""
            
            response = self._device.transfer_in(self._in_endpoint, timeout=timeout)
            return bytes(response) if response is not None else b""
            
        except Exception as exc:
            raise PumpCommunicationError(f"Failed to send command via USB: {exc}") from exc
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


# Legacy compatibility
UsbPumpController = PumpController
BartelsPump = PumpController

__all__ = ["PumpController", "UsbPumpController", "PumpCommunicationError", "BartelsPump"]
