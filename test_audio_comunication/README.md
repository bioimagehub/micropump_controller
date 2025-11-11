# Audio-Based Communication for Airgapped Microscope Control

## Overview

This folder contains an **FSK (Frequency Shift Keying) audio modem** for communicating between:
- **Microfluidics PC** (this computer) running `cli.py`
- **Microscope PC** (airgapped computer) running `microscope_control.exe`

The system uses audio tones (like old-school modems) to send commands without any physical connection.

---

## Files

- **`audio_protocol.py`** - Core FSK modem implementation with error correction
- **`microscope_audio_test.py`** - Standalone test suite for feasibility testing
- **`build_standalone.py`** - Build script to create `.exe` for airgapped transfer
- **`requirements.txt`** - Python dependencies (sounddevice, numpy)

---

## How It Works

### FSK Protocol Features

The protocol is based on Bell 202 modem standard with safety features:

- **Two frequencies for binary data:**
  - 1200 Hz = binary 0 (mark)
  - 1800 Hz = binary 1 (space)

- **Preamble sync tone (2400 Hz for 500ms)**
  - Prevents false triggers from background speech
  - Signals "start of transmission"

- **4-bit checksum**
  - Detects corrupted transmissions
  - Auto-rejects invalid data

- **Noise immunity:**
  - Minimum tone duration (80ms) filters out speech
  - Frequency tolerance (±100 Hz) handles speaker variations
  - Minimum signal power threshold

- **Total transmission time: ~1.3 seconds per command**
  - Too long for accidental speech patterns to trigger

### Available Commands

```python
Command.CAPTURE  # Trigger image capture
Command.DONE     # Capture complete
Command.ERROR    # Capture failed
Command.PING     # Test connection
Command.PONG     # Respond to ping
```

---

## Testing on Two Computers

### Step 1: Install Dependencies (on THIS PC)

```powershell
cd test_audio_comunication
pip install -r requirements.txt
```

### Step 2: Run Feasibility Test (on THIS PC first)

```powershell
python microscope_audio_test.py
```

**Expected output:**
- Test 1: Hear system beep ✓
- Test 2: Hear 1200 Hz tone ✓
- Test 3: Clap hands, see audio detected ✓
- Test 4: Frequency detection working ✓
- Test 5: FSK protocol encode/decode ✓
- Test 6: Noise rejection working ✓

### Step 3: Transfer to Second Test PC

**Option A: Standalone Executable (Recommended)**

```powershell
# Build .exe
pip install pyinstaller
python build_standalone.py

# Copy to USB stick:
# dist/microscope_audio_test.exe
```

**Option B: Python Script (if Python installed on test PC)**

Copy to USB stick:
- `audio_protocol.py`
- `microscope_audio_test.py`
- `requirements.txt`

On test PC:
```powershell
pip install -r requirements.txt
python microscope_audio_test.py
```

### Step 4: Run Test on Second PC

Run the same test - all 6 tests should pass on both PCs.

### Step 5: Two-PC Communication Test

**On PC 1 (sender):**
```python
from audio_protocol import MicroscopeAudioController, Command

controller = MicroscopeAudioController()
controller.send_command(Command.PING)
print("Sent PING - listen on other PC!")
```

**On PC 2 (receiver):**
```python
from audio_protocol import MicroscopeAudioController

controller = MicroscopeAudioController()
cmd = controller.wait_for_command(timeout=30)
print(f"Received: {cmd.name if cmd else 'Nothing'}")
```

Position speaker near microphone between the two PCs. If you receive the PING command, the system is working! 🎧

---

## Troubleshooting

### No audio output?
- Check volume is up (>50%)
- Verify speakers/headphones plugged in
- Test with: `powershell -c "[console]::beep(1000,500)"`

### No audio input?
- Check microphone is plugged in
- Open Windows Sound settings → Recording devices
- Verify microphone is not muted
- Test levels while speaking

### FSK protocol fails?
- **Audio loopback may not work** - use separate speaker/mic
- Position speaker close to microphone (within 1 meter)
- Reduce background noise
- Increase volume on sender PC

### Checksum errors?
- Audio quality too low
- Too much background noise
- Increase speaker volume
- Move speaker closer to microphone

---

## Next Steps (After Successful Testing)

Once both test PCs pass:

1. **Build microscope control software** (`microscope_control.exe`)
2. **Integrate with `cli.py`** on microfluidics PC
3. **Add YAML command:** `microscope_capture: 0`
4. **Deploy to production** microscope PC

---

## Production Usage (Future)

### On Microfluidics PC (this computer)

Add to YAML config:
```yaml
required hardware:
  microscope: true

run:
  - pump_on: full flow
  - microscope_capture: 0  # Trigger + wait for completion
  - duration: 5
  - pump_off: 0
```

### On Microscope PC (airgapped)

Run `microscope_control.exe`:
- Listens for `CAPTURE` command via audio
- Triggers microscope image capture
- Sends `DONE` response when complete

---

## Technical Details

**Why FSK instead of simple beeps?**
- Digital data transmission (not just "beep = trigger")
- Error detection with checksums
- Multiple commands supported
- Immune to false triggers

**Why so slow (10 baud)?**
- Maximum reliability over acoustic channel
- Better noise immunity
- Easier frequency discrimination
- Still fast enough for microscope control (1.3s per command)

**Can someone talking trigger it?**
- No! Requires sustained 2400 Hz preamble for 500ms
- Human speech doesn't create pure sustained tones
- Checksum prevents random noise from being decoded as valid command

---

## Safety Features Summary

✓ Preamble prevents false triggers from speech  
✓ Checksum detects corrupted transmissions  
✓ Frequency tolerance handles speaker variations  
✓ 1.3s transmission too long for accidental patterns  
✓ Minimum signal power filters out distant noise  
✓ Auto-retry logic for failed transmissions


