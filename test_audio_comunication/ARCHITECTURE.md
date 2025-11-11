# Audio Communication System Architecture

## System Overview

```
┌─────────────────────────────────────────────────────────────────┐
│                    AIRGAPPED COMMUNICATION                       │
│                     (No Network/Cables)                          │
└─────────────────────────────────────────────────────────────────┘

    Microfluidics PC                    Microscope PC
    ┌──────────────┐                   ┌──────────────┐
    │              │                   │              │
    │   cli.py     │                   │  Microscope  │
    │              │    🔊 Audio 🎧    │   Control    │
    │ MicroscopeAu │ ◄═══════════════► │   Software   │
    │ dioController│                   │              │
    │              │                   │              │
    └──────────────┘                   └──────────────┘
         │                                    │
    [Speaker] ──── Sound Waves ────► [Microphone]
         │                                    │
    [Microphone] ◄─── Sound Waves ──── [Speaker]
```

## Communication Flow

```
Trigger Image Capture:
──────────────────────
Microfluidics PC                          Microscope PC
      │                                         │
      │  🔊 Send: Command.CAPTURE              │
      │────────────────────────────────────────►│
      │     (FSK: 1.3 seconds)                 │
      │                                         │ ⏱️ Capture image
      │                                         │    (2-10 seconds)
      │                                         │
      │  🎧 Receive: Command.DONE               │
      │◄────────────────────────────────────────│
      │     (FSK: 1.3 seconds)                 │
      │                                         │
      ✓ Continue experiment                     ✓ Ready for next
```

## FSK Protocol Structure

```
Single Command Transmission (~1.3 seconds):
────────────────────────────────────────────

┌─────────┬─────────┬──────────┬──────────┬─────────┐
│Preamble │ Bit 0   │ Bit 1    │ Bit 2    │Postamble│
│500ms    │ 100ms   │ 100ms    │ 100ms    │ 200ms   │
│2400Hz   │1200/1800│1200/1800 │1200/1800 │ silence │
└─────────┴─────────┴──────────┴──────────┴─────────┘
   ▲           ▲         ▲          ▲          ▲
   │           │         │          │          │
   │           └─────────┴──────────┘          │
   │              8 bits total:                │
   │           4 bits data + 4 bits checksum   │
   │                                           │
   └─ Sync tone (prevents false triggers)     └─ End marker

Example: Command.CAPTURE (value=1)
  Binary: 0001 (4 bits data)
  Checksum: 0001 (4 bits)
  
  Tones: [2400Hz-500ms][1200][1200][1200][1800][1200][1200][1200][1800][silence]
         └─Preamble──┘└─────────Data──────┘└────Checksum────┘
```

## Frequency Spectrum

```
Human Speech Range: ~80-300 Hz (fundamentals)
                    ~300-3400 Hz (harmonics)
                    
FSK Frequencies:    1200 Hz  ◄── Binary 0 (mark)
                    1800 Hz  ◄── Binary 1 (space)
                    2400 Hz  ◄── Preamble (sync)
                    
Why These Frequencies?
- Well above speech fundamentals
- Within clear audio range (20-20,000 Hz)
- Easy to discriminate with FFT
- Less affected by room acoustics
```

## Safety Mechanisms

```
False Trigger Prevention:
─────────────────────────

Background Noise     ─→  [Preamble Detector]  ─→  ✗ Rejected
(random frequencies)         "No 2400Hz tone"

Speech/Conversation  ─→  [Preamble Detector]  ─→  ✗ Rejected
(varying tones)          "No sustained 500ms"

FSK Transmission     ─→  [Preamble Detector]  ─→  ✓ Continue
(2400Hz, 500ms)          "Valid sync"
                              │
                              ▼
                        [Decode 8 bits]
                              │
                              ▼
                        [Checksum Verify]
                              │
                    ┌─────────┴─────────┐
                    ✓                   ✗
              Valid Command         Rejected
```

## Two-PC Test Setup

```
Physical Setup:
───────────────

┌─────────────────┐                  ┌─────────────────┐
│   Computer 1    │                  │   Computer 2    │
│   (Sender)      │                  │   (Receiver)    │
│                 │                  │                 │
│  🔊 [Speaker] ──┼──► Sound ►──────┼─► [Mic] 🎧     │
│                 │    1-2 meters    │                 │
│  🎧 [Mic]    ◄──┼───◄ Sound ◄─────┼──  [Speaker] 🔊│
│                 │                  │                 │
└─────────────────┘                  └─────────────────┘

Terminal Commands:
──────────────────
Computer 1:                          Computer 2:
$ python two_pc_test.py sender       $ python two_pc_test.py receiver
                                     (Start this FIRST!)
```

## Production Deployment (Future)

```
Final System Architecture:
──────────────────────────

┌───────────────────────────┐       ┌─────────────────────────────┐
│  Microfluidics PC         │       │  Microscope PC (Airgapped)  │
│  ─────────────────        │       │  ──────────────────────────  │
│                           │       │                             │
│  ┌─────────────────┐      │       │  ┌────────────────────┐    │
│  │   cli.py        │      │       │  │ microscope_control │    │
│  │                 │      │       │  │       .exe         │    │
│  │ - Pump control  │      │       │  │                    │    │
│  │ - Valve control │      │       │  │ - Listen for       │    │
│  │ - YAML configs  │      │       │  │   CAPTURE cmd      │    │
│  └────────┬────────┘      │       │  │ - Trigger camera   │    │
│           │               │       │  │ - Send DONE        │    │
│  ┌────────▼────────┐      │       │  └──────────┬─────────┘    │
│  │ microscope.py   │      │       │             │              │
│  │                 │      │       │  ┌──────────▼─────────┐    │
│  │ Audio FSK       │🔊🎧  │  🔊🎧 │  │  Microscope API    │    │
│  │ Controller      │◄═════╪═══════╪═►│  (MicroManager/    │    │
│  └─────────────────┘      │       │  │   PyroScope/etc)   │    │
│                           │       │  └────────────────────┘    │
└───────────────────────────┘       └─────────────────────────────┘
```

## Command Reference

```python
# Available Commands
Command.CAPTURE   # 0b0001 - Trigger image capture
Command.DONE      # 0b0010 - Capture complete
Command.ERROR     # 0b0011 - Capture failed
Command.PING      # 0b0100 - Test connection
Command.PONG      # 0b0101 - Respond to ping

# Usage Examples
controller = MicroscopeAudioController()

# Send command
controller.send_command(Command.CAPTURE)

# Wait for response
response = controller.wait_for_command(expected=Command.DONE)

# High-level trigger (send + wait)
success = controller.trigger_and_wait(timeout=60)
```
