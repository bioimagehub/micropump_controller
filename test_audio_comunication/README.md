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





This will record audio and show detected frequencies in real-time.
Run simple_tone_generator.py on the SENDER computer.

Available audio input devices:
  [0] Microsoft Sound Mapper - Input
  [1] Headset (Lenovo Wireless VoIP H
  [7] Primary Sound Capture Driver
  [8] Headset (Lenovo Wireless VoIP Headset)
  [18] Headset (Lenovo Wireless VoIP Headset)
  [22] Stereo Mix (Realtek HD Audio Stereo input)
  [23] Microphone (Realtek HD Audio Mic input)
  [27] Headset (@System32\drivers\bthhfenum.sys,#2;%1 Hands-Free%0
;(Lenovo Wireless VoIP Headset))
  [29] Headset (@System32\drivers\bthhfenum.sys,#2;%1 Hands-Free%0
;(WH-1000XM4))

Select input device (press Enter for default): 22

======================================================================
LISTENING... (Press Ctrl+C to stop)
======================================================================

[Chunk 1] Recording 1.0s...
  RMS: 5243727.0000  |  Max: 630456320.0000
  Top frequencies detected:
    1.     0.0 Hz  (magnitude: 2179348480)
    2. 22050.0 Hz  (magnitude: 2179348480)
    3.     1.0 Hz  (magnitude: 2179325184)
    4. 22049.0 Hz  (magnitude: 2179325184)
    5. 22048.0 Hz  (magnitude: 2179254528)

[Chunk 2] Recording 1.0s...
  RMS: 183593248.0000  |  Max: 14160101376.0000
  Top frequencies detected:
    1. 22016.0 Hz  (magnitude: 617989996544)
    2. 22017.0 Hz  (magnitude: 617827139584)
    3. 22015.0 Hz  (magnitude: 617134686208)
    4. 22018.0 Hz  (magnitude: 616644280320)
    5. 22014.0 Hz  (magnitude: 615266254848)

[Chunk 3] Recording 1.0s...
  RMS: 21097066496.0000  |  Max: 547134865408.0000
  Top frequencies detected:
    1.     0.0 Hz  (magnitude: 55287943790592)
    2.     1.0 Hz  (magnitude: 55250559959040)
    3.     2.0 Hz  (magnitude: 55138651734016)
    4.     3.0 Hz  (magnitude: 54952894398464)
    5.     4.0 Hz  (magnitude: 54694403637248)

[Chunk 4] Recording 1.0s...
  RMS: 2431327141888.0000  |  Max: 55059614269440.0000
  Top frequencies detected:
    1.    39.0 Hz  (magnitude: 7751196198567936)
    2.    40.0 Hz  (magnitude: 7748938656382976)
    3.    38.0 Hz  (magnitude: 7743100722085888)
    4.    41.0 Hz  (magnitude: 7735947454054400)
    5.    37.0 Hz  (magnitude: 7725081186795520)

[Chunk 5] Recording 1.0s...
  RMS: 293777910530048.0000  |  Max: 6685147197865984.0000
  Top frequencies detected:
    1.     0.0 Hz  (magnitude: 548254808717393920)
    2.     1.0 Hz  (magnitude: 547751610348994560)
    3.     2.0 Hz  (magnitude: 546244282986528768)
    4.     3.0 Hz  (magnitude: 543739904736100352)
    5.     4.0 Hz  (magnitude: 540250192268492800)

[Chunk 6] Recording 1.0s...
  RMS: 27457107448037376.0000  |  Max: 544125592799281152.0000
  Top frequencies detected:
    1.    27.0 Hz  (magnitude: 105495510653293559808)
    2.    28.0 Hz  (magnitude: 105495493061107515392)
    3.    26.0 Hz  (magnitude: 105352275074519924736)
    4.    29.0 Hz  (magnitude: 105349733003636506624)
    5.    25.0 Hz  (magnitude: 105069128840135049216)

[Chunk 7] Recording 1.0s...
C:\git\micropump_controller\test_audio_comunication\simple_audio_listener.py:18: RuntimeWarning: overflow encountered in square
  rms = np.sqrt(np.mean(audio ** 2))
C:\git\micropump_controller\.venv\Lib\site-packages\numpy\_core\_methods.py:134: RuntimeWarning: overflow encountered in reduce
  ret = umr_sum(arr, axis, dtype, out, keepdims, where=where)
  RMS: inf  |  Max: 102110448602906099712.0000
  Top frequencies detected:
    1.     0.0 Hz  (magnitude: 6015228338697775611904)
    2.     1.0 Hz  (magnitude: 6007773755414570598400)
    3.     2.0 Hz  (magnitude: 5985458982210903212032)
    4.     3.0 Hz  (magnitude: 5948419690025547988992)
    5.     4.0 Hz  (magnitude: 5896885562439500824576)

[Chunk 8] Recording 1.0s...
  RMS: inf  |  Max: 5974691438451813777408.0000
  Top frequencies detected:
    1. 22021.0 Hz  (magnitude: 1502310187237497752256512)
    2. 22022.0 Hz  (magnitude: 1501922805611949851672576)
    3. 22020.0 Hz  (magnitude: 1499742486931550228185088)
    4. 22023.0 Hz  (magnitude: 1498588700735814926073856)
    5. 22019.0 Hz  (magnitude: 1494225613416818389549056)

[Chunk 9] Recording 1.0s...
  RMS: inf  |  Max: 1456894735673589063745536.0000
  Top frequencies detected:
    1.     0.0 Hz  (magnitude: 87218032208162057286057984)
    2.     1.0 Hz  (magnitude: 87151171984266897016225792)
    3.     2.0 Hz  (magnitude: 86951117044787516928950272)
    4.     3.0 Hz  (magnitude: 86619481479830366609997824)
    5.     4.0 Hz  (magnitude: 86158921620542060234801152)

[Chunk 10] Recording 1.0s...
  RMS: inf  |  Max: 86873576156073678828732416.0000
  Top frequencies detected:
    1.    27.0 Hz  (magnitude: 18428023432379835624961605632)
    2.    28.0 Hz  (magnitude: 18421368437413851577444204544)
    3.    26.0 Hz  (magnitude: 18398003348648233290338140160)
    4.    29.0 Hz  (magnitude: 18377626337274650771241041920)
    5.    25.0 Hz  (magnitude: 18331920913270196910040285184)

[Chunk 11] Recording 1.0s...
  RMS: inf  |  Max: 16965500629677002915223437312.0000
  Top frequencies detected:
    1. 22012.0 Hz  (magnitude: 1242582465548427902758642778112)
    2. 22011.0 Hz  (magnitude: 1242084539226474127367310671872)
    3. 22013.0 Hz  (magnitude: 1241875772848999426091703599104)
    4. 22010.0 Hz  (magnitude: 1240496766278137763774980947968)
    5. 22014.0 Hz  (magnitude: 1239855204457241025254829064192)

[Chunk 12] Recording 1.0s...
  RMS: inf  |  Max: 1068436852348668021970864963584.0000
  Top frequencies detected:
    1.    29.0 Hz  (magnitude: 285806524490858209691382805692416)
    2.    28.0 Hz  (magnitude: 285515821352570397501516259786752)
    3.    30.0 Hz  (magnitude: 285339086069149295633207614504960)
    4.    27.0 Hz  (magnitude: 284458639901833796580819202998272)
    5.    31.0 Hz  (magnitude: 284124570176544768413197597147136)

[Chunk 13] Recording 1.0s...
  RMS: inf  |  Max: 283656551470442439333018546995200.0000
  Top frequencies detected:
    1.   259.0 Hz  (magnitude: 12009798538844681043356809913434112)
    2.   260.0 Hz  (magnitude: 12006860907131456835964474291650560)
    3.   258.0 Hz  (magnitude: 12003420671762282764180529625432064)
    4.   261.0 Hz  (magnitude: 11994635011303474420369570540814336)
    5.   257.0 Hz  (magnitude: 11987858527528426248744772734812160)

[Chunk 14] Recording 1.0s...
  RMS: inf  |  Max: 11822865879092470765706217458237440.0000
  Top frequencies detected:
    1. 22050.0 Hz  (magnitude: 3937620662199934154958111881151119360)
    2. 22049.0 Hz  (magnitude: 3936499742156682343109838421341765632)
    3. 22048.0 Hz  (magnitude: 3933134129813076394048864674331492352)
    4. 22047.0 Hz  (magnitude: 3927509247187213683137073428033437696)
    5. 22046.0 Hz  (magnitude: 3919603227306240273417288864317308928)

[Chunk 15] Recording 1.0s...
  RMS: inf  |  Max: 3930319945480569724777541993215557632.0000
  Top frequencies detected:
    1.    27.0 Hz  (magnitude: 200971379048861538752926627244187582464)
    2.    26.0 Hz  (magnitude: 200937689966509873328352450859801509888)
    3.    28.0 Hz  (magnitude: 200811634790823178196667618693058920448)
    4.    25.0 Hz  (magnitude: 200716895655564521244117361082301939712)
    5.    29.0 Hz  (magnitude: 200453609696499518910344101813358166016)

[Chunk 16] Recording 1.0s...
C:\git\micropump_controller\.venv\Lib\site-packages\numpy\fft\_pocketfft.py:101: RuntimeWarning: overflow encountered in cast
  return ufunc(a, fct, axes=[(axis,), (), (axis,)], out=out)
  RMS: inf  |  Max: 200714116965448820965269280308875755520.0000
  Top frequencies detected:
    1.    27.0 Hz  (magnitude:        inf)
    2. 22032.0 Hz  (magnitude:        inf)
    3. 22033.0 Hz  (magnitude:        inf)
    4. 22034.0 Hz  (magnitude:        inf)
    5. 22035.0 Hz  (magnitude:        inf)