"""
Quick two-terminal test for audio communication.

Run this script in two separate terminals to test audio communication
between them on the same PC.

Terminal 1: python two_pc_test.py sender
Terminal 2: python two_pc_test.py receiver

This simulates communication between microfluidics PC and microscope PC.
"""

import sys
from audio_protocol import MicroscopeAudioController, Command
import time


def run_sender() -> None:
    """Simulate microfluidics PC sending commands"""
    print("=" * 60)
    print("SENDER MODE (Simulating Microfluidics PC)")
    print("=" * 60)
    print("\nThis terminal will send audio commands.")
    print("Make sure the RECEIVER terminal is running first!\n")
    
    input("Press Enter when receiver is ready...")
    
    controller = MicroscopeAudioController()
    
    if not controller.is_initialized:
        print(f"✗ Error: {controller.last_error}")
        return
    
    print("\n" + "=" * 60)
    print("Test 1: PING/PONG")
    print("=" * 60)
    
    print("\nSending PING command...")
    if controller.send_command(Command.PING):
        print("✓ PING sent successfully")
        print("\nListening for PONG response...")
        response = controller.wait_for_command(timeout=30, expected=Command.PONG)
        
        if response == Command.PONG:
            print("✓ PONG received! Audio communication working!")
        else:
            print("✗ No PONG received - check audio setup")
    
    print("\n" + "=" * 60)
    print("Test 2: CAPTURE/DONE (Simulating Microscope Trigger)")
    print("=" * 60)
    
    input("\nPress Enter to trigger microscope capture...")
    
    if controller.trigger_and_wait(timeout=60):
        print("\n✓ SUCCESS! Full microscope capture cycle completed.")
    else:
        print("\n✗ FAILED! Microscope did not respond.")
    
    print("\n" + "=" * 60)
    print("Sender test complete!")
    print("=" * 60)


def run_receiver() -> None:
    """Simulate microscope PC receiving commands"""
    print("=" * 60)
    print("RECEIVER MODE (Simulating Microscope PC)")
    print("=" * 60)
    print("\nThis terminal will listen for audio commands.")
    print("Start the SENDER terminal to begin testing.\n")
    
    controller = MicroscopeAudioController()
    
    if not controller.is_initialized:
        print(f"✗ Error: {controller.last_error}")
        return
    
    print("🎧 Listening for commands...")
    print("   (Waiting up to 60 seconds)\n")
    
    # Test 1: Wait for PING, respond with PONG
    print("Waiting for PING...")
    cmd = controller.wait_for_command(timeout=60, expected=Command.PING)
    
    if cmd == Command.PING:
        print("✓ PING received!")
        print("\nSending PONG response...")
        time.sleep(1)  # Brief delay
        controller.send_command(Command.PONG)
        print("✓ PONG sent!")
    else:
        print("✗ No PING received")
        return
    
    # Test 2: Wait for CAPTURE, respond with DONE
    print("\n" + "=" * 60)
    print("Waiting for CAPTURE command...")
    cmd = controller.wait_for_command(timeout=60, expected=Command.CAPTURE)
    
    if cmd == Command.CAPTURE:
        print("✓ CAPTURE received!")
        print("\n🔬 Simulating microscope image capture...")
        print("   (In production, this would trigger actual microscope)")
        time.sleep(3)  # Simulate capture time
        print("   Image saved!")
        
        print("\nSending DONE response...")
        time.sleep(1)
        controller.send_command(Command.DONE)
        print("✓ DONE sent!")
    else:
        print("✗ No CAPTURE received")
    
    print("\n" + "=" * 60)
    print("Receiver test complete!")
    print("=" * 60)


def main() -> None:
    """Main entry point"""
    if len(sys.argv) != 2 or sys.argv[1] not in ['sender', 'receiver']:
        print("Usage:")
        print("  Terminal 1: python two_pc_test.py receiver")
        print("  Terminal 2: python two_pc_test.py sender")
        print()
        print("Run receiver first, then sender.")
        sys.exit(1)
    
    mode = sys.argv[1]
    
    if mode == 'sender':
        run_sender()
    else:
        run_receiver()


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\n\nTest interrupted by user.")
        sys.exit(0)
