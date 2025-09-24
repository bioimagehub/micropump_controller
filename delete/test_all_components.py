#!/usr/bin/env python3
"""
Comprehensive hardware test for all four components:
- Pump (Bartels micropump via serial)
- Valve (Arduino-controlled solenoid via serial) 
- Microscope (placeholder - reports status only)
- 3D Stage (GRBL-based CNC pipetting robot)

This script discovers available hardware, reports what's found, and runs
basic functional tests for each detected component.
"""

import sys
import time
import logging
from pathlib import Path

# Add src to path for imports
sys.path.insert(0, str(Path(__file__).parent / "src"))

try:
    import serial
    import serial.tools.list_ports
    SERIAL_AVAILABLE = True
except ImportError:
    SERIAL_AVAILABLE = False
    print("WARNING: pyserial not available - install with: pip install pyserial")

from pump import PumpController
from pump_nodriver import PumpController as PumpControllerNoDriver
from pump_libusb import PumpController as PumpControllerLibUSB
from valve import ValveController  
from microscope import MicroscopeController
from stage3d import Stage3DController
from delete.resolve_ports import find_pump_port_by_vid_pid, list_all_ports

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s [%(levelname)s] %(message)s')


class HardwareTestSuite:
    """Test suite for all four hardware components."""
    
    def __init__(self):
        self.results = {
            'pump_driver': {'found': False, 'controller': None, 'test_passed': False},
            'pump_nodriver': {'found': False, 'controller': None, 'test_passed': False},
            'pump_libusb': {'found': False, 'controller': None, 'test_passed': False},
            'valve': {'found': False, 'controller': None, 'test_passed': False},
            'microscope': {'found': False, 'controller': None, 'test_passed': False},
            'stage3d': {'found': False, 'controller': None, 'test_passed': False}
        }
        
    def discover_components(self):
        """Discover all available hardware components."""
        print("🔍 HARDWARE DISCOVERY")
        print("=" * 50)
        
        if not SERIAL_AVAILABLE:
            print("❌ Serial communication not available - cannot test hardware")
            return
            
        self._discover_pump_driver()
        self._discover_pump_nodriver()
        self._discover_pump_libusb()
        self._discover_valve() 
        self._discover_microscope()
        self._discover_stage3d()
        
    def _discover_pump_driver(self):
        """Discover and initialize pump using original driver-based controller."""
        print("\n💧 PUMP (Bartels Micropump - WITH DRIVERS)")
        print("-" * 40)
        
        try:
            # Look for Bartels device (VID:0403, PID:B4C0)
            pump_port = find_pump_port_by_vid_pid(0x0403, 0xB4C0)
            print(f"✓ Found Bartels device on: {pump_port}")
            
            pump = PumpController(pump_port)
            if pump.ser is not None:
                self.results['pump_driver']['found'] = True
                self.results['pump_driver']['controller'] = pump
                print(f"✅ Pump (driver-based) initialized successfully")
                # Close immediately to allow driver-free test
                pump.close()
                self.results['pump_driver']['controller'] = None
            else:
                print(f"❌ Pump found but failed to initialize (driver-based)")
                
        except Exception as e:
            print(f"❌ Pump (driver-based) not found: {e}")
            
    def _discover_pump_nodriver(self):
        """Discover and initialize pump using driver-free controller."""
        print("\n💧 PUMP (Bartels Micropump - DRIVER-FREE)")
        print("-" * 40)
        
        try:
            # Look for Bartels device (VID:0403, PID:B4C0)
            pump_port = find_pump_port_by_vid_pid(0x0403, 0xB4C0)
            print(f"✓ Found Bartels device on: {pump_port}")
            
            pump = PumpControllerNoDriver(pump_port)
            if pump.handle is not None and pump.handle != -1:
                self.results['pump_nodriver']['found'] = True
                self.results['pump_nodriver']['controller'] = pump
                print(f"✅ Pump (driver-free) initialized successfully")
                # Close immediately after verification
                pump.close()
                self.results['pump_nodriver']['controller'] = None
            else:
                print(f"❌ Pump found but failed to initialize (driver-free)")
                
        except Exception as e:
            print(f"❌ Pump (driver-free) not found: {e}")
            
    def _discover_pump_libusb(self):
        """Discover and initialize pump using libusb-win32 controller."""
        print("\n💧 PUMP (Bartels Micropump - LIBUSB)")
        print("-" * 40)
        
        try:
            # Try libusb approach (works with libusb-win32 driver from Zadig)
            pump = PumpControllerLibUSB()
            if pump.device is not None:
                self.results['pump_libusb']['found'] = True
                self.results['pump_libusb']['controller'] = pump
                print(f"✅ Pump (libusb) initialized successfully")
                # Close immediately after verification
                pump.close()
                self.results['pump_libusb']['controller'] = None
            else:
                print(f"❌ Pump found but failed to initialize (libusb)")
                
        except Exception as e:
            print(f"❌ Pump (libusb) not found: {e}")
    
    def _discover_pump(self):
        """Legacy method - replaced by _discover_pump_driver and _discover_pump_nodriver."""
        pass
            
    def _discover_valve(self):
        """Discover and initialize valve."""
        print("\n🔧 VALVE (Arduino Solenoid)")
        print("-" * 30)
        
        try:
            # Look for Arduino-compatible devices but skip GRBL devices
            ports_info = list_all_ports()
            valve_port = None
            
            for device, desc, vid, pid in ports_info:
                # Look for Arduino devices (not CH340 which might be GRBL)
                if vid == "2341":  # Only official Arduino devices
                    # Test if it responds to valve commands
                    try:
                        test_valve = ValveController(device)
                        if test_valve.ser is not None:
                            valve_port = device
                            test_valve.close()
                            break
                    except:
                        continue
                        
            if valve_port:
                valve = ValveController(valve_port)
                self.results['valve']['found'] = True
                self.results['valve']['controller'] = valve
                print(f"✅ Valve initialized on {valve_port}")
            else:
                print("❌ No suitable Arduino device found for valve")
                
        except Exception as e:
            print(f"❌ Valve discovery failed: {e}")
            
    def _discover_microscope(self):
        """Discover and initialize microscope."""
        print("\n🔬 MICROSCOPE")
        print("-" * 30)
        
        try:
            microscope = MicroscopeController()
            self.results['microscope']['found'] = True
            self.results['microscope']['controller'] = microscope
            print("✅ Microscope controller initialized (placeholder)")
        except Exception as e:
            print(f"❌ Microscope initialization failed: {e}")
            
    def _discover_stage3d(self):
        """Discover and initialize 3D stage."""
        print("\n🎯 3D STAGE (GRBL CNC Robot)")
        print("-" * 30)
        
        try:
            # Look for CH340 device (common for GRBL controllers)
            stage_port = find_pump_port_by_vid_pid(0x1A86, 0x7523)
            print(f"✓ Found GRBL device on: {stage_port}")
            
            # Create stage without auto-connect to avoid initialization movement during discovery
            stage = Stage3DController(port=stage_port, config_path="robot_config.yaml", auto_connect=False)
            
            if stage.connect():
                self.results['stage3d']['found'] = True
                self.results['stage3d']['controller'] = stage
                print(f"✅ 3D Stage connected successfully")
                print(f"   Status: {stage.get_status()}")
                print(f"   Config loaded: {stage.has_well_plate_config()}")
                stage.disconnect()  # Disconnect after verification
            else:
                print("❌ 3D Stage found but failed to connect")
                
        except Exception as e:
            print(f"❌ 3D Stage not found: {e}")

    def run_functional_tests(self):
        """Run functional tests for all discovered components."""
        print("\n🧪 FUNCTIONAL TESTS")
        print("=" * 50)
        
        self._test_pump_driver()
        self._test_pump_nodriver()
        self._test_pump_libusb()
        self._test_valve()
        self._test_microscope() 
        self._test_stage3d()
        
    def _test_pump_driver(self):
        """Test pump functionality using driver-based controller."""
        print("\n💧 Testing Pump (WITH DRIVERS)...")
        
        if not self.results['pump_driver']['found']:
            print("❌ Pump (driver-based) not available for testing")
            return
            
        try:
            # Reinitialize for testing
            pump_port = find_pump_port_by_vid_pid(0x0403, 0xB4C0)
            pump = PumpController(pump_port)
            
            if pump.ser is None:
                print("❌ Failed to reinitialize pump for testing")
                return
            
            print("  Setting frequency to 100 Hz...")
            pump.set_frequency(100)
            time.sleep(0.5)
            
            print("  Setting voltage to 50V...")
            pump.set_voltage(50)
            time.sleep(0.5)
            
            print("  Turning pump ON for 2 seconds...")
            pump.start()
            time.sleep(2)
            
            print("  Turning pump OFF...")
            pump.stop()
            
            pump.close()  # Clean up
            
            self.results['pump_driver']['test_passed'] = True
            print("✅ Pump (driver-based) test completed successfully")
            
        except Exception as e:
            print(f"❌ Pump (driver-based) test failed: {e}")
            
    def _test_pump_nodriver(self):
        """Test pump functionality using driver-free controller."""
        print("\n💧 Testing Pump (DRIVER-FREE)...")
        
        if not self.results['pump_nodriver']['found']:
            print("❌ Pump (driver-free) not available for testing")
            return
            
        try:
            # Reinitialize for testing
            pump_port = find_pump_port_by_vid_pid(0x0403, 0xB4C0)
            pump = PumpControllerNoDriver(pump_port)
            
            if pump.handle is None or pump.handle == -1:
                print("❌ Failed to reinitialize driver-free pump for testing")
                return
            
            print("  Setting frequency to 100 Hz...")
            pump.set_frequency(100)
            time.sleep(0.5)
            
            print("  Setting voltage to 50V...")
            pump.set_voltage(50)
            time.sleep(0.5)
            
            print("  Turning pump ON for 2 seconds...")
            pump.start()
            time.sleep(2)
            
            print("  Turning pump OFF...")
            pump.stop()
            
            pump.close()  # Clean up
            
            self.results['pump_nodriver']['test_passed'] = True
            print("✅ Pump (driver-free) test completed successfully")
            
        except Exception as e:
            print(f"❌ Pump (driver-free) test failed: {e}")
            
    def _test_pump_libusb(self):
        """Test pump functionality using libusb controller."""
        print("\n💧 Testing Pump (LIBUSB)...")
        
        if not self.results['pump_libusb']['found']:
            print("❌ Pump (libusb) not available for testing")
            return
            
        try:
            # Reinitialize for testing
            pump = PumpControllerLibUSB()
            
            if pump.device is None:
                print("❌ Failed to reinitialize libusb pump for testing")
                return
            
            print("  Setting frequency to 100 Hz...")
            pump.set_frequency(100)
            time.sleep(0.5)
            
            print("  Setting voltage to 50V...")
            pump.set_voltage(50)
            time.sleep(0.5)
            
            print("  Turning pump ON for 2 seconds...")
            pump.start()
            time.sleep(2)
            
            print("  Turning pump OFF...")
            pump.stop()
            
            pump.close()  # Clean up
            
            self.results['pump_libusb']['test_passed'] = True
            print("✅ Pump (libusb) test completed successfully")
            
        except Exception as e:
            print(f"❌ Pump (libusb) test failed: {e}")
    
    def _test_pump(self):
        """Legacy method - replaced by _test_pump_driver and _test_pump_nodriver."""
        pass
            
    def _test_valve(self):
        """Test valve functionality."""
        print("\n🔧 Testing Valve...")
        
        if not self.results['valve']['found']:
            print("❌ Valve not available for testing")
            return
            
        valve = self.results['valve']['controller']
        
        try:
            print("  Opening valve...")
            valve.on()
            time.sleep(1)
            
            print("  Closing valve...")
            valve.off()
            time.sleep(1)
            
            print("  Testing pulse (500ms)...")
            valve.pulse(500)
            time.sleep(1)
            
            self.results['valve']['test_passed'] = True
            print("✅ Valve test completed successfully")
            
        except Exception as e:
            print(f"❌ Valve test failed: {e}")
            
    def _test_microscope(self):
        """Test microscope functionality."""
        print("\n🔬 Testing Microscope...")
        
        if not self.results['microscope']['found']:
            print("❌ Microscope not available for testing")
            return
            
        microscope = self.results['microscope']['controller']
        
        try:
            # Test placeholder functionality
            print("  Testing microscope status...")
            status = microscope.get_status()
            print(f"  Microscope status: {status}")
            
            self.results['microscope']['test_passed'] = True
            print("✅ Microscope test completed successfully")
            
        except Exception as e:
            print(f"❌ Microscope test failed: {e}")
            
    def _test_stage3d(self):
        """Test 3D stage functionality.""" 
        print("\n🎯 Testing 3D Stage...")
        
        if not self.results['stage3d']['found']:
            print("❌ 3D Stage not available for testing")
            return
            
        stage = self.results['stage3d']['controller']
        
        try:
            print("  Connecting to stage...")
            if not stage.connect():
                print("❌ Failed to connect to stage")
                return
                
            print("  Performing initialization movement test...")
            stage._perform_initialization_test()
            
            print("  Testing coordinate movement...")
            stage.move_to_coordinates(x=1, y=1)
            time.sleep(0.5)
            
            print("  Returning to origin...")
            stage.move_to_coordinates(x=0, y=0)
            time.sleep(0.5)
            
            if stage.has_well_plate_config():
                print("  Testing well coordinate calculation...")
                coords = stage.calculate_well_coordinates("A1")
                print(f"    Well A1: {coords}")
                
            print("  Disconnecting from stage...")
            stage.disconnect()
            
            self.results['stage3d']['test_passed'] = True
            print("✅ 3D Stage test completed successfully")
            
        except Exception as e:
            print(f"❌ 3D Stage test failed: {e}")
            
    def cleanup(self):
        """Clean up all connections."""
        print("\n🧹 CLEANUP")
        print("=" * 50)
        
        for component_name, result in self.results.items():
            if result['found'] and result['controller']:
                try:
                    if hasattr(result['controller'], 'close'):
                        result['controller'].close()
                    elif hasattr(result['controller'], 'disconnect'):
                        result['controller'].disconnect()
                    print(f"✅ {component_name.upper()} cleaned up")
                except Exception as e:
                    print(f"⚠️ {component_name.upper()} cleanup warning: {e}")
                    
    def print_summary(self):
        """Print test summary."""
        print("\n📊 TEST SUMMARY")
        print("=" * 50)
        
        total_found = sum(1 for r in self.results.values() if r['found'])
        total_passed = sum(1 for r in self.results.values() if r['test_passed'])
        
        print(f"Components discovered: {total_found}/6")
        print(f"Tests passed: {total_passed}/{total_found}")
        print()
        
        for component, result in self.results.items():
            status = "✅" if result['found'] else "❌"
            test_status = "✅" if result['test_passed'] else "❌" if result['found'] else "⏭️"
            print(f"{status} {component.upper():<15} - Discovery: {'Found' if result['found'] else 'Not Found':<9} | Test: {test_status}")


def main():
    """Main test execution."""
    print("🔬 MICROPUMP CONTROLLER - HARDWARE TEST SUITE")
    print("=" * 60)
    print("Testing components: Pump (driver, driver-free & libusb), Valve, Microscope, 3D Stage")
    print()
    
    # List available ports for reference
    if SERIAL_AVAILABLE:
        print("📡 Available Serial Ports:")
        try:
            ports_info = list_all_ports()
            for device, desc, vid, pid in ports_info:
                print(f"  {device}: {desc} (VID:{vid}, PID:{pid})")
        except Exception as e:
            print(f"  Error listing ports: {e}")
        print()
    
    suite = HardwareTestSuite()
    
    try:
        # Run the complete test suite
        suite.discover_components()
        suite.run_functional_tests()
        
    except KeyboardInterrupt:
        print("\n\n⚠️ Test interrupted by user")
        
    except Exception as e:
        print(f"\n\n❌ Unexpected error: {e}")
        import traceback
        traceback.print_exc()
        
    finally:
        # Always cleanup
        suite.cleanup()
        suite.print_summary()
        
    print("\n🎉 Hardware test suite completed!")


if __name__ == "__main__":
    main()