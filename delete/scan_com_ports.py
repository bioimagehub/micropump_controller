#!/usr/bin/env python3
"""
Check available COM ports and identify potential Bartels device.
"""

import serial.tools.list_ports

def scan_com_ports():
    """Scan and display all available COM ports."""
    print("=== COM Port Scanner ===")
    
    ports = serial.tools.list_ports.comports()
    
    if not ports:
        print("No COM ports found!")
        print("This means either:")
        print("1. No devices are connected")
        print("2. FTDI VCP drivers are not installed")
        print("3. Device is using generic USB drivers")
        return
    
    print(f"\nFound {len(ports)} COM port(s):")
    print("-" * 60)
    
    for i, port in enumerate(ports, 1):
        print(f"{i}. Port: {port.device}")
        print(f"   Description: {port.description}")
        print(f"   Hardware ID: {port.hwid}")
        
        # Check if this might be the Bartels device
        is_potential = False
        identifiers = ['ftdi', 'bartels', 'micropump', 'bami', '0403', 'b4c0']
        
        port_info = f"{port.description} {port.hwid}".lower()
        for identifier in identifiers:
            if identifier in port_info:
                is_potential = True
                break
        
        if is_potential:
            print(f"   >>> POTENTIAL BARTELS DEVICE <<<")
        print()
    
    return ports

if __name__ == "__main__":
    scan_com_ports()
