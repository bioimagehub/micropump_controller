"""
Simplified two-PC test - no automatic microphone detection.

On SENDER PC:
    uv run python simple_two_pc_test.py send

On RECEIVER PC:
    uv run python simple_two_pc_test.py receive

Manually specify audio devices to avoid auto-detection issues.
"""

import sys
from audio_protocol import MicroscopeAudioController, Command
import time


def run_sender():
    """Send commands via audio"""
    print("=" * 60)
    print("SENDER: Sending audio commands")
    print("=" * 60)
    
    # Don't specify input device - sender only needs output
    controller = MicroscopeAudioController(output_device=None)
    
    if not controller.is_initialized:
        print(f"✗ Error: {controller.last_error}")
        return
    
    print("\n✓ Audio output ready")
    input("\nPress Enter when receiver is listening...")
    
    print("\n" + "=" * 60)
    print("Test 1: PING")
    print("=" * 60)
    
    print("Sending PING...")
    if controller.send_command(Command.PING):
        print("✓ PING sent")
    else:
        print("✗ PING failed")
        return
    
    time.sleep(3)
    
    print("\n" + "=" * 60)
    print("Test 2: CAPTURE")
    print("=" * 60)
    
    print("Sending CAPTURE...")
    if controller.send_command(Command.CAPTURE):
        print("✓ CAPTURE sent")
    else:
        print("✗ CAPTURE failed")
    
    print("\n" + "=" * 60)
    print("Sender complete!")
    print("=" * 60)


def run_receiver():
    """Receive commands via audio"""
    print("=" * 60)
    print("RECEIVER: Listening for audio commands")
    print("=" * 60)
    
    import sounddevice as sd
    
    # Show available input devices
    print("\nAvailable audio input devices:")
    devices = sd.query_devices()
    for i, device in enumerate(devices):
        if device['max_input_channels'] > 0:
            print(f"  [{i}] {device['name']}")
    
    device_input = input("\nSelect input device number (or press Enter for default): ").strip()
    
    if device_input:
        input_device = int(device_input)
        print(f"\n✓ Using device {input_device}")
    else:
        input_device = None
        print("\n✓ Using default input device")
    
    controller = MicroscopeAudioController(input_device=input_device, output_device=None)
    
    if not controller.is_initialized:
        print(f"✗ Error: {controller.last_error}")
        return
    
    print("\n🎧 Listening for commands...")
    print("   Start the sender now!\n")
    
    # Listen for PING
    print("Waiting for PING (30s timeout)...")
    cmd = controller.wait_for_command(timeout=30, expected=Command.PING)
    
    if cmd == Command.PING:
        print("✓ PING received!")
    else:
        print("✗ No PING received")
        return
    
    # Listen for CAPTURE
    print("\nWaiting for CAPTURE (30s timeout)...")
    cmd = controller.wait_for_command(timeout=30, expected=Command.CAPTURE)
    
    if cmd == Command.CAPTURE:
        print("✓ CAPTURE received!")
    else:
        print("✗ No CAPTURE received")
    
    print("\n" + "=" * 60)
    print("Receiver complete!")
    print("=" * 60)


def main():
    if len(sys.argv) != 2 or sys.argv[1] not in ['send', 'receive']:
        print("Usage:")
        print("  RECEIVER PC: python simple_two_pc_test.py receive")
        print("  SENDER PC:   python simple_two_pc_test.py send")
        print()
        print("Run receiver first!")
        sys.exit(1)
    
    if sys.argv[1] == 'send':
        run_sender()
    else:
        run_receiver()


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\n\nInterrupted by user")
        sys.exit(0)
